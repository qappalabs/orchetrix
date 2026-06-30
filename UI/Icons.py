"""
Icons — provides standard icons for the application.
Icons are loaded exclusively from SVG files in the Icons/ root folder.
Theme-aware coloring is applied dynamically in memory via SVG content rewriting,
eliminating the need for separate 'light' and 'dark' icon folders.
"""
import os
import re
import logging
import sys
import tempfile

from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient
from PyQt6.QtCore import Qt, QRect, QByteArray
from PyQt6.QtSvg import QSvgRenderer

from UI.Styles import AppStyles


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            full_path = os.path.join(base_path, relative_path)
            if not os.path.exists(full_path):
                filename = os.path.basename(relative_path)
                for candidate in [
                    os.path.join(base_path, filename),
                    os.path.join(base_path, "_internal", "Icons", filename),
                    os.path.join(base_path, "Icons", filename),
                ]:
                    if os.path.exists(candidate):
                        return candidate
            return full_path
        else:
            base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
    except Exception as e:
        logging.error(f"Error resolving resource path for {relative_path}: {e}")
        return relative_path


# ---------------------------------------------------------------------------
# Color tokens that the SVG recoloring step will replace.
# SVGs use these sentinel colors; they get swapped to the active theme color.
# ---------------------------------------------------------------------------
_SVG_STROKE_TOKENS = [
    "#000000", "#000", "black",
    "#ffffff", "#fff", "white",
    "#1a1a1a", "#333333", "#333", "#666666", "#666",
    "#cccccc", "#ccc",
    # Near-white colors used in some SVGs (e.g. settings.svg uses #F5F5F5)
    "#f5f5f5", "#F5F5F5", "#f0f0f0", "#F0F0F0",
    "#eeeeee", "#EEEEEE", "#e0e0e0", "#E0E0E0",
    "#fafafa", "#FAFAFA", "#d4d4d4", "#D4D4D4",
    "#e6e6e6", "#E6E6E6", "#888888", "#292D32",
]


