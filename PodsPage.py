# from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
#                            QTableWidgetItem, QLabel, QHeaderView, QPushButton,
#                            QMenu, QToolButton, QCheckBox)
# from PyQt6.QtCore import Qt, QSize, QPoint
# from PyQt6.QtGui import QColor, QFont, QIcon

# class PodsPage(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.selected_pods = set()  # Track selected pods
#         self.setup_ui()
#         self.load_data()

#     def setup_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(16, 16, 16, 16)
#         layout.setSpacing(16)

#         # Header section
#         header = QHBoxLayout()
#         title = QLabel("Pods")
#         title.setStyleSheet("""
#             font-size: 20px;
#             font-weight: bold;
#             color: #ffffff;
#         """)
#         header.addWidget(title)
#         header.addStretch()

#         # Create table
#         self.table = QTableWidget()
#         self.table.setColumnCount(11)  # Added column for checkboxes
#         headers = ["", "Name", "Namespace", "Containers", "Restarts",
#                   "Age", "By", "Node", "QoS", "Status", ""]  # Added empty header for actions
#         self.table.setHorizontalHeaderLabels(headers)
        
#         # Style the table
#         self.table.setStyleSheet("""
#             QTableWidget {
#                 background-color: #1e1e1e;
#                 border: none;
#                 gridline-color: transparent;
#                 outline: none;  /* Remove focus outline */
#             }
#             QTableWidget::item {
#                 padding: 0;  /* Remove padding to prevent checkbox misalignment */
#                 border: none;
#                 outline: none;  /* Remove item focus outline */
#             }
#             QTableWidget::item:hover {
#                 background-color: rgba(255, 255, 255, 0.05);
#                 border-radius: 4px;
                
#             }
#             QTableWidget::item:selected {
#                 background-color: rgba(33, 150, 243, 0.2);
#                 border: none;
#             }
#             # QTableWidget::item:focus {
#             #     border: none;
#             #     outline: none;
#             #     background-color: transparent;
#             # }
#             QHeaderView::section {
#                 background-color: #252525;
#                 color: #888888;
#                 padding: 8px;
#                 border: none;
#                 border-bottom: 1px solid #2d2d2d;
#                 font-size: 12px;
#             }
#             # QToolButton {
#             #     border: none;
#             #     border-radius: 4px;
#             #     padding: 4px;
#             # }
#             # QToolButton:hover {
#             #     background-color: rgba(255, 255, 255, 0.1);
#             # }
#         """)
#         # Additional table properties
#         self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Disable focus highlighting
#         self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)  # Disable selection
        
#         # Configure table properties
#         self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
#         self.table.horizontalHeader().setStretchLastSection(False)
#         self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
#         self.table.setColumnWidth(10, 30)  # Width for action column
#         self.table.setShowGrid(True)
#         self.table.setAlternatingRowColors(True)
#         self.table.verticalHeader().setVisible(False)
        
#         # Configure table properties
#         self.table.horizontalHeader().setSectionsMovable(False)  # Prevent column moving
#         self.table.setShowGrid(True)  # Hide grid
#         self.table.setAlternatingRowColors(False)  # Disable alternating colors
#         self.table.verticalHeader().setVisible(False)  # Hide vertical header
        
#         # Make columns responsive but not resizable by user
#         self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column
        
#         # Fixed widths for other columns
#         column_widths = [40, None, 120, 100, 80, 80, 100, 120, 100, 100, 40]  # Changed first column to 40
#         for i, width in enumerate(column_widths):
#             if width is not None:
#                 self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
#                 self.table.setColumnWidth(i, width)
#             else:
#                 self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

#         select_all_checkbox = self.create_select_all_checkbox()
#         self.set_header_widget(0, select_all_checkbox)

#         layout.addLayout(header)
#         layout.addWidget(self.table)

#     def create_action_button(self, row):
#         button = QToolButton()
#         button.setText("⋮")  # Three dots
#         button.setFixedWidth(30)
#         # Set alignment programmatically instead of through stylesheet
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
        
