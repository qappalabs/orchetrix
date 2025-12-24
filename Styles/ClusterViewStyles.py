"""
ClusterView-specific styles
Contains styles that are unique to ClusterView and defined inline in the page.
"""

from UI.ThemeManager import get_theme_manager

# LoadingOverlay styles (extracted from inline styles in ClusterView.py)

def get_loading_overlay_style():
    """Style for loading overlay widget"""
    return f"""
            #loadingOverlay {{
                background-color: rgba(20, 20, 20, 0.8);
            }}
            QLabel {{
                color: white;
                font-size: 18px;
                font-weight: bold;
            }}
        """

# ClusterView main widget styles (extracted from inline styles in ClusterView.py)

def get_cluster_view_main_style():
    """Style for ClusterView main widget"""
    theme = get_theme_manager().get_current_theme()
    return f"""
            QWidget {{
                background-color: {theme.colors.BG_DARK};
                color: {theme.colors.TEXT_LIGHT};
            }}
        """

def get_right_container_style():
    """Style for right container widget"""
    return f"background-color: {get_theme_manager().get_current_theme().colors.BG_DARK};"

def get_stacked_widget_style():
    """Style for stacked widget"""
    return f"background-color: {get_theme_manager().get_current_theme().colors.BG_DARK};"

# Theme-aware styles for _on_theme_changed method (extracted from inline styles in ClusterView.py)

def get_main_widget_style_for_theme(theme):
    """Style for main widget when theme changes"""
    return f"""
            QWidget {{
                background-color: {theme.colors.BG_DARK};
                color: {theme.colors.TEXT_LIGHT};
            }}
        """

def get_right_container_style_for_theme(theme):
    """Style for right container when theme changes"""
    return f"background-color: {theme.colors.BG_DARK};"

def get_stacked_widget_style_for_theme(theme):
    """Style for stacked widget when theme changes"""
    return f"background-color: {theme.colors.BG_DARK};"
