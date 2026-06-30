"""
Dynamic implementation of the Storage Classes page with live Kubernetes data.
"""

from PyQt6.QtWidgets import (QHeaderView, QWidget, QLabel)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors
from Utils.data_formatters import parse_age_to_seconds


class StorageClassesPage(BaseResourcePage):
    """
    Displays Kubernetes storage classes with live data and resource operations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "storageclasses"  # Set resource type for kubectl
        self.show_namespace_dropdown = False  # StorageClasses are cluster-scoped
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the Storage Classes page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Provisioner", "Reclaim Policy", "Default", "Age", ""]
        sortable_columns = {1, 2, 3, 4, 5}

        # Set up the base UI components with styles
        layout = super().setup_ui("Storage Classes", headers, sortable_columns)

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
            (1, 140, "stretch"),     # Name - stretch to fill remaining space
            (2, 90, "interactive"),  # Provisioner
            (3, 80, "interactive"),  # Reclaim Policy
            (4, 70, "interactive"),  # Default
            (5, 60, "interactive"),  # Age
            (6, 40, "fixed")         # Actions
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
        """Override to provide explicit minimum widths for columns that contain wider strings."""
        explicit_mins = {
            # 0 is Checkbox
            1: 140,  # Name
            2: 240,  # Provisioner - needs to be quite wide to fit things like 'k8s.io/minikube-hostpath'
            3: 130,  # Reclaim Policy
            4: 80,   # Default
            5: 60,   # Age
            6: 40,   # Actions
        }
        
        # Merge with any caller overrides
        if min_col_widths:
            explicit_mins.update(min_col_widths)
            
        explicit_maxes = {
            2: 300,  # Provisioner
            3: 180,  # Reclaim Policy
            4: 100,  # Default
            5: 80,   # Age
        }
        if max_col_widths:
            explicit_maxes.update(max_col_widths)
            
        super()._auto_resize_columns(max_col_widths=explicit_maxes, min_col_widths=explicit_mins)

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with storage class data from live Kubernetes resources
        """
        # Set row height once
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection
        resource_name = resource["name"]
        # Checkbox styling handled by BaseResourcePage
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Extract data from resource
        raw_data = resource.get("raw_data", {})
        provisioner = raw_data.get("provisioner", "<none>")
        reclaim_policy = raw_data.get("reclaimPolicy", "<none>")

        # Check if it's the default storage class
        annotations = raw_data.get("metadata", {}).get("annotations", {})
        is_default = "Yes" if annotations.get("storageclass.kubernetes.io/is-default-class") == "true" else "No"

        # Prepare data columns
        columns = [
            resource["name"],
            provisioner,
            reclaim_policy,
            is_default,
            resource["age"]
        ]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting
            if col == 4:  # Age column
                seconds = parse_age_to_seconds(value)
                item = SortableTableWidgetItem(value, seconds)
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col == 0:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Set text color
            item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Highlight default storage class
            if col == 3 and value == "Yes":  # Default column
                item.setForeground(QColor(AppColors.STATUS_ACTIVE))

            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Create and add action button
        # Action button styling handled by BaseResourcePage
        action_button = self._create_action_button(row, resource["name"], resource.get("namespace", ""))
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)

            # Get resource details
            resource_name = None
            raw_data = None

            # Get the resource name
            if self.table.item(row, 1) is not None:
                resource_name = self.table.item(row, 1).text()

            # Get raw data from resources if available
            if row < len(getattr(self, 'resources', [])):
                resource = self.resources[row]
                raw_data = resource.get("raw_data")

            # Show detail view
            if resource_name:
                # Find the ClusterView instance
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()

                if parent and hasattr(parent, 'detail_manager'):
                    # StorageClasses are cluster-wide resources, no namespace needed
                    parent.detail_manager.show_detail("storageclass", resource_name, None, raw_data=raw_data)
