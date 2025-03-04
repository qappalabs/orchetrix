from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QToolButton, QGraphicsDropShadowEffect,
                             QMenu, QToolTip)
from PyQt6.QtCore import Qt, QPoint, QRect, QEvent, QTimer
from PyQt6.QtGui import QFont, QColor, QAction

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

        # Colors
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
                          "Network Policies","Port Forwarding"]
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
            action = self.dropdown_menu.addAction(item)
            action.triggered.connect(lambda checked=False, item_name=item:
                                     self.parent_window.handle_dropdown_selection(item_name))

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

class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedWidth(40)
        self.setStyleSheet(f"""
            background-color: #1e1e1e;
            border-right: 2px solid { "#444444" };
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create nav buttons
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
            nav_btn = NavIconButton(item[0], item[1], item[2], item[3] if len(item) > 3 else False, self.parent)
            self.nav_buttons.append(nav_btn)
            layout.addWidget(nav_btn)

        layout.addStretch(1)
        Compare_btn = NavIconButton("🖱️", "Compare", False, False, self.parent)
        Terminal_btn = NavIconButton("⌨️", "Terminal", False, False, self.parent)
        Download_btn = NavIconButton("🛠️", "Download", False, False, self.parent)

        self.nav_buttons.append(Compare_btn)
        self.nav_buttons.append(Terminal_btn)
        self.nav_buttons.append(Download_btn)

        layout.addWidget(Compare_btn)
        layout.addWidget(Terminal_btn)
        layout.addWidget(Download_btn)
