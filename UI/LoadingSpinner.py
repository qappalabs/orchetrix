"""
Lightweight Loading Spinner Component for all pages
Google-style loading animation with smooth performance
"""

import math
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import QTimer, QPropertyAnimation, QRect, pyqtProperty, Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from UI.Styles import AppColors


class CircularSpinner(QWidget):
    """Lightweight circular spinner similar to Google's loading animation"""

    def __init__(self, size=32, color=None, parent=None):
        super().__init__(parent)
        self.size = size
        self.color = QColor(color) if color else QColor(AppColors.ACCENT_ORANGE)
        self.angle = 0
        self.setFixedSize(size, size)

        # Animation timer - optimized for smooth 60fps
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_rotation)
        self.timer.setInterval(16)  # ~60fps for smooth animation

    def start_animation(self):
        """Start the spinning animation"""
        self.timer.start()

    def stop_animation(self):
        """Stop the spinning animation"""
        self.timer.stop()

    def update_rotation(self):
        """Update rotation angle for smooth animation"""
        self.angle = (self.angle + 8) % 360  # 8 degrees per frame for smooth rotation
        self.update()

    def paintEvent(self, event):
        """Paint the circular spinner"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Center the spinner
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 2

        # Create gradient pen for modern look
        pen = QPen(self.color)
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        # Draw arc with rotating effect
        painter.setPen(pen)

        # Draw multiple arcs with different opacities for gradient effect
        for i in range(8):
            opacity = 1.0 - (i * 0.1)
            if opacity <= 0:
                break

            color = QColor(self.color)
            color.setAlphaF(opacity)
            pen.setColor(color)
            painter.setPen(pen)

            start_angle = self.angle + (i * 45)
            span_angle = 45

            rect = QRect(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.drawArc(rect, start_angle * 16, span_angle * 16)


class PulsingDots(QWidget):
    """Three pulsing dots loading animation (alternative style)"""

    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self.color = QColor(color) if color else QColor(AppColors.ACCENT_ORANGE)
        self.setFixedSize(60, 20)

        self.phase = 0

        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_phase)
        self.timer.setInterval(100)  # 100ms for smooth pulsing

    def start_animation(self):
        """Start the pulsing animation"""
        self.timer.start()

    def stop_animation(self):
        """Stop the pulsing animation"""
        self.timer.stop()

    def update_phase(self):
        """Update animation phase"""
        self.phase = (self.phase + 1) % 30  # 3 second cycle
        self.update()

    def paintEvent(self, event):
        """Paint the pulsing dots"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw three dots with pulsing effect
        dot_radius = 4
        spacing = 15
        y = self.height() // 2

        for i in range(3):
            x = spacing + (i * spacing)

            # Calculate pulsing effect with phase offset
            pulse_phase = (self.phase + i * 10) % 30
            scale = 1.0 + 0.3 * math.sin(pulse_phase * math.pi / 15)
            opacity = 0.3 + 0.7 * math.sin(pulse_phase * math.pi / 15)

            color = QColor(self.color)
            color.setAlphaF(opacity)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)

            radius = dot_radius * scale
            painter.drawEllipse(int(x - radius), int(y - radius), int(radius * 2), int(radius * 2))


