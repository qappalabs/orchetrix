"""
DeploymentsPage-specific styles
Contains styles that are unique to DeploymentsPage and defined inline in the page.
"""

from PyQt6.QtGui import QColor
from UI.Styles import AppColors


# Style for MultiStatusWidget background
MULTI_STATUS_WIDGET_BACKGROUND_STYLE = "background-color: transparent;"


def get_empty_status_style():
    """Style for empty/none status label"""
    return get_default_status_style()


def get_available_status_style():
    """Style for 'Available' status label"""
    return f"color: {QColor(AppColors.STATUS_ACTIVE).name()};"


def get_progressing_status_style():
    """Style for 'Progressing' status label"""
    return f"color: {QColor(AppColors.STATUS_PROGRESS).name()};"


def get_default_status_style():
    """Style for default/unknown status label"""
    return f"color: {QColor(AppColors.TEXT_TABLE).name()};"
