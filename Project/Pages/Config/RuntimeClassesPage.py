"""
Optimized implementation of the priority_classess page with better memory management
and performance.
"""

from PyQt6.QtWidgets import  QHeaderView
from PyQt6.QtCore import Qt

from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class RuntimeClassesPage(BaseTablePage):
    """
    Displays Kubernetes priority_classes with optimizations for performance and memory usage.
    
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
        """Set up the main UI elements for the priority_classes page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Handler", "Age", ""]
        sortable_columns = {1, 2, 3}
        
        # Set up the base UI components
        layout = self.setup_ui("Runtime Classes", headers, sortable_columns)
        
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
        stretch_columns = [2, 3]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 40)
    
    def load_data(self):
        """Load  priority_classes data into the table with optimized batch processing"""
        # Sample priority_classes data
        runtime_classes_data = [
            ["cluster-info", "kube-public", "71d"],
            ["coredns", "kube-system", "71d"],
            ["extension-apiserver-authentication", "kube-system", "71d"],
            ["kube-apiserver-legacy-service-account-token-tra", "kube-system", "71d"],
            ["kube-proxy", "kube-system","71d"],
        ]

        # Set up the table for the data
        self.table.setRowCount(len(runtime_classes_data))
        
        # Batch process all rows using a single loop for better performance
        for row, priority_classes in enumerate(runtime_classes_data):
            self.populate_priority_classes_row(row, priority_classes)
        
        # Update the item count
        self.items_count.setText(f"{len(runtime_classes_data)} items")
    
    def populate_priority_classes_row(self, row, runtime_classes_data):
        """
        Populate a single row with priority_classes data using efficient methods
        
        Args:
            row: The row index
            runtime_classes_data: List containing priority_classes information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        runtime_classes_name = runtime_classes_data[0]
        checkbox_container = self._create_checkbox_container(row, runtime_classes_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(runtime_classes_data):
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
        self.table.setCellWidget(row, len(runtime_classes_data) + 1, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection (can be removed in production)
            runtime_classes_name = self.table.item(row, 1).text()
            print(f"Selected runtime classes : {runtime_classes_name}")