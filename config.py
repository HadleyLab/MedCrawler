from pathlib import Path
import logging.config
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base configuration
APP_NAME = "Medical Literature Assistant"
LOG_LEVEL = os.getenv('LOG_LEVEL', "INFO")
BASE_DIR = Path(__file__).parent

# Notification settings
NOTIFICATION_DEFAULTS = {
    "position": os.getenv('NOTIFICATION_POSITION', 'top-right'),
    "timeout": int(os.getenv('NOTIFICATION_TIMEOUT', '5000')),
}

# Crawler Configuration
class CrawlerConfig:
    """Configuration for medical literature crawlers."""
    
    def __init__(
        self,
        user_agent: str = "Medical Literature Assistant/1.0",
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_wait: float = 1.0,
        min_interval: float = 0.2,  # Seconds between requests
        default_batch_size: int = 10,
        source_settings: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """
        Initialize crawler configuration.
        
        Args:
            user_agent: User agent string for API requests
            email: Email for API authentication (required by some APIs)
            api_key: API key for authentication (required by some APIs)
            max_retries: Maximum number of retry attempts for failed requests
            retry_wait: Base wait time for retries (in seconds)
            min_interval: Minimum time between API requests (in seconds)
            default_batch_size: Default batch size for bulk operations
            source_settings: Source-specific settings as a nested dictionary
        """
        self.user_agent = user_agent
        self.email = email or os.environ.get("CRAWLER_EMAIL")
        self.api_key = api_key or os.environ.get("CRAWLER_API_KEY") 
        self.max_retries = max_retries
        self.retry_wait = retry_wait
        self.min_interval = min_interval
        self.default_batch_size = default_batch_size
        self.source_settings = source_settings or {
            "pubmed": {
                "tool_name": "MedLitAssistant",
                "email": self.email,
                "api_key": self.api_key,
            },
        }

# Default crawler configuration
DEFAULT_CRAWLER_CONFIG = CrawlerConfig(
    email=os.environ.get("PUBMED_EMAIL"),
    api_key=os.environ.get("PUBMED_API_KEY"),
)

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "level": LOG_LEVEL,
            "formatter": "standard",
            "filename": str(BASE_DIR / "app.log"),
            "mode": "a",
        }
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": True
        }
    }
}

# Initialize logging
logging.config.dictConfig(LOGGING_CONFIG)