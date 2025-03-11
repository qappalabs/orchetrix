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
        self.select_all_checkbox = None
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
        index = self.table.indexAt(event.pos())
        if index.isValid():
            row = index.row()
            if index.column() != 7:  # Skip action column
                # Toggle checkbox when clicking anywhere in the row
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

            # If any checkbox is unchecked, uncheck the select-all checkbox
            if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
                # Block signals to prevent infinite recursion
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setChecked(False)
                self.select_all_checkbox.blockSignals(False)

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
        self.select_all_checkbox = checkbox
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





# from PyQt6.QtWidgets import (
#     QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
#     QLabel, QHeaderView, QToolButton, QCheckBox, QComboBox, QApplication,
#     QStyle, QStyleOptionHeader,QMenu
# )
# from PyQt6.QtCore import Qt, QSize, QPoint
# from PyQt6.QtGui import QColor, QIcon, QCursor
# import datetime

# # Custom QTableWidgetItem that supports numeric sorting.
# class SortableTableWidgetItem(QTableWidgetItem):
#     def __init__(self, text, value=0):
#         super().__init__(text)
#         self.value = value

#     def __lt__(self, other):
#         if hasattr(other, 'value'):
#             return self.value < other.value
#         return super().__lt__(other)

# # Custom header that enables sorting only on specific columns and shows a hover indicator.
# class PodsHeader(QHeaderView):
#     def __init__(self, orientation, parent=None):
#         super().__init__(orientation, parent)
#         self.sortable_columns = {1, 2, 3, 4, 5, 7, 9}
#         self.setSectionsClickable(True)
#         self.setHighlightSections(True)

#     def mousePressEvent(self, event):
#         logicalIndex = self.logicalIndexAt(event.pos())
#         if logicalIndex in self.sortable_columns:
#             super().mousePressEvent(event)
#         else:
#             event.ignore()

#     def paintSection(self, painter, rect, logicalIndex):
#         option = QStyleOptionHeader()
#         self.initStyleOption(option)
#         option.rect = rect
#         option.section = logicalIndex
#         header_text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)
#         option.text = str(header_text) if header_text is not None else ""

#         if logicalIndex in self.sortable_columns:
#             mouse_pos = QCursor.pos()
#             local_mouse = self.mapFromGlobal(mouse_pos)
#             if rect.contains(local_mouse):
#                 option.state |= QStyle.StateFlag.State_MouseOver
#                 option.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
#                 option.state |= QStyle.StateFlag.State_Sunken
#             else:
#                 option.state &= ~QStyle.StateFlag.State_MouseOver
#         else:
#             option.state &= ~QStyle.StateFlag.State_MouseOver

#         self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

# # Main widget that displays pod information.
# class PodsPage(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.selected_pods = set()  # Track selected pods
#         self.select_all_checkbox = None
#         self.setup_ui()
#         self.load_data()

#     def setup_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(16, 16, 16, 16)
#         layout.setSpacing(16)

#         # Header section with title and sorting controls.
#         header = QHBoxLayout()
#         title = QLabel("Pods")
#         title.setStyleSheet("""
#             font-size: 20px;
#             font-weight: bold;
#             color: #ffffff;
#         """)
#         self.items_count = QLabel("0 items")
#         self.items_count.setStyleSheet("""
#             color: #9ca3af;
#             font-size: 12px;
#             margin-left: 8px;
#             font-family: 'Segoe UI';
#         """)
#         self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
#         header.addWidget(title)
#         header.addWidget(self.items_count)
#         header.addStretch()

#         # Sorting dropdown.
#         sort_label = QLabel("Sort by:")
#         sort_label.setStyleSheet("""
#             color: #e2e8f0;
#             font-size: 13px;
#             margin-right: 8px;
#         """)
#         self.sort_combo = QComboBox()
#         self.sort_combo.addItems(["Name", "Namespace", "Containers (Highest)", "Restarts (Highest)", "Age (Newest)"])
#         self.sort_combo.setStyleSheet("""
#             QComboBox {
#                 background-color: #2d2d2d;
#                 color: #e2e8f0;
#                 border: 1px solid #444444;
#                 border-radius: 4px;
#                 padding: 4px 12px;
#                 min-width: 150px;
#             }
#             QComboBox::drop-down {
#                 subcontrol-origin: padding;
#                 subcontrol-position: center right;
#                 width: 20px;
#                 border-left: none;
#             }
#             QComboBox::down-arrow {
#                 image: none;
#                 width: 0;
#             }
#             QComboBox QAbstractItemView {
#                 background-color: #2d2d2d;
#                 color: #e2e8f0;
#                 border: 1px solid #444444;
#                 selection-background-color: #2196F3;
#             }
#         """)
        
