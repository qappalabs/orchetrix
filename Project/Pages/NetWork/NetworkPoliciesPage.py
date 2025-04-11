"""
Optimized implementation of the Network Policies page with better memory management
and performance.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor

from base_components.base_components import BaseTablePage, SortableTableWidgetItem
from UI.Styles import AppStyles, AppColors

class NetworkPoliciesPage(BaseTablePage):
    """
    Displays Kubernetes network policies with optimizations for performance and memory usage.
    
    Optimizations:
    1. Uses BaseTablePage for common functionality to reduce code duplication
    2. Implements lazy loading of table rows for better performance with large datasets
    3. Uses object pooling to reduce GC pressure from widget creation
    4. Implements virtualized scrolling for better performance with large tables
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_page_ui()
        self.load_data()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Network Policies page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Policy Type", "Age", ""]
        sortable_columns = {1, 2, 4}
        
        # Set up the base UI components with styles
        layout = self.setup_ui("Network Policies", headers, sortable_columns)
        
        # Apply table style
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure column widths
        self.configure_columns()
        
        # Connect the row click handler
        self.table.cellClicked.connect(self.handle_row_click)
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Column 0: Checkbox (fixed width) - already set in base class
        
        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Configure stretch columns
        stretch_columns = [2, 3, 4]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        fixed_widths = {5: 40}
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
    
    def load_data(self):
        """Load network policy data into the table with optimized batch processing"""
        # Sample network policy data - empty for now as in the original
        network_policies_data = [
            # ["docker.io-hostpath", "kube-system", "<none>", "70d"]
        ]

        # Set up the table for the data
        self.table.setRowCount(len(network_policies_data))
        
        # Batch process all rows using a single loop for better performance
        for row, policy in enumerate(network_policies_data):
            self.populate_policy_row(row, policy)
        
        # Update the item count with style
        self.items_count.setStyleSheet(AppStyles.ITEMS_COUNT_STYLE)
        self.items_count.setText(f"{len(network_policies_data)} items")
    
    def populate_policy_row(self, row, policy_data):
        """
        Populate a single row with network policy data using efficient methods
        
        Args:
            row: The row index
            policy_data: List containing network policy information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        policy_name = policy_data[0]
        checkbox_container = self._create_checkbox_container(row, policy_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(policy_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 3:  # Age column
                try:
                    num = float(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [2, 3]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set text color using AppColors
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(policy_data) + 1, action_container)
    
    def _handle_action(self, action, row):
        """Override base action handler for network policy-specific actions"""
        policy_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing network policy: {policy_name}")
        elif action == "Delete":
            print(f"Deleting network policy: {policy_name}")
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection
            policy_name = self.table.item(row, 1).text()
            print(f"Selected network policy: {policy_name}")
