from UI.ThemeManager import get_theme_manager

def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()

def get_main_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_SIDEBAR};
            color: {theme.colors.TEXT_LIGHT};
            font-family: 'Segoe UI', Arial, sans-serif;
        }}
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
        }}
    """

def get_sidebar_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_DARKER};
        }}
    """

def get_header_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            padding: 20px;
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 12px;
            font-weight: bold;
        }}
    """

def get_section_header_style():
    theme = _get_theme()
    return f"""
        QLabel#header {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 22px;
            font-weight: bold;
            padding-bottom: 10px;
        }}
    """

def get_subsection_header_style():
    theme = _get_theme()
    return f"""
        QLabel#sectionHeader {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            padding-top: 20px;
            padding-bottom: 10px;
        }}
    """

def get_text_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 14px;
        }}
    """

def get_description_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 13px;
            padding: 10px 0px;
        }}
    """

def get_status_text_style(enabled=False):
    theme = _get_theme()
    color = theme.colors.ACCENT_BLUE if enabled else theme.colors.TEXT_SUBTLE
    return f"""
        QLabel {{
            color: {color};
            font-size: 12px;
            margin-right: 10px;
        }}
    """

def get_input_style():
    theme = _get_theme()
    return f"""
        QLineEdit {{
            background-color: {theme.colors.HEADER_BG};
            border: 1px solid {theme.colors.BORDER_DARK};
            border-radius: 4px;
            padding: 8px 12px;
            color: {theme.colors.TEXT_LIGHT};
        }}
    """

def get_dropdown_style():
    theme = _get_theme()
    return f"""
        QComboBox {{
            background-color: {theme.colors.HEADER_BG};
            border: 1px solid {theme.colors.BORDER_DARK};
            border-radius: 4px;
            padding: 8px 12px;
            color: {theme.colors.TEXT_LIGHT};
            min-width: 200px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox:hover {{
            background-color: {theme.colors.HOVER_BG};
        }}
    """

def get_divider_style():
    theme = _get_theme()
    return f"""
        QFrame#divider {{
            background-color: {theme.colors.BORDER_DARK};
            max-height: 1px;
            margin: 20px 0px;
        }}
    """

def get_synced_item_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 14px;
            background-color: {theme.colors.HEADER_BG};
            padding: 8px;
            border-radius: 4px;
        }}
    """

def get_delete_button_style():
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {theme.colors.TEXT_SUBTLE};
            border: none;
            font-size: 16px;
        }}
        QPushButton:hover {{
            color: {theme.colors.TEXT_DANGER};
        }}
    """

def get_button_primary_style():
    theme = _get_theme()
    hover_bg = "#3A8EDF" if hasattr(theme.colors, 'BG_DARK') else "#5AB4FF"
    return f"""
        QPushButton {{
            background-color: {theme.colors.ACCENT_BLUE};
            color: {theme.colors.TEXT_LIGHT};
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {hover_bg};
        }}
    """

def get_button_secondary_style():
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.HEADER_BG};
            color: {theme.colors.TEXT_SUBTLE};
            border: 1px solid {theme.colors.ACCENT_BLUE};
            padding: 8px 15px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.BG_MEDIUM};
        }}
    """

def get_placeholder_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 14px;
            padding: 40px 0px;
        }}
    """

def get_sidebar_button_style():
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {theme.colors.TEXT_SUBTLE};
            text-align: left;
            padding: 10px 20px;
            border: none;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.HOVER_BG};
            color: {theme.colors.TEXT_LIGHT};
        }}
        QPushButton:checked {{
            background-color: {theme.colors.HOVER_BG};
            color: {theme.colors.TEXT_LIGHT};
            border-left: 3px solid {theme.colors.ACCENT_BLUE};
        }}
    """

def get_scroll_style():
    theme = _get_theme()
    scroll_area_style = f"""
        QScrollArea {{
            background-color: {theme.colors.BG_DARK};
            border: none;
            outline: none;
        }}
    """
    return scroll_area_style + theme.get_scrollbar_style()

def get_toggle_switch_colors():
    """Get theme-aware colors for toggle switch"""
    theme = _get_theme()
    return {
        'checked_bg': theme.colors.ACCENT_BLUE,
        'unchecked_bg': theme.colors.TEXT_SECONDARY,
        'circle': theme.colors.TEXT_LIGHT
    }

def get_back_button_style():
    """Get theme-aware back button style"""
    return "QPushButton { background-color: transparent; border: none; }"
