from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen, QBrush, QConicalGradient
from UI.Styles import AppStyles
from UI.Icons import resource_path
import logging
import math
import os
import sys

class PulsatingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Rotation angle
        self.angle = 0

        # Pulsation variables
        self.pulse_phase = 0
        self.max_width = 10
        self.min_width = 4

        # Color definitions for gradient
        self.orange = QColor("#FF6D3F")
        self.yellow = QColor("#FFCD3A")
        self.orange_trans = QColor(self.orange)
        self.orange_trans.setAlpha(0)

        # Start rotation timer directly in constructor for reliability
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)  # ~60fps

    def update_animation(self):
        # Update rotation
        self.angle = (self.angle + 5) % 360

        # Update pulsation
        self.pulse_phase = (self.pulse_phase + 0.05) % (2 * math.pi)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Define center and radius
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) - 5

        # Calculate pulsating width
        pulse_factor = (math.sin(self.pulse_phase) + 1) / 2  # 0 to 1
        current_width = self.min_width + (self.max_width - self.min_width) * pulse_factor

        # Create conical gradient for the spinner
        gradient = QConicalGradient(center_x, center_y, self.angle)

        # Create a gradient with a visible "head" to make rotation more obvious
        gradient.setColorAt(0.0, self.yellow)  # Bright "head"
        gradient.setColorAt(0.1, self.orange)
        gradient.setColorAt(0.3, self.orange_trans)  # Fade out
        gradient.setColorAt(0.7, self.orange_trans)  # Stay transparent
        gradient.setColorAt(0.9, self.orange)  # Fade in
        gradient.setColorAt(1.0, self.yellow)  # Back to bright "head"

        # Create pen with the gradient
        pen = QPen()
        pen.setBrush(QBrush(gradient))
        pen.setWidth(int(current_width))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # Draw circular spinner
        painter.drawEllipse(
            int(center_x - radius),
            int(center_y - radius),
            int(radius * 2),
            int(radius * 2)
        )

        # Draw brightest point as a dot
        bright_x = center_x + radius * math.cos(math.radians(self.angle))
        bright_y = center_y + radius * math.sin(math.radians(self.angle))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.yellow))

        highlight_size = current_width * 0.8  # Slightly smaller than pen width
        painter.drawEllipse(
            QRectF(
                bright_x - highlight_size/2,
                bright_y - highlight_size/2,
                highlight_size,
                highlight_size
            )
        )

    def stop(self):
        if self.timer.isActive():
            self.timer.stop()


class SplashScreen(QWidget):
    # Signal to notify when loading is complete
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading")
        self.setFixedSize(700, 400)  # Size to match the image
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Counter for automatic closing
        self.counter = 0

        self.setup_ui()

    def setup_ui(self):
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Center container for content
        center_container = QWidget()
        center_container.setObjectName("center_container")
        center_container.setStyleSheet(AppStyles.SPLASH_CENTER_CONTAINER_STYLE)

        # Use a layout for content positioning
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)  # No margins to allow full-screen image
        center_layout.setSpacing(0)

        # Create background image container that will display the entire splash image
        self.bg_container = QLabel(center_container)
        self.bg_container.setObjectName("bg_container")
        self.bg_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bg_container.setFixedSize(680, 380)  # Make it fit the container

        try:
            # Load the splash screen image with resource_path
            splash_path = resource_path("Images/orchetrix_splash.png")
            bg_pixmap = QPixmap(splash_path)
            
            if not bg_pixmap.isNull():
                logging.debug("Successfully loaded splash screen image")
                self.bg_container.setPixmap(bg_pixmap.scaled(
                    self.bg_container.size(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                logging.debug("Failed to load splash screen image - pixmap is null")
                # Fallback to a static color if image isn't available
                self.bg_container.setStyleSheet(AppStyles.SPLASH_ANIMATION_FALLBACK_STYLE)
        except Exception as e:
            logging.debug(f"Error loading splash screen image: {e}")
            # Fallback to static color
            self.bg_container.setStyleSheet(AppStyles.SPLASH_ANIMATION_FALLBACK_STYLE)
        # Create and position the spinner
        self.spinner = PulsatingSpinner(self.bg_container)
        # Position at bottom center - adjust these values as needed
        self.spinner.move(300, 280)

        # Add center container to main layout
        center_layout.addWidget(self.bg_container)
        main_layout.addWidget(center_container)

        # Start a timer for auto-closing after some time
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.update_timer)
        self.close_timer.start(30)  # Update every 30ms for a total of about 3 seconds

    def update_timer(self):
        # Update counter
        self.counter += 1

        # When counter reaches 100, emit finished signal
        if self.counter >= 100:
            self.close_timer.stop()
            if hasattr(self, 'spinner'):
                self.spinner.stop()
            self.finished.emit()

    def paintEvent(self, event):
        # Add shadow effect to the widget
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw shadow
        painter.setBrush(QColor(20, 20, 20, 60))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(10, 10, self.width() - 20, self.height() - 20, 10, 10)

    def closeEvent(self, event):
        # Clean up resources when the window is closed
        if hasattr(self, 'spinner'):
            self.spinner.stop()
        super().closeEvent(event)