"""
Non-blocking toast notification system for Orchestrix.

Displays temporary, corner-anchored notifications that appear in the
bottom-right of the main window without interrupting the user's workflow.

Two deliberate design choices:
  - Background drawn in paintEvent (not stylesheet) so the app's global
    QWidget stylesheet rule cannot bleed through and destroy contrast.
  - Widget is moved off-screen before show(), then repositioned via
    QTimer.singleShot(0) so Qt has computed the actual widget geometry
    before we calculate bottom-right coordinates.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath

# Toast type constants
TOAST_SUCCESS = 'success'
TOAST_ERROR = 'error'
TOAST_INFO = 'info'

# Per-theme, per-type colour palettes.
# Light theme: very subtle tinted backgrounds with high-contrast dark text —
#   the bg is tinted but nearly white, keeping contrast with the border.
# Dark theme: deep saturated backgrounds with near-white text.
_THEME_COLORS = {
    'Light': {
        TOAST_SUCCESS: {
            'bg': '#f0fdf4', 'border': '#16a34a',
            'icon_color': '#16a34a', 'icon': '✓',
            'title': '#14532d', 'body': '#166534',
        },
        TOAST_ERROR: {
            'bg': '#fef2f2', 'border': '#dc2626',
            'icon_color': '#dc2626', 'icon': '✕',
            'title': '#7f1d1d', 'body': '#991b1b',
        },
        TOAST_INFO: {
            'bg': '#eff6ff', 'border': '#2563eb',
            'icon_color': '#2563eb', 'icon': 'ℹ',
            'title': '#1e3a8a', 'body': '#1d4ed8',
        },
    },
    'Dark': {
        TOAST_SUCCESS: {
            'bg': '#1b4332', 'border': '#22c55e',
            'icon_color': '#4ade80', 'icon': '✓',
            'title': '#f0f0f0', 'body': '#f0f0f0',
        },
        TOAST_ERROR: {
            'bg': '#450a0a', 'border': '#ef4444',
            'icon_color': '#f87171', 'icon': '✕',
            'title': '#f0f0f0', 'body': '#f0f0f0',
        },
        TOAST_INFO: {
            'bg': '#0c2340', 'border': '#3b82f6',
            'icon_color': '#60a5fa', 'icon': 'ℹ',
            'title': '#f0f0f0', 'body': '#f0f0f0',
        },
    },
}

_CLOSE_COLORS = {
    'Light': {'normal': '#6b7280', 'hover': '#111827'},
    'Dark':  {'normal': '#6b7280', 'hover': '#ffffff'},
}


def _get_theme_name() -> str:
    """Return the active theme name ('Light' or 'Dark'), defaulting to 'Light'."""
    try:
        from UI.ThemeManager import get_theme_manager
        return get_theme_manager().get_current_theme_name()
    except Exception:
        return 'Light'


class ToastWidget(QWidget):
    """A single, self-dismissing toast notification.

    The background is drawn entirely in paintEvent using QPainter so it is
    immune to the application's global QWidget stylesheet rule.
    """

    dismissed = pyqtSignal(object)

    def __init__(self, title: str, message: str = '', toast_type: str = TOAST_INFO,
                 duration: int = 4000, parent=None):
        super().__init__(parent)

        # Never steal focus or appear in the taskbar / Alt-Tab switcher.
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Prevent Qt from auto-filling the background from the palette —
        # paintEvent is responsible for the entire background.
        self.setAutoFillBackground(False)

        theme = _get_theme_name()
        palette = _THEME_COLORS.get(theme, _THEME_COLORS['Light'])
        c = palette.get(toast_type, palette[TOAST_INFO])
        close_c = _CLOSE_COLORS.get(theme, _CLOSE_COLORS['Light'])

        # Store as QColor objects for use in paintEvent.
        self._bg_color = QColor(c['bg'])
        self._border_color = QColor(c['border'])

        # Shadow: lighter in light theme so it doesn't look too heavy against
        # a white background; stronger in dark theme for separation.
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 50 if theme == 'Light' else 120))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self._build_ui(c, close_c, title, message)

        self.setFixedWidth(340)
        self.adjustSize()

        self._is_dismissed = False
        self._dismiss_timer = None

        if duration > 0:
            self._dismiss_timer = QTimer(self)
            self._dismiss_timer.setSingleShot(True)
            self._dismiss_timer.timeout.connect(self._dismiss)
            self._dismiss_timer.start(duration)

    # Custom painting — bypasses the global stylesheet cascade
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Inset by 0.5 px so the border sits cleanly on a pixel boundary.
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)

        # Fill
        painter.fillPath(path, self._bg_color)

        # Border
        painter.setPen(self._border_color)
        painter.drawPath(path)

    # UI construction
    def _build_ui(self, c: dict, close_c: dict, title: str, message: str):
        # All child labels use transparent backgrounds so the paintEvent
        # background shows through correctly.
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 12, 12)
        root.setSpacing(10)

        # Type icon
        icon_lbl = QLabel(c['icon'])
        icon_lbl.setStyleSheet(
            f"color: {c['icon_color']}; font-size: 14px; font-weight: bold;"
            " background: transparent; border: none;"
        )
        icon_lbl.setFixedWidth(18)
        root.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignTop)

        # Title + body text
        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {c['title']}; font-weight: bold; font-size: 13px;"
            " background: transparent; border: none;"
        )
        title_lbl.setWordWrap(True)
        text_col.addWidget(title_lbl)

        if message:
            display_msg = message if len(message) <= 200 else message[:197] + '…'
            msg_lbl = QLabel(display_msg)
            msg_lbl.setStyleSheet(
                f"color: {c['body']}; font-size: 12px;"
                " background: transparent; border: none;"
            )
            msg_lbl.setWordWrap(True)
            msg_lbl.setMaximumWidth(260)
            text_col.addWidget(msg_lbl)

        root.addLayout(text_col, 1)

        # Dismiss button
        close_btn = QPushButton('×')
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {close_c['normal']};
                background: transparent;
                border: none;
                font-size: 18px;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{ color: {close_c['hover']}; }}
        """)
        close_btn.setFixedSize(20, 20)
        close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_btn.clicked.connect(self._dismiss)
        root.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)

    def _dismiss(self):
        if self._is_dismissed:
            return

        self._is_dismissed = True

        if self._dismiss_timer is not None:
            self._dismiss_timer.stop()
            self._dismiss_timer = None

        self.dismissed.emit(self)
        self.hide()
        self.deleteLater()


