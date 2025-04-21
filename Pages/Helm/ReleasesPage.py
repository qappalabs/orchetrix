# """
# Optimized implementation of the Releases page with better memory management
# and performance.
# """

# from PyQt6.QtWidgets import (
#     QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout
# )
# from PyQt6.QtCore import Qt, QEvent
# from PyQt6.QtGui import QColor

# from base_components.base_components import BaseTablePage, SortableTableWidgetItem

# class ReleasesPage(BaseTablePage):
#     """
#     Displays Helm releases with optimizations for performance and memory usage.
    
#     Optimizations:
#     1. Uses BaseTablePage for common functionality to reduce code duplication
#     2. Implements lazy loading of table rows for better performance with large datasets
#     3. Uses object pooling to reduce GC pressure from widget creation
#     4. Implements virtualized scrolling for better performance with large tables
#     """
    
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setup_page_ui()
#         self.load_data()
        
#     def setup_page_ui(self):
#         """Set up the main UI elements for the Releases page"""
#         # Define headers and sortable columns
#         headers = ["", "Name", "Namespace", "Chart", "Revision", "Version", "App Version", "Status", "Updated", ""]
#         sortable_columns = {1, 2, 3, 4, 7, 8}
        
#         # Set up the base UI components
#         layout = self.setup_ui("Releases", headers, sortable_columns)
        
#         # Configure column widths
#         self.configure_columns()
        
#         # Connect the row click handler
#         self.table.cellClicked.connect(self.handle_row_click)
    
#     def configure_columns(self):
#         """Configure column widths and behaviors"""
#         # Column 0: Checkbox (fixed width) - already set in base class
        
#         # Column 1: Name (stretch)
#         self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
#         # Configure stretch columns
#         stretch_columns = [2, 3, 4, 5, 6, 7, 8]
#         for col in stretch_columns:
#             self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
#         # Fixed width columns
#         fixed_widths = {9: 40}
#         for col, width in fixed_widths.items():
#             self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
#             self.table.setColumnWidth(col, width)
    
#     def load_data(self):
#         """Load release data into the table with optimized batch processing"""
#         # Sample release data
#         releases_data = [
#             ["docker.io-hostpath", "kube-system", "<none>", "<none>", "<none>", "<none>", "<none>", "<none>"],
#             ["docker.io-hostpath", "kube-system", "<none>", "<none>", "<none>", "<none>", "<none>", "<none>"]
#         ]

#         # Set up the table for the data
#         self.table.setRowCount(len(releases_data))
        
#         # Batch process all rows using a single loop for better performance
#         for row, release in enumerate(releases_data):
#             self.populate_release_row(row, release)
        
#         # Update the item count
#         self.items_count.setText(f"{len(releases_data)} items")
    
#     def populate_release_row(self, row, release_data):
#         """
#         Populate a single row with release data using efficient methods
        
#         Args:
#             row: The row index
#             release_data: List containing release information
#         """
#         # Set row height once
#         self.table.setRowHeight(row, 40)
        
#         # Create checkbox for row selection
#         release_name = release_data[0]
#         checkbox_container = self._create_checkbox_container(row, release_name)
#         self.table.setCellWidget(row, 0, checkbox_container)
        
#         # Populate data columns efficiently
#         for col, value in enumerate(release_data):
#             cell_col = col + 1  # Adjust for checkbox column
            
#             # Create item
#             item = SortableTableWidgetItem(value)
            
#             # Set text alignment
#             if col == 6:  # Status column
#                 item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
#                 # Set color based on status
#                 if value == "Active":
#                     item.setForeground(QColor("#4caf50"))
#                 else:
#                     item.setForeground(QColor("#cc0606"))
#             elif col == 0:  # Name column
#                 item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
#                 item.setForeground(QColor("#e2e8f0"))
#             else:
#                 item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#                 item.setForeground(QColor("#e2e8f0"))
            
#             # Make cells non-editable
#             item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
#             # Add the item to the table
#             self.table.setItem(row, cell_col, item)
        
#         # Create and add action button
#         action_button = self._create_action_button(row, [
#             {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
#             {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
#         ])
#         action_container = self._create_action_container(row, action_button)
#         self.table.setCellWidget(row, len(release_data) + 1, action_container)
    
