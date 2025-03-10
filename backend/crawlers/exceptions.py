"""Crawler-specific exceptions."""

class CrawlerError(Exception):
    """Base exception for crawler errors."""
    pass

class APIError(CrawlerError):
    """Exception for API-related errors."""
    pass

class RateLimitError(APIError):
    """Exception for rate limiting errors."""
    pass

class ConfigurationError(CrawlerError):
    """Exception for configuration errors."""
    pass