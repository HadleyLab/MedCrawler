"""Test suite for notification manager."""
import asyncio
import pytest
from config import NOTIFICATION_DEFAULTS

def mock_sync_task():
    """Mock successful sync task."""
    return "Success"

def mock_error_task():
    """Mock failing sync task."""
    raise ValueError("Test error")

async def mock_async_success():
    """Mock successful async task."""
    await asyncio.sleep(0.1)
    return "Async Success"

async def mock_async_error():
    """Mock failing async task."""
    await asyncio.sleep(0.1)
    raise ValueError("Async error")

@pytest.mark.asyncio
async def test_notify_basic(notification_manager):
    """Test basic notification functionality."""
    await notification_manager.notify(
        "Test",
        "Test message",
        type="info"
    )
    
    notifications = notification_manager._test_notifications
    assert len(notifications) == 1
    assert notifications[0]["message"] == "Test message"
    assert notifications[0]["type"] == "info"
    assert notifications[0]["dismissible"] is True

@pytest.mark.asyncio
async def test_notify_with_actions(notification_manager):
    """Test notification with custom actions."""
    actions = [
        {"label": "Test", "handler": lambda: None}
    ]
    await notification_manager.notify(
        "Test",
        "Test message",
        type="info",
        actions=actions
    )
    
    notifications = notification_manager._test_notifications
    assert len(notifications) == 1
    assert "actions" in notifications[0]
    assert len(notifications[0]["actions"]) > 1  # Include dismiss + custom actions

@pytest.mark.asyncio
async def test_notify_non_dismissible(notification_manager):
    """Test non-dismissible notification."""
    await notification_manager.notify(
        "Test",
        "Test message",
        type="info",
        dismissible=False
    )
    
    notifications = notification_manager._test_notifications
    assert len(notifications) == 1
    assert notifications[0]["dismissible"] is False

@pytest.mark.asyncio
async def test_notify_successful_sync_task(notification_manager):
    """Test notification for successful sync task."""
    await notification_manager.notify_task(
        mock_sync_task,
        "Test Task",
        "Task completed",
        "Task failed"
    )
    
    notifications = notification_manager._test_notifications
    assert len(notifications) == 2  # Initial + Success notification
    
    # Check initial notification
    assert notifications[0]["type"] == "ongoing"
    assert notifications[0]["message"] == "Test Task in progress..."
    assert notifications[0]["dismissible"] is False
    assert notifications[0]["spinner"] is True
    
    # Check success notification
    assert notifications[1]["type"] == "positive"
    assert notifications[1]["message"] == "Task completed"
    assert "icon" in notifications[1]

@pytest.mark.asyncio
async def test_notify_failed_sync_task(notification_manager):
    """Test notification for failed sync task."""
    with pytest.raises(ValueError, match="Test error"):
        await notification_manager.notify_task(
            mock_error_task,
            "Error Task",
            "Should not see this",
            "Task failed"
        )
    
    notifications = notification_manager._test_notifications
    assert len(notifications) == 2  # Initial + Error notification
    
    # Check initial notification
    assert notifications[0]["type"] == "ongoing"
    assert notifications[0]["message"] == "Error Task in progress..."
    
    # Check error notification
    assert notifications[1]["type"] == "negative"
    assert "Task failed: Test error" in notifications[1]["message"]
    assert "icon" in notifications[1]
    assert "actions" in notifications[1]

@pytest.mark.asyncio
async def test_notify_successful_async_task(notification_manager):
    """Test notification for successful async task."""
    await notification_manager.notify_task(
        mock_async_success(),
        "Async Test",
        "Async completed",
        "Async failed"
    )
    
    notifications = notification_manager._test_notifications
    assert len(notifications) == 2
    
    # Check initial notification
    assert notifications[0]["type"] == "ongoing"
    assert notifications[0]["message"] == "Async Test in progress..."
    assert notifications[0]["spinner"] is True
    
    # Check success notification
    assert notifications[1]["type"] == "positive"
    assert notifications[1]["message"] == "Async completed"
    assert "icon" in notifications[1]

@pytest.mark.asyncio
async def test_notify_failed_async_task(notification_manager):
    """Test notification for failed async task."""
    with pytest.raises(ValueError, match="Async error"):
        await notification_manager.notify_task(
            mock_async_error(),
            "Async Error",
            "Should not see this",
            "Async failed"
        )
    
    notifications = notification_manager._test_notifications
    assert len(notifications) == 2
    
    # Check initial notification
    assert notifications[0]["type"] == "ongoing"
    assert notifications[0]["message"] == "Async Error in progress..."
    
    # Check error notification
    assert notifications[1]["type"] == "negative"
    assert "Async failed: Async error" in notifications[1]["message"]
    assert "icon" in notifications[1]
    assert "actions" in notifications[1]

@pytest.mark.asyncio
async def test_notification_position(notification_manager):
    """Test notification position setting."""
    await notification_manager.notify(
        "Test",
        "Test message"
    )
    
    notifications = notification_manager._test_notifications
    assert len(notifications) > 0
    assert notifications[0]["position"] == NOTIFICATION_DEFAULTS["position"]

@pytest.mark.asyncio
async def test_notification_cleanup(notification_manager):
    """Test notification cleanup."""
    await notification_manager.notify(
        "Test",
        "Test message",
        type="ongoing"
    )
    
    assert len(notification_manager._ongoing_notifications) > 0
    notification_manager.cleanup()
    assert len(notification_manager._ongoing_notifications) == 0
    assert len(notification_manager._test_notifications) == 0

@pytest.mark.asyncio
async def test_multiple_ongoing_notifications(notification_manager):
    """Test handling multiple ongoing notifications."""
    # Create multiple ongoing notifications
    for i in range(3):
        await notification_manager.notify(
            f"Test {i}",
            f"Message {i}",
            type="ongoing"
        )
    
    assert len(notification_manager._ongoing_notifications) == 3
    notification_manager._dismiss_all_ongoing()
    assert len(notification_manager._ongoing_notifications) == 0