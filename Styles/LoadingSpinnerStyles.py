"""
LoadingSpinner-specific styles
Contains styles that are unique to LoadingSpinner and defined inline in the file.
"""

from UI.Styles import AppColors

# LoadingOverlay styles (extracted from inline styles in LoadingSpinner.py)

def get_loading_overlay_style():
    """Style for loading overlay widget"""
    return f"""
            QWidget#LoadingOverlay {{
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
            }}
        """

def get_message_label_style():
    """Style for loading message label"""
    return f"""
            QLabel {{
                color: {AppColors.TEXT_LIGHT};
                font-size: 14px;
                font-weight: 500;
                background-color: transparent;
                margin: 8px;
            }}
        """
