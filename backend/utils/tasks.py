"""
Example tasks for notification system demonstration.

This module provides example synchronous and asynchronous tasks of
varying durations to demonstrate the notification system functionality.
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


def short_task():
    """
    Short synchronous task that takes about 0.5 seconds.
    
    Returns:
        str: Completion message
    """
    logger.debug("Starting short task")
    time.sleep(0.5)
    logger.debug("Completed short task")
    return "Short task completed"


def medium_task():
    """
    Medium synchronous task that takes about 2 seconds.
    
    Returns:
        str: Completion message
    """
    logger.debug("Starting medium task")
    time.sleep(2)
    logger.debug("Completed medium task")
    return "Medium task completed"


def long_task():
    """
    Long synchronous task that takes about 5 seconds.
    
    Returns:
        str: Completion message
    """
    logger.debug("Starting long task")
    time.sleep(5)
    logger.debug("Completed long task")
    return "Long task completed"


def error_task():
    """
    Task that raises an error for testing error handling.
    
    Raises:
        ValueError: Simulated error for testing
    """
    logger.debug("Starting error task")
    time.sleep(0.2)  # Brief pause before error
    logger.error("Error task is about to raise an exception")
    raise ValueError("Simulated error in task")


async def short_async_task():
    """
    Short asynchronous task that takes about 0.5 seconds.
    
    Returns:
        str: Completion message
    """
    logger.debug("Starting short async task")
    await asyncio.sleep(0.5)
    logger.debug("Completed short async task")
    return "Short async task completed"


async def medium_async_task():
    """
    Medium asynchronous task that takes about 2 seconds.
    
    Returns:
        str: Completion message
    """
    logger.debug("Starting medium async task")
    await asyncio.sleep(2)
    logger.debug("Completed medium async task")
    return "Medium async task completed"


async def long_async_task():
    """
    Long asynchronous task that takes about 5 seconds.
    
    Returns:
        str: Completion message
    """
    logger.debug("Starting long async task")
    await asyncio.sleep(5)
    logger.debug("Completed long async task")
    return "Long async task completed"


async def error_async_task():
    """
    Asynchronous task that raises an error for testing error handling.
    
    Raises:
        ValueError: Simulated error for testing
    """
    logger.debug("Starting error async task")
    await asyncio.sleep(0.1)  # Brief pause before error
    logger.error("Error async task is about to raise an exception")
    raise ValueError("Simulated error in async task")