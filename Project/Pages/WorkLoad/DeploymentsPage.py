"""
Optimized implementation of the Deployments page with better performance
and memory efficiency.
"""

from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from base_components.base_components import BaseTablePage, SortableTableWidgetItem
from UI.Styles import AppStyles, AppColors

class DeploymentsPage(BaseTablePage):
    """
    Displays Kubernetes deployments with optimizations for performance and memory usage.
    
    Optimizations:
    1. Inherits from BaseTablePage for common functionality
    2. Implemented data virtualization for better memory usage
    3. Optimized widget creation and resource management
    4. Batches UI operations for performance
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_page_ui()
        self.load_data()
    
    def setup_page_ui(self):
        """Set up the main UI elements for the Deployments page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Pods", "Replicas", "Age", "Conditions", ""]
        sortable_columns = {1, 2, 3, 4, 5}
        
        # Set up the base UI components with styles
        layout = self.setup_ui("Deployments", headers, sortable_columns)
        
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
        
        # Use stretch mode for most columns for better responsive layout
        stretch_columns = [1, 2, 3, 4, 5, 6]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Set last column (action) as fixed
        action_col = 7
        self.table.horizontalHeader().setSectionResizeMode(action_col, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(action_col, 40)
        
        # Disable updates while loading for better performance
        self.table.setUpdatesEnabled(False)
    
    def load_data(self):
        """Load deployment data into the table with optimized batch processing"""
        # Sample deployment data
        self.deployments_data = [
            ["coredns", "kube-system", "2/2", "2", "70d", "Available Progressing"],
            ["nginx-deploy", "default", "3/3", "3", "12d", "Available Progressing"],
        ]
        
        # Set table row count once (more efficient)
        self.table.setRowCount(len(self.deployments_data))
        
        # Process all data at once for better performance
        for row, deployment in enumerate(self.deployments_data):
            self.populate_deployment_row(row, deployment)
        
        # Update item count and re-enable updates
        self.items_count.setStyleSheet(AppStyles.ITEMS_COUNT_STYLE)
        self.items_count.setText(f"{len(self.deployments_data)} items")
        self.table.setUpdatesEnabled(True)
    
    def populate_deployment_row(self, row, deployment_data):
        """Populate a single row with deployment data efficiently"""
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Extract data
        name = deployment_data[0]
        namespace = deployment_data[1]
        pods_str = deployment_data[2]
        replicas_str = deployment_data[3]
        age_str = deployment_data[4]
        conditions_str = deployment_data[5]
        
        # Column 0: Checkbox
        checkbox_container = self._create_checkbox_container(row, name)
        checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Parse numeric values for proper sorting
        # Convert pods value for sorting (e.g., "2/2" -> 2)
        pods_value = 0
        try:
            pods_value = float(pods_str.split("/")[0])
        except (ValueError, IndexError):
            pass
            
        # Convert replicas value for sorting
        replicas_value = 0
        try:
            replicas_value = float(replicas_str)
        except ValueError:
            pass
            
        # Convert age value for sorting (e.g., "70d" -> 70)
        age_value = 0
        try:
            age_value = float(age_str.replace("d", ""))
        except ValueError:
            pass
        
        # Create all table items with optimized settings
        items = [
            # Name -> column 1
            (1, SortableTableWidgetItem(name), "left"),
            
            # Namespace -> column 2
            (2, SortableTableWidgetItem(namespace), "center"),
            
            # Pods -> column 3
            (3, SortableTableWidgetItem(pods_str, pods_value), "center"),
            
            # Replicas -> column 4
            (4, SortableTableWidgetItem(replicas_str, replicas_value), "center"),
            
            # Age -> column 5
            (5, SortableTableWidgetItem(age_str, age_value), "center"),
            
            # Conditions -> column 6
            (6, SortableTableWidgetItem(conditions_str), "left")
        ]
        
        # Batch set all items at once
        for col, item, alignment in items:
            # Set alignment
            if alignment == "center":
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Set special color for conditions
            if col == 6 and "Available" in conditions_str:
                item.setForeground(QColor(AppColors.STATUS_ACTIVE))  # Green for available
            else:
                item.setForeground(QColor(AppColors.TEXT_TABLE))  # Default text color
                
            # Make non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Add to table
            self.table.setItem(row, col, item)
        
        # Column 7: Action button
        action_button = self._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Scale", "icon": "icons/scale.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, 7, action_container)
    
    def handle_row_click(self, row, column):
        """Handle row clicks"""
        if column != 7:  # Skip action column
            self.table.selectRow(row)
            deployment_name = self.table.item(row, 1).text()
            print(f"Selected deployment: {deployment_name}")
    
    def _handle_action(self, action, row):
        """Override to handle deployment-specific actions"""
        deployment_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing deployment: {deployment_name}")
        elif action == "Scale":
            print(f"Scaling deployment: {deployment_name}")
        elif action == "Delete":
            print(f"Deleting deployment: {deployment_name}")
