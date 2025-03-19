"""
Configuration module for medical literature medcrawler.

This module provides configuration settings for crawler classes through
a dataclass-based approach, defining default values and types for all
configuration parameters.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class CrawlerConfig:
    """Configuration for crawler behavior and API access.
    
    This class centralizes all configuration parameters that control
    crawler behavior, such as rate limiting, retries, and identification.
    
    Attributes:
        user_agent: User agent string for API requests
        email: Email address for API identification
        api_key: Optional API key for increased rate limits
        min_interval: Minimum seconds between requests
        max_retries: Maximum number of retry attempts
        retry_wait: Base wait time in seconds for exponential backoff
        default_batch_size: Default size for batch operations
        cache_ttl: Cache time-to-live in seconds
        extra_headers: Optional additional HTTP headers
    """
    user_agent: str = "MedCrawler/1.0"
    email: str = "example@example.com"
    api_key: Optional[str] = None
    min_interval: float = 0.2  # Seconds between requests
    max_retries: int = 3
    retry_wait: int = 2  # Base wait time for exponential backoff
    default_batch_size: int = 10
    cache_ttl: int = 3600  # 1 hour cache
    extra_headers: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization.
        
        Raises:
            ValueError: If any configuration parameter has an invalid value
        """
        if self.min_interval < 0:
            raise ValueError("min_interval must be non-negative")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_wait < 0:
            raise ValueError("retry_wait must be non-negative")
        if self.default_batch_size < 1:
            raise ValueError("default_batch_size must be positive")
        if self.cache_ttl < 0:
            raise ValueError("cache_ttl must be non-negative")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> CrawlerConfig:
        """Create a CrawlerConfig instance from a dictionary.
        
        Args:
            config_dict: Dictionary containing configuration values
            
        Returns:
            A new CrawlerConfig instance with values from the dictionary
            
        Notes:
            Only keys that match CrawlerConfig fields will be used.
            Other keys in the dictionary will be ignored.
        """
        return cls(**{
            k: v for k, v in config_dict.items()
            if k in cls.__dataclass_fields__
        })


# Default configuration used if none provided
DEFAULT_CRAWLER_CONFIG = CrawlerConfig()