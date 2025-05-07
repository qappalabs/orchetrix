from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QFont
from PyQt6.QtCore import Qt, QRect, QSize
import os
import sys

from UI.Styles import AppStyles, AppColors  # Import AppStyles and AppColors for styling

"""
This module provides standard icons for the application.
Icons can be loaded from local paths or use fallback emoji/text.
Support for both SVG and PNG formats.
"""

class Icons:
    """Static class to provide consistent icons throughout the app"""
    
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
    CHAT = "💬"
    
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
    
    # Track if we're running in a bundled app
    _is_bundled = getattr(sys, 'frozen', False)
    
    # @staticmethod
    # def resource_path(relative_path):
    #     """Get absolute path to resource, works for dev and for PyInstaller"""
    #     try:
    #         # PyInstaller creates a temp folder and stores path in _MEIPASS
    #         if getattr(sys, 'frozen', False):
    #             # Running in a bundle
    #             base_path = sys._MEIPASS
    #             # Print for debugging - can remove in production
    #             print(f"Running in bundled mode, MEIPASS: {base_path}")
    #         else:
    #             # Running in normal Python environment
    #             base_path = os.path.abspath(".")
    #             # Print for debugging - can remove in production
    #             print(f"Running in development mode, base path: {base_path}")
            
    #         full_path = os.path.join(base_path, relative_path)
    #         # Print for debugging - can remove in production
    #         print(f"Resource path: {full_path}")
            
    #         # Check if the file exists
    #         if not os.path.exists(full_path):
    #             print(f"Warning: Resource file does not exist: {full_path}")
    #             # List directory contents for debugging
    #             parent_dir = os.path.dirname(full_path)
    #             if os.path.exists(parent_dir):
    #                 print(f"Directory contents of {parent_dir}:")
    #                 for f in os.listdir(parent_dir):
    #                     print(f"  - {f}")
    #             else:
    #                 print(f"Parent directory does not exist: {parent_dir}")
            
    #         return full_path
    #     except Exception as e:
    #         print(f"Error in resource_path: {e}")
    #         return relative_path
    # Add this to your Icons.py resource_path method
    def resource_path(relative_path):
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
                print(f"Running in bundled mode, MEIPASS: {base_path}")
            else:
                base_path = os.path.abspath(".")
                print(f"Running in development mode, base path: {base_path}")
            
            full_path = os.path.join(base_path, relative_path)
            
            # Check if the file exists
            if os.path.exists(full_path):
                return full_path
            else:
                print(f"Warning: Resource file not found: {full_path}")
                # Fall back to trying relative path directly
                if os.path.exists(relative_path):
                    return relative_path
                else:
                    print(f"Warning: Also failed with direct relative path: {relative_path}")
                    
                    # Last resort: search in all known resource directories
                    for dirname in ['icons', 'images', 'logos']:
                        test_path = os.path.join(dirname, os.path.basename(relative_path))
                        if os.path.exists(test_path):
                            print(f"Found resource at: {test_path}")
                            return test_path
            
            # Return the original path as last resort
            return relative_path
        except Exception as e:
            print(f"Error in resource_path: {e}")
            return relative_path
        
    @staticmethod
    def get_icon_from_path(icon_path, fallback_text=None):
        """
        Load an icon from a local file path with emoji fallback
        
        Args:
            icon_path (str): Path to the icon file
            fallback_text (str, optional): Text/emoji to use if loading fails
            
        Returns:
            QIcon: The loaded icon or fallback
        """
        # Use resource_path to get correct path for both development and PyInstaller
        full_path = Icons.resource_path(icon_path)
        
        # Check if already cached
        if full_path in Icons._icon_cache:
            return Icons._icon_cache[full_path]
        
        # Try to load from file
        try:
            icon = QIcon(full_path)
            
            # Test if icon loaded successfully
            if not icon.isNull():
                # Cache the icon
                Icons._icon_cache[full_path] = icon
                return icon
            else:
                print(f"Icon loaded but is null: {full_path}")
        except Exception as e:
            print(f"Error loading icon from {full_path}: {e}")
        
        # If we get here, loading failed - use fallback
        if fallback_text:
            # Create a simple text-based icon
            return Icons.create_text_icon(fallback_text)
        
        # Last resort - empty icon
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
        
        # Define base path for icons
        icons_dir = "icons"
        
        # Try to load from SVG first
        try:
            icon_path_svg = os.path.join(icons_dir, f"{icon_id.lower()}.svg")
            full_path_svg = Icons.resource_path(icon_path_svg)
            
            if os.path.exists(full_path_svg):  # Check if file exists before trying to load
                icon = QIcon(full_path_svg)
                if not icon.isNull():
                    return icon
        except Exception as e:
            print(f"Error loading SVG icon {icon_id}: {e}")
                
        # Try PNG as fallback
        try:
            icon_path_png = os.path.join(icons_dir, f"{icon_id.lower()}.png")
            full_path_png = Icons.resource_path(icon_path_png)
            
            if os.path.exists(full_path_png):  # Check if file exists before trying to load
                icon = QIcon(full_path_png)
                if not icon.isNull():
                    return icon
        except Exception as e:
            print(f"Error loading PNG icon {icon_id}: {e}")
        
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
        """Get the application logo, trying PNG first, then fallback to generated"""
        try:
            # Try PNG first for logo
            png_path = "icons/logoIcon.png"
            full_png_path = Icons.resource_path(png_path)
            
            if os.path.exists(full_png_path):
                pixmap = QPixmap(full_png_path)
                if not pixmap.isNull():
                    return QIcon(pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))
            
            # Try SVG as alternative
            svg_path = "icons/logoIcon.svg"
            full_svg_path = Icons.resource_path(svg_path)
            
            if os.path.exists(full_svg_path):
                pixmap = QPixmap(full_svg_path)
                if not pixmap.isNull():
                    return QIcon(pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))
        except Exception as e:
            print(f"Error loading logo: {e}")
            
        # Fallback to a generated logo
        return Icons.create_logo(size, "Orchestrix")