"""
Improved Port Forward Dialog with better UI layout and content display
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QComboBox, QLineEdit, QFormLayout, QGroupBox,
    QMessageBox, QCheckBox, QTextEdit, QFrame, QScrollArea,
    QWidget, QSizePolicy, QAbstractButton, QApplication,
    QGraphicsDropShadowEffect, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, QEvent, QObject
from PyQt6.QtGui import QFont, QPainter, QColor, QIcon, QPen, QAction
from typing import List, Optional
from Utils.svg_utils import render_svg_icon

from UI.ThemeAwarePage import ThemeAwareMixin
from UI.CustomComboBox import CustomComboBox
from UI.ThemeManager import get_theme_manager
from UI.Styles import AppStyles
from Styles.PortForwardDialogStyles import (
    get_dialog_style, get_resource_info_style, get_namespace_info_style,
    get_form_label_style, get_help_text_style, get_active_dialog_style
)
from Utils.port_forward_manager import get_port_forward_manager
import time
import webbrowser


class PortToggle(QAbstractButton):
    """Compact orange toggle switch for Auto-assign, inspired by ThemeToggle."""
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._position = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"position", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.toggled.connect(self._start_animation)

    @pyqtProperty(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def _start_animation(self, checked):
        self._anim.stop()
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        track = QRectF(rect).adjusted(1, 1, -1, -1)
        r = track.height() / 2
        # Track color: orange when checked, grey when unchecked
        if self._position > 0.01:
            track_color = QColor("#fa7238")
            track_color.setAlphaF(0.3 + 0.7 * self._position)
        else:
            track_color = QColor("#94a3b8")
            track_color.setAlphaF(0.4)
        p.setBrush(track_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(track, r, r)
        # Draw border
        border_col = QColor("#fa7238") if self._position > 0.5 else QColor("#94a3b8")
        border_col.setAlphaF(0.6)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(border_col, 1))
        p.drawRoundedRect(track, r, r)
        # Handle (white circle)
        h = track.height() - 4
        start_x = track.left() + 2
        end_x = track.right() - h - 2
        cur_x = start_x + (end_x - start_x) * self._position
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(cur_x, track.top() + 2, h, h))
        p.end()


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

        self.setWindowTitle("Create Port Forward")
        self.setModal(True)
        self.setMinimumSize(600, 700)
        self.setMaximumSize(700, 800)

        # Set dialog properties for better display
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setSizeGripEnabled(True)
        self.setObjectName("PortForwardDialog")

        # Store widget references for theme updates
        self.resource_info = None
        self.namespace_info = None
        self.help_labels = []
        self.create_button = None
        self.cancel_button = None

        self.setup_ui()
        self.apply_styles()
        self.populate_ports()
        self.update_preview()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def setup_ui(self):
        """Setup the improved dialog UI"""
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(15, 15, 15, 15)
        
        self.main_container = QFrame(self)
        self.main_container.setObjectName("MainDialogContainer")
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.main_container.setGraphicsEffect(shadow)
        
        outer_layout.addWidget(self.main_container)
        
        # Create main layout with 0 side margins so separator spans full width
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 20, 0, 0)

        # Header section (renders at full width, separator included)
        self.create_header_section(main_layout)

        # Inner padded widget for scroll + buttons
        inner_widget = QWidget()
        inner_widget.setStyleSheet("background: transparent;")
        inner_layout = QVBoxLayout(inner_widget)
        inner_layout.setContentsMargins(20, 15, 0, 0)  # right=0 → scrollbar at dialog edge, bottom=0
        inner_layout.setSpacing(15)

        # Create scroll area for main content with custom scrollbar
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Store reference for styling
        self.main_scroll_area = scroll_area

        # Content widget inside scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 20, 0)  # 20px right → card + content breathing room
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
        inner_layout.addWidget(scroll_area, 1)  # Give scroll area stretch priority

        main_layout.addWidget(inner_widget, 1)
        
        # Button section (fixed at bottom, spans full width)
        self.create_button_section(main_layout)

        # Connect signals for live preview updates
        self.connect_preview_signals()

    def create_header_section(self, layout):
        """Create clean header: SVG icon + title, no card border, with separator below."""

        theme = get_theme_manager().get_current_theme()
        accent = theme.colors.ACCENT_ORANGE

        # --- Header row (no card frame) ---
        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setSpacing(10)
        header_layout.setContentsMargins(20, 0, 20, 12)

        # Icon: ip-addresses.svg in a small square badge
        icon_badge = QFrame()
        icon_badge.setFixedSize(36, 36)
        icon_badge.setStyleSheet(
            "QFrame { background-color: rgba(250,114,56,0.10); "
            "border-radius: 8px; border: 1px solid rgba(250,114,56,0.45); }"
        )
        badge_layout = QHBoxLayout(icon_badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        icon_label.setStyleSheet("background: transparent; border: none;")
        # Render at 2x for crisp display on HiDPI screens
        _ratio = max(1.0, QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0)
        _pix = render_svg_icon("ip-addresses.svg", accent, size=int(20 * _ratio))
        _pix.setDevicePixelRatio(_ratio)
        icon_label.setPixmap(_pix)
        badge_layout.addWidget(icon_label)
        header_layout.addWidget(icon_badge)
        self._header_icon_label = icon_label  # keep ref for theme refresh

        # Title
        title_label = QLabel("Create Port Forward")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("background: transparent; border: none;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Close button
        close_button = QPushButton("✕")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setFixedSize(28, 28)
        close_button.setStyleSheet(
            "QPushButton { background: transparent; border: none; "
            "font-size: 15px; font-weight: normal; color: #888888; }"
            "QPushButton:hover { color: #d32f2f; }"
        )
        close_button.clicked.connect(self.reject)
        header_layout.addWidget(close_button)

        layout.addWidget(header_widget)

        # --- Separator below header ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setStyleSheet(
            f"background-color: {theme.colors.BORDER_COLOR}; max-height: 1px; border: none;"
        )
        separator.setFixedHeight(1)
        layout.addWidget(separator)

    def _create_section_header(self, icon_file, label_text):
        """Create a section sub-header: small svg icon badge + bold label, matching CONDITIONS style."""

        theme = get_theme_manager().get_current_theme()
        accent = theme.colors.ACCENT_ORANGE

        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(0, 0, 0, 5)
        h_layout.setSpacing(8)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Small icon badge (no border, just tinted bg)
        badge = QFrame()
        badge.setFixedSize(22, 22)
        badge.setStyleSheet(
            "QFrame { background-color: rgba(250,114,56,0.10); "
            "border-radius: 5px; border: none; }"
        )
        b_layout = QHBoxLayout(badge)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(14, 14)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        # Render at 2x for crisp HiDPI display
        _ratio = max(1.0, QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0)
        _pix = render_svg_icon(icon_file, accent, size=int(14 * _ratio))
        _pix.setDevicePixelRatio(_ratio)
        icon_lbl.setPixmap(_pix)
        b_layout.addWidget(icon_lbl)
        h_layout.addWidget(badge)

        # Section label — 14px, semibold, primary text color (matches desired image)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 600; "
            f"color: {theme.colors.TEXT_LIGHT}; "
            f"background: transparent; border: none;"
        )
        h_layout.addWidget(lbl)
        h_layout.addStretch()
        return header_widget

    def _form_label(self, text):
        """Create a form row label (left column). Style applied via apply_styles."""
        lbl = QLabel(text)
        return lbl

    def _form_value(self, text):
        """Create a right-aligned form row value label. Style applied via apply_styles."""
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def create_resource_info_section(self, layout):
        """Create resource information section"""
        layout.addWidget(self._create_section_header("node.svg", "Resource Information"))

        info_frame = QFrame()
        info_frame.setObjectName("SectionCard")
        info_layout = QFormLayout(info_frame)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(14, 12, 14, 12)

        # Resource type and name
        self.resource_info = self._form_value(
            f"Pod: {self.resource_name}" if self.resource_type.lower() == "pod"
            else f"{self.resource_type.title()}: {self.resource_name}"
        )
        info_layout.addRow(self._form_label("Resource:"), self.resource_info)

        # Namespace
        self.namespace_info = self._form_value(self.namespace)
        info_layout.addRow(self._form_label("Namespace:"), self.namespace_info)

        # Available ports as clickable badge buttons (right-aligned)
        if self.available_ports:
            self._port_badges = []
            ports_widget = QWidget()
            ports_widget.setStyleSheet("background: transparent;")
            ports_layout = QHBoxLayout(ports_widget)
            ports_layout.setContentsMargins(0, 2, 0, 2)
            ports_layout.setSpacing(6)
            ports_layout.addStretch()  # push badges to the right

            for port in self.available_ports[:8]:
                btn = QPushButton(str(port))
                btn.setFixedHeight(22)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setProperty("port_value", str(port))
                btn.clicked.connect(lambda checked, p=str(port): self._select_port_badge(p))
                ports_layout.addWidget(btn)
                self._port_badges.append(btn)

            info_layout.addRow(self._form_label("Available Ports:"), ports_widget)

        layout.addWidget(info_frame)
        # Update badge highlights after combo is populated
        self._pending_badge_update = True

        # Thin separator after Resource Information card
        _border = get_theme_manager().get_current_theme().colors.BORDER_COLOR
        _sep = QWidget()
        _sep.setFixedHeight(1)
        _sep.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        _sep.setStyleSheet(f"background-color: {_border}; border: none;")
        layout.addWidget(_sep)

    def create_port_configuration_section(self, layout):
        """Port Configuration — vertical label-above design matching reference image."""
        layout.addWidget(self._create_section_header("config.svg", "Port Configuration"))

        colors = get_theme_manager().get_current_theme().colors
        text_primary = colors.TEXT_LIGHT
        text_secondary = colors.TEXT_SECONDARY
        text_orange = getattr(colors, 'ACCENT_ORANGE', '#fa7238')

        def _field_label(txt):
            lbl = QLabel(txt)
            lbl.setStyleSheet(
                f"color: {text_primary}; font-size: 14px; font-weight: 600;"
                f" background: transparent; border: none;"
            )
            return lbl

        port_frame = QWidget()
        port_frame.setStyleSheet("background: transparent;")
        port_layout = QVBoxLayout(port_frame)
        port_layout.setSpacing(6)   # tight spacing matching reference
        port_layout.setContentsMargins(0, 4, 0, 0)

        # ─── Target Port ───────────────────────────────────────────
        port_layout.addWidget(_field_label("Target Port"))

        self.target_port_combo = CustomComboBox(self)
        self.target_port_combo.setMinimumHeight(38)
        self.target_port_combo.setPlaceholderText("Select or enter a port")
        port_layout.addWidget(self.target_port_combo)

        tp_help = QLabel("Select or enter the port number on the target resource")
        self.help_labels.append(tp_help)
        port_layout.addWidget(tp_help)
        port_layout.addSpacing(10)  # gap before next section

        # ─── Local Port ────────────────────────────────────────────
        port_layout.addWidget(_field_label("Local Port"))

        local_row = QWidget()
        local_row.setStyleSheet("background: transparent;")
        local_h = QHBoxLayout(local_row)
        local_h.setContentsMargins(0, 0, 0, 0)
        local_h.setSpacing(10)

        self.local_port_spin = QSpinBox()
        self.local_port_spin.setRange(1024, 65535)
        self.local_port_spin.setValue(8080)
        self.local_port_spin.setMinimumHeight(35)
        self.local_port_spin.setFixedWidth(110)
        self.local_port_spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.local_port_spin.installEventFilter(self)  # hover → show arrows
        self.local_port_spin.setStyleSheet(self._spin_normal_style())
        local_h.addWidget(self.local_port_spin)

        self.auto_port_check = PortToggle(checked=True)
        local_h.addWidget(self.auto_port_check)

        self.auto_assign_lbl = QLabel("Auto-assign")
        self.auto_assign_lbl.setStyleSheet(
            f"color: {text_orange}; font-size: 14px; font-weight: 600;"
            f" background: transparent; border: none;"
        )
        local_h.addWidget(self.auto_assign_lbl)
        local_h.addStretch()
        port_layout.addWidget(local_row)

        self.lp_help = QLabel("Automatically finds an available port")
        self.help_labels.append(self.lp_help)
        port_layout.addWidget(self.lp_help)
        port_layout.addSpacing(10)  # gap before next section

        # Connect toggle
        self.auto_port_check.toggled.connect(self.on_auto_port_toggled)
        self.on_auto_port_toggled(True)  # initial state: auto on → spin disabled

        # ─── Protocol ──────────────────────────────────────────────
        port_layout.addWidget(_field_label("Protocol"))

        self._protocol_badges = []
        proto_row = QWidget()
        proto_row.setStyleSheet("background: transparent;")
        proto_h = QHBoxLayout(proto_row)
        proto_h.setContentsMargins(0, 0, 0, 0)
        proto_h.setSpacing(8)

        for proto in ["TCP"]:  # kubectl port-forward is TCP-only
            btn = QPushButton(proto)
            btn.setFixedHeight(36)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("proto_value", proto)
            btn.clicked.connect(lambda checked, p=proto: self._select_protocol_badge(p))
            proto_h.addWidget(btn)
            self._protocol_badges.append(btn)
        # No addStretch — buttons expand equally to fill the row
        port_layout.addWidget(proto_row)

        pr_help = QLabel("kubectl port-forward operates over TCP")
        self.help_labels.append(pr_help)
        port_layout.addWidget(pr_help)

        # Default: TCP selected
        self._selected_protocol = "TCP"
        self._update_protocol_badges()

        layout.addWidget(port_frame)

        # Thin separator at end of Port Configuration
        _sep2 = QWidget()
        _sep2.setFixedHeight(1)
        _sep2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        border = get_theme_manager().get_current_theme().colors.BORDER_COLOR
        _sep2.setStyleSheet(f"background-color: {border}; border: none;")
        layout.addWidget(_sep2)

    def on_auto_port_toggled(self, checked: bool):
        """Disable/enable spinbox, update description text and label color."""
        colors = get_theme_manager().get_current_theme().colors
        orange = getattr(colors, 'ACCENT_ORANGE', '#fa7238')
        grey = colors.TEXT_SECONDARY

        # setEnabled drives QSpinBox:disabled CSS — no manual stylesheet needed
        self.local_port_spin.setEnabled(not checked)

        if checked:
            if hasattr(self, 'auto_assign_lbl'):
                self.auto_assign_lbl.setStyleSheet(
                    f"color: {orange}; font-size: 14px; font-weight: 600;"
                    f" background: transparent; border: none;"
                )
            if hasattr(self, 'lp_help'):
                self.lp_help.setText("Automatically finds an available port")
        else:
            if hasattr(self, 'auto_assign_lbl'):
                self.auto_assign_lbl.setStyleSheet(
                    f"color: {grey}; font-size: 14px; font-weight: 600;"
                    f" background: transparent; border: none;"
                )
            if hasattr(self, 'lp_help'):
                self.lp_help.setText("Port to listen on locally")


    def _spin_normal_style(self):
        """Spinbox style — buttons hidden, no arrows visible."""
        c = get_theme_manager().get_current_theme().colors
        return (
            f"QSpinBox {{"
            f"  background: transparent;"
            f"  color: {c.TEXT_LIGHT};"
            f"  border: 1px solid rgba(148,163,184,0.40);"
            f"  border-radius: 8px;"
            f"  padding: 6px 10px;"
            f"  font-size: 13px;"
            f"}}"
            f"QSpinBox:disabled {{"
            f"  color: {c.TEXT_SECONDARY};"
            f"}}"
            f"QSpinBox::up-button, QSpinBox::down-button {{"
            f"  width: 0px; border: none; background: transparent;"
            f"}}"
            f"QSpinBox::up-arrow, QSpinBox::down-arrow {{ image: none; }}"
        )

    def _spin_hover_style(self):
        """Spinbox style on hover — shows SVG triangle arrows, no border/bg change."""
        c = get_theme_manager().get_current_theme().colors
        return (
            f"QSpinBox {{"
            f"  background: transparent;"
            f"  color: {c.TEXT_LIGHT};"
            f"  border: 1px solid rgba(148,163,184,0.40);"
            f"  border-radius: 8px;"
            f"  padding: 6px 28px 6px 10px;"
            f"  font-size: 13px;"
            f"}}"
            f"QSpinBox:disabled {{"
            f"  color: {c.TEXT_SECONDARY};"
            f"}}"
            f"QSpinBox::up-button {{"
            f"  subcontrol-origin: border;"
            f"  subcontrol-position: top right;"
            f"  width: 20px;"
            f"  border: none; background: transparent;"
            f"}}"
            f"QSpinBox::down-button {{"
            f"  subcontrol-origin: border;"
            f"  subcontrol-position: bottom right;"
            f"  width: 20px;"
            f"  border: none; background: transparent;"
            f"}}"
            f"QSpinBox::up-arrow {{"
            f"  image: url(icons/spin_up.svg);"
            f"  width: 8px; height: 5px;"
            f"}}"
            f"QSpinBox::down-arrow {{"
            f"  image: url(icons/spin_down.svg);"
            f"  width: 8px; height: 5px;"
            f"}}"
        )

    def eventFilter(self, obj, event):
        """Show/hide spinbox SVG arrows on hover."""
        if hasattr(self, 'local_port_spin') and obj is self.local_port_spin:
            if event.type() == QEvent.Type.Enter and self.local_port_spin.isEnabled():
                self.local_port_spin.setStyleSheet(self._spin_hover_style())
            elif event.type() == QEvent.Type.Leave:
                self.local_port_spin.setStyleSheet(self._spin_normal_style())
        return super().eventFilter(obj, event)

    def _select_protocol_badge(self, proto: str):
        """Select a protocol badge and update styling."""
        self._selected_protocol = proto
        self._update_protocol_badges()


    def _update_protocol_badges(self):
        """Refresh protocol badge styles to reflect selection."""
        if not hasattr(self, '_protocol_badges'):
            return
        text_color = get_theme_manager().get_current_theme().colors.TEXT_LIGHT
        for btn in self._protocol_badges:
            pv = btn.property("proto_value")
            if pv == self._selected_protocol:
                btn.setStyleSheet(
                    "QPushButton {"
                    "  background-color: rgba(250,114,56,0.12);"
                    "  color: #fa7238;"
                    "  border: 1px solid rgba(250,114,56,0.55);"
                    "  border-radius: 8px;"
                    "  font-size: 13px; font-weight: 600;"
                    "}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f"  background-color: transparent;"
                    f"  color: {text_color};"
                    f"  border: 1px solid rgba(148,163,184,0.40);"
                    f"  border-radius: 8px;"
                    f"  font-size: 13px; font-weight: normal;"
                    f"}}"
                    f"QPushButton:hover {{"
                    f"  border: 1px solid rgba(250,114,56,0.60);"
                    f"}}"
                )

    def create_advanced_options_section(self, layout):
        """Advanced Options — flat, no card, vertical label-above-input like Port Configuration."""
        layout.addWidget(self._create_section_header("options.svg", "Advanced Options"))

        colors = get_theme_manager().get_current_theme().colors
        text_primary = colors.TEXT_LIGHT
        text_secondary = colors.TEXT_SECONDARY

        adv_frame = QWidget()
        adv_frame.setStyleSheet("background: transparent;")
        adv_layout = QVBoxLayout(adv_frame)
        adv_layout.setSpacing(6)
        adv_layout.setContentsMargins(0, 4, 0, 0)

        # ─── Bind Address label ────────────────────────────────────
        bind_lbl = QLabel("Bind Address")
        bind_lbl.setStyleSheet(
            f"color: {text_primary}; font-size: 14px; font-weight: 600;"
            f" background: transparent; border: none;"
        )
        adv_layout.addWidget(bind_lbl)

        # ─── Input row with globe icon ─────────────────────────────
        bind_row = QWidget()
        bind_row.setStyleSheet(
            "QWidget {"
            "  background: transparent;"
            "  border: 1px solid rgba(148,163,184,0.40);"
            "  border-radius: 8px;"
            "}"
        )
        bind_row.setMinimumHeight(36)
        bind_row_h = QHBoxLayout(bind_row)
        bind_row_h.setContentsMargins(10, 0, 10, 0)
        bind_row_h.setSpacing(6)

        # Globe icon (rendered from link.svg)
        globe_lbl = QLabel()
        globe_lbl.setStyleSheet("border: none; background: transparent;")
        globe_lbl.setFixedSize(16, 16)
        try:
            _ratio = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else 1.0
            pixmap = render_svg_icon("link.svg", color=text_secondary, size=int(16 * _ratio))
            pixmap.setDevicePixelRatio(_ratio)
            globe_lbl.setPixmap(pixmap)
        except Exception:
            globe_lbl.setText("🌐")
        bind_row_h.addWidget(globe_lbl)

        self.bind_address = QLineEdit("localhost")
        self.bind_address.setMinimumHeight(34)
        self.bind_address.setStyleSheet(
            "QLineEdit {"
            "  border: none;"
            "  background: transparent;"
            f"  color: {text_primary};"
            "  font-size: 13px;"
            "  padding: 0px;"
            "}"
        )
        bind_row_h.addWidget(self.bind_address)
        adv_layout.addWidget(bind_row)

        # ─── Help text ─────────────────────────────────────────────
        bind_help = QLabel("Network interface to bind to (localhost for local access only)")
        self.help_labels.append(bind_help)
        adv_layout.addWidget(bind_help)

        layout.addWidget(adv_frame)

        # Add horizontal separator
        _sep3 = QWidget()
        _sep3.setFixedHeight(1)
        _sep3.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        _border = get_theme_manager().get_current_theme().colors.BORDER_COLOR
        _sep3.setStyleSheet(f"background-color: {_border}; border: none;")
        layout.addWidget(_sep3)



    def create_preview_section(self, layout):
        """Create structured preview section matching the requested 3rd image style"""
        layout.addWidget(self._create_section_header("eye.svg", "Configuration Preview"))

        colors = get_theme_manager().get_current_theme().colors
        b = "rgba(148,163,184,0.30)"
        
        self.preview_frame = QFrame()
        # Outer card styling
        self.preview_frame.setStyleSheet(
            f"QFrame {{"
            f"  background-color: transparent;"
            f"  border: 1px solid {b};"
            f"  border-radius: 8px;"
            f"}}"
        )
        p_layout = QVBoxLayout(self.preview_frame)
        p_layout.setSpacing(0)
        p_layout.setContentsMargins(0, 0, 0, 0)
        
        # Helper to create horizontal lines
        def add_line():
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet(f"background-color: {b}; border: none;")
            p_layout.addWidget(line)
        
        # Helper to create subsection headers
        def add_header(icon, title, icon_color):
            w = QWidget()
            w.setStyleSheet("border: none; background: transparent;")
            l = QHBoxLayout(w)
            l.setContentsMargins(16, 12, 16, 8)
            l.setSpacing(8)
            
            # The circle container
            circle = QWidget()
            circle.setFixedSize(28, 28)
            circle.setStyleSheet(
                f"border: 1px solid rgba(148,163,184,0.30);"
                f"border-radius: 10px;"
                f"background: transparent;"
            )
            cl = QVBoxLayout(circle)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            icon_lbl = QLabel()
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            ratio = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else 1.0
            pix = render_svg_icon(icon, icon_color, size=int(14 * ratio))
            pix.setDevicePixelRatio(ratio)
            icon_lbl.setPixmap(pix)
            cl.addWidget(icon_lbl)
            
            title_lbl = QLabel(title.upper())
            title_lbl.setStyleSheet(f"color: {colors.TEXT_LIGHT}; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;")
            l.addWidget(circle)
            l.addWidget(title_lbl)
            l.addStretch()
            p_layout.addWidget(w)
        
        # Helper to add key-value pairs
        def add_kv(parent_layout, key, val_widget):
            row = QWidget()
            row.setStyleSheet("border: none; background: transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(42, 2, 16, 2)
            
            k_lbl = QLabel(key)
            k_lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 13px;")
            k_lbl.setMinimumWidth(120)
            
            rl.addWidget(k_lbl)
            rl.addStretch()  # Push val_widget to the right
            if isinstance(val_widget, QLabel):
                val_widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            rl.addWidget(val_widget)
            parent_layout.addWidget(row)

        # --- Resource Details ---
        add_header("node.svg", "Resource Details", colors.ACCENT_ORANGE)
        
        res_container = QWidget()
        res_container.setStyleSheet("border: none; background: transparent;")
        res_layout = QVBoxLayout(res_container)
        res_layout.setContentsMargins(0, 0, 0, 12)
        res_layout.setSpacing(4)
        
        type_lbl = QLabel(self.resource_type.capitalize())
        type_lbl.setStyleSheet(f"color: {colors.TEXT_LIGHT}; font-size: 13px;")
        add_kv(res_layout, "Type", type_lbl)
        
        name_lbl = QLabel(self.resource_name)
        name_lbl.setStyleSheet(f"color: {colors.TEXT_LIGHT}; font-size: 13px;")
        add_kv(res_layout, "Name", name_lbl)
        
        ns_lbl = QLabel(self.namespace)
        ns_lbl.setStyleSheet(f"color: {colors.TEXT_LIGHT}; font-size: 13px;")
        add_kv(res_layout, "Namespace", ns_lbl)
        
        p_layout.addWidget(res_container)
        add_line()
        
        # --- Network Configuration ---
        add_header("link.svg", "Network Configuration", colors.ACCENT_BLUE)
        
        net_container = QWidget()
        net_container.setStyleSheet("border: none; background: transparent;")
        net_layout = QVBoxLayout(net_container)
        net_layout.setContentsMargins(0, 0, 0, 12)
        net_layout.setSpacing(4)
        
        self.preview_local_addr = QLabel()
        self.preview_local_addr.setStyleSheet(f"color: {colors.TEXT_LIGHT}; font-size: 12px; font-family: monospace;")
        add_kv(net_layout, "Local Address", self.preview_local_addr)
        
        self.preview_target_port = QLabel()
        self.preview_target_port.setStyleSheet(f"color: {colors.TEXT_LIGHT}; font-size: 12px; font-family: monospace;")
        add_kv(net_layout, "Target Port", self.preview_target_port)
        
        self.preview_protocol = QLabel()
        self.preview_protocol.setStyleSheet(
            f"background-color: rgba(0, 149, 255, 0.15);"
            f"color: {colors.ACCENT_BLUE};"
            f"border-radius: 8px;"
            f"padding: 2px 8px;"
            f"font-size: 10px;"
            f"font-weight: 700;"
        )
        add_kv(net_layout, "Protocol", self.preview_protocol)
        
        p_layout.addWidget(net_container)
        add_line()
        
        # --- Access Information ---
        add_header("chain.svg", "Access Information", colors.ACCENT_GREEN)
        
        acc_container = QWidget()
        acc_container.setStyleSheet("border: none; background: transparent;")
        acc_layout = QVBoxLayout(acc_container)
        acc_layout.setContentsMargins(0, 0, 0, 12)
        acc_layout.setSpacing(4)
        
        self.preview_url = QLabel()
        self.preview_url.setTextFormat(Qt.TextFormat.RichText)
        self.preview_url.setOpenExternalLinks(True)
        self.preview_url.setStyleSheet("border: none; background: transparent;")
        add_kv(acc_layout, "URL", self.preview_url)
        
        # Status badge with dot
        self.preview_status_w = QWidget()
        status_l = QHBoxLayout(self.preview_status_w)
        status_l.setContentsMargins(8, 2, 8, 2)
        status_l.setSpacing(4)
        self.preview_status_w.setStyleSheet(
            f"background-color: rgba(76, 175, 80, 0.15);"
            f"border-radius: 8px;"
            f"padding: 2px 8px;"
        )
        self.preview_status_dot = QLabel()
        self.preview_status_dot.setFixedSize(6, 6)
        self.preview_status_dot.setStyleSheet(f"background-color: {colors.ACCENT_GREEN}; border-radius: 3px;")
        self.preview_status_txt = QLabel("Ready to create")
        self.preview_status_txt.setStyleSheet(f"color: {colors.ACCENT_GREEN}; font-size: 10px; font-weight: 700; background: transparent; border: none;")
        status_l.addWidget(self.preview_status_dot)
        status_l.addWidget(self.preview_status_txt)
        
        add_kv(acc_layout, "Status", self.preview_status_w)
        
        p_layout.addWidget(acc_container)
        add_line()
        
        # --- Traffic Flow ---
        add_header("thunder.svg", "Traffic Flow", colors.ACCENT_ORANGE)
        
        flow_container = QWidget()
        flow_container.setStyleSheet("border: none; background: transparent;")
        flow_layout = QHBoxLayout(flow_container)
        flow_layout.setContentsMargins(42, 4, 16, 16)
        flow_layout.setSpacing(12)
        
        def create_flow_card(icon_name, text_lbl_ref, icon_color):
            w = QWidget()
            w.setStyleSheet(
                f"QWidget {{"
                f"  background-color: transparent;"
                f"  border: 1px solid rgba(148,163,184,0.30);"
                f"  border-radius: 6px;"
                f"}}"
            )
            l = QHBoxLayout(w)
            l.setContentsMargins(8, 4, 12, 4)
            l.setSpacing(6)
            
            icon_lbl = QLabel()
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            ratio = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else 1.0
            pix = render_svg_icon(icon_name, icon_color, size=int(14 * ratio))
            pix.setDevicePixelRatio(ratio)
            icon_lbl.setPixmap(pix)
            
            text_lbl_ref.setStyleSheet("border: none; background: transparent; font-size: 12px; font-family: monospace;")
            l.addWidget(icon_lbl)
            l.addWidget(text_lbl_ref)
            return w
            
        flow_layout.addStretch()  # Add stretch to left side
        
        self.flow_local = QLabel()
        flow_layout.addWidget(create_flow_card("link.svg", self.flow_local, colors.ACCENT_BLUE))
        
        arrow_lbl = QLabel("→")
        arrow_lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 16px; background: transparent; border: none;")
        flow_layout.addWidget(arrow_lbl)
        
        self.flow_target = QLabel()
        flow_layout.addWidget(create_flow_card("node.svg", self.flow_target, colors.TEXT_SECONDARY))
        
        flow_layout.addStretch()  # Add stretch to right side
        
        p_layout.addWidget(flow_container)
        
        layout.addWidget(self.preview_frame)


    def create_button_section(self, layout):
        """Create button section matching the header's layout and styling"""
        
        # --- Separator above footer ---
        self.footer_separator = QFrame()
        self.footer_separator.setFrameShape(QFrame.Shape.HLine)
        self.footer_separator.setFrameShadow(QFrame.Shadow.Plain)
        self.footer_separator.setFixedHeight(1)
        layout.addWidget(self.footer_separator)

        # --- Footer row ---
        self.button_frame = QWidget()
        
        button_layout = QHBoxLayout(self.button_frame)
        button_layout.setContentsMargins(20, 16, 20, 16)
        button_layout.setSpacing(10)

        # Help button
        self.help_button = QPushButton(" Help")
        self.help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.help_button.clicked.connect(self.show_help)
        button_layout.addWidget(self.help_button)
        
        # Load default icon
        _theme = get_theme_manager().get_current_theme()
        ratio = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else 1.0
        
        def update_help_icon(hovered=False):
            color = _theme.colors.ACCENT_ORANGE if hovered else _theme.colors.TEXT_SECONDARY
            pix = render_svg_icon("help.svg", color, size=int(16 * ratio))
            pix.setDevicePixelRatio(ratio)
            self.help_button.setIcon(QIcon(pix))
            
        update_help_icon(False)
        
        class HoverFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Enter:
                    update_help_icon(True)
                elif event.type() == QEvent.Type.Leave:
                    update_help_icon(False)
                return False
                
        self.help_filter = HoverFilter()
        self.help_button.installEventFilter(self.help_filter)

        button_layout.addStretch()

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        # Create button
        self.create_button = QPushButton(" Create Port Forward")
        
        # Add checkmark icon to create button
        try:
            check_pix = render_svg_icon("checkmark_white.svg", "#ffffff", size=int(16 * ratio))
            check_pix.setDevicePixelRatio(ratio)
            self.create_button.setIcon(QIcon(check_pix))
        except Exception:
            self.create_button.setText("✓ Create Port Forward")
            
        self.create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_button.clicked.connect(self.create_port_forward)
        self.create_button.setDefault(True)
        button_layout.addWidget(self.create_button)

        layout.addWidget(self.button_frame)

    def connect_preview_signals(self):
        """Connect signals for live preview updates"""
        self.target_port_combo.currentTextChanged.connect(self.on_target_port_changed)
        self.target_port_combo.currentTextChanged.connect(self._update_port_badges)
        self.local_port_spin.valueChanged.connect(self.update_preview)
        # protocol is now badge-driven (_selected_protocol); no combo signal needed
        if hasattr(self, 'bind_address'):
            self.bind_address.textChanged.connect(self.update_preview)
        # auto_port_check (PortToggle) already connected in create_port_configuration_section
        # Trigger badge update now that combo is populated
        if getattr(self, '_pending_badge_update', False):
            self._update_port_badges()


    def _select_port_badge(self, port_str: str):
        """Handle port badge click: update combo, refresh badges, trigger auto-assign."""
        self.target_port_combo.setCurrentText(port_str)
        # CustomComboBox.setCurrentText is silent — call badge refresh directly
        self._update_port_badges()
        # Also fire auto-assign logic (same as if user picked from the dropdown)
        self.on_target_port_changed(port_str)

    def _update_port_badges(self, _=None):
        """Refresh badge styles based on the currently selected port."""
        if not hasattr(self, '_port_badges'):
            return
        current = self.target_port_combo.currentText().strip()
        for btn in self._port_badges:
            port_val = btn.property("port_value")
            if port_val == current:
                # Selected: orange fill + thin orange border
                btn.setStyleSheet(
                    "QPushButton {"
                    "  background-color: rgba(250,114,56,0.12);"
                    "  color: #fa7238;"
                    "  border: 1px solid rgba(250,114,56,0.45);"
                    "  border-radius: 10px;"
                    "  padding: 2px 10px;"
                    "  font-size: 12px;"
                    "  font-weight: 600;"
                    "}"
                )
            else:
                # Unselected: transparent bg, primary text color, subtle border
                text_color = get_theme_manager().get_current_theme().colors.TEXT_LIGHT
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f"  background-color: transparent;"
                    f"  color: {text_color};"
                    f"  border: 1px solid rgba(148,163,184,0.40);"
                    f"  border-radius: 10px;"
                    f"  padding: 2px 10px;"
                    f"  font-size: 12px;"
                    f"  font-weight: normal;"
                    f"}}"
                    f"QPushButton:hover {{"
                    f"  background-color: transparent;"
                    f"  border: 1px solid rgba(250,114,56,0.60);"
                    f"}}"
                )

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
        first_port_text = ""
        if self.target_port_combo.count() > 0:
            self.target_port_combo.setCurrentIndex(0)
            first_port_text = self.target_port_combo.currentText()
        # CustomComboBox.setCurrentIndex is silent — sync badge highlight
        self._update_port_badges()
        # Trigger auto-assign for the initial port now that ports are populated
        if first_port_text:
            self.on_target_port_changed(first_port_text)


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



    def update_preview(self):
        """Update the port forward preview dynamically"""
        if not hasattr(self, 'preview_frame'):  # not yet created during init
            return
            
        colors = get_theme_manager().get_current_theme().colors
        
        try:
            target_port = self.target_port_combo.currentText().strip()
            if not target_port:
                target_port = "..."
            local_port = str(self.local_port_spin.value())
            protocol = getattr(self, '_selected_protocol', 'TCP')
            bind_addr = self.bind_address.text() if hasattr(self, 'bind_address') and self.bind_address.text() else 'localhost'

            # Network Configuration
            self.preview_local_addr.setText(f"{bind_addr}:{local_port}")
            self.preview_target_port.setText(target_port)
            self.preview_protocol.setText(protocol)
            
            # Access Information
            url = f"http://{bind_addr}:{local_port}"
            self.preview_url.setText(f"<a href='{url}' style='color: {colors.TEXT_LINK}; text-decoration: none; font-size: 12px; font-family: monospace;'>{url}</a>")
            
            # Traffic Flow Cards
            local_html = f"<span style='color: {colors.TEXT_LIGHT}; font-size: 12px;'>{bind_addr}: </span><span style='color: {colors.ACCENT_ORANGE}; font-weight: 700; font-size: 12px;'>{local_port}</span>"
            self.flow_local.setText(local_html)
            
            target_html = f"<span style='color: {colors.TEXT_LIGHT}; font-size: 12px;'>{self.resource_type.lower()}/{self.resource_name} : </span><span style='color: {colors.ACCENT_GREEN}; font-weight: 700; font-size: 12px;'>{target_port}</span>"
            self.flow_target.setText(target_html)
            
            # Dynamic Status Badge Logic
            status_text = "Ready to create"  # Or update dynamically based on your app's validation
            if "error" in status_text.lower() or status_text != "Ready to create":
                bg_color = "rgba(239, 68, 68, 0.15)" # Red
                fg_color = colors.ACCENT_RED
            else:
                bg_color = "rgba(76, 175, 80, 0.15)" # Green
                fg_color = colors.ACCENT_GREEN
                
            self.preview_status_w.setStyleSheet(f"background-color: {bg_color}; border-radius: 8px;")
            self.preview_status_dot.setStyleSheet(f"background-color: {fg_color}; border-radius: 3px;")
            self.preview_status_txt.setStyleSheet(f"color: {fg_color}; font-size: 10px; font-weight: 700; background: transparent; border: none;")
            self.preview_status_txt.setText(status_text)
            
        except Exception as e:
            pass

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
            protocol = getattr(self, '_selected_protocol', 'TCP')

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
                        # Toggling auto-assign only disables the spinbox; it does not
                        # pick a free port. Resolve one explicitly so we don't submit
                        # the same in-use port.
                        try:
                            local_port = self.port_manager.get_available_local_port(local_port)
                            self.local_port_spin.setValue(local_port)
                        except RuntimeError as e:
                            self.show_validation_error(f"Cannot find available port: {str(e)}")
                            return
                    else:
                        return

            # Create configuration dictionary
            bind_address = (
                self.bind_address.text().strip()
                if hasattr(self, 'bind_address') and self.bind_address.text().strip()
                else 'localhost'
            )
            config = {
                'resource_name': self.resource_name,
                'resource_type': self.resource_type,
                'namespace': self.namespace,
                'target_port': target_port,
                'local_port': local_port,
                'protocol': protocol,
                'bind_address': bind_address
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
        
        # Apply main scroll area styling
        if hasattr(self, 'main_scroll_area'):
            self.main_scroll_area.setStyleSheet(AppStyles.UNIFIED_SCROLL_BAR_STYLE)
        
        # Refresh header SVG icon with new theme accent color
        if hasattr(self, '_header_icon_label'):
            accent = get_theme_manager().get_current_theme().colors.ACCENT_ORANGE
            self._header_icon_label.setPixmap(render_svg_icon("ip-addresses.svg", accent, size=20))
        
        if self.resource_info:
            self.resource_info.setStyleSheet(get_resource_info_style())

        if self.namespace_info:
            self.namespace_info.setStyleSheet(get_namespace_info_style())

        # Style all form row labels
        for lbl in self.findChildren(QLabel):
            if lbl.text() in ("Resource:", "Namespace:", "Available Ports:"):
                lbl.setStyleSheet(get_form_label_style())

        # Apply help text styling
        for help_label in self.help_labels:
            help_label.setStyleSheet(get_help_text_style())
        
        if hasattr(self, 'target_port_combo'):
            # CustomComboBox handles its own theming — just refresh
            self.target_port_combo._apply_theme()

        if hasattr(self, 'local_port_spin'):
            self.local_port_spin.setStyleSheet(self._spin_normal_style())



        if hasattr(self, '_protocol_badges'):
            self._update_protocol_badges()

        # bind_address uses inline styling (border on parent row widget) — no override needed


        # Refresh port badges too
        self._update_port_badges()

        # Apply button frame styling
        theme = get_theme_manager().get_current_theme()
        
        if hasattr(self, 'footer_separator'):
            self.footer_separator.setStyleSheet(
                f"background-color: {theme.colors.BORDER_COLOR}; max-height: 1px; border: none;"
            )

        if self.button_frame:
            self.button_frame.setStyleSheet("background: transparent; border: none;")
        
        # Apply button styling
        if self.create_button:
            self.create_button.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: #fa7238;"  # Same as auto-assign toggle
                f"  border: none;"
                f"  border-radius: 6px;"
                f"  padding: 6px 16px;"
                f"  color: white;"
                f"  font-weight: bold;"
                f"  font-size: 13px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: rgba(250, 114, 56, 0.85);"  # Whitish dull orange
                f"}}"
            )
        
        if self.cancel_button:
            self.cancel_button.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: transparent;"
                f"  border: 1px solid {theme.colors.BORDER_COLOR};"
                f"  border-radius: 6px;"
                f"  padding: 6px 16px;"
                f"  color: {theme.colors.TEXT_LIGHT};"
                f"  font-weight: 600;"
                f"  font-size: 13px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: rgba(250, 114, 56, 0.10);"
                f"  color: #fa7238;"
                f"  border: 1px solid {theme.colors.BORDER_COLOR};"
                f"}}"
            )
        
        # Apply secondary button styling to help button
        if hasattr(self, 'help_button'):
            self.help_button.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: transparent;"
                f"  border: none;"
                f"  padding: 6px 12px;"
                f"  color: {theme.colors.TEXT_SECONDARY};"
                f"  font-weight: 600;"
                f"  font-size: 13px;"
                f"  border-radius: 6px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: rgba(250, 114, 56, 0.10);"
                f"  color: #fa7238;"
                f"}}"
            )

    def _on_theme_changed(self, theme_name):
        """Handle theme changes by refreshing all widget styles"""
        self.apply_styles()


