from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFrame, QScrollArea, QSizePolicy, QGridLayout)
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QCursor

from UI.Styles import AppColors, AppStyles

class ProfileScreen(QWidget):
    """
    A slide-in profile screen that displays user information and account settings.
    Appears from the right side of the main window.
    """
    closed = pyqtSignal()  # Signal emitted when profile screen is closed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.is_visible = False
        self.setFixedWidth(350)  # Width of the profile panel
        self.setup_ui()

        # Set initial position off-screen
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def setup_ui(self):
        """Initialize the UI components"""
        # Use the actual styles from AppColors and AppStyles
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.BG_SIDEBAR};
                color: {AppColors.TEXT_LIGHT};
                font-family: 'Segoe UI';
                font-size: 10pt;
            }}
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
            }}
            QPushButton {{
                background-color: {AppColors.ACCENT_BLUE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3A8EDF;
            }}
            QPushButton:pressed {{
                background-color: #0066CC;
            }}
            QFrame#separator {{
                background-color: {AppColors.BORDER_COLOR};
            }}
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with close button
        header_widget = QWidget()
        header_widget.setFixedHeight(40)
        header_widget.setStyleSheet(f"background-color: {AppColors.BG_HEADER};")

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 0, 15, 0)

        title_label = QLabel("Profile")
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {AppColors.TEXT_LIGHT};
                font-size: 14pt;
                border-radius: 15px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {AppColors.HOVER_BG};
            }}
        """)
        close_btn.clicked.connect(self.hide_profile)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        # Add header to main layout
        main_layout.addWidget(header_widget)

        # Create a scroll area for the content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Create content widget that will be inside scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # User Information Section
        content_layout.addWidget(self.create_section_label("User Information"))

        # Profile picture and name container
        profile_container = QWidget()
        profile_layout = QHBoxLayout(profile_container)
        profile_layout.setContentsMargins(0, 10, 0, 10)

        # Profile picture (avatar)
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(80, 80)
        self.set_default_avatar()
        profile_layout.addWidget(self.avatar_label)

        # Name and info container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(10, 0, 0, 0)
        info_layout.setSpacing(5)

        self.full_name_label = QLabel("John Doe")
        self.full_name_label.setStyleSheet("font-size: 16pt; font-weight: bold;")

        self.username_label = QLabel("@johndoe")
        self.username_label.setStyleSheet(f"font-size: 11pt; color: {AppColors.TEXT_SECONDARY};")

        self.email_label = QLabel("john.doe@example.com")
        self.email_label.setStyleSheet("font-size: 10pt;")

        info_layout.addWidget(self.full_name_label)
        info_layout.addWidget(self.username_label)
        info_layout.addWidget(self.email_label)
        info_layout.addStretch()

        profile_layout.addWidget(info_container)
        profile_layout.addStretch()

        content_layout.addWidget(profile_container)

        # Organization info
        org_container = QWidget()
        org_layout = QGridLayout(org_container)
        org_layout.setContentsMargins(0, 0, 0, 0)
        org_layout.setSpacing(10)

        org_layout.addWidget(QLabel("Organization:"), 0, 0)
        self.org_value = QLabel("Acme Corp")
        org_layout.addWidget(self.org_value, 0, 1)

        org_layout.addWidget(QLabel("Team:"), 1, 0)
        self.team_value = QLabel("DevOps")
        org_layout.addWidget(self.team_value, 1, 1)

        org_layout.addWidget(QLabel("Role:"), 2, 0)
        self.role_value = QLabel("Administrator")
        self.role_value.setStyleSheet("font-weight: bold;")
        org_layout.addWidget(self.role_value, 2, 1)

        content_layout.addWidget(org_container)

        # Separator
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        content_layout.addWidget(separator)

        # Account Security Section
        content_layout.addWidget(self.create_section_label("Account Security"))

        # Change Password Button
        change_pwd_btn = QPushButton("Change Password")
        change_pwd_btn.setFixedHeight(36)
        change_pwd_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Custom style with #FF6D3F color
        change_pwd_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF6D3F;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FF8659;  /* Lighter version for hover */
            }}
            QPushButton:pressed {{
                background-color: #E55A2C;  /* Darker version for pressed state */
            }}
        """)

        content_layout.addWidget(change_pwd_btn)

        # Login History
        content_layout.addWidget(QLabel("Login History"))

        login_history = QWidget()
        login_layout = QVBoxLayout(login_history)
        login_layout.setContentsMargins(0, 5, 0, 5)
        login_layout.setSpacing(8)

        # Add some login history entries
        login_entries = [
            {"time": "Today, 09:45 AM", "ip": "192.168.1.1", "device": "Chrome / Windows"},
            {"time": "Yesterday, 06:30 PM", "ip": "192.168.1.1", "device": "Firefox / MacOS"},
            {"time": "Apr 10, 2025, 11:22 AM", "ip": "10.0.0.15", "device": "Edge / Windows"}
        ]

        for entry in login_entries:
            entry_widget = self.create_login_entry(entry["time"], entry["ip"], entry["device"])
            login_layout.addWidget(entry_widget)

        content_layout.addWidget(login_history)

        # Add some space at the bottom
        content_layout.addStretch()

        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def create_section_label(self, text):
        """Create a section header label"""
        label = QLabel(text)
        label.setStyleSheet(AppStyles.SUBSECTION_HEADER_STYLE.replace("#sectionHeader", ""))
        return label

    def create_login_entry(self, time, ip, device):
        """Create a login history entry widget"""
        entry = QWidget()
        entry.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.BG_MEDIUM};
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(entry)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(3)

        time_label = QLabel(time)
        time_label.setStyleSheet("font-weight: bold;")

        details_label = QLabel(f"{device} • {ip}")
        details_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY};")

        layout.addWidget(time_label)
        layout.addWidget(details_label)

        return entry

    def set_default_avatar(self):
        """Set a default avatar if no profile picture is available"""
        # Create a colored circle with initials
        pixmap = QPixmap(80, 80)
        pixmap.fill(Qt.GlobalColor.transparent)

        from PyQt6.QtGui import QPainter, QBrush, QPen, QFont
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw circle with gradient
        from PyQt6.QtGui import QLinearGradient
        gradient = QLinearGradient(0, 0, 0, 80)
        gradient.setColorAt(0, QColor(74, 158, 255))  # Light blue
        gradient.setColorAt(1, QColor(0, 102, 204))   # Dark blue

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 80, 80)

        # Draw initials
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI", 24)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "JD")

        painter.end()
        self.avatar_label.setPixmap(pixmap)
        self.avatar_label.setScaledContents(True)

    def set_user_info(self, name, username, email, organization="", team="", role=""):
        """Set user information to display"""
        self.full_name_label.setText(name)
        self.username_label.setText(f"@{username}")
        self.email_label.setText(email)
        self.org_value.setText(organization)
        self.team_value.setText(team)
        self.role_value.setText(role)

        # Generate initials for avatar
        initials = ""
        if name:
            parts = name.split()
            if len(parts) >= 2:
                initials = parts[0][0] + parts[-1][0]
            else:
                initials = parts[0][0:2]

        # Update avatar with new initials if needed
        # For simplicity, we'll just keep the default avatar

    def show_profile(self):
        """Show the profile panel with animation"""
        if self.is_visible:
            return

        self.is_visible = True
        self.show()

        # Position at the right edge of the parent
        parent_width = self.parent.width() if self.parent else self.width() + 50
        self.setGeometry(parent_width, 0, self.width(), self.parent.height() if self.parent else 700)

        # Create animation - FIXED: Use QRect instead of QSize
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(QRect(parent_width - self.width(), 0, self.width(), self.parent.height()))
        self.anim.start()

    def hide_profile(self):
        """Hide the profile panel with animation"""
        if not self.is_visible:
            return

        self.is_visible = False

        # Create animation - FIXED: Use QRect instead of QSize
        parent_width = self.parent.width() if self.parent else self.width() + 50
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(QRect(parent_width, 0, self.width(), self.parent.height()))
        self.anim.finished.connect(self._on_hide_finished)
        self.anim.start()

    def _on_hide_finished(self):
        """Called when the hide animation finishes"""
        self.hide()
        self.closed.emit()

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if self.parent and self.is_visible:
            # Maintain position at the right edge with correct height
            self.setGeometry(self.parent.width() - self.width(), 0, self.width(), self.parent.height())