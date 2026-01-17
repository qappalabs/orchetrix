import sys
import os
import logging
# Add the project root directory to sys.path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(project_root)

from PyQt6.QtCore import Qt, QPoint, QEvent, QSize
from PyQt6.QtGui import QFont, QLinearGradient, QPainter, QColor, QPixmap, QIcon, QPainterPath, QCursor, QAction
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QFrame, QLineEdit, QMenu, QSpacerItem, QWidgetAction

from Styles import TitleBarStyles
from UI.Icons import Icons, resource_path
from UI.ThemeAwarePage import ThemeAwareMixin
from UI.ThemeManager import get_theme_manager


class TitleBar(ThemeAwareMixin, QWidget):
    def __init__(self, parent=None, update_pinned_items_signal=None):
        self._parent_window = parent
        super().__init__(parent)
        self.setFixedHeight(40)

        # Define consistent icon sizes
        self.normal_icon_size = QSize(18, 18)      # Standard size for most icons
        self.logo_icon_size = QSize(24, 24)        # Size for the app logo
        self.window_ctrl_size = QSize(10, 10)      # Original size for window controls
        self.maximized_icon_size = QSize(18, 18)   # Size for maximized state icon

        # Store the signal for pinned items updates
        self.update_pinned_items_signal = update_pinned_items_signal
        # Store the signal for opening clusters
        self.open_cluster_signal = getattr(parent.home_page, 'open_cluster_signal', None) if hasattr(parent, 'home_page') else None

        # Store the pinned items list to preserve it during filtering
        self.pinned_items = []

        # Store the currently selected cluster name
        self.current_cluster = None

        # Track signal connections for proper cleanup
        self._signal_connections = []

        self.setup_ui()
        self.old_pos = None
        self.dropdown_menu = None
        self.search_input = None  # Instance variable for the search input
        self.search_action = None  # Instance variable for the search action

    def setup_ui(self):
        # Apply title bar style from Styles.py
        self.setStyleSheet(TitleBarStyles.get_title_bar_style())

        # Create a container widget with vertical layout
        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Create the main content widget
        content = QWidget()
        layout = QHBoxLayout(content)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(14)

        # Orchetrix logo on the left
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(self.logo_icon_size)

        try:
            logo_path = resource_path("Icons/logoIcon.png")
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                self.logo_label.setPixmap(pixmap.scaled(self.logo_icon_size, Qt.AspectRatioMode.KeepAspectRatio,
                                                        Qt.TransformationMode.SmoothTransformation))
            else:
                # Create a fallback logo
                self.create_fallback_logo()
        except Exception as e:
            logging.debug(f"Failed to load logo: {e}")
            self.create_fallback_logo()

        # Home icon button
        self.home_btn = self.create_icon_button("home", "Home")
        self.home_btn.clicked.connect(self.navigate_to_home)

        # Pinned Clusters button with dropdown (using QWidget for better control)
        self.pinned_clusters_container = QWidget()
        self.pinned_clusters_container.setFixedSize(300, 30)
        pinned_layout = QHBoxLayout(self.pinned_clusters_container)
        pinned_layout.setContentsMargins(8, 0, 0, 0)  # Add left margin for the container
        pinned_layout.setSpacing(8)  # Increase spacing between icon and text

        # Icon label for cluster icon
        self.pinned_clusters_icon = QLabel()
        self.pinned_clusters_icon.setFixedSize(16, 16)
        self.pinned_clusters_icon.setStyleSheet(TitleBarStyles.get_pinned_cluster_icon_style())
        self.pinned_clusters_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pinned_clusters_icon.hide()  # Hidden by default

        # Label for "Pinned Clusters" text or current cluster name
        self.pinned_clusters_label = QLabel("Pinned Clusters")
        self.pinned_clusters_label.setStyleSheet(TitleBarStyles.get_pinned_cluster_label_style())
        self.pinned_clusters_label.setFixedHeight(30)

        # Button for the arrow
        self.pinned_clusters_arrow_btn = QToolButton()
        self.pinned_clusters_arrow_btn.setFixedSize(30, 30)
        self.pinned_clusters_arrow_btn.setIcon(self.create_down_arrow_icon())
        self.pinned_clusters_arrow_btn.setIconSize(QSize(10, 10))
        self.pinned_clusters_arrow_btn.setStyleSheet(TitleBarStyles.get_pinned_cluster_arrow_style())
        self.pinned_clusters_arrow_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pinned_clusters_arrow_btn.clicked.connect(self.toggle_pinned_clusters_dropdown)

        # Container widget styling
        self.pinned_clusters_container.setStyleSheet(TitleBarStyles.get_pinned_cluster_container_style())

        # Add widgets to layout in correct order
        pinned_layout.addWidget(self.pinned_clusters_icon)
        pinned_layout.addWidget(self.pinned_clusters_label)
        pinned_layout.addStretch()
        pinned_layout.addWidget(self.pinned_clusters_arrow_btn)

        # Settings icon on the right (removed troubleshoot, notifications, and profile)
        self.settings_btn = self.create_icon_button("preferences", "Settings")

        # Window control buttons
        self.minimize_btn = self.create_window_control_button("minimize", "Minimize")
        self.minimize_btn.clicked.connect(self._parent_window.showMinimized)

        self.maximize_btn = self.create_window_control_button("maximize", "Maximize")
        self.maximize_btn.clicked.connect(self.toggle_maximize)

        self.close_btn = self.create_window_control_button("close", "Close")
        self.close_btn.clicked.connect(self._parent_window.close)
        self.close_btn.setStyleSheet(TitleBarStyles.get_close_button_style())

        # Add widgets to layout (removed troubleshoot_btn, notifications_btn, and profile_btn)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.home_btn)
        layout.addSpacerItem(QSpacerItem(90, 0))
        layout.addWidget(self.pinned_clusters_container)
        layout.addStretch(1)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)

        # Add the content to the container
        container_layout.addWidget(content)

        # Create a frame for the bottom border
        self.bottom_frame = QFrame()
        self.bottom_frame.setFixedHeight(2)
        self.bottom_frame.setStyleSheet(TitleBarStyles.get_title_bar_bottom_frame_style())
        container_layout.addWidget(self.bottom_frame)

        # Set up the main layout for this widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(container)

        # Install event filter for double-click
        self.installEventFilter(self)

        # Connect the pinned items signal if provided - with proper tracking
        if self.update_pinned_items_signal:
            self._connect_signal_safely(
                self.update_pinned_items_signal,
                self.update_pinned_dropdown
            )

        # Connect the open cluster signal to update the label - with proper tracking
        if self.open_cluster_signal:
            self._connect_signal_safely(
                self.open_cluster_signal,
                self.update_current_cluster
            )

    def _on_theme_changed(self, theme_name):
        """Re-apply all styles when theme changes"""
        self.setStyleSheet(TitleBarStyles.get_title_bar_style())
        self.pinned_clusters_icon.setStyleSheet(TitleBarStyles.get_pinned_cluster_icon_style())
        self.pinned_clusters_label.setStyleSheet(TitleBarStyles.get_pinned_cluster_label_style())
        self.pinned_clusters_arrow_btn.setStyleSheet(TitleBarStyles.get_pinned_cluster_arrow_style())
        self.pinned_clusters_container.setStyleSheet(TitleBarStyles.get_pinned_cluster_container_style())
        self.close_btn.setStyleSheet(TitleBarStyles.get_close_button_style())
        self.home_btn.setStyleSheet(TitleBarStyles.get_icon_button_style())
        self.settings_btn.setStyleSheet(TitleBarStyles.get_icon_button_style())
        self.minimize_btn.setStyleSheet(TitleBarStyles.get_window_control_style())
        self.maximize_btn.setStyleSheet(TitleBarStyles.get_window_control_style())
        if hasattr(self, 'bottom_frame'):
            self.bottom_frame.setStyleSheet(TitleBarStyles.get_title_bar_bottom_frame_style())
        if self.dropdown_menu:
            self.dropdown_menu.setStyleSheet(TitleBarStyles.get_dropdown_menu_style())
        if self.search_input:
            self.search_input.setStyleSheet(TitleBarStyles.get_search_input_style())

        # Update icons based on the active theme using theme-specific assets
        theme_folder = theme_name.lower() if isinstance(theme_name, str) else "dark"

        # Home and Settings buttons use 18x18 icons
        if hasattr(self, 'home_btn'):
            home_icon = Icons.get_theme_icon("home.svg", theme_folder)
            if not home_icon.isNull():
                self.home_btn.setIcon(home_icon)
                self.home_btn.setIconSize(self.normal_icon_size)

        if hasattr(self, 'settings_btn'):
            prefs_icon = Icons.get_theme_icon("preferences.svg", theme_folder)
            if not prefs_icon.isNull():
                self.settings_btn.setIcon(prefs_icon)
                self.settings_btn.setIconSize(self.normal_icon_size)

        # Window control buttons use 10x10 icons
        if hasattr(self, 'minimize_btn'):
            min_icon = Icons.get_theme_icon("minimize.svg", theme_folder)
            if not min_icon.isNull():
                self.minimize_btn.setIcon(min_icon)
                self.minimize_btn.setIconSize(QSize(10, 10))

        if hasattr(self, 'close_btn'):
            close_icon = Icons.get_theme_icon("close.svg", theme_folder)
            if not close_icon.isNull():
                self.close_btn.setIcon(close_icon)
                self.close_btn.setIconSize(QSize(10, 10))

        # Maximize button needs smart sizing based on state
        if hasattr(self, 'maximize_btn'):
            is_maximized = bool(self._parent_window and self._parent_window.isMaximized())
            max_filename = "maximize_active.svg" if is_maximized else "maximize.svg"
            max_icon = Icons.get_theme_icon(max_filename, theme_folder)

            # Determine correct size (Preserve original logic: 10x10 for restore, window_ctrl_size for maximized)
            current_size = self.window_ctrl_size if is_maximized else QSize(10, 10)

            if not max_icon.isNull():
                self.maximize_btn.setIcon(max_icon)
                self.maximize_btn.setIconSize(current_size)

    def update_current_cluster(self, cluster_name):
        """Update the pinned clusters label with the selected cluster name and icon"""
        self.current_cluster = cluster_name
        if cluster_name:
            # Truncate if necessary to prevent overflow
            display_name = cluster_name[:25] + "..." if len(cluster_name) > 25 else cluster_name
            self.pinned_clusters_label.setText(display_name)

            # Get the cluster icon using existing HomePage system
            cluster_icon = self.get_cluster_icon(cluster_name)
            if cluster_icon and not cluster_icon.isNull():
                self.pinned_clusters_icon.setPixmap(cluster_icon)
                self.pinned_clusters_icon.show()
            else:
                self.pinned_clusters_icon.hide()
        else:
            self.pinned_clusters_label.setText("Pinned Clusters")
            self.pinned_clusters_icon.hide()
        logging.debug(f"Updated pinned clusters label to: {self.pinned_clusters_label.text()}")

    def get_cluster_icon(self, cluster_name):
        """Get cluster icon using the HomePage's color system"""
        try:
            # Access the HomePage's color and icon creation methods
            if hasattr(self._parent_window, 'home_page'):
                home_page = self._parent_window.home_page

                # Get the cluster color using existing system
                cluster_color = home_page.get_cluster_color(cluster_name)

                # Create colored icon using same size as HomePage (16x16)
                colored_pixmap = home_page.create_colored_icon(
                    "Icons/Cluster_Logo.svg",
                    cluster_color,
                    16
                )

                return colored_pixmap

            # Fallback if home_page not accessible
            return None

        except Exception as e:
            logging.debug(f"Error getting cluster icon for {cluster_name}: {e}")
            return None

    def create_down_arrow_icon(self):
        """Create a downward arrow icon for the dropdown"""
        size = QSize(10, 10)  # Smaller size for the arrow
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))

        path = QPainterPath()
        path.moveTo(size.width() * 0.5, size.height() * 0.85)  # Bottom point
        path.lineTo(size.width() * 0.15, size.height() * 0.35)  # Top-left point
        path.lineTo(size.width() * 0.85, size.height() * 0.35)  # Top-right point
        path.closeSubpath()

        painter.drawPath(path)
        painter.end()

        return QIcon(pixmap)

    def toggle_pinned_clusters_dropdown(self):
        """Toggle the visibility of the pinned clusters dropdown"""
        if self.dropdown_menu and self.dropdown_menu.isVisible():
            self.dropdown_menu.hide()
            # Keep the current cluster name displayed when closing dropdown
        else:
            self.create_or_update_dropdown()
            # The label should maintain the current cluster name
            if self.search_input:
                self.search_input.setFocus()  # Set focus to the search input when opening

    def create_or_update_dropdown(self):
        """Create or update the dropdown menu with search input and pinned items"""
        if not self.dropdown_menu:
            self.dropdown_menu = QMenu(self)
            self.dropdown_menu.setStyleSheet(TitleBarStyles.get_dropdown_menu_style())

        # Initialize or reuse the search input and action
        if not self.search_input:
            self.search_input = QLineEdit(self)  # Set parent to self to prevent deletion
            self.search_input.setPlaceholderText("Search...")
            self.search_input.setFixedWidth(287)  # Match the width of pinned_clusters_container
            self.search_input.setStyleSheet(TitleBarStyles.get_search_input_style())
            self.search_input.textChanged.connect(self.filter_pinned_items)
            self.search_action = QWidgetAction(self)  # Set parent to self to prevent deletion
            self.search_action.setDefaultWidget(self.search_input)
            self.dropdown_menu.addAction(self.search_action)

        # Clear and update the pinned items
        self.dropdown_menu.clear()
        self.dropdown_menu.addAction(self.search_action)  # Re-add the search action

        # Add pinned items as actions
        if self.pinned_items:
            for item in self.pinned_items:
                action = QAction(item, self.dropdown_menu)
                action.triggered.connect(lambda checked, i=item: self.handle_item_selection(i))
                self.dropdown_menu.addAction(action)
        else:
            action = QAction("No pinned clusters", self.dropdown_menu)
            action.setEnabled(False)
            self.dropdown_menu.addAction(action)

        # Show the dropdown below the container
        button_pos = self.pinned_clusters_container.mapToGlobal(QPoint(0, self.pinned_clusters_container.height()))
        self.dropdown_menu.move(button_pos)
        self.dropdown_menu.show()

    def filter_pinned_items(self, text):
        """Filter the dropdown items based on the search input with Elasticsearch-like matching"""
        if not self.pinned_items or not self.dropdown_menu:
            return

        search_text = text.lower()
        self.dropdown_menu.clear()
        self.dropdown_menu.addAction(self.search_action)  # Re-add the search action

        # Filter items using substring matching (Elasticsearch-like)
        filtered_items = [item for item in self.pinned_items if search_text in item.lower()]
        if filtered_items:
            for item in filtered_items:
                action = QAction(item, self.dropdown_menu)
                action.triggered.connect(lambda checked, i=item: self.handle_item_selection(i))
                self.dropdown_menu.addAction(action)
        else:
            action = QAction("No matching pinned clusters", self.dropdown_menu)
            action.setEnabled(False)
            self.dropdown_menu.addAction(action)

        # Update the dropdown position and restore focus
        button_pos = self.pinned_clusters_container.mapToGlobal(QPoint(0, self.pinned_clusters_container.height()))
        self.dropdown_menu.move(button_pos)
        if self.search_input:
            self.search_input.setFocus()  # Restore focus to ensure continuous typing

    def handle_item_selection(self, item):
        """Handle the selection of a pinned item"""
        self.current_cluster = item

        # Update both text and icon
        display_name = item[:25] + "..." if len(item) > 25 else item
        self.pinned_clusters_label.setText(display_name)

        # Set the cluster icon using existing system
        cluster_icon = self.get_cluster_icon(item)
        if cluster_icon and not cluster_icon.isNull():
            self.pinned_clusters_icon.setPixmap(cluster_icon)
            self.pinned_clusters_icon.show()
        else:
            self.pinned_clusters_icon.hide()

        # Emit signal to open cluster
        if self.open_cluster_signal and hasattr(self._parent_window.home_page, 'all_data'):
            for view_type in self._parent_window.home_page.all_data:
                for data_item in self._parent_window.home_page.all_data[view_type]:
                    if data_item.get("name") == item and "Cluster" in data_item.get("kind", ""):
                        self.open_cluster_signal.emit(item)
                        break
        self.dropdown_menu.hide()

    def create_icon_button(self, icon_id, tooltip, fallback_icon=None):
        """Create a tool button with the specified icon and tooltip.

        For TitleBar icons, we make them theme-aware by asking ThemeManager for the
        current theme name and loading Icons/<theme>/<icon_id>.svg when available.
        """
        btn = QToolButton()
        btn.setFixedSize(30, 30)
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Determine current theme name ("Light" / "Dark") and map to folder name
        theme_name = get_theme_manager().get_current_theme_name()
        theme_folder = theme_name.lower() if isinstance(theme_name, str) else "dark"

        # Try theme-specific icon first: Icons/<theme>/<icon_id>.svg
        themed_icon = Icons.get_theme_icon(f"{icon_id}.svg", theme_folder)

        if not themed_icon.isNull():
            btn.setIcon(themed_icon)
            btn.setIconSize(self.normal_icon_size)
            btn.setText("")
        else:
            # Fallback to existing, non-themed icon lookup behaviour
            icon = Icons.get_icon(icon_id)

            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(self.normal_icon_size)
                btn.setText("")
            elif fallback_icon is not None:
                btn.setIcon(fallback_icon)
                btn.setIconSize(self.normal_icon_size)
                btn.setText("")
            else:
                fallback_text = getattr(Icons, icon_id.upper(), "") if isinstance(icon_id, str) else ""
                btn.setText(fallback_text)

        btn.setStyleSheet(TitleBarStyles.get_icon_button_style())
        return btn

    def _get_window_control_fallback_text(self, icon_id):
        """Get fallback text for window control buttons when icon is unavailable"""
        if icon_id == "minimize":
            return "-"
        elif icon_id == "maximize":
            return "[]" if not self._parent_window or not self._parent_window.isMaximized() else "="
        elif icon_id == "close":
            return "X"
        else:
            return getattr(Icons, icon_id.upper(), "") if isinstance(icon_id, str) else ""

    def create_window_control_button(self, icon_id, tooltip):
        """Create a window control button with minimal style, using theme-aware icons."""
        btn = QToolButton()
        btn.setFixedSize(46, 30)
        btn.setToolTip(tooltip)

        # Determine current theme and try theme-specific icon first
        theme_name = get_theme_manager().get_current_theme_name()
        theme_folder = theme_name.lower() if isinstance(theme_name, str) else "dark"
        icon = Icons.get_theme_icon(f"{icon_id}.svg", theme_folder)

        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(10, 10))
            btn.setText("")
        else:
            btn.setText(self._get_window_control_fallback_text(icon_id))
            btn.setFont(QFont("Segoe UI", 9))

        if icon_id == "close":
            btn.setStyleSheet(TitleBarStyles.get_close_button_style())
        else:
            btn.setStyleSheet(TitleBarStyles.get_window_control_style())

        return btn

    def create_back_icon(self):
        """Create a back arrow icon"""
        size = self.normal_icon_size
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))

        path = QPainterPath()
        path.moveTo(size.width() * 0.65, size.height() * 0.15)
        path.lineTo(size.width() * 0.35, size.height() * 0.5)
        path.lineTo(size.width() * 0.65, size.height() * 0.85)
        path.lineTo(size.width() * 0.55, size.height() * 0.5)
        path.closeSubpath()

        painter.drawPath(path)
        painter.end()

        return QIcon(pixmap)

    def create_forward_icon(self):
        """Create a forward arrow icon"""
        size = self.normal_icon_size
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))

        path = QPainterPath()
        path.moveTo(size.width() * 0.35, size.height() * 0.15)
        path.lineTo(size.width() * 0.65, size.height() * 0.5)
        path.lineTo(size.width() * 0.35, size.height() * 0.85)
        path.lineTo(size.width() * 0.45, size.height() * 0.5)
        path.closeSubpath()

        painter.drawPath(path)
        painter.end()

        return QIcon(pixmap)

    def create_fallback_logo(self):
        """Create a simple colored logo as fallback"""
        pixmap = QPixmap(self.logo_icon_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, self.logo_icon_size.width(), self.logo_icon_size.height())
        gradient.setColorAt(0, QColor("#4A9EFF"))
        gradient.setColorAt(1, QColor("#0066CC"))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.logo_icon_size.width(), self.logo_icon_size.height(), 6, 6)

        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Ox")
        painter.end()

        self.logo_label.setPixmap(pixmap)

    def navigate_to_home(self):
        """Navigate to the home page and reset cluster label"""
        if hasattr(self._parent_window, 'switch_to_home'):
            self._parent_window.switch_to_home()
            self.current_cluster = None
            self.pinned_clusters_label.setText("Pinned Clusters")
            self.pinned_clusters_icon.hide()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggle_maximize()
            return True
        return super().eventFilter(obj, event)

    def toggle_maximize(self):
        theme_name = get_theme_manager().get_current_theme_name()
        theme_folder = theme_name.lower() if isinstance(theme_name, str) else "dark"

        if self._parent_window.isMaximized():
            self._parent_window.showNormal()
            icon = Icons.get_theme_icon("maximize.svg", theme_folder)
            if not icon.isNull():
                self.maximize_btn.setIcon(icon)
                self.maximize_btn.setIconSize(QSize(10, 10))
                self.maximize_btn.setText("")
            else:
                self.maximize_btn.setText("[]")
                self.maximize_btn.setFont(QFont("Segoe UI", 9))
            self.maximize_btn.setStyleSheet(TitleBarStyles.get_window_control_style())
        else:
            self._parent_window.showMaximized()
            icon = Icons.get_theme_icon("maximize_active.svg", theme_folder)
            if not icon.isNull():
                self.maximize_btn.setIcon(icon)
                self.maximize_btn.setIconSize(self.window_ctrl_size)
                self.maximize_btn.setText("")
            else:
                self.maximize_btn.setText("=")
                self.maximize_btn.setFont(QFont("Segoe UI", 9))
            self.maximize_btn.setStyleSheet(TitleBarStyles.get_window_control_style())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._parent_window:
            self.double_click_in_progress = True
            if self._parent_window.isMaximized():
                self._parent_window.showNormal()
                self.update_maximize_button_icon(False)
                cursor_pos = event.globalPosition().toPoint()
                local_pos = event.position().toPoint()
                new_window_pos = cursor_pos - local_pos
                self._parent_window.move(new_window_pos)
                self.drag_position = cursor_pos
            else:
                self._parent_window.showMaximized()
                self.update_maximize_button_icon(True)
                self.drag_position = None
            event.accept()

    def mouseMoveEvent(self, event):
        if (self.drag_position is not None and
                event.buttons() == Qt.MouseButton.LeftButton and
                self._parent_window and
                not self._parent_window.isMaximized()):
            delta = event.globalPosition().toPoint() - self.drag_position
            self._parent_window.move(self._parent_window.pos() + delta)
            self.drag_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            self.double_click_in_progress = False

    def update_maximize_button_icon(self, is_maximized):
        theme_name = get_theme_manager().get_current_theme_name()
        theme_folder = theme_name.lower() if isinstance(theme_name, str) else "dark"

        icon_filename = "maximize_active.svg" if is_maximized else "maximize.svg"
        icon = Icons.get_theme_icon(icon_filename, theme_folder)

        if not icon.isNull():
            self.maximize_btn.setIcon(icon)
            # Use correct size based on state (10x10 vs 18x18)
            current_size = self.window_ctrl_size if is_maximized else QSize(10, 10)
            self.maximize_btn.setIconSize(current_size)
            self.maximize_btn.setText("")
        else:
            self.maximize_btn.setText("=" if is_maximized else "[]")
            self.maximize_btn.setFont(QFont("Segoe UI", 9))
        self.maximize_btn.setStyleSheet(TitleBarStyles.get_window_control_style())

    def update_pinned_dropdown(self, pinned_items):
        """Update the pinned items list from HomePage"""
        if not isinstance(pinned_items, list):
            pinned_items = []
        self.pinned_items = pinned_items
        if self.dropdown_menu and self.dropdown_menu.isVisible():
            self.create_or_update_dropdown()

    def _connect_signal_safely(self, signal, slot):
        """Connect signal safely with proper tracking for cleanup"""
        try:
            # First, try to disconnect existing connections to this slot
            # This prevents duplicate connections
            signal.disconnect(slot)
        except (RuntimeError, TypeError):
            # No existing connection or signal is invalid
            pass

        try:
            # Connect the signal to the slot
            signal.connect(slot)
            # Store the connection info for later cleanup
            self._signal_connections.append((signal, slot))
            logging.debug(f"Connected signal to {slot.__name__}")
        except Exception as e:
            logging.error(f"Failed to connect signal to {slot.__name__}: {e}")

    def cleanup_signals(self):
        """Clean up all signal connections"""
        for signal, slot in self._signal_connections:
            try:
                signal.disconnect(slot)
                logging.debug(f"Disconnected signal from {slot.__name__}")
            except (RuntimeError, TypeError):
                # Signal already disconnected or invalid
                pass
        self._signal_connections.clear()

    def closeEvent(self, event):
        """Handle close event with proper cleanup"""
        try:
            self.cleanup_signals()
        except Exception as e:
            logging.error(f"Error during TitleBar cleanup: {e}")
        super().closeEvent(event)

    def __del__(self):
        """Destructor to ensure cleanup when object is destroyed"""
        try:
            self.cleanup_signals()
        except Exception:
            pass  # Ignore errors during destruction