#         # Center align the text
#         button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
#         button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

#         # Update table styling to fix cursor property
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
#                 background-color: rgba(255, 255, 255, 0.05);
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
        
#         # Set cursor programmatically
#         button.setCursor(Qt.CursorShape.PointingHandCursor)

#         # Rest of the menu creation code...
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
#                 padding: 8px 24px 8px 36px;  /* Added left padding for icons */
#                 border-radius: 4px;
#                 font-size: 13px;
#             }
#             QMenu::item:selected {
#             background-color: rgba(33, 150, 243, 0.2);
#             color: #ffffff;
#             }
#             QMenu::item[dangerous="true"] {
#                 color: #ff4444;
#             }
#             QMenu::item[dangerous="true"]:selected {
#                 background-color: rgba(255, 68, 68, 0.1);
#             }
#         """)
        
#         # Create Edit action with pencil icon
#         edit_action = menu.addAction("Edit")
#         edit_action.setIcon(QIcon("icons/edit.png"))  # Add your edit icon path
#         edit_action.triggered.connect(lambda: self.handle_action("Edit", row))

#         # Create Delete action with trash icon
#         delete_action = menu.addAction("Delete")
#         delete_action.setIcon(QIcon("icons/delete.png"))  # Add your delete icon path
#         delete_action.setProperty("dangerous", True)  # Set property instead of stylesheet
#         delete_action.triggered.connect(lambda: self.handle_action("Delete", row))

#         button.setMenu(menu)
#         button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
#         return button

#     def handle_action(self, action, row):
#         pod_name = self.table.item(row, 1).text()
#         if action == "Edit":
#             print(f"Editing pod: {pod_name}")
#             # Add edit logic here
#         elif action == "Delete":
#             print(f"Deleting pod: {pod_name}")
#             # Add delete logic here

#     def create_checkbox(self, row, pod_name):
#         checkbox = QCheckBox()
#         checkbox.setStyleSheet("""
#             QCheckBox {
#                 spacing: 5px;
#                 padding-left: 5px;  /* Add padding to center the checkbox */
#                 padding-bottom: 20px;  /* Add padding to center the checkbox */
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
#                 image: url(check.png);  /* Optional: Add a checkmark image */
#             }
#             QCheckBox::indicator:hover {
#                 border-color: #888888;
#             }
#         """)
        
#         # Set fixed size for the checkbox
#         checkbox.setFixedSize(40, 40)
#         checkbox.stateChanged.connect(lambda state: self.handle_checkbox_change(state, pod_name))
#         return checkbox

#     def handle_checkbox_change(self, state, pod_name):
#         if state == Qt.CheckState.Checked.value:
#             self.selected_pods.add(pod_name)
#         else:
#             self.selected_pods.discard(pod_name)
#         print(f"Selected pods: {self.selected_pods}")

#     def create_select_all_checkbox(self):
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
#         checkbox.stateChanged.connect(self.handle_select_all)
#         return checkbox

#     def handle_select_all(self, state):
#         for row in range(self.table.rowCount()):
#             checkbox = self.table.cellWidget(row, 0)
#             if checkbox:
#                 checkbox.setChecked(state == Qt.CheckState.Checked.value)

#     def load_data(self):
#         pods_data = [
#             ["kube-proxy-crs/r4w", "kube-system", "5", "6", "69d", "DaemonSet", "docker-desktop", "BestEffort", "Running"],
#             ["coredns-7db6lf44-d7nwq", "kube-system", "1", "0", "69d", "ReplicaSet", "docker-desktop", "Burstable", "Running"],
#             ["coredns-7db6lf44-dj8lp", "kube-system", "1", "0", "69d", "ReplicaSet", "docker-desktop", "Burstable", "Running"],
#             ["vpnkit-controller", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
#             ["etcd-docker-desktop", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
#             ["kube-apiserver-docker-desktop", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
#             ["kube-controller-manager-docker-desktop", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
#             ["storage-provisioner", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"],
#             ["kube-scheduler-docker-desktop", "kube-system", "1", "0", "69d", "Node", "docker-desktop", "Burstable", "Running"]
#         ]

