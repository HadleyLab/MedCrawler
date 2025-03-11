"""Literature search page for querying medical databases."""
import asyncio
import logging
from datetime import datetime
from nicegui import ui
from backend.crawlers import PubMedCrawler, ClinicalTrialsCrawler
from config import DEFAULT_CRAWLER_CONFIG

logger = logging.getLogger(__name__)

def create_search_page(notification_manager):
    """Create the literature search page content."""
    page_container = ui.column().classes('w-full max-w-3xl mx-auto')
    
    with page_container:
        with ui.card().classes('w-full p-4'):
            ui.label('Medical Literature Search').classes('text-h5 q-mb-md')
            
            with ui.column().classes('w-full gap-4'):
                # Search input and button
                with ui.row().classes('w-full items-center gap-2'):
                    search_input = ui.input(
                        placeholder='Enter search terms...'
                    ).props('outlined clearable').classes('flex-grow')
                    
                    search_button = ui.button(
                        'Search',
                        on_click=lambda: asyncio.create_task(_handle_search(
                            search_input, search_button, results_container, 
                            notification_manager, page_container,
                            [year_from.value, year_to.value], pubmed_check.value, trials_check.value
                        ))
                    ).props('color=primary icon=search')
                
                # Source selection
                with ui.row().classes('w-full items-center gap-4'):
                    ui.label('Sources:').classes('text-subtitle1')
                    pubmed_check = ui.checkbox('PubMed', value=True)
                    trials_check = ui.checkbox('Clinical Trials', value=True)
                
                # Year range inputs
                with ui.column().classes('w-full gap-2'):
                    ui.label('Publication Year Range:').classes('text-subtitle1')
                    current_year = datetime.now().year
                    with ui.row().classes('w-full items-center gap-4'):
                        year_from = ui.number(
                            label='From Year',
                            value=current_year - 5,
                            min=1900,
                            max=current_year
                        ).props('outlined')
                        year_to = ui.number(
                            label='To Year',
                            value=current_year,
                            min=1900,
                            max=current_year
                        ).props('outlined')
                
                search_input.on('keydown.enter', lambda: asyncio.create_task(_handle_search(
                    search_input, search_button, results_container,
                    notification_manager, page_container,
                    [year_from.value, year_to.value], pubmed_check.value, trials_check.value
                )))
            
            results_container = ui.element('div').classes('w-full mt-4')

async def _handle_search(search_input, search_button, results_container, 
                        notification_manager, page_container, 
                        year_range, include_pubmed, include_trials):
    """Handle the search operation with proper UI context."""
    query = search_input.value.strip()
    if not query:
        with page_container:
            await notification_manager.notify(
                "Search Error",
                "Please enter a search query",
                type="warning",
                icon="warning",
                dismissible=True
            )
        return
    
    if not include_pubmed and not include_trials:
        with page_container:
            await notification_manager.notify(
                "Search Error",
                "Please select at least one source to search",
                type="warning",
                icon="warning",
                dismissible=True
            )
        return

    try:
        search_button.props('loading disable')
        
        # Year range slider returns a list of [from_year, to_year]
        year_from = year_range[0]
        year_to = year_range[1]
        
        with page_container:
            # Start search notification
            await notification_manager.notify_task(
                _execute_search(
                    query=query,
                    notification_manager=notification_manager,
                    results_container=results_container,
                    page_container=page_container,
                    year_from=year_from,
                    year_to=year_to,
                    include_pubmed=include_pubmed,
                    include_trials=include_trials
                ),
                "Literature Search",
                f'Found results for "{query}"',
                f'Search failed for "{query}"'
            )
            
    except Exception as e:
        logger.exception("Search error")
        with page_container:
            await notification_manager.notify(
                "Search Error",
                f"An error occurred: {str(e)}",
                type="negative",
                icon="error",
                actions=[
                    {"label": "Dismiss", "color": "white", "flat": True}
                ]
            )
    finally:
        search_button.props('loading- disable-')

async def _execute_search(query: str, notification_manager, results_container, page_container,
                         year_from: int, year_to: int, include_pubmed: bool, include_trials: bool):
    """Execute the search operation across selected sources."""
    results_container.clear()
    total_results = 0
    
    with results_container:
        with ui.tabs().classes('w-full') as results_tabs:
            if include_pubmed:
                ui.tab('pubmed', 'PubMed')
            if include_trials:
                ui.tab('trials', 'Clinical Trials')
            
        with ui.tab_panels(results_tabs, value='pubmed' if include_pubmed else 'trials').classes('w-full'):
            if include_pubmed:
                pubmed_count = await _create_pubmed_panel(
                    query, notification_manager, page_container,
                    year_from=year_from, year_to=year_to
                )
                total_results += pubmed_count
                
            if include_trials:
                trials_count = await _create_trials_panel(
                    query, notification_manager, page_container,
                    year_from=year_from, year_to=year_to
                )
                total_results += trials_count
            
    return total_results

async def _fetch_pubmed_results(crawler, query, year_from, year_to):
    """Fetch PubMed results with proper notification handling."""
    # Add year range to query
    date_query = f"{query} AND {year_from}:{year_to}[dp]"
    
    # First collect the IDs
    pmids = []
    async for pmid in crawler.search(date_query, max_results=5):
        pmids.append(pmid)
        
    if not pmids:
        return []
        
    # Then fetch all articles in parallel
    return await crawler.get_items_batch(pmids)

