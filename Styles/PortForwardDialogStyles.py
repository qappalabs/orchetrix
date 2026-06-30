"""
Theme-aware styles for PortForwardDialog and ActivePortForwardsDialog components.
Contains only dialog-specific unique styles.
Shared styles (like UNIFIED_SCROLL_BAR_STYLE) should be imported directly from UI.Styles.AppStyles.
"""

from UI.ThemeManager import get_theme_manager
from UI.Styles import AppStyles


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()

# DIALOG STYLING
def get_dialog_style():
    """Main dialog container style - theme-aware"""
    theme = _get_theme()
    
    return f"""
        #PortForwardDialog {{
            background: transparent;
            color: {theme.colors.TEXT_LIGHT};
            font-size: 12px;
        }}
        
        #MainDialogContainer {{
            background-color: {theme.colors.DIALOG_BG};
            border-radius: 12px;
            border: 1px solid {theme.colors.BORDER_COLOR};
        }}
        
        #SectionCard {{
            background-color: {theme.colors.SECTION_CARD_BG};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 8px;
        }}
        
        #SectionCard QLabel {{
            background: transparent;
        }}

        #PortForwardDialog QLabel {{
            color: {theme.colors.TEXT_LIGHT};
            background: transparent;
        }}
        
        #PortForwardDialog QScrollArea {{
            border: none;
            background: transparent;
        }}
    """

# RESOURCE INFO STYLING — form row labels (left column)
def get_form_label_style():
    """Form row label style (Resource:, Namespace:, Available Ports:) — theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-size: 14px;
            font-weight: 500;
            color: {theme.colors.TEXT_SECONDARY};
            background: transparent;
        }}
    """

# Form row value style (right column) — used by resource_info and namespace_info
def get_form_value_style(color=None):
    """Form row value style (right-aligned, link-colored) — theme-aware"""
    theme = _get_theme()
    if color is None:
        color = theme.colors.TEXT_LINK
    return f"""
        QLabel {{
            font-size: 14px;
            font-weight: 600;
            color: {color};
            background: transparent;
        }}
    """

def get_resource_info_style():
    """Resource value label style — theme-aware"""
    theme = _get_theme()
    return get_form_value_style(theme.colors.TEXT_LINK)

def get_namespace_info_style():
    """Namespace value label style — theme-aware"""
    theme = _get_theme()
    return get_form_value_style(theme.colors.STATUS_ACTIVE)

# HELP TEXT STYLING
def get_help_text_style():
    """Help text label style - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 12px;
            font-style: italic;
        }}
    """

# ACTIVE PORT FORWARDS DIALOG STYLING
def get_active_dialog_style():
    """Active port forwards dialog style - theme-aware"""
    theme = _get_theme()
    
    return f"""
        #ActivePortForwardsDialog {{
            background: transparent;
            color: {theme.colors.TEXT_LIGHT};
        }}
        
        #ActivePortForwardsDialog #MainDialogContainer {{
            background-color: {theme.colors.DIALOG_BG};
            border-radius: 12px;
            border: 1px solid {theme.colors.BORDER_COLOR};
        }}
        
        #ActivePortForwardsDialog QTextEdit {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 8px;
            padding: 15px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            line-height: 1.5;
        }}
        
        #ActivePortForwardsDialog QScrollArea {{
            border: none;
            background: transparent;
        }}
        
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        
        #ActivePortForwardsDialog QPushButton {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 12px;
            min-width: 100px;
        }}
        
        #ActivePortForwardsDialog QPushButton:hover {{
            background-color: {theme.colors.BG_LIGHT};
        }}
    """
