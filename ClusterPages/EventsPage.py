from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QHeaderView, QToolButton, QMenu, QLabel, QCheckBox, QApplication, QStyle, QStyleOptionHeader
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QCursor, QPainter, QPen, QLinearGradient, QPainterPath, QBrush
import random, datetime

# Constants for column indices
TYPE_COL = 0
MESSAGE_COL = 1
NAMESPACE_COL = 2
INVOLVED_OBJECT_COL = 3
SOURCE_COL = 4
COUNT_COL = 5
AGE_COL = 6
LAST_SEEN_COL = 7
ACTIONS_COL = 8

class SortableTableWidgetItem(QTableWidgetItem):
    """
    Custom QTableWidgetItem that allows numeric sorting if you provide a numeric 'value'.
    Otherwise, it sorts by text.
    """
    def __init__(self, text, value=None):
        super().__init__(str(text))  # Ensure text is converted to string
        self.value = value

    def __lt__(self, other):
        if isinstance(other, SortableTableWidgetItem) and self.value is not None and other.value is not None:
            return self.value < other.value
        return super().__lt__(other)

class EventsHeader(QHeaderView):
    """
    A custom header that enables sorting only for specific columns
    and displays a hover sort indicator arrow on those columns.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        # Define which columns are sortable
        self.sortable_columns = {TYPE_COL, NAMESPACE_COL, INVOLVED_OBJECT_COL, COUNT_COL, AGE_COL, LAST_SEEN_COL}
        self.setSectionsClickable(True)
        self.setHighlightSections(True)

    def mousePressEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex in self.sortable_columns:
            super().mousePressEvent(event)
        else:
            event.ignore()

    def paintSection(self, painter, rect, logicalIndex):
        option = QStyleOptionHeader()
        self.initStyleOption(option)
        option.rect = rect
        option.section = logicalIndex

        # Retrieve header text from the model and set it
        header_text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)
        option.text = str(header_text) if header_text is not None else ""

        if logicalIndex in self.sortable_columns:
            mouse_pos = QCursor.pos()
            local_mouse = self.mapFromGlobal(mouse_pos)
            if rect.contains(local_mouse):
                option.state |= QStyle.StateFlag.State_MouseOver
                option.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
                option.state |= QStyle.StateFlag.State_Sunken
            else:
                option.state &= ~QStyle.StateFlag.State_MouseOver
        else:
            option.state &= ~QStyle.StateFlag.State_MouseOver

        self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

class EventPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.empty_label = None
        self.selected_events = set()  # Track which events are checked
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header layout with title and item count
        header_layout = QHBoxLayout()
        
        title = QLabel("Events")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
        """)
        
        self.items_count = QLabel("0 items")
        self.items_count.setStyleSheet("""
            color: #9ca3af;
            font-size: 12px;
            margin-left: 8px;
            font-family: 'Segoe UI';
        """)
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(self.items_count)
        header_layout.addStretch()
    
        layout.addLayout(header_layout)

        # Create table with checkbox column
        self.table = QTableWidget()
        self.table.setColumnCount(9)  # Added a checkbox column
        headers = ["Type", "Message", "Namespace", "Involved Object", "Source", "Count", "Age", "Last Seen", ""]
        self.table.setHorizontalHeaderLabels(headers)
        
        # Use the custom header for sorting
        custom_header = EventsHeader(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(custom_header)
        self.table.setSortingEnabled(True)
        
        # Style the table
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                border: none;
                gridline-color: #2d2d2d;
                outline: none;
                color: #e2e8f0;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                outline: none;
                color: #e2e8f0;
            }
            QTableWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
            }
            QTableWidget::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                border: none;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #888888;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d2d2d;
                font-size: 12px;
            }
        """)
        
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Make table read-only
        
        # Configure column widths
       
        
        # Type column - fixed
        self.table.horizontalHeader().setSectionResizeMode(TYPE_COL, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(TYPE_COL, 80)
        
        # Message column takes the most space
        self.table.horizontalHeader().setSectionResizeMode(MESSAGE_COL, QHeaderView.ResizeMode.Stretch)
        
        # Fixed width columns
        fixed_widths = {
            NAMESPACE_COL: 120,
            INVOLVED_OBJECT_COL: 150,
            SOURCE_COL: 150,
            COUNT_COL: 60,
            AGE_COL: 80,
            LAST_SEEN_COL: 100,
            ACTIONS_COL: 40
        }
        
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        
        # Empty state label
        self.empty_label = QLabel("No events found")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            color: #9ca3af;
            font-size: 16px;
            background-color: transparent;
        """)
        self.empty_label.hide()  # Hide initially
        
        layout.addWidget(self.table)
        layout.addWidget(self.empty_label)
        
        # Install event filter to handle clicks outside the table
        self.installEventFilter(self)
        self.table.cellClicked.connect(self.handle_row_click)
        
        # Override mousePressEvent to handle selection properly
        self.table.mousePressEvent = self.custom_table_mousePressEvent

    def custom_table_mousePressEvent(self, event):
        index = self.table.indexAt(event.pos())
        if index.isValid():
            row = index.row()
            if index.column() != ACTIONS_COL:  # Skip action column
                # Toggle checkbox when clicking anywhere in the row (except actions)
                checkbox_container = self.table.cellWidget(row, 0)
                if checkbox_container:
                    for child in checkbox_container.children():
                        if isinstance(child, QCheckBox):
                            child.setChecked(not child.isChecked())
                            break
                # Select the row
                self.table.selectRow(row)
            QTableWidget.mousePressEvent(self.table, event)
        else:
            self.table.clearSelection()
            QTableWidget.mousePressEvent(self.table, event)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            pos = event.pos()
            if not self.table.geometry().contains(pos):
                self.table.clearSelection()
        return super().eventFilter(obj, event)
    def load_data(self):
        """Load event data into the table"""
        # Sample event data for Kubernetes events
        events_data = [
            ["Normal", "Started container", "default", "Pod/nginx-78f5d695b", "kubelet", "1", "10m", "21h"],
            ["Warning", "Failed to pull image", "kube-system", "Pod/dashboard-5469c", "kubelet", "3", "25m", "30h"],
            ["Normal", "Scaled deployment", "app-ns", "Deployment/web-app", "deployment-controller", "1", "1h", "23h"],
        ]
        
        # Check if data is empty
        if not events_data:
            self.update_ui([])
            return
        
        # Update UI with data
        self.update_ui(events_data)
        
        # Set up table rows
        self.table.setRowCount(len(events_data))
        
        for row, event in enumerate(events_data):
            self.table.setRowHeight(row, 40)
            
            # Extract data
            event_type = event[0]
            message = event[1]
            namespace = event[2]
            involved_object = event[3]
            source = event[4]
            count = event[5]
            age = event[6]
            last_seen = event[7]
            
            # Type column with checkbox container
            type_container = QWidget()
            type_layout = QHBoxLayout(type_container)
            type_layout.setContentsMargins(4, 0, 4, 0)
            type_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Create type label with appropriate color
            type_label = QLabel(event_type)
            type_layout.addWidget(type_label)
            type_container.setStyleSheet("background-color: transparent;")
            self.table.setCellWidget(row, TYPE_COL, type_container)
            
            # Message column
            message_item = QLabel(message)
            message_item.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Set message color based on event type
            if event_type == "Warning":
                message_item.setStyleSheet("color: #FF5252;")  # Red for warnings
            else:
                message_item.setStyleSheet("color: #e2e8f0;")  # Default light gray
                
            self.table.setCellWidget(row, MESSAGE_COL, message_item)
            
            # Namespace column
            namespace_item = QTableWidgetItem(namespace)
            namespace_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            namespace_item.setForeground(QColor("#e2e8f0"))
            self.table.setItem(row, NAMESPACE_COL, namespace_item)
            
            # Involved Object column
            involved_obj_item = QTableWidgetItem(involved_object)
            involved_obj_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            involved_obj_item.setForeground(QColor("#e2e8f0"))
            self.table.setItem(row, INVOLVED_OBJECT_COL, involved_obj_item)
            
            # Source column - display as link (blue text)
            source_item = QTableWidgetItem(source)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            source_item.setForeground(QColor("#4FC3F7"))  # Light blue for links
            self.table.setItem(row, SOURCE_COL, source_item)
            
            # Count column
            count_value = int(count) if count.isdigit() else 0
            count_item = SortableTableWidgetItem(count, count_value)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            count_item.setForeground(QColor("#e2e8f0"))
            self.table.setItem(row, COUNT_COL, count_item)
            
            # Age column
            age_value = self._parse_age_to_minutes(age)
            age_item = SortableTableWidgetItem(age, age_value)
            age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            age_item.setForeground(QColor("#e2e8f0"))
            self.table.setItem(row, AGE_COL, age_item)
            
            # Last Seen column
            last_seen_item = QTableWidgetItem(last_seen)
            last_seen_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            last_seen_item.setForeground(QColor("#e2e8f0"))
            self.table.setItem(row, LAST_SEEN_COL, last_seen_item)
            
            # Action column
            action_button = self.create_action_button(row)
            action_container = QWidget()
            action_layout = QHBoxLayout(action_container)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.addWidget(action_button)
            action_container.setStyleSheet("background-color: transparent;")
            self.table.setCellWidget(row, ACTIONS_COL, action_container)

    def _parse_age_to_minutes(self, age):
        """Parse age string to minutes for sorting"""
        if 'm' in age:
            return int(age.replace('m', ''))
        elif 'h' in age:
            return int(age.replace('h', '')) * 60
        elif 'd' in age:
            return int(age.replace('d', '')) * 1440  # 24 * 60
        else:
            try:
                return int(age)
            except ValueError:
                return 0

    def update_ui(self, data):
        """Update UI based on data availability"""
        if not data:
            self.table.hide()
            self.empty_label.show()
            self.items_count.setText("0 items")
        else:
            self.table.show()
            self.empty_label.hide()
            self.items_count.setText(f"{len(data)} items")

    #------- Action Menu -------
    def create_action_button(self, row):
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(30)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet("""
            QToolButton {
                color: #888888;
                font-size: 18px;
                background: transparent;
                padding: 2px;
                margin: 0;
                border: none;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                color: #ffffff;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(button)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                color: #ffffff;
                padding: 8px 24px 8px 36px;
                border-radius: 4px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                color: #ffffff;
            }
            QMenu::item[dangerous="true"] {
                color: #ff4444;
            }
            QMenu::item[dangerous="true"]:selected {
                background-color: rgba(255, 68, 68, 0.1);
            }
        """)
        view_action = menu.addAction("View Details")
        view_action.setIcon(QIcon("icons/view.png"))
        view_action.triggered.connect(lambda: self.handle_action("View", row))
        
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(QIcon("icons/delete.png"))
        delete_action.setProperty("dangerous", True)
        delete_action.triggered.connect(lambda: self.handle_action("Delete", row))
        
        button.setMenu(menu)
        return button

    def handle_action(self, action, row):
        # Get widgets from cells
        type_container = self.table.cellWidget(row, TYPE_COL)
        type_label = type_container.findChild(QLabel) if type_container else None
        message_container = self.table.cellWidget(row, MESSAGE_COL)
        namespace_item = self.table.item(row, NAMESPACE_COL)
        
        if type_label and message_container and namespace_item:
            event_type = type_label.text()
            event_message = message_container.text()
            namespace = namespace_item.text()
            
            if action == "View":
                print(f"Viewing event details: {event_type} in {namespace}: {event_message}")
                # Implement view details functionality
            elif action == "Delete":
                print(f"Deleting event: {event_type} in {namespace}: {event_message}")
                # Implement delete functionality
        else:
            print(f"Warning: Could not retrieve event data for {action} action on row {row}")
    def handle_row_click(self, row, column):
        if column != ACTIONS_COL:  # Don't trigger for action column
            # Get type widget
            type_container = self.table.cellWidget(row, TYPE_COL)
            type_label = type_container.findChild(QLabel) if type_container else None
            
            # Get message widget
            message_container = self.table.cellWidget(row, MESSAGE_COL)
            
            if type_label and message_container:
                event_type = type_label.text()
                event_message = message_container.text()
                self.table.selectRow(row)
                print(f"Selected event: {event_type} - {event_message}")
            else:
                print(f"Warning: Could not retrieve event data for row {row}")




