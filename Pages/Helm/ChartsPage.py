"""
Enhanced implementation of the Charts page with comprehensive data from ArtifactHub API.
Includes icon detection, better error handling, and more metadata from the API.
"""

from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QHBoxLayout,
    QToolButton, QMenu, QVBoxLayout, QTableWidgetItem, 
    QProgressBar, QScrollBar, QAbstractSlider
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QIcon, QPixmap

import requests
import json
import os
import re
import hashlib
import time
import shutil
from urllib.parse import urljoin
from datetime import datetime

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles


class ChartDataThread(QThread):
    """Thread for loading Helm charts from ArtifactHub API without blocking the UI."""
    data_loaded = pyqtSignal(list, bool)  # Data, is_more_available
    error_occurred = pyqtSignal(str)
    
    def __init__(self, limit=25, offset=0, use_search=True, search_term=""):
        super().__init__()
        self.limit = limit
        self.offset = offset
        self.use_search = use_search
        self.search_term = search_term
        
        # Create the directories for storing icons
        self.setup_directories()
        
        # Repository icons cache (repo_name -> icon_path)
        self.repository_icons = {}
        
    def __del__(self):
        """Clean up resources when object is deleted"""
        self.cleanup_threads()
    
    def setup_directories(self):
        """Set up directories for storing icons and cache"""
        # Create directory for icons
        self.icons_dir = os.path.join(os.path.expanduser('~'), '.artifacthub', 'icons')
        os.makedirs(self.icons_dir, exist_ok=True)
        
        # Create directory for default icons
        self.default_icons_dir = os.path.join(os.path.expanduser('~'), '.artifacthub', 'default_icons')
        os.makedirs(self.default_icons_dir, exist_ok=True)
        
        # Download default Helm icon if not present
        self.default_helm_icon_path = os.path.join(self.default_icons_dir, 'default_helm_icon.png')
        if not os.path.exists(self.default_helm_icon_path):
            try:
                # Create a session for cookies and headers
                session = requests.Session()
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json'
                }
                
                # Try to get the Helm icon from Artifact Hub
                default_icon_url = "https://artifacthub.io/static/media/helm-chart.svg"
                icon_response = session.get(default_icon_url, headers=headers, timeout=10)
                if icon_response.status_code == 200:
                    with open(self.default_helm_icon_path, 'wb') as f:
                        f.write(icon_response.content)
                    print(f"Downloaded default Helm icon to {self.default_helm_icon_path}")
            except Exception as e:
                print(f"Error downloading default Helm icon: {e}")
        
    def cleanup_threads(self):
        """Safely clean up any running threads"""
        # List of thread attributes to clean up
        thread_attrs = ['api_thread', 'download_thread']
        
        # Stop each thread safely
        for attr in thread_attrs:
            if hasattr(self, attr):
                thread = getattr(self, attr)
                if thread and thread.isRunning():
                    thread.wait(300)  # Wait up to 300ms for thread to finish

    def run(self):
        """Execute the API request and emit results."""
        try:
            # Create a session for cookies and headers
            session = requests.Session()
            
            # Use a more browser-like user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # Try different API methods: POST first (seems more reliable based on paste.txt)
            charts_data = []
            is_more_available = True  # ALWAYS assume more data is available for pagination
            
            # First try POST method
            try:
                post_endpoint = 'https://artifacthub.io/api/v1/packages/search'
                
                # Build search parameters
                search_query = "apache -solr -hadoop"  # Default query from paste.txt
                if self.use_search and self.search_term:
                    search_query = self.search_term
                
                post_data = {
                    "filters": {
                        "kind": [0]  # 0 is for Helm charts
                    },
                    "offset": self.offset,
                    "limit": self.limit,
                    "sort": "last_updated", 
                    "ts_query_web": search_query
                }
                
                print(f"Fetching data with offset {self.offset}, limit {self.limit}...")
                response = session.post(post_endpoint, json=post_data, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    page_data = response.json()
                    
                    # Process the data
                    charts_data = self.process_api_data(page_data, session, headers)
                    
                    # We'll assume more data is available if we got a full page
                    is_more_available = len(charts_data) >= self.limit
                    
                    print(f"POST method successful, found {len(charts_data)} charts. More available: {is_more_available}")
                else:
                    print(f"POST request failed with status code {response.status_code}")
            except Exception as e:
                print(f"Error with POST method: {e}")
            
            # If POST failed and we have no data, try GET method
            if not charts_data:
                try:
                    # Try different API endpoints
                    possible_api_endpoints = [
                        'https://artifacthub.io/api/v1/packages/search',
                        'https://artifacthub.io/api/packages/search',
                        'https://artifacthub.io/packages/api/v1/search'
                    ]
                    
                    for endpoint in possible_api_endpoints:
                        # Parameters for the search
                        search_query = "apache -solr -hadoop"  # Default query from paste.txt
                        if self.use_search and self.search_term:
                            search_query = self.search_term
                            
                        params = {
                            'kind': '0',  # Helm charts
                            'ts_query_web': search_query,
                            'sort': 'last_updated',
                            'page': (self.offset // self.limit) + 1,
                            'limit': self.limit
                        }
                        
                        print(f"Trying GET with endpoint: {endpoint}")
                        response = session.get(endpoint, params=params, headers=headers, timeout=30)
                        
                        if response.status_code == 200:
                            page_data = response.json()
                            
                            # Process the data
                            charts_data = self.process_api_data(page_data, session, headers)
                            
                            # We'll assume more data is available if we got a full page
                            is_more_available = len(charts_data) >= self.limit
                            
                            print(f"GET method successful with {endpoint}, found {len(charts_data)} charts. More available: {is_more_available}")
                            break  # Exit the loop if we got data
                except Exception as e:
                    print(f"Error with GET method: {e}")
            
            # If both API methods failed, try the old endpoint as a fallback
            if not charts_data:
                try:
                    legacy_endpoint = "https://artifacthub.io/api/v1/helm-exporter"
                    print(f"Trying legacy endpoint: {legacy_endpoint}")
                    
                    response = session.get(legacy_endpoint, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        all_data = response.json()
                        
                        # Calculate available data slice
                        start = self.offset
                        end = min(start + self.limit, len(all_data))
                        
                        # Check if more data is available beyond this request
                        is_more_available = end < len(all_data)
                        
                        # Process requested slice of data
                        charts_data = []
                        for item in all_data[start:end]:
                            # Extract data with more robust error handling
                            chart = {
                                "name": item.get("name", "Unknown"),
                                "description": item.get("description", "No description available"),
                                "version": item.get("version", "N/A"),
                                "app_version": item.get("app_version", "N/A"),
                                "created_at": item.get("created_at", ""),
                                "icon_path": None
                            }
                            
                            # Handle repository data with better error checking
                            repository = item.get("repository", {})
                            if isinstance(repository, dict):
                                chart["repository"] = repository.get("name", "Unknown")
                                chart["repository_url"] = repository.get("url", "")
                            else:
                                chart["repository"] = "Unknown"
                                chart["repository_url"] = ""
                            
                            charts_data.append(chart)
                        
                        print(f"Legacy endpoint successful, found {len(charts_data)} charts. More available: {is_more_available}")
                except Exception as e:
                    print(f"Error with legacy endpoint: {e}")
            
            # Force more data available flag to true if we got any data at all
            # This ensures we can always try to load more data when scrolling
            if charts_data:
                is_more_available = True
            
            # Do a second pass to add default icons for charts missing them
            charts_missing_icons = [chart for chart in charts_data if not chart.get('icon_path')]
            if charts_missing_icons:
                print(f"Adding default icons for {len(charts_missing_icons)} charts")
                
                for chart in charts_missing_icons:
                    # First try repository icon
                    repo_name = chart.get('repository', 'Unknown')
                    if repo_name in self.repository_icons and self.repository_icons[repo_name] != 'N/A':
                        chart['icon_path'] = self.repository_icons[repo_name]
                    else:
                        # Use default Helm icon as last resort
                        if os.path.exists(self.default_helm_icon_path):
                            chart['icon_path'] = self.default_helm_icon_path
            
            # Emit the result with more data available flag
            print(f"Emitting {len(charts_data)} charts with is_more_available={is_more_available}")
            self.data_loaded.emit(charts_data, is_more_available)
            
        except Exception as e:
            self.error_occurred.emit(f"Error fetching charts: {str(e)}")
    
    def process_api_data(self, api_data, session, headers):
        """Process API data to extract helm charts with icons"""
        helm_charts = []
        
        if not api_data:
            return helm_charts
        
        # Handle different possible data structures
        packages = []
        
        if isinstance(api_data, dict):
            if 'packages' in api_data:
                packages = api_data['packages']
            elif 'data' in api_data and isinstance(api_data['data'], list):
                packages = api_data['data']
            elif 'items' in api_data and isinstance(api_data['items'], list):
                packages = api_data['items']
        elif isinstance(api_data, list):
            packages = api_data
        
        # Process packages
        for package in packages:
            try:
                # Extract data (adjust based on actual API response structure)
                name = package.get('name', 'Unknown')
                if isinstance(name, dict) and 'name' in name:
                    name = name['name']
                
                description = package.get('description', 'No description available')
                version = package.get('version', 'N/A')
                app_version = package.get('app_version', None)
                if app_version is None and 'appVersion' in package:
                    app_version = package.get('appVersion', 'N/A')
                
                # Extract repository info
                repository = 'Unknown'
                repository_url = ''
                if 'repository' in package and isinstance(package.get('repository'), dict):
                    repo = package.get('repository', {})
                    repository = repo.get('name', 'Unknown')
                    repository_url = repo.get('url', '')
                
                # Get stars and last updated
                stars = str(package.get('stars', 0))
                last_updated = package.get('last_updated', None)
                if not last_updated:
                    last_updated = package.get('created_at', '')
                
                # Store package_id for potential later use to get detailed info
                package_id = package.get('package_id', 'N/A')
                if package_id == 'N/A' and 'packageId' in package:
                    package_id = package.get('packageId', 'N/A')
                
                # Download icon if available
                icon_url, icon_path = self.download_icon(package, session, headers)
                
                # Add to our list
                helm_charts.append({
                    'name': name,
                    'description': description,
                    'version': version,
                    'app_version': app_version,
                    'repository': repository,
                    'repository_url': repository_url,
                    'stars': stars,
                    'last_updated': last_updated,
                    'package_id': package_id,
                    'icon_url': icon_url,
                    'icon_path': icon_path
                })
            except Exception as e:
                print(f"Error processing package: {e}")
        
        return helm_charts
    
    def download_icon(self, package, session, headers):
        """Download and save the package icon if available"""
        icon_url = None
        icon_path = None
        
        try:
            # Get package name for debugging
            package_name = package.get('name', 'unknown')
            
            # Specifically target logo_image_id field
            if 'logo_image_id' in package and package['logo_image_id']:
                logo_id = package.get('logo_image_id')
                if logo_id:
                    icon_url = f"https://artifacthub.io/image/{logo_id}"
            
            # If no logo_image_id, check other possible icon fields
            if not icon_url:
                # Check for direct logoURL or logo field
                if 'logoURL' in package and package['logoURL']:
                    icon_url = package.get('logoURL')
                elif 'logo_url' in package and package['logo_url']:
                    icon_url = package.get('logo_url')
                elif 'logoImageId' in package and package['logoImageId']:
                    logo_id = package.get('logoImageId')
                    if logo_id:
                        icon_url = f"https://artifacthub.io/image/{logo_id}"
                elif 'logo' in package and package['logo']:
                    icon_url = package.get('logo')
                elif 'icon' in package and package['icon']:
                    icon_url = package.get('icon')
                    
                # Check for nested structures
                elif 'repository' in package and isinstance(package['repository'], dict):
                    repo = package['repository']
                    
                    # Save repository logo for future use as fallback
                    repo_name = repo.get('name')
                    if repo_name:
                        # Look for repository logo
                        repo_logo_id = None
                        if 'logo_image_id' in repo and repo['logo_image_id']:
                            repo_logo_id = repo['logo_image_id']
                        elif 'logoImageId' in repo and repo['logoImageId']:
                            repo_logo_id = repo['logoImageId']
                        
                        if repo_logo_id and repo_name not in self.repository_icons:
                            repo_icon_url = f"https://artifacthub.io/image/{repo_logo_id}"
                            # Download the repository icon
                            try:
                                repo_icon_filename = f"repo_{repo_name}_{hashlib.md5(repo_icon_url.encode()).hexdigest()[:8]}.png"
                                repo_icon_path = os.path.join(self.icons_dir, repo_icon_filename)
                                
                                if not os.path.exists(repo_icon_path):
                                    repo_icon_response = session.get(repo_icon_url, headers=headers, timeout=10)
                                    if repo_icon_response.status_code == 200:
                                        with open(repo_icon_path, 'wb') as f:
                                            f.write(repo_icon_response.content)
                                        self.repository_icons[repo_name] = repo_icon_path
                                else:
                                    self.repository_icons[repo_name] = repo_icon_path
                            except Exception as e:
                                print(f"Error downloading repository icon for '{repo_name}': {e}")
                                self.repository_icons[repo_name] = 'N/A'
                    
                    # Try to use repo logo fields for the package icon if not found elsewhere
                    if not icon_url:
                        if 'logoURL' in repo and repo['logoURL']:
                            icon_url = repo.get('logoURL')
                        elif 'logo_url' in repo and repo['logo_url']:
                            icon_url = repo.get('logo_url')
                        elif 'logo_image_id' in repo and repo['logo_image_id']:
                            logo_id = repo.get('logo_image_id')
                            if logo_id:
                                icon_url = f"https://artifacthub.io/image/{logo_id}"
                        elif 'logo' in repo and repo['logo']:
                            icon_url = repo.get('logo')
                
                # Check for chart metadata
                elif 'chart' in package and isinstance(package['chart'], dict):
                    chart = package['chart']
                    if 'logo' in chart and chart['logo']:
                        icon_url = chart.get('logo')
                    elif 'icon' in chart and chart['icon']:
                        icon_url = chart.get('icon')
                
                # Try additional nested paths (based on actual API structure)
                elif 'content' in package and isinstance(package['content'], dict):
                    content = package['content']
                    if 'logo' in content and content['logo']:
                        icon_url = content.get('logo')
                    elif 'icon' in content and content['icon']:
                        icon_url = content.get('icon')
            
            # If icon URL starts with /, it's a relative URL
            if icon_url and icon_url.startswith('/'):
                icon_url = urljoin('https://artifacthub.io', icon_url)
            
            # If we found an icon URL, download it
            if icon_url:
                # Create a filename based on package name and URL hash
                url_hash = hashlib.md5(icon_url.encode()).hexdigest()[:8]
                
                # Determine file extension from URL or default to .png
                file_ext = os.path.splitext(icon_url)[1].lower()
                if not file_ext or len(file_ext) > 5:  # If no extension or suspicious extension
                    file_ext = '.png'
                
                # Clean package name for filename
                safe_name = re.sub(r'[^\w\-\.]', '_', package_name)
                icon_filename = f"{safe_name}_{url_hash}{file_ext}"
                icon_path = os.path.join(self.icons_dir, icon_filename)
                
                # Download the icon if it doesn't exist
                if not os.path.exists(icon_path):
                    try:
                        icon_response = session.get(icon_url, headers=headers, timeout=10)
                        
                        if icon_response.status_code == 200:
                            with open(icon_path, 'wb') as f:
                                f.write(icon_response.content)
                        else:
                            print(f"Failed to download icon for '{package_name}': HTTP {icon_response.status_code}")
                            icon_path = None
                    except Exception as e:
                        print(f"Error downloading icon for '{package_name}': {e}")
                        icon_path = None
            else:
                icon_path = None
        
        except Exception as e:
            print(f"Error in download_icon: {e}")
            icon_path = None
        
        return icon_url, icon_path


class ChartSearchThread(QThread):
    """Thread for searching Helm charts from ArtifactHub API."""
    search_completed = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, search_term=""):
        super().__init__()
        self.search_term = search_term
        
    def run(self):
        """Execute the search request and emit results."""
        # Create and start a ChartDataThread with search parameters
        data_thread = ChartDataThread(limit=25, offset=0, use_search=True, search_term=self.search_term)
        data_thread.data_loaded.connect(lambda data, is_more: self.search_completed.emit(data, self.search_term))
        data_thread.error_occurred.connect(self.error_occurred)
        data_thread.start()
        data_thread.wait()  # Wait for thread to complete


class ChartsPage(BaseResourcePage):
    """
    Displays Helm charts with enhanced data from ArtifactHub API.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "charts"  # Set resource type for detail page
        self.resources = []  # Store loaded chart data
        self.offset = 0  # Current offset for pagination
        self.is_more_available = True  # Flag to indicate if more data can be loaded
        self.is_loading_more = False  # Flag to prevent multiple load-more operations
        self.is_searching = False  # Flag to indicate search mode
        
        # Add a safety mechanism to recover from stuck loading states
        self._loading_timer = QTimer()
        self._loading_timer.timeout.connect(self._reset_loading_state)
        self._loading_timer.setSingleShot(True)
        
        # Track total items available (for pagination)
        self.total_items = 1000  # Force a large number to ensure pagination works
        
        # Initialize the UI
        self.setup_page_ui()
        
    # Removed Helm installation check since it's not needed for charts browser
    
    def _reset_loading_state(self):
        """Reset loading state if it gets stuck"""
        if hasattr(self, 'is_loading') and self.is_loading:
            print("Loading state was stuck, resetting...")
            self.is_loading = False
            
        if hasattr(self, 'is_loading_more') and self.is_loading_more:
            print("Loading more state was stuck, resetting...")
            self.is_loading_more = False
            
        # Always ensure is_more_available is True to allow trying to load more
        if hasattr(self, 'resources') and len(self.resources) > 0:
            self.is_more_available = True
            
        # Re-enable the table if it was disabled
        if hasattr(self, 'table'):
            self.table.setEnabled(True)
            
        # If we had a loading indicator row, remove it
        if hasattr(self, 'table') and self.table.rowCount() > 0:
            last_row = self.table.rowCount() - 1
            cell_widget = self.table.cellWidget(last_row, 0)
            if cell_widget and hasattr(cell_widget, 'findChild'):
                progress_bar = cell_widget.findChild(QProgressBar)
                if progress_bar:
                    # This is likely a loading indicator row, remove it
                    self.table.setRowCount(last_row)
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Charts page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Description", "Version", "App Version", "Repository", ""]
        sortable_columns = {1, 3, 4, 5}
        
        # Create base UI
        layout = super().setup_ui("Charts", headers, sortable_columns)
        
        # Apply table style
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure column widths
        self.configure_columns()
        
        # Connect vertical scrollbar to detect when user reaches bottom
        scrollbar = self.table.verticalScrollBar()
        scrollbar.valueChanged.connect(self.check_scroll_position)
        
        # Remove checkbox column if present in the base class
        if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox:
            self.select_all_checkbox.hide()
        
        return layout
    
    def _apply_filters(self):
        """Apply search filter to the table"""
        if not hasattr(self, 'table') or self.table.rowCount() == 0:
            return
                
        # Get the search text
        search_text = ""
        if hasattr(self, 'search_bar'):
            search_text = self.search_bar.text().lower()
        
        # Hide rows that don't match the filters
        for row in range(self.table.rowCount()):
            show_row = True
            
            # Apply search filter if text is entered
            if search_text:
                row_matches = False
                
                # Search through all displayed columns, including the name column (column 0)
                # Skip only the actions column (the last column)
                for col in range(1, self.table.columnCount() - 1):  # Skip icon and actions columns
                    # Check regular table items
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        row_matches = True
                        break
                    
                    # Check for cell widgets (like status labels)
                    cell_widget = self.table.cellWidget(row, col)
                    if cell_widget:
                        widget_text = ""
                        # Handle widgets which contain QLabels
                        for label in cell_widget.findChildren(QLabel):
                            widget_text += label.text() + " "
                        
                        if search_text in widget_text.lower():
                            row_matches = True
                            break
                
                if not row_matches:
                    show_row = False
            
            # Show or hide the row based on filters
            self.table.setRowHidden(row, not show_row)

    def check_scroll_position(self, value):
        """Check if user has scrolled to the bottom and load more data if needed"""
        # Don't load more data if we're in search mode or if we're already loading
        if self.is_searching or self.is_loading or self.is_loading_more:
            return
            
        scrollbar = self.table.verticalScrollBar()
        
        # Get scrollbar values
        max_value = scrollbar.maximum()
        page_step = scrollbar.pageStep()
        current_value = value
        
        # Calculate how far we've scrolled as a percentage (0.0 to 1.0)
        # Avoid division by zero if max_value is 0
        if max_value <= 0:
            return
            
        scroll_percentage = current_value / max_value
        
        # Print debugging info occasionally when scroll_percentage changes significantly
        if int(scroll_percentage * 10) != getattr(self, '_last_scroll_debug', -1):
            self._last_scroll_debug = int(scroll_percentage * 10)
            print(f"Scroll position: {scroll_percentage:.2%}, current={current_value}, max={max_value}")
            print(f"Loading state: is_loading={self.is_loading}, is_loading_more={self.is_loading_more}")
            print(f"Data state: items={len(self.resources)}, offset={self.offset}, more_available={self.is_more_available}")
        
        # ALWAYS try to load more data when we're over 70% scrolled
        # This is the key fix - even if is_more_available is False, we try anyway
        if scroll_percentage >= 0.65:
            print(f"Reached 65% scroll threshold, forcing load more data (even if API says no more)...")
            
            # Force is_more_available to True to ensure we try loading more
            self.is_more_available = True
            
            # Call load_more_data if we're not already loading
            if not self.is_loading_more and not self.is_loading:
                print("Calling load_more_data()...")
                self.load_more_data()
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Configure columns with fixed widths
        fixed_widths = {
            0: 50,   # Icon
            1: 180,  # Name
            3: 100,  # Version
            4: 120,  # App Version
            5: 150,  # Repository
            6: 40    # Actions
        }
        
        # Set column widths
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        
        # Make Description column stretch
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    
    def load_data(self):
        """Load initial chart data from ArtifactHub API"""
        if hasattr(self, 'is_loading') and self.is_loading:
            print("Already loading data, skipping request")
            return
            
        self.is_loading = True
        self.resources = []
        self.offset = 0
        self.is_more_available = True
        
        # Start the safety timer to recover from potential stuck states
        self._loading_timer.start(15000)  # 15 seconds timeout
        
        # Clear the table first
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        # Show loading indicator
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setContentsMargins(20, 20, 20, 20)
        
        loading_bar = QProgressBar()
        loading_bar.setRange(0, 0)  # Indeterminate
        loading_bar.setTextVisible(False)
        loading_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                background-color: #1e1e1e;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
            }
        """)
        
        loading_text = QLabel(f"Loading charts from ArtifactHub API...")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        # Create and start the data loading thread
        self.chart_thread = ChartDataThread(limit=25, offset=self.offset)
        self.chart_thread.data_loaded.connect(self.on_data_loaded)
        self.chart_thread.error_occurred.connect(self.on_load_error)
        self.chart_thread.start()

    def load_more_data(self):
        """Load more chart data when user scrolls to bottom"""
        if not self.is_more_available or self.is_loading_more:
            print("Not loading more: is_more_available =", self.is_more_available, 
                  "is_loading_more =", self.is_loading_more)
            return
            
        print("Loading more data from offset", self.offset)
        self.is_loading_more = True
        
        # Start the safety timer to recover from potential stuck states
        self._loading_timer.start(15000)  # 15 seconds timeout
        
        # Calculate the new offset for next batch of data
        self.offset = len(self.resources)
        
        # Add a loading indicator row at the bottom
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QHBoxLayout(loading_widget)
        loading_layout.setContentsMargins(10, 5, 10, 5)
        
        loading_bar = QProgressBar()
        loading_bar.setRange(0, 0)  # Indeterminate
        loading_bar.setTextVisible(False)
        loading_bar.setMaximumHeight(10)
        loading_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 2px;
                background-color: #1e1e1e;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
            }
        """)
        
        loading_text = QLabel("Loading more charts...")
        loading_text.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        # Create and start the data loading thread for additional data
        self.more_thread = ChartDataThread(limit=25, offset=self.offset)
        self.more_thread.data_loaded.connect(self.on_more_data_loaded)
        self.more_thread.error_occurred.connect(self.on_load_more_error)
        self.more_thread.start()
    
    def on_data_loaded(self, data, is_more_available):
        """Handle loaded chart data for initial load"""
        # Stop the safety timer
        self._loading_timer.stop()
        
        self.is_loading = False
        self.resources = data
        
        # Force is_more_available to True for better UX until we reach the true end
        self.is_more_available = True if data else False
        
        print(f"Initial data loaded: {len(data)} items, more available set to TRUE for pagination")
        
        # Update the item count
        self.items_count.setText(f"{len(data)} items (scroll for more)")
        
        # Clear the table and populate with data
        self.table.setRowCount(0)
        self.populate_table(data)
        
        # Re-enable sorting
        self.table.setSortingEnabled(True)
        
        # Apply any existing filters
        if hasattr(self, '_apply_filters'):
            self._apply_filters()
    
    def on_more_data_loaded(self, data, is_more_available):
        """Handle loaded chart data for load-more operation"""
        # Stop the safety timer
        self._loading_timer.stop()
        
        # Remove the loading indicator row
        self.table.setRowCount(self.table.rowCount() - 1)
        
        # Update tracking variables
        self.is_loading_more = False
        
        print(f"More data loaded: {len(data)} additional items")
        
        if data:
            # Keep trying to load more as long as we get some data
            self.is_more_available = True
            
            # Add new data to existing resources
            self.resources.extend(data)
            
            # Disable sorting temporarily while adding rows
            was_sorting_enabled = self.table.isSortingEnabled()
            self.table.setSortingEnabled(False)
            
            # Add new rows
            start_row = self.table.rowCount()
            self.table.setRowCount(start_row + len(data))
            
            # Populate new rows
            for i, chart in enumerate(data):
                self.populate_chart_row(start_row + i, chart)
            
            # Restore sorting state
            self.table.setSortingEnabled(was_sorting_enabled)
            
            # Make sure we update the offset for next pagination request
            self.offset = len(self.resources)
            
            # Update the item count with pagination indication
            self.items_count.setText(f"{len(self.resources)} items (scroll for more)")
        else:
            # No data returned means we've likely reached the end
            self.is_more_available = False
            print("No additional data returned, setting is_more_available to False")
            
            # Update the item count without pagination indication
            self.items_count.setText(f"{len(self.resources)} items (end of results)")
        
    def on_search_completed(self, search_results, search_term):
        """Handle search results"""
        # Clear the search indicator
        self.table.setRowCount(0)
        
        # Store results
        self.resources = search_results
        
        # Display results
        self.table.setSortingEnabled(False)
        self.populate_table(search_results)
        self.table.setSortingEnabled(True)
        
        # Update item count to show search context
        self.items_count.setText(f"{len(search_results)} results for '{search_term}'")
        
    def on_search_error(self, error_message):
        """Handle search error"""
        # Clear the loading indicator
        self.table.setRowCount(0)
        
        # Show error message
        error_row = 0
        self.table.setRowCount(1)
        self.table.setSpan(error_row, 0, 1, self.table.columnCount())
        
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.setContentsMargins(20, 30, 20, 30)
        
        error_text = QLabel(f"Search error: {error_message}")
        error_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_text.setStyleSheet("color: #ff6b6b; font-size: 14px;")
        error_text.setWordWrap(True)
        
        error_layout.addWidget(error_text)
        
        self.table.setCellWidget(error_row, 0, error_widget)
        
        # Log the error
        print(f"Error searching charts: {error_message}")
    
    def on_load_error(self, error_message):
        """Handle error loading data"""
        # Stop the safety timer
        self._loading_timer.stop()
        
        self.is_loading = False
        
        # Clear the table
        self.table.setRowCount(0)
        
        # Show error message
        error_row = self.table.rowCount()
        self.table.setRowCount(error_row + 1)
        self.table.setSpan(error_row, 0, 1, self.table.columnCount())
        
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.setContentsMargins(20, 30, 20, 30)
        
        error_text = QLabel(f"Error: {error_message}")
        error_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_text.setStyleSheet("color: #ff6b6b; font-size: 14px;")
        error_text.setWordWrap(True)
        
        error_layout.addWidget(error_text)
        
        self.table.setCellWidget(error_row, 0, error_widget)
        
        # Log the error
        print(f"Error loading charts: {error_message}")
    
    def on_load_more_error(self, error_message):
        """Handle error when loading more data"""
        # Stop the safety timer
        self._loading_timer.stop()
        
        # Remove the loading indicator row
        self.table.setRowCount(self.table.rowCount() - 1)
        
        self.is_loading_more = False
        
        # Show a temporary error message at the bottom of the table
        row = self.table.rowCount()
        self.table.setRowCount(row + 1)
        self.table.setSpan(row, 0, 1, self.table.columnCount())
        
        error_widget = QWidget()
        error_layout = QHBoxLayout(error_widget)
        error_layout.setContentsMargins(10, 5, 10, 5)
        
        error_text = QLabel(f"Error loading more charts: {error_message}")
        error_text.setStyleSheet("color: #ff6b6b; font-size: 12px;")
        error_text.setWordWrap(True)
        
        error_layout.addWidget(error_text)
        
        self.table.setCellWidget(row, 0, error_widget)
        
        # Log the error
        print(f"Error loading more charts: {error_message}")
        
        # Remove the error message after 5 seconds
        QTimer.singleShot(5000, lambda: self.table.setRowCount(self.table.rowCount() - 1))
    
    def populate_table(self, data):
        """Populate the table with chart data"""
        # Set row count
        self.table.setRowCount(len(data))
        
        # Fill the table
        for row, chart in enumerate(data):
            self.populate_chart_row(row, chart)
    
    def populate_chart_row(self, row, chart):
        """
        Populate a single row with chart data, including icons
        
        Args:
            row: The row index
            chart: Chart data dictionary
        """
        # Set row height
        self.table.setRowHeight(row, 42)  # Further reduced from 45
        
        # Extract chart data with proper defaults
        chart_name = chart.get("name", "Unknown")
        description = chart.get("description", "No description available")
        version = chart.get("version", "N/A")
        app_version = chart.get("app_version", "N/A")
        repository = chart.get("repository", "Unknown")
        
        # If description is too long, truncate it
        if len(description) > 100:
            description = description[:100] + "..."
        
        # Create icon widget for column 0
        icon_widget = QWidget()
        icon_layout = QHBoxLayout(icon_widget)
        icon_layout.setContentsMargins(0, 0, 0, 0)  # Zero padding
        icon_layout.setSpacing(0)  # No spacing
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add icon if available
        icon_label = QLabel()
        icon_label.setFixedSize(28, 28)  # Further reduced from 32x32
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                border-radius: 3px;
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        icon_path = chart.get("icon_path")
        if icon_path and os.path.exists(icon_path):
            try:
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)  # Further reduced from 28x28
                    icon_label.setPixmap(pixmap)
                else:
                    # If pixmap is null, show a placeholder text
                    icon_label.setText("📦")
                    icon_label.setStyleSheet("""
                        QLabel {
                            color: #aaaaaa;
                            font-size: 14px;  /* Further decreased */
                            border-radius: 3px;
                            background-color: rgba(255, 255, 255, 0.05);
                            border: none;
                            padding: 0px;
                            margin: 0px;
                        }
                    """)
            except Exception as e:
                print(f"Error loading icon for {chart_name}: {e}")
                icon_label.setText("📦")
                icon_label.setStyleSheet("""
                    QLabel {
                        color: #aaaaaa;
                        font-size: 14px;  /* Further decreased */
                        border-radius: 3px;
                        background-color: rgba(255, 255, 255, 0.05);
                        border: none;
                        padding: 0px;
                        margin: 0px;
                    }
                """)
        else:
            # No icon available, show placeholder
            icon_label.setText("📦")
            icon_label.setStyleSheet("""
                QLabel {
                    color: #aaaaaa;
                    font-size: 14px;  /* Further decreased */
                    border-radius: 3px;
                    background-color: rgba(255, 255, 255, 0.05);
                    border: none;
                    padding: 0px;
                    margin: 0px;
                }
            """)
        
        icon_layout.addWidget(icon_label)
        self.table.setCellWidget(row, 0, icon_widget)
        
        # Create data items for the text columns
        columns = [chart_name, description, version, app_version, repository]
        
        for col, value in enumerate(columns, 1):  # Start at column 1 (after icon)
            # Create item
            item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col == 1:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setForeground(QColor("#e2e8f0"))
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor("#e2e8f0"))
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Add the item to the table
            self.table.setItem(row, col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, chart_name)
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(action_button)
        action_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, len(columns) + 1, action_container)  # +1 for icon column
    
    def _create_action_button(self, row, chart_name):
        """Create an action button with view details action"""
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(20)  # Further decreased from 24
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet("""
            QToolButton {
                color: #888888;
                font-size: 14px;  /* Further decreased from 16px */
                background: transparent;
                padding: 0px;
                margin: 0;
                border: none;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
                color: #ffffff;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create menu
        menu = QMenu(button)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                color: #ffffff;
                padding: 6px 20px 6px 24px;  /* Reduced padding */
                border-radius: 3px;
                font-size: 12px;  /* Reduced font size */
            }
            QMenu::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                color: #ffffff;
            }
        """)
        
        # Add view action
        view_action = menu.addAction("View Details")
        view_action.triggered.connect(lambda: self._handle_view_details(row))
        
        button.setMenu(menu)
        return button
    
    def _handle_view_details(self, row):
        """Handle view details action, showing detail page"""
        if row >= len(self.resources):
            return
            
        chart = self.resources[row]
        chart_name = chart.get("name", "Unknown")
        
        # Find the ClusterView instance
        parent = self.parent()
        while parent and not hasattr(parent, 'detail_manager'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'detail_manager'):
            # Prepare data for the detail page
            # Include more metadata from the enhanced API
            resource_data = {
                "kind": "Chart",
                "apiVersion": "helm.sh/v1",
                "metadata": {
                    "name": chart_name,
                    "creationTimestamp": chart.get("last_updated", ""),
                    "labels": {
                        "repository": chart.get("repository", "Unknown"),
                        "version": chart.get("version", ""),
                        "app_version": chart.get("app_version", ""),
                        "stars": chart.get("stars", "0")
                    },
                    "annotations": {
                        "description": chart.get("description", "")[:200],  # Limit description length
                        "repository_url": chart.get("repository_url", ""),
                        "package_id": chart.get("package_id", "")
                    }
                },
                "spec": {
                    "version": chart.get("version", ""),
                    "appVersion": chart.get("app_version", ""),
                    "repository": chart.get("repository", "Unknown"),
                },
                "status": {
                    "phase": "Available"
                }
            }
            
            # Add icon data if available
            icon_path = chart.get("icon_path")
            if icon_path and os.path.exists(icon_path):
                resource_data["metadata"]["annotations"]["icon_path"] = icon_path
            
            # Create a global reference to the current chart data for detail page
            import json
            global current_chart_data
            current_chart_data = json.dumps(resource_data)
            
            # Call the detail page
            parent.detail_manager.show_detail("chart", chart_name)
    
    def handle_search(self):
        """Handle search button click or enter key press in search bar"""
        if hasattr(self, 'is_searching') and self.is_searching:
            return
            
        # Get search text
        search_text = self.search_bar.text().strip()
        
        if not search_text:
            # If search bar is empty, reload all data
            self.is_searching = False
            self.load_data()
            return
        
        # Set searching flag
        self.is_searching = True
        
        # Clear the table and show loading indicator
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        # Add loading indicator
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setContentsMargins(20, 20, 20, 20)
        
        loading_bar = QProgressBar()
        loading_bar.setRange(0, 0)  # Indeterminate
        loading_bar.setTextVisible(False)
        loading_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                background-color: #1e1e1e;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
            }
        """)
        
        loading_text = QLabel(f"Searching for '{search_text}'...")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        # Start search thread
        self.search_thread = ChartSearchThread(search_text)
        self.search_thread.search_completed.connect(self.on_search_completed)
        self.search_thread.error_occurred.connect(self.on_search_error)
        self.search_thread.start()
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
            # If this is a direct click (not on action), show details
            if row < len(self.resources):
                self._handle_view_details(row)