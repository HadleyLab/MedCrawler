"""
Integration tests for the ClinicalTrials.gov crawler.

This module contains tests that make real API calls to ClinicalTrials.gov's
API v2 to verify the correct functionality of the ClinicalTrialsCrawler.
"""
import pytest
import asyncio
from datetime import datetime, timedelta

from crawlers.clinical_trials import ClinicalTrialsCrawler
from crawlers.exceptions import APIError

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


async def test_search_basic(test_config):
    """Test basic search functionality.
    
    Verifies that the search method returns valid NCT IDs
    and the expected number of results.
    
    Args:
        test_config: Test configuration fixture
    """
    async with ClinicalTrialsCrawler(test_config) as crawler:
        results = []
        async for nct_id in crawler.search("metastatic breast cancer", max_results=5):
            assert nct_id.startswith("NCT")
            results.append(nct_id)
        
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
    ninety_days_ago = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    
    async with ClinicalTrialsCrawler(test_config) as crawler:
        results = []
        async for nct_id in crawler.search(
            "covid vaccine",
            max_results=3,
            from_date=ninety_days_ago,
            to_date=today_str
        ):
            assert nct_id.startswith("NCT")
            results.append(nct_id)
        
        assert len(results) > 0


async def test_get_metadata(test_config):
    """Test retrieving metadata for known studies.
    
    Verifies that study metadata can be retrieved and contains
    all expected fields with correct content.
    
    Args:
        test_config: Test configuration fixture
    """
    async with ClinicalTrialsCrawler(test_config) as crawler:
        # Test with multiple stable, completed studies
        test_studies = [
            # NSABP breast cancer prevention trial
            ("NCT00004205", "Breast Cancer"),
            # Major statin trial
            ("NCT00000488", "Cardiovascular"),
            # AIDS Clinical Trial
            ("NCT00000760", "HIV")
        ]
        
        for nct_id, condition_type in test_studies:
            metadata = await crawler.get_item(nct_id)
            
            assert metadata["nct_id"] == nct_id
            assert "title" in metadata
            assert "status" in metadata
            assert "phase" in metadata
            assert "conditions" in metadata
            assert any(condition_type.lower() in condition.lower() 
                      for condition in metadata["conditions"])
            assert "description" in metadata
            assert "summary" in metadata
            assert "eligibility_criteria" in metadata
            assert metadata["status"] is not None


async def test_get_items_batch(test_config):
    """Test batch retrieval of multiple studies.
    
    Verifies that multiple studies can be retrieved in a single batch
    with all metadata fields present for each study.
    
    Args:
        test_config: Test configuration fixture
    """
    # Use stable, completed studies
    known_ids = ["NCT00004205", "NCT00000488", "NCT00000760"]
    
    async with ClinicalTrialsCrawler(test_config) as crawler:
        results = await crawler.get_items_batch(known_ids)
        
        assert len(results) == 3
        assert all(item["nct_id"] in known_ids for item in results)
        assert all("title" in item for item in results)
        assert all("status" in item for item in results)
        assert all("phase" in item for item in results)


async def test_search_with_exclusions(test_config):
    """Test search with excluded IDs.
    
    Verifies that search results exclude previously known IDs.
    
    Args:
        test_config: Test configuration fixture
    """
    async with ClinicalTrialsCrawler(test_config) as crawler:
        # First get some IDs to exclude
        exclude_ids = set()
        async for nct_id in crawler.search("lung cancer", max_results=2):
            exclude_ids.add(nct_id)
        
        # Now search with exclusions
        results = []
        async for nct_id in crawler.search("lung cancer", max_results=5, old_item_ids=exclude_ids):
            assert nct_id not in exclude_ids
            results.append(nct_id)
        
        assert len(results) == 5
        assert not set(results) & exclude_ids  # No intersection


async def test_invalid_id(test_config):
    """Test error handling for invalid study ID.
    
    Verifies that attempting to retrieve metadata for an invalid ID
    raises the appropriate exception.
    
    Args:
        test_config: Test configuration fixture
    """
    async with ClinicalTrialsCrawler(test_config) as crawler:
        with pytest.raises(APIError):
            await crawler.get_item("INVALID_ID")


async def test_retry_mechanism(test_config):
    """Test the retry mechanism with real API calls.
    
    Verifies that the retry mechanism works correctly when making
    multiple API calls in succession.
    
    Args:
        test_config: Test configuration fixture
    """
    test_config.min_interval = 0.5  # Short interval
    test_config.max_retries = 2
    
    async with ClinicalTrialsCrawler(test_config) as crawler:
        results = []
        async for nct_id in crawler.search("cancer", max_results=5):
            results.append(nct_id)
        
        assert len(results) == 5
        assert all(nct_id.startswith("NCT") for nct_id in results)


async def test_date_formats(test_config):
    """Test various date format handling with real searches.
    
    Verifies that different date formats and special values (MIN/MAX)
    are correctly handled in search queries.
    
    Args:
        test_config: Test configuration fixture
    """
    async with ClinicalTrialsCrawler(test_config) as crawler:
        # Test with MIN/MAX
        results_min_max = []
        async for nct_id in crawler.search(
            "rare disease",
            max_results=2,
            from_date="MIN",
            to_date="MAX"
        ):
            results_min_max.append(nct_id)
        
        assert len(results_min_max) == 2
        
        # Test with specific dates
        results_dates = []
        async for nct_id in crawler.search(
            "cancer",
            max_results=2,
            from_date="2020-01-01",
            to_date="2023-12-31"
        ):
            results_dates.append(nct_id)
        
        assert len(results_dates) == 2
        assert set(results_min_max) != set(results_dates)  # Should be different studies


async def test_metadata_fields(test_config):
    """Test all expected metadata fields are present.
    
    Verifies that study metadata contains all required fields
    with appropriate content.
    
    Args:
        test_config: Test configuration fixture
    """
    async with ClinicalTrialsCrawler(test_config) as crawler:
        # Use a stable, well-documented study
        metadata = await crawler.get_item("NCT00004205")  # NSABP breast cancer prevention trial
        
        required_fields = {
            "nct_id",
            "title",
            "status",
            "phase",
            "conditions",
            "description",
            "summary",
            "eligibility_criteria",
            "start_date",
            "completion_date",
            "last_updated"
        }
        
        assert all(field in metadata for field in required_fields)
        assert len(metadata["conditions"]) > 0
        assert metadata["phase"]  # Should have a phase
        assert "breast" in " ".join(metadata["conditions"]).lower()  # Should be about breast cancer