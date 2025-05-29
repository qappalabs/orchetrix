import sys
import platform
import os
import time
import json
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFrame, QLineEdit, QCheckBox, QScrollArea, QTextEdit, QMessageBox
)
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QPainter
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer

from UI.Styles import AppStyles, AppColors

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 24)
        self.toggled.connect(self.on_state_changed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._circle_position = 10

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Set colors based on state
        if self.isChecked():
            bg_color = QColor(AppColors.ACCENT_BLUE)
            circle_pos = 30
        else:
            bg_color = QColor(AppColors.TEXT_SECONDARY)
            circle_pos = 10

        # Draw background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)

        # Draw circle
        painter.setBrush(QColor(AppColors.TEXT_LIGHT))
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
                import winreg
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
                import winreg
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
        self.setStyleSheet(AppStyles.SIDEBAR_BUTTON_STYLE)
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class PreferencesWidget(QWidget):
    back_signal = pyqtSignal()
    font_changed = pyqtSignal(str)  # Signal for font family changes
    font_size_changed = pyqtSignal(int)  # Signal for font size changes
    copy_paste_changed = pyqtSignal(bool)  # Signal for copy-paste toggle changes
    line_numbers_changed = pyqtSignal(bool)  # Signal for line numbers toggle changes
    tab_size_changed = pyqtSignal(int)  # Signal for tab size changes
    timezone_changed = pyqtSignal(str)  # Signal for timezone changes
    update_channel_changed = pyqtSignal(str)  # Signal for update channel changes

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
        self._current_update_dialog = None  # Track current update dialog
        
        # Initialize timezone
        self.current_timezone = self.get_system_timezone()
        
        # Initialize update channel
        self.current_update_channel = "Stable"  # Default to Stable
        
        print("PreferencesWidget: Initialized with terminal_panel=None")
        self.setup_ui()
        
        # Set timer to update the timezone display every second
        self.timezone_timer = QTimer(self)
        self.timezone_timer.timeout.connect(self.update_timezone_display)
        self.timezone_timer.start(1000)  # Update every second

    def get_system_timezone(self):
        """Get the current system timezone"""
        try:
            # Try to get from time module
            return time.tzname[0]
        except Exception:
            # Fallback
            return "Asia/Calcutta"  # Default timezone

    def setup_ui(self):
        self.setStyleSheet(AppStyles.PREFERENCES_MAIN_STYLE)

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(AppStyles.PREFERENCES_SIDEBAR_STYLE)
        sidebar_layout = QVBoxLayout(sidebar)
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
        preferences_label = QLabel("PREFERENCES")
        preferences_label.setStyleSheet(AppStyles.PREFERENCES_HEADER_STYLE)
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
        self.content_scroll.setStyleSheet(AppStyles.CONTENT_AREA_STYLE)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_scroll)

        self.current_section = "app"
        self.show_section("app")

    def go_back(self):
        self.back_signal.emit()

    def create_back_button(self):
        back_btn = QPushButton()
        back_btn.setIcon(QIcon("icons/back_arrow.png"))
        back_btn.setIconSize(QSize(24, 24))
        back_btn.setFixedSize(30, 30)
        back_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; }")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.go_back)
        return back_btn

    def show_section(self, section):
        self.app_btn.setChecked(False)
        self.proxy_btn.setChecked(False)
        self.kubernetes_btn.setChecked(False)
        self.editor_btn.setChecked(False)
        self.terminal_btn.setChecked(False)

        self.current_section = section
        if section == "app":
            self.app_btn.setChecked(True)
            self.show_app_section()
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
        app_header.setStyleSheet(AppStyles.SECTION_HEADER_STYLE)
        content_layout.addWidget(app_header)

        # Theme section
        theme_label = QLabel("THEME")
        theme_label.setObjectName("sectionHeader")
        theme_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(theme_label)

        theme_combo = QComboBox()
        theme_combo.addItems(["Select...", "Dark"])
        theme_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(theme_combo)

        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider1)

        # Extension registry section
        registry_label = QLabel("EXTENSION INSTALL REGISTRY")
        registry_label.setObjectName("sectionHeader")
        registry_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(registry_label)

        registry_combo = QComboBox()
        registry_combo.addItems(["Default Url", "Custom Url"])
        registry_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        registry_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(registry_combo)

        registry_help = QLabel(
            "This setting is to change the registry URL for installing extensions by name. If you are unable to access the\n"
            "default registry (https://registry.npmjs.org) you can change it in your .npmrc file or in the input below."
        )
        registry_help.setStyleSheet(AppStyles.DESCRIPTION_STYLE)
        registry_help.setWordWrap(True)
        content_layout.addWidget(registry_help)

        registry_input = QLineEdit()
        registry_input.setPlaceholderText("Custom Extension Registry URL...")
        registry_input.setStyleSheet(AppStyles.INPUT_STYLE)
        content_layout.addWidget(registry_input)

        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider2)

        # Start-up section
        startup_label = QLabel("START-UP")
        startup_label.setObjectName("sectionHeader")
        startup_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(startup_label)

        startup_container = QWidget()
        startup_layout = QHBoxLayout(startup_container)
        startup_layout.setContentsMargins(0, 10, 0, 10)

        startup_text = QLabel("Automatically start Orchetrix on login")
        startup_text.setStyleSheet(AppStyles.TEXT_STYLE)

        self.startup_status = QLabel("Disabled")
        self.startup_status.setStyleSheet(AppStyles.STATUS_TEXT_STYLE)

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
        divider3.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider3)

        # Update channel section
        update_label = QLabel("UPDATE CHANNEL")
        update_label.setObjectName("sectionHeader")
        update_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(update_label)

        # Update channel combo box
        self.update_channel_combo = QComboBox()
        self.update_channel_combo.addItems(["Stable", "Beta", "Alpha"])
        
        # Set current value from settings if available
        try:
            # Try to set the combo box to the current update channel
            index = self.update_channel_combo.findText(self.current_update_channel)
            if index >= 0:
                self.update_channel_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error setting current update channel: {e}")
            
        self.update_channel_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        self.update_channel_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_channel_combo.currentTextChanged.connect(self.on_update_channel_changed)
        content_layout.addWidget(self.update_channel_combo)

        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        divider4.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider4)

        # Local Timezone section
        timezone_label = QLabel("LOCAL TIMEZONE")
        timezone_label.setObjectName("sectionHeader")
        timezone_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(timezone_label)

        # Timezone combo box
        self.timezone_combo = QComboBox()
        self.timezone_combo.addItems([
            "Asia/Calcutta", "America/New_York", "Europe/London",
            "Europe/Berlin", "Asia/Tokyo", "Asia/Singapore",
            "Australia/Sydney", "Pacific/Auckland"
        ])
        self.timezone_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
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
        self.timezone_info.setStyleSheet(AppStyles.DESCRIPTION_STYLE)
        self.update_timezone_display()  # Initialize with current time
        content_layout.addWidget(self.timezone_info)

        # Add apply button
        timezone_apply_container = QWidget()
        timezone_apply_layout = QHBoxLayout(timezone_apply_container)
        timezone_apply_layout.setContentsMargins(0, 10, 0, 10)
        
        timezone_apply_btn = QPushButton("Apply Timezone")
        timezone_apply_btn.setStyleSheet(AppStyles.BUTTON_PRIMARY_STYLE)
        timezone_apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        timezone_apply_btn.clicked.connect(self.apply_timezone)
        
        timezone_apply_layout.addStretch()
        timezone_apply_layout.addWidget(timezone_apply_btn)
        
        content_layout.addWidget(timezone_apply_container)

        content_layout.addStretch()

        self.content_scroll.setWidget(content_widget)

    def on_update_channel_changed(self, channel):
        """Handle update channel selection change - apply changes immediately"""
        if channel != self.current_update_channel:
            old_channel = self.current_update_channel
            self.current_update_channel = channel
            print(f"Update channel selection changed from {old_channel} to: {channel}")
            
            # Apply the channel change immediately
            self.apply_update_channel(channel)
            
            # Check for updates automatically
            QTimer.singleShot(300, self.check_for_updates)

    def apply_update_channel(self, channel):
        """Apply the selected update channel"""
        try:
            print(f"Applying update channel change to {channel}")
            
            # Emit signal to notify application of update channel change
            self.update_channel_changed.emit(channel)
            
            # Show notification message with appropriate warning based on channel
            if channel == "Stable":
                message = f"Update channel has been changed to {channel}.\nYou are now using the production-ready stable version."
            elif channel == "Beta":
                message = f"Update channel has been changed to {channel}.\nYou may encounter some minor issues. Use for testing."
            elif channel == "Alpha":
                message = f"Update channel has been changed to {channel}.\nWARNING: Alpha version may have significant bugs. Use with caution!"
            else:
                message = f"Update channel has been changed to {channel}."
            
            # Show a notification toast instead of a modal dialog to be less intrusive
            # For now, we'll show a small, non-modal message box
            msg = QMessageBox(self)
            msg.setWindowTitle("Update Channel Changed")
            msg.setText(message)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
            msg.setWindowOpacity(0.9)
            
            # Position it in the bottom right corner of the app section
            QTimer.singleShot(0, lambda: self.position_notification(msg))
            
            # Automatically close after 3 seconds
            QTimer.singleShot(3000, msg.close)
            
            # Show the notification
            msg.show()
            
            # Save the preference to settings
            self.save_update_channel_preference(channel)
            
        except Exception as e:
            print(f"Error applying update channel: {e}")
            QMessageBox.warning(self, "Update Channel Error", 
                               f"Failed to change update channel: {str(e)}")

    def position_notification(self, msg):
        """Position the notification in the bottom right of the app section"""
        if hasattr(self, 'content_scroll') and self.content_scroll:
            # Calculate position
            pos = self.content_scroll.mapToGlobal(self.content_scroll.rect().bottomRight())
            pos.setX(pos.x() - msg.width() - 20)
            pos.setY(pos.y() - msg.height() - 20)
            msg.move(pos)

    def check_for_updates(self):
        """Check for updates based on the selected channel"""
        try:
            channel = self.current_update_channel
            print(f"Checking for updates on {channel} channel")
            
            # Create a progress message with a Cancel button
            checking_msg = QMessageBox(self)
            checking_msg.setWindowTitle("Checking for Updates")
            checking_msg.setText(f"Checking for updates on {channel} channel...")
            checking_msg.setStandardButtons(QMessageBox.StandardButton.Cancel)
            checking_msg.setModal(True)  # Make it modal to ensure it stays in focus
            
            # Connect the rejected signal (triggered when Cancel is clicked or dialog is closed)
            checking_msg.rejected.connect(checking_msg.close)
            
            # Store the message box reference
            self._current_update_dialog = checking_msg
            
            # Show the message and process events to update UI
            checking_msg.show()
            
            # Simulate a network request here
            QTimer.singleShot(1500, lambda: self.handle_update_check_result(checking_msg, channel))
            
        except Exception as e:
            print(f"Error checking for updates: {e}")
            QMessageBox.warning(self, "Update Check Error", 
                               f"Failed to check for updates: {str(e)}")
            # Ensure any open dialog is closed
            if hasattr(self, '_current_update_dialog') and self._current_update_dialog:
                try:
                    self._current_update_dialog.close()
                except:
                    pass

    def handle_update_check_result(self, message_box, channel):
        """Handle the result of the update check"""
        # Check if the message box is still valid and open
        try:
            if message_box and message_box.isVisible():
                message_box.close()
        except RuntimeError:
            # Widget might have been deleted
            pass
        
        # Clear the reference
        if hasattr(self, '_current_update_dialog'):
            self._current_update_dialog = None
        
        # Simulate different results based on channel
        update_available = False
        
        if channel == "Alpha":
            # Alpha has frequent updates
            update_available = True
            version = "2.1.0-alpha.3"
            notes = "New experimental features added:\n- Cloud synchronization\n- Advanced terminal capabilities\n- Extended API support\n\nWarning: This is an alpha build with known issues."
        elif channel == "Beta":
            # Beta has occasional updates
            update_available = True
            version = "2.0.5-beta"
            notes = "Beta features ready for testing:\n- Performance improvements\n- Bug fixes for recent issues\n- UI enhancements\n\nThis version has been tested but may have minor issues."
        else:  # Stable
            # Stable has rare updates
            update_available = False
            version = "2.0.0"
            notes = "You are running the latest stable version."
        
        if update_available:
            # Show update available message with details
            update_msg = QMessageBox(self)
            update_msg.setWindowTitle("Update Available")
            update_msg.setText(f"A new {channel} update is available!")
            update_msg.setInformativeText(f"Version: {version}\n\nRelease notes:\n{notes}")
            update_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            update_msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            update_msg.button(QMessageBox.StandardButton.Yes).setText("Download and Install")
            update_msg.button(QMessageBox.StandardButton.No).setText("Not Now")
            update_msg.setModal(True)  # Make it modal
            
            # Store reference to the dialog
            self._current_update_dialog = update_msg
            
            result = update_msg.exec()
            
            # Clear the reference after dialog is closed
            self._current_update_dialog = None
            
            if result == QMessageBox.StandardButton.Yes:
                # User chose to download and install
                self.download_and_install_update(version, channel)
        else:
            # No update available - just show a brief notification
            msg = QMessageBox(self)
            msg.setWindowTitle("No Updates Available")
            msg.setText(f"You're running the latest {channel} version: {version}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
            msg.setWindowOpacity(0.9)
            
            # Position it in the bottom right corner of the app section
            QTimer.singleShot(0, lambda: self.position_notification(msg))
            
            # Automatically close after 2 seconds
            QTimer.singleShot(2000, msg.close)
            
            # Show the notification
            msg.show()

    def download_and_install_update(self, version, channel):
        """Download and install the update"""
        try:
            # Show download progress
            progress_msg = QMessageBox(self)
            progress_msg.setWindowTitle("Downloading Update")
            progress_msg.setText(f"Downloading {channel} version {version}...")
            progress_msg.setStandardButtons(QMessageBox.StandardButton.Cancel)
            progress_msg.setModal(True)  # Make it modal
            
            # Store reference
            self._current_update_dialog = progress_msg
            
            # Show the message and process events to update UI
            progress_msg.show()
            
            # Simulate download and installation process
            QTimer.singleShot(3000, lambda: self.finish_update_installation(progress_msg, version, channel))
            
        except Exception as e:
            print(f"Error downloading update: {e}")
            QMessageBox.warning(self, "Update Error", 
                               f"Failed to download and install update: {str(e)}")
            # Ensure any open dialog is closed
            if hasattr(self, '_current_update_dialog') and self._current_update_dialog:
                try:
                    self._current_update_dialog.close()
                except:
                    pass

    def finish_update_installation(self, progress_msg, version, channel):
        """Finish the update installation process"""
        # Close the progress message if it's still valid
        try:
            if progress_msg and progress_msg.isVisible():
                progress_msg.close()
        except RuntimeError:
            # Widget might have been deleted
            pass
        
        # Clear the reference
        self._current_update_dialog = None
        
        # Show completion message
        completion_msg = QMessageBox(self)
        completion_msg.setWindowTitle("Update Complete")
        completion_msg.setText(f"Successfully updated to {channel} version {version}!\n\nThe application will restart to apply changes.")
        completion_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        completion_msg.setModal(True)
        completion_msg.exec()
        
        # In a real implementation, you would restart the application here
        # For this demo, we'll just print a message
        print(f"Application would restart now to apply {channel} version {version}")

    def save_update_channel_preference(self, channel):
        """Save the update channel preference to settings file"""
        try:
            # Determine settings file path
            if getattr(sys, 'frozen', False):
                # Running in PyInstaller bundle
                base_dir = os.path.dirname(sys.executable)
            else:
                # Running in normal Python environment
                base_dir = os.path.dirname(os.path.abspath(__file__))
                
            settings_dir = os.path.join(base_dir, "settings")
            os.makedirs(settings_dir, exist_ok=True)
            
            settings_file = os.path.join(settings_dir, "app_settings.txt")
            
            # Read existing settings
            settings = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            settings[key] = value
            
            # Update update channel
            settings['update_channel'] = channel
            
            # Write back all settings
            with open(settings_file, 'w') as f:
                for key, value in settings.items():
                    f.write(f"{key}={value}\n")
                    
            print(f"Saved update channel preference to {settings_file}")
            
        except Exception as e:
            print(f"Failed to save update channel preference: {e}")

    def update_timezone_display(self):
        """Update the timezone info label with current time in selected timezone"""
        try:
            # Use the current selected timezone
            timezone = self.timezone_combo.currentText() if hasattr(self, 'timezone_combo') else self.current_timezone
            
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
            
            if hasattr(self, 'timezone_info'):
                self.timezone_info.setText(time_str)
        except Exception as e:
            print(f"Error updating timezone display: {e}")
            if hasattr(self, 'timezone_info'):
                self.timezone_info.setText(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
        proxy_header.setStyleSheet(AppStyles.SECTION_HEADER_STYLE)
        header_layout.addWidget(proxy_header)
        # header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        # HTTP Proxy section
        http_proxy_label = QLabel("HTTP PROXY")
        http_proxy_label.setObjectName("sectionHeader")
        http_proxy_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(http_proxy_label)

        proxy_input = QLineEdit()
        proxy_input.setPlaceholderText("Type HTTP proxy url (example: http://proxy.acme.org:8080)")
        proxy_input.setStyleSheet(AppStyles.INPUT_STYLE)
        content_layout.addWidget(proxy_input)

        proxy_desc = QLabel("Proxy is used only for non-cluster communication.")
        proxy_desc.setStyleSheet(AppStyles.DESCRIPTION_STYLE)
        content_layout.addWidget(proxy_desc)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider)

        # Certificate Trust section
        cert_label = QLabel("CERTIFICATE TRUST")
        cert_label.setObjectName("sectionHeader")
        cert_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(cert_label)

        cert_container = QWidget()
        cert_layout = QHBoxLayout(cert_container)
        cert_layout.setContentsMargins(0, 10, 0, 10)

        cert_text = QLabel("Allow untrusted Certificate Authorities")
        cert_text.setStyleSheet(AppStyles.TEXT_STYLE)

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
        cert_desc.setStyleSheet(AppStyles.DESCRIPTION_STYLE)
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

        kubernetes_header = QLabel("Kubernetes")
        kubernetes_header.setObjectName("header")
        kubernetes_header.setStyleSheet(AppStyles.SECTION_HEADER_STYLE)
        header_layout.addWidget(kubernetes_header)
        # header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        # Kubectl Binary Download section
        kubectl_label = QLabel("KUBECTL BINARY DOWNLOAD")
        kubectl_label.setObjectName("sectionHeader")
        kubectl_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(kubectl_label)

        kubectl_download_container = QWidget()
        kubectl_download_layout = QHBoxLayout(kubectl_download_container)
        kubectl_download_layout.setContentsMargins(0, 10, 0, 10)

        kubectl_download_text = QLabel("Download kubectl binaries matching the Kubernetes cluster version")
        kubectl_download_text.setStyleSheet(AppStyles.TEXT_STYLE)

        kubectl_download_toggle = ToggleSwitch()
        kubectl_download_toggle.setChecked(True)

        kubectl_download_layout.addWidget(kubectl_download_text)
        kubectl_download_layout.addStretch()
        kubectl_download_layout.addWidget(kubectl_download_toggle)

        content_layout.addWidget(kubectl_download_container)

        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider1)

        # Download Mirror section
        download_mirror_label = QLabel("DOWNLOAD MIRROR")
        download_mirror_label.setObjectName("sectionHeader")
        download_mirror_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(download_mirror_label)

        download_mirror_combo = QComboBox()
        download_mirror_combo.addItems(["Default (Google)", "Alternative Mirror 1", "Alternative Mirror 2"])
        download_mirror_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        download_mirror_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(download_mirror_combo)

        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider2)

        # Directory for Binaries section
        binaries_dir_label = QLabel("DIRECTORY FOR BINARIES")
        binaries_dir_label.setObjectName("sectionHeader")
        binaries_dir_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(binaries_dir_label)

        binaries_dir_input = QLineEdit()
        binaries_dir_input.setText(r"C:\Users\Admin\AppData\Roaming\OpenLens\binaries")
        binaries_dir_input.setPlaceholderText("Directory to download binaries into")
        binaries_dir_input.setStyleSheet(AppStyles.INPUT_STYLE)
        content_layout.addWidget(binaries_dir_input)

        binaries_dir_desc = QLabel("The directory to download binaries into.")
        binaries_dir_desc.setStyleSheet(AppStyles.DESCRIPTION_STYLE)
        content_layout.addWidget(binaries_dir_desc)

        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        divider3.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider3)

        # Path to Kubectl Binary section
        kubectl_path_label = QLabel("PATH TO KUBECTL BINARY")
        kubectl_path_label.setObjectName("sectionHeader")
        kubectl_path_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(kubectl_path_label)

        kubectl_path_input = QLineEdit()
        kubectl_path_input.setText(r"C:\Users\Admin\AppData\Roaming\OpenLens\binaries\kubectl")
        kubectl_path_input.setPlaceholderText("Path to kubectl binary")
        kubectl_path_input.setStyleSheet(AppStyles.INPUT_STYLE)
        content_layout.addWidget(kubectl_path_input)

        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        divider4.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider4)

        # Kubeconfig Syncs section
        kubeconfig_label = QLabel("KUBECONFIG SYNCS")
        kubeconfig_label.setObjectName("sectionHeader")
        kubeconfig_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(kubeconfig_label)

        kubeconfig_sync_container = QWidget()
        kubeconfig_sync_layout = QHBoxLayout(kubeconfig_sync_container)
        kubeconfig_sync_layout.setContentsMargins(0, 10, 0, 10)

        sync_file_btn = QPushButton("Sync file(s)")
        sync_file_btn.setStyleSheet(AppStyles.BUTTON_PRIMARY_STYLE)
        sync_folder_btn = QPushButton("Sync folder(s)")
        sync_folder_btn.setStyleSheet(AppStyles.BUTTON_SECONDARY_STYLE)

        kubeconfig_sync_layout.addWidget(sync_file_btn)
        kubeconfig_sync_layout.addSpacing(10)
        kubeconfig_sync_layout.addWidget(sync_folder_btn)
        kubeconfig_sync_layout.addStretch()

        content_layout.addWidget(kubeconfig_sync_container)

        # Synced Items section
        synced_items_label = QLabel("SYNCED ITEMS")
        synced_items_label.setObjectName("sectionHeader")
        synced_items_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(synced_items_label)

        synced_items_container = QWidget()
        synced_items_layout = QHBoxLayout(synced_items_container)
        synced_items_layout.setContentsMargins(0, 10, 0, 10)

        synced_item = QLabel(r"C:\Users\Admin\.kube")
        synced_item.setStyleSheet(AppStyles.SYNCED_ITEM_STYLE)

        delete_btn = QPushButton("🗑")
        delete_btn.setStyleSheet(AppStyles.DELETE_BUTTON_STYLE)

        synced_items_layout.addWidget(synced_item)
        synced_items_layout.addStretch()
        synced_items_layout.addWidget(delete_btn)

        content_layout.addWidget(synced_items_container)

        divider5 = QFrame()
        divider5.setObjectName("divider")
        divider5.setFrameShape(QFrame.Shape.HLine)
        divider5.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider5)

        # Helm Charts section
        helm_charts_label = QLabel("HELM CHARTS")
        helm_charts_label.setObjectName("sectionHeader")
        helm_charts_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(helm_charts_label)

        helm_repos_container = QWidget()
        helm_repos_layout = QHBoxLayout(helm_repos_container)
        helm_repos_layout.setContentsMargins(0, 10, 0, 10)

        helm_repos_combo = QComboBox()
        helm_repos_combo.addItem("Repositories")
        helm_repos_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)

        add_repo_btn = QPushButton("Add Custom Helm Repo")
        add_repo_btn.setStyleSheet(AppStyles.BUTTON_PRIMARY_STYLE)

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
        helm_repo_item.setStyleSheet(AppStyles.TEXT_STYLE)
        helm_repo_url.setStyleSheet(AppStyles.DESCRIPTION_STYLE)

        delete_repo_btn = QPushButton("🗑")
        delete_repo_btn.setStyleSheet(AppStyles.DELETE_BUTTON_STYLE)

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
        editor_header.setStyleSheet(AppStyles.SECTION_HEADER_STYLE)
        header_layout.addWidget(editor_header)
        # header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        # Line Numbers section
        line_numbers_label = QLabel("LINE NUMBERS")
        line_numbers_label.setObjectName("sectionHeader")
        line_numbers_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(line_numbers_label)

        self.line_numbers_combo = QComboBox()
        self.line_numbers_combo.addItems(["On", "Off"])
        self.line_numbers_combo.setCurrentText("On" if self.show_line_numbers else "Off")
        self.line_numbers_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        self.line_numbers_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.line_numbers_combo.currentTextChanged.connect(self.on_line_numbers_changed)
        content_layout.addWidget(self.line_numbers_combo)

        # Help text for line numbers
        line_numbers_help = QLabel("Show or hide line numbers in editor")
        line_numbers_help.setStyleSheet(AppStyles.DESCRIPTION_STYLE)
        line_numbers_help.setWordWrap(True)
        content_layout.addWidget(line_numbers_help)

        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider2)

        # Tab Size section
        tab_size_label = QLabel("TAB SIZE")
        tab_size_label.setObjectName("sectionHeader")
        tab_size_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(tab_size_label)

        # Modified to use self.tab_size_input and connect signal
        self.tab_size_input = QLineEdit()
        self.tab_size_input.setText(str(self.current_tab_size))
        self.tab_size_input.setStyleSheet(AppStyles.INPUT_STYLE)
        self.tab_size_input.editingFinished.connect(self.on_tab_size_changed)
        content_layout.addWidget(self.tab_size_input)

        # Help text for Tab Size
        tab_size_help = QLabel("Number of spaces per tab in the editor")
        tab_size_help.setStyleSheet(AppStyles.DESCRIPTION_STYLE)
        tab_size_help.setWordWrap(True)
        content_layout.addWidget(tab_size_help)

        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        divider3.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider3)

        # Font Size section
        font_size_label = QLabel("FONT SIZE")
        font_size_label.setObjectName("sectionHeader")
        font_size_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(font_size_label)

        # This now affects the YAML editor too
        self.editor_font_size_input = QLineEdit()
        self.editor_font_size_input.setText(str(self.current_font_size))
        self.editor_font_size_input.setStyleSheet(AppStyles.INPUT_STYLE)
        self.editor_font_size_input.editingFinished.connect(self.on_editor_font_size_changed)
        content_layout.addWidget(self.editor_font_size_input)

        # Help text for Editor font size
        editor_font_help = QLabel("This font size applies to all editors including the YAML editor")
        editor_font_help.setStyleSheet(AppStyles.DESCRIPTION_STYLE)
        editor_font_help.setWordWrap(True)
        content_layout.addWidget(editor_font_help)

        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        divider4.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider4)

        # Font Family section
        font_family_label = QLabel("FONT FAMILY")
        font_family_label.setObjectName("sectionHeader")
        font_family_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(font_family_label)

        # This affects editors including YAML
        self.editor_font_family_combo = QComboBox()
        self.editor_font_family_combo.addItems(["Consolas", "RobotoMono", "Courier New", "Monospace"])
        self.editor_font_family_combo.setCurrentText(self.current_font_family)
        self.editor_font_family_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        self.editor_font_family_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.editor_font_family_combo.currentTextChanged.connect(self.on_editor_font_changed)
        content_layout.addWidget(self.editor_font_family_combo)

        # Help text for editor font family
        editor_font_family_help = QLabel("This font family applies to all editors including the YAML editor")
        editor_font_family_help.setStyleSheet(AppStyles.DESCRIPTION_STYLE)
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
        terminal_header.setStyleSheet(AppStyles.SECTION_HEADER_STYLE)
        header_layout.addWidget(terminal_header)
        # header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        # Terminal Shell Path section
        shell_path_label = QLabel("TERMINAL SHELL PATH")
        shell_path_label.setObjectName("sectionHeader")
        shell_path_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(shell_path_label)

        shell_path_input = QLineEdit()
        shell_path_input.setText("powershell.exe")
        shell_path_input.setStyleSheet(AppStyles.INPUT_STYLE)
        content_layout.addWidget(shell_path_input)

        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider1)

        # Terminal Copy & Paste section
        copy_paste_label = QLabel("TERMINAL COPY & PASTE")
        copy_paste_label.setObjectName("sectionHeader")
        copy_paste_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(copy_paste_label)

        copy_paste_container = QWidget()
        copy_paste_layout = QHBoxLayout(copy_paste_container)
        copy_paste_layout.setContentsMargins(0, 10, 0, 10)

        copy_paste_text = QLabel("Copy on select and paste on right-click")
        copy_paste_text.setStyleSheet(AppStyles.TEXT_STYLE)

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
        divider2.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider2)

        # Terminal Theme section
        theme_label = QLabel("TERMINAL THEME")
        theme_label.setObjectName("sectionHeader")
        theme_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(theme_label)

        theme_combo = QComboBox()
        theme_combo.addItems(["Dark"])
        theme_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(theme_combo)

        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        divider3.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider3)

        # Font Size section
        font_size_label = QLabel("FONT SIZE")
        font_size_label.setObjectName("sectionHeader")
        font_size_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(font_size_label)

        self.font_size_input = QLineEdit()
        self.font_size_input.setText(str(self.current_font_size))
        self.font_size_input.setStyleSheet(AppStyles.INPUT_STYLE)
        self.font_size_input.editingFinished.connect(self.on_font_size_changed)
        content_layout.addWidget(self.font_size_input)

        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        divider4.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider4)

        # Font Family section
        font_family_label = QLabel("FONT FAMILY")
        font_family_label.setObjectName("sectionHeader")
        font_family_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(font_family_label)

        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(["RobotoMono", "Consolas", "Courier New"])
        self.font_family_combo.setCurrentText(self.current_font_family)
        self.font_family_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
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
        section_header.setStyleSheet(AppStyles.SECTION_HEADER_STYLE)
        header_layout.addWidget(section_header)
        header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        placeholder = QLabel(f"{title} settings would go here")
        placeholder.setStyleSheet(AppStyles.PLACEHOLDER_STYLE)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(placeholder)

        content_layout.addStretch()

        self.content_scroll.setWidget(content_widget)

    def update_startup_status(self, checked):
        if checked:
            self.startup_status.setText("Enabled")
            self.startup_status.setStyleSheet(AppStyles.STATUS_TEXT_ENABLED_STYLE)
        else:
            self.startup_status.setText("Disabled")
            self.startup_status.setStyleSheet(AppStyles.STATUS_TEXT_STYLE)

    def on_line_numbers_changed(self, text):
        """Update line numbers setting"""
        show_line_numbers = text == "On"
        print(f"PreferencesWidget: Line numbers changed to {show_line_numbers}")
        self.show_line_numbers = show_line_numbers
        self.line_numbers_changed.emit(show_line_numbers)

    # New method to handle tab size changes
    def on_tab_size_changed(self):
        """Update tab size for YAML editor"""
        text = self.tab_size_input.text()
        try:
            tab_size = int(text)
            # Validate tab size within a reasonable range
            if 1 <= tab_size <= 8:
                # Only emit signal if the size has actually changed
                if tab_size != self.current_tab_size:
                    self.current_tab_size = tab_size
                    print(f"PreferencesWidget: Emitting tab_size_changed with size: {tab_size}")
                    self.tab_size_changed.emit(tab_size)
            else:
                print(f"PreferencesWidget: Tab size {tab_size} out of range (1-8)")
                self.tab_size_input.setText(str(self.current_tab_size))
        except ValueError:
            print(f"PreferencesWidget: Invalid tab size input: {text}")
            self.tab_size_input.setText(str(self.current_tab_size))

    def on_font_changed(self, font_family):
        """Update terminal font family"""
        if self.current_font_family != font_family:
            self.current_font_family = font_family
            print(f"PreferencesWidget: Font family changed to {font_family}")
            self.font_changed.emit(font_family)

    def on_editor_font_changed(self, font_family):
        """Update editor font family - applies to YAML editor too"""
        if self.current_font_family != font_family:
            self.current_font_family = font_family
            print(f"PreferencesWidget: Editor font family changed to {font_family}")
            # Emit signal to update all YAML editors
            self.font_changed.emit(font_family)
            
            # Sync terminal font family combo if it exists
            if hasattr(self, 'font_family_combo') and not self.font_family_combo.isNull():
                try:
                    self.font_family_combo.blockSignals(True)
                    self.font_family_combo.setCurrentText(font_family)
                    self.font_family_combo.blockSignals(False)
                except RuntimeError:
                    # Handle the case where the widget has been deleted
                    print("Warning: font_family_combo has been deleted")
                    
            # Additional logging to confirm signal emission
            print(f"PreferencesWidget: Emitted font_changed signal with font family: {font_family}")

    def on_font_size_changed(self):
        """Update terminal font size"""
        text = self.font_size_input.text()
        try:
            font_size = int(text)
            # Validate font size within a reasonable range
            if 6 <= font_size <= 72:
                # Only emit signal if the size has actually changed
                if font_size != self.last_emitted_size:
                    self.current_font_size = font_size
                    self.pending_font_size = font_size
                    self.last_emitted_size = font_size
                    print(f"PreferencesWidget: Emitting font_size_changed with size: {font_size}")
                    self.font_size_changed.emit(font_size)
                    self.apply_font_size_manually(font_size)
                    
                    # Sync editor font size input if it exists
                    if hasattr(self, 'editor_font_size_input'):
                        self.editor_font_size_input.blockSignals(True)
                        self.editor_font_size_input.setText(str(font_size))
                        self.editor_font_size_input.blockSignals(False)
            else:
                print(f"PreferencesWidget: Font size {font_size} out of range (6-72)")
                self.font_size_input.setText(str(self.current_font_size))
        except ValueError:
            print(f"PreferencesWidget: Invalid font size input: {text}")
            self.font_size_input.setText(str(self.current_font_size))

    def on_editor_font_size_changed(self):
        """Update editor font size - applies to YAML editor too"""
        text = self.editor_font_size_input.text() if hasattr(self, 'editor_font_size_input') else "9"
        try:
            font_size = int(text)
            # Validate font size within a reasonable range
            if 6 <= font_size <= 72:
                # Only emit signal if the size has actually changed
                if font_size != self.last_emitted_size:
                    self.current_font_size = font_size
                    self.pending_font_size = font_size
                    self.last_emitted_size = font_size
                    print(f"PreferencesWidget: Emitting font_size_changed with size: {font_size}")
                    self.font_size_changed.emit(font_size)
                    
                    # Sync terminal font size input if it exists
                    if hasattr(self, 'font_size_input'):
                        self.font_size_input.blockSignals(True)
                        self.font_size_input.setText(str(font_size))
                        self.font_size_input.blockSignals(False)
            else:
                print(f"PreferencesWidget: Font size {font_size} out of range (6-72)")
                if hasattr(self, 'editor_font_size_input'):
                    self.editor_font_size_input.setText(str(self.current_font_size))
        except ValueError:
            print(f"PreferencesWidget: Invalid font size input: {text}")
            if hasattr(self, 'editor_font_size_input'):
                self.editor_font_size_input.setText(str(self.current_font_size))

    def on_copy_paste_changed(self, checked):
        self.copy_paste_enabled = checked
        print(f"PreferencesWidget: Copy-paste toggle changed to {checked}")
        self.copy_paste_changed.emit(checked)
        try:
            if self.terminal_panel:
                print(f"PreferencesWidget: Applying copy-paste setting {checked} to terminal panel")
                self.terminal_panel.apply_copy_paste_to_terminals(checked)
            else:
                print("PreferencesWidget: Terminal panel not set, copy-paste setting will be applied when panel is set")
        except Exception as e:
            print(f"PreferencesWidget: Failed to apply copy-paste setting: {e}")

    def get_current_font_size(self):
        """Return the last valid font size set by the user."""
        return self.current_font_size

    def set_terminal_panel(self, terminal_panel):
        """Set the TerminalPanel instance for manual font size and copy-paste application."""
        self.terminal_panel = terminal_panel
        print(f"PreferencesWidget: Terminal panel set to {self.terminal_panel}")
        try:
            # Apply any pending font size changes
            if self.pending_font_size is not None:
                print(f"PreferencesWidget: Applying pending font size {self.pending_font_size}")
                self.apply_font_size_manually(self.pending_font_size)
            # Apply current copy-paste setting
            print(f"PreferencesWidget: Applying copy-paste setting {self.copy_paste_enabled}")
            self.terminal_panel.apply_copy_paste_to_terminals(self.copy_paste_enabled)
        except Exception as e:
            print(f"PreferencesWidget: Error applying settings to terminal panel: {e}")

    def find_terminal_widgets(self, widget):
        """Recursively search for QTextEdit widgets that might be used as terminals."""
        terminal_widgets = []
        if isinstance(widget, QTextEdit):
            print(f"PreferencesWidget: Found QTextEdit widget: {widget}")
            terminal_widgets.append(widget)
        for child in widget.findChildren(QWidget):
            terminal_widgets.extend(self.find_terminal_widgets(child))
        return terminal_widgets

    def apply_font_size_manually(self, font_size):
        """Manually apply the font size to the terminal panel if set, or search for terminal widgets."""
        try:
            if self.terminal_panel:
                print(f"PreferencesWidget: Manually applying font size {font_size} to terminal panel")
                self.terminal_panel.apply_font_size_to_terminals(font_size)
            else:
                print("PreferencesWidget: Terminal panel not set, searching for terminal widgets")
                # Start searching from the top-level parent widget
                parent = self
                while parent.parent():
                    parent = parent.parent()
                terminal_widgets = self.find_terminal_widgets(parent)
                if terminal_widgets:
                    print(f"PreferencesWidget: Found {len(terminal_widgets)} potential terminal widget(s)")
                    for i, widget in enumerate(terminal_widgets):
                        print(f"PreferencesWidget: Applying font size {font_size} to terminal widget {i}")
                        font = QFont(self.current_font_family, font_size)
                        widget.setFont(font)
                        print(f"PreferencesWidget: Updated font to {self.current_font_family}, size {font_size} for widget {i}")
                        widget.update()  # Force a repaint
                    self.pending_font_size = None  # Clear pending font size since we've applied it
                else:
                    print("PreferencesWidget: No terminal widgets found, font size change is pending")
                    print("PreferencesWidget: Font size change is pending until terminal panel is set or terminal widgets are found")
        except Exception as e:
            print(f"PreferencesWidget: Error applying font size: {e}")