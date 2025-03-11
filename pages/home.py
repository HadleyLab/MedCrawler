"""
Home page for the Medical Literature Assistant.

This module provides the welcome screen and overview of the application,
explaining its features and guiding users on how to navigate the application.
"""
import logging
from nicegui import ui

logger = logging.getLogger(__name__)

def create_home_page():
    """
    Create the home page content with application overview and feature explanations.
    
    Displays a welcome message, explains what the application does, and guides
    users on how to navigate to different features.
    """
    logger.debug("Creating home page")
    
    with ui.card().classes('w-full p-6'):
        ui.label('Welcome to Medical Literature Assistant').classes('text-h4 text-center q-mb-md')
        
        with ui.column().classes('w-full items-center q-mb-lg'):
            ui.label(
                'A centralized platform for searching and monitoring medical literature'
            ).classes('text-h6 text-center')
        
        # Application description
        with ui.card().classes('q-mb-md bg-blue-1'):
            with ui.column().classes('q-pa-md'):
                ui.markdown("""
                ### About This Application
                
                Medical Literature Assistant helps healthcare professionals and researchers stay
                updated with the latest medical literature by providing a unified interface to
                search across multiple medical databases including PubMed and ClinicalTrials.gov.
                """).classes('q-mb-md')

        # Feature cards section
        ui.label('Available Features').classes('text-h5 q-mb-md')
        
        with ui.grid(columns=2).classes('q-col-gutter-md'):
            # Literature Search Feature Card
            with ui.card().classes('col-span-1'):
                with ui.card_section().classes('bg-primary text-white'):
                    ui.label('Literature Search').classes('text-h6')
                
                with ui.card_section():
                    ui.markdown("""
                    Search across PubMed and ClinicalTrials.gov with a single query.
                    Filter by date range and view results in a unified interface.
                    
                    **Key Features:**
                    - Combined search across multiple sources
                    - Year-based filtering
                    - Tabbed results view
                    """)
                    
                with ui.card_actions().classes('justify-end'):
                    ui.button(
                        'Go to Search',
                        on_click=lambda: ui.navigate.to('/search')
                    ).props('color=primary flat')
            
            # Notifications Demo Feature Card
            with ui.card().classes('col-span-1'):
                with ui.card_section().classes('bg-secondary text-white'):
                    ui.label('Notifications System').classes('text-h6')
                
                with ui.card_section():
                    ui.markdown("""
                    Explore the notification system that provides real-time feedback
                    for both synchronous and asynchronous tasks.
                    
                    **Key Features:**
                    - Progress tracking for long-running tasks
                    - Error handling with detailed feedback
                    - Multiple notification styles and behaviors
                    """)
                    
                with ui.card_actions().classes('justify-end'):
                    ui.button(
                        'Try Notifications',
                        on_click=lambda: ui.navigate.to('/notifications')
                    ).props('color=secondary flat')
        
        # Navigation help
        with ui.expansion('Navigation Help', icon='help').classes('q-mt-lg'):
            ui.markdown("""
            ### Getting Started
            
            1. Use the menu button (☰) in the top-left corner to open the navigation drawer
            2. Select a feature to navigate to that section
            3. Each feature provides its own instructions and controls
            
            ### Need Help?
            
            - Informative notifications will guide you through each process
            - Error messages include detailed explanations when something goes wrong
            - Progress indicators show real-time status for longer operations
            """)
            
    logger.debug("Home page created successfully")