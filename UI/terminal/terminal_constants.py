"""
Terminal constants and styles - Split from TerminalPanel.py
"""

from enum import Enum
from UI.Styles import AppColors, AppStyles


class StyleConstants:
    """Centralized stylesheet constants"""
    TERMINAL_TEXTEDIT = f"""
        QTextEdit {{
            background-color: #1E1E1E;
            color: #E0E0E0;
            border: none;
            selection-background-color: #264F78;
            selection-color: #E0E0E0;
            padding: 8px;
        }}

        {AppStyles.UNIFIED_SCROLL_BAR_STYLE}

    """
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
            image: url(icons/down_btn.svg);
            width: 12px;
            height: 12px;
            margin-right: 8px;
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