from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QLabel, QHBoxLayout,
    QToolButton, QMenu, QVBoxLayout, QTableWidgetItem, QApplication, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor, QIcon
import logging

from base_components.base_components import SortableTableWidgetItem
from base_components.base_resource_page import BaseResourcePage, KubernetesResourceLoader
from UI.Styles import AppStyles, AppColors, AppConstants
from utils.thread_manager import get_thread_manager

class EventsPage(BaseResourcePage):
    """
    Displays Kubernetes events with live data and resource operations.
    Simplified version without pagination/lazy loading and checkboxes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "events"

        # Disable pagination and lazy loading
        self.items_per_page = None
        self.all_data_loaded = True

        self.setup_page_ui()

    def setup_page_ui(self):
        """Set up the main UI elements for the Events page"""
        # Define headers - include proper header for checkbox column even though it's hidden
        headers = ["✓", "Type", "Message", "Namespace", "Involved Object", "Source", "Count", "Age", "Last Seen", ""]
        sortable_columns = {1, 3, 4, 6, 7, 8}  # Type, Namespace, Involved Object, Count, Age, Last Seen

        # Create base UI - this will add a checkbox column at index 0
        layout = super().setup_ui("Events", headers, sortable_columns)

        # Ensure proper header visibility and styling
        header = self.table.horizontalHeader()
        header.setVisible(True)
        header.setMinimumHeight(35)
        header.setDefaultSectionSize(100)

        # Apply enhanced table style
        if hasattr(AppStyles, 'TABLE_STYLE'):
            self.table.setStyleSheet(AppStyles.TABLE_STYLE)

        # FIXED: Enhanced header style with better text visibility
        header.setStyleSheet(f"""
            QHeaderView::section {{
                background-color: {AppColors.HEADER_BG};
                color: #FFFFFF;
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid {AppColors.BORDER_COLOR};
                border-right: 1px solid {AppColors.BORDER_COLOR};
                font-size: 12px;
                font-weight: bold;
                text-align: center;
                margin: 0px;
            }}
            QHeaderView::section:hover {{
                background-color: {AppColors.BG_MEDIUM};
                color: #FFFFFF;
            }}
            QHeaderView::section:first {{
                border-left: 1px solid {AppColors.BORDER_COLOR};
                padding-left: 0px;
                margin-left: 0px;
            }}
            QHeaderView::section:pressed {{
                background-color: {AppColors.BG_DARKER};
                color: #FFFFFF;
            }}
        """)

        # Configure column widths
        self.configure_columns()

        # Force load data after setup is complete
        QTimer.singleShot(100, self.force_load_data)

        return layout

    def configure_columns(self):
        """FIXED: Configure column widths for optimal display with resizable message column"""
        if not self.table:
            return

        header = self.table.horizontalHeader()

        # FIXED: Ensure proper column resize behavior and dragging
        header.setSectionsMovable(False)  # Disable moving columns but allow resizing
        header.setMinimumSectionSize(50)  # Minimum width for resizing

        # Set column resize modes and widths
        for col_index in range(self.table.columnCount()):
            if col_index == 0:  # Hide checkbox column completely
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col_index, 0)
                self.table.setColumnHidden(col_index, True)
            elif col_index == 2:  # FIXED: Message column - make it interactive and resizable
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(col_index, 300)  # Start with reasonable width
            elif col_index == self.table.columnCount() - 1:  # Action column - FIXED: Tighter spacing
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col_index, 50)  # Increased from 30 to give more space on right
            else:  # All other columns - FIXED: Enable proper interactive resizing
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)

        # Set initial widths for interactive columns
        column_widths = {
            1: 80,   # Type
            2: 300,  # Message - increased width
            3: 100,  # Namespace
            4: 150,  # Involved object
            5: 120,  # Source
            6: 60,   # Count
            7: 80,   # Age
            8: 100,  # Last Seen
        }

        for col, width in column_widths.items():
            if col < self.table.columnCount():
                self.table.setColumnWidth(col, width)

        # FIXED: Ensure the header properly handles the hidden first column
        header.setSectionHidden(0, True)

    def _handle_scroll(self, value):
        """Override to disable infinite scrolling"""
        pass

    def load_data(self, load_more=False):
        """Override to always load all data at once"""
        if self._shutting_down:
            return

        if self.is_loading_initial:
            return

        self.is_loading_initial = True
        self.resources = []
        self.selected_items.clear()
        self.current_continue_token = None
        self.all_data_loaded = True

        if self.table:
            self.table.setRowCount(0)
        if hasattr(self, '_show_skeleton_loader') and self.table.rowCount() == 0:
            self._show_skeleton_loader()
        else:
            self._show_table_area()

        # Create worker without pagination parameters
        worker = KubernetesResourceLoader(
            self.resource_type,
            self.namespace_filter,
            limit=None,
            continue_token=None
        )

        worker.signals.finished.connect(
            lambda result: self.on_resources_loaded(result[0], result[1], result[2], False)
        )
        worker.signals.error.connect(
            lambda err_msg: self.on_load_error(err_msg, False)
        )

        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"resource_load_{self.resource_type}_all", worker)

    def on_resources_loaded(self, new_resources, resource_type, next_continue_token, load_more=False):
        """Override to handle all data loading"""
        if self._shutting_down:
            return

        search_text = self.search_bar.text().lower() if self.search_bar and self.search_bar.text() else ""

        filtered_new_resources = []
        if search_text:
            for r_item in new_resources:
                match = search_text in r_item.get("name", "").lower()
                if not match and r_item.get("namespace"):
                    match = search_text in r_item.get("namespace", "").lower()
                if not match and r_item.get("raw_data", {}).get("message", ""):
                    match = search_text in r_item.get("raw_data", {}).get("message", "").lower()
                if match:
                    filtered_new_resources.append(r_item)
        else:
            filtered_new_resources = new_resources

        if self.is_showing_skeleton:
            self.is_showing_skeleton = False
            if hasattr(self, 'skeleton_timer') and self.skeleton_timer.isActive():
                self.skeleton_timer.stop()

        self.is_loading_initial = False
        self.resources = filtered_new_resources
        self.all_data_loaded = True

        self._clear_empty_state()

        if filtered_new_resources:
            self.table.setRowCount(0)
            self.populate_table(self.resources)
            self._show_table_area()
            self.table.setSortingEnabled(True)
        else:
            empty_message = f"No {self.resource_type} found"
            if search_text:
                empty_message = f"No {self.resource_type} found matching '{search_text}'"
                description = "Try adjusting your search criteria or check if resources exist in other namespaces."
            else:
                description = f"No {self.resource_type} are currently available in the selected namespace."

            self._show_message_in_table_area(empty_message, description)

        self.items_count.setText(f"{len(self.resources)} items")
        QApplication.processEvents()

    def populate_resource_row(self, row, resource):
        """FIXED: Populate a single row with event data - no message truncation, add tooltips"""
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
            source = source_info.get("component", source_info.get("host", "Unknown"))
        else:
            source = str(source_info) if source_info else "Unknown"

        # Get count
        count = str(raw_data.get("count", 1))

        # Get age from resource
        age = resource.get("age", "Unknown")

        # Get last seen with better parsing
        last_seen = raw_data.get("lastTimestamp", raw_data.get("eventTime", ""))
        if last_seen:
            import datetime
            try:
                if 'Z' in last_seen:
                    last_seen = last_seen.replace('Z', '+00:00')
                last_seen_time = datetime.datetime.fromisoformat(last_seen)
                if last_seen_time.tzinfo is None:
                    last_seen_time = last_seen_time.replace(tzinfo=datetime.timezone.utc)
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
        # Populate columns 1-8 with data
        for i, value in enumerate(display_values):
            col = i + 1  # Skip checkbox column at index 0
            if col >= self.table.columnCount() - 1:  # Leave room for action column
                break

            item = SortableTableWidgetItem(str(value))

            # FIXED: Add tooltip for all cells to show full content
            item.setToolTip(str(value))

            # Set alignment
            if col == 2:  # Message column (accounting for checkbox offset)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Enhanced color coding for different event types and columns
            if col == 1:  # Type column - different colors for different event types
                # Force color application with important styling
                type_colors = {
                    "Normal": "#4CAF50",      # Green for normal events
                    "Warning": "#FF9800",     # Orange for warnings
                    "Error": "#F44336",       # Red for errors
                    "FailedMount": "#F44336", # Red for failed mounts
                    "Failed": "#F44336",      # Red for failed events
                    "FailedScheduling": "#F44336",  # Red for scheduling failures
                    "Unhealthy": "#FF5722",   # Deep orange for health issues
                    "BackOff": "#FF9800",     # Orange for backoff events
                    "Killing": "#FF5722",     # Deep orange for killing events
                    "Created": "#2196F3",     # Blue for creation events
                    "Started": "#4CAF50",     # Green for started events
                    "Pulled": "#4CAF50",      # Green for successful pulls
                    "Scheduled": "#4CAF50",   # Green for successful scheduling
                }
                color = type_colors.get(event_type, "#ffffff")  # Default to white
                item.setForeground(QColor(color))
                # Force the color by setting data role as well
                item.setData(Qt.ItemDataRole.ForegroundRole, QColor(color))

            elif col == 2:  # Message column - inherit color from event type for warnings/errors
                if event_type in ["Warning", "Error", "Failed", "FailedMount", "FailedScheduling"]:
                    color = QColor("#F44336")  # Red for error messages
                elif event_type in ["BackOff", "Unhealthy"]:
                    color = QColor("#FF9800")  # Orange for warning messages
                else:
                    color = QColor("#ffffff")  # White for normal messages
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            elif col == 3:  # Namespace column
                color = QColor("#64B5F6")  # Light blue for namespace
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            elif col == 4:  # Involved Object column
                color = QColor("#81C784")  # Light green for objects
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            elif col == 5:  # Source column
                color = QColor("#FFB74D")  # Light orange for source
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            elif col == 6:  # Count column
                count_value = int(value) if str(value).isdigit() else 0
                if count_value > 10:
                    color = QColor("#F44336")  # Red for high count
                elif count_value > 5:
                    color = QColor("#FF9800")  # Orange for medium count
                else:
                    color = QColor("#4CAF50")  # Green for low count
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            else:  # Age and Last Seen columns
                color = QColor("#B0BEC5")  # Light gray for timestamps
                item.setForeground(color)
                item.setData(Qt.ItemDataRole.ForegroundRole, color)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, col, item)

        # Enhanced action button in last column
        action_column = self.table.columnCount() - 1
        action_button = self._create_enhanced_action_button(row, resource.get("name", ""), resource.get("namespace", ""))
        action_container = self._create_perfect_action_container(action_button)
        self.table.setCellWidget(row, action_column, action_container)

    def _create_enhanced_action_button(self, row, resource_name, resource_namespace):
        """Create a very compact action button"""
        button = QToolButton()

        # Use custom SVG icon
        icon = QIcon("icons/Moreaction_Button.svg")
        button.setIcon(icon)
        button.setIconSize(QSize(12, 12))  # Even smaller icon

        # Very compact button styling
        button.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 3px;
                margin: 0px;
                color: {AppColors.TEXT_SECONDARY};
            }}
            QToolButton:hover {{
                background-color: {AppColors.HOVER_BG};
                color: {AppColors.TEXT_LIGHT};
            }}
            QToolButton:pressed {{
                background-color: {AppColors.HOVER_BG_DARKER};
            }}
            QToolButton::menu-indicator {{
                image: none;
                width: 0px;
                height: 0px;
            }}
        """)

        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(20, 20)  # Very small size

        # Create simple menu
        menu = QMenu(button)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {AppColors.BG_DARKER};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                padding: 4px;
                color: {AppColors.TEXT_LIGHT};
            }}
            QMenu::item {{
                color: {AppColors.TEXT_LIGHT};
                padding: 8px 12px;
                border-radius: 3px;
                font-size: 12px;
                margin: 1px 0px;
                min-width: 80px;
            }}
            QMenu::item:selected {{
                background-color: {AppColors.SELECTED_BG};
                color: {AppColors.TEXT_LIGHT};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {AppColors.BORDER_COLOR};
                margin: 3px 6px;
            }}
        """)

        # Simple menu actions
        view_action = menu.addAction("View Details")
        view_action.triggered.connect(lambda: self._handle_view_event_details(row))

        menu.addSeparator()

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._handle_action("Delete", row))

        button.setMenu(menu)

        # Connect row highlighting
        menu.aboutToShow.connect(lambda: self._highlight_active_row(row, True))
        menu.aboutToHide.connect(lambda: self._highlight_active_row(row, False))

        return button

    def _create_perfect_action_container(self, button):
        """Create a well-spaced action button container - FIXED: Better spacing on right"""
        container = QWidget()
        container.setFixedSize(40, 24)  # Increased width from 24 to 40 for better right spacing
        container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 10, 0)  # Add left and right margins for better spacing
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(button)

        return container

    def _handle_view_event_details(self, row):
        """Handle viewing event details"""
        if row < len(self.resources):
            # Trigger the existing detail view mechanism
            self.handle_row_click(row, 1)  # Simulate clicking on a non-action column

    def _highlight_active_row(self, row, is_active):
        """Enhanced row highlighting for better visual feedback"""
        if row >= self.table.rowCount():
            return

        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                if is_active:
                    # More subtle highlight color
                    item.setBackground(QColor(f"{AppColors.ACCENT_BLUE}15"))  # Very transparent blue
                else:
                    item.setBackground(QColor("transparent"))

        # Also highlight any cell widgets (like the action button)
        action_container = self.table.cellWidget(row, self.table.columnCount() - 1)
        if action_container:
            if is_active:
                action_container.setStyleSheet("""
                    QWidget {
                        background-color: rgba(33, 150, 243, 0.08);
                        border-radius: 4px;
                    }
                """)
            else:
                action_container.setStyleSheet("""
                    QWidget {
                        background-color: transparent;
                        border: none;
                    }
                """)

    def _handle_action(self, action, row):
        """Handle action button clicks"""
        if row >= len(self.resources):
            return
        resource = self.resources[row]
        if action == "Delete":
            self.delete_resource(resource["name"], resource["namespace"])

    def _parse_age_to_minutes(self, age):
        """Parse age string to minutes for sorting"""
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
        """Handle row click event to show detail page"""
        if column != self.table.columnCount() - 1:  # Not the action column
            self.table.selectRow(row)

            # Get the parent view to show detail
            parent = self.parent()
            while parent and not hasattr(parent, 'show_detail_for_table_item'):
                parent = parent.parent()

            # If we found the parent with detail function, call it
            if parent and hasattr(parent, 'show_detail_for_table_item'):
                parent.show_detail_for_table_item(row, column, self, "Events")

    # Override checkbox-related methods to disable them for events
    def _create_select_all_checkbox(self):
        """Override to return None - events don't need bulk selection"""
        return None

    def _handle_select_all(self, state):
        """Override to do nothing - events don't support bulk operations"""
        pass

    def _handle_checkbox_change(self, state, item_name):
        """Override to do nothing - events don't support bulk operations"""
        pass