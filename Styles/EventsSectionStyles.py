"""
Styles for DetailPageEventsSection component.
Contains only page-specific unique styles.
Shared styles should be imported directly from UI.Styles.AppStyles.
"""
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_events_list_style():
    """Events list widget style - uses unified AppStyles scrollbar for consistency"""
    from UI.Styles import AppStyles
    theme = _get_theme()
    return f"""
        QListWidget {{
            background-color: {theme.colors.BG_SIDEBAR};
            border: none;
            outline: none;
        }}
        QListWidget::item {{
            border-bottom: 1px solid {theme.colors.BORDER_COLOR};
            padding: 0px;
        }}
        QListWidget::item:hover {{
            background-color: {theme.colors.HOVER_BG};
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """


def get_no_events_color():
    """Color for 'no events' message - theme-aware"""
    theme = _get_theme()
    return theme.colors.TEXT_SUBTLE


def get_no_events_foreground_color():
    """Foreground color for 'no events found' item"""
    theme = _get_theme()
    return theme.colors.TEXT_SUBTLE


def get_event_widget_style():
    """Event widget container style - hardcoded transparent"""
    return "background-color: transparent;"


def get_event_type_warning_style():
    """Event type badge style for Warning events"""
    theme = _get_theme()
    # rgba background is hardcoded as it's a semantic color for warnings
    return f"""
        color: {theme.colors.TEXT_WARNING};
        font-weight: bold;
        padding: 2px 6px;
        background-color: rgba(255, 152, 0, 0.1);
        border-radius: 3px;
    """


def get_event_type_normal_style():
    """Event type badge style for Normal events"""
    theme = _get_theme()
    # rgba background is hardcoded as it's a semantic color for success
    return f"""
        color: {theme.colors.TEXT_SUCCESS};
        font-weight: bold;
        padding: 2px 6px;
        background-color: rgba(76, 175, 80, 0.1);
        border-radius: 3px;
    """


def get_event_reason_style():
    """Event reason label style"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_LIGHT};
        font-weight: bold;
    """


def get_event_age_style():
    """Event age label style"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_SUBTLE};
        font-size: 11px;
    """


def get_event_message_style():
    """Event message label style"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_SECONDARY};
        font-size: 12px;
        line-height: 1.4;
    """
