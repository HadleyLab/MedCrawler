"""
Notifications demo page for testing notification system.

This module provides a demo interface for testing different notification
types and behaviors with both synchronous and asynchronous tasks.
"""
import logging
from nicegui import ui

from backend.utils import tasks

logger = logging.getLogger(__name__)


def create_notifications_page(run_task):
    """
    Create the notifications demo page content.
    
    Args:
        run_task: Function to execute tasks with notification feedback
    """
    logger.debug("Creating notifications demo page")
    
    with ui.card().classes('w-full p-4'):
        ui.label('Notifications Demo').classes('text-h5 q-mb-md')
        ui.markdown("""
        This page demonstrates the notification system with various task types.
        Click on the buttons to see different notification behaviors.
        """).classes('q-mb-md')
        
        with ui.tabs().classes('q-mb-md') as tabs:
            ui.tab('sync', 'Synchronous Tasks')
            ui.tab('async', 'Asynchronous Tasks')
            ui.tab('custom', 'Custom Notifications')
            
        with ui.tab_panels(tabs, value='sync').classes('w-full'):
            # Synchronous Tasks Panel
            with ui.tab_panel('sync'):
                ui.markdown("""
                ### Synchronous Tasks
                These tasks run in a thread pool and block until completion.
                """).classes('q-mb-sm')
                
                with ui.grid(columns=3).classes('gap-4'):
                    task_infos = [
                        ('Short Task (0.5s)', tasks.short_task, 'Quick synchronous task (0.5 seconds)'),
                        ('Medium Task (2s)', tasks.medium_task, 'Medium-length synchronous task (2 seconds)'),
                        ('Long Task (5s)', tasks.long_task, 'Long-running synchronous task (5 seconds)'),
                        ('Error Task', tasks.error_task, 'Task that generates an error for testing error handling')
                    ]
                    
                    for name, task_fn, tooltip_text in task_infos:
                        button = ui.button(
                            name,
                            on_click=lambda t=task_fn, n=name: run_task(
                                t,
                                n.split(' ')[0] + ' Task',  # Use first word as notification title
                                f'{n} completed successfully!',
                                f'{n} failed!'
                            )
                        ).props('outline color=primary').classes('w-full')
                        button.tooltip(tooltip_text)
            
            # Asynchronous Tasks Panel            
            with ui.tab_panel('async'):
                ui.markdown("""
                ### Asynchronous Tasks
                These tasks use Python's asyncio and don't block the main thread.
                """).classes('q-mb-sm')
                
                with ui.grid(columns=3).classes('gap-4'):
                    task_infos = [
                        ('Short Async (0.5s)', tasks.short_async_task(), 'Quick asynchronous task (0.5 seconds)'),
                        ('Medium Async (2s)', tasks.medium_async_task(), 'Medium-length asynchronous task (2 seconds)'),
                        ('Long Async (5s)', tasks.long_async_task(), 'Long-running asynchronous task (5 seconds)'),
                        ('Error Async', tasks.error_async_task(), 'Async task that generates an error for testing error handling')
                    ]
                    
                    for name, task_fn, tooltip_text in task_infos:
                        button = ui.button(
                            name,
                            on_click=lambda t=task_fn, n=name: run_task(
                                t,
                                n.split(' ')[0] + ' Task',  # Use first word as notification title
                                f'{n} completed successfully!',
                                f'{n} failed!'
                            )
                        ).props('outline color=secondary').classes('w-full')
                        button.tooltip(tooltip_text)
            
            # Custom Notifications Panel            
            with ui.tab_panel('custom'):
                with ui.column().classes('w-full gap-4'):
                    ui.markdown("""
                    ### Custom Notification Examples
                    Click the buttons below to see different notification styles with custom actions and behaviors.
                    """).classes('q-mb-sm')
                    
                    with ui.grid(columns=2).classes('gap-4'):
                        ui.button(
                            'Info with Actions',
                            on_click=lambda: run_task(
                                lambda: "Info notification demo",
                                'Info Notification',
                                'This is an info notification with custom actions!',
                                'Info notification demo failed',
                            )
                        ).props('outline color=info').classes('w-full')
                        
                        ui.button(
                            'Warning with Details',
                            on_click=lambda: run_task(
                                lambda: "Warning notification demo",
                                'Warning Notification',
                                'This is a warning notification with details!',
                                'Warning notification demo failed',
                            )
                        ).props('outline color=warning').classes('w-full')
                        
                        ui.button(
                            'Success with Icon',
                            on_click=lambda: run_task(
                                lambda: "Success notification demo",
                                'Success Notification',
                                'Operation completed successfully!',
                                'Success notification demo failed',
                            )
                        ).props('outline color=positive').classes('w-full')
                        
                        ui.button(
                            'Error with Details',
                            on_click=lambda: run_task(
                                tasks.error_task,
                                'Error Notification',
                                'This should not appear',
                                'Error occurred during demonstration',
                            )
                        ).props('outline color=negative').classes('w-full')
    
    logger.debug("Notifications demo page created")