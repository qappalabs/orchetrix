"""
Dynamic implementation of the Definitions page with live Kubernetes data.
"""

from PyQt6.QtWidgets import (QHeaderView, QWidget, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
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
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure column widths
        self.configure_columns()
        
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Column 0: Checkbox (fixed width) - already set in base class
        
        # Column 1: Resource (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Configure stretch columns
        stretch_columns = [2, 3, 4, 5]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 40)
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with CustomResourceDefinition data from live Kubernetes resources
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
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
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 1, action_container)
    
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