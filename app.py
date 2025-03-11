"""Medical Literature Assistant main application."""
import asyncio
import logging
from nicegui import ui
from backend.utils.notification_manager import NotificationManager
from config import APP_NAME, LOGGING_CONFIG
from pages import create_home_page, create_notifications_page, create_search_page

# Initialize logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Initialize managers
notification_manager = NotificationManager()

def create_navigation():
    """Create navigation drawer with menu items."""
    drawer = ui.left_drawer().classes('bg-blue-50').props('bordered')
    with drawer:
        ui.button('Home', on_click=lambda: ui.navigate.to('/'), icon='home').props('flat')
        ui.button('Notifications', on_click=lambda: ui.navigate.to('/notifications'), icon='notifications').props('flat')
        ui.button('Literature Search', on_click=lambda: ui.navigate.to('/search'), icon='search').props('flat')
    return drawer

def create_header(drawer):
    """Create consistent header with navigation toggle."""
    with ui.header().classes('bg-primary text-white items-center justify-between'):
        with ui.row().classes('w-full items-center'):
            ui.button(on_click=lambda: drawer.toggle(), icon='menu').props('flat color=white')
            ui.label(APP_NAME).classes('text-h6 q-ml-md')

def create_layout():
    """Create main layout with header, navigation, and content area."""
    drawer = create_navigation()
    create_header(drawer)

async def run_task(task, title, success_msg, error_msg):
    """Run a task with notification feedback."""
    try:
        result = await notification_manager.notify_task(
            task=task,
            title=title,
            success_message=success_msg,
            error_message=error_msg
        )
        return result
    except Exception as e:
        logger.exception(f"Task execution failed: {title} - {str(e)}")
        return None

@ui.page('/')
def home_page():
    """Home page route."""
    create_layout()
    with ui.column().classes('w-full max-w-3xl mx-auto p-4'):
        create_home_page()

@ui.page('/notifications')
def notifications_page():
    """Notifications demo page route."""
    create_layout()
    with ui.column().classes('w-full max-w-3xl mx-auto p-4'):
        create_notifications_page(run_task)

@ui.page('/search')
def search_page():
    """Literature search page route."""
    create_layout()
    with ui.column().classes('w-full max-w-3xl mx-auto p-4'):
        create_search_page(run_task)

if __name__ in {"__main__", "__mp_main__"}:
    logger.info(f"Starting {APP_NAME}")
    ui.run(title=APP_NAME)
