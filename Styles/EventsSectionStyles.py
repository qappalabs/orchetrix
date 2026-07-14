"""
Styles for DetailPageEventsSection component.
Contains only page-specific unique styles.
Shared styles should be imported directly from UI.Styles.AppStyles.
"""
from UI.Styles import AppStyles
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_events_list_style():
    """Events list widget style - uses unified AppStyles scrollbar for consistency"""
    theme = _get_theme()
    return f"""
        QListWidget {{
            background-color: transparent;
            border: none;
            outline: none;
        }}
        QListWidget::item {{
            padding: 2px 0px; 
            border: none;
        }}
        QListWidget::item:hover {{
            background-color: transparent;
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
    """Event widget container style - Matches Overview Card style"""
    theme = _get_theme()
    return f"""
        QFrame#event_card {{
            background-color: {theme.colors.CARD_BG};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 12px;
        }}
    """


def get_event_reason_style():
    """Event reason label style"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_LIGHT};
        font-size: 13px;
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
        font-size: 13px;
    """

