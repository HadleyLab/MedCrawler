"""
Demonstration module for the medical literature crawlers.

This module provides demonstration utilities for the medical literature crawlers,
including command-line interface and sample usage patterns for the crawler classes.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from .clinical_trials import ClinicalTrialsCrawler
from .pubmed import PubMedCrawler

logger = logging.getLogger(__name__)


async def demo_crawler(
    crawler_type: str,
    query: str,
    max_results: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> None:
    """Demonstrate crawler functionality with a single source.
    
    Args:
        crawler_type: Type of crawler to use ('clinicaltrials' or 'pubmed')
        query: Search query string
        max_results: Maximum number of results to retrieve
        from_date: Start date for filtering results (format depends on crawler)
        to_date: End date for filtering results (format depends on crawler)
        
    Raises:
        ValueError: If an unknown crawler type is provided
    """
    # Create the appropriate crawler
    if crawler_type.lower() == "clinicaltrials":
        crawler = ClinicalTrialsCrawler()
        print(f"Searching ClinicalTrials.gov for '{query}'...")
        if from_date or to_date:
            print(f"Date range filter: StartDate from {from_date or 'MIN'} and LastUpdatePostDate to {to_date or 'MAX'}")
    elif crawler_type.lower() == "pubmed":
        crawler = PubMedCrawler()
        print(f"Searching PubMed for '{query}'...")
        if from_date or to_date:
            print(f"Date range filter: from {from_date or '1900/01/01'} to {to_date or 'today'}")
    else:
        raise ValueError(f"Unknown crawler type: {crawler_type}")
    
    # Use the crawler within an async context
    async with crawler:
        # Search demonstration
        print(f"\n=== SEARCH DEMONSTRATION ===")
        print(f"Fetching up to {max_results} results...")
        item_ids = []
        counter = 0
        
        async for item_id in crawler.search(
            query, 
            max_results=max_results,
            from_date=from_date,
            to_date=to_date
        ):
            item_ids.append(item_id)
            counter += 1
            print(f"  Found item {counter}: {item_id}")
            
        if not item_ids:
            print("No results found.")
            return
            
        # Single item metadata demonstration
        print(f"\n=== SINGLE ITEM METADATA DEMONSTRATION ===")
        first_id = item_ids[0]
        print(f"Retrieving metadata for {first_id}:")
        
        try:
            metadata = await crawler.get_item(first_id)
            print("\nMetadata:")
            for key, value in metadata.items():
                if isinstance(value, (list, dict)):
                    print(f"  {key}:")
                    if isinstance(value, list) and value and isinstance(value[0], str):
                        print(f"    {', '.join(value)}")
                    else:
                        print(f"    {value}")
                else:
                    if isinstance(value, str) and len(value) > 100:
                        print(f"  {key}: {value[:100]}...")
                    else:
                        print(f"  {key}: {value}")
        except Exception as e:
            print(f"Error retrieving metadata: {e}")
            
        # Batch retrieval demonstration
        if len(item_ids) > 1:
            print(f"\n=== BATCH RETRIEVAL DEMONSTRATION ===")
            batch_size = min(3, len(item_ids))
            print(f"Retrieving metadata for {batch_size} items in batch:")
            
            try:
                batch_results = await crawler.get_items_batch(item_ids[:batch_size])
                print(f"Successfully retrieved {len(batch_results)} items")
                
                for i, result in enumerate(batch_results):
                    title = result.get("title", "No title")
                    if len(title) > 60:
                        title = title[:57] + "..."
                    
                    if crawler_type.lower() == "clinicaltrials":
                        id_field = "nct_id"
                        status = result.get("status", "Unknown")
                        print(f"  {i+1}. [{result.get(id_field, 'Unknown ID')}] {title} (Status: {status})")
                    else:  # pubmed
                        id_field = "pmid"
                        authors = result.get("authors", [])
                        author_text = ", ".join(authors[:2]) + (", et al." if len(authors) > 2 else "")
                        print(f"  {i+1}. [{result.get(id_field, 'Unknown ID')}] {title} ({author_text})")
                        
            except Exception as e:
                print(f"Error retrieving batch: {e}")
                
        # Caching demonstration
        print(f"\n=== CACHING DEMONSTRATION ===")
        print(f"Retrieving {first_id} again (should use cache):")
        start_time = time.time()
        try:
            cached_metadata = await crawler.get_item(first_id)
            elapsed = time.time() - start_time
            print(f"Retrieved in {elapsed:.4f} seconds")
            
            # Find a field to compare to verify it's the same data
            if crawler_type.lower() == "clinicaltrials":
                compare_field = "title"
            else:
                compare_field = "title"
                
            print(f"Verified cached {compare_field}: {cached_metadata.get(compare_field, 'N/A')}")
            
        except Exception as e:
            print(f"Error retrieving cached item: {e}")


def main():
    """Entry point for the crawler demonstration.
    
    This function sets up the command-line argument parser and runs the selected
    crawler demonstrations based on user input.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Demonstrate medical literature crawler functionality')
    parser.add_argument('--source', type=str, default='all',
                       choices=['all', 'clinicaltrials', 'pubmed'],
                       help='Source to crawl (clinicaltrials, pubmed, or all)')
    parser.add_argument('--query', type=str, default='cancer',
                       help='Search query')
    parser.add_argument('--max', type=int, default=5,
                       help='Maximum number of results to retrieve')
    
    # Add date range parameters
    parser.add_argument('--from-date', type=str, default=None,
                       help='Start date for filtering results (YYYY-MM-DD for ClinicalTrials, YYYY/MM/DD for PubMed)')
    parser.add_argument('--to-date', type=str, default=None,
                       help='End date for filtering results (YYYY-MM-DD for ClinicalTrials, YYYY/MM/DD for PubMed)')
    parser.add_argument('--recent', action='store_true',
                       help='Short for setting from-date to 90 days ago')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handle --recent option
    if args.recent and not args.from_date:
        # Calculate date 90 days ago
        today = datetime.now()
        days_ago_90 = today - timedelta(days=90)
        
        # Format differently based on source
        if args.source == 'pubmed':
            args.from_date = days_ago_90.strftime('%Y/%m/%d')
        else:  # clinicaltrials or all
            args.from_date = days_ago_90.strftime('%Y-%m-%d')
    
    # Run demonstrations
    if args.source == 'all':
        print("=== CLINICALTRIALS.GOV DEMONSTRATION ===")
        # For ClinicalTrials.gov, use YYYY-MM-DD format
        from_date = args.from_date
        to_date = args.to_date
        
        asyncio.run(demo_crawler(
            'clinicaltrials', 
            args.query, 
            args.max,
            from_date,
            to_date
        ))
        
        print("\n\n=== PUBMED DEMONSTRATION ===")
        # For PubMed, convert dates to YYYY/MM/DD format if needed
        from_date = args.from_date
        to_date = args.to_date
        
        # Convert date format if needed (from YYYY-MM-DD to YYYY/MM/DD)
        if from_date and '-' in from_date:
            from_date = from_date.replace('-', '/')
        if to_date and '-' in to_date:
            to_date = to_date.replace('-', '/')
        
        asyncio.run(demo_crawler(
            'pubmed', 
            args.query, 
            args.max,
            from_date,
            to_date
        ))
    else:
        # Set format based on source
        from_date = args.from_date
        to_date = args.to_date
        
        if args.source == 'pubmed':
            # Convert date format if needed (from YYYY-MM-DD to YYYY/MM/DD)
            if from_date and '-' in from_date:
                from_date = from_date.replace('-', '/')
            if to_date and '-' in to_date:
                to_date = to_date.replace('-', '/')
        
        asyncio.run(demo_crawler(args.source, args.query, args.max, from_date, to_date))


if __name__ == "__main__":
    main()