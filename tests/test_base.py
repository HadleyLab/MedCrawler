"""
Tests for the BaseCrawler and related components.

This module contains tests for the core functionality of the base crawler,
including the caching mechanism, rate limiting, session management,
batch processing, and error handling.
"""
import asyncio
import pytest

from medcrawler.base import TimedCache
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
    """Test rate limiting behavior using real API calls.
    
    Verifies that the crawler respects the configured minimum interval
    between API requests.
    
    Args:
        test_config: Test configuration fixture
    """
    test_config.min_interval = 0.5  # Set a small but measurable delay
    
    async with ClinicalTrialsCrawler(test_config) as crawler:
        start_time = asyncio.get_event_loop().time()
        
        # Make multiple requests to test rate limiting
        await crawler.get_item("NCT00001372")
        await crawler.get_item("NCT00001379")
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # Should take at least min_interval seconds between requests
        assert elapsed >= test_config.min_interval


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