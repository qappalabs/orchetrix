from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLabel, QHeaderView, QToolButton, QMenu, QComboBox, QCheckBox, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon

class SortableTableWidgetItem(QTableWidgetItem):
    """
    Custom QTableWidgetItem that allows numeric sorting if you provide a numeric 'value'.
    Otherwise, it sorts by text.
    """
    def __init__(self, text, value=None):
        super().__init__(text)
        self.value = value

    def __lt__(self, other):
        # If both items have a numeric 'value', compare numerically
        if isinstance(other, SortableTableWidgetItem) and self.value is not None and other.value is not None:
            return self.value < other.value
        return super().__lt__(other)

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

        # Header layout with title and item count
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
        
        # Sorting dropdown
        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 13px;
            margin-right: 8px;
        """)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Name")
        self.sort_combo.addItem("Namespace")
        self.sort_combo.addItem("Pods (Highest)")
        self.sort_combo.addItem("Replicas (Highest)")
        self.sort_combo.addItem("Age (Longest)")
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

        header_layout.addWidget(sort_label)
        header_layout.addWidget(self.sort_combo)
        layout.addLayout(header_layout)

        # Table
        # 8 columns total: [Checkbox] + Name + Namespace + Pods + Replicas + Age + Conditions + [Action]
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        headers = ["", "Name", "Namespace", "Pods", "Replicas", "Age", "Conditions", ""]
        self.table.setHorizontalHeaderLabels(headers)
        
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
                font-size: 12px;
            }
        """)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Configure table column sizes
        # Column 0: checkboxes
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 40)

        # Column 1: Name (stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Column 2: Namespace
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 150)

        # Column 3: Pods
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 100)

        # Column 4: Replicas
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 80)

        # Column 5: Age
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 80)

        # Column 6: Conditions
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 180)

        # Column 7: Action
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 40)
        
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

        # Create and set the select-all checkbox in the header of column 0
        select_all_checkbox = self.create_select_all_checkbox()
        self.set_header_widget(0, select_all_checkbox)

    def load_data(self):
        """
        Example data from your screenshot:
          Name: coredns
          Namespace: kube-system
          Pods: 2/2
          Replicas: 2
          Age: 70d
          Conditions: Available Progressing
        """
        self.deployments_data = [
            ["coredns", "kube-system", "2/2", "2", "70d", "Available Progressing"],
            # Add more rows if desired
            ["nginx-deploy", "default", "3/3", "3", "12d", "Available Progressing"],
        ]

        self.tablCount(len(self.deployments_data))

        for row, deployment in enumerate(self.deployments_data):
            name = deployment[0]
            namespace = deployment[1]
            pods_str = deployment[2]   # e.g. "2/2"
            replicas_str = deployment[3]
            age_str = deployment[4]
            conditions_str = deployment[5]

            # Create checkbox in column 0
            checkbox = self.create_checkbox(row, name)
            self.table.setCellWidget(row, 0, checkbox)

            # Convert numeric parts for sorting
            pods_value = 0
            try:
                pods_value = float(pods_str.split("/")[0])  # e.g. "2/2" => 2.0
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
            self.table.setCellWidget(row, 7, action_button)

        # Update items count label
        self.items_count.setText(f"{len(self.deployments_data)} items")

    #
    # -----------  Checkboxes (Select All & Per-Row)  -----------
    #
    def create_checkbox(self, row, deployment_name):
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 10px;
                height: 10px;
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
                background: #252525; /* match header background */
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
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
            row_checkbox = self.table.cellWidget(row, 0)
            if row_checkbox:
                row_checkbox.setChecked(state == Qt.CheckState.Checked.value)

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
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(widget)
        container.setFixedHeight(header.height())

        container.setParent(header)
        container.setGeometry(header.sectionPosition(col), 0, header.sectionSize(col), header.height())
        container.show()

    #
    # -----------  Action Menu  -----------
    #
    def create_action_button(self, row):
        button = QToolButton()
        button.setText("⋮")  # Three dots
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

        # Menu with actions
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
        deployment_name = self.table.item(row, 1).text()  # column 1 is Name
        if action == "Edit":
            print(f"Editing deployment: {deployment_name}")
        elif action == "Delete":
            print(f"Deleting deployment: {deployment_name}")

    #
    # -----------  Sorting  -----------
    #
    def sort_table(self, sort_by):
        """
        Sort the table based on the combo box selection.
        Columns now:
          1 - Name
          2 - Namespace
          3 - Pods
          4 - Replicas
          5 - Age
        """
        if sort_by == "Name":
            self.table.sortItems(1, Qt.SortOrder.AscendingOrder)
        elif sort_by == "Namespace":
            self.table.sortItems(2, Qt.SortOrder.AscendingOrder)
        elif sort_by == "Pods (Highest)":
            self.table.sortItems(3, Qt.SortOrder.DescendingOrder)
        elif sort_by == "Replicas (Highest)":
            self.table.sortItems(4, Qt.SortOrder.DescendingOrder)
        elif sort_by == "Age (Longest)":
            self.table.sortItems(5, Qt.SortOrder.DescendingOrder)
