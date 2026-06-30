"""
EventsPage - specific styles
Contains styles that are unique to EventsPage and defined inline in the page.
"""

from UI.ThemeManager import get_theme_manager

# Event type colors mapping for consistent styling across the application
TYPE_COLORS = {
    "Normal": "#4CAF50",      # Green for normal events
    "Warning": "#FF9800",     # Orange for warnings
    "Error": "#F44336",       # Red for errors
    "FailedMount": "#F44336",  # Red for failed mounts
    "Failed": "#F44336",      # Red for failed events
    "FailedScheduling": "#F44336",  # Red for scheduling failures
    "Unhealthy": "#FF5722",   # Deep orange for health issues
    "BackOff": "#FF9800",     # Orange for backoff events
    "Killing": "#FF5722",     # Deep orange for killing events
    "Created": "#2196F3",     # Blue for creation events
    "Started": "#4CAF50",     # Green for started events
    "Pulled": "#4CAF50",      # Green for successful pulls
    "Scheduled": "#4CAF50",   # Green for successful scheduling
}

# Theme-aware column colors for EventsPage
def get_message_color():
    """Color for event message column"""
    theme = get_theme_manager().get_current_theme()
    return theme.colors.TEXT_LIGHT


def get_namespace_color():
    """Color for namespace column"""
    return "#64B5F6"  # Light blue


def get_object_color():
    """Color for involved object column"""
    return "#81C784"  # Light green


def get_source_color():
    """Color for source column"""
    return "#FFB74D"  # Light orange


def get_count_high_color():
    """Color for high count values (>10)"""
    return "#F44336"  # Red


def get_count_medium_color():
    """Color for medium count values (6-10)"""
    return "#FF9800"  # Orange


def get_count_low_color():
    """Color for low count values (1-5)"""
    return "#4CAF50"  # Green


def get_timestamp_color():
    """Color for age and last seen timestamp columns"""
    return "#B0BEC5"  # Light gray


def get_error_message_color():
    """Color for error/warning message text"""
    return "#F44336"  # Red


def get_warning_message_color():
    """Color for warning message text"""
    return "#FF9800"  # Orange


def get_header_style():
    theme = get_theme_manager().get_current_theme()
    return f"""
            QHeaderView::section {{
                background-color: {theme.colors.HEADER_BG};
                color: {theme.colors.TEXT_LIGHT};
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid {theme.colors.BORDER_COLOR};
                border-right: 1px solid {theme.colors.BORDER_COLOR};
                font-size: 12px;
                font-weight: bold;
                text-align: center;
                margin: 0px;
            }}
            QHeaderView::section:hover {{
                background-color: {theme.colors.BG_MEDIUM};
                color: {theme.colors.TEXT_LIGHT};
            }}
            QHeaderView::section:first {{
                border-left: 1px solid {theme.colors.BORDER_COLOR};
                padding-left: 0px;
                margin-left: 0px;
            }}
            QHeaderView::section:pressed {{
                background-color: {theme.colors.BG_DARKER};
                color: {theme.colors.TEXT_LIGHT};
            }}
        """


def get_action_button_style():
    theme = get_theme_manager().get_current_theme()
    return f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 3px;
                margin: 0px;
                color: {theme.colors.TEXT_SECONDARY};
            }}
            QToolButton:hover {{
                background-color: {theme.colors.HOVER_BG};
                color: {theme.colors.TEXT_LIGHT};
            }}
            QToolButton:pressed {{
                background-color: {theme.colors.HOVER_BG_DARKER};
            }}
            QToolButton::menu-indicator {{
                image: none;
                width: 0px;
                height: 0px;
            }}
        """


def get_menu_style():
    theme = get_theme_manager().get_current_theme()
    return f"""
            QMenu {{
                background-color: {theme.colors.BG_DARKER};
                border: 1px solid {theme.colors.BORDER_COLOR};
                border-radius: 6px;
                padding: 4px;
                color: {theme.colors.TEXT_LIGHT};
            }}
            QMenu::item {{
                color: {theme.colors.TEXT_LIGHT};
                padding: 8px 12px;
                border-radius: 3px;
                font-size: 12px;
                margin: 1px 0px;
                min-width: 80px;
            }}
            QMenu::item:selected {{
                background-color: {theme.colors.SELECTED_BG};
                color: {theme.colors.TEXT_LIGHT};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {theme.colors.BORDER_COLOR};
                margin: 3px 6px;
            }}
        """

# Transparent action container style (no theme color needed)
ACTION_CONTAINER_STYLE = """
    QWidget {
        background-color: transparent;
        border: none;
        margin: 0px;
        padding: 0px;
    }
"""

# Inactive action container style (no theme color needed)
ACTION_CONTAINER_INACTIVE_STYLE = """
    QWidget {
        background-color: transparent;
        border: none;
    }
"""

# Active action container style (hardcoded fallback; prefer get_action_container_active_style() for full theme-awareness)
ACTION_CONTAINER_ACTIVE_STYLE = """
    QWidget {
        background-color: rgba(0, 149, 255, 0.08);
        border-radius: 4px;
    }
"""


def get_action_container_active_style():
    theme = get_theme_manager().get_current_theme()

    # Convert hex accent color to rgba with 0.08 alpha (matching original opacity)
    # ACCENT_BLUE is typically "#0095FF" -> rgb(0, 149, 255)
    r, g, b = _parse_hex_color(theme.colors.ACCENT_BLUE, default=(0, 149, 255))

    return f"""
                    QWidget {{
                        background-color: rgba({r}, {g}, {b}, 0.08);
                        border-radius: 4px;
                    }}
                """


def _parse_hex_color(hex_color, default=(0, 0, 0)):
    """Helper to safely parse hex color string into (r, g, b) tuple."""
    try:
        if not hex_color or not isinstance(hex_color, str):
            return default
            
        hex_clean = hex_color.lstrip('#')
        
        # Handle 3-char shorthand (e.g., "09F" -> "0099FF")
        if len(hex_clean) == 3:
            hex_clean = "".join([c*2 for c in hex_clean])
            
        if len(hex_clean) != 6:
            return default
            
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        return (r, g, b)
    except Exception:
        return default