class PortForwardCard(QFrame):
    def __init__(self, config, parent_dialog):
        super().__init__(parent_dialog)
        self.config = config
        self.parent_dialog = parent_dialog
        self.setup_ui()

    def setup_ui(self):

        theme = get_theme_manager().get_current_theme()
        has_error = self.config.status == 'error' or self.config.error_message
        
        ratio = max(1.0, QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0)
        
        # Colors
        if has_error:
            status_color = getattr(theme.colors, 'STATUS_ERROR', '#ef4444')
            bg_color = "rgba(239, 68, 68, 0.03)"
            border_color = "rgba(239, 68, 68, 0.2)"
        else:
            status_color = getattr(theme.colors, 'STATUS_SUCCESS', '#22c55e')
            bg_color = "transparent"
            border_color = theme.colors.BORDER_COLOR
        
        self.setObjectName("PortForwardCard")
        self.setStyleSheet(f"""
            #PortForwardCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            #PortForwardCard:hover {{
                background-color: rgba(128, 128, 128, 0.05);
            }}
        """)
        
        # Use a horizontal layout to hold the indicator bar and content separately
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        # Left Indicator Bar (Straight line, no curve)
        indicator = QFrame()
        indicator.setFixedWidth(4)
        # Use smaller margins to cover more of the edge while staying straight
        indicator.setStyleSheet(f"background-color: {status_color}; border: none; margin-top: 6px; margin-bottom: 6px; border-radius: 2px;")
        outer_layout.addWidget(indicator)
        
        # Content Container
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent; border: none;")
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(20, 20, 24, 20)
        main_layout.setSpacing(16)
        outer_layout.addWidget(content_widget)
        
        # --- Row 1: Header ---
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        
        # Status icon container card
        icon_bg = QFrame()
        icon_bg.setObjectName("StatusIconCard")
        icon_bg.setFixedSize(32, 32)
        
        if has_error:
            bg = "rgba(239, 68, 68, 0.1)"
            icon_name = "alert_triangle.svg"
        else:
            bg = "rgba(34, 197, 94, 0.1)"
            icon_name = "thunder.svg"
            
        icon_bg.setStyleSheet(f"#StatusIconCard {{ background-color: {bg}; border-radius: 10px; border: none; }}")
        
        il = QVBoxLayout(icon_bg)
        il.setContentsMargins(0, 0, 0, 0)
        il.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel()
        icon_label.setStyleSheet("border: none; background: transparent;")
        pix = render_svg_icon(icon_name, status_color, size=int(18 * ratio))
        pix.setDevicePixelRatio(ratio)
        icon_label.setPixmap(pix)
        il.addWidget(icon_label)
        
        row1.addWidget(icon_bg)
        
        # Target Name
        name_label = QLabel(self.config.resource_name)
        name_label.setStyleSheet(f"color: {theme.colors.TEXT_LIGHT}; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        row1.addWidget(name_label)
        
        # Namespace badge
        ns_badge = QFrame()
        ns_badge.setObjectName("ns_badge")
        ns_badge.setStyleSheet(f"#ns_badge {{ background-color: rgba(128, 128, 128, 0.1); border-radius: 12px; border: none; }}")
        ns_layout = QHBoxLayout(ns_badge)
        ns_layout.setContentsMargins(8, 2, 8, 2)
        ns_layout.setSpacing(4)
        
        ns_icon = QLabel()
        ns_icon.setStyleSheet("background: transparent; border: none;")
        ns_pix = render_svg_icon("namespaces.svg", theme.colors.TEXT_SECONDARY, size=int(12 * ratio))
        ns_pix.setDevicePixelRatio(ratio)
        ns_icon.setPixmap(ns_pix)
        ns_layout.addWidget(ns_icon)
        
        ns_label = QLabel(self.config.namespace)
        ns_label.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; font-size: 11px; border: none; background: transparent;")
        ns_layout.addWidget(ns_label)
        row1.addWidget(ns_badge)
        
        row1.addStretch()
        
        # Status Badge
        status_badge = QFrame()
        if has_error:
            status_badge.setStyleSheet("QFrame { background-color: rgba(239, 68, 68, 0.1); border-radius: 12px; border: none; }")
            s_text = "ERROR"
            curr_status_color = getattr(theme.colors, 'STATUS_ERROR', '#ef4444')
        elif self.config.status == 'inactive':
            status_badge.setStyleSheet("QFrame { background-color: rgba(148, 163, 184, 0.1); border-radius: 12px; border: none; }")
            s_text = "INACTIVE"
            curr_status_color = theme.colors.TEXT_SECONDARY
        elif self.config.status == 'starting':
            status_badge.setStyleSheet("QFrame { background-color: rgba(250, 114, 56, 0.1); border-radius: 12px; border: none; }")
            s_text = "STARTING"
            curr_status_color = theme.colors.ACCENT_ORANGE
        else:
            status_badge.setStyleSheet("QFrame { background-color: rgba(34, 197, 94, 0.1); border-radius: 12px; border: none; }")
            s_text = "ACTIVE"
            curr_status_color = getattr(theme.colors, 'STATUS_SUCCESS', '#22c55e')
            
        s_layout = QHBoxLayout(status_badge)
        s_layout.setContentsMargins(8, 2, 8, 2)
        s_layout.setSpacing(6)
        
        if s_text == "ACTIVE":
            s_dot = QFrame()
            s_dot.setFixedSize(8, 8)
            s_dot.setStyleSheet(f"QFrame {{ background-color: {curr_status_color}; border-radius: 4px; border: none; }}")
            s_layout.addWidget(s_dot)
            
        s_label = QLabel(s_text)
        s_label.setStyleSheet(f"color: {curr_status_color}; font-size: 10px; font-weight: bold; border: none; background: transparent;")
        s_layout.addWidget(s_label)
        row1.addWidget(status_badge)
        
        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(2)
        actions_layout.setContentsMargins(10, 0, 0, 0)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Action button helper to ensure stability and consistent styling
        def create_btn(icon_path, callback, hover_bg, hover_icon_color=None, is_stop=False):
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: transparent; border: none; border-radius: 10px; padding: 0px; margin: 0px; min-width: 32px; min-height: 32px; }}"
                f"QPushButton:hover {{ background-color: {hover_bg}; }}"
            )
            
            if is_stop:
                icon_btn_layout = QVBoxLayout(btn)
                icon_btn_layout.setContentsMargins(0, 0, 0, 0)
                icon_btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                stop_icon = QFrame()
                stop_icon.setFixedSize(14, 14)
                s_style_n = f"QFrame {{ background-color: {theme.colors.TEXT_SECONDARY}; border-radius: 3px; border: none; }}"
                stop_icon.setStyleSheet(s_style_n)
                icon_btn_layout.addWidget(stop_icon)
                
                if hover_icon_color:
                    s_style_h = f"QFrame {{ background-color: {hover_icon_color}; border-radius: 3px; border: none; }}"
                    def enter_evt(e):
                        stop_icon.setStyleSheet(s_style_h)
                        QPushButton.enterEvent(btn, e)
                    def leave_evt(e):
                        stop_icon.setStyleSheet(s_style_n)
                        QPushButton.leaveEvent(btn, e)
                    btn.enterEvent = enter_evt
                    btn.leaveEvent = leave_evt
            else:
                n_icon = QIcon(render_svg_icon(icon_path, theme.colors.TEXT_SECONDARY, size=int(18 * ratio)))
                btn.setIcon(n_icon)
                
                if hover_icon_color:
                    h_icon = QIcon(render_svg_icon(icon_path, hover_icon_color, size=int(18 * ratio)))
                    def enter_evt(e):
                        btn.setIcon(h_icon)
                        QPushButton.enterEvent(btn, e)
                    def leave_evt(e):
                        btn.setIcon(n_icon)
                        QPushButton.leaveEvent(btn, e)
                    btn.enterEvent = enter_evt
                    btn.leaveEvent = leave_evt
            
            btn.clicked.connect(callback)
            return btn

        if not has_error:
            # Link button - Blue on hover, orange-tinted background
            btn_link = create_btn("external_link.svg", self._open_in_browser, "rgba(249, 115, 22, 0.1)", hover_icon_color="#3b82f6")
            actions_layout.addWidget(btn_link)
            
            # Copy button - Orange on hover, orange-tinted background
            btn_copy = create_btn("replica.svg", self._copy_to_clipboard, "rgba(249, 115, 22, 0.1)", hover_icon_color="#f97316")
            actions_layout.addWidget(btn_copy)
            
        # Stop button (re-implemented as 32x32 button for consistency)
        btn_stop = create_btn(None, self._stop_forward, "rgba(239, 68, 68, 0.1)", hover_icon_color="#ef4444", is_stop=True)
        actions_layout.addWidget(btn_stop)
            
        # (Removed redundant Stop button code)
        
        row1.addLayout(actions_layout)
        main_layout.addLayout(row1)
        
        # --- Row 2: Details ---
        row2 = QHBoxLayout()
        row2.setContentsMargins(44, 0, 0, 0)
        row2.setSpacing(12)
        
        # Port info cards (Pill style - Icon and text in ONE box)
        def create_mini_card(icon_name, label, value, val_color, icon_color):
            card = QFrame()
            card.setObjectName("MiniCard")
            card.setStyleSheet(
                f"#MiniCard {{ "
                f"  background-color: rgba(148, 163, 184, 0.08); "
                f"  border: 1px solid rgba(148, 163, 184, 0.25); "
                f"  border-radius: 12px; "
                f"}}"
            )
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(10, 4, 12, 4)
            c_lay.setSpacing(6)
            
            i_lbl = QLabel()
            i_lbl.setStyleSheet("border: none; background: transparent;")
            i_pix = render_svg_icon(icon_name, icon_color, size=int(12 * ratio))
            i_pix.setDevicePixelRatio(ratio)
            i_lbl.setPixmap(i_pix)
            c_lay.addWidget(i_lbl)
            
            t_lbl = QLabel(f"<span style='color: {theme.colors.TEXT_SECONDARY};'>{label}:</span> <span style='color: {val_color}; font-weight: bold; font-family: monospace;'>{value}</span>")
            t_lbl.setTextFormat(Qt.TextFormat.RichText)
            t_lbl.setStyleSheet("border: none; background: transparent; font-size: 12px;")
            c_lay.addWidget(t_lbl)
            return card

        local_card = create_mini_card("link.svg", "localhost", self.config.local_port, theme.colors.ACCENT_ORANGE, theme.colors.ACCENT_BLUE)
        row2.addWidget(local_card)
        
        arrow_lbl = QLabel("→")
        arrow_lbl.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        row2.addWidget(arrow_lbl)
        
        target_card = create_mini_card("node.svg", self.config.resource_type, self.config.target_port, theme.colors.ACCENT_GREEN, theme.colors.TEXT_SECONDARY)
        row2.addWidget(target_card)
        
        # Protocol Badge
        proto_badge = QLabel(f" {self.config.protocol.upper()} ")
        proto_badge.setStyleSheet(f"background-color: rgba(59, 130, 246, 0.1); color: {theme.colors.ACCENT_BLUE}; font-size: 10px; font-weight: bold; border-radius: 8px; padding: 2px 6px;")
        row2.addWidget(proto_badge)
        
        row2.addStretch()
        main_layout.addLayout(row2)
        
        # --- Row 3: Status Details ---
        row3 = QHBoxLayout()
        row3.setContentsMargins(44, 0, 0, 0)
        row3.setSpacing(8)
        
        if has_error:
            err_icon = QLabel()
            err_pix = render_svg_icon("alert_triangle.svg", status_color, size=int(14 * ratio))
            err_pix.setDevicePixelRatio(ratio)
            err_icon.setPixmap(err_pix)
            row3.addWidget(err_icon)
            
            err_label = QLabel(self.config.error_message or "kubectl port-forward failed to start")
            err_label.setStyleSheet(f"color: {status_color}; font-size: 12px; border: none; background: transparent;")
            row3.addWidget(err_label)
        else:
            # Uptime
            check_icon = QLabel()
            check_pix = render_svg_icon("check_circle.svg", status_color, size=int(14 * ratio))
            check_pix.setDevicePixelRatio(ratio)
            check_icon.setPixmap(check_pix)
            row3.addWidget(check_icon)
            
            uptime = time.time() - (self.config.created_at or time.time())
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            up_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            
            up_label = QLabel(f"Uptime <span style='font-weight: bold; color: {theme.colors.TEXT_LIGHT};'>{up_text}</span>")
            up_label.setTextFormat(Qt.TextFormat.RichText)
            up_label.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; font-size: 12px; border: none; background: transparent;")
            row3.addWidget(up_label)
            
            # Data transferred not shown — no real per-forward byte counters yet.

        row3.addStretch()
        main_layout.addLayout(row3)
        
    def _open_in_browser(self):
        webbrowser.open(f"http://localhost:{self.config.local_port}")
        
    def _copy_to_clipboard(self):
        QApplication.clipboard().setText(f"http://localhost:{self.config.local_port}")
        
    def _stop_forward(self, event=None):
        get_port_forward_manager().stop_port_forward(self.config.key)
        if self.parent_dialog:
            self.parent_dialog.refresh_forwards()