# """
# Optimized implementation of the Events page with better performance
# and memory efficiency.
# """

# from PyQt6.QtWidgets import QHeaderView, QWidget, QLabel, QHBoxLayout
# from PyQt6.QtCore import Qt
# from PyQt6.QtGui import QColor

# from Workload.base_components import BaseTablePage, SortableTableWidgetItem

# class EventsPage(BaseTablePage):
#     """
#     Displays Kubernetes events with optimizations for performance and memory usage.
    
#     Optimizations:
#     1. Uses shared base components to reduce code duplication
#     2. Implements lazy widget creation
#     3. Uses efficient data structures for storage
#     4. Implements optimized sorting and filtering
#     """
    
#     # Column indices constants for better maintainability
#     TYPE_COL = 0
#     MESSAGE_COL = 1
#     NAMESPACE_COL = 2
#     INVOLVED_OBJECT_COL = 3
#     SOURCE_COL = 4
#     COUNT_COL = 5
#     AGE_COL = 6
#     LAST_SEEN_COL = 7
#     ACTIONS_COL = 8
    
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.empty_label = None
#         self.setup_page_ui()
#         self.load_data()
    
#     def setup_page_ui(self):
#         """Set up the UI components for the Events page"""
#         # Define headers and sortable columns
#         headers = ["Type", "Message", "Namespace", "Involved Object", "Source", "Count", "Age", "Last Seen", ""]
#         sortable_columns = {self.TYPE_COL, self.NAMESPACE_COL, self.INVOLVED_OBJECT_COL, 
#                             self.COUNT_COL, self.AGE_COL, self.LAST_SEEN_COL}
        
#         # Set up the base UI components
#         layout = self.setup_ui("Events", headers, sortable_columns)
        
#         # Configure column widths
#         self.configure_columns()
        
#         # Add empty state label for when no events exist
#         self.setup_empty_state(layout)
        
#         # Connect the row click handler
#         self.table.cellClicked.connect(self.handle_row_click)
    
#     def setup_empty_state(self, layout):
#         """Create the empty state message for when no events are found"""
#         self.empty_label = QLabel("No events found")
#         self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self.empty_label.setStyleSheet("""
#             color: #9ca3af;
#             font-size: 16px;
#             background-color: transparent;
#         """)
#         self.empty_label.hide()  # Hide initially
#         layout.addWidget(self.empty_label)
    
#     def configure_columns(self):
#         """Configure column widths and behaviors"""
#         # Type column - fixed width
#         self.table.horizontalHeader().setSectionResizeMode(self.TYPE_COL, QHeaderView.ResizeMode.Fixed)
#         self.table.setColumnWidth(self.TYPE_COL, 80)
        
#         # Message column takes the most space
#         self.table.horizontalHeader().setSectionResizeMode(self.MESSAGE_COL, QHeaderView.ResizeMode.Stretch)
        
#         # Fixed width columns
#         fixed_widths = {
#             self.NAMESPACE_COL: 120,
#             self.INVOLVED_OBJECT_COL: 150,
#             self.SOURCE_COL: 150,
#             self.COUNT_COL: 60,
#             self.AGE_COL: 80,
#             self.LAST_SEEN_COL: 100,
#             self.ACTIONS_COL: 40
#         }
        
