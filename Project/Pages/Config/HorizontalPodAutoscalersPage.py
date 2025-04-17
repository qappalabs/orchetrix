"""
Dynamic implementation of the Horizontal Pod Autoscalers page with live Kubernetes data.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles

class HorizontalPodAutoscalersPage(BaseResourcePage):
    """
    Displays Kubernetes Horizontal Pod Autoscalers with live data and resource operations.
    
    Features:
    1. Dynamic loading of HPAs from the cluster
    2. Editing HPAs with editor
    3. Deleting HPAs (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "horizontalpodautoscalers"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the HPAs page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Metrics", "Min Pods", "Max Pods", "Replicas", "Age", "Status", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8}
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Horizontal Pod Autoscalers", headers, sortable_columns)
        
        # Apply table style
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure column widths
        self.configure_columns()
        
        # Add delete selected button
        self._add_delete_selected_button()
        
    def _add_delete_selected_button(self):
        """Add a button to delete selected resources."""
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_resources)
        
        # Find the header layout
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "Refresh":
                        # Insert before the refresh button
                        item.layout().insertWidget(item.layout().count() - 1, delete_btn)
                        break
    
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Column 0: Checkbox (fixed width) - already set in base class
        
        # Configure column 1 (Name) to stretch
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Configure stretch columns
        stretch_columns = [2, 3, 4, 5, 6, 7, 8]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Last column (action button) fixed width
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(9, 40)
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with HPA data
        """
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            resource.get("metrics", "None"),
            resource.get("min_pods", "1"),
            resource.get("max_pods", "10"),
            resource.get("current_replicas", "0"),
            resource["age"],
            resource.get("status", "Unknown")
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
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
            if col in [3, 4, 5, 6]:
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
            
            # Add item to table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 1, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)