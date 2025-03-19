"""
ClinicalTrials.gov crawler implementation.

This module provides a crawler for studies from ClinicalTrials.gov using their API v2.
It handles searching for studies, fetching study metadata, and parsing
JSON responses from ClinicalTrials.gov.
"""
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Set, List
from .base import BaseCrawler, async_timed_cache
from .config import CrawlerConfig
from .exceptions import APIError

logger = logging.getLogger(__name__)


class ClinicalTrialsCrawler(BaseCrawler):
    """Crawler for ClinicalTrials.gov studies using their API v2.
    
    This crawler interfaces with ClinicalTrials.gov API v2 to search for studies
    and retrieve detailed study metadata in JSON format. It implements the
    abstract methods defined in BaseCrawler specifically for ClinicalTrials.gov.
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """Initialize the ClinicalTrials.gov crawler with API v2 endpoint.
        
        Args:
            config: Optional crawler configuration. If not provided,
                   the default configuration will be used.
        """
        super().__init__(
            "https://clinicaltrials.gov/api/v2/studies",
            config
        )
        
        if self.debug_mode:
            logger.debug("ClinicalTrials.gov crawler initialized")
    
    @async_timed_cache()
    async def _search_studies(
        self,
        query: str,
        page_size: int,
        page_token: Optional[str] = None
    ) -> Dict:
        """Search for clinical trials.
        
        Args:
            query: Search query string for clinical trials
            page_size: Number of results per page
            page_token: Token for pagination, if any
            
        Returns:
            Dictionary containing search results
            
        Raises:
            APIError: If the search request fails
        """
        params = {
            "query.term": query,
            "pageSize": page_size,
            "format": "json"
        }
        if page_token:
            params["pageToken"] = page_token
            
        return await self._make_request(
            "",  # Base URL already includes 'studies'
            params=params,
            error_prefix="Clinical Trials search error"
        )

    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        old_item_ids: Optional[Set[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Search for clinical trials and yield their NCT IDs.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            old_item_ids: Set of NCT IDs to exclude from results
            from_date: Start date for filtering trials using StartDate (format: YYYY-MM-DD or "MIN")
            to_date: End date for filtering trials using LastUpdatePostDate (format: YYYY-MM-DD or "MAX")
            
        Yields:
            NCT IDs of matching studies
            
        Raises:
            APIError: If search requests fail
        """
        old_item_ids = old_item_ids or set()
        total_fetched = 0
        page_token = None
        page_size = 100  # Maximum allowed by the API
        
        # Add date range filters if provided
        original_query = query
        
        # Handle the from_date filter using StartDate
        if from_date:
            from_date_value = from_date
            query = f"{query} AREA[StartDate]RANGE[{from_date_value},MAX]"
            logger.info(f"Added StartDate filter for from_date: {from_date_value}")
        
        # Handle the to_date filter using LastUpdatePostDate
        if to_date:
            to_date_value = to_date
            query = f"{query} AREA[LastUpdatePostDate]RANGE[MIN,{to_date_value}]"
            logger.info(f"Added LastUpdatePostDate filter for to_date: {to_date_value}")
        
        if from_date or to_date:
            logger.info(f"Modified query: {original_query} -> {query}")
        
        while True:
            data = await self._search_studies(query, page_size, page_token)
            studies = data.get("studies", [])
            
            if not studies:
                break
                
            for study in studies:
                try:
                    nct_id = study["protocolSection"]["identificationModule"].get("nctId")
                    if nct_id and nct_id not in old_item_ids:
                        yield nct_id
                        total_fetched += 1
                        if max_results and total_fetched >= max_results:
                            return
                except KeyError:
                    logger.warning(f"Malformed study data: {study}")
                    continue
                        
            page_token = data.get("nextPageToken")
            if not page_token:
                break

    async def get_metadata_request_params(self, item_id: str) -> Dict:
        """Get parameters for requesting clinical trial metadata.
        
        Args:
            item_id: NCT ID of the study to retrieve
            
        Returns:
            Dictionary of request parameters for the ClinicalTrials.gov API
        """
        return {
            "query.id": item_id,
            "format": "json"
        }

    async def get_metadata_endpoint(self) -> str:
        """Get the endpoint URL for ClinicalTrials.gov study metadata requests.
        
        Returns:
            Endpoint path string for the ClinicalTrials.gov API
        """
        return ""  # Base URL already includes 'studies'

    def extract_metadata(self, response_data: Any) -> Dict[str, Any]:
        """Extract metadata from ClinicalTrials.gov JSON response.
        
        Args:
            response_data: JSON response data from ClinicalTrials.gov API
            
        Returns:
            Dictionary containing structured study metadata
            
        Raises:
            APIError: If metadata extraction fails
        """
        if isinstance(response_data, str):
            data = json.loads(response_data)
        else:
            data = response_data
            
        studies = data.get("studies", [])
        if not studies:
            raise APIError("Study not found")
            
        study = studies[0]
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        description = protocol.get("descriptionModule", {})
        conditions = protocol.get("conditionsModule", {})
        eligibility = protocol.get("eligibilityModule", {})
        
        nct_id = identification.get("nctId")
        if not nct_id:
            raise APIError("Invalid trial data: missing NCT ID")
            
        return {
            "nct_id": nct_id,
            "title": identification.get("briefTitle"),
            "status": status.get("overallStatus"),
            "phase": design.get("phases", []),
            "conditions": conditions.get("conditions", []),
            "description": description.get("detailedDescription"),
            "summary": description.get("briefSummary"),
            "eligibility_criteria": eligibility.get("eligibilityCriteria"),
            "start_date": status.get("startDateStruct", {}).get("date"),
            "completion_date": status.get("primaryCompletionDateStruct", {}).get("date"),
            "last_updated": status.get("lastUpdateSubmitDateStruct", {}).get("date")
        }