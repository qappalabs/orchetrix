"""
LoadingSpinner-specific styles
Contains styles that are unique to LoadingSpinner and defined inline in the file.
"""

from UI.ThemeManager import get_theme_manager


class LoadingSpinnerConstants:
    """Constants for loading spinner styling with theme awareness"""

    @staticmethod
    def get_accent_color():
        """Get theme-aware accent color for spinners"""
        theme_manager = get_theme_manager()
        return theme_manager.get_current_theme().colors.ACCENT_ORANGE

    @staticmethod
    def get_secondary_color():
        """Get theme-aware secondary color for compact spinners"""
        theme_manager = get_theme_manager()
        return theme_manager.get_current_theme().colors.TEXT_SECONDARY

    @staticmethod
    def get_white_color():
        """Get theme-aware white color for Google-style spinner"""
        # For Google-style spinner, we use a consistent white color
        # but could be theme-aware if needed
        return "#ffffff"

    @staticmethod
    def get_overlay_background():
        """Get theme-aware overlay background color"""
        theme_manager = get_theme_manager()
        return theme_manager.get_current_theme().colors.OVERLAY_BG_COLOR

    @staticmethod
    def get_text_color():
        """Get theme-aware text color for loading messages"""
        theme_manager = get_theme_manager()
        return theme_manager.get_current_theme().colors.TEXT_LIGHT


# LoadingOverlay styles (extracted from inline styles in LoadingSpinner.py)


def get_loading_overlay_style():
    """Style for loading overlay widget with theme awareness"""
    return f"""
            QWidget#LoadingOverlay {{
                background-color: {LoadingSpinnerConstants.get_overlay_background()};
                border-radius: 8px;
            }}
        """


def get_message_label_style():
    """Style for loading message label with theme awareness"""
    return f"""
            QLabel#LoadingMessage {{
                color: {LoadingSpinnerConstants.get_text_color()};
                font-size: 14px;
                font-weight: 500;
                background-color: transparent;
                margin: 8px;
            }}
        """
