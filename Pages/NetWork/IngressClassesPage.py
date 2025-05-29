from PyQt6.QtWidgets import (
    QHeaderView, QPushButton, QLabel, QVBoxLayout, QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppStyles, AppColors

class IngressClassesPage(BaseResourcePage):
    """
    Displays Kubernetes IngressClasses with live data and resource operations.
    
    Features:
    1. Dynamic loading of IngressClasses from the cluster
    2. Editing IngressClasses with terminal editor
    3. Deleting IngressClasses (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "ingressclasses"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the IngressClasses page"""
        # Define headers and sortable columns - KEEP ORIGINAL
        headers = ["", "Name", "Controller", "API Group", "Scope", "Kind", "Age", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6}
        
        # Set up the base UI components
        layout = super().setup_ui("Ingress Classes", headers, sortable_columns)
        
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
        
        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Configure stretch columns
        stretch_columns = [2, 3, 4, 5, 6]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 40)
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with IngressClass data extracted from raw_data
        """
        # Set row height once
        self.table.setRowHeight(row, 40)
        
        # Create checkbox for row selection
        resource_name = resource["name"]
        checkbox_container = self._create_checkbox_container(row, resource_name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Extract data from raw_data
        raw_data = resource.get("raw_data", {})
        spec = raw_data.get("spec", {})
        metadata = raw_data.get("metadata", {})
        
        # Get controller
        controller = spec.get("controller", "<none>")
        
        # Get API group from apiVersion
        api_version = raw_data.get("apiVersion", "networking.k8s.io/v1")
        if "/" in api_version:
            api_group = api_version.split("/")[0]
        else:
            api_group = "core"
        
        # Get scope (IngressClasses are always Cluster scoped)
        scope = "Cluster"
        
        # Get kind
        kind = raw_data.get("kind", "IngressClass")
        
        # Prepare data columns - MATCH ORIGINAL HEADERS
        columns = [
            resource["name"],      # Name
            controller,            # Controller  
            api_group,            # API Group
            scope,                # Scope
            kind,                 # Kind
            resource["age"]       # Age
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 5:  # Age column
                try:
                    # Extract numeric part from age string
                    if 'd' in value:
                        num = int(value.replace('d', ''))
                    elif 'h' in value:
                        num = int(value.replace('h', '')) / 24  # Convert to fraction of day
                    elif 'm' in value:
                        num = int(value.replace('m', '')) / (24 * 60)  # Convert to fraction of day
                    else:
                        num = 0
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
            
            # Add item to table
            self.table.setItem(row, cell_col, item)
        
        # Create and add action button
        action_button = self._create_action_button(row, resource["name"], resource.get("namespace", ""))
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, len(columns) + 1, action_container)

    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
            # Get resource details
            resource_name = None
            
            # Get the resource name
            if self.table.item(row, 1) is not None:
                resource_name = self.table.item(row, 1).text()
            
            # Show detail view
            if resource_name:
                # Find the ClusterView instance
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    # IngressClasses are cluster-scoped, so no namespace
                    parent.detail_manager.show_detail("ingressclass", resource_name, None)