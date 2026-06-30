"""
Dynamic implementation of the PriorityClasses page with live Kubernetes data.
"""

from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt, QTimer

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from Utils.data_formatters import parse_age_to_seconds, int_sort_key

class PriorityClassesPage(BaseResourcePage):
    """
    Displays Kubernetes PriorityClasses with live data and resource operations.
    
    Features:
    1. Dynamic loading of PriorityClasses from the cluster
    2. Editing PriorityClasses with editor
    3. Deleting PriorityClasses (individual and batch)
    4. Resource details viewer
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "priorityclasses"
        self.show_namespace_dropdown = False  # PriorityClasses are cluster-scoped
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the PriorityClasses page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Value", "Global Default", "Age", ""]
        sortable_columns = {1, 2, 3, 4}

        # Set up the base UI components
        super().setup_ui("Priority Classes", headers, sortable_columns)

        # Configure column widths
        self.configure_columns()

    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return

        header = self.table.horizontalHeader()

        # Column specifications with optimized default widths
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 140, "stretch"),     # Name - stretch to fill remaining space
            (2, 90, "interactive"),  # Value
            (3, 60, "interactive"),  # Global Default
            (4, 80, "interactive"),  # Status
            (5, 40, "fixed")         # Actions
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

    def _auto_resize_columns(self, max_col_widths=None, min_col_widths=None):
        """Override to provide explicit widths for columns to let Name stretch and avoid clipping."""
        explicit_mins = {
            1: 120,  # Name
            2: 100,  # Value
            3: 100,  # Global Default
            4: 80,   # Status
            5: 40,   # Actions
        }
        if min_col_widths:
            explicit_mins.update(min_col_widths)
        explicit_maxes = {
            2: 120,  # Value
            3: 120,  # Global Default
            4: 100,  # Status
        }
        if max_col_widths:
            explicit_maxes.update(max_col_widths)
        super()._auto_resize_columns(max_col_widths=explicit_maxes, min_col_widths=explicit_mins)

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with PriorityClass data
        """
        # Set row height
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection (styling already handled by BaseResourcePage)
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Prepare data columns
        columns = [
            resource["name"],
            resource.get("value", "0"),
            resource.get("global_default", "false"),
            resource["age"]
        ]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting
            if col == 1:  # Value column
                item = SortableTableWidgetItem(value, int_sort_key(value))
            elif col == 3:  # Age column
                item = SortableTableWidgetItem(value, parse_age_to_seconds(value))
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col in [1, 2, 3]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Add item to table
            self.table.setItem(row, cell_col, item)

        # Create and add action button
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        action_container = self._create_action_container(row, action_button)
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
                    parent.detail_manager.show_detail("priorityclasses", resource_name, namespace)
