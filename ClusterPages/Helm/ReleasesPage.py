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

class PersistentVolumeClaimsHeader(QHeaderView):
    """
    A custom header that enables sorting only for specific columns (here, columns 1-5)
    and displays a hover sort indicator arrow on those columns.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        # Define which columns are sortable: 1 (Name), 2 (Namespace), 3 (Chart),  4 (Revision),  7 (Status), 8 (Updated)
        self.sortable_columns = {1, 2, 3, 4,7, 8}
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

class ReleasesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_releases = set()  # Track which deployments are checked
        self.select_all_checkbox = None
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header layout with title, item count, and sort drop-down.
        header_layout = QHBoxLayout()
        
        title = QLabel("Persistent Volume Claims")
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

        # Table: 8 columns total: [Checkbox] + Name + Namespace + Chart + Revision + Version + App Version +Status + Updated + [Action]
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        headers = ["", "Name", "Namespace", "Chart", "Revision", "Version", "App Version","Status", "Updated", "⋮"]
        self.table.setHorizontalHeaderLabels(headers)
        
        # Use the custom header for selective header-based sorting.
        custom_header = PersistentVolumeClaimsHeader(Qt.Orientation.Horizontal, self.table)
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
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        # self.table.setColumnWidth(2, 150)

        # Column 3: Storage class (fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        # self.table.setColumnWidth(3, 100)

        # Column 4: Size (fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        # self.table.setColumnWidth(3, 100)
       
        # Column 5:  Pods (fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        # self.table.setColumnWidth(5, 80)
       
       # Column 6: Age (fixed)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
       

        # Column 7: Status (fixed)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
     

         # Column 8: Updated (fixed)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
       
        # Column 9: Action (fixed)  
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(9, 40)
        
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
        index = self.table.indexAt(event.pos())
        if index.isValid():
            row = index.row()
            if index.column() != 8:  # Skip action column
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

    def load_data(self):
        """
        Example data:
          Name: docker.io-hostpath
          Namespace: kube-system
          Storage class:<none>
          Size:<none>
          Pods:<none>
          Age:<none>
          Status:<none>
          updated:<none>
        """
        self.ingress_classes_data = [
            ["docker.io-hostpath", "kube-system", "<none>", "<none>", "<none>", "<none>", "<none>","<none>"],
            ["docker.io-hostpath", "kube-system", "<none>", "<none>", "<none>", "<none>", "<none>","<none>"],
        ]
        self.table.setRowCount(len(self.ingress_classes_data))

        for row, ingress_classes in enumerate(self.ingress_classes_data):
            self.table.setRowHeight(row, 40)
            name = ingress_classes[0]
            namespace = ingress_classes[1]
            chart = ingress_classes[2]
            revision = ingress_classes[3]
            version = ingress_classes[4]
            app_version = ingress_classes[5]
            status = ingress_classes[6]
            updated = ingress_classes[7]

            # Create checkbox in column 0
            checkbox_container = self.create_checkbox_container(row, name)
            self.table.setCellWidget(row, 0, checkbox_container)

            # age_value = 0
            # try:
            #     age_value = float(age_str.replace("d", ""))
            # except:
            #     pass

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

            # Chart -> column 3
            item_chart = QTableWidgetItem(chart)
            item_chart.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_chart.setForeground(QColor("#e2e8f0"))
            item_chart.setFlags(item_chart.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item_chart)

            # Revision -> column 4
            item_revision = QTableWidgetItem(revision)
            item_revision.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_revision.setForeground(QColor("#e2e8f0"))
            item_revision.setFlags(item_revision.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item_revision)

            # Version -> column 5
            item_version = QTableWidgetItem(version)
            item_version.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_version.setForeground(QColor("#e2e8f0"))
            item_version.setFlags(item_version.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, item_version)

            # App Version -> column 6
            item_app_version = QTableWidgetItem(app_version)
            item_app_version.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_app_version.setForeground(QColor("#e2e8f0"))
            item_app_version.setFlags(item_app_version.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 6, item_app_version)

            # Status -> column 7
            item_status = QTableWidgetItem(status)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if item_status.text() == "Active":
                item_status.setForeground(QColor("#4caf50"))
            else:
                item_status.setForeground(QColor("#cc0606"))
            item_status.setFlags(item_status.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 7, item_status)

            # Updated -> column 8
            item_updated = QTableWidgetItem(updated)
            item_updated.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_updated.setForeground(QColor("#e2e8f0"))
            item_updated.setFlags(item_updated.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 8, item_updated)


            # Action -> column 8
            action_button = self.create_action_button(row)
            action_container = QWidget()
            action_layout = QHBoxLayout(action_container)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.addWidget(action_button)
            action_container.setStyleSheet("background-color: transparent;")
            self.table.setCellWidget(row, 9, action_container)

        self.table.cellClicked.connect(self.handle_row_click)
        self.items_count.setText(f"{len(self.ingress_classes_data)} items")

    #------- Checkbox Helpers -------
    def create_checkbox(self, row, Releases):
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
        checkbox.stateChanged.connect(lambda s: self.handle_checkbox_change(s, Releases))
        return checkbox

    def create_checkbox_container(self, row, Releases):
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = self.create_checkbox(row, Releases)
        layout.addWidget(checkbox)
        return container

    def handle_checkbox_change(self, state, Releases):
        if state == Qt.CheckState.Checked.value:
            self.selected_releases.add(Releases)
        else:
            self.selected_releases.discard(Releases)

            # If any checkbox is unchecked, uncheck the select-all checkbox
            if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
                # Block signals to prevent infinite recursion
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setChecked(False)
                self.select_all_checkbox.blockSignals(False)


        print("Selected Releases:", self.selected_releases)

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
        Releases = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing Releases: {Releases}")
        elif action == "Delete":
            print(f"Deleting Releases: {Releases}")

    #------- Row Selection -------
    def select_releases(self, row):
        self.table.selectRow(row)
        print(f"Selected Releases: {self.table.item(row, 1).text()}")

    def handle_row_click(self, row, column):
        if column != 7:
            self.select_releases(row)