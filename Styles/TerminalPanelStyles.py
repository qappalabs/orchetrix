"""
TerminalPanel-specific styles
Contains styles that are unique to TerminalPanel and defined inline in the page.
"""

# Enhanced logs tab styles (extracted from inline styles in TerminalPanel.py)

ENHANCED_LOGS_TAB_LABEL_STYLE = """
                color: #4CAF50;
                background: transparent;
                font-size: 12px;
                font-weight: bold;
                text-decoration: none;
                border: none;
                outline: none;
            """

ENHANCED_LOGS_TAB_BUTTON_STYLE = """
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-right: 1px solid #3d3d3d;
                    border-left: 1px solid #3d3d3d;
                    border-bottom: 1px solid #3d3d3d;
                    border-top: 1px solid #3d3d3d;
                    padding: 0px 35px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(76, 175, 80, 0.1);
                }
                QPushButton:checked {
                    background-color: #1E1E1E;
                    border-bottom: 2px solid #4CAF50;
                }
            """

# SSH tab styles (extracted from inline styles in TerminalPanel.py)

SSH_TAB_LABEL_STYLE = """
                color: #FF9800;
                background: transparent;
                font-size: 12px;
                font-weight: bold;
                text-decoration: none;
                border: none;
                outline: none;
            """

SSH_TAB_BUTTON_STYLE = """
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-right: 1px solid #3d3d3d;
                    border-left: 1px solid #3d3d3d;
                    border-bottom: 1px solid #3d3d3d;
                    border-top: 1px solid #3d3d3d;
                    padding: 0px 35px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 152, 0, 0.1);
                }
                QPushButton:checked {
                    background-color: #1E1E1E;
                    border-bottom: 2px solid #FF9800;
                }
            """
