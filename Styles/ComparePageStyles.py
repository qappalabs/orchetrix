"""
ComparePage-specific styles
Contains styles that are unique to ComparePage and defined inline in the page.
"""

from UI.Styles import AppStyles
from UI.ThemeManager import get_theme_manager


def _build_button_style(theme, padding: str = "5px 10px", include_pressed: bool = False) -> str:
    """
    Helper to build theme-aware button styles with common properties.

    Args:
        theme: The current theme object
        padding: CSS padding value for the button
        include_pressed: Whether to include QPushButton:pressed state
    """
    style = f"""
            QPushButton {{
                background-color: {theme.colors.BG_DARKER};
                color: {theme.colors.TEXT_LIGHT};
                border: 1px solid {theme.colors.BORDER_COLOR};
                border-radius: 4px;
                padding: {padding};
            }}
            QPushButton:hover {{
                background-color: {theme.colors.BG_MEDIUM};
            }}"""
    if include_pressed:
        style += f"""
            QPushButton:pressed {{
                background-color: {theme.colors.BG_DARK};
            }}"""
    return style


# Edit button style (used for both left and right)
def get_edit_btn_style():
    """Edit button style using current theme"""
    theme = get_theme_manager().get_current_theme()
    return _build_button_style(theme, padding="5px 15px", include_pressed=False)


# Save button style (used for both left and right)
def get_save_btn_style():
    """Save button style using current theme"""
    theme = get_theme_manager().get_current_theme()
    return _build_button_style(theme, padding="5px 10px", include_pressed=True)


# Deploy button style (used for both left and right) - Uses semantic success color
def get_deploy_btn_style():
    """Deploy button style with success color.

    Note: The green colors (#4CAF50, #45a049) are intentionally hardcoded
    to represent semantic "success" actions. These should be updated centrally
    here if the app's semantic color scheme changes.
    """
    return """
            QPushButton {
                background-color: #4CAF50;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """


# Cancel button style (used for both left and right) - Uses semantic error color
def get_cancel_btn_style():
    """Cancel button style with error color.

    Note: The red colors (#f44336, #d32f2f) are intentionally hardcoded
    to represent semantic "error/cancel" actions. These should be updated
    centrally here if the app's semantic color scheme changes.
    """
    return """
            QPushButton {
                background-color: #f44336;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """


# Error widget style - Uses semantic error color
def get_error_widget_style():
    """Error widget style with error color"""
    return """
                QLabel {
                    color: #ff4444;
                    background-color: rgba(255, 68, 68, 0.1);
                    padding: 10px;
                    border-radius: 4px;
                    border: 1px solid rgba(255, 68, 68, 0.3);
                }
            """


def get_edit_mode_text_box_style():
    """Text editor style when in edit mode (with blue border)

    Note: YAML editor colors are intentionally hardcoded to maintain
    VS Code-like syntax highlighting consistency regardless of app theme.
    """
    return f"""
                QTextEdit {{
                    background-color: #1E1E1E;
                    color: #D4D4D4;
                    border: 1px solid #0078d7;
                    selection-background-color: #264F78;
                    selection-color: #D4D4D4;
                    padding: 20px;
                }}
                {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
            """


# Search menu style for resource combo boxes
def get_search_menu_style():
    """Search menu style using current theme"""
    theme = get_theme_manager().get_current_theme()
    return f"""
                QMenu {{
                    background-color: {theme.colors.BG_DARKER};
                    color: {theme.colors.TEXT_LIGHT};
                    border: 1px solid {theme.colors.BORDER_COLOR};
                    border-radius: 4px;
                    padding: 5px;
                }}
                QMenu::item {{
                    padding: 5px 20px;
                    border-radius: 3px;
                }}
                QMenu::item:selected {{
                    background-color: {theme.colors.SELECTED_BG};
                }}
            """


# Search input style for resource combo boxes
def get_search_input_style():
    """Search input style using current theme"""
    theme = get_theme_manager().get_current_theme()
    return f"""
                QLineEdit {{
                    background-color: {theme.colors.BG_DARKER};
                    color: {theme.colors.TEXT_LIGHT};
                    border: 1px solid {theme.colors.BORDER_COLOR};
                    border-radius: 3px;
                    padding: 5px;
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border: 1px solid {theme.colors.ACCENT_BLUE};
                }}
            """