#         for col, width in fixed_widths.items():
#             self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
#             self.table.setColumnWidth(col, width)
    
#     def load_data(self):
#         """Load event data into the table with optimized batch processing"""
#         # Sample event data
#         events_data = [
#             ["Normal", "Started container", "default", "Pod/nginx-78f5d695b", "kubelet", "1", "10m", "21h"],
#             ["Warning", "Failed to pull image", "kube-system", "Pod/dashboard-5469c", "kubelet", "3", "25m", "30h"],
#             ["Normal", "Scaled deployment", "app-ns", "Deployment/web-app", "deployment-controller", "1", "1h", "23h"],
#         ]
        
#         # Check if data is empty
#         if not events_data:
#             self.update_ui_for_empty_state()
#             return
        
#         # Set up table rows
#         self.table.setRowCount(len(events_data))
#         self.table.setUpdatesEnabled(False)  # Disable updates for batch processing
        
#         # Process all data at once for better performance
#         for row, event in enumerate(events_data):
#             self.populate_event_row(row, event)
        
#         # Update item count and re-enable updates
#         self.items_count.setText(f"{len(events_data)} items")
#         self.table.setUpdatesEnabled(True)
#         self.table.show()
#         self.empty_label.hide()
    
#     def update_ui_for_empty_state(self):
#         """Update UI when no data is available"""
#         self.table.hide()
#         self.empty_label.show()
#         self.items_count.setText("0 items")
    
#     def populate_event_row(self, row, event_data):
#         """Populate a single row with event data efficiently"""
#         # Set row height
#         self.table.setRowHeight(row, 40)
        
#         # Extract data
#         event_type = event_data[0]
#         message = event_data[1]
#         namespace = event_data[2]
#         involved_object = event_data[3]
#         source = event_data[4]
#         count = event_data[5]
#         age = event_data[6]
#         last_seen = event_data[7]
        
