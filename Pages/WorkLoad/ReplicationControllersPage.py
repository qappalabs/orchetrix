"""
Dynamic implementation of the ReplicationControllers page with live Kubernetes data and resource operations.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles

class ReplicaControllersPage(BaseResourcePage):
    """
    Displays Kubernetes ReplicationControllers with live data and resource operations.
    
    Features:
    1. Dynamic loading of ReplicationControllers from the cluster
    2. Editing ReplicationControllers with editor
    3. Deleting ReplicationControllers (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "replicationcontrollers"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the ReplicationControllers page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Replicas", "Desired Replicas", "Selector", ""]
        sortable_columns = {1, 2, 3, 4, 5}
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Replication Controllers", headers, sortable_columns)
        
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
        
        # Configure stretch columns
        stretch_columns = [1, 2, 3, 4, 5]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width column for action
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 40)
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with ReplicationController data
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
        
        # Get replicas info
        replicas = "0"
        desired_replicas = "0"
        selector = ""
        
        if raw_data:
            spec = raw_data.get("spec", {})
            status = raw_data.get("status", {})
            
            replicas = str(status.get("replicas", 0))
            desired_replicas = str(spec.get("replicas", 0))
            
            # Get selector as string
            selectors = spec.get("selector", {})
            selector = ", ".join([f"{k}={v}" for k, v in selectors.items()])
            if not selector:
                selector = "<none>"
        
        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            replicas,
            desired_replicas,
            selector
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 2 or col == 3:  # Replicas, DesiredReplicas columns
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            
            # Set text alignment
            if col == 2 or col == 3:  # Replicas, DesiredReplicas
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set default text color
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