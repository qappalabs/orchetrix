# file: Pages/Helm/ChartsPage.py
"""
Enhanced implementation of the Charts page displaying charts from various repositories.
Includes icon detection, better error handling, and repository-based filtering.
"""

from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QHBoxLayout,
    QToolButton, QMenu, QVBoxLayout, QTableWidgetItem, 
    QProgressBar, QLineEdit, QPushButton, QMessageBox, QDialog, QComboBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPixmap, QIcon

import requests
import json
import os
import re
import hashlib
from urllib.parse import urljoin
import yaml
import logging

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from utils.helm_utils import ChartInstallDialog, HelmInstallThread, get_helm_repos, update_helm_repos, ScrollableMessageBox, ManageReposDialog

class ChartDataThread(QThread):
    """Thread for loading Helm charts from ArtifactHub API and local repo cache."""
    data_loaded = pyqtSignal(list, bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, repository=None, limit=50, offset=0, search_term=""):
        super().__init__()
        self.repository = repository
        self.limit = limit
        self.offset = offset
        self.search_term = search_term
        self.setup_directories()

    def setup_directories(self):
        self.icons_dir = os.path.join(os.path.expanduser('~'), '.orchestrix', 'icons')
        os.makedirs(self.icons_dir, exist_ok=True)
        self.default_chart_icon_path = os.path.join(self.icons_dir, 'default_chart_icon.png')

    def run(self):
        try:
            charts = self.search_artifact_hub()
            is_more_available = len(charts) == self.limit
            self.data_loaded.emit(charts, is_more_available)
        except requests.exceptions.ConnectionError:
             self.error_occurred.emit("Network connection error. Could not connect to Artifact Hub.")
        except Exception as e:
            logging.error(f"Failed to fetch charts from ArtifactHub: {e}")
            try:
                charts = self.load_from_local_cache()
                self.data_loaded.emit(charts, False)
            except Exception as cache_e:
                self.error_occurred.emit(f"API Error: {e}\nCache Error: {cache_e}")

    def search_artifact_hub(self):
        session = requests.Session()
        headers = {'User-Agent': 'Orchestrix/1.0', 'Accept': 'application/json'}
        search_query = self.search_term if self.search_term else ""
        
        endpoint = 'https://artifacthub.io/api/v1/packages/search'
        params = {
            'kind': '0', 
            'ts_query_web': search_query,
            'sort': 'relevance',
            'offset': self.offset,
            'limit': self.limit
        }
        if self.repository and self.repository.lower() != 'all':
            params['repo'] = [self.repository]

        response = session.get(endpoint, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        page_data = response.json()
        return self.process_api_data(page_data, session, headers)

    def load_from_local_cache(self):
        if self.repository and self.repository.lower() != 'all':
            return self.load_charts_from_repo(self.repository)
        return self.load_charts_from_all_repos_cache()

    def load_charts_from_repo(self, repo_name):
        charts = []
        cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'helm', 'repository')
        index_file = f"{repo_name}-index.yaml"
        index_path = os.path.join(cache_dir, index_file)
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = yaml.safe_load(f)
                for name, chart_versions in index_data.get('entries', {}).items():
                    if self.search_term and self.search_term.lower() not in name.lower():
                        continue
                    if chart_versions:
                        latest = chart_versions[0]
                        charts.append({
                            'name': latest.get('name'), 'description': latest.get('description'),
                            'version': latest.get('version'), 'app_version': latest.get('appVersion'),
                            'repository': repo_name, 'icon_path': self.default_chart_icon_path
                        })
        return charts

    def load_charts_from_all_repos_cache(self):
        all_charts = []
        repos = get_helm_repos()
        for repo in repos:
            all_charts.extend(self.load_charts_from_repo(repo['name']))
        if self.search_term:
            term = self.search_term.lower()
            return [c for c in all_charts if term in c['name'].lower() or term in c['description'].lower()]
        return all_charts

    def process_api_data(self, api_data, session, headers):
        charts = []
        for package in api_data.get('packages', []):
            repo_info = package.get('repository', {})
            charts.append({
                'name': package.get('name'), 
                'description': package.get('description'),
                'version': package.get('version'), 
                'app_version': package.get('app_version'),
                'repository': repo_info.get('name'),
                'repository_url': repo_info.get('url'),
                'icon_path': self.download_icon(package, session, headers)
            })
        return charts

    def download_icon(self, package, session, headers):
        icon_url = package.get('logo_url') or (f"https://artifacthub.io/image/{package['logo_image_id']}" if package.get('logo_image_id') else None)
        if not icon_url: return self.default_chart_icon_path
        try:
            url_hash = hashlib.md5(icon_url.encode()).hexdigest()
            file_ext = (os.path.splitext(icon_url)[1] or '.png').split('?')[0]
            icon_path = os.path.join(self.icons_dir, f"{url_hash}{file_ext}")
            if not os.path.exists(icon_path):
                res = session.get(icon_url, headers=headers, timeout=10)
                if res.status_code == 200:
                    with open(icon_path, 'wb') as f: f.write(res.content)
                else: return self.default_chart_icon_path
            return icon_path
        except Exception:
            return self.default_chart_icon_path

