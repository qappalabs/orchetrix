import sys
import platform
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QComboBox,
                           QFrame, QLineEdit, QCheckBox, QScrollArea)
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QPainter
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtSignal

from UI.Styles import AppColors, AppStyles

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
            bg_color = QColor("#555555")
            circle_pos = 10
            
        # Draw background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
        # Draw circle
        painter.setBrush(QColor("#ffffff"))
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
                # Windows registry implementation would go here
                print("Added to Windows startup")
            except Exception as e:
                print(f"Failed to add to Windows startup: {e}")
                
        elif system == 'Darwin':  # macOS
            try:
                # macOS launchd implementation would go here
                print("Added to macOS startup")
            except Exception as e:
                print(f"Failed to add to macOS startup: {e}")
                
        elif system == 'Linux':
            try:
                # Linux autostart implementation would go here
                print("Added to Linux startup")
            except Exception as e:
                print(f"Failed to add to Linux startup: {e}")
        
        print("Start-up enabled")
        
    def disable_startup(self):
        system = platform.system()
        
        if system == 'Windows':
            try:
                import winreg
                # Windows registry removal would go here
                print("Removed from Windows startup")
            except Exception as e:
                print(f"Failed to remove from Windows startup: {e}")
                
        elif system == 'Darwin':  # macOS
            try:
                # macOS launchd removal would go here
                print("Removed from macOS startup")
            except Exception as e:
                print(f"Failed to remove from macOS startup: {e}")
                
        elif system == 'Linux':
            try:
                # Linux autostart removal would go here
                print("Removed from Linux startup")
            except Exception as e:
                print(f"Failed to remove from Linux startup: {e}")
                
        print("Start-up disabled")

    def hitButton(self, pos):
        # Make the entire widget clickable
        return self.contentsRect().contains(pos)

