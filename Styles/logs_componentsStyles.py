"""
logs_components-specific styles
Contains static styles for logs_components extracted for centralized maintenance.
"""

from UI.Styles import AppStyles

# LogsHeaderWidget styles
def get_logs_header_widget_style():
    """Get header widget style."""
    return """
        #logsHeader {
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
            background: transparent;
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
            background: transparent;
        }
    """

def get_pod_info_label_style():
    """Get pod info label style."""
    return "font-weight: bold; color: #4CAF50; font-size: 11px; background: transparent;"

def get_search_results_label_style():
    """Get search results label style."""
    return "color: #4CAF50; font-size: 10px; font-weight: bold; background: transparent;"

# EnhancedLogsViewer styles
def get_logs_display_style():
    """Get logs display text edit style."""
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

def get_status_indicator_style():
    """Get default status indicator style."""
    return get_status_indicator_style_with_color("#4CAF50")

def get_status_indicator_style_with_color(color):
    """Get status indicator style with custom color."""
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
