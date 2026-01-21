"""
ChartsPage-specific styles
Contains styles that are unique to ChartsPage and defined inline in the page.
"""

from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_repository_label_style():
    """Style for repository label"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; font-size: 12px; font-weight: normal;"


def get_loading_bar_style():
    """Style for loading progress bar"""
    theme = _get_theme()
    return f"""
        QProgressBar {{
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 2px;
            background-color: {theme.colors.BG_DARKER};
            height: 10px;
        }}
        QProgressBar::chunk {{
            background-color: {theme.colors.ACCENT_BLUE};
        }}
    """


def get_loading_text_style():
    """Style for loading text"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px;"


def get_icon_label_default_style():
    """Default style for icon labels (chart icons)"""
    theme = _get_theme()
    return f"""
        QLabel {{
            border-radius: 3px;
            background-color: {theme.colors.HOVER_BG};
            border: none;
            padding: 0px;
            margin: 0px;
        }}
    """


def get_icon_label_emoji_style():
    """Style for icon label with emoji fallback"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.STATUS_ACTIVE};
            font-size: 14px;
            border-radius: 3px;
            background-color: {theme.colors.HOVER_BG};
            border: none;
            padding: 0px;
            margin: 0px;
        }}
    """


def get_chart_detail_dialog_style() -> str:
    """Style for chart detail dialog window"""
    theme = _get_theme()
    return f"""
        QDialog {{
            background-color: {theme.colors.BG_DARK};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 8px;
        }}
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            color: {theme.colors.TEXT_LIGHT};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }}
    """


def get_detail_icon_label_style() -> str:
    """Style for icon label in detail dialog"""
    theme = _get_theme()
    return f"border: 1px solid {theme.colors.BORDER_COLOR}; border-radius: 8px;"


def get_chart_name_label_style() -> str:
    """Style for chart name label in detail dialog"""
    theme = _get_theme()
    return f"color: {theme.colors.ACCENT_BLUE}; margin-bottom: 5px;"


def get_description_text_style() -> str:
    """Style for description text edit"""
    theme = _get_theme()
    return f"QTextEdit {{ background-color: {theme.colors.BG_MEDIUM}; border: 1px solid {theme.colors.BORDER_COLOR}; color: {theme.colors.TEXT_LIGHT}; }}"
