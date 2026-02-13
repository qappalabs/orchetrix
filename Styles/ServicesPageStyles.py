"""
Theme-aware styles for ServicesPage components.
Contains styles that are unique to ServicesPage.
Shared styles (like TABLE_STYLE) should be imported directly from UI.Styles.AppStyles.
"""

from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_port_forward_button_style():
    """Port Forward management button style - theme-aware"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.ACCENT_BLUE};
            color: {theme.colors.TEXT_LIGHT};
            border: none;
            border-radius: 4px;
            padding: 5px 10px;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.ACCENT_BLUE_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.ACCENT_BLUE_PRESSED};
        }}
    """
