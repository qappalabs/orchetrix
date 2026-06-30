"""
TitleBar-specific styles with theme-aware support.
Contains styles for the custom window title bar including icon buttons,
window controls (minimize, maximize, close), and cluster indicator.
"""
from UI.ThemeManager import get_theme_manager

def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()

def get_title_bar_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_DARK};
            color: {theme.colors.TEXT_LIGHT};
        }}
    """

def get_title_bar_bottom_frame_style():
    theme = _get_theme()
    return f"""
        QFrame {{
            background-color: {theme.colors.BORDER_COLOR};
            min-height: 1px;
            max-height: 1px;
        }}
    """

def get_icon_button_style():
    theme = _get_theme()
    return f"""
        QToolButton {{
            background-color: transparent;
            color: {theme.colors.TEXT_LIGHT};
            border: none;
            font-size: 16px;
        }}
        QToolButton:hover {{
            background-color: {theme.colors.HOVER_BG};
            border-radius: 4px;
        }}
    """

def get_window_control_style():
    theme = _get_theme()
    return f"""
        QToolButton {{
            background-color: transparent;
            color: {theme.colors.TEXT_SECONDARY};
            border: none;
            font-size: 10px;
            min-width: 46px;
            min-height: 30px;
            padding: 0px;
            margin: 0px;
        }}
        QToolButton:hover {{
            background-color: {theme.colors.HOVER_BG};
            color: {theme.colors.TEXT_LIGHT};
            border-radius: 0px;
        }}
    """

def get_close_button_style():
    theme = _get_theme()
    return f"""
        QToolButton {{
            background-color: transparent;
            color: {theme.colors.TEXT_SECONDARY};
            border: none;
            font-size: 10px;
            min-width: 46px;
            min-height: 30px;
            padding: 0px;
            margin: 0px;
        }}
        QToolButton:hover {{
            background-color: #E81123;
            color: white;
            border-radius: 0px;
        }}
    """

def get_pinned_cluster_container_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BORDER_DARK};
            border-radius: 4px;
        }}
    """

