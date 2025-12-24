"""
ChartsPage-specific styles
Contains styles that are unique to ChartsPage and defined inline in the page.
"""

from UI.Styles import AppColors


# Repository label style
REPOSITORY_LABEL_STYLE = "color: #ffffff; font-size: 12px; font-weight: normal;"


# Loading progress bar style
LOADING_BAR_STYLE = """
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 2px;
                background-color: #1e1e1e;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
            }
        """


# Loading text style
LOADING_TEXT_STYLE = "color: #aaaaaa; font-size: 12px;"


# Icon label default style (for chart icons)
ICON_LABEL_DEFAULT_STYLE = """
            QLabel {
                border-radius: 3px;
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """


# Icon label style with emoji fallback
ICON_LABEL_EMOJI_STYLE = """
                        QLabel {
                            color: #4CAF50;
                            font-size: 14px;
                            border-radius: 3px;
                            background-color: rgba(255, 255, 255, 0.05);
                            border: none;
                            padding: 0px;
                            margin: 0px;
                        }
                    """


def get_chart_detail_dialog_style():
    """Style for chart detail dialog window"""
    return f"""
            QDialog {{
                background-color: {AppColors.BG_DARK};
                color: {AppColors.TEXT_LIGHT};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 8px;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """


# Icon label style in detail dialog
DETAIL_ICON_LABEL_STYLE = "border: 1px solid #ddd; border-radius: 8px;"


# Chart name label style in detail dialog
CHART_NAME_LABEL_STYLE = "color: #2196F3; margin-bottom: 5px;"


# Description text edit style
DESCRIPTION_TEXT_STYLE = "QTextEdit { background-color: #f5f5f5; border: 1px solid #ddd; }"
