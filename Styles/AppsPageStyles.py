"""
AppsPage-specific styles
Contains styles that are unique to AppsPage and defined inline in the page.
"""

from UI.Styles import AppColors, AppStyles


# Live monitoring button - Start state (green)
LIVE_MONITOR_BTN_START_STYLE = """
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: 1px solid #34ce57;
                border-radius: 4px;
                padding: 3px 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #34ce57;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                border-color: #6c757d;
                color: #adb5bd;
            }
        """


# Live monitoring button - Stop state (red)
LIVE_MONITOR_BTN_STOP_STYLE = """
                    QPushButton {
                        background-color: #dc3545;
                        color: #ffffff;
                        border: 1px solid #dc3545;
                        border-radius: 4px;
                        padding: 5px 10px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #c82333;
                    }
                    QPushButton:pressed {
                        background-color: #bd2130;
                    }
                """


# Refresh button style
REFRESH_BTN_STYLE = """
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """


# Title label style
TITLE_LABEL_STYLE = "font-size: 20px; font-weight: bold; color: #ffffff;"


# Filter label styles (namespace, workload, resource)
FILTER_LABEL_STYLE = "color: #ffffff; font-size: 13px; margin-right: 5px;"


def get_diagram_frame_style():
    """Diagram container frame style"""
    return f"""
            QFrame {{
                background-color: {AppColors.BG_MEDIUM};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                margin-top: 10px;
            }}
        """


def get_diagram_title_style():
    """Diagram title label style"""
    return f"""
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
                font-size: 11px;
                font-weight: bold;
                margin: 0px;
                padding: 0px;
                max-height: 16px;
            }}
        """


# Export button style
EXPORT_BTN_STYLE = """
            QToolButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #5d5d5d;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 12px;
                min-width: 20px;
                max-height: 16px;
            }
            QToolButton:hover {
                background-color: #4d4d4d;
            }
            QToolButton:pressed {
                background-color: #2d2d2d;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """


def get_export_menu_style():
    """Export dropdown menu style"""
    return f"""
            QMenu {{
                background-color: {AppColors.BG_MEDIUM};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 4px;
                padding: 2px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: {AppColors.TEXT_LIGHT};
                padding: 4px 12px;
                border-radius: 2px;
            }}
            QMenu::item:selected {{
                background-color: {AppColors.BG_LIGHT};
            }}
        """


def get_diagram_view_style():
    """Diagram graphics view style with scroll bars"""
    return f"""
            QGraphicsView {{
                background-color: {AppColors.BG_DARK};
                border: 1px solid {AppColors.BORDER_LIGHT};
                border-radius: 4px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """


def get_diagram_splitter_style():
    """Splitter style for diagram and status text"""
    return f"""
            QSplitter {{
                background-color: {AppColors.BG_MEDIUM};
            }}
            QSplitter::handle {{
                background-color: {AppColors.BORDER_LIGHT};
                height: 3px;
                border-radius: 1px;
                margin: 2px 0px;
            }}
            QSplitter::handle:hover {{
                background-color: {AppColors.ACCENT_BLUE};
            }}
            QSplitter::handle:pressed {{
                background-color: {AppColors.ACCENT_BLUE};
            }}
        """


def get_status_container_style():
    """Status text container frame style"""
    return f"""
            QFrame {{
                background-color: {AppColors.BG_MEDIUM};
                border: none;
                margin: 0px;
            }}
        """


def get_status_header_style():
    """Status area header label style"""
    return f"""
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
                font-size: 10px;
                font-weight: bold;
                margin: 2px 8px;
                padding: 0px;
            }}
        """


def get_status_text_style():
    """Status text area (analysis log) style"""
    return f"""
            QTextEdit {{
                background-color: {AppColors.BG_DARK};
                border: 1px solid {AppColors.BORDER_LIGHT};
                border-radius: 4px;
                color: {AppColors.TEXT_SECONDARY};
                font-size: 12px;
                padding: 8px;
                margin: 0px 2px 2px 2px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """
