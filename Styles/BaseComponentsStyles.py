"""
base_components-specific styles
Contains styles that are unique to base_components and defined inline in the file.
"""

from PyQt6.QtGui import QColor

# StatusBadge styles (extracted from inline styles in base_components.py)

def get_status_badge_label_style(color):
    """Style for status badge label with dynamic color"""
    return f"color: {QColor(color).name()}; background-color: transparent;"

STATUS_BADGE_WIDGET_STYLE = "background-color: transparent;"

# Table component styles (extracted from inline styles in base_components.py)

CONTAINER_TRANSPARENT_STYLE = "background-color: transparent;"

EMPTY_STATE_MESSAGE_LABEL_STYLE = "font-size: 18px; font-weight: bold; margin-bottom: 10px;"

HEADER_RESET_STYLE = ""  # Forces header to use table's stylesheet
