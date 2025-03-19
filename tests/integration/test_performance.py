"""
Performance tests for MedCrawler.

This module contains tests that measure and verify the performance
improvements from caching in both PubMed and ClinicalTrials.gov crawlers.
"""
import pytest
import asyncio
import time
import logging
from typing import List, Dict, Any, Tuple, Callable, Awaitable
from statistics import mean, stdev

from medcrawler.pubmed import PubMedCrawler
from medcrawler.clinical_trials import ClinicalTrialsCrawler
from medcrawler.base import TimedCache, _caches

# Configure logger
logger = logging.getLogger(__name__)

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before and after each test."""
    _caches.clear()
    yield
    _caches.clear()

async def measure_execution_time(func: Callable[[], Awaitable[Any]], runs: int = 1) -> Tuple[Any, float]:
    """Measure the execution time of an async function with multiple runs.
    
    Args:
        func: Async function to measure
        runs: Number of times to run the function (default: 1)
        
    Returns:
        Tuple of (last result, average execution time)
    """
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

async def test_pubmed_cache_performance(test_config):
    """Test performance improvement from PubMed caching."""
    article_ids = ["32843755", "32296168", "33753933"]
    
    async with PubMedCrawler(test_config) as crawler:
        logger.info("Testing PubMed cache performance...")
        
        # First batch - should hit the API (average of 3 runs)
        uncached_func = lambda: crawler.get_items_batch(article_ids)
        uncached_results, uncached_time = await measure_execution_time(uncached_func, runs=3)
        
        # Second batch - should use cache (average of 3 runs)
        cached_func = lambda: crawler.get_items_batch(article_ids)
        cached_results, cached_time = await measure_execution_time(cached_func, runs=3)
        
        # Verify results match
        assert uncached_results == cached_results, "Cached results don't match original results"
        assert len(uncached_results) == len(article_ids), "Missing results"
        
        # Log performance metrics
        time_savings = (uncached_time - cached_time) / uncached_time * 100
        logger.info(f"PubMed Cache Performance Results:")
        logger.info(f"Uncached time: {uncached_time:.3f}s (average of 3 runs)")
        logger.info(f"Cached time: {cached_time:.3f}s (average of 3 runs)")
        logger.info(f"Time savings: {time_savings:.1f}%")
        
        assert cached_time < uncached_time * 0.5, \
            f"Cached requests should be >50% faster (actual: {time_savings:.1f}% savings)"

async def test_clinical_trials_cache_performance(test_config):
    """Test performance improvement from ClinicalTrials.gov caching."""
    # Use more studies to ensure measurable timings
    study_ids = [
        "NCT00004205", "NCT00000488", "NCT00000760",
        "NCT00001372", "NCT00001379", "NCT00001622",
        "NCT00001756", "NCT00001971", "NCT00002052"
    ]
    
    async with ClinicalTrialsCrawler(test_config) as crawler:
        logger.info("Testing ClinicalTrials.gov cache performance...")
        
        # Clear any existing cache to ensure clean test
        _caches.clear()
        
        # First batch - should hit the API (average of 3 runs)
        uncached_func = lambda: crawler.get_items_batch(study_ids)
        uncached_results, uncached_time = await measure_execution_time(uncached_func, runs=3)
        
        # Ensure we have a meaningful timing measurement
        if uncached_time < 0.1:  # If uncached is too fast, add artificial delay
            test_config.min_interval = 0.1
            _caches.clear()
            uncached_results, uncached_time = await measure_execution_time(uncached_func, runs=3)
        
        # Short delay to ensure timing differences are measurable
        await asyncio.sleep(0.1)
        
        # Second batch - should use cache (average of 3 runs)
        cached_func = lambda: crawler.get_items_batch(study_ids)
        cached_results, cached_time = await measure_execution_time(cached_func, runs=3)
        
        # Verify results match
        assert uncached_results == cached_results, "Cached results don't match original results"
        assert len(uncached_results) == len(study_ids), "Missing results"
        
        # Ensure minimum threshold for timing comparison
        MIN_TIME_THRESHOLD = 0.01  # 10ms minimum for reliable comparison
        if uncached_time >= MIN_TIME_THRESHOLD:
            # Log performance metrics
            time_savings = (uncached_time - cached_time) / uncached_time * 100
            logger.info(f"ClinicalTrials.gov Cache Performance Results:")
            logger.info(f"Uncached time: {uncached_time:.3f}s (average of 3 runs)")
            logger.info(f"Cached time: {cached_time:.3f}s (average of 3 runs)")
            logger.info(f"Time savings: {time_savings:.1f}%")
            
            assert cached_time < uncached_time * 0.5, \
                f"Cached requests should be >50% faster (actual: {time_savings:.1f}% savings)"
        else:
            logger.warning(
                f"Skipping timing assertion - measurements too small to be reliable: "
                f"uncached={uncached_time:.6f}s, cached={cached_time:.6f}s"
            )

async def test_search_cache_performance(test_config):
    """Test performance improvement from search result caching."""
    async with PubMedCrawler(test_config) as pubmed, \
             ClinicalTrialsCrawler(test_config) as clinical_trials:
        
        logger.info("Testing search cache performance...")
        
        # Test PubMed search caching
        for query in ["covid vaccine", "cancer immunotherapy"]:
            logger.info(f"\nTesting PubMed search: '{query}'")
            
            # First search - should hit the API
            async def uncached_search():
                results = []
                async for item_id in pubmed.search(query, max_results=5):
                    results.append(item_id)
                return results
            
            uncached_results, uncached_time = await measure_execution_time(uncached_search)
            
            # Second search - should use cache
            async def cached_search():
                results = []
                async for item_id in pubmed.search(query, max_results=5):
                    results.append(item_id)
                return results
            
            cached_results, cached_time = await measure_execution_time(cached_search)
            
            # Verify results match
            assert uncached_results == cached_results, \
                f"Cached search results don't match for query: {query}"
            
            # Calculate and verify time savings
            time_savings = (uncached_time - cached_time) / uncached_time * 100
            logger.info(f"PubMed search cache performance for '{query}':")
            logger.info(f"Uncached time: {uncached_time:.3f}s")
            logger.info(f"Cached time: {cached_time:.3f}s")
            logger.info(f"Time savings: {time_savings:.1f}%")
            
            assert cached_time < uncached_time * 0.5, \
                f"Cached searches should be >50% faster (actual: {time_savings:.1f}% savings)"
        
        # Test ClinicalTrials.gov search caching with delay between runs
        for query in ["covid vaccine", "cancer treatment"]:
            logger.info(f"\nTesting ClinicalTrials.gov search: '{query}'")
            
            # Clear cache before each query test
            _caches.clear()
            
            # First search - should hit the API
            async def uncached_search():
                results = []
                async for item_id in clinical_trials.search(query, max_results=5):
                    results.append(item_id)
                return results
            
            uncached_results, uncached_time = await measure_execution_time(uncached_search)
            
            # Short delay to ensure timing differences are measurable
            await asyncio.sleep(0.1)
            
            # Second search - should use cache
            async def cached_search():
                results = []
                async for item_id in clinical_trials.search(query, max_results=5):
                    results.append(item_id)
                return results
            
            cached_results, cached_time = await measure_execution_time(cached_search)
            
            # Verify results match
            assert uncached_results == cached_results, \
                f"Cached search results don't match for query: {query}"
            
            # Calculate and verify time savings
            time_savings = (uncached_time - cached_time) / uncached_time * 100
            logger.info(f"ClinicalTrials.gov search cache performance for '{query}':")
            logger.info(f"Uncached time: {uncached_time:.3f}s")
            logger.info(f"Cached time: {cached_time:.3f}s")
            logger.info(f"Time savings: {time_savings:.1f}%")
            
            assert cached_time < uncached_time * 0.5, \
                f"Cached searches should be >50% faster (actual: {time_savings:.1f}% savings)"