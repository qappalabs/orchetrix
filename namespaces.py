import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLabel, QFrame, QTabWidget, QGridLayout, QSizePolicy,
                           QGraphicsDropShadowEffect, QMenu, QToolButton, QToolTip, QLineEdit, 
                           QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QEvent, QTimer, QPoint, QRect
from PyQt6.QtGui import (QIcon, QFont, QColor, QPalette, QPixmap, QPainter, QLinearGradient, 
                       QGradient, QShortcut, QAction, QGuiApplication, QActionGroup)

class NavMenuDropdown(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                padding: 1px 16px;
                border-radius: 4px;
                margin: 2px 5px;
                color: #e0e0e0;
                font-size: 14px;
            }
            QMenu::item:selected {
                background-color: rgba(33, 150, 243, 0.15);
                color: #ffffff;
            }
            QMenu::item[selected="true"] {
                background-color: rgba(33, 150, 243, 0.3);
                color: #ffffff;
            }
            QMenu::item:selected[selected="true"] {
                background-color: rgba(33, 150, 243, 0.4);
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #444444;
                margin: 5px 10px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

class NavIconButton(QToolButton):
    def __init__(self, icon, text, active=False, has_dropdown=False, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.icon_text = icon
        self.item_text = text
        self.is_active = active
        self.has_dropdown = has_dropdown
        self.dropdown_open = False
        self.dropdown_menu = None
        self.selected_item = None
        self.active_by_child = False
        
        self.bg_dark = "#1a1a1a"
        self.accent_blue = "#2196F3"
        self.accent_light_blue = "#64B5F6"
        self.text_light = "#f0f0f0"
        self.text_secondary = "#888888"
        
        self.setup_ui()
        if self.has_dropdown:
            self.setup_dropdown()
            
    def setup_ui(self):
        self.setFixedSize(40, 40)
        self.setText(self.icon_text)
        self.setToolTip(self.item_text)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 16))
        self.setAutoRaise(True)
        self.update_style()
        self.clicked.connect(self.activate)
        if self.has_dropdown:
            self.clicked.connect(self.show_dropdown)
        self.installEventFilter(self)
            
    def setup_dropdown(self):
        self.dropdown_menu = NavMenuDropdown(self.parent_window)
        title_action = QAction(f"{self.icon_text} {self.item_text}", self)
        title_action.setEnabled(False)
        self.dropdown_menu.addAction(title_action)
        self.dropdown_menu.addSeparator()
        
        menu_items = []
        if self.item_text == "Workloads":
            menu_items = ["Overview", "Pods", "Deployments", "Daemon Sets", 
                        "Stateful Sets", "Replica Sets", "Replication Controllers",
                        "Jobs", "Cron Jobs"]
        elif self.item_text == "Config":
            menu_items = ["Config Maps", "Secrets", "Resource Quotas", "Limit Ranges",
                        "Horizontal Pod Autoscalers", "Pod Disruption Budgets",
                        "Priority Classes", "Runtime Classes", "Leases"]
        elif self.item_text == "Network":
            menu_items = ["Services", "Endpoints", "Ingresses", "Ingress Classes",
                        "Network Policies"]
        elif self.item_text == "Storage":
            menu_items = ["Persistent Volume Claims", "Persistent Volumes", 
                        "Storage Classes"]
        elif self.item_text == "Helm":
            menu_items = ["Charts", "Releases"]
        elif self.item_text == "Access Control":
            menu_items = ["Service Accounts", "Cluster Roles", "Roles",
                        "Cluster Role Bindings", "Role Bindings"]
        elif self.item_text == "Custom Resources":
            menu_items = ["Definitions"]

        for item in menu_items:
            action = QAction(item, self.dropdown_menu)
            action.setData(item)
            self.dropdown_menu.addAction(action)
            action.triggered.connect(lambda checked, i=item: self.handle_menu_action(i))
    
    def handle_menu_action(self, item):
        if hasattr(self.parent_window, "reset_all_buttons_and_dropdowns"):
            self.parent_window.reset_all_buttons_and_dropdowns()
        
        self.selected_item = item
        self.active_by_child = True
        self.is_active = True
        
        for action in self.dropdown_menu.actions():
            if isinstance(action, QAction) and action.data() is not None:
                action.setProperty("selected", "true" if action.data() == item else "false")
        
        self.dropdown_menu.style().unpolish(self.dropdown_menu)
        self.dropdown_menu.style().polish(self.dropdown_menu)
        self.update_style()
    
    def show_dropdown(self):
        if self.has_dropdown:
            self.dropdown_open = True
            self.update_style()
            pos = self.mapToGlobal(QPoint(self.width(), 0))
            self.dropdown_menu.popup(pos)
            self.dropdown_menu.aboutToHide.connect(self.dropdown_closed)
            QTimer.singleShot(50, lambda: self.setDown(False))
    
    def dropdown_closed(self):
        self.dropdown_open = False
        self.update_style()
    
    def activate(self):
        if hasattr(self.parent_window, "set_active_nav_button"):
            self.parent_window.set_active_nav_button(self)
    
    def update_style(self):
        if self.is_active or self.active_by_child:
            self.setStyleSheet(f"""
                QToolButton {{
                    background-color: rgba(255, 255, 255, 0.1);
                    color: {self.text_light};
                    border: none;
                    border-radius: 0;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.15);
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QToolButton {{
                    background-color: transparent;
                    color: {self.text_secondary};
                    border: none;
                    border-radius: 0;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                    color: {self.text_light};
                }}
            """)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            QToolTip.showText(
                self.mapToGlobal(QPoint(self.width() + 5, self.height() // 2)),
                self.item_text,
                self,
                QRect(),
                2000
            )
        return super().eventFilter(obj, event)

class SearchBar(QLineEdit):
    def __init__(self, placeholder_text, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setFixedHeight(28)
        self.setMinimumWidth(250)  # Increased width to 250 pixels for "Search namespace..."
        self.setStyleSheet("""
            QLineEdit {
                background-color: #333333;
                border: none;
                border-radius: 3px;
                color: #ffffff;
                padding: 4px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                background-color: #404040;
            }
        """)

class SortableTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that can be sorted with values"""
    def __init__(self, text, value=0):
        super().__init__(text)
        self.value = value
        
    def __lt__(self, other):
        if hasattr(other, 'value'):
            return self.value < other.value
        return super().__lt__(other)

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

        # Header section (centered "9 items" with search at right, matching first code’s style)
        header = QHBoxLayout()
        title = QLabel("Namespaces")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
            font-family: 'Segoe UI';
        """)
        
        self.items_count = QLabel("9 items")
        self.items_count.setStyleSheet("""
            color: #9ca3af;
            font-size: 12px;
            font-family: 'Segoe UI';
        """)
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align the text, matching first code

        namespace_search = SearchBar("Search Namespaces...", self)
        namespace_search.setFixedHeight(28)

        header.addWidget(title)
        header.addStretch()  # Push items_count and search to the right, matching first code
        header.addWidget(self.items_count)
        header.addStretch()  # Add more stretch before search to push it to the far right, matching first code
        header.addWidget(namespace_search)  # Add search bar at the right, matching first code

        # Create table with only specified headings and action button
        self.table = QTableWidget()
        self.table.setColumnCount(6)  # Checkbox, Name, Labels, Age, Status, Action (⋮)
        headers = ["", "Name", "Labels", "Age", "Status", "⋮"]  # No serial number column
        self.table.setHorizontalHeaderLabels(headers)
        
        # Style the table
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                border: none;
                gridline-color: #2d2d2d;
                outline: none;
                font-family: 'Segoe UI';
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                outline: none;
                background-color: transparent;
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
                font-family: 'Segoe UI';
                font-weight: bold;
            }
            QToolButton {
                border: none;
                border-radius: 4px;
                padding: 4px;
                background-color: transparent;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
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
        
        # Additional table properties
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Disable focus highlighting
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)  # Disable selection
        self.table.verticalHeader().setVisible(False)  # Hide the vertical header (row numbers)
        
        # Configure table properties
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # "Name" column stretches
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Action column fixed
        self.table.setColumnWidth(5, 40)  # Width for action column
        
        column_widths = [40, None, 120, 80, 80, 40]  # Match widths (checkbox, Name, Labels, Age, Status, Action)
        for i, width in enumerate(column_widths):
            if i != 1:  # Skip "Name" column which stretches
                if width is not None:
                    self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                    self.table.setColumnWidth(i, width)
        
        # Disable the built-in sorting
        self.table.setSortingEnabled(False)
        
        # Set up select all checkbox
        select_all_checkbox = self.create_select_all_checkbox()
        self.set_header_widget(0, select_all_checkbox)

        layout.addLayout(header)
        layout.addWidget(self.table)

    def create_action_button(self, row):
        button = QToolButton()
        button.setText("⋮")
        button.setFixedWidth(30)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setStyleSheet("""
            QToolButton {
                color: #888888;
                font-size: 18px;
                background: transparent;
                padding: 2px;
                margin: 0;
                border: none;
                font-weight: bold;
                font-family: 'Segoe UI';
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

        menu = QMenu(button)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #3d3d2d;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                color: #ffffff;
                padding: 8px 24px 8px 36px;
                border-radius: 4px;
                font-size: 13px;
                font-family: 'Segoe UI';
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

        edit_action = menu.addAction("🖍  Edit")
        edit_action.triggered.connect(lambda: self.handle_action("Edit", row))

        delete_action = menu.addAction("🗑️  Delete")
        delete_action.setProperty("dangerous", True)
        delete_action.triggered.connect(lambda: self.handle_action("Delete", row))

        button.setMenu(menu)
        return button

    def handle_action(self, action, row):
        pod_name = self.table.item(row, 1).text()
        if action == "Edit":
            print(f"Editing namespace: {pod_name}")
        elif action == "Delete":
            print(f"Deleting namespace: {pod_name}")

    def create_checkbox(self, row, pod_name):
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
                padding-left: 5px;
                padding-bottom: 20px;
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
        
        checkbox.setFixedSize(40, 40)
        checkbox.stateChanged.connect(lambda state: self.handle_checkbox_change(state, pod_name))
        return checkbox

    def handle_checkbox_change(self, state, pod_name):
        if state == Qt.CheckState.Checked.value:
            self.selected_pods.add(pod_name)
        else:
            self.selected_pods.discard(pod_name)
        print(f"Selected namespaces: {self.selected_pods}")

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
        checkbox.setFixedSize(40, 40)  # Match the size of row checkboxes
        checkbox.stateChanged.connect(self.handle_select_all)
        return checkbox

    def handle_select_all(self, state):
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(state == Qt.CheckState.Checked.value)

    def load_data(self):
        pods_data = [
            ["kube-proxy-crs/r4w", "app=kube-proxy", "69d", "Active", ""],
            ["coredns-7db6lf44-d7nwq", "app=coredns", "69d", "Active", ""],
            ["coredns-7db6lf44-dj8lp", "app=coredns", "69d", "Inactive", ""],
            ["vpnkit-controller", "app=vpnkit", "69d", "Active", ""],
            ["etcd-docker-desktop", "app=etcd", "69d", "Inactive", ""],
            ["kube-apiserver-docker-desktop", "app=kube-apiserver", "69d", "Active", ""],
            ["kube-controller-manager-docker-desktop", "app=kube-controller", "69d", "Active", ""],
            ["storage-provisioner", "app=storage", "69d", "Inactive", ""],
            ["kube-scheduler-docker-desktop", "app=kube-scheduler", "69d", "Active", ""]
        ]

        self.table.setRowCount(len(pods_data))
        
        for row, pod in enumerate(pods_data):
            # Add checkbox first
            checkbox = self.create_checkbox(row, pod[0])
            self.table.setCellWidget(row, 0, checkbox)
            
            # Add Name, Labels, Age, Status
            for col, value in enumerate(pod[:4]):  # Use first 4 columns (Name, Labels, Age, Status)
                if col == 2:  # Age column (for sorting and alignment)
                    # Extract number for proper sorting (e.g., "69d" -> 69)
                    days = int(value.replace('d', ''))
                    item = SortableTableWidgetItem(value, days)
                elif col == 3:  # Status column (center-aligned)
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:  # Name, Labels
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setForeground(QColor("#e2e8f0"))  # Light gray for all columns
                
                self.table.setItem(row, col + 1, item)  # Position in columns 1, 2, 3, 4 (Name, Labels, Age, Status)
            
            # Add action button (now at last column, index 5)
            action_button = self.create_action_button(row)
            self.table.setCellWidget(row, 5, action_button)  # Position in the last column

    def set_header_widget(self, col, widget):
        header = self.table.horizontalHeader()
        
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(14, 0, 0, 0)  # Updated to 14px left margin (10px + 4px) to shift checkbox right
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the checkbox vertically
        layout.addWidget(widget)
        
        # Apply background color to match the header background
        container.setStyleSheet("""
            background-color: #252525;
        """)
        
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(col, 40)  # Match the column width for checkbox
        
        self.table.setHorizontalHeaderItem(col, QTableWidgetItem(""))
        container.setFixedHeight(header.height())
        container.setParent(header)
        container.setGeometry(header.sectionPosition(col), 0, 
                             header.sectionSize(col), header.height())
        container.show()

class DockerDesktopUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Docker Desktop")
        self.setMinimumSize(1000, 700)
        
        self.bg_dark = "#1a1a1a"
        self.bg_sidebar = "#1e1e1e"
        self.bg_header = "#1e1e1e"
        self.text_light = "#ffffff"
        self.text_secondary = "#888888"
        self.accent_blue = "#0095ff"
        self.border_color = "#2d2d2d"
        
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {self.bg_dark};
                color: {self.text_light};
                font-family: 'Segoe UI', sans-serif;
            }}
        """)
        
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        header = self.create_header()
        right_layout.addWidget(header)
        
        self.table_widget = PodsPage(self)  # Replace PodsTable with PodsPage
        right_layout.addWidget(self.table_widget, 1)
        
        main_layout.addWidget(right_container, 1)
        self.setCentralWidget(main_widget)
    
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(40)
        sidebar.setStyleSheet(f"""
            background-color: {self.bg_sidebar};
            border-right: 1px solid {self.border_color};
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.nav_buttons = []
        nav_items = [
            ("⚙️", "Cluster", True),
            ("💻", "Nodes", False),
            ("📦", "Workloads", False, True),
            ("📝", "Config", False, True),
            ("🌐", "Network", False, True),
            ("📂", "Storage", False, True),
            ("🔖", "Namespaces", False),
            ("🕒", "Events", False),
            ("⎈", "Helm", False, True),
            ("🔐", "Access Control", False, True),
            ("🧩", "Custom Resources", False, True)
        ]
        
        for item in nav_items:
            nav_btn = NavIconButton(item[0], item[1], item[2], item[3] if len(item) > 3 else False, self)
            self.nav_buttons.append(nav_btn)
            layout.addWidget(nav_btn)
        
        layout.addStretch(1)
        
        x_btn = NavIconButton("🖱️", "X Button", False, False, self)
        y_btn = NavIconButton("⌨️", "Y Button", False, False, self)
        z_btn = NavIconButton("🛠️", "Z Button", False, False, self)
        
        self.nav_buttons.append(x_btn)
        self.nav_buttons.append(y_btn)
        self.nav_buttons.append(z_btn)
        
        layout.addWidget(x_btn)
        layout.addWidget(y_btn)
        layout.addWidget(z_btn)
        
        return sidebar
    
    def create_header(self):
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet(f"""
            background-color: {self.bg_header};
            border-bottom: 1px solid {self.border_color};
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)
        
        # Cluster dropdown
        cluster_menu = QMenu()
        cluster_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.bg_sidebar};
                color: {self.text_light};
                border: 1px solid {self.border_color};
                border-radius: 4px;
                padding: 8px 0px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        
        cluster_menu.addAction("docker-desktop")
        cluster_menu.addSeparator()
        cluster_menu.addAction("dev-cluster")
        cluster_menu.addAction("staging-cluster")
        cluster_menu.addAction("production-cluster")
        
        cluster_dropdown = QToolButton()
        cluster_dropdown.setFixedSize(160, 28)
        cluster_dropdown.setMinimumWidth(200)
        
        button_layout = QHBoxLayout(cluster_dropdown)
        button_layout.setContentsMargins(12, 0, 32, 0)
        button_layout.setSpacing(8)
        
        text_label = QLabel("docker-desktop")
        text_label.setStyleSheet(f"color: #55c732; background: transparent;")
        
        arrow_label = QLabel("▼")
        arrow_label.setFixedWidth(20)
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        arrow_label.setStyleSheet(f"color: {self.text_secondary}; background: transparent; padding-right: 8px;")
        
        button_layout.addWidget(text_label)
        button_layout.addStretch()
        button_layout.addWidget(arrow_label)
        
        cluster_dropdown.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        cluster_dropdown.setMenu(cluster_menu)
        cluster_dropdown.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                background-color: rgba(255, 255, 255, 0.1);
                font-size: 13px;
                text-align: left;
                padding-left: 12px;
                padding-right: 32px;
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
            QToolButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }}
        """)
        
        search_bar = SearchBar("Search...", self)
        search_bar.setFixedHeight(28)
        
        namespace_search = SearchBar("Search namespace...", self)
        namespace_search.setFixedHeight(28)
        namespace_search.setMinimumWidth(250)  # Increased width to 250 pixels for "Search namespace..."

        layout.addWidget(cluster_dropdown)
        layout.addStretch(1)
        layout.addWidget(search_bar)
        layout.addWidget(namespace_search)
        
        return header

    def reset_all_buttons_and_dropdowns(self):
        for btn in self.nav_buttons:
            btn.is_active = False
            btn.active_by_child = False
            btn.selected_item = None
            if btn.dropdown_menu:
                for action in btn.dropdown_menu.actions():
                    if isinstance(action, QAction):
                        action.setProperty("selected", "false")
            btn.update_style()

    def set_active_nav_button(self, active_button):
        self.reset_all_buttons_and_dropdowns()
        active_button.is_active = True
        active_button.update_style()

    def row_count(self):
        return self.table_widget.rowCount()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QToolTip {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #444444;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
    """)
    window = DockerDesktopUI()
    window.show()
    sys.exit(app.exec())