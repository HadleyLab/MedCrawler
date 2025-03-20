"""
Base crawler module with core functionality for medical literature medcrawler.

This module provides the foundation for all crawler implementations, including:
- HTTP request handling with retry logic
- Rate limiting and backoff strategies
- Caching with time-based expiration
- Abstract interfaces for crawler implementations
"""
import asyncio
import logging
import time
import json
import ssl
import hashlib
from abc import ABC, abstractmethod
from functools import wraps, lru_cache
from typing import Dict, Any, Optional, AsyncGenerator, Callable, TypeVar, Union, Set, List, Tuple
import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_not_exception_type,
    before_sleep_log,
    after_log,
    RetryError,
    wait_fixed,
    wait_chain
)

from medcrawler.config import CrawlerConfig, DEFAULT_CRAWLER_CONFIG
from medcrawler.exceptions import APIError, RateLimitError

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
T = TypeVar('T')

# Create a custom SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


# Cache expiration times dictionary to track TTL for cached items
_cache_expiry = {}
_caches = {}  # Keep for backward compatibility with tests


class TimedCache:
    """Cache with time-based expiration for items.
    
    Implements a simple in-memory cache with TTL (time-to-live) for each item
    and automatic eviction of oldest entries when size limits are reached.
    """
    
    def __init__(self, ttl_seconds: int = 3600, maxsize: int = 1000):
        """Initialize a new timed cache."""
        self.ttl = ttl_seconds
        self.maxsize = maxsize
        self.cache: Dict[str, Tuple[Any, float]] = {}
        logger.debug(f"TimedCache initialized: TTL={ttl_seconds}s, maxsize={maxsize}")
        
    def get(self, key: str) -> Optional[Any]:
        """Get an item from the cache if it exists and hasn't expired."""
        if key not in self.cache:
            return None
            
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl:
            logger.debug(f"Cache item expired: {key}")
            del self.cache[key]
            return None
            
        logger.debug(f"Cache hit: {key}")
        return value
        
    def set(self, key: str, value: Any) -> None:
        """Store an item in the cache."""
        if len(self.cache) >= self.maxsize and key not in self.cache:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            logger.debug(f"Cache evicting oldest item: {oldest_key}")
            del self.cache[oldest_key]
            
        self.cache[key] = (value, time.time())
        logger.debug(f"Cache set: {key}")
        
    def clear(self) -> None:
        """Clear all cache entries."""
        logger.debug(f"Clearing cache with {len(self.cache)} items")
        self.cache.clear()


