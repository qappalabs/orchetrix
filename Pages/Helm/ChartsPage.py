"""
Enhanced implementation of the Charts page displaying only Bitnami charts.
Includes icon detection, better error handling, and Bitnami-specific filtering.
"""

from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QHBoxLayout,
    QToolButton, QMenu, QVBoxLayout, QTableWidgetItem, 
    QProgressBar, QLineEdit, QPushButton,QMessageBox,QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPixmap

import requests
import json
import os
import re
import hashlib
from urllib.parse import urljoin

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from utils.helm_utils import ChartInstallDialog, install_helm_chart


class ChartDataThread(QThread):
    """Thread for loading Bitnami Helm charts from ArtifactHub API without blocking the UI."""
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
        
    def setup_directories(self):
        """Set up directories for storing icons and cache"""
        # Create directory for icons
        self.icons_dir = os.path.join(os.path.expanduser('~'), '.artifacthub', 'icons')
        os.makedirs(self.icons_dir, exist_ok=True)
        
        # Create directory for default icons
        self.default_icons_dir = os.path.join(os.path.expanduser('~'), '.artifacthub', 'default_icons')
        os.makedirs(self.default_icons_dir, exist_ok=True)
        
        # Download default Bitnami icon if not present
        self.default_bitnami_icon_path = os.path.join(self.default_icons_dir, 'bitnami_icon.png')
        if not os.path.exists(self.default_bitnami_icon_path):
            try:
                session = requests.Session()
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
                
                # Try to get the Bitnami icon from Artifact Hub
                bitnami_icon_url = "https://bitnami.com/assets/stacks/bitnami/img/bitnami-mark.png"
                icon_response = session.get(bitnami_icon_url, headers=headers, timeout=10)
                if icon_response.status_code == 200:
                    with open(self.default_bitnami_icon_path, 'wb') as f:
                        f.write(icon_response.content)

            except Exception as e:
                pass

    def run(self):
        """Execute the API request and emit results for Bitnami charts only."""
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            charts_data = []
            is_more_available = True
            
            # Build Bitnami-specific search query
            if self.use_search and self.search_term:
                # If user provides search term, search within Bitnami charts
                search_query = f"bitnami {self.search_term}"
            else:
                # Default to showing popular Bitnami charts
                search_query = "bitnami"
            
            # Try POST method first (more reliable for ArtifactHub)
            try:
                post_endpoint = 'https://artifacthub.io/api/v1/packages/search'
                
                post_data = {
                    "filters": {
                        "kind": [0],  # 0 is for Helm charts
                        "repo": ["bitnami"]  # Filter specifically for Bitnami repository
                    },
                    "offset": self.offset,
                    "limit": self.limit,
                    "sort": "relevance",  # Sort by relevance for better results
                    "ts_query_web": search_query
                }
                
                response = session.post(post_endpoint, json=post_data, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    page_data = response.json()
                    charts_data = self.process_api_data(page_data, session, headers)
                    is_more_available = len(charts_data) >= self.limit

            except Exception as e:
                pass
            
            # If POST failed, try GET method with Bitnami-specific parameters
            if not charts_data:
                try:
                    endpoint = 'https://artifacthub.io/api/v1/packages/search'
                    
                    params = {
                        'kind': '0',  # Helm charts
                        'ts_query_web': search_query,
                        'repo': 'bitnami',  # Specific repository filter
                        'sort': 'relevance',
                        'page': (self.offset // self.limit) + 1,
                        'limit': self.limit
                    }
                    
                    response = session.get(endpoint, params=params, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        page_data = response.json()
                        charts_data = self.process_api_data(page_data, session, headers)
                        is_more_available = len(charts_data) >= self.limit

                except Exception as e:
                    pass
            
            # Final fallback: Use a curated list of popular Bitnami charts if API fails
            if not charts_data:
                charts_data = self.get_fallback_bitnami_charts()
                is_more_available = False
            
            # Filter to ensure only Bitnami charts are included
            bitnami_charts = [chart for chart in charts_data if 
                            chart.get('repository', '').lower() == 'bitnami' or
                            'bitnami' in chart.get('repository', '').lower()]
            
            self.data_loaded.emit(bitnami_charts, is_more_available)
            
        except Exception as e:
            self.error_occurred.emit(f"Error fetching Bitnami charts: {str(e)}")
    
    def process_api_data(self, api_data, session, headers):
        """Process API data to extract Bitnami helm charts with icons"""
        bitnami_charts = []
        
        if not api_data:
            return bitnami_charts
        
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
        
        # Process packages and filter for Bitnami
        for package in packages:
            try:
                # Extract repository info first to filter
                repository = 'Unknown'
                repository_url = ''
                if 'repository' in package and isinstance(package.get('repository'), dict):
                    repo = package.get('repository', {})
                    repository = repo.get('name', 'Unknown')
                    repository_url = repo.get('url', '')
                
                # Only process if it's a Bitnami chart
                if repository.lower() != 'bitnami':
                    continue
                
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
                
                # Add to Bitnami charts list
                bitnami_charts.append({
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
        
        return bitnami_charts
    
    def get_fallback_bitnami_charts(self):
        """Provide a curated list of popular Bitnami charts as fallback"""
        fallback_charts = [
            {
                'name': 'apache',
                'description': 'Chart for Apache HTTP Server',
                'version': 'latest',
                'app_version': 'N/A',
                'repository': 'bitnami',
                'repository_url': 'https://charts.bitnami.com/bitnami',
                'stars': '0',
                'last_updated': '',
                'package_id': 'N/A',
                'icon_url': None,
                'icon_path': self.default_bitnami_icon_path if os.path.exists(self.default_bitnami_icon_path) else None
            },
            {
                'name': 'mysql',
                'description': 'Chart for MySQL database',
                'version': 'latest',
                'app_version': 'N/A',
                'repository': 'bitnami',
                'repository_url': 'https://charts.bitnami.com/bitnami',
                'stars': '0',
                'last_updated': '',
                'package_id': 'N/A',
                'icon_url': None,
                'icon_path': self.default_bitnami_icon_path if os.path.exists(self.default_bitnami_icon_path) else None
            },
            {
                'name': 'nginx',
                'description': 'Chart for NGINX web server',
                'version': 'latest',
                'app_version': 'N/A',
                'repository': 'bitnami',
                'repository_url': 'https://charts.bitnami.com/bitnami',
                'stars': '0',
                'last_updated': '',
                'package_id': 'N/A',
                'icon_url': None,
                'icon_path': self.default_bitnami_icon_path if os.path.exists(self.default_bitnami_icon_path) else None
            },
            {
                'name': 'postgresql',
                'description': 'Chart for PostgreSQL database',
                'version': 'latest',
                'app_version': 'N/A',
                'repository': 'bitnami',
                'repository_url': 'https://charts.bitnami.com/bitnami',
                'stars': '0',
                'last_updated': '',
                'package_id': 'N/A',
                'icon_url': None,
                'icon_path': self.default_bitnami_icon_path if os.path.exists(self.default_bitnami_icon_path) else None
            },
            {
                'name': 'redis',
                'description': 'Chart for Redis in-memory database',
                'version': 'latest',
                'app_version': 'N/A',
                'repository': 'bitnami',
                'repository_url': 'https://charts.bitnami.com/bitnami',
                'stars': '0',
                'last_updated': '',
                'package_id': 'N/A',
                'icon_url': None,
                'icon_path': self.default_bitnami_icon_path if os.path.exists(self.default_bitnami_icon_path) else None
            }
        ]
        
        return fallback_charts
    
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
                icon_filename = f"bitnami_{safe_name}_{url_hash}{file_ext}"
                icon_path = os.path.join(self.icons_dir, icon_filename)
                
                # Download the icon if it doesn't exist
                if not os.path.exists(icon_path):
                    try:
                        icon_response = session.get(icon_url, headers=headers, timeout=10)
                        
                        if icon_response.status_code == 200:
                            with open(icon_path, 'wb') as f:
                                f.write(icon_response.content)
                        else:
                            # Use default Bitnami icon
                            icon_path = self.default_bitnami_icon_path if os.path.exists(self.default_bitnami_icon_path) else None
                    except Exception as e:
                        icon_path = self.default_bitnami_icon_path if os.path.exists(self.default_bitnami_icon_path) else None
            else:
                # No icon URL found, use default Bitnami icon
                icon_path = self.default_bitnami_icon_path if os.path.exists(self.default_bitnami_icon_path) else None
        
        except Exception as e:
            icon_path = self.default_bitnami_icon_path if os.path.exists(self.default_bitnami_icon_path) else None
        
        return icon_url, icon_path


class ChartSearchThread(QThread):
    """Thread for searching Bitnami Helm charts from ArtifactHub API."""
    search_completed = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, search_term=""):
        super().__init__()
        self.search_term = search_term
        
    def run(self):
        """Execute the search request and emit results."""
        data_thread = ChartDataThread(limit=25, offset=0, use_search=True, search_term=self.search_term)
        data_thread.data_loaded.connect(lambda data, is_more: self.search_completed.emit(data, self.search_term))
        data_thread.error_occurred.connect(self.error_occurred)
        data_thread.start()
        data_thread.wait()


class ChartsPage(BaseResourcePage):
    """
    Displays Bitnami Helm charts with enhanced data from ArtifactHub API.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "charts"
        self.resources = []
        self.offset = 0
        self.is_more_available = True
        self.is_loading_more = False
        self.is_searching = False
        
        # Add a safety mechanism to recover from stuck loading states
        self._loading_timer = QTimer()
        self._loading_timer.timeout.connect(self._reset_loading_state)
        self._loading_timer.setSingleShot(True)
        
        # Initialize the UI
        self.setup_page_ui()
        
    def _reset_loading_state(self):
        """Reset loading state if it gets stuck"""
        if hasattr(self, 'is_loading') and self.is_loading:
            self.is_loading = False
            
        if hasattr(self, 'is_loading_more') and self.is_loading_more:
            self.is_loading_more = False
            
        if hasattr(self, 'resources') and len(self.resources) > 0:
            self.is_more_available = True
            
        if hasattr(self, 'table'):
            self.table.setEnabled(True)
            
        if hasattr(self, 'table') and self.table.rowCount() > 0:
            last_row = self.table.rowCount() - 1
            cell_widget = self.table.cellWidget(last_row, 0)
            if cell_widget and hasattr(cell_widget, 'findChild'):
                progress_bar = cell_widget.findChild(QProgressBar)
                if progress_bar:
                    self.table.setRowCount(last_row)
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Bitnami Charts page"""
        headers = ["", "Name", "Description", "Version", "App Version", "Repository", ""]
        sortable_columns = {1, 3, 4, 5}
        
        layout = super().setup_ui("Bitnami Charts", headers, sortable_columns)
        
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        self.configure_columns()
        
        scrollbar = self.table.verticalScrollBar()
        scrollbar.valueChanged.connect(self.check_scroll_position)
        
        if hasattr(self, 'select_all_checkbox') and self.select_all_checkbox:
            self.select_all_checkbox.hide()
        
        return layout
    
    def _apply_filters(self):
        """Apply search filter to the table"""
        if not hasattr(self, 'table') or self.table.rowCount() == 0:
            return
                
        search_text = ""
        if hasattr(self, 'search_bar'):
            search_text = self.search_bar.text().lower()
        
        if not search_text:
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, False)
            return
            
        for row in range(self.table.rowCount()):
            row_matches = False
            
            for col in range(1, self.table.columnCount() - 1):
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    row_matches = True
                    break
                
                cell_widget = self.table.cellWidget(row, col)
                if cell_widget:
                    widget_text = ""
                    for label in cell_widget.findChildren(QLabel):
                        widget_text += label.text() + " "
                    
                    if search_text in widget_text.lower():
                        row_matches = True
                        break
            
            self.table.setRowHidden(row, not row_matches)

    def _handle_scroll(self, value):
        """Disable the base class's scroll handler"""
        pass

    def check_scroll_position(self, value):
        """Check if the user has scrolled to the bottom and load more Bitnami charts"""
        if self.is_loading or self.is_loading_more or not self.is_more_available:
            return

        scrollbar = self.table.verticalScrollBar()

        if value >= scrollbar.maximum() - (2 * self.table.rowHeight(0)):
            self.load_more_data()

    def configure_columns(self):
        """Configure column widths and behaviors"""
        fixed_widths = {
            0: 50,   # Icon
            1: 180,  # Name
            3: 100,  # Version
            4: 120,  # App Version
            5: 150,  # Repository
            6: 40    # Actions
        }
        
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    
    def load_data(self, load_more=False):
        """Load initial Bitnami chart data from ArtifactHub API"""
        if hasattr(self, 'is_loading') and self.is_loading:
            return
            
        self.is_loading = True
        self.resources = []
        self.offset = 0
        self.is_more_available = True
        
        self._loading_timer.start(15000)
        
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setContentsMargins(20, 20, 20, 20)
        
        loading_bar = QProgressBar()
        loading_bar.setRange(0, 0)
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
        
        loading_text = QLabel(f"Loading Bitnami charts from ArtifactHub API...")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        self.chart_thread = ChartDataThread(limit=25, offset=self.offset)
        self.chart_thread.data_loaded.connect(self.on_data_loaded)
        self.chart_thread.error_occurred.connect(self.on_load_error)
        self.chart_thread.start()

    def load_more_data(self):
        """Load more Bitnami chart data when user scrolls to bottom"""
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
        
        loading_text = QLabel("Loading more Bitnami charts...")
        loading_text.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        self.more_thread = ChartDataThread(limit=25, offset=self.offset)
        self.more_thread.data_loaded.connect(self.on_more_data_loaded)
        self.more_thread.error_occurred.connect(self.on_load_more_error)
        self.more_thread.start()
    
    def on_data_loaded(self, data, is_more_available):
        """Handle loaded Bitnami chart data for initial load"""
        self._loading_timer.stop()
        
        self.is_loading = False
        self.resources = data
        
        self.is_more_available = True if data else False
        
        self.items_count.setText(f"{len(data)} Bitnami items (scroll for more)")
        
        self.table.setRowCount(0)
        self.populate_table(data)
        
        self.table.setSortingEnabled(True)
        
        self._apply_filters()
    
    def on_more_data_loaded(self, data, is_more_available):
        """Handle loaded Bitnami chart data for load-more operation"""
        self._loading_timer.stop()
        
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
            
            self.items_count.setText(f"{len(self.resources)} Bitnami items (scroll for more)")
        else:
            self._show_table_area()
        
        if not hasattr(self, '_scroll_handler_connected'):
            self.table.verticalScrollBar().valueChanged.connect(self._on_scroll)
            self._scroll_handler_connected = True

    def _on_scroll(self, value):
        if self.is_loading or not self.is_more_available:
            return
        
        scrollbar = self.table.verticalScrollBar()
        if value >= scrollbar.maximum() * 0.9: 
            self.load_data(load_more=True)

    def setup_page_ui(self):
        headers = ["", "Name", "Description", "Version", "App Version", "Repository", ""]
        sortable_columns = {1, 3, 4, 5}
        super().setup_ui("Helm Charts", headers, sortable_columns)
        self.configure_columns()
        if hasattr(self, 'select_all_checkbox'): self.select_all_checkbox.hide()

    # def configure_columns(self):
    #     fixed_widths = {0: 50, 1: 220, 3: 120, 4: 120, 5: 150, 6: 40}
    #     for col, width in fixed_widths.items():
    #         self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
    #         self.table.setColumnWidth(col, width)
    #     self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
        
        header = self.table.horizontalHeader()
        
        # Column specifications with optimized default widths
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 140, "interactive"), # Name
            (2, 90, "interactive"),  # Description
            (3, 80, "interactive"),  # Version
            (4, 60, "interactive"),  # App Version
            (5, 80, "stretch"),      # Repository - stretch to fill remaining space
            (6, 40, "fixed")        # Actions
        ]
        
        # Apply column configuration
        for col_index, default_width, resize_type in column_specs:
            if col_index < self.table.columnCount():
                if resize_type == "fixed":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "interactive":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "stretch":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
                    self.table.setColumnWidth(col_index, default_width)
        
        # Ensure full width utilization after configuration
        QTimer.singleShot(100, self._ensure_full_width_utilization)



    def populate_resource_row(self, row, chart):
        self.table.setRowHeight(row, 42)
        
        chart_name = chart.get("name", "Unknown")
        description = chart.get("description", "No description available")
        version = chart.get("version", "N/A")
        app_version = chart.get("app_version", "N/A")
        repository = chart.get("repository", "bitnami")  # Default to bitnami
        
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
                    icon_label.setText("🔸")  # Bitnami icon
                    icon_label.setStyleSheet("""
                        QLabel {
                            color: #f39c12;
                            font-size: 14px;
                            border-radius: 3px;
                            background-color: rgba(255, 255, 255, 0.05);
                            border: none;
                            padding: 0px;
                            margin: 0px;
                        }
                    """)
            except Exception as e:
                icon_label.setText("🔸")
                icon_label.setStyleSheet("""
                    QLabel {
                        color: #f39c12;
                        font-size: 14px;
                        border-radius: 3px;
                        background-color: rgba(255, 255, 255, 0.05);
                        border: none;
                        padding: 0px;
                        margin: 0px;
                    }
                """)
        else:
            icon_label.setText("🔸")  # Bitnami-style icon
            icon_label.setStyleSheet("""
                QLabel {
                    color: #f39c12;
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
        columns = [chart_name, description, version, app_version, repository]
        
        for col, value in enumerate(columns, 1):
            item = SortableTableWidgetItem(value)
            
            if col == 1:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setForeground(QColor("#e2e8f0"))
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor("#e2e8f0"))
            
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            self.table.setItem(row, col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, chart_name)
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(action_button)
        action_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, len(columns) + 1, action_container)
   
    def _create_action_button(self, row, chart_name):
        """Create an action button with view details and install options"""
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(20)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet("""
            QToolButton {
                color: #888888;
                font-size: 14px;
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
                padding: 6px 20px 6px 24px;
                border-radius: 3px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                color: #ffffff;
            }
        """)
        
        # Add view action
        view_action = menu.addAction("View Details")
        view_action.triggered.connect(lambda: self._handle_view_details(row))
        
        # Add install action
        install_action = menu.addAction("Install")
        install_action.triggered.connect(lambda: self._handle_action("Install", row))
    
        button.setMenu(menu)
        return button
    
    def _handle_action(self, action, row):
        """Handle action button clicks in the Bitnami charts page"""
        if row >= len(self.resources):
            return
            
        chart = self.resources[row]
        chart_name = chart.get("name", "Unknown")
        
        if action == "View Details":
            self._handle_view_details(row)
        elif action == "Install":
            self._install_chart(chart)

    def _install_chart(self, chart):
        """Display installation dialog and install the Bitnami chart"""
        chart_name = chart.get("name", "Unknown")
        repository = "bitnami"  # Force Bitnami repository
        
        # Create and show the installation dialog with Bitnami defaults
        dialog = ChartInstallDialog(chart_name, repository, self)
        
        # Pre-configure for Bitnami
        if hasattr(dialog, 'repo_name_input'):
            dialog.repo_name_input.setText("bitnami")
        if hasattr(dialog, 'use_existing_repo'):
            dialog.use_existing_repo.setChecked(True)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_values()
            
            # Ensure Bitnami repository is used
            if options.get("repository", {}).get("type") == "name":
                options["repository"]["value"] = "bitnami"
            
            success, message = install_helm_chart(chart_name, "bitnami", options, self)
            
            if success:
                QMessageBox.information(self, "Installation Successful", message)
                
                parent = self.parent()
                while parent and not hasattr(parent, 'stacked_widget'):
                    parent = parent.parent()
                    
                if parent and hasattr(parent, 'pages') and "Releases" in parent.pages:
                    releases_page = parent.pages["Releases"]
                    if hasattr(releases_page, 'load_data'):
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(1000, releases_page.load_data)
            else:
                QMessageBox.critical(self, "Installation Failed", message)
    
    def _handle_view_details(self, row):
        """Handle view details action for Bitnami charts"""
        if row >= len(self.resources):
            return
            
        chart = self.resources[row]
        chart_name = chart.get("name", "Unknown")
        
        # Find the ClusterView instance
        parent = self.parent()
        while parent and not hasattr(parent, 'detail_manager'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'detail_manager'):
            resource_data = {
                "kind": "HelmChart",
                "apiVersion": "helm.sh/v1",
                "metadata": {
                    "name": chart_name,
                    "creationTimestamp": chart.get("last_updated", ""),
                    "labels": {
                        "repository": "bitnami",
                        "version": chart.get("version", ""),
                        "appVersion": chart.get("app_version", ""),
                        "stars": chart.get("stars", "0")
                    },
                    "annotations": {
                        "description": chart.get("description", ""),
                        "repository_url": "https://charts.bitnami.com/bitnami",
                        "package_id": chart.get("package_id", ""),
                        "source": "Bitnami via ArtifactHub"
                    }
                },
                "spec": {
                    "version": chart.get("version", ""),
                    "appVersion": chart.get("app_version", ""),
                    "repository": "bitnami",
                },
                "status": {
                    "phase": "Available"
                }
            }
            
            try:
                icon_path = chart.get("icon_path")
                if icon_path and isinstance(icon_path, str) and os.path.exists(icon_path):
                    resource_data["metadata"]["annotations"]["icon_path"] = icon_path
            except Exception as e:
                pass
            
            import json
            global current_chart_data
            current_chart_data = json.dumps(resource_data)
            
            parent.detail_manager.show_detail("chart", chart_name)
    
    def handle_search(self):
        """Handle search button click or enter key press in search bar for Bitnami charts"""
        if hasattr(self, 'is_searching') and self.is_searching:
            return
            
        search_text = self.search_bar.text().strip()
        
        if not search_text:
            self.is_searching = False
            self.load_data()
            return
        
        self.is_searching = True
        
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setContentsMargins(20, 20, 20, 20)
        
        loading_bar = QProgressBar()
        loading_bar.setRange(0, 0)
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
        
        loading_text = QLabel(f"Searching Bitnami charts for '{search_text}'...")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        self.search_thread = ChartSearchThread(search_text)
        self.search_thread.search_completed.connect(self.on_search_completed)
        self.search_thread.error_occurred.connect(self.on_search_error)
        self.search_thread.start()
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:
            self.table.selectRow(row)
            
            if row < len(self.resources):
                self._handle_view_details(row)