"""
Dynamic implementation of the Port Forwarding page with live Kubernetes data
and a status column, formatted similarly to ServicesPage.
"""

from PyQt6.QtWidgets import (QHeaderView, QPushButton, QLabel, QVBoxLayout, 
                            QWidget, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
import psutil


class StatusLabel(QWidget):
    """Widget that displays a status with consistent styling and background handling."""
    clicked = pyqtSignal()
    
    def __init__(self, status_text, color=None, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create label
        self.label = QLabel(status_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set color if provided, otherwise use default color
        if color:
            self.label.setStyleSheet(f"color: {QColor(color).name()}; background-color: transparent;")
        
        # Add label to layout
        layout.addWidget(self.label)
        
        # Make sure this widget has a transparent background
        self.setStyleSheet("background-color: transparent;")
    
    def mousePressEvent(self, event):
        """Emit clicked signal when widget is clicked"""
        self.clicked.emit()
        super().mousePressEvent(event)
class PortForwardingPage(BaseResourcePage):
    """
    Displays Kubernetes port forwarding configurations with live data.
    
    Features:
    1. Dynamic loading of port forwards from kubectl
    2. Editing port forwards
    3. Deleting port forwards (individual and batch)
    4. Status monitoring
    """
    
    def __init__(self, parent=None):
        # Initialize empty resources list before calling parent's init
        self.resources = []
        # We need to set resource_type even for pseudo-resources
        self.resource_type = "portforwarding"
        self.port_forward_processes = {}  # Store running port-forward processes
        super().__init__(parent)
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Port Forwarding page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Kind", "Pod Port", "Local Port", "Protocol", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7}
        
        # Set up the base UI components
        layout = super().setup_ui("Port Forwarding", headers, sortable_columns)
        
        # Apply table style
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure column widths
        self.configure_columns()
        
        # Add delete selected button
        self._add_delete_selected_button()
        
    def _add_delete_selected_button(self):
        """Add a button to delete selected resources."""
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_resources)
        
        # Find the header layout
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "Refresh":
                        # Insert before the refresh button
                        item.layout().insertWidget(item.layout().count() - 1, delete_btn)
                        break
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Column 0: Checkbox (fixed width) - already set in base class
        
        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Configure stretch columns
        stretch_columns = [2, 3, 4, 5, 6, 7]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 40)
    
    def load_data(self):
        """Load port forwarding data into the table with live data"""
        # Check if already loading - use the base class implementation to show loading state
        if self.is_loading:
            return
            
        self.is_loading = True
            
        # Clear existing data
        self.resources = []
        self.selected_items.clear()
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        # Show proper loading indicator using the base class approach
        loading_row = self.table.rowCount()
        self.table.setRowCount(loading_row + 1)
        self.table.setSpan(loading_row, 0, 1, self.table.columnCount())
        
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.setContentsMargins(20, 20, 20, 20)
        
        loading_text = QLabel("Loading port forwards...")
        loading_text.setStyleSheet("color: #BBBBBB; font-size: 14px;")
        loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        loading_layout.addWidget(loading_text)
        
        self.table.setCellWidget(loading_row, 0, loading_widget)
        
        # Use a QTimer to delay the actual data loading slightly, allowing the UI to update first
        QTimer.singleShot(50, self._load_port_forwarding_data)
    
    def _load_port_forwarding_data(self):
        """Internal method to load port forwarding data asynchronously"""
        try:
            import subprocess
            import json
            
            # Get all pods - we need this for reference
            result = subprocess.run(
                ["kubectl", "get", "pods", "--all-namespaces", "-o", "json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.on_load_error(f"Failed to get pods: {result.stderr}")
                return
            
            port_forwards = []
            
            # For running port-forwards, we need to check the actual processes
            kubectl_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'kubectl' and proc.info['cmdline']:
                        cmdline = proc.info['cmdline']
                        if 'port-forward' in cmdline:
                            kubectl_processes.append({
                                'pid': proc.info['pid'],
                                'cmdline': cmdline
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Process each port-forward
            for process in kubectl_processes:
                cmdline = process['cmdline']
                pid = process['pid']
                
                # Extract details from command line
                resource_type = "pod"  # Default 
                resource_name = None
                namespace = "default"
                local_port = None
                target_port = None
                
                # Extract command arguments
                for i, arg in enumerate(cmdline):
                    if arg == 'port-forward' and i + 1 < len(cmdline):
                        # Next arg is usually resource/name
                        resource_arg = cmdline[i+1]
                        if '/' in resource_arg:
                            parts = resource_arg.split('/')
                            if len(parts) == 2:
                                resource_type = parts[0]
                                resource_name = parts[1]
                    
                    if arg == '-n' and i + 1 < len(cmdline):
                        namespace = cmdline[i+1]
                    
                    # Look for port mapping (local:remote)
                    if ':' in arg:
                        parts = arg.split(':')
                        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                            local_port = parts[0]
                            target_port = parts[1]
                
                # If we found a valid port-forward, add it to our list
                if resource_name and local_port and target_port:
                    port_forwards.append({
                        'name': f"{resource_name}-{local_port}-{target_port}",
                        'resource_name': resource_name,
                        'namespace': namespace,
                        'kind': resource_type.capitalize(),
                        'pod_port': target_port,
                        'local_port': local_port,
                        'protocol': 'TCP',  # Default
                        'status': 'Active',
                        'pid': pid
                    })
            
            # Add data from our stored port forwards dict for anything not running
            for key, process_info in self.port_forward_processes.items():
                if not process_info['process'] or not process_info['process'].isRunning():
                    # Process not running, mark as disconnected
                    name, namespace = key
                    found = False
                    
                    # Check if this is already in our list
                    for pf in port_forwards:
                        if pf['name'] == name and pf['namespace'] == namespace:
                            found = True
                            break
                    
                    if not found:
                        # Add as disconnected
                        port_forwards.append({
                            'name': name,
                            'resource_name': process_info.get('resource_name', name),
                            'namespace': namespace,
                            'kind': process_info.get('kind', 'Pod'),
                            'pod_port': process_info.get('target_port', '<none>'),
                            'local_port': process_info.get('local_port', '<none>'),
                            'protocol': process_info.get('protocol', 'TCP'),
                            'status': 'Disconnected',
                            'pid': None
                        })
            
            # Update the resources list
            self.resources = port_forwards
            
            # Use the base class method to show the results
            self.on_resources_loaded(port_forwards, self.resource_type)
            
        except Exception as e:
            self.on_load_error(f"Error loading port forwarding data: {str(e)}")
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with port forwarding data using ServicesPage style
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Prepare data columns
        columns = [
            resource["resource_name"],
            resource["namespace"],
            resource["kind"],
            resource["pod_port"],
            resource["local_port"], 
            resource["protocol"]
            # Status is now handled separately using StatusLabel widget
        ]
        
        # Add columns to table - similar to ServicesPage style
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Create item for each cell
            item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [2, 3, 4, 5]:  # Center-align Kind, Pod Port, Local Port, Protocol
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set default text color for all non-status columns
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create status widget with proper color for Port Forwarding
        status_col = 7  # Status column index
        status_text = resource["status"]
        
        # Pick the right color
        if status_text == "Active":
            color = AppColors.STATUS_ACTIVE
        else:
            color = AppColors.STATUS_DISCONNECTED
        
        # Create status widget with proper color
        status_widget = StatusLabel(status_text, color)
        # Connect click event to select the row
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)
        
        # Create and add action button
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 2, action_container)  # +2 for checkbox and status
    def _handle_action(self, action, row):
        """Handle action button clicks - Edit or Delete"""
        if row >= len(self.resources):
            return
            
        resource = self.resources[row]
        resource_name = resource.get("name", "")
        resource_namespace = resource.get("namespace", "")
        
        if action == "Edit":
            self.edit_resource(resource)
        elif action == "Delete":
            self.delete_resource(resource_name, resource_namespace)
    
    def edit_resource(self, resource):
        """Open editor for port-forwarding configuration"""
        from PyQt6.QtWidgets import QMessageBox
        
        # Stop the port-forward if it's running
        if resource["status"] == "Active" and resource.get("pid"):
            try:
                process = psutil.Process(resource["pid"])
                process.terminate()
            except Exception as e:
                pass
            
            # Mark as disconnected
            resource["status"] = "Disconnected"
        
        # Since port-forwarding isn't a real K8s resource type with YAML definition,
        # we'll create a dialog to edit the configuration instead
        QMessageBox.information(
            self,
            "Edit Port Forward",
            f"Editing port forward to {resource['resource_name']}\n\n"
            f"Resource: {resource['kind']}/{resource['resource_name']}\n"
            f"Namespace: {resource['namespace']}\n"
            f"Local Port: {resource['local_port']}\n"
            f"Target Port: {resource['pod_port']}\n\n"
            "To edit port-forwards, terminate the current one and create a new one using kubectl."
        )
        
        # Reload data to reflect changes
        self.load_data()
    
    def delete_resource(self, resource_name, resource_namespace):
        """Override to handle port-forward specific deletion"""
        # Find the resource
        resource = None
        for r in self.resources:
            if r["name"] == resource_name and r["namespace"] == resource_namespace:
                resource = r
                break
                
        if not resource:
            return
            
        from PyQt6.QtWidgets import QMessageBox
        
        # Confirm deletion
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the port forward to {resource['resource_name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Additional port-forward specific cleanup
        if resource["status"] == "Active" and resource.get("pid"):
            try:
                process = psutil.Process(resource["pid"])
                process.terminate()
            except Exception as e:
                pass
            
        # Remove from our internal tracking
        key = (resource_name, resource_namespace)
        if key in self.port_forward_processes:
            process_info = self.port_forward_processes[key]
            if process_info["process"] and process_info["process"].isRunning():
                process_info["process"].terminate()
            del self.port_forward_processes[key]
        
        # Remove from resources list
        self.resources = [r for r in self.resources if not (
            r["name"] == resource_name and r["namespace"] == resource_namespace
        )]
        
        # Show success message
        QMessageBox.information(
            self,
            "Port Forward Deleted",
            f"Port forward to {resource['resource_name']} has been deleted."
        )
        
        # Update table
        self.load_data()
    
    def delete_selected_resources(self):
        """Override to handle port-forward specific deletion for multiple resources"""
        from PyQt6.QtWidgets import QMessageBox
        
        if not self.selected_items:
            QMessageBox.information(
                self, 
                "No Selection", 
                "No port forwards selected for deletion."
            )
            return
            
        # Confirm deletion
        count = len(self.selected_items)
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {count} selected port forwards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Collect resources to delete
        resources_to_delete = []
        for key in self.selected_items:
            for resource in self.resources:
                if resource["name"] == key[0] and resource.get("namespace", "") == key[1]:
                    resources_to_delete.append(resource)
                    break
        
        # Delete each port forward
        for port_forward in resources_to_delete:
            # Stop the process if it's running
            if port_forward["status"] == "Active" and port_forward.get("pid"):
                try:
                    process = psutil.Process(port_forward["pid"])
                    process.terminate()
                except Exception as e:
                    pass
            
            # Remove from our internal tracking
            key = (port_forward["name"], port_forward["namespace"])
            if key in self.port_forward_processes:
                process_info = self.port_forward_processes[key]
                if process_info["process"] and process_info["process"].isRunning():
                    process_info["process"].terminate()
                del self.port_forward_processes[key]
        
        # Show success message
        QMessageBox.information(
            self,
            "Port Forwards Deleted",
            f"{len(resources_to_delete)} port forwards have been deleted."
        )
        
        # Clear selected items
        self.selected_items.clear()
        
        # Reload data to reflect changes
        self.load_data()
        
    # def handle_row_click(self, row, column):
    #     """Handle row selection when a table cell is clicked"""
    #     if column != self.table.columnCount() - 1:  # Skip action column
    #         # Select the row
    #         self.table.selectRow(row)

    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
            # Get resource details
            resource_name = None
            namespace = None
            
            # Get the resource name
            if self.table.item(row, 1) is not None:
                resource_name = self.table.item(row, 1).text()
            
            # Get namespace if applicable
            if self.table.item(row, 2) is not None:
                namespace = self.table.item(row, 2).text()
            
            # Show detail view
            if resource_name:
                # Find the ClusterView instance
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    # Get singular resource type
                    resource_type = self.resource_type
                    if resource_type.endswith('s'):
                        resource_type = resource_type[:-1]
                    
                    parent.detail_manager.show_detail(resource_type, resource_name, namespace)