"""
Terminal constants and styles - Split from TerminalPanel.py
"""

from enum import Enum
from UI.Styles import AppColors, AppStyles


class StyleConstants:
    """Centralized stylesheet constants"""

    # Terminal-specific colors - hardcoded by design for terminal authenticity
    # Terminals should remain dark in both themes for professional appearance,
    # better readability, and reduced eye strain during long sessions
    _TERMINAL_BG = "#1E1E1E"  # Dark background - terminal standard
    _TERMINAL_TEXT = "#E0E0E0"  # Light text - good contrast on dark background
    _TERMINAL_SELECTION_BG = "#264F78"  # Blue selection - VS Code terminal standard
    _TERMINAL_SELECTION_TEXT = "#E0E0E0"  # Light selection text

    TERMINAL_TEXTEDIT = f"""
        QTextEdit {{
            background-color: {_TERMINAL_BG};
            color: {_TERMINAL_TEXT};
            border: none;
            selection-background-color: {_TERMINAL_SELECTION_BG};
            selection-color: {_TERMINAL_SELECTION_TEXT};
            padding: 8px;
        }}

        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}

    """

    @staticmethod
    def get_search_highlight_colors():
        """Get theme-aware search highlight colors for terminal"""
        from UI.ThemeManager import get_theme_manager

        theme_name = get_theme_manager().get_current_theme_name()

        if theme_name == "Dark":
            return {
                "background": "#FFA500",  # Orange background - better contrast than yellow
                "foreground": "#000000",  # Black text - readable on orange
            }
        else:  # light theme
            return {
                "background": "#FFD700",  # Gold background - good contrast on dark terminal
                "foreground": "#000000",  # Black text - readable on gold
            }

    @staticmethod
    def get_terminal_text_color():
        """Get terminal text color - always light for readability on dark background"""
        return StyleConstants._TERMINAL_TEXT

    @staticmethod
    def get_terminal_background_color():
        """Get terminal background color - always dark for terminal authenticity"""
        return StyleConstants._TERMINAL_BG

    # Status message colors - intentionally hardcoded for consistent feedback
    _SUCCESS_COLOR = "#4CAF50"  # Green for success messages
    _ERROR_COLOR = "#FF6B68"  # Red for error messages

    @staticmethod
    def get_success_color():
        """Get success message color - always green for positive feedback"""
        return StyleConstants._SUCCESS_COLOR

    @staticmethod
    def get_error_color():
        """Get error message color - always red for negative feedback"""
        return StyleConstants._ERROR_COLOR

    # Non-terminal UI elements - use theme-aware AppColors for proper theme switching
    TERMINAL_WRAPPER = f"""
        QWidget#terminal_wrapper {{
            background-color: {AppColors.BG_DARKER};
            border: 1px solid {AppColors.BORDER_COLOR};
            border-bottom: none;
        }}
    """

    HEADER_CONTENT = f"""
        background-color: {AppColors.BG_DARKER};
        border-bottom: 1px solid {AppColors.BORDER_COLOR};
    """

    TAB_LABEL = f"""
        color: {AppColors.TEXT_SECONDARY};
        padding: 2px 4px;
        border-radius: 3px;
        border: none;
        font-weight: 500;
    """

    LOGS_TAB_LABEL = f"""
        color: {AppColors.TEXT_SECONDARY};
        padding: 2px 4px;
        border-radius: 3px;
        border: none;
        font-weight: 500;
    """

    TERMINAL_HEADER = f"""
        QWidget#header_widget {{
            background-color: {AppColors.BG_DARKER};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        }}
    """

    RESIZE_HANDLE = f"""
        QWidget#resize_handle {{
            background-color: {AppColors.BORDER_COLOR};
        }}
        QWidget#resize_handle:hover {{
            background-color: {AppColors.ACCENT_BLUE};
        }}
    """

    SEARCH_INPUT = f"""
        QLineEdit {{
            background-color: {AppColors.BG_DARKER};
            color: {AppColors.TEXT_LIGHT};
            border: 1px solid {AppColors.BORDER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }}
        QLineEdit:focus {{
            border-color: {AppColors.ACCENT_BLUE};
        }}
    """

    # DEPRECATED: Use AppStyles.get_dropdown_style_with_icon() instead
    # This style has the same icon path issue and should be replaced
    @staticmethod
    def get_shell_dropdown_style():
        """Get shell dropdown style with proper icon resolution"""
        return AppStyles.get_dropdown_style_with_icon()

    # Keep old constant for backward compatibility but mark as deprecated
    # WARNING: This constant uses hardcoded colors and should not be used in new code
    SHELL_DROPDOWN = f"""
        QComboBox {{
            background-color: {AppColors.BG_DARKER};
            color: {AppColors.TEXT_LIGHT};
            border: 1px solid {AppColors.BORDER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            min-width: 80px;
        }}
        QComboBox:hover {{
            border-color: {AppColors.ACCENT_BLUE};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            width: 0px;
            height: 0px;
            border: none;
        }}
    """

    TAB_CLOSE_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.TEXT_SECONDARY};
            border: none;
            border-radius: 2px;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {AppColors.HOVER_BG};
            color: {AppColors.TEXT_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: {AppColors.BG_MEDIUM};
        }}
    """


class CommandConstants(Enum):
    """Constants for command types and operations"""

    SSH = "ssh"
    EXEC = "exec"
    LOGS = "logs"
    LOCAL = "local"
    CLEAR = "clear"
    EXIT = "exit"
    QUIT = "quit"
