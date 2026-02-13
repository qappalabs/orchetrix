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
        QDialog {{
            background-color: {theme.colors.BG_DARK};
            color: {theme.colors.TEXT_LIGHT};
            font-size: 12px;
        }}
        
        QLabel {{
            color: {theme.colors.TEXT_LIGHT};
            background: transparent;
        }}
        
        QScrollArea {{
            border: none;
            background: transparent;
        }}
    """

# HEADER SECTION STYLING
def get_header_frame_style():
    """Header frame container style - theme-aware"""
    theme = _get_theme()
    return f"""
        QFrame {{
            background-color: {theme.colors.BG_MEDIUM};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 6px;
            padding: 10px;
        }}
    """

# GROUP BOX STYLING
def get_group_box_style():
    """Group box container style - theme-aware"""
    theme = _get_theme()
    return f"""
        QGroupBox {{
            font-weight: bold;
            font-size: 13px;
            border: 2px solid {theme.colors.BORDER_COLOR};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 15px;
            background-color: {theme.colors.BG_MEDIUM};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 15px;
            padding: 2px 8px;
            background-color: {theme.colors.BG_MEDIUM};
            border-radius: 4px;
        }}
    """

# RESOURCE INFO STYLING
def get_resource_info_style():
    """Resource information label style - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-weight: bold;
            color: {theme.colors.STATUS_ACTIVE};
        }}
    """

def get_namespace_info_style():
    """Namespace information label style - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-weight: bold;
            color: {theme.colors.ACCENT_BLUE};
        }}
    """

def get_ports_info_style():
    """Available ports information label style - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.STATUS_WARNING};
        }}
    """

# HELP TEXT STYLING
def get_help_text_style():
    """Help text label style - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 11px;
            font-style: italic;
        }}
    """

# INPUT FIELD STYLING
def get_input_field_style():
    """Input field (SpinBox, LineEdit) style - theme-aware"""
    theme = _get_theme()
    return f"""
        QSpinBox, QLineEdit {{
            background-color: {theme.colors.BG_LIGHT};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 13px;
        }}
        QSpinBox:focus, QLineEdit:focus {{
            border-color: {theme.colors.ACCENT_BLUE};
            background-color: {theme.colors.BG_MEDIUM};
        }}
    """

# CHECKBOX STYLING
def get_auto_port_checkbox_style():
    """Auto-assign port checkbox style - theme-aware"""
    theme = _get_theme()
    return f"""
        QCheckBox {{
            color: {theme.colors.STATUS_ACTIVE};
            font-weight: bold;
        }}
    """

# PREVIEW SECTION STYLING
def get_preview_text_style():
    """Configuration preview text area style - theme-aware"""
    theme = _get_theme()
    return f"""
        QTextEdit {{
            background-color: {theme.colors.BG_DARK};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 8px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
            line-height: 1.4;
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """

# BUTTON SECTION STYLING
def get_button_frame_style():
    """Button section frame style - theme-aware"""
    theme = _get_theme()
    return f"""
        QFrame {{
            border-top: 1px solid {theme.colors.BORDER_COLOR};
        }}
    """

def get_primary_button_style():
    """Primary action button style - theme-aware"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.ACCENT_BLUE};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 12px 24px;
            font-size: 13px;
            font-weight: bold;
            min-width: 120px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.ACCENT_BLUE_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.ACCENT_BLUE_PRESSED};
        }}
    """

def get_secondary_button_style():
    """Secondary action button style - theme-aware"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 2px solid {theme.colors.BORDER_COLOR};
            border-radius: 6px;
            padding: 12px 20px;
            font-size: 12px;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.BG_LIGHT};
            border-color: {theme.colors.ACCENT_BLUE};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.BG_DARK};
        }}
    """

# ACTIVE PORT FORWARDS DIALOG STYLING
def get_active_dialog_style():
    """Active port forwards dialog style - theme-aware"""
    theme = _get_theme()
    return f"""
        QDialog {{
            background-color: {theme.colors.BG_DARK};
            color: {theme.colors.TEXT_LIGHT};
        }}
        QTextEdit {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 8px;
            padding: 15px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            line-height: 1.5;
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        QPushButton {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 12px;
            min-width: 100px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.BG_LIGHT};
        }}
    """

# STATUS LABEL STYLING
def get_status_loading_style():
    """Loading status label style - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.STATUS_WARNING};
            font-weight: bold;
        }}
    """

def get_status_inactive_style():
    """Inactive status label style - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            font-weight: bold;
        }}
    """

def get_status_active_style():
    """Active status label style - theme-aware"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.STATUS_ACTIVE};
            font-weight: bold;
        }}
    """
