"""
Styles for DetailPageComponent.
Contains only component-specific unique styles.
Shared styles should be imported directly from UI.Styles.
"""
from UI.ThemeManager import get_theme_manager
from UI.Styles import AppStyles


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


# Dimension constants - use shared AppStyles
def get_detail_page_width():
    """Get detail page default width"""
    return AppStyles.DETAIL_PAGE_WIDTH


def get_detail_page_min_width():
    """Get detail page minimum width"""
    return AppStyles.DETAIL_PAGE_MIN_WIDTH


def get_detail_page_max_width():
    """Get detail page maximum width"""
    return AppStyles.DETAIL_PAGE_MAX_WIDTH


def get_main_widget_style():
    """Main widget background style - theme-aware"""
    theme = _get_theme()
    return f"""
        background-color: {theme.colors.BG_SIDEBAR};
        border: none;
        border-radius: 8px;
    """


def get_header_style():
    """Header widget style - theme-aware"""
    theme = _get_theme()
    return f"""
        background-color: {theme.colors.BG_HEADER};
        border: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    """


def get_back_button_style():
    """Back/Close button style - theme-aware"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            border: 1px solid {theme.colors.BORDER_LIGHT};
            border-radius: 20px;
        }}
        QPushButton:hover {{
            background-color: {theme.colors.BG_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: {theme.colors.BG_MEDIUM};
        }}
    """


def get_title_label_style():
    """Title label style - theme-aware"""
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_LIGHT};
        font-size: 16px;
        font-weight: bold;
        margin-left: 10px;
    """


def get_action_button_install_style():
    """Action button style for Install (green) - theme-aware with hardcoded hover/pressed"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.ACCENT_GREEN};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: #45a049;
        }}
        QPushButton:pressed {{
            background-color: #3d8b40;
        }}
    """


def get_action_button_upgrade_style():
    """Action button style for Upgrade (blue) - theme-aware with hardcoded hover/pressed"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.ACCENT_BLUE};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 20px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #0078e7;
        }}
        QPushButton:pressed {{
            background-color: #0063b1;
        }}
    """


def get_resize_handle_style():
    """Resize handle style - theme-aware"""
    theme = _get_theme()
    return f"""
        QFrame {{
            background-color: transparent;
            border: none;
        }}
        QFrame:hover {{
            background-color: {theme.colors.ACCENT_BLUE};
        }}
    """


def get_content_area_style():
    """Content area style - theme-aware"""
    theme = _get_theme()
    return f"background-color: {theme.colors.BG_SIDEBAR}; border: none;"


def get_tab_widget_style():
    """Tab widget and tab bar style - theme-aware"""
    theme = _get_theme()
    return f"""
        QTabWidget {{
            border: none;
            background-color: {theme.colors.BG_SIDEBAR};
        }}
        QTabWidget::pane {{
            border: none;
            background-color: {theme.colors.BG_SIDEBAR};
            margin: 0px;
            padding: 0px;
            top: 0px;
        }}
        QTabBar {{
            qproperty-drawBase: 0;
            border: none;
            background-color: {theme.colors.BG_SIDEBAR};
            outline: none;
            margin: 0px;
            padding: 0px;
        }}
        QTabBar::tab {{
            background-color: {theme.colors.BG_SIDEBAR};
            color: {theme.colors.TEXT_SECONDARY};
            padding: 12px 20px;
            border: none;
            border-top: none;
            border-left: none;
            border-right: none;
            border-bottom: 2px solid transparent;
            margin: 0px;
            margin-right: 2px;
            font-size: 13px;
            font-weight: 500;
            min-width: 70px;
            max-width: 120px;
        }}
        QTabBar::tab:selected {{
            color: {theme.colors.TEXT_LIGHT};
            border-bottom: 2px solid {theme.colors.ACCENT_BLUE};
            background-color: {theme.colors.BG_SIDEBAR};
            font-weight: 600;
            border-top: none;
            border-left: none;
            border-right: none;
        }}
        QTabBar::tab:hover:!selected {{
            color: {theme.colors.TEXT_LIGHT};
            background-color: {theme.colors.HOVER_BG_DARKER};
            border-bottom: 2px solid transparent;
            border-top: none;
            border-left: none;
            border-right: none;
        }}
        QTabBar::scroller {{
            width: 0px;
            height: 0px;
        }}
    """
