"""
Styles for BaseDetailSection component.
Contains shared styles for all detail sections (Overview, Details, YAML, Events).
"""
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


# SPACING CONSTANTS

SECTION_GAP = 24
SUBSECTION_GAP = 16
FIELD_GAP = 8
CONTENT_PADDING = 20


# ============================================================================
# THEME-AWARE TYPOGRAPHY STYLES (moved from EnhancedStyles)
# ============================================================================

def get_section_header_style():
    """Theme-aware section header style (e.g., 'METADATA', 'STATUS', 'SPEC')"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {theme.colors.TEXT_LIGHT};
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }}
    """


def get_field_label_style():
    """Theme-aware field label style (key names in key-value pairs)"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-size: 13px;
            font-weight: 500;
            color: {theme.colors.ACCENT_BLUE};
        }}
    """


def get_field_value_style():
    """Theme-aware field value style (values in key-value pairs)"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-size: 13px;
            font-weight: normal;
            color: {theme.colors.TEXT_LIGHT};
            line-height: 1.5;
        }}
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


# ============================================================================
# ERROR/INFO WIDGET STYLES (updated to be theme-aware)
# ============================================================================

def get_error_widget_error_style():
    """Error widget style for actual errors (red) - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_DANGER};
            background-color: rgba(255, 68, 68, 0.1);
            padding: 10px;
            border-radius: 4px;
            border: 1px solid rgba(255, 68, 68, 0.3);
        }}
    """


def get_error_widget_info_style():
    """Error widget style for info messages (gray) - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            background-color: rgba(136, 136, 136, 0.1);
            padding: 10px;
            border-radius: 4px;
            border: 1px solid rgba(136, 136, 136, 0.3);
        }}
    """
