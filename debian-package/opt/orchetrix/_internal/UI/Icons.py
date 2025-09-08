from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QFont
from PyQt6.QtCore import Qt, QRect, QSize
import os
import logging
import sys

from UI.Styles import AppStyles, AppColors  # Import AppStyles and AppColors for styling

# Define resource_path function directly in this file to ensure it's always available
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            
            # Log the resolved path for debugging
            logging.debug(f"Resolving resource: {relative_path} from base {base_path}")
            full_path = os.path.join(base_path, relative_path)
            exists = os.path.exists(full_path)
            logging.debug(f"Resolved path {full_path} exists: {exists}")
            
            # If file doesn't exist, try alternative paths
            if not exists:
                # Try without subdirectory
                filename = os.path.basename(relative_path)
                alt_path = os.path.join(base_path, filename)
                if os.path.exists(alt_path):
                    logging.debug(f"Found alternative path: {alt_path}")
                    return alt_path
                
                # Try in _internal/Icons directory (PyInstaller structure)
                alt_path2 = os.path.join(base_path, "_internal", "Icons", filename)
                if os.path.exists(alt_path2):
                    logging.debug(f"Found in _internal/Icons subdirectory: {alt_path2}")
                    return alt_path2
                
                # Try in Icons subdirectory
                alt_path3 = os.path.join(base_path, "Icons", filename)
                if os.path.exists(alt_path3):
                    logging.debug(f"Found in icons subdirectory: {alt_path3}")
                    return alt_path3
            
            return full_path
        else:
            # Running in normal Python environment
            base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
    except Exception as e:
        logging.error(f"Error resolving resource path for {relative_path}: {e}")
        return relative_path

"""
This module provides standard icons for the application.
Icons can be loaded from local paths or use fallback emoji/text.
Support for both SVG and PNG formats.
"""

