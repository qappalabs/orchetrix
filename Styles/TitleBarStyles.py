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

def get_pinned_cluster_icon_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            background-color: {theme.colors.BORDER_DARK};
            border: none;
            margin: 0px;
        }}
    """

def get_pinned_cluster_label_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            background-color: {theme.colors.BORDER_DARK};
            color: {theme.colors.TEXT_LIGHT};
            padding: 0px 4px;
            font-size: 14px;
            font-family: 'Segoe UI', sans-serif;
            border: none;
            margin: 0px;
        }}
    """

def get_pinned_cluster_arrow_style():
    theme = _get_theme()
    return f"""
        QToolButton {{
            background-color: {theme.colors.BORDER_DARK};
            border: none;
            border-left: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 0 4px 4px 0;
            margin: 0px;
        }}
        QToolButton:hover {{
            background-color: {theme.colors.BG_LIGHT};
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

def get_dropdown_menu_style():
    theme = _get_theme()
    return f"""
        QMenu {{
            background-color: {theme.colors.BORDER_DARK};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            padding: 5px;
        }}
        QMenu::item {{
            padding: 5px 20px;
        }}
        QMenu::item:selected {{
            background-color: {theme.colors.SELECTED_BG};
        }}
    """

def get_search_input_style():
    theme = _get_theme()
    return f"""
        QLineEdit {{
            background-color: {theme.colors.BORDER_DARK};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 4px;
            padding: 5px;
            margin-bottom: 5px;
        }}
        QLineEdit[placeholderText="Search..."] {{
            color: {theme.colors.TEXT_SUBTLE};
        }}
    """
