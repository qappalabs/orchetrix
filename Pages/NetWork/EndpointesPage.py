"""
Dynamic implementation of the Endpoints page with live Kubernetes data.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage

class EndpointsPage(BaseResourcePage):
    """
    Displays Kubernetes Endpoints with live data and resource operations.
    
    Features:
    1. Dynamic loading of Endpoints from the cluster
    2. Editing Endpoints with editor
    3. Deleting Endpoints (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "endpoints"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Endpoints page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Endpoints", "Age", ""]
        sortable_columns = {1, 2, 3, 4}
        
        # Set up the base UI components
        layout = super().setup_ui("Endpoints", headers, sortable_columns)
        
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
            (1, 160, "interactive"), # Name
            (2, 200, "interactive"),  # Namespace
            (3, 190, "interactive"),  # Endpoints
            (4, 60, "stretch"),  # Age
            (5, 40, "fixed")        # Actions
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
        Populate a single row with Endpoint data
        """
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            resource.get("endpoints", "<none>"),
            resource["age"]
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 3:  # Age column
                try:
                    num = int(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in (1, 2, 3):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Add item to table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button using base class method with proper styling
        from PyQt6.QtWidgets import QWidget, QHBoxLayout
        from UI.Styles import AppStyles, AppConstants
        
        action_button = self._create_action_button(row, resource["name"])
        action_button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE +
    """
    QToolButton::menu-indicator { image: none; width: 0px; }
    """)
        
        # Create action container with proper styling
        action_container = QWidget()
        action_container.setFixedWidth(AppConstants.SIZES["ACTION_WIDTH"])
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(action_button)
        
        self.table.setCellWidget(row, len(columns) + 1, action_container)

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
                    # Always use "endpoint" (singular) for the resource type
                    parent.detail_manager.show_detail("endpoints", resource_name, namespace)