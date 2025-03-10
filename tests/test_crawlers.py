"""Test suite for crawler functionality."""
import os
import asyncio
import pytest
from config import CrawlerConfig
from backend.crawlers import PubMedCrawler, ClinicalTrialsCrawler

def get_test_config() -> CrawlerConfig:
    """Create a test configuration with safe defaults."""
    return CrawlerConfig(
        user_agent="MedLitAssistant/Tests",
        email=os.environ.get("PUBMED_EMAIL"),  # Email is optional but recommended
        api_key=None,  # API key is optional
        min_interval=0.5  # Add small delay between requests
    )

@pytest.mark.asyncio
async def test_pubmed_json_search(notification_manager) -> None:
    """Test PubMed search and metadata retrieval functionality."""
    config = get_test_config()
    
    async with PubMedCrawler(notification_manager, config=config) as pubmed:
        # Test search functionality
        pmids = []
        async for pmid in pubmed.search("cancer immunotherapy", max_results=2):
            pmids.append(pmid)
            
        assert len(pmids) > 0, "Should find at least one article"
        
        # Test article retrieval
        article = await pubmed.get_item(pmids[0])
        assert article, "Should retrieve article details"
        assert "title" in article, "Article should have a title"
        assert "abstract" in article, "Article should have an abstract"
        assert "authors" in article, "Article should have authors"
        assert isinstance(article["authors"], list), "Authors should be a list"
        assert "journal" in article, "Article should have a journal"
        assert "pubdate" in article, "Article should have a publication date"

@pytest.mark.asyncio
async def test_clinical_trials_search(notification_manager) -> None:
    """Test ClinicalTrials.gov search and metadata retrieval functionality."""
    config = get_test_config()
    
    async with ClinicalTrialsCrawler(notification_manager, config=config) as trials:
        # Test search functionality
        nctids = []
        async for nctid in trials.search("cancer immunotherapy", max_results=2):
            nctids.append(nctid)
            
        assert len(nctids) > 0, "Should find at least one trial"
        
        # Test trial retrieval
        trial = await trials.get_item(nctids[0])
        assert trial, "Should retrieve trial details"
        assert "title" in trial, "Trial should have a title"
        assert "nct_id" in trial, "Trial should have an NCT ID"
        assert "status" in trial, "Trial should have a status"
        assert "conditions" in trial, "Trial should have conditions"
        assert isinstance(trial["conditions"], list), "Conditions should be a list"

@pytest.mark.asyncio
async def test_batch_processing(notification_manager) -> None:
    """Test batch processing functionality for both crawlers."""
    config = get_test_config()
    
    # Test PubMed batch processing
    async with PubMedCrawler(notification_manager, config=config) as pubmed:
        pmids = []
        async for pmid in pubmed.search("cancer", max_results=3):
            pmids.append(pmid)
            
        articles = await pubmed.get_items_batch(pmids, batch_size=2)
        assert len(articles) > 0, "Should retrieve articles in batch"
        
    # Test ClinicalTrials batch processing
    async with ClinicalTrialsCrawler(notification_manager, config=config) as trials:
        nctids = []
        async for nctid in trials.search("cancer", max_results=3):
            nctids.append(nctid)
            
        trial_results = await trials.get_items_batch(nctids, batch_size=2)
        assert len(trial_results) > 0, "Should retrieve trials in batch"

@pytest.mark.asyncio
async def test_error_handling(notification_manager) -> None:
    """Test error handling in crawlers."""
    config = get_test_config()
    
    async with PubMedCrawler(notification_manager, config=config) as pubmed:
        # Test invalid ID handling
        with pytest.raises(Exception):
            await pubmed.get_item("invalid_id_xyz123")
            
    async with ClinicalTrialsCrawler(notification_manager, config=config) as trials:
        # Test invalid ID handling
        with pytest.raises(Exception):
            await trials.get_item("invalid_id_xyz123")

@pytest.mark.asyncio
async def test_duplicate_filtering(notification_manager) -> None:
    """Test filtering of duplicate IDs when using old_item_ids."""
    config = get_test_config()
    
    async with PubMedCrawler(notification_manager, config=config) as pubmed:
        # First search
        first_pmids = []
        async for pmid in pubmed.search("cancer", max_results=2):
            first_pmids.append(pmid)
            
        # Second search excluding first results
        second_pmids = []
        async for pmid in pubmed.search("cancer", max_results=2, old_item_ids=set(first_pmids)):
            second_pmids.append(pmid)
            
        # Check no duplicates
        assert not set(first_pmids) & set(second_pmids), "Should not have duplicate PMIDs"