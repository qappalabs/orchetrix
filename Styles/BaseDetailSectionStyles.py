"""
Styles for BaseDetailSection component.
Contains shared styles for all detail sections (Overview, Details, YAML, Events).
"""
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def _hex_to_rgba(hex_color, alpha):
    """Convert hex to rgba string"""
    from PyQt6.QtGui import QColor
    color = QColor(hex_color)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


# SPACING CONSTANTS

SECTION_GAP = 16
SUBSECTION_GAP = 12
FIELD_GAP = 4
CONTENT_PADDING = 16


# THEME-AWARE TYPOGRAPHY STYLES (moved from EnhancedStyles)

def get_section_header_style():
    """Theme-aware section header style (e.g., 'METADATA', 'STATUS', 'SPEC')"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-size: 16px;
            font-weight: 700;
            color: {theme.colors.TEXT_SECONDARY};
            letter-spacing: 0.5px;
            margin-bottom: 0px;
        }}
    """


def get_section_header_color():
    """Get the color used for section headers (TEXT_SECONDARY)"""
    return _get_theme().colors.TEXT_SECONDARY


def get_field_label_style():
    """Theme-aware field label style (key names in key-value pairs) - matches SYSTEM INFO reference"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_SECONDARY};
        font-size: 14px;
        font-weight: normal;
    """


def get_field_value_style():
    """Theme-aware field value style (values in key-value pairs) - matches SYSTEM INFO reference"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_LIGHT};
        font-size: 14px;
        font-weight: 600;
    """


def get_primary_text_style():
    """Theme-aware primary text style (main headings, resource names)"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-size: 20px;
            font-weight: bold;
            color: {theme.colors.TEXT_LIGHT};
            padding: 4px 0px;
        }}
    """


def get_secondary_text_style():
    """Theme-aware secondary text style (subtitles, descriptions)"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-size: 14px;
            font-weight: normal;
            color: {theme.colors.TEXT_SUBTLE};
            padding: 2px 0px;
        }}
    """


# ERROR/INFO WIDGET STYLES (updated to be theme-aware)

def get_error_widget_error_style():
    """Error widget style for actual errors (red) - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_DANGER};
            background-color: rgba(255, 68, 68, 26);
            padding: 10px;
            border-radius: 4px;
            border: 1px solid rgba(255, 68, 68, 76);
        }}
    """


def get_error_widget_info_style():
    """Error widget style for info messages (gray) - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            background-color: rgba(136, 136, 136, 26);
            padding: 10px;
            border-radius: 4px;
            border: 1px solid rgba(136, 136, 136, 76);
        }}
    """


# CARD STYLES (moved from OverviewSectionStyles)

def get_info_card_style():
    """Info card container style - theme-aware"""
    theme = _get_theme()
    return f"""
        QFrame#info_card {{
            background-color: {theme.colors.CARD_BG};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 12px;
            min-width: 180px;
        }}
    """


def get_card_title_style():
    """Info card title style - theme-aware"""
    theme = _get_theme()
    return f"""
        font-family: Arial;
        font-size: 10px;
        font-weight: 600;
        color: {theme.colors.TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 0.5px;
    """


def get_card_value_style():
    """Info card value style - theme-aware"""
    theme = _get_theme()
    return f"""
        font-family: Arial;
        font-size: 13px;
        font-weight: 600;
        color: {theme.colors.TEXT_LIGHT};
        margin-top: 1px;
    """


# CONDITION STYLES (moved from OverviewSectionStyles)

def get_condition_badge_true_style():
    """Style for True condition badge"""
    theme = _get_theme()
    bg_color = _hex_to_rgba(theme.colors.STATUS_ACTIVE, 0.15)
    return f"""
        background-color: {bg_color};
        color: {theme.colors.STATUS_ACTIVE};
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 11px;
        font-weight: bold;
    """


