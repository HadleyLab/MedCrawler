"""Example tasks for notification demo."""
import asyncio
import time

def short_task():
    """Short synchronous task that takes about 0.5 seconds."""
    time.sleep(0.5)
    return "Short task completed"

def medium_task():
    """Medium synchronous task that takes about 2 seconds."""
    time.sleep(2)
    return "Medium task completed"

def long_task():
    """Long synchronous task that takes about 5 seconds."""
    time.sleep(5)
    return "Long task completed"

def error_task():
    """Task that raises an error."""
    raise ValueError("Simulated error in task")

async def short_async_task():
    """Short asynchronous task that takes about 0.5 seconds."""
    await asyncio.sleep(0.5)
    return "Short async task completed"

async def medium_async_task():
    """Medium asynchronous task that takes about 2 seconds."""
    await asyncio.sleep(2)
    return "Medium async task completed"

async def long_async_task():
    """Long asynchronous task that takes about 5 seconds."""
    await asyncio.sleep(5)
    return "Long async task completed"

async def error_async_task():
    """Asynchronous task that raises an error."""
    await asyncio.sleep(0.1)
    raise ValueError("Simulated error in async task")