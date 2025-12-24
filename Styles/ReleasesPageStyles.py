"""
ReleasesPage-specific styles
Contains styles that are unique to ReleasesPage and defined inline in the page.
"""

from UI.Styles import AppColors


def get_upgrade_dialog_style():
    """Background style for upgrade dialog"""
    return f"""
            background-color: {AppColors.BG_DARK};
            color: {AppColors.TEXT_LIGHT};
        """


CHART_INPUT_STYLE = """
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
        """


VERSION_INPUT_STYLE = """
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
        """


VALUES_EDITOR_STYLE = """
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                font-family: Consolas, 'Courier New', monospace;
            }
            QTextEdit:focus {
                border: 1px solid #0078d7;
            }
        """


ATOMIC_CHECKBOX_STYLE = """
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """


CANCEL_BUTTON_STYLE = """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """


UPGRADE_BUTTON_STYLE = """
            QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0086e7;
            }
            QPushButton:pressed {
                background-color: #0063b1;
            }
        """


LOADING_BAR_STYLE = """
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                background-color: #1e1e1e;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
            }
        """


LOADING_TEXT_STYLE = "color: #ffffff; font-size: 14px;"


EMPTY_OVERLAY_STYLE = """
                color: #888888;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                padding: 20px;
                margin: 20px;
            """


ACTION_CONTAINER_STYLE = "background-color: transparent;"


MENU_STYLE = """
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                color: #ffffff;
                padding: 8px 24px 8px 36px;
                border-radius: 4px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: rgba(33, 150, 243, 0.2);
                color: #ffffff;
            }
            QMenu::item[dangerous="true"] {
                color: #ff4444;
            }
            QMenu::item[dangerous="true"]:selected {
                background-color: rgba(255, 68, 68, 0.1);
            }
        """
