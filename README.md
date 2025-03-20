# MedCrawler

MedCrawler is a Python package that provides asynchronous interfaces for crawling medical literature databases. It currently supports crawling data from PubMed (via NCBI E-utilities) and ClinicalTrials.gov (via their API v2).

## Features

- Asynchronous HTTP requests for efficient data retrieval
- Built-in rate limiting and retry strategies with exponential backoff
- Caching with time-based expiration
- Batch processing capabilities
- Comprehensive error handling
- Date-based filtering for both PubMed and ClinicalTrials.gov
- Well-defined abstract interfaces for easy extension to other sources

## Installation

### As a Package
```bash
pip install git+https://github.com/yourusername/MedCrawler.git
```

### As a Git Submodule
Add the repository as a submodule to your project:
```bash
git submodule add https://github.com/yourusername/MedCrawler.git
git submodule update --init --recursive
```

Install the package in editable mode:
```bash
pip install -e ./MedCrawler
```

## Usage

### Basic Example

```python
import asyncio
from crawlers import PubMedCrawler

async def main():
    async with PubMedCrawler() as crawler:
        # Search for articles
        async for pmid in crawler.search("cancer treatment", max_results=5):
            # Fetch metadata for each article
            metadata = await crawler.get_item(pmid)
            print(f"Title: {metadata['title']}")
            print(f"Authors: {', '.join(metadata['authors'])}")
            print(f"Abstract: {metadata['abstract'][:100]}...")
            print("\n" + "-" * 50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
```

### Command-Line Demo

The package includes a demonstration script that showcases its functionality:

```bash
python main.py --source pubmed --query "diabetes" --max 10
python main.py --source clinicaltrials --query "covid" --max 5 --recent
```

Available options:
- `--source`: `pubmed`, `clinicaltrials`, or `all` (default: `all`)
- `--query`: Search query string (default: `cancer`)
- `--max`: Maximum number of results (default: `5`)
- `--from-date`: Start date for filtering results (format depends on source)
- `--to-date`: End date for filtering results (format depends on source)
- `--recent`: Short for setting from-date to 90 days ago

## API Reference

### Base Crawler

The `BaseCrawler` class provides core functionality used by all crawler implementations:

```python
from crawlers import CrawlerConfig
from medcrawler.base import BaseCrawler

# Create a custom configuration
config = CrawlerConfig(
    user_agent="YourApp/1.0",
    email="your@email.com",
    api_key="your-api-key",  # Optional
    min_interval=0.5  # Seconds between requests
)

# Use the crawler with the configuration
async with YourCrawler(config) as crawler:
    # Your code here
```

### PubMed Crawler

```python
from crawlers import PubMedCrawler

async with PubMedCrawler() as crawler:
    # Search with date filtering (YYYY/MM/DD format)
    async for pmid in crawler.search(
        query="cancer treatment",
        max_results=10,
        from_date="2023/01/01",
        to_date="2023/12/31"
    ):
        metadata = await crawler.get_item(pmid)
        
    # Batch retrieval for efficiency
    pmids = ["12345678", "23456789", "34567890"]
    results = await crawler.get_items_batch(pmids)
```

### ClinicalTrials Crawler

```python
from crawlers import ClinicalTrialsCrawler

async with ClinicalTrialsCrawler() as crawler:
    # Search with date filtering (YYYY-MM-DD format)
    async for nct_id in crawler.search(
        query="covid vaccine",
        max_results=10,
        from_date="2023-01-01",
        to_date="2023-12-31"
    ):
        metadata = await crawler.get_item(nct_id)
```

## Extending

You can implement your own crawler by extending the `BaseCrawler` class:

```python
from medcrawler.base import BaseCrawler
from typing import Dict, Any, AsyncGenerator, Set, Optional

class YourCrawler(BaseCrawler):
    def __init__(self, config=None):
        super().__init__("https://your-api-base-url.com", config)
    
    async def search(
        self, 
        query: str, 
        max_results: Optional[int] = None,
        old_item_ids: Optional[Set[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        # Implementation here
    
    async def get_metadata_request_params(self, item_id: str) -> Dict:
        # Implementation here
    
    async def get_metadata_endpoint(self) -> str:
        # Implementation here
    
    def extract_metadata(self, response_data: Any) -> Dict[str, Any]:
        # Implementation here
```

## Development

### Project Structure
```
medcrawler/
├── __init__.py     # Package version and exports
├── base.py         # Base crawler implementation
├── pubmed.py       # PubMed crawler
├── clinical_trials.py  # ClinicalTrials.gov crawler
└── config.py       # Configuration handling
```

### Running Tests

```bash
pytest
```

### Code Style

This project follows PEP 8 style guidelines and uses:
- Black for code formatting
- isort for import sorting
- pytest for testing

### Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[MIT License](LICENSE)