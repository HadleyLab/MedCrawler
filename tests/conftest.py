"""
Test configuration fixtures for MedCrawler.

This module provides pytest fixtures for testing the MedCrawler package,
including event loop setup, logging configuration, and test-specific
crawler configurations.
"""
import pytest
import asyncio
import logging

from crawlers.config import CrawlerConfig


@pytest.fixture(autouse=True)
def configure_logging():
    """Configure logging for all tests.
    
    This fixture is applied automatically to all tests to ensure
    consistent logging behavior.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case.
    
    This fixture ensures that each test gets a fresh event loop,
    preventing state leakage between tests.
    
    Yields:
        asyncio.AbstractEventLoop: A new event loop instance
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Create a test configuration with proper settings for real API calls.
    
    This configuration is designed for integration tests that make
    actual API calls, with conservative rate limiting to avoid
    overloading external services.
    
    Returns:
        CrawlerConfig: Configuration for integration tests
    """
    return CrawlerConfig(
        user_agent="MedCrawler/1.0 (Testing; mailto:test@example.com)",
        email="test@example.com",
        min_interval=2.0,  # 2 seconds between requests to be more conservative
        max_retries=3,
        retry_wait=3,      # Wait 3 seconds before retrying
        default_batch_size=3,  # Smaller batch size for testing
        cache_ttl=60  # Short cache for testing
    )


@pytest.fixture
def mock_config():
    """Create a mock configuration for unit tests.
    
    This configuration uses minimal delays and retries for fast unit tests
    that don't make real API calls.
    
    Returns:
        CrawlerConfig: Configuration for mock/unit tests
    """
    return CrawlerConfig(
        user_agent="MedCrawler/1.0 (Mock)",
        email="mock@example.com",
        min_interval=0.01,  # Very short interval for mock tests
        max_retries=1,
        retry_wait=0.1,
        default_batch_size=2,
        cache_ttl=1  # Very short cache for testing expiration
    )