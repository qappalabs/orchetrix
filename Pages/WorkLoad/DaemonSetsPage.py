"""
Dynamic implementation of the DaemonSets page with live Kubernetes data and resource operations.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles

class DaemonSetsPage(BaseResourcePage):
    """
    Displays Kubernetes DaemonSets with live data and resource operations.
    
    Features:
    1. Dynamic loading of DaemonSets from the cluster
    2. Editing DaemonSets with editor
    3. Deleting DaemonSets (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "daemonsets"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the DaemonSets page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Pods", "Node Selector", "Age", ""]
        sortable_columns = {1, 2, 3, 5}
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Daemon Sets", headers, sortable_columns)
        
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
            (3, 80, "interactive"),  # Pods
            (4, 70, "interactive"),  # Node Selector
            (5, 130, "stretch"), # Age
            (6, 40, "fixed"), # Actions

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
        Populate a single row with DaemonSet data
        """
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Extract additional data from the raw_data field if available
        raw_data = resource.get("raw_data", {})
        
        # Get pod status
        pods_str = "0/0"
        if raw_data:
            status = raw_data.get("status", {})
            current_number_scheduled = status.get("currentNumberScheduled", 0)
            desired_number_scheduled = status.get("desiredNumberScheduled", 0)
            pods_str = f"{current_number_scheduled}/{desired_number_scheduled}"
        
        # Get node selector - fix to correctly extract from template
        node_selector = "<none>"
        if raw_data:
            spec = raw_data.get("spec", {})
            
            # DaemonSets have nodeSelector in spec.template.spec
            template = spec.get("template", {})
            template_spec = template.get("spec", {})
            
            # First try to get from template.spec.nodeSelector
            selectors = template_spec.get("nodeSelector", {})
            
            # If that's empty, try to get from spec.nodeSelector directly (old format)
            if not selectors:
                selectors = spec.get("nodeSelector", {})
                
            # Format the node selectors as a string
            if selectors:
                node_selector = ", ".join([f"{k}={v}" for k, v in selectors.items()])
        
        # Parse age correctly from metadata
        age_str = resource["age"]
        if raw_data:
            metadata = raw_data.get("metadata", {})
            creation_timestamp = metadata.get("creationTimestamp")
            if creation_timestamp:
                import datetime
                from dateutil import parser
                try:
                    # Parse creation time and calculate age
                    creation_time = parser.parse(creation_timestamp)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    delta = now - creation_time
                    
                    # Format age string
                    days = delta.days
                    seconds = delta.seconds
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    
                    if days > 0:
                        age_str = f"{days}d"
                    elif hours > 0:
                        age_str = f"{hours}h"
                    else:
                        age_str = f"{minutes}m"
                except Exception:
                    # Keep the original age if parsing fails
                    pass
                
        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            pods_str,
            node_selector,
            age_str
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 2:  # Pods column
                try:
                    current, desired = value.split("/")
                    pods_value = float(current) / float(desired) if float(desired) > 0 else 0
                except (ValueError, ZeroDivisionError):
                    pods_value = 0
                item = SortableTableWidgetItem(value, pods_value)
            elif col == 4:  # Age column
                try:
                    # Convert age string (like "5d" or "2h") to minutes for sorting
                    if 'd' in value:
                        age_value = int(value.replace('d', '')) * 1440  # days to minutes
                    elif 'h' in value:
                        age_value = int(value.replace('h', '')) * 60  # hours to minutes
                    elif 'm' in value:
                        age_value = int(value.replace('m', ''))  # minutes
                    else:
                        age_value = 0
                except ValueError:
                    age_value = 0
                item = SortableTableWidgetItem(value, age_value)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [1, 2, 3, 4]:  # Pods, Age
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set text color
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button with only Edit and Delete options
        action_button = self._create_action_button(row, resource_name, resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 1, action_container)

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