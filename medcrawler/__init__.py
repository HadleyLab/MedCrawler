"""
Medical literature crawlers package.

This package provides asynchronous crawlers for medical literature databases:
- ClinicalTrials.gov: Access clinical trial data through their API v2
- PubMed: Search and retrieve medical research articles via NCBI E-utilities

Features:
- Asynchronous HTTP requests
- Built-in rate limiting and retry mechanisms
- Response caching with TTL
- Batch processing capabilities
- Comprehensive error handling
- Date-based filtering

Example:
    >>> from crawlers import ClinicalTrialsCrawler
    >>> async with ClinicalTrialsCrawler() as crawler:
    ...     async for nct_id in crawler.search("cancer", max_results=5):
    ...         metadata = await crawler.get_item(nct_id)
    ...         print(metadata["title"])
"""

from .__version__ import (
    __version__,
    __title__,
    __description__,
    __author__,
    __author_email__,
    __license__,
    __url__,
)
from .config import CrawlerConfig, DEFAULT_CRAWLER_CONFIG
from .exceptions import CrawlerError, APIError, RateLimitError, ConfigurationError
from .clinical_trials import ClinicalTrialsCrawler
from .pubmed import PubMedCrawler
from .demo import demo_crawler, main

__all__ = [
    'CrawlerConfig',
    'DEFAULT_CRAWLER_CONFIG',
    'CrawlerError',
    'APIError',
    'RateLimitError',
    'ConfigurationError',
    'ClinicalTrialsCrawler',
    'PubMedCrawler',
    'demo_crawler',
    'main'
]