"""
Improved Port Forward Dialog with better UI layout and content display
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QComboBox, QLineEdit, QFormLayout, QGroupBox,
    QMessageBox, QCheckBox, QTextEdit, QFrame, QScrollArea,
    QSizePolicy, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPalette
from typing import Optional, Dict, List

from UI.ThemeAwarePage import ThemeAwareMixin
from Styles.PortForwardDialogStyles import (
    get_dialog_style, get_header_frame_style, get_group_box_style,
    get_resource_info_style, get_namespace_info_style, get_ports_info_style,
    get_help_text_style, get_input_field_style, get_auto_port_checkbox_style,
    get_preview_text_style, get_button_frame_style, get_primary_button_style,
    get_secondary_button_style, get_active_dialog_style, get_status_loading_style,
    get_status_inactive_style, get_status_active_style
)
from Utils.port_forward_manager import get_port_forward_manager, PortForwardConfig
import time

class PortForwardDialog(ThemeAwareMixin, QDialog):
    """Improved dialog for creating port forwards with better content display"""

    port_forward_requested = pyqtSignal(dict)  # Configuration dictionary

    def __init__(self, resource_name: str, resource_type: str, namespace: str,
                 available_ports: List[int] = None, parent=None):
        super().__init__(parent)
        self.resource_name = resource_name
        self.resource_type = resource_type
        self.namespace = namespace
        self.available_ports = available_ports or []
        self.port_manager = get_port_forward_manager()

        self.setWindowTitle(f"Create Port Forward")
        self.setModal(True)
        self.setMinimumSize(450, 500)
        self.setMaximumSize(550, 650)

        # Set dialog properties for better display
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setSizeGripEnabled(True)

        # Store widget references for theme updates
        self.header_frame = None
        self.resource_info = None
        self.namespace_info = None
        self.ports_info = None
        self.help_labels = []
        self.preview_text = None
        self.button_frame = None
        self.create_button = None
        self.cancel_button = None

        self.setup_ui()
        self.apply_styles()
        self.populate_ports()
        self.update_preview()

    def setup_ui(self):
        """Setup the improved dialog UI"""
        # Create main layout with compact spacing
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header section
        self.create_header_section(main_layout)

        # Create scroll area for main content with custom scrollbar
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Scroll area styling will be applied in apply_styles()

        # Content widget inside scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)

        # Resource information section
        self.create_resource_info_section(content_layout)

        # Port configuration section
        self.create_port_configuration_section(content_layout)

        # Advanced options section
        self.create_advanced_options_section(content_layout)

        # Preview section
        self.create_preview_section(content_layout)

        # Set content widget in scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, 1)  # Give scroll area stretch priority

        # Button section (fixed at bottom)
        self.create_button_section(main_layout)

        # Connect signals for live preview updates
        self.connect_preview_signals()

    def create_header_section(self, layout):
        """Create the compact header section with title and icon"""
        self.header_frame = QFrame()
        self.header_frame.setFrameStyle(QFrame.Shape.Box)

        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setSpacing(10)
        header_layout.setContentsMargins(8, 8, 8, 8)

        # Smaller icon
        icon_label = QLabel("🚀")
        icon_label.setFont(QFont("Arial", 16))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(32, 32)
        header_layout.addWidget(icon_label)

        # Compact title only
        title_label = QLabel("Create Port Forward")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        layout.addWidget(self.header_frame)

    def create_resource_info_section(self, layout):
        """Create resource information section"""
        info_group = QGroupBox("📋 Resource Information")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(12)

        # Resource type and name
        self.resource_info = QLabel(f"{self.resource_type.title()}: {self.resource_name}")
        info_layout.addRow("Resource:", self.resource_info)

        # Namespace
        self.namespace_info = QLabel(self.namespace)
        info_layout.addRow("Namespace:", self.namespace_info)

        # Available ports info
        if self.available_ports:
            ports_text = ", ".join(map(str, self.available_ports[:5]))
            if len(self.available_ports) > 5:
                ports_text += f" (+{len(self.available_ports) - 5} more)"
            self.ports_info = QLabel(ports_text)
            info_layout.addRow("Available Ports:", self.ports_info)

        layout.addWidget(info_group)

    def create_port_configuration_section(self, layout):
        """Create port configuration section"""
        port_group = QGroupBox("⚙️ Port Configuration")
        port_layout = QFormLayout(port_group)
        port_layout.setSpacing(15)

        # Target port selection
        target_container = QWidget()
        target_layout = QVBoxLayout(target_container)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(8)

        self.target_port_combo = QComboBox()
        self.target_port_combo.setEditable(True)
        # Styling will be applied in apply_styles()
        self.target_port_combo.setMinimumHeight(35)
        target_layout.addWidget(self.target_port_combo)

        target_help = QLabel("Select or enter the port number on the target resource")
        self.help_labels.append(target_help)
        target_layout.addWidget(target_help)

        port_layout.addRow("Target Port:", target_container)

        # Local port configuration
        local_container = QWidget()
        local_layout = QVBoxLayout(local_container)
        local_layout.setContentsMargins(0, 0, 0, 0)
        local_layout.setSpacing(8)

        local_port_widget = QWidget()
        local_port_layout = QHBoxLayout(local_port_widget)
        local_port_layout.setContentsMargins(0, 0, 0, 0)
        local_port_layout.setSpacing(10)

        self.local_port_spin = QSpinBox()
        self.local_port_spin.setRange(1024, 65535)
        self.local_port_spin.setValue(8080)
        self.local_port_spin.setMinimumHeight(35)
        self.local_port_spin.setMinimumWidth(120)
        local_port_layout.addWidget(self.local_port_spin)

        self.auto_port_check = QCheckBox("Auto-assign available port")
        self.auto_port_check.setChecked(True)
        local_port_layout.addWidget(self.auto_port_check)
        local_port_layout.addStretch()

        local_layout.addWidget(local_port_widget)

        local_help = QLabel("Local port to listen on (automatically finds available port if checked)")
        self.help_labels.append(local_help)
        local_layout.addWidget(local_help)

        port_layout.addRow("Local Port:", local_container)

        # Protocol selection
        protocol_container = QWidget()
        protocol_layout = QVBoxLayout(protocol_container)
        protocol_layout.setContentsMargins(0, 0, 0, 0)
        protocol_layout.setSpacing(8)

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["TCP", "UDP"])
        self.protocol_combo.setMinimumHeight(35)
        protocol_layout.addWidget(self.protocol_combo)

        protocol_help = QLabel("Network protocol (TCP for HTTP/HTTPS, UDP for other protocols)")
        self.help_labels.append(protocol_help)
        protocol_layout.addWidget(protocol_help)

        port_layout.addRow("Protocol:", protocol_container)

        layout.addWidget(port_group)

    def create_advanced_options_section(self, layout):
        """Create advanced options section"""
        advanced_group = QGroupBox("🔧 Advanced Options")
        advanced_layout = QFormLayout(advanced_group)
        advanced_layout.setSpacing(12)

        # Bind address
        bind_container = QWidget()
        bind_layout = QVBoxLayout(bind_container)
        bind_layout.setContentsMargins(0, 0, 0, 0)
        bind_layout.setSpacing(8)

        self.bind_address = QLineEdit("localhost")
        self.bind_address.setMinimumHeight(35)
        bind_layout.addWidget(self.bind_address)

        bind_help = QLabel("Network interface to bind to (localhost for local access only)")
        self.help_labels.append(bind_help)
        bind_layout.addWidget(bind_help)

        advanced_layout.addRow("Bind Address:", bind_container)

        layout.addWidget(advanced_group)

    def create_preview_section(self, layout):
        """Create preview section"""
        preview_group = QGroupBox("👁️ Configuration Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setSpacing(10)

        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(120)
        self.preview_text.setMinimumHeight(120)
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group)

    def create_button_section(self, layout):
        """Create button section"""
        self.button_frame = QFrame()
        self.button_frame.setFrameStyle(QFrame.Shape.HLine)

        button_layout = QHBoxLayout(self.button_frame)
        button_layout.setContentsMargins(0, 15, 0, 0)
        button_layout.setSpacing(15)

        # Help button
        help_button = QPushButton("❓ Help")
        help_button.clicked.connect(self.show_help)
        button_layout.addWidget(help_button)

        button_layout.addStretch()

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        # Create button
        self.create_button = QPushButton("🚀 Create Port Forward")
        self.create_button.clicked.connect(self.create_port_forward)
        self.create_button.setDefault(True)
        button_layout.addWidget(self.create_button)

        layout.addWidget(self.button_frame)

    def connect_preview_signals(self):
        """Connect signals for live preview updates"""
        self.target_port_combo.currentTextChanged.connect(self.on_target_port_changed)
        self.local_port_spin.valueChanged.connect(self.update_preview)
        self.protocol_combo.currentTextChanged.connect(self.update_preview)
        self.bind_address.textChanged.connect(self.update_preview)
        self.auto_port_check.toggled.connect(self.on_auto_port_toggled)

    def populate_ports(self):
        """Populate available ports"""
        if self.available_ports:
            for port in sorted(self.available_ports):
                self.target_port_combo.addItem(str(port))
        else:
            # Default common ports
            common_ports = [80, 443, 8080, 8443, 3000, 5000, 9090]
            for port in common_ports:
                self.target_port_combo.addItem(str(port))

        # Set first port as default if available
        if self.target_port_combo.count() > 0:
            self.target_port_combo.setCurrentIndex(0)

    def on_target_port_changed(self, text):
        """Handle target port change"""
        try:
            port = int(text)
            # Auto-suggest local port based on target port
            if self.auto_port_check.isChecked():
                suggested_port = self.port_manager.get_available_local_port(port)
                self.local_port_spin.setValue(suggested_port)
        except ValueError:
            pass

        self.update_preview()

    def on_auto_port_toggled(self, checked):
        """Handle auto port assignment toggle"""
        self.local_port_spin.setEnabled(not checked)
        if checked:
            try:
                target_port = int(self.target_port_combo.currentText())
                available_port = self.port_manager.get_available_local_port(target_port)
                self.local_port_spin.setValue(available_port)
            except (ValueError, RuntimeError):
                self.local_port_spin.setValue(8080)

        self.update_preview()

    def update_preview(self):
        """Update the port forward preview"""
        try:
            target_port = int(self.target_port_combo.currentText())
            local_port = self.local_port_spin.value()
            protocol = self.protocol_combo.currentText()
            bind_addr = self.bind_address.text()

            preview_text = f"""🔧 Port Forward Configuration
{'='*50}

