from PyQt6.QtCore import Qt, QPoint, QEvent, QSize
from PyQt6.QtGui import QFont, QLinearGradient, QPainter, QColor, QPixmap, QIcon, QPainterPath, QCursor
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QPushButton, QFrame

from UI.Styles import AppColors, AppStyles
from UI.Icons import Icons

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)

        # Define consistent icon sizes
        self.normal_icon_size = QSize(18, 18)      # Standard size for most icons
        self.logo_icon_size = QSize(24, 24)        # Size for the app logo
        self.window_ctrl_size = QSize(18, 18)      # MODIFIED: Increased to match normal icon size
        self.maximized_icon_size = QSize(18, 18)   # MODIFIED: Made consistent with other icons

        self.setup_ui()
        self.old_pos = None

    def setup_ui(self):
        # Apply title bar style from Styles.py
        self.setStyleSheet(AppStyles.TITLE_BAR_STYLE)

        # Create a container widget with vertical layout
        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Create the main content widget
        content = QWidget()
        layout = QHBoxLayout(content)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(14)

        # Orchetrix logo on the left
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

        # Settings and other icons on the right
        self.troubleshoot_btn = self.create_icon_button("help", "Help & Troubleshoot")
        self.notifications_btn = self.create_icon_button("notifications", "Notifications")
        self.profile_btn = self.create_icon_button("profile", "Profile")
        self.profile_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))  # Set pointing hand cursor for profile button
        self.settings_btn = self.create_icon_button("preferences", "Settings")

        # Window control buttons
        self.minimize_btn = self.create_window_control_button("minimize", "Minimize")
        self.minimize_btn.clicked.connect(self.parent.showMinimized)

        self.maximize_btn = self.create_window_control_button("maximize", "Maximize")
        self.maximize_btn.clicked.connect(self.toggle_maximize)

        self.close_btn = self.create_window_control_button("close", "Close")
        self.close_btn.clicked.connect(self.parent.close)
        self.close_btn.setStyleSheet(AppStyles.TITLE_BAR_CLOSE_BUTTON_STYLE)

        # Add widgets to layout
        layout.addWidget(self.logo_label)
        layout.addWidget(self.home_btn)
        layout.addStretch(1)
        layout.addWidget(self.troubleshoot_btn)
        layout.addWidget(self.notifications_btn)
        layout.addWidget(self.profile_btn)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)

        # Add the content to the container
        container_layout.addWidget(content)

        # Create a frame for the bottom border
        bottom_frame = QFrame()
        bottom_frame.setFixedHeight(2)  # You can adjust the height as needed
        bottom_frame.setStyleSheet(f"background-color: {AppColors.BORDER_COLOR};")  # Use accent color
        container_layout.addWidget(bottom_frame)

        # Set up the main layout for this widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(container)

        # Install event filter for double-click
        self.installEventFilter(self)

    def create_icon_button(self, icon_id, tooltip, fallback_icon=None):
        """Create a tool button with the specified icon and tooltip"""
        btn = QToolButton()
        btn.setFixedSize(30, 30)
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))  # Set pointing hand cursor for all icon buttons

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

        btn.setStyleSheet(AppStyles.TITLE_BAR_ICON_BUTTON_STYLE)
        return btn

    def create_window_control_button(self, icon_id, tooltip):
        """Create a window control button with minimal style"""
        btn = QToolButton()
        btn.setFixedSize(46, 30)  # Width is larger than height to match the style in your image
        btn.setToolTip(tooltip)

        # Try to load icon from file
        icon = Icons.get_icon(icon_id)

        if not icon.isNull():
            # If icon loaded successfully, use it
            btn.setIcon(icon)
            btn.setIconSize(QSize(10, 10))  # Smaller icon size for minimal look
            btn.setText("")
        else:
            # Fallback to text/emoji if icon loading failed
            fallback_text = ""
            font_size = 9  # Smaller font size

            if icon_id == "minimize":
                fallback_text = "—"  # Em dash for minimize
            elif icon_id == "maximize":
                # Use normal square symbol for non-maximized state
                fallback_text = "□" if not self.parent or not self.parent.isMaximized() else "❐"
            elif icon_id == "close":
                fallback_text = "✕"  # X symbol for close
            else:
                fallback_text = getattr(Icons, icon_id.upper(), "⚙️") if isinstance(icon_id, str) else "⚙️"

            btn.setText(fallback_text)
            btn.setFont(QFont("Segoe UI", font_size))

        if icon_id == "close":
            btn.setStyleSheet(AppStyles.TITLE_BAR_CLOSE_BUTTON_STYLE)
        else:
            btn.setStyleSheet(AppStyles.TITLE_BAR_WINDOW_BUTTON_STYLE)

        return btn

    # Original create_window_button method is kept but not used anymore
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

        btn.setStyleSheet(AppStyles.TITLE_BAR_WINDOW_BUTTON_STYLE)
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
                self.maximize_btn.setIconSize(QSize(10, 10))  # Same small size as initial creation
                self.maximize_btn.setText("")
            else:
                # Use square symbol (□) for maximize
                self.maximize_btn.setText("□")
                self.maximize_btn.setFont(QFont("Segoe UI", 9))
            # Make sure the correct style is applied
            self.maximize_btn.setStyleSheet(AppStyles.TITLE_BAR_WINDOW_BUTTON_STYLE)
        else:
            self.parent.showMaximized()

            # Update maximize button icon when maximized - show "restore down" icon
            icon = Icons.get_icon("maximize_active")  # If you have this icon
            if not icon.isNull():
                self.maximize_btn.setIcon(icon)
                self.maximize_btn.setIconSize(self.window_ctrl_size)
                self.maximize_btn.setText("")
            else:
                # Use overlapping squares symbol (⧉) for restore down
                # Alternative symbols: ❐ or ⧉
                self.maximize_btn.setText("⧉")  # This is a better symbol for the restore icon
                self.maximize_btn.setFont(QFont("Segoe UI", 9))
            # Make sure the correct style is applied
            self.maximize_btn.setStyleSheet(AppStyles.TITLE_BAR_WINDOW_BUTTON_STYLE)

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