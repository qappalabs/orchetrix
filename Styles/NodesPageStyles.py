"""
NodesPage-specific styles extracted from the original NodesPage.py
These are UNIQUE styles for the Nodes page that are not shared with other components.

Note: Shared styles (TABLE_STYLE, CHECKBOX_STYLE, MENU_STYLE, HOME_ACTION_BUTTON_STYLE, 
      ACTION_CONTAINER_STYLE, CUSTOM_HEADER_STYLE, status colors) remain in UI/Styles.py
"""

from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()



# NoDataWidget styles - hardcoded decorative colors (stays as-is per instructions)
def get_no_data_icon_style():
    """Style for no data widget icon - hardcoded decorative color"""
    return "font-size: 48px; color: #666;"


def get_no_data_message_style():
    """Style for no data widget message - hardcoded decorative color"""
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




def get_status_active_color():
    """Get theme-aware status active color"""
    theme = _get_theme()
    return theme.colors.STATUS_ACTIVE


def get_status_disconnected_color():
    """Get theme-aware status disconnected color"""
    theme = _get_theme()
    return theme.colors.STATUS_DISCONNECTED