#         # Type column with label (custom widget)
#         type_container = QWidget()
#         type_layout = QHBoxLayout(type_container)
#         type_layout.setContentsMargins(4, 0, 4, 0)
#         type_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
#         type_label = QLabel(event_type)
#         type_layout.addWidget(type_label)
#         type_container.setStyleSheet("background-color: transparent;")
#         self.table.setCellWidget(row, self.TYPE_COL, type_container)
        
#         # Message column (custom label for color support)
#         message_label = QLabel(message)
#         message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
#         # Set message color based on event type
#         if event_type == "Warning":
#             message_label.setStyleSheet("color: #FF5252;")  # Red for warnings
#         else:
#             message_label.setStyleSheet("color: #e2e8f0;")  # Default light gray
            
#         self.table.setCellWidget(row, self.MESSAGE_COL, message_label)
        
#         # Create table items efficiently
#         items = [
#             # Namespace column
#             (self.NAMESPACE_COL, SortableTableWidgetItem(namespace), "center"),
            
#             # Involved Object column
#             (self.INVOLVED_OBJECT_COL, SortableTableWidgetItem(involved_object), "center"),
            
#             # Source column - display as link (blue text)
#             (self.SOURCE_COL, SortableTableWidgetItem(source), "center", QColor("#4FC3F7")),
            
#             # Count column with numeric value for sorting
#             (self.COUNT_COL, SortableTableWidgetItem(count, int(count) if count.isdigit() else 0), "center"),
            
#             # Age column with numeric value for sorting
#             (self.AGE_COL, SortableTableWidgetItem(age, self._parse_age_to_minutes(age)), "center"),
            
#             # Last Seen column
#             (self.LAST_SEEN_COL, SortableTableWidgetItem(last_seen), "center")
#         ]
        
#         # Batch process all items
#         for data in items:
#             col, item, alignment = data[:3]
#             color = data[3] if len(data) > 3 else QColor("#e2e8f0")
            
#             # Set alignment
#             if alignment == "center":
#                 item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#             else:
#                 item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
#             # Set color
#             item.setForeground(color)
            
#             # Make non-editable
#             item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
#             # Add to table
#             self.table.setItem(row, col, item)
        
#         # Add action button
#         action_button = self._create_action_button(row, [
#             {"text": "View Details", "icon": "icons/view.png", "dangerous": False},
#             {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
#         ])
#         action_container = self._create_action_container(row, action_button)
#         self.table.setCellWidget(row, self.ACTIONS_COL, action_container)
    
#     def _parse_age_to_minutes(self, age):
#         """Parse age string to minutes for sorting"""
#         if 'm' in age:
#             return int(age.replace('m', ''))
#         elif 'h' in age:
#             return int(age.replace('h', '')) * 60
#         elif 'd' in age:
#             return int(age.replace('d', '')) * 1440  # 24 * 60
#         else:
#             try:
#                 return int(age)
#             except ValueError:
#                 return 0
    
#     def handle_row_click(self, row, column):
#         """Handle row selection when a table cell is clicked"""
#         if column != self.ACTIONS_COL:  # Don't trigger for action column
#             # Get type widget
#             type_container = self.table.cellWidget(row, self.TYPE_COL)
#             type_label = type_container.findChild(QLabel) if type_container else None
            
#             # Get message widget
#             message_container = self.table.cellWidget(row, self.MESSAGE_COL)
            
#             if type_label and message_container:
#                 event_type = type_label.text()
#                 event_message = message_container.text()
#                 self.table.selectRow(row)
#                 print(f"Selected event: {event_type} - {event_message}")
    
#     def _handle_action(self, action, row):
#         """Override to handle event-specific actions"""
#         # Get widgets from cells
#         type_container = self.table.cellWidget(row, self.TYPE_COL)
#         type_label = type_container.findChild(QLabel) if type_container else None
#         message_container = self.table.cellWidget(row, self.MESSAGE_COL)
#         namespace_item = self.table.item(row, self.NAMESPACE_COL)
        
#         if type_label and message_container and namespace_item:
#             event_type = type_label.text()
#             event_message = message_container.text()
#             namespace = namespace_item.text()
            
#             if action == "View Details":
#                 print(f"Viewing event details: {event_type} in {namespace}: {event_message}")
#                 # Implement view details functionality here
#             elif action == "Delete":
#                 print(f"Deleting event: {event_type} in {namespace}: {event_message}")
#                 # Implement delete functionality here