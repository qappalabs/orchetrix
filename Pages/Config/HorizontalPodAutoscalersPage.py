"""
Dynamic implementation of the Horizontal Pod Autoscalers page with live Kubernetes data.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles


class HorizontalPodAutoscalersPage(BaseResourcePage):
    """
    Displays Kubernetes Horizontal Pod Autoscalers with live data and resource operations.
    
    Features:
    1. Dynamic loading of HPAs from the cluster
    2. Editing HPAs with editor
    3. Deleting HPAs (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "horizontalpodautoscalers"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the HPAs page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Metrics", "Min Pods", "Max Pods", "Replicas", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8}
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Horizontal Pod Autoscalers", headers, sortable_columns)
        
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
            (3, 80, "interactive"),  # Metrics
            (4, 80, "interactive"),  # Min Pods
            (5, 60, "interactive"),  # Max Pods
            (6, 60, "interactive"),  # Replicas
            (7, 80, "interactive"),  # Age
            (8, 80, "stretch"),      # Status - stretch to fill remaining space
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

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with HPA data
        """
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            resource.get("metrics", "None"),
            resource.get("min_pods", "1"),
            resource.get("max_pods", "10"),
            resource.get("current_replicas", "0"),
            resource["age"]
            # Status is now handled separately using StatusLabel widget
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 3:  # Min Pods column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 4:  # Max Pods column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 5:  # Replicas column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 6:  # Age column
                try:
                    num = int(value.replace('d', '').replace('h', '').replace('m', ''))
                    if 'd' in value:
                        num = num * 1440  # Convert days to minutes
                    elif 'h' in value:
                        num = num * 60    # Convert hours to minutes
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [1, 2, 3, 4, 5, 6]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set default text color
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Add item to table
            self.table.setItem(row, cell_col, item)
        
        # Create status widget with proper color for HPAs
        status_col = 8  # Status column index
        status_text = resource.get("status", "Unknown")
        
        # Pick the right color
        if status_text == "Healthy":
            color = AppColors.STATUS_ACTIVE
        elif status_text == "Warning":
            color = AppColors.ACCENT_RED
        elif status_text == "Scaling":
            color = AppColors.ACCENT_BLUE
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