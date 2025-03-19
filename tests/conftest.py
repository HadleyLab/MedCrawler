"""
Test configuration fixtures for MedCrawler.

This module provides pytest fixtures for testing the MedCrawler package,
including event loop setup, logging configuration, and test-specific
crawler configurations.
"""
import pytest
import asyncio

from medcrawler.config import CrawlerConfig
from medcrawler.logging_config import configure_logging

@pytest.fixture(autouse=True)
def configure_test_logging():
    """Configure logging for all tests."""
    configure_logging()

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
        user_agent="MedCrawler/1.0 (Test Suite)",
        min_interval=0.5,  # Increased to better simulate real API latency
        max_retries=2,
        retry_wait=1,
        default_batch_size=3,
        cache_ttl=3600  # Ensure cache doesn't expire during test
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