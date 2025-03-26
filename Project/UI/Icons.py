from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QFont
from PyQt6.QtCore import Qt, QRect, QSize
import os

"""
This module provides standard icons for the application.
Icons can be loaded from local paths or use fallback emoji/text.
Support for both SVG and PNG formats.
"""

class Icons:
    """Static class to provide consistent icons throughout the app"""
    
    # Base path for icons - change this to your local directory
    ICONS_BASE_PATH = "icons/"
    
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
        # Check if already cached
        if icon_path in Icons._icon_cache:
            return Icons._icon_cache[icon_path]
        
        # Try to load from file
        try:
            icon = QIcon(icon_path)
            
            # Test if icon loaded successfully
            if not icon.isNull():
                # Cache the icon
                Icons._icon_cache[icon_path] = icon
                return icon
        except Exception as e:
            print(f"Error loading icon from {icon_path}: {e}")
        
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
        
        # Try to load from SVG first - but don't print errors
        try:
            icon_path_svg = os.path.join(Icons.ICONS_BASE_PATH, f"{icon_id.lower()}.svg")
            if os.path.exists(icon_path_svg):  # Check if file exists before trying to load
                icon = QIcon(icon_path_svg)
                if not icon.isNull():
                    return icon
        except Exception:
            pass
                
        # Try PNG as fallback - but don't print errors
        try:
            icon_path_png = os.path.join(Icons.ICONS_BASE_PATH, f"{icon_id.lower()}.png")
            if os.path.exists(icon_path_png):  # Check if file exists before trying to load
                icon = QIcon(icon_path_png)
                if not icon.isNull():
                    return icon
        except Exception:
            pass
        
        # Fall back to text icon
        return Icons.create_text_icon(fallback_text)
    
    @staticmethod
    def create_text_icon(text, size=QSize(24, 24)):
        """Create a simple text-based icon"""
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw text
        painter.setPen(QColor(255, 255, 255))
        font = painter.font()
        font.setPointSize(size.width() // 2)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        
        return QIcon(pixmap)
    
    @staticmethod
    def create_tag_icon(text, color):
        """Create a colored tag icon with text"""
        pixmap = QPixmap(28, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background rectangle
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 28, 16, 2, 2)
        
        # Draw text
        painter.setPen(QColor("black"))
        painter.drawText(QRect(0, 0, 28, 16), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        
        return QIcon(pixmap)
    
    @staticmethod
    def create_logo(size=QSize(24, 24), text="Ox",
                   start_color="#FF8A00", end_color="#FF5722"):
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
        painter.drawRoundedRect(0, 0, size.width(), size.height(), 6, 6)
        
        # Add text
        painter.setPen(QColor("black"))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        
        return QIcon(pixmap)
    
    @staticmethod
    def get_app_logo(size=QSize(120, 30)):
        """Get the application logo, trying SVG first, then PNG"""
        try:
            # Try SVG first
            svg_path = "icons/logoIcon.svg"
            pixmap = QPixmap(svg_path)
            if not pixmap.isNull():
                return QIcon(pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))
                                         
            # Try PNG as fallback
            png_path = "icons/logoIcon.png"
            pixmap = QPixmap(png_path)
            if not pixmap.isNull():
                return QIcon(pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))
        except Exception as e:
            print(f"Error loading logo: {e}")
            
        # Fallback to a generated logo
        return Icons.create_logo(size, "Orchestrix", "#4A9EFF", "#0066CC")