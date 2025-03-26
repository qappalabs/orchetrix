from PyQt6.QtCore import Qt, QPoint, QEvent, QSize
from PyQt6.QtGui import QFont, QLinearGradient, QPainter, QColor, QPixmap, QIcon, QPainterPath
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QPushButton

from UI.Styles import AppColors
from UI.Icons import Icons

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        
        # Define consistent icon sizes
        self.normal_icon_size = QSize(18, 18)      # Standard size for most icons
        self.logo_icon_size = QSize(24, 24)        # Size for the app logo
        self.window_ctrl_size = QSize(10, 10)      # Size for all window control icons
        self.maximized_icon_size = QSize(16, 16)   # Larger size ONLY for maximized state icon
        
        self.setup_ui()
        self.old_pos = None

    def setup_ui(self):
        # Add bottom border to titlebar
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.BG_DARKER};
                color: {AppColors.TEXT_LIGHT};
                border-bottom: 1px solid {AppColors.BORDER_COLOR};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(14)

        # Orchestrix logo on the left
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(self.logo_icon_size)

        # Try to load app logo from file first
        try:
            pixmap = QPixmap("icons/logoIcon.png")
            if not pixmap.isNull():
                self.logo_label.setPixmap(pixmap.scaled(self.logo_icon_size, Qt.AspectRatioMode.KeepAspectRatio, 
                                                     Qt.TransformationMode.SmoothTransformation))
            else:
                # Create a fallback logo
                self.create_fallback_logo()
        except Exception as e:
            print(f"Error loading logo: {e}")
            self.create_fallback_logo()

        # Home icon button
        self.home_btn = self.create_icon_button("home", "Home")
        self.home_btn.clicked.connect(self.navigate_to_home)

        # Navigation arrows
        self.back_btn = self.create_icon_button("back", "Back", self.create_back_icon())
        self.forward_btn = self.create_icon_button("forward", "Forward", self.create_forward_icon())

        # Settings and other icons on the right
        self.troubleshoot_btn = self.create_icon_button("help", "Help & Troubleshoot")
        self.notifications_btn = self.create_icon_button("notifications", "Notifications")
        self.profile_btn = self.create_icon_button("profile", "Profile")
        self.settings_btn = self.create_icon_button("preferences", "Settings")

        # All window control buttons with consistent size
        self.minimize_btn = self.create_window_button("minimize", "Minimize", 14, self.window_ctrl_size)
        self.minimize_btn.clicked.connect(self.parent.showMinimized)
        
        # Maximize button - same size as others but will use larger icon when maximized
        self.maximize_btn = self.create_window_button("maximize", "Maximize", 14, self.window_ctrl_size)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        
        self.close_btn = self.create_window_button("close", "Close", 14, self.window_ctrl_size)
        self.close_btn.clicked.connect(self.parent.close)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                font-size: 9px;
                min-width: 14px;
                min-height: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #E81123;
                color: white;
                border-radius: 2px;
            }
        """)

        # Add widgets to layout
        layout.addWidget(self.logo_label)
        layout.addWidget(self.home_btn)
        layout.addWidget(self.back_btn)
        layout.addWidget(self.forward_btn)
        layout.addStretch(1)
        layout.addWidget(self.troubleshoot_btn)
        layout.addWidget(self.notifications_btn)
        layout.addWidget(self.profile_btn)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)
        
        # Install event filter for double-click
        self.installEventFilter(self)
    
    def create_icon_button(self, icon_id, tooltip, fallback_icon=None):
        """Create a tool button with the specified icon and tooltip"""
        btn = QToolButton()
        btn.setFixedSize(30, 30)
        btn.setToolTip(tooltip)
        
        # Try to load icon from file
        icon = Icons.get_icon(icon_id)
        
        if not icon.isNull():
            # If icon loaded successfully, use it
            btn.setIcon(icon)
            btn.setIconSize(self.normal_icon_size)
            btn.setText("")
        elif fallback_icon is not None:
            # Use provided fallback icon if available
            btn.setIcon(fallback_icon)
            btn.setIconSize(self.normal_icon_size)
            btn.setText("")
        else:
            # Fallback to text/emoji if icon loading failed
            fallback_text = getattr(Icons, icon_id.upper(), "⚙️") if isinstance(icon_id, str) else "⚙️"
            btn.setText(fallback_text)
            
        btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 16px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        return btn
    
    def create_window_button(self, icon_id, tooltip, size=14, icon_size=None):
        """Create a small window control button with light color"""
        btn = QPushButton()
        btn.setFixedSize(size, size)
        btn.setToolTip(tooltip)
        
        if icon_size is None:
            icon_size = self.window_ctrl_size
            
        # Try to load icon from file
        icon = Icons.get_icon(icon_id)
        
        if not icon.isNull():
            # If icon loaded successfully, use it
            btn.setIcon(icon)
            btn.setIconSize(icon_size)
            btn.setText("")
        else:
            # Fallback to text/emoji if icon loading failed
            fallback_text = ""
            font_size = 9
            
            if icon_id == "minimize":
                fallback_text = "─"
            elif icon_id == "maximize":
                # Use normal square symbol for non-maximized state
                fallback_text = "□" if not self.parent or not self.parent.isMaximized() else "❐"
            elif icon_id == "close":
                fallback_text = "✕"
            else:
                fallback_text = getattr(Icons, icon_id.upper(), "⚙️") if isinstance(icon_id, str) else "⚙️"
                
            btn.setText(fallback_text)
            btn.setFont(QFont("Segoe UI", font_size))
            
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #888888;
                border: none;
                font-size: 9px;
                min-width: {size}px;
                min-height: {size}px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                border-radius: 2px;
            }}
        """)
        return btn
    
    def create_back_icon(self):
        """Create a back arrow icon"""
        size = self.normal_icon_size
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw back arrow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        
        # Create arrow path
        path = QPainterPath()
        path.moveTo(size.width() * 0.65, size.height() * 0.15)  # Top-right
        path.lineTo(size.width() * 0.35, size.height() * 0.5)   # Middle-left
        path.lineTo(size.width() * 0.65, size.height() * 0.85)  # Bottom-right
        path.lineTo(size.width() * 0.55, size.height() * 0.5)   # Middle point
        path.closeSubpath()
        
        painter.drawPath(path)
        painter.end()
        
        return QIcon(pixmap)

    def create_forward_icon(self):
        """Create a forward arrow icon"""
        size = self.normal_icon_size
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw forward arrow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        
        # Create arrow path
        path = QPainterPath()
        path.moveTo(size.width() * 0.35, size.height() * 0.15)  # Top-left
        path.lineTo(size.width() * 0.65, size.height() * 0.5)   # Middle-right
        path.lineTo(size.width() * 0.35, size.height() * 0.85)  # Bottom-left
        path.lineTo(size.width() * 0.45, size.height() * 0.5)   # Middle point
        path.closeSubpath()
        
        painter.drawPath(path)
        painter.end()
        
        return QIcon(pixmap)
    
    def create_fallback_logo(self):
        """Create a simple colored logo as fallback"""
        pixmap = QPixmap(self.logo_icon_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create gradient background
        gradient = QLinearGradient(0, 0, self.logo_icon_size.width(), self.logo_icon_size.height())
        gradient.setColorAt(0, QColor("#4A9EFF"))
        gradient.setColorAt(1, QColor("#0066CC"))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.logo_icon_size.width(), self.logo_icon_size.height(), 6, 6)
        
        # Add text
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Ox")
        painter.end()
        
        self.logo_label.setPixmap(pixmap)
    
    def navigate_to_home(self):
        """Navigate to the home page"""
        if hasattr(self.parent, 'switch_to_home'):
            self.parent.switch_to_home()
    
    def eventFilter(self, obj, event):
        # Handle double-click on titlebar to maximize
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggle_maximize()
            return True
        return super().eventFilter(obj, event)
    
    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            
            # Update maximize button icon when restored
            icon = Icons.get_icon("maximize")
            if not icon.isNull():
                self.maximize_btn.setIcon(icon)
                self.maximize_btn.setIconSize(self.window_ctrl_size)  # Normal size
                self.maximize_btn.setText("")
            else:
                self.maximize_btn.setText("□")  # Square symbol for maximize
                self.maximize_btn.setFont(QFont("Segoe UI", 9))  # Normal font size
        else:
            self.parent.showMaximized()
            
            # Update maximize button icon when maximized - use larger icon size
            icon = Icons.get_icon("maximize_active")
            if not icon.isNull():
                self.maximize_btn.setIcon(icon)
                self.maximize_btn.setIconSize(self.maximized_icon_size)  # Larger size
                self.maximize_btn.setText("")
            else:
                self.maximize_btn.setText("❐")  # Overlapping squares symbol for restore
                self.maximize_btn.setFont(QFont("Segoe UI", 11))  # Larger font size for text

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.parent.move(self.parent.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None