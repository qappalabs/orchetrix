from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QLabel, QHeaderView, QPushButton,
                           QMenu, QToolButton, QCheckBox, QComboBox)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QColor, QFont, QIcon

class SortableTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that can be sorted with values"""
    def __init__(self, text, value=0):
        super().__init__(text)
        self.value = value
        
    def __lt__(self, other):
        if hasattr(other, 'value'):
            return self.value < other.value
        return super().__lt__(other)

class ConfigMapsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_config_maps = set()  # Track selected config maps
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header section with sorting dropdown
        header = QHBoxLayout()
        title = QLabel("Config Maps")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
        """)
        
        self.items_count = QLabel("11 items")
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
        self.table.setColumnCount(6)  # Checkbox, Name, Namespace, Keys, Age, Actions
        headers = ["", "Name", "Namespace", "Keys", "Age", ""]
        self.table.setHorizontalHeaderLabels(headers)
        
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
                /* Remove hover highlighting */
                background-color: transparent;
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
        """)
        
        # Configure selection behavior
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Configure table properties
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 40)  # Width for action column
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        
        # Fixed widths for columns
        column_widths = [40, None, 120, 200, 80, 40]
        for i, width in enumerate(column_widths):
            if i != 1:  # Skip the Name column which is set to stretch
                if width is not None:
                    self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                    self.table.setColumnWidth(i, width)
        
        # Disable the built-in sorting
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

    def custom_table_mousePressEvent(self, event):
        """
        Custom handler for table mouse press events to control selection behavior
        """
        # Get the item at the click position
        item = self.table.itemAt(event.pos())
        index = self.table.indexAt(event.pos())
        
        # Check if we're clicking on a cell that has a widget (checkbox or action button)
        if index.isValid() and (index.column() == 0 or index.column() == 5):
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

    def sort_table(self, sort_by):
        """Sort the table based on the selected criteria"""
        if sort_by == "Name":
            self.table.sortItems(1, Qt.SortOrder.AscendingOrder)
        elif sort_by == "Namespace":
            self.table.sortItems(2, Qt.SortOrder.AscendingOrder)
        elif sort_by == "Age (Newest)":
            self.table.sortItems(4, Qt.SortOrder.AscendingOrder)

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
        config_map_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing config map: {config_map_name}")
            # Add edit logic here
        elif action == "Delete":
            print(f"Deleting config map: {config_map_name}")
            # Add delete logic here

    def create_checkbox(self, row, config_map_name):
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
        
        checkbox.stateChanged.connect(lambda state: self.handle_checkbox_change(state, config_map_name))
        return checkbox

    def create_checkbox_container(self, row, config_map_name):
        """Create a container widget for the checkbox to prevent row selection"""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        checkbox = self.create_checkbox(row, config_map_name)
        layout.addWidget(checkbox)
        
        return container

    def handle_checkbox_change(self, state, config_map_name):
        if state == Qt.CheckState.Checked.value:
            self.selected_config_maps.add(config_map_name)
        else:
            self.selected_config_maps.discard(config_map_name)
        print(f"Selected config maps: {self.selected_config_maps}")

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
        # Data from the image
        config_maps_data = [
            ["cluster-info", "kube-public", "kubeconfig", "71d"],
            ["coredns", "kube-system", "Corefile", "71d"],
            ["extension-apiserver-authentication", "kube-system", "client-ca-file, requestheader-allowed-names, requestheader", "71d"],
            ["kube-apiserver-legacy-service-account-token-tra", "kube-system", "since", "71d"],
            ["kube-proxy", "kube-system", "config.conf, kubeconfig.conf", "71d"],
            ["kube-root-ca.crt", "default", "ca.crt", "71d"],
            ["kube-root-ca.crt", "kube-node-lease", "ca.crt", "71d"],
            ["kube-root-ca.crt", "kube-public", "ca.crt", "71d"],
            ["kube-root-ca.crt", "kube-system", "ca.crt", "71d"],
            ["kubeadm-config", "kube-system", "ClusterConfiguration", "71d"],
            ["kubelet-config", "kube-system", "kubelet", "71d"]
        ]

        self.table.setRowCount(len(config_maps_data))
        
        for row, config_map in enumerate(config_maps_data):
            # Set row height
            self.table.setRowHeight(row, 40)
            
            # Add checkbox in a container to prevent selection issues
            checkbox_container = self.create_checkbox_container(row, config_map[0])
            self.table.setCellWidget(row, 0, checkbox_container)
            
            # Add rest of the data
            for col, value in enumerate(config_map):
                # Skip value extraction for the checkbox already handled
                cell_col = col + 1
                
                # Use SortableTableWidgetItem for columns that need sorting
                if col == 3:  # Age column
                    # Extract number for proper sorting (e.g., "71d" -> 71)
                    days = int(value.replace('d', ''))
                    item = SortableTableWidgetItem(value, days)
                else:
                    item = QTableWidgetItem(value)
                
                # Set alignment based on column
                if col == 3:  # Age column
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setForeground(QColor("#e2e8f0"))
                
                self.table.setItem(row, cell_col, item)
            
            # Add action button
            action_button = self.create_action_button(row)
            self.table.setCellWidget(row, 5, action_button)

        # Update items count label
        self.items_count.setText(f"{len(config_maps_data)} items")

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