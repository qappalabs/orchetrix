from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QHeaderView, QToolButton, QMenu, QStyle, QStyleOptionHeader
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QCursor

from UI.Styles import AppColors, AppStyles, AppConstants

class SortableTableWidgetItem(QTableWidgetItem):
    """
    Custom QTableWidgetItem that allows numeric sorting if you provide a numeric 'value'.
    Otherwise, it sorts by text.
    """
    def __init__(self, text, value=None):
        super().__init__(str(text))
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
        self.sortable_columns = {
            AppConstants.EVENTS_TABLE_COLUMNS["TYPE"],
            AppConstants.EVENTS_TABLE_COLUMNS["NAMESPACE"],
            AppConstants.EVENTS_TABLE_COLUMNS["INVOLVED_OBJECT"],
            AppConstants.EVENTS_TABLE_COLUMNS["COUNT"],
            AppConstants.EVENTS_TABLE_COLUMNS["AGE"],
            AppConstants.EVENTS_TABLE_COLUMNS["LAST_SEEN"]
        }
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

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

        header_text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)
        option.text = str(header_text) if header_text is not None else ""
        option.textAlignment = Qt.AlignmentFlag.AlignCenter

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
        self.selected_events = set()
        self.setStyleSheet(f"background-color: {AppColors.BG_DARK};")
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header layout with title and item count
        header_layout = QHBoxLayout()
        
        title = QLabel("Events")
        title.setStyleSheet(AppStyles.TITLE_STYLE)
        
        self.items_count = QLabel("0 items")
        self.items_count.setStyleSheet(AppStyles.ITEMS_COUNT_STYLE)
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(self.items_count)
        header_layout.addStretch()
    
        layout.addLayout(header_layout)

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        headers = ["Type", "Message", "Namespace", "Involved Object", "Source", "Count", "Age", "Last Seen", ""]
        self.table.setHorizontalHeaderLabels(headers)
        
        custom_header = EventsHeader(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(custom_header)
        self.table.setSortingEnabled(True)
        
        self.table.setStyleSheet(AppStyles.TABLE_STYLE)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Configure column widths
        self.table.horizontalHeader().setSectionResizeMode(AppConstants.EVENTS_TABLE_COLUMNS["TYPE"], QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(AppConstants.EVENTS_TABLE_COLUMNS["TYPE"], 80)
        self.table.horizontalHeader().setSectionResizeMode(AppConstants.EVENTS_TABLE_COLUMNS["MESSAGE"], QHeaderView.ResizeMode.Stretch)
        
        fixed_widths = {
            AppConstants.EVENTS_TABLE_COLUMNS["NAMESPACE"]: 120,
            AppConstants.EVENTS_TABLE_COLUMNS["INVOLVED_OBJECT"]: 150,
            AppConstants.EVENTS_TABLE_COLUMNS["SOURCE"]: 150,
            AppConstants.EVENTS_TABLE_COLUMNS["COUNT"]: 60,
            AppConstants.EVENTS_TABLE_COLUMNS["AGE"]: 80,
            AppConstants.EVENTS_TABLE_COLUMNS["LAST_SEEN"]: 100,
            AppConstants.EVENTS_TABLE_COLUMNS["ACTIONS"]: AppConstants.SIZES["ACTION_WIDTH"]
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
        self.empty_label.setStyleSheet(AppStyles.EMPTY_LABEL_STYLE)
        self.empty_label.hide()
        
        layout.addWidget(self.table)
        layout.addWidget(self.empty_label)
        
        self.installEventFilter(self)
        self.table.cellClicked.connect(self.handle_row_click)
        self.table.mousePressEvent = self.custom_table_mousePressEvent

    def custom_table_mousePressEvent(self, event):
        index = self.table.indexAt(event.pos())
        if index.isValid():
            row = index.row()
            if index.column() != AppConstants.EVENTS_TABLE_COLUMNS["ACTIONS"]:
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
        events_data = [
            ["Normal", "Started container", "default", "Pod/nginx-78f5d695b", "kubelet", "1", "10m", "21h"],
            ["Warning", "Failed to pull image", "kube-system", "Pod/dashboard-5469c", "kubelet", "3", "25m", "30h"],
            ["Normal", "Scaled deployment", "app-ns", "Deployment/web-app", "deployment-controller", "1", "1h", "23h"],
        ]
        
        if not events_data:
            self.update_ui([])
            return
        
        self.update_ui(events_data)
        self.table.setRowCount(len(events_data))
        
        for row, event in enumerate(events_data):
            self.table.setRowHeight(row, AppConstants.SIZES["ROW_HEIGHT"])
            
            event_type, message, namespace, involved_object, source, count, age, last_seen = event
            
            # Type column
            type_container = QWidget()
            type_layout = QHBoxLayout(type_container)
            type_layout.setContentsMargins(4, 0, 4, 0)
            type_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            type_label = QLabel(event_type)
            type_layout.addWidget(type_label)
            type_container.setStyleSheet("background-color: transparent;")
            self.table.setCellWidget(row, AppConstants.EVENTS_TABLE_COLUMNS["TYPE"], type_container)
            
            # Message column
            message_item = QLabel(message)
            message_item.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            message_item.setStyleSheet(AppStyles.MESSAGE_WARNING_STYLE if event_type == "Warning" else AppStyles.MESSAGE_NORMAL_STYLE)
            self.table.setCellWidget(row, AppConstants.EVENTS_TABLE_COLUMNS["MESSAGE"], message_item)
            
            # Namespace column
            namespace_item = QTableWidgetItem(namespace)
            namespace_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            namespace_item.setForeground(QColor(AppColors.TEXT_LIGHT))
            self.table.setItem(row, AppConstants.EVENTS_TABLE_COLUMNS["NAMESPACE"], namespace_item)
            
            # Involved Object column
            involved_obj_item = QTableWidgetItem(involved_object)
            involved_obj_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            involved_obj_item.setForeground(QColor(AppColors.TEXT_LIGHT))
            self.table.setItem(row, AppConstants.EVENTS_TABLE_COLUMNS["INVOLVED_OBJECT"], involved_obj_item)
            
            # Source column
            source_item = QTableWidgetItem(source)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            source_item.setForeground(QColor(AppColors.TEXT_LINK))
            self.table.setItem(row, AppConstants.EVENTS_TABLE_COLUMNS["SOURCE"], source_item)
            
            # Count column
            count_value = int(count) if count.isdigit() else 0
            count_item = SortableTableWidgetItem(count, count_value)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            count_item.setForeground(QColor(AppColors.TEXT_LIGHT))
            self.table.setItem(row, AppConstants.EVENTS_TABLE_COLUMNS["COUNT"], count_item)
            
            # Age column
            age_value = self._parse_age_to_minutes(age)
            age_item = SortableTableWidgetItem(age, age_value)
            age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            age_item.setForeground(QColor(AppColors.TEXT_LIGHT))
            self.table.setItem(row, AppConstants.EVENTS_TABLE_COLUMNS["AGE"], age_item)
            
            # Last Seen column
            last_seen_item = QTableWidgetItem(last_seen)
            last_seen_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            last_seen_item.setForeground(QColor(AppColors.TEXT_LIGHT))
            self.table.setItem(row, AppConstants.EVENTS_TABLE_COLUMNS["LAST_SEEN"], last_seen_item)
            
            # Action column
            action_button = self.create_action_button(row)
            action_container = QWidget()
            action_layout = QHBoxLayout(action_container)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.addWidget(action_button)
            action_container.setStyleSheet("background-color: transparent;")
            self.table.setCellWidget(row, AppConstants.EVENTS_TABLE_COLUMNS["ACTIONS"], action_container)

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

    def update_ui(self, data):
        if not data:
            self.table.hide()
            self.empty_label.show()
            self.items_count.setText("0 items")
        else:
            self.table.show()
            self.empty_label.hide()
            self.items_count.setText(f"{len(data)} items")

    def create_action_button(self, row):
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(AppConstants.SIZES["ACTION_WIDTH"])
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        menu = QMenu(button)
        menu.setStyleSheet(AppStyles.MENU_STYLE)
        
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
        type_container = self.table.cellWidget(row, AppConstants.EVENTS_TABLE_COLUMNS["TYPE"])
        type_label = type_container.findChild(QLabel) if type_container else None
        message_container = self.table.cellWidget(row, AppConstants.EVENTS_TABLE_COLUMNS["MESSAGE"])
        namespace_item = self.table.item(row, AppConstants.EVENTS_TABLE_COLUMNS["NAMESPACE"])
        
        if type_label and message_container and namespace_item:
            event_type = type_label.text()
            event_message = message_container.text()
            namespace = namespace_item.text()
            
            if action == "View":
                print(f"Viewing event details: {event_type} in {namespace}: {event_message}")
            elif action == "Delete":
                print(f"Deleting event: {event_type} in {namespace}: {event_message}")
        else:
            print(f"Warning: Could not retrieve event data for {action} action on row {row}")

    def handle_row_click(self, row, column):
        if column != AppConstants.EVENTS_TABLE_COLUMNS["ACTIONS"]:
            type_container = self.table.cellWidget(row, AppConstants.EVENTS_TABLE_COLUMNS["TYPE"])
            type_label = type_container.findChild(QLabel) if type_container else None
            message_container = self.table.cellWidget(row, AppConstants.EVENTS_TABLE_COLUMNS["MESSAGE"])
            
            if type_label and message_container:
                event_type = type_label.text()
                event_message = message_container.text()
                self.table.selectRow(row)
                print(f"Selected event: {event_type} - {event_message}")
            else:
                print(f"Warning: Could not retrieve event data for row {row}")
