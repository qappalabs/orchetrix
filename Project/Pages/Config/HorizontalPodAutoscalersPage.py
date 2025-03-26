"""
Optimized implementation of the Pods page with better memory management
and performance.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor

from base_components.base_components import BaseTablePage, SortableTableWidgetItem

class HorizontalPodAutoscalersPage(BaseTablePage):
    """
    Displays Kubernetes horizontal pod autoscalers with optimizations for performance and memory usage.
    
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
        """Set up the main UI elements for the Pods page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Metrics", "Min Pods", "Max Pods", "Replicas", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7,8}
        
        # Set up the base UI components
        layout = self.setup_ui("Horizontal Pod Autoscalers", headers, sortable_columns)
        
        # Configure column widths
        self.configure_columns()
        
        # Connect the row click handler
        self.table.cellClicked.connect(self.handle_row_click)
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Column 0: Checkbox (fixed width) - already set in base class

        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Configure stretch columns
        stretch_columns = [2, 3, 4, 5, 6, 7, 8]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(9, 40)
    
    def load_data(self):
        """Load horizontal_pod_auotscalers_name data into the table with optimized batch processing"""
        # Sample horizontal_pod_auotscalers_name data
        pods_data = [
            ["default-quota", "default", "CPU/80%", "1", "10", "3", "71d", "Healthy"],
            ["dev-quota", "dev", "Memory/70%", "2", "8", "5", "45d", "Healthy"],
            ["system-quota", "kube-system", "CPU/60%", "3", "12", "6", "71d", "Scaling"],
            ["test-quota", "test", "CPU/90%", "1", "5", "4", "30d", "Healthy"],
            ["production-quota", "production", "Memory/85%", "5", "20", "10", "71d", "Warning"]
        ]

        # Set up the table for the data
        self.table.setRowCount(len(pods_data))
        
        # Batch process all rows using a single loop for better performance
        for row, pod in enumerate(pods_data):
            self.populate_pod_row(row, pod)
        
        # Update the item count
        self.items_count.setText(f"{len(pods_data)} items")
    
    def populate_pod_row(self, row, horizontal_pod_auotscalers_data):
        """
        Populate a single row with pod data using efficient methods
        
        Args:
            row: The row index
            horizontal_pod_auotscalers_data: List containing pod information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        horizontal_pod_auotscalers_name = horizontal_pod_auotscalers_data[0]
        checkbox_container = self._create_checkbox_container(row, horizontal_pod_auotscalers_name)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(horizontal_pod_auotscalers_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
        
            if col == 3:  # Min pods column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)

            elif col == 4:  # Max pods column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)

            elif col == 5:  # Replicas pods column
                try:
                    num = int(value)
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
            if col in [2, 3, 4, 5, 6, 7]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set special colors for status column
            if col == 7 and value == "Healthy":
                item.setForeground(QColor("#4CAF50"))

            elif col == 7 and value == "Warning":
                item.setForeground(QColor("#d32e1a"))
            
            elif col == 7 and value == "Scaling":
                item.setForeground(QColor("#0d91b1"))  # Blue

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
        self.table.setCellWidget(row, len(horizontal_pod_auotscalers_data) + 1, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection (can be removed in production)
            horizontal_pod_auotscalers_name = self.table.item(row, 1).text()
            print(f"Selected horizontal_pod_auotscalers_name: {horizontal_pod_auotscalers_name}")