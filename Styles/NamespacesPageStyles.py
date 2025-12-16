"""
NamespacesPage-specific styles extracted from NamespacesPage.py
These are unique styles for the NamespacesPage that are not shared with other components.
Note: Shared styles (TABLE_STYLE, CHECKBOX_STYLE, ACTION_BUTTON_STYLE, etc.) use imports from UI/Styles.py
"""

from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_add_namespace_button_style():
    """Style for Add Namespaces button

    Extracted from NamespacesPage.py lines 124-136 (fallback in try/except block)

    Original hardcoded colors:
        background-color: #3d3d3d -> theme.colors.BG_MEDIUM
        color: white -> theme.colors.TEXT_LIGHT
        hover: #333333 -> theme.colors.BG_LIGHT
        pressed: #388E3C -> kept as semantic green (success color)
    """
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            padding: 5px 15px;
            border-radius: 2px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.BG_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: #388E3C;
        }}
    """

