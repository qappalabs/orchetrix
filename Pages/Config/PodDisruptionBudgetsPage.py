"""
Dynamic implementation of the PodDisruptionBudgets page with live Kubernetes data.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles

class PodDisruptionBudgetsPage(BaseResourcePage):
    """
    Displays Kubernetes PodDisruptionBudgets with live data and resource operations.
    
    Features:
    1. Dynamic loading of PodDisruptionBudgets from the cluster
    2. Editing PodDisruptionBudgets with editor
    3. Deleting PodDisruptionBudgets (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "poddisruptionbudgets"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the PodDisruptionBudgets page"""
        # Define headers and sortable columns - KEEP ORIGINAL
        headers = ["", "Name", "Namespace", "Min Available", "Max Unavailable", "Current Healthy", "Desired Healthy", "Age", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7}
        
        # Set up the base UI components
        layout = super().setup_ui("Pod Disruption Budgets", headers, sortable_columns)
        
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
            (3, 80, "interactive"),  # Min Available
            (4, 80, "interactive"),  # Max UnAvailable
            (5, 60, "interactive"),  # Current Healthy
            (6, 60, "interactive"),  # Desired Healthy
            (7, 80, "stretch"),      # Age - stretch to fill remaining space
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
        Populate a single row with PodDisruptionBudget data extracted from raw_data
        """
        # Set row height
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
        
        # Get min available
        min_available = "N/A"
        if spec.get("minAvailable") is not None:
            min_available = str(spec["minAvailable"])
        
        # Get max unavailable
        max_unavailable = "N/A"
        if spec.get("maxUnavailable") is not None:
            max_unavailable = str(spec["maxUnavailable"])
        
        # Get status information
        current_healthy = str(status.get("currentHealthy", 0))
        desired_healthy = str(status.get("desiredHealthy", 0))
        
        # Prepare data columns - MATCH ORIGINAL HEADERS
        columns = [
            resource["name"],        # Name
            resource["namespace"],   # Namespace
            min_available,          # Min Available
            max_unavailable,        # Max Unavailable
            current_healthy,        # Current Healthy
            desired_healthy,        # Desired Healthy
            resource["age"]         # Age
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col in [4, 5]:  # Current/Desired Healthy columns
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 6:  # Age column
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
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in  (1, 2, 3, 4, 5, 6):  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Add item to table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
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
                    parent.detail_manager.show_detail("poddisruptionbudget", resource_name, namespace)