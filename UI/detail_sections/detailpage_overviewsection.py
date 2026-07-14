"""
Overview section for DetailPage component
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QSizePolicy, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QMenu, QApplication, QLayout, QGraphicsDropShadowEffect,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, QByteArray, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from typing import Dict, Any
import logging
import re
from UI.ThemeManager import get_theme_manager
from Utils.qt_utils import is_valid


class ClickableSelectableLabel(QLabel):
    """
    A QLabel that allows text selection but also emits a clicked signal 
    when clicked (and not selecting text).
    """
    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        # Mouse tracking not strictly needed unless we want hover effects

    def mouseReleaseEvent(self, event):
        # Only emit clicked if text was NOT selected during this click action
        # AND it was a left click
        if not self.hasSelectedText() and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

from .base_detail_section import BaseDetailSection
import Styles.BaseDetailSectionStyles as BaseDetailSectionStyles
import Styles.OverviewSectionStyles as OverviewSectionStyles
from Utils.data_formatters import format_age
from Utils.time_utils import TimezoneManager


class DetailPageOverviewSection(BaseDetailSection):

    def __init__(self, kubernetes_client, parent=None):
        super().__init__("Overview", kubernetes_client, parent)
        
        self._current_status_type = 'default'  # Track status type for theme updates
        self.setup_overview_ui()
        # Note: Theme signals connected via ThemeAwareMixin in BaseDetailSection

    def _render_svg_from_file(self, icon_filename, color, size=18):
        """Load an SVG from Icons folder, recolor it, and return a QPixmap."""
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_path, "Icons", icon_filename)
        try:
            with open(icon_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Pattern to match stroke or fill attributes/styles with common sentinel colors
            sentinel_pattern = r'(?:#[0-9a-fA-F]{3,6}|black|white|currentColor|gray)'
            
            # Replace attributes: stroke="color" or fill="color"
            svg_content = re.sub(rf'(stroke|fill)\s*=\s*["\']{sentinel_pattern}["\']', rf'\1="{color}"', svg_content, flags=re.IGNORECASE)
            
            # Replace inline styles: stroke: color or fill: color
            svg_content = re.sub(rf'(stroke|fill)\s*:\s*{sentinel_pattern}', rf'\1: {color}', svg_content, flags=re.IGNORECASE)
                
            renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            return pixmap
        except Exception as e:
            logging.error(f"Error rendering SVG {icon_filename}: {e}")
            return QPixmap(size, size)

    def _on_theme_changed(self, theme_name):

        # Refresh overview content style
        if hasattr(self, 'overview_content'):
            self.overview_content.setStyleSheet(
                OverviewSectionStyles.get_overview_content_style())

        # Refresh resource header widgets (static)
        if hasattr(self, 'resource_name_label'):
            self.resource_name_label.setStyleSheet(
                OverviewSectionStyles.get_overview_header_style())
        if hasattr(self, 'resource_type_label'):
             self.resource_type_label.setStyleSheet(
                 OverviewSectionStyles.get_resource_type_style())

        # Refresh section headers (static)
        if hasattr(self, 'status_header'):
            self.status_header.setStyleSheet(
                BaseDetailSectionStyles.get_section_header_style())
        if hasattr(self, 'conditions_header'):
            self.conditions_header.setStyleSheet(
                BaseDetailSectionStyles.get_section_header_style())
        if hasattr(self, 'labels_header'):
            self.labels_header.setStyleSheet(
                BaseDetailSectionStyles.get_section_header_style())

        # Refresh status widgets (static)
        if hasattr(self, 'status_text_label'):
            # This might be removed in redesign, check if exists
             self.status_text_label.setStyleSheet(
                BaseDetailSectionStyles.get_field_value_style())
                
        # Refresh Info Cards
        if hasattr(self, 'created_card'):
             self.created_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
             self.created_card.title_label.setStyleSheet(BaseDetailSectionStyles.get_card_title_style())
             self.created_card.value_label.setStyleSheet(BaseDetailSectionStyles.get_card_value_style())
             # Refresh Icon
             if hasattr(self.created_card, 'icon_info'):
                 info = self.created_card.icon_info
                 theme = get_theme_manager().get_current_theme()
                 stroke_color = theme.colors.ACCENT_BLUE if "time" in info['name'] else theme.colors.ACCENT_ORANGE
                 bg_color = f"rgba({QColor(stroke_color).red()}, {QColor(stroke_color).green()}, {QColor(stroke_color).blue()}, 0.1)"
                 
                 # Scope both styles to avoid inheritance/leakage
                 self.created_card.icon_container.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border-radius: 12px; border: none; }}")
                 self.created_card.icon_label.setStyleSheet("background: transparent; border: none;")
                 self.created_card.icon_label.setPixmap(self._render_svg_from_file(info['file'], stroke_color, size=24))
                 
        if hasattr(self, 'secondary_card'):
             self.secondary_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
             self.secondary_card.title_label.setStyleSheet(BaseDetailSectionStyles.get_card_title_style())
             self.secondary_card.value_label.setStyleSheet(BaseDetailSectionStyles.get_card_value_style())
             # Refresh Icon
             if hasattr(self.secondary_card, 'icon_info'):
                 info = self.secondary_card.icon_info
                 theme = get_theme_manager().get_current_theme()
                 stroke_color = theme.colors.ACCENT_BLUE if "time" in info['name'] else theme.colors.ACCENT_ORANGE
                 bg_color = f"rgba({QColor(stroke_color).red()}, {QColor(stroke_color).green()}, {QColor(stroke_color).blue()}, 0.1)"
                 
                 self.secondary_card.icon_container.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border-radius: 12px; border: none; }}")
                 self.secondary_card.icon_label.setStyleSheet("background: transparent; border: none;")
                 self.secondary_card.icon_label.setPixmap(self._render_svg_from_file(info['file'], stroke_color, size=24))

        # Refresh status badge with current status type (static)
        if hasattr(self, 'status_badge') and hasattr(self, '_current_status_type'):
            self.status_badge.setStyleSheet(
                BaseDetailSectionStyles.get_status_badge_style(self._current_status_type))

        # Refresh labels content (static)
        if hasattr(self, 'labels_content'):
            self.labels_content.setStyleSheet(BaseDetailSectionStyles.get_field_value_style() + """
                font-family: 'Consolas', 'Courier New', monospace;
                background-color: rgba(255, 255, 255, 13);
                padding: 8px;
                border-radius: 4px;
            """)

        # Refresh table styles (if they exist)
        try:
            if hasattr(self, 'history_table') and self.history_table:
                # Use a safe way to check if the widget still exists
                self.history_table.setStyleSheet(
                    OverviewSectionStyles.get_history_table_style())
        except (RuntimeError, AttributeError):
            # Widget might have been deleted or reference is None
            pass
            
        try:
            if hasattr(self, 'pods_table') and self.pods_table:
                if self.pods_table.isVisible():
                    self.pods_table.setStyleSheet(
                        OverviewSectionStyles.get_pods_table_style())
        except (RuntimeError, AttributeError):
            pass

        # Refresh Card Styles (Explicitly to ensure background update)
        if hasattr(self, 'conditions_card'):
             self.conditions_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
             self.conditions_card.style().unpolish(self.conditions_card)
             self.conditions_card.style().polish(self.conditions_card)

        if hasattr(self, 'labels_card'):
             self.labels_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
             self.labels_card.style().unpolish(self.labels_card)
             self.labels_card.style().polish(self.labels_card)

        if hasattr(self, 'specific_card'):
             self.specific_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
             self.specific_card.style().unpolish(self.specific_card)
             self.specific_card.style().polish(self.specific_card)
        
        try:
            if hasattr(self, 'rollback_icon_label') and self.rollback_icon_label:
                 theme = get_theme_manager().get_current_theme()
                 self.rollback_icon_label.setPixmap(self._render_svg_from_file("history.svg", BaseDetailSectionStyles.get_section_header_color()))
        except (RuntimeError, AttributeError):
             pass

        # Refresh specific header
        if hasattr(self, 'specific_header'):
            self.specific_header.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())

        # Refresh dynamic widgets in layouts by iterating through them
        if hasattr(self, 'conditions_container_layout'):
            self._refresh_dynamic_widgets_in_layout(self.conditions_container_layout)
        
        if hasattr(self, 'labels_layout'):
             self._refresh_dynamic_widgets_in_layout(self.labels_layout)

        if hasattr(self, 'specific_layout'):
            self._refresh_dynamic_widgets_in_layout(self.specific_layout)

        # Refresh scroll area style
        if hasattr(self, 'scroll_area'):
            self.scroll_area.setStyleSheet(
                OverviewSectionStyles.get_scroll_area_style())

        # DO NOT call update_ui_with_data() - eliminates race condition

    def _refresh_dynamic_widgets_in_layout(self, layout):
        if not layout:
            return

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item:
                if item.widget():
                    widget = item.widget()
                    class_name = widget.__class__.__name__

                    if class_name == 'QLabel':
                        text = widget.text()
                        if text and text.isupper() and len(text.split()) <= 2:
                            widget.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
                        elif text.endswith(':'):
                            widget.setStyleSheet(BaseDetailSectionStyles.get_field_label_style())
                        else:
                            # Check for specialized labels
                            object_name = widget.objectName()
                            if object_name == "card_title":
                                widget.setStyleSheet(BaseDetailSectionStyles.get_card_title_style())
                            elif object_name == "card_value":
                                widget.setStyleSheet(BaseDetailSectionStyles.get_card_value_style())
                            elif text in ["True", "False"]:
                                if text == "True":
                                    widget.setStyleSheet(BaseDetailSectionStyles.get_condition_badge_true_style())
                                else:
                                    widget.setStyleSheet(BaseDetailSectionStyles.get_condition_badge_false_style())
                                widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            else:
                                widget.setStyleSheet(BaseDetailSectionStyles.get_field_value_style())

                    elif class_name == 'QFrame':
                        obj_name = widget.objectName()
                        if obj_name == "info_card":
                            widget.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
                            # Force style re-application
                            widget.style().unpolish(widget)
                            widget.style().polish(widget)

                    # Recurse
                    if widget.layout():
                        self._refresh_dynamic_widgets_in_layout(widget.layout())

                elif item.layout():
                    self._refresh_dynamic_widgets_in_layout(item.layout())

    def set_raw_data(self, raw_data):

        logging.info(
            f"OverviewSection: Received raw data for {self.resource_type}, keys: {list(raw_data.keys()) if raw_data else 'None'}")
        self.current_data = raw_data
        self.update_ui_with_data(raw_data)

    def setup_overview_ui(self):

        # Create scroll area for overview content
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet(
            OverviewSectionStyles.get_scroll_area_style())
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Overview content widget
        self.overview_content = QWidget()
        self.overview_content.setStyleSheet(
            OverviewSectionStyles.get_overview_content_style())
        overview_layout = QVBoxLayout(self.overview_content)
        overview_layout.setContentsMargins(
            BaseDetailSectionStyles.CONTENT_PADDING,
            BaseDetailSectionStyles.CONTENT_PADDING,
            BaseDetailSectionStyles.CONTENT_PADDING,
            BaseDetailSectionStyles.CONTENT_PADDING
        )
        overview_layout.setSpacing(BaseDetailSectionStyles.SECTION_GAP)

        self.create_overview_sections(overview_layout)

        self.scroll_area.setWidget(self.overview_content)
        self.content_layout.addWidget(self.scroll_area)

    def create_overview_sections(self, layout):

        # Resource Header Section
        self.create_resource_header(layout)

        # Info Cards Section
        self.create_info_cards_section(layout)

        # Separator Line
        theme = get_theme_manager().get_current_theme()
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setStyleSheet(f"background-color: {theme.colors.BORDER_LIGHT}; max-height: 1px; border: none;")
        layout.addWidget(separator)

        # Conditions Section
        self.create_conditions_section(layout)

        # Resource - specific section
        self.create_specific_section(layout)

        # Labels Section
        self.create_labels_section(layout)

        layout.addStretch(1)


    def create_resource_header(self, layout):
        """Create the redesigned header with Name, Badge, and Sub-header"""
        
        # Main Header Card (Transparent background for header area)
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 10)
        header_layout.setSpacing(5)

        # Top Row: Resource Name (Left) + Ready Badge (Right)
        top_row = QHBoxLayout()
        # top_row.setSpacing(10) # Removed spacing as icon is gone
        
        self.resource_name_label = QLabel("Minikube") # Placeholder
        self.resource_name_label.setStyleSheet(
            OverviewSectionStyles.get_overview_header_style())
        self.resource_name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # KEY FIX: Enable wrapping and size policy
        self.resource_name_label.setWordWrap(True)
        self.resource_name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.resource_name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Status Badge (Pill shape -> Card shape)
        self.status_badge = QLabel("✔ Ready") # Added Checkmark
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setStyleSheet(BaseDetailSectionStyles.get_status_badge_style('success'))
        
        # Add Shadow for Card look
        shadow = QGraphicsDropShadowEffect(self.status_badge)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.status_badge.setGraphicsEffect(shadow)
        
        # Let the widget size itself naturally based on QSS padding
        self.status_badge.setMinimumHeight(24)
        self.status_badge.setMinimumWidth(80)
        self.status_badge.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        # Layout: Label takes all space (pushing badge right). AlignTop makes the badge 
        # stay at the top level and prevents it from height-stretching next to multi-line titles.
        top_row.addWidget(self.resource_name_label, 1)
        top_row.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignTop)

        # Bottom Row: Icon + Resource Type
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        
        # Package/box icon loaded from Icons folder
        icon_color = OverviewSectionStyles.get_resource_type_color()
        
        self.type_icon = QLabel()
        self.type_icon.setFixedSize(20, 20)
        self.type_icon.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.type_icon.setPixmap(self._render_svg_from_file("package-box.svg", icon_color, size=20))
        self.type_icon.setStyleSheet("border: none; background: transparent;")
        
        
        self.resource_type_label = QLabel("Node")
        self.resource_type_label.setStyleSheet(OverviewSectionStyles.get_resource_type_style())
        
        bottom_row.addWidget(self.type_icon)
        bottom_row.addWidget(self.resource_type_label)
        bottom_row.addStretch()

        header_layout.addLayout(top_row)
        header_layout.addLayout(bottom_row)
        
        layout.addWidget(header_container)

    def create_info_cards_section(self, layout):
        """Create the row of info cards (Created, Version/Age, etc.)"""
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        # Card 1: Created
        self.created_card = self._create_info_card("time_icon", "CREATED", "Unknown")
        
        # Card 2: Secondary Info (Version, IP, etc. - dynamic)
        self.secondary_card = self._create_info_card("activity_icon", "VERSION", "Unknown")
        
        # equal width for both cards
        cards_layout.addWidget(self.created_card, 1)
        cards_layout.addWidget(self.secondary_card, 1)
        
        layout.addLayout(cards_layout)

    def _create_info_card(self, icon_name, title, value):
        """Helper to create a styled info card using Horizontal Layout for strict separation"""
        card = QFrame()
        card.setObjectName("info_card") 
        card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        
        # KEY FIX: Use Preferred to allow natural grow/shrink
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        # Add Shadow Effect (matching GraphWidget style from NodesPage)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 40))
        card.setGraphicsEffect(shadow)
        
        # MAIN LAYOUT: Horizontal
        # [ Icon Label ] [ Text Layout ] [ Stretch ]
        layout = QHBoxLayout(card)
        
        # REMOVED: layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize) - causing sticky height
        
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(10) # 10px Gap
        # Note: We rely on addStretch() at the end to pack items to the left.
        
        # 1. ICON (Left)
        # 1. ICON CONTAINER (Left)
        # Determine colors and icon based on type using current theme
        theme = get_theme_manager().get_current_theme()
        
        if "time" in icon_name:
            stroke_color = theme.colors.ACCENT_BLUE
            icon_file = "events.svg"
        else: # activity/version
            stroke_color = theme.colors.ACCENT_ORANGE
            icon_file = "activity.svg"
            
        bg_color = f"rgba({QColor(stroke_color).red()}, {QColor(stroke_color).green()}, {QColor(stroke_color).blue()}, 0.1)"
            
        icon_container = QFrame()
        icon_container.setObjectName("card_icon_container")
        icon_container.setFixedSize(48, 48)
        icon_container.setStyleSheet(f"""
            QFrame#card_icon_container {{
                background-color: {bg_color}; 
                border-radius: 12px;
                border: none;
            }}
        """)
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel()
        icon_label.setPixmap(self._render_svg_from_file(icon_file, stroke_color, size=24))
        icon_label.setStyleSheet("background: transparent; border: none;")

        # KEY FIX: Rigid width and Fixed Policy for Icon
        icon_label.setFixedSize(24, 24)
        icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_layout.addWidget(icon_label)
        
        # Store icon info for theme refresh
        card.icon_info = {'name': icon_name, 'file': icon_file}
        card.icon_container = icon_container
        card.icon_label = icon_label
        
        # 2. TEXT LAYOUT (Direct VBox)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        title_label = QLabel(title)
        title_label.setObjectName("card_title")
        title_label.setStyleSheet(BaseDetailSectionStyles.get_card_title_style())
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        
        # Format value for wrapping: inject zero-width space after common separators to handle JSON and long annotations
        display_value = str(value)
        for char in ['-', '.', '/', ',', ':', '"', '{', '}', '[', ']', '(', ')', '_', '=', ' ']:
            display_value = display_value.replace(char, char + '\u200b')
            
        value_label = QLabel(display_value)
        value_label.setObjectName("card_value")
        # Ensure we use the (already updated) smaller font style
        value_label.setStyleSheet(BaseDetailSectionStyles.get_card_value_style())
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # KEY FIX: Enable Word Wrap and Dynamic Height
        value_label.setWordWrap(True)
        # Horizontal: Preferred (try to fit text), Vertical: Minimum (grow as needed)
        value_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(value_label)
        text_layout.addStretch() # Push text to top if card is tall
        
        # Add to main layout
        # Add container to main layout
        layout.addWidget(icon_container)
        layout.addLayout(text_layout)
        # Use a scaling stretch to keep text left but allow taking up space
        layout.setStretch(1, 1) 
        
        # Store references
        card.title_label = title_label
        card.value_label = value_label
        card.icon_label = icon_label
        
        return card

    def create_conditions_section(self, layout):
        """Create the conditions section with redesigned header and card"""
        
        # Main wrapper to control spacing between header and card tightly
        conditions_wrapper = QWidget()
        wrapper_layout = QVBoxLayout(conditions_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(4) # TIGHT padding between Header and Card
        
        # Header Container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 5) # Top margin 20, Bottom 0
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter) # Align items vertically
        
        # Activity icon from Icons folder
        stroke_color = BaseDetailSectionStyles.get_section_header_color()
        icon_label = QLabel()
        icon_label.setFixedSize(16, 16)
        icon_label.setPixmap(self._render_svg_from_file("activity.svg", stroke_color, size=16))
        
        # Header Text
        self.conditions_header = QLabel("CONDITIONS")
        self.conditions_header.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(self.conditions_header)
        header_layout.addStretch()
        
        wrapper_layout.addWidget(header_container)

        # Card Container
        self.conditions_card = QFrame()
        self.conditions_card.setObjectName("info_card") 
        # Revert to Info Card style as requested (provides base for shadow)
        self.conditions_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        
        # Enhanced Shadow Effect (Pop-out look)
        shadow = QGraphicsDropShadowEffect(self.conditions_card)
        shadow.setBlurRadius(8) # Larger blur for depth
        shadow.setOffset(0, 1)   # Increased vertical offset for lift
        shadow.setColor(QColor(0, 0, 0, 40)) # Darker shadow for contrast
        self.conditions_card.setGraphicsEffect(shadow)
        
        conditions_card_layout = QVBoxLayout(self.conditions_card)
        conditions_card_layout.setContentsMargins(16, 16, 16, 16)
        conditions_card_layout.setSpacing(0) # Spacing handled by separators
        
        self.conditions_container_layout = QVBoxLayout()
        self.conditions_container_layout.setSpacing(0) 

        self.no_conditions_label = QLabel("No conditions available")
        self.no_conditions_label.setStyleSheet(BaseDetailSectionStyles.get_secondary_text_style() + """
            font-style: italic;
            padding: 8px;
        """)
        self.conditions_container_layout.addWidget(self.no_conditions_label)

        conditions_card_layout.addLayout(self.conditions_container_layout)
        
        wrapper_layout.addWidget(self.conditions_card)
        
        layout.addWidget(conditions_wrapper)

    def create_labels_section(self, layout):
        """Create labels section with header icon and individual label cards"""
        
        # Main wrapper to control spacing
        labels_wrapper = QWidget()
        wrapper_layout = QVBoxLayout(labels_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(4)
        
        # Header Container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 5)
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Tag icon from Icons folder
        stroke_color = BaseDetailSectionStyles.get_section_header_color()
        icon_label = QLabel()
        icon_label.setFixedSize(16, 16)
        icon_label.setPixmap(self._render_svg_from_file("tag.svg", stroke_color, size=16))
        
        # Header Text
        self.labels_header = QLabel("LABELS")
        self.labels_header.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(self.labels_header)
        header_layout.addStretch()
        
        wrapper_layout.addWidget(header_container)
        
        # Card Container for individual label cards
        # Card Container for individual label cards
        # Card Container for individual label cards
        self.labels_card = QFrame()
        self.labels_card.setObjectName("info_card") 
        # Revert to Info Card style as requested
        self.labels_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        
        # Enhanced Shadow Effect (Pop-out look) to the OUTER card
        shadow = QGraphicsDropShadowEffect(self.labels_card)
        shadow.setBlurRadius(8) 
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.labels_card.setGraphicsEffect(shadow)
        
        self.labels_layout = QVBoxLayout(self.labels_card)
        self.labels_layout.setContentsMargins(16, 16, 16, 16)
        self.labels_layout.setSpacing(8)
        
        # Placeholder for no labels
        self.no_labels_label = QLabel("No labels")
        self.no_labels_label.setStyleSheet(BaseDetailSectionStyles.get_secondary_text_style() + """
            font-style: italic;
            padding: 8px;
        """)
        self.labels_layout.addWidget(self.no_labels_label)
        
        wrapper_layout.addWidget(self.labels_card)
        
        layout.addWidget(labels_wrapper)

    def create_specific_section(self, layout):
        """Create resource-specific section with header icon and card"""
        
        # Main wrapper to control spacing
        specific_wrapper = QWidget()
        wrapper_layout = QVBoxLayout(specific_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(4)  # Tight padding between header and card
        
        # Header Container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 5)
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Load SVG icon
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        svg_path = os.path.join(project_root, "Icons", "details-page-detail-icon.svg")
        icon_label = QLabel()
        icon_label.setFixedSize(16, 16)
        
        if os.path.exists(svg_path):
            stroke_color = BaseDetailSectionStyles.get_section_header_color()
            pixmap = self._render_svg_from_file("details-page-detail-icon.svg", stroke_color, size=16)
            icon_label.setPixmap(pixmap)
        
        # Header Text (set dynamically by add_resource_specific_fields)
        self.specific_header = QLabel("DETAILS")
        self.specific_header.setStyleSheet(BaseDetailSectionStyles.get_section_header_style())
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(self.specific_header)
        header_layout.addStretch()
        
        wrapper_layout.addWidget(header_container)
        
        # Card Container
        # Card Container
        self.specific_card = QFrame()
        self.specific_card.setObjectName("info_card")
        # Revert to Info Card style as requested
        self.specific_card.setStyleSheet(BaseDetailSectionStyles.get_info_card_style())
        
        # Enhanced Shadow Effect (Pop-out look)
        shadow = QGraphicsDropShadowEffect(self.specific_card)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.specific_card.setGraphicsEffect(shadow)
        
        self.specific_layout = QVBoxLayout(self.specific_card)
        self.specific_layout.setContentsMargins(16, 16, 16, 16)
        self.specific_layout.setSpacing(BaseDetailSectionStyles.FIELD_GAP)
        
        wrapper_layout.addWidget(self.specific_card)
        
        self.specific_section = specific_wrapper
        self.specific_section.hide()
        layout.addWidget(self.specific_section)

    def _load_data_async(self):
        """Load overview data using Kubernetes API"""
        try:
            # CRITICAL FIX: Check if we already have raw_data from the page (e.g., CustomResourcePages, NodesPage)
            # This prevents unnecessary API calls and empty detail sections
            if self.current_data is not None:
                logging.info(f"Overview section: Using existing raw_data for {self.resource_type}/{self.resource_name}")
                # Use the existing data directly instead of making API call
                self.handle_data_loaded(self.current_data)
                return
            
            # Only make API call if we don't have current_data
            logging.info(f"Overview section: No raw_data available, fetching from API for {self.resource_type}/{self.resource_name}")
            self.connect_api_signals()
            self.kubernetes_client.get_resource_detail(
                self.resource_type,
                self.resource_name,
                self.resource_namespace or "default"
            )
        except Exception as e:
            self.handle_error(f"Failed to start data loading: {str(e)}")

    def handle_api_data_loaded(self, data):

        try:
            self.disconnect_api_signals()
            if data:
                self.handle_data_loaded(data)
            else:
                # Resource exists in list but not accessible individually
                self.handle_resource_not_accessible()
        except Exception as e:
            self.handle_error(f"Error processing loaded data: {str(e)}")

    def handle_resource_not_accessible(self):

        self.hide_loading()
        # Create basic info from what we know
        basic_data = {
            'metadata': {
                'name': self.resource_name,
                'namespace': self.resource_namespace
            },
            'kind': self.resource_type.capitalize(),
            '_note': 'Resource details not accessible individually'
        }
        self.update_ui_with_basic_info(basic_data)

    def handle_api_error(self, error_message):

        self.disconnect_api_signals()

        # Provide more specific error messages for common issues
        if "customresourcedefinition" in error_message.lower() and "not found" in error_message.lower():
            error_message = f"CustomResourceDefinition '{self.resource_name}' not found. It may have been deleted or you may not have permission to view it."
        elif "forbidden" in error_message.lower():
            error_message = f"Access denied. You don't have permission to view {self.resource_type} '{self.resource_name}'."

        self.handle_error(error_message)

    def update_ui_with_data(self, data: Dict[str, Any]):

        if not data:
            return

        try:
            # Handle special resource types (charts and releases)
            if self.resource_type and self.resource_type.lower() in ["chart", "helmchart"]:
                logging.info(
                    f"OverviewSection: Updating chart UI for {self.resource_type}")
                self._update_chart_ui(data)
                return
            elif self.resource_type and self.resource_type.lower() in ["helmrelease", "release"]:
                logging.info(
                    f"OverviewSection: Updating release UI for {self.resource_type}")
                self._update_release_ui(data)
                return

            # Standard Kubernetes resource handling
            metadata = data.get("metadata", {})

            # Update resource header
            self.resource_name_label.setText(metadata.get("name", "Unnamed"))
            
            # Update Resource Type Label
            resource_info = f"{self.resource_type.capitalize()}"
            # Add Namespace if it exists
            # if "namespace" in metadata:
            #     resource_info += f"  •  {metadata.get('namespace')}" 
            # (Keeping it simple per design, or add namespace if strictly requested)
            self.resource_type_label.setText(resource_info)

            # Update creation time card
            creation_timestamp = metadata.get("creationTimestamp", "")
            if creation_timestamp:
                try:
                    formatted_time = TimezoneManager.get_instance().format_time(creation_timestamp)
                    self.created_card.value_label.setText(formatted_time)
                except Exception:
                    self.created_card.value_label.setText("Unknown")
            
            # Update Secondary Card (Dynamic based on resource)
            self._update_secondary_info_card(data)

            # Update status (Badge Only now)
            self.update_resource_status(data)

            # Update conditions
            self.update_conditions(data)

            # Update labels
            self.update_labels(data)
            
            # Ensure UI recalculates flexible height
            self.overview_content.adjustSize()
            self.overview_content.updateGeometry()
            
            # Update resource - specific fields
            self.add_resource_specific_fields(data)

        except Exception as e:
            self.handle_error(f"Error updating UI: {str(e)}")

    def _update_secondary_info_card(self, data):
        """Update the second info card based on resource type"""
        resource_type = self.resource_type.lower()
        status = data.get("status", {})
        spec = data.get("spec", {})
        
        # Default fallback
        title = "AGE"
        value = "Unknown" # Calculate age if possible, for now placeholder
        
        # Calculate Age from timestamp if needed
        creation_timestamp = data.get("metadata", {}).get("creationTimestamp", "")
        if creation_timestamp:
            value = format_age(creation_timestamp)

        if resource_type in ["node", "nodes"]:
            title = "VERSION"
            value = status.get("nodeInfo", {}).get("kubeletVersion", "Unknown")
        elif resource_type in ["pod", "pods"]:
            title = "POD IP"
            value = status.get("podIP", "Pending")
        elif resource_type in ["service", "services", "svc"]:
            title = "TYPE"
            value = spec.get("type", "ClusterIP")
        elif resource_type in ["deployment", "deployments", "replicaset", "replicasets", "statefulset", "statefulsets"]:
            title = "REPLICAS"
            ready = status.get("readyReplicas", 0)
            total = status.get("replicas", 0)
            value = f"{ready} / {total}"
        
        self.secondary_card.title_label.setText(title)
        self.secondary_card.value_label.setText(str(value))



    def update_ui_with_basic_info(self, data: Dict[str, Any]):

        try:
            metadata = data.get("metadata", {})

            # Update resource header
            self.resource_name_label.setText(metadata.get("name", "Unnamed"))

            resource_info = f"{self.resource_type.capitalize()}"
            if "namespace" in metadata:
                resource_info += f" / {metadata.get('namespace')}"
            self.resource_type_label.setText(resource_info)

            # Set creation time as unavailable
            self.created_card.title_label.setText("CREATED")
            self.created_card.value_label.setText("Details not available")

            # Set secondary card with limited-info status
            self.secondary_card.title_label.setText("STATUS")
            self.secondary_card.value_label.setText(
                data.get('_note', 'Not accessible individually'))

            # Update status badge to limited/default
            self.status_badge.setText("Limited")
            self.status_badge.setStyleSheet(
                BaseDetailSectionStyles.get_status_badge_style('default'))

            # Clear conditions and add a note about limited access
            self.clear_conditions_content()

            # Clear labels using the new layout-based approach
            for i in reversed(range(self.labels_layout.count())):
                item = self.labels_layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()
            no_labels = QLabel("No labels")
            no_labels.setStyleSheet(BaseDetailSectionStyles.get_secondary_text_style() + """
                font-style: italic;
                padding: 8px;
            """)
            self.labels_layout.addWidget(no_labels)

            # Clear and hide specific section
            self.clear_specific_content()

        except Exception as e:
            self.handle_error(f"Error updating UI with basic info: {str(e)}")

    def update_resource_status(self, data):

        status = data.get("status", {})
        status_value = "Unknown"
        status_text = "Status not available"
        status_type = "default"

        resource_type_lower = self.resource_type.lower()

        # Pod status with enhanced container state checking
        if resource_type_lower in ["pod", "pods"]:
            phase = status.get("phase", "Unknown")
            status_value = phase

            # Check container statuses for more detailed information
            container_statuses = status.get("containerStatuses", [])
            if container_statuses:
                for cs in container_statuses:
                    if cs.get("state"):
                        state = cs["state"]
                        if "waiting" in state:
                            waiting = state["waiting"]
                            reason = waiting.get("reason", "")
                            if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                                status_value = reason
                                break
                        elif "terminated" in state:
                            terminated = state["terminated"]
                            exit_code = terminated.get("exitCode", 0)
                            reason = terminated.get("reason", "")
                            if exit_code != 0:
                                status_value = f"Error ({reason})"
                                break
                            elif reason == "Completed":
                                status_value = f"Completed ({exit_code})"
                                break

            if status_value in ["Running"]:
                status_text = "Pod is running"
                status_type = "success"
            elif status_value in ["Pending"]:
                status_text = "Pod is pending"
                status_type = "warning"
            elif status_value in ["Failed"] or "Error" in status_value:
                status_text = "Pod has failed"
                status_type = "error"
            elif status_value in ["Succeeded"] or "Completed" in status_value:
                status_text = "Pod completed successfully"
                status_type = "success"
            elif status_value in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"]:
                status_text = f"Pod error: {status_value}"
                status_type = "error"

        # NetworkPolicy status
        elif resource_type_lower in ["networkpolicy", "networkpolicies", "netpol"]:
            # NetworkPolicies don't have a traditional status, but we can show if they're active
            spec = data.get("spec", {})
            pod_selector = spec.get("podSelector", {})

            status_value = "Active"
            if pod_selector:
                match_labels = pod_selector.get("matchLabels", {})
                if match_labels:
                    status_text = f"NetworkPolicy active for pods matching {len(match_labels)} labels"
                else:
                    status_text = "NetworkPolicy active for all pods"
            else:
                status_text = "NetworkPolicy active for all pods"
            status_type = "success"

        # CustomResourceDefinition status - FIXED
        elif resource_type_lower in ["customresourcedefinition", "customresourcedefinitions", "crd", "definitions"]:
            conditions = status.get("conditions", [])
            if conditions:
                established_condition = next(
                    (c for c in conditions if c.get("type") == "Established"), None)
                names_accepted_condition = next(
                    (c for c in conditions if c.get("type") == "NamesAccepted"), None)

                if established_condition and established_condition.get("status") == "True":
                    status_value = "Established"
                    status_text = "CustomResourceDefinition is established and ready"
                    status_type = "success"
                elif names_accepted_condition and names_accepted_condition.get("status") == "True":
                    status_value = "Names Accepted"
                    status_text = "CustomResourceDefinition names are accepted"
                    status_type = "warning"
                else:
                    status_value = "Pending"
                    status_text = "CustomResourceDefinition is being processed"
                    status_type = "warning"
            else:
                # Check accepted names from spec
                spec = data.get("spec", {})
                names = spec.get("names", {})
                if names.get("kind"):
                    status_value = "Available"
                    status_text = f"CustomResourceDefinition for {names.get('kind')} is available"
                    status_type = "success"
                else:
                    status_value = "Invalid"
                    status_text = "CustomResourceDefinition has invalid configuration"
                    status_type = "error"

        # Deployment status
        elif resource_type_lower in ["deployment", "deployments", "deploy"]:
            available_replicas = status.get("availableReplicas", 0)
            replicas = status.get("replicas", 0)

            if available_replicas == replicas and replicas > 0:
                status_value = "Available"
                status_text = f"Deployment is available ({available_replicas}/{replicas} replicas)"
                status_type = "success"
            else:
                status_value = "Progressing"
                status_text = f"Deployment is progressing ({available_replicas}/{replicas} replicas available)"
                status_type = "warning"

        # ReplicaSet status
        elif resource_type_lower in ["replicaset", "replicasets", "rs"]:
            ready_replicas = status.get("readyReplicas", 0)
            replicas = status.get("replicas", 0)

            if ready_replicas == replicas and replicas > 0:
                status_value = "Ready"
                status_text = f"ReplicaSet is ready ({ready_replicas}/{replicas} replicas)"
                status_type = "success"
            else:
                status_value = "Not Ready"
                status_text = f"ReplicaSet not ready ({ready_replicas}/{replicas} replicas ready)"
                status_type = "warning"

        # DaemonSet status
        elif resource_type_lower in ["daemonset", "daemonsets", "ds"]:
            desired = status.get("desiredNumberScheduled", 0)
            ready = status.get("numberReady", 0)

            if ready == desired and desired > 0:
                status_value = "Ready"
                status_text = f"DaemonSet is ready ({ready}/{desired} pods)"
                status_type = "success"
            else:
                status_value = "Not Ready"
                status_text = f"DaemonSet not ready ({ready}/{desired} pods ready)"
                status_type = "warning"

        # StatefulSet status
        elif resource_type_lower in ["statefulset", "statefulsets", "sts"]:
            ready_replicas = status.get("readyReplicas", 0)
            replicas = status.get("replicas", 0)

            if ready_replicas == replicas and replicas > 0:
                status_value = "Ready"
                status_text = f"StatefulSet is ready ({ready_replicas}/{replicas} replicas)"
                status_type = "success"
            else:
                status_value = "Not Ready"
                status_text = f"StatefulSet not ready ({ready_replicas}/{replicas} replicas ready)"
                status_type = "warning"

        # Job status
        elif resource_type_lower in ["job", "jobs"]:
            conditions = status.get("conditions", [])
            if conditions:
                last_condition = conditions[-1]
                condition_type = last_condition.get("type", "Unknown")
                condition_status = last_condition.get("status", "Unknown")

                if condition_type == "Complete" and condition_status == "True":
                    status_value = "Complete"
                    status_text = "Job completed successfully"
                    status_type = "success"
                elif condition_type == "Failed" and condition_status == "True":
                    status_value = "Failed"
                    status_text = "Job failed"
                    status_type = "error"
                else:
                    status_value = "Running"
                    status_text = "Job is running"
                    status_type = "warning"

        # CronJob status
        elif resource_type_lower in ["cronjob", "cronjobs", "cj"]:
            spec = data.get("spec", {})
            suspend = spec.get("suspend", False)

            if suspend:
                status_value = "Suspended"
                status_text = "CronJob is suspended"
                status_type = "warning"
            else:
                status_value = "Active"
                status_text = "CronJob is active"
                status_type = "success"

        # Service status
        elif resource_type_lower in ["service", "services", "svc"]:
            spec = data.get("spec", {})
            service_type = spec.get("type", "ClusterIP")

            status_value = service_type
            status_text = f"Service is available (type: {service_type})"
            status_type = "success"

        # ConfigMap status
        elif resource_type_lower in ["configmap", "configmaps", "cm"]:
            data_section = data.get("data", {})
            data_count = len(data_section)

            status_value = "Available"
            status_text = f"ConfigMap available with {data_count} data entries"
            status_type = "success"

        # Secret status
        elif resource_type_lower in ["secret", "secrets"]:
            data_section = data.get("data", {})
            data_count = len(data_section)

            status_value = "Available"
            status_text = f"Secret available with {data_count} data entries"
            status_type = "success"

        # PersistentVolume status
        elif resource_type_lower in ["persistentvolume", "persistentvolumes", "pv"]:
            phase = status.get("phase", "Unknown")
            status_value = phase

            if phase == "Available":
                status_text = "PersistentVolume is available"
                status_type = "success"
            elif phase == "Bound":
                status_text = "PersistentVolume is bound"
                status_type = "success"
            elif phase == "Released":
                status_text = "PersistentVolume is released"
                status_type = "warning"
            elif phase == "Failed":
                status_text = "PersistentVolume failed"
                status_type = "error"

        # PersistentVolumeClaim status
        elif resource_type_lower in ["persistentvolumeclaim", "persistentvolumeclaims", "pvc"]:
            phase = status.get("phase", "Unknown")
            status_value = phase

            if phase == "Bound":
                status_text = "PersistentVolumeClaim is bound"
                status_type = "success"
            elif phase == "Pending":
                status_text = "PersistentVolumeClaim is pending"
                status_type = "warning"
            elif phase == "Lost":
                status_text = "PersistentVolumeClaim is lost"
                status_type = "error"

        # Ingress status
        elif resource_type_lower in ["ingress", "ingresses", "ing"]:
            load_balancer = status.get("loadBalancer", {})
            ingress_ips = load_balancer.get("ingress", [])

            if ingress_ips:
                status_value = "Ready"
                status_text = f"Ingress ready with {len(ingress_ips)} endpoints"
                status_type = "success"
            else:
                status_value = "Pending"
                status_text = "Ingress is pending"
                status_type = "warning"

        # Node status
        elif resource_type_lower in ["node", "nodes"]:
            conditions = status.get("conditions", [])
            ready_condition = next(
                (c for c in conditions if c.get("type") == "Ready"), None)

            if ready_condition and ready_condition.get("status") == "True":
                status_value = "Ready"
                status_text = "Node is ready"
                status_type = "success"
            else:
                status_value = "NotReady"
                status_text = "Node is not ready"
                status_type = "error"

        # Namespace status
        elif resource_type_lower in ["namespace", "namespaces", "ns"]:
            phase = status.get("phase", "Unknown")
            status_value = phase

            if phase == "Active":
                status_text = "Namespace is active"
                status_type = "success"
            elif phase == "Terminating":
                status_text = "Namespace is terminating"
                status_type = "warning"

        # HelmRelease status
        elif resource_type_lower in ["helmrelease", "helmreleases", "hr", "chart", "charts"]:
            conditions = status.get("conditions", [])
            if conditions:
                ready_condition = next(
                    (c for c in conditions if c.get("type") == "Ready"), None)
                if ready_condition:
                    condition_status = ready_condition.get("status", "Unknown")
                    if condition_status == "True":
                        status_value = "Ready"
                        status_text = "Helm release is ready"
                        status_type = "success"
                    else:
                        status_value = "Not Ready"
                        status_text = "Helm release is not ready"
                        status_type = "warning"

        # PriorityClass status
        elif resource_type_lower in ["priorityclass", "priorityclasses", "pc"]:
            value = data.get("value", 0)
            status_value = "Available"
            status_text = f"PriorityClass available with value {value}"
            status_type = "success"

        # Lease status
        elif resource_type_lower in ["lease", "leases"]:
            spec = data.get("spec", {})
            holder = spec.get("holderIdentity", "Unknown")
            status_value = "Active"
            status_text = f"Lease held by {holder}"
            status_type = "success"

        # ValidatingWebhookConfiguration status
        elif resource_type_lower in ["validatingwebhookconfiguration", "validatingwebhookconfigurations", "vwc"]:
            webhooks = data.get("webhooks", [])
            if webhooks:
                status_value = "Active"
                status_text = f"ValidatingWebhookConfiguration active with {len(webhooks)} webhooks"
                status_type = "success"
            else:
                status_value = "No Webhooks"
                status_text = "ValidatingWebhookConfiguration has no webhooks configured"
                status_type = "warning"

        # MutatingWebhookConfiguration status
        elif resource_type_lower in ["mutatingwebhookconfiguration", "mutatingwebhookconfigurations", "mwc"]:
            webhooks = data.get("webhooks", [])
            if webhooks:
                status_value = "Active"
                status_text = f"MutatingWebhookConfiguration active with {len(webhooks)} webhooks"
                status_type = "success"
            else:
                status_value = "No Webhooks"
                status_text = "MutatingWebhookConfiguration has no webhooks configured"
                status_type = "warning"

        # ReplicationController status
        elif resource_type_lower in ["replicationcontroller", "replicationcontrollers", "rc"]:
            replicas = data.get("spec", {}).get("replicas", 0)
            ready_replicas = data.get("status", {}).get("readyReplicas", 0)

            if ready_replicas == replicas and replicas > 0:
                status_value = "Ready"
                status_text = f"ReplicationController ready ({ready_replicas}/{replicas} replicas)"
                status_type = "success"
            else:
                status_value = "Not Ready"
                status_text = f"ReplicationController not ready ({ready_replicas}/{replicas} replicas ready)"
                status_type = "warning"

        # IngressClass status
        elif resource_type_lower in ["ingressclass", "ingressclasses", "ic"]:
            spec = data.get("spec", {})
            controller = spec.get("controller", "Unknown")
            status_value = "Available"
            status_text = f"IngressClass available (controller: {controller})"
            status_type = "success"

        # Generic custom resource status
        else:
            # Try to detect status from common fields
            conditions = status.get("conditions", [])
            if conditions:
                ready_condition = next(
                    (c for c in conditions if c.get("type") == "Ready"), None)
                if ready_condition:
                    condition_status = ready_condition.get("status", "Unknown")
                    status_value = condition_status
                    status_text = f"Resource status: {condition_status}"
                    status_type = "success" if condition_status == "True" else "warning"
            else:
                phase = status.get("phase", status.get("state", "Unknown"))
                status_value = phase
                status_text = f"Resource phase: {phase}"
                status_type = "default"

        # Store status type for theme updates
        self._current_status_type = status_type

        # Apply styling
        self.status_badge.setText(status_value)
        self.status_badge.setStyleSheet(
            BaseDetailSectionStyles.get_status_badge_style(status_type))

        if hasattr(self, 'status_text_label'):
             self.status_text_label.setText(status_text)

    def update_conditions(self, data):
        
        # Clear existing content safely
        while self.conditions_container_layout.count():
            item = self.conditions_container_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                # Recursively delete layouts if needed
                self._clear_layout(item.layout())

        status = data.get("status", {})
        conditions = status.get("conditions", [])

        if not conditions:
            self.no_conditions_label = QLabel("No conditions available")
            self.no_conditions_label.setStyleSheet(BaseDetailSectionStyles.get_secondary_text_style() + """
                font-style: italic;
                padding: 8px;
            """)
            self.conditions_container_layout.addWidget(self.no_conditions_label)
            return

        # Sort conditions? Usually default order is fine.
        
        for i, condition in enumerate(conditions):
            condition_type = condition.get("type", "Unknown")
            condition_status = condition.get("status", "Unknown")
            condition_message = condition.get("message", "")
            
            # Helper to check true/false
            is_true = (str(condition_status).lower() == "true")
            
            # Row Container
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 8, 0, 8)
            row_layout.setSpacing(12)
            
            # 1. Status Dot
            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(BaseDetailSectionStyles.get_badge_dot_style(is_true))
            
            # Center vertically relative to the entire row (Title + Message)
            row_layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
            
            # 2. Text Column
            text_col = QWidget()
            text_col_layout = QVBoxLayout(text_col)
            text_col_layout.setContentsMargins(0, 0, 0, 0)
            text_col_layout.setSpacing(4)
            
            # Header Row: Title + Badge
            header_row = QHBoxLayout()
            header_row.setContentsMargins(0, 0, 0, 0)
            header_row.setSpacing(8)
            
            title_label = QLabel(condition_type)
            # Use slightly larger/darker font for condition name
            title_label.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {BaseDetailSectionStyles._get_theme().colors.TEXT_LIGHT};")
            
            badge_label = QLabel(condition_status)
            if is_true:
                badge_label.setStyleSheet(BaseDetailSectionStyles.get_condition_badge_true_style())
            else:
                badge_label.setStyleSheet(BaseDetailSectionStyles.get_condition_badge_false_style())
            
            # badge fixed size tweak if needed, or let padding handle it
            
            header_row.addWidget(title_label)
            header_row.addWidget(badge_label)
            header_row.addStretch()
            
            text_col_layout.addLayout(header_row)
            
            # Message (Optional)
            if condition_message:
                msg_label = QLabel(condition_message)
                msg_label.setWordWrap(True)
                msg_label.setStyleSheet(BaseDetailSectionStyles.get_condition_message_style())
                msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                text_col_layout.addWidget(msg_label)
            
            row_layout.addWidget(text_col, 1) # Give text column all space
            
            self.conditions_container_layout.addWidget(row_widget)
            
            # Add Separator if not last item
            if i < len(conditions) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setFrameShadow(QFrame.Shadow.Plain)
                sep.setStyleSheet(f"background-color: {OverviewSectionStyles._get_theme().colors.BORDER_COLOR}; max-height: 1px; border: none;")
                self.conditions_container_layout.addWidget(sep)
            
    def _clear_layout(self, layout):
        if layout is not None:
             while layout.count():
                 item = layout.takeAt(0)
                 widget = item.widget()
                 if widget is not None:
                     widget.deleteLater()
                 else:
                     self._clear_layout(item.layout())

    def update_labels(self, data):
        """Update labels section with individual label cards"""
        
        # Clear existing labels
        for i in reversed(range(self.labels_layout.count())):
            item = self.labels_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        metadata = data.get("metadata", {})
        labels = metadata.get("labels", {})
        
        if not labels:
            # Show "No labels" placeholder
            no_labels = QLabel("No labels")
            no_labels.setStyleSheet(BaseDetailSectionStyles.get_secondary_text_style() + """
                font-style: italic;
                padding: 8px;
            """)
            self.labels_layout.addWidget(no_labels)
            return
        
        # Create individual label cards
        for key, value in labels.items():
            label_card = self._create_label_card(key, value)
            self.labels_layout.addWidget(label_card)
    
    def _create_label_card(self, key, value):
        """Create a single label card - uses info_card styling"""
        
        # Use QFrame with info_card styling (same as Created/Version cards)
        # BUT: For individual labels inside the main card, we might want a simpler style
        # or just a border. The user said "add those card for every labels same as shown in image"
        # The image shows simple rounded boxes.
        # Since we are putting them INSIDE a 3D card now, we probably don't want double shadows.
        card = QFrame()
        card.setObjectName("label_item") 
        # Simpler style for inner items: rounded with border, no shadow
        card.setStyleSheet(f"""
            QFrame#label_item {{
                background-color: {OverviewSectionStyles._get_theme().colors.CARD_BG};
                border: 1px solid {OverviewSectionStyles._get_theme().colors.BORDER_COLOR};
                border-radius: 6px;
            }}
        """)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(10)
        
        # Label text: key=value (no icon on individual cards)
        # Format value for wrapping: inject zero-width space after common separators
        display_text = f"{key}={value}"
        for char in ['-', '.', '/', ',', ':', '"', '{', '}', '[', ']', '(', ')', '_', '=', ' ']:
            display_text = display_text.replace(char, char + '\u200b')
            
        label_text = QLabel(display_text)
        label_text.setStyleSheet(f"""
            color: {OverviewSectionStyles._get_theme().colors.TEXT_LIGHT};
            font-size: 13px;
            font-weight: 500;
            font-family: 'Consolas', 'Courier New', monospace;
        """)
        label_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label_text.setWordWrap(True)
        
        # Add to layout
        card_layout.addWidget(label_text, 1)
        
        return card

    def add_resource_specific_fields(self, data):

        # Clear existing content
        for i in reversed(range(self.specific_layout.count())):
            item = self.specific_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        resource_type_lower = self.resource_type.lower()

        # Set dynamic header text based on resource type
        header_map = {
            "pod": "POD DETAILS", "pods": "POD DETAILS",
            "service": "SERVICE DETAILS", "services": "SERVICE DETAILS", "svc": "SERVICE DETAILS",
            "deployment": "DEPLOYMENT DETAILS", "deployments": "DEPLOYMENT DETAILS", "deploy": "DEPLOYMENT DETAILS",
            "configmap": "CONFIGMAP DETAILS", "configmaps": "CONFIGMAP DETAILS", "cm": "CONFIGMAP DETAILS",
            "secret": "SECRET DETAILS", "secrets": "SECRET DETAILS",
            "ingress": "INGRESS DETAILS", "ingresses": "INGRESS DETAILS", "ing": "INGRESS DETAILS",
            "networkpolicy": "NETWORK POLICY DETAILS", "networkpolicies": "NETWORK POLICY DETAILS", "netpol": "NETWORK POLICY DETAILS",
            "customresourcedefinition": "CRD DETAILS", "customresourcedefinitions": "CRD DETAILS", "crd": "CRD DETAILS",
            "persistentvolume": "PV DETAILS", "persistentvolumes": "PV DETAILS", "pv": "PV DETAILS",
            "persistentvolumeclaim": "PVC DETAILS", "persistentvolumeclaims": "PVC DETAILS", "pvc": "PVC DETAILS",
            "replicaset": "REPLICASET DETAILS", "replicasets": "REPLICASET DETAILS", "rs": "REPLICASET DETAILS",
            "daemonset": "DAEMONSET DETAILS", "daemonsets": "DAEMONSET DETAILS", "ds": "DAEMONSET DETAILS",
            "statefulset": "STATEFULSET DETAILS", "statefulsets": "STATEFULSET DETAILS", "sts": "STATEFULSET DETAILS",
            "job": "JOB DETAILS", "jobs": "JOB DETAILS",
            "cronjob": "CRONJOB DETAILS", "cronjobs": "CRONJOB DETAILS", "cj": "CRONJOB DETAILS",
            "node": "NODE DETAILS", "nodes": "NODE DETAILS",
            "namespace": "NAMESPACE DETAILS", "namespaces": "NAMESPACE DETAILS", "ns": "NAMESPACE DETAILS",
            "helmrelease": "HELM RELEASE DETAILS", "helmreleases": "HELM RELEASE DETAILS", "hr": "HELM RELEASE DETAILS",
            "chart": "CHART DETAILS", "charts": "CHART DETAILS",
            "priorityclass": "PRIORITY CLASS DETAILS", "priorityclasses": "PRIORITY CLASS DETAILS", "pc": "PRIORITY CLASS DETAILS",
            "lease": "LEASE DETAILS", "leases": "LEASE DETAILS",
            "ingressclass": "INGRESS CLASS DETAILS", "ingressclasses": "INGRESS CLASS DETAILS", "ic": "INGRESS CLASS DETAILS",
        }
        self.specific_header.setText(header_map.get(resource_type_lower, f"{self.resource_type.upper()} DETAILS"))

        # Add fields based on resource type
        if resource_type_lower in ["pod", "pods"]:
            self._add_pod_specific_fields(data)
        elif resource_type_lower in ["service", "services", "svc"]:
            self._add_service_specific_fields(data)
        elif resource_type_lower in ["deployment", "deployments", "deploy"]:
            self._add_deployment_specific_fields(data)
        elif resource_type_lower in ["configmap", "configmaps", "cm"]:
            self._add_configmap_specific_fields(data)
        elif resource_type_lower in ["secret", "secrets"]:
            self._add_secret_specific_fields(data)
        elif resource_type_lower in ["ingress", "ingresses", "ing"]:
            self._add_ingress_specific_fields(data)
        # ADD THESE TWO NEW LINES HERE:
        elif resource_type_lower in ["networkpolicy", "networkpolicies", "netpol"]:
            self._add_networkpolicy_specific_fields(data)
        elif resource_type_lower in ["customresourcedefinition", "customresourcedefinitions", "crd"]:
            self._add_customresourcedefinition_specific_fields(data)
        # END OF NEW LINES
        elif resource_type_lower in ["persistentvolume", "persistentvolumes", "pv"]:
            self._add_persistentvolume_specific_fields(data)
        elif resource_type_lower in ["persistentvolumeclaim", "persistentvolumeclaims", "pvc"]:
            self._add_persistentvolumeclaim_specific_fields(data)
        elif resource_type_lower in ["replicaset", "replicasets", "rs"]:
            self._add_replicaset_specific_fields(data)
        elif resource_type_lower in ["daemonset", "daemonsets", "ds"]:
            self._add_daemonset_specific_fields(data)
        elif resource_type_lower in ["statefulset", "statefulsets", "sts"]:
            self._add_statefulset_specific_fields(data)
        elif resource_type_lower in ["job", "jobs"]:
            self._add_job_specific_fields(data)
        elif resource_type_lower in ["cronjob", "cronjobs", "cj"]:
            self._add_cronjob_specific_fields(data)
        elif resource_type_lower in ["node", "nodes"]:
            self._add_node_specific_fields(data)
        elif resource_type_lower in ["namespace", "namespaces", "ns"]:
            self._add_namespace_specific_fields(data)
        elif resource_type_lower in ["helmrelease", "helmreleases", "hr"]:
            self._add_helmrelease_specific_fields(data)
        elif resource_type_lower in ["chart", "charts"]:
            self._add_helmrelease_specific_fields(
                data)  # Use same method for charts
        elif resource_type_lower in ["priorityclass", "priorityclasses", "pc"]:
            self._add_priorityclass_specific_fields(data)
        elif resource_type_lower in ["lease", "leases"]:
            self._add_lease_specific_fields(data)
        elif resource_type_lower in ["validatingwebhookconfiguration", "validatingwebhookconfigurations", "vwc"]:
            self._add_validating_webhook_specific_fields(data)
        elif resource_type_lower in ["mutatingwebhookconfiguration", "mutatingwebhookconfigurations", "mwc"]:
            self._add_mutating_webhook_specific_fields(data)
        elif resource_type_lower in ["replicationcontroller", "replicationcontrollers", "rc"]:
            self._add_replicationcontroller_specific_fields(data)
        elif resource_type_lower in ["ingressclass", "ingressclasses", "ic"]:
            self._add_ingressclass_specific_fields(data)
        else:
            # Generic custom resource handling
            self._add_generic_custom_resource_fields(data)

        if self.specific_layout.count() > 0:
            self.specific_section.show()
        else:
            self.specific_section.hide()

    def _add_networkpolicy_specific_fields(self, data):

        spec = data.get("spec", {})

        # Pod selector
        pod_selector = spec.get("podSelector", {})
        if pod_selector:
            match_labels = pod_selector.get("matchLabels", {})
            if match_labels:
                labels_text = ", ".join(
                    [f"{k}={v}" for k, v in match_labels.items()])
                self._add_detail_field("Pod Selector", labels_text)
            else:
                self._add_detail_field("Pod Selector", "All pods")
        else:
            self._add_detail_field("Pod Selector", "All pods")

        # Policy types
        policy_types = spec.get("policyTypes", [])
        if policy_types:
            self._add_detail_field("Policy Types", ", ".join(policy_types))

        # Ingress rules
        self._add_detail_field("Ingress Rules", len(spec.get("ingress", [])))

        # Egress rules
        self._add_detail_field("Egress Rules", len(spec.get("egress", [])))

    def _add_customresourcedefinition_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        # Group and versions
        self._add_detail_field("Group", spec.get("group", "Unknown"))

        versions = spec.get("versions", [])
        if versions:
            version_names = [v.get("name", "unknown") for v in versions]
            self._add_detail_field("Versions", ", ".join(version_names))

        # Names
        names = spec.get("names", {})
        if names:
            self._add_detail_field("Kind", names.get("kind", "Unknown"))
            self._add_detail_field("Plural", names.get("plural", "Unknown"))
            self._add_detail_field("Singular", names.get("singular", "Unknown"))

        # Scope
        self._add_detail_field("Scope", spec.get("scope", "Unknown"))

        # Status
        conditions = status.get("conditions", [])
        if conditions:
            established_condition = next(
                (c for c in conditions if c.get("type") == "Established"), None)
            if established_condition:
                self._add_detail_field("Established", established_condition.get("status", "Unknown"))

    def _add_pod_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        containers = spec.get("containers", [])
        self._add_detail_field("Containers", len(containers))

        node_name = spec.get("nodeName", "")
        if node_name:
            self._add_detail_field("Node", node_name)

        pod_ip = status.get("podIP", "")
        if pod_ip:
            self._add_detail_field("Pod IP", pod_ip)

    def _add_service_specific_fields(self, data):

        spec = data.get("spec", {})

        self._add_detail_field("Type", spec.get("type", "ClusterIP"))

        cluster_ip = spec.get("clusterIP", "")
        if cluster_ip:
            self._add_detail_field("Cluster IP", cluster_ip)

    def _add_deployment_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        self._add_detail_field("Desired Replicas", spec.get("replicas", 0))
        self._add_detail_field("Ready Replicas", status.get("readyReplicas", 0))

        # Add rollback section
        self._add_deployment_rollback_section(data)

    def _add_deployment_rollback_section(self, data):

        metadata = data.get("metadata", {})
        deployment_name = metadata.get("name", "")
        namespace = metadata.get("namespace", "default")

        if not deployment_name:
            return

        # Create header with icon
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Add History Icon
        self.rollback_icon_label = QLabel()
        theme = BaseDetailSectionStyles._get_theme()
        self.rollback_icon_label.setPixmap(self._render_svg_from_file("history.svg", BaseDetailSectionStyles.get_section_header_color()))
        header_layout.addWidget(self.rollback_icon_label)

        rollback_header = QLabel("ROLLBACK HISTORY")
        rollback_header.setStyleSheet(
            BaseDetailSectionStyles.get_section_header_style())
        rollback_header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header_layout.addWidget(rollback_header)

        # Add spacing before header for better separation
        self.specific_layout.addSpacing(15)
        self.specific_layout.addWidget(header_container)

        # Create loading label for history
        self.history_loading_label = QLabel("Loading rollback history...")
        self.history_loading_label.setStyleSheet(
            BaseDetailSectionStyles.get_field_value_style())
        self.specific_layout.addWidget(self.history_loading_label)

        # Create container for history table
        self.history_container = QWidget()
        history_layout = QVBoxLayout(self.history_container)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(8)

        # Create table for rollback history
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["Revision", "Age", "Status", "Change Cause", "Action"])

        # Style the table
        self.history_table.setStyleSheet(
            OverviewSectionStyles.get_history_table_style())

        # Configure table properties
        self.history_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.verticalHeader().setVisible(False)

        # Set consistent row height to accommodate widgets
        self.history_table.verticalHeader().setDefaultSectionSize(45)

        # Ensure the table shows widgets properly
        self.history_table.setShowGrid(True)
        self.history_table.setWordWrap(False)

        # Set column widths and resize modes
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed)     # Revision
        header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)  # Age (dynamic)
        header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed)     # Status
        # Change Cause (stretches)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            4, QHeaderView.ResizeMode.Fixed)     # Action

        # Set fixed column widths
        self.history_table.setColumnWidth(0, 80)   # Revision
        # Status (wider for better visibility)
        self.history_table.setColumnWidth(2, 120)
        self.history_table.setColumnWidth(4, 120)  # Action (wider for button)

        # Set reasonable height for table (dynamic based on content)
        self.history_table.setMinimumHeight(100)
        # Allow more space for multiple revisions
        self.history_table.setMaximumHeight(300)

        history_layout.addWidget(self.history_table)
        self.history_container.hide()  # Hide initially
        self.specific_layout.addWidget(self.history_container)

        # Store deployment info for rollback operations
        self.current_deployment_name = deployment_name
        self.current_deployment_namespace = namespace

        # Connect to kubernetes client signals with safe handling
        try:
            # Disconnect any existing connections first
            try:
                self.kubernetes_client.deployment_history_loaded.disconnect()
            except TypeError:
                pass  # No connections to disconnect

            try:
                self.kubernetes_client.deployment_rollback_completed.disconnect()
            except TypeError:
                pass  # No connections to disconnect

            # Connect new handlers
            self.kubernetes_client.deployment_history_loaded.connect(
                self._handle_deployment_history_loaded)
            self.kubernetes_client.deployment_rollback_completed.connect(
                self._handle_deployment_rollback_completed)

        except Exception as e:
            logging.error(f"Error connecting rollback signals: {str(e)}")

        # Fetch rollback history
        logging.info(
            f"Requesting rollout history for deployment {deployment_name} in namespace {namespace}")
        self.kubernetes_client.get_deployment_rollout_history_async(
            deployment_name, namespace)

    def _handle_deployment_history_loaded(self, history_data):

        try:
            # Safely disconnect the signal to avoid multiple calls
            try:
                self.kubernetes_client.deployment_history_loaded.disconnect(
                    self._handle_deployment_history_loaded)
            except (TypeError, RuntimeError):
                pass  # Signal already disconnected or object deleted

            # Guard against a late signal after the panel was cleared:
            # clear_content() sets these child widgets to None, so dereferencing
            # them would raise AttributeError (not caught by the RuntimeError
            # guard below). Validate each child before touching it.
            if not (is_valid(self.history_loading_label)
                    and is_valid(self.history_container)
                    and is_valid(self.history_table)):
                return

            # Hide loading label and show container
            try:
                self.history_loading_label.hide()
                self.history_container.show()
            except RuntimeError:
                # Widget deleted, panel was closed - skip UI update
                return

            if not history_data:
                no_history_label = QLabel("No rollback history available")
                no_history_label.setStyleSheet(
                    BaseDetailSectionStyles.get_secondary_text_style())
                self.specific_layout.addWidget(no_history_label)
                return

            # Populate the table
            self.history_table.setRowCount(len(history_data))

            logging.info(
                f"Processing {len(history_data)} rollback history items for display")

            for row, revision_data in enumerate(history_data):
                revision = revision_data.get("revision", 1)
                creation_time = revision_data.get("creation_time", "")
                age = self._calculate_age_from_timestamp(creation_time)
                change_cause = revision_data.get(
                    "change_cause", "No change cause recorded")
                current = revision_data.get("current", False)
                status = revision_data.get("status", "Unknown")
                images = revision_data.get("images", [])

                logging.debug(
                    f"Row {row}: Revision {revision}, Current: {current}, Status: {status}")

                # Add revision cell - using setCellWidget for text selection
                revision_text = str(revision)
                revision_label = QLabel(revision_text)
                revision_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                revision_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                
                # Combine base style with specific overrides
                base_style = BaseDetailSectionStyles.get_field_value_style()
                revision_style = f"{base_style} QLabel {{ padding: 5px;"
                if current:
                    revision_style += f" font-weight: bold; color: {OverviewSectionStyles.get_status_active_color()};"
                revision_style += " }"
                revision_label.setStyleSheet(revision_style)
                self.history_table.setCellWidget(row, 0, revision_label)

                revision_item = QTableWidgetItem(revision_text)
                revision_item.setFlags(
                    revision_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row, 0, revision_item)

                # Add age cell
                age_label = QLabel(age)
                age_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                age_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                age_label.setStyleSheet(BaseDetailSectionStyles.get_field_value_style() + "QLabel { padding: 5px; }")
                self.history_table.setCellWidget(row, 1, age_label)

                age_item = QTableWidgetItem(age)
                age_item.setFlags(age_item.flags() & ~
                                  Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row, 1, age_item)

                # Add status cell
                status_label = QLabel(status)
                status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                
                base_style = BaseDetailSectionStyles.get_field_value_style()
                status_style = f"{base_style} QLabel {{ padding: 5px;"
                if current:
                     status_style += f" font-weight: bold; color: {OverviewSectionStyles.get_status_active_color()};"
                elif status == "Available":
                     status_style += " color: #4CAF50;"
                elif status == "Inactive":
                     status_style += f" color: {OverviewSectionStyles.get_text_secondary_color()};"
                status_style += " }"
                
                status_label.setStyleSheet(status_style)
                self.history_table.setCellWidget(row, 2, status_label)

                status_item = QTableWidgetItem(status)
                status_item.setFlags(status_item.flags() &
                                     ~Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row, 2, status_item)

                # Add change cause cell with enhanced tooltip
                truncated_cause = change_cause[:50] + \
                    "..." if len(change_cause) > 50 else change_cause
                
                cause_label = QLabel(truncated_cause)
                cause_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                cause_label.setStyleSheet(BaseDetailSectionStyles.get_field_value_style() + "QLabel { padding: 5px; }")
                
                # Create detailed tooltip
                tooltip_text = f"Change Cause: {change_cause}"
                if images:
                    # Show first 3 images
                    tooltip_text += f"\nImages: {', '.join(images[:3])}"
                    if len(images) > 3:
                        tooltip_text += f"\n... and {len(images) - 3} more"
                
                cause_label.setToolTip(tooltip_text)
                self.history_table.setCellWidget(row, 3, cause_label)

                cause_item = QTableWidgetItem(truncated_cause)
                cause_item.setFlags(cause_item.flags() & ~
                                    Qt.ItemFlag.ItemIsEditable)
                cause_item.setToolTip(tooltip_text)
                self.history_table.setItem(row, 3, cause_item)

                # Add action cell (rollback button or current label)
                logging.debug(
                    f"Setting action widget for row {row}, current={current}, revision={revision}")

                if not current:  # Don't show rollback button for current revision
                    rollback_btn = QPushButton("Rollback")
                    rollback_btn.setStyleSheet(
                        OverviewSectionStyles.get_rollback_button_style())
                    rollback_btn.clicked.connect(
                        lambda checked, rev=revision: self._rollback_to_revision(rev))
                    self.history_table.setCellWidget(row, 4, rollback_btn)
                    logging.debug(f"Added rollback button for row {row}")
                else:
                    # Show "Current" label for current revision
                    current_label = QLabel("Current")
                    current_label.setStyleSheet(
                        OverviewSectionStyles.get_current_label_style())
                    current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.history_table.setCellWidget(row, 4, current_label)
                    logging.debug(f"Added current label for row {row}")

                # Verify the widget was set
                test_widget = self.history_table.cellWidget(row, 4)
                if test_widget:
                    logging.debug(
                        f"Successfully set action widget for row {row}: {type(test_widget).__name__}")
                else:
                    logging.error(f"Failed to set action widget for row {row}")
                    # If widget setting failed, at least keep the text item
                    if not current:
                        fallback_item = QTableWidgetItem("Rollback (Fallback)")
                        self.history_table.setItem(row, 4, fallback_item)

            # Ensure Age column adjusts to content (already set to ResizeToContents)
            # Other columns maintain their fixed / stretch settings from table setup

            # Ensure rows fit content properly
            # self.history_table.resizeRowsToContents()

            # Adjust table height based on content
            self._adjust_table_height(len(history_data))

            logging.info(
                f"Populated rollback history table with {len(history_data)} revisions")

        except Exception as e:
            logging.error(f"Error handling deployment history: {str(e)}")
            error_label = QLabel("Error loading rollback history")
            error_label.setStyleSheet(
                OverviewSectionStyles.get_error_label_style())
            self.specific_layout.addWidget(error_label)

    def _calculate_age_from_timestamp(self, timestamp_str):

        if not timestamp_str:
            return "Unknown"

        try:
            from datetime import datetime
            from dateutil import parser

            creation_time = parser.parse(timestamp_str)
            now = datetime.now(creation_time.tzinfo)
            delta = now - creation_time

            days = delta.days
            seconds = delta.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60

            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"

        except Exception:
            logging.exception("Failed to parse timestamp: %s", timestamp_str)
            return "Unknown"

    def _adjust_table_height(self, row_count):

        try:
            # Calculate height: header + rows + padding
            header_height = 35  # Header row height
            row_height = 40     # Each row height (matches defaultSectionSize)
            padding = 10        # Extra padding

            # Calculate optimal height
            calculated_height = header_height + \
                (row_count * row_height) + padding

            # Ensure it's within our min / max bounds
            min_height = 120    # Minimum to show at least header + one row
            max_height = 350    # Allow more space for widget containers
            final_height = max(min_height, min(calculated_height, max_height))

            self.history_table.setFixedHeight(final_height)
            logging.debug(
                f"Adjusted table height to {final_height}px for {row_count} rows")
        except Exception as e:
            logging.error(f"Error adjusting table height: {str(e)}")

    def _rollback_to_revision(self, revision):

        from PyQt6.QtWidgets import QMessageBox

        # Show confirmation dialog
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Confirm Rollback")
        msg_box.setText(
            f"Are you sure you want to rollback deployment '{self.current_deployment_name}' to revision {revision}?")
        msg_box.setInformativeText(
            "This action will update the deployment and trigger a new rollout.")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Question)

        # Apply theme styling
        msg_box.setStyleSheet(OverviewSectionStyles.get_message_box_style())

        result = msg_box.exec()

        if result == QMessageBox.StandardButton.Yes:
            logging.info(
                f"User confirmed rollback of {self.current_deployment_name} to revision {revision}")

            # Show progress indicator
            for i in range(self.history_table.rowCount()):
                widget = self.history_table.cellWidget(
                    i, 4)  # Action column widget
                if isinstance(widget, QPushButton):
                    widget.setText("Rolling back...")
                    widget.setEnabled(False)

            # Trigger rollback
            self.kubernetes_client.rollback_deployment_async(
                self.current_deployment_name,
                revision,
                self.current_deployment_namespace
            )

    def _handle_deployment_rollback_completed(self, result):

        try:
            # Safely disconnect the signal
            try:
                self.kubernetes_client.deployment_rollback_completed.disconnect(
                    self._handle_deployment_rollback_completed)
            except (TypeError, RuntimeError):
                pass  # Signal already disconnected or object deleted

            # Re-enable buttons - validate the table first since clear_content()
            # may have set it to None (AttributeError isn't caught below).
            if is_valid(self.history_table):
                try:
                    for i in range(self.history_table.rowCount()):
                        widget = self.history_table.cellWidget(
                            i, 4)  # Action column widget
                        if isinstance(widget, QPushButton):
                            widget.setText("Rollback")
                            widget.setEnabled(True)
                except RuntimeError:
                    # Widget deleted, panel was closed - skip UI update
                    pass

            # Show result message
            from PyQt6.QtWidgets import QMessageBox

            msg_box = QMessageBox()
            msg_box.setWindowTitle("Rollback Result")

            if result.get("success", False):
                msg_box.setText("Rollback completed successfully!")
                msg_box.setInformativeText(result.get("message", ""))
                msg_box.setIcon(QMessageBox.Icon.Information)

                # Refresh the deployment details after successful rollback
                QTimer.singleShot(
                    2000, lambda: self._refresh_deployment_details())

            else:
                msg_box.setText("Rollback failed!")
                msg_box.setInformativeText(
                    result.get("message", "Unknown error"))
                msg_box.setIcon(QMessageBox.Icon.Critical)

            # Apply theme styling
            msg_box.setStyleSheet(
                OverviewSectionStyles.get_message_box_style())

            msg_box.exec()

            logging.info(f"Rollback completed with result: {result}")

        except Exception as e:
            logging.error(f"Error handling rollback completion: {str(e)}")

    def _refresh_deployment_details(self):

        try:
            # Trigger a refresh of the current resource
            if hasattr(self, 'resource_name') and hasattr(self, 'resource_namespace'):
                self.load_data(self.resource_type,
                               self.resource_name, self.resource_namespace)
        except Exception as e:
            logging.error(f"Error refreshing deployment details: {str(e)}")

    def _add_configmap_specific_fields(self, data):

        data_section = data.get("data", {})
        self._add_detail_field("Data entries", len(data_section))

        if data_section:
            data_keys = list(data_section.keys())[:5]
            keys_text = ", ".join(data_keys)
            if len(data_section) > 5:
                keys_text += f"... and {len(data_section) - 5} more"
            self._add_detail_field("Keys", keys_text)

    def _add_secret_specific_fields(self, data):

        self._add_detail_field("Type", data.get("type", "Opaque"))

        data_section = data.get("data", {})
        self._add_detail_field("Data entries", len(data_section))

    def _add_ingress_specific_fields(self, data):

        spec = data.get("spec", {})

        self._add_detail_field("Ingress Class", spec.get("ingressClassName", "default"))

        rules = spec.get("rules", [])
        self._add_detail_field("Rules", len(rules))

        if rules:
            hosts = [rule.get("host", "no-host") for rule in rules[:3]]
            hosts_text = ", ".join(hosts)
            if len(rules) > 3:
                hosts_text += f"... and {len(rules) - 3} more"
            self._add_detail_field("Hosts", hosts_text)

    def _add_persistentvolume_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        self._add_detail_field("Capacity", spec.get("capacity", {}).get("storage", "Unknown"))
        self._add_detail_field("Access Modes", ", ".join(spec.get("accessModes", [])))
        self._add_detail_field("Reclaim Policy", spec.get("persistentVolumeReclaimPolicy", "Unknown"))
        self._add_detail_field("Phase", status.get("phase", "Unknown"))

    def _add_persistentvolumeclaim_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        self._add_detail_field("Access Modes", ", ".join(spec.get("accessModes", [])))
        self._add_detail_field("Requested Storage", spec.get("resources", {}).get("requests", {}).get("storage", "Unknown"))
        self._add_detail_field("Storage Class", spec.get("storageClassName", "default"))
        self._add_detail_field("Phase", status.get("phase", "Unknown"))

    def _add_replicaset_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        self._add_detail_field("Desired Replicas", spec.get("replicas", 0))
        self._add_detail_field("Ready Replicas", status.get("readyReplicas", 0))
        self._add_detail_field("Available Replicas", status.get("availableReplicas", 0))

    def _add_daemonset_specific_fields(self, data):

        status = data.get("status", {})

        self._add_detail_field("Desired", status.get("desiredNumberScheduled", 0))
        self._add_detail_field("Current", status.get("currentNumberScheduled", 0))
        self._add_detail_field("Ready", status.get("numberReady", 0))

    def _add_statefulset_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        self._add_detail_field("Desired Replicas", spec.get("replicas", 0))
        self._add_detail_field("Ready Replicas", status.get("readyReplicas", 0))
        self._add_detail_field("Service Name", spec.get("serviceName", "Unknown"))

    def _add_job_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        self._add_detail_field("Parallelism", spec.get("parallelism", 1))
        self._add_detail_field("Completions", spec.get("completions", 1))
        self._add_detail_field("Succeeded", status.get("succeeded", 0))

    def _add_cronjob_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        self._add_detail_field("Schedule", spec.get("schedule", "Unknown"))
        self._add_detail_field("Suspended", "Yes" if spec.get("suspend", False) else "No")
        
        last_schedule = status.get("lastScheduleTime", "Never")
        if last_schedule != "Never":
            try:
                last_schedule = TimezoneManager.get_instance().format_time(last_schedule)
            except Exception:
                pass
                
        self._add_detail_field("Last Schedule", last_schedule)

    def _add_detail_field(self, label, value):
        """Helper to add a horizontal label-value row matching SYSTEM INFO style"""
        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(12)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet(BaseDetailSectionStyles.get_field_label_style())
        label_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label_widget.setMinimumWidth(140)
        label_widget.setMaximumWidth(140)
        
        value_widget = QLabel(str(value))
        value_widget.setStyleSheet(BaseDetailSectionStyles.get_field_value_style())
        value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value_widget.setWordWrap(True)
        
        field_layout.addWidget(label_widget)
        field_layout.addWidget(value_widget, 1)
        
        self.specific_layout.addWidget(field_container)

    def _add_node_specific_fields(self, data):

        status = data.get("status", {})

        # Node info
        node_info = status.get("nodeInfo", {})
        self._add_detail_field("OS Image", node_info.get("osImage", "Unknown"))
        self._add_detail_field("Kernel Version", node_info.get("kernelVersion", "Unknown"))
        self._add_detail_field("Container Runtime", node_info.get("containerRuntimeVersion", "Unknown"))

        # Add pods section for this node
        self._add_node_pods_section(data)

    def _add_namespace_specific_fields(self, data):

        status = data.get("status", {})
        self._add_detail_field("Phase", status.get("phase", "Unknown"))

    def _add_helmrelease_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        chart = spec.get("chart", {})
        self._add_detail_field("Chart", chart.get("spec", {}).get("chart", "Unknown"))
        self._add_detail_field("Version", chart.get("spec", {}).get("version", "Unknown"))

        release_status = status.get("conditions", [])
        if release_status:
            last_condition = release_status[-1]
            self._add_detail_field("Status", f"{last_condition.get('type', 'Unknown')} = {last_condition.get('status', 'Unknown')}")

    def _add_generic_custom_resource_fields(self, data):

        spec = data.get("spec", {})

        self._add_detail_field("API Version", data.get("apiVersion", "Unknown"))
        self._add_detail_field("Kind", data.get("kind", "Unknown"))

        # Show some basic spec fields if available
        if spec:
            spec_keys = list(spec.keys())[:3]
            spec_text = ", ".join(spec_keys)
            if len(spec) > 3:
                spec_text += f"... and {len(spec) - 3} more"
            self._add_detail_field("Spec fields", spec_text)

    def _add_priorityclass_specific_fields(self, data):

        self._add_detail_field("Priority Value", data.get("value", 0))
        self._add_detail_field("Global Default", "Yes" if data.get("globalDefault", False) else "No")

        description = data.get("description", "")
        if description:
            self._add_detail_field("Description", description)

    def _add_lease_specific_fields(self, data):

        spec = data.get("spec", {})

        self._add_detail_field("Holder Identity", spec.get("holderIdentity", "Unknown"))
        self._add_detail_field("Lease Duration", f"{spec.get('leaseDurationSeconds', 'Unknown')}s")

        acquire_time = spec.get("acquireTime", "")
        if acquire_time:
            self._add_detail_field("Acquire Time", acquire_time)

    def clear_content(self):

        # Defensive: Clear cached data
        # Defensive: Clear cached data
        self.current_data = None
        
        # KEY FIX: Disconnect any pending pod signals to prevent ghost windows
        self._disconnect_pods_signals()
        
        # Clear widget references
        self._pod_widgets = []

        if hasattr(self, 'resource_name_label'):
             self.resource_name_label.setText("Resource Name")
        if hasattr(self, 'resource_type_label'):
             self.resource_type_label.setText("Type")
        
        # Reset cards if they exist
        if hasattr(self, 'created_card'):
             self.created_card.value_label.setText("Unknown")
        if hasattr(self, 'secondary_card'):
             self.secondary_card.title_label.setText("INFO")
             self.secondary_card.value_label.setText("Unknown")
             
        if hasattr(self, 'status_badge'):
             self.status_badge.setText("Unknown")
             self.status_badge.setStyleSheet(BaseDetailSectionStyles.get_status_badge_style('default'))
        
        if hasattr(self, 'status_text_label'):
             self.status_text_label.setText("Status not available")
        
        # Clear labels layout
        # Clear labels layout using helper
        self._clear_layout(self.labels_layout)
        
        # Add "No labels" placeholder
        no_labels = QLabel("No labels")
        no_labels.setStyleSheet(BaseDetailSectionStyles.get_secondary_text_style() + """
            font-style: italic;
            padding: 8px;
        """)
        self.labels_layout.addWidget(no_labels)

        # Safe conditions clearing
        self._clear_layout(self.conditions_container_layout)

        # Safe specific section clearing
        self._clear_layout(self.specific_layout)
        
        # Reset dynamic widget references to prevent RuntimeError during theme changes
        self.rollback_icon_label = None
        self.history_loading_label = None
        self.history_table = None
        self.history_container = None

        self.specific_section.hide()

    def clear_status_content(self):

        self.status_badge.setText("Unknown")
        if hasattr(self, 'status_text_label'):
            self.status_text_label.setText("Status not available")

    def clear_conditions_content(self):

        try:
            # Use helper for safe clearing
            self._clear_layout(self.conditions_container_layout)
        except Exception as e:
            logging.error(f"Error clearing conditions content: {e}")

    def clear_labels_content(self):

        self._clear_layout(self.labels_layout)
        no_labels = QLabel("No labels")
        no_labels.setStyleSheet(BaseDetailSectionStyles.get_secondary_text_style() + """
            font-style: italic;
            padding: 8px;
        """)
        self.labels_layout.addWidget(no_labels)

    def clear_specific_content(self):

        self._clear_layout(self.specific_layout)
        self.specific_section.hide()

    def _add_validating_webhook_specific_fields(self, data):

        webhooks = data.get("webhooks", [])
        self._add_detail_field("Webhooks", len(webhooks))

        if webhooks:
            first_webhook = webhooks[0]
            self._add_detail_field("First Webhook Name", first_webhook.get("name", "Unknown"))

    def _add_mutating_webhook_specific_fields(self, data):

        webhooks = data.get("webhooks", [])
        self._add_detail_field("Webhooks", len(webhooks))

    def _add_replicationcontroller_specific_fields(self, data):

        spec = data.get("spec", {})
        status = data.get("status", {})

        self._add_detail_field("Desired Replicas", spec.get("replicas", 0))
        self._add_detail_field("Ready Replicas", status.get("readyReplicas", 0))

    def _add_ingressclass_specific_fields(self, data):

        spec = data.get("spec", {})

        self._add_detail_field("Controller", spec.get("controller", "Unknown"))

        parameters = spec.get("parameters", {})
        if parameters:
            self._add_detail_field("Parameters", parameters)

    def _add_node_pods_section(self, data):

        node_name = data.get("metadata", {}).get("name", "")
        if not node_name:
            return

        # Create pods section header container
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        # Add spacing above the header
        self.specific_layout.addSpacing(20)
        
        # Icon
        try:
            # Calculate path to icon: ../../Icons/pods-icon.svg
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            icon_path = os.path.join(base_path, "Icons", "pods-icon.svg")
            
            if os.path.exists(icon_path):
                icon_label = QLabel()
                icon_label.setFixedSize(20, 20)
                
                # Use theme color matching text (TEXT_SECONDARY)
                theme = OverviewSectionStyles._get_theme()
                color = QColor(theme.colors.TEXT_SECONDARY)
                
                # Load and paint SVG
                renderer = QSvgRenderer(icon_path)
                pixmap = QPixmap(20, 20)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                
                # Paint the icon with the text color (SourceIn composition)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(pixmap.rect(), color)
                painter.end()
                
                icon_label.setPixmap(pixmap)
                header_layout.addWidget(icon_label)
        except Exception as e:
            logging.warning(f"Failed to load pods icon: {e}")

        # Header Text
        pods_header = QLabel("PODS RUNNING ON THIS NODE")
        pods_header.setStyleSheet(
            BaseDetailSectionStyles.get_section_header_style().replace("font-size: 16px;", "font-size: 14px;"))
        pods_header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        header_layout.addWidget(pods_header)
        header_layout.addStretch() # Push everything to left
        
        self.specific_layout.addWidget(header_container)

        # Create loading label
        self.pods_loading_label = QLabel("Loading pods...")
        self.pods_loading_label.setStyleSheet(
            BaseDetailSectionStyles.get_field_value_style())
        self.specific_layout.addWidget(self.pods_loading_label)

        # Create container for pods table
        self.pods_container = QWidget()
        pods_layout = QVBoxLayout(self.pods_container)
        pods_layout.setContentsMargins(0, 0, 0, 0)
        pods_layout.setSpacing(8)

        # Create table for pods
        self.pods_table = QTableWidget()
        self.pods_table.setColumnCount(5)
        self.pods_table.setHorizontalHeaderLabels(
            ["Pod Name", "Namespace", "Status", "CPU", "Memory"])

        # Style the table
        self.pods_table.horizontalHeader().setStretchLastSection(True)
        self.pods_table.verticalHeader().setVisible(False)
        
        # Style the table - Restore stylesheet for borders
        self.pods_table.setStyleSheet(
            OverviewSectionStyles.get_pods_table_style())

        # Disable row selection highlight
        self.pods_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.pods_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pods_table.setSortingEnabled(False) # Disable sorting for now to avoid complexity with widgets only # Disable row selection
        self.pods_table.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Remove focus outline
        self.pods_table.verticalHeader().setVisible(False)
        self.pods_table.verticalHeader().setDefaultSectionSize(45)

        # Connect single - click event to navigate to pod
        self.pods_table.itemClicked.connect(self._on_pod_clicked)

        # Set column widths
        header = self.pods_table.horizontalHeader()
        header.setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed)    # Pod Name
        header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed)    # Namespace
        header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed)    # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # CPU
        header.setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch)  # Memory

        self.pods_table.setColumnWidth(0, 250)  # Pod Name - made larger
        self.pods_table.setColumnWidth(1, 120)  # Namespace
        self.pods_table.setColumnWidth(2, 100)  # Status
        self.pods_table.setColumnWidth(3, 80)   # CPU
        # Memory column will stretch to fill remaining space

        # Set maximum height for table (show max 8 rows)
        self.pods_table.setMaximumHeight(250)

        pods_layout.addWidget(self.pods_table)
        self.pods_container.hide()  # Hide initially
        self.specific_layout.addWidget(self.pods_container)

        # Store node name for pod operations
        self.current_node_name = node_name

        # Fetch pods for this node
        self._fetch_node_pods(node_name)

    def _fetch_node_pods(self, node_name):

        try:
            # Connect to kubernetes client signals for pods
            self.kubernetes_client.pods_data_loaded.connect(
                self._handle_node_pods_loaded)
            self.kubernetes_client.api_error.connect(
                self._handle_node_pods_error)

            # Request pods for this node
            self.kubernetes_client.get_pods_for_node_async(node_name)

        except Exception as e:
            self._handle_node_pods_error(f"Failed to fetch pods: {str(e)}")

    def _disconnect_pods_signals(self):
        """Helper to disconnect pod-related signals"""
        try:
            self.kubernetes_client.pods_data_loaded.disconnect(self._handle_node_pods_loaded)
        except (TypeError, RuntimeError):
            pass
            
        try:
            self.kubernetes_client.api_error.disconnect(self._handle_node_pods_error)
        except (TypeError, RuntimeError):
            pass

    def _handle_node_pods_loaded(self, pods_data):

        try:
            # Safely disconnect signals using helper
            self._disconnect_pods_signals()

            # Hide loading label and show table container
            # Hide loading label and show table container
            try:
                # CRITICAL FIX: Ghost window issue
                # Check if the overall section is visible. If not, do NOT show children.
                if not self.isVisible() or not self.parent():
                    return
                
                # Check if widgets still have a parent and are valid
                if not self.pods_loading_label.parent() or not self.pods_container.parent():
                    return

                self.pods_loading_label.hide()
                self.pods_container.show()
            except RuntimeError:
                # Widget deleted, panel was closed - skip UI update
                return

            if not pods_data:
                # Show empty state in table
                self.pods_table.setRowCount(1)
                empty_item = QTableWidgetItem("No pods running on this node")
                empty_item.setFlags(empty_item.flags() & ~
                                    Qt.ItemFlag.ItemIsEditable)
                empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.pods_table.setItem(0, 0, empty_item)

                # Span across all columns
                self.pods_table.setSpan(0, 0, 1, 5)
                return

            # Clear existing content and prepare for new data
            self.pods_table.clearContents()
            self.pods_table.clearSpans()
            self.pods_table.setRowCount(len(pods_data))
            
            # Keep strong references to widgets to prevent GC issues
            self._pod_widgets = []

            for row, pod in enumerate(pods_data):
                pod_name = pod.get("name", "Unknown")
                namespace = pod.get("namespace", "Unknown")
                status = pod.get("status", "Unknown")

                # Get resource usage if available
                cpu_usage = pod.get("cpu_usage", "N/A")
                memory_usage = pod.get("memory_usage", "N/A")

                # Format resource usage
                if isinstance(cpu_usage, (int, float)):
                    cpu_display = f"{cpu_usage:.0f}m"
                else:
                    cpu_display = str(cpu_usage)

                if isinstance(memory_usage, (int, float)):
                    if memory_usage > 1024:
                        memory_display = f"{memory_usage / 1024:.1f}Gi"
                    else:
                        memory_display = f"{memory_usage:.0f}Mi"
                else:
                    memory_display = str(memory_usage)

                # Pod Name Cell - Orange, Clickable, Selectable
                name_label = ClickableSelectableLabel(pod_name)
                # Use explicit style
                theme = OverviewSectionStyles._get_theme()
                name_label.setStyleSheet(f"""
                    QLabel {{
                        font-size: 13px;
                        font-weight: normal;
                        color: {theme.colors.ACCENT_ORANGE};
                        padding: 4px;
                    }}
                """)
                name_label.setCursor(Qt.CursorShape.PointingHandCursor)
                # Connect click signal for navigation
                name_label.clicked.connect(lambda n=pod_name, ns=namespace: self._navigate_to_pods_page(n, ns))
                
                # Still set item for sorting and base data
                name_item = QTableWidgetItem(pod_name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.pods_table.setItem(row, 0, name_item)
                
                # Set the interactive widget
                self.pods_table.setCellWidget(row, 0, name_label)
                self._pod_widgets.append(name_label) # Keep reference

                # Namespace Cell - Selectable
                ns_label = QLabel(namespace)
                ns_label.setStyleSheet(f"""
                    QLabel {{
                        font-size: 13px;
                        font-weight: normal;
                        color: {theme.colors.TEXT_LIGHT};
                        padding: 4px;
                    }}
                """)
                ns_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                
                namespace_item = QTableWidgetItem(namespace)
                namespace_item.setFlags(namespace_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.pods_table.setItem(row, 1, namespace_item)
                
                self.pods_table.setCellWidget(row, 1, ns_label)
                self._pod_widgets.append(ns_label) # Keep reference

                # Add status cell with pill style (custom widget)
                status_bg = "rgba(100, 100, 100, 26)" # Default gray
                status_text = theme.colors.TEXT_SECONDARY
                
                if status.lower() == "running":
                    status_bg = "rgba(40, 167, 69, 38)" # Light green bg
                    status_text = theme.colors.STATUS_ACTIVE # Green text
                elif status.lower() in ["pending", "containercreating"]:
                    status_bg = "rgba(255, 193, 7, 38)" # Light orange bg
                    status_text = theme.colors.STATUS_WARNING # Orange text
                elif status.lower() in ["failed", "crashloopbackoff", "error"]:
                    status_bg = "rgba(220, 53, 69, 38)" # Light red bg
                    status_text = theme.colors.TEXT_DANGER # Red text

                # Prepare status item first
                status_item = QTableWidgetItem(status)
                self.pods_table.setItem(row, 2, status_item)

                # Create pill widget for status
                status_widget = QWidget()
                status_layout = QHBoxLayout(status_widget)
                status_layout.setContentsMargins(4, 4, 4, 4)
                status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                status_label = QLabel(status)
                status_label.setStyleSheet(f"""
                    QLabel {{ 
                        background-color: {status_bg}; 
                        color: {status_text}; 
                        border-radius: 4px; 
                        padding: 4px 8px;
                        font-weight: bold; 
                        font-size: 13px; 
                    }}
                """)
                status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                # Make status selectable? Usually not necessary for pill, but if requested:
                # status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse) 
                # (might look weird with background)
                status_layout.addWidget(status_label)
                
                self.pods_table.setCellWidget(row, 2, status_widget)
                self._pod_widgets.append(status_widget) # Keep reference

                # CPU Cell - Selectable
                cpu_label = QLabel(cpu_display)
                cpu_label.setStyleSheet(f"""
                    QLabel {{
                        font-size: 13px;
                        font-weight: normal;
                        color: {theme.colors.TEXT_LIGHT};
                        padding: 4px;
                    }}
                """)
                cpu_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                cpu_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                
                cpu_item = QTableWidgetItem(cpu_display)
                cpu_item.setFlags(cpu_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.pods_table.setItem(row, 3, cpu_item)
                
                self.pods_table.setCellWidget(row, 3, cpu_label)
                self._pod_widgets.append(cpu_label) # Keep reference

                # Memory Cell - Selectable
                mem_label = QLabel(memory_display)
                mem_label.setStyleSheet(f"""
                    QLabel {{
                        font-size: 13px;
                        font-weight: normal;
                        color: {theme.colors.TEXT_LIGHT};
                        padding: 4px;
                    }}
                """)
                mem_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                mem_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                
                mem_item = QTableWidgetItem(memory_display)
                mem_item.setFlags(mem_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                mem_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.pods_table.setItem(row, 4, mem_item)
                
                self.pods_table.setCellWidget(row, 4, mem_label)
                self._pod_widgets.append(mem_label) # Keep reference



            logging.info(
                f"Populated pods table with {len(pods_data)} pods for node")
            
            # Ensure rows fit content properly
            # self.pods_table.resizeRowsToContents()

        except Exception as e:
            logging.error(f"Error handling node pods data: {str(e)}")
            self._handle_node_pods_error(str(e))

    def _handle_node_pods_error(self, error_message):

        try:
            # Safely disconnect signals
            try:
                self.kubernetes_client.pods_data_loaded.disconnect(
                    self._handle_node_pods_loaded)
            except (TypeError, RuntimeError):
                pass

            try:
                self.kubernetes_client.api_error.disconnect(
                    self._handle_node_pods_error)
            except (TypeError, RuntimeError):
                pass
        except Exception:
            pass

        # Hide loading label and show error in table
        try:
            self.pods_loading_label.hide()
            self.pods_container.show()

            # Show error in table
            self.pods_table.setRowCount(1)
            error_item = QTableWidgetItem(f"Error loading pods: {error_message}")
            error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            error_item.setForeground(
                QColor(OverviewSectionStyles.get_text_danger_color()))
            self.pods_table.setItem(0, 0, error_item)

            # Span across all columns
            self.pods_table.setSpan(0, 0, 1, 5)
        except RuntimeError:
            # Widget deleted, panel was closed - skip UI update
            pass

        logging.error(f"Node pods error: {error_message}")

    def _on_pod_clicked(self, item):

        try:
            if not item:
                return

            # Get the row that was clicked
            row = item.row()

            # Get pod name from the first column (Pod Name)
            pod_name_item = self.pods_table.item(row, 0)
            if not pod_name_item:
                return

            pod_name = pod_name_item.text()

            # Get namespace from the second column (Namespace)
            namespace_item = self.pods_table.item(row, 1)
            namespace = namespace_item.text() if namespace_item else ""

            # Skip if this is an empty row or error message
            if pod_name in ["No pods running on this node", "Error loading pods"] or "Error loading pods" in pod_name:
                return

            logging.info(
                f"Navigating to pod '{pod_name}' in namespace '{namespace}'")

            # Navigate to the pods page and search for this specific pod
            self._navigate_to_pods_page(pod_name, namespace)

        except Exception as e:
            logging.error(f"Error handling pod click: {e}")

    def _navigate_to_pods_page(self, pod_name: str, namespace: str):

        try:
            # Get the main cluster view (parent window)
            detail_page = self.parent()
            while detail_page and not hasattr(detail_page, 'parent_window'):
                detail_page = detail_page.parent()

            if not detail_page or not hasattr(detail_page, 'parent_window'):
                logging.error("Could not find detail page with parent_window")
                return

            main_window = detail_page.parent_window
            logging.info(f"Found main_window: {type(main_window).__name__}")

            # Get the actual cluster view from the main window
            cluster_view = None
            if hasattr(main_window, 'cluster_view'):
                cluster_view = main_window.cluster_view
                logging.info(
                    f"Found cluster_view: {type(cluster_view).__name__}")
                logging.info(
                    f"Cluster view has handle_dropdown_selection: {hasattr(cluster_view, 'handle_dropdown_selection')}")
            else:
                logging.error(
                    "MainWindow does not have cluster_view attribute")
                return

            # Close the detail page first
            if hasattr(detail_page, 'close_detail'):
                detail_page.close_detail()
            elif hasattr(detail_page, 'hide'):
                detail_page.hide()

            # Navigate to pods page - try multiple methods
            navigation_success = False

            if hasattr(cluster_view, 'handle_dropdown_selection'):
                try:
                    cluster_view.handle_dropdown_selection("Pods")
                    logging.info(
                        "Called handle_dropdown_selection for Pods page")
                    navigation_success = True
                except Exception as e:
                    logging.error(
                        f"Error calling handle_dropdown_selection: {e}")

            # Try alternative navigation method
            if not navigation_success and hasattr(cluster_view, 'pages') and 'Pods' in cluster_view.pages:
                try:
                    pods_page = cluster_view.pages['Pods']
                    if hasattr(cluster_view, 'stacked_widget'):
                        cluster_view.stacked_widget.setCurrentWidget(pods_page)
                        logging.info(
                            "Navigated to Pods page using direct stacked widget")
                        navigation_success = True

                        # Load data for the pods page
                        if hasattr(cluster_view, '_load_page_data'):
                            cluster_view._load_page_data(pods_page)
                        elif hasattr(pods_page, 'force_load_data'):
                            pods_page.force_load_data()
                except Exception as e:
                    logging.error(f"Error with direct navigation: {e}")

            if not navigation_success:
                logging.error("All navigation methods failed")
                return

            # Wait longer for the page to load, then set search filter
            QTimer.singleShot(1000, lambda: self._set_pod_search_filter(
                cluster_view, pod_name, namespace))

        except Exception as e:
            logging.error(f"Error navigating to pods page: {e}")

    def _set_pod_search_filter(self, cluster_view, pod_name: str, namespace: str):

        try:
            # Check if we have stacked_widget
            if not hasattr(cluster_view, 'stacked_widget'):
                logging.error("ClusterView does not have stacked_widget")
                return

            # Get the current page (should be pods page)
            current_widget = cluster_view.stacked_widget.currentWidget()

            if not current_widget:
                logging.error("No current widget found in cluster view")
                return

            # Check if it's the pods page and has search functionality
            widget_type = type(current_widget).__name__
            logging.info(f"Current widget type: {widget_type}")
            logging.info(
                f"Has search_bar attribute: {hasattr(current_widget, 'search_bar')}")

            # If we still get ClusterView instead of PodsPage, try a different approach
            if widget_type == "ClusterView":
                logging.warning(
                    "Still showing ClusterView instead of PodsPage, trying alternative navigation")
                # Try to force navigate to pods page directly
                if hasattr(cluster_view, 'pages') and 'Pods' in cluster_view.pages:
                    pods_page = cluster_view.pages['Pods']
                    cluster_view.stacked_widget.setCurrentWidget(pods_page)
                    logging.info("Switched to pods page directly")
                    # Try again with the pods page
                    QTimer.singleShot(500, lambda: self._apply_search_to_pods_page(
                        pods_page, pod_name, namespace))
                else:
                    logging.error(
                        "Could not find Pods page in cluster view pages")
                return

            # We have the right page, now try to apply search
            self._apply_search_to_pods_page(
                current_widget, pod_name, namespace)

        except Exception as e:
            logging.error(f"Error setting pod search filter: {e}")

    def _apply_search_to_pods_page(self, pods_page, pod_name: str, namespace: str):

        try:
            logging.info(
                f"Applying search to pods page: {type(pods_page).__name__}")

            if hasattr(pods_page, 'search_bar'):
                logging.info(f"search_bar found: {pods_page.search_bar}")

                if pods_page.search_bar:
                    # Set the search text to find the specific pod
                    search_text = pod_name
                    pods_page.search_bar.setText(search_text)

                    # If the pods page has namespace filtering, try to set that too
                    if hasattr(pods_page, 'namespace_combo') and pods_page.namespace_combo:
                        # Try to find and select the namespace
                        combo = pods_page.namespace_combo
                        for i in range(combo.count()):
                            if combo.itemText(i) == namespace:
                                combo.setCurrentIndex(i)
                                break

                    logging.info(
                        f"Set pods page search filter to '{search_text}' in namespace '{namespace}'")
                    return

            # Try alternative methods to trigger search
            if hasattr(pods_page, '_perform_global_search'):
                logging.info(
                    f"Using alternative search method for pod '{pod_name}'")
                pods_page._perform_global_search(pod_name.lower())
            elif hasattr(pods_page, 'force_load_data'):
                logging.info("Triggering data reload for pods page")
                pods_page.force_load_data()
            else:
                logging.warning("Pods page does not have search functionality")

        except Exception as e:
            logging.error(f"Error applying search to pods page: {e}")

    def _update_chart_ui(self, data: Dict[str, Any]):

        try:
            metadata = data.get("metadata", {})
            spec = data.get("spec", {})

            # Update resource header
            chart_name = metadata.get("name", "Unnamed Chart")
            self.resource_name_label.setText(chart_name)

            chart_info = "Helm Chart"
            repository = spec.get("repository", metadata.get(
                "labels", {}).get("repository", "Unknown"))
            if repository:
                chart_info += f" / {repository}"
            self.resource_type_label.setText(chart_info)

            # Update creation / updated time card
            created_time = metadata.get("creationTimestamp", metadata.get(
                "annotations", {}).get("updated", ""))
            if created_time:
                try:
                    created_time = TimezoneManager.get_instance().format_time(created_time)
                except Exception:
                    pass
                self.created_card.title_label.setText("LAST UPDATED")
                self.created_card.value_label.setText(created_time)
            else:
                self.created_card.title_label.setText("CREATED")
                self.created_card.value_label.setText("Unknown")

            # Update chart - specific status
            self._update_chart_status(data)

        except Exception as e:
            logging.error(f"Error updating chart UI: {e}")

    def _update_release_ui(self, data: Dict[str, Any]):

        try:
            metadata = data.get("metadata", {})
            status = data.get("status", {})

            # Update resource header
            release_name = metadata.get("name", "Unnamed Release")
            self.resource_name_label.setText(release_name)

            release_info = "Helm Release"
            namespace = metadata.get("namespace")
            if namespace:
                release_info += f" / {namespace}"
            self.resource_type_label.setText(release_info)

            # Update creation / deployed time card
            deployed_time = status.get(
                "lastDeployed", metadata.get("creationTimestamp", ""))
            if deployed_time:
                try:
                    deployed_time = TimezoneManager.get_instance().format_time(deployed_time)
                except Exception:
                    pass
                self.created_card.title_label.setText("LAST DEPLOYED")
                self.created_card.value_label.setText(deployed_time)
            else:
                self.created_card.title_label.setText("DEPLOYED")
                self.created_card.value_label.setText("Unknown")

            # Update release - specific status
            self._update_release_status(data)

        except Exception as e:
            logging.error(f"Error updating release UI: {e}")

    def _update_chart_status(self, data: Dict[str, Any]):

        try:
            metadata = data.get("metadata", {})
            spec = data.get("spec", {})
            labels = metadata.get("labels", {})

            # Chart version and status
            version = spec.get("version", labels.get("version", "Unknown"))
            repository = spec.get(
                "repository", labels.get("repository", "Unknown"))

            if hasattr(self, "status_badge"):
                self.status_badge.setText("Available")
                self.status_badge.setStyleSheet(
                    BaseDetailSectionStyles.get_status_badge_style('success'))

            if hasattr(self, "status_text_label"):
                self.status_text_label.setText(
                    f"Version: {version} | Repository: {repository}")
                self.status_text_label.setVisible(True)

        except Exception as e:
            logging.error(f"Error updating chart status: {e}")

    def _update_release_status(self, data: Dict[str, Any]):

        try:
            status = data.get("status", {})
            spec = data.get("spec", {})

            # Release status
            release_status = status.get("phase", "Unknown")
            chart = spec.get("chart", "Unknown")
            revision = spec.get("revision", "1")

            if hasattr(self, "status_badge"):
                # Set badge color based on status using theme-aware colors
                if release_status.lower() in ["deployed", "success"]:
                    self.status_badge.setStyleSheet(
                        BaseDetailSectionStyles.get_status_badge_style('success'))
                elif release_status.lower() in ["failed", "error"]:
                    self.status_badge.setStyleSheet(
                        BaseDetailSectionStyles.get_status_badge_style('error'))
                else:
                    self.status_badge.setStyleSheet(
                        BaseDetailSectionStyles.get_status_badge_style('default'))

                self.status_badge.setText(release_status)

            if hasattr(self, "status_text_label"):
                self.status_text_label.setText(
                    f"Chart: {chart} | Revision: {revision}")
                self.status_text_label.setVisible(True)

        except Exception as e:
            logging.error(f"Error updating release status: {e}")
