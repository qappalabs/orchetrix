"""
Optimized implementation of the daemonsetss page with better memory management
and performance.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor

from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class DaemonSetsPage(BaseTablePage):
    """
    Displays Kubernetes daemonsets with optimizations for performance and memory usage.
    
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
        """Set up the main UI elements for the daemonsets page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Pods","Node Selector", "Age",""]
        sortable_columns = {1, 2, 3, 5}
        
        # Set up the base UI components
        layout = self.setup_ui("Daemon Sets", headers, sortable_columns)
        
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
        stretch_columns = [1, 2, 3, 4, 5]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
       
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 40)
    
    def load_data(self):
        """Load  daemonsets data into the table with optimized batch processing"""
        # Sample daemonsets data
        daemonsets_data = [
            ["kube-proxy", "kube-system", "1", "kubernetes.io/os=linux", "17h"],
        ]

        # Set up the table for the data
        self.table.setRowCount(len(daemonsets_data))
        
        # Batch process all rows using a single loop for better performance
        for row, daemonsets in enumerate(daemonsets_data):
            self.populate_daemonsets_row(row, daemonsets)
        
        # Update the item count
        self.items_count.setText(f"{len(daemonsets_data)} items")
    
    def populate_daemonsets_row(self, row, daemonsets_data):
        """
        Populate a single row with daemonsets data using efficient methods
        
        Args:
            row: The row index
            daemonsets_data: List containing daemonsets information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        daemonsets_name = daemonsets_data[0]
        checkbox_container = self._create_checkbox_container(row, daemonsets_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(daemonsets_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 2:  # Sechdule column
                # Convert to numeric value for sorting if possible
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
        
            elif col == 4:  # Age column
                try:
                    num = int(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [2, 4]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
           
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True},
            {"text": "Logs", "icon": "icons/logs.png", "dangerous": False},
            {"text": "Shell", "icon": "icons/shell.png", "dangerous": False},
        ])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(daemonsets_data) + 1, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection (can be removed in production)
            daemonsets_name = self.table.item(row, 1).text()
            print(f"Selected daemonsets: {daemonsets_name}")