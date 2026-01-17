"""
ClusterView-specific styles
Contains styles that are unique to ClusterView and defined inline in the page.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from UI.ThemeManager import BaseTheme as Theme

from UI.ThemeManager import get_theme_manager

# Helper functions for common styles
def get_bg_dark_style():
    """Helper to get background-color for BG_DARK"""
    return f"background-color: {get_theme_manager().get_current_theme().colors.BG_DARK};"

def get_bg_dark_style_for_theme(theme: "Theme"):
    """Helper to get background-color for BG_DARK with given theme"""
    return f"background-color: {theme.colors.BG_DARK};"

# LoadingOverlay styles (extracted from inline styles in ClusterView.py)

def get_loading_overlay_style():
    """Style for loading overlay widget"""
    theme = get_theme_manager().get_current_theme()
    return f"""
            #loadingOverlay {{
                background-color: {theme.colors.OVERLAY_BG_COLOR};
            }}
            QLabel {{
                color: {theme.colors.OVERLAY_TEXT_COLOR};
                font-size: 18px;
                font-weight: bold;
            }}
        """

# ClusterView main widget styles (extracted from inline styles in ClusterView.py)

def get_cluster_view_main_style():
    """Style for ClusterView main widget"""
    return get_main_widget_style_for_theme(get_theme_manager().get_current_theme())

def get_right_container_style():
    """Style for right container widget"""
    return get_right_container_style_for_theme(get_theme_manager().get_current_theme())

def get_stacked_widget_style():
    """Style for stacked widget"""
    return get_stacked_widget_style_for_theme(get_theme_manager().get_current_theme())

# Theme-aware styles for _on_theme_changed method (extracted from inline styles in ClusterView.py)

def get_main_widget_style_for_theme(theme: "Theme") -> str:
    """Style for main widget when theme changes"""
    return f"""
            QWidget {{
                background-color: {theme.colors.BG_DARK};
                color: {theme.colors.TEXT_LIGHT};
            }}
        """

def get_right_container_style_for_theme(theme: "Theme") -> str:
    """Style for right container when theme changes"""
    return get_bg_dark_style_for_theme(theme)

def get_stacked_widget_style_for_theme(theme: "Theme") -> str:
    """Style for stacked widget when theme changes"""
    return get_bg_dark_style_for_theme(theme)