class ToastManager:
    """Manages a stack of ToastWidgets anchored to the bottom-right of the
    parent window.  Multiple toasts stack upward.
    """

    _MARGIN = 16
    _SPACING = 8

    def __init__(self, parent_window: QWidget):
        self._parent = parent_window
        self._toasts: list[ToastWidget] = []

    # Public API
    def show_success(self, title: str, message: str = '', duration: int = 3000):
        self._show(TOAST_SUCCESS, title, message, duration)

    def show_error(self, title: str, message: str = '', duration: int = 6000):
        self._show(TOAST_ERROR, title, message, duration)

    def show_persistent_error(self, title: str, message: str = ''):
        """Show an error that stays visible until the user manually dismisses it.
        Use for critical failures (e.g. port-forward collapse) that must not
        auto-dismiss before the user has a chance to see them.
        """
        self._show(TOAST_ERROR, title, message, duration=0)

    def show_info(self, title: str, message: str = '', duration: int = 4000):
        self._show(TOAST_INFO, title, message, duration)

    def reposition(self):
        """Call whenever the parent window resizes."""
        self._reposition()

    # Internal helpers
    def _show(self, toast_type: str, title: str, message: str, duration: int):
        toast = ToastWidget(title, message, toast_type, duration, self._parent)
        toast.dismissed.connect(self._on_dismissed)
        self._toasts.append(toast)

        # Move off-screen before showing so there is no visible flash at (0, 0).
        # Qt needs the widget to be shown before it computes the final geometry,
        # so we show it in an invisible position first, then reposition after
        # one event-loop tick (singleShot 0) once the size is known.
        toast.move(-2000, -2000)
        toast.show()
        toast.raise_()
        QTimer.singleShot(0, self._reposition)

    def _on_dismissed(self, toast: ToastWidget):
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._reposition()

    def _reposition(self):
        if not self._parent:
            return

        pw = self._parent.width()
        ph = self._parent.height()
        y = ph - self._MARGIN

        for toast in reversed(self._toasts):
            if not toast.isVisible():
                continue
            # After show() Qt has set a real height; fall back to sizeHint
            # if for some reason height is still 0.
            th = toast.height() if toast.height() > 0 else toast.sizeHint().height()
            x = pw - toast.width() - self._MARGIN
            y -= th
            toast.move(x, y)
            y -= self._SPACING



# Module-level singleton

_toast_manager: ToastManager | None = None


def initialize_toast_manager(parent_window: QWidget) -> ToastManager:
    """Create the singleton ToastManager bound to the main window.
    Call once from MainWindow.__init__ after the window geometry is established.
    """
    global _toast_manager
    if _toast_manager is not None:
        import logging
        logging.warning("initialize_toast_manager called but a ToastManager already exists; returning existing instance")
        return _toast_manager
    _toast_manager = ToastManager(parent_window)
    return _toast_manager


def get_toast_manager() -> ToastManager | None:
    """Return the singleton ToastManager, or None if not yet initialised."""
    return _toast_manager
