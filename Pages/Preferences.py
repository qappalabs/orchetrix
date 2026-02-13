import platform
import os
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFrame, QLineEdit, QCheckBox, QScrollArea, QMessageBox
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer

import Styles.PreferencesStyles as PreferencesStyles
from UI.Icons import Icons
from UI.ThemeManager import get_theme_manager
from UI.ThemeAwarePage import ThemeAwareMixin

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 24)
        self.toggled.connect(self.on_state_changed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._circle_position = 10

        # Connect to theme changes
        from UI.ThemeManager import get_theme_manager
        get_theme_manager().theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name):
        """Refresh widget when theme changes"""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get theme-aware colors
        colors = PreferencesStyles.get_toggle_switch_colors()

        # Set colors based on state
        if self.isChecked():
            bg_color = QColor(colors['checked_bg'])
            circle_pos = 30
        else:
            bg_color = QColor(colors['unchecked_bg'])
            circle_pos = 10

        # Draw background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)

        # Draw circle
        painter.setBrush(QColor(colors['circle']))
        painter.drawEllipse(circle_pos, 4, 16, 16)

    def on_state_changed(self, checked):
        if checked:
            self.enable_startup()
        else:
            self.disable_startup()

    def enable_startup(self):
        system = platform.system()
        if system == 'Windows':
            try:
                print("Added to Windows startup")
            except Exception as e:
                print(f"Failed to add to Windows startup: {e}")
        elif system == 'Darwin':  # macOS
            try:
                print("Added to macOS startup")
            except Exception as e:
                print(f"Failed to add to macOS startup: {e}")
        elif system == 'Linux':
            try:
                print("Added to Linux startup")
            except Exception as e:
                print(f"Failed to add to Linux startup: {e}")
        print("Start-up enabled")

    def disable_startup(self):
        system = platform.system()
        if system == 'Windows':
            try:
                print("Removed from Windows startup")
            except Exception as e:
                print(f"Failed to remove from Windows startup: {e}")
        elif system == 'Darwin':  # macOS
            try:
                print("Removed from macOS startup")
            except Exception as e:
                print(f"Failed to remove from macOS startup: {e}")
        elif system == 'Linux':
            try:
                print("Removed from Linux startup")
            except Exception as e:
                print(f"Failed to remove from Linux startup: {e}")
        print("Start-up disabled")

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(PreferencesStyles.get_sidebar_button_style())
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class PreferencesWidget(ThemeAwareMixin, QWidget):
    back_signal = pyqtSignal()
    font_changed = pyqtSignal(str)  # Signal for font family changes
    font_size_changed = pyqtSignal(int)  # Signal for font size changes
    copy_paste_changed = pyqtSignal(bool)  # Signal for copy-paste toggle changes
    line_numbers_changed = pyqtSignal(bool)  # Signal for line numbers toggle changes
    tab_size_changed = pyqtSignal(int)  # Signal for tab size changes
    timezone_changed = pyqtSignal(str)  # Signal for timezone changes

    def __init__(self):
        super().__init__()
        self.current_font_size = 9  # Changed from 12 to 9 - Default font size for all editors
        self.current_font_family = "Consolas"  # Default font family
        self.current_tab_size = 2  # Default tab size
        self.terminal_panel = None  # Will be set by the main application
        self.pending_font_size = None  # Store pending font size if terminal_panel is not set
        self.copy_paste_enabled = False  # Track copy-paste state
        self.show_line_numbers = True  # Default to showing line numbers
        self.last_emitted_size = self.current_font_size  # Keep track of last emitted size to avoid duplicates

        # Initialize timezone
        self.current_timezone = self.get_system_timezone()

        # Initialize theme manager and settings
        self.theme_manager = get_theme_manager()
        from PyQt6.QtCore import QSettings
        self.settings = QSettings("Orchetrix", "OX")
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet(PreferencesStyles.get_sidebar_style())
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Header container with back button and preferences label
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(10, 10, 10, 10)
        header_layout.setSpacing(10)

        # Back button
        back_btn = self.create_back_button()
        header_layout.addWidget(back_btn)

        # Preferences label
        preferences_label = QLabel("SETTINGS")
        preferences_label.setStyleSheet(PreferencesStyles.get_header_style())
        header_layout.addWidget(preferences_label)

        header_layout.addStretch()
        sidebar_layout.addWidget(header_container)

        # Sidebar menu buttons
        self.app_btn = SidebarButton("App")
        self.proxy_btn = SidebarButton("Proxy")
        self.kubernetes_btn = SidebarButton("Kubernetes")
        self.editor_btn = SidebarButton("Editor")
        self.terminal_btn = SidebarButton("Terminal")

        # Connect sidebar buttons
        self.app_btn.clicked.connect(lambda: self.show_section("app"))
        self.proxy_btn.clicked.connect(lambda: self.show_section("proxy"))
        self.kubernetes_btn.clicked.connect(lambda: self.show_section("kubernetes"))
        self.editor_btn.clicked.connect(lambda: self.show_section("editor"))
        self.terminal_btn.clicked.connect(lambda: self.show_section("terminal"))

        self.app_btn.setChecked(True)

        sidebar_layout.addWidget(self.app_btn)
        sidebar_layout.addWidget(self.proxy_btn)
        sidebar_layout.addWidget(self.kubernetes_btn)
        sidebar_layout.addWidget(self.editor_btn)
        sidebar_layout.addWidget(self.terminal_btn)
        sidebar_layout.addStretch()

        # Content area with scroll
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setStyleSheet(PreferencesStyles.get_scroll_style())
        self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_scroll)

        self.current_section = "app"
        self.show_section("app")

    def get_system_timezone(self):
        """Get the system timezone"""
        try:
            # Simple implementation to get local timezone name
            return str(datetime.now().astimezone().tzinfo)
        except Exception:
            return "UTC"

    def _on_theme_changed(self, theme_name):
        """Refresh UI when theme changes"""
        # Defer refresh to avoid crashes if triggered during signal handling
        QTimer.singleShot(0, lambda: self._perform_theme_refresh())

    def _perform_theme_refresh(self):
        """Actual UI update logic"""
        # Update sidebar style
        self.sidebar.setStyleSheet(PreferencesStyles.get_sidebar_style())

        # Update scroll area style
        self.content_scroll.setStyleSheet(PreferencesStyles.get_scroll_style())

        # Refresh sidebar buttons
        if hasattr(self, 'app_btn'):
            self.app_btn.setStyleSheet(PreferencesStyles.get_sidebar_button_style())
        if hasattr(self, 'proxy_btn'):
            self.proxy_btn.setStyleSheet(PreferencesStyles.get_sidebar_button_style())
        if hasattr(self, 'kubernetes_btn'):
            self.kubernetes_btn.setStyleSheet(PreferencesStyles.get_sidebar_button_style())
        if hasattr(self, 'editor_btn'):
            self.editor_btn.setStyleSheet(PreferencesStyles.get_sidebar_button_style())
        if hasattr(self, 'terminal_btn'):
            self.terminal_btn.setStyleSheet(PreferencesStyles.get_sidebar_button_style())

        # Update Back Button Icon
        if hasattr(self, 'back_btn'):
            from UI.Icons import Icons
            theme_name = self.theme_manager.get_current_theme_name() or "Dark"
            icon = Icons.get_theme_icon("back_arrow.png", theme_name)
            self.back_btn.setIcon(icon)
            self.back_btn.setStyleSheet(PreferencesStyles.get_back_button_style())

        # Refresh current section to update its components
        self.show_section(self.current_section)

        # Update Theme Dropdown if it exists
        if hasattr(self, 'theme_combo'):
            theme_name = self.theme_manager.get_current_theme_name()
            if self.theme_combo.currentText() != theme_name:
                self.theme_combo.blockSignals(True)
                self.theme_combo.setCurrentText(theme_name)
                self.theme_combo.blockSignals(False)

    def go_back(self):
        self.back_signal.emit()

    def create_back_button(self):
        self.back_btn = QPushButton()

        # Use theme-aware icon
        theme_name = get_theme_manager().get_current_theme_name() or "Dark"
        icon = Icons.get_theme_icon("back_arrow.png", theme_name)

        self.back_btn.setIcon(icon)
        self.back_btn.setIconSize(QSize(24, 24))
        self.back_btn.setFixedSize(30, 30)
        self.back_btn.setStyleSheet(PreferencesStyles.get_back_button_style())
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.go_back)
        return self.back_btn

    def show_section(self, section):
        # Stop timezone timer when leaving app section
        if self.current_section == "app" and section != "app":
            if hasattr(self, 'timezone_timer') and self.timezone_timer:
                self.timezone_timer.stop()

        self.app_btn.setChecked(False)
        self.proxy_btn.setChecked(False)
        self.kubernetes_btn.setChecked(False)
        self.editor_btn.setChecked(False)
        self.terminal_btn.setChecked(False)

        self.current_section = section
        if section == "app":
            self.app_btn.setChecked(True)
            self.show_app_section()
            # Start timezone timer for app section
            if hasattr(self, 'timezone_timer') and self.timezone_timer:
                self.timezone_timer.start(1000)
        elif section == "proxy":
            self.proxy_btn.setChecked(True)
            self.show_proxy_section()
        elif section == "kubernetes":
            self.kubernetes_btn.setChecked(True)
            self.show_kubernetes_section()
        elif section == "editor":
            self.editor_btn.setChecked(True)
            self.show_editor_section()
        elif section == "terminal":
            self.terminal_btn.setChecked(True)
            self.show_terminal_section()

    def show_app_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)

        # Header
        app_header = QLabel("Application")
        app_header.setObjectName("header")
        app_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        content_layout.addWidget(app_header)

        # Theme section
        theme_label = QLabel("THEME")
        theme_label.setObjectName("sectionHeader")
        theme_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setStyleSheet(PreferencesStyles.get_dropdown_style())
        self.theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)

        # Set current theme from settings
        current_theme = self.settings.value("theme", "Light")
        self.theme_combo.setCurrentText(current_theme)

        # Connect signal
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        content_layout.addWidget(self.theme_combo)

        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider1)

        # Extension registry section
        registry_label = QLabel("EXTENSION INSTALL REGISTRY")
        registry_label.setObjectName("sectionHeader")
        registry_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(registry_label)

        registry_combo = QComboBox()
        registry_combo.addItems(["Default Url", "Custom Url"])
        registry_combo.setStyleSheet(PreferencesStyles.get_dropdown_style())
        registry_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(registry_combo)

        registry_help = QLabel(
            "This setting is to change the registry URL for installing extensions by name. If you are unable to access the\n"
            "default registry (https://registry.npmjs.org) you can change it in your .npmrc file or in the input below."
        )
        registry_help.setStyleSheet(PreferencesStyles.get_description_style())
        registry_help.setWordWrap(True)
        content_layout.addWidget(registry_help)

        registry_input = QLineEdit()
        registry_input.setPlaceholderText("Custom Extension Registry URL...")
        registry_input.setStyleSheet(PreferencesStyles.get_input_style())
        content_layout.addWidget(registry_input)

        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider2)

        # Start-up section
        startup_label = QLabel("START-UP")
        startup_label.setObjectName("sectionHeader")
        startup_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(startup_label)

        startup_container = QWidget()
        startup_layout = QHBoxLayout(startup_container)
        startup_layout.setContentsMargins(0, 10, 0, 10)

        startup_text = QLabel("Automatically start Orchetrix on login")
        startup_text.setStyleSheet(PreferencesStyles.get_text_style())

        self.startup_status = QLabel("Disabled")
        self.startup_status.setStyleSheet(PreferencesStyles.get_status_text_style(False))

        toggle_switch = ToggleSwitch()
        toggle_switch.setChecked(False)
        toggle_switch.toggled.connect(self.update_startup_status)

        startup_layout.addWidget(startup_text)
        startup_layout.addStretch()
        startup_layout.addWidget(self.startup_status)
        startup_layout.addWidget(toggle_switch)

        content_layout.addWidget(startup_container)

        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        divider3.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider3)

        # Local Timezone section
        timezone_label = QLabel("LOCAL TIMEZONE")
        timezone_label.setObjectName("sectionHeader")
        timezone_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(timezone_label)

        # Timezone combo box
        self.timezone_combo = QComboBox()
        self.timezone_combo.addItems([
            "Asia/Calcutta", "America/New_York", "Europe/London",
            "Europe/Berlin", "Asia/Tokyo", "Asia/Singapore",
            "Australia/Sydney", "Pacific/Auckland"
        ])
        self.timezone_combo.setStyleSheet(PreferencesStyles.get_dropdown_style())
        self.timezone_combo.setCursor(Qt.CursorShape.PointingHandCursor)

        # Try to set the current timezone in the combo box
        try:
            index = self.timezone_combo.findText(self.current_timezone)
            if index >= 0:
                self.timezone_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error setting current timezone: {e}")

        self.timezone_combo.currentIndexChanged.connect(self.change_timezone)
        content_layout.addWidget(self.timezone_combo)

        # Add current time display
        self.timezone_info = QLabel()
        self.timezone_info.setStyleSheet(PreferencesStyles.get_description_style())
        self.update_timezone_display()  # Initialize with current time
        content_layout.addWidget(self.timezone_info)

        # Add apply button
        timezone_apply_container = QWidget()
        timezone_apply_layout = QHBoxLayout(timezone_apply_container)
        timezone_apply_layout.setContentsMargins(0, 10, 0, 10)

        timezone_apply_btn = QPushButton("Apply Timezone")
        timezone_apply_btn.setStyleSheet(PreferencesStyles.get_button_primary_style())
        timezone_apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        timezone_apply_btn.clicked.connect(self.apply_timezone)

        timezone_apply_layout.addStretch()
        timezone_apply_layout.addWidget(timezone_apply_btn)

        content_layout.addWidget(timezone_apply_container)

        content_layout.addStretch()

        self.content_scroll.setWidget(content_widget)

    def update_timezone_display(self):
        """Update the timezone info label with current time in selected timezone"""
        try:
            # Check if timezone_info widget exists and is valid
            if not hasattr(self, 'timezone_info') or self.timezone_info is None:
                return

            # Check if the widget hasn't been deleted
            try:
                self.timezone_info.isVisible()  # This will raise RuntimeError if deleted
            except RuntimeError:
                # Widget has been deleted, stop the timer
                if hasattr(self, 'timezone_timer') and self.timezone_timer:
                    self.timezone_timer.stop()
                return

            # Use the current selected timezone with proper validation
            timezone = self.current_timezone  # Use stored timezone as default

            # Only try to get from combo box if it exists and is valid
            if hasattr(self, 'timezone_combo') and self.timezone_combo is not None:
                try:
                    timezone = self.timezone_combo.currentText()
                except RuntimeError:
                    # ComboBox has been deleted, use stored timezone
                    pass

            # Get current time in UTC
            now_utc = datetime.utcnow()

            # Format the time display
            time_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

            # Try to get local time in the selected timezone
            # Note: This is simplified and would need proper timezone handling in a real app
            if timezone == "Asia/Calcutta":
                local_time = now_utc.replace(hour=(now_utc.hour + 5) % 24)
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                time_str += f" | {local_time_str} IST (+5:30)"
            elif timezone == "America/New_York":
                local_time = now_utc.replace(hour=(now_utc.hour - 5) % 24)
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                time_str += f" | {local_time_str} EST (-5:00)"
            elif timezone == "Europe/London":
                local_time = now_utc.replace(hour=(now_utc.hour + 0) % 24)
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                time_str += f" | {local_time_str} GMT (+0:00)"
            elif timezone == "Europe/Berlin":
                local_time = now_utc.replace(hour=(now_utc.hour + 1) % 24)
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                time_str += f" | {local_time_str} CET (+1:00)"
            elif timezone == "Asia/Tokyo":
                local_time = now_utc.replace(hour=(now_utc.hour + 9) % 24)
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                time_str += f" | {local_time_str} JST (+9:00)"
            elif timezone == "Asia/Singapore":
                local_time = now_utc.replace(hour=(now_utc.hour + 8) % 24)
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                time_str += f" | {local_time_str} SGT (+8:00)"
            elif timezone == "Australia/Sydney":
                local_time = now_utc.replace(hour=(now_utc.hour + 10) % 24)
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                time_str += f" | {local_time_str} AEST (+10:00)"
            elif timezone == "Pacific/Auckland":
                local_time = now_utc.replace(hour=(now_utc.hour + 12) % 24)
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                time_str += f" | {local_time_str} NZST (+12:00)"

            # Try to set the text, but handle if widget has been deleted
            try:
                self.timezone_info.setText(time_str)
            except RuntimeError:
                # Widget has been deleted, stop the timer
                if hasattr(self, 'timezone_timer') and self.timezone_timer:
                    self.timezone_timer.stop()

        except Exception as e:
            print(f"Error updating timezone display: {e}")
            # Stop the timer if there are persistent errors
            if hasattr(self, 'timezone_timer') and self.timezone_timer:
                self.timezone_timer.stop()

    def change_timezone(self, index):
        """Handle timezone selection change"""
        self.pending_timezone = self.timezone_combo.currentText()
        print(f"Timezone selection changed to: {self.pending_timezone}")
        self.update_timezone_display()  # Update time display immediately

    def apply_timezone(self):
        """Apply the selected timezone"""
        if hasattr(self, 'pending_timezone'):
            try:
                timezone = self.pending_timezone
                self.current_timezone = timezone
                print(f"Applying timezone change to: {timezone}")

                # Emit signal to notify application of timezone change
                self.timezone_changed.emit(timezone)

                # Show confirmation message
                QMessageBox.information(self, "Timezone Changed",
                                        f"Timezone has been changed to {timezone}.\nApplication display times will use this timezone.")

                # Update environment variable if needed
                if platform.system() == "Linux" or platform.system() == "Darwin":
                    os.environ["TZ"] = timezone
                    time.tzset()  # Apply the timezone change

                # In a real app, you might also want to:
                # 1. Save this preference to settings
                # 2. Update any time displays throughout the app
                # 3. Handle Windows timezone changes differently

                # Clear pending timezone
                del self.pending_timezone
            except Exception as e:
                print(f"Error applying timezone: {e}")
                QMessageBox.warning(self, "Timezone Error",
                                    f"Failed to change timezone: {str(e)}")
        else:
            QMessageBox.information(self, "No Change",
                                    "No timezone change was pending.")

    def show_proxy_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)

        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)

        proxy_header = QLabel("Proxy")
        proxy_header.setObjectName("header")
        proxy_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        header_layout.addWidget(proxy_header)
        # header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        # HTTP Proxy section
        http_proxy_label = QLabel("HTTP PROXY")
        http_proxy_label.setObjectName("sectionHeader")
        http_proxy_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(http_proxy_label)

        proxy_input = QLineEdit()
        proxy_input.setPlaceholderText("Type HTTP proxy url (example: http://proxy.acme.org:8080)")
        proxy_input.setStyleSheet(PreferencesStyles.get_input_style())
        content_layout.addWidget(proxy_input)

        proxy_desc = QLabel("Proxy is used only for non-cluster communication.")
        proxy_desc.setStyleSheet(PreferencesStyles.get_description_style())
        content_layout.addWidget(proxy_desc)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider)

        # Certificate Trust section
        cert_label = QLabel("CERTIFICATE TRUST")
        cert_label.setObjectName("sectionHeader")
        cert_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(cert_label)

        cert_container = QWidget()
        cert_layout = QHBoxLayout(cert_container)
        cert_layout.setContentsMargins(0, 10, 0, 10)

        cert_text = QLabel("Allow untrusted Certificate Authorities")
        cert_text.setStyleSheet(PreferencesStyles.get_text_style())

        cert_toggle = ToggleSwitch()
        cert_toggle.setChecked(False)

        cert_layout.addWidget(cert_text)
        cert_layout.addStretch()
        cert_layout.addWidget(cert_toggle)

        content_layout.addWidget(cert_container)

        cert_desc = QLabel(
            "This will make Lens to trust ANY certificate authority without any validations. Needed with some corporate proxies "
            "that do certificate re-writing. Does not affect cluster communications!"
        )
        cert_desc.setStyleSheet(PreferencesStyles.get_description_style())
        cert_desc.setWordWrap(True)
        content_layout.addWidget(cert_desc)

        content_layout.addStretch()

        self.content_scroll.setWidget(content_widget)

    def show_kubernetes_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)

        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)

        k8s_header = QLabel("Kubernetes")
        k8s_header.setObjectName("header")
        k8s_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        header_layout.addWidget(k8s_header)
        # header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        # Kubectl Binary section
        kubectl_label = QLabel("KUBECTL BINARY")
        kubectl_label.setObjectName("sectionHeader")
        kubectl_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(kubectl_label)

        kubectl_path_input = QLineEdit()
        kubectl_path_input.setPlaceholderText("Path to kubectl binary...")
        kubectl_path_input.setStyleSheet(PreferencesStyles.get_input_style())
        content_layout.addWidget(kubectl_path_input)

        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider1)

        # Kubeconfig section
        kubeconfig_label = QLabel("KUBECONFIG")
        kubeconfig_label.setObjectName("sectionHeader")
        kubeconfig_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(kubeconfig_label)

        kubeconfig_path_input = QLineEdit()
        kubeconfig_path_input.setPlaceholderText("Path to kubeconfig file...")
        kubeconfig_path_input.setStyleSheet(PreferencesStyles.get_input_style())
        content_layout.addWidget(kubeconfig_path_input)

        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider2)

        # Helm Charts section
        helm_charts_label = QLabel("HELM CHARTS")
        helm_charts_label.setObjectName("sectionHeader")
        helm_charts_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(helm_charts_label)

        helm_repos_container = QWidget()
        helm_repos_layout = QHBoxLayout(helm_repos_container)
        helm_repos_layout.setContentsMargins(0, 10, 0, 10)

        helm_repos_combo = QComboBox()
        helm_repos_combo.addItem("Repositories")
        helm_repos_combo.setStyleSheet(PreferencesStyles.get_dropdown_style())

        add_repo_btn = QPushButton("Add Custom Helm Repo")
        add_repo_btn.setStyleSheet(PreferencesStyles.get_button_primary_style())

        helm_repos_layout.addWidget(helm_repos_combo)
        helm_repos_layout.addSpacing(10)
        helm_repos_layout.addWidget(add_repo_btn)
        helm_repos_layout.addStretch()

        content_layout.addWidget(helm_repos_container)

        helm_repo_item_container = QWidget()
        helm_repo_item_layout = QHBoxLayout(helm_repo_item_container)
        helm_repo_item_layout.setContentsMargins(0, 10, 0, 10)

        helm_repo_item = QLabel("bitnami")
        helm_repo_url = QLabel("https://charts.bitnami.com/bitnami")
        helm_repo_item.setStyleSheet(PreferencesStyles.get_text_style())
        helm_repo_url.setStyleSheet(PreferencesStyles.get_description_style())

        delete_repo_btn = QPushButton("🗑")
        delete_repo_btn.setStyleSheet(PreferencesStyles.get_delete_button_style())

        repo_details_layout = QVBoxLayout()
        repo_details_layout.addWidget(helm_repo_item)
        repo_details_layout.addWidget(helm_repo_url)

        helm_repo_item_layout.addLayout(repo_details_layout)
        helm_repo_item_layout.addStretch()
        helm_repo_item_layout.addWidget(delete_repo_btn)

        content_layout.addWidget(helm_repo_item_container)

        content_layout.addStretch()

        self.content_scroll.setWidget(content_widget)

    def show_editor_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)

        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)

        editor_header = QLabel("Editor")
        editor_header.setObjectName("header")
        editor_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        header_layout.addWidget(editor_header)
        # header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        # Line Numbers section
        line_numbers_label = QLabel("LINE NUMBERS")
        line_numbers_label.setObjectName("sectionHeader")
        line_numbers_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(line_numbers_label)

        self.line_numbers_combo = QComboBox()
        self.line_numbers_combo.addItems(["On", "Off"])
        self.line_numbers_combo.setCurrentText("On" if self.show_line_numbers else "Off")
        self.line_numbers_combo.setStyleSheet(PreferencesStyles.get_dropdown_style())
        self.line_numbers_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.line_numbers_combo.currentTextChanged.connect(self.on_line_numbers_changed)
        content_layout.addWidget(self.line_numbers_combo)

        # Help text for line numbers
        line_numbers_help = QLabel("Show or hide line numbers in editor")
        line_numbers_help.setStyleSheet(PreferencesStyles.get_description_style())
        line_numbers_help.setWordWrap(True)
        content_layout.addWidget(line_numbers_help)

        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider2)

        # Tab Size section
        tab_size_label = QLabel("TAB SIZE")
        tab_size_label.setObjectName("sectionHeader")
        tab_size_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(tab_size_label)

        # Modified to use self.tab_size_input and connect signal
        self.tab_size_input = QLineEdit()
        self.tab_size_input.setText(str(self.current_tab_size))
        self.tab_size_input.setStyleSheet(PreferencesStyles.get_input_style())
        self.tab_size_input.editingFinished.connect(self.on_tab_size_changed)
        content_layout.addWidget(self.tab_size_input)

        # Help text for Tab Size
        tab_size_help = QLabel("Number of spaces per tab in the editor")
        tab_size_help.setStyleSheet(PreferencesStyles.get_description_style())
        tab_size_help.setWordWrap(True)
        content_layout.addWidget(tab_size_help)

        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        divider3.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider3)

        # Font Size section
        font_size_label = QLabel("FONT SIZE")
        font_size_label.setObjectName("sectionHeader")
        font_size_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(font_size_label)

        # This now affects the YAML editor too
        self.editor_font_size_input = QLineEdit()
        self.editor_font_size_input.setText(str(self.current_font_size))
        self.editor_font_size_input.setStyleSheet(PreferencesStyles.get_input_style())
        self.editor_font_size_input.editingFinished.connect(self.on_editor_font_size_changed)
        content_layout.addWidget(self.editor_font_size_input)

        # Help text for Editor font size
        editor_font_help = QLabel("This font size applies to all editors including the YAML editor")
        editor_font_help.setStyleSheet(PreferencesStyles.get_description_style())
        editor_font_help.setWordWrap(True)
        content_layout.addWidget(editor_font_help)

        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        divider4.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider4)

        # Font Family section
        font_family_label = QLabel("FONT FAMILY")
        font_family_label.setObjectName("sectionHeader")
        font_family_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(font_family_label)

        # This affects editors including YAML
        self.editor_font_family_combo = QComboBox()
        self.editor_font_family_combo.addItems(["Consolas", "RobotoMono", "Courier New", "Monospace"])
        self.editor_font_family_combo.setCurrentText(self.current_font_family)
        self.editor_font_family_combo.setStyleSheet(PreferencesStyles.get_dropdown_style())
        self.editor_font_family_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.editor_font_family_combo.currentTextChanged.connect(self.on_editor_font_changed)
        content_layout.addWidget(self.editor_font_family_combo)

        # Help text for editor font family
        editor_font_family_help = QLabel("This font family applies to all editors including the YAML editor")
        editor_font_family_help.setStyleSheet(PreferencesStyles.get_description_style())
        editor_font_family_help.setWordWrap(True)
        content_layout.addWidget(editor_font_family_help)

        content_layout.addStretch()

        self.content_scroll.setWidget(content_widget)

    def show_terminal_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)

        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)

        terminal_header = QLabel("Terminal")
        terminal_header.setObjectName("header")
        terminal_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        header_layout.addWidget(terminal_header)
        # header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        # Terminal Shell Path section
        shell_path_label = QLabel("TERMINAL SHELL PATH")
        shell_path_label.setObjectName("sectionHeader")
        shell_path_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(shell_path_label)

        shell_path_input = QLineEdit()
        shell_path_input.setText("powershell.exe")
        shell_path_input.setStyleSheet(PreferencesStyles.get_input_style())
        content_layout.addWidget(shell_path_input)

        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider1)

        # Terminal Copy & Paste section
        copy_paste_label = QLabel("TERMINAL COPY & PASTE")
        copy_paste_label.setObjectName("sectionHeader")
        copy_paste_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(copy_paste_label)

        copy_paste_container = QWidget()
        copy_paste_layout = QHBoxLayout(copy_paste_container)
        copy_paste_layout.setContentsMargins(0, 10, 0, 10)

        copy_paste_text = QLabel("Copy on select and paste on right-click")
        copy_paste_text.setStyleSheet(PreferencesStyles.get_text_style())

        copy_paste_toggle = ToggleSwitch()
        copy_paste_toggle.setChecked(self.copy_paste_enabled)
        copy_paste_toggle.toggled.connect(self.on_copy_paste_changed)

        copy_paste_layout.addWidget(copy_paste_text)
        copy_paste_layout.addStretch()
        copy_paste_layout.addWidget(copy_paste_toggle)

        content_layout.addWidget(copy_paste_container)

        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider2)

        # Terminal Theme section
        theme_label = QLabel("TERMINAL THEME")
        theme_label.setObjectName("sectionHeader")
        theme_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(theme_label)

        theme_combo = QComboBox()
        theme_combo.addItems(["Dark"])
        theme_combo.setStyleSheet(PreferencesStyles.get_dropdown_style())
        theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(theme_combo)

        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        divider3.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider3)

        # Font Size section
        font_size_label = QLabel("FONT SIZE")
        font_size_label.setObjectName("sectionHeader")
        font_size_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(font_size_label)

        self.font_size_input = QLineEdit()
        self.font_size_input.setText(str(self.current_font_size))
        self.font_size_input.setStyleSheet(PreferencesStyles.get_input_style())
        self.font_size_input.editingFinished.connect(self.on_font_size_changed)
        content_layout.addWidget(self.font_size_input)

        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        divider4.setStyleSheet(PreferencesStyles.get_divider_style())
        content_layout.addWidget(divider4)

        # Font Family section
        font_family_label = QLabel("FONT FAMILY")
        font_family_label.setObjectName("sectionHeader")
        font_family_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        content_layout.addWidget(font_family_label)

        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(["RobotoMono", "Consolas", "Courier New"])
        self.font_family_combo.setCurrentText(self.current_font_family)
        self.font_family_combo.setStyleSheet(PreferencesStyles.get_dropdown_style())
        self.font_family_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.font_family_combo.currentTextChanged.connect(self.on_font_changed)
        content_layout.addWidget(self.font_family_combo)

        content_layout.addStretch()

        self.content_scroll.setWidget(content_widget)

    def show_placeholder_section(self, title):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)

        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)

        section_header = QLabel(title)
        section_header.setObjectName("header")
        section_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        header_layout.addWidget(section_header)
        header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        placeholder = QLabel(f"{title} settings would go here")
        placeholder.setStyleSheet(PreferencesStyles.get_placeholder_style())
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(placeholder)

        content_layout.addStretch()

        self.content_scroll.setWidget(content_widget)

    def update_startup_status(self, checked):
        if checked:
            self.startup_status.setText("Enabled")
            self.startup_status.setStyleSheet(PreferencesStyles.get_status_text_style(True))
        else:
            self.startup_status.setText("Disabled")
            self.startup_status.setStyleSheet(PreferencesStyles.get_status_text_style(False))

    def on_theme_changed(self, theme_name):
        """Handle theme change from dropdown"""
        print(f"PreferencesWidget: Theme changed to {theme_name}")

        # Save to settings
        self.settings.setValue("theme", theme_name)

        # Apply theme - theme_changed signal will update all widgets
        self.theme_manager.set_theme(theme_name)

    def on_font_changed(self, font_family):
        """Handle terminal font family change"""
        print(f"PreferencesWidget: Font family changed to {font_family}")
        self.current_font_family = font_family

        # Emit signal for other components
        self.font_changed.emit(font_family)

        # Update terminal if available
        if self.terminal_panel:
            self.terminal_panel.update_font(font_family)

    def on_font_size_changed(self):
        """Handle terminal font size change"""
        try:
            size = int(self.font_size_input.text())
            if 6 <= size <= 72:
                print(f"PreferencesWidget: Font size changed to {size}")
                self.current_font_size = size

                # Emit signal for other components
                self.font_size_changed.emit(size)

                # Update terminal if available
                if self.terminal_panel:
                    self.terminal_panel.update_font_size(size)
                else:
                    self.pending_font_size = size
            else:
                # Restore previous value if invalid
                self.font_size_input.setText(str(self.current_font_size))
        except ValueError:
            self.font_size_input.setText(str(self.current_font_size))

    def on_editor_font_size_changed(self):
        """Handle editor font size change"""
        try:
            size = int(self.editor_font_size_input.text())
            if 6 <= size <= 72:
                if size == self.last_emitted_size:
                    return

                print(f"PreferencesWidget: Editor font size changed to {size}")
                self.current_font_size = size
                self.last_emitted_size = size

                # Emit signal for other components
                self.font_size_changed.emit(size)

                # Update terminal font size input too to keep in sync
                if hasattr(self, 'font_size_input'):
                    self.font_size_input.setText(str(size))
            else:
                self.editor_font_size_input.setText(str(self.current_font_size))
        except ValueError:
            self.editor_font_size_input.setText(str(self.current_font_size))

    def on_editor_font_changed(self, font_family):
        """Handle editor font family change"""
        print(f"PreferencesWidget: Editor font family changed to {font_family}")
        self.current_font_family = font_family

        # Emit signal for other components
        self.font_changed.emit(font_family)

        # Update terminal font family combo too to keep in sync
        if hasattr(self, 'font_family_combo'):
            self.font_family_combo.setCurrentText(font_family)

    def on_copy_paste_changed(self, checked):
        """Handle copy-paste toggle change"""
        print(f"PreferencesWidget: Copy-paste enabled: {checked}")
        self.copy_paste_enabled = checked
        self.copy_paste_changed.emit(checked)

    def on_line_numbers_changed(self, text):
        """Handle line numbers toggle change"""
        enabled = (text == "On")
        print(f"PreferencesWidget: Line numbers enabled: {enabled}")
        self.show_line_numbers = enabled
        self.line_numbers_changed.emit(enabled)

    def on_tab_size_changed(self):
        """Handle tab size change"""
        try:
            size = int(self.tab_size_input.text())
            if 1 <= size <= 8:
                print(f"PreferencesWidget: Tab size changed to {size}")
                self.current_tab_size = size
                self.tab_size_changed.emit(size)
            else:
                self.tab_size_input.setText(str(self.current_tab_size))
        except ValueError:
            self.tab_size_input.setText(str(self.current_tab_size))

    def set_terminal_panel(self, terminal_panel):
        """Set the terminal panel reference"""
        print("PreferencesWidget: Setting terminal panel reference")
        self.terminal_panel = terminal_panel

        # Apply any pending font size
        if self.pending_font_size:
            print(f"PreferencesWidget: Applying pending font size {self.pending_font_size}")
            self.terminal_panel.update_font_size(self.pending_font_size)
            self.pending_font_size = None

    def set_initial_timezone(self, timezone):
        """Set the initial timezone from settings"""
        self.current_timezone = timezone
        if hasattr(self, 'timezone_combo'):
            index = self.timezone_combo.findText(timezone)
            if index >= 0:
                self.timezone_combo.setCurrentIndex(index)