#         self.table.setRowCount(len(pods_data))
        
#         for row, pod in enumerate(pods_data):
#             # Add checkbox first
#             checkbox = self.create_checkbox(row, pod[0])
#             self.table.setCellWidget(row, 0, checkbox)
            
#             # Add rest of the data (shifted one column to the right)
#             for col, value in enumerate(pod):
#                 item = QTableWidgetItem(value)
#                 item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
#                 item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
#                 # Status column styling (now at index 9)
#                 if col == 8:  # Status column
#                     if value == "Running":
#                         item.setForeground(QColor("#4CAF50"))
                
#                 self.table.setItem(row, col + 1, item)  # Shift one column right
            
#             # Add action button (now at last column)
#             action_button = self.create_action_button(row)
#             self.table.setCellWidget(row, 10, action_button)
#         # Add click handler for rows
#             # self.table.cellClicked.connect(self.handle_row_click)
#             # pod_name = self.table.item(row, 1).text()
#             # print(f"Clicked pod: {pod_name}")
#             # Add your pod click handling logic here

#     def set_header_widget(self, col, widget):


#         header = self.table.horizontalHeader()
        
#         container = QWidget()
#         layout = QHBoxLayout(container)
#         layout.setContentsMargins(12, 0, 0, 0)  # Adjusted left margin to match checkbox padding
#         layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         layout.addWidget(widget)
        
#         header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
#         header.resizeSection(col, 40)  # Match the column width
        
#         self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))
#         container.setFixedHeight(header.height())
#         container.setParent(header)
#         container.setGeometry(header.sectionPosition(col), 0, 
#                              header.sectionSize(col), header.height())
#         container.show()