#         # Create table with 11 columns.
#         self.table = QTableWidget()
#         self.table.setColumnCount(11)  # Column 0 for checkboxes; column 10 for actions.
#         headers = ["", "Name", "Namespace", "Containers", "Restarts", "Age", "By", "Node", "QoS", "Status", ""]
#         self.table.setHorizontalHeaderLabels(headers)

#         # Apply custom header for sorting.
#         pods_header = PodsHeader(Qt.Orientation.Horizontal, self.table)
#         self.table.setHorizontalHeader(pods_header)
#         self.table.setSortingEnabled(True)
#         self.table.setStyleSheet("""
#             QTableWidget {
#                 background-color: #1e1e1e;
#                 border: none;
#                 gridline-color: #2d2d2d;
#                 outline: none;
#             }
#             QTableWidget::item {
#                 padding: 8px;
#                 border: none;
#                 outline: none;
#             }
#             QTableWidget::item:hover {
#                 background-color: transparent;
#                 border-radius: 4px;
#             }
#             QTableWidget::item:selected {
#                 background-color: rgba(33, 150, 243, 0.2);
#                 border: none;
#             }
#             QHeaderView::section {
#                 background-color: #252525;
#                 color: #888888;
#                 padding: 8px;
#                 border: none;
#                 border-bottom: 1px solid #2d2d2d;
#                 font-size: 12px;
#             }
#         """)
#         self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
#         self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
#         self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

#         # Configure column widths.
#         self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
#         self.table.setColumnWidth(0, 40)
#         self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
#         for col in [2, 6, 7, 8, 9]:
#             self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
#         fixed_widths = {3: 100, 4: 80, 5: 80, 10: 40}
#         for col, width in fixed_widths.items():
#             self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
#             self.table.setColumnWidth(col, width)

#         self.table.setShowGrid(True)
#         self.table.setAlternatingRowColors(False)
#         self.table.verticalHeader().setVisible(False)

#         # Insert select-all checkbox in column 0 header.
#         select_all_checkbox = self.create_select_all_checkbox()
#         self.set_header_widget(0, select_all_checkbox)

#         # Override mouse press event to handle selection.
#         self.installEventFilter(self)
#         self.table.mousePressEvent = self.custom_table_mousePressEvent

#         # Error label (hidden by default)
#         self.error_label = QLabel()
#         self.error_label.setStyleSheet("color: red; font-size: 14px;")
#         self.error_label.hide()

#         # Assemble layout.
#         main_layout = QVBoxLayout()
#         main_layout.addLayout(header)
#         main_layout.addWidget(self.error_label)
#         main_layout.addWidget(self.table)
#         layout.addLayout(main_layout)

    # def custom_table_mousePressEvent(self, event):
    #     index = self.table.indexAt(event.pos())
    #     if index.isValid():
    #         row = index.row()
    #         if index.column() != 7:  # Skip action column
    #             # Toggle checkbox when clicking anywhere in the row
    #             checkbox_container = self.table.cellWidget(row, 0)
    #             if checkbox_container:
    #                 for child in checkbox_container.children():
    #                     if isinstance(child, QCheckBox):
    #                         child.setChecked(not child.isChecked())
    #                         break
    #             # Select the row
    #             self.table.selectRow(row)
    #         QTableWidget.mousePressEvent(self.table, event)
    #     else:
    #         self.table.clearSelection()
    #         QTableWidget.mousePressEvent(self.table, event)

#     def eventFilter(self, obj, event):
#         if event.type() == event.Type.MouseButtonPress:
#             if not self.table.geometry().contains(event.pos()):
#                 self.table.clearSelection()
#         return super().eventFilter(obj, event)


