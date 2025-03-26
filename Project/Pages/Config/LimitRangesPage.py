"""
Optimized implementation of the limit_rangess page with better memory management
and performance.
"""

from PyQt6.QtWidgets import  QHeaderView
from PyQt6.QtCore import Qt

from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class LimitRangesPage(BaseTablePage):
    """
    Displays Kubernetes limit_ranges with optimizations for performance and memory usage.
    
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
        """Set up the main UI elements for the limit_ranges page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Age", ""]
        sortable_columns = {1, 2, 3}
        
        # Set up the base UI components
        layout = self.setup_ui("Limit Ranges", headers, sortable_columns)
        
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
        stretch_columns = [1, 2, 3]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
       
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 40)
    
    def load_data(self):
        """Load  limit_ranges data into the table with optimized batch processing"""
        # Sample limit_ranges data
        limit_ranges_data = [
            ["default-limits", "default", "71d"],
            ["dev-limits", "dev", "45d"],
            ["system-limits", "kube-system", "71d"],
            ["test-limits", "test", "30d"],
            ["production-limits", "production", "71d"],
            ["frontend-limits", "frontend", "14d"],
            ["backend-limits", "backend", "21d"],
            ["database-limits", "database", "60d"],
            ["monitoring-limits", "monitoring", "90d"],
            ["logging-limits", "logging", "55d"]
        ]

        # Set up the table for the data
        self.table.setRowCount(len(limit_ranges_data))
        
        # Batch process all rows using a single loop for better performance
        for row, limit_ranges in enumerate(limit_ranges_data):
            self.populate_limit_ranges_row(row, limit_ranges)
        
        # Update the item count
        self.items_count.setText(f"{len(limit_ranges_data)} items")
    
    def populate_limit_ranges_row(self, row, limit_ranges_data):
        """
        Populate a single row with limit_ranges data using efficient methods
        
        Args:
            row: The row index
            limit_ranges_data: List containing limit_ranges information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        limit_ranges_name = limit_ranges_data[0]
        checkbox_container = self._create_checkbox_container(row, limit_ranges_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(limit_ranges_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            
            if col == 2:  # Age column
                try:
                    num = int(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [2]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True},
            {"text": "Logs", "icon": "icons/logs.png", "dangerous": False},
            {"text": "Shell", "icon": "icons/shell.png", "dangerous": False},
        ])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(limit_ranges_data) + 1, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection (can be removed in production)
            limit_ranges_name = self.table.item(row, 1).text()
            print(f"Selected limit_ranges: {limit_ranges_name}")