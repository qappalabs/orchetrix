from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QHBoxLayout,
    QToolButton, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppConstants
from UI.ThemeManager import get_theme_manager

import Styles.EventsPageStyles as EventsPageStyles
import datetime


class EventsPage(BaseResourcePage):
    """
    Displays Kubernetes events with live data and resource operations.
    Simplified version without pagination / lazy loading and checkboxes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.resource_type = "events"

        # FIXED: Enable pagination for events to prevent loading massive datasets
        self.items_per_page = 100  # Load 100 events at a time
        self.all_data_loaded = False

        # Defer UI setup to ensure base class is fully initialized
        QTimer.singleShot(0, self.setup_page_ui)

    def setup_page_ui(self):

        # Define headers - include proper header for checkbox column even though it's hidden
        headers = ["", "Type", "Message", "Namespace", "Involved Object", "Source", "Count", "Age", "Last Seen", ""]

        # Create base UI - this will add a checkbox column at index 0
        page_layout = super().setup_ui("Events", headers)

        # Ensure proper header visibility and styling
        header = self.table.horizontalHeader()
        header.setVisible(True)
        header.setMinimumHeight(35)
        header.setDefaultSectionSize(100)

        # Table styling is already handled by BaseResourcePage
        # Header styling is handled by CustomHeader (theme - aware)

        # Configure column widths
        self.configure_columns()

        # Force load data after setup is complete
        QTimer.singleShot(100, self.force_load_data)

        return page_layout

    def configure_columns(self):

        if not self.table:
            return

        header = self.table.horizontalHeader()

        # FIXED: Ensure proper column resize behavior and dragging
        # Disable moving columns but allow resizing
        header.setSectionsMovable(False)
        header.setMinimumSectionSize(50)  # Minimum width for resizing
        # We'll manually control stretching
        header.setStretchLastSection(False)

        # Simple column configuration for better performance
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Hide first column (checkbox)
        self.table.setColumnHidden(0, True)

        # Set last column as stretch to fill remaining space
        header.setSectionResizeMode(
            self.table.columnCount() - 2, QHeaderView.ResizeMode.Stretch)

        # Simple width setting - message column will stretch automatically
        widths = [0, 80, 0, 100, 150, 120, 60, 80, 100, 50]
        for i, width in enumerate(widths):
            if i < self.table.columnCount() and width > 0:
                self.table.setColumnWidth(i, width)

    def _handle_scroll(self, value):

        # Use base class scroll handling which includes pagination
        super()._handle_scroll(value)

    def on_resources_loaded(self, new_resources, resource_type, next_continue_token, load_more=False):

        if self._shutting_down:
            return

        # FIXED: Use base class pagination handling instead of custom logic
        try:
            # Call the base class method which handles pagination properly
            super()._on_resources_loaded((new_resources, resource_type, next_continue_token))

        except AttributeError:
            # Fallback to manual pagination handling if base method not available
            if load_more:
                # Append to existing resources
                self.resources.extend(new_resources)
            else:
                # Replace resources
                self.resources = new_resources

            # Update pagination state
            self.current_continue_token = next_continue_token
            self.all_data_loaded = not next_continue_token

            # Update UI
            self._display_resources(self.resources)
            self._update_items_count()

            self.is_loading_initial = False
            self.is_loading_more = False

            if self.all_data_loaded:
                self.all_items_loaded_signal.emit()

            self.load_more_complete.emit()

    def populate_resource_row(self, row, resource):

        # Set row height - increased for better readability
        self.table.setRowHeight(row, 50)

        # Extract data from resource
        raw_data = resource.get("raw_data", {})

        # Get event type
        event_type = raw_data.get("type", "Normal")

        # FIXED: Get full event message without truncation
        message = raw_data.get("message", raw_data.get("reason", "No message"))

        # Get namespace
        namespace = resource.get("namespace", "default")

        # Get involved object
        involved_object = raw_data.get("involvedObject", {})
        involved_kind = involved_object.get("kind", "")
        involved_name = involved_object.get("name", "")
        involved_text = f"{involved_kind}/{involved_name}" if involved_kind and involved_name else "Unknown"

        # Get source
        source_info = raw_data.get("source", {})
        if isinstance(source_info, dict):
            source = source_info.get(
                "component", source_info.get("host", "Unknown"))
        else:
            source = str(source_info) if source_info else "Unknown"

        # Get count
        count = str(raw_data.get("count", 1))

        # Get age from resource
        age = resource.get("age", "Unknown")

        # Get last seen with better parsing
        last_seen = raw_data.get(
            "lastTimestamp", raw_data.get("eventTime", ""))
        if last_seen:
            try:
                if 'Z' in last_seen:
                    last_seen = last_seen.replace('Z', '+00:00')
                last_seen_time = datetime.datetime.fromisoformat(last_seen)
                if last_seen_time.tzinfo is None:
                    last_seen_time = last_seen_time.replace(
                        tzinfo=datetime.timezone.utc)
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

        # FIXED: Create all items with full message (no truncation)
        display_values = [
            event_type,
            message,  # Full message without truncation
            namespace,
            involved_text,
            source,
            count,
            age,
            last_seen_text
        ]

        # Column 0 is hidden checkbox, so start data population from column 1
        # Populate columns 1 - 8 with data
        for i, value in enumerate(display_values):
            col = i + 1  # Skip checkbox column at index 0
            if col >= self.table.columnCount() - 1:  # Leave room for action column
                break

            item = SortableTableWidgetItem(str(value))

            # FIXED: Add tooltip for all cells to show full content
            item.setToolTip(str(value))

            # Set alignment
            if col == 2:  # Message column (accounting for checkbox offset)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Enhanced color coding for different event types and columns
            if col == 1:  # Type column - different colors for different event types
                # Force color application with important styling
                color = EventsPageStyles.TYPE_COLORS.get(event_type, "#FFFFFF")  # Default to white
                item.setForeground(QColor(color))
                # Force the color by setting data role as well
                item.setData(Qt.ItemDataRole.ForegroundRole, QColor(color))

            elif col == 2:  # Message column - inherit color from event type for warnings / errors
                if event_type in ["Warning", "Error", "Failed", "FailedMount", "FailedScheduling"]:
                    color = QColor(EventsPageStyles.get_error_message_color())
                elif event_type in ["BackOff", "Unhealthy"]:
                    color = QColor(EventsPageStyles.get_warning_message_color())
                else:
                    color = QColor(EventsPageStyles.get_message_color())
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            elif col == 3:  # Namespace column
                color = QColor(EventsPageStyles.get_namespace_color())
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            elif col == 4:  # Involved Object column
                color = QColor(EventsPageStyles.get_object_color())
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            elif col == 5:  # Source column
                color = QColor(EventsPageStyles.get_source_color())
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            elif col == 6:  # Count column
                count_value = int(value) if str(value).isdigit() else 0
                if count_value > 10:
                    color = QColor(EventsPageStyles.get_count_high_color())
                elif count_value > 5:
                    color = QColor(EventsPageStyles.get_count_medium_color())
                else:
                    color = QColor(EventsPageStyles.get_count_low_color())
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            else:  # Age and Last Seen columns
                color = QColor(EventsPageStyles.get_timestamp_color())
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, col, item)

        # Enhanced action button in last column
        action_column = self.table.columnCount() - 1
        action_button = self._create_enhanced_action_button(
            row, resource.get("name", ""), resource.get("namespace", ""))
        action_container = self._create_perfect_action_container(action_button)
        self.table.setCellWidget(row, action_column, action_container)

    def _create_enhanced_action_button(self, row, resource_name, resource_namespace):

        button = QToolButton()

        # Use theme - aware icon from parent class (cached and updates with theme)
        button.setIcon(self.action_button_icon)
        button.setIconSize(QSize(
            # Even smaller icon
            AppConstants.SIZES["ICON_SIZE"], AppConstants.SIZES["ICON_SIZE"]))

        # Very compact button styling
        button.setStyleSheet(EventsPageStyles.get_action_button_style())

        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(20, 20)  # Very small size

        # Create simple menu
        menu = QMenu(button)
        menu.setStyleSheet(EventsPageStyles.get_menu_style())

        # Simple menu actions
        view_action = menu.addAction("View Details")
        view_action.triggered.connect(
            lambda: self._handle_view_event_details(row))

        menu.addSeparator()

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(
            lambda: self._handle_action("Delete", row))

        button.setMenu(menu)

        # Connect row highlighting
        menu.aboutToShow.connect(lambda: self._highlight_active_row(row, True))
        menu.aboutToHide.connect(
            lambda: self._highlight_active_row(row, False))

        return button

    def _create_perfect_action_container(self, button):

        container = QWidget()
        # Increased width from 24 to 40 for better right spacing
        container.setFixedSize(40, 24)
        container.setStyleSheet(EventsPageStyles.ACTION_CONTAINER_STYLE)

        layout = QHBoxLayout(container)
        # Add left and right margins for better spacing
        layout.setContentsMargins(5, 0, 10, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(button)

        return container

    def _handle_view_event_details(self, row):

        if row < len(self.resources):
            # Trigger the existing detail view mechanism
            # Simulate clicking on a non - action column
            self.handle_row_click(row, 1)

    def _highlight_active_row(self, row, is_active):

        if row >= self.table.rowCount():
            return

        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                if is_active:
                    # More subtle highlight color
                    # Very transparent blue
                    accent_color = getattr(get_theme_manager().get_current_theme().colors, 'ACCENT_BLUE', AppColors.ACCENT_BLUE)
                    highlight_color = QColor(accent_color)
                    highlight_color.setAlpha(0x15)  # 21/255 = ~8% opacity
                    item.setBackground(highlight_color)
                else:
                    item.setBackground(QColor("transparent"))

        # Also highlight any cell widgets (like the action button)
        action_container = self.table.cellWidget(
            row, self.table.columnCount() - 1)
        if action_container:
            if is_active:
                action_container.setStyleSheet(
                    EventsPageStyles.ACTION_CONTAINER_ACTIVE_STYLE)
            else:
                action_container.setStyleSheet(
                    EventsPageStyles.ACTION_CONTAINER_INACTIVE_STYLE)

    def _handle_action(self, action, row):

        if row >= len(self.resources):
            return
        resource = self.resources[row]
        if action == "Delete":
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

        if column != self.table.columnCount() - 1:  # Not the action column
            self.table.selectRow(row)

            # Get the parent view to show detail
            parent = self.parent()
            while parent and not hasattr(parent, 'show_detail_for_table_item'):
                parent = parent.parent()

            # If we found the parent with detail function, call it
            if parent and hasattr(parent, 'show_detail_for_table_item'):
                parent.show_detail_for_table_item(row, column, self, "Events")

    # Override checkbox - related methods to disable them for events
    def _create_select_all_checkbox(self):

        return None

    def _handle_select_all(self, state):

        pass

    def _handle_checkbox_change(self, state, item_name):

        pass
