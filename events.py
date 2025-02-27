import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QToolButton, QLabel, QMenu, QLineEdit, QPushButton, QTableWidget,
                           QTableWidgetItem, QHeaderView, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize, QEvent, QTimer
from PyQt6.QtGui import (QFont, QColor, QAction)
from datetime import datetime

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
        
        self.bg_dark = "#1a1a1a"
        self.accent_blue = "#2196F3"
        self.accent_light_blue = "#64B5F6"
        self.text_light = "#ffffff"
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
            
    def setup_dropdown(self):
        self.dropdown_menu = NavMenuDropdown(self.parent_window)
        title_action = QAction(f"{self.icon_text} {self.item_text}", self)
        title_action.setEnabled(False)
        self.dropdown_menu.addAction(title_action)
        self.dropdown_menu.addSeparator()
        
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
        else:
            menu_items = []
            
        for item in menu_items:
            self.dropdown_menu.addAction(item)
            
    def show_dropdown(self):
        if self.has_dropdown:
            self.dropdown_open = True
            self.update_style()
            pos = self.mapToGlobal(QPoint(self.width(), 0))
            self.dropdown_menu.popup(pos)
            self.dropdown_menu.aboutToHide.connect(self.dropdown_closed)
    
    def dropdown_closed(self):
        self.dropdown_open = False
        self.update_style()
    
    def activate(self):
        if hasattr(self.parent_window, "set_active_nav_button"):
            self.parent_window.set_active_nav_button(self)
    
    def update_style(self):
        if self.is_active:
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

class SearchBar(QLineEdit):
    def __init__(self, placeholder_text, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setFixedHeight(28)
        self.setMinimumWidth(300)
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

class EventsTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_data()
        self.update_row_count_button()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Header section
        top_widget = QWidget(self)
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(16)

        heading_label = QLabel("Events", top_widget)
        heading_label.setStyleSheet("""
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
        """)
        top_layout.addWidget(heading_label)

        top_layout.addStretch(1)

        self.row_count_button = QPushButton("0 items   ⓘ", top_widget)
        self.row_count_button.setFixedHeight(28)
        self.row_count_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                border: none;
                border-radius: 3px;
                color: #ffffff;
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        top_layout.addWidget(self.row_count_button)

        top_layout.addStretch(1)

        namespace_search = SearchBar("Search Events", top_widget)
        namespace_search.setFixedHeight(28)
        top_layout.addWidget(namespace_search, stretch=1)

        layout.addWidget(top_widget)

        # Table header
        headers_widget = QWidget(self)
        headers_widget.setStyleSheet("""
            background-color: #252525;
            border-bottom: 1px solid #2d2d2d;
        """)
        headers_layout = QHBoxLayout(headers_widget)
        headers_layout.setContentsMargins(0, 0, 0, 0)
        headers_layout.setSpacing(0)

        headers = ["Type", "Message", "Namespace", "Involved Object", "Source", "Count", "Age", "Last Seen", "⋮"]
        for i, header_text in enumerate(headers):
            label = QLabel(header_text, headers_widget)
            label.setStyleSheet("""
                color: #888888;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 0;
            """)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align all headers
            if i == 8:
                label.setFixedWidth(30)  # Fixed width for "⋮"
                label.setStyleSheet("""
                    color: #888888;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 8px 0;
                    margin-right: 18px;
                """)
            headers_layout.addWidget(label, stretch=1)  # All columns stretch equally

        layout.addWidget(headers_widget)

        # Table setup with adjusted properties
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.horizontalHeader().setVisible(False)

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
            QToolButton {
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)

        # Apply table properties
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        
        # Configure column properties - all stretch except action column
        for i in range(8):  # Columns 0-7 stretch
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 40)  # Action column fixed at 40px

        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)

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
                font-size: 12px;
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

        view_action = menu.addAction("View Details")
        view_action.triggered.connect(lambda: self.handle_action("View", row))

        delete_action = menu.addAction("Delete")
        delete_action.setProperty("dangerous", True)
        delete_action.triggered.connect(lambda: self.handle_action("Delete", row))

        button.setMenu(menu)
        return button

    def handle_action(self, action, row):
        event_type = self.table.item(row, 0).text()
        if action == "View":
            print(f"Viewing details for event: {event_type}")
        elif action == "Delete":
            print(f"Deleting event: {event_type}")

    def format_relative_time(self, timestamp_str):
        event_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
        current_time = datetime.now()
        time_diff = (current_time - event_time).total_seconds() / 60
        
        if time_diff < 60:
            return f"{int(time_diff)}m"
        elif time_diff < 1440:
            return f"{int(time_diff // 60)}h"
        else:
            return f"{int(time_diff // 1440)}d"

    def load_data(self):
        events_data = [
            ["Normal", "Pod started successfully", "default", "kube-proxy-crs/r4w", "kubelet", "1", "69d", "2025-02-25 00:11"],
            ["Warning", "Pod failed to pull image", "kube-system", "coredns-7db6lf44-d7nwq", "kubelet", "3", "69d", "2025-02-25 00:16"],
            ["Normal", "Pod scheduled", "default", "vpnkit-controller", "scheduler", "1", "69d", "2025-02-25 00:21"],
            ["Error", "API server unavailable", "kube-system", "kube-apiserver-docker-desktop", "apiserver", "2", "69d", "2025-02-25 00:26"],
            ["Normal", "Volume mounted", "default", "storage-provisioner", "kubelet", "1", "69d", "2025-02-25 00:31"],
        ]

        self.table.setRowCount(len(events_data))

        for row, event in enumerate(events_data):
            for col, value in enumerate(event):
                if col == 7:
                    value = self.format_relative_time(value)
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setForeground(QColor("#FFFFFF"))  # All columns white
                self.table.setItem(row, col, item)

            action_button = self.create_action_button(row)
            self.table.setCellWidget(row, 8, action_button)

    def row_count(self):
        return self.table.rowCount()

    def update_row_count_button(self):
        row_count = self.row_count()
        self.row_count_button.setText(f"{row_count} items   ⓘ")

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
        
        main_widget = QWidget(self)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        right_container = QWidget(main_widget)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        header = self.create_header()
        right_layout.addWidget(header)
        
        self.table_widget = EventsTable(right_container)
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
        
        layout.addWidget(cluster_dropdown)
        layout.addStretch(1)
        layout.addWidget(search_bar)
        layout.addWidget(namespace_search)
        
        return header

    def set_active_nav_button(self, active_button):
        for btn in self.nav_buttons:
            btn.is_active = False
            btn.update_style()
        active_button.is_active = True
        active_button.update_style()

    def row_count(self):
        return self.table_widget.row_count()

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