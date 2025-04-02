import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel, 
                            QGraphicsDropShadowEffect, QMenu, QToolTip, QSizePolicy,
                            QFrame)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QEvent, QTimer, QPoint, QRect
from PyQt6.QtGui import QIcon, QFont, QColor, QAction

from UI.Styles import AppColors, AppStyles
from UI.Icons import Icons

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

        # Try to load icons from files
        try:
            # self.expanded_icon = QIcon("logos/collapse icon.png")
            # self.collapsed_icon = QIcon("logos/expand icon.png")
            self.expanded_icon = QIcon("icons/back.svg")
            self.collapsed_icon = QIcon("icons/forward.svg")
            # Check if icons loaded successfully
            if self.expanded_icon.isNull() or self.collapsed_icon.isNull():
                # Fallback to text-based icons
                self.expanded_icon = None
                self.collapsed_icon = None
        except Exception as e:
            print(f"Error loading sidebar toggle icons: {e}")
            # Fallback to text-based icons
            self.expanded_icon = None
            self.collapsed_icon = None
        
        # Set the initial icon
        self.update_icon()
        self.setIconSize(QSize(16, 16))

    def toggle_expanded(self):
        self.expanded = not self.expanded
        self.update_icon()

    def update_icon(self):
        """Update the button's icon based on the expanded state"""
        if self.expanded:
            if self.expanded_icon:
                self.setIcon(self.expanded_icon)
            else:
                # Text-based fallback for collapse
                self.setText("◀")
        else:
            if self.collapsed_icon:
                self.setIcon(self.collapsed_icon)
            else:
                # Text-based fallback for expand
                self.setText("▶")


