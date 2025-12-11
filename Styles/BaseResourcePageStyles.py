"""
BaseResourcePage-specific styles extracted from base_resource_page.py
These are unique styles for the BaseResourcePage that are not shared with other components.
Note: Shared styles (TABLE_STYLE, MENU_STYLE, HOME_ACTION_BUTTON_STYLE) remain in UI/Styles.py
"""

import os
from UI.ThemeManager import get_theme_manager
from UI.Icons import resource_path


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_search_label_style():
    """Style for search label"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; font-size: 12px; font-weight: normal;"


def get_namespace_label_style():
    """Style for namespace label"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; font-size: 12px; font-weight: normal;"


def get_empty_title_style():
    """Style for empty state title"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; font-size: 20px; font-weight: bold; background-color: transparent; margin: 8px;"


def get_empty_subtitle_style():
    """Style for empty state subtitle"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_SUBTLE}; font-size: 14px; background-color: transparent; margin: 4px;"


def get_error_label_style():
    """Style for error label - hardcoded red for semantic meaning"""
    return "color: #ef4444; font-size: 16px;"


def get_checkbox_style(unchecked_path, checked_path):
    """Style for checkboxes (select all and row checkboxes)
    
    Args:
        unchecked_path: Path to unchecked icon SVG
        checked_path: Path to checked icon SVG
    """
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.CARD_BG};
        }}
        QCheckBox {{
            margin: 0px;
            padding: 0px;
            background-color: transparent;
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            margin: 1px;
            background-color: transparent;
            border: none;
            image: url({unchecked_path.replace(os.sep, '/')});
        }}
        QCheckBox::indicator:checked {{
            background-color: transparent;
            border: none;
            image: url({checked_path.replace(os.sep, '/')});
        }}
        QCheckBox::indicator:hover {{
            border-color: {theme.colors.ACCENT_BLUE};
        }}
    """

def get_checkbox_container_style():
    """Style for checkbox container QWidget to match table background"""
    theme = _get_theme()
    return f"background-color: {theme.colors.CARD_BG}; border: none; margin: 0; padding: 0;"





def get_delete_button_style():
    """Style for delete selected button - hardcoded red for semantic meaning"""
    return """
        QPushButton#deleteSelectedBtn {
            background-color: #d32f2f;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 5px 16px;
            font-size: 13px;
            margin-right: 8px;
        }
        QPushButton#deleteSelectedBtn:hover {
            background-color: #b71c1c;
        }
        QPushButton#deleteSelectedBtn:pressed {
            background-color: #8d1e1e;
        }
        QPushButton#deleteSelectedBtn:disabled {
            background-color: #cccccc;
            color: #666666;
        }
    """


def get_refresh_button_style():
    """Style for refresh button"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 5px 10px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.BG_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.BG_DARK};
        }}
    """


def get_search_input_style():
    """Style for search input field"""
    theme = _get_theme()
    return f"""
        QLineEdit {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 12px;
        }}
        QLineEdit:focus {{
            border-color: {theme.colors.ACCENT_BLUE};
            background-color: {theme.colors.BG_LIGHT};
        }}
    """


def get_namespace_combo_style():
    """Style for namespace dropdown"""
    theme = _get_theme()
    down_arrow_icon = resource_path("Icons/down_btn.svg")
    
    return f"""
        QComboBox {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 12px;
        }}
        QComboBox:hover {{
            border-color: {theme.colors.BORDER_LIGHT};
            background-color: {theme.colors.BG_LIGHT};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
            subcontrol-origin: padding;
            subcontrol-position: top right;
        }}
        QComboBox::down-arrow {{
            image: url({down_arrow_icon.replace(os.sep, '/')});
            width: 12px;
            height: 12px;
            margin-right: 4px;
        }}
        QComboBox::down-arrow:hover {{
            opacity: 0.8;
        }}
    """


def get_title_label_style():
    """Style for page title label"""
    theme = _get_theme()
    return f"font-size: 20px; font-weight: bold; color: {theme.colors.TEXT_LIGHT};"


def get_items_count_style():
    """Style for items count label"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px; margin-left: 8px;"


def get_hover_bg_color():
    """Get hover background color for row highlighting"""
    theme = _get_theme()
    return theme.colors.HOVER_BG


def get_transparent_color():
    """Get transparent color string"""
    return "transparent"