def generate_cache_key(*args, **kwargs) -> str:
    """Generate a consistent cache key for function arguments.
    
    Uses a hash of the stringified args and kwargs to create a unique key.
    
    Args:
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key
        
    Returns:
        String hash to use as a cache key
    """
    # Create a list of string representations of all args
    key_parts = [str(arg) for arg in args]
    
    # Add sorted kwargs to ensure consistent ordering
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    # Join all parts and hash to create a fixed-length key
    key_str = ":".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def api_retry(config: Optional[CrawlerConfig] = None) -> Callable:
    """Retry decorator for API calls with exponential backoff.
    
    Implements a standardized retry strategy using tenacity with settings
    from the provided configuration.
    
    Args:
        config: Configuration object with retry settings.
               If not provided, the default configuration will be used.
    
    Returns:
        A decorated function that will retry on specified exceptions.
    """
    cfg = config or DEFAULT_CRAWLER_CONFIG
    
    # Use tenacity's retry decorator with our configuration
    return retry(
        stop=stop_after_attempt(cfg.max_retries),
        wait=wait_chain(
            # Start with fixed wait time
            wait_fixed(cfg.retry_wait),
            # Then switch to exponential backoff
            wait_exponential(
                multiplier=cfg.retry_wait,
                exp_base=cfg.retry_exponential_base,
                max=cfg.retry_max_wait
            )
        ),
        retry=retry_if_exception_type((
            aiohttp.ClientError, 
            asyncio.TimeoutError, 
            json.JSONDecodeError,
            ValueError,
            APIError
        )) & retry_if_not_exception_type(RateLimitError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True
    )


def async_timed_cache(ttl_seconds: int = 3600, maxsize: int = 128):
    """Async-compatible cache with time-based expiration.
    
    Uses a simple dictionary-based cache with timestamp checking.
    
    Args:
        ttl_seconds: Time-to-live for cache entries in seconds
        maxsize: Maximum number of items to store in the cache
        
    Returns:
        A decorated function that will cache results with TTL expiration
    """
    def decorator(func):
        # Create simple cache storage - key -> (result, timestamp)
        cache = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate a unique key for these arguments
            key = generate_cache_key(func.__qualname__, *args, **kwargs)
            
            # Check for cached result
            if key in cache:
                result, timestamp = cache[key]
                # If within TTL, return cached result
                if time.time() - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__qualname__}")
                    return result
                else:
                    # Expired, remove from cache
                    logger.debug(f"Cache expired for {func.__qualname__}")
                    del cache[key]
            
            # Not in cache or expired, call the function
            logger.debug(f"Cache miss for {func.__qualname__}, executing function")
            result = await func(*args, **kwargs)
            
            # Store in cache with timestamp
            cache[key] = (result, time.time())
            
            # Limit cache size if needed
            if len(cache) > maxsize:
                # Find the oldest entry
                oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                # Remove it
                if oldest_key != key:  # Do not remove what we just added
                    del cache[oldest_key]
                    logger.debug(f"Cache evicted oldest item: {oldest_key}")
            
            return result
        
        # Add method to clear the cache
        wrapper.cache_clear = lambda: cache.clear()
        
        return wrapper
    return decorator


