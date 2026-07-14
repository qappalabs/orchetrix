"""
AppsPage-specific styles with theme-aware support.
Contains styles that are unique to AppsPage and defined inline in the page.
"""

import logging
import os

from UI.Icons import resource_path
from UI.Styles import AppStyles
from UI.ThemeManager import get_theme_manager


def _get_theme():
    return get_theme_manager().get_current_theme()


def _get_theme_name():
    return get_theme_manager().get_current_theme_name()


def _text_color_for_colored_button():
    """Return correct text color for colored (green/red) buttons based on current theme."""
    theme = _get_theme()
    return theme.colors.TEXT_LIGHT if _get_theme_name() == "Dark" else theme.colors.TEXT_DARK


# Live monitoring button - Start state (green)
def get_live_monitor_btn_start_style():
    theme = _get_theme()
    text_color = _text_color_for_colored_button()
    return f"""
        QPushButton {{
            background-color: {theme.colors.STATUS_ACTIVE};
            color: {text_color};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 4px;
            padding: 3px 8px;
            font-weight: bold;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.SUCCESS_HOVER_BG};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.SUCCESS_PRESSED_BG};
        }}
        QPushButton:disabled {{
            background-color: {theme.colors.BUTTON_DISABLED_BG};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            color: {theme.colors.BUTTON_DISABLED_TEXT};
        }}
    """


# Live monitoring button - Stop state (red)
def get_live_monitor_btn_stop_style():
    theme = _get_theme()
    text_color = _text_color_for_colored_button()
    return f"""
        QPushButton {{
            background-color: {theme.colors.ACCENT_RED};
            color: {text_color};
            border: 1px solid {theme.colors.ACCENT_RED};
            border-radius: 4px;
            padding: 5px 10px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.DANGER_HOVER_BG};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.DANGER_PRESSED_BG};
        }}
        QPushButton:disabled {{
            background-color: {theme.colors.BUTTON_DISABLED_BG};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            color: {theme.colors.BUTTON_DISABLED_TEXT};
        }}
    """


# Refresh button style
def get_refresh_btn_style():
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.BG_DARK};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_DARK};
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.HOVER_BG_DARKER};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.BORDER_DARK};
        }}
    """


# Title label style
def get_title_label_style():
    theme = _get_theme()
    return f"font-size: 20px; font-weight: bold; color: {theme.colors.TEXT_LIGHT};"


def get_main_background_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_DARK};
        }}
    """


# Filter label styles (namespace, workload, resource)
def get_filter_label_style():
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; font-size: 13px; margin-right: 5px;"


def get_diagram_frame_style():
    theme = _get_theme()
    return f"""
        QFrame {{
            background-color: {theme.colors.CARD_BG};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 6px;
            margin-top: 10px;
        }}
    """


