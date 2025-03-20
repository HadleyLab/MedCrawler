"""
Tests to determine optimal rate limiting settings.

This module contains tests that deliberately try to hit API rate limits
to help determine appropriate rate limiting parameters.
"""
import pytest
import asyncio
import time
import logging
from typing import List
from datetime import datetime, timedelta

from medcrawler.pubmed import PubMedCrawler
from medcrawler.clinical_trials import ClinicalTrialsCrawler
from medcrawler.config import CrawlerConfig
from medcrawler.exceptions import RateLimitError, APIError

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio

async def test_pubmed_rate_limits():
    """Test PubMed's rate limits by making rapid requests."""
    config = CrawlerConfig(
        user_agent="MedCrawler/1.0 (Rate Limit Test)",
        min_interval=0.1  # Very short interval to trigger rate limits
    )
    
    async with PubMedCrawler(config) as crawler:
        # Test rapid sequential requests
        start_time = time.time()
        requests_made = 0
        try:
            while time.time() - start_time < 5:  # Run for 5 seconds
                await crawler.get_item("12345678")
                requests_made += 1
        except RateLimitError as e:
            elapsed = time.time() - start_time
            rate = requests_made / elapsed
            logger.error(f"Hit rate limit after {requests_made} requests in {elapsed:.2f}s")
            logger.error(f"Effective rate: {rate:.2f} requests/second")
            logger.error(f"Rate limit error: {str(e)}")
            return
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

async def test_clinicaltrials_rate_limits():
    """Test ClinicalTrials.gov's rate limits by making rapid requests."""
    config = CrawlerConfig(
        user_agent="MedCrawler/1.0 (Rate Limit Test)",
        min_interval=0.1  # Very short interval to trigger rate limits
    )
    
    async with ClinicalTrialsCrawler(config) as crawler:
        # Test rapid sequential requests
        start_time = time.time()
        requests_made = 0
        try:
            while time.time() - start_time < 5:  # Run for 5 seconds
                await crawler.get_item("NCT00001372")
                requests_made += 1
        except RateLimitError as e:
            elapsed = time.time() - start_time
            rate = requests_made / elapsed
            logger.error(f"Hit rate limit after {requests_made} requests in {elapsed:.2f}s")
            logger.error(f"Effective rate: {rate:.2f} requests/second")
            logger.error(f"Rate limit error: {str(e)}")
            return
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

async def test_pubmed_batch_limits():
    """Test PubMed's behavior with different batch sizes."""
    config = CrawlerConfig(
        user_agent="MedCrawler/1.0 (Rate Limit Test)",
        min_interval=0.1
    )
    
    async with PubMedCrawler(config) as crawler:
        # Test different batch sizes
        test_sizes = [2, 3, 5, 10]
        for batch_size in test_sizes:
            start_time = time.time()
            try:
                # Generate test PMIDs
                pmids = [str(12345678 + i) for i in range(batch_size)]
                await crawler.get_items_batch(pmids)
                elapsed = time.time() - start_time
                logger.info(f"Batch size {batch_size} succeeded in {elapsed:.2f}s")
            except (RateLimitError, APIError) as e:
                logger.error(f"Batch size {batch_size} failed: {str(e)}")

async def test_clinicaltrials_batch_limits():
    """Test ClinicalTrials.gov's behavior with different batch sizes."""
    config = CrawlerConfig(
        user_agent="MedCrawler/1.0 (Rate Limit Test)",
        min_interval=0.1
    )
    
    async with ClinicalTrialsCrawler(config) as crawler:
        # Test different batch sizes
        test_sizes = [2, 3, 5, 10]
        base_nct = "NCT0000"
        for batch_size in test_sizes:
            start_time = time.time()
            try:
                # Generate test NCT IDs
                nct_ids = [f"{base_nct}{1372 + i}" for i in range(batch_size)]
                await crawler.get_items_batch(nct_ids)
                elapsed = time.time() - start_time
                logger.info(f"Batch size {batch_size} succeeded in {elapsed:.2f}s")
            except (RateLimitError, APIError) as e:
                logger.error(f"Batch size {batch_size} failed: {str(e)}")

async def test_concurrent_request_limits():
    """Test behavior with concurrent requests to both APIs."""
    config = CrawlerConfig(
        user_agent="MedCrawler/1.0 (Rate Limit Test)",
        min_interval=0.1
    )
    
    async with PubMedCrawler(config) as pubmed, ClinicalTrialsCrawler(config) as clinical:
        start_time = time.time()
        try:
            # Make concurrent requests
            tasks = []
            for i in range(5):
                tasks.append(pubmed.get_item(str(12345678 + i)))
                tasks.append(clinical.get_item(f"NCT0000{1372 + i}"))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start_time
            
            errors = [r for r in results if isinstance(r, Exception)]
            successes = len(results) - len(errors)
            
            logger.info(f"Concurrent test completed in {elapsed:.2f}s")
            logger.info(f"Successful requests: {successes}")
            logger.info(f"Failed requests: {len(errors)}")
            
            for error in errors:
                logger.error(f"Error during concurrent test: {str(error)}")
                
        except Exception as e:
            logger.error(f"Unexpected error in concurrent test: {str(e)}")
            raise