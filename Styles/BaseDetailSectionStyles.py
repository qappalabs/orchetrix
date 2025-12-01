"""
Styles for BaseDetailSection component.
"""


def get_error_widget_error_style():
    """Error widget style for actual errors (red)"""
    return """
        QLabel {
            color: #ff4444;
            background-color: rgba(255, 68, 68, 0.1);
            padding: 10px;
            border-radius: 4px;
            border: 1px solid rgba(255, 68, 68, 0.3);
        }
    """


def get_error_widget_info_style():
    """Error widget style for info messages (gray)"""
    return """
        QLabel {
            color: #888888;
            background-color: rgba(136, 136, 136, 0.1);
            padding: 10px;
            border-radius: 4px;
            border: 1px solid rgba(136, 136, 136, 0.3);
        }
    """
