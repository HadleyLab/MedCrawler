"""PubMed crawler using NCBI E-utilities API."""
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Set
import xml.etree.ElementTree as ET
import json
from .base import BaseCrawler, async_timed_cache, APIError
from backend.utils.notification_manager import NotificationManager
from config import CrawlerConfig

logger = logging.getLogger(__name__)

class PubMedCrawler(BaseCrawler):
    """Crawler for PubMed articles using NCBI E-utilities."""
    
    def __init__(self, notification_manager: NotificationManager, config: Optional[CrawlerConfig] = None):
        """Initialize the PubMed crawler with NCBI E-utilities endpoint."""
        super().__init__(
            notification_manager,
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
            config
        )
        # Get PubMed-specific settings from config
        pubmed_config = self.config.source_settings.get("pubmed", {})
        self.tool = pubmed_config.get("tool_name", "MedLitAssistant")
        self.email = pubmed_config.get("email", self.config.email)
        self.api_key = pubmed_config.get("api_key", None)  # API key is optional
        
        # Log configuration info
        if self.debug_mode:
            logger.debug(f"PubMed crawler initialized with:")
            logger.debug(f"  Tool name: {self.tool}")
            logger.debug(f"  Email: {self.email or 'Not provided'}")
            logger.debug(f"  API key: {'Provided' if self.api_key else 'Not used'}")
        else:
            logger.info("PubMed crawler initialized")

    def _add_auth_params(self, params: Dict) -> Dict:
        """Add authentication and identification parameters to the request."""
        params = params.copy()
        params["tool"] = self.tool
        if self.email:  # Email is important for rate limiting
            params["email"] = self.email
        if self.api_key:  # API key is optional
            params["api_key"] = self.api_key
        return params

    @async_timed_cache()
    async def _get_article_count(self, query: str) -> int:
        """Get total count of articles matching query."""
        params = {
            "db": "pubmed",
            "term": query,
            "rettype": "count",
            "retmode": "json"
        }
        params = self._add_auth_params(params)
        data = await self._make_request(
            "esearch.fcgi",
            params=params,
            error_prefix="PubMed count error"
        )
        if isinstance(data, str):
            data = json.loads(data)
        return int(data.get("esearchresult", {}).get("count", 0))

    @async_timed_cache()
    async def _get_article_batch(self, query: str, batch_size: int, retstart: int) -> Set[str]:
        """Get a batch of article IDs."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": batch_size,
            "retstart": retstart,
            "retmode": "json"
        }
        params = self._add_auth_params(params)
        data = await self._make_request(
            "esearch.fcgi",
            params=params,
            error_prefix="PubMed search error"
        )
        if isinstance(data, str):
            data = json.loads(data)
        return set(data.get("esearchresult", {}).get("idlist", []))

    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        old_item_ids: Optional[Set[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Search for PubMed articles and yield their PMIDs.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            old_item_ids: Set of PMIDs to exclude from results
            
        Yields:
            PMIDs matching the search criteria
        """
        old_item_ids = old_item_ids or set()
        total_fetched = 0
        retstart = 0
        batch_size = 100  # Max allowed by PubMed API
        
        total_results = await self._get_article_count(query)
        target_results = min(max_results or total_results, total_results)
        
        if self.debug_mode:
            logger.debug(f"Found {total_results} total results for query: {query}")
            logger.debug(f"Will fetch up to {target_results} results")
        
        while total_fetched < target_results:
            try:
                pmids = await self._get_article_batch(query, batch_size, retstart)
                if not pmids:
                    break
                    
                for pmid in pmids:
                    if pmid not in old_item_ids:
                        yield pmid
                        total_fetched += 1
                        if max_results and total_fetched >= max_results:
                            return
                
                retstart += batch_size
            except Exception as e:
                logger.error(f"Error fetching batch at offset {retstart}: {e}")
                raise

    async def get_metadata_request_params(self, item_id: str) -> Dict:
        """Get parameters for requesting PubMed article metadata."""
        params = {
            "db": "pubmed",
            "id": item_id,
            "retmode": "xml",
            "rettype": "full"
        }
        return self._add_auth_params(params)

    async def get_metadata_endpoint(self) -> str:
        """Get the endpoint URL for PubMed article metadata requests."""
        return "efetch.fcgi"

    def extract_metadata(self, response_data: Any) -> Dict[str, Any]:
        """Extract metadata from PubMed XML response."""
        try:
            root = ET.fromstring(response_data)
            article = root.find(".//PubmedArticle")
            
            if article is None:
                raise APIError("Article not found")
                
            pmid = article.findtext(".//PMID")
            if not pmid:
                raise APIError("Invalid article data: missing PMID")
                
            return {
                "pmid": pmid,
                "title": article.findtext(".//ArticleTitle") or "No title",
                "abstract": " ".join(
                    text.text or ""
                    for text in article.findall(".//AbstractText")
                ),
                "authors": [
                    f"{author.findtext('LastName', '')} {author.findtext('ForeName', '')}"
                    for author in article.findall(".//Author")
                ],
                "journal": article.findtext(".//Journal/Title"),
                "doi": article.findtext(".//ArticleId[@IdType='doi']"),
                "pubdate": self._format_publication_date(article.find(".//PubDate"))
            }
        except ET.ParseError as e:
            raise APIError(f"Invalid XML response: {str(e)}")
    
    def _format_publication_date(self, pubdate_elem: Optional[ET.Element]) -> str:
        """Format publication date from PubMed XML."""
        if pubdate_elem is None:
            return "Unknown date"
            
        return "/".join(
            date.text
            for date in pubdate_elem.findall("*")
            if date is not None and date.text
        )