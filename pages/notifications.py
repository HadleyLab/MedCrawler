"""Notifications demo page for testing notification system."""
from nicegui import ui
from backend.utils import tasks
import logging

logger = logging.getLogger(__name__)

def create_notifications_page(run_task):
    """Create the notifications demo page content."""
    with ui.card().classes('w-full p-4'):
        ui.label('Notifications Demo').classes('text-h5 q-mb-md')
        
        with ui.tabs().classes('q-mb-md') as tabs:
            ui.tab('sync', 'Sync Tasks')
            ui.tab('async', 'Async Tasks')
            ui.tab('custom', 'Custom Notifications')
            
        with ui.tab_panels(tabs, value='sync').classes('w-full'):
            with ui.tab_panel('sync'):
                with ui.grid(columns=3).classes('gap-4'):
                    task_infos = [
                        ('Short Task', tasks.short_task, 'Quick synchronous task'),
                        ('Medium Task', tasks.medium_task, 'Medium-length synchronous task'),
                        ('Long Task', tasks.long_task, 'Long-running synchronous task'),
                        ('Error Task', tasks.error_task, 'Task that generates an error')
                    ]
                    for name, task_fn, tooltip_text in task_infos:
                        button = ui.button(
                            name,
                            on_click=lambda t=task_fn, n=name: run_task(
                                t,
                                f'{n}',
                                f'{n} completed!',
                                f'{n} failed!'
                            )
                        ).props('outline')
                        button.tooltip(tooltip_text)
                        
            with ui.tab_panel('async'):
                with ui.grid(columns=3).classes('gap-4'):
                    task_infos = [
                        ('Short Async', tasks.short_async_task(), 'Quick asynchronous task'),
                        ('Medium Async', tasks.medium_async_task(), 'Medium-length asynchronous task'),
                        ('Long Async', tasks.long_async_task(), 'Long-running asynchronous task'),
                        ('Error Async', tasks.error_async_task(), 'Async task that generates an error')
                    ]
                    for name, task_fn, tooltip_text in task_infos:
                        button = ui.button(
                            name,
                            on_click=lambda t=task_fn, n=name: run_task(
                                t,
                                f'{n}',
                                f'{n} completed!',
                                f'{n} failed!'
                            )
                        ).props('outline color=primary')
                        button.tooltip(tooltip_text)
                        
            with ui.tab_panel('custom'):
                with ui.column().classes('w-full gap-4'):
                    ui.markdown('''
                    ### Custom Notification Examples
                    Click the buttons below to see different notification styles with custom actions and behaviors.
                    ''')
                    
                    with ui.grid(columns=2).classes('gap-4'):
                        ui.button(
                            'Info with Actions',
                            on_click=lambda: run_task(
                                lambda: "Info notification demo",
                                'Info Demo',
                                'This is an info notification with custom actions!',
                                'Info demo failed',
                            )
                        ).props('outline color=info')
                        
                        ui.button(
                            'Warning with Details',
                            on_click=lambda: run_task(
                                lambda: "Warning notification demo",
                                'Warning Demo',
                                'This is a warning notification with details!',
                                'Warning demo failed',
                            )
                        ).props('outline color=warning')
                        
                        ui.button(
                            'Success with Icon',
                            on_click=lambda: run_task(
                                lambda: "Success notification demo",
                                'Success Demo',
                                'Operation completed successfully!',
                                'Success demo failed',
                            )
                        ).props('outline color=positive')
                        
                        ui.button(
                            'Error with Details',
                            on_click=lambda: run_task(
                                tasks.error_task,
                                'Error Demo',
                                'This should not appear',
                                'Error occurred during demo',
                            )
                        ).props('outline color=negative')