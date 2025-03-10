"""Test fixtures for Medical Literature Assistant."""
import asyncio
import pytest
from nicegui import ui
from backend.utils.notification_manager import NotificationManager

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def notification_manager(mock_ui_notification):
    """Fixture to provide a clean NotificationManager instance for each test."""
    manager = NotificationManager()
    manager.enable_test_mode()
    yield manager
    # Ensure cleanup happens before the event loop is closed
    await asyncio.sleep(0)  # Allow pending tasks to complete
    manager.cleanup()

@pytest.fixture
def mock_ui_notification(monkeypatch):
    """Mock ui.notification to track notifications during tests."""
    notifications = []
    
    def mock_notification(*args, **kwargs):
        notification = type('MockNotification', (), {
            'dismiss': lambda: None,
            'props': kwargs,
            'message': kwargs.get('message', ''),
            'type': kwargs.get('type', None)
        })
        notifications.append(notification)
        return notification
    
    monkeypatch.setattr(ui, 'notification', mock_notification)
    return notifications

@pytest.fixture
def async_client():
    """Fixture for async test client if needed."""
    from nicegui import Client
    return Client()