from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QHBoxLayout,
    QToolButton, QMenu, QVBoxLayout, QTableWidgetItem
)
from PyQt6.QtCore import Qt,QTimer
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
        
        # Force load data after setup is complete
        QTimer.singleShot(100, self.force_load_data)
        
        return layout
    # def configure_columns(self):
    #     """Configure column widths and behaviors"""
    #     # Configure columns with fixed widths
    #     fixed_widths = {
    #         0: 80,  # Type
    #         2: 120, # Namespace
    #         3: 150, # Involved Object
    #         4: 150, # Source
    #         5: 60,  # Count
    #         6: 80,  # Age
    #         7: 100, # Last Seen
    #         8: 40   # Actions
    #     }
        
    #     # Set column widths
    #     for col, width in fixed_widths.items():
    #         self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
    #         self.table.setColumnWidth(col, width)
        
    #     # Make Message column stretch
    #     self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    
    def configure_columns(self):
        """Configure column widths for full screen utilization"""
        if not self.table:
            return
        
        header = self.table.horizontalHeader()
        
        # Column specifications with optimized default widths
        column_specs = [
            (0, 140, "interactive"), # Type
            (1, 90, "interactive"),  # Message
            (2, 80, "interactive"),  # Namespace
            (3, 70, "interactive"),  # Involved object
            (4, 80, "interactive"),  # Scope
            (5, 70, "interactive"),  # Count
            (6, 60, "interactive"),  # Age
            (7, 80, "stretch"),      # Last Seen - stretch to fill remaining space
            (8, 40, "fixed")        # Actions
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
        Populate a single row with event data from live Kubernetes resources
        """
        # Set row height
        self.table.setRowHeight(row, 40)
        
        # Extract data from resource
        raw_data = resource.get("raw_data", {})
        
        # Get event type
        event_type = raw_data.get("type", "Normal")
        
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
        
        # Type column
        type_item = SortableTableWidgetItem(event_type)
        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if event_type == "Warning":
            type_item.setForeground(QColor("#ff4d4f"))
        else:
            type_item.setForeground(QColor(AppColors.TEXT_TABLE))
        type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, type_item)
        
        # Message column
        message_item = SortableTableWidgetItem(message)
        message_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if event_type == "Warning":
            message_item.setForeground(QColor("#ff4d4f"))
        else:
            message_item.setForeground(QColor(AppColors.TEXT_TABLE))
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
            pass
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

        # Add this method to EventsPage to properly handle row clicks
    def handle_row_click(self, row, column):
            """Handle row click event to show detail page"""
            if column != 8:  # Not the action column
                self.table.selectRow(row)
                
                # Get the parent view to show detail
                parent = self.parent()
                while parent and not hasattr(parent, 'show_detail_for_table_item'):
                    parent = parent.parent()
                    
                # If we found the parent with detail function, call it
                if parent and hasattr(parent, 'show_detail_for_table_item'):
                    parent.show_detail_for_table_item(row, column, self, "Events")