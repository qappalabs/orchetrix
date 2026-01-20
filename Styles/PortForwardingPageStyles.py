"""
PortForwardingPage-specific styles
Contains styles that are unique to PortForwardingPage and defined inline in the page.
"""

import textwrap

# Stop button color constants
STOP_BUTTON_BG = "#f44336"
STOP_BUTTON_TEXT = "#ffffff"
STOP_BUTTON_HOVER = "#da190b"
STOP_BUTTON_PRESSED = "#c82333"
STOP_BUTTON_DISABLED_BG = "rgba(204, 204, 204, 0.6)"
STOP_BUTTON_DISABLED_FG = "rgba(102, 102, 102, 0.6)"

# Style for Stop All button (red warning button)
STOP_ALL_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {STOP_BUTTON_BG};
        color: {STOP_BUTTON_TEXT};
        border: none;
        border-radius: 4px;
        padding: 5px 10px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {STOP_BUTTON_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {STOP_BUTTON_PRESSED};
    }}
    QPushButton:disabled {{
        background-color: {STOP_BUTTON_DISABLED_BG};
        color: {STOP_BUTTON_DISABLED_FG};
    }}
""".strip()
