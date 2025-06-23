"""
Enhanced Releases page implementation with proper upgrade and rollback functionality.
Fixed critical issues in upgrade process and added rollback capabilities.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout, QVBoxLayout,
    QMessageBox, QProgressBar, QApplication, QDialog, QFormLayout,
    QComboBox, QTextEdit, QDialogButtonBox, QProgressDialog, QMenu, QCheckBox,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QIcon

import time
import datetime
import os
import tempfile
import yaml
import logging
from typing import Optional, List, Dict, Any

from base_components.base_resource_page import BaseResourcePage
from base_components.base_components import SortableTableWidgetItem
from UI.Styles import AppColors, AppStyles
from utils.helm_client import HelmClient
from utils.kubernetes_client import get_kubernetes_client


class HelmReleasesLoader(QThread):
    """Thread to load Helm releases using pure Python implementation"""
    
    releases_loaded = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, namespace: Optional[str] = None):
        super().__init__()
        self.namespace = namespace
        self.helm_client = None
        
    def run(self):
        """Execute the release loading process"""
        try:
            # Initialize Helm client
            kube_client = get_kubernetes_client()
            if not kube_client or not kube_client.v1:
                self.error_occurred.emit("Kubernetes client not available. Please check cluster connection.")
                self.releases_loaded.emit([], "helmreleases")
                return
                
            self.helm_client = HelmClient(kube_client.v1)
            
            # Load releases
            releases = []
            
            if self.namespace and self.namespace != "all":
                helm_releases = self.helm_client.list_releases(namespace=self.namespace)
            else:
                helm_releases = self.helm_client.list_releases(all_namespaces=True)
            
            # Convert HelmRelease objects to the format expected by the UI
            for helm_release in helm_releases:
                # Calculate age
                age = self._format_age(helm_release.updated)
                formatted_updated = self._format_updated_timestamp(helm_release.updated)
                
                release_data = {
                    "name": helm_release.name,
                    "namespace": helm_release.namespace,
                    "age": age,
                    "raw_data": {
                        "chart": f"{helm_release.chart_name}-{helm_release.chart_version}",
                        "revision": helm_release.revision,
                        "version": helm_release.chart_version,
                        "appVersion": helm_release.app_version,
                        "status": helm_release.status,
                        "updated": formatted_updated,
                        "notes": helm_release.notes
                    }
                }
                releases.append(release_data)
            
            # Sort releases by name
            releases.sort(key=lambda x: x["name"])
            
            # Emit the loaded releases
            self.releases_loaded.emit(releases, "helmreleases")
            
        except Exception as e:
            error_message = f"Error loading Helm releases: {str(e)}"
            logging.error(error_message)
            self.error_occurred.emit(error_message)
            self.releases_loaded.emit([], "helmreleases")

    def _format_age(self, timestamp: datetime.datetime) -> str:
        """Format age from timestamp"""
        if not timestamp:
            return "Unknown"
            
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                
            diff = now - timestamp
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"

    def _format_updated_timestamp(self, timestamp: datetime.datetime) -> str:
        """Format timestamp into human-readable relative time"""
        if not timestamp:
            return "<none>"
            
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                
            diff = now - timestamp
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            seconds = diff.seconds % 60
            
            if days > 0:
                return f"{days}d {hours}h ago"
            elif hours > 0:
                return f"{hours}h {minutes}m ago"
            elif minutes > 0:
                return f"{minutes}m {seconds}s ago"
            else:
                return f"{seconds}s ago"
        except Exception:
            return str(timestamp)


class ReleaseUpgradeDialog(QDialog):
    """Enhanced dialog for upgrading Helm releases with better validation"""
    
    def __init__(self, release_name: str, namespace: str, parent=None):
        super().__init__(parent)
        self.release_name = release_name
        self.namespace = namespace
        self.helm_client = None
        
        # Initialize Helm client
        kube_client = get_kubernetes_client()
        if kube_client and kube_client.v1:
            self.helm_client = HelmClient(kube_client.v1)
            
        self.setWindowTitle(f"Upgrade Release: {release_name}")
        self.setMinimumWidth(600)
        self.setStyleSheet(f"""
            background-color: {AppColors.BG_DARK};
            color: {AppColors.TEXT_LIGHT};
        """)
        self.setup_ui()
        self.load_current_values()
    
    def setup_ui(self):
        """Setup the dialog user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Form layout for inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Chart input field
        self.chart_input = QLineEdit()
        self.chart_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
        """)
        self.chart_input.setPlaceholderText("Leave empty to use current chart")
        form_layout.addRow("Chart:", self.chart_input)
        
        # Version input field
        self.version_input = QLineEdit()
        self.version_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
        """)
        self.version_input.setPlaceholderText("Leave empty for latest version")
        form_layout.addRow("Version:", self.version_input)
        
        # Values editor
        self.values_editor = QTextEdit()
        self.values_editor.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                font-family: Consolas, 'Courier New', monospace;
            }
            QTextEdit:focus {
                border: 1px solid #0078d7;
            }
        """)
        self.values_editor.setMinimumHeight(200)
        self.values_editor.setPlaceholderText("# Enter values in YAML format\n# Leave empty to use current values")
        form_layout.addRow("Values:", self.values_editor)
        
        # Atomic upgrade checkbox
        self.atomic_checkbox = QCheckBox("Atomic upgrade (rollback on failure)")
        self.atomic_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.atomic_checkbox.setChecked(True)
        form_layout.addRow("", self.atomic_checkbox)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        self.upgrade_button = QPushButton("Upgrade")
        self.upgrade_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0086e7;
            }
            QPushButton:pressed {
                background-color: #0063b1;
            }
        """)
        self.upgrade_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.upgrade_button)
        
        layout.addLayout(button_layout)
    
    def load_current_values(self):
        """Load current release information"""
        if not self.helm_client:
            return
            
        try:
            # Get current release details
            release = self.helm_client.get_release(self.release_name, self.namespace)
            if release:
                # Set chart placeholder
                chart_display = f"{release.chart_name}-{release.chart_version}"
                self.chart_input.setPlaceholderText(f"Current: {chart_display}")
                
                # Load current values
                if release.values:
                    values_yaml = yaml.dump(release.values, default_flow_style=False)
                    if values_yaml.strip() and values_yaml.strip() != "{}":
                        self.values_editor.setPlainText(values_yaml)
                    else:
                        self.values_editor.setPlainText("# No custom values set for this release")
                else:
                    self.values_editor.setPlainText("# No custom values set for this release")
                    
        except Exception as e:
            logging.error(f"Error loading current values: {e}")
            self.values_editor.setPlainText("# Error loading current values")
    
    def get_values(self) -> Dict[str, Any]:
        """Get values from the dialog"""
        values_text = self.values_editor.toPlainText().strip()
        values_dict = {}
        
        if values_text and not values_text.startswith("# No custom values") and not values_text.startswith("# Error loading"):
            try:
                values_dict = yaml.safe_load(values_text) or {}
            except yaml.YAMLError:
                values_dict = {}
        
        return {
            "chart": self.chart_input.text().strip(),
            "version": self.version_input.text().strip(),
            "values": values_dict,
            "atomic": self.atomic_checkbox.isChecked()
        }


