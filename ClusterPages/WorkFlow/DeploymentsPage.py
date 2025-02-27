from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QHeaderView, QToolButton, QMenu, QComboBox, QCheckBox, QApplication, QStyle, QStyleOptionHeader
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QCursor, QPainter, QPen, QLinearGradient, QPainterPath, QBrush
import random, datetime

class SortableTableWidgetItem(QTableWidgetItem):
    """
    Custom QTableWidgetItem that allows numeric sorting if you provide a numeric 'value'.
    Otherwise, it sorts by text.
    """
    def __init__(self, text, value=None):
        super().__init__(text)
        self.value = value

    def __lt__(self, other):
        if isinstance(other, SortableTableWidgetItem) and self.value is not None and other.value is not None:
            return self.value < other.value
        return super().__lt__(other)

class DeploymentsHeader(QHeaderView):
    """
    A custom header that enables sorting only for specific columns (here, columns 1-5)
    and displays a hover sort indicator arrow on those columns.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        # Define which columns are sortable: 1 (Name), 2 (Namespace), 3 (Pods), 4 (Replicas), 5 (Age)
        self.sortable_columns = {1, 2, 3, 4, 5}
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
                # Use the Qt6 enum value for sort indicator arrow (SortDown for descending)
                option.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
                option.state |= QStyle.StateFlag.State_Sunken
            else:
                option.state &= ~QStyle.StateFlag.State_MouseOver
        else:
            option.state &= ~QStyle.StateFlag.State_MouseOver

        self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

class DeploymentsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_deployments = set()  # Track which deployments are checked
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header layout with title, item count, and sort drop-down.
        header_layout = QHBoxLayout()
        
        title = QLabel("Deployments")
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

        # Table: 8 columns total: [Checkbox] + Name + Namespace + Pods + Replicas + Age + Conditions + [Action]
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        headers = ["", "Name", "Namespace", "Pods", "Replicas", "Age", "Conditions", ""]
        self.table.setHorizontalHeaderLabels(headers)
        
        # Use the custom header for selective header-based sorting.
        custom_header = DeploymentsHeader(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(custom_header)
        self.table.setSortingEnabled(True)
        
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
                background-color: transparent;
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
        
        # Configure table column sizes.
        # Column 0: Checkboxes
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Column 2: Namespace (fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 150)
        # Column 3: Pods (fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 100)
        # Column 4: Replicas (fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 80)
        # Column 5: Age (fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 80)
        # Column 6: Conditions (fixed)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 180)
        # Column 7: Action (fixed)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 40)
        
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table)
        
        # Create and set the select-all checkbox in the header of column 0.
        select_all_checkbox = self.create_select_all_checkbox()
        self.set_header_widget(0, select_all_checkbox)
        
        # Install event filter to handle clicks outside the table.
        self.installEventFilter(self)
        
        # Override mousePressEvent to handle selection properly.
        self.table.mousePressEvent = self.custom_table_mousePressEvent

    def custom_table_mousePressEvent(self, event):
        item = self.table.itemAt(event.pos())
        index = self.table.indexAt(event.pos())
        if index.isValid() and (index.column() == 0 or index.column() == 7):
            QTableWidget.mousePressEvent(self.table, event)
        elif item:
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
        """
        Example data:
          Name: coredns
          Namespace: kube-system
          Pods: 2/2
          Replicas: 2
          Age: 70d
          Conditions: Available Progressing
        """
        self.deployments_data = [
            ["coredns", "kube-system", "2/2", "2", "70d", "Available Progressing"],
            ["nginx-deploy", "default", "3/3", "3", "12d", "Available Progressing"],
        ]
        self.table.setRowCount(len(self.deployments_data))

        for row, deployment in enumerate(self.deployments_data):
            self.table.setRowHeight(row, 40)
            name = deployment[0]
            namespace = deployment[1]
            pods_str = deployment[2]
            replicas_str = deployment[3]
            age_str = deployment[4]
            conditions_str = deployment[5]

            # Create checkbox in column 0
            checkbox_container = self.create_checkbox_container(row, name)
            self.table.setCellWidget(row, 0, checkbox_container)

            # Convert numeric parts for sorting
            pods_value = 0
            try:
                pods_value = float(pods_str.split("/")[0])
            except:
                pass

            replicas_value = 0
            try:
                replicas_value = float(replicas_str)
            except:
                pass

            age_value = 0
            try:
                age_value = float(age_str.replace("d", ""))
            except:
                pass

            # Name -> column 1
            item_name = QTableWidgetItem(name)
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_name.setForeground(QColor("#e2e8f0"))
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, item_name)

            # Namespace -> column 2
            item_namespace = QTableWidgetItem(namespace)
            item_namespace.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_namespace.setForeground(QColor("#e2e8f0"))
            item_namespace.setFlags(item_namespace.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_namespace)

            # Pods -> column 3
            item_pods = SortableTableWidgetItem(pods_str, pods_value)
            item_pods.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_pods.setForeground(QColor("#e2e8f0"))
            item_pods.setFlags(item_pods.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item_pods)

            # Replicas -> column 4
            item_replicas = SortableTableWidgetItem(replicas_str, replicas_value)
            item_replicas.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_replicas.setForeground(QColor("#e2e8f0"))
            item_replicas.setFlags(item_replicas.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item_replicas)

            # Age -> column 5
            item_age = SortableTableWidgetItem(age_str, age_value)
            item_age.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_age.setForeground(QColor("#e2e8f0"))
            item_age.setFlags(item_age.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, item_age)

            # Conditions -> column 6
            item_conditions = QTableWidgetItem(conditions_str)
            item_conditions.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if "Available" in conditions_str:
                item_conditions.setForeground(QColor("#4CAF50"))
            else:
                item_conditions.setForeground(QColor("#e2e8f0"))
            item_conditions.setFlags(item_conditions.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 6, item_conditions)

            # Action -> column 7
            action_button = self.create_action_button(row)
            action_container = QWidget()
            action_layout = QHBoxLayout(action_container)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.addWidget(action_button)
            action_container.setStyleSheet("background-color: transparent;")
            self.table.setCellWidget(row, 7, action_container)

        self.table.cellClicked.connect(self.handle_row_click)
        self.items_count.setText(f"{len(self.deployments_data)} items")

    #------- Checkbox Helpers -------
    def create_checkbox(self, row, deployment_name):
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
        checkbox.stateChanged.connect(lambda s: self.handle_checkbox_change(s, deployment_name))
        return checkbox

    def create_checkbox_container(self, row, deployment_name):
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = self.create_checkbox(row, deployment_name)
        layout.addWidget(checkbox)
        return container

    def handle_checkbox_change(self, state, deployment_name):
        if state == Qt.CheckState.Checked.value:
            self.selected_deployments.add(deployment_name)
        else:
            self.selected_deployments.discard(deployment_name)
        print("Selected deployments:", self.selected_deployments)

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
        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                for child in checkbox_container.children():
                    if isinstance(child, QCheckBox):
                        child.setChecked(state == Qt.CheckState.Checked.value)
                        break

    def set_header_widget(self, col, widget):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(col, 40)
        self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))
        container = QWidget()
        container.setStyleSheet("background-color: #252525;")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(widget)
        container.setFixedHeight(header.height())
        container.setParent(header)
        container.setGeometry(header.sectionPosition(col), 0, header.sectionSize(col), header.height())
        container.show()

    #------- Action Menu -------
    def create_action_button(self, row):
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(30)
        # Use Qt.ToolButtonStyle.ToolButtonTextOnly in PyQt6
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
        edit_action = menu.addAction("Edit")
        edit_action.setIcon(QIcon("icons/edit.png"))
        edit_action.triggered.connect(lambda: self.handle_action("Edit", row))
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(QIcon("icons/delete.png"))
        delete_action.setProperty("dangerous", True)
        delete_action.triggered.connect(lambda: self.handle_action("Delete", row))
        button.setMenu(menu)
        return button

    def handle_action(self, action, row):
        deployment_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing deployment: {deployment_name}")
        elif action == "Delete":
            print(f"Deleting deployment: {deployment_name}")

    #------- Row Selection -------
    def select_deployment(self, row):
        self.table.selectRow(row)
        print(f"Selected deployment: {self.table.item(row, 1).text()}")

    def handle_row_click(self, row, column):
        if column != 7:
            self.select_deployment(row)