class ChartsPage(BaseResourcePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "charts"
        self.current_repo = "bitnami" 
        self.is_loading = False
        self.offset = 0
        self.is_more_available = True
        self.install_thread = None
        self.setup_page_ui()
        self.load_helm_repos()

    def _add_controls_to_header(self, header_layout):
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search charts...")
        self.search_bar.setMinimumWidth(350)
        self.search_bar.setFixedHeight(30)
        search_style = getattr(AppStyles, "SEARCH_BAR_STYLE", "QLineEdit {}")
        self.search_bar.setStyleSheet(search_style)
        self.search_bar.textChanged.connect(self._handle_search)
        header_layout.addWidget(self.search_bar)

        header_layout.addStretch(1)
        
        repo_label = QLabel("Repository:")
        repo_label.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(repo_label)
        
        self.repo_combo = QComboBox()
        self.repo_combo.setMinimumWidth(200)
        self.repo_combo.setFixedHeight(30)
        combo_style = getattr(AppStyles, "COMBO_BOX_STYLE", "QComboBox {}")
        self.repo_combo.setStyleSheet(combo_style)
        self.repo_combo.currentTextChanged.connect(self._handle_repo_change)
        header_layout.addWidget(self.repo_combo)

        manage_repos_btn = QPushButton("Manage Repos")
        btn_style = getattr(AppStyles, "SECONDARY_BUTTON_STYLE", "QPushButton {}")
        manage_repos_btn.setStyleSheet(btn_style)
        manage_repos_btn.clicked.connect(self.manage_repositories)
        header_layout.addWidget(manage_repos_btn)

    def load_helm_repos(self):
        """Loads helm repositories and sets the default selection."""
        self.repo_combo.blockSignals(True)
        self.repo_combo.clear()
        self.repo_combo.addItem("All")
        
        # On first load, self.current_repo is 'bitnami'
        default_repo_to_select = self.current_repo 
        
        try:
            # This now uses the pure Python client via the updated helm_utils
            repos = get_helm_repos()
            if repos:
                repo_names = sorted([repo['name'] for repo in repos])
                self.repo_combo.addItems(repo_names)
        except Exception as e:
            QMessageBox.warning(self, "Helm Error", f"Could not list Helm repositories: {e}")

        # Attempt to set the default repository
        repo_index = self.repo_combo.findText(default_repo_to_select, Qt.MatchFlag.MatchFixedString)
        if repo_index >= 0:
            self.repo_combo.setCurrentIndex(repo_index)
        else:
            # If default 'bitnami' isn't found, default to 'All'
            self.repo_combo.setCurrentIndex(0)
            
        self.repo_combo.blockSignals(False)
        
        # Manually trigger the handler with the newly set text to ensure initial data load
        current_text = self.repo_combo.currentText()
        if self.current_repo != current_text.lower():
             self._handle_repo_change(current_text)
        else:
             self.force_load_data()

    def manage_repositories(self):
        dialog = ManageReposDialog(self)
        if dialog.exec():
            self.load_helm_repos()
            self.force_load_data()

    def _handle_repo_change(self, repo_name):
        if repo_name:
            self.current_repo = repo_name.lower()
            self.force_load_data()
        
    def _handle_search(self, text):
        if hasattr(self, '_search_timer'): self._search_timer.stop()
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.force_load_data)
        self._search_timer.start(500)

    def load_data(self, load_more=False):
        if self.is_loading: return
        self.is_loading = True
        if not load_more:
            self.offset = 0
            self.resources = []
            self._show_skeleton_loader()
        
        search_term = self.search_bar.text() if hasattr(self, 'search_bar') else ""
        repo = self.current_repo
        self.chart_thread = ChartDataThread(repository=repo, offset=self.offset, search_term=search_term, limit=25)
        self.chart_thread.data_loaded.connect(lambda d, m: self.on_data_loaded(d, m, load_more))
        self.chart_thread.error_occurred.connect(self.on_load_error)
        self.chart_thread.start()

    def on_data_loaded(self, data, is_more_available, is_load_more):
        if self.is_showing_skeleton:
            self.table.setRowCount(0) # Clear skeleton
            self.is_showing_skeleton = False

        if not is_load_more:
            self.table.setRowCount(0)
            self.resources = []
        
        start_row = len(self.resources)
        self.resources.extend(data)
        
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(self.resources))
        for i, chart_data in enumerate(data):
            self.populate_resource_row(start_row + i, chart_data)
        self.table.setUpdatesEnabled(True)

        self.is_more_available = is_more_available
        self.offset = len(self.resources)
        self.is_loading = False
             
        self.items_count.setText(f"{len(self.resources)} items")
        if not self.resources:
            self._show_message_in_table_area("No charts found.", "Try a different search or repository.")
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
        icon_path = chart.get("icon_path")
        icon_widget = QLabel()
        icon_widget.setFixedSize(28, 28)
        icon_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_widget.setPixmap(pixmap)
        self.table.setCellWidget(row, 0, icon_widget)

        for i, key in enumerate(['name', 'description', 'version', 'app_version', 'repository'], 1):
            self.table.setItem(row, i, SortableTableWidgetItem(chart.get(key, '')))
        
        action_button = self._create_action_button(row)
        self.table.setCellWidget(row, 6, action_button)

    def _create_action_button(self, row):
        button = QToolButton()
        button.setIcon(QIcon(os.path.join("icons", "Moreaction_Button.svg")))
        
        button.setStyleSheet("""
            QToolButton {
                color: #888888;
                font-size: 18px;
                background: transparent;
                padding: 2px;
                margin: 0;
                border: none;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                color: #ffffff;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        
        button.setFixedSize(30, 30)
        
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
                padding: 8px 24px 8px 36px;
                border-radius: 4px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                color: #ffffff;
            }
            QMenu::item[dangerous="true"] {
                color: #ff4444;
            }
            QMenu::item[dangerous="true"]:selected {
                background-color: rgba(255, 68, 68, 0.1);
            }
        """)
        
        install_action = menu.addAction("Install")
        install_action.triggered.connect(lambda: self._handle_action("Install", row))
        
        def show_menu():
            button_pos = button.mapToGlobal(button.rect().bottomLeft())
            menu.exec(button_pos)
        
        button.clicked.connect(show_menu)
        button.setToolTip("Chart actions")
        return button

    def _handle_action(self, action, row):
        if action == "Install" and row < len(self.resources):
            chart = self.resources[row]
            dialog = ChartInstallDialog(chart, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                options = dialog.get_values()
                if options: self.start_install_chart(chart, options)

    def start_install_chart(self, chart, options):
        if self.install_thread and self.install_thread.isRunning():
            QMessageBox.warning(self, "Installation in Progress", "Another chart installation is already running.")
            return

        progress = QProgressDialog("Preparing installation...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Installing Chart")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        self.install_thread = HelmInstallThread(chart, options)
        self.install_thread.progress_update.connect(progress.setLabelText)
        self.install_thread.progress_percentage.connect(progress.setValue)
        self.install_thread.installation_complete.connect(lambda s, m: self.on_install_complete(progress, s, m))
        progress.canceled.connect(self.install_thread.cancel)
        self.install_thread.start()
        
    def on_install_complete(self, progress_dialog, success, message):
        progress_dialog.close()
        if success:
            msg_box = ScrollableMessageBox("Installation Success", message, self)
            msg_box.exec()
        else:
            QMessageBox.critical(self, "Installation Failed", message)
        self.install_thread = None
