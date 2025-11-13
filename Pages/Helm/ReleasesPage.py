"""
Optimized implementation of the Releases page that loads Helm releases data dynamically
with proper threading for operations to prevent UI freezing and automatic refresh.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout, QVBoxLayout,
    QMessageBox, QProgressBar, QApplication, QDialog, QFormLayout,
    QComboBox, QTextEdit, QDialogButtonBox, QProgressDialog, QMenu, QCheckBox,QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QColor, QIcon

import subprocess
import json
import datetime
import os
import platform
import shutil
import tempfile
import time
import logging
import sys

# Windows subprocess configuration to prevent terminal popup
if sys.platform == 'win32':
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0

from Base_Components.base_resource_page import BaseResourcePage
from Base_Components.base_components import SortableTableWidgetItem
from UI.Styles import AppColors, AppStyles, AppConstants
from UI.Icons import resource_path


class HelmOperationThread(QThread):
    """Base thread class for Helm operations"""
    
    progress_update = pyqtSignal(str)  # Progress message
    progress_percentage = pyqtSignal(int)  # Progress percentage (0-100)
    operation_complete = pyqtSignal(bool, str)  # Success, message
    
    def __init__(self, operation_type, *args, **kwargs):
        super().__init__()
        self.operation_type = operation_type
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False
        
    def cancel(self):
        """Cancel the operation"""
        self._is_cancelled = True
        
    def run(self):
        """Execute the operation in a separate thread"""
        try:
            if self.operation_type == "delete":
                self._delete_release()
            elif self.operation_type == "upgrade":
                self._upgrade_release()
            elif self.operation_type == "batch_delete":
                self._batch_delete_releases()
        except Exception as e:
            logging.error(f"Error in helm operation thread: {e}")
            self.operation_complete.emit(False, f"Operation error: {str(e)}")
            
    def _delete_release(self):
        """Delete a single release with improved error handling and monitoring"""
        release_name, namespace = self.args
        
        self.progress_update.emit(f"Locating Helm executable...")
        self.progress_percentage.emit(10)
        
        helm_path = find_helm_executable()
        if not helm_path:
            self.operation_complete.emit(False, "Helm CLI not found. Please install Helm to uninstall releases.")
            return
            
        if self._is_cancelled:
            return
            
        self.progress_update.emit(f"Uninstalling release {release_name}...")
        self.progress_percentage.emit(30)
        
        try:
            cmd = [helm_path, "uninstall", release_name, "-n", namespace]
            logging.info(f"Executing delete command: {' '.join(cmd)}")
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0
            )
            
            self.progress_percentage.emit(50)
            
            # Monitor process with timeout
            check_interval = 1.0  # Check every second
            max_wait_time = 120  # 2 minutes maximum for deletion
            elapsed_time = 0
            
            while process.poll() is None and elapsed_time < max_wait_time:
                if self._is_cancelled:
                    logging.info(f"Delete operation cancelled by user for {release_name}")
                    try:
                        process.terminate()
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    return
                
                # Update progress
                if elapsed_time > 30:
                    self.progress_percentage.emit(70)
                elif elapsed_time > 60:
                    self.progress_percentage.emit(80)
                elif elapsed_time > 90:
                    self.progress_percentage.emit(90)
                
                self.msleep(int(check_interval * 1000))
                elapsed_time += check_interval
            
            # Handle timeout
            if elapsed_time >= max_wait_time and process.poll() is None:
                logging.error(f"Delete operation timed out for {release_name}")
                try:
                    process.terminate()
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                
                self.operation_complete.emit(False, f"Delete operation timed out for release {release_name}")
                return
            
            stdout, stderr = process.communicate()
            
            self.progress_percentage.emit(100)
            
            if process.returncode == 0:
                logging.info(f"Successfully deleted release {release_name}")
                self.operation_complete.emit(True, f"Successfully uninstalled release {release_name}")
            else:
                error_msg = stderr.strip() if stderr.strip() else stdout.strip()
                logging.error(f"Failed to delete release {release_name}: {error_msg}")
                
                # Handle specific error cases
                if "not found" in error_msg.lower():
                    # Release doesn't exist, consider it successful
                    self.operation_complete.emit(True, f"Release {release_name} was not found (may have been already deleted)")
                else:
                    self.operation_complete.emit(False, f"Failed to uninstall release: {error_msg}")
                
        except Exception as e:
            logging.error(f"Exception during delete operation for {release_name}: {str(e)}")
            self.operation_complete.emit(False, f"Error uninstalling release: {str(e)}")
            
    def _upgrade_release(self):
        """Upgrade a release"""
        release_name, namespace, upgrade_options = self.args
        
        self.progress_update.emit("Locating Helm executable...")
        self.progress_percentage.emit(5)
        
        helm_path = find_helm_executable()
        if not helm_path:
            self.operation_complete.emit(False, "Helm CLI not found. Please install Helm to upgrade releases.")
            return
            
        if self._is_cancelled:
            return
            
        try:
            self.progress_update.emit("Building upgrade command...")
            self.progress_percentage.emit(15)
            
            # Build the upgrade command
            cmd = [helm_path, "upgrade", release_name]
            
            # Add chart reference
            chart = upgrade_options.get("chart")
            if not chart:
                # Get current chart from release
                self.progress_update.emit("Getting current release information...")
                self.progress_percentage.emit(25)
                
                info_cmd = [helm_path, "list", "--filter", f"^{release_name}$", "-n", namespace, "-o", "json"]
                result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=15,
                                       creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        releases = json.loads(result.stdout)
                        if releases and len(releases) > 0:
                            release_info = releases[0]
                            chart_full = release_info.get("chart", "")
                            
                            if '/' in chart_full:
                                repo, chart_with_version = chart_full.split('/', 1)
                                if '-' in chart_with_version:
                                    version_parts = chart_with_version.split('-')
                                    if len(version_parts) > 1 and version_parts[-1][0].isdigit():
                                        chart = f"{repo}/{'-'.join(version_parts[:-1])}"
                                    else:
                                        chart = chart_full
                                else:
                                    chart = chart_full
                            else:
                                chart = chart_full.split('-')[0]
                                chart = f"bitnami/{chart}"  # Default to bitnami
                    except json.JSONDecodeError:
                        pass
            
            if not chart:
                self.operation_complete.emit(False, "Could not determine chart name. Please specify the chart explicitly.")
                return
                
            cmd.append(chart)
            cmd.extend(["-n", namespace])
            
            # Add version if specified
            if upgrade_options.get("version"):
                cmd.extend(["--version", upgrade_options.get("version")])
            
            # Add values file if provided
            values_file = None
            if upgrade_options.get("values"):
                self.progress_update.emit("Creating values file...")
                self.progress_percentage.emit(35)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w") as temp:
                    temp.write(upgrade_options.get("values"))
                    values_file = temp.name
                cmd.extend(["-f", values_file])
            
            # Add --atomic flag for atomic upgrades
            if upgrade_options.get("atomic", True):
                cmd.append("--atomic")
            
            if self._is_cancelled:
                if values_file and os.path.exists(values_file):
                    os.unlink(values_file)
                return
                
            self.progress_update.emit(f"Executing upgrade for {release_name}...")
            self.progress_percentage.emit(60)
            
            logging.info(f"Executing upgrade command: {' '.join(cmd)}")
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0
            )
            
            # Monitor progress
            progress_steps = [70, 80, 90, 95]
            step_index = 0
            
            while process.poll() is None:
                if self._is_cancelled:
                    process.terminate()
                    process.wait()
                    if values_file and os.path.exists(values_file):
                        os.unlink(values_file)
                    return
                    
                if step_index < len(progress_steps):
                    self.progress_percentage.emit(progress_steps[step_index])
                    step_index += 1
                    
                self.msleep(500)
            
            stdout, stderr = process.communicate()
            
            # Clean up values file
            if values_file and os.path.exists(values_file):
                os.unlink(values_file)
            
            self.progress_percentage.emit(100)
            
            if process.returncode == 0:
                self.operation_complete.emit(True, f"Successfully upgraded release {release_name}")
            else:
                self.operation_complete.emit(False, f"Failed to upgrade release: {stderr}")
                
        except Exception as e:
            # Clean up values file if it exists
            if 'values_file' in locals() and values_file and os.path.exists(values_file):
                os.unlink(values_file)
            self.operation_complete.emit(False, f"Error upgrading release: {str(e)}")
            
    def _batch_delete_releases(self):
        """Delete multiple releases"""
        releases_to_delete = self.args[0]
        
        self.progress_update.emit("Locating Helm executable...")
        self.progress_percentage.emit(5)
        
        helm_path = find_helm_executable()
        if not helm_path:
            self.operation_complete.emit(False, "Helm CLI not found. Please install Helm to uninstall releases.")
            return
            
        total_releases = len(releases_to_delete)
        successful_deletions = []
        failed_deletions = []
        
        for i, (release_name, namespace) in enumerate(releases_to_delete):
            if self._is_cancelled:
                break
                
            self.progress_update.emit(f"Uninstalling {release_name} ({i+1}/{total_releases})...")
            progress = int(10 + (80 * (i+1) / total_releases))
            self.progress_percentage.emit(progress)
            
            try:
                cmd = [helm_path, "uninstall", release_name, "-n", namespace]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                       creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
                
                if result.returncode == 0:
                    successful_deletions.append((release_name, namespace))
                else:
                    failed_deletions.append((release_name, namespace, result.stderr))
                    
            except Exception as e:
                failed_deletions.append((release_name, namespace, str(e)))
        
        self.progress_percentage.emit(100)
        
        # Generate result message
        success_count = len(successful_deletions)
        error_count = len(failed_deletions)
        
        if error_count == 0:
            self.operation_complete.emit(True, f"Successfully deleted all {success_count} releases.")
        else:
            message = f"Deleted {success_count} of {success_count + error_count} releases."
            if error_count > 0:
                message += f"\n\nFailed to delete {error_count} releases:"
                for name, namespace, error in failed_deletions[:5]:
                    ns_text = f" in namespace {namespace}" if namespace else ""
                    message += f"\n- {name}{ns_text}: {error}"
                if error_count > 5:
                    message += f"\n... and {error_count - 5} more."
            
            # Consider it successful if at least some were deleted
            self.operation_complete.emit(success_count > 0, message)


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
                creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0,
                check=True,
                timeout=30
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
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=15,
                                   creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            
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
            result = subprocess.run(values_cmd, capture_output=True, text=True, timeout=15,
                                   creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            
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
            logging.warning(f"Error loading current values: {e}")
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
    Displays Helm releases with dynamic data loading and threaded operations to prevent UI freezing.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "helmreleases"  # Custom resource type for Helm releases
        
        # Flag to indicate if we should focus on a specific release
        self.focus_release = None
        self.focus_namespace = None
        self.force_refresh_for_focus = False
        self.focus_retry_attempted = False
        
        # Track active operations
        self.active_operation = None
        
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
    
    # def configure_columns(self):
    #     """Configure column widths and behaviors"""
    #     self.table.setColumnWidth(1, 150)  # Name
        
    #     fixed_widths = {
    #         2: 120,  # Namespace
    #         4: 80,   # Revision
    #         7: 100,  # Status
    #         8: 120,  # Updated
    #         9: 40    # Actions
    #     }
        
    #     for col, width in fixed_widths.items():
    #         self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
    #         self.table.setColumnWidth(col, width)
        
    #     # Set flexible columns
    #     self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Chart
    #     self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Version
    #     self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # App Version

    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
        
        header = self.table.horizontalHeader()
        
        # Column specifications with optimized default widths
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 140, "interactive"), # Name
            (2, 90, "interactive"),  # Namespace
            (3, 80, "interactive"),  # Chart
            (4, 60, "interactive"),  # Revision
            (5, 60, "interactive"),  # Version
            (6, 60, "interactive"),  # App Version
            (7, 60, "interactive"),  # Status
            (8, 80, "stretch"),      # Update - stretch to fill remaining space
            (9, 40, "fixed")        # Actions
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


    def load_data(self, load_more=False):
        """Load resource data with improved detection of all releases including partial ones"""
        if hasattr(self, 'is_loading') and self.is_loading:
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

    def on_resources_loaded(self, resources, resource_type):
        """Handle loaded resources with improved focus handling"""
        # Clear loading state
        self.is_loading = False
        
        # Store the resources
        self.resources = resources
        self.selected_items.clear()
        
        # Clear table and prepare for new data
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        # Hide any existing empty overlay
        if hasattr(self, 'empty_overlay') and self.empty_overlay:
            self.empty_overlay.hide()
        
        # Populate table with resources
        if resources:
            for i, resource in enumerate(resources):
                self.table.setRowCount(i + 1)
                self.populate_resource_row(i, resource)
            
            self.table.setSortingEnabled(True)
            self.table.show()
            self.table.setEnabled(True)
            
            # Update count
            self.items_count.setText(f"{len(resources)} items")
        else:
            # Show empty state
            self.table.setEnabled(True)
            self.items_count.setText("0 items")
        
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
                    creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0, 
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
                logging.warning(f"Error fetching release directly: {e}")
        
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
            
        # Create action button
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(action_button)
        action_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    def _create_action_button(self, row, resource_name, resource_namespace):
        """Create an action button with enhanced upgrade and delete options"""
        button = QToolButton()
        
        icon = resource_path("Icons/Moreaction_Button.svg")
        button.setIcon(QIcon(icon))
        button.setIconSize(QSize(AppConstants.SIZES["ICON_SIZE"], AppConstants.SIZES["ICON_SIZE"]))

        # Remove text and change to icon-only style
        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        button.setFixedWidth(30)
        button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
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
            {"text": "Upgrade", "icon": "Icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "Icons/delete.png", "dangerous": True}
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
        """Upgrade a Helm release with user input for parameters using threading"""
        # Check if there's already an active operation
        if self.active_operation and self.active_operation.isRunning():
            QMessageBox.warning(self, "Operation in Progress", "Another operation is currently in progress. Please wait for it to complete.")
            return
        
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
            
            # Create and show progress dialog
            progress = QProgressDialog("Preparing upgrade...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Upgrading Release")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setAutoClose(False)
            progress.setValue(0)
            progress.show()
            QApplication.processEvents()
            
            # Create and start the operation thread
            self.active_operation = HelmOperationThread("upgrade", release_name, namespace, options)
            
            def on_progress_update(message):
                if not progress.wasCanceled():
                    progress.setLabelText(message)
                    QApplication.processEvents()
            
            def on_progress_percentage(percentage):
                if not progress.wasCanceled():
                    progress.setValue(percentage)
                    QApplication.processEvents()
            
            def on_operation_complete(success, message):
                progress.close()
                self.active_operation = None
                
                if success:
                    QMessageBox.information(self, "Upgrade Successful", message)
                else:
                    QMessageBox.critical(self, "Upgrade Failed", message)
                
                # Automatically refresh the data
                QTimer.singleShot(1000, self.load_data)
            
            def on_progress_cancelled():
                if self.active_operation:
                    self.active_operation.cancel()
                progress.close()
                self.active_operation = None
            
            # Connect signals
            self.active_operation.progress_update.connect(on_progress_update)
            self.active_operation.progress_percentage.connect(on_progress_percentage)
            self.active_operation.operation_complete.connect(on_operation_complete)
            progress.canceled.connect(on_progress_cancelled)
            
            # Start the thread
            self.active_operation.start()
    
    def delete_release(self, resource_name, resource_namespace):
        """Delete a Helm release with confirmation dialog using threading"""
        # Check if there's already an active operation
        if self.active_operation and self.active_operation.isRunning():
            QMessageBox.warning(self, "Operation in Progress", "Another operation is currently in progress. Please wait for it to complete.")
            return
        
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
            f"Are you sure you want to uninstall Helm release {resource_name} in namespace {resource_namespace}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Create and show progress dialog with improved settings
        progress = QProgressDialog("Preparing to uninstall...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Uninstalling Release")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        # Track completion state
        operation_completed = {"completed": False}
        user_cancelled = {"cancelled": False}
        
        # Create and start the operation thread
        self.active_operation = HelmOperationThread("delete", resource_name, resource_namespace)
        
        def on_progress_update(message):
            try:
                if not operation_completed["completed"] and not user_cancelled["cancelled"]:
                    progress.setLabelText(message)
                    QApplication.processEvents()
                    logging.info(f"Helm delete progress: {message}")
            except RuntimeError:
                pass
        
        def on_progress_percentage(percentage):
            try:
                if not operation_completed["completed"] and not user_cancelled["cancelled"]:
                    progress.setValue(percentage)
                    QApplication.processEvents()
            except RuntimeError:
                pass
        
        def on_operation_complete(success, message):
            operation_completed["completed"] = True
            
            logging.info(f"Helm delete completed: success={success}, message={message}")
            
            # Cleanup thread properly
            if self.active_operation:
                if self.active_operation.isRunning():
                    self.active_operation.wait(1000)  # Wait for thread to finish
                self.active_operation = None
            
            try:
                if progress and not progress.wasCanceled():
                    progress.setValue(100)
                    progress.setLabelText("Deletion completed!")
                    QApplication.processEvents()
            except RuntimeError:
                pass
            
            # Close progress dialog after showing completion
            QTimer.singleShot(1000, lambda: progress.close() if progress else None)
            
            # Show result message
            QTimer.singleShot(1100, lambda: self._show_delete_result(success, message))
            
            # Automatically refresh the data
            QTimer.singleShot(2000, self.load_data)
        
        def on_progress_cancelled():
            if not operation_completed["completed"]:
                user_cancelled["cancelled"] = True
                logging.info("User cancelled Helm delete operation")
                if self.active_operation:
                    self.active_operation.cancel()
                self.active_operation = None
        
        # Connect signals
        self.active_operation.progress_update.connect(on_progress_update)
        self.active_operation.progress_percentage.connect(on_progress_percentage)
        self.active_operation.operation_complete.connect(on_operation_complete)
        progress.canceled.connect(on_progress_cancelled)
        
        # Start the thread
        self.active_operation.start()
        logging.info(f"Started Helm delete thread for {resource_name}")
    
    def _show_delete_result(self, success, message):
        """Show the result of delete operation"""
        try:
            if success:
                QMessageBox.information(self, "Deletion Successful", message)
            else:
                QMessageBox.critical(self, "Deletion Failed", message)
        except Exception as e:
            logging.error(f"Error showing delete result: {e}")

    def delete_selected_resources(self):
        """Delete multiple selected releases using threading"""
        # Check if there's already an active operation
        if self.active_operation and self.active_operation.isRunning():
            QMessageBox.warning(self, "Operation in Progress", "Another operation is currently in progress. Please wait for it to complete.")
            return
            
        if not self.selected_items:
            QMessageBox.information(self, "No Selection", "No resources selected for deletion.")
            return
            
        count = len(self.selected_items)
        result = QMessageBox.warning(self, "Confirm Deletion",
            f"Are you sure you want to delete {count} selected {self.resource_type}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes: 
            return
        
        resources_list = list(self.selected_items)
        
        # Create and show progress dialog
        progress = QProgressDialog(f"Deleting {count} {self.resource_type}...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Deleting Resources")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        # Create and start the operation thread
        self.active_operation = HelmOperationThread("batch_delete", resources_list)
        
        def on_progress_update(message):
            if not progress.wasCanceled():
                progress.setLabelText(message)
                QApplication.processEvents()
        
        def on_progress_percentage(percentage):
            if not progress.wasCanceled():
                progress.setValue(percentage)
                QApplication.processEvents()
        
        def on_operation_complete(success, message):
            progress.close()
            self.active_operation = None
            
            QMessageBox.information(self, "Deletion Results", message)
            
            # Clear selected items and refresh
            self.selected_items.clear()
            QTimer.singleShot(1000, self.load_data)
        
        def on_progress_cancelled():
            if self.active_operation:
                self.active_operation.cancel()
            progress.close()
            self.active_operation = None
        
        # Connect signals
        self.active_operation.progress_update.connect(on_progress_update)
        self.active_operation.progress_percentage.connect(on_progress_percentage)
        self.active_operation.operation_complete.connect(on_operation_complete)
        progress.canceled.connect(on_progress_cancelled)
        
        # Start the thread
        self.active_operation.start()

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
    
    def handle_row_click(self, row, column):
        """Handle row selection and open detail view with enhanced data"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
            # Get the resource for this row
            if row < len(self.resources):
                resource = self.resources[row]
                release_name = resource.get("name", "")
                namespace = resource.get("namespace", "default")
                
                # Pre-load release resources for the Resources tab
                release_resources = self.get_release_resources(release_name, namespace)
                
                # Store the resources for the detail view
                if hasattr(self, 'detail_resources_cache'):
                    self.detail_resources_cache[f"{release_name}_{namespace}"] = release_resources
                else:
                    self.detail_resources_cache = {f"{release_name}_{namespace}": release_resources}
            
            # Find the ClusterView parent to show details
            parent = self.parent()
            while parent and not hasattr(parent, 'show_detail_for_table_item'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'show_detail_for_table_item'):
                parent.show_detail_for_table_item(row, column, self, "Releases")
    
    def get_raw_data_for_row(self, row: int) -> dict:
        """Get dynamic raw data for a specific table row from actual Helm release"""
        try:
            logging.info(f"Getting raw data for row {row}")
            if hasattr(self, 'resources') and self.resources and row < len(self.resources):
                resource = self.resources[row]
                release_name = resource.get("name", "")
                namespace = resource.get("namespace", "default")
                
                logging.info(f"Processing release {release_name} in namespace {namespace}")
                
                # Get detailed release information from Helm
                detailed_data = self._get_detailed_release_data(release_name, namespace)
                if detailed_data:
                    logging.info(f"Returning detailed data for {release_name}")
                    return detailed_data
                    
                # Fallback to basic resource data if detailed fetch fails
                logging.warning(f"Falling back to basic resource data for {release_name}")
                
                # Enhance basic resource data to be more compatible with detail view
                enhanced_resource = {
                    "kind": "HelmRelease",
                    "apiVersion": "helm.sh/v3",
                    "metadata": {
                        "name": release_name,
                        "namespace": namespace,
                        "labels": {
                            "app.kubernetes.io/managed-by": "Helm",
                            "app.kubernetes.io/instance": release_name
                        }
                    },
                    "spec": {
                        "chart": resource.get("raw_data", {}).get("chart", ""),
                        "releaseName": release_name,
                        "targetNamespace": namespace
                    },
                    "status": {
                        "phase": resource.get("raw_data", {}).get("status", ""),
                        "revision": resource.get("raw_data", {}).get("revision", ""),
                        "lastDeployed": resource.get("raw_data", {}).get("updated", "")
                    },
                    # Include original resource data
                    "original_resource": resource
                }
                
                return enhanced_resource
            
            logging.warning(f"No resource found for row {row}")
            return {}
        except Exception as e:
            logging.error(f"Error getting raw data for row {row}: {e}")
            return {}
    
    def _get_detailed_release_data(self, release_name: str, namespace: str) -> dict:
        """Fetch detailed release data from Helm CLI"""
        try:
            logging.info(f"Fetching detailed release data for {release_name} in namespace {namespace}")
            helm_path = find_helm_executable()
            if not helm_path:
                logging.warning("Helm executable not found")
                return {}
                
            # Get release status information first (this is more reliable)
            status_cmd = [helm_path, "list", "--filter", f"^{release_name}$", "-n", namespace]
            logging.info(f"Running status command: {' '.join(status_cmd)}")
            status_result = subprocess.run(status_cmd, capture_output=True, text=True, timeout=10,
                                          creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            
            status_info = {}
            if status_result.returncode == 0 and status_result.stdout.strip():
                # Parse table output from helm list
                lines = status_result.stdout.strip().split('\n')
                logging.info(f"Helm list output for {release_name}:")
                for i, line in enumerate(lines):
                    logging.info(f"  Line {i}: '{line}'")
                    
                if len(lines) > 1:  # Header + data
                    # Use tab-based splitting for more reliable parsing, fallback to spaces
                    data_line = lines[1]
                    logging.info(f"Parsing data line: '{data_line}'")
                    
                    # Try tab-separated first
                    if '\t' in data_line:
                        fields = data_line.split('\t')
                    else:
                        # For space-separated, we need to handle the updated field carefully
                        # Format: NAME NAMESPACE REVISION UPDATED STATUS CHART APP_VERSION
                        parts = data_line.split()
                        if len(parts) >= 5:
                            # Reconstruct by finding where STATUS starts (usually "deployed", "failed", etc.)
                            status_keywords = ["deployed", "failed", "pending-install", "pending-upgrade", "pending-rollback", "superseded", "uninstalling", "uninstalled"]
                            status_index = -1
                            
                            for i, part in enumerate(parts):
                                if part.lower() in status_keywords:
                                    status_index = i
                                    break
                            
                            if status_index >= 4:  # Valid position for status
                                name = parts[0]
                                namespace = parts[1]
                                revision = parts[2]
                                # Updated field might contain spaces - join from index 3 to status_index
                                updated = ' '.join(parts[3:status_index])
                                status = parts[status_index]
                                chart = parts[status_index + 1] if len(parts) > status_index + 1 else ""
                                app_version = parts[status_index + 2] if len(parts) > status_index + 2 else ""
                                
                                fields = [name, namespace, revision, updated, status, chart, app_version]
                            else:
                                # Fallback to simple split
                                fields = parts
                        else:
                            fields = parts
                    
                    if len(fields) >= 5:
                        status_info = {
                            "name": fields[0].strip(),
                            "namespace": fields[1].strip(),
                            "revision": fields[2].strip(),
                            "updated": fields[3].strip(),
                            "status": fields[4].strip(),
                            "chart": fields[5].strip() if len(fields) > 5 else "",
                            "app_version": fields[6].strip() if len(fields) > 6 else ""
                        }
                        logging.info(f"Successfully parsed status data for {release_name}: {status_info}")
                    else:
                        logging.warning(f"Could not parse status data for {release_name}: insufficient fields in '{data_line}'")
                else:
                    logging.warning(f"No status data found for {release_name}")
            else:
                logging.warning(f"Failed to get status for {release_name}: {status_result.stderr}")
            
            # Get detailed release information (values and manifest)
            detailed_release = {}
            
            # Get values
            values_cmd = [helm_path, "get", "values", release_name, "-n", namespace]
            logging.info(f"Running values command: {' '.join(values_cmd)}")
            values_result = subprocess.run(values_cmd, capture_output=True, text=True, timeout=10,
                                          creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            
            if values_result.returncode == 0:
                try:
                    import yaml
                    values_output = values_result.stdout.strip()
                    
                    # Comprehensive null/empty value detection
                    null_patterns = ["null", "nil", "{}", "", "null\n", "\nnull", "null\r\n", "\r\nnull"]
                    is_null_value = (
                        not values_output or 
                        values_output.strip().lower() in null_patterns or
                        values_output.strip().lower().startswith('null\n') or
                        values_output.strip().lower().endswith('\nnull') or
                        values_output.strip().lower() == 'null\r\n' or
                        values_output.strip() == 'null'
                    )
                    
                    if is_null_value:
                        detailed_release["config"] = {}
                        logging.info(f"No custom values set for {release_name} (null/empty output: '{values_output.strip()}')")
                    else:
                        try:
                            values_data = yaml.safe_load(values_output)
                            detailed_release["config"] = values_data or {}
                            logging.info(f"Successfully loaded values for {release_name}")
                        except yaml.YAMLError as e:
                            logging.warning(f"Failed to parse values YAML for {release_name}: {e}")
                            detailed_release["config"] = {"raw_output": values_output}
                        
                except Exception as e:
                    logging.info(f"Values parsing handled for {release_name}: {e} - setting empty config")
                    detailed_release["config"] = {}
            else:
                detailed_release["config"] = {}
                
            # Get manifest
            manifest_cmd = [helm_path, "get", "manifest", release_name, "-n", namespace]
            logging.info(f"Running manifest command: {' '.join(manifest_cmd)}")
            manifest_result = subprocess.run(manifest_cmd, capture_output=True, text=True, timeout=10,
                                            creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            
            if manifest_result.returncode == 0:
                detailed_release["manifest"] = manifest_result.stdout
                logging.info(f"Successfully loaded manifest for {release_name}")
            else:
                detailed_release["manifest"] = ""
                
            # Get notes if available
            notes_cmd = [helm_path, "get", "notes", release_name, "-n", namespace]
            notes_result = subprocess.run(notes_cmd, capture_output=True, text=True, timeout=10,
                                         creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            
            if notes_result.returncode == 0:
                detailed_release["info"] = {"notes": notes_result.stdout}
            else:
                detailed_release["info"] = {"notes": ""}
                
            if status_info:  # Only proceed if we have status info
                logging.info(f"Successfully loaded detailed release data for {release_name}")
                
                # Structure the data dynamically
                structured_data = {
                    "kind": "HelmRelease",
                    "apiVersion": "helm.sh/v3",
                    "metadata": {
                        "name": release_name,
                        "namespace": namespace,
                        "creationTimestamp": status_info.get("updated", ""),
                        "labels": {
                            "app.kubernetes.io/managed-by": "Helm",
                            "app.kubernetes.io/instance": release_name,
                            "helm.sh/chart": status_info.get("chart", "")
                        },
                        "annotations": {
                            "helm.sh/revision": str(status_info.get("revision", "")),
                            "helm.sh/status": status_info.get("status", "")
                        }
                    },
                    "spec": {
                        "chart": status_info.get("chart", ""),
                        "version": status_info.get("chart", "").split("-")[-1] if "-" in status_info.get("chart", "") else "",
                        "appVersion": status_info.get("app_version", ""),
                        "values": detailed_release.get("config", {}),
                        "releaseName": release_name,
                        "targetNamespace": namespace
                    },
                    "status": {
                        "phase": status_info.get("status", ""),
                        "revision": status_info.get("revision", ""),
                        "lastDeployed": status_info.get("updated", ""),
                        "description": f"Release {release_name} in namespace {namespace}",
                        "notes": detailed_release.get("info", {}).get("notes", "")
                    },
                    # Include manifest for YAML view
                    "manifest": detailed_release.get("manifest", ""),
                    # Include values for debugging
                    "values": detailed_release.get("config", {}),
                    # Include hooks if any
                    "hooks": detailed_release.get("hooks", []),
                    # Include release info
                    "info": detailed_release.get("info", {}),
                    # Raw Helm data for reference
                    "helm_data": {
                        "release": detailed_release,
                        "status": status_info
                    }
                }
                
                logging.info(f"Successfully structured release data for {release_name}")
                logging.info(f"Structured data keys: {list(structured_data.keys())}")
                logging.info(f"Values data: {len(structured_data.get('values', {}))} items")
                logging.info(f"Manifest length: {len(structured_data.get('manifest', ''))}")
                return structured_data
            else:
                logging.warning(f"No status info found for {release_name}")
                return {}
                
        except Exception as e:
            logging.warning(f"Error fetching detailed release data for {release_name}: {e}")
            
        return {}
    
    def get_release_resources(self, release_name: str, namespace: str) -> list:
        """Get all Kubernetes resources deployed by this Helm release"""
        try:
            helm_path = find_helm_executable()
            if not helm_path:
                return []
                
            # Get the manifest of deployed resources
            cmd = [helm_path, "get", "manifest", release_name, "-n", namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                                   creationflags=SUBPROCESS_FLAGS if sys.platform == 'win32' else 0)
            
            if result.returncode == 0 and result.stdout.strip():
                import yaml
                resources = []
                
                # Parse YAML documents from the manifest
                for doc in yaml.safe_load_all(result.stdout):
                    if doc and isinstance(doc, dict) and doc is not None:
                        try:
                            # Ensure metadata exists and is a dict
                            if 'metadata' not in doc or doc['metadata'] is None:
                                doc['metadata'] = {}
                            elif not isinstance(doc['metadata'], dict):
                                doc['metadata'] = {}
                                
                            # Ensure labels exists and is a dict
                            if 'labels' not in doc['metadata'] or doc['metadata']['labels'] is None:
                                doc['metadata']['labels'] = {}
                            elif not isinstance(doc['metadata']['labels'], dict):
                                doc['metadata']['labels'] = {}
                                
                            # Ensure annotations exists and is a dict
                            if 'annotations' not in doc['metadata'] or doc['metadata']['annotations'] is None:
                                doc['metadata']['annotations'] = {}
                            elif not isinstance(doc['metadata']['annotations'], dict):
                                doc['metadata']['annotations'] = {}
                                
                            # Add Helm-specific labels and annotations safely
                            doc['metadata']['labels']['app.kubernetes.io/managed-by'] = 'Helm'
                            doc['metadata']['labels']['app.kubernetes.io/instance'] = release_name
                            doc['metadata']['annotations']['meta.helm.sh/release-name'] = release_name
                            doc['metadata']['annotations']['meta.helm.sh/release-namespace'] = namespace
                            
                            resources.append(doc)
                        except (TypeError, AttributeError) as e:
                            logging.warning(f"Error processing resource document: {e}")
                            # Still add the document even if we can't add metadata
                            resources.append(doc)
                        
                return resources
                
        except Exception as e:
            logging.warning(f"Error fetching release resources for {release_name}: {e}")
            
        return []
    
    def get_release_resources_for_detail(self, row: int) -> list:
        """Get cached release resources for detail view"""
        try:
            if row < len(self.resources):
                resource = self.resources[row]
                release_name = resource.get("name", "")
                namespace = resource.get("namespace", "default")
                cache_key = f"{release_name}_{namespace}"
                
                if hasattr(self, 'detail_resources_cache') and cache_key in self.detail_resources_cache:
                    return self.detail_resources_cache[cache_key]
                else:
                    # Fetch if not cached
                    return self.get_release_resources(release_name, namespace)
            return []
        except Exception as e:
            logging.error(f"Error getting release resources for detail view: {e}")
            return []

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
        
        # Cancel any active operation that might interfere
        if self.active_operation and self.active_operation.isRunning():
            self.active_operation.cancel()
            self.active_operation.wait(1000)
        
        # Load data from helm
        self.load_data()
    
    def closeEvent(self, event):
        """Handle close event and cleanup active operations"""
        self._cleanup_active_operation()
        super().closeEvent(event)
    
    def _cleanup_active_operation(self):
        """Properly cleanup the active operation thread"""
        if self.active_operation and self.active_operation.isRunning():
            logging.info("Cleaning up active Helm operation thread...")
            self.active_operation.cancel()
            
            # Wait for thread to finish gracefully
            if not self.active_operation.wait(3000):  # Wait 3 seconds
                logging.warning("Thread did not finish gracefully, terminating...")
                self.active_operation.terminate()
                
                # Force wait after terminate
                if not self.active_operation.wait(2000):  # Wait 2 more seconds
                    logging.error("Thread failed to terminate, forcing cleanup...")
                    
            # Clear the reference
            self.active_operation = None
            logging.info("Active operation cleanup completed")