class ReleaseRollbackDialog(QDialog):
    """Dialog for rolling back Helm releases"""
    
    def __init__(self, release_name: str, namespace: str, parent=None):
        super().__init__(parent)
        self.release_name = release_name
        self.namespace = namespace
        self.helm_client = None
        self.selected_revision = None
        
        # Initialize Helm client
        kube_client = get_kubernetes_client()
        if kube_client and kube_client.v1:
            self.helm_client = HelmClient(kube_client.v1)
            
        self.setWindowTitle(f"Rollback Release: {release_name}")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(f"""
            background-color: {AppColors.BG_DARK};
            color: {AppColors.TEXT_LIGHT};
        """)
        self.setup_ui()
        self.load_revision_history()
    
    def setup_ui(self):
        """Setup the dialog user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Info label
        info_label = QLabel(f"Select a revision to rollback release '{self.release_name}' to:")
        info_label.setStyleSheet("color: #ffffff; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Revision list
        self.revision_list = QListWidget()
        self.revision_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3d3d3d;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.revision_list.itemClicked.connect(self.on_revision_selected)
        layout.addWidget(self.revision_list)
        
        # Warning label
        warning_label = QLabel("⚠️ Warning: This will revert the release to the selected revision state.")
        warning_label.setStyleSheet("color: #ff9800; font-size: 12px; margin-top: 10px;")
        layout.addWidget(warning_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        self.rollback_button = QPushButton("Rollback")
        self.rollback_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.rollback_button.clicked.connect(self.accept)
        self.rollback_button.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.rollback_button)
        
        layout.addLayout(button_layout)
    
    def load_revision_history(self):
        """Load revision history for the release"""
        if not self.helm_client:
            return
            
        try:
            # Get release history
            history = self.helm_client.get_release_history(self.release_name, self.namespace)
            
            if not history:
                item = QListWidgetItem("No revision history found")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.revision_list.addItem(item)
                return
            
            for revision in history:
                # Format revision info
                status_color = "#4CAF50" if revision.status == "deployed" else "#ff6b6b"
                revision_text = f"Revision {revision.revision} - {revision.status} - {revision.updated.strftime('%Y-%m-%d %H:%M:%S')}"
                
                item = QListWidgetItem(revision_text)
                item.setData(Qt.ItemDataRole.UserRole, revision.revision)
                
                # Disable current revision
                current_release = self.helm_client.get_release(self.release_name, self.namespace)
                if current_release and revision.revision == current_release.revision:
                    item.setText(f"{revision_text} (Current)")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                    item.setForeground(QColor("#888888"))
                
                self.revision_list.addItem(item)
                
        except Exception as e:
            logging.error(f"Error loading revision history: {e}")
            item = QListWidgetItem(f"Error loading history: {str(e)}")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.revision_list.addItem(item)
    
    def on_revision_selected(self, item):
        """Handle revision selection"""
        revision = item.data(Qt.ItemDataRole.UserRole)
        if revision:
            self.selected_revision = revision
            self.rollback_button.setEnabled(True)
        else:
            self.selected_revision = None
            self.rollback_button.setEnabled(False)
    
    def get_selected_revision(self) -> Optional[int]:
        """Get the selected revision"""
        return self.selected_revision


class HelmUpgradeThread(QThread):
    """Enhanced thread for upgrading Helm releases with proper upgrade logic"""
    
    upgrade_complete = pyqtSignal(bool, str)
    progress_update = pyqtSignal(str)
    progress_percentage = pyqtSignal(int)
    
    def __init__(self, release_name: str, namespace: str, options: Dict[str, Any]):
        super().__init__()
        self.release_name = release_name
        self.namespace = namespace
        self.options = options
        self.helm_client = None
        self.downloaded_chart_path = None
        self._is_cancelled = False
        
    def run(self):
        """Execute the upgrade process with proper upgrade logic"""
        try:
            self.progress_update.emit("Initializing upgrade...")
            self.progress_percentage.emit(10)
            
            # Initialize Helm client
            kube_client = get_kubernetes_client()
            if not kube_client or not kube_client.v1:
                self.upgrade_complete.emit(False, "Kubernetes client not available")
                return
                
            self.helm_client = HelmClient(kube_client.v1)
            
            if self._is_cancelled:
                return
            
            self.progress_update.emit("Getting current release information...")
            self.progress_percentage.emit(20)
            
            # Get current release
            current_release = self.helm_client.get_release(self.release_name, self.namespace)
            if not current_release:
                self.upgrade_complete.emit(False, f"Release {self.release_name} not found")
                return
            
            if self._is_cancelled:
                return
            
            # Determine chart and version to upgrade to
            chart_name = self.options.get("chart") or current_release.chart_name
            version = self.options.get("version") or "latest"
            
            self.progress_update.emit(f"Downloading chart {chart_name}:{version}...")
            self.progress_percentage.emit(40)
            
            # Download the new chart version
            self.downloaded_chart_path = self._download_chart_for_upgrade(chart_name, version)
            
            if not self.downloaded_chart_path:
                self.upgrade_complete.emit(
                    False, 
                    f"Could not download chart {chart_name}:{version}"
                )
                return
            
            if self._is_cancelled:
                self._cleanup()
                return
            
            # Find chart directory
            chart_dir = self._find_chart_directory(self.downloaded_chart_path, chart_name)
            if not chart_dir:
                self.upgrade_complete.emit(False, "Chart directory not found in download")
                return
            
            self.progress_update.emit("Preparing upgrade...")
            self.progress_percentage.emit(60)
            
            # Get upgrade values
            upgrade_values = self.options.get("values", {})
            atomic = self.options.get("atomic", True)
            
            if self._is_cancelled:
                self._cleanup()
                return
            
            self.progress_update.emit("Applying upgrade...")
            self.progress_percentage.emit(80)
            
            # Perform the proper upgrade (not install)
            success = self.helm_client.upgrade_release(
                release_name=self.release_name,
                namespace=self.namespace,
                chart_path=chart_dir,
                values=upgrade_values,
                atomic=atomic
            )
            
            if self._is_cancelled:
                self._cleanup()
                return
            
            if success:
                self.progress_percentage.emit(100)
                self.upgrade_complete.emit(True, f"Successfully upgraded release {self.release_name}")
            else:
                self.upgrade_complete.emit(False, "Upgrade failed")
                
        except Exception as e:
            logging.error(f"Upgrade error: {e}")
            self.upgrade_complete.emit(False, f"Upgrade error: {str(e)}")
        finally:
            self._cleanup()
    
    def _download_chart_for_upgrade(self, chart_name: str, version: str) -> Optional[str]:
        """Download chart for upgrade with fallback strategies"""
        # Get list of repositories
        repositories = self.helm_client.list_repositories()
        
        # Try each repository
        for repo in repositories:
            try:
                repo_name = repo['name']
                self.progress_update.emit(f"Trying repository {repo_name}...")
                
                chart_path = self.helm_client.repo_manager.download_chart(
                    repo_name, chart_name, version
                )
                
                if chart_path and os.path.exists(chart_path):
                    logging.info(f"Downloaded chart from repository {repo_name}")
                    return chart_path
                    
            except Exception as e:
                logging.warning(f"Failed to download from repository {repo['name']}: {e}")
                continue
        
        # Try common repositories if not found
        common_repos = {
            'bitnami': 'https://charts.bitnami.com/bitnami',
            'stable': 'https://charts.helm.sh/stable',
            'ingress-nginx': 'https://kubernetes.github.io/ingress-nginx',
            'prometheus': 'https://prometheus-community.github.io/helm-charts'
        }
        
        for repo_name, repo_url in common_repos.items():
            try:
                self.progress_update.emit(f"Trying common repository {repo_name}...")
                
                # Add temporary repository
                temp_repo_name = f"temp-upgrade-{repo_name}-{int(time.time())}"
                self.helm_client.repo_manager.add_repository(temp_repo_name, repo_url)
                self.helm_client.repo_manager.update_repository_index(temp_repo_name)
                
                chart_path = self.helm_client.repo_manager.download_chart(
                    temp_repo_name, chart_name, version
                )
                
                # Clean up temp repository
                try:
                    self.helm_client.repo_manager.remove_repository(temp_repo_name)
                except:
                    pass
                
                if chart_path and os.path.exists(chart_path):
                    logging.info(f"Downloaded chart from common repository {repo_name}")
                    return chart_path
                    
            except Exception as e:
                logging.warning(f"Failed to download from common repository {repo_name}: {e}")
                continue
        
        return None
    
    def _find_chart_directory(self, downloaded_path: str, chart_name: str) -> Optional[str]:
        """Find the chart directory within the downloaded path"""
        try:
            # Try expected chart directory first
            chart_dir = os.path.join(downloaded_path, chart_name)
            if os.path.exists(chart_dir) and os.path.exists(os.path.join(chart_dir, "Chart.yaml")):
                return chart_dir
            
            # Look for any subdirectory with Chart.yaml
            for item in os.listdir(downloaded_path):
                item_path = os.path.join(downloaded_path, item)
                if os.path.isdir(item_path):
                    chart_yaml_path = os.path.join(item_path, "Chart.yaml")
                    if os.path.exists(chart_yaml_path):
                        return item_path
            
            # Look recursively
            for root, dirs, files in os.walk(downloaded_path):
                if "Chart.yaml" in files:
                    return root
            
            return None
            
        except Exception as e:
            logging.error(f"Error finding chart directory: {e}")
            return None
    
    def _cleanup(self):
        """Clean up downloaded files"""
        if self.downloaded_chart_path and os.path.exists(self.downloaded_chart_path):
            try:
                import shutil
                shutil.rmtree(self.downloaded_chart_path, ignore_errors=True)
                self.downloaded_chart_path = None
            except Exception as e:
                logging.error(f"Error cleaning up upgrade download: {e}")
    
    def cancel(self):
        """Cancel the upgrade"""
        self._is_cancelled = True
        self.progress_update.emit("Cancelling upgrade...")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self._cleanup()


class HelmRollbackThread(QThread):
    """Thread for rolling back Helm releases"""
    
    rollback_complete = pyqtSignal(bool, str)
    progress_update = pyqtSignal(str)
    progress_percentage = pyqtSignal(int)
    
    def __init__(self, release_name: str, namespace: str, revision: int):
        super().__init__()
        self.release_name = release_name
        self.namespace = namespace
        self.revision = revision
        self.helm_client = None
        self._is_cancelled = False
        
    def run(self):
        """Execute the rollback process"""
        try:
            self.progress_update.emit("Initializing rollback...")
            self.progress_percentage.emit(10)
            
            # Initialize Helm client
            kube_client = get_kubernetes_client()
            if not kube_client or not kube_client.v1:
                self.rollback_complete.emit(False, "Kubernetes client not available")
                return
                
            self.helm_client = HelmClient(kube_client.v1)
            
            if self._is_cancelled:
                return
            
            self.progress_update.emit(f"Rolling back to revision {self.revision}...")
            self.progress_percentage.emit(50)
            
            # Perform the rollback
            success = self.helm_client.rollback_release(
                release_name=self.release_name,
                namespace=self.namespace,
                revision=self.revision
            )
            
            if self._is_cancelled:
                return
            
            if success:
                self.progress_percentage.emit(100)
                self.rollback_complete.emit(True, f"Successfully rolled back release {self.release_name} to revision {self.revision}")
            else:
                self.rollback_complete.emit(False, "Rollback failed")
                
        except Exception as e:
            logging.error(f"Rollback error: {e}")
            self.rollback_complete.emit(False, f"Rollback error: {str(e)}")
    
    def cancel(self):
        """Cancel the rollback"""
        self._is_cancelled = True
        self.progress_update.emit("Cancelling rollback...")


class ReleasesPage(BaseResourcePage):
    """Enhanced Releases page with proper upgrade and rollback functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "helmreleases"
        self.helm_client = None
        
        # Initialize Helm client
        kube_client = get_kubernetes_client()
        if kube_client and kube_client.v1:
            self.helm_client = HelmClient(kube_client.v1)
        
        # Release focus functionality
        self.focus_release = None
        self.focus_namespace = None
        self.force_refresh_for_focus = False
        self.focus_retry_attempted = False
        
        self.setup_page_ui()

    def setup_page_ui(self):
        """Setup the main UI elements for the Releases page"""
        headers = ["", "Name", "Namespace", "Chart", "Revision", "Version", "App Version", "Status", "Updated", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8}
        
        self.setup_ui("Releases", headers, sortable_columns)
        self.configure_columns()
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        self.table.setColumnWidth(1, 150)  # Name
        
        fixed_widths = {
            2: 120,  # Namespace
            4: 80,   # Revision
            7: 100,  # Status
            8: 120,  # Updated
            9: 40    # Actions
        }
        
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        
        # Set flexible columns
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Chart
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Version
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # App Version

    def load_data(self):
        """Load Helm releases data"""
        if self.is_loading:
            return
        
        if hasattr(self, 'loading_thread') and self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.wait(300)
        
        self.is_loading = True
        self.resources = []
        self.selected_items.clear()
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
        
        loading_text = QLabel("Loading Helm releases...")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        # Get namespace filter if available
        namespace_filter = None
        if hasattr(self, 'namespace_combo') and self.namespace_combo.currentText() != "All Namespaces":
            namespace_filter = self.namespace_combo.currentText()
        
        # Start loading thread
        self.loading_thread = HelmReleasesLoader(namespace_filter)
        self.loading_thread.releases_loaded.connect(self.on_resources_loaded)
        self.loading_thread.error_occurred.connect(self.on_load_error)
        self.loading_thread.start()

    def on_resources_loaded(self, resources: List[Dict], resource_type: str):
        """Handle loaded resources"""
        super().on_resources_loaded(resources, resource_type, next_continue_token="", load_more=False)
        
        # Handle focus functionality
        if self.focus_release and self.focus_namespace:
            release_found = any(
                r.get("name") == self.focus_release and 
                r.get("namespace", "default") == self.focus_namespace
                for r in resources
            )
            
            if not release_found and getattr(self, 'force_refresh_for_focus', False):
                self._fetch_release_directly(self.focus_release, self.focus_namespace)
                self.force_refresh_for_focus = False
                
            self.focus_on_release(self.focus_release, self.focus_namespace)
            self.focus_release = None
            self.focus_namespace = None

    def _fetch_release_directly(self, release_name: str, namespace: str):
        """Fetch a specific release directly"""
        if not self.helm_client:
            return False
            
        try:
            release = self.helm_client.get_release(release_name, namespace)
            if release:
                # Convert to expected format and add to resources
                age = self._format_age(release.updated)
                formatted_updated = self._format_updated_timestamp(release.updated)
                
                new_resource = {
                    "name": release.name,
                    "namespace": release.namespace,
                    "age": age,
                    "raw_data": {
                        "chart": f"{release.chart_name}-{release.chart_version}",
                        "revision": release.revision,
                        "version": release.chart_version,
                        "appVersion": release.app_version,
                        "status": release.status,
                        "updated": formatted_updated
                    }
                }
                
                self._add_release_to_resources(new_resource)
                return True
                
        except Exception as e:
            logging.error(f"Error fetching release {release_name}: {e}")
            
        return False

    def _format_age(self, timestamp: datetime.datetime) -> str:
        """Format age from timestamp"""
        if not timestamp:
            return "Unknown"
            
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                
            diff = now - timestamp
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"

    def _format_updated_timestamp(self, timestamp: datetime.datetime) -> str:
        """Format timestamp into human-readable relative time"""
        if not timestamp:
            return "<none>"
            
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                
            diff = now - timestamp
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            seconds = diff.seconds % 60
            
            if days > 0:
                return f"{days}d {hours}h ago"
            elif hours > 0:
                return f"{hours}h {minutes}m ago"
            elif minutes > 0:
                return f"{minutes}m {seconds}s ago"
            else:
                return f"{seconds}s ago"
        except Exception:
            return str(timestamp)

    def _add_release_to_resources(self, new_resource: Dict[str, Any]) -> bool:
        """Add a release to resources and update UI"""
        already_exists = any(
            r.get("name") == new_resource["name"] and 
            r.get("namespace") == new_resource["namespace"]
            for r in self.resources
        )
            
        if not already_exists:
            self.resources.append(new_resource)
            
            was_sorting_enabled = self.table.isSortingEnabled()
            self.table.setSortingEnabled(False)
            
            new_row = self.table.rowCount()
            self.table.setRowCount(new_row + 1)
            self.populate_resource_row(new_row, new_resource)
            
            self.table.setSortingEnabled(was_sorting_enabled)
            self.items_count.setText(f"{len(self.resources)} items")
            return True
            
        return False

    def populate_resource_row(self, row: int, resource: Dict[str, Any]):
        """Populate table row with release data"""
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for selection
        checkbox_container = self._create_checkbox_container(row, resource["name"])
        self.table.setCellWidget(row, 0, checkbox_container)
        
        raw_data = resource.get("raw_data", {})
        
        # Extract release information
        name = resource["name"]
        namespace = resource.get("namespace", "default")
        chart = raw_data.get("chart", "<none>")
        revision = str(raw_data.get("revision", ""))
        version = raw_data.get("version", "<none>")
        app_version = raw_data.get("appVersion", "<none>")
        status = raw_data.get("status", "<none>")
        updated = raw_data.get("updated", "<none>")
        
        # Table columns
        columns = [name, namespace, chart, revision, version, app_version, status, updated]
        
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle revision as numeric for sorting
            if col == 3:  # Revision column
                try:
                    sort_value = int(value)
                except (ValueError, TypeError):
                    sort_value = 0
                item = SortableTableWidgetItem(value, sort_value)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment and colors
            if col == 0:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            elif col == 6:  # Status column
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Color coding for status
                status_lower = str(value).lower()
                if "deployed" in status_lower or "success" in status_lower:
                    item.setForeground(QColor("#4CAF50"))  # Green
                elif "fail" in status_lower or "error" in status_lower:
                    item.setForeground(QColor("#f44336"))  # Red
                elif "pending" in status_lower or "installing" in status_lower:
                    item.setForeground(QColor("#2196F3"))  # Blue
                else:
                    item.setForeground(QColor("#9E9E9E"))  # Gray
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, cell_col, item)
            
        # Create action button
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(action_button)
        action_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    def _create_action_button(self, row: int, resource_name: str, resource_namespace: str) -> QToolButton:
        """Create action button for release row with upgrade and rollback options"""
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(30)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
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
        
        # Add actions
        upgrade_action = menu.addAction("Upgrade")
        upgrade_action.setIcon(QIcon("icons/edit.png"))
        
        rollback_action = menu.addAction("Rollback")
        rollback_action.setIcon(QIcon("icons/rollback.png"))
        
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(QIcon("icons/delete.png"))
        delete_action.setProperty("dangerous", True)
        
        # Connect actions
        upgrade_action.triggered.connect(
            lambda: self._handle_action("Upgrade", row)
        )
        rollback_action.triggered.connect(
            lambda: self._handle_action("Rollback", row)
        )
        delete_action.triggered.connect(
            lambda: self._handle_action("Delete", row)
        )
        
        button.setMenu(menu)
        return button

    def _handle_action(self, action: str, row: int):
        """Handle release action selection"""
        if row >= len(self.resources):
            return
            
        resource = self.resources[row]
        release_name = resource["name"]
        namespace = resource.get("namespace", "default")
        
        if action == "Upgrade":
            self.upgrade_release(release_name, namespace)
        elif action == "Rollback":
            self.rollback_release(release_name, namespace)
        elif action == "Delete":
            self.delete_release(release_name, namespace)

    def upgrade_release(self, release_name: str, namespace: str):
        """Upgrade a Helm release with enhanced thread management"""
        if not self.helm_client:
            QMessageBox.warning(self, "Helm Error", "Helm client not available")
            return
        
        # Check if upgrade thread is already running
        if hasattr(self, 'upgrade_thread') and self.upgrade_thread and self.upgrade_thread.isRunning():
            QMessageBox.warning(self, "Upgrade in Progress", 
                            "Another upgrade is already in progress. Please wait for it to complete.")
            return
        
        dialog = ReleaseUpgradeDialog(release_name, namespace, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_values()
            
            # Create progress dialog
            progress = QProgressDialog("Preparing upgrade...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Upgrading Release")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)  # Show immediately
            progress.show()
            
            # Create and configure upgrade thread
            self.upgrade_thread = HelmUpgradeThread(release_name, namespace, options)
            
            # Connect signals
            self.upgrade_thread.progress_update.connect(progress.setLabelText)
            self.upgrade_thread.progress_percentage.connect(progress.setValue)
            self.upgrade_thread.upgrade_complete.connect(
                lambda success, message: self._on_upgrade_complete(progress, success, message)
            )
            
            # Connect cancel button
            progress.canceled.connect(self._cancel_upgrade)
            
            # Set thread properties for proper cleanup
            self.upgrade_thread.setParent(self)
            self.upgrade_thread.finished.connect(self._cleanup_upgrade_thread)
            
            # Start the upgrade
            self.upgrade_thread.start()

    def rollback_release(self, release_name: str, namespace: str):
        """Rollback a Helm release to a previous revision"""
        if not self.helm_client:
            QMessageBox.warning(self, "Helm Error", "Helm client not available")
            return
        
        # Check if rollback thread is already running
        if hasattr(self, 'rollback_thread') and self.rollback_thread and self.rollback_thread.isRunning():
            QMessageBox.warning(self, "Rollback in Progress", 
                            "Another rollback is already in progress. Please wait for it to complete.")
            return
        
        dialog = ReleaseRollbackDialog(release_name, namespace, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            revision = dialog.get_selected_revision()
            if revision is None:
                QMessageBox.warning(self, "No Revision Selected", "Please select a revision to rollback to.")
                return
            
            # Confirm rollback
            result = QMessageBox.warning(
                self,
                "Confirm Rollback",
                f"Are you sure you want to rollback release '{release_name}' to revision {revision}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if result != QMessageBox.StandardButton.Yes:
                return
            
            # Create progress dialog
            progress = QProgressDialog("Preparing rollback...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Rolling Back Release")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()
            
            # Create and configure rollback thread
            self.rollback_thread = HelmRollbackThread(release_name, namespace, revision)
            
            # Connect signals
            self.rollback_thread.progress_update.connect(progress.setLabelText)
            self.rollback_thread.progress_percentage.connect(progress.setValue)
            self.rollback_thread.rollback_complete.connect(
                lambda success, message: self._on_rollback_complete(progress, success, message)
            )
            
            # Connect cancel button
            progress.canceled.connect(self._cancel_rollback)
            
            # Set thread properties for proper cleanup
            self.rollback_thread.setParent(self)
            self.rollback_thread.finished.connect(self._cleanup_rollback_thread)
            
            # Start the rollback
            self.rollback_thread.start()

    def _cancel_upgrade(self):
        """Cancel the upgrade operation"""
        if hasattr(self, 'upgrade_thread') and self.upgrade_thread and self.upgrade_thread.isRunning():
            self.upgrade_thread.cancel()
            # Wait a bit for graceful cancellation
            QTimer.singleShot(2000, self._force_stop_upgrade_thread)

    def _cancel_rollback(self):
        """Cancel the rollback operation"""
        if hasattr(self, 'rollback_thread') and self.rollback_thread and self.rollback_thread.isRunning():
            self.rollback_thread.cancel()
            # Wait a bit for graceful cancellation
            QTimer.singleShot(2000, self._force_stop_rollback_thread)

    def _force_stop_upgrade_thread(self):
        """Force stop upgrade thread if it doesn't stop gracefully"""
        if hasattr(self, 'upgrade_thread') and self.upgrade_thread and self.upgrade_thread.isRunning():
            self.upgrade_thread.terminate()
            self.upgrade_thread.wait(1000)  # Wait up to 1 second

    def _force_stop_rollback_thread(self):
        """Force stop rollback thread if it doesn't stop gracefully"""
        if hasattr(self, 'rollback_thread') and self.rollback_thread and self.rollback_thread.isRunning():
            self.rollback_thread.terminate()
            self.rollback_thread.wait(1000)

    def _cleanup_upgrade_thread(self):
        """Clean up upgrade thread"""
        if hasattr(self, 'upgrade_thread') and self.upgrade_thread:
            try:
                if self.upgrade_thread.isRunning():
                    self.upgrade_thread.wait(1000)
                self.upgrade_thread.deleteLater()
            except Exception as e:
                logging.error(f"Error cleaning up upgrade thread: {e}")
            finally:
                self.upgrade_thread = None

    def _cleanup_rollback_thread(self):
        """Clean up rollback thread"""
        if hasattr(self, 'rollback_thread') and self.rollback_thread:
            try:
                if self.rollback_thread.isRunning():
                    self.rollback_thread.wait(1000)
                self.rollback_thread.deleteLater()
            except Exception as e:
                logging.error(f"Error cleaning up rollback thread: {e}")
            finally:
                self.rollback_thread = None

    def _on_upgrade_complete(self, progress_dialog: QProgressDialog, success: bool, message: str):
        """Handle upgrade completion with proper cleanup"""
        try:
            progress_dialog.close()
            
            if success:
                QMessageBox.information(self, "Upgrade Success", message)
                # Refresh the releases list
                QTimer.singleShot(1000, self.load_data)
            else:
                QMessageBox.critical(self, "Upgrade Failed", message)
                
        except Exception as e:
            logging.error(f"Error in upgrade completion handler: {e}")
        finally:
            # Ensure thread cleanup
            QTimer.singleShot(100, self._cleanup_upgrade_thread)

    def _on_rollback_complete(self, progress_dialog: QProgressDialog, success: bool, message: str):
        """Handle rollback completion with proper cleanup"""
        try:
            progress_dialog.close()
            
            if success:
                QMessageBox.information(self, "Rollback Success", message)
                # Refresh the releases list
                QTimer.singleShot(1000, self.load_data)
            else:
                QMessageBox.critical(self, "Rollback Failed", message)
                
        except Exception as e:
            logging.error(f"Error in rollback completion handler: {e}")
        finally:
            # Ensure thread cleanup
            QTimer.singleShot(100, self._cleanup_rollback_thread)

    def delete_release(self, release_name: str, namespace: str):
        """Delete a Helm release"""
        if not self.helm_client:
            QMessageBox.warning(self, "Helm Error", "Helm client not available")
            return
            
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to uninstall Helm release {release_name} in namespace {namespace}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            
            success = self.helm_client.delete_release(release_name, namespace)
            
            QApplication.restoreOverrideCursor()
            
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Successfully uninstalled release {release_name}"
                )
                self.load_data()  # Refresh the list
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to uninstall release {release_name}"
                )
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Error",
                f"Error uninstalling release: {str(e)}"
            )

    def set_focus_release(self, release_name: str, namespace: str):
        """Set a release to focus on"""
        self.focus_release = release_name
        self.focus_namespace = namespace
        self.force_refresh_for_focus = True
        
        if self.isVisible():
            self.force_load_data()

    def focus_on_release(self, release_name: str, namespace: str):
        """Focus on a specific release in the table"""
        target_row = -1
        for row, resource in enumerate(self.resources):
            if (resource.get("name") == release_name and 
                resource.get("namespace", "default") == namespace):
                target_row = row
                break
        
        if target_row >= 0:
            self.table.setRowHidden(target_row, False)
            self.table.selectRow(target_row)
            self.table.scrollTo(self.table.model().index(target_row, 0))
            self.flash_row(target_row)
            return True
        else:
            if not hasattr(self, 'focus_retry_attempted') or not self.focus_retry_attempted:
                self.focus_retry_attempted = True
                QTimer.singleShot(2000, lambda: self._delayed_focus_retry(release_name, namespace))
            return False
        
    def _delayed_focus_retry(self, release_name: str, namespace: str):
        """Retry focusing after a delay"""
        if self._fetch_release_directly(release_name, namespace):
            self.focus_on_release(release_name, namespace)
        self.focus_retry_attempted = False

    def flash_row(self, row: int):
        """Flash a row to highlight it"""
        highlight_count = 0
        
        def toggle_highlight():
            nonlocal highlight_count
            
            cells = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    cells.append(item)
            
            if highlight_count % 2 == 0:
                for item in cells:
                    item.setBackground(QColor(AppColors.ACCENT_BLUE).darker(200))
            else:
                for item in cells:
                    item.setBackground(QColor(0, 0, 0, 0))
            
            highlight_count += 1
            
            if highlight_count >= 6:
                highlight_timer.stop()
        
        highlight_timer = QTimer(self)
        highlight_timer.timeout.connect(toggle_highlight)
        highlight_timer.start(300)

    def handle_row_click(self, row: int, column: int):
        """Handle row selection and open detail view"""
        if column != self.table.columnCount() - 1:  # Skip action column
            self.table.selectRow(row)
            
            parent = self.parent()
            while parent and not hasattr(parent, 'show_detail_for_table_item'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'show_detail_for_table_item'):
                parent.show_detail_for_table_item(row, column, self, "Releases")

    def force_load_data(self):
        """Force reload data"""
        self.is_loading = False
        self.load_data()