#     def create_action_button(self, row):
#         button = QToolButton()
#         button.setText("⋮")
#         button.setFixedWidth(30)
#         button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
#         button.setStyleSheet("""
#             QToolButton {
#                 color: #888888;
#                 font-size: 18px;
#                 background: transparent;
#                 padding: 2px;
#                 margin: 0;
#                 border: none;
#                 font-weight: bold;
#             }
#             QToolButton:hover {
#                 background-color: rgba(255, 255, 255, 0.1);
#                 border-radius: 3px;
#                 color: #ffffff;
#             }
#             QToolButton::menu-indicator {
#                 image: none;
#             }
#         """)
#         button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
#         button.setCursor(Qt.CursorShape.PointingHandCursor)
#         menu = QMenu(button)
#         menu.setStyleSheet("""
#             QMenu {
#                 background-color: #2d2d2d;
#                 border: 1px solid #3d3d3d;
#                 border-radius: 4px;
#                 padding: 4px;
#             }
#             QMenu::item {
#                 color: #ffffff;
#                 padding: 8px 24px 8px 36px;
#                 border-radius: 4px;
#                 font-size: 13px;
#             }
#             QMenu::item:selected {
#                 background-color: rgba(33, 150, 243, 0.2);
#                 color: #ffffff;
#             }
#             QMenu::item[dangerous="true"] {
#                 color: #ff4444;
#             }
#             QMenu::item[dangerous="true"]:selected {
#                 background-color: rgba(255, 68, 68, 0.1);
#             }
#         """)
#         edit_action = menu.addAction("Edit")
#         edit_action.setIcon(QIcon("icons/edit.png"))
#         edit_action.triggered.connect(lambda: self.handle_action("Edit", row))
#         delete_action = menu.addAction("Delete")
#         delete_action.setIcon(QIcon("icons/delete.png"))
#         delete_action.setProperty("dangerous", True)
#         delete_action.triggered.connect(lambda: self.handle_action("Delete", row))
#         button.setMenu(menu)
#         return button

#     def handle_action(self, action, row):
#         pod_name = self.table.item(row, 1).text()
#         if action == "Edit":
#             print(f"Editing pod: {pod_name}")
#         elif action == "Delete":
#             print(f"Deleting pod: {pod_name}")

#     def create_checkbox(self, row, pod_name):
#         checkbox = QCheckBox()
#         checkbox.setStyleSheet("""
#             QCheckBox {
#                 spacing: 5px;
#                 background: transparent;
#             }
#             QCheckBox::indicator {
#                 width: 16px;
#                 height: 16px;
#                 border: 2px solid #666666;
#                 border-radius: 3px;
#                 background: transparent;
#             }
#             QCheckBox::indicator:checked {
#                 background-color: #0095ff;
#                 border-color: #0095ff;
#             }
#             QCheckBox::indicator:hover {
#                 border-color: #888888;
#             }
#         """)
#         checkbox.stateChanged.connect(lambda state: self.handle_checkbox_change(state, pod_name))
#         return checkbox

#     def create_checkbox_container(self, row, pod_name):
#         container = QWidget()
#         container.setStyleSheet("background-color: transparent;")
#         layout = QHBoxLayout(container)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         checkbox = self.create_checkbox(row, pod_name)
#         layout.addWidget(checkbox)
#         return container

#     def handle_checkbox_change(self, state, pod_name):
#         if state == Qt.CheckState.Checked.value:
#             self.selected_pods.add(pod_name)
#         else:
#             self.selected_pods.discard(pod_name)
#       # If any checkbox is unchecked, uncheck the select-all checkbox
#         if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
#               # Block signals to prevent infinite recursion
#             self.select_all_checkbox.blockSignals(True)
#             self.select_all_checkbox.setChecked(False)
#             self.select_all_checkbox.blockSignals(False)
#         print(f"Selected pods: {self.selected_pods}")

#     def create_select_all_checkbox(self):
#         checkbox = QCheckBox()
#         checkbox.setStyleSheet("""
#             QCheckBox {
#                 spacing: 5px;
#                 background-color: #252525;
#             }
#             QCheckBox::indicator {
#                 width: 16px;
#                 height: 16px;
#                 border: 2px solid #666666;
#                 border-radius: 3px;
#                 background: transparent;
#             }
#             QCheckBox::indicator:checked {
#                 background-color: #0095ff;
#                 border-color: #0095ff;
#             }
#             QCheckBox::indicator:hover {
#                 border-color: #888888;
#             }
#         """)
#         checkbox.stateChanged.connect(self.handle_select_all)
#         self.select_all_checkbox = checkbox 
#         return checkbox

