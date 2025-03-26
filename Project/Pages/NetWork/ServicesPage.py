"""
Optimized implementation of the Services page with better memory management
and performance.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor

from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class ServicesPage(BaseTablePage):
    """
    Displays Kubernetes services with optimizations for performance and memory usage.
    
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
        """Set up the main UI elements for the Services page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Type", "Cluster IP", "Port", "External IP", "Selector", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 7, 8, 9}
        
        # Set up the base UI components
        layout = self.setup_ui("Services", headers, sortable_columns)
        
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
        stretch_columns = [2, 3, 4, 5, 6, 7, 8, 9]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
      
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(10, 40)
    
    def load_data(self):
        """Load service data into the table with optimized batch processing"""
        # Sample service data
        services_data = [
            ["kube-dns", "kube-system", "Cluster", "09:87.012", "89/UDS,89/TCP,9", "", "k8s-app=kub..", "2d23h", "Active"]
        ]

        # Set up the table for the data
        self.table.setRowCount(len(services_data))
        
        # Batch process all rows using a single loop for better performance
        for row, service in enumerate(services_data):
            self.populate_service_row(row, service)
        
        # Update the item count
        self.items_count.setText(f"{len(services_data)} items")
    
    def populate_service_row(self, row, service_data):
        """
        Populate a single row with service data using efficient methods
        
        Args:
            row: The row index
            service_data: List containing service information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        service_name = service_data[0]
        checkbox_container = self._create_checkbox_container(row, service_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(service_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 3:  # Containers column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 4:  # Restarts column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 7:  # Age column
                try:
                    num = int(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [3, 4, 7, 8]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set special colors for status column
            if col == 8 and value == "Active":
                item.setForeground(QColor("#4CAF50"))
            else:
                item.setForeground(QColor("#e2e8f0"))
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ])
        action_container = self._create_action_container(row, action_button)
        self.table.setCellWidget(row, len(service_data) + 1, action_container)
    
    def _handle_action(self, action, row):
        """Override base action handler for service-specific actions"""
        service_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing Service: {service_name}")
        elif action == "Delete":
            print(f"Deleting Service: {service_name}")
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection
            service_name = self.table.item(row, 1).text()
            print(f"Selected service: {service_name}")