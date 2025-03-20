"""
Tests for the BaseCrawler and related components.

This module contains tests for the core functionality of the base crawler,
including the caching mechanism, rate limiting, session management,
batch processing, and error handling.
"""
import asyncio
import time
import hashlib
import pytest
from tenacity import RetryError

from medcrawler.base import BaseCrawler, api_retry, async_timed_cache, generate_cache_key, _cache_expiry
from medcrawler.config import CrawlerConfig
from medcrawler.clinical_trials import ClinicalTrialsCrawler
from medcrawler.exceptions import APIError, RateLimitError


@pytest.mark.asyncio
async def test_generate_cache_key():
    """Test cache key generation function."""
    # Test with different args and kwargs
    key1 = generate_cache_key("arg1", "arg2", kwarg1="value1")
    key2 = generate_cache_key("arg1", "arg2", kwarg1="value1")
    key3 = generate_cache_key("arg1", "arg2", kwarg1="different")
    
    # Same arguments should produce same key
    assert key1 == key2
    
    # Different arguments should produce different keys
    assert key1 != key3
    
    # Test keyword argument order shouldn't matter
    key4 = generate_cache_key("arg", kwarg1="value1", kwarg2="value2")
    key5 = generate_cache_key("arg", kwarg2="value2", kwarg1="value1")
    assert key4 == key5


@pytest.mark.asyncio
async def test_async_timed_cache():
    """Test the async_timed_cache implementation."""
    # Clear any existing cache entries
    _cache_expiry.clear()
    
    # Track function calls
    call_count = 0
    
    @async_timed_cache(ttl_seconds=1)
    async def cached_func(arg1, arg2=None):
        nonlocal call_count
        call_count += 1
        # Return a constant value that doesn't depend on call_count
        return f"{arg1}-{arg2}"
    
    # Test basic caching
    result1 = await cached_func("test", arg2="value")
    result2 = await cached_func("test", arg2="value")
    assert result1 == result2
    assert call_count == 1  # Function should only be called once
    
    # Test different args bypass cache
    result3 = await cached_func("test", arg2="different")
    assert result3 == "test-different"  # Predictable result
    assert call_count == 2  # Function should be called again
    
    # Test TTL expiration
    await asyncio.sleep(1.1)  # Wait for TTL to expire
    result4 = await cached_func("test", arg2="value")
    assert result4 == "test-value"  # Same return value but should be recomputed
    assert call_count == 3  # Function should be called again after TTL expires
    
    # Test cache clearing
    cached_func.cache_clear()
    result5 = await cached_func("test", arg2="value")
    assert result5 == "test-value"  # Same result after cache cleared
    assert call_count == 4  # Function should be called again after cache clear


@pytest.mark.asyncio
async def test_rate_limiting(test_config):
    """Test that rate limiting is enforced between API requests."""
    # Set a longer min_interval to make timing measurements more reliable
    test_config.min_interval = 0.5
    
    async with ClinicalTrialsCrawler(test_config) as crawler:
        # Make first request
        start_time = time.time()
        item1 = await crawler.get_item("NCT00001372")
        
        # Make second request immediately after
        item2 = await crawler.get_item("NCT00001379")
        elapsed = time.time() - start_time
        
        # Since we made two requests and min_interval is 0.5s,
        # the total time should be >= 0.5s
        assert elapsed >= test_config.min_interval, \
            f"Rate limiting not enforced. Elapsed time {elapsed:.3f}s < {test_config.min_interval}s minimum interval"
        
        # Verify both requests succeeded
        assert item1 is not None
        assert item2 is not None


@pytest.mark.asyncio
async def test_session_management():
    """Test proper session creation and cleanup."""
    crawler = ClinicalTrialsCrawler()
    
    # Session should not exist before context
    assert crawler.session is None
    
    async with crawler:
        # Session should exist within context
        assert crawler.session is not None
        
    # Session should be cleaned up after context
    assert crawler.session is None


@pytest.mark.asyncio
async def test_batch_processing(test_config):
    """Test batch processing functionality with real API calls."""
    async with ClinicalTrialsCrawler(test_config) as crawler:
        items = ["NCT00001372", "NCT00001379", "NCT00001622"]
        test_config.default_batch_size = 2
        
        results = await crawler.get_items_batch(items)
        assert len(results) == len(items)
        
        # Verify each result has expected metadata
        for result in results:
            assert isinstance(result, dict)
            assert "nct_id" in result
            assert "title" in result
            assert "status" in result


@pytest.mark.asyncio
async def test_error_handling(test_config):
    """Test error handling with real API calls."""
    async with ClinicalTrialsCrawler(test_config) as crawler:
        # Test invalid ID
        with pytest.raises(APIError):
            await crawler.get_item("INVALID_ID")
            
        # Test rate limit handling
        test_config.min_interval = 0  # Force potential rate limiting
        with pytest.raises((APIError, RateLimitError)):
            tasks = [crawler.get_item(f"NCT0000{i}") for i in range(50)]
            await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_exponential_backoff():
    """Test that exponential backoff works correctly with retries."""
    test_config = CrawlerConfig(
        retry_wait=1,
        retry_max_wait=8,
        retry_exponential_base=2,
        max_retries=3
    )
    
    # Mock API that fails with error
    class TestCrawler(BaseCrawler):
        def __init__(self):
            super().__init__("http://test.com", test_config)
            self.attempt = 0
            self.retry_times = []
            self.last_try = 0
        
        @api_retry(test_config)
        async def test_request(self):
            now = time.time()
            if self.last_try > 0:
                self.retry_times.append(now - self.last_try)
            self.last_try = now
            self.attempt += 1
            raise APIError("Test error")
            
        async def search(self, *args, **kwargs): pass
        async def get_metadata_request_params(self, *args): pass
        async def get_metadata_endpoint(self): pass
        def extract_metadata(self, *args): pass
    
    async with TestCrawler() as crawler:
        try:
            await crawler.test_request()
        except APIError:
            # Should have attempted max_retries times total
            assert crawler.attempt == test_config.max_retries
            
            # Wait times should follow the wait chain pattern defined in api_retry
            # First wait is from wait_fixed, subsequent waits are from wait_exponential
            expected_waits = [test_config.retry_wait]
            expected_waits.append(
                min(
                    test_config.retry_wait * (test_config.retry_exponential_base ** 1),
                    test_config.retry_max_wait
                )
            )
            
            # Check that we have the expected number of retry waits
            assert len(crawler.retry_times) == len(expected_waits)
            
            # Allow 10% variance in timing due to scheduling
            for actual, expected in zip(crawler.retry_times, expected_waits):
                assert abs(actual - expected) <= expected * 0.1, \
                    f"Expected wait time {expected}s, got {actual}s"
        else:
            pytest.fail("Expected APIError after retries exhausted")