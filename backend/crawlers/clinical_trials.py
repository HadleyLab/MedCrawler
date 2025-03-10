"""Clinical Trials crawler using clinicaltrials.gov API."""
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Set
import json
from .base import BaseCrawler, async_timed_cache, APIError
from backend.utils.notification_manager import NotificationManager
from config import CrawlerConfig

logger = logging.getLogger(__name__)

class ClinicalTrialsCrawler(BaseCrawler):
    """Crawler for ClinicalTrials.gov studies using their API v2."""
    
    def __init__(self, notification_manager: NotificationManager, config: Optional[CrawlerConfig] = None):
        """Initialize the ClinicalTrials.gov crawler with API v2 endpoint."""
        super().__init__(
            notification_manager,
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
        """
        Search for clinical trials.
        
        Args:
            query: Search query string
            page_size: Number of results per page
            page_token: Token for pagination
            
        Returns:
            Dictionary containing search results
        """
        params = {
            "query.titles": query,
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
        old_item_ids: Optional[Set[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Search for clinical trials and yield their NCT IDs.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            old_item_ids: Set of NCT IDs to exclude from results
            
        Yields:
            NCT IDs matching the search criteria
        """
        old_item_ids = old_item_ids or set()
        total_fetched = 0
        page_token = None
        page_size = 100  # Maximum allowed by the API
        
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
        """Get parameters for requesting clinical trial metadata."""
        return {
            "query.id": item_id,
            "format": "json"
        }

    async def get_metadata_endpoint(self) -> str:
        """Get the endpoint URL for ClinicalTrials.gov study metadata requests."""
        return ""  # Base URL already includes 'studies'

    def extract_metadata(self, response_data: Any) -> Dict[str, Any]:
        """Extract metadata from ClinicalTrials.gov JSON response."""
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