
"""
Dynamic implementation of the Deployments page with live Kubernetes data and resource operations.
Status display shows color-coded status, including multiple status conditions in different colors.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles

class MultiColorStatusLabel(QWidget):
    """Widget that displays status conditions with different colors in a single label."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)  # Space between different status text
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Make sure this widget has a transparent background
        self.setStyleSheet("background-color: transparent;")
    
    def set_status_text(self, status_text):
        """Set status text, parsing multiple statuses if present."""
        # Clear any existing labels
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # If no status text, show an empty label
        if not status_text:
            label = QLabel("<none>")
            label.setStyleSheet(f"color: {QColor(AppColors.TEXT_TABLE).name()};")
            self.layout.addWidget(label)
            return
            
        # Parse status text - split by space
        statuses = status_text.split()
        
        for status in statuses:
            label = QLabel(status)
            
            # Set color based on status type
            if status == "Available":
                label.setStyleSheet(f"color: {QColor(AppColors.STATUS_ACTIVE).name()};")
            elif status == "Progressing":
                label.setStyleSheet(f"color: {QColor(AppColors.STATUS_PROGRESS).name()};")
            else:
                label.setStyleSheet(f"color: {QColor(AppColors.TEXT_TABLE).name()};")
                
            self.layout.addWidget(label)

class DeploymentsPage(BaseResourcePage):
    """
    Displays Kubernetes Deployments with live data and resource operations.
    
    Features:
    1. Dynamic loading of Deployments from the cluster
    2. Editing Deployments with editor
    3. Deleting Deployments (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "deployments"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Deployments page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Pods", "Replicas", "Age", "Conditions", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6}
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Deployments", headers, sortable_columns)
        
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
        
        # Use stretch mode for most columns for better responsive layout
        stretch_columns = [1, 2, 3, 4, 5, 6]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Set last column (action) as fixed
        action_col = 7
        self.table.horizontalHeader().setSectionResizeMode(action_col, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(action_col, 40)
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with Deployment data
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
        
        # Get pod status
        pods_str = "0/0"
        if raw_data:
            status = raw_data.get("status", {})
            available_replicas = status.get("availableReplicas", 0)
            replicas = status.get("replicas", 0)
            pods_str = f"{available_replicas}/{replicas}"
        
        # Get replicas count
        replicas_str = "0"
        if raw_data:
            spec = raw_data.get("spec", {})
            replicas_str = str(spec.get("replicas", 0))
        
        # Get conditions
        conditions_str = ""
        if raw_data:
            status = raw_data.get("status", {})
            conditions = status.get("conditions", [])
            condition_types = []
            for condition in conditions:
                if condition.get("status") == "True":
                    condition_types.append(condition.get("type", ""))
            conditions_str = " ".join(condition_types)
        
        # Parse age correctly from metadata
        age_str = resource["age"]
        if raw_data:
            metadata = raw_data.get("metadata", {})
            creation_timestamp = metadata.get("creationTimestamp")
            if creation_timestamp:
                import datetime
                from dateutil import parser
                try:
                    # Parse creation time and calculate age
                    creation_time = parser.parse(creation_timestamp)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    delta = now - creation_time
                    
                    # Format age string
                    days = delta.days
                    seconds = delta.seconds
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    
                    if days > 0:
                        age_str = f"{days}d"
                    elif hours > 0:
                        age_str = f"{hours}h"
                    else:
                        age_str = f"{minutes}m"
                except Exception:
                    # Keep the original age if parsing fails
                    pass

        # Prepare data columns - all except Conditions
        columns = [
            resource["name"],
            resource["namespace"],
            pods_str,
            replicas_str,
            age_str
        ]
        
        # Add normal columns to table (all except Conditions)
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 2:  # Pods column
                try:
                    available, total = value.split("/")
                    # Calculate as percentage for better sorting
                    pods_value = (float(available) / float(total)) * 100 if float(total) > 0 else 0
                except (ValueError, IndexError, ZeroDivisionError):
                    pods_value = 0
                item = SortableTableWidgetItem(value, pods_value)
            elif col == 3:  # Replicas column
                try:
                    replicas_value = float(value)
                except ValueError:
                    replicas_value = 0
                item = SortableTableWidgetItem(value, replicas_value)
            elif col == 4:  # Age column
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
            if col in [2, 3, 4]:  # Pods, Replicas, Age
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set default color for regular columns
            item.setForeground(QColor(AppColors.TEXT_TABLE))
            
            # Add the item to the table
            self.table.setItem(row, cell_col, item)
        
        # Add the Conditions column as a special multi-color widget (cell 6)
        conditions_widget = MultiColorStatusLabel()
        conditions_widget.set_status_text(conditions_str)
        self.table.setCellWidget(row, 6, conditions_widget)
        
        # Create and add action button with only Edit and Delete options
        action_button = self._create_action_button(row, resource_name, resource["namespace"])
        action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        action_container = self._create_action_container(row, action_button)
        action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        self.table.setCellWidget(row, 7, action_container)
    

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