"""
Theme-aware styles for BaseTablePage component.
Contains shared styles for all resource pages (Pods, Deployments, Services, etc.).
"""
import os

from UI.Styles import AppStyles
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_table_container_style():
    """Style for the card container wrapping the table"""
    theme = _get_theme()
    return f"""
        QFrame#table_container {{
            background-color: {theme.colors.CARD_BG};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 12px;
        }}
    """


# TABLE STYLING

def get_table_style():
    """Theme-aware table style for resource pages"""
    theme = _get_theme()
    # Get selection/hover colors from theme with fallbacks
    selection_bg = getattr(theme.colors, 'SELECTED_BG', 'rgba(255, 87, 51, 46)')
    hover_highlight = getattr(theme.colors, 'HOVER_HIGHLIGHT', 'rgba(255, 87, 51, 20)')
    selection_hover = getattr(theme.colors, 'SELECTION_HOVER', 'rgba(255, 87, 51, 64)')
    accent_orange = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')
    
    return f"""
        QTableWidget {{
            background-color: transparent;
            border: none;
            gridline-color: transparent;
            outline: none;
            color: {theme.colors.TEXT_TABLE};
            selection-background-color: {selection_bg};
            alternate-background-color: transparent;
        }}

        QTableWidget::item {{
            padding: 10px 8px;
            border: none;
            outline: none;
            color: {theme.colors.TEXT_TABLE};
            background-color: transparent;
        }}

        QTableWidget::item:hover {{
            background-color: {hover_highlight};
        }}

        QTableWidget::item:selected {{
            background-color: {selection_bg};
            color: {theme.colors.TEXT_LIGHT};
            border: none;
        }}

        QTableWidget::item:selected:hover {{
            background-color: {selection_hover};
        }}
        {get_table_header_style()}
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """


def get_table_header_style():
    """Theme-aware style for the table header (QHeaderView)"""
    theme = _get_theme()
    return f"""
        QHeaderView {{
            background-color: {theme.colors.TABLE_HEADER};
            border: none;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        }}

        QHeaderView::section {{
            background-color: transparent;
            color: {theme.colors.TEXT_LIGHT};
            padding: 10px 16px;
            border: none;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}

        QHeaderView::section:hover {{
            background-color: #1AFFFFFF;
        }}

        /* Completely hide default sort indicators */
        QHeaderView::down-arrow, QHeaderView::up-arrow {{
            image: none;
            width: 0px;
            height: 0px;
            border: none;
            background: none;
        }}
    """


# TITLE AND COUNT LABEL STYLING

def get_title_style():
    """Theme-aware title label style"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-size: 24px;
            font-weight: bold;
            color: {theme.colors.TEXT_LIGHT};
            padding: 0px;
            background-color: transparent;
        }}
    """


def get_count_style():
    """Theme-aware count label style with pill-shaped badge"""
    theme = _get_theme()
    # Use background color that provides contrast for the pill
    badge_bg = getattr(theme.colors, 'BG_DARK', '#f1f1f1') if get_theme_manager().get_current_theme_name() == "Light" else getattr(theme.colors, 'BG_MEDIUM', '#2d2d2d')
    
    return f"""
        QLabel {{
            font-size: 13px;
            font-weight: 500;
            color: {theme.colors.TEXT_SUBTLE};
            padding: 4px 12px;
            background-color: {badge_bg};
            border-radius: 12px;
            margin-left: 10px;
        }}
    """


# CHECKBOX STYLING

def get_checkbox_style():
    """Theme-aware checkbox style with icon paths from current theme folder"""
    from UI.Icons import resource_path

    white_checkmark = resource_path("Icons/checkmark_white.svg").replace(os.sep, '/')

    # Use Accent Orange for the border and checked background
    theme = get_theme_manager().get_current_theme()
    accent_orange = getattr(theme.colors, 'ACCENT_ORANGE', '#FF5733')

    # Subtle hover tint derived from the active accent so it stays aligned
    # with the accent-colored border and checked fill.
    _accent_hex = accent_orange.lstrip('#')
    if len(_accent_hex) == 6:
        _r, _g, _b = (int(_accent_hex[i:i + 2], 16) for i in (0, 2, 4))
        accent_hover = f"rgba({_r}, {_g}, {_b}, 0.1)"
    else:
        accent_hover = accent_orange

    return f"""
        QCheckBox {{
            background: none;
            border: none;
            outline: none;
            margin: 0px;
            padding: 0px;
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border-radius: 3px;
            margin: 0px;
            padding: 0px;
            spacing: 0px;
            background: none;
            subcontrol-position: center;
            subcontrol-origin: content;
        }}
        QCheckBox::indicator:unchecked {{
            border: 2px solid {accent_orange};
            background-color: transparent;
            image: none;
        }}
        QCheckBox::indicator:checked {{
            border: 2px solid {accent_orange};
            background-color: {accent_orange};
            image: url({white_checkmark.replace(os.sep, '/')});
        }}
        QCheckBox::indicator:unchecked:hover {{
            background-color: {accent_hover};
        }}
        QCheckBox::indicator:checked:hover {{
            background-color: {accent_orange};
            opacity: 0.9;
        }}
    """


# ACTION BUTTON AND MENU STYLING

def get_action_button_style():
    """Theme-aware action button style"""
    theme = _get_theme()
    return f"""
        QToolButton {{
            background-color: transparent;
            border: none;
            padding: 2px;
            margin: 0;
        }}
        QToolButton:hover {{
            background-color: {theme.colors.HOVER_BG};
            border-radius: 3px;
        }}
        QToolButton:pressed {{
            background-color: {theme.colors.HOVER_BG_DARKER};
        }}
        QToolButton::menu-indicator {{
            image: none;
        }}
    """


def get_menu_style():
    """Theme-aware menu style for action buttons"""
    theme = _get_theme()
    return f"""
        QMenu {{
            background-color: {theme.colors.BG_DARKER};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 6px;
            padding: 6px;
        }}
        QMenu::item {{
            color: {theme.colors.TEXT_LIGHT};
            padding: 10px 24px 10px 36px;
            border-radius: 4px;
            font-size: 13px;
            margin: 2px 0px;
        }}
        QMenu::item:selected {{
            background-color: {theme.colors.SELECTED_BG};
            color: {theme.colors.TEXT_LIGHT};
        }}
        QMenu::item[dangerous="true"] {{
            color: {theme.colors.TEXT_DANGER};
        }}
        QMenu::item[dangerous="true"]:selected {{
            background-color: {theme.colors.DANGER_HOVER_BG};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {theme.colors.BORDER_COLOR};
            margin: 6px 10px;
        }}
    """


# HEADER WIDGET STYLING

def get_header_widget_style():
    """Theme-aware header widget container style"""
    theme = _get_theme()
    return f"background-color: {theme.colors.TABLE_HEADER};"


# EMPTY STATE STYLING

def get_empty_state_style():
    """Theme-aware empty state widget style"""
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: transparent;
        }}
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 14px;
            background-color: transparent;
        }}
    """


def get_empty_message_style():
    """Theme-aware empty message label style"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.TEXT_SUBTLE};
            font-size: 16px;
            font-weight: normal;
            padding: 20px;
            background-color: transparent;
        }}
    """
