"""
OverviewPage-specific styles
Contains styles that are unique to OverviewPage and defined inline in the page.
"""

from UI.Styles import AppStyles, AppColors


def get_metric_card_style(colors):
    """Default metric card style"""
    return f"""
            QFrame#metricCard {{
                background-color: {colors['bg_secondary']};
                border: 1px solid {colors['border_color']};
                border-radius: 8px;
                padding: 0px;
            }}
            QFrame#metricCard:hover {{
                border-color: {colors['accent_color']};
            }}
        """


def get_metric_card_style_with_border(colors, border_color):
    """Metric card style with custom border color"""
    return f"""
            QFrame#metricCard {{
                background-color: {colors['bg_secondary']};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 0px;
            }}
            QFrame#metricCard:hover {{
                border-color: {colors['accent_color']};
            }}
        """


def get_metric_card_loading_style(colors):
    """Metric card style for loading state"""
    return f"""
            QFrame#metricCard {{
                background-color: {colors['bg_secondary']};
                border: 1px solid {colors['accent_color']};
                border-radius: 8px;
                padding: 0px;
            }}
        """


def get_metric_card_error_style(colors):
    """Metric card style for error state"""
    return f"""
                QFrame#metricCard {{
                    background-color: {colors['bg_secondary']};
                    border: 1px solid #ff4444;
                    border-radius: 8px;
                    padding: 0px;
                }}
            """


def get_metric_card_normal_style(colors):
    """Metric card style for normal data display"""
    return f"""
                QFrame#metricCard {{
                    background-color: {colors['bg_secondary']};
                    border: 1px solid {colors['border_color']};
                    border-radius: 8px;
                    padding: 0px;
                }}
                QFrame#metricCard:hover {{
                    border-color: {colors['accent_color']};
                }}
            """


def get_title_label_style(colors):
    """Style for metric card title label"""
    return f"""
            QLabel {{
                color: {colors['text_primary']};
                background-color: transparent;
                border: none;
                margin: 0px;
            }}
        """


def get_metric_label_style(colors):
    """Style for metric card value label"""
    return f"""
            QLabel {{
                color: {colors['text_primary']};
                background-color: transparent;
                border: none;
                margin: 8px 0px;
            }}
        """


def get_subtitle_label_style(colors):
    """Style for metric card subtitle label"""
    return f"""
            QLabel {{
                color: {colors['text_secondary']};
                background-color: transparent;
                border: none;
                margin: 0px;
            }}
        """


def get_page_title_style():
    """Style for page title label"""
    return f"""
            QLabel {{
                color: {getattr(AppColors, 'TEXT_LIGHT', '#ffffff')};
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
