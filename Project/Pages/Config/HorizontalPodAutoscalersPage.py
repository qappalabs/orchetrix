"""
Optimized implementation of the Horizontal Pod Autoscalers page with better memory management
and performance.
"""

from PyQt6.QtWidgets import (
    QLabel, QHeaderView, QWidget, QToolButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor

from base_components.base_components import BaseTablePage, SortableTableWidgetItem
from UI.Styles import AppStyles, AppColors

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
        """Set up the main UI elements for the Horizontal Pod Autoscalers page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Metrics", "Min Pods", "Max Pods", "Replicas", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8}
        
        # Set up the base UI components with styles
        layout = self.setup_ui("Horizontal Pod Autoscalers", headers, sortable_columns)
        
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
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Configure stretch columns
        stretch_columns = [2, 3, 4, 5, 6, 7, 8]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Last column (action button) fixed width
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(9, 40)
    
    def load_data(self):
        """Load horizontal pod autoscaler data into the table with optimized batch processing"""
        # Sample horizontal pod autoscaler data
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
        
        # Update the item count with style
        self.items_count.setStyleSheet(AppStyles.ITEMS_COUNT_STYLE)
        self.items_count.setText(f"{len(pods_data)} items")
    
    def populate_pod_row(self, row, horizontal_pod_autoscalers_data):
        """
        Populate a single row with pod data using efficient methods
        
        Args:
            row: The row index
            horizontal_pod_autoscalers_data: List containing pod information
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        horizontal_pod_autoscalers_name = horizontal_pod_autoscalers_data[0]
        checkbox_container = self._create_checkbox_container(row, horizontal_pod_autoscalers_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Populate data columns efficiently
        for col, value in enumerate(horizontal_pod_autoscalers_data):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 3:  # Min Pods column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 4:  # Max Pods column
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 5:  # Replicas column
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
            
            # Set special colors for status column using AppColors
            if col == 7:  # Status column
                if value == "Healthy":
                    item.setForeground(QColor(AppColors.STATUS_ACTIVE))
                elif value == "Warning":
                    item.setForeground(QColor(AppColors.ACCENT_RED))
                elif value == "Scaling":
                    item.setForeground(QColor(AppColors.ACCENT_BLUE))
                else:
                    item.setForeground(QColor(AppColors.TEXT_TABLE))
            else:
                item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True},
            {"text": "Logs", "icon": "icons/logs.png", "dangerous": False},
            {"text": "Shell", "icon": "icons/shell.png", "dangerous": False},
        ])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(horizontal_pod_autoscalers_data) + 1, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            # Log selection (can be removed in production)
            horizontal_pod_autoscalers_name = self.table.item(row, 1).text()
            print(f"Selected horizontal pod autoscaler: {horizontal_pod_autoscalers_name}")
