"""Literature search page for querying medical databases."""
import asyncio
import logging
from datetime import datetime
from nicegui import ui
from backend.crawlers import PubMedCrawler, ClinicalTrialsCrawler
from backend.utils import NotificationManager
from config import DEFAULT_CRAWLER_CONFIG

logger = logging.getLogger(__name__)

def create_search_page(run_task):
    """Create the literature search page content."""
    page_container = ui.column().classes('w-full max-w-3xl mx-auto')
    current_year = datetime.now().year
    year_from = current_year - 5
    year_to = current_year
    notifier = NotificationManager()
    
    with page_container:
        with ui.card().classes('w-full p-4'):
            ui.label('Medical Literature Search').classes('text-h5 q-mb-md')
            
            # Search input with inline controls
            with ui.column().classes('w-full gap-2'):
                # Search input box
                search_input = ui.input(
                    placeholder='Enter search terms...'
                ).props('outlined clearable').classes('w-full')
                
                # Source selection with inline controls 
                with ui.row().classes('w-full items-center justify-between q-mt-sm'):
                    # Sources and max results
                    with ui.row().classes('gap-4 items-center'):
                        with ui.row().classes('gap-2 items-center'):
                            ui.label('Sources:').classes('text-body1')
                            pubmed_check = ui.checkbox('PubMed', value=True).props('dense color=primary')
                            trials_check = ui.checkbox('Clinical Trials', value=True).props('dense color=secondary')
                        
                        with ui.row().classes('gap-2 items-center'):
                            ui.label('Max results:').classes('text-body1')
                            max_results = ui.select(
                                options=[5, 10, 25, 50, 100],
                                value=5
                            ).props('outlined dense options-dense').classes('w-24')
                    
                    # Year range inputs
                    with ui.row().classes('gap-2 items-center'):
                        ui.label('Years:').classes('text-body1')
                        year_from_input = ui.number(value=year_from, min=1900, max=current_year).props('outlined dense').classes('w-20')
                        ui.label('to').classes('text-body1')
                        year_to_input = ui.number(value=year_to, min=1900, max=current_year).props('outlined dense').classes('w-20')
                    
                    # Search button
                    search_button = ui.button(
                        'Search',
                        on_click=lambda: validate_and_search()
                    ).props('color=primary icon=search no-caps')
            
            async def validate_and_search():
                """Validate inputs and execute search if valid."""
                query = search_input.value.strip()
                
                # Check for empty query
                if not query:
                    await notifier.notify(
                        "Validation Error",
                        "Please enter a search query",
                        type="warning",
                        icon="warning",
                        dismissible=True
                    )
                    return
                
                # Check source selection
                if not pubmed_check.value and not trials_check.value:
                    await notifier.notify(
                        "Validation Error",
                        "Please select at least one source to search",
                        type="warning",
                        icon="warning",
                        dismissible=True
                    )
                    return
                
                # Clear previous results and show search is starting
                results_container.clear()
                await notifier.notify(
                    "Literature Search",
                    "Starting search...",
                    type="info",
                    timeout=2000,
                    spinner=True
                )
                
                try:
                    # Execute search directly
                    await _execute_search(query)
                    await notifier.notify(
                        "Literature Search",
                        "Search completed successfully",
                        type="positive",
                        timeout=3000
                    )
                except Exception as e:
                    logger.exception("Search failed")
                    await notifier.notify(
                        "Search Error",
                        str(e),
                        type="negative",
                        dismissible=True
                    )
            
            async def _execute_search(query: str):
                """Execute the search operation across selected sources."""
                results_container.clear()
                
                with results_container:
                    # Create tabbed interface for results
                    with ui.card().classes('w-full q-pa-md'):
                        ui.label('Search Results').classes('text-h6 q-mb-md')
                        
                        # Create tabs
                        with ui.tabs().classes('q-mb-md') as tabs:
                            ui.tab('all', 'All Results')  # Default combined results tab
                            if pubmed_check.value:
                                ui.tab('pubmed', 'PubMed')
                            if trials_check.value:
                                ui.tab('trials', 'Clinical Trials')
                        
                        # Create tab panels with results lists
                        with ui.tab_panels(tabs, value='all').classes('w-full'):
                            # All Results tab panel
                            with ui.tab_panel('all'):
                                with ui.column().classes('w-full gap-2'):
                                    all_stats = ui.element('div').classes('text-body1 q-mb-sm')
                                    with all_stats:
                                        ui.label('Loading results...').classes('text-body1')
                                    all_list = ui.element('div').classes('w-full')
                            
                            # PubMed tab panel
                            if pubmed_check.value:
                                with ui.tab_panel('pubmed'):
                                    with ui.column().classes('w-full gap-2'):
                                        pubmed_stats = ui.element('div').classes('text-body1 q-mb-sm')
                                        with pubmed_stats:
                                            ui.label('Loading PubMed results...').classes('text-body1')
                                        pubmed_list = ui.element('div').classes('w-full')
                            
                            # Clinical Trials tab panel
                            if trials_check.value:
                                with ui.tab_panel('trials'):
                                    with ui.column().classes('w-full gap-2'):
                                        trials_stats = ui.element('div').classes('text-body1 q-mb-sm')
                                        with trials_stats:
                                            ui.label('Loading Clinical Trials results...').classes('text-body1')
                                        trials_list = ui.element('div').classes('w-full')
                        
                        # Start searches in parallel
                        tasks = []
                        total_results = 0
                        
                        if pubmed_check.value:
                            tasks.append(_fetch_pubmed_results(
                                query=query,
                                run_task=run_task,
                                page_container=page_container,
                                year_from=year_from_input.value,
                                year_to=year_to_input.value,
                                results_list=pubmed_list,
                                all_list=all_list,  # Pass all_list for combined view
                                results_stats=pubmed_stats,
                                all_stats=all_stats,  # Pass all_stats for combined count
                                max_results=max_results.value
                            ))
                        
                        if trials_check.value:
                            tasks.append(_fetch_trials_results(
                                query=query,
                                run_task=run_task,
                                page_container=page_container,
                                year_from=year_from_input.value,
                                year_to=year_to_input.value,
                                results_list=trials_list,
                                all_list=all_list,  # Pass all_list for combined view
                                results_stats=trials_stats,
                                all_stats=all_stats,  # Pass all_stats for combined count
                                max_results=max_results.value
                            ))
                        
                        # Wait for all searches to complete
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Update final total in all results tab
                        total_count = sum(r for r in results if isinstance(r, int))
                        with all_stats:
                            all_stats.clear()
                            if total_count > 0:
                                ui.label(f"Found {total_count} total result{'s' if total_count != 1 else ''}").classes('text-body1')
                            else:
                                ui.label("No results found").classes('text-body1')

            # Hook up enter key to validation function
            search_input.on('keydown.enter', validate_and_search)
            
            # Results container
            results_container = ui.element('div').classes('w-full mt-4')