📦 Resource Details:
   Type: {self.resource_type.upper()}
   Name: {self.resource_name}
   Namespace: {self.namespace}

🌐 Network Configuration:
   Local Address: {bind_addr}:{local_port}
   Target Port: {target_port}
   Protocol: {protocol}

🔗 Access Information:
   URL: http://{bind_addr}:{local_port}
   Status: Ready to create

⚡ Traffic Flow:
   {bind_addr}:{local_port} ──► {self.resource_type}/{self.resource_name}:{target_port}"""

            self.preview_text.setPlainText(preview_text)

        except ValueError:
            self.preview_text.setPlainText("❌ Invalid port configuration\nPlease check your port settings.")

    def show_help(self):
        """Show help dialog"""
        help_text = """
<h3>Port Forward Help</h3>

<p><b>What is Port Forwarding?</b><br>
Port forwarding allows you to access services running inside your Kubernetes cluster from your local machine.</p>

<p><b>Target Port:</b><br>
The port number that your application is listening on inside the pod or service.</p>

<p><b>Local Port:</b><br>
The port number on your local machine that will forward traffic to the target port.</p>

<p><b>Protocol:</b><br>
• TCP: Use for HTTP/HTTPS web services<br>
• UDP: Use for other protocols like DNS</p>

<p><b>Auto-assign:</b><br>
Automatically finds an available local port if the suggested port is already in use.</p>
"""

        msg = QMessageBox(self)
        msg.setWindowTitle("Port Forward Help")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def create_port_forward(self):
        """Create the port forward with improved validation"""
        try:
            # Validate inputs
            target_port_text = self.target_port_combo.currentText().strip()
            if not target_port_text:
                self.show_validation_error("Please specify a target port")
                return

            try:
                target_port = int(target_port_text)
                if not (1 <= target_port <= 65535):
                    raise ValueError()
            except ValueError:
                self.show_validation_error("Target port must be between 1 and 65535")
                return

            local_port = self.local_port_spin.value()
            protocol = self.protocol_combo.currentText()

            # Auto-assign local port if enabled
            if self.auto_port_check.isChecked():
                try:
                    local_port = self.port_manager.get_available_local_port(local_port)
                    self.local_port_spin.setValue(local_port)
                except RuntimeError as e:
                    self.show_validation_error(f"Cannot find available port: {str(e)}")
                    return

            # Check if local port is available
            if not self.auto_port_check.isChecked():
                if not self.port_manager._is_port_available(local_port):
                    reply = QMessageBox.question(
                        self, "Port In Use",
                        f"Local port {local_port} is already in use.\n\n"
                        f"Would you like to auto-assign an available port instead?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self.auto_port_check.setChecked(True)
                        self.on_auto_port_toggled(True)
                        local_port = self.local_port_spin.value()
                    else:
                        return

            # Create configuration dictionary
            config = {
                'resource_name': self.resource_name,
                'resource_type': self.resource_type,
                'namespace': self.namespace,
                'target_port': target_port,
                'local_port': local_port,
                'protocol': protocol
            }

            self.port_forward_requested.emit(config)
            self.accept()

        except Exception as e:
            self.show_validation_error(f"Failed to create port forward: {str(e)}")

    def show_validation_error(self, message):
        """Show validation error with consistent styling"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Validation Error")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def apply_styles(self):
        """Apply comprehensive styling to the dialog"""
        self.setStyleSheet(get_dialog_style())
        
        # Apply styles to stored widget references
        if self.header_frame:
            self.header_frame.setStyleSheet(get_header_frame_style())
        
        if self.resource_info:
            self.resource_info.setStyleSheet(get_resource_info_style())
        
        if self.namespace_info:
            self.namespace_info.setStyleSheet(get_namespace_info_style())
        
        if hasattr(self, 'ports_info') and self.ports_info:
            self.ports_info.setStyleSheet(get_ports_info_style())
        
        # Apply help text styling
        for help_label in self.help_labels:
            help_label.setStyleSheet(get_help_text_style())
        
        # Apply input field styling
        if hasattr(self, 'target_port_combo'):
            from UI.Styles import AppStyles
            self.target_port_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
        
        if hasattr(self, 'local_port_spin'):
            self.local_port_spin.setStyleSheet(get_input_field_style())
        
        if hasattr(self, 'protocol_combo'):
            from UI.Styles import AppStyles
            self.protocol_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
        
        if hasattr(self, 'bind_address'):
            self.bind_address.setStyleSheet(get_input_field_style())
        
        if hasattr(self, 'auto_port_check'):
            self.auto_port_check.setStyleSheet(get_auto_port_checkbox_style())
        
        # Apply group box styling to all group boxes
        for group_box in self.findChildren(QGroupBox):
            group_box.setStyleSheet(get_group_box_style())
        
        # Apply preview text styling
        if self.preview_text:
            self.preview_text.setStyleSheet(get_preview_text_style())
        
        # Apply button frame styling
        if self.button_frame:
            self.button_frame.setStyleSheet(get_button_frame_style())
        
        # Apply button styling
        if self.create_button:
            self.create_button.setStyleSheet(get_primary_button_style())
        
        if self.cancel_button:
            self.cancel_button.setStyleSheet(get_secondary_button_style())
        
        # Apply secondary button styling to help button
        for button in self.findChildren(QPushButton):
            if button.text() == "❓ Help":
                button.setStyleSheet(get_secondary_button_style())

    def _on_theme_changed(self, theme_name):
        """Handle theme changes by refreshing all widget styles"""
        self.apply_styles()

    def stop_all_forwards(self):
        """Stop all port forwards with confirmation"""
        forwards = self.port_manager.get_port_forwards()
        if not forwards:
            QMessageBox.information(self, "No Port Forwards", "No active port forwards to stop.")
            return

        reply = QMessageBox.question(
            self, "Confirm Stop All",
            f"Stop all {len(forwards)} port forwards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.port_manager.stop_all_port_forwards()
            self.refresh_forwards()
