import logging
from PyQt6.QtWidgets import QWidget, QMainWindow
from UI.ThemeManager import get_theme_manager

logger = logging.getLogger(__name__)


class ThemeAwareMixin:
    """Mixin for pages that need to refresh when theme changes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connect_theme_manager()

    def _connect_theme_manager(self):
        get_theme_manager().theme_changed.connect(self._on_theme_changed)
        # Disconnect on C++ destruction so the singleton ThemeManager stops
        # holding a bound-method reference to this widget. Without this, the
        # Python wrapper outlives the C++ half and the next theme_changed
        # emission fires _on_theme_changed on a zombie, raising
        # "wrapped C/C++ object ... has been deleted".
        self.destroyed.connect(self._disconnect_theme_manager)

    def _disconnect_theme_manager(self, _obj=None):
        try:
            get_theme_manager().theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            logger.debug(
                "Teardown diagnostic: Failed to disconnect get_theme_manager().theme_changed in _disconnect_theme_manager.",
                exc_info=True
            )

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
