"""
NodesPage-specific styles
Contains styles that are unique to NodesPage and defined inline in the page.
"""

# Shared color constants
MUTED_COLOR = "#666"

# NoDataWidget styles (extracted from inline styles in NodesPage.py)

def get_no_data_icon_style():
    """Style for no data icon"""
    return f"font-size: 48px; color: {MUTED_COLOR};"

def get_no_data_message_style():
    """Style for no data message"""
    return f"font-size: 18px; color: {MUTED_COLOR};"
