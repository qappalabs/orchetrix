"""
Theme-aware styles for Sidebar component.
Migrated from UI/Styles.py AppStyles and AppColors.
"""
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


# Nav menu dropdown styles
def get_nav_menu_dropdown_style():
    """Theme-aware dropdown menu style for navigation buttons"""
    theme = _get_theme()
    return f"""
        QMenu {{
            background-color: {theme.colors.BG_MEDIUM};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 6px;
            padding: 5px;
        }}
        QMenu::item {{
            padding: 1px 16px;
            border-radius: 4px;
            margin: 2px 5px;
            color: {theme.colors.TEXT_LIGHT};
            font-size: 14px;
        }}
        QMenu::item:selected {{
            background-color: {theme.colors.SELECTED_BG};
        }}
        QMenu::item[under_development="true"] {{
            color: #FF9500 !important;
            background-color: rgba(255, 149, 0, 0.15) !important;
        }}
        QMenu::item[under_development="true"]:hover {{
            color: #FF9500 !important;
            background-color: rgba(255, 149, 0, 0.25) !important;
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {theme.colors.BORDER_LIGHT};
            margin: 5px 10px;
        }}
    """


# Sidebar toggle button styles
def get_sidebar_toggle_button_style():
    """Theme-aware toggle button style"""
    theme = _get_theme()
    return f"""
        QToolButton {{
            background-color: transparent;
            border-top: none;
        }}
        QToolButton:hover {{
            background-color: {theme.colors.HOVER_BG};
        }}
    """


# Nav icon button styles
def get_nav_icon_button_expanded_style(background_color, text_color):
    """Theme-aware expanded nav button style"""
    theme = _get_theme()
    return f"""
        QToolButton {{
            background-color: {background_color};
            border: none;
            border-radius: 0;
            text-align: left;
        }}
        QToolButton:hover {{
            background-color: {theme.colors.SIDEBAR_HOVER_BG};
        }}
    """


def get_nav_icon_button_collapsed_style(background_color, text_color):
    """Theme-aware collapsed nav button style"""
    theme = _get_theme()
    return f"""
        QToolButton {{
            background-color: {background_color};
            color: {text_color};
            border: none;
            border-radius: 0;
            padding-left: 10px;
            text-align: left;
        }}
        QToolButton:hover {{
            background-color: {theme.colors.SIDEBAR_HOVER_BG};
        }}
    """


def get_nav_icon_button_icon_label_style():
    """Theme-aware icon label style"""
    theme = _get_theme()
    return f"""
        QLabel {{
            background-color: transparent;
            color: {theme.colors.TEXT_SUBTLE};
        }}
    """


def get_nav_icon_button_text_label_style():
    """Theme-aware text label style"""
    theme = _get_theme()
    return f"""
        QLabel {{
            background-color: transparent;
            color: {theme.colors.TEXT_SUBTLE};
        }}
    """


def get_nav_icon_button_dropdown_label_style():
    """Theme-aware dropdown indicator label style"""
    theme = _get_theme()
    return f"""
        QLabel {{
            background-color: transparent;
            color: {theme.colors.TEXT_SUBTLE};
        }}
    """


# Sidebar container styles
def get_sidebar_style():
    """Theme-aware sidebar container style"""
    theme = _get_theme()
    return f"""
        #sidebar_content {{
            background-color: {theme.colors.BG_SIDEBAR};
            border-top: 1px solid {theme.colors.BORDER_COLOR};
        }}
    """


def get_sidebar_border_style():
    """Theme-aware sidebar border style"""
    theme = _get_theme()
    return f"color: {theme.colors.BORDER_LIGHT};"


def get_sidebar_controls_style():
    """Theme-aware sidebar controls style"""
    theme = _get_theme()
    return f"""
        QWidget#sidebar_controls {{
            background-color: {theme.colors.BG_SIDEBAR};
        }}
    """


def get_divider_style():
    """Theme-aware divider style for utility section"""
    theme = _get_theme()
    return f"background-color: {theme.colors.BORDER_LIGHT}; margin: 8px 10px;"


# Helper functions for dynamic colors
def get_hover_bg():
    """Get theme-aware hover background color"""
    return _get_theme().colors.HOVER_BG


def get_sidebar_active_bg():
    """Get theme-aware sidebar active/selected background color"""
    return _get_theme().colors.SIDEBAR_ACTIVE_BG


def get_sidebar_active_text():
    """Get theme-aware sidebar active/selected text color"""
    return _get_theme().colors.SIDEBAR_ACTIVE_TEXT


def get_text_light():
    """Get theme-aware light text color"""
    return _get_theme().colors.TEXT_LIGHT


def get_text_subtle():
    """Get theme-aware subtle text color"""
    return _get_theme().colors.TEXT_SUBTLE
