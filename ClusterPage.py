import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QFrame, QTabWidget, QGridLayout, QSizePolicy,
                               QGraphicsDropShadowEffect, QMenu, QToolButton, QToolTip)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QEvent, QTimer, QPoint
from PyQt6.QtGui import (QIcon, QFont, QColor, QPalette, QPixmap, QPainter, QLinearGradient, 
                         QGradient, QShortcut, QAction, QGuiApplication)

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
                padding: 8px 16px;
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
        self.accent_light_blue = "#64B5F6"  # Blue active state (when page is selected)
        self.text_light = "#f0f0f0"
        self.text_secondary = "#a8a8a8"
        
        self.setup_ui()
        if self.has_dropdown:
            self.setup_dropdown()
            
    def setup_ui(self):
        self.setFixedSize(50, 50)
        self.setText(self.icon_text)
        self.setToolTip(self.item_text)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 18))
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
            self.dropdown_menu.addAction("Overview")
            self.dropdown_menu.addAction("Pods")
            self.dropdown_menu.addAction("Deployments")
            self.dropdown_menu.addAction("Daemon Sets")
            self.dropdown_menu.addAction("Stateful Sets")
            self.dropdown_menu.addAction("Replica Sets")
            self.dropdown_menu.addAction("Replication Controllers")
            self.dropdown_menu.addAction("Jobs")
            self.dropdown_menu.addAction("Cron Jobs")
        elif self.item_text == "Config":
            self.dropdown_menu.addAction("Config Maps")
            self.dropdown_menu.addAction("Secrets")
            self.dropdown_menu.addAction("Resource Quotas")
            self.dropdown_menu.addAction("Limit Ranges")
            self.dropdown_menu.addAction("Horizontal Pod Autoscalers")
            self.dropdown_menu.addAction("Pod Disruption Budgets")
            self.dropdown_menu.addAction("Priority Classes")
            self.dropdown_menu.addAction("Runtime Classes")
            self.dropdown_menu.addAction("Leases")
            self.dropdown_menu.addAction("Mutating Webhook Configurations")
            self.dropdown_menu.addAction("Validating Webhook Configurations")
        elif self.item_text == "Network":
            self.dropdown_menu.addAction("Services")
            self.dropdown_menu.addAction("Endpoints")
            self.dropdown_menu.addAction("Ingresses")
            self.dropdown_menu.addAction("Ingress Classes")
            self.dropdown_menu.addAction("Network Policies")
            self.dropdown_menu.addAction("Port Forwarding")
        elif self.item_text == "Storage":
            self.dropdown_menu.addAction("Persistent Volume Claims")
            self.dropdown_menu.addAction("Persistent Volumes")
            self.dropdown_menu.addAction("Storage Classes")
        elif self.item_text == "Helm":
            self.dropdown_menu.addAction("Charts")
            self.dropdown_menu.addAction("Releases")
        elif self.item_text == "Access Control":
            self.dropdown_menu.addAction("Service Accounts")
            self.dropdown_menu.addAction("Cluster Roles")
            self.dropdown_menu.addAction("Roles")
            self.dropdown_menu.addAction("Cluster Role Bindings")
            self.dropdown_menu.addAction("Role Bindings")
        elif self.item_text == "Custom Resources":
            self.dropdown_menu.addAction("Definitions")
    
    def show_dropdown(self):
        if self.has_dropdown:
            self.dropdown_open = True
            self.update_style()
            pos = self.mapToGlobal(QPoint(0, self.height()))
            self.dropdown_menu.popup(pos)
            self.dropdown_menu.aboutToHide.connect(self.dropdown_closed)
            QTimer.singleShot(50, lambda: self.setDown(False))
    
    def dropdown_closed(self):
        self.dropdown_open = False
        self.update_style()
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.setDown(False)
    
    def activate(self):
        if hasattr(self.parent_window, "set_active_nav_button"):
            self.parent_window.set_active_nav_button(self)
    
    def update_style(self):
        if self.dropdown_open:
            self.setStyleSheet(f"""
                QToolButton {{
                    background-color: rgba(255, 255, 255, 0.08);
                    color: {self.text_light};
                    border: none;
                    border-radius: 6px;
                    font-size: 18px;
                    padding: 4px;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.08);
                }}
            """)
        elif self.is_active:
            self.setStyleSheet(f"""
                QToolButton {{
                    background-color: {self.accent_light_blue};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 18px;
                    padding: 4px;
                }}
                QToolButton:hover {{
                    background-color: {self.accent_light_blue};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QToolButton {{
                    background-color: transparent;
                    color: {self.text_secondary};
                    border: none;
                    border-radius: 6px;
                    font-size: 18px;
                    padding: 4px;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.08);
                    color: {self.text_light};
                }}
            """)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            QToolTip.showText(
                self.mapToGlobal(QPoint(self.width() // 2, self.height())),
                self.item_text,
                self
            )
            return False
        return super().eventFilter(obj, event)

class DockerDesktopUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Docker Desktop")
        self.setMinimumSize(1000, 700)
        
        self.bg_dark = "#1a1a1a"
        self.bg_sidebar = "#222222"
        self.bg_header = "#262626"
        self.text_light = "#f0f0f0"
        self.text_secondary = "#a8a8a8"
        self.accent_blue = "#2196F3"
        self.accent_green = "#4CAF50"
        self.border_color = "#333333"
        self.tab_inactive = "#303030"
        self.card_bg = "#252525"
        
        font = QFont("Segoe UI", 9)
        QApplication.setFont(font)
        
        QToolTip.setFont(QFont('Segoe UI', 10))
        app = QApplication.instance()
        if app:
            app.setStyleSheet("""
                QToolTip {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    border: 1px solid #444444;
                    border-radius: 4px;
                    padding: 5px;
                    opacity: 230;
                }
            """)
        
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {self.bg_dark};
                color: {self.text_light};
                font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
            }}
            QPushButton {{
                border: none;
                color: {self.text_secondary};
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.08);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.12);
            }}
            QTabWidget::pane {{
                border: none;
                padding-top: 2px;
            }}
            QTabBar::tab {{
                background-color: {self.tab_inactive};
                color: {self.text_secondary};
                padding: 8px 24px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                font-weight: 500;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                background-color: {self.bg_dark};
                color: {self.text_light};
                border-bottom: 2px solid {self.accent_blue};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {self.text_light};
            }}
        """)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.nav_buttons = []
        
        nav_header = self.create_nav_header()
        main_layout.addWidget(nav_header)
        
        tab_container = self.create_tab_container()
        main_layout.addWidget(tab_container)
        
        content_area = self.create_content_area()
        main_layout.addWidget(content_area, 1)
        
        footer = self.create_footer()
        main_layout.addWidget(footer)
        
        self.setCentralWidget(main_widget)
        
        self.setWindowOpacity(0)
        self.show()
        self.fade_in_animation()
    
    def fade_in_animation(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(250)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()
    
    def set_active_nav_button(self, active_button):
        for btn in self.nav_buttons:
            btn.is_active = False
            btn.update_style()
        active_button.is_active = True
        active_button.update_style()
    
    def create_nav_header(self):
        nav_header = QWidget()
        nav_header.setFixedHeight(60)
        nav_header.setStyleSheet(f"""
            background-color: {self.bg_header};
            border-bottom: 1px solid {self.border_color};
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #2c2c2c, stop:1 #262626);
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        nav_header.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(nav_header)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        
        logo_btn = QPushButton()
        logo_btn.setFixedSize(160, 40)
        logo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        logo_layout = QHBoxLayout(logo_btn)
        logo_layout.setContentsMargins(10, 0, 10, 0)
        logo_layout.setSpacing(8)
        
        logo = QLabel("DD")
        logo.setFixedSize(30, 30)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"""
            background-color: {self.accent_green};
            color: white;
            font-weight: bold;
            font-size: 14px;
            border-radius: 5px;
        """)
        
        name_label = QLabel("docker-desktop")
        name_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: #e0e0e0;
        """)
        
        dropdown_icon = QLabel("▼")
        dropdown_icon.setStyleSheet("""
            font-size: 8px;
            color: #b8b8b8;
        """)
        
        logo_layout.addWidget(logo)
        logo_layout.addWidget(name_label)
        logo_layout.addWidget(dropdown_icon)
        
        logo_btn.setStyleSheet("""
            background-color: transparent;
            border: none;
            border-radius: 4px;
            text-align: left;
        """)
        
        nav_items_container = QWidget()
        nav_items_layout = QHBoxLayout(nav_items_container)
        nav_items_layout.setContentsMargins(0, 0, 0, 0)
        nav_items_layout.setSpacing(5)
        
        items = [
            ("⚙️", "Cluster", True),
            ("🖥️", "Nodes", False),
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
        
        for item in items:
            has_dropdown = len(item) > 3 and item[3]
            nav_btn = NavIconButton(item[0], item[1], item[2], has_dropdown, self)
            self.nav_buttons.append(nav_btn)
            nav_items_layout.addWidget(nav_btn)
        
        nav_items_layout.addStretch(1)
        
        layout.addWidget(logo_btn)
        layout.addWidget(nav_items_container, 1)
        
        return nav_header
    
    def create_tab_container(self):
        tab_widget = QTabWidget()
        tab_widget.setFixedHeight(44)
        tab_widget.addTab(QWidget(), "Master")
        tab_widget.addTab(QWidget(), "Worker")
        tab_widget.setCurrentIndex(0)
        return tab_widget
    
    def create_content_area(self):
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        metric_panel1 = self.create_metric_panel()
        metric_panel2 = self.create_metric_panel()
        status_panel = self.create_status_panel()
        
        content_layout.addWidget(metric_panel1, 0, 0)
        content_layout.addWidget(metric_panel2, 0, 1)
        content_layout.addWidget(status_panel, 1, 0, 1, 2)
        
        return content_widget
    
    def create_metric_panel(self):
        panel = QWidget()
        panel.setStyleSheet(f"""
            background-color: {self.card_bg};
            border-radius: 8px;
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        panel.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        
        tabs = QWidget()
        tabs_layout = QHBoxLayout(tabs)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(8)
        
        cpu_tab = QLabel("CPU")
        cpu_tab.setStyleSheet(f"""
            padding: 6px 16px;
            border-radius: 4px;
            background-color: {self.tab_inactive};
            font-weight: 500;
        """)
        
        memory_tab = QLabel("Memory")
        memory_tab.setStyleSheet("""
            padding: 6px 16px;
            font-weight: 500;
            opacity: 0.7;
        """)
        
        tabs_layout.addWidget(cpu_tab)
        tabs_layout.addWidget(memory_tab)
        tabs_layout.addStretch(1)
        
        info_icon = QLabel("i")
        info_icon.setFixedSize(28, 28)
        info_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_icon.setStyleSheet(f"""
            border: 1px solid {self.text_secondary};
            border-radius: 14px;
            color: {self.text_secondary};
            font-style: italic;
            font-weight: 600;
            font-family: 'Georgia', serif;
        """)
        
        error_msg = QLabel("Metrics are not available due to missing or invalid Prometheus configuration.")
        error_msg.setWordWrap(True)
        error_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_msg.setStyleSheet(f"""
            color: {self.text_secondary};
            font-size: 14px;
            line-height: 1.4;
            letter-spacing: 0.2px;
            max-width: 300px;
        """)
        
        settings_link = QLabel("Open cluster settings")
        settings_link.setStyleSheet(f"""
            color: {self.accent_blue};
            font-size: 14px;
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 4px;
        """)
        settings_link.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_link.enterEvent = lambda e: settings_link.setStyleSheet(f"""
            color: {self.accent_blue};
            font-size: 14px;
            font-weight: 500;
            background-color: rgba(33, 150, 243, 0.08);
            padding: 4px 8px;
            border-radius: 4px;
        """)
        settings_link.leaveEvent = lambda e: settings_link.setStyleSheet(f"""
            color: {self.accent_blue};
            font-size: 14px;
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 4px;
        """)
        
        layout.addWidget(tabs, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        layout.addWidget(info_icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(error_msg, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(settings_link, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        
        return panel
    
    def create_status_panel(self):
        panel = QWidget()
        panel.setStyleSheet(f"""
            background-color: {self.card_bg};
            border-radius: 8px;
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        panel.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        
        # Updated success icon container: now without border for a clean round appearance.
        success_icon_container = QWidget()
        success_icon_container.setFixedSize(70, 70)
        success_icon_container.setStyleSheet(f"""
            background-color: {self.accent_green};
            border-radius: 35px;
        """)
        
        success_icon_layout = QVBoxLayout(success_icon_container)
        success_icon_layout.setContentsMargins(0, 0, 0, 0)
        success_icon_layout.setSpacing(0)
        success_icon = QLabel("✓")
        success_icon.setStyleSheet("""
            color: white;
            font-size: 32px;
            font-weight: 300;
        """)
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_icon_layout.addWidget(success_icon)
        
        icon_shadow = QGraphicsDropShadowEffect()
        icon_shadow.setBlurRadius(15)
        icon_shadow.setColor(QColor(0, 0, 0, 60))
        icon_shadow.setOffset(0, 0)
        success_icon_container.setGraphicsEffect(icon_shadow)
        
        status_title = QLabel("No issues found")
        status_title.setStyleSheet("""
            font-size: 22px;
            font-weight: 500;
            letter-spacing: 0.3px;
            margin-top: 8px;
        """)
        
        status_subtitle = QLabel("Everything is fine in the Cluster")
        status_subtitle.setStyleSheet(f"""
            color: {self.text_secondary};
            font-size: 15px;
            letter-spacing: 0.2px;
            margin-top: 4px;
        """)
        
        layout.addWidget(success_icon_container, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_title, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_subtitle, 0, Qt.AlignmentFlag.AlignCenter)
        
        return panel
    
    def create_footer(self):
        footer = QWidget()
        footer.setFixedHeight(36)
        footer.setStyleSheet(f"""
            background-color: {self.bg_sidebar};
            border-top: 1px solid {self.border_color};
        """)
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(16, 0, 16, 0)
        
        add_tab = QPushButton("+")
        add_tab.setFixedSize(28, 28)
        add_tab.setStyleSheet(f"""
            background-color: transparent;
            color: {self.text_secondary};
            font-size: 18px;
            font-weight: 300;
            border-radius: 4px;
            padding: 0;
        """)
        add_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        add_tab.enterEvent = lambda e: add_tab.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.08);
            color: {self.text_light};
            font-size: 18px;
            font-weight: 300;
            border-radius: 4px;
            padding: 0;
        """)
        add_tab.leaveEvent = lambda e: add_tab.setStyleSheet(f"""
            background-color: transparent;
            color: {self.text_secondary};
            font-size: 18px;
            font-weight: 300;
            border-radius: 4px;
            padding: 0;
        """)
        
        layout.addStretch(1)
        layout.addWidget(add_tab)
        
        return footer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DockerDesktopUI()
    sys.exit(app.exec())
