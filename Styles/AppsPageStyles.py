"""
AppsPage - specific styles with theme - aware support
Contains styles that are unique to AppsPage and defined inline in the page.
"""

import logging
import os
from UI.ThemeManager import get_theme_manager
from UI.Styles import AppColors, AppStyles


def _get_theme():

    return get_theme_manager().get_current_theme()

# Live monitoring button - Start state (green)


def get_live_monitor_btn_start_style():
    theme = _get_theme()
    theme_manager = get_theme_manager()
    theme_name = theme_manager.get_current_theme_name()

    # For colored buttons (green / red), use white text in dark theme, dark text in light theme
    if theme_name == "Dark":
        text_color = theme.colors.TEXT_LIGHT  # White in dark theme
    else:
        text_color = theme.colors.TEXT_DARK  # Dark text in light theme

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
            background-color: {theme.colors.HOVER_BG};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.BORDER_DARK};
        }}
        QPushButton:disabled {{
            background-color: {theme.colors.TEXT_SUBTLE};
            border-color: {theme.colors.TEXT_SUBTLE};
            color: {theme.colors.TEXT_SUBTLE};
        }}
    """

# Live monitoring button - Stop state (red)


def get_live_monitor_btn_stop_style():
    theme = _get_theme()
    theme_manager = get_theme_manager()
    theme_name = theme_manager.get_current_theme_name()

    # For colored buttons (green / red), use white text in dark theme, dark text in light theme
    if theme_name == "Dark":
        text_color = theme.colors.TEXT_LIGHT  # White in dark theme
    else:
        text_color = theme.colors.TEXT_DARK  # Dark text in light theme

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
    colors = theme.colors
    text_color = colors.TEXT_LIGHT
    return f"color: {text_color}; font-size: 13px; margin-right: 5px;"


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
            border-radius: 3px;
            padding: 2px 6px;
            font-size: 12px;
            min-width: 20px;
            max-height: 16px;
        }}
        QToolButton:hover {{
            background-color: {theme.colors.HOVER_BG_DARKER};
        }}
        QToolButton:pressed {{
            background-color: {theme.colors.BORDER_DARK};
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
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 2px;
        }}
        QMenu::item {{
            background-color: transparent;
            color: {theme.colors.TEXT_LIGHT};
            padding: 4px 12px;
            border-radius: 2px;
        }}
        QMenu::item:selected {{
            background-color: {theme.colors.SELECTED_BG};
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
            background-color: {theme.colors.CARD_BG};
        }}
        QSplitter::handle {{
            background-color: {theme.colors.BORDER_LIGHT};
            height: 3px;
            border-radius: 1px;
            margin: 2px 0px;
        }}
        QSplitter::handle:hover {{
            background-color: {theme.colors.ACCENT_BLUE};
        }}
        QSplitter::handle:pressed {{
            background-color: {theme.colors.ACCENT_BLUE};
        }}
    """


def get_status_container_style():
    bg_color = getattr(getattr(_get_theme(), 'colors', None), 'CARD_BG', AppColors.BG_MEDIUM)
    return f"""
        QFrame {{
            background-color: {bg_color};
            border: none;
            margin: 0px;
        }}
    """


def get_status_header_style():
    theme = _get_theme()
    theme_manager = get_theme_manager()
    theme_name = theme_manager.get_current_theme_name()

    # Ensure correct text color: white in dark theme, dark in light theme
    if theme_name == "Dark":
        text_color = theme.colors.TEXT_LIGHT  # White in dark theme
    else:
        text_color = theme.colors.TEXT_DARK  # Dark text in light theme

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
    if hasattr(theme, 'colors'):
        colors = theme.colors
        main_bg = getattr(colors, 'BG_DARK', AppColors.BG_DARK)
        border_color = getattr(colors, 'BORDER_COLOR', AppColors.BORDER_COLOR)
        light_border = getattr(colors, 'BORDER_LIGHT', AppColors.BORDER_LIGHT)
    else:
        main_bg = AppColors.BG_DARK
        border_color = AppColors.BORDER_COLOR
        light_border = AppColors.BORDER_LIGHT

    return f"""
        /* Main container with theme - aware background */
        QWidget {{
            background-color: {main_bg};
        }}

        /* Diagram frame */
        QFrame {{
            background-color: {main_bg};
            border: 1px solid {border_color};
            border-radius: 6px;
        }}

        /* Graphics view */
        QGraphicsView {{
            background-color: {main_bg};
            border: 1px solid {light_border};
            border-radius: 4px;
        }}

        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """


def get_theme_aware_dropdown_style():
    theme = _get_theme()
    if hasattr(theme, 'colors'):
        colors = theme.colors
        bg_color = getattr(colors, 'BG_MEDIUM', '#2d2d2d')
        text_color = getattr(colors, 'TEXT_LIGHT', '#ffffff')
        border_color = getattr(colors, 'BORDER_LIGHT', '#3d3d3d')
        hover_border = getattr(colors, 'ACCENT_BLUE', '#555555')
        selection_bg = getattr(colors, 'SELECTED_BG', '#0078d7')
    else:
        # Fallback to dark theme colors
        bg_color = '#2d2d2d'
        text_color = '#ffffff'
        border_color = '#3d3d3d'
        hover_border = '#555555'
        selection_bg = '#0078d7'

    try:
        from UI.Icons import resource_path
        down_arrow_icon = resource_path("Icons/down_btn.svg")

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
            image: url({down_arrow_icon.replace(os.sep, '/')});
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
            f"Failed to load icon for dropdown style, falling back to style without icon: {type(e).__name__}: {e}")
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
