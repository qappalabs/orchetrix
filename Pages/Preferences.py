import sys
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFrame, QLineEdit, QCheckBox, QScrollArea
)
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QPainter
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtSignal

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

    def __init__(self):
        super().__init__()
        self.setup_ui()

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

        # Back button with icon
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
        theme_combo.addItems(["Select...", "Dark", "Light"])
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

        update_combo = QComboBox()
        update_combo.addItems(["Stable", "Beta", "Alpha"])
        update_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        update_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(update_combo)

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

        self.timezone_combo = QComboBox()
        self.timezone_combo.addItems([
            "Asia/Calcutta", "America/New_York", "Europe/London",
            "Europe/Berlin", "Asia/Tokyo", "Asia/Singapore",
            "Australia/Sydney", "Pacific/Auckland"
        ])
        self.timezone_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
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
        proxy_header.setStyleSheet(AppStyles.SECTION_HEADER_STYLE)
        header_layout.addWidget(proxy_header)
        header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

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
        header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

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
        header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        content_layout.addWidget(header_container)

        # Minimap section
        minimap_label = QLabel("MINIMAP")
        minimap_label.setObjectName("sectionHeader")
        minimap_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(minimap_label)

        minimap_container = QWidget()
        minimap_layout = QHBoxLayout(minimap_container)
        minimap_layout.setContentsMargins(0, 10, 0, 10)

        minimap_text = QLabel("Show minimap")
        minimap_text.setStyleSheet(AppStyles.TEXT_STYLE)

        minimap_toggle = ToggleSwitch()
        minimap_toggle.setChecked(True)

        minimap_position = QComboBox()
        minimap_position.addItems(["right", "left"])
        minimap_position.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        minimap_position.setCursor(Qt.CursorShape.PointingHandCursor)

        minimap_layout.addWidget(minimap_text)
        minimap_layout.addStretch()
        minimap_layout.addWidget(minimap_position)
        minimap_layout.addWidget(minimap_toggle)

        content_layout.addWidget(minimap_container)

        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(AppStyles.DIVIDER_STYLE)
        content_layout.addWidget(divider1)

        # Line Numbers section
        line_numbers_label = QLabel("LINE NUMBERS")
        line_numbers_label.setObjectName("sectionHeader")
        line_numbers_label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE)
        content_layout.addWidget(line_numbers_label)

        line_numbers_combo = QComboBox()
        line_numbers_combo.addItems(["On", "Off"])
        line_numbers_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        line_numbers_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(line_numbers_combo)

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

        tab_size_input = QLineEdit()
        tab_size_input.setText("2")
        tab_size_input.setStyleSheet(AppStyles.INPUT_STYLE)
        content_layout.addWidget(tab_size_input)

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

        font_size_input = QLineEdit()
        font_size_input.setText("12")
        font_size_input.setStyleSheet(AppStyles.INPUT_STYLE)
        content_layout.addWidget(font_size_input)

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

        font_family_input = QLineEdit()
        font_family_input.setText("RobotoMono")
        font_family_input.setStyleSheet(AppStyles.INPUT_STYLE)
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
        terminal_header.setStyleSheet(AppStyles.SECTION_HEADER_STYLE)
        header_layout.addWidget(terminal_header)
        header_layout.addWidget(self.create_back_button(), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

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
        copy_paste_toggle.setChecked(False)

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
        theme_combo.addItems(["Light", "Dark", "System"])
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

        font_size_input = QLineEdit()
        font_size_input.setText("12")
        font_size_input.setStyleSheet(AppStyles.INPUT_STYLE)
        content_layout.addWidget(font_size_input)

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

        font_family_combo = QComboBox()
        font_family_combo.addItems(["RobotoMono", "Consolas", "Courier New"])
        font_family_combo.setStyleSheet(AppStyles.DROPDOWN_STYLE)
        font_family_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(font_family_combo)

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

    def change_timezone(self, index):
        timezone = self.timezone_combo.currentText()
        print(f"Timezone changed to: {timezone}")