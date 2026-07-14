"""
ClusterPage-specific styles with theme-aware support.
Contains styles for the cluster overview page including charts, metrics,
and status panels. Chart rendering colors are intentionally fixed constants.
"""
from UI.Styles import AppStyles
from UI.ThemeManager import get_theme_manager

def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()

def get_main_background_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_DARK};
        }}
    """

def get_chart_panel_style():
    theme = _get_theme()
    return f"""
        QWidget {{
            background-color: {theme.colors.BG_SIDEBAR};
            border-radius: 4px;
        }}
    """

def get_metrics_panel_style():
    theme = _get_theme()
    return f"""
        background-color: {theme.colors.BG_SIDEBAR};
        border-radius: 4px;
    """

def get_status_panel_style():
    theme = _get_theme()
    return f"""
        background-color: {theme.colors.BG_SIDEBAR};
        border-radius: 4px;
    """

def get_status_box_style():
    theme = _get_theme()

    return f"""
        #statusBox {{
            background-color: {theme.colors.BG_SIDEBAR};
            border-radius: 5px;
            border: 1px solid transparent;
        }}
        #statusBox:hover {{
            background-color: {theme.colors.HOVER_BG_DARKER};
            border: 1px solid {theme.colors.BORDER_DARK};
        }}
    """

def get_resource_title_style():
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_LIGHT};
        font-size: 16px;
    """

def get_resource_label_usage_style():
    # Legacy color: #32dc32 (Green) - Kept hardcoded for both themes
    return "color: #32dc32;"

def get_resource_label_requests_style():
    # Legacy color: #50a0ff (Blue) - Kept hardcoded for both themes
    return "color: #50a0ff;"

def get_resource_label_limits_style():
    # Legacy color: #c050ff (Purple) - Kept hardcoded for both themes
    return "color: #c050ff;"

def get_resource_label_allocated_style():
    # Legacy color: #ff9428 (Orange) - Kept hardcoded for both themes
    return "color: #ff9428;"

def get_resource_label_capacity_style():
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_SECONDARY};"

def get_active_button_style():
    theme = _get_theme()

    return f"""
        QPushButton {{
            background-color: {theme.colors.BG_HEADER};
            color: {theme.colors.TEXT_LIGHT};
            border: none;
            padding: 6px 16px;
            font-size: 13px;
            border-radius: 4px;
        }}
    """

def get_inactive_button_style():
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {theme.colors.TEXT_SECONDARY};
            border: none;
            padding: 6px 16px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            color: {theme.colors.TEXT_LIGHT};
        }}
    """

def get_disabled_button_style():
    theme = _get_theme()

    return f"""
        QPushButton {{
            background-color: {theme.colors.BG_SIDEBAR};
            color: {theme.colors.TEXT_SECONDARY};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: normal;
            opacity: 0.6;
        }}
        QPushButton:disabled {{
            background-color: {theme.colors.BG_SIDEBAR};
            color: {theme.colors.TEXT_SECONDARY};
            border: 1px solid {theme.colors.BORDER_COLOR};
            opacity: 0.5;
        }}
    """

def get_status_icon_style():
    theme = _get_theme()
    return f"""
        background-color: {theme.colors.STATUS_ACTIVE};
        color: {theme.colors.TEXT_LIGHT};
        font-size: 40px;
        border-radius: 40px;
        qproperty-alignment: AlignCenter;
    """

def get_status_title_style():
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_LIGHT};
        font-size: 20px;
        font-weight: 500;
        margin-top: 16px;
    """

def get_status_subtitle_style():
    theme = _get_theme()
    return f"""
        color: {theme.colors.TEXT_SECONDARY};
        font-size: 14px;
        margin-top: 4px;
    """

def get_bar_chart_tooltip_style():
    theme = _get_theme()

    return f"""
        QToolTip {{
            background-color: {theme.colors.BG_SIDEBAR};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 4px;
            padding: 5px;
            font-size: 12px;
        }}
    """

def get_circular_indicator_tooltip_style():
    # Same as bar chart tooltip
    return get_bar_chart_tooltip_style()

def get_issues_table_style():
    theme = _get_theme()
    return f"""
        QTableWidget {{
            background-color: {theme.colors.CARD_BG};
            border: none;
            gridline-color: {theme.colors.BORDER_COLOR};
            outline: none;
            color: {theme.colors.TEXT_TABLE};
            alternate-background-color: transparent;
        }}
        QTableWidget::item {{
            padding: 8px;
            border: none;
            outline: none;
        }}
        QTableWidget::item:hover {{
            background-color: {theme.colors.HOVER_BG_DARKER};
            border-radius: 4px;
        }}
        QTableWidget::item:selected {{
            background-color: {theme.colors.SELECTED_BG};
            border: none;
        }}
        
        QHeaderView {{
            background-color: {theme.colors.TABLE_HEADER};
            border: none;
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

        QHeaderView::down-arrow, QHeaderView::up-arrow {{
            image: none;
            width: 0px;
            height: 0px;
            border: none;
        }}
        
        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
    """

# Chart rendering color constants.
# These are passed to native paint routines (not QSS), so they are fixed hex values
# and are not routed through the theme system.
def get_chart_colors():
    return {
        'background': '#2d2d2d',
        'bar': '#0095ff',
        'text': '#ffffff'
    }

def get_circular_indicator_colors():
    return {
        'background': '#2d2d2d',
        'progress': '#0095ff',
        'text': '#ffffff'
    }