#     def handle_select_all(self, state):
#         for row in range(self.table.rowCount()):
#             checkbox_container = self.table.cellWidget(row, 0)
#             if checkbox_container:
#                 for child in checkbox_container.children():
#                     if isinstance(child, QCheckBox):
#                         child.setChecked(state == Qt.CheckState.Checked.value)
#                         break

#     def fetch_pods_data(self):
#         """
#         Attempts to fetch live pod data from a Kubernetes cluster.
#         Raises an exception if data retrieval fails.
#         """
#         from kubernetes import client, config
#         config.load_kube_config()  # Ensure your kubeconfig is set up properly.
#         v1 = client.CoreV1Api()
#         pods = v1.list_pod_for_all_namespaces(watch=False)
#         pods_data = []
#         now = datetime.datetime.now(datetime.timezone.utc)
#         for pod in pods.items:
#             name = pod.metadata.name
#             namespace = pod.metadata.namespace
#             containers = str(len(pod.spec.containers)) if pod.spec.containers else "0"
#             restarts = str(sum(cs.restart_count for cs in (pod.status.container_statuses or [])))
#             age_delta = now - pod.metadata.creation_timestamp
#             age = f"{age_delta.days}d"
#             owner = pod.metadata.owner_references[0].kind if pod.metadata.owner_references else ""
#             node = pod.spec.node_name if pod.spec.node_name else ""
#             qos = pod.status.qos_class if pod.status.qos_class else ""
#             status = pod.status.phase if pod.status.phase else ""
#             pods_data.append([name, namespace, containers, restarts, age, owner, node, qos, status])
#         return pods_data

#     def load_data(self):
#         try:
#             pods_data = self.fetch_pods_data()
#         except Exception as e:
#             self.display_error_message(f"Error fetching pods data: {e}")
#             return

#         # Hide error message if data is fetched successfully.
#         self.error_label.hide()
#         self.table.show()

#         self.table.setRowCount(len(pods_data))
#         for row, pod in enumerate(pods_data):
#             self.table.setRowHeight(row, 40)
#             # Column 0: Checkbox
#             checkbox_container = self.create_checkbox_container(row, pod[0])
#             self.table.setCellWidget(row, 0, checkbox_container)
#             # Columns 1-9: Pod data
#             for col, value in enumerate(pod):
#                 cell_col = col + 1  # shift by one due to checkbox column
#                 if col in (2, 3, 4):  # Numeric columns: Containers, Restarts, Age
#                     try:
#                         num = int(value.replace('d', '')) if col == 4 else int(value)
#                     except Exception:
#                         num = 0
#                     item = SortableTableWidgetItem(value, num)
#                 else:
#                     item = QTableWidgetItem(value)
#                 if col in (2, 3, 4, 8):
#                     item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
#                 else:
#                     item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
#                 item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
#                 if col == 8 and value == "Running":
#                     item.setForeground(QColor("#4CAF50"))
#                 else:
#                     item.setForeground(QColor("#e2e8f0"))
#                 self.table.setItem(row, cell_col, item)
#             # Column 10: Action button.
#             action_button = self.create_action_button(row)
#             self.table.setCellWidget(row, 10, action_button)
#         self.table.cellClicked.connect(self.handle_row_click)
#         self.items_count.setText(f"{len(pods_data)} items")

#     def display_error_message(self, message):
#         """
#         Displays an error message on the UI and hides the pods table.
#         """
#         self.table.hide()
#         self.error_label.setText(message)
#         self.error_label.show()

#     def set_header_widget(self, col, widget):
#         header = self.table.horizontalHeader()
#         header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
#         header.resizeSection(col, 40)
#         self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))
#         container = QWidget()
#         container.setStyleSheet("background-color: #252525;")
#         container_layout = QHBoxLayout(container)
#         container_layout.setContentsMargins(0, 0, 0, 0)
#         container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         container_layout.addWidget(widget)
#         container.setFixedHeight(header.height())
#         container.setParent(header)
#         container.setGeometry(header.sectionPosition(col), 0, header.sectionSize(col), header.height())
#         container.show()

#     def handle_row_click(self, row, column):
#         if column != 10:
#             self.table.selectRow(row)
#             print(f"Selected pod: {self.table.item(row, 1).text()}")

# # if __name__ == "__main__":
# #     import sys
# #     app = QApplication(sys.argv)
# #     pods_page = PodsPage()
# #     pods_page.resize(1200, 600)
# #     pods_page.show()
# #     sys.exit(app.exec())
