"""
Dynamic implementation of the Jobs page with live Kubernetes data and resource operations.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles

class JobsPage(BaseResourcePage):
    """
    Displays Kubernetes Jobs with live data and resource operations.
    
    Features:
    1. Dynamic loading of Jobs from the cluster
    2. Editing Jobs with editor
    3. Deleting Jobs (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "jobs"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Jobs page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Completions", "Age", "Conditions", ""]
        sortable_columns = {1, 2, 3, 4, 5}
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Jobs", headers, sortable_columns)
        
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
        
    # def configure_columns(self):
    #     """Configure column widths and behaviors"""
    #     # Column 0: Checkbox (fixed width) - already set in base class
        
    #     # Configure stretch columns
    #     stretch_columns = [1, 2, 3, 4, 5]
    #     for col in stretch_columns:
    #         self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
    #     # Fixed width column for action
    #     self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
    #     self.table.setColumnWidth(6, 40)
    
    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
        
        header = self.table.horizontalHeader()
        
        # Column specifications with optimized default widths
        column_specs = [
            (0, 40, "fixed"),        # Checkbox
            (1, 140, "interactive"), # Name
            (2, 90, "interactive"),  # Namespace
            (3, 80, "interactive"),  # Completions
            (4, 70, "interactive"),  # Age
            (5, 80, "stretch"),      # Conditions - stretch to fill remaining space
            (6, 40, "fixed")        # Actions
        ]
        
        # Apply column configuration
        for col_index, default_width, resize_type in column_specs:
            if col_index < self.table.columnCount():
                if resize_type == "fixed":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "interactive":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)
                    self.table.setColumnWidth(col_index, default_width)
                elif resize_type == "stretch":
                    header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
                    self.table.setColumnWidth(col_index, default_width)
        
        # Ensure full width utilization after configuration
        QTimer.singleShot(100, self._ensure_full_width_utilization)


    def populate_resource_row(self, row, resource):
        """
        Populate a single row with Job data
        """
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Extract additional data from the raw_data field if available
        raw_data = resource.get("raw_data", {})
        
        # Get job details
        completions = "0/1"
        conditions = ""
        
        if raw_data:
            spec = raw_data.get("spec", {})
            status = raw_data.get("status", {})
            
            # Get completions count
            successful = status.get("succeeded", 0)
            parallelism = spec.get("completions", 1)
            completions = f"{successful}/{parallelism}"
            
            # Get conditions
            condition_list = status.get("conditions", [])
            condition_types = []
            for condition in condition_list:
                if condition.get("status") == "True":
                    condition_types.append(condition.get("type", ""))
            conditions = " ".join(condition_types)
        
        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            completions,
            resource["age"],
            conditions
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 2:  # Completions column
                try:
                    successful, total = value.split("/")
                    completion_value = float(successful) / float(total) if float(total) > 0 else 0
                except (ValueError, ZeroDivisionError):
                    completion_value = 0
                item = SortableTableWidgetItem(value, completion_value)
            elif col == 3:  # Age column
                try:
                    # Convert age string (like "5d" or "2h") to minutes for sorting
                    if 'd' in value:
                        age_value = int(value.replace('d', '')) * 1440  # days to minutes
                    elif 'h' in value:
                        age_value = int(value.replace('h', '')) * 60  # hours to minutes
                    elif 'm' in value:
                        age_value = int(value.replace('m', ''))  # minutes
                    else:
                        age_value = 0
                except ValueError:
                    age_value = 0
                item = SortableTableWidgetItem(value, age_value)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col in [1, 2, 3]:  # Completions, Age
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set special colors for Conditions column
            if col == 4:  # Conditions column
                if "Complete" in value:
                    item.setForeground(QColor(AppColors.STATUS_ACTIVE))  # Green for Complete
                elif "Failed" in value:
                    item.setForeground(QColor(AppColors.STATUS_DISCONNECTED))  # Red for Failed
                else:
                    item.setForeground(QColor(AppColors.TEXT_TABLE))  # Default text color
            else:
                item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button with only Edit and Delete options
        action_button = self._create_action_button(row, resource_name, resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    # def handle_row_click(self, row, column):
    #     """Handle row selection when a table cell is clicked"""
    #     if column != self.table.columnCount() - 1:  # Skip action column
    #         # Select the row
    #         self.table.selectRow(row)

    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
            # Get resource details
            resource_name = None
            namespace = None
            
            # Get the resource name
            if self.table.item(row, 1) is not None:
                resource_name = self.table.item(row, 1).text()
            
            # Get namespace if applicable
            if self.table.item(row, 2) is not None:
                namespace = self.table.item(row, 2).text()
            
            # Show detail view
            if resource_name:
                # Find the ClusterView instance
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    # Get singular resource type
                    resource_type = self.resource_type
                    if resource_type.endswith('s'):
                        resource_type = resource_type[:-1]
                    
                    parent.detail_manager.show_detail(resource_type, resource_name, namespace)