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
from UI.Styles import AppStyles, AppColors
from Utils.port_forward_manager import get_port_forward_manager, PortForwardConfig
import time

class PortForwardDialog(QDialog):
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
        scroll_area.setStyleSheet(AppStyles.UNIFIED_SCROLL_BAR_STYLE)
        
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
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.BG_MEDIUM};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        
        header_layout = QHBoxLayout(header_frame)
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
        
        layout.addWidget(header_frame)
    
    def create_resource_info_section(self, layout):
        """Create resource information section"""
        info_group = QGroupBox("📋 Resource Information")
        info_group.setStyleSheet(self.get_group_style())
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(12)
        
        # Resource type and name
        resource_info = QLabel(f"{self.resource_type.title()}: {self.resource_name}")
        resource_info.setStyleSheet("font-weight: bold; color: #4CAF50;")
        info_layout.addRow("Resource:", resource_info)
        
        # Namespace
        namespace_info = QLabel(self.namespace)
        namespace_info.setStyleSheet("font-weight: bold; color: #2196F3;")
        info_layout.addRow("Namespace:", namespace_info)
        
        # Available ports info
        if self.available_ports:
            ports_text = ", ".join(map(str, self.available_ports[:5]))
            if len(self.available_ports) > 5:
                ports_text += f" (+{len(self.available_ports) - 5} more)"
            ports_info = QLabel(ports_text)
            ports_info.setStyleSheet("color: #FF9800;")
            info_layout.addRow("Available Ports:", ports_info)
        
        layout.addWidget(info_group)
    
    def create_port_configuration_section(self, layout):
        """Create port configuration section"""
        port_group = QGroupBox("⚙️ Port Configuration")
        port_group.setStyleSheet(self.get_group_style())
        port_layout = QFormLayout(port_group)
        port_layout.setSpacing(15)
        
        # Target port selection
        target_container = QWidget()
        target_layout = QVBoxLayout(target_container)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(8)
        
        self.target_port_combo = QComboBox()
        self.target_port_combo.setEditable(True)
        self.target_port_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
        self.target_port_combo.setMinimumHeight(35)
        target_layout.addWidget(self.target_port_combo)
        
        target_help = QLabel("Select or enter the port number on the target resource")
        target_help.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")
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
        self.local_port_spin.setStyleSheet(self.get_input_style())
        self.local_port_spin.setMinimumHeight(35)
        self.local_port_spin.setMinimumWidth(120)
        local_port_layout.addWidget(self.local_port_spin)
        
        self.auto_port_check = QCheckBox("Auto-assign available port")
        self.auto_port_check.setChecked(True)
        self.auto_port_check.setStyleSheet("color: #4CAF50; font-weight: bold;")
        local_port_layout.addWidget(self.auto_port_check)
        local_port_layout.addStretch()
        
        local_layout.addWidget(local_port_widget)
        
        local_help = QLabel("Local port to listen on (automatically finds available port if checked)")
        local_help.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")
        local_layout.addWidget(local_help)
        
        port_layout.addRow("Local Port:", local_container)
        
        # Protocol selection
        protocol_container = QWidget()
        protocol_layout = QVBoxLayout(protocol_container)
        protocol_layout.setContentsMargins(0, 0, 0, 0)
        protocol_layout.setSpacing(8)
        
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["TCP", "UDP"])
        self.protocol_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
        self.protocol_combo.setMinimumHeight(35)
        protocol_layout.addWidget(self.protocol_combo)
        
        protocol_help = QLabel("Network protocol (TCP for HTTP/HTTPS, UDP for other protocols)")
        protocol_help.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")
        protocol_layout.addWidget(protocol_help)
        
        port_layout.addRow("Protocol:", protocol_container)
        
        layout.addWidget(port_group)
    
    def create_advanced_options_section(self, layout):
        """Create advanced options section"""
        advanced_group = QGroupBox("🔧 Advanced Options")
        advanced_group.setStyleSheet(self.get_group_style())
        advanced_layout = QFormLayout(advanced_group)
        advanced_layout.setSpacing(12)
        
        # Bind address
        bind_container = QWidget()
        bind_layout = QVBoxLayout(bind_container)
        bind_layout.setContentsMargins(0, 0, 0, 0)
        bind_layout.setSpacing(8)
        
        self.bind_address = QLineEdit("localhost")
        self.bind_address.setStyleSheet(self.get_input_style())
        self.bind_address.setMinimumHeight(35)
        bind_layout.addWidget(self.bind_address)
        
        bind_help = QLabel("Network interface to bind to (localhost for local access only)")
        bind_help.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")
        bind_layout.addWidget(bind_help)
        
        advanced_layout.addRow("Bind Address:", bind_container)
        
        layout.addWidget(advanced_group)
    
    def create_preview_section(self, layout):
        """Create preview section"""
        preview_group = QGroupBox("👁️ Configuration Preview")
        preview_group.setStyleSheet(self.get_group_style())
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setSpacing(10)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(120)
        self.preview_text.setMinimumHeight(120)
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                line-height: 1.4;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """)
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
    
    def create_button_section(self, layout):
        """Create button section"""
        button_frame = QFrame()
        button_frame.setFrameStyle(QFrame.Shape.HLine)
        button_frame.setStyleSheet(f"border-top: 1px solid {AppColors.BORDER_COLOR};")
        
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 15, 0, 0)
        button_layout.setSpacing(15)
        
        # Help button
        help_button = QPushButton("❓ Help")
        help_button.setStyleSheet(self.get_secondary_button_style())
        help_button.clicked.connect(self.show_help)
        button_layout.addWidget(help_button)
        
        button_layout.addStretch()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet(self.get_secondary_button_style())
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # Create button
        self.create_button = QPushButton("🚀 Create Port Forward")
        self.create_button.setStyleSheet(self.get_primary_button_style())
        self.create_button.clicked.connect(self.create_port_forward)
        self.create_button.setDefault(True)
        button_layout.addWidget(self.create_button)
        
        layout.addWidget(button_frame)
    
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
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
                font-size: 12px;
            }}
            
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
                background: transparent;
            }}
            
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)
    
    def get_group_style(self):
        """Get group box styling"""
        return f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {AppColors.BORDER_COLOR};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: {AppColors.BG_MEDIUM};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 2px 8px;
                background-color: {AppColors.BG_MEDIUM};
                border-radius: 4px;
            }}
        """
    
    def get_input_style(self):
        """Get input field styling"""
        return f"""
            QSpinBox, QLineEdit {{
                background-color: {AppColors.BG_LIGHT};
                color: {AppColors.TEXT_LIGHT};
                border: 2px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QSpinBox:focus, QLineEdit:focus {{
                border-color: {AppColors.ACCENT_BLUE};
                background-color: {AppColors.BG_MEDIUM};
            }}
        """
    
    def get_primary_button_style(self):
        """Get primary button styling"""
        return f"""
            QPushButton {{
                background-color: {AppColors.ACCENT_BLUE};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 13px;
                font-weight: bold;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
            QPushButton:pressed {{
                background-color: #1565C0;
            }}
        """
    
    def get_secondary_button_style(self):
        """Get secondary button styling"""
        return f"""
            QPushButton {{
                background-color: {AppColors.BG_MEDIUM};
                color: {AppColors.TEXT_LIGHT};
                border: 2px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 12px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {AppColors.BG_LIGHT};
                border-color: {AppColors.ACCENT_BLUE};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.BG_DARK};
            }}
        """


