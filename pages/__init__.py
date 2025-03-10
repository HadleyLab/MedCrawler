"""Pages package for the Medical Literature Assistant app."""
from .home import create_home_page
from .notifications import create_notifications_page
from .search import create_search_page

__all__ = ['create_home_page', 'create_notifications_page', 'create_search_page']