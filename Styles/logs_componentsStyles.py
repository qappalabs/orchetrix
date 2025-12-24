"""
logs_components-specific styles
Contains styles that are unique to logs_components and defined inline in the file.
"""

from UI.Styles import AppStyles

# LogsHeaderWidget styles (extracted from inline styles in logs_components.py)

LOGS_HEADER_WIDGET_STYLE = """
            QWidget {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
            }
            QComboBox {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
                font-size: 12px;
                min-width: 80px;
                max-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: white;
                selection-background-color: #2196F3;
            }
            QCheckBox {
                color: white;
                font-size: 12px;
                padding: 2px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #666;
                border-radius: 3px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
        """

POD_INFO_LABEL_STYLE = "font-weight: bold; color: #4CAF50; font-size: 11px;"

SEARCH_RESULTS_LABEL_STYLE = "color: #4CAF50; font-size: 10px; font-weight: bold;"

# EnhancedLogsViewer styles (extracted from inline styles in logs_components.py)

def get_logs_display_style():
    """Style for logs display text edit"""
    return f"""
            QTextEdit {{
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: none;
                selection-background-color: #264F78;
                padding: 8px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """

STATUS_INDICATOR_STYLE = """
            QLabel {
                background-color: rgba(45, 45, 45, 0.8);
                color: #4CAF50;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                margin: 4px;
            }
        """

def get_status_indicator_style_with_color(color):
    """Style for status indicator with custom color"""
    return f"""
            QLabel {{
                background-color: rgba(45, 45, 45, 0.8);
                color: {color};
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                margin: 4px;
            }}
        """