class BaseCrawler(ABC):
    """Base class for medical literature medcrawler."""
    
    def __init__(
        self,
        base_url: str,
        config: Optional[CrawlerConfig] = None
    ):
        """Initialize a crawler with a base URL and configuration."""
        self.base_url = base_url.rstrip('/')
        self.config = config or DEFAULT_CRAWLER_CONFIG
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {"User-Agent": self.config.user_agent}
        self._last_request_time = 0.0  # Instance-level rate limiting
        
        # Setup debug mode based on environment
        self.debug_mode = logger.getEffectiveLevel() <= logging.DEBUG
        logger.info(f"Initialized {self.__class__.__name__} with base URL: {self.base_url}")
        
    async def __aenter__(self):
        """Setup resources for async context."""
        if not self.session:
            logger.debug(f"{self.__class__.__name__}: Creating new aiohttp session")
            conn = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(headers=self.headers, connector=conn)
        
        # Reset state for clean test isolation
        self._last_request_time = 0.0
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources when exiting async context."""
        if self.session:
            logger.debug(f"{self.__class__.__name__}: Closing aiohttp session")
            await self.session.close()
            self.session = None
            
    @api_retry()
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        error_prefix: str = "API Error"
    ) -> Union[Dict[str, Any], str]:
        """Make an HTTP request with retry logic."""
        if not self.session:
            raise RuntimeError(f"{self.__class__.__name__} must be used within async context")
        
        # Always wait for min_interval since last request
        now = time.time()
        time_since_last = now - self._last_request_time
        logger.debug(f"Time since last request: {time_since_last:.3f}s")
        
        if time_since_last < self.config.min_interval:
            delay = self.config.min_interval - time_since_last
            logger.debug(f"Sleeping for {delay:.3f}s to enforce rate limit")
            await asyncio.sleep(delay)
            logger.debug("Finished sleeping")
        
        # Update last_request_time after sleeping
        self._last_request_time = time.time()
        logger.debug(f"Updated last_request_time to {self._last_request_time}")
            
        endpoint = endpoint.lstrip('/')
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        
        logger.info(f"Making API request to: {url}")
        logger.debug(f"With parameters: {json.dumps(params or {}, indent=2)}")
            
        try:
            async with self.session.get(url, params=params, timeout=30) as response:
                status = response.status
                logger.debug(f"Response status: {status}")
                
                if self.debug_mode:
                    logger.debug(f"Response headers: {dict(response.headers)}")
                
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    message = f"Rate limit exceeded: {await response.text()}"
                    logger.warning(message)
                    retry_after_int = int(retry_after) if retry_after.isdigit() else None
                    raise RateLimitError(message, retry_after_int)
                
                if status == 404:
                    message = f"Resource not found: {await response.text()}"
                    logger.error(message)
                    raise APIError(message)
                
                if status >= 400:
                    error_text = await response.text()
                    message = f"HTTP {status}: {error_text[:200]}"
                    logger.error(f"API error {status}: {error_text[:200]}")
                    raise APIError(message)
                
                content_type = response.headers.get('Content-Type', '').lower()
                
                try:
                    if 'application/json' in content_type or endpoint.endswith('json'):
                        response_data = await response.json()
                        if self.debug_mode:
                            preview = json.dumps(response_data, indent=2)[:500]
                            logger.debug(f"JSON Response preview: {preview}...")
                    else:
                        response_data = await response.text()
                        if self.debug_mode:
                            logger.debug(f"Text Response preview: {response_data[:500]}...")
                    
                    return response_data
                except json.JSONDecodeError as e:
                    response_data = await response.text()
                    logger.warning(f"Failed to parse JSON response: {str(e)}")
                    return response_data
                
        except aiohttp.ClientResponseError as e:
            message = f"{error_prefix}: {str(e)}"
            logger.error(f"Request failed: {str(e)}")
            raise APIError(message)
            
        except Exception as e:
            message = f"{error_prefix}: {str(e)}"
            logger.exception(f"Exception during request to {url}: {str(e)}")
            raise APIError(message)

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        old_item_ids: Optional[Set[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Search for items matching the query and yield their IDs."""
        pass
    
    @abstractmethod    
    async def get_metadata_request_params(self, item_id: str) -> Dict:
        """Get parameters for requesting item metadata."""
        pass
    
    @abstractmethod
    async def get_metadata_endpoint(self) -> str:
        """Get the endpoint URL for metadata requests."""
        pass
    
    @abstractmethod    
    def extract_metadata(self, response_data: Any) -> Dict[str, Any]:
        """Extract metadata from the API response."""
        pass
            
    @async_timed_cache()
    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific item."""
        endpoint = await self.get_metadata_endpoint()
        params = await self.get_metadata_request_params(item_id)
        
        try:
            logger.info(f"Fetching item {item_id}")
            response_data = await self._make_request(
                endpoint, 
                params=params,
                error_prefix=f"Error fetching item {item_id}"
            )
            return self.extract_metadata(response_data)
        except Exception as e:
            logger.error(f"Failed to get item {item_id}: {str(e)}")
            raise
    
    async def get_items_batch(
        self,
        item_ids: List[str],
        batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get multiple items in parallel batches."""
        batch_size = batch_size or self.config.default_batch_size
        results = []
        total = len(item_ids)
        
        logger.info(f"Fetching {total} items in batches of {batch_size}")
        
        for i in range(0, total, batch_size):
            batch = item_ids[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total - 1) // batch_size + 1
            
            tasks = [self.get_item(item_id) for item_id in batch]
            logger.info(f"Fetching batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching item {batch[j]}: {result}")
                else:
                    results.append(result)
            
            logger.info(f"Completed batch {batch_num}/{total_batches}: " 
                       f"{len([r for r in batch_results if not isinstance(r, Exception)])} successful, "
                       f"{len([r for r in batch_results if isinstance(r, Exception)])} failed")
        
        return results