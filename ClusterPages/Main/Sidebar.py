import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel, 
                            QGraphicsDropShadowEffect, QMenu, QToolTip, QSizePolicy,
                            QFrame)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QEvent, QTimer, QPoint, QRect
from PyQt6.QtGui import QIcon, QFont, QColor,QAction

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

class SidebarToggleButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Toggle Sidebar")
        self.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border-top: none;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.expanded = True

        # Create icons for collapsed and expanded states
        self.expanded_icon = QIcon("logos/collapse icon.png")  # Icon showing collapse action
        self.collapsed_icon = QIcon("logos/expand icon.png")   # Icon showing expand action

        # Set the initial icon
        self.setIcon(self.expanded_icon)
        self.setIconSize(QSize(30, 30))  # Set appropriate size for your icon

    def toggle_expanded(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.setIcon(self.expanded_icon)
        else:
            self.setIcon(self.collapsed_icon)
class NavIconButton(QToolButton):
    def __init__(self, icon, text, active=False, has_dropdown=False, parent=None, expanded=True):
        super().__init__(parent)
        self.parent_window = parent
        self.icon_text = icon
        self.item_text = text
        self.is_active = active
        self.has_dropdown = has_dropdown
        self.dropdown_open = False
        self.dropdown_menu = None
        self.expanded = expanded  # Track if sidebar is expanded

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
        self.setFixedHeight(40)
        
        if self.expanded:
            # Expanded state with text
            self.setFixedWidth(180)
            
            # Create a custom layout for better alignment
            layout = QHBoxLayout(self)
            layout.setContentsMargins(12, 0, 10, 0)  # Left padding for icon and text
            layout.setSpacing(8)  # Space between icon and text
            
            # Add icon label
            icon_label = QLabel(self.icon_text)
            icon_label.setFixedWidth(20)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Add text label
            text_label = QLabel(self.item_text)
            text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Add dropdown indicator if needed
            if self.has_dropdown:
                dropdown_label = QLabel("▸")
                dropdown_label.setFixedWidth(15)
                dropdown_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                layout.addWidget(icon_label)
                layout.addWidget(text_label)
                layout.addWidget(dropdown_label)
            else:
                layout.addWidget(icon_label)
                layout.addWidget(text_label)
                layout.addStretch()  # Push content to the left
                
            # Set empty text so the layout manages the content
            self.setText("")
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        else:
            # Collapsed state with icon only
            self.setFixedWidth(40)
            self.setText(self.icon_text)
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            
            # Clear any existing layout
            if self.layout():
                # Remove all widgets from layout
                while self.layout().count():
                    item = self.layout().takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                # Delete the layout
                QWidget().setLayout(self.layout())

        self.setToolTip(self.item_text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 12))
        self.setAutoRaise(True)
        self.update_style()
        
        # Connect signals
        self.clicked.connect(self.activate)
        if self.has_dropdown:
            self.clicked.connect(self.show_dropdown)
        self.installEventFilter(self)

    def set_expanded(self, expanded):
        self.expanded = expanded
        self.setup_ui()
        self.update_style()

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
                          "Network Policies", 'Port Forwarding']
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
            if self.expanded:
                pos = self.mapToGlobal(QPoint(self.width(), 0))
            else:
                pos = self.mapToGlobal(QPoint(40, 0))
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
        if self.expanded:
            # Style for labels inside the button when expanded
            self.setStyleSheet(f"""
                QToolButton {{
                    background-color: {self.get_background_color()};
                    border: none;
                    border-radius: 0;
                    text-align: left;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.15);
                }}
                QLabel {{
                    background-color: transparent;
                    color: {self.get_text_color()};
                }}
            """)
            
            # Update label colors
            if self.layout():
                for i in range(self.layout().count()):
                    widget = self.layout().itemAt(i).widget()
                    if isinstance(widget, QLabel):
                        widget.setStyleSheet(f"color: {self.get_text_color()};")
        else:
            # Simple style for collapsed state
            self.setStyleSheet(f"""
                QToolButton {{
                    background-color: {self.get_background_color()};
                    color: {self.get_text_color()};
                    border: none;
                    border-radius: 0;
                    padding-left: 10px;
                    text-align: left;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.15);
                }}
            """)

    def get_background_color(self):
        if self.is_active:
            return "rgba(255, 255, 255, 0.1)"
        return "transparent"
        
    def get_text_color(self):
        if self.is_active:
            return self.text_light
        return self.text_secondary

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter and not self.expanded:
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
        self.parent_window = parent
        
        # States and dimensions
        self.sidebar_expanded = True
        self.sidebar_width_expanded = 180
        self.sidebar_width_collapsed = 40
        
        # Colors
        self.bg_sidebar = "transparent"
        self.bg_dark = "#1a1a1a"
        self.border_color = "#2d2d2d"
        self.text_light = "#ffffff"
        self.text_secondary = "#888888"
        self.accent_blue = "#0095ff"
        
        # Initialize the UI
        self.setup_ui()
        
    def setup_ui(self):
        # Main container layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create the main sidebar content widget
        self.content_widget = QWidget()
        self.content_widget.setObjectName("sidebar_content")
        
        # Set initial width based on expanded state
        if self.sidebar_expanded:
            self.content_widget.setFixedWidth(self.sidebar_width_expanded)
        else:
            self.content_widget.setFixedWidth(self.sidebar_width_collapsed)
            
        # Apply basic styles
        self.content_widget.setStyleSheet(f"""
            #sidebar_content {{
                background-color: {self.bg_sidebar};
                border-top: 1px solid {self.border_color};
            }}
        """)
        
        # Create the vertical layout for sidebar content
        self.sidebar_layout = QVBoxLayout(self.content_widget)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)
        
        # Create the border widget (a vertical line)
        self.border = QFrame()
        self.border.setFrameShape(QFrame.Shape.VLine)
        self.border.setFrameShadow(QFrame.Shadow.Plain)
        self.border.setLineWidth(1)
        self.border.setStyleSheet("color: #444444;") # Red border for testing
        
        # Add the sidebar content and border to the main layout
        main_layout.addWidget(self.content_widget)
        main_layout.addWidget(self.border)
        
        # Add toggle controls
        self.create_toggle_controls()
        
        # Create navigation buttons
        self.create_nav_buttons()
        
        # Add spacer
        self.sidebar_layout.addStretch(1)
        
        # Create utility buttons at the bottom
        self.create_utility_buttons()
    
    def create_toggle_controls(self):
        sidebar_controls = QWidget()
        sidebar_controls.setObjectName("sidebar_controls")
        sidebar_controls.setFixedHeight(40)
        sidebar_controls.setStyleSheet(f"border-top: 1px solid {self.border_color};")
        controls_layout = QHBoxLayout(sidebar_controls)
        
        # Set margins to position the toggle button correctly
        if self.sidebar_expanded:
            controls_layout.setContentsMargins(self.sidebar_width_expanded - 35, 5, 5, 5)
        else:
            controls_layout.setContentsMargins(5, 5, 5, 5)
            
        # Add toggle button
        self.toggle_btn = SidebarToggleButton()
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        controls_layout.addWidget(self.toggle_btn)
        
        self.sidebar_layout.addWidget(sidebar_controls)
    
    def create_nav_buttons(self):
        self.nav_buttons = []
        nav_items = [
            ("⚙️", "Cluster", True),
            ("💻", "Nodes", False),
            ("📦", "Workloads", False, True),
            ("📝", "Config", False, True),
            ("🌐", "Network", False, True),
            ("📂", "Storage", False, True),
            ("⎈", "Helm", False, True),
            ("🔐", "Access Control", False, True),
            ("🧩", "Custom Resources", False, True),
            ("🔖", "Namespaces", False),
            ("🕒", "Events", False),
        ]
        
        for item in nav_items:
            nav_btn = NavIconButton(
                item[0], item[1], item[2],
                item[3] if len(item) > 3 else False,
                self.parent_window, self.sidebar_expanded
            )
            self.nav_buttons.append(nav_btn)
            self.sidebar_layout.addWidget(nav_btn)
    
    def create_utility_buttons(self):
        Compare_btn = NavIconButton("🖱️", "Compare", False, False, self.parent_window, self.sidebar_expanded)
        Terminal_btn = NavIconButton("⌨️", "Terminal", False, False, self.parent_window, self.sidebar_expanded)
        Download_btn = NavIconButton("🛠️", "Download", False, False, self.parent_window, self.sidebar_expanded)
        
        self.nav_buttons.append(Compare_btn)
        self.nav_buttons.append(Terminal_btn)
        self.nav_buttons.append(Download_btn)
        
        self.sidebar_layout.addWidget(Compare_btn)
        self.sidebar_layout.addWidget(Terminal_btn)
        self.sidebar_layout.addWidget(Download_btn)
    
    def toggle_sidebar(self):
        self.sidebar_expanded = not self.sidebar_expanded
        self.toggle_btn.toggle_expanded()
        self.update_sidebar_state()
    
    def update_sidebar_state(self):
        # Create animation for smooth transition
        self.sidebar_animation = QPropertyAnimation(self.content_widget, b"minimumWidth")
        self.sidebar_animation.setDuration(200)
        self.sidebar_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        if self.sidebar_expanded:
            self.sidebar_animation.setStartValue(self.sidebar_width_collapsed)
            self.sidebar_animation.setEndValue(self.sidebar_width_expanded)
            # Update toggle button position for expanded state
            controls_layout = self.content_widget.findChild(QWidget, "sidebar_controls").layout()
            controls_layout.setContentsMargins(self.sidebar_width_expanded - 35, 5, 5, 5)
        else:
            self.sidebar_animation.setStartValue(self.sidebar_width_expanded)
            self.sidebar_animation.setEndValue(self.sidebar_width_collapsed)
            # Update toggle button position for collapsed state
            controls_layout = self.content_widget.findChild(QWidget, "sidebar_controls").layout()
            controls_layout.setContentsMargins(5, 5, 5, 5)
            
        self.sidebar_animation.start()
        
        # Update all nav buttons
        for btn in self.nav_buttons:
            btn.set_expanded(self.sidebar_expanded)