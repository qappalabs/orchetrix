from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QHBoxLayout,
    QToolButton, QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor

from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppConstants
from UI.ThemeManager import get_theme_manager
from Utils.data_formatters import parse_age_to_seconds

import Styles.EventsPageStyles as EventsPageStyles
import datetime


class EventsPage(BaseResourcePage):
    """
    Displays Kubernetes events with live data and resource operations.
    Simplified version without pagination / lazy loading and checkboxes.
    """

    REQUIRES_FULL_RESET = True

    def __init__(self, parent=None):
        super().__init__(parent)

        self.resource_type = "events"

        # FIXED: Enable pagination for events to prevent loading massive datasets
        self.items_per_page = 100  # Load 100 events at a time
        self.all_data_loaded = False

        # Setup UI immediately
        self.setup_page_ui()

    def _parse_last_seen_text(self, last_seen):
        """Parse ISO timestamp into a human-readable duration."""
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
                    return f"{days}d"
                elif hours > 0:
                    return f"{hours}h"
                else:
                    return f"{minutes}m"
            except Exception:
                return "Unknown"
        return "Unknown"

    def _project_row_data(self, resource):
        """Project raw event resource into flat schema-driven row data with per-cell colors.

        Extracts the semantic fields and projects cell colors via ForegroundRole.
        """
        raw_data = resource.get("raw_data", {}) or {}
        event_type = raw_data.get("type", "Normal")
        reason = raw_data.get("reason", "")
        message = raw_data.get("message", raw_data.get("reason", "No message"))
        namespace = resource.get("namespace", "default")

        involved_object = raw_data.get("involvedObject", {}) or {}
        involved_kind = involved_object.get("kind", "")
        involved_name = involved_object.get("name", "")
        involved_text = f"{involved_kind}/{involved_name}" if involved_kind and involved_name else "Unknown"

        source_info = raw_data.get("source", {}) or {}
        if isinstance(source_info, dict):
            source = source_info.get("component", source_info.get("host", "Unknown"))
        else:
            source = str(source_info) if source_info else "Unknown"

        count = str(raw_data.get("count", 1))
        age = resource.get("age", "Unknown")

        last_seen = raw_data.get("lastTimestamp", raw_data.get("eventTime", ""))
        last_seen_text = self._parse_last_seen_text(last_seen)

        # Build theme-aware colors dictionary
        type_color = EventsPageStyles.TYPE_COLORS.get(event_type, "#FFFFFF")

        # Severity is driven by both the event "type" (only ever Normal/Warning)
        # and the "reason" (FailedMount, BackOff, Unhealthy, ...), since the
        # special buckets below are reason values, not type values.
        if event_type in ["Warning", "Error"] or reason in ["Error", "Failed", "FailedMount", "FailedScheduling"]:
            msg_color = EventsPageStyles.get_error_message_color()
        elif reason in ["BackOff", "Unhealthy"]:
            msg_color = EventsPageStyles.get_warning_message_color()
        else:
            msg_color = EventsPageStyles.get_message_color()

        ns_color = EventsPageStyles.get_namespace_color()
        obj_color = EventsPageStyles.get_object_color()
        src_color = EventsPageStyles.get_source_color()

        count_value = int(count) if count.isdigit() else 0
        if count_value > 10:
            count_color = EventsPageStyles.get_count_high_color()
        elif count_value > 5:
            count_color = EventsPageStyles.get_count_medium_color()
        else:
            count_color = EventsPageStyles.get_count_low_color()

        ts_color = EventsPageStyles.get_timestamp_color()

        colors = {
            1: type_color,
            2: msg_color,
            3: ns_color,
            4: obj_color,
            5: src_color,
            6: count_color,
            7: ts_color,
            8: ts_color,
        }

        return {
            "uid": self._build_uid_from_resource(resource),
            "type": event_type,
            "message": message,
            "namespace": namespace,
            "object": involved_text,
            "source": source,
            "count": count,
            "age": age,
            "last_seen": last_seen_text,
            "_colors": colors,
            "_raw": resource
        }

    def populate_resource_row(self, row, resource):
        """Populate table row with schema-driven, theme-colored event data."""
        self.table.setRowHeight(row, 50)

        # Set a dummy item for column 0 (which is hidden)
        dummy_item = SortableTableWidgetItem("")
        dummy_item.setFlags(dummy_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, dummy_item)

        row_data = self._project_row_data(resource)
        # Stash the stable UID on the hidden marker cell so a theme refresh can
        # map a visible (possibly sorted) row back to its backing resource.
        dummy_item.setData(Qt.ItemDataRole.UserRole, row_data["uid"])
        display_values = [
            row_data["type"],
            row_data["message"],
            row_data["namespace"],
            row_data["object"],
            row_data["source"],
            row_data["count"],
            row_data["age"],
            row_data["last_seen"]
        ]

        colors = row_data["_colors"]

        for i, value in enumerate(display_values):
            col = i + 1
            if col >= self.table.columnCount() - 1:  # Leave room for action column
                break

            if col in (7, 8):
                item = SortableTableWidgetItem(str(value), parse_age_to_seconds(str(value)))
            else:
                item = SortableTableWidgetItem(str(value))

            item.setToolTip(str(value))

            if col == 2:  # Message column
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.style_table_item(item)

            # Apply dynamic projected colors
            color_str = colors.get(col)
            if color_str:
                color = QColor(color_str)
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, col, item)

        # Enhanced action button in last column
        action_column = self.table.columnCount() - 1

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

        # Enable horizontal scrolling so resizing columns pushes the scrollbar
        # (Excel-like behaviour: drag right edge grows that column, others stay put)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Configure column widths
        self.configure_columns()

        # Force load data after setup is complete
        QTimer.singleShot(100, self.force_load_data)

        return page_layout

    def configure_columns(self):

        if not self.table:
            return

        header = self.table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(40)

        # ALL content columns are Interactive so the user can drag-resize any of
        # them.  The auto-resizer (_auto_resize_columns below) enforces per-column
        # minimums that prevent any header text from being clipped at startup.
        #
        # Default widths are chosen to be "just right" for typical content:
        #   short fixed-value columns  → tight default (= their header min + a
        #                               little breathing room)
        #   long free-text columns     → wider default so they carry most of the
        #                               width budget and absorb overflow first
        #
        # Headers: ["", "Type", "Message", "Namespace", "Involved Object",
        #           "Source", "Count", "Age", "Last Seen", ""]
        column_specs = [
            # (col_index, default_width)
            (0, 0,   "hidden"),       # Checkbox (hidden)
            (1, 80,  "interactive"),  # Type      — "Normal" / "Warning"
            (2, 160, "interactive"),  # Message   — long free-text (primary absorber)
            (3, 105, "interactive"),  # Namespace
            (4, 120, "interactive"),  # Involved Object — long (secondary absorber)
            (5, 75,  "interactive"),  # Source
            (6, 65,  "interactive"),  # Count
            (7, 55,  "interactive"),  # Age
            (8, 95,  "interactive"),  # Last Seen
            (9, 50,  "fixed"),        # Actions
        ]

        for col_index, col_width, resize_type in column_specs:
            if col_index >= self.table.columnCount():
                continue
            if resize_type == "hidden":
                self.table.setColumnHidden(col_index, True)
            elif resize_type == "fixed":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col_index, col_width)
            elif resize_type == "interactive":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(col_index, col_width)

    def _handle_scroll(self, value):

        # Use base class scroll handling which includes pagination
        super()._handle_scroll(value)

    def _auto_resize_columns(self, max_col_widths=None, min_col_widths=None):
        """Viewport-fit with hardcoded per-column minimums.

        Explicit minimums are passed to the base class instead of relying on
        font-metrics (which is unreliable before the first render).

        Priority for shrinking during Phase 2:
          1. Message (col 2)         — widest, shrinks most
          2. Involved Object (col 4) — shrinks second
          All other Interactive columns have tight minimums = their header
          text width, so they effectively never get shrunk further.
        """
        # Hardcoded minimum widths in pixels.  Values are chosen so each column
        # header text is always fully visible at any window size.
        explicit_mins = {
            1:  80,   # "Type"
            2:  68,   # "Message"
            3:  105,  # "Namespace"
            4: 116,   # "Involved Object"
            5:  75,   # "Source"
            6:  65,   # "Count"
            7:  55,   # "Age"
            8:  95,   # "Last Seen"
        }
        # Caller-supplied overrides take precedence
        if min_col_widths:
            explicit_mins.update(min_col_widths)

        caps = {
            2: 320,   # Message  — cap so it doesn't blow the table out
            3: 160,   # Namespace — cap it to push horizontal space into messages
            4: 240,   # Involved Object — cap for long pod names
        }
        if max_col_widths:
            caps.update(max_col_widths)

        super()._auto_resize_columns(max_col_widths=caps, min_col_widths=explicit_mins)

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
        """Override to return None - events don't need bulk selection"""
        return None

    def _handle_select_all(self, state):
        """Override to do nothing - events don't support bulk operations"""
        pass

    def _handle_checkbox_change(self, state, item_name):
        """Override to do nothing - events don't support bulk operations"""
        pass

    def _on_theme_changed(self, theme_name):
        """Refresh UI and row cell colors when theme changes."""
        super()._on_theme_changed(theme_name)
        if not (hasattr(self, 'table') and self.table):
            return

        # Visible row order diverges from self.resources once the user sorts a
        # column, so resolve each row back to its resource by the projected UID
        # rather than indexing self.resources by the visual row number.
        resources_by_uid = {
            self._build_uid_from_resource(resource): resource
            for resource in self.resources
        }

        for row in range(self.table.rowCount()):
            marker = self.table.item(row, 0)
            uid = marker.data(Qt.ItemDataRole.UserRole) if marker else None
            resource = resources_by_uid.get(uid)
            if resource is None and row < len(self.resources):
                resource = self.resources[row]
            if resource is not None:
                self.populate_resource_row(row, resource)