class Icons:
    """Static class to provide consistent icons throughout the app.

    All icons live in the single Icons/ root folder as SVG files.
    Dynamic per-theme coloring is done by rewriting the SVG's stroke/fill
    colors before rendering, so no light/ or dark/ sub-folders are needed.
    """

    ICONS_BASE_PATH = "Icons/"

    # ── Emoji / text fallbacks ──────────────────────────────────────────────
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
    BACK = "←"
    FORWARD = "→"
    MINIMIZE = "─"
    MAXIMIZE = "□"
    MAXIMIZE_ACTIVE = "❐"
    CLOSE = "✕"
    DROPDOWN_ARROW = "▼"
    RIGHT_ARROW = "▸"
    MENU_DOTS = "⋮"
    STATUS_OK = "✓"
    STATUS_ERROR = "✗"
    STATUS_WARNING = "⚠"

    # ── Internal caches ─────────────────────────────────────────────────────
    _icon_cache: dict = {}          # (path, color?) → QIcon
    _svg_path_cache: dict = {}      # (filename, color) → tmp file path

    # ── Temp directory for stylesheet-compatible colored SVG files ──────────
    _tmp_dir: str = os.path.join(tempfile.gettempdir(), "orchetrix_icons")

    # -----------------------------------------------------------------------
    # Public helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _ensure_tmp_dir() -> None:
        os.makedirs(Icons._tmp_dir, exist_ok=True)

    @staticmethod
    def _get_svg_content(svg_path: str) -> str | None:
        """Read and return the raw SVG text, or None on failure."""
        try:
            resolved = resource_path(svg_path)
            if os.path.exists(resolved):
                with open(resolved, "r", encoding="utf-8", errors="ignore") as fh:
                    return fh.read()
        except Exception as e:
            logging.error(f"Could not read SVG {svg_path}: {e}")
        return None

    @staticmethod
    def _recolor_svg(svg_content: str, color: str) -> str:
        """Replace all known sentinel stroke/fill colors in SVG with *color*."""
        result = svg_content

        # Replace attribute values: stroke="#000000"  fill="#000000"  etc.
        for token in _SVG_STROKE_TOKENS:
            escaped = re.escape(token)
            # Match inside attribute quotes
            result = re.sub(
                rf'((?:stroke|fill)\s*=\s*["\'])({escaped})(["\'])',
                rf'\g<1>{color}\g<3>',
                result,
                flags=re.IGNORECASE,
            )
            # Match inside style="…stroke:…;fill:…"
            result = re.sub(
                rf'((?:stroke|fill)\s*:\s*)({escaped})([\s;"\'])',
                rf'\g<1>{color}\g<3>',
                result,
                flags=re.IGNORECASE,
            )

        return result

    @staticmethod
    def _icon_from_svg_content(svg_content: str, size: int = 24) -> QIcon:
        """Render SVG text to a QIcon via QSvgRenderer while preserving aspect ratio."""
        from PyQt6.QtCore import QRectF
        try:
            renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))
            if not renderer.isValid():
                return QIcon()
            
            # Determine the target rectangle that preserves the SVG's aspect ratio
            svg_size = renderer.defaultSize()
            if svg_size.isEmpty():
                target_rect = QRectF(0, 0, size, size)
            else:
                # Scale SVG to fit into (size, size) while keeping aspect ratio
                w, h = float(svg_size.width()), float(svg_size.height())
                svg_ar = w / h
                
                if svg_ar > 1:  # Wider than tall
                    target_w = float(size)
                    target_h = target_w / svg_ar
                else:  # Taller than wide
                    target_h = float(size)
                    target_w = target_h * svg_ar
                
                # Center the rectangle
                x = (float(size) - target_w) / 2.0
                y = (float(size) - target_h) / 2.0
                target_rect = QRectF(x, y, target_w, target_h)

            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter, target_rect)
            painter.end()
            return QIcon(pixmap)
        except Exception as e:
            logging.error(f"SVG render failed: {e}")
            return QIcon()

    # -----------------------------------------------------------------------
    # Core public API
    # -----------------------------------------------------------------------

    @staticmethod
    def get_icon_from_path(icon_path: str, fallback_text: str | None = None) -> QIcon:
        """Load an icon from a local SVG path (no theme recoloring)."""
        cache_key = icon_path
        if cache_key in Icons._icon_cache:
            return Icons._icon_cache[cache_key]

        content = Icons._get_svg_content(icon_path)
        if content:
            icon = Icons._icon_from_svg_content(content)
            if not icon.isNull():
                Icons._icon_cache[cache_key] = icon
                return icon

        if fallback_text:
            return Icons.create_text_icon(fallback_text)
        return QIcon()

    @staticmethod
    def get_icon(icon_id: str, use_local: bool = True) -> QIcon:
        """Get an icon by its ID, SVG only (no PNG fallback)."""
        fallback_attr = icon_id.upper() if isinstance(icon_id, str) else None
        fallback_text = getattr(Icons, fallback_attr, "⚙️") if fallback_attr else "⚙️"

        if not use_local:
            return Icons.create_text_icon(fallback_text)

        cache_key = f"plain::{icon_id}"
        if cache_key in Icons._icon_cache:
            return Icons._icon_cache[cache_key]

        svg_path = os.path.join(Icons.ICONS_BASE_PATH, f"{icon_id.lower()}.svg")
        content = Icons._get_svg_content(svg_path)
        if content:
            icon = Icons._icon_from_svg_content(content)
            if not icon.isNull():
                Icons._icon_cache[cache_key] = icon
                return icon

        return Icons.create_text_icon(fallback_text)

    @staticmethod
    def get_theme_icon(icon_filename: str, theme_name: str) -> QIcon:
        """Get a theme-colored icon by its filename (e.g. 'minimize.svg').

        Reads from the single Icons/ root folder and recolors the SVG in
        memory according to the active theme — no light/ or dark/ sub-folder.
        """
        if not isinstance(icon_filename, str):
            return QIcon()

        color = Icons._theme_icon_color(theme_name)
        base_name, _ = os.path.splitext(icon_filename)
        cache_key = f"themed::{icon_filename}::{color}"

        if cache_key in Icons._icon_cache:
            return Icons._icon_cache[cache_key]

        svg_path = os.path.join(Icons.ICONS_BASE_PATH, icon_filename)
        content = Icons._get_svg_content(svg_path)
        if content:
            colored = Icons._recolor_svg(content, color)
            icon = Icons._icon_from_svg_content(colored)
            if not icon.isNull():
                Icons._icon_cache[cache_key] = icon
                return icon

        # Fallback: uncolored version
        fallback_attr = base_name.upper()
        return Icons.get_icon_from_path(
            svg_path,
            fallback_text=getattr(Icons, fallback_attr, "⚙️"),
        )

    @staticmethod
    def get_theme_icon_path(icon_filename: str, theme_name: str) -> str:
        """Return a path to a colored SVG suitable for Qt stylesheets.

        Because Qt stylesheets need a real file path, we write the colored SVG
        to a temp file the first time and reuse it on subsequent calls.
        """
        if not isinstance(icon_filename, str):
            return resource_path(os.path.join(Icons.ICONS_BASE_PATH, icon_filename))

        color = Icons._theme_icon_color(theme_name)
        cache_key = (icon_filename, color)

        if cache_key in Icons._svg_path_cache:
            return Icons._svg_path_cache[cache_key]

        svg_path = os.path.join(Icons.ICONS_BASE_PATH, icon_filename)
        content = Icons._get_svg_content(svg_path)

        if content:
            colored = Icons._recolor_svg(content, color)
            Icons._ensure_tmp_dir()
            safe_color = color.lstrip("#")
            tmp_filename = f"{os.path.splitext(icon_filename)[0]}_{safe_color}.svg"
            tmp_path = os.path.join(Icons._tmp_dir, tmp_filename)
            try:
                with open(tmp_path, "w", encoding="utf-8") as fh:
                    fh.write(colored)
                Icons._svg_path_cache[cache_key] = tmp_path
                return tmp_path
            except Exception as e:
                logging.error(f"Could not write temp SVG for stylesheet: {e}")

        # Fallback: return the raw (uncolored) path
        return resource_path(svg_path)

    @staticmethod
    def get_theme_icon_by_id(icon_id: str, theme_name: str) -> QIcon:
        """Get a theme-colored icon by its ID (without extension).

        Reads Icons/{icon_id}.svg from the root folder and applies theme color.
        """
        if not isinstance(icon_id, str):
            return QIcon()

        color = Icons._theme_icon_color(theme_name)
        cache_key = f"themed_id::{icon_id}::{color}"

        if cache_key in Icons._icon_cache:
            return Icons._icon_cache[cache_key]

        svg_path = os.path.join(Icons.ICONS_BASE_PATH, f"{icon_id}.svg")
        content = Icons._get_svg_content(svg_path)
        if content:
            colored = Icons._recolor_svg(content, color)
            icon = Icons._icon_from_svg_content(colored)
            if not icon.isNull():
                Icons._icon_cache[cache_key] = icon
                return icon

        # Fallback to uncolored plain icon
        return Icons.get_icon(icon_id)

    @staticmethod
    def clear_cache() -> None:
        """Clear icon and path caches (call when theme changes)."""
        Icons._icon_cache.clear()
        Icons._svg_path_cache.clear()

    # -----------------------------------------------------------------------
    # Theme color helper
    # -----------------------------------------------------------------------

    @staticmethod
    def _theme_icon_color(theme_name: str) -> str:
        """Return the icon stroke/fill color for the given theme."""
        if isinstance(theme_name, str) and theme_name.lower() == "light":
            return "#000000"   # pure black for light backgrounds
        return "#ffffff"       # white for dark backgrounds

    # -----------------------------------------------------------------------
    # Drawing utilities (unchanged)
    # -----------------------------------------------------------------------

    @staticmethod
    def create_text_icon(text: str, size=AppStyles.TEXT_ICON_SIZE) -> QIcon:
        """Create a simple text-based icon."""
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(AppStyles.TEXT_ICON_COLOR))
        font = painter.font()
        font.setPointSize(AppStyles.TEXT_ICON_FONT_SIZE)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def create_tag_icon(text: str, color: str) -> QIcon:
        """Create a colored tag icon with text."""
        pixmap = QPixmap(AppStyles.TAG_ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            0, 0,
            AppStyles.TAG_ICON_SIZE.width(),
            AppStyles.TAG_ICON_SIZE.height(),
            AppStyles.TAG_ICON_RADIUS,
            AppStyles.TAG_ICON_RADIUS,
        )
        painter.setPen(QColor(AppStyles.TAG_ICON_TEXT_COLOR))
        painter.drawText(
            QRect(0, 0, AppStyles.TAG_ICON_SIZE.width(), AppStyles.TAG_ICON_SIZE.height()),
            Qt.AlignmentFlag.AlignCenter, text,
        )
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def create_logo(
        size=AppStyles.LOGO_ICON_SIZE,
        text: str = "Ox",
        start_color: str = AppStyles.LOGO_START_COLOR,
        end_color: str = AppStyles.LOGO_END_COLOR,
    ) -> QIcon:
        """Create a gradient logo icon."""
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, size.width(), size.height())
        gradient.setColorAt(0, QColor(start_color))
        gradient.setColorAt(1, QColor(end_color))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            0, 0, size.width(), size.height(),
            AppStyles.LOGO_ICON_RADIUS, AppStyles.LOGO_ICON_RADIUS,
        )
        painter.setPen(QColor(AppStyles.LOGO_TEXT_COLOR))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def get_app_logo(size=AppStyles.APP_LOGO_SIZE) -> QIcon:
        """Get the application logo from SVG, falling back to the generated logo."""
        try:
            svg_path = resource_path("Icons/logoIcon.svg")
            if os.path.exists(svg_path):
                with open(svg_path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                renderer = QSvgRenderer(QByteArray(content.encode("utf-8")))
                if renderer.isValid():
                    pixmap = QPixmap(size)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    renderer.render(painter)
                    painter.end()
                    if not pixmap.isNull():
                        return QIcon(pixmap)
        except Exception as e:
            logging.debug(f"Failed to load app logo SVG: {e}")

        return Icons.create_logo(size, "Orchestrix")
