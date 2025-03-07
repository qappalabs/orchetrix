from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QFont, QLinearGradient, QPainter, QColor, QPixmap
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QPushButton

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.setup_ui()
        self.old_pos = None

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0D1117;
                color: #ffffff;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(14)

        # Orchestrix logo on the left using the provided image
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(24, 24)

        # Use the image URL for the logo
        logo_url = "logos/Group 31.png"  # Replace with actual URL

        # For demonstration, let's load a local resource or use a fallback
        try:
            pixmap = QPixmap(logo_url)
            if pixmap.isNull():
                # Fallback to creating our own logo if URL loading fails
                pixmap = QPixmap(24, 24)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                # Create a gradient background similar to the OX logo
                gradient = QLinearGradient(0, 0, 24, 24)
                gradient.setColorAt(0, QColor("#FF8A00"))  # Top light orange
                gradient.setColorAt(1, QColor("#FF5722"))  # Bottom darker orange
                painter.setBrush(gradient)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(0, 0, 24, 24, 6, 6)  # Rounded rectangle for the logo background

                # Add the "Ox" text
                painter.setPen(QColor("black"))
                painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Ox")
                painter.end()
        except:
            # Fallback if any error occurs
            pixmap = QPixmap(24, 24)
            pixmap.fill(QColor("#FF5722"))

        # Scale the pixmap to fit our label size while preserving aspect ratio
        pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(pixmap)

        # Home icon
        self.home_btn = QToolButton()
        self.home_btn.setText("🏠")
        self.home_btn.setFixedSize(30, 30)
        self.home_btn.setStyleSheet("""
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

        # Navigation arrows
        self.back_btn = QToolButton()
        self.back_btn.setText("←")
        self.back_btn.setFixedSize(30, 30)
        self.back_btn.setStyleSheet("""
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

        self.forward_btn = QToolButton()
        self.forward_btn.setText("→")
        self.forward_btn.setFixedSize(30, 30)
        self.forward_btn.setStyleSheet("""
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

        # Settings and other icons on the right
        self.troubleshoot_btn = QToolButton()
        self.troubleshoot_btn.setText("❓")
        self.troubleshoot_btn.setFixedSize(30, 30)
        self.troubleshoot_btn.setStyleSheet("""
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

        self.notifications_btn = QToolButton()
        self.notifications_btn.setText("🔔")
        self.notifications_btn.setFixedSize(30, 30)
        self.notifications_btn.setStyleSheet("""
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

        self.profile_btn = QToolButton()
        self.profile_btn.setText("👤")
        self.profile_btn.setFixedSize(30, 30)
        self.profile_btn.setStyleSheet("""
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

        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙️")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.setStyleSheet("""
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

        # Window control buttons
        self.minimize_btn = QPushButton("─")
        self.minimize_btn.setFixedSize(30, 30)
        self.minimize_btn.clicked.connect(self.parent.showMinimized)
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)

        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setFixedSize(30, 30)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.maximize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.parent.close)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #E81123;
                border-radius: 4px;
            }
        """)

        # Add widgets to layout
        layout.addWidget(self.logo_label)
        layout.addWidget(self.home_btn)
        layout.addWidget(self.back_btn)
        layout.addWidget(self.forward_btn)
        layout.addStretch(1)
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
    
    def eventFilter(self, obj, event):
        # Handle double-click on titlebar to maximize
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggle_maximize()
            return True
        return super().eventFilter(obj, event)
    

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.maximize_btn.setText("□")
        else:
            self.parent.showMaximized()
            self.maximize_btn.setText("❐")

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
