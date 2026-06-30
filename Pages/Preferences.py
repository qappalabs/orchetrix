import platform
import os
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFrame, QLineEdit, QCheckBox, QScrollArea, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QSettings

import logging
import zoneinfo
import Styles.PreferencesStyles as PreferencesStyles
from UI.Icons import Icons
from UI.ThemeManager import get_theme_manager
from UI.ThemeAwarePage import ThemeAwareMixin
from UI.CustomComboBox import CustomComboBox
from Utils.time_utils import TimezoneManager

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 24)
        self.toggled.connect(self.on_state_changed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._circle_position = 10

        # Connect to theme changes
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

        # Initialize timezone manager
        self.tz_manager = TimezoneManager.get_instance()
        self.current_timezone = self.tz_manager.get_current_timezone_name()
        
        self.timezone_timer = QTimer(self)
        self.timezone_timer.timeout.connect(self.update_timezone_display)

        # Initialize theme manager and settings
        self.theme_manager = get_theme_manager()
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
        return self.tz_manager.get_current_timezone_name()

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
        for btn_name in ('app_btn', 'proxy_btn', 'kubernetes_btn', 'editor_btn', 'terminal_btn'):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.setStyleSheet(PreferencesStyles.get_sidebar_button_style())
                except RuntimeError:
                    pass

        # Update Back Button Icon
        if hasattr(self, 'back_btn'):
            try:
                theme_name = self.theme_manager.get_current_theme_name() or "Dark"
                icon = Icons.get_theme_icon("back_arrow.svg", theme_name)
                self.back_btn.setIcon(icon)
                self.back_btn.setStyleSheet(PreferencesStyles.get_back_button_style())
            except RuntimeError:
                pass

        # Null-out tracked widget references BEFORE rebuilding so no stale
        # C++ objects remain accessible after the old content widget is deleted.
        for attr in ('theme_combo', 'timezone_combo', 'timezone_info',
                     'line_numbers_combo', 'tab_size_input',
                     'editor_font_size_input', 'editor_font_family_combo',
                     'font_size_input', 'font_family_combo', 'startup_status'):
            if hasattr(self, attr):
                obj = getattr(self, attr)
                if obj is not None:
                    try:
                        obj.blockSignals(True)
                    except RuntimeError:
                        pass
                setattr(self, attr, None)

        # Rebuild the current section with updated styles
        try:
            self.show_section(self.current_section)
        except Exception as e:
            logging.warning(f"PreferencesWidget: error rebuilding section on theme change: {e}")

    def go_back(self):
        self.back_signal.emit()

    def create_back_button(self):
        self.back_btn = QPushButton()

        # Use theme-aware icon
        theme_name = get_theme_manager().get_current_theme_name() or "Dark"
        icon = Icons.get_theme_icon("back_arrow.svg", theme_name)

        self.back_btn.setIcon(icon)
        self.back_btn.setIconSize(QSize(24, 24))
        self.back_btn.setFixedSize(30, 30)
        self.back_btn.setStyleSheet(PreferencesStyles.get_back_button_style())
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.go_back)
        return self.back_btn

    def _make_settings_card(self, title):
        """Create a card QFrame with a grey title bar and content area.
        Returns (card_frame, content_layout) so caller can add widgets."""
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(PreferencesStyles.get_card_outer_style())

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Title bar
        title_label = QLabel(title)
        title_label.setObjectName("sectionHeader")
        title_label.setStyleSheet(PreferencesStyles.get_subsection_header_style())
        card_layout.addWidget(title_label)

        # Content container
        content_widget = QWidget()
        content_widget.setStyleSheet(PreferencesStyles.get_card_content_style())
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 20, 24, 24)
        content_layout.setSpacing(10)
        card_layout.addWidget(content_widget)

        return card, content_layout

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
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        # Page title
        app_header = QLabel("Application")
        app_header.setObjectName("header")
        app_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        content_layout.addWidget(app_header)

        # --- THEME card ---
        theme_card, theme_content = self._make_settings_card("THEME")
        self.theme_combo = CustomComboBox()
        self.theme_combo.setFixedHeight(40)
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        current_theme = self.theme_manager.get_current_theme_name()
        self.theme_combo.setCurrentText(current_theme)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_content.addWidget(self.theme_combo)
        content_layout.addWidget(theme_card)

        # --- EXTENSION INSTALL REGISTRY card ---
        reg_card, reg_content = self._make_settings_card("EXTENSION INSTALL REGISTRY")

        radio_container = QWidget()
        radio_container.setObjectName("RadioGroup")
        radio_container.setStyleSheet(PreferencesStyles.get_radio_group_style())
        radio_layout = QHBoxLayout(radio_container)
        radio_layout.setContentsMargins(12, 8, 12, 8)
        radio_layout.setSpacing(20)
        radio_default = QRadioButton("Default Url")
        radio_custom = QRadioButton("Custom Url")
        radio_default.setChecked(True)
        radio_layout.addWidget(radio_default)
        radio_layout.addWidget(radio_custom)
        radio_layout.addStretch()
        reg_content.addWidget(radio_container)

        registry_help = QLabel(
            "This setting is to change the registry URL for installing extensions by name. "
            "If you are unable to access the default registry (https://registry.npmjs.org) "
            "you can change it in your .npmrc file or in the input below."
        )
        registry_help.setStyleSheet(PreferencesStyles.get_description_style())
        registry_help.setWordWrap(True)
        reg_content.addWidget(registry_help)

        registry_input = QLineEdit()
        registry_input.setPlaceholderText("Custom Extension Registry URL...")
        registry_input.setStyleSheet(PreferencesStyles.get_input_style())
        reg_content.addWidget(registry_input)
        content_layout.addWidget(reg_card)

        # --- START-UP card ---
        startup_card, startup_content = self._make_settings_card("START-UP")
        startup_row = QWidget()
        startup_row.setStyleSheet("background-color: transparent;")
        startup_layout = QHBoxLayout(startup_row)
        startup_layout.setContentsMargins(0, 4, 0, 4)
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
        startup_content.addWidget(startup_row)
        content_layout.addWidget(startup_card)

        # --- LOCAL TIMEZONE card ---
        tz_card, tz_content = self._make_settings_card("LOCAL TIMEZONE")
        self.timezone_combo = CustomComboBox()
        self.timezone_combo.setFixedHeight(40)
        self.timezone_combo.addItems([
            "Asia/Calcutta", "America/New_York", "Europe/London",
            "Europe/Berlin", "Asia/Tokyo", "Asia/Singapore",
            "Australia/Sydney", "Pacific/Auckland"
        ])
        self.timezone_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            index = self.timezone_combo.findText(self.current_timezone)
            if index < 0 and self.current_timezone:
                # Saved tz isn't a preset (e.g. default "UTC"); add it so it
                # can be selected instead of falling back to the first preset.
                self.timezone_combo.addItem(self.current_timezone)
                index = self.timezone_combo.findText(self.current_timezone)
            if index >= 0:
                self.timezone_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error setting current timezone: {e}")
        self.timezone_combo.currentIndexChanged.connect(self.change_timezone)
        tz_content.addWidget(self.timezone_combo)

        self.timezone_info = QLabel()
        self.timezone_info.setStyleSheet(PreferencesStyles.get_description_style())
        self.update_timezone_display()
        tz_content.addWidget(self.timezone_info)

        tz_btn_row = QWidget()
        tz_btn_row.setStyleSheet("background-color: transparent;")
        tz_btn_layout = QHBoxLayout(tz_btn_row)
        tz_btn_layout.setContentsMargins(0, 8, 0, 0)
        timezone_apply_btn = QPushButton("Apply Timezone")
        timezone_apply_btn.setStyleSheet(PreferencesStyles.get_button_primary_style())
        timezone_apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        timezone_apply_btn.clicked.connect(self.apply_timezone)
        tz_btn_layout.addStretch()
        tz_btn_layout.addWidget(timezone_apply_btn)
        tz_content.addWidget(tz_btn_row)
        content_layout.addWidget(tz_card)

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

            # Simulate exactly what TimezoneManager would output for that selected timezone
            # without inherently applying it fully yet
            try:
                selected_tz = zoneinfo.ZoneInfo(timezone)
                now_utc = datetime.now(zoneinfo.ZoneInfo("UTC"))
                local_time = now_utc.astimezone(selected_tz)
                
                time_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
                local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
                # Format timezone string: get abbreviation format (e.g., EST)
                tz_abbr = local_time.tzname()
                
                # Format time offset
                offset = local_time.utcoffset()
                hours, remainder = divmod(int(offset.total_seconds()), 3600)
                minutes = remainder // 60
                sign = '+' if hours >= 0 else '-'
                offset_str = f"{sign}{abs(hours)}:{abs(minutes):02d}"
                
                time_str += f" | {local_time_str} {tz_abbr} (UTC{offset_str})"
            except Exception as tz_err:
                 time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

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

                success = self.tz_manager.set_timezone(timezone)

                if success:
                    # Update only after the manager confirms, so a failed apply
                    # leaves the UI aligned with the active timezone.
                    self.current_timezone = timezone
                    print(f"Applying timezone change to: {timezone}")
                    # Emit signal to notify application of timezone change
                    self.timezone_changed.emit(timezone)
                    
                    # Show confirmation message
                    QMessageBox.information(self, "Timezone Changed",
                                            f"Timezone has been changed to {timezone}.\nApplication display times will use this timezone.")
                    
                    # Clear pending timezone
                    del self.pending_timezone
                else:
                    QMessageBox.warning(self, "Timezone Error",
                                        f"Failed to change timezone to {timezone}")
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
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        proxy_header = QLabel("Proxy")
        proxy_header.setObjectName("header")
        proxy_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        content_layout.addWidget(proxy_header)

        # --- HTTP PROXY card ---
        proxy_card, proxy_content = self._make_settings_card("HTTP PROXY")
        proxy_input = QLineEdit()
        proxy_input.setPlaceholderText("Type HTTP proxy url (example: http://proxy.acme.org:8080)")
        proxy_input.setStyleSheet(PreferencesStyles.get_input_style())
        proxy_content.addWidget(proxy_input)
        proxy_desc = QLabel("Proxy is used only for non-cluster communication.")
        proxy_desc.setStyleSheet(PreferencesStyles.get_description_style())
        proxy_content.addWidget(proxy_desc)
        content_layout.addWidget(proxy_card)

        # --- CERTIFICATE TRUST card ---
        cert_card, cert_content = self._make_settings_card("CERTIFICATE TRUST")
        cert_row = QWidget()
        cert_row.setStyleSheet("background-color: transparent;")
        cert_layout = QHBoxLayout(cert_row)
        cert_layout.setContentsMargins(0, 4, 0, 4)
        cert_text = QLabel("Allow untrusted Certificate Authorities")
        cert_text.setStyleSheet(PreferencesStyles.get_text_style())
        cert_toggle = ToggleSwitch()
        cert_toggle.setChecked(False)
        cert_layout.addWidget(cert_text)
        cert_layout.addStretch()
        cert_layout.addWidget(cert_toggle)
        cert_content.addWidget(cert_row)
        cert_desc = QLabel(
            "This will make Orchetrix trust ANY certificate authority without any validations. "
            "Needed with some corporate proxies that do certificate re-writing. "
            "Does not affect cluster communications!"
        )
        cert_desc.setStyleSheet(PreferencesStyles.get_description_style())
        cert_desc.setWordWrap(True)
        cert_content.addWidget(cert_desc)
        content_layout.addWidget(cert_card)

        content_layout.addStretch()
        self.content_scroll.setWidget(content_widget)


    def show_kubernetes_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        k8s_header = QLabel("Kubernetes")
        k8s_header.setObjectName("header")
        k8s_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        content_layout.addWidget(k8s_header)

        # --- KUBECTL BINARY card ---
        kubectl_card, kubectl_content = self._make_settings_card("KUBECTL BINARY")
        kubectl_path_input = QLineEdit()
        kubectl_path_input.setPlaceholderText("Path to kubectl binary...")
        kubectl_path_input.setStyleSheet(PreferencesStyles.get_input_style())
        kubectl_content.addWidget(kubectl_path_input)
        content_layout.addWidget(kubectl_card)

        # --- KUBECONFIG card ---
        kubeconfig_card, kubeconfig_content = self._make_settings_card("KUBECONFIG")
        kubeconfig_path_input = QLineEdit()
        kubeconfig_path_input.setPlaceholderText("Path to kubeconfig file...")
        kubeconfig_path_input.setStyleSheet(PreferencesStyles.get_input_style())
        kubeconfig_content.addWidget(kubeconfig_path_input)
        content_layout.addWidget(kubeconfig_card)

        # --- HELM CHARTS card ---
        helm_card, helm_content = self._make_settings_card("HELM CHARTS")
        helm_row = QWidget()
        helm_row.setStyleSheet("background-color: transparent;")
        helm_row_layout = QHBoxLayout(helm_row)
        helm_row_layout.setContentsMargins(0, 0, 0, 0)
        helm_repos_combo = CustomComboBox()
        helm_repos_combo.setFixedHeight(40)
        helm_repos_combo.addItem("Repositories")
        add_repo_btn = QPushButton("Add Custom Helm Repo")
        add_repo_btn.setStyleSheet(PreferencesStyles.get_button_primary_style())
        helm_row_layout.addWidget(helm_repos_combo)
        helm_row_layout.addSpacing(10)
        helm_row_layout.addWidget(add_repo_btn)
        helm_row_layout.addStretch()
        helm_content.addWidget(helm_row)

        repo_item_row = QWidget()
        repo_item_row.setStyleSheet("background-color: transparent;")
        repo_item_layout = QHBoxLayout(repo_item_row)
        repo_item_layout.setContentsMargins(0, 8, 0, 0)
        repo_details = QVBoxLayout()
        helm_repo_item = QLabel("bitnami")
        helm_repo_url = QLabel("https://charts.bitnami.com/bitnami")
        helm_repo_item.setStyleSheet(PreferencesStyles.get_text_style())
        helm_repo_url.setStyleSheet(PreferencesStyles.get_description_style())
        repo_details.addWidget(helm_repo_item)
        repo_details.addWidget(helm_repo_url)
        delete_repo_btn = QPushButton("🗑")
        delete_repo_btn.setStyleSheet(PreferencesStyles.get_delete_button_style())
        repo_item_layout.addLayout(repo_details)
        repo_item_layout.addStretch()
        repo_item_layout.addWidget(delete_repo_btn)
        helm_content.addWidget(repo_item_row)
        content_layout.addWidget(helm_card)

        content_layout.addStretch()
        self.content_scroll.setWidget(content_widget)


    def show_editor_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        editor_header = QLabel("Editor")
        editor_header.setObjectName("header")
        editor_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        content_layout.addWidget(editor_header)

        # --- LINE NUMBERS card ---
        ln_card, ln_content = self._make_settings_card("LINE NUMBERS")
        self.line_numbers_combo = CustomComboBox()
        self.line_numbers_combo.setFixedHeight(40)
        self.line_numbers_combo.addItems(["On", "Off"])
        self.line_numbers_combo.setCurrentText("On" if self.show_line_numbers else "Off")
        self.line_numbers_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.line_numbers_combo.currentTextChanged.connect(self.on_line_numbers_changed)
        ln_content.addWidget(self.line_numbers_combo)
        ln_help = QLabel("Show or hide line numbers in editor")
        ln_help.setStyleSheet(PreferencesStyles.get_description_style())
        ln_content.addWidget(ln_help)
        content_layout.addWidget(ln_card)

        # --- TAB SIZE card ---
        tab_card, tab_content = self._make_settings_card("TAB SIZE")
        self.tab_size_input = QLineEdit()
        self.tab_size_input.setText(str(self.current_tab_size))
        self.tab_size_input.setStyleSheet(PreferencesStyles.get_input_style())
        self.tab_size_input.editingFinished.connect(self.on_tab_size_changed)
        tab_content.addWidget(self.tab_size_input)
        tab_help = QLabel("Number of spaces per tab in the editor")
        tab_help.setStyleSheet(PreferencesStyles.get_description_style())
        tab_content.addWidget(tab_help)
        content_layout.addWidget(tab_card)

        # --- FONT SIZE card ---
        fs_card, fs_content = self._make_settings_card("FONT SIZE")
        self.editor_font_size_input = QLineEdit()
        self.editor_font_size_input.setText(str(self.current_font_size))
        self.editor_font_size_input.setStyleSheet(PreferencesStyles.get_input_style())
        self.editor_font_size_input.editingFinished.connect(self.on_editor_font_size_changed)
        fs_content.addWidget(self.editor_font_size_input)
        fs_help = QLabel("This font size applies to all editors including the YAML editor")
        fs_help.setStyleSheet(PreferencesStyles.get_description_style())
        fs_content.addWidget(fs_help)
        content_layout.addWidget(fs_card)

        # --- FONT FAMILY card ---
        ff_card, ff_content = self._make_settings_card("FONT FAMILY")
        self.editor_font_family_combo = CustomComboBox()
        self.editor_font_family_combo.setFixedHeight(40)
        self.editor_font_family_combo.addItems(["Consolas", "RobotoMono", "Courier New", "Monospace"])
        self.editor_font_family_combo.setCurrentText(self.current_font_family)
        self.editor_font_family_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.editor_font_family_combo.currentTextChanged.connect(self.on_editor_font_changed)
        ff_content.addWidget(self.editor_font_family_combo)
        ff_help = QLabel("This font family applies to all editors including the YAML editor")
        ff_help.setStyleSheet(PreferencesStyles.get_description_style())
        ff_content.addWidget(ff_help)
        content_layout.addWidget(ff_card)

        content_layout.addStretch()
        self.content_scroll.setWidget(content_widget)

    def show_terminal_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        terminal_header = QLabel("Terminal")
        terminal_header.setObjectName("header")
        terminal_header.setStyleSheet(PreferencesStyles.get_section_header_style())
        content_layout.addWidget(terminal_header)

        # --- TERMINAL SHELL PATH card ---
        shell_card, shell_content = self._make_settings_card("TERMINAL SHELL PATH")
        shell_path_input = QLineEdit()
        shell_path_input.setText("powershell.exe")
        shell_path_input.setStyleSheet(PreferencesStyles.get_input_style())
        shell_content.addWidget(shell_path_input)
        content_layout.addWidget(shell_card)

        # --- TERMINAL COPY & PASTE card ---
        cp_card, cp_content = self._make_settings_card("TERMINAL COPY & PASTE")
        cp_row = QWidget()
        cp_row.setStyleSheet("background-color: transparent;")
        cp_layout = QHBoxLayout(cp_row)
        cp_layout.setContentsMargins(0, 4, 0, 4)
        copy_paste_text = QLabel("Copy on select and paste on right-click")
        copy_paste_text.setStyleSheet(PreferencesStyles.get_text_style())
        copy_paste_toggle = ToggleSwitch()
        copy_paste_toggle.setChecked(self.copy_paste_enabled)
        copy_paste_toggle.toggled.connect(self.on_copy_paste_changed)
        cp_layout.addWidget(copy_paste_text)
        cp_layout.addStretch()
        cp_layout.addWidget(copy_paste_toggle)
        cp_content.addWidget(cp_row)
        content_layout.addWidget(cp_card)

        # --- TERMINAL THEME card ---
        tt_card, tt_content = self._make_settings_card("TERMINAL THEME")
        theme_combo = CustomComboBox()
        theme_combo.setFixedHeight(40)
        theme_combo.addItems(["Dark"])
        theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        tt_content.addWidget(theme_combo)
        content_layout.addWidget(tt_card)

        # --- FONT SIZE card ---
        tfs_card, tfs_content = self._make_settings_card("FONT SIZE")
        self.font_size_input = QLineEdit()
        self.font_size_input.setText(str(self.current_font_size))
        self.font_size_input.setStyleSheet(PreferencesStyles.get_input_style())
        self.font_size_input.editingFinished.connect(self.on_font_size_changed)
        tfs_content.addWidget(self.font_size_input)
        content_layout.addWidget(tfs_card)

        # --- FONT FAMILY card ---
        tff_card, tff_content = self._make_settings_card("FONT FAMILY")
        self.font_family_combo = CustomComboBox()
        self.font_family_combo.setFixedHeight(40)
        self.font_family_combo.addItems(["RobotoMono", "Consolas", "Courier New"])
        self.font_family_combo.setCurrentText(self.current_font_family)
        self.font_family_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.font_family_combo.currentTextChanged.connect(self.on_font_changed)
        tff_content.addWidget(self.font_family_combo)
        content_layout.addWidget(tff_card)

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

        # Apply theme - theme_manager.set_theme now handles persistence
        # and emits theme_changed signal to update all widgets
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
