from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QHBoxLayout,
    QToolButton, QMenu, QVBoxLayout, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QIcon

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles, AppConstants

class EventsPage(BaseResourcePage):
    """
    Displays Kubernetes events with live data and resource operations.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "events"  # Set resource type for kubectl
        self.setup_page_ui()
        
    def setup_page_ui(self):
        """Set up the main UI elements for the Events page"""
        # Define headers and sortable columns
        headers = ["Type", "Message", "Namespace", "Involved Object", "Source", "Count", "Age", "Last Seen", ""]
        sortable_columns = {0, 2, 3, 5, 6, 7}
        
        # Create base UI
        layout = super().setup_ui("Events", headers, sortable_columns)
        
        # Remove default checkbox header and show "Type" instead
        header_widget = self._item_widgets.get("header_widget")
        if header_widget:
            header_widget.hide()
        # Clear select-all functionality
        self.select_all_checkbox = None
        # Restore header label text
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem("Type"))

        # Apply table style
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
        
        # Configure column widths
        self.configure_columns()
        return layout
    
    def showEvent(self, event):
        """
        Ensure data is loaded when the page is shown.
        This is the key to fixing the initial load issue.
        """
        super().showEvent(event)
        # Force data to load when the page is shown, bypassing any internal state checks
        self.force_load_data()
        
    def force_load_data(self):
        """
        Override the force_load_data method to ensure it properly loads data
        regardless of the current loading state.
        """
        # Reset loading state
        self.is_loading = False
        # Call the base class load_data method
        super().load_data()
        
    def configure_columns(self):
        """Configure column widths and behaviors"""
        # Configure columns with fixed widths
        fixed_widths = {
            0: 80,  # Type
            2: 120, # Namespace
            3: 150, # Involved Object
            4: 150, # Source
            5: 60,  # Count
            6: 80,  # Age
            7: 100, # Last Seen
            8: 40   # Actions
        }
        
        # Set column widths
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        
        # Make Message column stretch
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with event data from live Kubernetes resources
        """
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Extract data from resource
        raw_data = resource.get("raw_data", {})
        
        # Get event type - ensure it's case-insensitive comparison
        event_type = raw_data.get("type", "Normal")
        is_warning = event_type.lower() == "warning"
        
        # Use a stronger red color for better visibility
        warning_color = QColor("#FF0000")  # Bright red for better contrast
        normal_color = QColor(AppColors.TEXT_TABLE)
        
        # Get event message
        message = raw_data.get("message", "")
        
        # Get involved object
        involved_object = raw_data.get("involvedObject", {})
        involved_kind = involved_object.get("kind", "")
        involved_name = involved_object.get("name", "")
        involved_text = f"{involved_kind}/{involved_name}" if involved_kind and involved_name else "<none>"
        
        # Get source
        source_component = raw_data.get("source", {}).get("component", "")
        source = source_component if source_component else "<none>"
        
        # Get count
        count = str(raw_data.get("count", "1"))
        
        # Get last seen
        last_seen = raw_data.get("lastTimestamp", "")
        if last_seen:
            import datetime
            try:
                last_seen = last_seen.replace('Z', '+00:00')
                last_seen_time = datetime.datetime.fromisoformat(last_seen)
                now = datetime.datetime.now(datetime.timezone.utc)
                diff = now - last_seen_time
                days = diff.days
                hours = diff.seconds // 3600
                minutes = (diff.seconds % 3600) // 60
                if days > 0:
                    last_seen_text = f"{days}d"
                elif hours > 0:
                    last_seen_text = f"{hours}h"
                else:
                    last_seen_text = f"{minutes}m"
            except Exception:
                last_seen_text = "Unknown"
        else:
            last_seen_text = "Unknown"
        
        # Type column - always normal color
        type_item = SortableTableWidgetItem(event_type)
        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        type_item.setForeground(normal_color)  # Always use normal color for Type column
        type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, type_item)
        
        # Message column - red only for warnings
        message_item = SortableTableWidgetItem(message)
        message_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        message_item.setForeground(warning_color if is_warning else normal_color)  # Red only for warnings
        message_item.setFlags(message_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 1, message_item)
        
        # Remaining columns
        columns = [
            resource["namespace"], involved_text, source, count, resource["age"], last_seen_text
        ]
        for col, value in enumerate(columns):
            cell_col = col + 2
            if col == 5:
                try:
                    num = self._parse_age_to_minutes(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 6:
                try:
                    num = self._parse_age_to_minutes(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            elif col == 4:
                try:
                    num = int(value)
                except ValueError:
                    num = 0
                item = SortableTableWidgetItem(value, num)
            else:
                item = SortableTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col == 2:
                item.setForeground(QColor(AppColors.TEXT_LINK))
            else:
                item.setForeground(QColor(AppColors.TEXT_LIGHT))
            self.table.setItem(row, cell_col, item)
        
        # Action button
        action_button = self._create_action_button(row, resource["name"], resource["namespace"])
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(action_button)
        action_container.setStyleSheet("background-color: transparent;")
        self.table.setCellWidget(row, 8, action_container)
    
    def _handle_action(self, action, row):
        if row >= len(self.resources):
            return
        resource = self.resources[row]
        event_type = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
        event_message = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
        namespace = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
        if action == "Edit":
            print(f"Viewing event details: {event_type} in {namespace}: {event_message}")
        elif action == "Delete":
            self.delete_resource(resource["name"], resource["namespace"])

    def _parse_age_to_minutes(self, age):
        if 'm' in age:
            return int(age.replace('m', ''))
        elif 'h' in age:
            return int(age.replace('h', '')) * 60
        elif 'd' in age:
            return int(age.replace('d', '')) * 1440
        else:
            try:
                return int(age)
            except ValueError:
                return 0
            
    def handle_row_click(self, row, column):
        if column != self.table.columnCount() - 1:  # Skip action column
            # Select the row
            self.table.selectRow(row)
            
            # We need to use the unique event name from our resources array
            # Rather than trying to reconstruct it from the table data
            if row < len(self.resources):
                resource = self.resources[row]
                resource_name = resource["name"]
                namespace = resource["namespace"]
                
                # Find the ClusterView instance
                parent = self.parent()
                while parent and not hasattr(parent, 'detail_manager'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'detail_manager'):
                    parent.detail_manager.show_detail("event", resource_name, namespace)
