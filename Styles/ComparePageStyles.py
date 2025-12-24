"""
ComparePage-specific styles
Contains styles that are unique to ComparePage and defined inline in the page.
"""

from UI.Styles import AppStyles


# Edit button style (used for both left and right)
EDIT_BTN_STYLE = """
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """


# Save button style (used for both left and right)
SAVE_BTN_STYLE = """
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """


# Deploy button style (used for both left and right)
DEPLOY_BTN_STYLE = """
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


# Cancel button style (used for both left and right)
CANCEL_BTN_STYLE = """
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


# Error widget style
ERROR_WIDGET_STYLE = """
                QLabel {
                    color: #ff4444;
                    background-color: rgba(255, 68, 68, 0.1);
                    padding: 10px;
                    border-radius: 4px;
                    border: 1px solid rgba(255, 68, 68, 0.3);
                }
            """


def get_edit_mode_text_box_style():
    """Text editor style when in edit mode (with blue border)"""
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
SEARCH_MENU_STYLE = """
                QMenu {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px 20px;
                    border-radius: 3px;
                }
                QMenu::item:selected {
                    background-color: #0078d7;
                }
            """


# Search input style for resource combo boxes
SEARCH_INPUT_STYLE = """
                QLineEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 3px;
                    padding: 5px;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border: 1px solid #0078d7;
                }
            """
