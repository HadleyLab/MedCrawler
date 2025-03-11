# MedCrawler

MedCrawler is a medical literature assistant that helps healthcare professionals and researchers crawl, extract, and monitor medical information from various online sources including PubMed and ClinicalTrials.gov.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/MedCrawler.git
cd MedCrawler

# Install dependencies
pip install -r requirements.txt

# Optional: Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Optional API credentials for increased rate limits
PUBMED_EMAIL=your.email@example.com
PUBMED_API_KEY=your_api_key_if_you_have_one

# Logging configuration
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Running the Application

### Main Application

The main application provides a web interface for searching medical literature:

```bash
python app.py
```

This will start the web server, and you can access the application at http://localhost:8080 in your browser.

### Using the Crawlers Directly

You can also use the crawlers directly from the demos directory:

```bash
# Navigate to the demos directory
cd demos/crawlers

# Run the crawler demo
python crawler.py --source pubmed --query "diabetes treatment" --max_results 10

# For ClinicalTrials.gov
python crawler.py --source clinical_trials --query "cancer immunotherapy" --max_results 10
```

Available options:
- `--source`: Specify the data source (`pubmed` or `clinical_trials`)
- `--query`: Your search query
- `--max_results`: Maximum number of results to retrieve
- `--year_from`: Filter by start year 
- `--year_to`: Filter by end year
- `--output`: Output file path (JSON format)

## Features

- **Unified Search Interface**: Search across multiple medical databases including PubMed and ClinicalTrials.gov
- **Year-Based Filtering**: Filter results by publication date range
- **Real-time Notifications**: Progress tracking for long-running search operations
- **Tabbed Results View**: View results in a structured, tabbed interface
- **Abstract Previews**: Read article abstracts without leaving the application

## Development

### Testing

Run the test suite with:

```bash
pytest
```

For coverage report:

```bash
pytest --cov=backend --cov-report=html
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
