"""
NodesPage-specific styles extracted from NodesPage.
These are styles that are currently unique to the Nodes page.

Notes:
- Shared styles (table/menu/action button/checkbox/header) remain in UI/Styles.py via theme-aware helpers.
- Legacy AppStyles/AppColors constants in UI/Styles.py are kept as-is for backward compatibility.
"""

from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()



# NoDataWidget styles - INTENTIONALLY NOT THEME-AWARE
# Reason: icon_label uses emoji (ignores CSS color), message_label is a simple
# gray placeholder text that works on both light/dark backgrounds.
def get_no_data_icon_style():
    """Style for no data widget icon - static color (emoji ignores this)"""
    return "font-size: 48px; color: #666;"


def get_no_data_message_style():
    """Style for no data widget message - static gray works on both themes"""
    return "font-size: 18px; color: #666;"


# Graph paintEvent colors - theme-aware
def get_graph_time_label_color():
    """Color for graph time labels - theme-aware"""
    theme = _get_theme()
    return theme.colors.TEXT_LIGHT


def get_text_subtle_color():
    """Color for graph placeholder text - theme-aware"""
    theme = _get_theme()
    return theme.colors.TEXT_SUBTLE


def get_row_highlight_color():
    """Color for row highlighting - theme-aware"""
    theme = _get_theme()
    return theme.colors.ACCENT_BLUE


# Graph accent colors - theme-aware
def get_cpu_graph_color():
    """CPU graph color - theme-aware accent"""
    theme = _get_theme()
    return theme.colors.ACCENT_ORANGE


def get_memory_graph_color():
    """Memory graph color - theme-aware accent"""
    theme = _get_theme()
    return theme.colors.ACCENT_BLUE


def get_disk_graph_color():
    """Disk graph color - theme-aware accent"""
    theme = _get_theme()
    return theme.colors.ACCENT_PURPLE


# Graph widget QSS (currently NodesPage-only) - theme-aware
def get_graph_frame_style():
    """QFrame style for NodesPage graphs - theme-aware"""
    theme = _get_theme()
    return f"""
        QFrame {{
            background-color: {theme.colors.CARD_BG};
            border-radius: 4px;
            border: 1px solid {theme.colors.BORDER_COLOR};
        }}
    """


def get_graph_title_style():
    """QLabel style for NodesPage graph titles - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 14px;
            font-weight: bold;
        }}
    """


def get_graph_value_style(color: str):
    """QLabel style for NodesPage graph values - color provided by caller"""
    return f"""
        QLabel {{
            color: {color};
            font-size: 16px;
            font-weight: bold;
        }}
    """




def get_status_active_color():
    theme = _get_theme()
    return theme.colors.STATUS_ACTIVE


def get_status_disconnected_color():
    """Get theme-aware status disconnected color"""
    theme = _get_theme()
    return theme.colors.STATUS_DISCONNECTED
