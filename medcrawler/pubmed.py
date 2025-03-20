"""
PubMed crawler implementation using NCBI E-utilities.

This module provides a crawler for PubMed articles using the NCBI E-utilities API.
It handles searching for articles, fetching article metadata, and parsing
XML responses from PubMed.
"""
import json
import xml.etree.ElementTree as ET
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Set, List
from .base import BaseCrawler, async_timed_cache
from .config import CrawlerConfig
from .exceptions import APIError

logger = logging.getLogger(__name__)


class PubMedCrawler(BaseCrawler):
    """Crawler for PubMed articles using NCBI E-utilities."""
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """Initialize the PubMed crawler with NCBI E-utilities endpoint.
        
        Args:
            config: Optional crawler configuration. If not provided,
                   the default configuration will be used.
        """
        config = config or CrawlerConfig()
        config.api_type = "pubmed"  # Ensure PubMed-specific settings
        
        super().__init__(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
            config
        )
        
        # Get API access credentials
        self.tool = "MedCrawler"
        self.email = self.config.email
        self.api_key = self.config.api_key
        
        # Log configuration info
        if self.debug_mode:
            logger.debug(f"PubMed crawler initialized with:")
            logger.debug(f"  Tool name: {self.tool}")
            logger.debug(f"  Email: {self.email or 'Not provided'}")
            logger.debug(f"  API key: {'Provided' if self.api_key else 'Not used'}")
            logger.debug(f"  Rate limit: {1/self.config.min_interval:.1f} req/sec")
            logger.debug(f"  Batch size: {self.config.default_batch_size}")
        else:
            logger.info("PubMed crawler initialized")

    def _add_auth_params(self, params: Dict) -> Dict:
        """Add authentication and identification parameters to the request.
        
        Args:
            params: Original request parameters dictionary
            
        Returns:
            Dictionary with added authentication parameters
        """
        params = params.copy()
        params["tool"] = self.tool
        if self.email:  # Email is important for rate limiting
            params["email"] = self.email
        if self.api_key:  # API key is optional
            params["api_key"] = self.api_key
        return params

    @async_timed_cache()
    async def _get_article_count(self, query: str) -> int:
        """Get total count of articles matching query.
        
        Args:
            query: PubMed search query string
            
        Returns:
            Total number of articles matching the query
            
        Raises:
            APIError: If the count request fails
        """
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
        """Get a batch of article IDs.
        
        Args:
            query: PubMed search query string
            batch_size: Number of results to return per batch
            retstart: Start index for pagination
            
        Returns:
            Set of PMIDs for articles matching the query
            
        Raises:
            APIError: If the search request fails
        """
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
        old_item_ids: Optional[Set[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Search for PubMed articles and yield their PMIDs.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            old_item_ids: Set of PMIDs to exclude from results
            from_date: Start date for filtering results (format: YYYY/MM/DD)
            to_date: End date for filtering results (format: YYYY/MM/DD)
            
        Yields:
            PMIDs of matching articles
            
        Raises:
            APIError: If search requests fail
        """
        old_item_ids = old_item_ids or set()
        total_fetched = 0
        retstart = 0
        batch_size = 100  # Max allowed by PubMed API
        
        # Format the query with date range
        if from_date or to_date:
            if from_date and to_date:
                date_filter = f" {from_date}:{to_date}[PDAT]"
            elif from_date:
                date_filter = f" {from_date}:{from_date}[PDAT]"
            elif to_date:
                # Use a reasonable distant past date for open-ended ranges
                date_filter = f" 1900/01/01:{to_date}[PDAT]"
            
            query = f"{query}{date_filter}"
            logger.info(f"Added date range filter: PDAT with query: {query}")
        
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
        """Get parameters for requesting PubMed article metadata.
        
        Args:
            item_id: PMID of the article to retrieve
            
        Returns:
            Dictionary of request parameters for the PubMed efetch API
        """
        params = {
            "db": "pubmed",
            "id": item_id,
            "retmode": "xml",
            "rettype": "full"
        }
        return self._add_auth_params(params)

    async def get_metadata_endpoint(self) -> str:
        """Get the endpoint URL for PubMed article metadata requests.
        
        Returns:
            Endpoint path string for the PubMed efetch API
        """
        return "efetch.fcgi"

    def extract_metadata(self, response_data: Any) -> Dict[str, Any]:
        """Extract metadata from PubMed XML response.
        
        Args:
            response_data: XML response data from PubMed API
            
        Returns:
            Dictionary containing structured article metadata
            
        Raises:
            APIError: If metadata extraction fails
        """
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
        """Format publication date from PubMed XML.
        
        Args:
            pubdate_elem: XML element containing publication date information
            
        Returns:
            Formatted publication date string
        """
        if pubdate_elem is None:
            return "Unknown date"
            
        return "/".join(
            date.text
            for date in pubdate_elem.findall("*")
            if date is not None and date.text
        )

    async def get_items_batch(
        self,
        item_ids: List[str],
        batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get multiple articles in parallel batches.
        
        Override base implementation to use smaller batch sizes for PubMed's
        rate limits and add delay between batches.
        
        Args:
            item_ids: List of PMIDs to retrieve
            batch_size: Optional override for batch size
            
        Returns:
            List of article metadata dictionaries
        """
        # Use smaller batch size for PubMed to avoid rate limits
        batch_size = min(batch_size or 3, 3)  # Max 3 per batch
        results = []
        total = len(item_ids)
        
        logger.info(f"Fetching {total} items in batches of {batch_size}")
        
        for i in range(0, total, batch_size):
            batch = item_ids[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total - 1) // batch_size + 1
            
            logger.info(f"Fetching batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            # Process items in batch sequentially to respect rate limits
            batch_results = []
            for item_id in batch:
                try:
                    result = await self.get_item(item_id)
                    batch_results.append(result)
                except Exception as e:
                    logger.error(f"Error fetching item {item_id}: {e}")
                    continue
            
            results.extend(batch_results)
            logger.info(f"Completed batch {batch_num}/{total_batches}: "
                       f"{len(batch_results)} successful")
            
        return results