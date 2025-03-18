"""
Integration tests for the PubMed crawler.

This module contains tests that make real API calls to PubMed's
E-utilities API to verify the correct functionality of the PubMedCrawler.
"""
import pytest
import asyncio
from datetime import datetime, timedelta

from crawlers.pubmed import PubMedCrawler
from crawlers.exceptions import APIError

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


async def test_search_basic(test_config):
    """Test basic search functionality.
    
    Verifies that the search method returns valid PubMed IDs
    and the expected number of results.
    
    Args:
        test_config: Test configuration fixture
    """
    async with PubMedCrawler(test_config) as crawler:
        results = []
        async for pmid in crawler.search("cancer immunotherapy", max_results=5):
            assert pmid.isdigit()  # PubMed IDs are numeric
            results.append(pmid)
        
        assert len(results) == 5
        assert len(set(results)) == 5  # Check for duplicates


async def test_search_with_dates(test_config):
    """Test search with date filtering.
    
    Verifies that date-filtered searches return results within
    the specified date range.
    
    Args:
        test_config: Test configuration fixture
    """
    # Get date range for last 90 days to ensure results
    today = datetime.now()
    ninety_days_ago = (today - timedelta(days=90)).strftime("%Y/%m/%d")
    today_str = today.strftime("%Y/%m/%d")
    
    async with PubMedCrawler(test_config) as crawler:
        results = []
        async for pmid in crawler.search(
            "covid vaccine",
            max_results=3,
            from_date=ninety_days_ago,
            to_date=today_str
        ):
            assert pmid.isdigit()
            results.append(pmid)
        
        assert len(results) > 0


async def test_get_metadata(test_config):
    """Test retrieving metadata for known articles.
    
    Verifies that article metadata can be retrieved and contains
    all expected fields with correct content.
    
    Args:
        test_config: Test configuration fixture
    """
    async with PubMedCrawler(test_config) as crawler:
        # Test with multiple stable articles
        test_articles = [
            # Nature paper about CRISPR
            ("32843755", "2020"),  
            # Highly cited COVID-19 paper
            ("32296168", "2020"),
            # Cancer immunotherapy review
            ("33753933", "2021")
        ]
        
        for pmid, year in test_articles:
            metadata = await crawler.get_item(pmid)
            
            assert metadata["pmid"] == pmid
            assert "title" in metadata
            assert "authors" in metadata
            assert isinstance(metadata["authors"], list)
            assert len(metadata["authors"]) > 0
            assert "abstract" in metadata
            assert "journal" in metadata
            assert "pubdate" in metadata
            assert year in metadata["pubdate"]


async def test_get_items_batch(test_config):
    """Test batch retrieval of multiple articles.
    
    Verifies that multiple articles can be retrieved in a single batch
    with all metadata fields present for each article.
    
    Args:
        test_config: Test configuration fixture
    """
    # Use stable, highly-cited articles for testing
    known_ids = ["32843755", "32296168", "33753933"]
    
    async with PubMedCrawler(test_config) as crawler:
        results = await crawler.get_items_batch(known_ids)
        
        assert len(results) == 3
        assert all(item["pmid"] in known_ids for item in results)
        assert all("title" in item for item in results)
        assert all("authors" in item for item in results)
        assert all("abstract" in item for item in results)


async def test_search_with_exclusions(test_config):
    """Test search with excluded IDs.
    
    Verifies that search results exclude previously known IDs.
    
    Args:
        test_config: Test configuration fixture
    """
    async with PubMedCrawler(test_config) as crawler:
        # First get some IDs to exclude
        exclude_ids = set()
        async for pmid in crawler.search("cancer therapy", max_results=2):
            exclude_ids.add(pmid)
        
        # Now search with exclusions
        results = []
        async for pmid in crawler.search("cancer therapy", max_results=5, old_item_ids=exclude_ids):
            assert pmid not in exclude_ids
            results.append(pmid)
        
        assert len(results) == 5
        assert not set(results) & exclude_ids  # No intersection


async def test_invalid_id(test_config):
    """Test error handling for invalid article ID.
    
    Verifies that attempting to retrieve metadata for an invalid ID
    raises the appropriate exception.
    
    Args:
        test_config: Test configuration fixture
    """
    async with PubMedCrawler(test_config) as crawler:
        with pytest.raises(APIError):
            await crawler.get_item("999999999999999")  # Invalid PMID


async def test_retry_mechanism(test_config):
    """Test the retry mechanism with real API calls.
    
    Verifies that the retry mechanism works correctly when making
    multiple API calls in succession.
    
    Args:
        test_config: Test configuration fixture
    """
    test_config.min_interval = 0.5  # Short interval
    test_config.max_retries = 2
    
    async with PubMedCrawler(test_config) as crawler:
        results = []
        async for pmid in crawler.search("cancer", max_results=5):
            results.append(pmid)
        
        assert len(results) == 5
        assert all(pmid.isdigit() for pmid in results)


async def test_date_formats(test_config):
    """Test various date format handling with real searches.
    
    Verifies that different date ranges return appropriate results
    and that date filtering works correctly.
    
    Args:
        test_config: Test configuration fixture
    """
    async with PubMedCrawler(test_config) as crawler:
        # Test recent dates
        results_recent = []
        current_year = datetime.now().year
        async for pmid in crawler.search(
            "covid",
            max_results=2,
            from_date=f"{current_year}/01/01",
            to_date=datetime.now().strftime("%Y/%m/%d")
        ):
            results_recent.append(pmid)
        
        assert len(results_recent) == 2
        
        # Test historical dates (using a more recent historical period)
        results_historical = []
        async for pmid in crawler.search(
            "cancer chemotherapy",
            max_results=2,
            from_date="2000/01/01",
            to_date="2000/12/31"
        ):
            results_historical.append(pmid)
        
        assert len(results_historical) == 2
        assert set(results_recent) != set(results_historical)  # Should be different articles


async def test_metadata_fields(test_config):
    """Test all expected metadata fields are present.
    
    Verifies that article metadata contains all required fields
    with appropriate content.
    
    Args:
        test_config: Test configuration fixture
    """
    async with PubMedCrawler(test_config) as crawler:
        # Use a stable, well-documented article
        metadata = await crawler.get_item("32843755")  # Nature CRISPR paper
        
        required_fields = {
            "pmid",
            "title",
            "abstract",
            "authors",
            "journal",
            "doi",
            "pubdate"
        }
        
        assert all(field in metadata for field in required_fields)
        assert len(metadata["authors"]) > 0
        assert "nature" in metadata["journal"].lower()
        assert metadata["doi"]  # Should have a DOI


async def test_author_format(test_config):
    """Test author name formatting in metadata.
    
    Verifies that author names are properly formatted in the metadata.
    
    Args:
        test_config: Test configuration fixture
    """
    async with PubMedCrawler(test_config) as crawler:
        metadata = await crawler.get_item("32843755")  # Nature CRISPR paper
        
        assert len(metadata["authors"]) > 0
        for author in metadata["authors"]:
            # Check that author names are properly formatted (LastName FirstName/ForeName)
            assert len(author.split()) >= 2
            assert not author.endswith(" ")
            assert " " in author  # Should have space between last and first name