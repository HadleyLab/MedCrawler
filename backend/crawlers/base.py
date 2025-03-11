"""
Base crawler functionality for medical literature data sources.

This module provides the foundation for all literature crawlers,
with common functionality for API requests, caching, error handling,
and rate limiting compliance.
"""
import asyncio
import logging
import time
import json
import ssl
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

# Create a custom SSL context that doesn't verify certificates
# This is necessary for development environments with SSL certificate issues
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def api_retry(config: Optional[CrawlerConfig] = None) -> Callable:
    """
    Retry decorator for API calls with exponential backoff.
    
    Args:
        config: Optional crawler configuration override
        
    Returns:
        Decorated function with retry behavior
    """
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
    """
    Cache with time-based expiration for items.
    
    Provides a simple cache mechanism with TTL expiration for reducing
    unnecessary API calls for frequently accessed data.
    """
    
    def __init__(self, ttl_seconds: int = 3600, maxsize: int = 1000):
        """
        Initialize a timed cache.
        
        Args:
            ttl_seconds: Time-to-live in seconds for cache items
            maxsize: Maximum cache size before oldest items are evicted
        """
        self.ttl = ttl_seconds
        self.maxsize = maxsize
        self.cache: Dict[str, tuple[Any, float]] = {}
        logger.debug(f"TimedCache initialized: TTL={ttl_seconds}s, maxsize={maxsize}")
        
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
            # Expired item
            logger.debug(f"Cache item expired: {key}")
            del self.cache[key]
            return None
            
        logger.debug(f"Cache hit: {key}")
        return value
        
    def set(self, key: str, value: Any) -> None:
        """
        Store an item in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # Evict oldest item if we've reached max size
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
    logger.debug(f"Creating async_timed_cache decorator: TTL={ttl_seconds}s, maxsize={maxsize}")
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key from function arguments
            key = str((func.__name__, args, frozenset(kwargs.items())))
            
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            logger.debug(f"Cache miss for {func.__name__}, fetching data")
            result = await func(*args, **kwargs)
            cache.set(key, result)
            return result
            
        return wrapper
    return decorator


class BaseCrawler(ABC):
    """
    Base class for medical literature crawlers.
    
    Provides common functionality for making API requests, handling errors,
    managing rate limits, and processing responses.
    """
    
    def __init__(
        self,
        notification_manager: NotificationManager,
        base_url: str,
        config: Optional[CrawlerConfig] = None
    ):
        """
        Initialize a crawler with a base URL and configuration.
        
        Args:
            notification_manager: Manager for displaying user notifications
            base_url: Base API URL for this crawler
            config: Optional crawler configuration
        """
        self.notification_manager = notification_manager
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.config = config or DEFAULT_CRAWLER_CONFIG
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {"User-Agent": self.config.user_agent}
        
        # Setup debug mode based on environment
        self.debug_mode = logger.getEffectiveLevel() <= logging.DEBUG
        logger.info(f"Initialized {self.__class__.__name__} with base URL: {self.base_url}")
    
    async def __aenter__(self):
        """
        Setup resources for async context.
        
        Returns:
            Self instance for context manager use
        """
        if not self.session:
            logger.debug(f"{self.__class__.__name__}: Creating new aiohttp session with SSL verification disabled")
            # Use the custom SSL context that doesn't verify certificates
            conn = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(headers=self.headers, connector=conn)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Cleanup resources when exiting async context.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
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
        """
        Make HTTP request with retry logic and notification handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters for the request
            error_prefix: Prefix for error messages
            
        Returns:
            Parsed JSON response or raw text
            
        Raises:
            APIError: For HTTP errors or API-specific errors
            RateLimitError: When rate limits are exceeded
        """
        if not self.session:
            raise RuntimeError(f"{self.__class__.__name__} must be used within async context")
        
        # Add a small delay between requests to avoid hitting rate limits
        await asyncio.sleep(self.config.min_interval)
            
        # Clean up endpoint and combine with base URL
        endpoint = endpoint.lstrip('/')  # Remove leading slash if present
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        
        # Debug logging    
        logger.info(f"Making API request to: {url}")
        logger.debug(f"With parameters: {json.dumps(params or {}, indent=2)}")
            
        try:
            async with self.session.get(url, params=params, timeout=30) as response:
                status = response.status
                logger.debug(f"Response status: {status}")
                
                if self.debug_mode:
                    logger.debug(f"Response headers: {dict(response.headers)}")
                
                # Handle rate limiting
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
                
                # Handle common HTTP errors
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
                        type="negative"
                    )
                    raise APIError(message)
                
                content_type = response.headers.get('Content-Type', '').lower()
                
                try:
                    if 'application/json' in content_type or endpoint.endswith('json'):
                        response_data = await response.json()
                        if self.debug_mode:
                            # Log JSON response preview in debug mode only
                            preview = json.dumps(response_data, indent=2)[:500]
                            logger.debug(f"JSON Response preview: {preview}...")
                    else:
                        response_data = await response.text()
                        if self.debug_mode:
                            # Log text response preview in debug mode only
                            logger.debug(f"Text Response preview: {response_data[:500]}...")
                    
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
                type="negative"
            )
            raise APIError(message)
            
        except Exception as e:
            message = f"{error_prefix}: {str(e)}"
            logger.exception(f"Exception during request to {url}: {str(e)}")
            await self.notification_manager.notify(
                error_prefix,
                message,
                type="negative"
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
        """
        Get detailed information for a specific item.
        
        Args:
            item_id: ID of the item to retrieve
            
        Returns:
            Dictionary containing item metadata
            
        Raises:
            APIError: If the API request fails
        """
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
        """
        Get multiple items in parallel batches.
        
        Args:
            item_ids: List of item IDs to retrieve
            batch_size: Optional override for batch size
            
        Returns:
            List of metadata dictionaries for successfully retrieved items
        """
        batch_size = batch_size or self.config.default_batch_size
        results = []
        total = len(item_ids)
        
        logger.info(f"Fetching {total} items in batches of {batch_size}")
        
        for i in range(0, total, batch_size):
            batch = item_ids[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total - 1) // batch_size + 1
            
            # Create tasks for this batch
            tasks = [self.get_item(item_id) for item_id in batch]
            
            # Log batch progress
            logger.info(f"Fetching batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            # Notify user of progress
            await self.notification_manager.notify(
                "Batch Progress",
                f"Fetching items {i + 1}-{min(i + batch_size, total)} of {total} ({batch_num}/{total_batches})",
                type="info"
            )
            
            # Execute batch requests in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching item {batch[j]}: {result}")
                else:
                    results.append(result)
            
            # Update on batch completion
            logger.info(f"Completed batch {batch_num}/{total_batches}: " 
                       f"{len([r for r in batch_results if not isinstance(r, Exception)])} successful, "
                       f"{len([r for r in batch_results if isinstance(r, Exception)])} failed")
                    
        # Final notification of overall results
        await self.notification_manager.notify(
            "Batch Processing Complete", 
            f"Retrieved {len(results)} of {total} items successfully",
            type="positive"
        )
        
        return results