class NavIconButton(QToolButton):
    def __init__(self, icon_id, text, active=False, has_dropdown=False, parent=None, expanded=True):
        super().__init__(parent)
        self.parent_window = parent
        self.icon_id = icon_id  # Store the icon ID to load icon from local file
        self.item_text = text
        self.is_active = active
        self.has_dropdown = has_dropdown
        self.dropdown_open = False
        self.dropdown_menu = None
        self.expanded = expanded  # Track if sidebar is expanded
        
        # Store the fallback icon text (emoji)
        self.icon_text = getattr(Icons, icon_id.upper(), "⚙️") if isinstance(icon_id, str) else "⚙️"
        
        # Try to load the icon
        self.icon = Icons.get_icon(icon_id)
        self.icon_loaded = not self.icon.isNull()

        self.setup_ui()
        if self.has_dropdown:
            self.setup_dropdown()

    def setup_ui(self):
        self.setFixedHeight(40)
        
        # Clear any existing layout first
        if self.layout():
            # Remove all widgets from layout
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            # Delete the layout
            QWidget().setLayout(self.layout())
        
        if self.expanded:
            # Expanded state with text and icon
            self.setFixedWidth(180)
            
            # Create a custom layout for better alignment
            layout = QHBoxLayout(self)
            layout.setContentsMargins(12, 0, 10, 0)  # Left padding for icon and text
            layout.setSpacing(8)  # Space between icon and text
            
            # Create icon label
            icon_label = QLabel()
            icon_label.setFixedWidth(20)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Set icon if loaded, otherwise set emoji text
            if self.icon_loaded:
                pixmap = self.icon.pixmap(QSize(20, 20))
                icon_label.setPixmap(pixmap)
            else:
                icon_label.setText(self.icon_text)
            
            # Add text label
            text_label = QLabel(self.item_text)
            text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Add dropdown indicator if needed
            if self.has_dropdown:
                dropdown_label = QLabel(Icons.RIGHT_ARROW)
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
            # Don't set any icon for the button itself when expanded
            self.setIcon(QIcon())
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        else:
            # Collapsed state with icon only
            self.setFixedWidth(40)
            
            # If icon is loaded, set it; otherwise use text/emoji
            if self.icon_loaded:
                self.setIcon(self.icon)
                self.setIconSize(QSize(20, 20))
                self.setText("")
            else:
                self.setText(self.icon_text)
                self.setIcon(QIcon())  # Clear any icon
                
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

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
        if self.expanded != expanded:  # Only update if state actually changed
            self.expanded = expanded
            self.setup_ui()
            self.update_style()

    def setup_dropdown(self):
        self.dropdown_menu = QMenu(self.parent_window)
        self.dropdown_menu.setWindowFlags(self.dropdown_menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.dropdown_menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.dropdown_menu.setStyleSheet("""
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

        shadow = QGraphicsDropShadowEffect(self.dropdown_menu)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 5)
        self.dropdown_menu.setGraphicsEffect(shadow)
        
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
                          "Priority Classes", "Runtime Classes", "Leases", "Mutating Webhook Configs","Validating Webhook Configs"]
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
                    background-color: {AppColors.HOVER_BG};
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
                    background-color: {AppColors.HOVER_BG};
                }}
            """)

    def get_background_color(self):
        if self.is_active:
            return AppColors.HOVER_BG
        return "transparent"
        
    def get_text_color(self):
        if self.is_active:
            return AppColors.TEXT_LIGHT
        return AppColors.TEXT_SECONDARY

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
        self.content_widget.setStyleSheet(AppStyles.SIDEBAR_STYLE)
        
        # Create the vertical layout for sidebar content
        self.sidebar_layout = QVBoxLayout(self.content_widget)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)
        
        # Create the border widget (a vertical line)
        self.border = QFrame()
        self.border.setFrameShape(QFrame.Shape.VLine)
        self.border.setFrameShadow(QFrame.Shadow.Plain)
        self.border.setLineWidth(1)
        self.border.setStyleSheet("color: #444444;")
        
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
        sidebar_controls.setStyleSheet(f"border-top: 1px solid {AppColors.BORDER_COLOR};")
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
        
        # Define navigation items with icon ID, name, is_active, has_dropdown
        nav_items = [
            ("cluster", "Cluster", False),
            ("nodes", "Nodes", False),
            ("workloads", "Workloads", False, True),
            ("config", "Config", False, True),
            ("network", "Network", False, True),
            ("storage", "Storage", False, True),
            ("helm", "Helm", False, True),
            ("access_control", "Access Control", False, True),
            ("custom_resources", "Custom Resources", False, True),
            ("namespaces", "Namespaces", False),
            ("events", "Events", False),
            ("apps", "Apps", False)
        ]
        
        for item in nav_items:
            nav_btn = NavIconButton(
                item[0],                 # icon_id
                item[1],                 # text
                item[2],                 # is_active
                item[3] if len(item) > 3 else False,  # has_dropdown
                self.parent_window,      # parent
                self.sidebar_expanded    # expanded
            )
            self.nav_buttons.append(nav_btn)
            self.sidebar_layout.addWidget(nav_btn)
    
    
    def toggle_complete_event(self):
        """Fire an event when sidebar toggle animation completes"""
        # This is a placeholder that will be connected to by the parent window
        pass
    
    # In Sidebar.py, add this method to the Sidebar class:

    def toggle_sidebar(self):
        """Toggle sidebar expansion state and adjust any dependent components"""
        self.sidebar_expanded = not self.sidebar_expanded
        self.toggle_btn.toggle_expanded()
        self.update_sidebar_state()
        
        # Find the parent cluster view
        parent_cluster_view = None
        if hasattr(self.parent_window, 'cluster_view'):
            parent_cluster_view = self.parent_window.cluster_view
        elif isinstance(self.parent_window, QWidget) and hasattr(self.parent_window, 'terminal_panel'):
            parent_cluster_view = self.parent_window
        
        # Trigger updating of terminal position if cluster view is found
        if parent_cluster_view and hasattr(parent_cluster_view, 'terminal_panel'):
            # Emit an event that the sidebar has been toggled
            # This allows the parent window to update terminal position if needed
            QTimer.singleShot(250, lambda: self.toggle_complete_event())
            
            # Notify terminal directly if possible
            if hasattr(parent_cluster_view, 'terminal_panel'):
                # Update terminal sidebar width after animation completes
                def update_terminal():
                    if hasattr(parent_cluster_view.terminal_panel, 'sidebar_width'):
                        parent_cluster_view.terminal_panel.sidebar_width = self.width()
                        if parent_cluster_view.terminal_panel.is_visible:
                            parent_cluster_view.terminal_panel.reposition()
                
                QTimer.singleShot(250, update_terminal)
        
    def create_utility_buttons(self):
        """Create utility buttons at the bottom of the sidebar"""
        # Create utility buttons
        compare_btn = NavIconButton(
            "compare", "Compare", False, False, 
            self.parent_window, self.sidebar_expanded
        )
        
        # Terminal button - special handling
        terminal_btn = NavIconButton(
            "terminal", "Terminal", False, False, 
            self.parent_window, self.sidebar_expanded
        )
        
        # We don't want the terminal button to behave like other navigation buttons
        # So we prevent it from calling activate() which would mark it as the active button
        # We'll connect it directly to the terminal toggle function in ClusterView
        try:
            terminal_btn.clicked.disconnect(terminal_btn.activate)
        except TypeError:
            pass  # No connections to disconnect
        
        chat_btn = NavIconButton(
            "chat", "Chat", False, False, 
            self.parent_window, self.sidebar_expanded
        )
        
        self.nav_buttons.append(compare_btn)
        self.nav_buttons.append(terminal_btn)
        self.nav_buttons.append(chat_btn)
        
        self.sidebar_layout.addWidget(compare_btn)
        self.sidebar_layout.addWidget(terminal_btn)
        self.sidebar_layout.addWidget(chat_btn)    
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