"""
Dynamic implementation of the Services page with live Kubernetes data
and a status column.
"""

from PyQt6.QtWidgets import (QHeaderView, QPushButton, QLabel, QVBoxLayout, 
                            QWidget, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles


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

class ServicesPage(BaseResourcePage):
    """
    Displays Kubernetes Services with live data and resource operations.
    
    Features:
    1. Dynamic loading of Services from the cluster
    2. Editing Services with terminal editor
    3. Deleting Services (individual and batch)
    4. Status column showing service availability
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "services"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Services page"""
        # Define headers and sortable columns - added Status column
        headers = ["", "Name", "Namespace", "Type", "Cluster IP", "Port", "External IP", "Selector", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8, 9}
        
        # Set up the base UI components
        layout = super().setup_ui("Services", headers, sortable_columns)
        
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
        stretch_columns = [2, 3, 4, 5, 6, 7, 8, 9]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(10, 40)
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with Service data including status
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Extract service details
        spec = resource.get("raw_data", {}).get("spec", {})
        service_type = spec.get("type", "ClusterIP")
        cluster_ip = spec.get("clusterIP", "<none>")
        
        # Get ports
        ports = spec.get("ports", [])
        port_strs = []
        for port in ports:
            port_str = f"{port.get('port')}/{port.get('protocol', 'TCP')}"
            if 'targetPort' in port:
                port_str += f"→{port.get('targetPort')}"
            port_strs.append(port_str)
        port_text = ", ".join(port_strs) if port_strs else "<none>"
        
        # Get external IPs
        external_ips = spec.get("externalIPs", [])
        lb_status = resource.get("raw_data", {}).get("status", {}).get("loadBalancer", {}).get("ingress", [])
        for lb in lb_status:
            if "ip" in lb:
                external_ips.append(lb["ip"])
            elif "hostname" in lb:
                external_ips.append(lb["hostname"])
        external_ip_text = ", ".join(external_ips) if external_ips else "<none>"
        
        # Get selector
        selector = spec.get("selector", {})
        selector_text = ", ".join([f"{k}={v}" for k, v in selector.items()]) if selector else "<none>"
        
        # Determine service status - based on multiple factors
        status = self.determine_service_status(resource)
        
        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            service_type,
            cluster_ip,
            port_text,
            external_ip_text,
            selector_text,
            resource["age"]
            # Status is now handled separately using StatusLabel widget
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 7:  # Age column
                try:
                    num = int(value.replace('d', '').replace('h', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [2, 3, 4, 5, 7]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set text color for non-status columns
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Add item to table
            self.table.setItem(row, cell_col, item)
        
        # Create status widget with proper color for Services
        status_col = 9  # Status column index
        status_text = status
        
        # Pick the right color
        if status_text == "Active":
            color = AppColors.STATUS_ACTIVE
        elif status_text == "Warning":
            color = AppColors.STATUS_WARNING
        elif status_text == "Error":
            color = AppColors.STATUS_ERROR
        elif status_text == "Pending":
            color = AppColors.STATUS_PENDING
        else:
            color = AppColors.TEXT_TABLE
        
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
    def determine_service_status(self, resource):
        """
        Determine the status of a service based on its configuration and state
        """
        # Get raw data
        raw_data = resource.get("raw_data", {})
        spec = raw_data.get("spec", {})
        status = raw_data.get("status", {})
        
        # Get service type
        service_type = spec.get("type", "ClusterIP")
        
        # Check for endpoints
        has_endpoints = False
        try:
            import subprocess
            import json
            
            # Use kubectl to check endpoints
            namespace = resource.get("namespace", "default")
            service_name = resource.get("name", "")
            
            if service_name and namespace:
                # Run kubectl command to get endpoints
                result = subprocess.run(
                    ["kubectl", "get", "endpoints", service_name, "-n", namespace, "-o", "json"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Parse JSON response
                    endpoints_data = json.loads(result.stdout)
                    subsets = endpoints_data.get("subsets", [])
                    
                    # Check if there are any ready endpoints
                    for subset in subsets:
                        if subset.get("addresses", []):
                            has_endpoints = True
                            break
        except:
            # If there's an error checking endpoints, assume they exist
            has_endpoints = True
        
        # Determine status based on service type and configuration
        if service_type == "ExternalName":
            # External name services are always "active" if configured
            if "externalName" in spec:
                return "Active"
            else:
                return "Warning"
        
        elif service_type == "LoadBalancer":
            # Check if load balancer is provisioned
            lb_ingress = status.get("loadBalancer", {}).get("ingress", [])
            if lb_ingress:
                # Load balancer has an external address
                if has_endpoints:
                    return "Active"
                else:
                    return "Warning"  # Has LB but no endpoints
            else:
                return "Pending"  # LB not provisioned yet
        
        elif service_type == "NodePort" or service_type == "ClusterIP":
            # Check if the service has endpoints
            if has_endpoints:
                return "Active"
            else:
                return "Warning"  # No endpoints
        
        # Default status if we can't determine
        return "Unknown"


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