async def _fetch_pubmed_results(query: str, run_task, page_container, year_from: int, year_to: int, 
                               results_list, all_list, results_stats, all_stats, max_results: int):
    """Fetch PubMed results and add them to both source-specific and combined lists."""
    try:
        notifier = NotificationManager()
        async with PubMedCrawler(notifier, DEFAULT_CRAWLER_CONFIG) as crawler:
            # Add year range to query
            date_query = f"{query} AND {year_from}:{year_to}[dp]"
            
            # First collect the IDs
            pmids = []
            async for pmid in crawler.search(date_query, max_results=max_results * 2):
                pmids.append(pmid)
                if len(pmids) >= max_results:
                    break
            
            if not pmids:
                with results_stats:
                    results_stats.clear()
                    ui.label('No PubMed results found').classes('text-body1')
                return 0
            
            with results_stats:
                results_stats.clear()
                ui.label(f"Found {len(pmids)} PubMed result{'s' if len(pmids) != 1 else ''}").classes('text-body1')
            
            # Create placeholder cards for each result in both lists
            loading_cards = {}
            all_loading_cards = {}
            for i, pmid in enumerate(pmids):
                # Create card in source-specific list
                with results_list:
                    card = ui.card().classes('w-full q-mb-md q-pa-md')
                    loading_cards[pmid] = card
                    with card:
                        with ui.row().classes('items-center w-full'):
                            ui.badge('PubMed', color='primary').classes('q-mr-sm')
                            ui.spinner('dots').classes('text-primary')
                            ui.label(f'Loading PubMed article {pmid}...').classes('text-subtitle1')
                
                # Create duplicate card in all results list
                with all_list:
                    all_card = ui.card().classes('w-full q-mb-md q-pa-md')
                    all_loading_cards[pmid] = all_card
                    with all_card:
                        with ui.row().classes('items-center w-full'):
                            ui.badge('PubMed', color='primary').classes('q-mr-sm')
                            ui.spinner('dots').classes('text-primary')
                            ui.label(f'Loading PubMed article {pmid}...').classes('text-subtitle1')
            
            # Fetch and display articles one by one
            articles = []
            for pmid in pmids:
                try:
                    article = await crawler.get_item(pmid)
                    articles.append(article)
                    
                    # Update both source-specific and combined view cards
                    for card in [loading_cards[pmid], all_loading_cards[pmid]]:
                        card.clear()
                        with card:
                            with ui.row().classes('items-center w-full'):
                                ui.badge('PubMed', color='primary').classes('q-mr-sm')
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
                            
                except Exception as e:
                    logger.error(f"Error fetching PubMed article {pmid}: {e}")
                    await notifier.notify(
                        "PubMed Error",
                        f"Error loading article {pmid}: {str(e)}",
                        type="negative",
                        icon="error",
                        dismissible=True
                    )
                    
                    # Update error state in both cards
                    for card in [loading_cards[pmid], all_loading_cards[pmid]]:
                        card.clear()
                        with card:
                            with ui.row().classes('items-center w-full'):
                                ui.badge('PubMed', color='primary').classes('q-mr-sm')
                                ui.label(f"Error loading article {pmid}: {str(e)}").classes('text-negative')
            
            return len(articles)
                
    except Exception as e:
        logger.exception("PubMed search error")
        with results_stats:
            results_stats.clear()
            ui.label(f"PubMed search error: {str(e)}").classes('text-negative')
        notifier = NotificationManager()
        await notifier.notify(
            "PubMed Error",
            str(e),
            type="negative",
            icon="error",
            dismissible=True
        )
        return 0