class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8e9ba9;
                text-align: left;
                padding: 10px 20px;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2D2D2D;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #1e2428;
                color: #ffffff;
                border-left: 3px solid #4A9EFF;
                padding-left: 17px;
            }
        """)
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class PreferencesWidget(QWidget):
    # Signal to go back to previous view
    back_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # Set consistent appearance
        self.setStyleSheet("""
            QWidget {
                background-color: #1e2428;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #8e9ba9;
            }
            QLabel#header {
                color: #ffffff;
                font-size: 22px;
                font-weight: bold;
                padding-bottom: 10px;
            }
            QLabel#sectionHeader {
                color: #8e9ba9;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
                padding-top: 20px;
                padding-bottom: 10px;
            }
            QComboBox {
                background-color: #252a2e;
                border: 1px solid #333639;
                border-radius: 4px;
                padding: 8px 12px;
                color: #ffffff;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QLineEdit {
                background-color: #252a2e;
                border: 1px solid #333639;
                border-radius: 4px;
                padding: 8px 12px;
                color: #ffffff;
            }
            QFrame#divider {
                background-color: #333639;
                max-height: 1px;
                margin: 20px 0px;
            }
        """)
        
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #1a1d20;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Preferences header
        preferences_label = QLabel("PREFERENCES")
        preferences_label.setStyleSheet("""
            padding: 20px;
            color: #8e9ba9;
            font-size: 12px;
            font-weight: bold;
        """)
        sidebar_layout.addWidget(preferences_label)
        
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
        
        # Add widgets to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_scroll)
        
        # Store section references for navigation
        self.current_section = "app"
        
        # Initialize with App section
        self.show_section("app")
    
    def create_back_button(self):
        # Back button in container
        back_container = QWidget()
        back_container.setFixedSize(40, 60)
        back_layout = QVBoxLayout(back_container)
        back_layout.setContentsMargins(0, 0, 0, 0)
        back_layout.setSpacing(4)
        back_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        
        back_btn = QPushButton("←")
        back_btn.setFixedSize(30, 30)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8e9ba9;
                font-size: 20px;
                font-weight: bold;
                border: 1px solid #3a3e42;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #3a3e42;
                color: #ffffff;
            }
        """)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.go_back)
        
        back_label = QLabel("Back")
        back_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        back_label.setStyleSheet("color: #8e9ba9; font-size: 10px;")
        
        back_layout.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignCenter)
        back_layout.addWidget(back_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        return back_container
    
    def go_back(self):
        """Emit signal to go back to previous view"""
        self.back_signal.emit()
    
    def show_section(self, section):
        # Uncheck all buttons first
        self.app_btn.setChecked(False)
        self.proxy_btn.setChecked(False)
        self.kubernetes_btn.setChecked(False)
        self.editor_btn.setChecked(False)
        self.terminal_btn.setChecked(False)
        
        # Set the current section and check appropriate button
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
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)
        
        # Header container with application title and back button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        # Application header
        app_header = QLabel("Application")
        app_header.setObjectName("header")
        header_layout.addWidget(app_header)
        
        # Add back button to header with alignment
        header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        # Add the header to main content
        content_layout.addWidget(header_container)
        
        # Content sections
        # 1. Theme section
        theme_label = QLabel("THEME")
        theme_label.setObjectName("sectionHeader")
        content_layout.addWidget(theme_label)
        
        theme_combo = QComboBox()
        theme_combo.addItem("Select...")
        theme_combo.addItem("Dark")
        theme_combo.addItem("Light")
        theme_combo.addItem("System")
        theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(theme_combo)
        
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider1)
        
        # 2. Extension registry section
        registry_label = QLabel("EXTENSION INSTALL REGISTRY")
        registry_label.setObjectName("sectionHeader")
        content_layout.addWidget(registry_label)
        
        registry_combo = QComboBox()
        registry_combo.addItem("Default Url")
        registry_combo.addItem("Custom Url")
        registry_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(registry_combo)
        
        registry_help = QLabel("This setting is to change the registry URL for installing extensions by name. If you are unable to access the\ndefault registry (https://registry.npmjs.org) you can change it in your .npmrc file or in the input below.")
        registry_help.setStyleSheet("color: #8e9ba9; font-size: 13px; padding: 10px 0px;")
        registry_help.setWordWrap(True)
        content_layout.addWidget(registry_help)
        
        registry_input = QLineEdit()
        registry_input.setPlaceholderText("Custom Extension Registry URL...")
        content_layout.addWidget(registry_input)
        
        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider2)
        
        # 3. Start-up section
        startup_label = QLabel("START-UP")
        startup_label.setObjectName("sectionHeader")
        content_layout.addWidget(startup_label)
        
        startup_container = QWidget()
        startup_layout = QHBoxLayout(startup_container)
        startup_layout.setContentsMargins(0, 10, 0, 10)
        
        startup_text = QLabel("Automatically start Orchestrix on login")
        startup_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        # Status indicator
        self.startup_status = QLabel("Disabled")
        self.startup_status.setStyleSheet("color: #8e9ba9; font-size: 12px; margin-right: 10px;")
        
        toggle_switch = ToggleSwitch()
        toggle_switch.setChecked(False)  # Make sure it's off by default
        toggle_switch.toggled.connect(self.update_startup_status)
        
        startup_layout.addWidget(startup_text)
        startup_layout.addStretch()
        startup_layout.addWidget(self.startup_status)
        startup_layout.addWidget(toggle_switch)
        
        content_layout.addWidget(startup_container)
        
        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider3)
        
        # 4. Update channel section
        update_label = QLabel("UPDATE CHANNEL")
        update_label.setObjectName("sectionHeader")
        content_layout.addWidget(update_label)
        
        update_combo = QComboBox()
        update_combo.addItem("Stable")
        update_combo.addItem("Beta")
        update_combo.addItem("Alpha")
        update_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(update_combo)
        
        # 5. Local Timezone section
        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider4)
        
        timezone_label = QLabel("LOCAL TIMEZONE")
        timezone_label.setObjectName("sectionHeader")
        content_layout.addWidget(timezone_label)
        
        self.timezone_combo = QComboBox()
        self.timezone_combo.addItem("Asia/Calcutta")
        self.timezone_combo.addItem("America/New_York")
        self.timezone_combo.addItem("Europe/London")
        self.timezone_combo.addItem("Europe/Berlin")
        self.timezone_combo.addItem("Asia/Tokyo")
        self.timezone_combo.addItem("Asia/Singapore")
        self.timezone_combo.addItem("Australia/Sydney")
        self.timezone_combo.addItem("Pacific/Auckland")
        self.timezone_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.timezone_combo.currentIndexChanged.connect(self.change_timezone)
        content_layout.addWidget(self.timezone_combo)
        
        content_layout.addStretch()
        
        # Set the content widget
        self.content_scroll.setWidget(content_widget)
    
    def show_proxy_section(self):
        # Create placeholder section
        self.show_placeholder_section("Proxy")
    
    def show_kubernetes_section(self):
        # Create placeholder section
        self.show_placeholder_section("Kubernetes")
    
    def show_editor_section(self):
        # Create placeholder section
        self.show_placeholder_section("Editor")
    
    def show_terminal_section(self):
        # Create placeholder section
        self.show_placeholder_section("Terminal")
    
    def show_placeholder_section(self, title):
        # Create content widget for placeholder sections
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)
        
        # Header container with title and back button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        # Section header
        section_header = QLabel(title)
        section_header.setObjectName("header")
        header_layout.addWidget(section_header)
        
        # Add back button to header with alignment
        header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        # Add the header to main content
        content_layout.addWidget(header_container)
    
        # Placeholder content
        placeholder = QLabel(f"{title} settings would go here")
        placeholder.setStyleSheet("color: #8e9ba9; font-size: 14px; padding: 40px 0px;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(placeholder)
        
        content_layout.addStretch()
        
        # Set the content widget
        self.content_scroll.setWidget(content_widget)
        
    def update_startup_status(self, checked):
        if checked:
            self.startup_status.setText("Enabled")
            self.startup_status.setStyleSheet("color: #4A9EFF; font-size: 12px; margin-right: 10px;")
        else:
            self.startup_status.setText("Disabled")
            self.startup_status.setStyleSheet("color: #8e9ba9; font-size: 12px; margin-right: 10px;")
    
    def change_timezone(self, index):
        timezone = self.timezone_combo.currentText()
        # Actual implementation would set system or application timezone
        print(f"Timezone changed to: {timezone}")