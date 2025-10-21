"""
Enhanced implementation of the Charts page displaying Helm charts from ArtifactHub API.
Includes comprehensive search, filtering, and browsing capabilities with support for all repositories.
"""

from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QToolButton, QMenu, QTableWidgetItem, QProgressBar, QLineEdit, 
    QPushButton, QMessageBox, QDialog, QComboBox, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPixmap

import requests
import json
import os
import re
import hashlib
import logging
from urllib.parse import urljoin

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles


class ChartDataThread(QThread):
    """Thread for loading Helm charts from ArtifactHub API with comprehensive filtering."""
    data_loaded = pyqtSignal(list, bool)  # Data, is_more_available
    error_occurred = pyqtSignal(str)
    
    def __init__(self, limit=25, offset=0, search_term="", repository="", kind="helm", sort="relevance"):
        super().__init__()
        self.limit = limit
        self.offset = offset
        self.search_term = search_term
        self.repository = repository
        self.kind = kind  # helm, falco, opa, etc.
        self.sort = sort
        
        # Create directories for storing icons
        self.setup_directories()
        
        # Repository icons cache
        self.repository_icons = {}
        
    def setup_directories(self):
        """Set up directories for storing icons and cache"""
        self.icons_dir = os.path.join(os.path.expanduser('~'), '.artifacthub', 'icons')
        os.makedirs(self.icons_dir, exist_ok=True)
        
        self.default_icons_dir = os.path.join(os.path.expanduser('~'), '.artifacthub', 'default_icons')
        os.makedirs(self.default_icons_dir, exist_ok=True)
        
    def run(self):
        """Execute the API request and emit results."""
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            charts_data = []
            is_more_available = True
            
            # Use GET method directly (POST is blocked by CloudFront)
            try:
                endpoint = 'https://artifacthub.io/api/v1/packages/search'
                
                # Map kind names to string IDs for GET request
                kind_id = '0'  # Default to Helm
                if self.kind == "falco":
                    kind_id = '1'
                elif self.kind == "opa":
                    kind_id = '2'
                elif self.kind == "tekton":
                    kind_id = '5'
                
                params = {
                    'kind': kind_id,
                    'sort': self.sort,
                    'page': (self.offset // self.limit) + 1,
                    'limit': self.limit
                }
                
                if self.search_term:
                    params['ts_query_web'] = self.search_term
                
                if self.repository and self.repository != "all":
                    params['repo'] = self.repository
                
                logging.info(f"ChartDataThread: GET request to {endpoint} with params: {params}")
                
                response = session.get(endpoint, params=params, headers=headers, timeout=30)
                
                logging.info(f"ChartDataThread: GET response status: {response.status_code}")
                
                if response.status_code == 200:
                    page_data = response.json()
                    logging.info(f"ChartDataThread: GET returned {len(page_data.get('packages', []))} packages")
                    charts_data = self.process_api_data(page_data, session, headers)
                    is_more_available = len(charts_data) >= self.limit
                    logging.info(f"ChartDataThread: GET processed {len(charts_data)} charts")
                else:
                    logging.error(f"ChartDataThread: GET request failed with status {response.status_code}")

            except Exception as e:
                logging.error(f"ChartDataThread: GET request failed: {e}")
            
            logging.info(f"ChartDataThread: Emitting {len(charts_data)} charts, more_available: {is_more_available}")
            self.data_loaded.emit(charts_data, is_more_available)
            
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                user_msg = "Unable to connect to ArtifactHub. Please check your internet connection and try again."
            elif "json" in error_msg.lower():
                user_msg = "ArtifactHub API returned invalid data. Please try again later."
            else:
                user_msg = f"Error fetching charts from ArtifactHub: {error_msg}"
            
            logging.error(f"Charts API error: {e}")
            self.error_occurred.emit(user_msg)
    
    def process_api_data(self, api_data, session, headers):
        """Process API data to extract helm charts with icons"""
        charts = []
        
        if not api_data:
            return charts
        
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
                # Validate that this is actually a Helm chart
                package_kind = package.get('kind', 0)
                repository_kind = None
                if 'repository' in package and isinstance(package.get('repository'), dict):
                    repo = package.get('repository', {})
                    repository_kind = repo.get('kind', 0)
                
                # Skip if this is not a Helm chart (kind should be 0 for Helm)
                if self.kind == "helm" and package_kind != 0:
                    continue
                
                # Extract repository info
                repository = 'Unknown'
                repository_url = ''
                if 'repository' in package and isinstance(package.get('repository'), dict):
                    repo = package.get('repository', {})
                    repository = repo.get('name', 'Unknown')
                    repository_url = repo.get('url', '')
                
                # Extract chart data
                name = package.get('name', 'Unknown')
                if isinstance(name, dict) and 'name' in name:
                    name = name['name']
                
                description = package.get('description', 'No description available')
                version = package.get('version', 'N/A')
                app_version = package.get('app_version', None)
                if app_version is None and 'appVersion' in package:
                    app_version = package.get('appVersion', 'N/A')
                
                # Get stars and last updated
                stars = str(package.get('stars', 0))
                last_updated = package.get('last_updated', None)
                if not last_updated:
                    last_updated = package.get('created_at', '')
                
                # Store package_id for potential later use
                package_id = package.get('package_id', 'N/A')
                if package_id == 'N/A' and 'packageId' in package:
                    package_id = package.get('packageId', 'N/A')
                
                # Download icon if available
                icon_url, icon_path = self.download_icon(package, session, headers)
                
                # Add to charts list
                charts.append({
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
                pass
        
        return charts
    
    def download_icon(self, package, session, headers):
        """Download and save the package icon if available"""
        icon_url = None
        icon_path = None
        
        try:
            package_name = package.get('name', 'unknown')
            
            # Check for logo_image_id first (most reliable)
            if 'logo_image_id' in package and package['logo_image_id']:
                logo_id = package.get('logo_image_id')
                if logo_id:
                    icon_url = f"https://artifacthub.io/image/{logo_id}"
            
            # If no logo_image_id, check other possible icon fields
            if not icon_url:
                for field in ['logoURL', 'logo_url', 'logoImageId', 'logo', 'icon']:
                    if field in package and package[field]:
                        if field == 'logoImageId':
                            logo_id = package.get(field)
                            if logo_id:
                                icon_url = f"https://artifacthub.io/image/{logo_id}"
                        else:
                            icon_url = package.get(field)
                        break
                    
                # Check for nested repository structures
                if not icon_url and 'repository' in package and isinstance(package['repository'], dict):
                    repo = package['repository']
                    repo_logo_id = repo.get('logo_image_id') or repo.get('logoImageId')
                    
                    if repo_logo_id:
                        icon_url = f"https://artifacthub.io/image/{repo_logo_id}"
            
            # If icon URL starts with /, it's a relative URL
            if icon_url and icon_url.startswith('/'):
                icon_url = urljoin('https://artifacthub.io', icon_url)
            
            # If we found an icon URL, download it
            if icon_url:
                url_hash = hashlib.md5(icon_url.encode()).hexdigest()[:8]
                
                file_ext = os.path.splitext(icon_url)[1].lower()
                if not file_ext or len(file_ext) > 5:
                    file_ext = '.png'
                
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
                            icon_path = None
                    except Exception as e:
                        icon_path = None
        
        except Exception as e:
            icon_path = None
        
        return icon_url, icon_path


# Removed unused ChartSearchThread class - search functionality handled directly by ChartDataThread


class ChartsPage(BaseResourcePage):
    """
    Enhanced Helm charts page with comprehensive ArtifactHub integration.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resources = []
        self.offset = 0
        self.is_more_available = True
        self.is_loading_more = False
        self.is_searching = False
        self.is_loading = False
        self.resource_type = "charts"  # Set resource type for BaseResourcePage
        self.show_namespace_dropdown = False  # Charts are not namespaced
        
        # Add state management for chart installation
        self.installation_in_progress = False
        self.current_installation_dialog = None
        
        # Filter options
        self.current_repository = "all"
        self.current_kind = "helm"
        
        # Add a safety mechanism to recover from stuck loading states
        self._loading_timer = QTimer()
        self._loading_timer.timeout.connect(self._reset_loading_state)
        self._loading_timer.setSingleShot(True)
        
        # Disable automatic resource loading from BaseResourcePage
        self._disable_auto_loading = True
        
        # Override the base class resource loading to prevent it from trying to load "charts" as Kubernetes resources
        self.resource_type = None  # Clear resource type so base class doesn't try to load it
        
        # Initialize the UI
        self.setup_page_ui()
        
    def _reset_loading_state(self):
        """Reset loading state if it gets stuck - now delegates to _reset_all_states"""
        logging.info("ChartsPage._reset_loading_state: Delegating to _reset_all_states")
        self._reset_all_states()
        
        # Additional recovery logic specific to stuck states
        if hasattr(self, 'table'):
            # Remove any loading rows from table
            if self.table.rowCount() > 0:
                last_row = self.table.rowCount() - 1
                cell_widget = self.table.cellWidget(last_row, 0)
                if cell_widget and hasattr(cell_widget, 'findChild'):
                    progress_bar = cell_widget.findChild(QProgressBar)
                    if progress_bar:
                        self.table.setRowCount(last_row)
            
            # If we have resources but no visible rows, repopulate table
            if hasattr(self, 'resources') and self.resources and self.table.rowCount() == 0:
                logging.info("ChartsPage._reset_loading_state: Repopulating table with existing data")
                self.populate_table(self.resources)
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Charts page"""
        headers = ["", "Name", "Description", "Version", "App Version", "Repository", "Stars", ""]
        sortable_columns = {1, 3, 4, 5, 6}
        
        layout = super().setup_ui("Helm Charts", headers, sortable_columns)
        
        # Namespace dropdown is already disabled via show_namespace_dropdown = False
        
        # Connect inherited search bar to chart search functionality
        if hasattr(self, 'search_bar'):
            self.search_bar.setPlaceholderText("Search Helm charts...")
            # Disconnect default search behavior and connect our custom search
            try:
                self.search_bar.textChanged.disconnect()
            except:
                pass
            # Connect our custom search handlers
            self.search_bar.textChanged.connect(self._on_search_text_changed)
            self.search_bar.returnPressed.connect(self.handle_search)
        
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        self.configure_columns()
        
        scrollbar = self.table.verticalScrollBar()
        scrollbar.valueChanged.connect(self.check_scroll_position)
        
        if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox:
            self.select_all_checkbox.hide()
        
        # Override the base class refresh mechanism completely
        # Find and reconnect the refresh button after the UI is set up
        QTimer.singleShot(100, self._override_refresh_button)
        
        # Load initial data from ArtifactHub (not Kubernetes)
        self.load_chart_data()
        
        return layout
    
    def _add_filter_controls(self, header_layout):
        """Override to add chart-specific filter controls with proper layout"""
        # Call parent to add search bar first
        super()._add_filter_controls(header_layout)
        
        # Create a container widget for our additional filters to prevent overlap
        additional_filters_container = QWidget()
        additional_filters_layout = QHBoxLayout(additional_filters_container)
        additional_filters_layout.setContentsMargins(10, 5, 10, 5)  # Add margins around container
        additional_filters_layout.setSpacing(15)  # Increase base spacing
        
        # Repository filter
        repo_label = QLabel("Repository:")
        repo_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: normal;")
        repo_label.setMinimumWidth(70)
        
        self.repository_combo = QComboBox()
        self.repository_combo.addItems([
            "all", "bitnami", "stable", "prometheus-community", 
            "grafana", "jetstack", "ingress-nginx", "elastic", "hashicorp"
        ])
        self.repository_combo.setCurrentText(self.current_repository)
        self.repository_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
        self.repository_combo.currentTextChanged.connect(self.on_repository_changed)
        self.repository_combo.setFixedWidth(150)
        self.repository_combo.setFixedHeight(32)
        
        # Note: Repository combo z-index handled by Qt automatically
        
        # Kind is fixed to helm only - no dropdown needed
        
        # Add widgets to the container layout with proper spacing
        additional_filters_layout.addWidget(repo_label)
        additional_filters_layout.addWidget(self.repository_combo)
        additional_filters_layout.addSpacing(20)  # Space after repository dropdown
        additional_filters_layout.addStretch()  # Add stretch to prevent expansion
        
        # Add the container to the header layout with proper spacing
        header_layout.addSpacing(30)  # Increased space before our controls
        header_layout.addWidget(additional_filters_container)
    
    
    def on_repository_changed(self, repository):
        """Handle repository filter change"""
        self.current_repository = repository
        # Force reload for repository change
        self._force_reload = True
        self.load_data()
    
    def _override_refresh_button(self):
        """Override the refresh button connection after UI setup"""
        # Find refresh button in the widget hierarchy
        refresh_buttons = self.findChildren(QPushButton)
        for btn in refresh_buttons:
            if btn.text() == "Refresh":
                try:
                    # Disconnect all existing connections
                    btn.clicked.disconnect()
                    # Connect to our custom refresh method
                    btn.clicked.connect(self.refresh_data)
                    logging.info("ChartsPage: Successfully overrode refresh button connection")
                    break
                except:
                    pass
    
    def refresh_data(self):
        """Force refresh of chart data - called by refresh button"""
        logging.info("ChartsPage.refresh_data: Force refreshing chart data")
        # Reset all states immediately
        self._reset_all_states()
        # Clear data and force reload
        self.resources = []
        self.offset = 0
        self._force_reload = True
        # Load fresh data
        self.load_chart_data()
    
    def force_load_data(self):
        """Override BaseResourcePage force_load_data to use our refresh method"""
        logging.info("ChartsPage.force_load_data: Redirecting to chart refresh")
        self.refresh_data()
    
    def _reset_all_states(self):
        """Reset all loading and search states"""
        self.is_loading = False
        self.is_loading_more = False
        self.is_searching = False
        # Cancel any running threads
        if hasattr(self, 'chart_thread') and self.chart_thread and self.chart_thread.isRunning():
            self.chart_thread.terminate()
            self.chart_thread.wait(1000)
        if hasattr(self, 'more_thread') and self.more_thread and self.more_thread.isRunning():
            self.more_thread.terminate()
            self.more_thread.wait(1000)
        # Stop timers
        if hasattr(self, '_loading_timer'):
            self._loading_timer.stop()
        if hasattr(self, '_search_timeout') and self._search_timeout:
            self._search_timeout.stop()
            self._search_timeout = None
        # Hide loading indicators
        super().hide_loading_indicator()
    
    def showEvent(self, event):
        """Handle show event to ensure proper state when page becomes visible"""
        super().showEvent(event)
        logging.info("ChartsPage.showEvent: Page becoming visible")
        
        # Reset any stuck states immediately
        self._reset_all_states()
        
        # Ensure table is visible and enabled
        if hasattr(self, 'table'):
            self.table.setEnabled(True)
            if hasattr(self, '_table_stack') and self._table_stack:
                self._table_stack.setCurrentWidget(self.table)
            
            # If we have no data, load it
            if not hasattr(self, 'resources') or not self.resources:
                QTimer.singleShot(100, self.load_chart_data)
        
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        fixed_widths = {
            0: 50,   # Icon
            1: 180,  # Name
            3: 100,  # Version
            4: 120,  # App Version
            5: 150,  # Repository
            6: 80,   # Stars
            7: 40    # Actions
        }
        
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    
    # Removed empty _on_resources_loaded override - not needed
    
    def _on_search_text_changed(self, text):
        """Override to use ArtifactHub search instead of local filtering"""
        # Cancel any existing search
        if hasattr(self, 'search_thread') and self.search_thread and self.search_thread.isRunning():
            self.search_thread.terminate()
            self.search_thread.wait()
        
        if len(text.strip()) >= 2:  # Start searching after 2 characters
            # Use QTimer to debounce search
            if not hasattr(self, '_search_timer'):
                self._search_timer = QTimer()
                self._search_timer.setSingleShot(True)
                self._search_timer.timeout.connect(self.handle_search)
            
            self._search_timer.stop()
            self._search_timer.start(300)  # 300ms debounce
        elif len(text.strip()) == 0:  # Clear search when empty
            # Clear search state immediately
            self.is_searching = False
            # Stop any active search timer
            if hasattr(self, '_search_timer'):
                self._search_timer.stop()
            # Cancel any running search thread
            if hasattr(self, 'search_thread') and self.search_thread and self.search_thread.isRunning():
                self.search_thread.terminate()
                self.search_thread.wait()
            # Cancel any running chart thread
            if hasattr(self, 'chart_thread') and self.chart_thread and self.chart_thread.isRunning():
                self.chart_thread.terminate()
                self.chart_thread.wait()
            # Clean up search timeout
            if hasattr(self, '_search_timeout') and self._search_timeout:
                self._search_timeout.stop()
                self._search_timeout = None
            # Hide any loading indicator
            super().hide_loading_indicator()
            # Force reload of default data by clearing resources first
            self.resources = []
            self.offset = 0
            self.is_loading = False
            self.is_loading_more = False
            # Now load default data
            self.load_chart_data()
    
    def load_data(self, load_more=False):
        """Override BaseResourcePage load_data to load from ArtifactHub"""
        self.load_chart_data(load_more)
    
    def _auto_load_data(self):
        """Override auto load data to properly handle chart loading"""
        logging.info("ChartsPage._auto_load_data: Auto-loading called")
        # Reset states first
        self._reset_all_states()
        
        # Always ensure proper UI state
        if hasattr(self, 'table'):
            self.table.setEnabled(True)
            if hasattr(self, '_table_stack') and self._table_stack:
                self._table_stack.setCurrentWidget(self.table)
        
        # Load data if we don't have any
        if not hasattr(self, 'resources') or not self.resources:
            logging.info("ChartsPage._auto_load_data: No data present, loading")
            self.load_chart_data()
        else:
            logging.info(f"ChartsPage._auto_load_data: Data already present ({len(self.resources)} items), ensuring table visibility")
            # Ensure existing data is visible
            if hasattr(self, 'table') and self.table.rowCount() == 0 and self.resources:
                self.populate_table(self.resources)
    
    def load_chart_data(self, load_more=False):
        """Load chart data from ArtifactHub API"""
        logging.info(f"ChartsPage.load_chart_data: Called with load_more={load_more}")
        
        # Check if already loading to prevent duplicate requests
        if hasattr(self, 'is_loading') and self.is_loading:
            logging.info("ChartsPage.load_chart_data: Already loading, returning")
            return
        
        # Don't load default data if we're currently searching
        if hasattr(self, 'is_searching') and self.is_searching:
            logging.info("ChartsPage.load_chart_data: Skipping default load because search is active")
            return
            
        # If this is a load_more request, delegate to load_more_data method
        if load_more:
            logging.info("ChartsPage.load_chart_data: Load more requested, delegating to load_more_data")
            self.load_more_data()
            return
            
        # Clear force reload flag if it was set
        force_reload = getattr(self, '_force_reload', False)
        if hasattr(self, '_force_reload'):
            self._force_reload = False
            
        # If we already have data and this isn't a load_more or forced request, just ensure UI state
        if (hasattr(self, 'resources') and self.resources and len(self.resources) > 0 
            and not load_more and not force_reload):
            logging.info(f"ChartsPage.load_chart_data: Data already loaded ({len(self.resources)} items), ensuring UI state")
            # Ensure table is visible and enabled
            if hasattr(self, '_table_stack') and self._table_stack:
                self._table_stack.setCurrentWidget(self.table)
            self.table.setEnabled(True)
            self.table.show()
            # Ensure data is displayed
            if self.table.rowCount() == 0:
                self.populate_table(self.resources)
            return
            
        logging.info("ChartsPage.load_chart_data: Starting default data load")
        
        # Clean up any existing thread
        if hasattr(self, 'chart_thread') and self.chart_thread and self.chart_thread.isRunning():
            self.chart_thread.terminate()
            self.chart_thread.wait(1000)
        
        self.is_loading = True
        
        # Only reset resources and offset if this isn't a load_more request
        if not load_more:
            self.resources = []
            self.offset = 0
        
        self.is_more_available = True
        
        self._loading_timer.start(15000)
        
        # Only clear table if this isn't a load_more request
        if not load_more:
            self.table.setRowCount(0)
            self.table.setSortingEnabled(False)
            # Use inherited loading indicator
            super().show_loading_indicator("Loading Helm charts from ArtifactHub API...")
        else:
            logging.info("ChartsPage.load_chart_data: Load more request, keeping existing data")
        
        self.chart_thread = ChartDataThread(
            limit=25, offset=self.offset, 
            repository=self.current_repository,
            kind=self.current_kind,
            sort="relevance"
        )
        self.chart_thread.data_loaded.connect(self.on_data_loaded)
        self.chart_thread.error_occurred.connect(self.on_load_error)
        self.chart_thread.start()

    def load_more_data(self):
        """Load more chart data when user scrolls to bottom"""
        if not self.is_more_available or self.is_loading_more:
            return
            
        self.is_loading_more = True
        
        self._loading_timer.start(15000)
        
        self.offset = len(self.resources)
        
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QHBoxLayout(loading_widget)
        loading_layout.setContentsMargins(10, 5, 10, 5)
        
        loading_bar = QProgressBar()
        loading_bar.setRange(0, 0)
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
        
        self.more_thread = ChartDataThread(
            limit=25, offset=self.offset,
            repository=self.current_repository,
            kind=self.current_kind,
            sort="relevance"
        )
        self.more_thread.data_loaded.connect(self.on_more_data_loaded)
        self.more_thread.error_occurred.connect(self.on_load_more_error)
        self.more_thread.start()
    
    def on_data_loaded(self, data, is_more_available):
        """Handle loaded chart data for initial load"""
        logging.info(f"ChartsPage.on_data_loaded: Received {len(data) if data else 0} charts, is_searching={getattr(self, 'is_searching', False)}")
        
        # Don't handle default data if we're currently searching
        if hasattr(self, 'is_searching') and self.is_searching:
            logging.info("ChartsPage.on_data_loaded: Ignoring default data load because search is active")
            return
        
        self._loading_timer.stop()
        super().hide_loading_indicator()
        
        # Clean up the thread
        if hasattr(self, 'chart_thread') and self.chart_thread:
            self.chart_thread.deleteLater()
            self.chart_thread = None
        
        self.is_loading = False
        self.resources = data
        
        self.is_more_available = True if data else False
        
        # Ensure table is visible
        if hasattr(self, '_table_stack') and self._table_stack:
            logging.info("ChartsPage.on_data_loaded: Setting table as current widget")
            self._table_stack.setCurrentWidget(self.table)
        
        if data:
            repo_text = f" from {self.current_repository}" if self.current_repository != "all" else ""
            self.items_count.setText(f"{len(data)} Helm charts{repo_text}")
            
            logging.info(f"ChartsPage.on_data_loaded: Populating table with {len(data)} charts")
            self.table.setRowCount(0)
            self.populate_table(data)
            
            self.table.setSortingEnabled(True)
            self.table.show()
            self.table.setEnabled(True)
            
            logging.info("ChartsPage.on_data_loaded: Table populated and visible")
        else:
            logging.info("ChartsPage.on_data_loaded: No data received, showing empty message")
            # Use inherited empty message functionality
            super()._show_empty_message()
            self.items_count.setText("0 items")
    
    def populate_table(self, charts, append=False):
        """Populate table with chart data"""
        logging.info(f"ChartsPage.populate_table: Starting to populate table with {len(charts)} charts, append={append}")
        
        if not append:
            self.table.setRowCount(0)
            self.table.setSortingEnabled(False)
            start_row = 0
        else:
            start_row = self.table.rowCount()
            self.table.setSortingEnabled(False)
        
        for i, chart in enumerate(charts):
            row_index = start_row + i
            self.table.setRowCount(row_index + 1)
            self.populate_chart_row(row_index, chart)
        
        logging.info(f"ChartsPage.populate_table: Finished populating table with {self.table.rowCount()} rows")
        self.table.setSortingEnabled(True)
    
    def on_more_data_loaded(self, data, is_more_available):
        """Handle loaded chart data for load-more operation"""
        self._loading_timer.stop()
        
        # Clean up the thread
        if hasattr(self, 'more_thread') and self.more_thread:
            self.more_thread.deleteLater()
            self.more_thread = None
        
        self.table.setRowCount(self.table.rowCount() - 1)
        
        self.is_loading_more = False
        
        if data:
            self.is_more_available = True
            
            self.resources.extend(data)
            
            was_sorting_enabled = self.table.isSortingEnabled()
            self.table.setSortingEnabled(False)
            
            start_row = self.table.rowCount()
            self.table.setRowCount(start_row + len(data))
            
            for i, chart in enumerate(data):
                self.populate_chart_row(start_row + i, chart)
            
            self.table.setSortingEnabled(was_sorting_enabled)
            
            self.offset = len(self.resources)
            
            repo_text = f" from {self.current_repository}" if self.current_repository != "all" else ""
            self.items_count.setText(f"{len(self.resources)} {self.current_kind}")
        else:
            self.is_more_available = False
        
        if not hasattr(self, '_scroll_handler_connected'):
            self.table.verticalScrollBar().valueChanged.connect(self._on_scroll)
            self._scroll_handler_connected = True

    def _on_scroll(self, value):
        if self.is_loading or not self.is_more_available:
            return
        
        scrollbar = self.table.verticalScrollBar()
        if value >= scrollbar.maximum() * 0.9: 
            self.load_data(load_more=True)
    
    def on_load_error(self, error_message):
        """Handle loading errors"""
        self._loading_timer.stop()
        super().hide_loading_indicator()
        
        # Clean up the thread
        if hasattr(self, 'chart_thread') and self.chart_thread:
            self.chart_thread.deleteLater()
            self.chart_thread = None
        
        self.is_loading = False
        
        # Use inherited empty message with error context
        super()._show_empty_message()
        self.items_count.setText("0 items")
    
    def on_load_more_error(self, error_message):
        """Handle load more errors"""
        self._loading_timer.stop()
        self.is_loading_more = False
        if self.table.rowCount() > 0:
            self.table.setRowCount(self.table.rowCount() - 1)
    
    def check_scroll_position(self, value):
        """Check if the user has scrolled to the bottom and load more charts"""
        if self.is_loading or self.is_loading_more or not self.is_more_available:
            return

        scrollbar = self.table.verticalScrollBar()

        if value >= scrollbar.maximum() - (2 * self.table.rowHeight(0)):
            self.load_more_data()

    def populate_resource_row(self, row, chart):
        self.populate_chart_row(row, chart)

    def populate_chart_row(self, row, chart):
        """Populate a row with chart data"""
        logging.info(f"ChartsPage.populate_chart_row: Creating row {row} for chart: {chart.get('name', 'Unknown')}")
        self.table.setRowHeight(row, 42)
        
        chart_name = chart.get("name", "Unknown")
        description = chart.get("description", "No description available")
        version = chart.get("version", "N/A")
        app_version = chart.get("app_version", "N/A")
        repository = chart.get("repository", "unknown")
        stars = chart.get("stars", "0")
        
        if len(description) > 100:
            description = description[:100] + "..."
        
        # Create icon widget for column 0
        icon_widget = QWidget()
        icon_layout = QHBoxLayout(icon_widget)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel()
        icon_label.setFixedSize(28, 28)
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
                    pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    icon_label.setPixmap(pixmap)
                else:
                    icon_label.setText("📦")
                    icon_label.setStyleSheet("""
                        QLabel {
                            color: #4CAF50;
                            font-size: 14px;
                            border-radius: 3px;
                            background-color: rgba(255, 255, 255, 0.05);
                            border: none;
                            padding: 0px;
                            margin: 0px;
                        }
                    """)
            except Exception as e:
                icon_label.setText("📦")
                icon_label.setStyleSheet("""
                    QLabel {
                        color: #4CAF50;
                        font-size: 14px;
                        border-radius: 3px;
                        background-color: rgba(255, 255, 255, 0.05);
                        border: none;
                        padding: 0px;
                        margin: 0px;
                    }
                """)
        else:
            icon_label.setText("📦")
            icon_label.setStyleSheet("""
                QLabel {
                    color: #4CAF50;
                    font-size: 14px;
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
        columns = [chart_name, description, version, app_version, repository, stars]
        
        for col, value in enumerate(columns, 1):
            item = SortableTableWidgetItem(str(value))
            
            if col == 1:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setForeground(QColor("#e2e8f0"))
            elif col == 6:  # Stars column
                try:
                    sort_value = int(value)
                except (ValueError, TypeError):
                    sort_value = 0
                item = SortableTableWidgetItem(value, sort_value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor("#ffd700"))
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor("#e2e8f0"))
            
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            self.table.setItem(row, col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, chart_name)
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 1, action_container)
   
    def _create_action_button(self, row, chart_name):
        """Create a standard more action button following the app's pattern"""
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize
        from UI.Icons import resource_path
        from UI.Styles import AppConstants
        from functools import partial
        
        button = QToolButton()

        # Use custom SVG icon instead of text
        icon = resource_path("Icons/Moreaction_Button.svg")
        button.setIcon(QIcon(icon))
        button.setIconSize(QSize(AppConstants.SIZES["ICON_SIZE"], AppConstants.SIZES["ICON_SIZE"]))

        # Remove text and change to icon-only style
        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        button.setFixedWidth(30)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create menu
        menu = QMenu(button)
        menu.setStyleSheet(AppStyles.MENU_STYLE)

        # Connect signals to change row appearance when menu opens/closes
        menu.aboutToShow.connect(lambda: self._highlight_active_row(row, True))
        menu.aboutToHide.connect(lambda: self._highlight_active_row(row, False))

        actions = [
            {"text": "View Details", "icon": "Icons/details.png", "dangerous": False},
            {"text": "Install Chart", "icon": "Icons/install.png", "dangerous": False}
        ]

        # Add actions to menu
        for action_info in actions:
            action = menu.addAction(action_info["text"])
            if "icon" in action_info:
                try:
                    action.setIcon(QIcon(resource_path(action_info["icon"])))
                except:
                    pass  # Icon loading failed, continue without icon
            if action_info.get("dangerous", False):
                action.setProperty("dangerous", True)
            action.triggered.connect(
                partial(self._handle_action, action_info["text"], row)
            )

        button.setMenu(menu)
        return button
    
    def _handle_install_chart(self, row):
        """Handle chart installation with duplicate prevention"""
        if row >= len(self.resources):
            return
        
        # Prevent multiple installations from running simultaneously
        if self.installation_in_progress:
            QMessageBox.warning(self, "Installation in Progress", 
                               "Another chart installation is already in progress. Please wait for it to complete.")
            return
            
        chart = self.resources[row]
        chart_name = chart.get("name", "Unknown")
        repository = chart.get("repository", "")
        
        if not repository:
            QMessageBox.critical(self, "Installation Error", "Repository information is missing for this chart.")
            return
        
        # Import the install dialog
        from Utils.helm_utils import ChartInstallDialog, install_helm_chart
        
        # Create and show install dialog
        dialog = ChartInstallDialog(chart_name, repository, self)
        
        # Store reference to prevent multiple dialogs
        if self.current_installation_dialog is not None:
            return  # Dialog already open
        
        self.current_installation_dialog = dialog
        
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get installation options
                options = dialog.get_values()
                
                if options:
                    # Set installation state
                    self.installation_in_progress = True
                    
                    try:
                        # Start installation
                        success, message = install_helm_chart(chart_name, repository, options, self)
                        
                        # Show single result dialog
                        if success:
                            QMessageBox.information(self, "Installation Successful", 
                                                   f"Chart '{chart_name}' has been successfully installed!\n\n{message}")
                        else:
                            QMessageBox.critical(self, "Installation Failed", 
                                               f"Failed to install chart '{chart_name}'.\n\n{message}")
                    finally:
                        # Reset installation state
                        self.installation_in_progress = False
        finally:
            # Clear dialog reference
            self.current_installation_dialog = None

    def _handle_action(self, action, row):
        """Handle action button menu selections"""
        if action == "View Details":
            self._handle_view_details(row)
        elif action == "Install Chart":
            self._handle_install_chart(row)
    
    def _highlight_active_row(self, row, highlight):
        """Highlight row when action menu is open"""
        if not self.table or row >= self.table.rowCount():
            return
            
        # Get the background color based on highlight state
        if highlight:
            bg_color = QColor(AppColors.SELECTED_BG)
        else:
            bg_color = QColor(AppColors.BG_MEDIUM)
        
        # Apply to all cells in the row
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(bg_color)
    
    def _handle_view_details(self, row):
        """Handle view details action for charts"""
        if row >= len(self.resources):
            return
            
        chart = self.resources[row]
        chart_name = chart.get("name", "Unknown")
        
        # Find the ClusterView instance to use its detail manager
        parent = self.parent()
        while parent and not hasattr(parent, 'detail_manager'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'detail_manager'):
            # Create a mock Kubernetes resource structure for Helm chart
            resource_data = {
                "kind": "HelmChart",
                "apiVersion": "helm.sh/v1",
                "metadata": {
                    "name": chart_name,
                    "creationTimestamp": chart.get("last_updated", ""),
                    "labels": {
                        "repository": chart.get("repository", ""),
                        "version": chart.get("version", ""),
                        "appVersion": chart.get("app_version", ""),
                        "stars": chart.get("stars", "0")
                    },
                    "annotations": {
                        "description": chart.get("description", ""),
                        "repository_url": chart.get("repository_url", ""),
                        "package_id": chart.get("package_id", ""),
                        "source": "ArtifactHub"
                    }
                },
                "spec": {
                    "version": chart.get("version", ""),
                    "appVersion": chart.get("app_version", ""),
                    "repository": chart.get("repository", ""),
                },
                "status": {
                    "phase": "Available"
                }
            }
            
            # Add icon path if available
            try:
                icon_path = chart.get("icon_path")
                if icon_path and isinstance(icon_path, str) and os.path.exists(icon_path):
                    resource_data["metadata"]["annotations"]["icon_path"] = icon_path
            except Exception:
                pass
            
            # Show detail page using the detail manager
            parent.detail_manager.show_detail("chart", chart_name, namespace=None, raw_data=resource_data)
        else:
            # Fallback to dialog if detail manager is not available
            self._show_chart_detail_dialog(chart)
    
    def handle_search(self):
        """Handle search button click or enter key press in search bar for charts"""
        if hasattr(self, 'is_loading') and self.is_loading:
            logging.info("ChartsPage.handle_search: Loading in progress, skipping")
            return
            
        # Use inherited search bar
        search_bar = getattr(self, 'search_bar', None)
        if not search_bar:
            logging.warning("ChartsPage.handle_search: No search bar found")
            return
            
        search_text = search_bar.text().strip()
        logging.info(f"ChartsPage.handle_search: Starting search for '{search_text}'")
        
        if not search_text:
            logging.info("ChartsPage.handle_search: Empty search, loading default data")
            self.is_searching = False
            self.load_chart_data()
            return
        
        # Clean up any existing search thread
        if hasattr(self, 'chart_thread') and self.chart_thread and self.chart_thread.isRunning():
            self.chart_thread.terminate()
            self.chart_thread.wait(1000)
        
        logging.info(f"ChartsPage.handle_search: Setting is_searching=True for search: '{search_text}'")
        self.is_searching = True
        self.is_loading = True
        self.current_search_term = search_text
        
        # Clear table and show loading spinner
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        # Show loading spinner for search using inherited functionality
        super().show_loading_indicator(f"Searching Helm charts for '{search_text}'...")
        
        # Use the same ChartDataThread but with search term
        self.chart_thread = ChartDataThread(
            limit=25, offset=0, search_term=search_text,
            repository=self.current_repository, kind=self.current_kind, sort="relevance"
        )
        self.chart_thread.data_loaded.connect(self.on_search_data_loaded)
        self.chart_thread.error_occurred.connect(self.on_search_error)
        
        # Add a timeout for search to prevent getting stuck
        if hasattr(self, '_search_timeout') and self._search_timeout:
            self._search_timeout.stop()
            
        search_timeout = QTimer()
        search_timeout.setSingleShot(True)
        search_timeout.timeout.connect(lambda: self._handle_search_timeout(search_text))
        search_timeout.start(15000)  # 15 second timeout
        self._search_timeout = search_timeout
        
        self.chart_thread.start()
    
    def on_search_data_loaded(self, data, is_more_available):
        """Handle search data loaded from ChartDataThread"""
        logging.info(f"ChartsPage.on_search_data_loaded: Received {len(data)} search results")
        
        # Clean up timeout timer
        if hasattr(self, '_search_timeout') and self._search_timeout:
            self._search_timeout.stop()
            self._search_timeout = None
            
        # Clean up the thread
        if hasattr(self, 'chart_thread') and self.chart_thread:
            self.chart_thread.deleteLater()
            self.chart_thread = None
            
        super().hide_loading_indicator()
        self.is_searching = False
        self.is_loading = False
        self.resources = data
        
        # Ensure table is visible
        if hasattr(self, '_table_stack') and self._table_stack:
            self._table_stack.setCurrentWidget(self.table)
        
        if data:
            logging.info(f"ChartsPage.on_search_data_loaded: Populating table with {len(data)} search results")
            self.table.setRowCount(0)
            self.populate_table(data)
            
            self.table.setSortingEnabled(True)
            self.table.show()
            self.table.setEnabled(True)
            
            # Update items count
            search_term = getattr(self, 'current_search_term', 'unknown')
            self.items_count.setText(f"{len(data)} search for'{search_term}'")
            logging.info("ChartsPage.on_search_data_loaded: Search results displayed")
        else:
            logging.info("ChartsPage.on_search_data_loaded: No search results found")
            super()._show_empty_message()
            search_term = getattr(self, 'current_search_term', 'unknown')
            self.items_count.setText(f"No results found for '{search_term}'")
            self.table.setEnabled(True)
    
    # Removed duplicate on_search_completed method - functionality handled by on_search_data_loaded
    
    def on_search_error(self, error_message):
        """Handle search errors"""
        # Clean up timeout timer
        if hasattr(self, '_search_timeout') and self._search_timeout:
            self._search_timeout.stop()
            self._search_timeout = None
            
        # Clean up the thread
        if hasattr(self, 'chart_thread') and self.chart_thread:
            self.chart_thread.deleteLater()
            self.chart_thread = None
            
        super().hide_loading_indicator()  # Ensure loading indicator is hidden
        self.is_searching = False
        self.is_loading = False
        
        # Show error message and enable table
        if hasattr(self, '_table_stack') and self._table_stack:
            self._table_stack.setCurrentWidget(self.table)
        self.table.setEnabled(True)
        
        # Show empty message for error
        super()._show_empty_message()
        self.items_count.setText(f"Search failed: {error_message}")
    
    def _handle_search_timeout(self, search_text):
        """Handle search timeout"""
        if hasattr(self, 'search_thread') and self.search_thread and self.search_thread.isRunning():
            self.search_thread.terminate()
            self.search_thread.wait()
        
        self.on_search_error("Search timed out. Please try again.")
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:
            self.table.selectRow(row)
            
            if row < len(self.resources):
                self._handle_view_details(row)
    
    # Removed _apply_filters method - search is handled server-side via ArtifactHub API
    
    def _show_chart_detail_dialog(self, chart):
        """Show a detailed dialog for the selected Helm chart"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QTextEdit, QGroupBox
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QFont, QPixmap
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Chart Details - {chart.get('name', 'Unknown')}")
        dialog.setMinimumSize(800, 600)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 8px;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        
        # Main layout
        layout = QVBoxLayout(dialog)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Header section with icon and basic info
        header_group = QGroupBox("Chart Information")
        header_layout = QHBoxLayout(header_group)
        
        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("border: 1px solid #ddd; border-radius: 8px;")
        
        # Try to load chart icon
        icon_path = chart.get("icon_path")
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)
            else:
                icon_label.setText("📦")
        else:
            icon_label.setText("📦")
        
        # Basic info
        info_layout = QVBoxLayout()
        
        # Name
        name_label = QLabel(f"<h2>{chart.get('name', 'Unknown')}</h2>")
        name_label.setStyleSheet("color: #2196F3; margin-bottom: 5px;")
        info_layout.addWidget(name_label)
        
        # Version and App Version
        version_label = QLabel(f"<b>Version:</b> {chart.get('version', 'N/A')} | <b>App Version:</b> {chart.get('app_version', 'N/A')}")
        info_layout.addWidget(version_label)
        
        # Repository
        repo_label = QLabel(f"<b>Repository:</b> {chart.get('repository', 'N/A')}")
        info_layout.addWidget(repo_label)
        
        # Stars
        stars_label = QLabel(f"<b>Stars:</b> ⭐ {chart.get('stars', '0')}")
        info_layout.addWidget(stars_label)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        scroll_layout.addWidget(header_group)
        
        # Description section
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_group)
        
        description = chart.get("description", "No description available.")
        desc_text = QTextEdit()
        desc_text.setPlainText(description)
        desc_text.setReadOnly(True)
        desc_text.setMaximumHeight(120)
        desc_text.setStyleSheet("QTextEdit { background-color: #f5f5f5; border: 1px solid #ddd; }")
        
        desc_layout.addWidget(desc_text)
        scroll_layout.addWidget(desc_group)
        
        # Additional information
        info_group = QGroupBox("Additional Information")
        info_layout = QVBoxLayout(info_group)
        
        # Last updated
        if chart.get("last_updated"):
            updated_label = QLabel(f"<b>Last Updated:</b> {chart.get('last_updated')}")
            info_layout.addWidget(updated_label)
        
        # Package ID
        if chart.get("package_id"):
            package_label = QLabel(f"<b>Package ID:</b> {chart.get('package_id')}")
            info_layout.addWidget(package_label)
        
        # Repository URL
        if chart.get("repository_url"):
            repo_url_label = QLabel(f"<b>Repository URL:</b> <a href='{chart.get('repository_url')}'>{chart.get('repository_url')}</a>")
            repo_url_label.setOpenExternalLinks(True)
            info_layout.addWidget(repo_url_label)
        
        scroll_layout.addWidget(info_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        install_button = QPushButton("Install Chart")
        install_button.setStyleSheet(AppStyles.BUTTON_STYLE)
        install_button.clicked.connect(lambda: self._install_chart_from_dialog(chart, dialog))
        
        close_button = QPushButton("Close")
        close_button.setStyleSheet(AppStyles.BUTTON_STYLE)
        close_button.clicked.connect(dialog.close)
        
        button_layout.addStretch()
        button_layout.addWidget(install_button)
        button_layout.addWidget(close_button)
        
        scroll_layout.addLayout(button_layout)
        scroll_layout.addStretch()
        
        # Set scroll content
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Show dialog
        dialog.exec()
    
    def _install_chart_from_dialog(self, chart, dialog):
        """Install chart from the detail dialog with duplicate prevention"""
        # Prevent multiple installations from running simultaneously
        if self.installation_in_progress:
            QMessageBox.warning(self, "Installation in Progress", 
                               "Another chart installation is already in progress. Please wait for it to complete.")
            return
        
        dialog.close()
        
        # Find the row for this chart and install
        for row, resource in enumerate(self.resources):
            if resource.get("name") == chart.get("name") and resource.get("repository") == chart.get("repository"):
                self._handle_install_chart(row)
                break