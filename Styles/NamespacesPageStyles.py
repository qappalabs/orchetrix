"""
NamespacesPage-specific styles
Contains styles that are unique to NamespacesPage and defined inline in the page.
"""

from UI.ThemeManager import get_theme_manager

def get_add_namespace_button_style():
    """Theme-aware button style for add namespace button"""
    theme = get_theme_manager().get_current_theme()
    
    return f"""
        QPushButton {{
            background-color: {theme.colors.BUTTON_BG};
            color: {theme.colors.BUTTON_TEXT};
            padding: 5px 15px;
            border-radius: 2px;
            border: 1px solid {theme.colors.BORDER_COLOR};
        }}
        QPushButton:hover {{
            background-color: {theme.colors.BUTTON_HOVER_BG};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.ACCENT_BLUE};
        }}
        QPushButton:disabled {{
            background-color: {theme.colors.BUTTON_DISABLED_BG};
            color: {theme.colors.BUTTON_DISABLED_TEXT};
        }}
    """
