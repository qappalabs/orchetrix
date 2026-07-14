from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPointF, pyqtProperty, QVariantAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen, QBrush, QConicalGradient, QFont, QLinearGradient, QRadialGradient
from UI.Styles import AppStyles
from UI.Icons import resource_path
from UI.ThemeAwarePage import ThemeAwareMixin
import logging
import math


class SplashScreenConstants:
    """Constants for splash screen styling - brand colors that remain consistent across themes"""

    # Brand colors for spinner - these are intentionally fixed for brand consistency
    _BRAND_ORANGE = "#D0D4D8"  # Silver-white for spinner ring trail
    _BRAND_YELLOW = "#FFFFFF"  # Pure white for bright head dot
    _SHADOW_COLOR = (20, 20, 20, 60)  # RGBA tuple for shadow

    @staticmethod
    def get_brand_orange():
        """Get brand orange color - fixed for brand consistency"""
        return SplashScreenConstants._BRAND_ORANGE

    @staticmethod
    def get_brand_yellow():
        """Get brand yellow color - fixed for brand consistency"""
        return SplashScreenConstants._BRAND_YELLOW

    @staticmethod
    def get_shadow_color():
        """Get shadow color for splash screen as QColor"""
        r, g, b, a = SplashScreenConstants._SHADOW_COLOR
        return QColor(r, g, b, a)


