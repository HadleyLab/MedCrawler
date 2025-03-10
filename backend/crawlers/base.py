"""Base crawler functionality."""
import asyncio
import logging
import time
import json
from abc import ABC, abstractmethod
from functools import wraps
from typing import Dict, Any, Optional, AsyncGenerator, Callable, TypeVar, Union, Set, List
import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_not_exception_type,
    before_sleep_log,
    after_log,
    RetryError
)
from backend.utils.notification_manager import NotificationManager
from config import CrawlerConfig, DEFAULT_CRAWLER_CONFIG
from .exceptions import APIError, RateLimitError

logger = logging.getLogger(__name__)
T = TypeVar('T')

def api_retry(config: Optional[CrawlerConfig] = None) -> Callable:
    """Retry decorator for API calls with exponential backoff."""
    cfg = config or DEFAULT_CRAWLER_CONFIG
    
    return retry(
        stop=stop_after_attempt(cfg.max_retries),
        wait=wait_exponential(multiplier=cfg.retry_wait, min=cfg.retry_wait, max=cfg.retry_wait * 10),
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

class TimedCache:
    """Cache with time-based expiration for items."""
    
    def __init__(self, ttl_seconds: int = 3600, maxsize: int = 1000):
        """
        Initialize a timed cache.
        
        Args:
            ttl_seconds: Time-to-live in seconds
            maxsize: Maximum cache size
        """
        self.ttl = ttl_seconds
        self.maxsize = maxsize
        self.cache: Dict[str, tuple[Any, float]] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get an item from the cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self.cache:
            return None
            
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
            
        return value
        
    def set(self, key: str, value: Any) -> None:
        """
        Store an item in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if len(self.cache) >= self.maxsize and key not in self.cache:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            
        self.cache[key] = (value, time.time())
        
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

def async_timed_cache(ttl_seconds: int = 3600, maxsize: int = 1000):
    """
    Cache decorator for async functions with TTL expiration.
    
    Args:
        ttl_seconds: Time-to-live in seconds
        maxsize: Maximum cache size
        
    Returns:
        Decorated function with timed caching
    """
    cache = TimedCache(ttl_seconds=ttl_seconds, maxsize=maxsize)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = str((args, frozenset(kwargs.items())))
            
            cached_value = cache.get(key)
            if (cached_value is not None):
                logger.debug(f"Cache hit for {func.__name__}({args}, {kwargs})")
                return cached_value
                
            result = await func(*args, **kwargs)
            cache.set(key, result)
            return result
            
        return wrapper
    return decorator

class BaseCrawler(ABC):
    """Base class for medical literature crawlers."""
    
    def __init__(
        self,
        notification_manager: NotificationManager,
        base_url: str,
        config: Optional[CrawlerConfig] = None
    ):
        """Initialize a crawler with a base URL."""
        self.notification_manager = notification_manager
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.config = config or DEFAULT_CRAWLER_CONFIG
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {"User-Agent": self.config.user_agent}
        
        # Setup debug mode based on environment
        self.debug_mode = logger.level <= logging.DEBUG

    async def __aenter__(self):
        """Setup resources for async context."""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources when exiting async context."""
        if self.session:
            await self.session.close()
            self.session = None
            
    @api_retry()
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        error_prefix: str = "API Error"
    ) -> Union[Dict[str, Any], str]:
        """Make HTTP request with retry logic and notification handling."""
        if not self.session:
            raise RuntimeError("Crawler must be used within async context")
        
        # Add a small delay between requests to avoid hitting rate limits
        await asyncio.sleep(self.config.min_interval)
            
        # Clean up endpoint and combine with base URL
        endpoint = endpoint.lstrip('/')  # Remove leading slash if present
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        
        # Debug logging    
        logger.info(f"Making API request to: {url}")
        logger.info(f"With parameters: {json.dumps(params, indent=2)}")
            
        try:
            async with self.session.get(url, params=params, timeout=30) as response:
                status = response.status
                logger.info(f"Response status: {status}")
                logger.info(f"Response headers: {dict(response.headers)}")
                
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    message = f"Rate limit exceeded: {await response.text()}"
                    logger.warning(message)
                    await self.notification_manager.notify(
                        "Rate Limit Exceeded",
                        f"Please wait {retry_after} seconds",
                        type="warning"
                    )
                    raise RateLimitError(message)
                
                if status == 404:
                    message = f"Resource not found: {await response.text()}"
                    logger.error(message)
                    raise APIError(message)
                
                if status >= 400:
                    error_text = await response.text()
                    message = f"HTTP {status}: {error_text[:200]}"
                    logger.error(f"API error {status}: {error_text[:200]}")
                    await self.notification_manager.notify(
                        error_prefix,
                        message,
                        type="error"
                    )
                    raise APIError(message)
                
                content_type = response.headers.get('Content-Type', '').lower()
                
                try:
                    if 'application/json' in content_type or endpoint.endswith('json'):
                        response_data = await response.json()
                        # Log JSON response preview
                        logger.info(f"JSON Response preview: {json.dumps(response_data, indent=2)[:500]}...")
                    else:
                        response_data = await response.text()
                        # Log text response preview
                        logger.info(f"Text Response preview: {response_data[:500]}...")
                    
                    return response_data
                except json.JSONDecodeError as e:
                    # If JSON parsing fails, return the raw text
                    response_data = await response.text()
                    logger.warning(f"Failed to parse JSON response: {str(e)}")
                    return response_data
                
        except aiohttp.ClientResponseError as e:
            message = f"{error_prefix}: {str(e)}"
            logger.error(f"Request failed: {str(e)}")
            await self.notification_manager.notify(
                error_prefix,
                message,
                type="error"
            )
            raise APIError(message)
            
        except Exception as e:
            message = f"{error_prefix}: {str(e)}"
            logger.exception(f"Exception during request to {url}: {str(e)}")
            await self.notification_manager.notify(
                error_prefix,
                message,
                type="error"
            )
            raise APIError(message)

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        old_item_ids: Optional[Set[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Search for items matching the query and yield their IDs.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            old_item_ids: Set of IDs to exclude from results
            
        Yields:
            Item IDs matching the search criteria
        """
        pass
    
    @abstractmethod    
    async def get_metadata_request_params(self, item_id: str) -> Dict:
        """
        Get parameters for requesting item metadata.
        
        Args:
            item_id: ID of the item to retrieve
            
        Returns:
            Dictionary containing request parameters
        """
        pass
    
    @abstractmethod
    async def get_metadata_endpoint(self) -> str:
        """
        Get the endpoint URL for metadata requests.
        
        Returns:
            URL string for the metadata endpoint
        """
        pass
    
    @abstractmethod    
    def extract_metadata(self, response_data: Any) -> Dict[str, Any]:
        """
        Extract metadata from the API response.
        
        Args:
            response_data: Raw response data from the API
            
        Returns:
            Dictionary containing extracted metadata
        """
        pass
            
    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific item."""
        endpoint = await self.get_metadata_endpoint()
        params = await self.get_metadata_request_params(item_id)
        
        try:
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
        item_ids: list[str],
        batch_size: Optional[int] = None
    ) -> list[Dict[str, Any]]:
        """Get multiple items in parallel batches."""
        batch_size = batch_size or self.config.default_batch_size
        results = []
        total = len(item_ids)
        
        for i in range(0, total, batch_size):
            batch = item_ids[i:i + batch_size]
            tasks = [self.get_item(item_id) for item_id in batch]
            
            logger.info(
                f"Fetching batch {i//batch_size + 1}/{(total-1)//batch_size + 1} ({len(batch)} items)"
            )
            
            await self.notification_manager.notify(
                "Batch Progress",
                f"Fetching items {i + 1}-{min(i + batch_size, total)} of {total}",
                type="info"
            )
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching item {batch[j]}: {result}")
                else:
                    results.append(result)
                    
        return results