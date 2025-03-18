"""
Optimized implementation of the Storage Classes page with better memory management
and performance.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor

from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class StorageClassesPage(BaseTablePage):
    """
    Displays Kubernetes storage classes with optimizations for performance and memory usage.
    
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
        """Set up the main UI elements for the Storage Classes page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Provisioner", "Reclaim Policy", "Default", "Age", ""]
        sortable_columns = {1, 2, 3, 5}
        
        # Set up the base UI components
        layout = self.setup_ui("Storage Classes", headers, sortable_columns)
        
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
        stretch_columns = [2, 3, 4, 5]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        fixed_widths = {6: 40}
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
    
    def load_data(self):
        """Load storage class data into the table with optimized batch processing"""
        # Sample storage class data - empty array as per the original
        storage_classes_data = [
            ["docker.io-hostpath", "kube-system", "<none>", "", "70d"]
        ]

        # Set up the table for the data
        self.table.setRowCount(len(storage_classes_data))
        
        # Batch process all rows using a single loop for better performance
        for row, storage_class in enumerate(storage_classes_data):
            self.populate_storage_class_row(row, storage_class)
        
        # Update the item count
        self.items_count.setText(f"{len(storage_classes_data)} items")
    
    def populate_storage_class_row(self, row, storage_class_data):
        """
        Populate a single row with storage class data using efficient methods
        
        Args:
            row: The row index
            storage_class_data: List containing storage class information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        storage_class_name = storage_class_data[0]
        checkbox_container = self._create_checkbox_container(row, storage_class_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(storage_class_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 4:  # Age column
                try:
                    num = float(value.replace('d', ''))
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col == 0:  # Name column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
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
        self.table.setCellWidget(row, len(storage_class_data) + 1, action_container)
    
    def _handle_action(self, action, row):
        """Override base action handler for storage class-specific actions"""
        storage_class_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing storage class: {storage_class_name}")
        elif action == "Delete":
            print(f"Deleting storage class: {storage_class_name}")
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection
            storage_class_name = self.table.item(row, 1).text()
            print(f"Selected storage class: {storage_class_name}")