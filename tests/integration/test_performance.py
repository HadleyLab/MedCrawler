"""
Performance tests for MedCrawler.

This module contains tests that measure and verify the performance
improvements from caching in both PubMed and ClinicalTrials.gov crawlers.
"""
import pytest
import asyncio
import time
import logging
import functools
from typing import List, Dict, Any, Tuple, Callable, Awaitable
from statistics import mean, stdev

from medcrawler.pubmed import PubMedCrawler
from medcrawler.clinical_trials import ClinicalTrialsCrawler
from medcrawler.base import _cache_expiry, async_timed_cache

# Configure logger
logger = logging.getLogger(__name__)

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before and after each test."""
    _cache_expiry.clear()
    yield
    _cache_expiry.clear()

async def measure_execution_time(func: Callable[[], Awaitable[Any]], runs: int = 1) -> Tuple[Any, float]:
    """Measure the execution time of an async function with multiple runs."""
    times = []
    result = None
    
    for _ in range(runs):
        start_time = time.time()
        result = await func()
        end_time = time.time()
        times.append(end_time - start_time)
        
    avg_time = mean(times)
    if runs > 1:
        std_dev = stdev(times)
        logger.debug(f"Execution times: mean={avg_time:.3f}s, std_dev={std_dev:.3f}s")
        
    return result, avg_time

# Remove xfail since tests are now working
async def test_pubmed_cache_performance(test_config):
    """Test performance improvement from PubMed caching."""
    article_ids = ["32843755", "32296168", "33753933"]
    
    # Set higher min_interval to avoid rate limiting
    test_config.min_interval = 1.0
    
    async with PubMedCrawler(test_config) as crawler:
        logger.info("Testing PubMed cache performance...")
        
        # First batch - should hit the API (average of 2 runs instead of 3 to reduce API calls)
        uncached_func = lambda: crawler.get_items_batch(article_ids)
        uncached_results, uncached_time = await measure_execution_time(uncached_func, runs=2)
        
        # Add a delay to ensure rate limits are reset
        await asyncio.sleep(2.0)
        
        # Second batch - should use cache (average of 2 runs)
        cached_func = lambda: crawler.get_items_batch(article_ids)
        cached_results, cached_time = await measure_execution_time(cached_func, runs=2)
        
        # Verify results match
        assert uncached_results == cached_results, "Cached results don't match original results"
        assert len(uncached_results) == len(article_ids), "Missing results"
        
        # Log performance metrics
        time_savings = (uncached_time - cached_time) / uncached_time * 100
        logger.info(f"PubMed Cache Performance Results:")
        logger.info(f"Uncached time: {uncached_time:.3f}s (average of 2 runs)")
        logger.info(f"Cached time: {cached_time:.3f}s (average of 2 runs)")
        logger.info(f"Time savings: {time_savings:.1f}%")
        
        # Increased threshold to expect significant performance gains
        assert time_savings > 80, \
            f"PubMed cache should show at least 80% time savings (actual: {time_savings:.1f}%)"

# Remove xfail since tests are now working
async def test_clinical_trials_cache_performance(test_config):
    """Test performance improvement from ClinicalTrials.gov caching."""
    # Use fewer studies to reduce test runtime
    study_ids = [
        "NCT00004205", "NCT00000488", "NCT00000760",
        "NCT00001372", "NCT00001379", "NCT00001622"
    ]
    
    # Add min_interval to ensure consistent timing
    test_config.min_interval = 0.3
    
    async with ClinicalTrialsCrawler(test_config) as crawler:
        logger.info("Testing ClinicalTrials.gov cache performance...")
        
        # Create a wrapper function with our caching decorator
        @async_timed_cache(ttl_seconds=60)
        async def get_batch(ids):
            return await crawler.get_items_batch(ids)
            
        # First batch - should hit the API (average of 2 runs)
        uncached_func = lambda: get_batch(study_ids)
        uncached_results, uncached_time = await measure_execution_time(uncached_func, runs=2)
        
        # Short delay to ensure timing differences are measurable
        await asyncio.sleep(1.0)
        
        # Second batch - should use cache (average of 2 runs)
        cached_func = lambda: get_batch(study_ids)
        cached_results, cached_time = await measure_execution_time(cached_func, runs=2)
        
        # Verify results match
        assert uncached_results == cached_results, "Cached results don't match original results"
        assert len(uncached_results) == len(study_ids), "Missing results"
        
        # Log performance metrics
        time_savings = (uncached_time - cached_time) / uncached_time * 100
        logger.info(f"ClinicalTrials.gov Cache Performance Results:")
        logger.info(f"Uncached time: {uncached_time:.3f}s (average of 2 runs)")
        logger.info(f"Cached time: {cached_time:.3f}s (average of 2 runs)")
        logger.info(f"Time savings: {time_savings:.1f}%")
        
        # Increased threshold to expect significant performance gains
        assert time_savings > 80, \
            f"ClinicalTrials.gov cache should show at least 80% time savings (actual: {time_savings:.1f}%)"

# Remove xfail since tests are now working
async def test_search_cache_performance(test_config):
    """Test performance improvement from search result caching."""
    # Increase min_interval to avoid rate limiting
    test_config.min_interval = 1.0
    
    async with PubMedCrawler(test_config) as pubmed:
        logger.info("Testing search cache performance...")
        
        # Test PubMed search caching - just one query to reduce API calls
        query = "covid vaccine"
        logger.info(f"\nTesting PubMed search: '{query}'")
        
        # Function to collect search results
        async def collect_pubmed_results(query_term, max_results):
            results = []
            async for item_id in pubmed.search(query_term, max_results=max_results):
                results.append(item_id)
            return results
        
        # Apply caching decorator
        cached_search = async_timed_cache(ttl_seconds=60)(collect_pubmed_results)
        
        # First search - should hit the API
        uncached_results, uncached_time = await measure_execution_time(
            lambda: cached_search(query, 5)
        )
        
        # Add delay before next call to avoid rate limiting
        await asyncio.sleep(1.0)
        
        # Second search - should use cache
        cached_results, cached_time = await measure_execution_time(
            lambda: cached_search(query, 5)
        )
        
        # Verify results match
        assert uncached_results == cached_results, \
            f"Cached search results don't match for query: {query}"
        
        # Calculate and verify time savings
        time_savings = (uncached_time - cached_time) / uncached_time * 100
        logger.info(f"PubMed search cache performance for '{query}':")
        logger.info(f"Uncached time: {uncached_time:.3f}s")
        logger.info(f"Cached time: {cached_time:.3f}s")
        logger.info(f"Time savings: {time_savings:.1f}%")
        
        # Increased threshold to expect significant performance gains
        assert time_savings > 80, \
            f"Search cache should show at least 80% time savings (actual: {time_savings:.1f}%)"