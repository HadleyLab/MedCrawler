"""
Logging configuration for MedCrawler.

This module provides centralized logging configuration for the entire package,
including formatters, handlers, and log level settings for different environments.
"""
import logging
import sys
from typing import Optional
import colorlog


def configure_logging(level: Optional[str] = None) -> None:
    """Configure logging for the MedCrawler package.
    
    Args:
        level: Optional log level override. If not provided, uses INFO.
              
    The configuration includes:
    - Console handler with colored output
    - Consistent formatting across all loggers
    - Different levels for different package components
    - Rate limiting for frequent log messages
    """
    # Always use INFO unless explicitly overridden
    if level is None:
        level = 'INFO'
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(level)
    
    # Create color formatter
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set specific levels for different components
    logging.getLogger('medcrawler.base').setLevel(level)
    logging.getLogger('medcrawler.pubmed').setLevel(level)
    logging.getLogger('medcrawler.clinical_trials').setLevel(level)
    
    # Quiet some noisy loggers in testing
    if 'pytest' in sys.modules:
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        logging.getLogger('aiohttp.client').setLevel(logging.WARNING)