class Icons:
    """Static class to provide consistent icons throughout the app"""
    
    # Base path for icons - change this to your local directory
    ICONS_BASE_PATH = "Icons/"
    
    # Emoji-based fallback icons
    CLUSTER = "⚙️"
    NODES = "💻"
    WORKLOADS = "📦"
    CONFIG = "📝"
    NETWORK = "🌐"
    STORAGE = "📂"
    HELM = "⎈"
    ACCESS_CONTROL = "🔐"
    CUSTOM_RESOURCES = "🧩"
    NAMESPACES = "🔖"
    EVENTS = "🕒"
    APPS = "📱"
    
    HOME = "🏠"
    PREFERENCES = "⚙️"
    PROFILE = "👤"
    NOTIFICATIONS = "🔔"
    HELP = "❓"
    
    COMPARE = "🔍"
    TERMINAL = "⌨️"
    AI_ASSIS = "💬"
    
    # Navigation
    BACK = "←"
    FORWARD = "→"
    
    # Window controls
    MINIMIZE = "─"
    MAXIMIZE = "□"
    MAXIMIZE_ACTIVE = "❐"
    CLOSE = "✕"
    
    # Menu indicators
    DROPDOWN_ARROW = "▼"
    RIGHT_ARROW = "▸"
    MENU_DOTS = "⋮"
    
    # Status
    STATUS_OK = "✓"
    STATUS_ERROR = "✗"
    STATUS_WARNING = "⚠"
    
    # Cache to store loaded icons
    _icon_cache = {}
    
    
    @staticmethod
    def get_icon_from_path(icon_path, fallback_text=None):
        """
        Load an icon from a local file path with emoji fallback
        Enhanced with better error handling for PyInstaller
        """
        # Check if already cached
        if icon_path in Icons._icon_cache:
            return Icons._icon_cache[icon_path]
        
        # Try to load from file
        try:
            # Use resource_path to resolve the path
            resolved_path = resource_path(icon_path)
            
            # Check if file exists before creating QIcon
            if os.path.exists(resolved_path):
                icon = QIcon(resolved_path)
                
                # Test if icon loaded successfully
                if not icon.isNull():
                    # Cache the icon
                    Icons._icon_cache[icon_path] = icon
                    logging.debug(f"Successfully loaded icon: {icon_path}")
                    return icon
                else:
                    logging.warning(f"QIcon created but is null for: {icon_path}")
            else:
                logging.warning(f"Icon file does not exist: {resolved_path}")
                
        except Exception as e:
            logging.error(f"Failed to load icon from {icon_path}: {e}")
        
        # If we get here, loading failed - use fallback
        if fallback_text:
            logging.debug(f"Using fallback text '{fallback_text}' for icon: {icon_path}")
            return Icons.create_text_icon(fallback_text)
        
        # Last resort - empty icon
        logging.warning(f"No fallback available for icon: {icon_path}")
        return QIcon()
    
    @staticmethod
    def get_icon(icon_id, use_local=True):
        """
        Get an icon by its ID, trying SVG first, then PNG
        """
        # Get the fallback text for this icon
        fallback_attr = icon_id.upper() if isinstance(icon_id, str) else None
        fallback_text = getattr(Icons, fallback_attr, "⚙️") if fallback_attr else "⚙️"
        
        # If not using local files, return text icon directly
        if not use_local:
            return Icons.create_text_icon(fallback_text)
        
        # Try to load from SVG first
        try:
            icon_path_svg = os.path.join(Icons.ICONS_BASE_PATH, f"{icon_id.lower()}.svg")
            resolved_path_svg = resource_path(icon_path_svg)
            
            if os.path.exists(resolved_path_svg):  # Check if file exists before trying to load
                icon = QIcon(resolved_path_svg)
                if not icon.isNull():
                    Icons._icon_cache[icon_id] = icon
                    return icon
        except Exception as e:
            logging.debug(f"Failed to load SVG icon {icon_id}: {e}")
                
        # Try PNG as fallback
        try:
            icon_path_png = os.path.join(Icons.ICONS_BASE_PATH, f"{icon_id.lower()}.png")
            resolved_path_png = resource_path(icon_path_png)

            if os.path.exists(resolved_path_png):  # Check if file exists before trying to load
                icon = QIcon(resolved_path_png)
                if not icon.isNull():
                    Icons._icon_cache[icon_id] = icon
                    return icon
        except Exception as e:
            logging.debug(f"Failed to load PNG icon {icon_id}: {e}")
        
        # Fall back to text icon
        return Icons.create_text_icon(fallback_text)
    
    @staticmethod
    def create_text_icon(text, size=AppStyles.TEXT_ICON_SIZE):
        """Create a simple text-based icon"""
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw text with centralized styling
        painter.setPen(QColor(AppStyles.TEXT_ICON_COLOR))
        font = painter.font()
        font.setPointSize(AppStyles.TEXT_ICON_FONT_SIZE)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        
        return QIcon(pixmap)
    
    @staticmethod
    def create_tag_icon(text, color):
        """Create a colored tag icon with text"""
        pixmap = QPixmap(AppStyles.TAG_ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background rectangle
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, AppStyles.TAG_ICON_SIZE.width(), AppStyles.TAG_ICON_SIZE.height(),
                              AppStyles.TAG_ICON_RADIUS, AppStyles.TAG_ICON_RADIUS)
        
        # Draw text
        painter.setPen(QColor(AppStyles.TAG_ICON_TEXT_COLOR))
        painter.drawText(QRect(0, 0, AppStyles.TAG_ICON_SIZE.width(), AppStyles.TAG_ICON_SIZE.height()),
                        Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        
        return QIcon(pixmap)
    
    @staticmethod
    def create_logo(size=AppStyles.LOGO_ICON_SIZE, text="Ox",
                   start_color=AppStyles.LOGO_START_COLOR, end_color=AppStyles.LOGO_END_COLOR):
        """Create a logo with specified dimensions and gradient"""
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create gradient background
        gradient = QLinearGradient(0, 0, size.width(), size.height())
        gradient.setColorAt(0, QColor(start_color))
        gradient.setColorAt(1, QColor(end_color))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, size.width(), size.height(), AppStyles.LOGO_ICON_RADIUS, AppStyles.LOGO_ICON_RADIUS)
        
        # Add text
        painter.setPen(QColor(AppStyles.LOGO_TEXT_COLOR))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        
        return QIcon(pixmap)
    
    @staticmethod
    def get_app_logo(size=AppStyles.APP_LOGO_SIZE):
        """Get the application logo, trying SVG first, then PNG"""
        try:
            # Try SVG first
            svg_path = resource_path("Icons/logoIcon.svg")
            if os.path.exists(svg_path):
                pixmap = QPixmap(svg_path)
                if not pixmap.isNull():
                    return QIcon(pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
                                         
            # Try PNG as fallback
            png_path = resource_path("Icons/logoIcon.png")
            if os.path.exists(png_path):
                pixmap = QPixmap(png_path)
                if not pixmap.isNull():
                    return QIcon(pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
        except Exception as e:
            logging.debug(f"Failed to load app logo: {e}")
            
        # Fallback to a generated logo
        return Icons.create_logo(size, "Orchestrix")