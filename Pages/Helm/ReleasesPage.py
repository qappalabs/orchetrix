"""
Optimized implementation of the Releases page that loads Helm releases data dynamically
with proper empty state handling and robust error detection.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout, QVBoxLayout,
    QMessageBox, QProgressBar, QApplication, QDialog, QFormLayout,
    QComboBox, QTextEdit, QDialogButtonBox, QProgressDialog, QMenu, QCheckBox,QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QIcon

import subprocess
import json
import datetime
import os
import platform
import shutil
import tempfile
import time

from base_components.base_resource_page import BaseResourcePage
from base_components.base_components import SortableTableWidgetItem
from UI.Styles import AppColors, AppStyles

class HelmReleasesLoader(QThread):
    """Thread to load Helm releases without blocking the UI"""
    releases_loaded = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, namespace=None):
        super().__init__()
        self.namespace = namespace
        
    def run(self):
        """Execute the Helm list command and emit results"""
        try:
            # Check if helm is installed first
            helm_path = find_helm_executable()
            if not helm_path:
                self.error_occurred.emit("Helm CLI not found. Please install Helm to view releases.")
                self.releases_loaded.emit([], "helmreleases")
                return
                
            # Build command
            cmd = [helm_path, "list", "--output", "json"]
            
            # Apply namespace if specified
            if self.namespace and self.namespace != "all":
                cmd.extend(["-n", self.namespace])
            else:
                cmd.append("--all-namespaces")
                
            # Execute the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Process the result
            releases = []
            try:
                # Parse JSON output
                data = json.loads(result.stdout)
                
                for item in data:
                    # Calculate age/updated time
                    updated_raw = item.get("updated", "")
                    age = "Unknown"
                    formatted_updated = "<none>"
                    
                    if updated_raw:
                        age = format_age(updated_raw)
                        formatted_updated = format_updated_timestamp(updated_raw)
                    
                    # Create resource object with correct field mapping
                    release = {
                        "name": item.get("name", ""),
                        "namespace": item.get("namespace", "default"),
                        "age": age,
                        "raw_data": {
                            "chart": item.get("chart", "<none>"),
                            "revision": item.get("revision", 1),
                            "version": item.get("version", "<none>"),
                            "appVersion": item.get("app_version", "<none>"),
                            "status": item.get("status", "<none>"),
                            "updated": formatted_updated
                        }
                    }
                    releases.append(release)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to parse the output line by line
                if not result.stdout.strip():
                    # Empty output means no releases found
                    self.releases_loaded.emit([], "helmreleases")
                    return
                    
                # Parse table output for older Helm versions
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Header + at least one data row
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 5:  # Basic validation
                            release = {
                                "name": parts[0],
                                "namespace": parts[1] if len(parts) > 5 else "default",
                                "age": parts[-1],
                                "raw_data": {
                                    "chart": parts[2],
                                    "revision": parts[3],
                                    "version": parts[4] if len(parts) > 4 else "<none>",
                                    "appVersion": "<none>",
                                    "status": parts[5] if len(parts) > 5 else "<none>",
                                    "updated": parts[-1]  # For older Helm, use the age directly
                                }
                            }
                            releases.append(release)
                if not releases:
                    self.error_occurred.emit("Failed to parse Helm releases output")
                
            # Emit the loaded releases
            self.releases_loaded.emit(releases, "helmreleases")
            
        except subprocess.CalledProcessError as e:
            # Error handling code
            stderr = e.stderr if hasattr(e, 'stderr') else ""
            
            if "No such file or directory" in str(e) or "not found" in str(e):
                self.error_occurred.emit("Helm CLI not found. Please install Helm to view releases.")
            elif "could not find a ready tiller pod" in stderr.lower():
                self.error_occurred.emit("Tiller not ready. Please check your Helm installation.")
            else:
                self.error_occurred.emit(f"Error loading Helm releases: {stderr}")
            
            self.releases_loaded.emit([], "helmreleases")
            
        except FileNotFoundError:
            self.error_occurred.emit("Item list is empty.")
            self.releases_loaded.emit([], "helmreleases")
            
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
            self.releases_loaded.emit([], "helmreleases")


def find_helm_executable():
    """Find the helm executable on the system"""
    # First check if helm is in PATH
    helm_exe = "helm.exe" if platform.system() == "Windows" else "helm"
    helm_path = shutil.which(helm_exe)
    
    if helm_path:
        return helm_path
        
    # Check common installation locations based on platform
    common_paths = []
    if platform.system() == "Windows":
        common_paths = [
            os.path.expanduser("~\\helm\\helm.exe"),
            "C:\\Program Files\\Helm\\helm.exe",
            "C:\\helm\\helm.exe",
            os.path.expanduser("~\\.windows-package-manager\\helm\\helm.exe"),
            os.path.expanduser("~\\AppData\\Local\\Programs\\Helm\\helm.exe")
        ]
    else:
        common_paths = [
            "/usr/local/bin/helm",
            "/usr/bin/helm",
            os.path.expanduser("~/bin/helm"),
            "/opt/homebrew/bin/helm"  # Common on macOS with Homebrew
        ]
        
    for path in common_paths:
        if os.path.isfile(path):
            return path
    
    # Not found
    return None


def format_age(timestamp):
    """Format the age field from a timestamp"""
    if not timestamp:
        return "Unknown"
        
    try:
        # Parse the timestamp to datetime object
        updated_time = parse_timestamp(timestamp)
        if not updated_time:
            return "Unknown"
            
        # Get current time and calculate difference
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - updated_time
        
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


def format_updated_timestamp(timestamp):
    """Format timestamp into human-readable relative time format"""
    if not timestamp or timestamp == "<none>":
        return "<none>"
        
    # If it's already formatted, return as is
    if "ago" in timestamp or timestamp == "Just now":
        return timestamp
        
    try:
        updated_time = parse_timestamp(timestamp)
        if not updated_time:
            return timestamp
            
        # Calculate time difference
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - updated_time
        
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        seconds = diff.seconds % 60
        
        # Format in relative time
        if days > 0:
            return f"{days}d {hours}h ago"
        elif hours > 0:
            return f"{hours}h {minutes}m ago"
        elif minutes > 0:
            return f"{minutes}m {seconds}s ago"
        else:
            return f"{seconds}s ago"
    except Exception:
        return timestamp


def parse_timestamp(timestamp):
    """Parse a timestamp string into a datetime object"""
    if not timestamp or not isinstance(timestamp, str):
        return None
        
    # Try various timestamp formats
    try:
        # Handle ISO format with Z
        if 'Z' in timestamp:
            try:
                return datetime.datetime.strptime(
                    timestamp.replace('Z', '+00:00'), 
                    "%Y-%m-%dT%H:%M:%S%z"
                )
            except ValueError:
                try:
                    return datetime.datetime.strptime(
                        timestamp.replace('Z', '+00:00'), 
                        "%Y-%m-%dT%H:%M:%S.%f%z"
                    )
                except ValueError:
                    pass
        
        # Handle IST format
        elif " IST" in timestamp:
            import re
            pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.?\d* (\+\d{4}) IST"
            match = re.search(pattern, timestamp)
            
            if match:
                date_part = match.group(1)
                offset = match.group(2)
                
                offset_hours = int(offset[1:3])
                offset_minutes = int(offset[3:5])
                offset_sign = 1 if offset[0] == '+' else -1
                offset_seconds = offset_sign * (offset_hours * 3600 + offset_minutes * 60)
                tz_info = datetime.timezone(datetime.timedelta(seconds=offset_seconds))
                
                updated_time = datetime.datetime.strptime(date_part, "%Y-%m-%d %H:%M:%S")
                return updated_time.replace(tzinfo=tz_info)
        
        # Try other common formats
        formats = [
            "%Y-%m-%d %H:%M:%S.%f %z",
            "%Y-%m-%d %H:%M:%S %z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(timestamp, fmt)
                # If no timezone, assume UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                return dt
            except ValueError:
                continue
                
        return None
    except Exception:
        return None
    
class ReleaseUpgradeDialog(QDialog):
    """Dialog for upgrading Helm releases with version and values input"""
    def __init__(self, release_name, namespace, parent=None):
        super().__init__(parent)
        self.release_name = release_name
        self.namespace = namespace
        self.setWindowTitle(f"Upgrade Release: {release_name}")
        self.setMinimumWidth(550)
        self.setStyleSheet(f"""
            background-color: {AppColors.BG_DARK};
            color: {AppColors.TEXT_LIGHT};
        """)
        self.setup_ui()
        self.load_current_values()
    
    def setup_ui(self):
        """Set up the dialog UI with inputs for upgrade parameters"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Form layout for inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Chart input field (optional)
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
        """Load the current chart and values for the release"""
        try:
            # Find helm executable
            helm_path = find_helm_executable()
            if not helm_path:
                return
            
            # Get current chart from helm list
            list_cmd = [helm_path, "list", "--filter", f"^{self.release_name}$", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    releases = json.loads(result.stdout)
                    if releases and len(releases) > 0:
                        # Get chart name and set as placeholder
                        chart = releases[0].get("chart", "")
                        if chart:
                            self.chart_input.setPlaceholderText(f"Current: {chart}")
                except json.JSONDecodeError:
                    pass
            
            # Get current values
            values_cmd = [helm_path, "get", "values", self.release_name, "-n", self.namespace, "-o", "yaml"]
            result = subprocess.run(values_cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                # Check if stdout is empty
                yaml_content = result.stdout.strip()
                if not yaml_content:
                    yaml_content = "# No custom values set for this release"
                
                # Make sure we're not setting the text to "null"
                if yaml_content == "null":
                    yaml_content = "# No custom values set for this release"
                
                # Set values in editor
                self.values_editor.setPlainText(yaml_content)
            else:
                # Failed to get values
                self.values_editor.setPlainText("# Could not retrieve current values")
                
                
        except Exception as e:
            pass
            self.values_editor.setPlainText("# Error loading current values")
    
    def get_values(self):
        """Get values from the dialog"""
        return {
            "chart": self.chart_input.text().strip(),
            "version": self.version_input.text().strip(),
            "values": self.values_editor.toPlainText().strip(),
            "atomic": self.atomic_checkbox.isChecked()
        }
class ReleasesPage(BaseResourcePage):
    """
    Displays Helm releases with dynamic data loading and optimizations for performance.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "helmreleases"  # Custom resource type for Helm releases
        
        # Flag to indicate if we should focus on a specific release
        self.focus_release = None
        self.focus_namespace = None
        self.force_refresh_for_focus = False
        self.focus_retry_attempted = False
        
        # Initialize UI
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the Releases page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Chart", "Revision", "Version", "App Version", "Status", "Updated", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8}
        
        # Set up the base UI components
        layout = self.setup_ui("Releases", headers, sortable_columns)
        
        # Configure column widths
        self.configure_columns()
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Set minimum width for name column
        self.table.setColumnWidth(1, 150)
        
        # Configure fixed width columns
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
        
        # Set chart and version columns to be flexible
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Chart
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Version
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # App Version

    def load_data(self):
        """Load resource data with improved detection of all releases including partial ones"""
        if self.is_loading:
            return
        
        # Clean up any existing loading thread
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
        
        loading_text = QLabel(f"Loading Helm releases...")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        # Get namespace filter value if it exists
        namespace_filter = None
        if hasattr(self, 'namespace_combo') and self.namespace_combo.currentText() != "All Namespaces":
            namespace_filter = self.namespace_combo.currentText()
        
        # Start loading thread
        self.loading_thread = HelmReleasesLoader(namespace_filter)
        self.loading_thread.releases_loaded.connect(self.on_resources_loaded)
        self.loading_thread.error_occurred.connect(self.on_load_error)
        self.loading_thread.start()
        
        # After starting the normal loader, look for partial releases as well
        QTimer.singleShot(1500, self.find_partial_installations)

    def find_partial_installations(self):
        """Find partial installations by looking for Helm secrets"""
        if not hasattr(self, 'resources') or not self.resources:
            return
        
        try:
            # Get namespace filter
            namespace = None
            if hasattr(self, 'namespace_combo') and self.namespace_combo.currentText() != "All Namespaces":
                namespace = self.namespace_combo.currentText()
            
            # Get all Helm secrets that might represent releases
            cmd = ["kubectl", "get", "secrets"]
            
            if namespace:
                cmd.extend(["-n", namespace])
            else:
                cmd.append("--all-namespaces")
                
            cmd.extend(["-o", "wide", "--field-selector", "metadata.name~=sh.helm.release"])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                
                # Skip header
                if len(lines) > 1:
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 2:
                            secret_name = parts[0]
                            secret_namespace = parts[0] if namespace else parts[0]
                            
                            # Extract release name from secret name
                            if "sh.helm.release.v1." in secret_name:
                                # Format: sh.helm.release.v1.RELEASE_NAME.v1
                                release_name = secret_name.split("sh.helm.release.v1.")[1].split(".v")[0]
                                
                                # Check if this release is already in our resources
                                existing = False
                                for resource in self.resources:
                                    if resource["name"] == release_name and resource.get("namespace") == secret_namespace:
                                        existing = True
                                        break
                                
                                if not existing:
                                    self._fetch_release_directly(release_name, secret_namespace)
        except Exception as e:
            pass

    def on_resources_loaded(self, resources, resource_type):
        """Handle loaded resources with improved focus handling"""
        # Call parent method first
        super().on_resources_loaded(resources, resource_type)
        
        # If we need to focus on a specific release, check if it's in the resources
        if self.focus_release and self.focus_namespace:
            # Check if the release we're looking for is in the loaded resources
            release_found = False
            for resource in resources:
                if (resource.get("name") == self.focus_release and 
                    resource.get("namespace", "default") == self.focus_namespace):
                    release_found = True
                    break
            
            # If not found and we need to force refresh
            if not release_found and getattr(self, 'force_refresh_for_focus', False):
                # Try to fetch it directly using Helm
                self._fetch_release_directly(self.focus_release, self.focus_namespace)
                # Clear the force refresh flag
                self.force_refresh_for_focus = False
                
            # Focus on the release (whether it was found or fetched)
            self.focus_on_release(self.focus_release, self.focus_namespace)
            
            # Clear the focus params after focusing once
            self.focus_release = None
            self.focus_namespace = None

    def _fetch_release_directly(self, release_name, namespace):
        """Fetch a specific release directly using multiple methods including partial installations"""
        # Try multiple methods to find the release
        helm_path = find_helm_executable()
        
        # Method 1: Try helm list with increased timeout
        if helm_path:
            try:
                # Run helm command with a longer timeout
                cmd = [
                    helm_path, "list",
                    "--namespace", namespace,
                    "--filter", f"^{release_name}$",
                    "--output", "json"
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=20,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    releases = json.loads(result.stdout)
                    if releases and len(releases) > 0:
                        # Process the found release and add to resources
                        self._process_direct_release(releases[0], namespace)
                        return True
            except Exception as e:
                pass
        
        # Method 2: Check for Helm secrets directly
        try:
            # Look for Helm 3 secrets
            secret_cmd = [
                "kubectl", "get", "secret",
                "-n", namespace,
                "--field-selector", f"metadata.name=sh.helm.release.v1.{release_name}.v*",
                "--no-headers"
            ]
            
            result = subprocess.run(secret_cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and "No resources found" not in result.stdout:
                # Create a minimal release object
                self._create_minimal_release(release_name, namespace, "failed/partial")
                return True
        except Exception as e:
            pass
        
        # Method 3: Check with kubectl get all resources by common labels
        try:
            label_cmd = [
                "kubectl", "get", "all",
                "-n", namespace,
                "-l", f"app.kubernetes.io/instance={release_name}",
                "--no-headers"
            ]
            
            result = subprocess.run(label_cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and result.stdout.strip():
                # Create minimal release object
                self._create_minimal_release(release_name, namespace, "deployed")
                return True
        except Exception as e:
            pass
        
        return False

    def _process_direct_release(self, release_data, namespace):
        """Process release data from direct fetch and add to resources"""
        # Calculate age
        updated_raw = release_data.get("updated", "")
        age = format_age(updated_raw)
        
        # Format the updated timestamp for the Updated column
        formatted_updated = format_updated_timestamp(updated_raw)

        # Create resource object with the properly formatted timestamp
        new_resource = {
            "name": release_data.get("name", ""),
            "namespace": namespace,
            "age": age,
            "raw_data": {
                "chart": release_data.get("chart", "<none>"),
                "revision": release_data.get("revision", 1),
                "version": release_data.get("chart_version", "<none>"),
                "appVersion": release_data.get("app_version", "<none>"),
                "status": release_data.get("status", "<none>"),
                "updated": formatted_updated
            }
        }
        
        # Add to resources if not already present
        self._add_release_to_resources(new_resource)

    def _create_minimal_release(self, release_name, namespace, status):
        """Create a minimal release object and add to resources"""
        # Create minimal release object
        new_resource = {
            "name": release_name,
            "namespace": namespace,
            "age": "0m",  # Just installed
            "raw_data": {
                "chart": "unknown",
                "revision": 1,
                "version": "unknown",
                "appVersion": "unknown",
                "status": status,
                "updated": "Just now"
            }
        }
        # Add to resources
        self._add_release_to_resources(new_resource)

    def _add_release_to_resources(self, new_resource):
        """Add a release to resources and update UI if not already present"""
        # Check if release already exists
        already_exists = False
        for r in self.resources:
            if r.get("name") == new_resource["name"] and r.get("namespace") == new_resource["namespace"]:
                already_exists = True
                break
                
        if not already_exists:
            # Add to resources and update UI
            self.resources.append(new_resource)
            
            # Update table with new resource
            was_sorting_enabled = self.table.isSortingEnabled()
            self.table.setSortingEnabled(False)
            
            new_row = self.table.rowCount()
            self.table.setRowCount(new_row + 1)
            self.populate_resource_row(new_row, new_resource)
            
            self.table.setSortingEnabled(was_sorting_enabled)
            
            # Update count
            self.items_count.setText(f"{len(self.resources)} items")
            return True
            
        return False

    def on_load_error(self, error_message):
        """Handle loading errors with better empty state presentation"""
        self.is_loading = False
        
        # Clear loading indicator and show error message directly in the table
        self.table.setRowCount(0)
        
        # Create overlay for error message if it doesn't exist
        if not hasattr(self, 'empty_overlay'):
            self.empty_overlay = QLabel()
            self.empty_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_overlay.setStyleSheet("""
                color: #888888;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                padding: 20px;
                margin: 20px;
            """)
            self.empty_overlay.setParent(self.table)
            self.empty_overlay.setWordWrap(True)
        
        # Set error message
        self.empty_overlay.setText(error_message)
        
        # Position the overlay relative to the table
        header_height = self.table.horizontalHeader().height()
        table_visible_height = self.table.height() - header_height
        
        # Set the geometry relative to the table
        self.empty_overlay.setGeometry(
            0,  # X position relative to table
            header_height,  # Y position just below header
            self.table.width(),  # Full table width
            table_visible_height  # Remaining table height
        )
        
        # Make sure the overlay is visible and on top
        self.empty_overlay.show()
        self.empty_overlay.raise_()

    def populate_resource_row(self, row, resource):
        """Populate a row with improved status indication for failed/partial installations"""
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        checkbox_container = self._create_checkbox_container(row, resource["name"])
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Get raw data for the release
        raw_data = resource.get("raw_data", {})
        
        # Extract data from resource
        name = resource["name"]
        namespace = resource.get("namespace", "default")
        chart = raw_data.get("chart", "<none>")
        revision = str(raw_data.get("revision", ""))
        
        # Version
        version = raw_data.get("version", raw_data.get("chart_version", "<none>"))
        if version == "<none>":
            if "-" in chart:
                chart_parts = chart.split("-")
                potential_version = chart_parts[-1]
                if potential_version and (potential_version[0].isdigit() or potential_version[0] == 'v'):
                    version = potential_version
        
        app_version = raw_data.get("appVersion", "<none>")
        
        # Status
        status = raw_data.get("status", "<none>")
        if status == "failed/partial":
            status = "Failed/Partial"
        
        # Get the updated value
        updated = raw_data.get("updated", "<none>")
        
        # Prepare the data columns - make sure order matches table headers
        columns = [name, namespace, chart, revision, version, app_version, status, updated]
        
        # Add items to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # For revision, ensure it's sortable by number
            if col == 3:  # Revision column
                try:
                    sort_value = int(value)
                except (ValueError, TypeError):
                    sort_value = 0
                item = SortableTableWidgetItem(value, sort_value)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col == 0:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            elif col == 6:  # Status column
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Set color based on status
                status_lower = str(value).lower()
                if status_lower == "failed/partial":
                    item.setForeground(QColor("#ff9800"))  # Orange for partial/failed
                elif "deployed" in status_lower or "success" in status_lower:
                    item.setForeground(QColor("#4CAF50"))  # Green for success
                elif "fail" in status_lower or "error" in status_lower or "bad" in status_lower:
                    item.setForeground(QColor("#f44336"))  # Red for error
                elif "pending" in status_lower or "installing" in status_lower or "loading" in status_lower:
                    item.setForeground(QColor("#2196F3"))  # Blue for pending
                else:
                    item.setForeground(QColor("#9E9E9E"))  # Gray for unknown
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
            
        # Create action button with appropriate options based on status
        action_button = None
        if status.lower() == "failed/partial":
            # For failed/partial installations, offer cleanup option
            action_button = self._create_failed_action_button(row, resource["name"], resource["namespace"])
        else:
            # For normal installations, use standard actions
            action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(action_button)
        action_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    def _create_failed_action_button(self, row, resource_name, resource_namespace):
        """Create an action button specifically for failed/partial installations"""
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(30)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet("""
            QToolButton {
                color: #ff9800;  /* Orange for warning */
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
        
        # Add special actions for failed/partial installations
        retry_action = menu.addAction("Retry Installation")
        retry_action.setIcon(QIcon("icons/refresh.png"))
        
        cleanup_action = menu.addAction("Clean Up")
        cleanup_action.setIcon(QIcon("icons/delete.png"))
        cleanup_action.setProperty("dangerous", True)
        
        # Connect actions
        retry_action.triggered.connect(
            lambda: self._handle_retry_installation(row, resource_name, resource_namespace)
        )
        
        cleanup_action.triggered.connect(
            lambda: self._handle_cleanup_installation(row, resource_name, resource_namespace)
        )
        
        button.setMenu(menu)
        return button

    def _handle_retry_installation(self, row, resource_name, resource_namespace):
        """Handle retry installation action for failed/partial installations"""
        # Show confirmation dialog
        result = QMessageBox.question(
            self,
            "Retry Installation",
            f"Do you want to retry the installation of release {resource_name}?\n\n"
            f"This will attempt to reinstall the chart.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Find helm binary
        helm_path = find_helm_executable()
        
        if not helm_path:
            QMessageBox.critical(
                self,
                "Helm Not Found",
                "Helm CLI not found. Please install Helm to retry installation."
            )
            return
        
        # Create progress dialog
        progress = QProgressDialog("Retrying installation...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Retrying Installation")
        progress.setModal(True)
        progress.setValue(10)
        progress.show()
        QApplication.processEvents()
        
        try:
            # First, uninstall the existing release
            progress.setLabelText("Cleaning up previous installation...")
            progress.setValue(30)
            QApplication.processEvents()
            
            uninstall_cmd = [
                helm_path, "uninstall",
                resource_name,
                "--namespace", resource_namespace,
                "--keep-history"  # Keep history for debugging
            ]
            
            subprocess.run(uninstall_cmd, capture_output=True, text=True, timeout=30)
            
            # Wait a moment for cleanup
            progress.setLabelText("Preparing to reinstall...")
            progress.setValue(50)
            QApplication.processEvents()
            
            time.sleep(2)
            
            # Then reinstall using bitnami as reliable repository
            progress.setLabelText("Reinstalling chart...")
            progress.setValue(70)
            QApplication.processEvents()
            
            # First make sure bitnami repo is added
            try:
                add_cmd = [helm_path, "repo", "add", "bitnami", "https://charts.bitnami.com/bitnami"]
                subprocess.run(add_cmd, capture_output=True, text=True, timeout=15)
                
                update_cmd = [helm_path, "repo", "update"]
                subprocess.run(update_cmd, capture_output=True, text=True, timeout=30)
            except:
                pass
            
            # Try to find a suitable chart in bitnami
            chart_name = resource_name.lower()
            install_cmd = [
                helm_path, "install",
                resource_name,
                f"bitnami/{chart_name}",
                "--namespace", resource_namespace,
                "--create-namespace"
            ]
            
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=60)
            
            progress.setValue(100)
            progress.close()
            
            if result.returncode == 0:
                QMessageBox.information(
                    self,
                    "Reinstallation Successful",
                    f"Release {resource_name} has been successfully reinstalled."
                )
                
                # Refresh the data
                self.load_data()
            else:
                QMessageBox.critical(
                    self,
                    "Reinstallation Failed",
                    f"Failed to reinstall release {resource_name}.\n\n"
                    f"Error: {result.stderr}"
                )
        except Exception as e:
            progress.close()
            
            QMessageBox.critical(
                self,
                "Reinstallation Error",
                f"Error reinstalling release: {str(e)}"
            )

    def _handle_cleanup_installation(self, row, resource_name, resource_namespace):
        """Handle cleanup action for failed/partial installations"""
        # Show confirmation dialog
        result = QMessageBox.warning(
            self,
            "Confirm Cleanup",
            f"Are you sure you want to clean up the failed installation of {resource_name}?\n\n"
            f"This will remove all resources associated with this release.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Create progress dialog
        progress = QProgressDialog("Cleaning up installation...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Cleaning Up")
        progress.setModal(True)
        progress.setValue(10)
        progress.show()
        QApplication.processEvents()
        
        try:
            # First try regular helm uninstall
            progress.setLabelText("Attempting helm uninstall...")
            progress.setValue(20)
            QApplication.processEvents()
            
            helm_path = find_helm_executable()
            
            if helm_path:
                uninstall_cmd = [
                    helm_path, "uninstall",
                    resource_name,
                    "--namespace", resource_namespace
                ]
                
                subprocess.run(uninstall_cmd, capture_output=True, text=True, timeout=30)
            
            # Then clean up Helm secrets directly
            progress.setLabelText("Cleaning up Helm secrets...")
            progress.setValue(50)
            QApplication.processEvents()
            
            secret_cmd = [
                "kubectl", "delete", "secret",
                "-n", resource_namespace,
                "--field-selector", f"metadata.name=sh.helm.release.v1.{resource_name}.v*"
            ]
            
            subprocess.run(secret_cmd, capture_output=True, text=True, timeout=30)
            
            # Finally check for any resources with the release name
            progress.setLabelText("Cleaning up related resources...")
            progress.setValue(80)
            QApplication.processEvents()
            
            # Common resource types that might be created by Helm charts
            resource_types = [
                "deployment", "statefulset", "service", "configmap", 
                "secret", "pod", "job", "daemonset", "replicaset"
            ]
            
            for resource_type in resource_types:
                try:
                    # Try to find resources with common Helm labels
                    label_cmd = [
                        "kubectl", "delete", resource_type,
                        "-n", resource_namespace,
                        "-l", f"app.kubernetes.io/instance={resource_name}"
                    ]
                    
                    subprocess.run(label_cmd, capture_output=True, text=True, timeout=15)
                    
                    # Also try by name pattern
                    name_cmd = [
                        "kubectl", "get", resource_type,
                        "-n", resource_namespace,
                        "--no-headers"
                    ]
                    
                    result = subprocess.run(name_cmd, capture_output=True, text=True, timeout=15)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        # Look for resources with the release name in their name
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                parts = line.strip().split()
                                if parts and resource_name.lower() in parts[0].lower():
                                    # Delete this resource
                                    delete_cmd = [
                                        "kubectl", "delete", resource_type,
                                        parts[0],
                                        "-n", resource_namespace
                                    ]
                                    
                                    subprocess.run(delete_cmd, capture_output=True, text=True, timeout=15)
                except:
                    continue
            
            progress.setValue(100)
            progress.close()
            
            QMessageBox.information(
                self,
                "Cleanup Successful",
                f"Release {resource_name} has been cleaned up successfully."
            )
            
            # Refresh the data
            self.load_data()
        except Exception as e:
            progress.close()
            
            QMessageBox.critical(
                self,
                "Cleanup Error",
                f"Error cleaning up release: {str(e)}"
            )

    def _create_action_button(self, row, resource_name, resource_namespace):
        """Create an action button with enhanced upgrade and delete options"""
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
        
        # Add actions with icons
        actions = [
            {"text": "Upgrade", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ]
        
        # Add actions to menu
        for action_info in actions:
            action = menu.addAction(action_info["text"])
            if "icon" in action_info:
                action.setIcon(QIcon(action_info["icon"]))
            if action_info.get("dangerous", False):
                action.setProperty("dangerous", True)
            action.triggered.connect(
                lambda checked, action=action_info["text"], row=row: self._handle_action(action, row)
            )
        
        button.setMenu(menu)
        return button
    
    def upgrade_release(self, release_name, namespace):
        """Upgrade a Helm release with user input for parameters"""
        # Find Helm executable
        helm_path = find_helm_executable()
        
        if not helm_path:
            QMessageBox.warning(
                self,
                "Helm Not Found",
                "Helm CLI not found. Please install Helm to upgrade releases."
            )
            return
        
        # Create and show upgrade dialog
        dialog = ReleaseUpgradeDialog(release_name, namespace, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get upgrade options from dialog
            options = dialog.get_values()
            
            # Show progress dialog
            progress = QProgressDialog("Upgrading release...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Upgrading Release")
            progress.setModal(True)
            progress.setValue(10)
            progress.show()
            QApplication.processEvents()
            
            try:
                # Build the upgrade command
                cmd = [helm_path, "upgrade", release_name]
                
                # Add chart reference
                chart = options.get("chart")
                if not chart:
                    # If chart not specified, use current chart from release
                    # First get current chart name with repository
                    info_cmd = [helm_path, "list", "--filter", f"^{release_name}$", "-n", namespace, "-o", "json"]
                    result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=15)
                    release_info = None
                    
                    if result.returncode == 0 and result.stdout.strip():
                        try:
                            releases = json.loads(result.stdout)
                            if releases and len(releases) > 0:
                                release_info = releases[0]
                                # Use chart name without version, but keep repository prefix
                                chart_full = release_info.get("chart", "")
                                # We need to handle two possible formats:
                                # 1. repo/chart-version
                                # 2. chart-version (need to find repo from another command)
                                
                                if '/' in chart_full:  # Format: repo/chart-version
                                    repo, chart_with_version = chart_full.split('/', 1)
                                    # Keep just repo/chart without version
                                    if '-' in chart_with_version:
                                        version_parts = chart_with_version.split('-')
                                        if len(version_parts) > 1 and version_parts[-1][0].isdigit():
                                            chart = f"{repo}/{'-'.join(version_parts[:-1])}"
                                        else:
                                            chart = chart_full
                                    else:
                                        chart = chart_full
                                else:  # Format: chart-version, need to find repo
                                    # Try to get repository from status command
                                    status_cmd = [helm_path, "status", release_name, "-n", namespace, "--output", "json"]
                                    status_result = subprocess.run(status_cmd, capture_output=True, text=True, timeout=15)
                                    
                                    # Look for repository information in status output
                                    if status_result.returncode == 0:
                                        try:
                                            status_data = json.loads(status_result.stdout)
                                            chart_meta = status_data.get("chart", {}).get("metadata", {})
                                            
                                            # Get repository URL/name from chart metadata if available
                                            repo_url = chart_meta.get("home", "")
                                            sources = chart_meta.get("sources", [])
                                            if sources and len(sources) > 0:
                                                repo_url = sources[0]
                                            
                                            # Extract repo name from URL if possible
                                            if repo_url:
                                                import re
                                                # Try to extract repo name from URL pattern
                                                match = re.search(r'github\.com/([^/]+/[^/]+)', repo_url)
                                                if match:
                                                    repo_name = match.group(1)
                                                    chart = f"{repo_name}/{chart_meta.get('name', '')}"
                                                else:
                                                    match = re.search(r'([^/\.]+)\.github\.io', repo_url)
                                                    if match:
                                                        repo_name = match.group(1)
                                                        chart = f"{repo_name}/{chart_meta.get('name', '')}"
                                                    else:
                                                        # Just use bitnami as a fallback for common charts
                                                        if "bitnami" in status_result.stdout.lower():
                                                            repo_name = "bitnami"
                                                            chart = f"{repo_name}/{chart_meta.get('name', '')}"
                                                        else:
                                                            # As a last resort, use the chart name directly
                                                            chart = chart_meta.get('name', chart_full.split('-')[0])
                                            else:
                                                # No repo info, try with chart name alone
                                                chart = chart_meta.get('name', chart_full.split('-')[0])
                                        except json.JSONDecodeError:
                                            # If can't get repo info, use chart name alone
                                            chart = chart_full.split('-')[0]
                                    else:
                                        # If can't get repo info, use chart name alone
                                        chart = chart_full.split('-')[0]
                        except json.JSONDecodeError:
                            pass
                
                if not chart:
                    progress.close()
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Could not determine chart name. Please specify the chart explicitly."
                    )
                    return
                
                # If chart doesn't contain a slash, prepend the most likely repo
                if chart and '/' not in chart:
                    # Common repositories to try
                    common_repos = ["bitnami", "stable", "prometheus-community", "jetstack", "hashicorp"]
                    
                    # Try to detect the most likely repo if we have release info
                    detected_repo = None
                    if release_info:
                        chart_name = release_info.get("chart", "").lower()
                        if "bitnami" in chart_name:
                            detected_repo = "bitnami"
                        elif "prometheus" in chart_name:
                            detected_repo = "prometheus-community" 
                        elif "grafana" in chart_name:
                            detected_repo = "grafana"
                        elif "nginx" in chart_name:
                            detected_repo = "nginx-stable"
                        elif "cert-manager" in chart_name:
                            detected_repo = "jetstack"
                        elif "consul" in chart_name or "vault" in chart_name:
                            detected_repo = "hashicorp"
                    
                    # Use detected repo or default to bitnami
                    repo_prefix = detected_repo or common_repos[0]
                    chart = f"{repo_prefix}/{chart}"
                    
                    # Log the chart reference for debugging
                    
                    
                # Add chart to command
                cmd.append(chart)
                
                # Add namespace
                cmd.extend(["-n", namespace])
                
                # Add version if specified
                if options.get("version"):
                    cmd.extend(["--version", options.get("version")])
                
                # Add values file if provided
                values_file = None
                if options.get("values"):
                    # Create temporary file for values
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w") as temp:
                        temp.write(options.get("values"))
                        values_file = temp.name
                    cmd.extend(["-f", values_file])
                
                # Add --atomic flag for atomic upgrades (rollback on failure)
                if options.get("atomic", True):
                    cmd.append("--atomic")
                
                # Update progress
                progress.setValue(30)
                progress.setLabelText("Executing upgrade command...")
                QApplication.processEvents()
                
                #  the command for debugging
              
                
                # Execute the command
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                # Clean up values file
                if values_file and os.path.exists(values_file):
                    os.unlink(values_file)
                
                progress.setValue(100)
                progress.close()
                
                if result.returncode == 0:
                    QMessageBox.information(
                        self,
                        "Upgrade Successful",
                        f"Successfully upgraded release {release_name}"
                    )
                    self.load_data()  # Refresh the list
                else:
                    QMessageBox.critical(
                        self,
                        "Upgrade Failed",
                        f"Failed to upgrade release:\n{result.stderr}"
                    )
                    
            except Exception as e:
                progress.close()
                
                # Clean up values file if it exists
                if 'values_file' in locals() and values_file and os.path.exists(values_file):
                    os.unlink(values_file)
                    
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error upgrading release:\n{str(e)}"
                )

    def _handle_action(self, action, row):
        """Handle specific actions for Helm releases"""
        if row >= len(self.resources):
            return
            
        resource = self.resources[row]
        release_name = resource["name"]
        namespace = resource.get("namespace", "default")
        
        if action == "Upgrade":
            self.upgrade_release(release_name, namespace)
        elif action == "Delete":
            self.delete_release(release_name, namespace)

    def set_focus_release(self, release_name, namespace):
        """Set a release to focus on with improved reliability"""
        self.focus_release = release_name
        self.focus_namespace = namespace
        
        # Set a flag to force a complete refresh
        self.force_refresh_for_focus = True
        
        # Load data immediately if the page is visible
        if self.isVisible():
            self.force_load_data()

    def focus_on_release(self, release_name, namespace):
        """Focus on a specific release in the table with improved reliability"""
        # Find the row containing the release
        target_row = -1
        for row, resource in enumerate(self.resources):
            if (resource.get("name") == release_name and 
                resource.get("namespace", "default") == namespace):
                target_row = row
                break
        
        if target_row >= 0:
            # Found the release, select it
            # Make sure it's visible (not filtered out)
            self.table.setRowHidden(target_row, False)
            
            # Select the row
            self.table.selectRow(target_row)
            
            # Scroll to the row
            self.table.scrollTo(self.table.model().index(target_row, 0))
            
            # Flash the row to highlight it
            self.flash_row(target_row)
            
            return True
        else:
            # Not found in current view, try direct fetch one more time
            # Try to fetch it directly one more time with increased timeout
            if not hasattr(self, 'focus_retry_attempted') or not self.focus_retry_attempted:
                self.focus_retry_attempted = True
                
                # Schedule a delayed retry with increased timeout
                QTimer.singleShot(2000, lambda: self._delayed_focus_retry(release_name, namespace))
            
            return False
        
    def _delayed_focus_retry(self, release_name, namespace):
        """Retry focusing after a delay to allow for kubernetes to catch up"""
        # Try direct fetch first
        if self._fetch_release_directly(release_name, namespace):
            # Now try focusing again
            self.focus_on_release(release_name, namespace)
        
        # Reset retry flag
        self.focus_retry_attempted = False

    def flash_row(self, row):
        """Flash a row to highlight it temporarily"""
        # Create a timer to toggle background color
        highlight_count = 0
        
        def toggle_highlight():
            nonlocal highlight_count
            
            # Get all cells in the row
            cells = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    cells.append(item)
            
            # Toggle background color based on count
            if highlight_count % 2 == 0:
                # Highlight
                for item in cells:
                    item.setBackground(QColor(AppColors.ACCENT_BLUE).darker(200))
            else:
                # Restore
                for item in cells:
                    item.setBackground(QColor(0, 0, 0, 0))  # Transparent background
            
            # Increment count
            highlight_count += 1
            
            # Stop after 6 toggles (3 flashes)
            if highlight_count >= 6:
                highlight_timer.stop()
        
        # Create and start timer
        highlight_timer = QTimer(self)
        highlight_timer.timeout.connect(toggle_highlight)
        highlight_timer.start(300)  # Toggle every 300ms

    def delete_release(self, release_name, namespace):
        """Delete a Helm release with confirmation dialog"""
        # Find Helm executable
        helm_path = find_helm_executable()
        
        if not helm_path:
            QMessageBox.warning(
                self,
                "Helm Not Found",
                "Helm CLI not found. Please install Helm to uninstall releases."
            )
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
            
        # Start the deletion process
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            
            cmd = [helm_path, "uninstall", release_name, "-n", namespace]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            QApplication.restoreOverrideCursor()
            
            if result.returncode == 0:
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
                    f"Failed to uninstall release:\n{result.stderr}"
                )
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Error",
                f"Error uninstalling release:\n{str(e)}"
            )
    
    def handle_row_click(self, row, column):
        """Handle row selection and open detail view"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
            # Find the ClusterView parent to show details
            parent = self.parent()
            while parent and not hasattr(parent, 'show_detail_for_table_item'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'show_detail_for_table_item'):
                parent.show_detail_for_table_item(row, column, self, "Releases")
    
    def resizeEvent(self, event):
        """Handle resizing to ensure empty overlay is properly positioned"""
        super().resizeEvent(event)
        
        # If empty overlay is visible, update its position
        if hasattr(self, 'empty_overlay') and self.empty_overlay.isVisible():
            if hasattr(self, 'table'):
                header_height = self.table.horizontalHeader().height()
                table_visible_height = self.table.height() - header_height
                
                # Set the geometry relative to the table
                self.empty_overlay.setGeometry(
                    0,  # X position relative to table
                    header_height,  # Y position just below header
                    self.table.width(),  # Full table width
                    table_visible_height  # Remaining table height
                )
                
    def force_load_data(self):
        """Force reload data with special handling for focusing on a specific release"""
        # Reset loading state
        self.is_loading = False
        
        # Load data from kubernetes
        self.load_data()