def get_condition_badge_false_style():
    """Style for False condition badge"""
    theme = _get_theme()
    bg_color = _hex_to_rgba(theme.colors.TEXT_DANGER, 0.15)
    return f"""
        background-color: {bg_color};
        color: {theme.colors.TEXT_DANGER};
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 11px;
        font-weight: bold;
    """



# STATUS BADGE STYLES (Unified)

def get_status_badge_style(status_type, is_small=False):
    """
    Get a unified badge style for status indicators.
    status_type: 'success', 'warning', 'error', 'default'
    is_small: if True, provides higher-density padding for inline use.
    """
    if status_type == 'success':
        return get_status_badge_success_style(is_small)
    elif status_type == 'warning':
        return get_status_badge_warning_style(is_small)
    elif status_type == 'error':
        return get_status_badge_error_style(is_small)
    else:
        return get_status_badge_default_style(is_small)

def get_custom_badge_style(text_color, is_small=False):
    """Generate a badge style for a custom color."""
    bg_color = _hex_to_rgba(text_color, 0.15)
    return f"""
        QLabel {{
            {_get_badge_base(is_small)}
            background-color: {bg_color};
            color: {text_color};
        }}
    """

def _get_badge_base(is_small=False):
    """Internal helper for shared badge properties"""
    # Use organic padding to shape the pill without hard constraints.
    # A slightly larger bottom padding centers the text nicely in Windows Qt.
    # The border-radius is kept strictly under height/2 to prevent Qt layout clipping.
    padding = "2px 10px 4px 10px" if is_small else "3px 12px 5px 12px"
    font_size = "11px" if is_small else "12px"
    radius = "8px" if is_small else "9px"
    
    return f"""
        padding: {padding};
        border-radius: {radius};
        font-weight: bold;
        font-size: {font_size};
        border: none;
    """


def get_status_badge_success_style(is_small=False):
    theme = _get_theme()
    bg_color = _hex_to_rgba(theme.colors.STATUS_ACTIVE, 0.15)
    return f"""
        QLabel {{
            {_get_badge_base(is_small)}
            background-color: {bg_color};
            color: {theme.colors.STATUS_ACTIVE};
        }}
    """

def get_status_badge_warning_style(is_small=False):
    theme = _get_theme()
    bg_color = _hex_to_rgba(theme.colors.STATUS_WARNING, 0.15)
    return f"""
        QLabel {{
            {_get_badge_base(is_small)}
            background-color: {bg_color};
            color: {theme.colors.STATUS_WARNING};
        }}
    """

def get_status_badge_error_style(is_small=False):
    theme = _get_theme()
    bg_color = _hex_to_rgba(theme.colors.TEXT_DANGER, 0.15)
    return f"""
        QLabel {{
            {_get_badge_base(is_small)}
            background-color: {bg_color};
            color: {theme.colors.TEXT_DANGER};
        }}
    """

def get_status_badge_default_style(is_small=False):
    theme = _get_theme()
    bg_color = _hex_to_rgba(theme.colors.TEXT_SECONDARY, 0.15)
    return f"""
        QLabel {{
            {_get_badge_base(is_small)}
            background-color: {bg_color};
            color: {theme.colors.TEXT_LIGHT};
        }}
    """

def get_condition_message_style():
    """Style for condition detail message"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_SECONDARY};
        font-size: 12px;
        margin-top: 2px;
    """

def get_badge_dot_style(status_bool):
    """Get style for condition status dot (green if True, gray if False)"""
    theme = _get_theme()
    # Use the theme's active-status green so the dot matches the condition badges;
    # fall back to the original Green-500 hex only if the theme key is absent.
    color = (getattr(theme.colors, 'STATUS_ACTIVE', "#22C55E")
             if status_bool else theme.colors.TEXT_SECONDARY)
    return f"""
        background-color: {color};
        border-radius: 4px;
        min-width: 8px;
        max-width: 8px;
        min-height: 8px;
        max-height: 8px;
        border: none;
    """
