"""
Dynamic implementation of the CronJobs page with live Kubernetes data and resource operations.
"""

from PyQt6.QtWidgets import QHeaderView, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles

class CronJobsPage(BaseResourcePage):
    """
    Displays Kubernetes CronJobs with live data and resource operations.
    
    Features:
    1. Dynamic loading of CronJobs from the cluster
    2. Editing CronJobs with editor
    3. Deleting CronJobs (individual and batch)
    4. Resource details viewer
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "cronjobs"
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the CronJobs page"""
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Schedule", "Suspend", "Active", "Last Schedule", "Age", ""]
        sortable_columns = {1, 2, 3, 4, 5, 6, 7}
        
        # Set up the base UI components with styles
        layout = super().setup_ui("Cron Jobs", headers, sortable_columns)
        
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
        stretch_columns = [1, 2, 3, 4, 5, 6, 7]
        for col in stretch_columns:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width column for action
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 40)
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with CronJob data
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
        
        # Get CronJob details
        schedule = ""
        suspend = "False"
        active = "0"
        last_schedule = "Never"
        
        if raw_data:
            spec = raw_data.get("spec", {})
            status = raw_data.get("status", {})
            
            # Get schedule
            schedule = spec.get("schedule", "")
            
            # Get suspend status
            suspend = str(spec.get("suspend", False))
            
            # Get active jobs count
            active_list = status.get("active", [])
            active = str(len(active_list))
            
            # Get last schedule time
            last_schedule_time = status.get("lastScheduleTime", "")
            if last_schedule_time:
                # Format the time relative to now
                import datetime
                from dateutil import parser
                try:
                    # Parse ISO format timestamp
                    last_time = parser.parse(last_schedule_time)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    diff = now - last_time
                    
                    # Format as human-readable
                    days = diff.days
                    hours = diff.seconds // 3600
                    minutes = (diff.seconds % 3600) // 60
                    
                    if days > 0:
                        last_schedule = f"{days}d ago"
                    elif hours > 0:
                        last_schedule = f"{hours}h ago"
                    else:
                        last_schedule = f"{minutes}m ago"
                except Exception:
                    last_schedule = "Error"
            
        # Prepare data columns
        columns = [
            resource["name"],
            resource["namespace"],
            schedule,
            suspend,
            active,
            last_schedule,
            resource["age"]
        ]
        
        # Add columns to table
        for col, value in enumerate(columns):
            cell_col = col + 1  # Adjust for checkbox column
            
            # Handle numeric columns for sorting
            if col == 3:  # Suspend column (boolean as string)
                num = 1 if value.lower() == "true" else 0
                item = SortableTableWidgetItem(value, num)
            elif col == 4:  # Active column (numeric)
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 5:  # Last Schedule column
                # Sort by time ago (rough approximation)
                try:
                    if value == "Never":
                        num = 99999  # Put at end of sort
                    elif "d ago" in value:
                        num = int(value.replace("d ago", "")) * 1440  # days to minutes
                    elif "h ago" in value:
                        num = int(value.replace("h ago", "")) * 60  # hours to minutes
                    elif "m ago" in value:
                        num = int(value.replace("m ago", ""))  # minutes
                    else:
                        num = 0
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 6:  # Age column
                try:
                    # Convert age string to minutes for sorting
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
            if col in [3, 4, 5, 6]:  # Suspend, Active, LastSchedule, Age
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Make cells non-editable
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set special colors for Suspend column
            if col == 3:  # Suspend column
                if value.lower() == "true":
                    item.setForeground(QColor(AppColors.STATUS_DISCONNECTED))  # Red for suspended
                else:
                    item.setForeground(QColor(AppColors.TEXT_TABLE))  # Default color
            # Set special colors for Active column
            elif col == 4:  # Active column
                try:
                    if int(value) > 0:
                        item.setForeground(QColor(AppColors.STATUS_ACTIVE))  # Green for active jobs
                    else:
                        item.setForeground(QColor(AppColors.TEXT_TABLE))  # Default for inactive
                except ValueError:
                    item.setForeground(QColor(AppColors.TEXT_TABLE))
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
    
    def handle_row_click(self, row, column):
        """Handle row selection when a table cell is clicked"""
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)