async def _fetch_trials_results(query: str, run_task, page_container, year_from: int, year_to: int,
                               results_list, all_list, results_stats, all_stats, max_results: int):
    """Fetch Clinical Trials results and add them to both source-specific and combined lists."""
    try:
        notifier = NotificationManager()
        async with ClinicalTrialsCrawler(notifier, DEFAULT_CRAWLER_CONFIG) as crawler:
            # Format the date range according to ClinicalTrials.gov API requirements
            date_query = f"{query} AREA[LastUpdatePostDate]RANGE[{year_from}-01-01,{year_to}-12-31]"
            
            # First collect the IDs
            nctids = []
            async for nctid in crawler.search(date_query, max_results=max_results):
                nctids.append(nctid)
                if len(nctids) >= max_results:
                    break
                
            if not nctids:
                with results_stats:
                    results_stats.clear()
                    ui.label('No Clinical Trials results found').classes('text-body1')
                return 0
            
            with results_stats:
                results_stats.clear()
                ui.label(f"Found {len(nctids)} Clinical Trial{'s' if len(nctids) != 1 else ''}").classes('text-body1')
            
            # Create placeholder cards for each result in both lists
            loading_cards = {}
            all_loading_cards = {}
            for i, nctid in enumerate(nctids):
                # Create card in source-specific list
                with results_list:
                    card = ui.card().classes('w-full q-mb-md q-pa-md')
                    loading_cards[nctid] = card
                    with card:
                        with ui.row().classes('items-center w-full'):
                            ui.badge('Clinical Trials', color='secondary').classes('q-mr-sm')
                            ui.spinner('dots').classes('text-primary')
                            ui.label(f'Loading trial {nctid}...').classes('text-subtitle1')
                
                # Create duplicate card in all results list
                with all_list:
                    all_card = ui.card().classes('w-full q-mb-md q-pa-md')
                    all_loading_cards[nctid] = all_card
                    with all_card:
                        with ui.row().classes('items-center w-full'):
                            ui.badge('Clinical Trials', color='secondary').classes('q-mr-sm')
                            ui.spinner('dots').classes('text-primary')
                            ui.label(f'Loading trial {nctid}...').classes('text-subtitle1')
            
            # Fetch and display trials one by one
            trials = []
            for nctid in nctids:
                try:
                    trial = await crawler.get_item(nctid)
                    trials.append(trial)
                    
                    # Update both source-specific and combined view cards
                    for card in [loading_cards[nctid], all_loading_cards[nctid]]:
                        card.clear()
                        with card:
                            # Title and source badge
                            with ui.row().classes('items-center w-full'):
                                ui.badge('Clinical Trials', color='secondary').classes('q-mr-sm')
                                ui.link(
                                    trial['title'],
                                    f"https://clinicaltrials.gov/study/{trial['nct_id']}"
                                ).classes('text-subtitle1 font-bold text-primary')
                            
                            # Status and phase badges
                            with ui.row().classes('items-center gap-2 q-mt-sm'):
                                ui.badge(trial['status'], color='info')
                                if trial.get('phase'):
                                    ui.badge(', '.join(trial['phase']), color='accent')
                            
                            # Key information outside expander
                            with ui.column().classes('q-mt-sm gap-1'):
                                if trial.get('conditions'):
                                    ui.markdown(f"**Conditions:** {', '.join(trial['conditions'])}").classes('text-body2')
                                
                                # Timeline information in a row
                                with ui.row().classes('items-center gap-4'):
                                    if trial.get('start_date'):
                                        ui.markdown(f"**Start:** {trial['start_date']}").classes('text-body2')
                                    if trial.get('completion_date'):
                                        ui.markdown(f"**Completion:** {trial['completion_date']}").classes('text-body2')
                                    if trial.get('enrollment'):
                                        ui.markdown(f"**Enrollment:** {trial['enrollment']} participants").classes('text-body2')
                                    
                            # Detailed information in expander
                            with ui.expansion('More Details', icon='info').classes('q-mt-sm items-stretch'):
                                with ui.element('div').classes('q-pa-none'):  # Wrapper with no padding
                                    # Study Description with minimal spacing
                                    if trial.get('description'):
                                        with ui.element('div').classes('q-mb-xs'):
                                            ui.markdown(f"**Description:**\n{trial['description']}").classes('text-body2 no-margin dense')
                                    elif trial.get('summary'):
                                        with ui.element('div').classes('q-mb-xs'):
                                            ui.markdown(f"**Summary:**\n{trial['summary']}").classes('text-body2 no-margin dense')
                                    else:
                                        ui.label('No description available').classes('text-body2 text-grey no-margin')
                                    
                                    ui.separator().classes('q-my-xs')  # Thin separator
                                    
                                    # Content sections in a tight layout
                                    with ui.element('div').classes('q-gutter-y-xs'):
                                        # Basic Information
                                        with ui.grid(columns=2).classes('full-width q-gutter-x-xs q-gutter-y-none'):
                                            if trial.get('interventions'):
                                                intervention_texts = [
                                                    f"{intervention['type']}: {intervention['name']}"
                                                    for intervention in trial['interventions']
                                                ]
                                                ui.markdown(f"**Interventions:** {', '.join(intervention_texts)}").classes('text-caption no-margin dense')
                                            if trial.get('study_type'):
                                                ui.markdown(f"**Study Type:** {trial['study_type']}").classes('text-caption no-margin dense')
                                            design_info = trial.get('design_info', {})
                                            if design_info.get('allocation'):
                                                ui.markdown(f"**Allocation:** {design_info['allocation']}").classes('text-caption no-margin dense')
                                            if design_info.get('intervention_model'):
                                                ui.markdown(f"**Intervention Model:** {design_info['intervention_model']}").classes('text-caption no-margin dense')
                                            if design_info.get('masking'):
                                                masking_text = design_info['masking']
                                                if design_info.get('who_masked'):
                                                    masking_text += f" ({', '.join(design_info['who_masked'])})"
                                                ui.markdown(f"**Masking:** {masking_text}").classes('text-caption no-margin dense')
                                        
                                        # Locations with minimal spacing
                                        if trial.get('locations'):
                                            ui.separator().classes('q-my-xs')
                                            with ui.element('div').classes('q-mt-none'):
                                                ui.markdown("**Study Locations:**").classes('text-caption no-margin dense')
                                                with ui.element('div').classes('q-ml-md q-mt-none'):
                                                    locations_text = "\n".join([f"- {location}" for location in trial['locations']])
                                                    ui.markdown(locations_text).classes('text-caption no-margin dense q-mt-none')
                                        
                                        # Timeline Information
                                        ui.separator().classes('q-my-xs')
                                        with ui.grid(columns=2).classes('full-width q-gutter-x-xs q-gutter-y-none'):
                                            if trial.get('primary_completion_date'):
                                                ui.markdown(f"**Primary Completion:** {trial['primary_completion_date']}").classes('text-caption no-margin dense')
                                            if trial.get('last_updated'):
                                                ui.markdown(f"**Last Updated:** {trial['last_updated']}").classes('text-caption no-margin dense')
                                        
                                        # Contacts with minimal spacing
                                        if trial.get('contacts'):
                                            ui.separator().classes('q-my-xs')
                                            with ui.element('div').classes('q-mt-none'):
                                                ui.markdown("**Contacts:**").classes('text-caption no-margin dense')
                                                with ui.element('div').classes('q-ml-md q-mt-none'):
                                                    contacts_text = "\n".join([f"- {contact}" for contact in trial['contacts']])
                                                    ui.markdown(contacts_text).classes('text-caption no-margin dense q-mt-none')
                        
                except Exception as e:
                    logger.error(f"Error fetching Clinical Trial {nctid}: {e}")
                    await notifier.notify(
                        "Clinical Trials Error",
                        f"Error loading trial {nctid}: {str(e)}",
                        type="negative",
                        icon="error",
                        dismissible=True
                    )
                    
                    # Update error state in both cards
                    for card in [loading_cards[nctid], all_loading_cards[nctid]]:
                        card.clear()
                        with card:
                            with ui.row().classes('items-center w-full'):
                                ui.badge('Clinical Trials', color='secondary').classes('q-mr-sm')
                                ui.label(f"Error loading trial {nctid}: {str(e)}").classes('text-negative')
            
            return len(trials)
                
    except Exception as e:
        logger.exception("Clinical Trials search error")
        with results_stats:
            results_stats.clear()
            ui.label(f"Clinical Trials search error: {str(e)}").classes('text-negative')
        notifier = NotificationManager()
        await notifier.notify(
            "Clinical Trials Error",
            str(e),
            type="negative",
            icon="error",
            dismissible=True
        )
        return 0