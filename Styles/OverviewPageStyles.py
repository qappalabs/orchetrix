"""
OverviewPage-specific styles
Contains styles that are unique to OverviewPage and defined inline in the page.
"""

from UI.Styles import AppStyles, AppColors


def _get_theme():
    """Get current theme"""
    from UI.ThemeManager import get_theme_manager
    return get_theme_manager().get_current_theme()


def get_metric_card_style():
    """Default metric card style"""
    theme = _get_theme()
    return f"""
            QFrame#metricCard {{
                background-color: {theme.colors.BG_SIDEBAR};
                border: 1px solid {theme.colors.BORDER_COLOR};
                border-radius: 8px;
                padding: 0px;
            }}
            QFrame#metricCard:hover {{
                border-color: {theme.colors.ACCENT_BLUE};
            }}
        """


def get_metric_card_style_with_border(border_color):
    """Metric card style with custom border color"""
    theme = _get_theme()
    return f"""
            QFrame#metricCard {{
                background-color: {theme.colors.BG_SIDEBAR};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 0px;
            }}
            QFrame#metricCard:hover {{
                border-color: {theme.colors.ACCENT_BLUE};
            }}
        """


def get_metric_card_loading_style():
    """Metric card style for loading state"""
    theme = _get_theme()
    return f"""
            QFrame#metricCard {{
                background-color: {theme.colors.BG_SIDEBAR};
                border: 1px solid {theme.colors.ACCENT_BLUE};
                border-radius: 8px;
                padding: 0px;
            }}
        """


def get_metric_card_error_style():
    """Metric card style for error state"""
    theme = _get_theme()
    return f"""
                QFrame#metricCard {{
                    background-color: {theme.colors.BG_SIDEBAR};
                    border: 1px solid {theme.colors.TEXT_DANGER};
                    border-radius: 8px;
                    padding: 0px;
                }}
            """


def get_metric_card_normal_style():
    """Metric card style for normal data display"""
    theme = _get_theme()
    return f"""
                QFrame#metricCard {{
                    background-color: {theme.colors.BG_SIDEBAR};
                    border: 1px solid {theme.colors.BORDER_COLOR};
                    border-radius: 8px;
                    padding: 0px;
                }}
                QFrame#metricCard:hover {{
                    border-color: {theme.colors.ACCENT_BLUE};
                }}
            """


def get_title_label_style():
    """Style for metric card title label"""
    theme = _get_theme()
    return f"""
            QLabel {{
                color: {theme.colors.TEXT_LIGHT};
                background-color: transparent;
                border: none;
                margin: 0px;
            }}
        """


def get_metric_label_style():
    """Style for metric card value label"""
    theme = _get_theme()
    return f"""
            QLabel {{
                color: {theme.colors.TEXT_LIGHT};
                background-color: transparent;
                border: none;
                margin: 8px 0px;
            }}
        """


def get_subtitle_label_style():
    """Style for metric card subtitle label"""
    theme = _get_theme()
    return f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                background-color: transparent;
                border: none;
                margin: 0px;
            }}
        """


def get_page_title_style():
    """Style for page title label"""
    theme = _get_theme()
    return f"""
            QLabel {{
                color: {theme.colors.TEXT_LIGHT};
                background-color: transparent;
                border: none;
                margin: 24px 0px 32px 0px;
                padding: 0px 24px;
            }}
        """


def get_scroll_area_style():
    """Style for main scroll area"""
    return f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """
