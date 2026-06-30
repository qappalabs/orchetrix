"""
TerminalPanel - specific styles
Contains styles that are unique to TerminalPanel and defined inline in the page.
"""

from UI.terminal.terminal_constants import StyleConstants


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to RGB string for rgba() usage."""
    hex_color = hex_color.lstrip("#")

    # Validate hex color format
    if len(hex_color) != 6:
        raise ValueError(
            f"Hex color must be exactly 6 characters after removing '#', got {len(hex_color)}: '{hex_color}'"
        )

    if not all(c in "0123456789abcdefABCDEF" for c in hex_color):
        raise ValueError(
            f"Hex color contains invalid characters, must be 0-9, a-f, A-F only: '{hex_color}'"
        )

    return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"


def create_tab_label_style(color: str) -> str:
    """Create label style for a tab with the given color."""
    return f"""
                color: {color};
                background: transparent;
                font-size: 12px;
                font-weight: bold;
                text-decoration: none;
                border: none;
                outline: none;
            """


def create_tab_button_style(
    color: str, border_color: str, background_color: str
) -> str:
    """Create button style for a tab with the given colors."""
    rgb = _hex_to_rgb(color)
    return f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {border_color};
                    padding: 0px 35px;
                    margin: 0px;
                }}
                QPushButton:hover {{
                    background-color: rgba({rgb}, 0.1);
                }}
                QPushButton:checked {{
                    background-color: {background_color};
                    border-bottom: 2px solid {color};
                }}
            """


def get_logs_tab_label_style() -> str:
    """Get logs tab label stylesheet using theme-aware colors."""
    return create_tab_label_style(StyleConstants.get_logs_info_color())


def get_logs_tab_button_style() -> str:
    """Get logs tab button stylesheet using theme-aware colors."""
    return create_tab_button_style(
        StyleConstants.get_logs_info_color(),
        StyleConstants.get_logs_header_border(),
        StyleConstants.get_terminal_background_color(),
    )


def get_ssh_tab_label_style() -> str:
    """Get SSH tab label stylesheet using theme-aware colors."""
    return create_tab_label_style(StyleConstants.get_ssh_warning_color())


def get_ssh_tab_button_style() -> str:
    """Get SSH tab button stylesheet using theme-aware colors."""
    return create_tab_button_style(
        StyleConstants.get_ssh_warning_color(),
        StyleConstants.get_logs_header_border(),
        StyleConstants.get_terminal_background_color(),
    )


