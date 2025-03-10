"""Tests for task execution."""
import pytest
import asyncio
from backend.utils import tasks

# Test synchronous tasks
def test_short_task():
    result = tasks.short_task()
    assert result == "Short task completed"

def test_medium_task():
    result = tasks.medium_task()
    assert result == "Medium task completed"

def test_long_task():
    result = tasks.long_task()
    assert result == "Long task completed"

def test_error_task():
    with pytest.raises(ValueError) as exc_info:
        tasks.error_task()
    assert str(exc_info.value) == "Simulated error in task"

# Test asynchronous tasks
@pytest.mark.asyncio
async def test_short_async_task():
    result = await tasks.short_async_task()
    assert result == "Short async task completed"

@pytest.mark.asyncio
async def test_medium_async_task():
    result = await tasks.medium_async_task()
    assert result == "Medium async task completed"

@pytest.mark.asyncio
async def test_long_async_task():
    result = await tasks.long_async_task()
    assert result == "Long async task completed"

@pytest.mark.asyncio
async def test_error_async_task():
    with pytest.raises(ValueError) as exc_info:
        await tasks.error_async_task()
    assert str(exc_info.value) == "Simulated error in async task"

# Test task execution times
@pytest.mark.parametrize("task,expected_min_time", [
    (tasks.short_task, 0.4),
    (tasks.medium_task, 1.9),
    (tasks.long_task, 4.9)
])
def test_sync_task_duration(task, expected_min_time):
    import time
    start_time = time.time()
    task()
    duration = time.time() - start_time
    assert duration >= expected_min_time

@pytest.mark.asyncio
@pytest.mark.parametrize("task,expected_min_time", [
    (tasks.short_async_task, 0.4),
    (tasks.medium_async_task, 1.9),
    (tasks.long_async_task, 4.9)
])
async def test_async_task_duration(task, expected_min_time):
    import time
    start_time = time.time()
    await task()
    duration = time.time() - start_time
    assert duration >= expected_min_time