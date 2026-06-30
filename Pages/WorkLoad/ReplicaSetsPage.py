"""
Dynamic implementation of the ReplicaSets page with live Kubernetes data and resource operations.
"""

from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors
from Utils.data_formatters import parse_age_to_seconds

class ReplicaSetsPage(BaseResourcePage):
    """
    Displays Kubernetes ReplicaSets with live data and resource operations.
    
    Features:
    1. Dynamic loading of ReplicaSets from the cluster
    2. Editing ReplicaSets with editor
    3. Deleting ReplicaSets (individual and batch)
    4. Resource details viewer
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "replicasets"
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the ReplicaSets page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Desired", "Current", "Ready", "Age", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6}

        # Set up the base UI components
        super().setup_ui("Replica Sets", headers, sortable_columns)

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
            (1, 180, "stretch"),     # Name - stretch to fill remaining space
            (2, 100, "interactive"),  # Namespace
            (3, 90, "interactive"),  # Desired
            (4, 80, "interactive"),  # Current
            (5, 80, "interactive"),  # Ready
            (6, 70, "interactive"),  # Age
            (7, 40, "fixed")        # Actions
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
        """Override to provide explicit widths for columns to let Name stretch."""
        explicit_mins = {
            1: 180,  # Name
            2: 100,  # Namespace
            3: 80,   # Desired
            4: 80,   # Current
            5: 80,   # Ready
            6: 60,   # Age
            7: 40,   # Actions
        }
        
        if min_col_widths:
            explicit_mins.update(min_col_widths)
            
        explicit_maxes = {
            2: 150,  # Namespace
            3: 110,  # Desired
            4: 110,  # Current
            5: 110,  # Ready
            6: 80,   # Age
        }
        
        if max_col_widths:
            explicit_maxes.update(max_col_widths)
            
        super()._auto_resize_columns(max_col_widths=explicit_maxes, min_col_widths=explicit_mins)

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with ReplicaSet data
        """
        # Set row height
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection - styling handled by BaseResourcePage
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Get status info directly from pre-parsed resource fields
        desired = str(resource.get("desired", "0"))
        current = str(resource.get("current", "0"))
        ready = str(resource.get("ready", "0"))

        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            desired,
            current,
            ready,
            resource["age"]
        ]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting
            if col >= 2 and col <= 4:  # Desired, Current, Ready columns
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 5:  # Age column
                item = SortableTableWidgetItem(value, parse_age_to_seconds(value))
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col >= 1 and col <= 5:  # Desired, Current, Ready, Age
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Set default text color
            item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Create and add action button - styling handled by BaseResourcePage
        action_button = self._create_action_button(row, resource_name, resource["namespace"])
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
                    # Get singular resource type
                    resource_type = self.resource_type
                    if resource_type.endswith('s'):
                        resource_type = resource_type[:-1]

                    parent.detail_manager.show_detail(resource_type, resource_name, namespace)
