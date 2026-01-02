"""
Theme-aware styles for BaseTablePage component.
Contains shared styles for all resource pages (Pods, Deployments, Services, etc.).
"""
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


# TABLE STYLING

def get_table_style():
    """Theme-aware table style for resource pages"""
    theme = _get_theme()
    return f"""
        QTableWidget {{
            background-color: {theme.colors.CARD_BG};
            border: none;
            gridline-color: transparent;
            outline: none;
            color: {theme.colors.TEXT_TABLE};
            selection-background-color: rgba(53, 132, 228, 0.15);
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
            background-color: rgba(53, 132, 228, 0.10);
        }}

        QTableWidget::item:selected {{
            background-color: rgba(53, 132, 228, 0.15);
            color: {theme.colors.TEXT_LIGHT};
            border: none;
        }}

        QTableWidget::item:selected:hover {{
            background-color: rgba(53, 132, 228, 0.20);
        }}

        QHeaderView::section {{
            background-color: {theme.colors.HEADER_BG};
            color: {theme.colors.TEXT_SECONDARY};
            padding: 10px 8px;
            border: none;
            border-bottom: 1px solid {theme.colors.BORDER_COLOR};
            font-size: 12px;
            text-align: center;
            font-weight: bold;
        }}

        QHeaderView::section:hover {{
            background-color: {theme.colors.BG_MEDIUM};
        }}

        QHeaderView::down-arrow, QHeaderView::up-arrow {{
            image: none;
            width: 0px;
            height: 0px;
            border: none;
        }}
        QScrollBar:vertical {{
            background: {theme.colors.BG_DARK};
            width: 12px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.colors.BG_MEDIUM};
            border-radius: 6px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {theme.colors.BORDER_LIGHT};
        }}
        QScrollBar:horizontal {{
            background: {theme.colors.BG_DARK};
            height: 12px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background: {theme.colors.BG_MEDIUM};
            border-radius: 6px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {theme.colors.BORDER_LIGHT};
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
    """Theme-aware count label style"""
    theme = _get_theme()
    return f"""
        QLabel {{
            font-size: 14px;
            color: {theme.colors.TEXT_SUBTLE};
            padding: 0px 8px;
            background-color: transparent;
        }}
    """


# CHECKBOX STYLING

def get_checkbox_style():
    """Theme-aware checkbox style with icon paths from current theme folder"""
    from UI.Icons import Icons
    from UI.ThemeManager import get_theme_manager
    import os

    # Get current theme and load theme-specific icon paths
    theme_name = get_theme_manager().get_current_theme_name() or "Dark"
    unchecked_icon = Icons.get_theme_icon_path("check_box_unchecked.svg", theme_name)
    checked_icon = Icons.get_theme_icon_path("check_box_checked.svg", theme_name)

    return f"""
        QCheckBox {{
            width: 14px;
            height: 14px;
            margin: 0px;
            padding: 0px;
            spacing: 0px;
            background-color: transparent;
            border: none;
            outline: none;
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border: none;
            background: transparent;
            margin: 0px;
            padding: 0px;
            spacing: 0px;
            subcontrol-position: center;
            subcontrol-origin: content;
        }}
        QCheckBox::indicator:unchecked {{
            image: url({unchecked_icon.replace(os.sep, '/')});
        }}
        QCheckBox::indicator:checked {{
            image: url({checked_icon.replace(os.sep, '/')});
        }}
        QCheckBox::indicator:unchecked:hover {{
            opacity: 0.8;
        }}
        QCheckBox::indicator:checked:hover {{
            opacity: 0.8;
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
