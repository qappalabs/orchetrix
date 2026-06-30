"""
Styles for DetailPageOverviewSection component.
Contains only page-specific unique styles.
Shared styles should be imported directly from UI.Styles.EnhancedStyles.
"""
from Styles import BaseDetailSectionStyles
from UI.Styles import AppStyles
from UI.ThemeManager import get_theme_manager


def _get_theme():
    """Get current theme"""
    return get_theme_manager().get_current_theme()


def get_scroll_area_style():
    """Scroll area style for overview section - uses shared AppStyles"""
    return AppStyles.DETAIL_PAGE_OVERVIEW_STYLE


def get_overview_content_style():
    """Overview content widget background style - theme-aware"""
    theme = _get_theme()
    return f"background-color: {theme.colors.BG_SIDEBAR}; border: none;"


def get_overview_header_style():
    """Resource name header style - theme-aware"""
    theme = _get_theme()
    return f"""
        font-size: 24px;
        font-weight: bold;
        color: {theme.colors.TEXT_LIGHT};
        margin-bottom: 4px;
    """


def get_resource_type_style():
    """Resource type label style - theme-aware"""
    theme = _get_theme()
    return f"""
        font-size: 14px;
        color: {theme.colors.TEXT_SECONDARY};
        font-weight: 500;
    """


def get_resource_type_color():
    """Get the color used for resource type text"""
    return _get_theme().colors.TEXT_SECONDARY


def get_condition_message_style():
    """Style for condition detail message"""
    return BaseDetailSectionStyles.get_condition_message_style()


def get_condition_dot_style(status_bool):
    """Style for condition status dot"""
    return BaseDetailSectionStyles.get_badge_dot_style(status_bool)


def get_history_table_style():
    """Rollback history table style - theme-aware"""
    theme = _get_theme()
    return f"""
        QTableWidget {{
            background-color: {theme.colors.BG_SIDEBAR};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            border-radius: 6px;
            gridline-color: {theme.colors.BORDER_COLOR};
            selection-background-color: {theme.colors.SELECTED_BG};
            selection-color: {theme.colors.TEXT_LIGHT};
        }}
        QTableWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {theme.colors.BORDER_COLOR};
        }}
        QTableWidget::item:selected {{
            background-color: {theme.colors.SELECTED_BG};
            color: {theme.colors.TEXT_LIGHT};
        }}
        QHeaderView::section {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            padding: 8px;
            border: 1px solid {theme.colors.BORDER_COLOR};
            font-weight: bold;
        }}
    """


def get_pods_table_style():
    """Pods table style (same as history table) - theme-aware"""
    return get_history_table_style()


def get_message_box_style():
    """Message box style for dialogs - theme-aware"""
    theme = _get_theme()
    return f"""
        QMessageBox {{
            background-color: {theme.colors.BG_SIDEBAR};
            color: {theme.colors.TEXT_LIGHT};
        }}
        QMessageBox QPushButton {{
            background-color: {theme.colors.BG_MEDIUM};
            color: {theme.colors.TEXT_LIGHT};
            border: 1px solid {theme.colors.BORDER_COLOR};
            padding: 8px 16px;
            border-radius: 4px;
            min-width: 80px;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {theme.colors.ACCENT_BLUE};
        }}
    """


def get_rollback_button_style():
    """Rollback button style - theme-aware success color"""
    theme = _get_theme()
    return f"""
        QPushButton {{
            background-color: {theme.colors.STATUS_ACTIVE};
            color: white;
            border: none;
            padding: 6px 12px;
            font-weight: bold;
        }}
    """


def get_current_label_style():
    """Current revision label style - theme-aware success color"""
    theme = _get_theme()
    return f"""
        QLabel {{
            color: {theme.colors.STATUS_ACTIVE};
            font-weight: bold;
            padding: 6px 12px;
        }}
    """


def get_error_label_style():
    """Error label style - theme-aware"""
    theme = _get_theme()
    return f"color: {theme.colors.TEXT_DANGER};"


# Color getters for QColor usage - theme-aware
def get_status_active_color():
    """Get status active color for QColor - theme-aware"""
    theme = _get_theme()
    return theme.colors.STATUS_ACTIVE


def get_status_warning_color():
    """Get status warning color for QColor - theme-aware"""
    theme = _get_theme()
    return theme.colors.STATUS_WARNING


def get_text_danger_color():
    """Get text danger color for QColor - theme-aware"""
    theme = _get_theme()
    return theme.colors.TEXT_DANGER


def get_text_secondary_color():
    """Get text secondary color for QColor - theme-aware"""
    theme = _get_theme()
    return theme.colors.TEXT_SECONDARY