class ActivePortForwardsDialog(ThemeAwareMixin, QDialog):
    """Enhanced dialog showing active port forwards with improved layout"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.port_manager = get_port_forward_manager()

        self.setWindowTitle("Active Port Forwards")
        self.setModal(True)
        self.setMinimumSize(750, 550)
        self.resize(850, 650)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("ActivePortForwardsDialog")

        # Store widget references for theme updates
        self.status_label = None
        self.refresh_button = None
        self.stop_all_button = None
        self.close_button = None

        self.setup_ui()
        self.apply_styles()
        self.refresh_forwards()

        # Connect to manager signals
        self.port_manager.port_forwards_updated.connect(self.refresh_forwards)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def setup_ui(self):
        """Setup enhanced UI"""
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(15, 15, 15, 15)
        
        self.main_container = QFrame(self)
        self.main_container.setObjectName("MainDialogContainer")
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.main_container.setGraphicsEffect(shadow)
        
        outer_layout.addWidget(self.main_container)

        layout = QVBoxLayout(self.main_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Header row (no card frame, icon + title, close button) ---
        theme = get_theme_manager().get_current_theme()
        accent = theme.colors.ACCENT_ORANGE

        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setSpacing(15)
        header_layout.setContentsMargins(20, 20, 15, 15)

        # Icon badge: activity.svg
        icon_badge = QFrame()
        icon_badge.setFixedSize(40, 40)
        icon_badge.setStyleSheet(
            "QFrame { background-color: rgba(250,114,56,0.10); "
            "border-radius: 8px; border: 1px solid rgba(250,114,56,0.45); }"
        )
        badge_layout = QHBoxLayout(icon_badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        icon_label.setStyleSheet("background: transparent; border: none;")
        _ratio = max(1.0, QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0)
        _pix = render_svg_icon("activity.svg", accent, size=int(20 * _ratio))
        _pix.setDevicePixelRatio(_ratio)
        icon_label.setPixmap(_pix)
        badge_layout.addWidget(icon_label)
        header_layout.addWidget(icon_badge, alignment=Qt.AlignmentFlag.AlignTop)
        self._header_icon_label = icon_label  # keep ref for theme refresh

        # Title and Description Layout
        title_desc_layout = QVBoxLayout()
        title_desc_layout.setSpacing(4)
        title_desc_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Active Port Forwards")
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("background: transparent; border: none; padding: 0px; margin: 0px;")
        title_desc_layout.addWidget(title)

        # Description
        desc = QLabel("Monitor and manage all running kubectl port-forward sessions.")
        desc.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; font-size: 13px; background: transparent; border: none; padding: 0px; margin: 0px;")
        title_desc_layout.addWidget(desc)

        header_layout.addLayout(title_desc_layout)

        header_layout.addStretch()

        # Status Badge Widget
        self.status_badge_widget = QWidget()
        self.status_badge_widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        badge_layout_inner = QHBoxLayout(self.status_badge_widget)
        badge_layout_inner.setContentsMargins(10, 4, 10, 4)
        badge_layout_inner.setSpacing(6)

        self.status_badge_dot = QLabel()
        self.status_badge_dot.setFixedSize(8, 8)
        
        self.status_label = QLabel("Loading...")
        
        badge_layout_inner.addWidget(self.status_badge_dot)
        badge_layout_inner.addWidget(self.status_label)
        
        header_layout.addWidget(self.status_badge_widget, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addSpacing(10)

        close_button = QPushButton("✕")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setFixedSize(28, 28)
        close_button.setStyleSheet(
            "QPushButton { background: transparent; border: none; "
            "font-size: 15px; font-weight: normal; color: #888888; padding: 0px; margin: 0px; }"
            "QPushButton:hover { color: #d32f2f; }"
        )
        close_button.clicked.connect(self.accept)
        header_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addWidget(header_widget)

        # --- Separator below header ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setStyleSheet(
            f"background-color: {theme.colors.BORDER_COLOR}; max-height: 1px; border: none;"
        )
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        # --- Toolbar row (Search + Buttons) ---
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("background: transparent;")
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(25, 12, 25, 12)
        toolbar_layout.setSpacing(12)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by pod, namespace, or port...")
        self.search_input.setMinimumHeight(36)
        
        self.search_action = QAction(self.search_input)
        self.search_input.addAction(self.search_action, QLineEdit.ActionPosition.LeadingPosition)
        self.search_input.textChanged.connect(self.refresh_forwards)
        
        toolbar_layout.addWidget(self.search_input, stretch=1)

        # Button Helper
        class IconHoverFilter(QObject):
            def __init__(self, button, icon_name, normal_color_attr, hover_color_attr, disabled_color_attr=None):
                super().__init__(button)
                self.button = button
                self.icon_name = icon_name
                self.normal_color_attr = normal_color_attr
                self.hover_color_attr = hover_color_attr
                self.disabled_color_attr = disabled_color_attr or normal_color_attr
                self.update_icon(False)
                
            def update_icon(self, hovered=False):
                
                theme = get_theme_manager().get_current_theme()
                
                def get_color(attr):
                    if attr.startswith('#') or attr.startswith('rgba'):
                        return attr
                    return getattr(theme.colors, attr, theme.colors.TEXT_SECONDARY)
                    
                is_disabled = not self.button.isEnabled()
                
                if is_disabled:
                    color = get_color(self.disabled_color_attr)
                else:
                    color = get_color(self.hover_color_attr) if hovered else get_color(self.normal_color_attr)
                    
                ratio = max(1.0, QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0)
                pix = render_svg_icon(self.icon_name, color, size=int(16 * ratio))
                pix.setDevicePixelRatio(ratio)
                icon = QIcon()
                icon.addPixmap(pix, QIcon.Mode.Normal, QIcon.State.Off)
                if is_disabled:
                    icon.addPixmap(pix, QIcon.Mode.Disabled, QIcon.State.Off)
                self.button.setIcon(icon)
                
            def eventFilter(self, obj, event):
                if not self.button.isEnabled():
                    return super().eventFilter(obj, event)
                if event.type() == QEvent.Type.Enter:
                    self.update_icon(True)
                elif event.type() == QEvent.Type.Leave:
                    self.update_icon(False)
                return super().eventFilter(obj, event)

        # Refresh button
        self.refresh_button = QPushButton(" Refresh")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.setMinimumHeight(32)
        self.refresh_button.clicked.connect(self.refresh_forwards)
        self.refresh_filter = IconHoverFilter(self.refresh_button, "terminal_refresh.svg", "TEXT_LIGHT", "ACCENT_ORANGE")
        self.refresh_button.installEventFilter(self.refresh_filter)
        toolbar_layout.addWidget(self.refresh_button)

        # Stop All button
        self.stop_all_button = QPushButton(" Stop All")
        self.stop_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_all_button.setMinimumHeight(32)
        self.stop_all_button.clicked.connect(self.stop_all_forwards)
        self.stop_filter = IconHoverFilter(self.stop_all_button, "stop.svg", "#ef4444", "#ef4444", disabled_color_attr="#fca5a5")
        self.stop_all_button.installEventFilter(self.stop_filter)
        toolbar_layout.addWidget(self.stop_all_button)

        layout.addWidget(toolbar_widget)

        # --- Separator below toolbar ---
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Plain)
        separator2.setStyleSheet(
            f"background-color: {theme.colors.BORDER_COLOR}; max-height: 1px; border: none;"
        )
        separator2.setFixedHeight(1)
        layout.addWidget(separator2)

        # Inner padded widget for content only
        inner_widget = QWidget()
        inner_widget.setStyleSheet("background: transparent;")
        inner_layout = QVBoxLayout(inner_widget)
        inner_layout.setContentsMargins(25, 15, 25, 15)
        inner_layout.setSpacing(20)

        self.stack = QStackedWidget()

        # Content area with scroll and custom scrollbar (Index 0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        # Store reference for styling
        self.active_scroll_area = scroll_area

        self.content_container = QWidget()
        self.content_container.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(24, 20, 24, 20)
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll_area.setWidget(self.content_container)
        self.stack.addWidget(scroll_area)

        # Empty state widget (Index 1)
        self.empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(12)
        
        self.empty_icon_label = QLabel()
        self.empty_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.empty_title = QLabel("No active port forwards")
        empty_layout.addWidget(self.empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.empty_desc = QLabel("Create port forwards from the Pods or Services pages using the\n'Port Forward' action.")
        self.empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_desc, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.stack.addWidget(self.empty_state_widget)
        inner_layout.addWidget(self.stack)

        layout.addWidget(inner_widget, 1)

        # --- Separator above footer ---
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setFrameShadow(QFrame.Shadow.Plain)
        separator3.setStyleSheet(
            f"background-color: {theme.colors.BORDER_COLOR}; max-height: 1px; border: none;"
        )
        separator3.setFixedHeight(1)
        layout.addWidget(separator3)

        # --- Footer row ---
        footer_widget = QWidget()
        footer_widget.setStyleSheet("background: transparent;")
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(24, 16, 24, 16)
        
        self.showing_label = QLabel("Showing 0 of 0 sessions")
        self.showing_label.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; font-size: 13px;")
        footer_layout.addWidget(self.showing_label)
        
        footer_layout.addStretch()

        self.close_button = QPushButton(" Close")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setMinimumHeight(32)
        self.close_button.clicked.connect(self.accept)
        self.close_filter = IconHoverFilter(self.close_button, "cross.svg", "TEXT_LIGHT", "ACCENT_ORANGE")
        self.close_button.installEventFilter(self.close_filter)
        footer_layout.addWidget(self.close_button)

        layout.addWidget(footer_widget)

    def apply_styles(self):
        """Apply enhanced styling"""
        self.setStyleSheet(get_active_dialog_style())
        
        # Apply scroll area styling
        if hasattr(self, 'active_scroll_area'):
            self.active_scroll_area.setStyleSheet(AppStyles.UNIFIED_SCROLL_BAR_STYLE)
        
        # Apply status label styling based on current state
        if hasattr(self, 'status_badge_widget'):
            self.refresh_forwards()
                
        if hasattr(self, '_header_icon_label'):
            theme = get_theme_manager().get_current_theme()
            accent = theme.colors.ACCENT_ORANGE
            _ratio = max(1.0, QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0)
            _pix = render_svg_icon("activity.svg", accent, size=int(20 * _ratio))
            _pix.setDevicePixelRatio(_ratio)
            self._header_icon_label.setPixmap(_pix)
            
        if hasattr(self, 'search_input'):
            theme = get_theme_manager().get_current_theme()
            self.search_input.setStyleSheet(
                f"QLineEdit {{"
                f"  background-color: transparent;"
                f"  color: {theme.colors.TEXT_LIGHT};"
                f"  border: 1px solid {theme.colors.BORDER_COLOR};"
                f"  border-radius: 6px;"
                f"  padding: 4px 8px 4px 30px;"
                f"  font-size: 13px;"
                f"}}"
                f"QLineEdit:focus {{"
                f"  border: 1px solid #fa7238;"
                f"}}"
            )
            
            _ratio = max(1.0, QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0)
            pix = render_svg_icon("search.svg", theme.colors.TEXT_SECONDARY, size=int(16 * _ratio))
            pix.setDevicePixelRatio(_ratio)
            self.search_action.setIcon(QIcon(pix))
            
            refresh_btn_style = (
                f"QPushButton {{"
                f"  background-color: transparent;"
                f"  border: 1px solid {theme.colors.BORDER_COLOR};"
                f"  border-radius: 6px;"
                f"  padding: 4px 10px;"
                f"  color: {theme.colors.TEXT_LIGHT};"
                f"  font-weight: 600;"
                f"  font-size: 13px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: rgba(250, 114, 56, 0.10);"
                f"  color: #fa7238;"
                f"  border: 1px solid {theme.colors.BORDER_COLOR};"
                f"}}"
            )
            
            error_color = getattr(theme.colors, 'STATUS_ERROR', '#ef4444')
            stop_btn_style = (
                f"QPushButton {{"
                f"  background-color: transparent;"
                f"  border: 1px solid {error_color};"
                f"  border-radius: 6px;"
                f"  padding: 4px 10px;"
                f"  color: {error_color};"
                f"  font-weight: 600;"
                f"  font-size: 13px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: rgba(239, 68, 68, 0.12);"
                f"  color: {error_color};"
                f"  border: 1px solid {error_color};"
                f"}}"
                f"QPushButton:disabled {{"
                f"  background-color: transparent;"
                f"  border: 1px solid #fca5a5;"
                f"  color: #fca5a5;"
                f"}}"
            )
            self.refresh_button.setStyleSheet(refresh_btn_style)
            self.stop_all_button.setStyleSheet(stop_btn_style)
            if hasattr(self, 'close_button'):
                self.close_button.setStyleSheet(refresh_btn_style)
            
            self.refresh_filter.update_icon(False)
            self.stop_filter.update_icon(False)
            if hasattr(self, 'close_filter'):
                self.close_filter.update_icon(False)
                
            if hasattr(self, 'empty_icon_label'):
                _ratio = max(1.0, QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0)
                _empty_pix = render_svg_icon("no_ports.svg", theme.colors.TEXT_SECONDARY, size=int(48 * _ratio))
                _empty_pix.setDevicePixelRatio(_ratio)
                self.empty_icon_label.setPixmap(_empty_pix)
                self.empty_icon_label.setFixedSize(80, 80)
                self.empty_icon_label.setStyleSheet(
                    f"background-color: rgba(128, 128, 128, 0.05); "
                    f"border: 1px solid rgba(128, 128, 128, 0.15); "
                    f"border-radius: 16px;"
                )
                self.empty_title.setStyleSheet(f"color: {theme.colors.TEXT_LIGHT}; font-size: 15px; font-weight: bold; background: transparent;")
                self.empty_desc.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; font-size: 13px; background: transparent;")

    def _on_theme_changed(self, theme_name):
        """Handle theme changes by refreshing all widget styles"""
        self.apply_styles()

    def refresh_forwards(self):
        """Refresh the list of port forwards with enhanced display"""
        forwards = self.port_manager.get_port_forwards()
        colors = get_theme_manager().get_current_theme().colors

        query = self.search_input.text().lower() if hasattr(self, 'search_input') else ""
        if query:
            display_forwards = []
            for f in forwards:
                if query in f.resource_name.lower() or query in f.namespace.lower() or query in str(f.local_port) or query in str(f.target_port):
                    display_forwards.append(f)
        else:
            display_forwards = forwards

        # Global active/total counts (search-independent) for the status badge;
        # the footer shows the filtered "shown" count against this total.
        active_count = sum(1 for f in forwards if f.status in ['active', 'starting'])
        total_count = len(forwards)
        
        # Toggle stop button state
        if hasattr(self, 'stop_all_button'):
            is_enabled = active_count > 0 or len(forwards) > 0
            # Wait, user wants it disabled when there is no port forwarding.
            self.stop_all_button.setEnabled(len(forwards) > 0)
            if hasattr(self, 'stop_filter'):
                self.stop_filter.update_icon(False)
                
        self.status_label.setText(f"{active_count}/{total_count} active")
        
        # Always green style as requested
        bg_color = "rgba(76, 175, 80, 0.15)"
        fg_color = colors.ACCENT_GREEN
            
        if hasattr(self, 'status_badge_widget'):
            self.status_badge_widget.setStyleSheet(f"background-color: {bg_color}; border-radius: 12px;")
            self.status_badge_dot.setStyleSheet(f"background-color: {fg_color}; border-radius: 4px;")
            self.status_label.setStyleSheet(f"color: {fg_color}; font-size: 12px; font-weight: bold; background: transparent; border: none;")

        if not display_forwards:
            if hasattr(self, 'stack'):
                self.stack.setCurrentIndex(1)
            else:
                # Fallback if stack is not setup
                while self.content_layout.count():
                    child = self.content_layout.takeAt(0)
                    if child.widget():
                        child.widget().hide()
                        child.widget().deleteLater()
            
            if hasattr(self, 'showing_label'):
                self.showing_label.setText(f"Showing <span style='font-weight: bold; color: {colors.TEXT_LIGHT};'>0</span> of <span style='font-weight: bold; color: {colors.TEXT_LIGHT};'>{total_count}</span> sessions")
            return

        if hasattr(self, 'stack'):
            self.stack.setCurrentIndex(0)
            
        if hasattr(self, 'showing_label'):
            self.showing_label.setText(f"Showing <span style='font-weight: bold; color: {colors.TEXT_LIGHT};'>{len(display_forwards)}</span> of <span style='font-weight: bold; color: {colors.TEXT_LIGHT};'>{total_count}</span> sessions")

        # Clear existing cards
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().hide()
                child.widget().deleteLater()
                
        # Populate new cards
        for config in display_forwards:
            card = PortForwardCard(config, self)
            self.content_layout.addWidget(card)

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