def get_diagram_title_style():
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_LIGHT};
            font-size: 11px;
            font-weight: bold;
            margin: 0px;
            padding: 0px;
            max-height: 16px;
        }}
    """


# Export button style
def get_export_btn_style():
    theme = _get_theme()
    return f"""
        QToolButton {{
            background-color: {theme.colors.BG_DARK};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_DARK};
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 500;
        }}
        QToolButton:hover {{
            background-color: {theme.colors.HOVER_BG};
            border-color: {theme.colors.ACCENT_BLUE};
        }}
        QToolButton:pressed {{
            background-color: {theme.colors.SELECTED_BG};
        }}
        QToolButton::menu-indicator {{
            image: none;
        }}
    """


def get_export_menu_style():
    theme = _get_theme()
    return f"""
        QMenu {{
            background-color: {theme.colors.CARD_BG};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 4px;
            padding: 4px;
        }}
        QMenu::item {{
            background-color: transparent;
            color: {theme.colors.TEXT_LIGHT};
            padding: 6px 20px 6px 10px;
            border-radius: 2px;
            margin: 1px 0px;
        }}
        QMenu::item:selected {{
            background-color: {theme.colors.HOVER_BG};
            color: {theme.colors.ACCENT_BLUE};
        }}
    """


def get_diagram_view_style():
    theme = _get_theme()
    return f"""
        QGraphicsView {{
            background-color: {theme.colors.BG_SIDEBAR};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 4px;
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """


def get_diagram_splitter_style():
    theme = _get_theme()
    return f"""
        QSplitter {{
            background-color: transparent;
        }}
        QSplitter::handle {{
            background-color: {theme.colors.BORDER_LIGHT};
            height: 4px;
            border-radius: 2px;
            margin: 4px 100px; /* Centered narrow handle for premium look */
        }}
        QSplitter::handle:hover {{
            background-color: {theme.colors.ACCENT_BLUE};
        }}
        QSplitter::handle:pressed {{
            background-color: {theme.colors.ACCENT_BLUE};
        }}
    """


def get_status_container_style():
    theme = _get_theme()
    return f"""
        QFrame {{
            background-color: {theme.colors.CARD_BG};
            border: none;
            margin: 0px;
        }}
    """


def get_status_header_style():
    theme = _get_theme()
    text_color = _text_color_for_colored_button()
    return f"""
        QLabel {{
            color: {text_color};
            font-size: 10px;
            font-weight: bold;
            margin: 2px 8px;
            padding: 0px;
        }}
    """


def get_status_text_style():
    theme = _get_theme()
    return f"""
        QTextEdit {{
            background-color: {theme.colors.BG_SIDEBAR};
            border: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 4px;
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 12px;
            padding: 8px;
            margin: 0px 2px 2px 2px;
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """


def get_diagram_area_main_style():
    theme = _get_theme()
    colors = theme.colors
    return f"""
        #diagramFrame QWidget {{
            background-color: {colors.BG_DARK};
        }}
        #diagramFrame QFrame {{
            background-color: {colors.BG_DARK};
            border: 1px solid {colors.BORDER_COLOR};
            border-radius: 6px;
        }}
        #diagramFrame QGraphicsView {{
            background-color: {colors.BG_DARK};
            border: 1px solid {colors.BORDER_LIGHT};
            border-radius: 4px;
        }}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """


def get_theme_aware_dropdown_style():
    theme = _get_theme()
    colors = theme.colors
    bg_color = getattr(colors, "BG_MEDIUM", "#2d2d2d")
    text_color = getattr(colors, "TEXT_LIGHT", "#ffffff")
    border_color = getattr(colors, "BORDER_LIGHT", "#3d3d3d")
    hover_border = getattr(colors, "ACCENT_BLUE", "#555555")
    selection_bg = getattr(colors, "SELECTED_BG", "#0078d7")

    try:
        down_arrow_icon = resource_path("Icons/down_arrow.svg")
        return f"""
        QComboBox {{
            background-color: {bg_color};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            padding: 5px 10px;
            font-size: 13px;
        }}
        QComboBox:hover {{
            border: 1px solid {hover_border};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
            subcontrol-origin: padding;
            subcontrol-position: top right;
        }}
        QComboBox::down-arrow {{
            image: url({down_arrow_icon.replace(os.sep, "/")});
            width: 12px;
            height: 12px;
            margin-right: 4px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {bg_color};
            color: {text_color};
            selection-background-color: {selection_bg};
            border: none;
            outline: none;
            padding: 0px;
        }}
        QComboBox QFrame {{
            border: none;
            background-color: {bg_color};
        }}
        """
    except Exception as e:
        logging.exception(
            f"Failed to load icon for dropdown style, falling back to style without icon: {type(e).__name__}: {e}"
        )
        return f"""
        QComboBox {{
            background-color: {bg_color};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            padding: 5px 10px;
            font-size: 13px;
        }}
        QComboBox:hover {{
            border: 1px solid {hover_border};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            width: 0px;
            height: 0px;
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {bg_color};
            color: {text_color};
            selection-background-color: {selection_bg};
            border: none;
            outline: none;
            padding: 0px;
        }}
        QComboBox QFrame {{
            border: none;
            background-color: {bg_color};
        }}
        """
