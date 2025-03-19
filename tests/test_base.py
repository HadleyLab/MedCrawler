"""
Tests for the BaseCrawler and related components.

This module contains tests for the core functionality of the base crawler,
including the caching mechanism, rate limiting, session management,
batch processing, and error handling.
"""
import asyncio
import time
import pytest
from tenacity import RetryError

from medcrawler.base import TimedCache, BaseCrawler, api_retry
from medcrawler.config import CrawlerConfig
from medcrawler.clinical_trials import ClinicalTrialsCrawler
from medcrawler.exceptions import APIError, RateLimitError


@pytest.mark.asyncio
async def test_timed_cache():
    """Test the TimedCache implementation.
    
    Tests basic cache operations:
    - Setting and getting values
    - Cache eviction when maxsize is reached
    - TTL-based expiration
    - Cache clearing
    """
    cache = TimedCache(ttl_seconds=1, maxsize=2)
    
    # Test basic set/get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    # Test maxsize eviction
    cache.set("key2", "value2")
    cache.set("key3", "value3")  # This should evict key1
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"
    
    # Test TTL expiration
    cache.set("key4", "value4")
    await asyncio.sleep(1.1)  # Wait for TTL to expire
    assert cache.get("key4") is None
    
    # Test clear
    cache.set("key5", "value5")
    cache.clear()
    assert cache.get("key5") is None


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
    """Test proper session creation and cleanup.
    
    Verifies that the aiohttp session is correctly created when entering
    the async context and properly closed when exiting.
    """
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
    """Test batch processing functionality with real API calls.
    
    Verifies that multiple items can be processed in batches and that
    all expected metadata is returned.
    
    Args:
        test_config: Test configuration fixture
    """
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
    """Test error handling with real API calls.
    
    Verifies that the crawler properly handles and raises exceptions
    for invalid IDs and rate limiting.
    
    Args:
        test_config: Test configuration fixture
    """
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
    """Test that exponential backoff works correctly with retries.
    
    This test verifies that:
    1. The wait time increases exponentially between retries
    2. The wait time doesn't exceed the configured maximum
    3. The correct number of retries is attempted
    """
    test_config = CrawlerConfig(
        retry_wait=1,
        retry_max_wait=8,
        retry_exponential_base=2,
        max_retries=3
    )
    
    # Mock API that fails with 500 error
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
            
            # Wait times should follow exponential pattern up to max
            expected_waits = [
                test_config.retry_wait * (test_config.retry_exponential_base ** i)
                for i in range(test_config.max_retries - 1)
            ]
            expected_waits = [min(w, test_config.retry_max_wait) for w in expected_waits]
            
            # Check that we have the expected number of retry waits
            assert len(crawler.retry_times) == len(expected_waits)
            
            # Allow 10% variance in timing due to scheduling
            for actual, expected in zip(crawler.retry_times, expected_waits):
                assert abs(actual - expected) <= expected * 0.1, \
                    f"Expected wait time {expected}s, got {actual}s"
        else:
            pytest.fail("Expected APIError after retries exhausted")