class ActivePortForwardsDialog(QDialog):
    """Enhanced dialog showing active port forwards with improved layout"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.port_manager = get_port_forward_manager()
        
        self.setWindowTitle("Active Port Forwards")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        self.setup_ui()
        self.apply_styles()
        self.refresh_forwards()
        
        # Connect to manager signals
        self.port_manager.port_forwards_updated.connect(self.refresh_forwards)
    
    def setup_ui(self):
        """Setup enhanced UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("🚀 Active Port Forwards")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_label = QLabel("Loading...")
        self.status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)
        
        # Content area with scroll and custom scrollbar
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet(AppStyles.UNIFIED_SCROLL_BAR_STYLE)
        
        self.content_area = QTextEdit()
        self.content_area.setReadOnly(True)
        scroll_area.setWidget(self.content_area)
        
        layout.addWidget(scroll_area)
        
        # Button section
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.refresh_forwards)
        
        self.stop_all_button = QPushButton("🛑 Stop All")
        self.stop_all_button.clicked.connect(self.stop_all_forwards)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.stop_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def apply_styles(self):
        """Apply enhanced styling"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
            }}
            QTextEdit {{
                background-color: {AppColors.BG_MEDIUM};
                color: {AppColors.TEXT_LIGHT};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 8px;
                padding: 15px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                line-height: 1.5;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
            QPushButton {{
                background-color: {AppColors.BG_MEDIUM};
                color: {AppColors.TEXT_LIGHT};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {AppColors.BG_LIGHT};
            }}
        """)
    
    def refresh_forwards(self):
        """Refresh the list of port forwards with enhanced display"""
        forwards = self.port_manager.get_port_forwards()
        
        # Update status
        if not forwards:
            self.status_label.setText("No active port forwards")
            self.status_label.setStyleSheet("color: #666; font-weight: bold;")
        else:
            active_count = sum(1 for f in forwards if f.status == 'active')
            self.status_label.setText(f"{active_count}/{len(forwards)} active")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        if not forwards:
            self.content_area.setPlainText("No active port forwards\n\nCreate port forwards from the Pods or Services pages using the 'Port Forward' action.")
            return
        
        content = "🚀 ACTIVE PORT FORWARDS\n"
        content += "=" * 60 + "\n\n"
        
        for i, config in enumerate(forwards, 1):
            # Status emoji
            status_emoji = {
                'active': '🟢',
                'inactive': '🔴',
                'starting': '🟡',
                'error': '❌'
            }.get(config.status, '⚪')
            
            content += f"{status_emoji} [{i}] {config.resource_type.upper()}: {config.resource_name}\n"
            content += f"    📂 Namespace: {config.namespace}\n"
            content += f"    🌐 Forward: localhost:{config.local_port} ──► {config.target_port}\n"
            content += f"    📡 Protocol: {config.protocol}\n"
            content += f"    📊 Status: {config.status.upper()}\n"
            
            if config.error_message:
                content += f"    ❌ Error: {config.error_message}\n"
            
            # Calculate uptime for active forwards
            if config.status == 'active' and config.created_at:
                uptime = time.time() - config.created_at
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                content += f"    ⏱️  Uptime: {hours}h {minutes}m\n"
            
            content += f"    🔗 Access: http://localhost:{config.local_port}\n"
            
            if i < len(forwards):
                content += "\n" + "-" * 50 + "\n\n"
        
        self.content_area.setPlainText(content)
    
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