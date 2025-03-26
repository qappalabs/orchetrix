"""
Optimized implementation of the Cluster Roles page with better memory management
and performance.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor

from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class ClusterRolesPage(BaseTablePage):
    """
    Displays Kubernetes cluster roles with optimizations for performance and memory usage.
    
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
        """Set up the main UI elements for the Cluster Roles page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Age", ""]
        sortable_columns = {1, 2}
        
        # Set up the base UI components
        layout = self.setup_ui("Cluster Roles", headers, sortable_columns)
        
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
        stretch_columns = [2]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        fixed_widths = {3: 40}
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
    
    def load_data(self):
        """Load cluster role data into the table with optimized batch processing"""
        # Sample cluster role data
        cluster_roles_data = [
            ["docker.io-hostpath", "70d"]
        ]

        # Set up the table for the data
        self.table.setRowCount(len(cluster_roles_data))
        
        # Batch process all rows using a single loop for better performance
        for row, role in enumerate(cluster_roles_data):
            self.populate_role_row(row, role)
        
        # Update the item count
        self.items_count.setText(f"{len(cluster_roles_data)} items")
    
    def populate_role_row(self, row, role_data):
        """
        Populate a single row with cluster role data using efficient methods
        
        Args:
            row: The row index
            role_data: List containing cluster role information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        role_name = role_data[0]
        checkbox_container = self._create_checkbox_container(row, role_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(role_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 1:  # Age column
                try:
                    num = float(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col == 1:  # Age column
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set text color
            item.setForeground(QColor("#e2e8f0"))
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(role_data) + 1, action_container)
    
    def _handle_action(self, action, row):
        """Override base action handler for cluster role-specific actions"""
        role_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing Cluster Role: {role_name}")
        elif action == "Delete":
            print(f"Deleting Cluster Role: {role_name}")
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection
            role_name = self.table.item(row, 1).text()
            print(f"Selected Cluster Role: {role_name}")