class RollingTextWidget(QWidget):
    """Text widget with rolling animation and dots"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_text = ""
        self.old_text = ""
        self.progress = 1.0
        
        # Use Roboto Bold as requested by the user for a consistent modern brand look
        self.font = QFont("Roboto")
        self.font.setFamilies(["Roboto", "Segoe UI", "Arial", "sans-serif"])
        self.font.setPointSize(13)
        self.font.setWeight(QFont.Weight.Bold)
        
        self.font.setBold(True) # Explicitly set bold for maximum compatibility
        
        self.dot_count = 3

        # Animation for rolling transition
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._on_anim_value_changed)
        
    def _on_anim_value_changed(self, value):
        self.progress = float(value)
        self.update()
        
    def set_text(self, text):
        if self.base_text == text:
            return
            
        dots = "..."
        self.old_text = f"{self.base_text}{dots}" if self.base_text else ""
        self.base_text = text
        
        if not self.old_text:
            self.progress = 1.0
            self.update()
            return
            
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
        
    def stop_animation(self):
        self.anim.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Clip region so text doesn't draw outside the widget when animating
        painter.setClipRect(0, 0, int(w), int(h))
        
        painter.setFont(self.font)
        
        dots = "..." if self.dot_count > 0 else ""
        current_display = f"{self.base_text}{dots}"
        
        # Helper to draw text with a subtle drop shadow
        def draw_text_shadowed(text, rect, opacity):
            # Draw shadow first
            painter.setOpacity(opacity * 0.5)
            painter.setPen(QColor(0, 0, 0, 150))
            shadow_rect = rect.translated(1, 1)
            painter.drawText(shadow_rect, Qt.AlignmentFlag.AlignCenter, text)
            
            # Draw actual text
            painter.setOpacity(opacity)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        
        # Animate Old Text (slides down and fades out)
        if self.progress < 1.0 and self.old_text:
            y_offset = (self.progress * (h * 0.7))
            opacity = 1.0 - self.progress
            rect = QRectF(0, y_offset, w, h)
            draw_text_shadowed(self.old_text, rect, opacity)
            
        # Draw New/Current Text (slides in from top and fades in)
        opacity = self.progress
        y_offset = ((self.progress - 1.0) * (h * 0.7))
        rect = QRectF(0, y_offset, w, h)
        draw_text_shadowed(current_display, rect, opacity)

class DotLoadingWidget(QWidget):
    """Realistic white glowing dot animation.
    
    Three dots orbit in a 3-axis figure-8 knot. Each dot is rendered as a
    luminous 3D sphere: soft outer bloom halo, radial gradient core with a 
    specular highlight, and a subtle depth shadow. When dots come close, they
    emit a proximity burst — all in pure white/grey tones.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0.0
        self.dot_size = 12  # Slightly increased as requested
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(6000)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setLoopCount(-1)
        self.anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.anim.valueChanged.connect(self._on_anim_value_changed)
        self.anim.start()

    def _on_anim_value_changed(self, value):
        self.progress = float(value)
        self.update()

    def stop_animation(self):
        self.anim.stop()

    def _dot_positions(self):
        """Return (x, y, depth) for each dot, depth in [0, 1]."""
        cx, cy = self.width() / 2, self.height() / 2
        t = self.progress
        max_r    = 35   # Wider orbit — clear separation between dots at all times
        wiggle_w = 13   # Slight width for the figure-8 shape
        axes = [-math.pi / 2, math.pi / 6, 5 * math.pi / 6]
        result = []
        for i in range(3):
            theta = (t * 2 * math.pi * 3) + (i * 2 * math.pi / 3)
            u = max_r    * math.cos(theta)
            v = wiggle_w * math.sin(2 * theta)
            alpha = axes[i]
            dx = u * math.cos(alpha) - v * math.sin(alpha)
            dy = u * math.sin(alpha) + v * math.cos(alpha)
            depth = (dy + max_r) / (2 * max_r)   # 0 = far, 1 = close/front
            result.append((cx + dx, cy + dy, depth))
        return result

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        positions = self._dot_positions()

        # Proximity detection
        threshold = self.dot_size * 3.5
        proximity = {}
        for i in range(3):
            for j in range(i + 1, 3):
                dist = math.hypot(positions[i][0] - positions[j][0],
                                  positions[i][1] - positions[j][1])
                proximity[(i, j)] = max(0.0, 1.0 - dist / threshold)

        # ── Global size factor — computed ONCE and shared by ALL dots ─────────
        # Average closeness across all 3 pairs gives how "clustered" the group is.
        # When all 3 converge → global_close ≈ 1.0 → dots are largest.
        # When all 3 are spread → global_close ≈ 0.0 → dots are smallest.
        avg_close = sum(proximity.values()) / max(len(proximity), 1)
        global_radius = (self.dot_size / 2) * (0.92 + 0.45 * avg_close)

        # Sort back-to-front (lower depth drawn first so front dots overlap)
        order = sorted(range(3), key=lambda i: positions[i][2])

        for i in order:
            px, py, depth = positions[i]

            # ALL dots use the exact same radius — perfect size sync guaranteed
            radius  = global_radius
            opacity = 0.80 + 0.20 * depth   # subtle depth cue via opacity only

            # ── 1. Tight inner glow (stays close to sphere surface) ──────────
            glow_r = radius * 1.8
            glow   = QRadialGradient(QPointF(px, py), glow_r)
            glow_alpha = int(90 * opacity)
            glow.setColorAt(0.0, QColor(255, 255, 255, glow_alpha))
            glow.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setOpacity(1.0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPointF(px, py), glow_r, glow_r)

            # ── 2. 3D sphere core — large and bold ───────────────────────────
            highlight_x = px - radius * 0.28
            highlight_y = py - radius * 0.28
            core = QRadialGradient(QPointF(highlight_x, highlight_y), radius * 1.3)
            core.setColorAt(0.00, QColor(255, 255, 255, int(255 * opacity)))      # bright top
            core.setColorAt(0.35, QColor(225, 225, 228, int(250 * opacity)))      # mid body
            core.setColorAt(0.70, QColor(175, 175, 182, int(220 * opacity)))      # shadow curve
            core.setColorAt(1.00, QColor(120, 120, 130, int(180 * opacity)))      # dark rim
            painter.setBrush(QBrush(core))
            painter.setOpacity(1.0)
            painter.drawEllipse(QPointF(px, py), radius, radius)

            # ── 3. Specular pinpoint highlight ────────────────────────────────
            spec_r = radius * 0.32
            spec_x = px - radius * 0.26
            spec_y = py - radius * 0.26
            spec = QRadialGradient(QPointF(spec_x, spec_y), spec_r)
            spec.setColorAt(0.0, QColor(255, 255, 255, int(220 * opacity)))
            spec.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(spec))
            painter.drawEllipse(QPointF(spec_x, spec_y), spec_r, spec_r)



