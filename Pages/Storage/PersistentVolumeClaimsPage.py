"""
Dynamic implementation of the Persistent Volume Claims page with live Kubernetes data.
"""

from PyQt6.QtWidgets import (QHeaderView, QWidget, QLabel, QHBoxLayout, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors


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
        
        # Get pods using this PVC - show placeholder to avoid blocking API calls
        # This information would require additional API calls which can block the UI
        pods = "<none>"
        
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
    
    # Removed _get_pods_using_pvc method to prevent blocking API calls on UI thread