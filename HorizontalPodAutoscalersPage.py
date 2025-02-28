from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QLabel, QHeaderView, QPushButton,
                             QMenu, QToolButton, QCheckBox, QComboBox, QStyle, QStyleOptionHeader)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QColor, QFont, QIcon, QCursor

#------------------------------------------------------------------
# CustomHeader: Controls which columns are sortable with visual indicators
#------------------------------------------------------------------
class CustomHeader(QHeaderView):
    """
    A custom header that only enables sorting for a subset of columns
    and shows a hover sort indicator arrow on those columns.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        # Define which columns will be sortable
        self.sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8}  # Name, Namespace, Metrics, Min Pods, Max Pods, Replicas, Age, Status
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
        # Retrieve header text from the model and set it in the option.
        header_text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)
        option.text = str(header_text) if header_text is not None else ""

        if logicalIndex in self.sortable_columns:
            mouse_pos = QCursor.pos()
            local_mouse = self.mapFromGlobal(mouse_pos)
            if rect.contains(local_mouse):
                option.state |= QStyle.StateFlag.State_MouseOver
                # Use the Qt6 enum value for sort indicator (SortDown for descending)
                option.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
                option.state |= QStyle.StateFlag.State_Sunken
            else:
                option.state &= ~QStyle.StateFlag.State_MouseOver
        else:
            option.state &= ~QStyle.StateFlag.State_MouseOver

        self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

class SortableTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that can be sorted with values"""
    def __init__(self, text, value=0):
        super().__init__(text)
        self.value = value

    def __lt__(self, other):
        if hasattr(other, 'value'):
            return self.value < other.value
        return super().__lt__(other)

class HorizontalPodAutoscalersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_horizontal_pod_autoscalers = set()  # Track selected horizontal pod autoscalers
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header section
        header = QHBoxLayout()
        title = QLabel("Horizontal Pod Autoscalers")
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

        header.addWidget(title)
        header.addWidget(self.items_count)
        header.addStretch()

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(10)  # Checkbox, Name, Namespace, Age, Actions
        headers = ["", "Name", "Namespace", "Metrics", "Min Pods", "Max Pods", "Replicas", "Age", "Status", ""]
        self.table.setHorizontalHeaderLabels(headers)

        # Use the custom header to control sorting
        custom_header = CustomHeader(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(custom_header)
        self.table.setSortingEnabled(True)

        # Style the table
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                border: none;
                gridline-color: #2d2d2d;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                outline: none;
            }
            QTableWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
            }
            QTableWidget::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                border: none;
            }
            QTableWidget::item:focus {
                border: none;
                outline: none;
                background-color: transparent;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #888888;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d2d2d;
                font-size: 14px;
            }
            QHeaderView::section:hover {
                background-color: #2d2d2d;
            }
            QToolButton {
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)

        # Configure selection behavior
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Configure table properties
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column
        self.table.horizontalHeader().setStretchLastSection(False)

        # Set fixed width for specific columns
        column_widths = [40, None, 120, 100, 80, 80, 80, 80, 100, 40]  # Adjusted for 10 columns
        for i, width in enumerate(column_widths):
            if width is not None:  # Apply fixed width to all columns except Name (which stretches)
                if i != 1:  # Skip Name column which is set to stretch
                    self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                    self.table.setColumnWidth(i, width)

        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)

        # Temporarily disable sorting during data loading
        self.table.setSortingEnabled(False)

        # Set up select all checkbox
        select_all_checkbox = self.create_select_all_checkbox()
        self.set_header_widget(0, select_all_checkbox)

        # Install event filter to handle clicks outside the table
        self.installEventFilter(self)

        # Override mousePressEvent to handle selections properly
        self.table.mousePressEvent = self.custom_table_mousePressEvent

        layout.addLayout(header)
        layout.addWidget(self.table)

        # Add click handler for rows
        self.table.cellClicked.connect(self.handle_row_click)

    def custom_table_mousePressEvent(self, event):
        """
        Custom handler for table mouse press events to control selection behavior
        """
        # Get the item at the click position
        item = self.table.itemAt(event.pos())
        index = self.table.indexAt(event.pos())

        # Check if we're clicking on a cell that has a widget (checkbox or action button)
        if index.isValid() and (index.column() == 0 or index.column() == 9):
            # Let the event pass through to the widget without selecting the row
            QTableWidget.mousePressEvent(self.table, event)
        elif item:
            # Clicking on a regular table cell - allow selection
            QTableWidget.mousePressEvent(self.table, event)
        else:
            # Clicking on empty space in table - clear selection
            self.table.clearSelection()
            QTableWidget.mousePressEvent(self.table, event)

    def eventFilter(self, obj, event):
        """
        Handle clicks outside the table to clear row selection
        """
        if event.type() == event.Type.MouseButtonPress:
            # Get the position of the mouse click
            pos = event.pos()
            if not self.table.geometry().contains(pos):
                # If click is outside the table, clear the selection (but keep checkboxes)
                self.table.clearSelection()
        return super().eventFilter(obj, event)

    def handle_row_click(self, row, column):
        if column != 9:  # Don't trigger for action button column
            horizontal_pod_autoscalers_name = self.table.item(row, 1).text()
            print(f"Clicked horizontal pod autoscalers: {horizontal_pod_autoscalers_name}")
            # Add your horizontal pod autoscalers click handling logic here

    def create_action_button(self, row):
        button = QToolButton()
        button.setText("⋮")  # Three dots
        button.setFixedWidth(30)
        # Set alignment programmatically instead of through stylesheet
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

        # Center align the text
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create menu with actions
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
                padding: 8px 24px 8px 36px;  /* Added left padding for icons */
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

        # Create View action with eye icon
        view_action = menu.addAction("View")
        view_action.setIcon(QIcon("icons/view.png"))
        view_action.triggered.connect(lambda: self.handle_action("View", row))

        # Create Edit action with pencil icon
        edit_action = menu.addAction("Edit")
        edit_action.setIcon(QIcon("icons/edit.png"))
        edit_action.triggered.connect(lambda: self.handle_action("Edit", row))

        # Create Delete action with trash icon
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(QIcon("icons/delete.png"))
        delete_action.setProperty("dangerous", True)
        delete_action.triggered.connect(lambda: self.handle_action("Delete", row))

        button.setMenu(menu)

        # Create a container for the action button to prevent selection
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(button)
        action_container.setStyleSheet("background-color: transparent;")

        return action_container

    def handle_action(self, action, row):
        horizontal_pod_autoscalers_name = self.table.item(row, 1).text()
        if action == "View":
            print(f"Viewing horizontal pod autoscalers: {horizontal_pod_autoscalers_name}")
            # Add view logic here
        elif action == "Edit":
            print(f"Editing horizontal pod autoscalers: {horizontal_pod_autoscalers_name}")
            # Add edit logic here
        elif action == "Delete":
            print(f"Deleting horizontal pod autoscalers: {horizontal_pod_autoscalers_name}")
            # Add delete logic here

    def create_checkbox(self, row, horizontal_pod_autoscalers_name):
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #666666;
                border-radius: 3px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #0095ff;
                border-color: #0095ff;
            }
            QCheckBox::indicator:hover {
                border-color: #888888;
            }
        """)

        checkbox.stateChanged.connect(lambda state: self.handle_checkbox_change(state, horizontal_pod_autoscalers_name))
        return checkbox

    def create_checkbox_container(self, row, horizontal_pod_autoscalers_name):
        """Create a container widget for the checkbox to prevent row selection"""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        checkbox = self.create_checkbox(row, horizontal_pod_autoscalers_name)
        layout.addWidget(checkbox)

        return container

    def handle_checkbox_change(self, state, horizontal_pod_autoscalers_name):
        if state == Qt.CheckState.Checked.value:
            self.selected_horizontal_pod_autoscalers.add(horizontal_pod_autoscalers_name)
        else:
            self.selected_horizontal_pod_autoscalers.discard(horizontal_pod_autoscalers_name)
        print(f"Selected horizontal pod autoscalers: {self.selected_horizontal_pod_autoscalers}")

    def create_select_all_checkbox(self):
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
                background-color: #252525;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #666666;
                border-radius: 3px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #0095ff;
                border-color: #0095ff;
            }
            QCheckBox::indicator:hover {
                border-color: #888888;
            }
        """)
        checkbox.stateChanged.connect(self.handle_select_all)
        return checkbox

    def handle_select_all(self, state):
        # Check/uncheck all row checkboxes
        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                # Find the checkbox within the container
                for child in checkbox_container.children():
                    if isinstance(child, QCheckBox):
                        child.setChecked(state == Qt.CheckState.Checked.value)
                        break

    def load_data(self):
        # Sample data for horizontal pod autoscalers
        horizontal_pod_autoscalers_data = [
            ["default-quota", "default", "CPU/80%", "1", "10", "3", "71d", "Healthy"],
            ["dev-quota", "dev", "Memory/70%", "2", "8", "5", "45d", "Healthy"],
            ["system-quota", "kube-system", "CPU/60%", "3", "12", "6", "71d", "Scaling"],
            ["test-quota", "test", "CPU/90%", "1", "5", "4", "30d", "Healthy"],
            ["production-quota", "production", "Memory/85%", "5", "20", "10", "71d", "Warning"]
        ]

        self.table.setRowCount(len(horizontal_pod_autoscalers_data))

        for row, hpa in enumerate(horizontal_pod_autoscalers_data):
            # Set row height
            self.table.setRowHeight(row, 40)

            # Add checkbox in a container to prevent selection issues
            checkbox_container = self.create_checkbox_container(row, hpa[0])
            self.table.setCellWidget(row, 0, checkbox_container)

            # Name column (column 1)
            item_name = QTableWidgetItem(hpa[0])
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_name.setForeground(QColor("#e2e8f0"))
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, item_name)

            # Namespace column (column 2)
            item_namespace = QTableWidgetItem(hpa[1])
            item_namespace.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_namespace.setForeground(QColor("#e2e8f0"))
            item_namespace.setFlags(item_namespace.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_namespace)

            # Metrics column (column 3)
            item_metrics = QTableWidgetItem(hpa[2])
            item_metrics.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_metrics.setForeground(QColor("#e2e8f0"))
            item_metrics.setFlags(item_metrics.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item_metrics)

            # Min Pods column (column 4)
            item_min_pods = QTableWidgetItem(hpa[3])
            item_min_pods.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_min_pods.setForeground(QColor("#e2e8f0"))
            item_min_pods.setFlags(item_min_pods.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item_min_pods)

            # Max Pods column (column 5)
            item_max_pods = QTableWidgetItem(hpa[4])
            item_max_pods.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_max_pods.setForeground(QColor("#e2e8f0"))
            item_max_pods.setFlags(item_max_pods.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, item_max_pods)

            # Replicas column (column 6)
            item_replicas = QTableWidgetItem(hpa[5])
            item_replicas.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_replicas.setForeground(QColor("#e2e8f0"))
            item_replicas.setFlags(item_replicas.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 6, item_replicas)

            # Age column (column 7)
            days = int(hpa[6].replace('d', ''))
            item_age = SortableTableWidgetItem(hpa[6], days)
            item_age.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_age.setForeground(QColor("#e2e8f0"))
            item_age.setFlags(item_age.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 7, item_age)

            # Status column (column 8)
            item_status = QTableWidgetItem(hpa[7])
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Set status color based on value
            if hpa[7] == "Healthy":
                item_status.setForeground(QColor("#399704"))  # Green
            elif hpa[7] == "Warning":
                item_status.setForeground(QColor("#d32e1a"))  # Yellow
            elif hpa[7] == "Scaling":
                item_status.setForeground(QColor("#0d91b1"))  # Blue
            else:
                item_status.setForeground(QColor("#e2e8f0"))  # Default

            item_status.setFlags(item_status.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 8, item_status)

            # Action button column (column 9)
            action_button = self.create_action_button(row)
            self.table.setCellWidget(row, 9, action_button)

        # Update items count label
        self.items_count.setText(f"{len(horizontal_pod_autoscalers_data)} items")

        # Re-enable sorting after data is loaded
        self.table.setSortingEnabled(True)

    def set_header_widget(self, col, widget):
        """
        Place a custom widget (like a 'select all' checkbox) into the horizontal header.
        """
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(col, 40)

        # Replace default header text with an empty string
        self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))

        # Position the widget
        # (We embed it in a container so we can manage layout easily)
        container = QWidget()
        container.setStyleSheet("background-color: #252525;") # Match header background
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(widget)
        container.setFixedHeight(header.height())

        container.setParent(header)
        container.setGeometry(header.sectionPosition(col), 0, header.sectionSize(col), header.height())
        container.show()