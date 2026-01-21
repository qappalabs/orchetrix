"""
Dynamic implementation of the Definitions page with live Kubernetes data.
"""

import logging

from PyQt6.QtWidgets import (QHeaderView, QWidget, QLabel)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors

class DefinitionsPage(BaseResourcePage):
    """
    Displays Kubernetes CustomResourceDefinitions with live data and resource operations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "customresourcedefinitions"  # Set resource type for kubectl
        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the Definitions page"""
        # Define headers and sortable columns
        headers = ["", "Resource", "Group", "Version", "Scope", "Age", ""]
        sortable_columns = {1, 2, 3, 4, 5}

        # Set up the base UI components
        layout = super().setup_ui("Definitions", headers, sortable_columns)

        # Apply table style
        # Table styling is already handled by BaseResourcePage

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
            (1, 180, "interactive"), # Resource
            (2, 150, "interactive"),  # Group
            (3, 120, "interactive"),  # Version
            (4, 150, "interactive"),  # Scope
            (5, 80, "stretch"),  # Age
            (6, 40, "fixed")        # Actions
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
        Populate a single row with CustomResourceDefinition data from live Kubernetes resources
        """
        # Set row height once
        self.table.setRowHeight(row, 40)

        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Extract CRD details from raw data
        raw_data = resource.get("raw_data", {})

        # Get resource name (short name if available)
        spec = raw_data.get("spec", {})
        names = spec.get("names", {})
        plural = names.get("plural", "")

        # Get group
        group = spec.get("group", "<none>")

        # Get version
        versions = spec.get("versions", [])
        version = versions[0].get("name", "<none>") if versions else "<none>"

        # Get scope
        scope = spec.get("scope", "<none>")

        # Prepare data columns
        columns = [
            plural,
            group,
            version,
            scope,
            resource["age"]
        ]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting
            if col == 4:  # Age column
                try:
                    num = int(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col == 0:  # Resource column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Set text color
            item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Create and add action button
        action_button = self._create_action_button(row, resource["name"], resource.get("namespace", ""))
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(columns) + 1, action_container)


    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)

            # Get resource details - FIXED: Get actual resource name from checkbox
            resource_name = None
            namespace = None

            # Get the actual resource name from the checkbox (which has the full CRD name)
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                # Find the checkbox widget inside the container
                checkbox = checkbox_container.findChild(checkbox_container.__class__.__bases__[0])
                if not checkbox:
                    # Try to find QCheckBox specifically
                    from PyQt6.QtWidgets import QCheckBox
                    checkbox = checkbox_container.findChild(QCheckBox)
                
                if checkbox:
                    resource_name = checkbox.property("resource_name")

            # Fallback: try to find by plural name if checkbox method failed
            if not resource_name:
                if self.table.item(row, 1) is not None:
                    plural_name = self.table.item(row, 1).text()
                    # Find the actual resource name by plural name
                    resource_name = self.get_resource_name_by_plural(plural_name)

            # Get namespace if applicable (for CRDs this is usually None)
            namespace = None  # CRDs are cluster-scoped

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

                    # Get raw_data from resources list and pass it to detail view
                    raw_data = self.get_raw_data_for_row(resource_name)
                    logging.info(f"DefinitionsPage: Passing raw_data for {resource_name}, keys: {list(raw_data.keys()) if raw_data else 'None'}")
                    parent.detail_manager.show_detail(resource_type, resource_name, namespace, raw_data)

    def get_resource_name_by_plural(self, plural_name):
        """Get the actual resource name (full CRD name) by plural name.
        
        This is needed because the table displays plural names but we need
        the full CRD name to find the raw_data.
        """
        try:
            for resource in self.resources:
                raw_data = resource.get("raw_data", {})
                spec = raw_data.get("spec", {})
                names = spec.get("names", {})
                if names.get("plural") == plural_name:
                    return resource.get("name")
        except Exception as e:
            logging.error(f"Error finding resource name for plural '{plural_name}': {e}")
        return plural_name  # Fallback to plural name

    def get_raw_data_for_row(self, resource_name):
        """Get raw data for a specific resource by name.
        
        Uses resource name lookup (not row index) to handle sorted/filtered tables correctly.
        This ensures detail sections can load data directly without relying on
        get_resource_detail API calls.
        """
        try:
            # Find resource by name to handle sorting/filtering correctly
            for resource in self.resources:
                if resource.get("name") == resource_name or resource.get("resource_name") == resource_name:
                    return resource.get("raw_data", {})
        except Exception as e:
            logging.error(f"Error getting raw data for resource '{resource_name}': {e}")
        return {}
