"""
Dynamic implementation of the CronJobs page with live Kubernetes data and resource operations.
"""

import datetime
import logging
from dateutil import parser

from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors
from Utils.data_formatters import parse_age_to_seconds
from Utils.resource_utils import singularize_resource_type


class CronJobsPage(BaseResourcePage):
    """
    Displays Kubernetes CronJobs with live data and resource operations.

    Features:
    1. Dynamic loading of CronJobs from the cluster
    2. Editing CronJobs with editor
    3. Deleting CronJobs (individual and batch)
    4. Resource details viewer
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.resource_type = "cronjobs"
        self.setup_page_ui()

    def setup_page_ui(self):

        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Schedule", "Suspend", "Active", "Last Schedule", "Age", ""]
        sortable_columns = [1, 2, 3, 4, 5, 6, 7]  # Name, Namespace, Schedule, Suspend, Active, Last Schedule, Age

        # Set up the base UI components
        super().setup_ui("CronJobs", headers, sortable_columns)

        # Configure column widths
        self.configure_columns()

    def configure_columns(self):

        if not self.table:
            return

        header = self.table.horizontalHeader()

        # Column specifications with optimized default widths
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 140, "stretch"),     # Name - stretch to fill remaining space
            (2, 90, "interactive"),  # Namespace
            (3, 80, "interactive"),  # Schedule
            (4, 70, "interactive"),  # Suspend
            (5, 70, "interactive"),  # Active
            (6, 70, "interactive"),  # Last Schedule
            (7, 80, "interactive"),  # Age
            (8, 40, "fixed")        # Actions
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

    def _auto_resize_columns(self, max_col_widths=None, min_col_widths=None):
        """Override to provide explicit widths for columns to let Name stretch and ensure Last Schedule has space."""
        explicit_mins = {
            1: 140,  # Name
            2: 90,   # Namespace
            3: 80,   # Schedule
            4: 70,   # Suspend
            5: 70,   # Active
            6: 100,  # Last Schedule
            7: 60,   # Age
            8: 40,   # Actions
        }
        
        if min_col_widths:
            explicit_mins.update(min_col_widths)
            
        explicit_maxes = {
            2: 150,  # Namespace
            3: 120,  # Schedule
            4: 80,   # Suspend
            5: 80,   # Active
            6: 130,  # Last Schedule
            7: 80,   # Age
        }
        
        if max_col_widths:
            explicit_maxes.update(max_col_widths)
            
        super()._auto_resize_columns(max_col_widths=explicit_maxes, min_col_widths=explicit_mins)

    def populate_resource_row(self, row, resource):
        """
        Populate a single row with CronJob data
        """
        # Set row height
        self.table.setRowHeight(row, 42)

        # Create checkbox for row selection - styling handled by BaseResourcePage
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(
            row, resource_name)
        self.table.setCellWidget(row, 0, checkbox_container)

        # Get CronJob details from pre-parsed resource fields
        schedule = resource.get("schedule", "")
        suspend = resource.get("suspend", "False")
        active = resource.get("active", "0")
        last_schedule = resource.get("last_schedule", "Never")

        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            schedule,
            suspend,
            active,
            last_schedule,
            resource["age"]
        ]

        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column

            # Handle numeric columns for sorting
            if col == 3:  # Suspend column (boolean as string)
                num = 1 if value.lower() == "true" else 0
                item = SortableTableWidgetItem(value, num)
            elif col == 4:  # Active column (numeric)
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 5:  # Last Schedule column
                item = SortableTableWidgetItem(value, parse_age_to_seconds(value))
            elif col == 6:  # Age column
                item = SortableTableWidgetItem(value, parse_age_to_seconds(value))
            else:
                item = SortableTableWidgetItem(value)

            # Set text alignment
            if col in [1, 2, 3, 4, 5, 6]:  # Suspend, Active, LastSchedule, Age
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Make cells non - editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Set special colors for Suspend column
            if col == 3:  # Suspend column
                if value.lower() == "true":
                    # Red for suspended
                    item.setForeground(QColor(AppColors.STATUS_DISCONNECTED))
                else:
                    item.setForeground(
                        QColor(AppColors.TEXT_TABLE))  # Default color
            # Set special colors for Active column
            elif col == 4:  # Active column
                try:
                    if int(value) > 0:
                        # Green for active jobs
                        item.setForeground(QColor(AppColors.STATUS_ACTIVE))
                    else:
                        # Default for inactive
                        item.setForeground(QColor(AppColors.TEXT_TABLE))
                except ValueError:
                    item.setForeground(QColor(AppColors.TEXT_TABLE))
            else:
                item.setForeground(QColor(AppColors.TEXT_TABLE))

            # Add the item to the table
            self.table.setItem(row, cell_col, item)

        # Create and add action button - styling handled by BaseResourcePage
        action_button = self._create_action_button(
            row, resource_name, resource["namespace"])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    def handle_row_click(self, row, column):
        # Skip action column
        if column == self.table.columnCount() - 1:
            return

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
