"""
Custom exceptions for the medical literature crawlers.

This module defines the exception hierarchy for the MedCrawler package,
providing specific error types for different failure scenarios.
"""


class CrawlerError(Exception):
    """Base exception for all crawler-related errors.
    
    This serves as the parent class for all exceptions raised by the
    MedCrawler package.
    
    Attributes:
        message: Explanation of the error
    """
    
    pass


class APIError(CrawlerError):
    """Exception raised for errors in API communication.
    
    This includes HTTP errors, request failures, and unexpected
    response formats.
    
    Attributes:
        message: Explanation of the API error
    """
    
    pass


class RateLimitError(APIError):
    """Exception raised when API rate limits are exceeded.
    
    This specialized error helps handle rate limiting scenarios
    differently from other API errors.
    
    Attributes:
        message: Explanation of the rate limit error
        retry_after: Optional time (in seconds) to wait before retrying
    """
    
    def __init__(self, message, retry_after=None):
        """Initialize a new RateLimitError.
        
        Args:
            message: Explanation of the rate limit error
            retry_after: Optional time (in seconds) to wait before retrying
        """
        super().__init__(message)
        self.retry_after = retry_after


class ConfigurationError(CrawlerError):
    """Exception raised for configuration-related errors.
    
    This includes invalid settings, missing required parameters,
    and incompatible configurations.
    
    Attributes:
        message: Explanation of the configuration error
    """
    
    pass