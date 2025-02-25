import sys
import platform
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

class SearchBar(QLineEdit):
    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table
        self.setPlaceholderText("Search...")
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 8px 32px;
                color: white;
                min-width: 200px;
            }
            QLineEdit:focus {
                background-color: #3D3D3D;
            }
        """)
        
        search_icon = QLabel(self)
        search_icon.setPixmap(QIcon.fromTheme("edit-find").pixmap(16, 16))
        search_icon.setStyleSheet("background: transparent;")
        search_icon.setGeometry(8, 8, 16, 16)
        search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.textChanged.connect(self.on_search)

    def on_search(self, text):
        search_text = text.lower()
        for row in range(self.table.rowCount()):
            row_visible = False
            name_widget = self.table.cellWidget(row, 0)
            if name_widget:
                label = name_widget.findChild(QLabel, "name_label")
                if label and search_text in label.text().lower():
                    row_visible = True
            if not row_visible:
                for col in range(1, self.table.columnCount() - 1):
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        row_visible = True
                        break
            self.table.setRowHidden(row, not row_visible)

class NameCell(QWidget):
    def __init__(self, icon_text, name, color=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)
        
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("transparent"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("transparent"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("transparent"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
        self.setPalette(palette)
        
        if color:
            icon = QLabel()
            icon.setFixedSize(28, 16)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setText(icon_text)
            icon.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    color: black;
                    border-radius: 2px;
                    font-size: 10px;
                    font-weight: bold;
                }}
                QLabel:selected, QLabel:focus {{
                    background-color: {color};
                    color: black;
                    background: transparent;
                }}
            """)
        else:
            icon = QLabel(icon_text)
            icon.setFixedWidth(20)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet("""
                QLabel {
                    color: white;
                    background: transparent;
                }
                QLabel:selected, QLabel:focus {
                    background: transparent;
                    color: white;
                }
            """)
        
        name_label = QLabel(name)
        name_label.setObjectName("name_label")
        name_label.setAutoFillBackground(False)
        name_label.setStyleSheet("""
            QLabel#name_label {
                color: white;
                background: transparent;
            }
            QLabel#name_label:selected, QLabel#name_label:focus {
                background: transparent;
                color: white;
            }
        """)
        
        layout.addWidget(icon)
        layout.addWidget(name_label)
        layout.addStretch()

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)

    def selectionChanged(self, selected, deselected):
        pass

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 24)
        self.toggled.connect(self.on_state_changed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.isChecked():
            bg_color = QColor("#4A9EFF")
            circle_pos = 30
        else:
            bg_color = QColor("#555555")
            circle_pos = 10
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
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
                print("Added to Windows startup")
            except Exception as e:
                print(f"Failed to add to Windows startup: {e}")
        elif system == 'Darwin':
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
        elif system == 'Darwin':
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
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.initUI()
        
    def initUI(self):
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
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #1a1d20;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        preferences_label = QLabel("PREFERENCES")
        preferences_label.setStyleSheet("""
            padding: 20px;
            color: #8e9ba9;
            font-size: 12px;
            font-weight: bold;
        """)
        sidebar_layout.addWidget(preferences_label)
        
        self.app_btn = SidebarButton("App")
        self.proxy_btn = SidebarButton("Proxy")
        self.kubernetes_btn = SidebarButton("Kubernetes")
        self.editor_btn = SidebarButton("Editor")
        self.terminal_btn = SidebarButton("Terminal")
        
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
        
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_scroll)
        
        self.current_section = "app"
        self.show_section("app")
        
    def create_close_button(self):
        close_container = QWidget()
        close_container.setFixedSize(40, 60)
        close_layout = QVBoxLayout(close_container)
        close_layout.setContentsMargins(0, 0, 0, 0)
        close_layout.setSpacing(4)
        close_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        
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
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.main_window.show_browser)
        
        esc_label = QLabel("ESC")
        esc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        esc_label.setStyleSheet("color: #8e9ba9; font-size: 10px;")
        
        close_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        close_layout.addWidget(esc_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        return close_container
    
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
        
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        app_header = QLabel("Application")
        app_header.setObjectName("header")
        header_layout.addWidget(app_header)
        
        header_layout.addWidget(self.create_close_button(), alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        content_layout.addWidget(header_container)
        
        theme_label = QLabel("THEME")
        theme_label.setObjectName("sectionHeader")
        content_layout.addWidget(theme_label)
        
        theme_combo = QComboBox()
        theme_combo.addItems(["Select...", "Dark", "Light", "System"])
        theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(theme_combo)
        
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider1)
        
        registry_label = QLabel("EXTENSION INSTALL REGISTRY")
        registry_label.setObjectName("sectionHeader")
        content_layout.addWidget(registry_label)
        
        registry_combo = QComboBox()
        registry_combo.addItems(["Default Url", "Custom Url"])
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
        
        startup_label = QLabel("START-UP")
        startup_label.setObjectName("sectionHeader")
        content_layout.addWidget(startup_label)
        
        startup_container = QWidget()
        startup_layout = QHBoxLayout(startup_container)
        startup_layout.setContentsMargins(0, 10, 0, 10)
        
        startup_text = QLabel("Automatically start Orchestrix on login")
        startup_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        self.startup_status = QLabel("Disabled")
        self.startup_status.setStyleSheet("color: #8e9ba9; font-size: 12px; margin-right: 10px;")
        
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
        content_layout.addWidget(divider3)
        
        update_label = QLabel("UPDATE CHANNEL")
        update_label.setObjectName("sectionHeader")
        content_layout.addWidget(update_label)
        
        update_combo = QComboBox()
        update_combo.addItems(["Stable", "Beta", "Alpha"])
        update_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(update_combo)
        
        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider4)
        
        timezone_label = QLabel("LOCAL TIMEZONE")
        timezone_label.setObjectName("sectionHeader")
        content_layout.addWidget(timezone_label)
        
        self.timezone_combo = QComboBox()
        self.timezone_combo.addItems([
            "Asia/Calcutta", "America/New_York", "Europe/London",
            "Europe/Berlin", "Asia/Tokyo", "Asia/Singapore",
            "Australia/Sydney", "Pacific/Auckland"
        ])
        self.timezone_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.timezone_combo.currentIndexChanged.connect(self.change_timezone)
        content_layout.addWidget(self.timezone_combo)
        
        content_layout.addStretch()
        
        self.content_scroll.setWidget(content_widget)
    
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
        header_layout.addWidget(proxy_header)
        
        header_layout.addWidget(self.create_close_button(), alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        content_layout.addWidget(header_container)
        
        http_proxy_label = QLabel("HTTP PROXY")
        http_proxy_label.setObjectName("sectionHeader")
        content_layout.addWidget(http_proxy_label)
        
        proxy_input = QLineEdit()
        proxy_input.setPlaceholderText("Type HTTP proxy url (example: http://proxy.acme.org:8080)")
        content_layout.addWidget(proxy_input)
        
        proxy_desc = QLabel("Proxy is used only for non-cluster communication.")
        proxy_desc.setStyleSheet("color: #8e9ba9; font-size: 13px; padding: 10px 0px;")
        content_layout.addWidget(proxy_desc)
        
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider)
        
        cert_label = QLabel("CERTIFICATE TRUST")
        cert_label.setObjectName("sectionHeader")
        content_layout.addWidget(cert_label)
        
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
        
        cert_desc = QLabel("This will make Lens to trust ANY certificate authority without any validations. Needed with some corporate proxies that do certificate re-writing. Does not affect cluster communications!")
        cert_desc.setStyleSheet("color: #8e9ba9; font-size: 13px; padding: 10px 0px;")
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
        header_layout.addWidget(kubernetes_header)
        
        header_layout.addWidget(self.create_close_button(), alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        content_layout.addWidget(header_container)
        
        kubectl_label = QLabel("KUBECTL BINARY DOWNLOAD")
        kubectl_label.setObjectName("sectionHeader")
        content_layout.addWidget(kubectl_label)
        
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
        
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider1)
        
        download_mirror_label = QLabel("DOWNLOAD MIRROR")
        download_mirror_label.setObjectName("sectionHeader")
        content_layout.addWidget(download_mirror_label)
        
        download_mirror_combo = QComboBox()
        download_mirror_combo.addItems(["Default (Google)", "Alternative Mirror 1", "Alternative Mirror 2"])
        download_mirror_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(download_mirror_combo)
        
        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider2)
        
        binaries_dir_label = QLabel("DIRECTORY FOR BINARIES")
        binaries_dir_label.setObjectName("sectionHeader")
        content_layout.addWidget(binaries_dir_label)
        
        binaries_dir_input = QLineEdit()
        binaries_dir_input.setText(r"C:\Users\Admin\AppData\Roaming\OpenLens\binaries")
        binaries_dir_input.setPlaceholderText("Directory to download binaries into")
        content_layout.addWidget(binaries_dir_input)
        
        binaries_dir_desc = QLabel("The directory to download binaries into.")
        binaries_dir_desc.setStyleSheet("color: #8e9ba9; font-size: 13px; padding: 10px 0px;")
        content_layout.addWidget(binaries_dir_desc)
        
        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider3)
        
        kubectl_path_label = QLabel("PATH TO KUBECTL BINARY")
        kubectl_path_label.setObjectName("sectionHeader")
        content_layout.addWidget(kubectl_path_label)
        
        kubectl_path_input = QLineEdit()
        kubectl_path_input.setText(r"C:\Users\Admin\AppData\Roaming\OpenLens\binaries\kubectl")
        kubectl_path_input.setPlaceholderText("Path to kubectl binary")
        content_layout.addWidget(kubectl_path_input)
        
        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider4)
        
        kubeconfig_label = QLabel("KUBECONFIG SYNCS")
        kubeconfig_label.setObjectName("sectionHeader")
        content_layout.addWidget(kubeconfig_label)
        
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
        
        synced_items_label = QLabel("SYNCED ITEMS")
        synced_items_label.setObjectName("sectionHeader")
        content_layout.addWidget(synced_items_label)
        
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
        
        divider5 = QFrame()
        divider5.setObjectName("divider")
        divider5.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider5)
        
        helm_charts_label = QLabel("HELM CHARTS")
        helm_charts_label.setObjectName("sectionHeader")
        content_layout.addWidget(helm_charts_label)
        
        helm_repos_container = QWidget()
        helm_repos_layout = QHBoxLayout(helm_repos_container)
        helm_repos_layout.setContentsMargins(0, 10, 0, 10)
        
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
        header_layout.addWidget(editor_header)
        
        header_layout.addWidget(self.create_close_button(), alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        content_layout.addWidget(header_container)
        
        minimap_label = QLabel("MINIMAP")
        minimap_label.setObjectName("sectionHeader")
        content_layout.addWidget(minimap_label)
        
        minimap_container = QWidget()
        minimap_layout = QHBoxLayout(minimap_container)
        minimap_layout.setContentsMargins(0, 10, 0, 10)
        
        minimap_text = QLabel("Show minimap")
        minimap_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        minimap_toggle = ToggleSwitch()
        minimap_toggle.setChecked(True)
        
        minimap_position = QComboBox()
        minimap_position.addItems(["right", "left"])
        minimap_position.setCursor(Qt.CursorShape.PointingHandCursor)
        
        minimap_layout.addWidget(minimap_text)
        minimap_layout.addStretch()
        minimap_layout.addWidget(minimap_position)
        minimap_layout.addWidget(minimap_toggle)
        
        content_layout.addWidget(minimap_container)
        
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider1)
        
        line_numbers_label = QLabel("LINE NUMBERS")
        line_numbers_label.setObjectName("sectionHeader")
        content_layout.addWidget(line_numbers_label)
        
        line_numbers_combo = QComboBox()
        line_numbers_combo.addItems(["On", "Off"])
        line_numbers_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(line_numbers_combo)
        
        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider2)
        
        tab_size_label = QLabel("TAB SIZE")
        tab_size_label.setObjectName("sectionHeader")
        content_layout.addWidget(tab_size_label)
        
        tab_size_input = QLineEdit()
        tab_size_input.setText("2")
        content_layout.addWidget(tab_size_input)
        
        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider3)
        
        font_size_label = QLabel("FONT SIZE")
        font_size_label.setObjectName("sectionHeader")
        content_layout.addWidget(font_size_label)
        
        font_size_input = QLineEdit()
        font_size_input.setText("12")
        content_layout.addWidget(font_size_input)
        
        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider4)
        
        font_family_label = QLabel("FONT FAMILY")
        font_family_label.setObjectName("sectionHeader")
        content_layout.addWidget(font_family_label)
        
        font_family_input = QLineEdit()
        font_family_input.setText("RobotoMono")
        content_layout.addWidget(font_family_input)
        
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
        header_layout.addWidget(terminal_header)
        
        header_layout.addWidget(self.create_close_button(), alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        content_layout.addWidget(header_container)
        
        shell_path_label = QLabel("TERMINAL SHELL PATH")
        shell_path_label.setObjectName("sectionHeader")
        content_layout.addWidget(shell_path_label)
        
        shell_path_input = QLineEdit()
        shell_path_input.setText("powershell.exe")
        content_layout.addWidget(shell_path_input)
        
        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider1)
        
        copy_paste_label = QLabel("TERMINAL COPY & PASTE")
        copy_paste_label.setObjectName("sectionHeader")
        content_layout.addWidget(copy_paste_label)
        
        copy_paste_container = QWidget()
        copy_paste_layout = QHBoxLayout(copy_paste_container)
        copy_paste_layout.setContentsMargins(0, 10, 0, 10)
        
        copy_paste_text = QLabel("Copy on select and paste on right-click")
        copy_paste_text.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        copy_paste_toggle = ToggleSwitch()
        copy_paste_toggle.setChecked(False)
        
        copy_paste_layout.addWidget(copy_paste_text)
        copy_paste_layout.addStretch()
        copy_paste_layout.addWidget(copy_paste_toggle)
        
        content_layout.addWidget(copy_paste_container)
        
        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider2)
        
        theme_label = QLabel("TERMINAL THEME")
        theme_label.setObjectName("sectionHeader")
        content_layout.addWidget(theme_label)
        
        theme_combo = QComboBox()
        theme_combo.addItems(["Light", "Dark", "System"])
        theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(theme_combo)
        
        divider3 = QFrame()
        divider3.setObjectName("divider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider3)
        
        font_size_label = QLabel("FONT SIZE")
        font_size_label.setObjectName("sectionHeader")
        content_layout.addWidget(font_size_label)
        
        font_size_input = QLineEdit()
        font_size_input.setText("12")
        content_layout.addWidget(font_size_input)
        
        divider4 = QFrame()
        divider4.setObjectName("divider")
        divider4.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(divider4)
        
        font_family_label = QLabel("FONT FAMILY")
        font_family_label.setObjectName("sectionHeader")
        content_layout.addWidget(font_family_label)
        
        font_family_combo = QComboBox()
        font_family_combo.addItems(["RobotoMono", "Consolas", "Courier New"])
        font_family_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(font_family_combo)
        
        content_layout.addStretch()
        
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
        print(f"Timezone changed to: {timezone}")

class BrowserWidget(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1A1A1A;
                color: white;
            }
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        sidebar = QWidget()
        sidebar.setFixedWidth(183)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        browser_btn = QPushButton("≡ Browser All")
        browser_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 15px;
                border: none;
                color: #4A9EFF;
                width: 183px;
            }
            QPushButton:hover {
                background-color: #2D2D2D;
                width: 183px;
            }
        """)
        browser_btn.clicked.connect(self.on_browser_click)
        sidebar_layout.addWidget(browser_btn)
        
        self.category_btn = QPushButton()
        category_layout = QHBoxLayout(self.category_btn)
        category_layout.setContentsMargins(15, 0, 15, 0)
        category_layout.setSpacing(0)

        text_label = QLabel("Category")
        arrow_label = QLabel("▼")
        arrow_label.setFixedWidth(20)

        category_layout.addWidget(text_label)
        category_layout.addStretch()
        category_layout.addWidget(arrow_label)

        self.category_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                border: none;
                background-color: #2D2D2D;
                color: white;
                width: 183px;
                padding: 10px 0;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QPushButton::menu-indicator {
                width: 0;
            }
            QLabel {
                background: transparent;
                color: white;
            }
        """)
        
        self.category_menu = QMenu(self)
        self.category_menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                width: 183px;
                padding: 5px 0px;
            }
            QMenu::item {
                padding: 8px 15px;
                color: white;
                min-width: 183px;
                margin: 0px;
            }
            QMenu::item:selected {
                background-color: #3D3D3D;
            }
            QMenu::item:checked {
                background-color: #4A9EFF;
            }
            QMenu::indicator {
                width: 0px;
            }
        """)
        self.category_menu.keyPressEvent = self.handle_menu_key_press
        
        categories = ["General", "Clusters", "Web Links"]
        self.category_actions = {}
        for category in categories:
            action = QAction(category, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, cat=category: self.filter_by_category(cat) if checked else None)
            self.category_menu.addAction(action)
            self.category_actions[category] = action
        
        self.category_btn.setMenu(self.category_menu)
        sidebar_layout.addWidget(self.category_btn)
        sidebar_layout.addStretch()
        sidebar.setStyleSheet("border-right: 1px solid #2D2D2D;")
        content_layout.addWidget(sidebar)
        
        main_area = QWidget()
        main_area_layout = QVBoxLayout(main_area)
        main_area_layout.setContentsMargins(20, 10, 20, 20)
        main_area_layout.setSpacing(10)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Name", "Kind", "Source", "Label", "Status", ""])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(self.on_table_click)
        
        palette = self.table.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#1A1A1A"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1A1A1A"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("transparent"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
        self.table.setPalette(palette)
        
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A1A;
                border: none;
                gridline-color: transparent;
                color: white;
            }
            QHeaderView::section {
                background-color: #1A1A1A;
                border: none;
                border-bottom: 1px solid #2D2D2D;
                padding: 8px;
                color: white;
                text-align: left;
            }
            QTableWidget::item {
                border-bottom: 1px solid #2D2D2D;
                padding: 4px;
                color: white;
                background-color: transparent;
            }
            QTableWidget::item:selected {
                background-color: transparent;
                color: white;
            }
            QTableWidget::item:focus {
                background-color: transparent;
                color: white;
            }
            QWidget {
                background-color: transparent;
                color: white;
            }
            QWidget:selected {
                background-color: transparent;
                color: white;
            }
            QLabel {
                background-color: transparent;
                color: white;
            }
            QLabel:selected {
                background-color: transparent;
                color: white;
            }
        """)
        
        browser_header = QWidget()
        browser_header_layout = QHBoxLayout(browser_header)
        browser_header_layout.setContentsMargins(0, 0, 0, 10)
        
        header_left = QWidget()
        header_left_layout = QHBoxLayout(header_left)
        header_left_layout.setContentsMargins(0, 0, 0, 0)
        header_left_layout.setSpacing(10)
        self.title_label = QLabel("Browser All")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.count_label = QLabel("10 items")
        self.count_label.setStyleSheet("color: #666666;")
        header_left_layout.addWidget(self.title_label)
        header_left_layout.addSpacerItem(QSpacerItem(200, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        header_left_layout.addWidget(self.count_label)
        header_left.setLayout(header_left_layout)
        
        search_container = QWidget()
        search_container.setFixedWidth(300)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        self.search_bar = SearchBar(self.table)
        search_layout.addWidget(self.search_bar)
        browser_header_layout.addWidget(header_left)
        browser_header_layout.addStretch(1)
        browser_header_layout.addWidget(search_container)
        main_area_layout.addWidget(browser_header)
        main_area_layout.addWidget(self.table)
        
        data = [
            ("⚙️", "Catalog", None, "General", "app", "", "active"),
            ("🏠", "Welcome Page", None, "General", "app", "", "active"),
            ("⚙️", "Preference", None, "General", "app", "", "active"),
            ("Ox", "Orchestrix Website", "#FFA500", "Web Links", "local", "", "available"),
            ("Ox", "Orchestrix Documentation", "#FFD700", "Web Links", "local", "", "available"),
            ("Ox", "Orchestrix Forum", "#800080", "Web Links", "local", "", "available"),
            ("Ox", "Orchestrix on X(Twitter)", "#00BFFF", "Web Links", "local", "", "available"),
            ("BL", "Orchestrix Official Blog", "#FF0000", "Web Links", "local", "", "available"),
            ("KD", "Kubernetes Documentation", "#32CD32", "Web Links", "local", "", "available"),
            ("DD", "docker-desktop", "#4CAF50", "Clusters", "local", "filter=~/.kube/cluster", "disconnected")
        ]
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            icon, name, color, kind, source, label, status = item
            self.table.setCellWidget(row, 0, NameCell(icon, name, color))
            self.table.setItem(row, 1, QTableWidgetItem(kind))
            self.table.setItem(row, 2, QTableWidgetItem(source))
            self.table.setItem(row, 3, QTableWidgetItem(label))
            status_item = QTableWidgetItem(status)
            if status == "available":
                status_item.setForeground(QColor("#00FF00"))
            elif status == "disconnected":
                status_item.setForeground(QColor("#FF0000"))
            self.table.setItem(row, 4, status_item)
            menu_btn = QPushButton("⋮")
            menu_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    color: #666666;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #2D2D2D;
                    border-radius: 3px;
                }
            """)
            self.table.setCellWidget(row, 5, menu_btn)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 30)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        for i in range(self.table.columnCount()):
            header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(main_area)
        main_layout.addWidget(content)
        
    def filter_by_category(self, category):
        for action in self.category_actions.values():
            action.setChecked(False)
        self.category_actions[category].setChecked(True)
        self.update_browser_header(category)
        visible_count = 0
        for row in range(self.table.rowCount()):
            if category == "All":
                self.table.setRowHidden(row, False)
                visible_count += 1
            else:
                kind = self.table.item(row, 1).text()
                is_visible = kind == category
                self.table.setRowHidden(row, not is_visible)
                if is_visible:
                    visible_count += 1
                    if category == "Clusters":
                        self.main_window.show_clusters()
        self.count_label.setText(f"{visible_count} items")

    def update_browser_header(self, category):
        self.title_label.setText(f"Browser {category}")

    def on_browser_click(self):
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)
        self.update_browser_header("All")
        self.count_label.setText(f"{self.table.rowCount()} items")
        for action in self.category_actions.values():
            action.setChecked(False)

    def handle_menu_key_press(self, event):
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            QMenu.keyPressEvent(self.category_menu, event)
        elif event.key() == Qt.Key.Key_Return:
            action = self.category_menu.activeAction()
            if action:
                action.trigger()
        else:
            QMenu.keyPressEvent(self.category_menu, event)

    def on_table_click(self, row, column):
        name_widget = self.table.cellWidget(row, 0)
        if name_widget:
            label = name_widget.findChild(QLabel, "name_label")
            if label:
                if label.text() == "Preference":
                    self.main_window.show_preferences()
                elif label.text() == "docker-desktop":
                    self.main_window.show_clusters()

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

class NavIconButton(QToolButton):
    def __init__(self, icon, text, active=False, has_dropdown=False, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.icon_text = icon
        self.item_text = text
        self.is_active = active
        self.has_dropdown = has_dropdown
        self.dropdown_open = False
        self.dropdown_menu = None
        
        self.bg_dark = "#1a1a1a"
        self.accent_blue = "#2196F3"
        self.accent_light_blue = "#64B5F6"
        self.text_light = "#f0f0f0"
        self.text_secondary = "#888888"
        
        self.setup_ui()
        if self.has_dropdown:
            self.setup_dropdown()
            
    def setup_ui(self):
        self.setFixedSize(40, 40)
        self.setText(self.icon_text)
        self.setToolTip(self.item_text)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 16))
        self.setAutoRaise(True)
        self.update_style()
        self.clicked.connect(self.activate)
        if self.has_dropdown:
            self.clicked.connect(self.show_dropdown)
        self.installEventFilter(self)
            
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
                         "Network Policies"]
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
            self.dropdown_menu.addAction(item)
            
    def show_dropdown(self):
        if self.has_dropdown:
            self.dropdown_open = True
            self.update_style()
            pos = self.mapToGlobal(QPoint(self.width(), 0))
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
        if self.is_active:
            self.setStyleSheet(f"""
                QToolButton {{
                    background-color: rgba(255, 255, 255, 0.1);
                    color: {self.text_light};
                    border: none;
                    border-radius: 0;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.15);
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QToolButton {{
                    background-color: transparent;
                    color: {self.text_secondary};
                    border: none;
                    border-radius: 0;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                    color: {self.text_light};
                }}
            """)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            QToolTip.showText(
                self.mapToGlobal(QPoint(self.width() + 5, self.height() // 2)),
                self.item_text,
                self,
                QRect(),
                2000
            )
        return super().eventFilter(obj, event)

class DockerDesktopUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Docker Desktop")
        self.setMinimumSize(1000, 700)
        
        app = QApplication.instance()
        if app:
            app.setStyleSheet("""
                QToolTip {
                    background-color: #333333;
                    color: #ffffff;
                    border: 1px solid #444444;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                }
            """)
        
        self.bg_dark = "#1a1a1a"
        self.bg_sidebar = "#1e1e1e"
        self.bg_header = "#1e1e1e"
        self.text_light = "#ffffff"
        self.text_secondary = "#888888"
        self.accent_blue = "#0095ff"
        self.accent_green = "#4CAF50"
        self.border_color = "#2d2d2d"
        self.tab_inactive = "#2d2d2d"
        self.card_bg = "#1e1e1e"
        
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {self.bg_dark};
                color: {self.text_light};
                font-family: 'Segoe UI', sans-serif;
            }}
            QTabWidget::pane {{
                border: none;
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {self.text_secondary};
                padding: 8px 24px;
                border: none;
                margin-right: 2px;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                color: {self.text_light};
                border-bottom: 2px solid {self.accent_blue};
            }}
            QTabBar::tab:hover:!selected {{
                color: {self.text_light};
            }}
        """)
        
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        header = self.create_header()
        right_layout.addWidget(header)
        
        tab_container = self.create_tab_container()
        right_layout.addWidget(tab_container)
        
        content_area = self.create_content_area()
        right_layout.addWidget(content_area, 1)
        
        main_layout.addWidget(right_container, 1)
        self.setCentralWidget(main_widget)
    
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(40)
        sidebar.setStyleSheet(f"""
            background-color: {self.bg_sidebar};
            border-right: 1px solid {self.border_color};
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.nav_buttons = []
        nav_items = [
            ("⚙️", "Cluster", True),
            ("💻", "Nodes", False),
            ("📦", "Workloads", False, True),
            ("📝", "Config", False, True),
            ("🌐", "Network", False, True),
            ("📂", "Storage", False, True),
            ("🔖", "Namespaces", False),
            ("🕒", "Events", False),
            ("⎈", "Helm", False, True),
            ("🔐", "Access Control", False, True),
            ("🧩", "Custom Resources", False, True)
        ]
        
        for item in nav_items:
            nav_btn = NavIconButton(item[0], item[1], item[2], item[3] if len(item) > 3 else False, self)
            self.nav_buttons.append(nav_btn)
            layout.addWidget(nav_btn)
        
        layout.addStretch(1)
        
        x_btn = NavIconButton("🖱️", "X Button", False, False, self)
        y_btn = NavIconButton("⌨️", "Y Button", False, False, self)
        z_btn = NavIconButton("🛠️", "Z Button", False, False, self)
        
        self.nav_buttons.append(x_btn)
        self.nav_buttons.append(y_btn)
        self.nav_buttons.append(z_btn)
        
        layout.addWidget(x_btn)
        layout.addWidget(y_btn)
        layout.addWidget(z_btn)
        
        return sidebar
    
    def create_header(self):
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet(f"""
            background-color: {self.bg_header};
            border-bottom: 1px solid {self.border_color};
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Use QToolButton for the dropdown
        cluster_btn = QToolButton()
        cluster_btn.setFixedHeight(30)  # Match SearchBar height
        cluster_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create horizontal layout for text, arrow, and spacing
        button_layout = QHBoxLayout(cluster_btn)
        button_layout.setContentsMargins(12, 0, 12, 0)  # Padding on left and right
        button_layout.setSpacing(0)  # No spacing between widgets by default

        # Text label
        text_label = QLabel("docker-desktop")
        text_label.setStyleSheet("color: #55c732; background: transparent;")

        # Arrow label
        arrow_label = QLabel("▼")
        arrow_label.setFixedWidth(20)  # Fixed width for arrow
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)  # Center the arrow
        arrow_label.setStyleSheet(f"color: {self.text_secondary}; background: transparent;")

        # Add widgets with equal spacing around the arrow
        button_layout.addWidget(text_label)
        button_layout.addSpacing(10)  # Space between text and arrow
        button_layout.addWidget(arrow_label)
        button_layout.addSpacing(10)  # Equal space between arrow and right edge

        # Style the QToolButton to be visible by default
        cluster_btn.setStyleSheet("""
            QToolButton {
                background-color: #2d2d2d;  /* Visible by default */
                border: none;
                font-size: 13px;
                text-align: left;
                border-radius: 4px;  /* Optional: adds rounded corners */
            }
            QToolButton:hover {
                background-color: #3d3d3d;  /* Slightly lighter on hover */
            }
            QToolButton::menu-indicator {
                image: none;  /* Remove default menu indicator */
            }
        """)

        # Create the dropdown menu
        cluster_menu = QMenu(self)
        cluster_menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 15px;
                color: #ffffff;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)
        
        # Static cluster options
        clusters = ["docker-desktop", "dev cluster", "staging-cluster", "production-cluster"]
        font = QFont("Segoe UI", 13)
        font_metrics = QFontMetrics(font)
        
        # Calculate the width based on the longest text plus spacing
        max_width = 0
        for cluster in clusters:
            text_width = font_metrics.horizontalAdvance(cluster) + 12 + 10 + 20 + 10 + 12  # Left padding + text-to-arrow + arrow + arrow-to-right + right padding
            max_width = max(max_width, text_width)
        
        # Set the button width
        cluster_btn.setFixedWidth(max_width)

        # Add menu items
        for cluster in clusters:
            action = QAction(cluster, self)
            action.triggered.connect(lambda checked, c=cluster: print(f"Selected cluster: {c}"))
            cluster_menu.addAction(action)
        
        cluster_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        cluster_btn.setMenu(cluster_menu)
        
        layout.addWidget(cluster_btn)
        
        # Add stretch to push search bars to the right
        layout.addStretch(1)
        
        # Updated search bar with consistent width
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Search...")
        search_bar.setFixedHeight(30)
        search_bar.setMinimumWidth(250)
        search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #333333;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 6px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                background-color: #404040;
            }
        """)
        
        # Updated namespace search bar with consistent width
        namespace_search = QLineEdit()
        namespace_search.setPlaceholderText("Search namespace...")
        namespace_search.setFixedHeight(30)
        namespace_search.setMinimumWidth(250)
        namespace_search.setStyleSheet("""
            QLineEdit {
                background-color: #333333;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                padding: 6px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                background-color: #404040;
            }
        """)
        
        layout.addWidget(search_bar)
        layout.addWidget(namespace_search)
        
        return header

    def create_tab_container(self):
        tab_widget = QTabWidget()
        tab_widget.setFixedHeight(44)
        tab_widget.addTab(QWidget(), "Master")
        tab_widget.addTab(QWidget(), "Worker")
        tab_widget.setCurrentIndex(0)
        return tab_widget
    
    def create_content_area(self):
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        metric_panel1 = self.create_metric_panel()
        metric_panel2 = self.create_metric_panel()
        status_panel = self.create_status_panel()
        
        content_layout.addWidget(metric_panel1, 0, 0)
        content_layout.addWidget(metric_panel2, 0, 1)
        content_layout.addWidget(status_panel, 1, 0, 1, 2)
        
        return content_widget
    
    def create_metric_panel(self):
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background-color: {self.card_bg};
                border-radius: 4px;
            }}
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        tabs = QWidget()
        tabs_layout = QHBoxLayout(tabs)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(4)
        
        cpu_btn = QPushButton("CPU")
        cpu_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: none;
                padding: 6px 16px;
                font-size: 13px;
                border-radius: 4px;
            }
        """)
        
        memory_btn = QPushButton("Memory")
        memory_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        
        tabs_layout.addWidget(cpu_btn)
        tabs_layout.addWidget(memory_btn)
        tabs_layout.addStretch()
        
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_msg = QLabel("Metrics are not available due to missing or invalid Prometheus")
        info_msg.setStyleSheet("color: #888888; font-size: 13px;")
        info_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        settings_link = QLabel("Open cluster settings")
        settings_link.setStyleSheet("""
            color: #0095ff;
            font-size: 13px;
            margin-top: 8px;
        """)
        settings_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_link.setCursor(Qt.CursorShape.PointingHandCursor)
        
        info_layout.addWidget(info_msg)
        info_layout.addWidget(settings_link)
        
        layout.addWidget(tabs)
        layout.addWidget(info_container, 1, Qt.AlignmentFlag.AlignCenter)
        
        return panel
    
    def create_status_panel(self):
        panel = QWidget()
        panel.setStyleSheet(f"""
            background-color: {self.card_bg};
            border-radius: 4px;
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 48, 32, 48)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        success_icon = QLabel("✓")
        success_icon.setFixedSize(80, 80)
        success_icon.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            font-size: 40px;
            border-radius: 40px;
            qproperty-alignment: AlignCenter;
        """)
        
        status_title = QLabel("No issues found")
        status_title.setStyleSheet("""
            color: white;
            font-size: 20px;
            font-weight: 500;
            margin-top: 16px;
        """)
        status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_subtitle = QLabel("Everything is fine in the Cluster")
        status_subtitle.setStyleSheet("""
            color: #888888;
            font-size: 14px;
            margin-top: 4px;
        """)
        status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(success_icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_title)
        layout.addWidget(status_subtitle)
        
        return panel
    
    def set_active_nav_button(self, active_button):
        for btn in self.nav_buttons:
            btn.is_active = False
            btn.update_style()
        active_button.is_active = True
        active_button.update_style()

class OrchestrixGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Orchetrix')
        self.setMinimumSize(1200, 700)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1A1A1A;
                color: white;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.stack = QStackedWidget()
        self.browser_widget = BrowserWidget(self)
        self.preferences_widget = PreferencesWidget(self)
        self.clusters_widget = DockerDesktopUI()
        
        self.stack.addWidget(self.browser_widget)
        self.stack.addWidget(self.preferences_widget)
        self.stack.addWidget(self.clusters_widget)
        
        main_layout.addWidget(self.stack)
        
    def show_browser(self):
        self.stack.setCurrentWidget(self.browser_widget)

    def show_preferences(self):
        self.stack.setCurrentWidget(self.preferences_widget)

    def show_clusters(self):
        self.stack.setCurrentWidget(self.clusters_widget)

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = OrchestrixGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()