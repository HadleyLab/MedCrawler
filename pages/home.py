"""Home page for the Medical Literature Assistant."""
from nicegui import ui

def create_home_page():
    """Create the home page content."""
    with ui.card().classes('w-full p-4'):
        ui.label('Welcome to Medical Literature Assistant').classes('text-h4 text-center q-mb-lg')
        ui.label('Choose a feature from the navigation menu to get started').classes('text-body1 text-center')