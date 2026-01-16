"""
Dynamic implementation of the Roles page with live Kubernetes data.
"""

from PyQt6.QtWidgets import (QHeaderView, QWidget, QLabel)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors
from Utils.resource_utils import singularize_resource_type


class RolesPage(BaseResourcePage):
    """
    Displays Kubernetes roles with live data and resource operations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.resource_type = "roles"  # Set resource type for kubectl
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the Roles page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Age", ""]
        sortable_columns = {1, 2, 3}

        # Set up the base UI components with styles
        super().setup_ui("Roles", headers, sortable_columns)

        # Table styling is already handled by BaseResourcePage

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
            (1, 140, "interactive"),  # Name
            (2, 90, "interactive"),  # Namespace
            (3, 80, "stretch"),  # Age
            (4, 40, "fixed")        # Actions
        ]

        # Apply column configuration
        for col_index, default_width, resize_type in column_specs:
            if col_index < self.table.columnCount():
                if resize_type == "fixed":
                    header.setSectionResizeMode(
                        col_index, QHeaderView.ResizeMode.Fixed)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "interactive":
                    header.setSectionResizeMode(
                        col_index, QHeaderView.ResizeMode.Interactive)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "stretch":
                    header.setSectionResizeMode(
                        col_index, QHeaderView.ResizeMode.Stretch)
                    self.table.setColumnWidth(col_index, default_width)

        # Ensure full width utilization after configuration
        QTimer.singleShot(100, self._ensure_full_width_utilization)

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with role data from live Kubernetes resources
        """
        # Set row height once
        self.table.setRowHeight(row, 40)

        # Create checkbox for row selection
        resource_name = resource["name"]
        # Checkbox styling handled by BaseResourcePage
        checkbox_container = self._create_checkbox_container(
            row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            resource["age"]
        ]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting
            if col == 2:  # Age column
                try:
                    # Parse age value supporting multiple units and convert to days as float
                    if value.endswith('d'):
                        num = float(value[:-1])  # days
                    elif value.endswith('h'):
                        num = float(value[:-1]) / 24  # hours to days
                    elif value.endswith('m'):
                        num = float(value[:-1]) / 1440  # minutes to days
                    else:
                        # Plain integer or unrecognized format, assume days
                        num = float(value)
                except ValueError:
                    num = 0.0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col in [1, 2]:  # Namespace, Age columns
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Make cells non - editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Set text color using AppColors
            item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Create and add action button
        # Action button styling handled by BaseResourcePage
        action_button = self._create_action_button(
            row, resource["name"], resource["namespace"])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    def handle_row_click(self, row, column):
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
                resource_type = singularize_resource_type(self.resource_type)

                parent.detail_manager.show_detail(
                    resource_type, resource_name, namespace)
