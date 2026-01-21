"""
logs_components-specific styles
Contains theme-aware styles for logs_components following UI restoration rulebook.
"""

from UI.Styles import AppStyles
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme for style functions."""
    return get_theme_manager().get_current_theme()


# LogsHeaderWidget styles (theme-aware)

def get_logs_header_widget_style():
    """Get theme-aware header widget style."""
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BACKGROUND_SECONDARY};
            border-bottom: 1px solid {theme.colors.BORDER_COLOR};
        }}
        QComboBox {{
            background-color: {theme.colors.BACKGROUND_DARK};
            border: 1px solid {theme.colors.BORDER_DARK};
            border-radius: 4px;
            padding: 4px 8px;
            color: {theme.colors.TEXT_PRIMARY};
            font-size: 12px;
            min-width: 80px;
            max-height: 24px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme.colors.BACKGROUND_SECONDARY};
            color: {theme.colors.TEXT_PRIMARY};
            selection-background-color: {theme.colors.ACCENT_BLUE};
        }}
        QCheckBox {{
            color: {theme.colors.TEXT_PRIMARY};
            font-size: 12px;
            padding: 2px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 2px solid {theme.colors.BORDER_DARK};
            border-radius: 3px;
            background: transparent;
        }}
        QCheckBox::indicator:checked {{
            background-color: {theme.colors.ACCENT_BLUE};
            border-color: {theme.colors.ACCENT_BLUE};
        }}
        QLabel {{
            color: {theme.colors.TEXT_PRIMARY};
            font-size: 12px;
        }}
    """


def get_pod_info_label_style():
    """Get theme-aware pod info label style."""
    theme = _get_theme()
    return f"font-weight: bold; color: {theme.colors.STATUS_ACTIVE}; font-size: 11px;"


def get_search_results_label_style():
    """Get theme-aware search results label style."""
    theme = _get_theme()
    return f"color: {theme.colors.STATUS_ACTIVE}; font-size: 10px; font-weight: bold;"


# EnhancedLogsViewer styles (theme-aware)

def get_logs_display_style():
    """Get theme-aware logs display text edit style."""
    theme = _get_theme()
    return f"""
        QTextEdit {{
            background-color: {theme.colors.BACKGROUND_DARK};
            color: {theme.colors.TEXT_SECONDARY};
            border: none;
            selection-background-color: {theme.colors.SELECTED_BG};
            padding: 8px;
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """


def get_status_indicator_style_with_color(color: str):
    """Get theme-aware status indicator style with custom color."""
    theme = _get_theme()
    return f"""
        QLabel {{
            background-color: {theme.colors.BACKGROUND_SECONDARY}CC;
            color: {color};
            font-size: 11px;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            margin: 4px;
        }}
    """


def get_status_indicator_style():
    """Get theme-aware default status indicator style."""
    theme = _get_theme()
    return get_status_indicator_style_with_color(theme.colors.STATUS_ACTIVE)
