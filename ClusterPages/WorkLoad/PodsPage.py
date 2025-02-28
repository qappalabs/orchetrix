from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QHeaderView, QPushButton, QMenu, QToolButton, QCheckBox, QComboBox, QApplication, 
    QStyle, QStyleOptionHeader
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QColor, QFont, QIcon, QCursor
import random, datetime

class SortableTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that can be sorted with values"""
    def __init__(self, text, value=0):
        super().__init__(text)
        self.value = value
        
    def __lt__(self, other):
        if hasattr(other, 'value'):
            return self.value < other.value
        return super().__lt__(other)

class PodsHeader(QHeaderView):
    """
    Custom header that enables sorting only for specific columns (by header click)
    and shows a hover sort indicator arrow.
    
    In this example, the following columns are sortable:
      - Column 1: Name
      - Column 2: Namespace
      - Column 3: Containers
      - Column 4: Restarts
      - Column 5: Age
      - Column 7: Node
      - Column 9: Status
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.sortable_columns = {1, 2, 3, 4, 5, 7, 9}
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

class PodsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_pods = set()  # Track selected pods
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header section with sorting dropdown
        header = QHBoxLayout()
        title = QLabel("Pods")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
        """)
        self.items_count = QLabel("9 items")
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
        
        # Add sorting dropdown
        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 13px;
            margin-right: 8px;
        """)
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Name")
        self.sort_combo.addItem("Namespace")
        self.sort_combo.addItem("Containers (Highest)")
        self.sort_combo.addItem("Restarts (Highest)")
        self.sort_combo.addItem("Age (Newest)")
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #e2e8f0;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 12px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: none;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e2e8f0;
                border: 1px solid #444444;
                selection-background-color: #2196F3;
            }
        """)
        self.sort_combo.currentTextChanged.connect(self.sort_table)
        header.addWidget(sort_label)
        header.addWidget(self.sort_combo)

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(11)  # Added column for checkboxes
        headers = ["", "Name", "Namespace", "Containers", "Restarts", "Age", "By", "Node", "QoS", "Status", ""]
        self.table.setHorizontalHeaderLabels(headers)
        
        # Use custom header for sorting (header clicks)
        pods_header = PodsHeader(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(pods_header)
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
        
        # Configure column widths:
        # Column 0: Checkbox (fixed)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)
        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        # Fixed widths for remaining columns.
        fixed_widths = {3:100, 4:80, 5:80, 10:40}
        for col, width in fixed_widths.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        
        # Set up select-all checkbox in header column 0.
        select_all_checkbox = self.create_select_all_checkbox()
        self.set_header_widget(0, select_all_checkbox)
        
        self.installEventFilter(self)
        self.table.mousePressEvent = self.custom_table_mousePressEvent

        # Add header and table to layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(header)
        main_layout.addWidget(self.table)
        layout.addLayout(main_layout)

    def custom_table_mousePressEvent(self, event):
        item = self.table.itemAt(event.pos())
        index = self.table.indexAt(event.pos())
        if index.isValid() and (index.column() == 0 or index.column() == 10):
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

    def sort_table(self, sort_by):
        """Sort the table based on the selected criteria from the dropdown."""
        if sort_by == "Name":
            self.table.sortItems(1, Qt.SortOrder.AscendingOrder)
        elif sort_by == "Namespace":
            self.table.sortItems(2, Qt.SortOrder.AscendingOrder)
        elif sort_by == "Containers (Highest)":
            self.table.sortItems(3, Qt.SortOrder.DescendingOrder)
        elif sort_by == "Restarts (Highest)":
            self.table.sortItems(4, Qt.SortOrder.DescendingOrder)
        elif sort_by == "Age (Newest)":
            self.table.sortItems(5, Qt.SortOrder.AscendingOrder)

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
        pod_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing pod: {pod_name}")
        elif action == "Delete":
            print(f"Deleting pod: {pod_name}")

    def create_checkbox(self, row, pod_name):
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
        checkbox.stateChanged.connect(lambda state: self.handle_checkbox_change(state, pod_name))
        return checkbox

    def create_checkbox_container(self, row, pod_name):
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = self.create_checkbox(row, pod_name)
        layout.addWidget(checkbox)
        return container

    def handle_checkbox_change(self, state, pod_name):
        if state == Qt.CheckState.Checked.value:
            self.selected_pods.add(pod_name)
        else:
            self.selected_pods.discard(pod_name)
        print(f"Selected pods: {self.selected_pods}")

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

    def load_data(self):
        pods_data = [
            ["kube-proxy-crs/r4w", "kube-system", "5", "6", "69d", "DaemonSet", "docker-desktop", "BestEffort", "Running"],
            ["coredns-7db6lf44-d7nwq", "kube-system", "1", "0", "69d", "ReplicaSet", "docker-desktop", "Burstable", "Running"],
            ["coredns-7db6lf44-dj8lp", "kube-system", "1", "0", "69d", "ReplicaSet", "docker-desktop", "Burstable", "Running"],
            ["vpnkit-controller", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
            ["etcd-docker-desktop", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
            ["kube-apiserver-docker-desktop", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
            ["kube-controller-manager-docker-desktop", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
            ["storage-provisioner", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
            ["kube-scheduler-docker-desktop", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"]
        ]

        self.table.setRowCount(len(pods_data))
        
        for row, pod in enumerate(pods_data):
            self.table.setRowHeight(row, 40)
            # Column 0: Checkbox
            checkbox_container = self.create_checkbox_container(row, pod[0])
            self.table.setCellWidget(row, 0, checkbox_container)
            
            for col, value in enumerate(pod):
                cell_col = col + 1
                if col == 2:  # Containers column
                    try:
                        num = int(value)
                    except:
                        num = 0
                    item = SortableTableWidgetItem(value, num)
                elif col == 3:  # Restarts column
                    try:
                        num = int(value)
                    except:
                        num = 0
                    item = SortableTableWidgetItem(value, num)
                elif col == 4:  # Age column
                    try:
                        num = int(value.replace('d', ''))
                    except:
                        num = 0
                    item = SortableTableWidgetItem(value, num)
                else:
                    item = QTableWidgetItem(value)
                
                if col in [2, 3, 4, 8]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                if col == 8 and value == "Running":
                    item.setForeground(QColor("#4CAF50"))
                else:
                    item.setForeground(QColor("#e2e8f0"))
                
                self.table.setItem(row, cell_col, item)
            
            action_button = self.create_action_button(row)
            self.table.setCellWidget(row, 10, action_button)

        self.table.cellClicked.connect(self.handle_row_click)
        self.items_count.setText(f"{len(pods_data)} items")

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

    def handle_row_click(self, row, column):
        if column != 10:
            self.table.selectRow(row)
            print(f"Selected pod: {self.table.item(row, 1).text()}")
