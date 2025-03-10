"""Notification manager for consistent notification handling."""
import asyncio
import inspect
import logging
from typing import Any, Callable, Coroutine, Optional, Union, List, Dict
from nicegui import ui
from config import NOTIFICATION_DEFAULTS

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages notifications throughout the application."""
    
    def __init__(self):
        self._test_mode = False
        self._test_notifications = []

    def enable_test_mode(self):
        self._test_mode = True
        self._test_notifications = []
        
    def cleanup(self):
        self._test_notifications = []

    async def notify(
        self,
        title: str,
        message: str,
        type: str = "info",
        timeout: Optional[int] = None,
        **kwargs
    ) -> Any:
        if self._test_mode:
            self._test_notifications.append({
                "title": title,
                "message": message,
                "type": type,
                "timeout": timeout,
                **kwargs
            })
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
            return ui.notify(
                message=f"{title}: {message}" if title else message,
                position=NOTIFICATION_DEFAULTS["position"],
                type=type,
                spinner=bool(kwargs.get("spinner", False)),
                timeout=timeout,
                actions=actions if actions else None,
                dismissible=True if type == "negative" else kwargs.get("dismissible", None),
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
        try:
            # Show in-progress notification with queue=False to show immediately
            ui.notify(
                message=f"{title}: In progress...",
                position=NOTIFICATION_DEFAULTS["position"],
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
                    result = await task
                else:
                    result = await task()
            else:
                # Handle regular function
                result = await asyncio.get_event_loop().run_in_executor(None, task)

            # Show success notification with queue=True to wait for in-progress to clear
            ui.notify(
                message=f"{title}: {success_message}",
                position=NOTIFICATION_DEFAULTS["position"],
                color="positive",
                timeout=NOTIFICATION_DEFAULTS.get("timeout", 5000),
                force=True,  # Force immediate display
                queue=True   # Queue this notification
            )

            return result

        except Exception as e:
            # Show error notification with dismiss button
            ui.notify(
                message=f"{title}: {error_message}: {str(e)}",
                position=NOTIFICATION_DEFAULTS["position"],
                color="negative",
                timeout=0,
                dismissible=True,
                actions=[{
                    "label": "Dismiss",
                    "color": "white",
                    "flat": True,
                    "icon": "close"
                }],
                force=True,  # Force immediate display
                queue=True   # Queue this notification
            )
            logger.error(f"Task failed: {str(e)}", exc_info=True)
            raise