class SplashScreen(QWidget, ThemeAwareMixin):
    # Signal to notify when loading is complete
    finished = pyqtSignal()
    loading_finished = pyqtSignal()  # Alias used by main.py for splash-to-window handshake

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading")
        self.setFixedSize(700, 400)  # Size to match the image
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Counter for automatic closing
        self.counter = 0
        
        # Loading messages
        self.loading_messages = [
            "Initializing Orchetrix IDE",
            "Connecting to cluster",
            "Loading configurations",
            "Fetching node data",
            "Syncing resources",
            "Preparing workspace"
        ]
        self.current_message_index = 0

        self.setup_ui()

    def _on_theme_changed(self, theme_name):
        """Handle theme changes - splash screen maintains brand consistency"""
        super()._on_theme_changed(theme_name)
        # Splash screen uses mostly fixed brand colors and AppStyles
        # The background image and brand colors remain consistent across themes

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
        center_layout.setContentsMargins(
            0, 0, 0, 0
        )  # No margins to allow full-screen image
        center_layout.setSpacing(0)

        # Create background image container that will display the entire splash image
        self.bg_container = QLabel(center_container)
        self.bg_container.setObjectName("bg_container")
        self.bg_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bg_container.setFixedSize(680, 380)  # Make it fit the container

        try:
            # Load the splash screen image with resource_path
            splash_path = resource_path("Images/Orchetrix_splash.png")
            bg_pixmap = QPixmap(splash_path)

            if not bg_pixmap.isNull():
                logging.debug("Successfully loaded splash screen image")
                self.bg_container.setPixmap(
                    bg_pixmap.scaled(
                        self.bg_container.size(),
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                logging.debug("Failed to load splash screen image - pixmap is null")
                # Fallback to a static color if image isn't available
                self.bg_container.setStyleSheet(
                    AppStyles.SPLASH_ANIMATION_FALLBACK_STYLE
                )
        except Exception as e:
            logging.debug(f"Error loading splash screen image: {e}")
            # Fallback to static color
            self.bg_container.setStyleSheet(AppStyles.SPLASH_ANIMATION_FALLBACK_STYLE)
        # Create and position the dot-based loading animation
        self.dot_animation = DotLoadingWidget(self.bg_container)
        self.dot_animation.setFixedSize(80, 80)
        self.dot_animation.move(int((680 - 80) / 2), 230) # Positioned below brand name, above status

        # Create and position the rolling text-based loading widget
        self.loading_label = RollingTextWidget(self.bg_container)
        
        # Initial text setup
        self.loading_label.set_text(self.loading_messages[0])
        
        # Position at bottom center
        w_p, h_p = 450, 50
        self.loading_label.setFixedSize(w_p, h_p)
        self.loading_label.move(int((680 - w_p) / 2), 310)  # Centered horizontally, near bottom

        # Add center container to main layout
        center_layout.addWidget(self.bg_container)
        main_layout.addWidget(center_container)

        # Start a timer for auto-closing after some time
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.update_timer)
        self.close_timer.start(30)  # Update every 30ms for a total of about 3 seconds

    def start_loading_simulation(self, duration_ms=3000):
        """Start loading simulation with specified duration.
        
        Called by main.py to initiate the timed splash screen sequence.
        Resets and reconfigures the close timer for the requested duration.
        """
        # Reset counter and recalculate interval for requested duration
        self.counter = 0
        interval = max(16, duration_ms // 100)  # 100 steps, min 16ms
        if hasattr(self, 'close_timer') and self.close_timer.isActive():
            self.close_timer.stop()
        self.close_timer.start(interval)

    def update_timer(self):
        # Update counter
        self.counter += 1

        # Calculate which message to show based on progress (0 to 100)
        if self.counter < 100:
            total_messages = len(self.loading_messages)
            new_index = min(int((self.counter / 100) * total_messages), total_messages - 1)
            if new_index != self.current_message_index:
                self.current_message_index = new_index
                if hasattr(self, "loading_label"):
                    self.loading_label.set_text(self.loading_messages[self.current_message_index])

        # When counter reaches 100, emit finished signals
        if self.counter >= 100:
            self.close_timer.stop()
            if hasattr(self, "loading_label"):
                self.loading_label.stop_animation()
                self.loading_label.base_text = "Ready!"
                self.loading_label.dot_count = 0
                self.loading_label.update()
            if hasattr(self, "dot_animation"):
                self.dot_animation.stop_animation()
            self.finished.emit()
            self.loading_finished.emit()

    def paintEvent(self, event):
        # Add shadow effect to the widget
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw shadow using centralized color constant
        shadow_color = SplashScreenConstants.get_shadow_color()
        painter.setBrush(shadow_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(10, 10, self.width() - 20, self.height() - 20, 10, 10)

    def closeEvent(self, event):
        # Clean up resources when the window is closed
        if hasattr(self, "loading_label"):
            self.loading_label.stop_animation()
        if hasattr(self, "dot_animation"):
            self.dot_animation.stop_animation()
        super().closeEvent(event)