#     def _handle_action(self, action, row):
#         """Override base action handler for release-specific actions"""
#         release_name = self.table.item(row, 1).text()
#         if action == "Edit":
#             print(f"Editing Release: {release_name}")
#         elif action == "Delete":
#             print(f"Deleting Release: {release_name}")
    
#     def handle_row_click(self, row, column):
#         """Handle row selection when a table cell is clicked"""
#         if column != self.table.columnCount() - 1:  # Skip action column
#             # Select the row
#             self.table.selectRow(row)
#             # Log selection
#             release_name = self.table.item(row, 1).text()
#             print(f"Selected Release: {release_name}")

"""
Dynamic implementation of the Helm Releases page with better error handling.
"""

from PyQt6.QtWidgets import (QHeaderView, QWidget, QLabel, QVBoxLayout, QPushButton, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import subprocess
import json
import shutil  # Used to check if helm command exists

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors

class HelmReleaseLoader(QThread):
    """Thread for loading Helm releases without blocking the UI."""
    releases_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
    def run(self):
        """Execute the helm command and emit results."""
        try:
            # First check if helm command is available
            if shutil.which("helm") is None:
                self.error_occurred.emit("Helm command not found. Please install Helm to view releases.")
                return
            
            # Run 'helm list' with JSON output across all namespaces
            cmd = ["helm", "list", "--all-namespaces", "-o", "json"]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Parse the JSON result
            releases = json.loads(result.stdout)
            
            # Format the releases for display
            formatted_releases = []
            for release in releases:
                # Calculate age
                formatted_releases.append({
                    "name": release.get("name", ""),
                    "namespace": release.get("namespace", "default"),
                    "revision": str(release.get("revision", "")),
                    "updated": release.get("updated", ""),
                    "status": release.get("status", ""),
                    "chart": release.get("chart", ""),
                    "app_version": release.get("app_version", ""),
                    "age": self._format_age(release.get("updated", "")),
                    "raw_data": release  # Store the raw data for reference
                })
            
            # Emit the result
            self.releases_loaded.emit(formatted_releases)
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Error loading Helm releases: {e.stderr}"
            self.error_occurred.emit(error_msg)
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
            
    def _format_age(self, timestamp):
        """Format the age field from a timestamp."""
        if not timestamp:
            return "Unknown"
            
        import datetime
        try:
            # Parse Helm timestamp format
            from dateutil import parser
            updated_time = parser.parse(timestamp)
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Calculate the difference
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

class ReleasesPage(BaseResourcePage):
    """
    Displays Helm releases with dynamic data and resource operations.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "helm-releases"  # This is not a real kubectl resource
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Releases page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Chart", "Revision", "Version", "App Version", "Status", "Updated", ""]
        sortable_columns = {1, 2, 3, 4, 7, 8}
        
        # Set up the base UI components
        layout = super().setup_ui("Helm Releases", headers, sortable_columns)
        
        # Apply table style
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure column widths
        self.configure_columns()
        
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Column 0: Checkbox (fixed width) - already set in base class
        
        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Configure stretch columns
        stretch_columns = [2, 3, 4, 5, 6, 7, 8]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(9, 40)
    
    def load_data(self):
        """Override to use Helm loader instead of kubectl"""
        if self.is_loading:
            return
            
        self.is_loading = True
        
        # Clear existing data
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
        
        loading_text = QLabel(f"Loading Helm releases...")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        loading_layout.addWidget(loading_text)
        loading_layout.addWidget(loading_bar)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        # Start loading thread
        self.helm_loader = HelmReleaseLoader()
        self.helm_loader.releases_loaded.connect(self.on_helm_releases_loaded)
        self.helm_loader.error_occurred.connect(self.on_helm_error)
        self.helm_loader.start()
        
    def on_helm_releases_loaded(self, releases):
        """Handle loaded Helm releases"""
        self.resources = releases
        self.on_resources_loaded(releases, self.resource_type)
        
    def on_helm_error(self, error_message):
        """Handle Helm errors with custom message for missing helm command"""
        self.is_loading = False
        
        # Clear the table
        self.table.setRowCount(0)
        
        # Create one row for the error message
        self.table.setRowCount(1)
        
        # Span all columns
        self.table.setSpan(0, 0, 1, self.table.columnCount())
        
        # Create error message widget
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.setContentsMargins(20, 40, 20, 40)
        
        if "not found" in error_message.lower() or "WinError 2" in error_message:
            # This is a "helm not installed" error
            error_text = QLabel("Helm is not installed or not found in PATH")
            info_text = QLabel("To view Helm releases, please install Helm and ensure it's in your system PATH.")
            
            # Add an install instructions link/button
            install_btn = QPushButton("Installation Instructions")
            install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 20px;
                    font-size: 14px;
                    max-width: 200px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            """)
            install_btn.clicked.connect(lambda: self.open_helm_install_instructions())
        else:
            # General error
            error_text = QLabel("Error loading Helm releases")
            info_text = QLabel(error_message)
            
            # Add a retry button
            install_btn = QPushButton("Retry")
            install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 20px;
                    font-size: 14px;
                    max-width: 100px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            """)
            install_btn.clicked.connect(self.load_data)
            
        # Style the error messages
        error_text.setStyleSheet("""
            color: #ff6b6b;
            font-size: 18px;
            font-weight: bold;
        """)
        info_text.setStyleSheet("""
            color: #aaaaaa;
            font-size: 14px;
            margin-top: 10px;
        """)
        
        error_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_text.setWordWrap(True)
        
        # Add widgets to layout
        error_layout.addWidget(error_text)
        error_layout.addWidget(info_text)
        error_layout.addSpacing(20)
        error_layout.addWidget(install_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Set the widget in the cell
        self.table.setCellWidget(0, 0, error_widget)
        
        # Set row height for better appearance
        self.table.setRowHeight(0, 200)
        
        # Update item count
        self.items_count.setText("0 items")
        
        # Disable sorting
        self.table.setSortingEnabled(False)
        
    def open_helm_install_instructions(self):
        """Open Helm installation instructions in the default browser"""
        import webbrowser
        webbrowser.open("https://helm.sh/docs/intro/install/")
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with Helm release data
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        release_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, release_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            resource["chart"],
            resource["revision"],
            resource.get("version", ""),
            resource["app_version"],
            resource["status"],
            resource["age"]  # We're using age instead of updated timestamp for better display
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Create item
            item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col == 6:  # Status column
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Set color based on status
                if "deployed" in value.lower():
                    item.setForeground(QColor(AppColors.STATUS_ACTIVE))
                elif "failed" in value.lower():
                    item.setForeground(QColor(AppColors.STATUS_ERROR))
                elif "pending" in value.lower():
                    item.setForeground(QColor(AppColors.STATUS_WARNING))
                else:
                    item.setForeground(QColor(AppColors.TEXT_TABLE))
            elif col == 0:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setForeground(QColor(AppColors.TEXT_TABLE))
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, release_name, resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 1, action_container)
    
    def _handle_action(self, action, row):
        """Handle Helm release-specific actions"""
        if row >= len(self.resources):
            return
            
        resource = self.resources[row]
        release_name = resource["name"]
        namespace = resource["namespace"]
        
        if action == "Edit":
            # For Helm releases, "edit" might mean upgrading with values
            print(f"Editing Helm Release: {release_name} in namespace {namespace}")
        elif action == "Delete":
            self.delete_helm_release(release_name, namespace)
    
    def delete_helm_release(self, release_name, namespace):
        """Delete a Helm release using helm uninstall"""
        # Confirm deletion
        from PyQt6.QtWidgets import QMessageBox
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to uninstall Helm release '{release_name}' in namespace '{namespace}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        try:
            # Check if helm is installed first
            if shutil.which("helm") is None:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Helm command not found. Please install Helm to manage releases."
                )
                return
                
            # Use helm uninstall command
            cmd = ["helm", "uninstall", release_name, "-n", namespace]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Helm release '{release_name}' was successfully uninstalled."
                )
                # Reload data
                self.load_data()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to uninstall Helm release: {stderr}"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred: {str(e)}"
            )
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)