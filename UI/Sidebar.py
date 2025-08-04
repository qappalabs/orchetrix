from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
                             QGraphicsDropShadowEffect, QMenu, QToolTip, QSizePolicy,
                             QFrame, QLayout)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QEvent, QTimer, QPoint, QRect
from PyQt6.QtGui import QIcon, QFont, QColor, QAction, QPixmap

from UI.Styles import AppColors, AppStyles
from UI.Icons import Icons
import logging

class NavMenuDropdown(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Simplified window flags to avoid Windows layered window issues
        self.setWindowFlags(Qt.WindowType.Popup)

        # Remove problematic attributes that cause Windows layered window errors
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setStyleSheet(AppStyles.NAV_MENU_DROPDOWN_STYLE)

        # Only add shadow effect on non-Windows platforms or disable it entirely
        # to avoid UpdateLayeredWindowIndirect errors
        try:
            import platform
            if platform.system() != "Windows":
                shadow = QGraphicsDropShadowEffect(self)
                shadow.setColor(QColor(0, 0, 0, 100))
                shadow.setBlurRadius(15)
                shadow.setOffset(0, 5)
                self.setGraphicsEffect(shadow)
        except Exception as e:
            logging.debug(f"Could not apply shadow effect: {e}")


class SidebarToggleButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Toggle Sidebar")
        self.setStyleSheet(AppStyles.SIDEBAR_TOGGLE_BUTTON_STYLE)
        self.expanded = True

        try:
            from UI.Icons import resource_path  # Import the resource_path function
            back_icon_path = resource_path("icons/back.svg")
            forward_icon_path = resource_path("icons/forward.svg")

            self.expanded_icon = QIcon(back_icon_path)
            self.collapsed_icon = QIcon(forward_icon_path)

            # Check if icons loaded successfully
            if self.expanded_icon.isNull() or self.collapsed_icon.isNull():
                # Fallback to text-based icons
                self.expanded_icon = None
                self.collapsed_icon = None
        except Exception as e:
            logging.debug(f"Failed to load sidebar toggle icons: {e}")
            # Fallback to text-based icons
            self.expanded_icon = None
            self.collapsed_icon = None

        # Set the initial icon
        self.update_icon()
        self.setIconSize(QSize(24, 24))

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
    def __init__(self, icon_id, text, active=False, has_dropdown=False, parent=None, expanded=True, coming_soon=False):
        super().__init__(parent)
        self.font_size = 14
        self.parent_window = parent
        self.icon_id = icon_id  # Store the icon ID to load icon from local file
        self.item_text = text
        self.is_active = active
        self.has_dropdown = has_dropdown
        self.dropdown_open = False
        self.dropdown_menu = None
        self.expanded = expanded  # Track if sidebar is expanded
        self.coming_soon = coming_soon  # New flag for coming soon features

        # Track signal connections to prevent multiple connections
        self._dropdown_connections = []

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
            text_label.setFont(QFont("Segoe UI", 14))

            # Apply styles to labels - don't override background for coming soon
            if self.coming_soon:
                # For coming soon buttons, use same text color as regular buttons
                text_color = AppColors.TEXT_SECONDARY
                icon_label.setStyleSheet(f"color: {text_color}; background: transparent; font-size: 14px;")
                text_label.setStyleSheet(f"color: {text_color}; background: transparent; font-size: 14px;")
            else:
                icon_label.setStyleSheet(AppStyles.NAV_ICON_BUTTON_ICON_LABEL_STYLE + "; font-size: 14px;")
                text_label.setStyleSheet(AppStyles.NAV_ICON_BUTTON_TEXT_LABEL_STYLE + "; font-size: 14px;")

            # Add coming soon indicator if needed
            if self.coming_soon:
                coming_soon_label = QLabel()
                coming_soon_label.setFixedWidth(15)
                coming_soon_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                # Load update icon
                update_pixmap = QPixmap("icons/update_icon.svg")
                if not update_pixmap.isNull():
                    coming_soon_label.setPixmap(update_pixmap.scaled(15, 15, Qt.AspectRatioMode.KeepAspectRatio))
                else:
                    # Fallback to text if image can't be loaded
                    coming_soon_label.setText("!")
                    coming_soon_label.setStyleSheet("color: #FF4500; font-weight: bold;")

                # Set transparent background for coming soon label
                coming_soon_label.setStyleSheet("background: transparent;")

                # Add all widgets to layout
                layout.addWidget(icon_label)
                layout.addWidget(text_label)
                layout.addWidget(coming_soon_label)

            elif self.has_dropdown:
                # Add dropdown indicator if needed
                dropdown_label = QLabel(Icons.RIGHT_ARROW)
                dropdown_label.setFixedWidth(15)
                dropdown_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if self.coming_soon:
                    dropdown_label.setStyleSheet("color: inherit; background: transparent;")
                else:
                    dropdown_label.setStyleSheet(AppStyles.NAV_ICON_BUTTON_DROPDOWN_LABEL_STYLE)
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

            # For collapsed state, center the icon/text in the button
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)  # No margins for better centering
            layout.setSpacing(0)

            # Create centered icon label
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Set icon if loaded, otherwise set emoji text
            if self.icon_loaded:
                pixmap = self.icon.pixmap(QSize(20, 20))
                icon_label.setPixmap(pixmap)
            else:
                icon_label.setText(self.icon_text)

            if self.coming_soon:
                icon_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; background: transparent;")
            else:
                icon_label.setStyleSheet(AppStyles.NAV_ICON_BUTTON_ICON_LABEL_STYLE)

            # Add the icon label to the centered layout
            layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)

            # Clear button's own icon/text since we're using a layout
            self.setText("")
            self.setIcon(QIcon())
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        # Set tooltip - include under development or coming soon message if applicable
        if self.coming_soon:
            if self.item_text == "Helm":
                self.setToolTip("**Under Development**\nThis feature is currently being developed.")
            else:
                self.setToolTip("**Coming Soon**\nThis feature will be available in a future update.")
        else:
            self.setToolTip(self.item_text)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 14))
        self.setAutoRaise(True)
        self.update_style()

        # Connect signals
        if self.coming_soon:
            # For coming soon features, disconnect existing click handlers
            try:
                self.clicked.disconnect()
            except TypeError:
                pass  # No connections to disconnect
        else:
            # Regular buttons get normal functionality - but don't disconnect terminal
            if self.item_text != "Terminal":  # Don't interfere with terminal button
                try:
                    self.clicked.disconnect()  # Clear any existing connections
                except TypeError:
                    pass

                self.clicked.connect(self.activate)
                if self.has_dropdown:
                    self.clicked.connect(self.show_dropdown)

        self.installEventFilter(self)

    def show_loading_state(self):
        """Show a loading state for the button without modifying item_text"""
        # Create loading indicator if needed
        if not hasattr(self, 'loading_indicator'):
            self.loading_indicator = QLabel("⟳")
            self.loading_indicator.setStyleSheet("color: #00A0FF;")

            # Add loading indicator to button layout without changing item_text
            if self.expanded:
                # Find the layout
                for child in self.children():
                    if isinstance(child, QLayout):
                        child.addWidget(self.loading_indicator)
                        break

        # Show the loading indicator
        if hasattr(self, 'loading_indicator'):
            self.loading_indicator.show()

        # Start animation timer
        if not hasattr(self, 'loading_timer'):
            self.loading_timer = QTimer(self)
            self.loading_timer.timeout.connect(self._update_loading_animation)
            self.loading_animation_step = 0
            self.loading_symbols = ["⟳", "⟲", "⟳", "⟲"]

        self.loading_timer.start(200)  # Update every 200ms

    def hide_loading_state(self):
        """Hide the loading indicator"""
        if hasattr(self, 'loading_timer') and self.loading_timer.isActive():
            self.loading_timer.stop()

        if hasattr(self, 'loading_indicator'):
            self.loading_indicator.hide()

    def _update_loading_animation(self):
        """Update the loading animation symbol"""
        if not hasattr(self, 'loading_indicator'):
            return

        # Update the loading symbol
        symbol = self.loading_symbols[self.loading_animation_step % len(self.loading_symbols)]
        self.loading_indicator.setText(symbol)
        self.loading_animation_step += 1

    def set_expanded(self, expanded):
        if self.expanded != expanded:  # Only update if state actually changed
            self.expanded = expanded
            self.setup_ui()
            self.update_style()

    def setup_dropdown(self):
        """Setup dropdown menu with improved error handling"""
        try:
            # Clean up existing dropdown if it exists
            if self.dropdown_menu:
                self.dropdown_menu.deleteLater()
                self.dropdown_menu = None

            # Clear previous connections
            self._clear_dropdown_connections()

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

        except Exception as e:
            logging.error(f"Error setting up dropdown for {self.item_text}: {e}")
            self.dropdown_menu = None

    def _clear_dropdown_connections(self):
        """Clear all dropdown signal connections"""
        for connection in self._dropdown_connections:
            try:
                connection.disconnect()
            except (TypeError, RuntimeError):
                pass  # Connection already broken or doesn't exist
        self._dropdown_connections.clear()

    def show_dropdown(self):
        """Show dropdown menu with improved error handling"""
        if not self.has_dropdown or not self.dropdown_menu:
            return

        try:
            self.dropdown_open = True
            self.update_style()

            # Calculate position
            if self.expanded:
                pos = self.mapToGlobal(QPoint(self.width(), 0))
            else:
                pos = self.mapToGlobal(QPoint(40, 0))

            # Clear any existing aboutToHide connections for this dropdown
            try:
                self.dropdown_menu.aboutToHide.disconnect()
            except TypeError:
                pass  # No connections to disconnect

            # Connect the aboutToHide signal
            connection = self.dropdown_menu.aboutToHide.connect(self.dropdown_closed)
            self._dropdown_connections.append(connection)

            # Show the dropdown
            self.dropdown_menu.popup(pos)

        except Exception as e:
            logging.error(f"Error showing dropdown for {self.item_text}: {e}")
            self.dropdown_open = False
            self.update_style()

    def dropdown_closed(self):
        """Handle dropdown close event"""
        try:
            self.dropdown_open = False
            self.update_style()
        except Exception as e:
            logging.error(f"Error in dropdown_closed for {self.item_text}: {e}")

    def activate(self):
        if hasattr(self.parent_window, "set_active_nav_button"):
            self.parent_window.set_active_nav_button(self)

    def update_style(self):
        if self.expanded:
            self.setStyleSheet(AppStyles.NAV_ICON_BUTTON_EXPANDED_STYLE.format(
                background_color=self.get_background_color(),
                hover_background_color=AppColors.HOVER_BG,
                text_color=self.get_text_color()
            ))
        else:
            self.setStyleSheet(AppStyles.NAV_ICON_BUTTON_COLLAPSED_STYLE.format(
                background_color=self.get_background_color(),
                hover_background_color=AppColors.HOVER_BG,
                text_color=self.get_text_color()
            ))

    def get_background_color(self):
        if self.coming_soon:
            return "rgba(255, 149, 0, 0.15)"  # Orange tint for coming soon
        elif self.is_active:
            return AppColors.HOVER_BG
        return "transparent"

    def get_text_color(self):
        if self.is_active:
            return AppColors.TEXT_LIGHT
        return AppColors.TEXT_SECONDARY

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            if self.coming_soon:
                # Show custom tooltip for coming soon/under development features
                if self.item_text == "Helm":
                    message = "**Under Development**\nThis feature is currently being developed."
                else:
                    message = "**Coming Soon**\nThis feature will be available in a future update."

                QToolTip.showText(
                    self.mapToGlobal(QPoint(self.width() + 5, self.height() // 2)),
                    message,
                    self,
                    QRect(),
                    3000
                )
            elif not self.expanded:
                # Show regular tooltip for collapsed items
                QToolTip.showText(
                    self.mapToGlobal(QPoint(self.width() + 5, self.height() // 2)),
                    self.item_text,
                    self,
                    QRect(),
                    2000
                )
        return super().eventFilter(obj, event)

    def __del__(self):
        """Clean up resources when button is destroyed"""
        try:
            self._clear_dropdown_connections()
            if hasattr(self, 'dropdown_menu') and self.dropdown_menu:
                self.dropdown_menu.deleteLater()
        except Exception:
            pass  # Ignore errors during cleanup


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
        self.border.setStyleSheet(AppStyles.SIDEBAR_BORDER_STYLE)

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
        sidebar_controls.setStyleSheet(AppStyles.SIDEBAR_CONTROLS_STYLE)
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
            ("helm", "Helm", False, True, True),
            ("access_control", "Access Control", False, True),
            ("custom_resources", "Custom Resources", False, True),
            ("namespaces", "Namespaces", False),
            ("events", "Events", False),
            ("apps", "AppsChart", False)
        ]

        for item in nav_items:
            nav_btn = NavIconButton(
                item[0],                 # icon_id
                item[1],                 # text
                item[2],                 # is_active
                item[3] if len(item) > 3 else False,  # has_dropdown
                self.parent_window,      # parent
                self.sidebar_expanded,   # expanded
                item[4] if len(item) > 4 else False   # coming_soon - NEW
            )
            self.nav_buttons.append(nav_btn)
            self.sidebar_layout.addWidget(nav_btn)

    def toggle_complete_event(self):
        """Fire an event when sidebar toggle animation completes"""
        # This is a placeholder that will be connected to by the parent window
        pass

    def toggle_sidebar(self):
        """Toggle sidebar expansion state and adjust any dependent components"""
        self.sidebar_expanded = not self.sidebar_expanded
        self.toggle_btn.toggle_expanded()

        # Determine start and end values for animation
        start_width = self.sidebar_width_expanded if not self.sidebar_expanded else self.sidebar_width_collapsed
        end_width = self.sidebar_width_collapsed if not self.sidebar_expanded else self.sidebar_width_expanded

        # Find the parent cluster view
        parent_cluster_view = None
        if hasattr(self.parent_window, 'cluster_view'):
            parent_cluster_view = self.parent_window.cluster_view
        elif isinstance(self.parent_window, QWidget) and hasattr(self.parent_window, 'terminal_panel'):
            parent_cluster_view = self.parent_window

        # Notify terminal directly if possible
        if parent_cluster_view and hasattr(parent_cluster_view, 'terminal_panel'):
            if parent_cluster_view.terminal_panel.is_visible:
                # Trigger the terminal animation in sync with sidebar
                parent_cluster_view.terminal_panel.animate_position(start_width, end_width)

        # Now update the sidebar state with animation
        self.update_sidebar_state()

        # Emit event when animation completes for any other components that need notification
        QTimer.singleShot(250, lambda: self.toggle_complete_event())

        # Notify terminal directly if possible
        if parent_cluster_view and hasattr(parent_cluster_view, 'terminal_panel'):
            # Update terminal sidebar width after animation completes
            def update_terminal():
                if hasattr(parent_cluster_view.terminal_panel, 'sidebar_width'):
                    parent_cluster_view.terminal_panel.sidebar_width = self.width()
                    if parent_cluster_view.terminal_panel.is_visible:
                        parent_cluster_view.terminal_panel.reposition()

            QTimer.singleShot(250, update_terminal)

    def create_utility_buttons(self):
        """Create utility buttons at the bottom of the sidebar"""
        # Add a horizontal divider line before utility buttons
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setLineWidth(1)
        divider.setStyleSheet(f"background-color: {AppColors.BORDER_LIGHT}; margin: 8px 10px;")
        self.sidebar_layout.addWidget(divider)

        # Create utility buttons
        compare_btn = NavIconButton(
            "compare", "Compare", False, False,
            self.parent_window, self.sidebar_expanded, coming_soon=True  # Add this parameter
        )

        # Terminal button - special handling
        terminal_btn = NavIconButton(
            "terminal", "Terminal", False, False,
            self.parent_window, self.sidebar_expanded
        )

        # We don't want the terminal button to behave like other navigation buttons
        # So we prevent it from calling activate() which would mark it as the active button
        try:
            terminal_btn.clicked.disconnect(terminal_btn.activate)
        except TypeError:
            pass  # No connections to disconnect

        ai_assis_btn = NavIconButton(
            "ai_assis", "AI Assistant", False, False,
            self.parent_window, self.sidebar_expanded, coming_soon=True  # Add this parameter
        )

        self.nav_buttons.append(compare_btn)
        self.nav_buttons.append(terminal_btn)
        self.nav_buttons.append(ai_assis_btn)

        self.sidebar_layout.addWidget(compare_btn)
        self.sidebar_layout.addWidget(terminal_btn)
        self.sidebar_layout.addWidget(ai_assis_btn)

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