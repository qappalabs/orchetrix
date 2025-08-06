"""
Dynamic implementation of the Persistent Volume Claims page with live Kubernetes data.
"""

from PyQt6.QtWidgets import (QHeaderView, QWidget, QLabel, QHBoxLayout, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors


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

class PersistentVolumeClaimsPage(BaseResourcePage):
    """
    Displays Kubernetes persistent volume claims with live data and resource operations.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "persistentvolumeclaims"  # Set resource type for kubectl
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Persistent Volume Claims page"""
        # Define headers and sortable columns - KEEP ORIGINAL
        headers = ["", "Name", "Namespace", "Storage Class", "Size", "Pods", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7}
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Persistent Volume Claims", headers, sortable_columns)
        
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
        delete_btn.clicked.connect(lambda: self.delete_selected_resources())
        
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
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
        
        header = self.table.horizontalHeader()
        
        # Column specifications with optimized default widths
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 140, "interactive"), # Name
            (2, 90, "interactive"),  # Namespace
            (3, 80, "interactive"),  # Storage Class
            (4, 70, "interactive"),  # Size
            (5, 130, "interactive"), # Pods
            (6, 110, "interactive"), # Age
            (7, 80, "stretch"),      # Status - stretch to fill remaining space
            (8, 40, "fixed")        # Actions
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

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with persistent volume claim data from live Kubernetes resources
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Extract data from raw_data
        raw_data = resource.get("raw_data", {})
        spec = raw_data.get("spec", {})
        status = raw_data.get("status", {})
        metadata = raw_data.get("metadata", {})
        
        # Get storage class
        storage_class = spec.get("storageClassName", "<none>")
        if not storage_class:
            storage_class = "<none>"
        
        # Get size
        size = "<none>"
        if status.get("capacity") and status["capacity"].get("storage"):
            size = status["capacity"]["storage"]
        elif spec.get("resources") and spec["resources"].get("requests") and spec["resources"]["requests"].get("storage"):
            size = spec["resources"]["requests"]["storage"]
        
        # Get pods using this PVC (we'll need to search for this)
        # For now, show placeholder - this requires additional API call to find pods using this PVC
        pods = self._get_pods_using_pvc(resource_name, resource["namespace"])
        
        # Get status
        pvc_status = status.get("phase", "Unknown")
        
        # Prepare data columns - MATCH ORIGINAL HEADERS
        columns = [
            resource["name"],        # Name
            resource["namespace"],   # Namespace
            storage_class,          # Storage Class
            size,                   # Size
            pods,                   # Pods
            resource["age"]         # Age
            # Status is handled separately as StatusLabel widget
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 5:  # Age column
                try:
                    # Extract numeric part from age string
                    if 'd' in value:
                        num = int(value.replace('d', ''))
                    elif 'h' in value:
                        num = int(value.replace('h', '')) / 24  # Convert to fraction of day
                    elif 'm' in value:
                        num = int(value.replace('m', '')) / (24 * 60)  # Convert to fraction of day
                    else:
                        num = 0
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 4:  # Pods column - sort by number of pods
                try:
                    if value == "<none>":
                        num = 0
                    elif "+" in value and "more" in value:
                        # Extract number from "pod1, pod2 +3 more" format
                        parts = value.split("+")
                        if len(parts) > 1:
                            num = int(parts[1].split()[0]) + 2  # +2 for the two shown pods
                        else:
                            num = 1
                    else:
                        # Count commas to get number of pods
                        num = len(value.split(","))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col == 0:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Set default text color for all non-status columns
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create status widget with proper color for PVCs (column 7 - Status)
        status_col = 7  # Status column index
        status_text = pvc_status
        
        # Pick the right color
        if status_text == "Bound":
            color = AppColors.STATUS_ACTIVE
        else:
            color = AppColors.STATUS_WARNING
        
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
                    parent.detail_manager.show_detail("persistentvolumeclaim", resource_name, namespace)
    
    def _get_pods_using_pvc(self, pvc_name, namespace):
        """Get the names of pods that are using this PVC"""
        try:
            # Get kubernetes client from parent or create new one
            kube_client = None
            
            # Try to get from parent first
            parent = self.parent()
            while parent and not hasattr(parent, 'kube_client'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'kube_client'):
                kube_client = parent.kube_client
            else:
                # Import and create new client
                from utils.kubernetes_client import get_kubernetes_client
                kube_client = get_kubernetes_client()
            
            # Get all pods in the same namespace
            pods_list = kube_client.v1.list_namespaced_pod(namespace=namespace)
            
            using_pods = []
            for pod in pods_list.items:
                if pod.spec and pod.spec.volumes:
                    for volume in pod.spec.volumes:
                        if (volume.persistent_volume_claim and 
                            volume.persistent_volume_claim.claim_name == pvc_name):
                            using_pods.append(pod.metadata.name)
                            break  # Found it, no need to check other volumes
            
            if using_pods:
                if len(using_pods) <= 3:
                    return ", ".join(using_pods)
                else:
                    return f"{using_pods[0]}, {using_pods[1]} +{len(using_pods)-2} more"
            else:
                return "<none>"
                
        except Exception as e:
            # If we can't get the pod info, return placeholder
            return "<none>"