from PyQt6.QtWidgets import QWidget, QMainWindow
from UI.ThemeManager import get_theme_manager


class ThemeAwareMixin:
    """Mixin for pages that need to refresh when theme changes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connect_theme_manager()

    def _connect_theme_manager(self):
        """Connect to theme changes - call this in __init__ after super().__init__()"""
        get_theme_manager().theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name):
        """Override this method in subclasses to refresh widgets when theme changes"""
        pass


class ThemeAwarePage(ThemeAwareMixin, QWidget):
    """Base class for QWidget-based pages that need theme support"""

    def __init__(self, parent=None):
        super().__init__(parent)


class ThemeAwareMainWindow(ThemeAwareMixin, QMainWindow):
    """Base class for QMainWindow-based pages that need theme support"""

    def __init__(self, parent=None):
        super().__init__(parent)
