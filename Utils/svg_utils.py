"""
Shared SVG rendering utilities for the application.
Provides theme-aware SVG icon rendering that can be reused across all pages.
"""
import os
import re
import logging

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer


def render_svg_icon(icon_filename: str, color: str, size: int = 18) -> QPixmap:
    """
    Load an SVG from the Icons folder, recolor it, and return a QPixmap.

    Args:
        icon_filename: Filename of the SVG icon (e.g. 'activity.svg')
        color: Hex color string to apply (e.g. '#FF5733')
        size: Size of the rendered icon in pixels (square)

    Returns:
        A QPixmap with the recolored icon, or a blank pixmap on error.
    """
    # Walk up from this file (Utils/) to the project root
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_path, "Icons", icon_filename)
    try:
        with open(icon_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        # Pattern to match common sentinel colors in SVG attributes/styles
        sentinel_pattern = r'(?:#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})|black|white|currentColor|gray|grey)'

        # Replace attributes: stroke="color" or fill="color"
        svg_content = re.sub(
            rf'(stroke|fill)\s*=\s*["\']{sentinel_pattern}["\']',
            rf'\1="{color}"',
            svg_content,
            flags=re.IGNORECASE
        )

        # Replace inline styles: stroke: color or fill: color
        svg_content = re.sub(
            rf'(stroke|fill)\s*:\s*{sentinel_pattern}',
            rf'\1: {color}',
            svg_content,
            flags=re.IGNORECASE
        )

        renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
        if not renderer.isValid():
            logging.error(f"svg_utils: Invalid or malformed SVG content for '{icon_filename}'")
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            return pixmap

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        try:
            renderer.render(painter)
        finally:
            if painter.isActive():
                painter.end()
        return pixmap

    except Exception as e:
        logging.error(f"svg_utils: Error rendering SVG '{icon_filename}': {e}")
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        return pixmap
