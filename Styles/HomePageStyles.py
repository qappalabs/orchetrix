"""
HomePage-specific styles with theme-aware support.
Contains styles for the main home/browse page including sidebar buttons,
tree widget, search, status badges, and action buttons.
"""
from PyQt6.QtGui import QFont
from UI.Styles import AppConstants
from UI.ThemeManager import get_theme_manager

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
            background-color: {theme.colors.SIDEBAR_HOVER_BG};
            color: {theme.colors.TEXT_LIGHT};
        }}
        QPushButton:checked {{
            background-color: {theme.colors.SIDEBAR_ACTIVE_BG};
            color: {theme.colors.SIDEBAR_ACTIVE_TEXT};
            padding-left: 17px;
            font-weight: bold;
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
    # Use orange-tinted selection like resources pages
    selection_bg = getattr(theme.colors, 'SELECTED_BG', 'rgba(255, 87, 51, 46)')
    hover_highlight = getattr(theme.colors, 'HOVER_HIGHLIGHT', 'rgba(255, 87, 51, 20)')
    selection_hover = getattr(theme.colors, 'SELECTION_HOVER', 'rgba(255, 87, 51, 64)')
    return f"""
        QTreeWidget {{
            background-color: transparent;
            border: none;
            outline: none;
            font-size: 13px;
            gridline-color: transparent;
            margin: 0;
            padding: 0;
            selection-background-color: {selection_bg};
            alternate-background-color: transparent;
            color: {theme.colors.TEXT_TABLE};
        }}
        QTreeWidget::item {{
            padding: 10px 4px;
            background-color: transparent;
            border: none;
            outline: none;
            color: {theme.colors.TEXT_TABLE};
        }}
        QTreeWidget::item:hover {{
            background-color: {hover_highlight};
        }}
        QTreeWidget::item:selected {{
            background-color: {selection_bg};
            color: {theme.colors.TEXT_LIGHT};
        }}
        QTreeWidget::item:selected:hover {{
            background-color: {selection_hover};
        }}
        QHeaderView {{
            background-color: {theme.colors.TABLE_HEADER};
            border: none;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
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
        QHeaderView::section:last {{
            padding: 0;
        }}
        QHeaderView::section:hover {{
            background-color: rgba(255, 255, 255, 26);
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
        QFrame#table_container {{
            background-color: {theme.colors.CARD_BG};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 12px;
        }}
    """

def get_home_status_badge_style(color):
    """Get pill-shaped status badge style matching the style used in Pods/Nodes pages."""
    from PyQt6.QtGui import QColor
    qc = QColor(color)
    bg = f"rgba({qc.red()}, {qc.green()}, {qc.blue()}, 38)"
    return f"""
        QLabel {{
            padding: 4px 12px;
            border-radius: 10px;
            font-weight: bold;
            font-size: 12px;
            border: none;
            background-color: {bg};
            color: {color};
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
