"""
PodsPage-specific styles
Contains theme-aware styles for PodsPage following UI restoration rulebook.
"""

from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme for style functions."""
    return get_theme_manager().get_current_theme()


def get_port_forward_button_style():
    """Get theme-aware Port Forwards button style."""
    theme = _get_theme()
    return f"""
QPushButton {{
    background-color: {theme.colors.ACCENT_BLUE};
    color: {theme.colors.TEXT_ON_ACCENT};
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
}}
QPushButton:hover {{
    background-color: {theme.colors.ACCENT_BLUE_HOVER};
}}
QPushButton:pressed {{
    background-color: {theme.colors.ACCENT_BLUE_PRESSED};
}}
QPushButton:disabled {{
    background-color: {theme.colors.BUTTON_DISABLED_BG};
    color: {theme.colors.BUTTON_DISABLED_TEXT};
}}
QPushButton:disabled:hover {{
    background-color: {theme.colors.BUTTON_DISABLED_BG};
}}
"""
