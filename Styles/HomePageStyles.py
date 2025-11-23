from UI.ThemeManager import get_theme_manager
from PyQt6.QtGui import QFont


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


# Theme-aware style functions
def get_sidebar_button_style():
    return _get_theme().get_sidebar_button_style()

def get_sidebar_container_style():
    return _get_theme().get_sidebar_style()

def get_top_bar_style():
    return _get_theme().get_top_bar_style()

def get_tree_widget_style():
    return _get_theme().get_tree_widget_style()

def get_menu_style():
    return _get_theme().get_menu_style()

def get_search_style():
    return _get_theme().get_search_bar_style()

def get_content_area_style():
    return _get_theme().get_content_area_style()

def get_action_container_style():
    return """
        background-color: transparent;
        border: none;
        margin: 0;
        padding: 0;
    """

def get_home_action_button_style():
    return _get_theme().get_action_button_style()

def get_home_action_button_disabled_style():
    """Get disabled state style for action button"""
    return get_home_action_button_style() + " QToolButton:disabled { opacity: 0.5; background-color: transparent; }"

def get_status_color(status):
    """Get theme-aware color for status labels"""
    theme = _get_theme()
    status_map = {
        "available": theme.colors.ACCENT_GREEN,
        "active": theme.colors.ACCENT_GREEN,
        "connected": theme.colors.ACCENT_GREEN,
        "disconnect": theme.colors.ACCENT_RED,
        "connecting": theme.colors.ACCENT_ORANGE,
        "loading": theme.colors.ACCENT_ORANGE
    }
    return status_map.get(status, theme.colors.ACCENT_RED)

def get_browser_label_style():
    """Get theme-aware browser label style"""
    theme = _get_theme()
    return f"font-weight: bold; font-size: 16px; color: {theme.colors.TEXT_LIGHT};"

def get_items_label_style():
    """Get theme-aware items count label style"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_SUBTLE}; margin-left: 10px; font-size: 14px;"

def get_cell_label_style():
    """Get theme-aware cell label style"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; background: transparent; padding: 0px; margin: 0px;"

def get_pin_button_style():
    """Get theme-aware pin button style"""
    theme = _get_theme()
    # Use theme-aware hover color
    hover_bg = "rgba(255, 255, 255, 0.1)" if hasattr(theme.colors, 'BG_DARK') else "rgba(0, 0, 0, 0.1)"
    return f"""
        QPushButton {{ background: transparent; border: none; padding: 0px; margin: 0px; }}
        QPushButton:hover {{ background: {hover_bg}; }}
    """


def get_status_label_style(color):
    """Get status label style with dynamic color"""
    return f"color: {color}; background: transparent;"


def get_cell_font():
    """Get reusable font for table cells"""
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    return font


# Theme-neutral constants (no colors)
TRANSPARENT_WIDGET = "background: transparent; padding: 0px; margin: 0px;"
STATUS_CELL = "QWidget#statusCell { background: transparent; }"