from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QLabel, QHeaderView, QPushButton,
                           QMenu, QToolButton, QCheckBox)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QColor, QFont, QIcon

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

        # Header section
        header = QHBoxLayout()
        title = QLabel("Pods")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
        """)
        header.addWidget(title)
        header.addStretch()

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(11)  # Added column for checkboxes
        headers = ["", "Name", "Namespace", "Containers", "Restarts",
                  "Age", "By", "Node", "QoS", "Status", ""]  # Added empty header for actions
        self.table.setHorizontalHeaderLabels(headers)
        
        # Style the table
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                border: none;
                gridline-color: transparent;
                outline: none;  /* Remove focus outline */
            }
            QTableWidget::item {
                padding: 0;  /* Remove padding to prevent checkbox misalignment */
                border: none;
                outline: none;  /* Remove item focus outline */
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
        # Additional table properties
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Disable focus highlighting
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)  # Disable selection
        
        # Configure table properties
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(10, 30)  # Width for action column
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # Configure table properties
        self.table.horizontalHeader().setSectionsMovable(False)  # Prevent column moving
        self.table.setShowGrid(True)  # Hide grid
        self.table.setAlternatingRowColors(False)  # Disable alternating colors
        self.table.verticalHeader().setVisible(False)  # Hide vertical header
        
        # Make columns responsive but not resizable by user
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column
        
        # Fixed widths for other columns
        column_widths = [40, None, 120, 100, 80, 80, 100, 120, 100, 100, 40]  # Changed first column to 40
        for i, width in enumerate(column_widths):
            if width is not None:
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(i, width)
            else:
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Set up select all checkbox
        select_all_checkbox = self.create_select_all_checkbox()
        self.set_header_widget(0, select_all_checkbox)

        # Set sortable columns
        self.table.horizontalHeader().setSortIndicatorShown(True)
        
        # Connect header click to sort handler
        self.table.horizontalHeader().sectionClicked.connect(self.handle_header_click)

        layout.addLayout(header)
        layout.addWidget(self.table)

    def handle_header_click(self, logicalIndex):
        # Only enable sorting for specific columns
        sortable_columns = [2, 3, 5, 7, 9]  # Namespace,Container, Age, Node, Status
        if logicalIndex not in sortable_columns:
            # If not a sortable column, disable sorting
            self.table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
            self.table.setSortingEnabled(False)
            return
        else:
            self.table.setSortingEnabled(True)

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

        # Update table styling to fix cursor property
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
            QHeaderView::section {
                background-color: #252525;
                color: #888888;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d2d2d;
                font-size: 12px;
            }
        """)
        
        # Set cursor programmatically
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Rest of the menu creation code...
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
        edit_action.setIcon(QIcon("icons/edit.png"))  # Add your edit icon path
        edit_action.triggered.connect(lambda: self.handle_action("Edit", row))

        # Create Delete action with trash icon
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(QIcon("icons/delete.png"))  # Add your delete icon path
        delete_action.setProperty("dangerous", True)  # Set property instead of stylesheet
        delete_action.triggered.connect(lambda: self.handle_action("Delete", row))

        button.setMenu(menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        return button

    def handle_action(self, action, row):
        pod_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing pod: {pod_name}")
            # Add edit logic here
        elif action == "Delete":
            print(f"Deleting pod: {pod_name}")
            # Add delete logic here

    def create_checkbox(self, row, pod_name):
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
                padding-left: 5px;  /* Add padding to center the checkbox */
                padding-bottom: 20px;  /* Add padding to center the checkbox */
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
                image: url(check.png);  /* Optional: Add a checkmark image */
            }
            QCheckBox::indicator:hover {
                border-color: #888888;
            }
        """)
        
        # Set fixed size for the checkbox
        checkbox.setFixedSize(40, 40)
        checkbox.stateChanged.connect(lambda state: self.handle_checkbox_change(state, pod_name))
        return checkbox

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
        checkbox.stateChanged.connect(self.handle_select_all)
        return checkbox

    def handle_select_all(self, state):
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(state == Qt.CheckState.Checked.value)

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
            # Add checkbox first
            checkbox = self.create_checkbox(row, pod[0])
            self.table.setCellWidget(row, 0, checkbox)
            
            # Add rest of the data (shifted one column to the right)
            for col, value in enumerate(pod):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Make age column sortable with correct data
                if col == 4:  # Age column
                    # Extract number of days for sorting
                    days = int(value.replace('d', ''))
                    item.setData(Qt.ItemDataRole.UserRole, days)
                
                # Status column styling (now at index 9)
                if col == 8:  # Status column
                    if value == "Running":
                        item.setForeground(QColor("#4CAF50"))
                
                self.table.setItem(row, col + 1, item)  # Shift one column right
            
            # Add action button (now at last column)
            action_button = self.create_action_button(row)
            self.table.setCellWidget(row, 10, action_button)

    def set_header_widget(self, col, widget):
        header = self.table.horizontalHeader()
        
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 0, 0, 0)  # Adjusted left margin to match checkbox padding
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget)
        
        # Apply background color to match the header background
        container.setStyleSheet("""
            background-color: #252525;
        """)
        
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(col, 40)  # Match the column width
        
        self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))
        container.setFixedHeight(header.height())
        container.setParent(header)
        container.setGeometry(header.sectionPosition(col), 0, 
                             header.sectionSize(col), header.height())
        container.show()

    # Helper method to update sorting icons
    def update_sort_indicators(self):
        # Add arrow indicators to sortable columns
        header = self.table.horizontalHeader()
        for col in [2, 3, 5, 7, 9]:  # Namespace, Containers,Age, Node, Status
            label_text = self.table.horizontalHeaderItem(col).text()
            if not "↑" in label_text and not "↓" in label_text:
                self.table.horizontalHeaderItem(col).setText(f"{label_text} ↕")