async def _create_pubmed_panel(query: str, notification_manager, page_container, year_from: int, year_to: int) -> int:
    """Create PubMed results panel and return result count."""
    with ui.tab_panel('pubmed'):
        with ui.card().classes('w-full q-ma-sm'):
            try:
                async with PubMedCrawler(notification_manager, DEFAULT_CRAWLER_CONFIG) as crawler:
                    with page_container:
                        results = await notification_manager.notify_task(
                            _fetch_pubmed_results(crawler, query, year_from, year_to),
                            "PubMed Search",
                            f"Found PubMed results",
                            "PubMed search failed",
                            spinner=True,
                            icon="search"
                        )
                    
                    if not results:
                        ui.label('No PubMed results found').classes('text-subtitle1 text-grey')
                        return 0
                    
                    # Display results
                    for article in results:
                        with ui.card().classes('w-full q-ma-sm q-pa-md'):
                            ui.link(
                                article['title'],
                                f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}"
                            ).classes('text-subtitle1 font-bold text-primary')
                            ui.markdown(f"**Authors:** {', '.join(article['authors'])}").classes('text-caption')
                            if 'pubdate' in article:
                                ui.markdown(f"**Published:** {article['pubdate']}").classes('text-caption')
                            if 'journal' in article:
                                ui.markdown(f"**Journal:** {article['journal']}").classes('text-caption')
                            if 'doi' in article and article['doi']:
                                ui.markdown(f"**DOI:** {article['doi']}").classes('text-caption')
                            with ui.expansion('Abstract', icon='description'):
                                ui.markdown(article['abstract']).classes('text-body2')
                                
                    return len(results)
                    
            except Exception as e:
                logger.exception("PubMed search error")
                with page_container:
                    await notification_manager.notify(
                        "PubMed Error",
                        str(e),
                        type="negative",
                        icon="error",
                        dismissible=True
                    )
                raise

async def _fetch_trials_results(crawler, query, year_from, year_to):
    """Fetch Clinical Trials results with proper notification handling."""
    # Format the date range according to ClinicalTrials.gov API requirements
    # Use study start date for filtering with proper +AREA syntax
    date_query = f"{query} AREA[LastUpdatePostDate]RANGE[{year_from}-01-01,{year_to}-12-31]"
    # First collect the IDs
    nctids = []
    async for nctid in crawler.search(date_query, max_results=5):
        nctids.append(nctid)
        
    if not nctids:
        return []
        
    # Then fetch all trials in parallel
    return await crawler.get_items_batch(nctids)

async def _create_trials_panel(query: str, notification_manager, page_container, year_from: int, year_to: int) -> int:
    """Create Clinical Trials results panel and return result count."""
    with ui.tab_panel('trials'):
        with ui.card().classes('w-full q-ma-sm'):
            try:
                async with ClinicalTrialsCrawler(notification_manager, DEFAULT_CRAWLER_CONFIG) as crawler:
                    with page_container:
                        results = await notification_manager.notify_task(
                            _fetch_trials_results(crawler, query, year_from, year_to),
                            "Clinical Trials Search",
                            "Found clinical trials results",
                            "Clinical trials search failed",
                            spinner=True,
                            icon="search"
                        )
                    
                    if not results:
                        ui.label('No Clinical Trials results found').classes('text-subtitle1 text-grey')
                        return 0
                    
                    # Display results
                    for trial in results:
                        with ui.card().classes('w-full q-ma-sm q-pa-md'):
                            ui.link(
                                trial['title'],
                                f"https://clinicaltrials.gov/study/{trial['nct_id']}"
                            ).classes('text-subtitle1 font-bold text-primary')
                            with ui.row().classes('items-center gap-2'):
                                ui.badge(trial['status'], color='primary')
                                if trial.get('phase'):
                                    ui.badge(', '.join(trial['phase']), color='secondary')
                                    
                            with ui.expansion('Details', icon='info'):
                                if trial.get('description'):
                                    ui.markdown(f"**Description:**\n{trial['description']}").classes('text-body2')
                                elif trial.get('summary'):
                                    ui.markdown(f"**Summary:**\n{trial['summary']}").classes('text-body2')
                                else:
                                    ui.label('No description available').classes('text-body2 text-grey')
                                    
                                if trial.get('conditions'):
                                    ui.markdown(f"**Conditions:** {', '.join(trial['conditions'])}").classes('text-caption')
                                if trial.get('start_date'):
                                    ui.markdown(f"**Start Date:** {trial['start_date']}").classes('text-caption')
                                if trial.get('completion_date'):
                                    ui.markdown(f"**Completion Date:** {trial['completion_date']}").classes('text-caption')
                                if trial.get('last_updated'):
                                    ui.markdown(f"**Last Updated:** {trial['last_updated']}").classes('text-caption')
                                    
                    return len(results)
                    
            except Exception as e:
                logger.exception("Clinical Trials search error")
                with page_container:
                    await notification_manager.notify(
                        "Clinical Trials Error",
                        str(e),
                        type="negative",
                        icon="error",
                        dismissible=True
                    )
                raise