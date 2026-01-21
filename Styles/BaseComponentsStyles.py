"""
base_components-specific styles
Contains styles that are unique to base_components and defined inline in the file.
"""

import logging
from PyQt6.QtGui import QColor

# StatusBadge styles (extracted from inline styles in base_components.py)

def get_status_badge_label_style(color: str) -> str:
    """
    Style for status badge label with dynamic color.

    Args:
        color: Color string (hex, named color, or RGB)

    Returns:
        str: CSS stylesheet with the specified color or fallback if invalid

    Notes:
        Invalid color inputs are logged at debug level and replaced with fallback color "#000000".
    """
    qcolor = QColor(color)
    if not qcolor.isValid():
        fallback_color = "#000000"
        logging.debug(f"Invalid color input '{color}'; using fallback '{fallback_color}'")
        qcolor = QColor(fallback_color)

    return f"color: {qcolor.name()}; background-color: transparent;"

STATUS_BADGE_WIDGET_STYLE = "background-color: transparent;"

# Table component styles (extracted from inline styles in base_components.py)

CONTAINER_TRANSPARENT_STYLE = "background-color: transparent;"

EMPTY_STATE_MESSAGE_LABEL_STYLE = "font-size: 18px; font-weight: bold; margin-bottom: 10px;"
