"""
Medical Literature Assistant configuration module.

This module contains configuration settings for the application, including
logging, notifications, and crawler settings. It provides centralized
configuration to maintain consistent behavior across the application.
"""
from pathlib import Path
import logging
import logging.config
import os
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base configuration
APP_NAME = "Medical Literature Assistant"
LOG_LEVEL = os.getenv('LOG_LEVEL', "INFO")
BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "app.log"

# Notification settings
NOTIFICATION_DEFAULTS = {
    "position": os.getenv('NOTIFICATION_POSITION', 'top-right'),
    "timeout": int(os.getenv('NOTIFICATION_TIMEOUT', '5000')),
    "dismissible": True,
}


@dataclass
class LoggingConfig:
    """
    Configuration for application logging.
    
    Attributes:
        level: Base logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        file_level: Logging level for file output (defaults to level)
        console_level: Logging level for console output (defaults to level)
        format_string: Format for log messages
        detailed_format: Detailed format for file logs
        date_format: Date format for timestamps
        disable_existing_loggers: Whether to disable existing loggers
    """
    level: str = LOG_LEVEL
    log_file: Union[str, Path] = LOG_FILE
    file_level: Optional[str] = None
    console_level: Optional[str] = None
    format_string: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    detailed_format: str = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    disable_existing_loggers: bool = False
    
    def get_config_dict(self) -> Dict[str, Any]:
        """
        Generate a logging configuration dictionary.
        
        Returns:
            Dictionary for logging.config.dictConfig
        """
        file_level = self.file_level or self.level
        console_level = self.console_level or self.level
        
        return {
            "version": 1,
            "disable_existing_loggers": self.disable_existing_loggers,
            "formatters": {
                "standard": {
                    "format": self.format_string,
                    "datefmt": self.date_format
                },
                "detailed": {
                    "format": self.detailed_format,
                    "datefmt": self.date_format
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": console_level,
                    "formatter": "standard",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.FileHandler",
                    "level": file_level,
                    "formatter": "detailed",
                    "filename": str(self.log_file),
                    "mode": "a",
                }
            },
            "loggers": {
                "": {  # Root logger
                    "handlers": ["console", "file"],
                    "level": self.level,
                    "propagate": True
                },
                # Add specific logger configurations
                "backend.crawlers": {
                    "level": os.getenv("CRAWLER_LOG_LEVEL", self.level),
                    "handlers": ["console", "file"],
                    "propagate": False
                },
                "backend.utils": {
                    "level": os.getenv("UTILS_LOG_LEVEL", self.level),
                    "handlers": ["console", "file"],
                    "propagate": False
                }
            }
        }


class CrawlerConfig:
    """
    Configuration for medical literature crawlers.
    
    Centralizes settings for API interactions including rate limiting,
    authentication, and retry behavior across different crawler implementations.
    """
    
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


# Default logging configuration
DEFAULT_LOGGING_CONFIG = LoggingConfig()


def configure_logging(config: Optional[LoggingConfig] = None) -> None:
    """
    Initialize application logging with the specified or default configuration.
    
    Args:
        config: Optional logging configuration (uses DEFAULT_LOGGING_CONFIG if None)
    """
    cfg = config or DEFAULT_LOGGING_CONFIG
    logging.config.dictConfig(cfg.get_config_dict())
    logging.info(f"Logging initialized at level {cfg.level}")
    
    # Log initial application startup information
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {APP_NAME}")
    logger.debug(f"Base directory: {BASE_DIR}")
    logger.debug(f"Log file: {cfg.log_file}")


# Initialize logging if this module is imported directly
if __name__ != "__main__":
    configure_logging()