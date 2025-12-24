"""
PortForwardingPage-specific styles
Contains styles that are unique to PortForwardingPage and defined inline in the page.
"""

# Style for Stop All button (red warning button)
STOP_ALL_BUTTON_STYLE = """
            QPushButton {
                background-color: #f44336;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c82333;
            }
        """
