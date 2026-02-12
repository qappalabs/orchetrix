"""
ChartsPage-specific styles
Contains styles that are unique to ChartsPage and defined inline in the page.
"""

from UI.ThemeManager import get_theme_manager, BaseTheme


def _get_theme() -> BaseTheme:
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_repository_label_style() -> str:
    """Style for repository label"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; font-size: 12px; font-weight: normal;"


def get_loading_bar_style() -> str:
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


def get_loading_text_style() -> str:
    """Style for loading text"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px;"


def _build_icon_label_style(
    color: str | None = None, font_size: str | None = None
) -> str:
    """
    Build icon label style with optional color and font size.

    Args:
        color: Optional text color (e.g., theme.colors.STATUS_ACTIVE)
        font_size: Optional font size (e.g., '14px')

    Returns:
        CSS style string for QLabel
    """
    theme = _get_theme()
    extra_styles = ""
    if color:
        extra_styles += f"color: {color};\n            "
    if font_size:
        extra_styles += f"font-size: {font_size};\n            "

    return f"""
        QLabel {{
            {extra_styles}border-radius: 3px;
            background-color: {theme.colors.HOVER_BG};
            border: none;
            padding: 0px;
            margin: 0px;
        }}
    """


def get_icon_label_default_style() -> str:
    """Default style for icon labels (chart icons)"""
    return _build_icon_label_style()


def get_icon_label_emoji_style() -> str:
    """Style for icon label with emoji fallback"""
    theme = _get_theme()
    return _build_icon_label_style(
        color=theme.colors.STATUS_ACTIVE, font_size="14px"
    )


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
