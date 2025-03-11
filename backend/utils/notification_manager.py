"""
Notification manager for consistent notification handling.

This module provides a centralized notification system for presenting
status updates, errors, and other user notifications throughout the application.
"""
import asyncio
import inspect
import logging
from typing import Any, Callable, Coroutine, Optional, Union, List, Dict

from nicegui import ui

from config import NOTIFICATION_DEFAULTS

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages notifications throughout the application.
    
    This class provides a consistent interface for sending notifications to users,
    handling notification queuing, and managing task progress updates.
    """
    
    def __init__(self):
        """Initialize the notification manager."""
        self._test_mode = False
        self._test_notifications = []
        logger.debug("NotificationManager initialized")
    
    def enable_test_mode(self):
        """Enable test mode to capture notifications for testing."""
        self._test_mode = True
        self._test_notifications = []
        logger.debug("NotificationManager test mode enabled")
        
    def disable_test_mode(self):
        """Disable test mode."""
        self._test_mode = False
        logger.debug("NotificationManager test mode disabled")
        
    def cleanup(self):
        """Clear any stored test notifications."""
        self._test_notifications = []
    
    def get_test_notifications(self) -> List[Dict]:
        """
        Get all notifications sent while in test mode.
        
        Returns:
            List of notification dictionaries
        """
        return self._test_notifications

    async def notify(
        self,
        title: str,
        message: str,
        type: str = "info",
        timeout: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Send a notification to the user.
        
        Args:
            title: The notification title
            message: The notification message body
            type: Notification type (info, positive, negative, warning)
            timeout: Timeout in milliseconds (0 for no timeout)
            **kwargs: Additional notification parameters
            
        Returns:
            Notification object or None if in test mode
        """
        if self._test_mode:
            notification_data = {
                "title": title,
                "message": message,
                "type": type,
                "timeout": timeout,
                **kwargs
            }
            self._test_notifications.append(notification_data)
            logger.debug(f"Test mode notification: {notification_data}")
            return None
            
        # Set timeout - error notifications get dismiss button instead of timeout
        if timeout is None:
            timeout = 0 if type == "negative" else NOTIFICATION_DEFAULTS.get("timeout", 5000)
            
        # For error notifications, ensure they're dismissible and have a dismiss action
        actions: List[Dict] = kwargs.pop("actions", [])
        if type == "negative":
            # Add dismiss button as first action for errors
            actions.insert(0, {
                "label": "Dismiss",
                "color": "white",
                "flat": True,
                "icon": "close"
            })
        
        try:
            logger.debug(f"Sending notification: {title}: {message}")
            return ui.notify(
                message=f"{title}: {message}" if title else message,
                position=NOTIFICATION_DEFAULTS.get("position", "top-right"),
                type=type,
                spinner=bool(kwargs.get("spinner", False)),
                timeout=timeout,
                actions=actions if actions else None,
                dismissible=True if type == "negative" else kwargs.get("dismissible", 
                                                           NOTIFICATION_DEFAULTS.get("dismissible", False)),
                **{k:v for k,v in kwargs.items() if k not in ["spinner", "type", "actions", "dismissible"]}
            )
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return None

    async def notify_task(
        self,
        task: Union[Callable, Coroutine],
        title: str,
        success_message: str,
        error_message: str,
        **kwargs
    ) -> Any:
        """
        Run a task with progress notifications.
        
        This method shows an in-progress notification while the task runs,
        then shows a success or error notification based on the outcome.
        
        Args:
            task: The function or coroutine to execute
            title: Task title for notifications
            success_message: Message to show on success
            error_message: Message to show on error
            **kwargs: Additional notification parameters
            
        Returns:
            The result of the task execution
            
        Raises:
            Exception: If the task raises an exception
        """
        try:
            # Show in-progress notification with queue=False to show immediately
            logger.debug(f"Starting task: {title}")
            ui.notify(
                message=f"{title}: In progress...",
                position=NOTIFICATION_DEFAULTS.get("position", "top-right"),
                color="grey-7",
                spinner=True,
                timeout=50,  # Minimum visible timeout
                force=True,  # Force immediate display
                queue=False  # Don't queue this notification
            )
            
            # Execute task based on its type
            if asyncio.iscoroutine(task) or inspect.iscoroutinefunction(task):
                # Handle coroutine or async function
                if asyncio.iscoroutine(task):
                    logger.debug(f"Executing coroutine task: {title}")
                    result = await task
                else:
                    logger.debug(f"Executing async function task: {title}")
                    result = await task()
            else:
                # Handle regular function
                logger.debug(f"Executing sync function task: {title}")
                result = await asyncio.get_event_loop().run_in_executor(None, task)
                
            # Show success notification with queue=True to wait for in-progress to clear
            logger.debug(f"Task completed successfully: {title}")
            await self.notify(
                title=title,
                message=success_message,
                type="positive",
                timeout=NOTIFICATION_DEFAULTS.get("timeout", 5000),
                force=True,  # Force immediate display
                queue=True   # Queue this notification
            )
            return result
            
        except Exception as e:
            # Show error notification with dismiss button
            logger.error(f"Task failed: {title} - {str(e)}", exc_info=True)
            await self.notify(
                title=title,
                message=f"{error_message}: {str(e)}",
                type="negative",
                timeout=0,
                dismissible=True,
                force=True,  # Force immediate display
                queue=True   # Queue this notification
            )
            raise