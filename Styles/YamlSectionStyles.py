"""
Styles for DetailPageYAMLSection component.
Contains only page-specific unique styles.
Shared styles (like UNIFIED_SCROLL_BAR_STYLE) should be imported directly from UI.Styles.AppStyles.
"""
from UI.ThemeManager import get_theme_manager
from UI.Styles import AppStyles


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_search_widget_style():
    """Search widget container and child elements style - theme-aware"""
    theme = _get_theme()
    return f"""
        QFrame {{
            background-color: {theme.colors.BG_HEADER};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
        }}
        QLineEdit {{
            background-color: {theme.colors.BG_DARK};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 3px;
            padding: 5px;
            font-size: 12px;
        }}
        QLineEdit:focus {{
            border: 1px solid {theme.colors.ACCENT_BLUE};
        }}
        QPushButton {{
            background-color: {theme.colors.BG_DARK};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 3px;
            padding: 4px 8px;
            font-size: 11px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.HOVER_BG_DARKER};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.BG_MEDIUM};
        }}
        QLabel {{
            color: {theme.colors.TEXT_SECONDARY};
            font-size: 11px;
        }}
    """


def get_yaml_toolbar_style():
    """YAML toolbar container style - theme-aware"""
    theme = _get_theme()
    return f"""
        background-color: {theme.colors.BG_DARK};
        border-bottom: 1px solid {theme.colors.BORDER_COLOR};
    """


def get_yaml_edit_button_style():
    """Edit button style - theme-aware"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 4px;
            padding: 5px 15px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.BG_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.BG_SIDEBAR};
        }}
        QPushButton:disabled {{
            background-color: {theme.colors.TEXT_SUBTLE};
            color: {theme.colors.TEXT_SECONDARY};
        }}
    """


def get_yaml_save_button_style():
    """Deploy/Save button style - hardcoded green theme"""
    return """
        QPushButton {
            background-color: #4CAF50;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        QPushButton:disabled {
            background-color: #555555;
            color: #888888;
        }
    """


def get_yaml_cancel_button_style():
    """Cancel button style - hardcoded red theme"""
    return """
        QPushButton {
            background-color: #f44336;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            background-color: #d32f2f;
        }
        QPushButton:pressed {
            background-color: #b71c1c;
        }
    """


def get_helm_status_label_style():
    """Helm resource warning label style - hardcoded orange"""
    return """
        QLabel {
            color: #ff9800;
            font-style: italic;
            padding: 5px;
        }
    """


def get_yaml_editor_readonly_style():
    """YAML editor style in read-only mode - hardcoded VS Code dark theme
    
    Note: YAML editor colors are intentionally hardcoded to maintain
    VS Code-like syntax highlighting consistency regardless of app theme.
    """
    return f"""
        QTextEdit {{
            background-color: #1E1E1E;
            color: #D4D4D4;
            border: none;
            selection-background-color: #264F78;
            selection-color: #D4D4D4;
            padding: 20px;
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """


def get_yaml_editor_edit_style():
    """YAML editor style in edit mode - hardcoded VS Code dark theme with blue border
    
    Note: YAML editor colors are intentionally hardcoded to maintain
    VS Code-like syntax highlighting consistency regardless of app theme.
    """
    return f"""
        QTextEdit {{
            background-color: #1E1E1E;
            color: #D4D4D4;
            border: 1px solid #0078d7;
            selection-background-color: #264F78;
            selection-color: #D4D4D4;
            padding: 20px;
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """
