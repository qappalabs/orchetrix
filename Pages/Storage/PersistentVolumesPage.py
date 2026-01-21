"""
Dynamic implementation of the Persistent Volumes page with live Kubernetes data.
"""

from PyQt6.QtWidgets import (QHeaderView, QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors


class PersistentVolumesPage(BaseResourcePage):
    """
    Displays Kubernetes persistent volumes with live data and resource operations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "persistentvolumes"  # Set resource type for kubectl
        self.show_namespace_dropdown = False  # PersistentVolumes are cluster-scoped
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the Persistent Volumes page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Storage Class", "Capacity", "Claim", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6}

        # Set up the base UI components with styles
        super().setup_ui("Persistent Volumes", headers, sortable_columns)

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
            (2, 90, "interactive"),  # Storage class
            (3, 80, "interactive"),  # Capacity
            (4, 70, "interactive"),  # Claim
            (5, 60, "interactive"),  # Age
            (6, 80, "stretch"),      # Status - stretch to fill remaining space
            (7, 40, "fixed")        # Actions
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
        Populate a single row with persistent volume data from live Kubernetes resources
        """
        # Set row height once
        self.table.setRowHeight(row, 40)

        # Create checkbox for row selection
        resource_name = resource["name"]
        # Checkbox styling handled by BaseResourcePage
        checkbox_container = self._create_checkbox_container(
            row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Extract data from resource
        storage_class = resource.get("raw_data", {}).get(
            "spec", {}).get("storageClassName", "<none>")
        capacity = resource.get("raw_data", {}).get(
            "spec", {}).get("capacity", {}).get("storage", "<none>")

        # Get claim information
        claim_ref = resource.get("raw_data", {}).get(
            "spec", {}).get("claimRef", {})
        claim = f"{claim_ref.get('namespace', '')}/{claim_ref.get('name', '')}" if claim_ref else "<none>"
        if claim == "/":
            claim = "<none>"

        # Get status
        status = resource.get("raw_data", {}).get(
            "status", {}).get("phase", "<none>")

        # Prepare data columns
        columns = [
            resource["name"],
            storage_class,
            capacity,
            claim,
            resource["age"]
            # Status is now handled separately using StatusLabel widget
        ]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting (Age column)
            if col == 4:  # Age column
                try:
                    # Parse age with support for d, h, m, s suffixes
                    age_str = str(value)
                    if age_str and age_str[-1] in 'dhms':
                        unit = age_str[-1]
                        numeric_part = age_str[:-1]
                        unit_multipliers = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}
                        num = int(float(numeric_part) * unit_multipliers.get(unit, 1))
                    else:
                        # No suffix, try to parse as integer
                        num = int(float(age_str)) if age_str else 0
                except (ValueError, TypeError):
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col == 0:  # Name column
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Set default text color for all non-status columns
            item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Create status widget with proper color for PVs
        status_col = 6  # Status column index
        status_text = status

        # Pick the right color based on status
        if status_text in ["Bound", "Available"]:
            color = AppColors.STATUS_ACTIVE
        else:
            color = AppColors.STATUS_WARNING

        # Create status widget with proper color
        status_widget = StatusLabel(status_text, color)
        # Connect click event to select the row
        status_widget.clicked.connect(lambda: self.table.selectRow(row))
        self.table.setCellWidget(row, status_col, status_widget)

        # Create and add action button - styling handled by BaseResourcePage
        action_button = self._create_action_button(
            row, resource["name"], resource.get("namespace", ""))
        action_container = self._create_action_container(row, action_button)
        # +2 for checkbox and status
        self.table.setCellWidget(row, len(columns) + 2, action_container)

    def handle_row_click(self, row, column):
        """
        Handle row selection when a table cell is clicked.
        Selects the row and shows detail view, ignoring clicks on the action column.
        """
        # Skip action column (last column)
        if column == self.table.columnCount() - 1:
            return

        # Select the row
        self.table.selectRow(row)

        # Get resource name from column 1
        resource_name = None
        if self.table.item(row, 1) is not None:
            resource_name = self.table.item(row, 1).text()

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

                # PersistentVolumes are cluster-scoped, no namespace needed
                parent.detail_manager.show_detail(resource_type, resource_name, None)