class GoogleStyleSpinner(QWidget):
    """Google-style multicolor spinner"""

    def __init__(self, size=32, parent=None):
        super().__init__(parent)
        self.size = size
        self.setFixedSize(size, size)

        # White color only with different opacities for Google-style effect
        white = QColor("#ffffff")
        self.colors = [
            QColor(white.red(), white.green(), white.blue(), 255),  # Full opacity
            QColor(white.red(), white.green(), white.blue(), 200),  # 80% opacity
            QColor(white.red(), white.green(), white.blue(), 150),  # 60% opacity
            QColor(white.red(), white.green(), white.blue(), 100),  # 40% opacity
        ]

        self.angle = 0

        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_rotation)
        self.timer.setInterval(20)  # 50fps for smooth animation

    def start_animation(self):
        """Start the spinning animation"""
        self.timer.start()

    def stop_animation(self):
        """Stop the spinning animation"""
        self.timer.stop()

    def update_rotation(self):
        """Update rotation angle"""
        self.angle = (self.angle + 6) % 360  # 6 degrees per frame
        self.update()

    def paintEvent(self, event):
        """Paint the Google-style spinner"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 3

        # Draw four colored arcs
        arc_span = 60  # Each arc spans 60 degrees
        gap = 30      # 30 degree gap between arcs

        for i, color in enumerate(self.colors):
            pen = QPen(color)
            pen.setWidth(3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            start_angle = (self.angle + i * (arc_span + gap)) % 360

            rect = QRect(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.drawArc(rect, start_angle * 16, arc_span * 16)


class LoadingOverlay(QWidget):
    """Full page loading overlay with spinner and message"""

    def __init__(self, message="Loading...", spinner_type="circular", parent=None):
        super().__init__(parent)
        self.setObjectName("LoadingOverlay")

        # Semi-transparent background
        self.setStyleSheet(f"""
            QWidget#LoadingOverlay {{
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
            }}
        """)

        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Create spinner based on type
        spinner_container = QHBoxLayout()
        spinner_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if spinner_type == "circular":
            self.spinner = CircularSpinner(40, AppColors.ACCENT_ORANGE)
        elif spinner_type == "dots":
            self.spinner = PulsingDots(AppColors.ACCENT_ORANGE)
        elif spinner_type == "google":
            self.spinner = GoogleStyleSpinner(40)
        else:
            self.spinner = CircularSpinner(40, AppColors.ACCENT_ORANGE)

        spinner_container.addWidget(self.spinner)
        layout.addLayout(spinner_container)

        # Loading message
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
                font-size: 14px;
                font-weight: 500;
                background-color: transparent;
                margin: 8px;
            }}
        """)
        layout.addWidget(self.message_label)

        self.hide()

    def show_loading(self, message=None):
        """Show the loading overlay with optional message"""
        if message:
            self.message_label.setText(message)

        self.spinner.start_animation()
        self.show()

    def hide_loading(self):
        """Hide the loading overlay"""
        self.spinner.stop_animation()
        self.hide()

    def set_message(self, message):
        """Update the loading message"""
        self.message_label.setText(message)


class CompactSpinner(QWidget):
    """Compact spinner for inline use in tables/cards"""

    def __init__(self, size=16, color=None, parent=None):
        super().__init__(parent)
        self.size = size
        self.color = QColor(color) if color else QColor(AppColors.TEXT_SECONDARY)
        self.setFixedSize(size, size)

        self.angle = 0

        # Lightweight timer for small spinner
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_rotation)
        self.timer.setInterval(50)  # 20fps for compact spinner

    def start_animation(self):
        """Start the spinning animation"""
        self.timer.start()

    def stop_animation(self):
        """Stop the spinning animation"""
        self.timer.stop()

    def update_rotation(self):
        """Update rotation angle"""
        self.angle = (self.angle + 15) % 360  # 15 degrees per frame
        self.update()

    def paintEvent(self, event):
        """Paint the compact spinner"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 1

        # Simple rotating arc
        pen = QPen(self.color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        rect = QRect(center_x - radius, center_y - radius, radius * 2, radius * 2)
        painter.drawArc(rect, self.angle * 16, 120 * 16)  # 120 degree arc


# Convenience functions for easy use
def create_loading_overlay(parent, message="Loading...", spinner_type="circular"):
    """Create and return a loading overlay widget"""
    overlay = LoadingOverlay(message, spinner_type, parent)
    return overlay

def create_compact_spinner(parent, size=16, color=None):
    """Create and return a compact spinner widget"""
    spinner = CompactSpinner(size, color, parent)
    return spinner

def create_circular_spinner(parent, size=32, color=None):
    """Create and return a circular spinner widget"""
    spinner = CircularSpinner(size, color, parent)
    return spinner