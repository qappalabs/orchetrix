from UI.ThemeManager import get_theme_manager
from PyQt6.QtGui import QFont
from UI.Styles import AppConstants


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


# Theme-aware style functions using direct pattern
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
            padding-left: 17px;
        }}
    """

def get_sidebar_container_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_SIDEBAR};
            border-right: 2px solid {theme.colors.BORDER_COLOR};
        }}
    """

def get_top_bar_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_DARK};
            border-bottom: 1px solid {theme.colors.BORDER_COLOR};
        }}
    """

def get_tree_widget_style():
    theme = _get_theme()
    return f"""
        QTreeWidget {{
            background-color: {theme.colors.BG_DARK};
            border: none;
            outline: none;
            font-size: 13px;
            gridline-color: {theme.colors.BORDER_DARK};
            margin: 0;
            padding: 0;
            selection-background-color: rgba(53, 132, 228, 0.15);
            alternate-background-color: transparent;
        }}
        
        QTreeWidget::item {{
            padding: 6px 4px;
            background-color: transparent;
            border: none;
            outline: none;
        }}
        
        QTreeWidget::item:hover {{
            background-color: rgba(53, 132, 228, 0.10);
        }}
        
        QTreeWidget::item:selected {{
            background-color: rgba(53, 132, 228, 0.15);
            color: {theme.colors.TEXT_LIGHT};
        }}
        
        QTreeWidget::item:selected:hover {{
            background-color: rgba(53, 132, 228, 0.20);
        }}
        
        QHeaderView::section {{
            background-color: {theme.colors.TABLE_HEADER};
            color: {theme.colors.TEXT_LIGHT};
            padding: 8px 8px;
            border-right: 1px solid {theme.colors.BORDER_DARK};
            border-bottom: 1px solid {theme.colors.BORDER_DARK};
            border-top: none;
            border-left: 1px solid {theme.colors.BORDER_DARK};
            text-align: left;
            font-weight: bold;
        }}
        
        QHeaderView::section:first {{
            border-left: 1px solid {theme.colors.BORDER_DARK};
        }}
        
        QHeaderView::section:last {{
            padding: 0;
            text-align: center;
            width: {AppConstants.SIZES["ACTION_WIDTH"]}px;
            max-width: {AppConstants.SIZES["ACTION_WIDTH"]}px;
            min-width: {AppConstants.SIZES["ACTION_WIDTH"]}px;
        }}
        
        QHeaderView::section:hover {{
            background-color: {theme.colors.BG_MEDIUM};
        }}
        
        QHeaderView::down-arrow, QHeaderView::up-arrow {{
            image: none;
            width: 0px;
            height: 0px;
            border: none;
            subcontrol-origin: content;
            subcontrol-position: right;
        }}
        
        QTreeWidget::branch {{
            border: none;
            border-image: none;
            outline: none;
        }}
    """

def get_menu_style():
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
        QMenu::separator {{
            height: 1px;
            background-color: {theme.colors.BORDER_COLOR};
            margin: 6px 10px;
        }}
    """

def get_search_style():
    theme = _get_theme()
    return f"""
        QLineEdit {{
            padding: 5px;
            background-color: {theme.colors.BG_MEDIUM};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 2px;
            color: {theme.colors.TEXT_LIGHT};
        }}
    """

def get_content_area_style():
    theme = _get_theme()
    return f"""
        QFrame {{
            background-color: {theme.colors.BG_DARK};
            border: none;
            padding: 0;
            margin: 0;
        }}
    """

def get_action_container_style():
    return """
        background-color: transparent;
        border: none;
        margin: 0;
        padding: 0;
    """

def get_home_action_button_style():
    theme = _get_theme()
    return f"""
        QToolButton {{
            background: transparent;
            padding: 2px;
            margin: 0;
            border: none;
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

def get_home_action_button_disabled_style():
    """Get disabled state style for action button"""
    return get_home_action_button_style() + " QToolButton:disabled { opacity: 0.5; background-color: transparent; }"

def get_status_color(status):
    """Get theme-aware color for status labels"""
    theme = _get_theme()
    status_map = {
        "available": theme.colors.ACCENT_GREEN,
        "active": theme.colors.ACCENT_GREEN,
        "connected": theme.colors.ACCENT_GREEN,
        "disconnect": theme.colors.ACCENT_RED,
        "connecting": theme.colors.ACCENT_ORANGE,
        "loading": theme.colors.ACCENT_ORANGE
    }
    return status_map.get(status, theme.colors.ACCENT_RED)

def get_browser_label_style():
    """Get theme-aware browser label style"""
    theme = _get_theme()
    return f"font-weight: bold; font-size: 16px; color: {theme.colors.TEXT_LIGHT};"

def get_items_label_style():
    """Get theme-aware items count label style"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_SUBTLE}; margin-left: 10px; font-size: 14px;"

def get_cell_label_style():
    """Get theme-aware cell label style"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_LIGHT}; background: transparent; padding: 0px; margin: 0px;"

def get_pin_button_style():
    """Get theme-aware pin button style"""
    theme = _get_theme()
    return f"""
        QPushButton {{ background: transparent; border: none; padding: 0px; margin: 0px; }}
        QPushButton:hover {{ background: {theme.colors.HOVER_BG}; }}
    """


def get_status_label_style(color):
    """Get status label style with dynamic color"""
    return f"color: {color}; background: transparent;"


def get_cell_font():
    """Get reusable font for table cells"""
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    return font


# Theme-neutral constants (no colors)
TRANSPARENT_WIDGET = "background: transparent; padding: 0px; margin: 0px;"
STATUS_CELL = "QWidget#statusCell { background: transparent; }"
