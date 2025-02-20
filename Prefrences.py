import sys
import platform
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QComboBox,
                           QFrame, QLineEdit, QCheckBox, QScrollArea)
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QPainter
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 24)
        self.toggled.connect(self.on_state_changed)
        self.setCursor(Qt.PointingHandCursor)
        self._circle_position = 10
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set colors based on state
        if self.isChecked():
            bg_color = QColor("#4A9EFF")
            circle_pos = 30
        else:
            bg_color = QColor("#555555")
            circle_pos = 10
            
        # Draw background
        painter.setPen(Qt.NoPen)
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
        self.setCursor(Qt.PointingHandCursor)

class PreferencesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Preferences')
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("""
            QMainWindow, QWidget {
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
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
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
        self.content_scroll.setFrameShape(QFrame.NoFrame)
        
        # Add widgets to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_scroll)
        
        # Set central widget
        self.setCentralWidget(main_widget)
        
        # Store section references for navigation
        self.current_section = "app"
        
        # Initialize with App section
        self.show_section("app")
        
    def create_close_button(self):
        # Close button in container
        close_container = QWidget()
        close_container.setFixedSize(40, 60)
        close_layout = QVBoxLayout(close_container)
        close_layout.setContentsMargins(0, 0, 0, 0)
        close_layout.setSpacing(4)
        close_layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8e9ba9;
                font-size: 24px;
                font-weight: bold;
                border: 1px solid #3a3e42;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #3a3e42;
                color: #ffffff;
            }
        """)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        
        esc_label = QLabel("ESC")
        esc_label.setAlignment(Qt.AlignCenter)
        esc_label.setStyleSheet("color: #8e9ba9; font-size: 10px;")
        
        close_layout.addWidget(close_btn, 0, Qt.AlignCenter)
        close_layout.addWidget(esc_label, 0, Qt.AlignCenter)
        
        return close_container
    
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
        
        # Header container with application title and close button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        # Application header
        app_header = QLabel("Application")
        app_header.setObjectName("header")
        header_layout.addWidget(app_header)
        
        # Add close button to header with alignment
        header_layout.addWidget(self.create_close_button(), 0, Qt.AlignRight | Qt.AlignTop)
        
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
        theme_combo.setCursor(Qt.PointingHandCursor)
        content_layout.addWidget(theme_combo)
        
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider1)
        
        # 2. Extension registry section
        registry_label = QLabel("EXTENSION INSTALL REGISTRY")
        registry_label.setObjectName("sectionHeader")
        content_layout.addWidget(registry_label)
        
        registry_combo = QComboBox()
        registry_combo.addItem("Default Url")
        registry_combo.addItem("Custom Url")
        registry_combo.setCursor(Qt.PointingHandCursor)
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
        divider2.setFrameShape(QFrame.HLine)
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
        divider3.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider3)
        
        # 4. Update channel section
        update_label = QLabel("UPDATE CHANNEL")
        update_label.setObjectName("sectionHeader")
        content_layout.addWidget(update_label)
        
        update_combo = QComboBox()
        update_combo.addItem("Stable")
        update_combo.addItem("Beta")
        update_combo.addItem("Alpha")
        update_combo.setCursor(Qt.PointingHandCursor)
        content_layout.addWidget(update_combo)
        
        # 5. Local Timezone section
        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.HLine)
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
        self.timezone_combo.setCursor(Qt.PointingHandCursor)
        self.timezone_combo.currentIndexChanged.connect(self.change_timezone)
        content_layout.addWidget(self.timezone_combo)
        
        content_layout.addStretch()
        
        # Set the content widget
        self.content_scroll.setWidget(content_widget)
    
    def show_proxy_section(self):
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)
        
        # Header container with proxy title and close button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        # Proxy header
        proxy_header = QLabel("Proxy")
        proxy_header.setObjectName("header")
        header_layout.addWidget(proxy_header)
        
        # Add close button to header with alignment
        header_layout.addWidget(self.create_close_button(), 0, Qt.AlignRight | Qt.AlignTop)
        
        # Add the header to main content
        content_layout.addWidget(header_container)
        
        # HTTP PROXY section
        http_proxy_label = QLabel("HTTP PROXY")
        http_proxy_label.setObjectName("sectionHeader")
        content_layout.addWidget(http_proxy_label)
        
        # Proxy URL input
        proxy_input = QLineEdit()
        proxy_input.setPlaceholderText("Type HTTP proxy url (example: http://proxy.acme.org:8080)")
        content_layout.addWidget(proxy_input)
        
        # Description
        proxy_desc = QLabel("Proxy is used only for non-cluster communication.")
        proxy_desc.setStyleSheet("color: #8e9ba9; font-size: 13px; padding: 10px 0px;")
        content_layout.addWidget(proxy_desc)
        
        # Divider
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider)
        
        # CERTIFICATE TRUST section
        cert_label = QLabel("CERTIFICATE TRUST")
        cert_label.setObjectName("sectionHeader")
        content_layout.addWidget(cert_label)
        
        # Certificate toggle
        cert_container = QWidget()
        cert_layout = QHBoxLayout(cert_container)
        cert_layout.setContentsMargins(0, 10, 0, 10)
        
        cert_text = QLabel("Allow untrusted Certificate Authorities")
        cert_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        cert_toggle = ToggleSwitch()
        cert_toggle.setChecked(False)
        
        cert_layout.addWidget(cert_text)
        cert_layout.addStretch()
        cert_layout.addWidget(cert_toggle)
        
        content_layout.addWidget(cert_container)
        
        # Certificate description
        cert_desc = QLabel("This will make Lens to trust ANY certificate authority without any validations. Needed with some corporate proxies that do certificate re-writing. Does not affect cluster communications!")
        cert_desc.setStyleSheet("color: #8e9ba9; font-size: 13px; padding: 10px 0px;")
        cert_desc.setWordWrap(True)
        content_layout.addWidget(cert_desc)
        
        content_layout.addStretch()
        
        # Set the content widget
        self.content_scroll.setWidget(content_widget)
    
    def show_kubernetes_section(self):
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)
        
        # Header container with Kubernetes title and close button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        # Kubernetes header
        kubernetes_header = QLabel("Kubernetes")
        kubernetes_header.setObjectName("header")
        header_layout.addWidget(kubernetes_header)
        
        # Add close button to header with alignment
        header_layout.addWidget(self.create_close_button(), 0, Qt.AlignRight | Qt.AlignTop)
        
        # Add the header to main content
        content_layout.addWidget(header_container)
        
        # KUBECTL BINARY DOWNLOAD section
        kubectl_label = QLabel("KUBECTL BINARY DOWNLOAD")
        kubectl_label.setObjectName("sectionHeader")
        content_layout.addWidget(kubectl_label)
        
        # Toggle switch for kubectl binary download
        kubectl_download_container = QWidget()
        kubectl_download_layout = QHBoxLayout(kubectl_download_container)
        kubectl_download_layout.setContentsMargins(0, 10, 0, 10)
        
        kubectl_download_text = QLabel("Download kubectl binaries matching the Kubernetes cluster version")
        kubectl_download_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        kubectl_download_toggle = ToggleSwitch()
        kubectl_download_toggle.setChecked(True)
        
        kubectl_download_layout.addWidget(kubectl_download_text)
        kubectl_download_layout.addStretch()
        kubectl_download_layout.addWidget(kubectl_download_toggle)
        
        content_layout.addWidget(kubectl_download_container)
        
        # Divider
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider1)
        
        # DOWNLOAD MIRROR section
        download_mirror_label = QLabel("DOWNLOAD MIRROR")
        download_mirror_label.setObjectName("sectionHeader")
        content_layout.addWidget(download_mirror_label)
        
        # Download mirror dropdown
        download_mirror_combo = QComboBox()
        download_mirror_combo.addItem("Default (Google)")
        download_mirror_combo.addItem("Alternative Mirror 1")
        download_mirror_combo.addItem("Alternative Mirror 2")
        download_mirror_combo.setCursor(Qt.PointingHandCursor)
        content_layout.addWidget(download_mirror_combo)
        
        # Divider
        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider2)
        
        # DIRECTORY FOR BINARIES section
        binaries_dir_label = QLabel("DIRECTORY FOR BINARIES")
        binaries_dir_label.setObjectName("sectionHeader")
        content_layout.addWidget(binaries_dir_label)
        
        # Binaries directory input
        binaries_dir_input = QLineEdit()
        binaries_dir_input.setText(r"C:\Users\Admin\AppData\Roaming\OpenLens\binaries")
        binaries_dir_input.setPlaceholderText("Directory to download binaries into")
        content_layout.addWidget(binaries_dir_input)
        
        binaries_dir_desc = QLabel("The directory to download binaries into.")
        binaries_dir_desc.setStyleSheet("color: #8e9ba9; font-size: 13px; padding: 10px 0px;")
        content_layout.addWidget(binaries_dir_desc)
        
        # Divider
        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider3)
        
        # PATH TO KUBECTL BINARY section
        kubectl_path_label = QLabel("PATH TO KUBECTL BINARY")
        kubectl_path_label.setObjectName("sectionHeader")
        content_layout.addWidget(kubectl_path_label)
        
        # Kubectl binary path input
        kubectl_path_input = QLineEdit()
        kubectl_path_input.setText(r"C:\Users\Admin\AppData\Roaming\OpenLens\binaries\kubectl")
        kubectl_path_input.setPlaceholderText("Path to kubectl binary")
        content_layout.addWidget(kubectl_path_input)
        
        # Divider
        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider4)
        
        # KUBECONFIG SYNCS section
        kubeconfig_label = QLabel("KUBECONFIG SYNCS")
        kubeconfig_label.setObjectName("sectionHeader")
        content_layout.addWidget(kubeconfig_label)
        
        # Kubeconfig sync buttons
        kubeconfig_sync_container = QWidget()
        kubeconfig_sync_layout = QHBoxLayout(kubeconfig_sync_container)
        kubeconfig_sync_layout.setContentsMargins(0, 10, 0, 10)
        
        sync_file_btn = QPushButton("Sync file(s)")
        sync_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A9EFF;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3A8EDF;
            }
        """)
        sync_folder_btn = QPushButton("Sync folder(s)")
        sync_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #252a2e;
                color: #8e9ba9;
                border: 1px solid #4A9EFF;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2D2D2D;
            }
        """)
        
        kubeconfig_sync_layout.addWidget(sync_file_btn)
        kubeconfig_sync_layout.addSpacing(10)
        kubeconfig_sync_layout.addWidget(sync_folder_btn)
        kubeconfig_sync_layout.addStretch()
        
        content_layout.addWidget(kubeconfig_sync_container)
        
        # SYNCED ITEMS section
        synced_items_label = QLabel("SYNCED ITEMS")
        synced_items_label.setObjectName("sectionHeader")
        content_layout.addWidget(synced_items_label)
        
        # Synced items container
        synced_items_container = QWidget()
        synced_items_layout = QHBoxLayout(synced_items_container)
        synced_items_layout.setContentsMargins(0, 10, 0, 10)
        
        synced_item = QLabel(r"C:\Users\Admin\.kube")
        synced_item.setStyleSheet("color: #ffffff; font-size: 14px; background-color: #252a2e; padding: 8px; border-radius: 4px;")
        
        delete_btn = QPushButton("🗑")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8e9ba9;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #ff0000;
            }
        """)
        
        synced_items_layout.addWidget(synced_item)
        synced_items_layout.addStretch()
        synced_items_layout.addWidget(delete_btn)
        
        content_layout.addWidget(synced_items_container)
        
        # Divider
        divider5 = QFrame()
        divider5.setObjectName("divider")
        divider5.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider5)
        
        # HELM CHARTS section
        helm_charts_label = QLabel("HELM CHARTS")
        helm_charts_label.setObjectName("sectionHeader")
        content_layout.addWidget(helm_charts_label)
        
        # Helm Charts repositories container
        helm_repos_container = QWidget()
        helm_repos_layout = QHBoxLayout(helm_repos_container)
        helm_repos_layout.setContentsMargins(0, 10, 0, 10)
        
        # Repositories dropdown
        helm_repos_combo = QComboBox()
        helm_repos_combo.addItem("Repositories")
        helm_repos_combo.setStyleSheet("""
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
        """)
        
        # Add Custom Helm Repo button
        add_repo_btn = QPushButton("Add Custom Helm Repo")
        add_repo_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A9EFF;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3A8EDF;
            }
        """)
        
        helm_repos_layout.addWidget(helm_repos_combo)
        helm_repos_layout.addSpacing(10)
        helm_repos_layout.addWidget(add_repo_btn)
        helm_repos_layout.addStretch()
        
        content_layout.addWidget(helm_repos_container)
        
        # Helm repositories list
        helm_repo_item_container = QWidget()
        helm_repo_item_layout = QHBoxLayout(helm_repo_item_container)
        helm_repo_item_layout.setContentsMargins(0, 10, 0, 10)
        
        helm_repo_item = QLabel("bitnami")
        helm_repo_url = QLabel("https://charts.bitnami.com/bitnami")
        helm_repo_item.setStyleSheet("color: #ffffff; font-size: 14px;")
        helm_repo_url.setStyleSheet("color: #8e9ba9; font-size: 12px;")
        
        delete_repo_btn = QPushButton("🗑")
        delete_repo_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8e9ba9;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #ff0000;
            }
        """)
        
        repo_details_layout = QVBoxLayout()
        repo_details_layout.addWidget(helm_repo_item)
        repo_details_layout.addWidget(helm_repo_url)
        
        helm_repo_item_layout.addLayout(repo_details_layout)
        helm_repo_item_layout.addStretch()
        helm_repo_item_layout.addWidget(delete_repo_btn)
        
        content_layout.addWidget(helm_repo_item_container)
        
        content_layout.addStretch()
        
        # Set the content widget
        self.content_scroll.setWidget(content_widget)

    def show_editor_section(self):
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)
        
        # Header container with Editor title and close button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        # Editor header
        editor_header = QLabel("Editor")
        editor_header.setObjectName("header")
        header_layout.addWidget(editor_header)
        
        # Add close button to header with alignment
        header_layout.addWidget(self.create_close_button(), 0, Qt.AlignRight | Qt.AlignTop)
        
        # Add the header to main content
        content_layout.addWidget(header_container)
        
        # MINIMAP section
        minimap_label = QLabel("MINIMAP")
        minimap_label.setObjectName("sectionHeader")
        content_layout.addWidget(minimap_label)
        
        # Minimap toggle and position container
        minimap_container = QWidget()
        minimap_layout = QHBoxLayout(minimap_container)
        minimap_layout.setContentsMargins(0, 10, 0, 10)
        
        # Minimap toggle
        minimap_text = QLabel("Show minimap")
        minimap_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        minimap_toggle = ToggleSwitch()
        minimap_toggle.setChecked(True)
        
        # Minimap position dropdown
        minimap_position = QComboBox()
        minimap_position.addItem("right")
        minimap_position.addItem("left")
        minimap_position.setCursor(Qt.PointingHandCursor)
        
        minimap_layout.addWidget(minimap_text)
        minimap_layout.addStretch()
        minimap_layout.addWidget(minimap_position)
        minimap_layout.addWidget(minimap_toggle)
        
        content_layout.addWidget(minimap_container)
        
        # Divider
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider1)
        
        # LINE NUMBERS section
        line_numbers_label = QLabel("LINE NUMBERS")
        line_numbers_label.setObjectName("sectionHeader")
        content_layout.addWidget(line_numbers_label)
        
        # Line numbers dropdown
        line_numbers_combo = QComboBox()
        line_numbers_combo.addItem("On")
        line_numbers_combo.addItem("Off")
        line_numbers_combo.setCursor(Qt.PointingHandCursor)
        content_layout.addWidget(line_numbers_combo)
        
        # Divider
        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider2)
        
        # TAB SIZE section
        tab_size_label = QLabel("TAB SIZE")
        tab_size_label.setObjectName("sectionHeader")
        content_layout.addWidget(tab_size_label)
        
        # Tab size input
        tab_size_input = QLineEdit()
        tab_size_input.setText("2")
        content_layout.addWidget(tab_size_input)
        
        # Divider
        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider3)
        
        # FONT SIZE section
        font_size_label = QLabel("FONT SIZE")
        font_size_label.setObjectName("sectionHeader")
        content_layout.addWidget(font_size_label)
        
        # Font size input
        font_size_input = QLineEdit()
        font_size_input.setText("12")
        content_layout.addWidget(font_size_input)
        
        # Divider
        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider4)
        
        # FONT FAMILY section
        font_family_label = QLabel("FONT FAMILY")
        font_family_label.setObjectName("sectionHeader")
        content_layout.addWidget(font_family_label)
        
        # Font family input
        font_family_input = QLineEdit()
        font_family_input.setText("RobotoMono")
        content_layout.addWidget(font_family_input)
        
        content_layout.addStretch()
        
        # Set the content widget
        self.content_scroll.setWidget(content_widget)

    def show_terminal_section(self):
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)
        
        # Header container with Terminal title and close button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        # Terminal header
        terminal_header = QLabel("Terminal")
        terminal_header.setObjectName("header")
        header_layout.addWidget(terminal_header)
        
        # Add close button to header with alignment
        header_layout.addWidget(self.create_close_button(), 0, Qt.AlignRight | Qt.AlignTop)
        
        # Add the header to main content
        content_layout.addWidget(header_container)
        
        # TERMINAL SHELL PATH section
        shell_path_label = QLabel("TERMINAL SHELL PATH")
        shell_path_label.setObjectName("sectionHeader")
        content_layout.addWidget(shell_path_label)
        
        # Shell path input
        shell_path_input = QLineEdit()
        shell_path_input.setText("powershell.exe")
        content_layout.addWidget(shell_path_input)
        
        # Divider
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider1)
        
        # TERMINAL COPY & PASTE section
        copy_paste_label = QLabel("TERMINAL COPY & PASTE")
        copy_paste_label.setObjectName("sectionHeader")
        content_layout.addWidget(copy_paste_label)
        
        # Copy & Paste container
        copy_paste_container = QWidget()
        copy_paste_layout = QHBoxLayout(copy_paste_container)
        copy_paste_layout.setContentsMargins(0, 10, 0, 10)
        
        # Copy & Paste text
        copy_paste_text = QLabel("Copy on select and paste on right-click")
        copy_paste_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        # Copy & Paste toggle
        copy_paste_toggle = ToggleSwitch()
        copy_paste_toggle.setChecked(False)
        
        copy_paste_layout.addWidget(copy_paste_text)
        copy_paste_layout.addStretch()
        copy_paste_layout.addWidget(copy_paste_toggle)
        
        content_layout.addWidget(copy_paste_container)
        
        # Divider
        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider2)
        
        # TERMINAL THEME section
        theme_label = QLabel("TERMINAL THEME")
        theme_label.setObjectName("sectionHeader")
        content_layout.addWidget(theme_label)
        
        # Theme dropdown
        theme_combo = QComboBox()
        theme_combo.addItem("Light")
        theme_combo.addItem("Dark")
        theme_combo.addItem("System")
        theme_combo.setCursor(Qt.PointingHandCursor)
        content_layout.addWidget(theme_combo)
        
        # Divider
        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider3)
        
        # FONT SIZE section
        font_size_label = QLabel("FONT SIZE")
        font_size_label.setObjectName("sectionHeader")
        content_layout.addWidget(font_size_label)
        
        # Font size input
        font_size_input = QLineEdit()
        font_size_input.setText("12")
        content_layout.addWidget(font_size_input)
        
        # Divider
        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.HLine)
        content_layout.addWidget(divider4)
        
        # FONT FAMILY section
        font_family_label = QLabel("FONT FAMILY")
        font_family_label.setObjectName("sectionHeader")
        content_layout.addWidget(font_family_label)
        
        # Font family dropdown
        font_family_combo = QComboBox()
        font_family_combo.addItem("RobotoMono")
        font_family_combo.addItem("Consolas")
        font_family_combo.addItem("Courier New")
        font_family_combo.setCursor(Qt.PointingHandCursor)
        content_layout.addWidget(font_family_combo)
        
        content_layout.addStretch()
        
        # Set the content widget
        self.content_scroll.setWidget(content_widget)
    
    def show_placeholder_section(self, title):
        # Create content widget for placeholder sections
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(5)
        
        # Header container with title and close button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        # Section header
        section_header = QLabel(title)
        section_header.setObjectName("header")
        header_layout.addWidget(section_header)
        
        # Add close button to header with alignment
        header_layout.addWidget(self.create_close_button(), 0, Qt.AlignRight | Qt.AlignTop)
        
        # Add the header to main content
        content_layout.addWidget(header_container)

    
        
        # Placeholder content
        placeholder = QLabel(f"{title} settings would go here")
        placeholder.setStyleSheet("color: #8e9ba9; font-size: 14px; padding: 40px 0px;")
        placeholder.setAlignment(Qt.AlignCenter)
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

def main():
    app = QApplication(sys.argv)
    window = PreferencesWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()