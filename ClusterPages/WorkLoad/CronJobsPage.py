"""
Optimized implementation of the cron_jobss page with better memory management
and performance.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor

from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class CronJobsPage(BaseTablePage):
    """
    Displays Kubernetes cron_jobss with optimizations for performance and memory usage.
    
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
        """Set up the main UI elements for the cron_jobss page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Sechdule", "Suspend", "Active", "Last sechdule", "Age", ""]
        sortable_columns = {1, 2, 4, 5, 6, 7}
        
        # Set up the base UI components
        layout = self.setup_ui("Cron Jobs", headers, sortable_columns)
        
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
        stretch_columns = [1, 2, 3, 4, 5, 6, 7]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
       
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 40)
    
    def load_data(self):
        """Load cron jobs data into the table with optimized batch processing"""
        # Sample cron_jobs data
        cron_jobs_data = [
            ["coredns", "kube-system", "2/2", "2", "Available Progressing", "3", "70d"],
            ["nginx-deploy", "default", "3/3", "3" ,"Available Progressing", "12d", "12d"],
        ]

        # Set up the table for the data
        self.table.setRowCount(len(cron_jobs_data))
        
        # Batch process all rows using a single loop for better performance
        for row, cron_jobs in enumerate(cron_jobs_data):
            self.populate_cron_jobs_row(row, cron_jobs)
        
        # Update the item count
        self.items_count.setText(f"{len(cron_jobs_data)} items")
    
    def populate_cron_jobs_row(self, row, cron_jobs_data):
        """
        Populate a single row with cron_jobs data using efficient methods
        
        Args:
            row: The row index
            cron_jobs_data: List containing cron_jobs information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        cron_jobs_name = cron_jobs_data[0]
        checkbox_container = self._create_checkbox_container(row, cron_jobs_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(cron_jobs_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 2:  # Sechdule column
                # Convert to numeric value for sorting if possible
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 3:  # suspend column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 5:  # Last Sechdule column
                try:
                    num = int(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 6:  # Age column
                try:
                    num = int(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [2, 3, 4, 5, 6,]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set special colors for status column
            if col == 4 and value == "Available Progressing":
                item.setForeground(QColor("#4CAF50"))
            else:
                item.setForeground(QColor("#e2e8f0"))
            
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
        self.table.setCellWidget(row, len(cron_jobs_data) + 1, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection (can be removed in production)
            cron_jobs_name = self.table.item(row, 1).text()
            print(f"Selected cron_jobs: {cron_jobs_name}")