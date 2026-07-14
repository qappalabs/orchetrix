import sys
import os
import logging

from PyQt6.QtCore import Qt, QPoint, QEvent, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF  # noqa: E402
from PyQt6.QtGui import QFont, QLinearGradient, QPainter, QColor, QPixmap, QIcon, QPainterPath, QCursor, QAction  # noqa: E402
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QFrame, QLineEdit, QMenu, QSpacerItem, QWidgetAction, QAbstractButton  # noqa: E402

from Styles import TitleBarStyles  # noqa: E402
from UI.Icons import Icons, resource_path  # noqa: E402
from UI.ThemeAwarePage import ThemeAwareMixin  # noqa: E402
from UI.ThemeManager import get_theme_manager  # noqa: E402
from UI.CustomComboBox import CustomComboBox  # noqa: E402

class ThemeToggle(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(52, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Colors
        self._track_color_light = QColor("#E0E0E0")
        self._track_color_dark = QColor("#404040")
        self._handle_color = QColor("#FFFFFF")
        
        self._position = 0.0
        self._anim = QPropertyAnimation(self, b"position", self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        # Load icons
        try:
            self._sun_icon = QIcon(resource_path("Icons/sun.svg"))
            self._moon_icon = QIcon(resource_path("Icons/moon.svg"))
        except Exception as e:
            logging.error(f"Failed to load toggle icons: {e}")
            self._sun_icon = QIcon()
            self._moon_icon = QIcon()
            
        self.toggled.connect(self.start_animation)

    @pyqtProperty(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def start_animation(self, checked):
        self._anim.stop()
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        track_rect = QRectF(rect).adjusted(2, 2, -2, -2)
        corner_radius = track_rect.height() / 2
        
        # Draw Track
        # Interpolate track color based on position
        color = self._interpolate_color(self._track_color_light, self._track_color_dark, self._position)
        
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(track_rect, corner_radius, corner_radius)
        
        # Draw Handle
        handle_height = track_rect.height() - 4
        handle_width = handle_height
        
        start_x = track_rect.left() + 2
        end_x = track_rect.right() - handle_width - 2
        
        current_x = start_x + (end_x - start_x) * self._position
        handle_rect = QRectF(current_x, track_rect.top() + 2, handle_width, handle_height)
        
        p.setBrush(self._handle_color)
        p.drawEllipse(handle_rect)
        
        # Draw Icon inside handle
        icon_rect = handle_rect.adjusted(3, 3, -3, -3)
        icon_target = icon_rect.toRect()
        
        if self._position < 0.5:
            # Draw Sun (fade out as we move right)
            opacity = 1.0 - (self._position * 2)
            if opacity > 0:
                p.setOpacity(opacity)
                self._sun_icon.paint(p, icon_target)
        else:
            # Draw Moon (fade in as we move right)
            opacity = (self._position - 0.5) * 2
            if opacity > 0:
                p.setOpacity(opacity)
                self._moon_icon.paint(p, icon_target)
                
    def _interpolate_color(self, start, end, progress):
        r = start.red() + (end.red() - start.red()) * progress
        g = start.green() + (end.green() - start.green()) * progress
        b = start.blue() + (end.blue() - start.blue()) * progress
        return QColor(int(r), int(g), int(b))


class TitleBar(ThemeAwareMixin, QWidget):
    def __init__(self, parent=None, update_pinned_items_signal=None):
        self._parent_window = parent
        super().__init__(parent)
        self.setFixedHeight(40)

        # Define consistent icon sizes
        self.normal_icon_size = QSize(18, 18)      # Standard size for most icons
        self.logo_icon_size = QSize(24, 24)        # Size for the app logo
        self.window_ctrl_size = QSize(18, 18)      # MODIFIED: Increased to match normal icon size
        self.maximized_icon_size = QSize(18, 18)   # MODIFIED: Made consistent with other icons

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
        self.drag_position = None
        self.double_click_in_progress = False
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
                # Try SVG via renderer
                from PyQt6.QtSvg import QSvgRenderer
                from PyQt6.QtCore import QByteArray
                svg_path = resource_path("Icons/logoIcon.svg")
                if os.path.exists(svg_path):
                    with open(svg_path, "r", encoding="utf-8") as f:
                        svg_content = f.read()
                    renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))
                    if renderer.isValid():
                        svg_pixmap = QPixmap(self.logo_icon_size)
                        svg_pixmap.fill(Qt.GlobalColor.transparent)
                        painter = QPainter(svg_pixmap)
                        renderer.render(painter)
                        painter.end()
                        self.logo_label.setPixmap(svg_pixmap)
                    else:
                        self.create_fallback_logo()
                else:
                    self.create_fallback_logo()
        except Exception as e:
            logging.debug(f"Failed to load logo: {e}")
            self.create_fallback_logo()

        # Home icon button
        self.home_btn = self.create_icon_button("home", "Home")
        self.home_btn.clicked.connect(self.navigate_to_home)

        # Pinned Clusters dropdown using searchable CustomComboBox
        self.pinned_clusters_combo = CustomComboBox(self, is_searchable=True, show_unpin=True)
        self.pinned_clusters_combo.setFixedSize(300, 34)
        self.pinned_clusters_combo.setPlaceholderText("Pinned Clusters")
        self.pinned_clusters_combo.currentTextChanged.connect(self.handle_item_selection)
        self.pinned_clusters_combo.unpin_clicked.connect(self.handle_unpin_item)
        self.pinned_clusters_combo.setObjectName("pinned_clusters_combo")
        
        # Override combo styling to fit TitleBar
        self.pinned_clusters_combo.setStyleSheet(TitleBarStyles.get_pinned_cluster_container_style())

        # Theme Toggle
        self.theme_toggle = ThemeToggle(self)
        self.theme_toggle.clicked.connect(self.toggle_theme)
        
        # Initialize state
        current_theme = get_theme_manager().get_current_theme_name()
        is_dark = current_theme == "Dark"
        # Block signals to prevent double-triggering logic, though toggle logic handles it
        self.theme_toggle.blockSignals(True)
        self.theme_toggle.setChecked(is_dark)
        self.theme_toggle.position = 1.0 if is_dark else 0.0 
        self.theme_toggle.blockSignals(False)

        # Settings icon on the right (removed troubleshoot, notifications, and profile)
        self.settings_btn = self.create_icon_button("settings", "Settings")

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
        layout.addWidget(self.pinned_clusters_combo)
        layout.addStretch(1)
        layout.addWidget(self.theme_toggle)
        layout.addSpacing(10)
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

    def _on_theme_changed(self, theme_name):
        """Re-apply all styles when theme changes"""
        self.setStyleSheet(TitleBarStyles.get_title_bar_style())
        if hasattr(self, 'pinned_clusters_combo'):
            self.pinned_clusters_combo.setStyleSheet(TitleBarStyles.get_pinned_cluster_container_style())
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
            prefs_icon = Icons.get_theme_icon("settings.svg", theme_folder)
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

            # Use original sizing: 10x10 for windowed, 18x18 for maximized
            current_size = self.window_ctrl_size if is_maximized else QSize(10, 10)

            if not max_icon.isNull():
                self.maximize_btn.setIcon(max_icon)
                self.maximize_btn.setIconSize(current_size)
        
        # Sync toggle state if theme changed externally (e.g. from Preferences)
        if hasattr(self, 'theme_toggle'):
            is_dark = theme_name == "Dark"
            if self.theme_toggle.isChecked() != is_dark:
                self.theme_toggle.blockSignals(True)
                self.theme_toggle.setChecked(is_dark)
                self.theme_toggle.position = 1.0 if is_dark else 0.0
                self.theme_toggle.blockSignals(False)

    def toggle_theme(self):
        """Toggle between Light and Dark themes"""
        is_dark = self.theme_toggle.isChecked()
        new_theme = "Dark" if is_dark else "Light"
        get_theme_manager().set_theme(new_theme)

    def update_current_cluster(self, cluster_name):
        """Update the current cluster name and icon in the dropdown"""
        self.current_cluster = cluster_name
        if hasattr(self, 'pinned_clusters_combo'):
            self.pinned_clusters_combo.setCurrentText(cluster_name if cluster_name else "")
            
            # Fetch and apply cluster icon
            if cluster_name:
                cluster_icon = self.get_cluster_icon(cluster_name)
                if cluster_icon and not cluster_icon.isNull():
                    self.pinned_clusters_combo.setIcon(cluster_icon)
                else:
                    self.pinned_clusters_combo.setIcon(None)
            else:
                self.pinned_clusters_combo.setIcon(None)
        logging.debug(f"Updated current cluster to: {cluster_name}")

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


    def handle_item_selection(self, item):
        """Handle the selection of a pinned item from the CustomComboBox"""
        if not item or item == self.current_cluster:
            return
            
        # Emit signal to open cluster
        if self.open_cluster_signal and hasattr(self._parent_window.home_page, 'all_data'):
            for view_type in self._parent_window.home_page.all_data:
                for data_item in self._parent_window.home_page.all_data[view_type]:
                    if data_item.get("name") == item and "Cluster" in data_item.get("kind", ""):
                        self.open_cluster_signal.emit(item)
                        return

    def handle_unpin_item(self, item_name):
        """Handle unpin action from the dropdown"""
        if hasattr(self._parent_window, 'home_page') and hasattr(self._parent_window.home_page, 'toggle_pin_item'):
            self._parent_window.home_page.toggle_pin_item(item_name)

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



    def create_fallback_logo(self):
        """Create a simple colored logo as fallback"""
        pixmap = QPixmap(self.logo_icon_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, self.logo_icon_size.width(), self.logo_icon_size.height())
        gradient.setColorAt(0, QColor("#FF9500"))
        gradient.setColorAt(1, QColor("#FF5500"))
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
            if hasattr(self, 'pinned_clusters_combo'):
                self.pinned_clusters_combo.setCurrentText("")
                self.pinned_clusters_combo.setIcon(None)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggle_maximize()
            return True
        return super().eventFilter(obj, event)

    def _get_theme_folder(self):
        """Return the lowercase theme folder name ('dark' or 'light') for icon lookups."""
        theme_name = get_theme_manager().get_current_theme_name()
        return theme_name.lower() if isinstance(theme_name, str) else "dark"

    def toggle_maximize(self):
        theme_folder = self._get_theme_folder()

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
        theme_folder = self._get_theme_folder()

        icon_filename = "maximize_active.svg" if is_maximized else "maximize.svg"
        icon = Icons.get_theme_icon(icon_filename, theme_folder)

        if not icon.isNull():
            self.maximize_btn.setIcon(icon)
            # Use original sizing: 10x10 for windowed, 18x18 for maximized
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
        if hasattr(self, 'pinned_clusters_combo'):
            self.pinned_clusters_combo.setItems(pinned_items)
            if self.current_cluster:
                self.pinned_clusters_combo.setCurrentText(self.current_cluster)

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
