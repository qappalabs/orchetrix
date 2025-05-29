"""
Reusable Detail Page component for displaying Kubernetes resource details.
Appears from the right side when a resource is clicked.
Provides tabbed interface for Overview, Details, YAML and Events.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, 
    QTextEdit, QFrame, QScrollArea, QTableWidget, QTableWidgetItem, 
    QHeaderView, QSplitter, QGraphicsDropShadowEffect, QToolButton,
    QListWidget, QListWidgetItem, QSizePolicy, QApplication, QStyleOption,
    QStyle, QMessageBox, QDialog, QDialogButtonBox, QComboBox, QLineEdit,
    QFormLayout, QProgressDialog
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QRect, QEasingCurve, QSize, QTimer, pyqtSignal,
    QParallelAnimationGroup, QSequentialAnimationGroup, QPoint, QObject, 
    QEvent, QAbstractAnimation
)
from PyQt6.QtGui import (
    QColor, QIcon, QFont, QPalette, QSyntaxHighlighter, QTextCharFormat, 
    QTextCursor, QPainter, QBrush, QPen, QLinearGradient, QPainterPath
)

from utils.helm_utils import ChartInstallDialog, install_helm_chart

from UI.Styles import AppStyles, AppColors, AppConstants
import yaml
import json
import difflib
import subprocess
import os
import tempfile
import platform
import time
import base64
import shutil
from datetime import datetime


class YamlHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for YAML content with improved color scheme"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        
        # Format for keys
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#569CD6"))
        key_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r'^\s*[^:]+:', key_format))
        
        # Format for values
        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#CE9178"))
        self.highlighting_rules.append((r':\s*[^{\\[].*$', value_format))
        
        # Format for lists
        list_format = QTextCharFormat()
        list_format.setForeground(QColor("#B5CEA8"))
        self.highlighting_rules.append((r'^\s*-\s+', list_format))
        
        # Format for comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.highlighting_rules.append((r'#.*$', comment_format))
        
        # Format for numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self.highlighting_rules.append((r'\b\d+\b', number_format))
        
        # Format for booleans
        boolean_format = QTextCharFormat()
        boolean_format.setForeground(QColor("#569CD6"))
        self.highlighting_rules.append((r'\b(true|false|True|False|yes|no|Yes|No)\b', boolean_format))
        
        # Format for null values
        null_format = QTextCharFormat()
        null_format.setForeground(QColor("#569CD6"))
        self.highlighting_rules.append((r'\b(null|Null|NULL|~)\b', null_format))
        
        # Format for strings in quotes
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self.highlighting_rules.append((r'"[^"]*"', string_format))
        self.highlighting_rules.append((r"'[^']*'", string_format))
        
        import re
        self.rules = [(re.compile(pattern), fmt) for pattern, fmt in self.highlighting_rules]
    
    def highlightBlock(self, text):
        """Apply highlighting to the given block of text"""
        for regex, format in self.rules:
            matches = regex.finditer(text)
            for match in matches:
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        
    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)
        
    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class YamlEditorWithLineNumbers(QTextEdit):
    """YAML editor with line numbers support"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_line_numbers = True
        self.tab_size = 2  # Default tab size
        self.line_number_area = LineNumberArea(self)
        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.verticalScrollBar().valueChanged.connect(self.update_line_number_area)
        self.textChanged.connect(lambda: self.update_line_number_area(0))
        self.update_line_number_area_width(0)
        
    def lineNumberAreaWidth(self):
        if not self.show_line_numbers:
            return 0
            
        digits = 1
        max_block = max(1, self.document().blockCount())
        while max_block >= 10:
            max_block /= 10
            digits += 1
            
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
        
    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
        
    def update_line_number_area(self, dy=0):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, 0, self.line_number_area.width(), self.height())
            
        if self.height() != self.line_number_area.height():
            self.line_number_area.setFixedHeight(self.height())
        self.update_line_number_area_width(0)
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))
        
    def set_show_line_numbers(self, show):
        self.show_line_numbers = show
        self.update_line_number_area_width(0)
        self.line_number_area.update()
        
    def set_tab_size(self, tab_size):
        """Set the tab size (number of spaces per tab)"""
        self.tab_size = tab_size
    
    def keyPressEvent(self, event):
        """Override key press event to handle tab with custom size"""
        if event.key() == Qt.Key.Key_Tab:
            # Insert spaces instead of tab character
            spaces = " " * self.tab_size
            self.insertPlainText(spaces)
        else:
            super().keyPressEvent(event)
            
    def line_number_area_paint_event(self, event):
        if not self.show_line_numbers:
            return
            
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(AppColors.BG_DARK))
        
        # Get visible blocks
        block = self.document().firstBlock()
        block_number = 0
        
        # Get viewport offset for proper text alignment
        viewport_offset = self.verticalScrollBar().value()
        
        while block.isValid():
            # Get block position in viewport coordinates
            block_rect = self.document().documentLayout().blockBoundingRect(block)
            block_top = int(block_rect.translated(0, -viewport_offset).top())  # Convert to int
            
            # Only paint if block is visible
            if block_top >= 0 and block_top < self.height():
                number = str(block_number + 1)
                painter.setPen(QColor(AppColors.TEXT_SUBTLE))
                painter.drawText(0, block_top, self.line_number_area.width() - 5, 
                                self.fontMetrics().height(),
                                Qt.AlignmentFlag.AlignRight, number)
                                
            block = block.next()
            block_number += 1

class ModernResizeHandle(QWidget):
    """A modern resize handle with visual feedback"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setFixedWidth(AppStyles.DETAIL_PAGE_RESIZE_HANDLE_WIDTH)
        self.setMouseTracking(True)
        self.hovered = False
        self.dragging = False
        
        self.normal_color = QColor(AppColors.BORDER_COLOR)
        self.hover_color = QColor(AppColors.ACCENT_BLUE)
        self.active_color = QColor(AppColors.ACCENT_BLUE)
        
    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
        super().mouseReleaseEvent(event)
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.dragging:
            color = self.active_color
            opacity = 1.0
        elif self.hovered:
            color = self.hover_color
            opacity = 0.8
        else:
            color = self.normal_color
            opacity = 0.6
        
        color.setAlphaF(opacity)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        
        dot_size = 2
        dot_spacing = 6
        num_dots = self.height() // dot_spacing - 1
        start_y = (self.height() - (num_dots * dot_spacing)) / 2
        
        for i in range(num_dots):
            y_pos = start_y + i * dot_spacing
            painter.drawEllipse(
                int(self.width() / 2 - dot_size / 2),
                int(y_pos),
                dot_size,
                dot_size
            )

class ModernBackButton(QToolButton):
    """A modern styled back button with animations"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setText("←")
        self.setFont(QFont("Segoe UI", 14))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.hovered = False
        self.pressed = False
        self.bg_normal = QColor(AppColors.BG_MEDIUM)
        self.bg_hover = QColor(AppColors.HOVER_BG)
        self.bg_pressed = QColor(AppColors.BG_DARK)
        self.color_normal = QColor(AppColors.TEXT_SUBTLE)
        self.color_hover = QColor(AppColors.TEXT_LIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    
    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.hovered = False
        self.pressed = False
        self.update()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed = True
            self.update()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed = False
            self.update()
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.pressed:
            bg_color = self.bg_pressed
            text_color = self.color_hover
        elif self.hovered:
            bg_color = self.bg_hover
            text_color = self.color_hover
        else:
            bg_color = self.bg_normal
            text_color = self.color_normal
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawEllipse(QRect(0, 0, self.width(), self.height()))
        
        painter.setPen(text_color)
        painter.setFont(self.font())
        painter.drawText(QRect(0, 0, self.width(), self.height()), 
                        Qt.AlignmentFlag.AlignCenter, self.text())


class DetailPage(QWidget):
    back_signal = pyqtSignal()
    resource_updated_signal = pyqtSignal(str, str, str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.resource_type = None
        self.resource_name = None
        self.resource_namespace = None
        self.current_data = None
        self.original_yaml = None
        self.yaml_edited = False
        self.is_minimized = False
        self.minimized_width = 0
        self.animation_in_progress = False
        self.current_font_size = 12  # Default font size
        self.current_font_family = "Consolas"  # Default font family
        self.current_tab_size = 2  # Default tab size
        self.show_line_numbers = True  # Default to showing line numbers
        
        # Initialize recursion prevention flags
        self._currently_updating_font = None
        self._currently_updating_size = None
        self._currently_updating_tab_size = None
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setup_ui()
        self.hide()
        self.setup_animations()
    
    def setup_ui(self):
        self.setFixedWidth(AppStyles.DETAIL_PAGE_WIDTH)
        self.setMinimumWidth(AppStyles.DETAIL_PAGE_MIN_WIDTH)
        self.setMaximumWidth(AppStyles.DETAIL_PAGE_MAX_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        
        self.setStyleSheet(f"""
            background-color: {AppColors.BG_SIDEBAR};
            border: none;
            border-radius: 8px;
        """)
        
        self.apply_shadow_effect()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.create_header()
        self.create_resize_handle()
        self.create_content_area()
        self.create_tabs()
    
    def apply_shadow_effect(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow_color = QColor(0, 0, 0)
        shadow_color.setAlpha(80)
        shadow.setColor(shadow_color)
        shadow.setOffset(-2, 0)
        self.setGraphicsEffect(shadow)
    
    def setup_animations(self):
        self.animation_group = QParallelAnimationGroup()
        
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(200)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        
        self.animation_group.addAnimation(self.slide_animation)
        self.animation_group.addAnimation(self.fade_animation)
        self.animation_group.finished.connect(self.on_animation_finished)
    
    def on_animation_finished(self):
        self.animation_in_progress = False
        if self.slide_animation.direction() == QAbstractAnimation.Direction.Backward and not self.is_minimized:
            self.hide()

    def create_header(self):
        self.header = QWidget()
        self.header.setFixedHeight(60)
        self.header.setStyleSheet(f"""
            background-color: {AppColors.BG_HEADER};
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        self.back_button = ModernBackButton()
        self.back_button.clicked.connect(self.close_detail)
        
        self.title_label = QLabel("Resource Details")
        self.title_label.setStyleSheet(f"""
            color: {AppColors.TEXT_LIGHT};
            font-size: 16px;
            font-weight: bold;
            margin-left: 10px;
        """)
        
        # Remove the action button from header
        
        self.loading_indicator = QFrame()
        self.loading_indicator.setFixedWidth(100)
        self.loading_indicator.setFixedHeight(5)
        self.loading_indicator.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.BG_MEDIUM};
                border: none;
                border-radius: 2px;
            }}
        """)
        
        self.loading_animation = QPropertyAnimation(self.loading_indicator, b"styleSheet")
        self.loading_animation.setDuration(1200)
        self.loading_animation.setLoopCount(-1)
        
        self.loading_animation.setKeyValueAt(0, f"""
            QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {AppColors.ACCENT_BLUE}, 
                    stop:0.1 {AppColors.ACCENT_BLUE}, 
                    stop:0.4 transparent, 
                    stop:0.6 transparent);
                border: none;
                border-radius: 2px;
            }}
        """)
        self.loading_animation.setKeyValueAt(0.5, f"""
            QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0.4 transparent, 
                    stop:0.6 {AppColors.ACCENT_BLUE}, 
                    stop:0.9 {AppColors.ACCENT_BLUE}, 
                    stop:1 transparent);
                border: none;
                border-radius: 2px;
            }}
        """)
        self.loading_animation.setKeyValueAt(1, f"""
            QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {AppColors.ACCENT_BLUE}, 
                    stop:0.1 {AppColors.ACCENT_BLUE}, 
                    stop:0.4 transparent, 
                    stop:0.6 transparent);
                border: none;
                border-radius: 2px;
            }}
        """)
        
        self.loading_indicator.hide()
        
        header_layout.addWidget(self.back_button)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.loading_indicator)
        
        self.main_layout.addWidget(self.header)
        
    def create_resize_handle(self):
        self.resize_handle = ModernResizeHandle(self)
        self.resize_handle.show()
        
        self.resize_start_x = 0
        self.resize_start_width = self.width()
        
        self.resize_handle.mousePressEvent = self.resize_handle_mousePressEvent
        self.resize_handle.mouseMoveEvent = self.resize_handle_mouseMoveEvent
        self.resize_handle.mouseReleaseEvent = self.resize_handle_mouseReleaseEvent
    
    def resize_handle_mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resize_start_x = int(event.globalPosition().x())
            self.resize_start_width = self.width()
        ModernResizeHandle.mousePressEvent(self.resize_handle, event)
    
    def resize_handle_mouseMoveEvent(self, event):
        if hasattr(event, 'buttons') and event.buttons() == Qt.MouseButton.LeftButton:
            delta = self.resize_start_x - event.globalPosition().x()
            new_width = int(self.resize_start_width + delta)
            
            if new_width >= AppStyles.DETAIL_PAGE_MIN_WIDTH and new_width <= AppStyles.DETAIL_PAGE_MAX_WIDTH:
                self.setFixedWidth(new_width)
                if self.parent():
                    self.move(self.parent().width() - self.width(), 0)
        ModernResizeHandle.mouseMoveEvent(self.resize_handle, event)
    
    def resize_handle_mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resize_start_width = self.width()
        ModernResizeHandle.mouseReleaseEvent(self.resize_handle, event)
    
    def create_content_area(self):
        self.content_area = QWidget()
        self.content_area.setStyleSheet(f"background-color: {AppColors.BG_SIDEBAR}; border: none;")
        
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {AppColors.BG_SIDEBAR};
            }}
            QTabBar::tab {{
                background-color: {AppColors.BG_SIDEBAR};
                color: {AppColors.TEXT_SECONDARY};
                padding: 8px 24px;
                border: none;
                margin-right: 2px;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                color: {AppColors.TEXT_LIGHT};
                border-bottom: 2px solid {AppColors.ACCENT_BLUE};
            }}
            QTabBar::tab:hover:!selected {{
                color: {AppColors.TEXT_LIGHT};
                background-color: {AppColors.HOVER_BG_DARKER};
            }}
        """)
        
        content_layout.addWidget(self.tab_widget)
        self.main_layout.addWidget(self.content_area)
    
    def create_tabs(self):
        self.overview_tab = QWidget()
        self.overview_tab.setStyleSheet(f"background-color: {AppColors.BG_SIDEBAR}; border: none;")
        self.overview_layout = QVBoxLayout(self.overview_tab)
        self.overview_layout.setContentsMargins(20, 20, 20, 20)
        self.overview_layout.setSpacing(10)
        
        self.create_overview_summary()
        
        self.details_tab = QScrollArea()
        self.details_tab.setStyleSheet(f"""
            QScrollArea {{
                background-color: {AppColors.BG_SIDEBAR};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {AppColors.BG_DARK};
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {AppColors.BG_LIGHT};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self.details_tab.setWidgetResizable(True)
        self.details_tab.setFrameShape(QFrame.Shape.NoFrame)
        self.details_tab.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.details_content = QWidget()
        self.details_content.setStyleSheet(f"background-color: {AppColors.BG_SIDEBAR}; border: none;")
        self.details_layout = QVBoxLayout(self.details_content)
        self.details_layout.setContentsMargins(20, 20, 20, 20)
        self.details_layout.setSpacing(10)
        self.details_tab.setWidget(self.details_content)
        
        self.yaml_tab = QWidget()
        self.yaml_tab.setStyleSheet(f"background-color: {AppColors.BG_SIDEBAR}; border: none;")
        self.yaml_layout = QVBoxLayout(self.yaml_tab)
        self.yaml_layout.setContentsMargins(0, 0, 0, 0)
        self.yaml_layout.setSpacing(0)
        
        self.create_yaml_editor()
        
        self.events_tab = QWidget()
        self.events_layout = QVBoxLayout(self.events_tab)
        self.events_tab.setStyleSheet(f"background-color: {AppColors.BG_SIDEBAR}; border: none;")
        self.events_layout.setContentsMargins(20, 20, 20, 20)
        self.events_layout.setSpacing(10)
        
        self.create_events_list()
        
        self.tab_widget.addTab(self.overview_tab, "Overview")
        self.tab_widget.addTab(self.details_tab, "Details")
        self.tab_widget.addTab(self.yaml_tab, "YAML")
        self.tab_widget.addTab(self.events_tab, "Events")
        
        self.tab_widget.currentChanged.connect(self.handle_tab_changed)
    
    def create_overview_summary(self):
        """Create the overview summary with install/upgrade button"""
        self.resource_name_label = QLabel("Resource Name")
        self.resource_name_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {AppColors.TEXT_LIGHT};
        """)
        
        self.resource_info_label = QLabel("Type / Namespace")
        self.resource_info_label.setStyleSheet(f"""
            font-size: 14px;
            color: {AppColors.TEXT_SUBTLE};
            margin-bottom: 10px;
        """)
        
        self.creation_time_label = QLabel("Created: unknown")
        self.creation_time_label.setStyleSheet(f"""
            font-size: 13px;
            color: {AppColors.TEXT_SUBTLE};
        """)
        
        # Create a container for header info and action button
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a vertical layout for the left side (name, info, creation time)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        left_layout.addWidget(self.resource_name_label)
        left_layout.addWidget(self.resource_info_label)
        left_layout.addWidget(self.creation_time_label)
        
        header_layout.addLayout(left_layout)
        header_layout.addStretch()
        
        # Add action button (Install/Upgrade)
        self.action_button = QPushButton("Install")
        self.action_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.ACCENT_GREEN};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
            QPushButton:pressed {{
                background-color: #3d8b40;
            }}
        """)
        self.action_button.clicked.connect(self.handle_action_button)
        self.action_button.hide()  # Hidden by default
        
        header_layout.addWidget(self.action_button)
        
        # Add the header container to the main layout
        self.overview_layout.addWidget(header_container)
        
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"""
            background-color: {AppColors.BORDER_COLOR};
            max-height: 1px;
            margin-top: 15px;
            margin-bottom: 15px;
        """)
        self.overview_layout.addWidget(divider)
        
        # Continue with the rest of your existing code...
        self.status_section = QWidget()
        self.status_layout = QVBoxLayout(self.status_section)
        self.status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_layout.setSpacing(10)
        
        status_title = QLabel("STATUS")
        status_title.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {AppColors.TEXT_SUBTLE};
            text-transform: uppercase;
        """)
        self.status_layout.addWidget(status_title)
        
        self.status_container = QWidget()
        self.status_container.setStyleSheet(f"""
            background-color: {AppColors.BG_MEDIUM};
            border-radius: 6px;
            padding: 5px;
        """)
        status_container_layout = QHBoxLayout(self.status_container)
        status_container_layout.setContentsMargins(15, 10, 15, 10)
        status_container_layout.setSpacing(5)
        
        self.status_value_label = QLabel("Unknown")
        self.status_value_label.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_RUNNING_STYLE)
        
        self.status_text_label = QLabel("Status not available")
        self.status_text_label.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_TEXT_STYLE)
        
        status_container_layout.addWidget(self.status_value_label)
        status_container_layout.addWidget(self.status_text_label)
        status_container_layout.addStretch()
        
        self.status_layout.addWidget(self.status_container)
        self.overview_layout.addWidget(self.status_section)
        
        self.conditions_section = QWidget()
        self.conditions_layout = QVBoxLayout(self.conditions_section)
        self.conditions_layout.setContentsMargins(0, 0, 0, 0)
        self.conditions_layout.setSpacing(10)
        
        conditions_title = QLabel("CONDITIONS")
        conditions_title.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {AppColors.TEXT_SUBTLE};
            text-transform: uppercase;
            margin-top: 10px;
        """)
        self.conditions_layout.addWidget(conditions_title)
        
        self.conditions_container = QWidget()
        self.conditions_container.setStyleSheet(f"""
            background-color: {AppColors.BG_MEDIUM};
            border-radius: 6px;
            padding: 5px;
        """)
        self.conditions_container_layout = QVBoxLayout(self.conditions_container)
        self.conditions_container_layout.setContentsMargins(15, 10, 15, 10)
        self.conditions_container_layout.setSpacing(8)
        
        self.no_conditions_label = QLabel("No conditions available")
        self.no_conditions_label.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_NO_DATA_STYLE)
        self.conditions_container_layout.addWidget(self.no_conditions_label)
        
        self.conditions_layout.addWidget(self.conditions_container)
        self.overview_layout.addWidget(self.conditions_section)
        
        self.labels_section = QWidget()
        self.labels_section.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.BG_MEDIUM};
                border-radius: 6px;
            }}
        """)
        self.labels_layout = QVBoxLayout(self.labels_section)
        self.labels_layout.setContentsMargins(15, 15, 15, 15)
        self.labels_layout.setSpacing(10)
        
        labels_title = QLabel("LABELS")
        labels_title.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {AppColors.TEXT_SUBTLE};
            text-transform: uppercase;
            margin-top: 0px;
        """)
        self.labels_layout.addWidget(labels_title)
        
        self.labels_content = QLabel("No labels")
        self.labels_content.setStyleSheet(f"""
            font-family: Consolas, 'Courier New', monospace;
            font-size: 14px;
            color: {AppColors.TEXT_LIGHT};
            padding: 5px 0px;
        """)
        self.labels_content.setWordWrap(True)
        self.labels_layout.addWidget(self.labels_content)
        
        self.overview_layout.addWidget(self.labels_section)
        
        self.specific_section = QWidget()
        self.specific_section.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.BG_MEDIUM};
                border-radius: 6px;
            }}
        """)
        self.specific_layout = QVBoxLayout(self.specific_section)
        self.specific_layout.setContentsMargins(15, 15, 15, 15)
        self.specific_layout.setSpacing(10)
        
        self.specific_section.hide()
        
        self.overview_layout.addWidget(self.specific_section)
        self.overview_layout.addStretch()
    
    def create_yaml_editor(self):
        yaml_toolbar = QWidget()
        yaml_toolbar.setFixedHeight(40)
        yaml_toolbar.setStyleSheet(f"""
            background-color: {AppColors.BG_DARK};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        """)
        
        toolbar_layout = QHBoxLayout(yaml_toolbar)
        toolbar_layout.setContentsMargins(10, 0, 10, 0)
        
        self.yaml_edit_button = QPushButton("Edit")
        self.yaml_edit_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.yaml_edit_button.clicked.connect(self.toggle_yaml_edit_mode)
        
        self.yaml_save_button = QPushButton("Save")
        self.yaml_save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.yaml_save_button.clicked.connect(self.save_yaml_changes)
        self.yaml_save_button.hide()
        
        self.yaml_cancel_button = QPushButton("Cancel")
        self.yaml_cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.yaml_cancel_button.clicked.connect(self.cancel_yaml_edit)
        self.yaml_cancel_button.hide()
        
        # Add a font size indicator
        self.yaml_font_size_label = QLabel(f"Font Size: {self.current_font_size}")
        self.yaml_font_size_label.setStyleSheet("""
            color: #aaaaaa;
            font-size: 12px;
            padding: 5px;
        """)
        
        # Add a font family indicator 
        self.yaml_font_family_label = QLabel(f"Font: {self.current_font_family}")
        self.yaml_font_family_label.setStyleSheet("""
            color: #aaaaaa;
            font-size: 12px;
            padding: 5px;
        """)
        
        # Add a line numbers indicator
        self.yaml_line_numbers_label = QLabel(f"Line Numbers: {'On' if self.show_line_numbers else 'Off'}")
        self.yaml_line_numbers_label.setStyleSheet("""
            color: #aaaaaa;
            font-size: 12px;
            padding: 5px;
        """)
        
        # Add a tab size indicator
        self.yaml_tab_size_label = QLabel(f"Tab Size: {self.current_tab_size}")
        self.yaml_tab_size_label.setStyleSheet("""
            color: #aaaaaa;
            font-size: 12px;
            padding: 5px;
        """)
        
        toolbar_layout.addWidget(self.yaml_edit_button)
        toolbar_layout.addWidget(self.yaml_save_button)
        toolbar_layout.addWidget(self.yaml_cancel_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.yaml_font_family_label)
        toolbar_layout.addWidget(self.yaml_font_size_label)
        toolbar_layout.addWidget(self.yaml_line_numbers_label)
        toolbar_layout.addWidget(self.yaml_tab_size_label)
        
        # Try to get font settings from parent window's preferences if available
        font_size = self.current_font_size
        font_family = self.current_font_family
        tab_size = self.current_tab_size
        
        if hasattr(self, 'parent_window') and self.parent_window:
            if hasattr(self.parent_window, 'preferences_page'):
                prefs = self.parent_window.preferences_page
                if hasattr(prefs, 'get_current_font_size'):
                    font_size = prefs.get_current_font_size()
                    self.current_font_size = font_size
                    self.yaml_font_size_label.setText(f"Font Size: {font_size}")
                if hasattr(prefs, 'current_font_family'):
                    font_family = prefs.current_font_family
                    self.current_font_family = font_family
                    self.yaml_font_family_label.setText(f"Font: {font_family}")
                if hasattr(prefs, 'show_line_numbers'):
                    self.show_line_numbers = prefs.show_line_numbers
                    self.yaml_line_numbers_label.setText(f"Line Numbers: {'On' if self.show_line_numbers else 'Off'}")
                if hasattr(prefs, 'current_tab_size'):
                    tab_size = prefs.current_tab_size
                    self.current_tab_size = tab_size
                    self.yaml_tab_size_label.setText(f"Tab Size: {tab_size}")
        
        # Use custom editor with line numbers support
        self.yaml_editor = YamlEditorWithLineNumbers()
        self.yaml_editor.setReadOnly(True)
        
        # Create a proper font with the right size and family
        font = QFont(self.current_font_family, self.current_font_size)
        self.yaml_editor.setFont(font)
        
        # Set line numbers visibility based on preference
        self.yaml_editor.set_show_line_numbers(self.show_line_numbers)
        
        # Set tab size based on preference
        self.yaml_editor.set_tab_size(self.current_tab_size)
        
        # Basic stylesheet without font settings (those are set directly with setFont)
        base_yaml_style = """
            background-color: #1E1E1E;
            color: #D4D4D4;
            border: none;
            selection-background-color: #264F78;
            selection-color: #D4D4D4;
        """
        self.yaml_editor.setStyleSheet(base_yaml_style)
        
        self.yaml_highlighter = YamlHighlighter(self.yaml_editor.document())
        
        self.yaml_layout.addWidget(yaml_toolbar)
        self.yaml_layout.addWidget(self.yaml_editor)
    
    def update_yaml_font_size(self, font_size):
        """Update the YAML editor font size"""
        if not hasattr(self, 'yaml_editor'):
            return
            
        # Guard against recursion by checking if we're already updating with this size
        if hasattr(self, '_currently_updating_size') and self._currently_updating_size == font_size:
            return
            
        print(f"DetailPage: Updating YAML font size to {font_size}")
        
        # Set recursion guard
        self._currently_updating_size = font_size
        
        try:
            # Update the internal state
            self.current_font_size = font_size
            
            # Update the font size label
            if hasattr(self, 'yaml_font_size_label'):
                self.yaml_font_size_label.setText(f"Font Size: {font_size}")
            
            # Get current font and update its size
            font = self.yaml_editor.font()
            font.setPointSize(font_size)
            
            # Apply the updated font
            self.yaml_editor.setFont(font)
        finally:
            # Clear recursion guard
            self._currently_updating_size = None
    
    def update_yaml_font_family(self, font_family):
        """Update the YAML editor font family"""
        if not hasattr(self, 'yaml_editor'):
            return
            
        # Guard against recursion by checking if we're already updating with this font
        if hasattr(self, '_currently_updating_font') and self._currently_updating_font == font_family:
            return
            
        print(f"DetailPage: Updating YAML font family to {font_family}")
        
        # Set recursion guard
        self._currently_updating_font = font_family
        
        try:
            # Update the internal state
            self.current_font_family = font_family
            
            # Update the font family label
            if hasattr(self, 'yaml_font_family_label'):
                self.yaml_font_family_label.setText(f"Font: {font_family}")
            
            # Get current font and update its family
            font = self.yaml_editor.font()
            font.setFamily(font_family)
            
            # Apply the updated font
            self.yaml_editor.setFont(font)
            
            print(f"DetailPage: Applied font family {font_family} to YAML editor")
        finally:
            # Clear recursion guard
            self._currently_updating_font = None
    
    def update_yaml_line_numbers(self, show_line_numbers):
        """Update the YAML editor line numbers visibility"""
        if not hasattr(self, 'yaml_editor'):
            return
            
        print(f"DetailPage: Updating YAML line numbers to {show_line_numbers}")
        
        # Update property and apply to editor
        self.show_line_numbers = show_line_numbers
        self.yaml_editor.set_show_line_numbers(show_line_numbers)
        
        # Update the line numbers label
        if hasattr(self, 'yaml_line_numbers_label'):
            self.yaml_line_numbers_label.setText(f"Line Numbers: {'On' if show_line_numbers else 'Off'}")
    
    def update_yaml_tab_size(self, tab_size):
        """Update the YAML editor tab size"""
        if not hasattr(self, 'yaml_editor'):
            return
            
        # Guard against recursion by checking if we're already updating with this size
        if hasattr(self, '_currently_updating_tab_size') and self._currently_updating_tab_size == tab_size:
            return
            
        print(f"DetailPage: Updating YAML tab size to {tab_size}")
        
        # Set recursion guard
        self._currently_updating_tab_size = tab_size
        
        try:
            # Update the internal state
            self.current_tab_size = tab_size
            
            # Update the tab size in the editor
            self.yaml_editor.set_tab_size(tab_size)
            
            # Update the tab size label
            if hasattr(self, 'yaml_tab_size_label'):
                self.yaml_tab_size_label.setText(f"Tab Size: {tab_size}")
        finally:
            # Clear recursion guard
            self._currently_updating_tab_size = None
    
    # Add an alias method to ensure compatibility with MainWindow's lookup
    def update_yaml_editor_font_family(self, font_family):
        """Alias method to ensure compatibility with MainWindow's font family update mechanism"""
        print(f"DetailPage: Called update_yaml_editor_font_family with {font_family}")
        self.update_yaml_font_family(font_family)
    
    # Add an alias method to ensure compatibility with MainWindow's lookup
    def update_yaml_editor_font_size(self, font_size):
        """Alias method to ensure compatibility with MainWindow's font size update mechanism"""
        print(f"DetailPage: Called update_yaml_editor_font_size with {font_size}")
        self.update_yaml_font_size(font_size)
    
    # Add an alias method to ensure compatibility with MainWindow's lookup
    def update_yaml_editor_tab_size(self, tab_size):
        """Alias method to ensure compatibility with MainWindow's tab size update mechanism"""
        print(f"DetailPage: Called update_yaml_editor_tab_size with {tab_size}")
        self.update_yaml_tab_size(tab_size)
    
    def create_events_list(self):
        self.events_list = QListWidget()
        self.events_list.setStyleSheet(AppStyles.DETAIL_PAGE_EVENTS_LIST_STYLE)
        self.events_list.setFrameShape(QFrame.Shape.NoFrame)
        self.events_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        
        self.events_layout.addWidget(self.events_list)
    
    def show_detail(self, resource_type, resource_name, namespace=None):
        """Show detail for resource with action button in overview"""
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.resource_namespace = namespace
        
        title_text = f"{resource_type}: {resource_name}"
        if namespace:
            title_text += f" (ns: {namespace})"
        self.title_label.setText(title_text)
        
        self.clear_content()
        
        # Show/Hide action button based on resource type
        if resource_type == "chart":
            self.action_button.setText("Install")
            self.action_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {AppColors.ACCENT_GREEN};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #45a049;
                }}
                QPushButton:pressed {{
                    background-color: #3d8b40;
                }}
            """)
            self.action_button.show()
        elif resource_type == "helmrelease":
            self.action_button.setText("Upgrade")
            self.action_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {AppColors.ACCENT_BLUE};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #0078e7;
                }}
                QPushButton:pressed {{
                    background-color: #0063b1;
                }}
            """)
            self.action_button.show()
        else:
            self.action_button.hide()
        
        self.loading_indicator.show()
        self.loading_animation.start()
        
        QTimer.singleShot(0, self.load_resource_details)
        
        if not self.isVisible():
            self.show_with_animation()
            
            # Install event filter on parent window to catch clicks outside
            if self.parent_window:
                # Remove any existing filter first to avoid duplicates
                self.parent_window.removeEventFilter(self)
                # Install our event filter
                self.parent_window.installEventFilter(self)
                
    def handle_action_button(self):
        """Handle install/upgrade button click based on resource type"""
        if self.resource_type == "chart":
            self._install_chart()
        elif self.resource_type == "helmrelease":
            self._upgrade_chart()

    def _install_chart(self):
        """Display installation dialog and install the chart"""
        # Get chart info
        chart_name = self.resource_name
        repository = None
        
        # Try to get repository from current_data
        if self.current_data:
            spec = self.current_data.get("spec", {})
            metadata = self.current_data.get("metadata", {})
            labels = metadata.get("labels", {})
            
            repository = spec.get("repository") or labels.get("repository")
        
        # Create and show the installation dialog
        dialog = ChartInstallDialog(chart_name, repository, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get installation options
            options = dialog.get_values()
            
            # Install the chart
            success, message = install_helm_chart(chart_name, repository, options, self)
            
            # Show result message
            if success:
                QMessageBox.information(self, "Installation Successful", message)
                
                # Emit signal to refresh the Releases page
                self.resource_updated_signal.emit(
                    "helmrelease",
                    options["release_name"],
                    options["namespace"]
                )
            else:
                QMessageBox.critical(self, "Installation Failed", message)

    def _upgrade_chart(self):
        """Display upgrade dialog and upgrade the release"""
        # Find the Releases page instance first
        releases_page = None
        for widget in QApplication.allWidgets():
            if isinstance(widget, QWidget) and hasattr(widget, 'upgrade_release') and hasattr(widget, 'resource_type'):
                if getattr(widget, 'resource_type', None) == "helmreleases":
                    releases_page = widget
                    break
        
        if not releases_page:
            QMessageBox.information(
                self,
                "Upgrade",
                "Could not find releases manager. Chart upgrade functionality is currently unavailable."
            )
            return
        
        # Now call the upgrade_release method from the ReleasesPage
        releases_page.upgrade_release(self.resource_name, self.resource_namespace)
        
        # After upgrading, reload the details
        QTimer.singleShot(500, self.load_resource_details)
        
    def handle_tab_changed(self, index):
        tab_name = self.tab_widget.tabText(index)
        
        if tab_name == "YAML" and self.yaml_editor.toPlainText() == "" and self.current_data:
            self.update_yaml_tab()
        elif tab_name == "Events" and self.events_list.count() == 0:
            self.load_events()
    
    def toggle_yaml_edit_mode(self):
        if self.yaml_editor.isReadOnly():
            self.yaml_editor.setReadOnly(False)
            self.yaml_edit_button.hide()
            self.yaml_save_button.show()
            self.yaml_cancel_button.show()
            
            # Don't change the font when toggling edit mode
            self.yaml_editor.setStyleSheet("""
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #0078d7;
                selection-background-color: #264F78;
                selection-color: #D4D4D4;
            """)
            
            self.original_yaml = self.yaml_editor.toPlainText()
        else:
            self.yaml_editor.setReadOnly(True)
            self.yaml_edit_button.show()
            self.yaml_save_button.hide()
            self.yaml_cancel_button.hide()
            
            # Reset to the basic style without changing the font
            self.yaml_editor.setStyleSheet("""
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                selection-background-color: #264F78;
                selection-color: #D4D4D4;
            """)
    
    def save_yaml_changes(self):
        yaml_text = self.yaml_editor.toPlainText()
        
        if yaml_text == self.original_yaml:
            self.toggle_yaml_edit_mode()
            return
        
        try:
            yaml_data = yaml.safe_load(yaml_text)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Invalid YAML",
                f"The YAML is not valid:\n\n{str(e)}"
            )
            return
        
        self.loading_indicator.show()
        self.loading_animation.start()
        
        try:
            import tempfile
            import os
            import subprocess
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w") as temp:
                temp.write(yaml_text)
                temp_path = temp.name
            
            cmd = ["kubectl", "apply", "-f", temp_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            os.unlink(temp_path)
            
            self.loading_indicator.hide()
            self.loading_animation.stop()
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Success",
                f"{self.resource_type}/{self.resource_name} updated successfully."
            )
            
            self.toggle_yaml_edit_mode()
            self.load_resource_details()
            
            self.resource_updated_signal.emit(
                self.resource_type,
                self.resource_name,
                self.resource_namespace or ""
            )
            
        except Exception as e:
            self.loading_indicator.hide()
            self.loading_animation.stop()
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update {self.resource_type}/{self.resource_name}:\n\n{str(e)}"
            )
    
    def cancel_yaml_edit(self):
        if self.original_yaml:
            self.yaml_editor.setPlainText(self.original_yaml)
        self.toggle_yaml_edit_mode()
    
    def clear_content(self):
        self.resource_name_label.setText("Resource Name")
        self.resource_info_label.setText("Type / Namespace")
        self.creation_time_label.setText("Created: unknown")
        self.status_value_label.setText("Unknown")
        self.status_text_label.setText("Status not available")
        
        for i in reversed(range(self.conditions_container_layout.count())):
            item = self.conditions_container_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        self.no_conditions_label = QLabel("No conditions available")
        self.no_conditions_label.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_NO_DATA_STYLE)
        self.conditions_container_layout.addWidget(self.no_conditions_label)
        
        self.labels_content.setText("No labels")
        
        for i in reversed(range(self.specific_layout.count())):
            item = self.specific_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        self.specific_section.hide()
        
        for i in reversed(range(self.details_layout.count())):
            item = self.details_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        self.yaml_editor.clear()
        self.original_yaml = None
        self.yaml_edited = False
        
        if not self.yaml_editor.isReadOnly():
            self.toggle_yaml_edit_mode()
        
        self.events_list.clear()
        self.current_data = None
    
    def load_resource_details(self):
        """Load detailed information about a specific resource with robust chart support"""
        if not self.resource_type or not self.resource_name:
            return
        
        try:
             # Special handling for event type
            if self.resource_type.lower() == "event":
                import subprocess
                import json
                
                # If we have raw event data, use it directly
                if hasattr(self, 'event_raw_data') and self.event_raw_data:
                    self.current_data = self.event_raw_data
                    self.update_ui_with_data()
                    self.loading_indicator.hide()
                    self.loading_animation.stop()
                    return
                
                # Otherwise, build a field selector to find the event
                cmd = ["kubectl", "get", "events"]
                
                if self.resource_namespace:
                    cmd.extend(["-n", self.resource_namespace])
                
                # For events, use field selectors to narrow down the search
                field_selectors = []
                if '/' in self.resource_name:
                    # If name has format "kind/name-reason", parse it
                    parts = self.resource_name.split('/', 1)
                    if len(parts) > 1:
                        kind, name_parts = parts
                        field_selectors.append(f"involvedObject.kind={kind}")
                        
                        # Further split name if it contains reason
                        if '-' in name_parts:
                            name, reason = name_parts.rsplit('-', 1)
                            field_selectors.append(f"involvedObject.name={name}")
                            field_selectors.append(f"reason={reason}")
                        else:
                            field_selectors.append(f"involvedObject.name={name_parts}")
                else:
                    # Try direct name match
                    field_selectors.append(f"metadata.name={self.resource_name}")
                
                if field_selectors:
                    cmd.extend(["--field-selector", ",".join(field_selectors)])
                
                cmd.extend(["-o", "json"])
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10
                )
                
                events_data = json.loads(result.stdout)
                if "items" in events_data and events_data["items"]:
                    # Use the first matching event
                    self.current_data = events_data["items"][0]
                else:
                    self.current_data = {}
                
                self.update_ui_with_data()
                self.loading_indicator.hide()
                self.loading_animation.stop()
                return
            # Special handling for Helm releases
            if self.resource_type == "helmrelease":
                import subprocess
                import json
                import platform
                import os
                import shutil
                
                # Find the helm binary
                helm_exe = "helm.exe" if platform.system() == "Windows" else "helm"
                helm_path = shutil.which(helm_exe)
                
                # Check common installation locations if not found in PATH
                if not helm_path:
                    common_paths = []
                    if platform.system() == "Windows":
                        common_paths = [
                            os.path.expanduser("~\\helm\\helm.exe"),
                            "C:\\Program Files\\Helm\\helm.exe",
                            "C:\\helm\\helm.exe",
                            os.path.expanduser("~\\.windows-package-manager\\helm\\helm.exe"),
                            os.path.expanduser("~\\AppData\\Local\\Programs\\Helm\\helm.exe")
                        ]
                    else:
                        common_paths = [
                            "/usr/local/bin/helm",
                            "/usr/bin/helm",
                            os.path.expanduser("~/bin/helm"),
                            "/opt/homebrew/bin/helm"  # Common on macOS with Homebrew
                        ]
                    
                    for path in common_paths:
                        if os.path.isfile(path):
                            helm_path = path
                            break
                
                if not helm_path:
                    raise Exception("Helm executable not found. Please install Helm to view release details.")
                
                # Build the command to get release details
                cmd = [
                    helm_path, "status", 
                    self.resource_name, 
                    "-o", "json"
                ]
                
                if self.resource_namespace:
                    cmd.extend(["-n", self.resource_namespace])
                    
                # Execute the command with increased timeout
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=15  # Increased timeout for slow clusters
                )
                
                # Parse the JSON response
                release_data = json.loads(result.stdout)
                
                # Additional command to get values
                values_cmd = [
                    helm_path, "get", "values",
                    self.resource_name,
                    "-o", "json"
                ]
                
                if self.resource_namespace:
                    values_cmd.extend(["-n", self.resource_namespace])
                    
                try:
                    values_result = subprocess.run(
                        values_cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=10
                    )
                    
                    # Add values to the data
                    values_data = json.loads(values_result.stdout)
                    release_data["values"] = values_data
                except Exception as values_err:
                    
                    release_data["values"] = {}
                
                # Format the data in Kubernetes-like structure
                # This makes it compatible with the rest of the UI
                self.current_data = {
                    "kind": "HelmRelease",
                    "apiVersion": "helm.sh/v1",
                    "metadata": {
                        "name": self.resource_name,
                        "namespace": self.resource_namespace or "default",
                        "creationTimestamp": release_data.get("info", {}).get("first_deployed", ""),
                        "annotations": {
                            "description": release_data.get("info", {}).get("description", ""),
                            "last_deployed": release_data.get("info", {}).get("last_deployed", "")
                        },
                        "labels": {}
                    },
                    "spec": {
                        "chart": release_data.get("chart", {}).get("metadata", {}).get("name", ""),
                        "version": release_data.get("chart", {}).get("metadata", {}).get("version", ""),
                        "values": release_data.get("values", {})
                    },
                    "status": {
                        "status": release_data.get("info", {}).get("status", ""),
                        "revision": release_data.get("version", 0),
                        "app_version": release_data.get("chart", {}).get("metadata", {}).get("appVersion", ""),
                        "last_deployed": release_data.get("info", {}).get("last_deployed", "")
                    },
                    # Store the original data for YAML view
                    "helmOutput": json.dumps(release_data, indent=2)
                }
                
                self.update_ui_with_data()
                self.loading_indicator.hide()
                self.loading_animation.stop()
                return
                
            elif self.resource_type == "chart":
                import json
                
                # Create a basic chart structure with the available information
                # This ensures we have something to display even if file access fails
                fallback_data = {
                    "kind": "HelmChart",
                    "apiVersion": "helm.sh/v1",
                    "metadata": {
                        "name": self.resource_name,
                        "namespace": self.resource_namespace,
                        "annotations": {
                            "description": f"Chart details for {self.resource_name}"
                        },
                        "labels": {}
                    },
                    "spec": {
                        "version": "Unknown",
                        "appVersion": "Unknown",
                        "repository": "Unknown"
                    },
                    "status": {
                        "phase": "Available"
                    }
                }
                
                # Try different methods to get chart data
                
                # Method 1: Try global variable from ChartsPage
                try:
                    if 'current_chart_data' in globals() and globals()['current_chart_data']:
                        chart_data = json.loads(globals()['current_chart_data'])
                        if chart_data.get("metadata", {}).get("name") == self.resource_name:
                            self.current_data = chart_data
                            self.update_ui_with_data()
                            self.loading_indicator.hide()
                            self.loading_animation.stop()
                            return
                except (json.JSONDecodeError, Exception) as e:
                    pass
                
                # Method 2: Try to get the chart info from the resources list
                try:
                    from PyQt6.QtWidgets import QApplication
                    for widget in QApplication.allWidgets():
                        if hasattr(widget, 'resources') and isinstance(widget.resources, list):
                            for chart in widget.resources:
                                if isinstance(chart, dict) and chart.get("name") == self.resource_name:
                                    # Found matching chart data, create a structured object
                                    chart_data = {
                                        "kind": "HelmChart",
                                        "apiVersion": "helm.sh/v1",
                                        "metadata": {
                                            "name": chart.get("name", self.resource_name),
                                            "creationTimestamp": chart.get("last_updated", ""),
                                            "annotations": {
                                                "description": chart.get("description", "No description available"),
                                                "repository_url": chart.get("repository_url", ""),
                                                "source": "ArtifactHub"
                                            },
                                            "labels": {
                                                "repository": chart.get("repository", "Unknown"),
                                                "version": chart.get("version", ""),
                                                "appVersion": chart.get("app_version", "")
                                            }
                                        },
                                        "spec": {
                                            "version": chart.get("version", "Unknown"),
                                            "appVersion": chart.get("app_version", "Unknown"),
                                            "repository": chart.get("repository", "Unknown")
                                        },
                                        "status": {
                                            "phase": "Available"
                                        }
                                    }
                                    
                                    # Add icon data if available, but check if it exists to avoid WinError 2
                                    icon_path = chart.get("icon_path")
                                    if icon_path and isinstance(icon_path, str):
                                        import os
                                        if os.path.exists(icon_path):
                                            chart_data["metadata"]["annotations"]["icon_path"] = icon_path
                                    
                                    self.current_data = chart_data
                                    self.update_ui_with_data()
                                    self.loading_indicator.hide()
                                    self.loading_animation.stop()
                                    return
                except Exception as e:
                    pass
                
                # Method 3: Try using helm command
                try:
                    import subprocess
                    import os
                    
                    # Check if helm is installed and available
                    try:
                        # Use a simple command that should work on both Windows and Unix
                        subprocess.run(
                            ["helm", "version", "--short"],
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=5
                        )
                        
                        # Now try to get chart info
                        cmd = ["helm", "list", "--filter", self.resource_name, "--output", "json"]
                        if self.resource_namespace:
                            cmd.extend(["-n", self.resource_namespace])
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=10
                        )
                        
                        chart_list = json.loads(result.stdout)
                        if chart_list and len(chart_list) > 0:
                            chart_info = chart_list[0]
                            
                            # Create structured data from helm output
                            chart_data = {
                                "kind": "HelmChart",
                                "apiVersion": "helm.sh/v1",
                                "metadata": {
                                    "name": chart_info.get("name", self.resource_name),
                                    "namespace": chart_info.get("namespace", self.resource_namespace),
                                    "creationTimestamp": chart_info.get("updated", ""),
                                    "annotations": {
                                        "description": f"Helm release: {self.resource_name}",
                                        "status": chart_info.get("status", "unknown"),
                                        "source": "Helm"
                                    },
                                    "labels": {}
                                },
                                "spec": {
                                    "version": chart_info.get("chart", "").split("-")[-1] if chart_info.get("chart", "") else "Unknown",
                                    "appVersion": chart_info.get("app_version", "Unknown"),
                                    "repository": chart_info.get("chart", "").split("-")[0] if chart_info.get("chart", "") else "Unknown"
                                },
                                "status": {
                                    "phase": chart_info.get("status", "Unknown")
                                },
                                "helmData": chart_info
                            }
                            
                            self.current_data = chart_data
                            self.update_ui_with_data()
                            self.loading_indicator.hide()
                            self.loading_animation.stop()
                            return
                    except (subprocess.SubprocessError, json.JSONDecodeError, Exception) as e:
                        pass
                except Exception as e:
                    pass
                    
                # Fallback: Use basic chart information we created
                pass
                self.current_data = fallback_data
                self.update_ui_with_data()
                self.loading_indicator.hide()
                self.loading_animation.stop()
                return
                
            # Standard behavior for other Kubernetes resources using kubectl
            import subprocess
            import json
            
            cmd = ["kubectl", "get", self.resource_type, self.resource_name]
            if self.resource_namespace:
                cmd.extend(["-n", self.resource_namespace])
            cmd.extend(["-o", "json"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            
            self.current_data = json.loads(result.stdout)
            self.update_ui_with_data()
            self.loading_indicator.hide()
            self.loading_animation.stop()
            
        except Exception as e:
            self.loading_indicator.hide()
            self.loading_animation.stop()
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load details for {self.resource_type}/{self.resource_name}:\n\n{str(e)}"
            )
    
    # Add a method to enhance the update_overview_tab method to handle helm charts
    def update_overview_tab(self):
        """Update the overview tab with resource-specific data and helm chart support"""
        metadata = self.current_data.get("metadata", {})
        
        self.resource_name_label.setText(metadata.get("name", "Unnamed"))
        
        resource_info = f"{self.resource_type.capitalize()}"
        if "namespace" in metadata:
            resource_info += f" / {metadata.get('namespace')}"
        self.resource_info_label.setText(resource_info)
        
        creation_timestamp = metadata.get("creationTimestamp", "")
        if creation_timestamp:
            import datetime
            from dateutil import parser
            try:
                creation_time = parser.parse(creation_timestamp)
                formatted_time = creation_time.strftime("%Y-%m-%d %H:%M:%S")
                self.creation_time_label.setText(f"Created: {formatted_time}")
            except Exception:
                self.creation_time_label.setText("Created: unknown")
        
        # Special handling for helm charts
        if self.resource_type == "chart":
            self.add_helm_chart_fields()
        else:
            self.update_resource_status()
            self.update_conditions()
            self.update_labels()
            self.add_resource_specific_fields()

    # Add a new method for Helm chart-specific fields
    def add_helm_chart_fields(self):
        """Add Helm chart specific fields to the overview tab with robust error handling"""
        # Clear existing status indicators first
        for i in reversed(range(self.conditions_container_layout.count())):
            item = self.conditions_container_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear specific section and prepare it for chart data
        for i in reversed(range(self.specific_layout.count())):
            item = self.specific_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Set a fixed status for charts
        self.status_value_label.setText("Available")
        self.status_value_label.setStyleSheet("""
            background-color: rgba(76, 175, 80, 0.1);
            color: #4CAF50;
            border-radius: 4px;
            padding: 2px 8px;
            font-weight: bold;
        """)
        self.status_text_label.setText("Chart is available")
        
        # Get chart metadata
        annotations = self.current_data.get("metadata", {}).get("annotations", {})
        labels = self.current_data.get("metadata", {}).get("labels", {})
        spec = self.current_data.get("spec", {})
        
        # Add chart version info if available
        no_conditions_label = QLabel("No chart conditions available")
        no_conditions_label.setStyleSheet("""
            color: #888888;
            font-style: italic;
            padding: 5px;
        """)
        self.conditions_container_layout.addWidget(no_conditions_label)
        
        # Set up the specific section for chart details
        section_header = QLabel("CHART DETAILS")
        section_header.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #aaaaaa;
            text-transform: uppercase;
            margin-top: 10px;
        """)
        self.specific_layout.addWidget(section_header)
        
        # Add version info from either spec or labels (support both structures)
        version = spec.get("version") or labels.get("version") or "Unknown"
        version_info = QLabel(f"Chart Version: {version}")
        version_info.setStyleSheet("""
            font-size: 13px;
            color: #ffffff;
            margin-top: 5px;
        """)
        self.specific_layout.addWidget(version_info)
        
        app_version = spec.get("appVersion") or labels.get("appVersion") or "Unknown"
        app_version_info = QLabel(f"App Version: {app_version}")
        app_version_info.setStyleSheet("""
            font-size: 13px;
            color: #ffffff;
            margin-top: 5px;
        """)
        self.specific_layout.addWidget(app_version_info)
        
        # Add description if available
        description = annotations.get("description", "No description available")
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #aaaaaa;
            margin-top: 10px;
        """)
        self.specific_layout.addWidget(desc_label)
        
        desc_text = QLabel(description)
        desc_text.setWordWrap(True)
        desc_text.setStyleSheet("""
            font-size: 13px;
            color: #ffffff;
            margin-top: 2px;
            margin-left: 10px;
        """)
        self.specific_layout.addWidget(desc_text)
        
        # Add repository info
        repository = spec.get("repository") or labels.get("repository") or "Unknown"
        repo_label = QLabel("Repository:")
        repo_label.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #aaaaaa;
            margin-top: 10px;
        """)
        self.specific_layout.addWidget(repo_label)
        
        repo_text = QLabel(repository)
        repo_text.setWordWrap(True)
        repo_text.setStyleSheet("""
            font-size: 13px;
            color: #ffffff;
            margin-top: 2px;
            margin-left: 10px;
        """)
        self.specific_layout.addWidget(repo_text)
        
        # Add source information
        source = annotations.get("source", "Unknown")
        source_label = QLabel("Source:")
        source_label.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #aaaaaa;
            margin-top: 10px;
        """)
        self.specific_layout.addWidget(source_label)
        
        source_text = QLabel(source)
        source_text.setStyleSheet("""
            font-size: 13px;
            color: #ffffff;
            margin-top: 2px;
            margin-left: 10px;
        """)
        self.specific_layout.addWidget(source_text)
        
        # Add icon if available - with robust error handling
        try:
            icon_path = annotations.get("icon_path")
            if icon_path:
                import os
                if os.path.exists(icon_path):  # Check that file exists first
                    from PyQt6.QtGui import QPixmap
                    from PyQt6.QtWidgets import QLabel
                    
                    icon_label = QLabel("Icon:")
                    icon_label.setStyleSheet("""
                        font-size: 13px;
                        font-weight: bold;
                        color: #aaaaaa;
                        margin-top: 10px;
                    """)
                    self.specific_layout.addWidget(icon_label)
                    
                    icon_widget = QLabel()
                    pixmap = QPixmap(icon_path)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        icon_widget.setPixmap(pixmap)
                        icon_widget.setStyleSheet("""
                            margin-left: 10px;
                            margin-top: 5px;
                        """)
                        self.specific_layout.addWidget(icon_widget)
        except Exception as e:
            # Just skip icon display on error
            pass
        
        # Show the specific section
        self.specific_section.show()
        
        # Update the labels section
        chart_labels = self.current_data.get("metadata", {}).get("labels", {})
        if chart_labels:
            labels_text = "\n".join([f"{k}={v}" for k, v in chart_labels.items()])
            self.labels_content.setText(labels_text)
        else:
            self.labels_content.setText("No labels")
    def update_ui_with_data(self):
        if not self.current_data:
            return
        
        self.update_overview_tab()
        self.update_details_tab()
        
        if self.tab_widget.currentIndex() == 2:
            self.update_yaml_tab()
        if self.tab_widget.currentIndex() == 3:
            self.load_events()
    
    def update_overview_tab(self):
        metadata = self.current_data.get("metadata", {})
        
        self.resource_name_label.setText(metadata.get("name", "Unnamed"))
        
        resource_info = f"{self.resource_type.capitalize()}"
        if "namespace" in metadata:
            resource_info += f" / {metadata.get('namespace')}"
        self.resource_info_label.setText(resource_info)
        
        creation_timestamp = metadata.get("creationTimestamp", "")
        if creation_timestamp:
            import datetime
            from dateutil import parser
            try:
                creation_time = parser.parse(creation_timestamp)
                formatted_time = creation_time.strftime("%Y-%m-%d %H:%M:%S")
                self.creation_time_label.setText(f"Created: {formatted_time}")
            except Exception:
                self.creation_time_label.setText("Created: unknown")
        
        self.update_resource_status()
        self.update_conditions()
        self.update_labels()
        self.add_resource_specific_fields()
    
    def update_resource_status(self):
        status = self.current_data.get("status", {})
        status_value = "Unknown"
        status_text = "Status not available"

        # Special case for Helm releases
        if self.resource_type == "helmrelease":
            # Check if status is directly in the status field
            if isinstance(status, dict) and "status" in status:
                status_value = status.get("status", "Unknown")
                
                # Map status to text
                if status_value.lower() == "deployed":
                    status_text = "Release is successfully deployed"
                elif status_value.lower() == "failed":
                    status_text = "Release deployment failed"
                elif status_value.lower() == "pending":
                    status_text = "Release is being deployed"
                elif status_value.lower() == "superseded":
                    status_text = "Release has been upgraded or replaced"
                elif status_value.lower() == "uninstalled":
                    status_text = "Release has been uninstalled but retained"
                elif status_value.lower() == "uninstalling":
                    status_text = "Release is being uninstalled"
                else:
                    status_text = f"Release status: {status_value}"
            
            # For helmOutput, parse the JSON and look for status
            elif "helmOutput" in self.current_data:
                try:
                    import json
                    helm_data = json.loads(self.current_data["helmOutput"])
                    info = helm_data.get("info", {})
                    status_value = info.get("status", "Unknown")
                    status_text = f"Release status: {status_value}"
                    
                    # Same mapping as above
                    if status_value.lower() == "deployed":
                        status_text = "Release is successfully deployed"
                    elif status_value.lower() == "failed":
                        status_text = "Release deployment failed"
                    elif status_value.lower() == "pending":
                        status_text = "Release is being deployed"
                    elif status_value.lower() == "superseded":
                        status_text = "Release has been upgraded or replaced"
                    elif status_value.lower() == "uninstalled":
                        status_text = "Release has been uninstalled but retained"
                    elif status_value.lower() == "uninstalling":
                        status_text = "Release is being uninstalled"
                except:
                    pass
        
        # For pods (unchanged existing code)
        elif self.resource_type == "pods":
            phase = status.get("phase", "Unknown")
            status_value = phase
            
            container_statuses = status.get("containerStatuses", [])
            for container in container_statuses:
                state = container.get("state", {})
                if "waiting" in state and state["waiting"].get("reason") in (
                        "CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                    status_value = state["waiting"]["reason"]
                    status_text = state["waiting"].get("message", "Container issue detected")
                    break
                if "terminated" in state and state["terminated"].get("exitCode", 0) != 0:
                    status_value = "Error"
                    status_text = state["terminated"].get("message", "Container terminated with error")
                    break
            
            if status_value == "Pending":
                for condition in status.get("conditions", []):
                    if condition.get("status") != "True" and condition.get("reason"):
                        status_text = condition.get("message", "Pending: waiting for resources")
                        break
                else:
                    status_text = "Pending: waiting to be scheduled"
            elif status_value == "Running":
                status_text = "Pod is running"
            elif status_value == "Succeeded":
                status_text = "Pod has completed successfully"
            elif status_value == "Failed":
                status_text = "Pod has failed"
        
        # Rest of the original method stays the same for other resource types
        elif self.resource_type == "deployments":
            available_replicas = status.get("availableReplicas", 0)
            replicas = status.get("replicas", 0)
            updated_replicas = status.get("updatedReplicas", 0)
            
            if available_replicas == replicas and replicas > 0:
                status_value = "Available"
                status_text = f"Deployment is available ({available_replicas}/{replicas} replicas)"
            elif updated_replicas < replicas:
                status_value = "Updating"
                status_text = f"Deployment is updating ({updated_replicas}/{replicas} replicas updated)"
            elif available_replicas < replicas:
                status_value = "Progressing"
                status_text = f"Deployment is progressing ({available_replicas}/{replicas} replicas available)"
            else:
                status_value = "Unknown"
                status_text = "Unable to determine deployment status"
        
        elif self.resource_type == "services":
            service_type = self.current_data.get("spec", {}).get("type", "ClusterIP")
            
            if service_type == "LoadBalancer":
                ingress = status.get("loadBalancer", {}).get("ingress", [])
                if ingress:
                    status_value = "Active"
                    status_text = "Load balancer is provisioned"
                else:
                    status_value = "Pending"
                    status_text = "Waiting for load balancer to be provisioned"
            else:
                status_value = "Active"
                status_text = f"{service_type} service is available"
        
        elif self.resource_type == "persistentvolumes" or self.resource_type == "persistentvolumeclaims":
            phase = status.get("phase", "Unknown")
            status_value = phase
            
            if phase == "Bound":
                status_text = "Volume is bound"
            elif phase == "Available":
                status_text = "Volume is available"
            elif phase == "Released":
                status_text = "Volume is released but not yet available"
            elif phase == "Failed":
                status_text = "Volume binding failed"
            elif phase == "Pending":
                status_text = "Volume is pending binding"
            else:
                status_text = "Unknown volume status"
        
        elif self.resource_type == "nodes":
            for condition in status.get("conditions", []):
                if condition.get("type") == "Ready":
                    if condition.get("status") == "True":
                        status_value = "Ready"
                        status_text = "Node is ready"
                    else:
                        status_value = "NotReady"
                        status_text = condition.get("message", "Node is not ready")
                    break
            else:
                status_value = "Unknown"
                status_text = "Unable to determine node status"
        
        elif self.resource_type == "namespaces":
            phase = status.get("phase", "Unknown")
            status_value = phase
            
            if phase == "Active":
                status_text = "Namespace is active"
            elif phase == "Terminating":
                status_text = "Namespace is being terminated"
            else:
                status_text = "Unknown namespace status"
        
        else:
            if "readyReplicas" in status and "replicas" in status:
                ready = status.get("readyReplicas", 0)
                total = status.get("replicas", 0)
                
                if ready == total and total > 0:
                    status_value = "Ready"
                    status_text = f"Ready ({ready}/{total} replicas)"
                elif ready < total:
                    status_value = "Progressing"
                    status_text = f"Progressing ({ready}/{total} replicas ready)"
                else:
                    status_value = "Unknown"
                    status_text = "Unable to determine status"
            elif "availableReplicas" in status:
                available = status.get("availableReplicas", 0)
                if available > 0:
                    status_value = "Available"
                    status_text = f"Available ({available} replicas)"
                else:
                    status_value = "Unavailable"
                    status_text = "No replicas available"
            elif "phase" in status:
                status_value = status["phase"]
                status_text = f"Status: {status_value}"
            elif "conditions" in status and status["conditions"]:
                latest_condition = status["conditions"][-1]
                status_value = latest_condition.get("type", "Unknown")
                status_text = latest_condition.get("message", "No status message")
        
        self.status_value_label.setText(status_value)
        self.status_text_label.setText(status_text)
        
        # Set style based on status value
        if status_value.lower() in ["running", "ready", "active", "available", "bound", "succeeded", "deployed"]:
            self.status_value_label.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_RUNNING_STYLE)
        elif status_value.lower() in ["pending", "progressing", "updating", "released", "superseded"]:
            self.status_value_label.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_PENDING_STYLE)
        elif status_value.lower() in ["succeeded", "completed", "complete"]:
            self.status_value_label.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_SUCCEEDED_STYLE)
        else:
            self.status_value_label.setStyleSheet(AppStyles.DETAIL_PAGE_STATUS_VALUE_FAILED_STYLE)
            
    def update_conditions(self):
        for i in reversed(range(self.conditions_container_layout.count())):
            item = self.conditions_container_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        status = self.current_data.get("status", {})
        conditions = status.get("conditions", [])
        
        if not conditions:
            self.no_conditions_label = QLabel("No conditions available")
            self.no_conditions_label.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_NO_DATA_STYLE)
            self.conditions_container_layout.addWidget(self.no_conditions_label)
            return
        
        for condition in conditions:
            condition_type = condition.get("type", "Unknown")
            condition_status = condition.get("status", "Unknown")
            condition_message = condition.get("message", "")
            
            condition_widget = QWidget()
            condition_layout = QHBoxLayout(condition_widget)
            condition_layout.setContentsMargins(0, 0, 0, 0)
            condition_layout.setSpacing(5)
            
            type_label = QLabel(condition_type)
            type_label.setFixedWidth(AppStyles.DETAIL_PAGE_CONDITION_TYPE_WIDTH)
            type_label.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_TYPE_STYLE)
            
            status_label = QLabel(condition_status)
            status_label.setFixedWidth(AppStyles.DETAIL_PAGE_CONDITION_STATUS_WIDTH)
            if condition_status == "True":
                status_label.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_STATUS_TRUE_STYLE)
            else:
                status_label.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_STATUS_FALSE_STYLE)
            
            message_label = QLabel(condition_message)
            message_label.setStyleSheet(AppStyles.DETAIL_PAGE_CONDITION_MESSAGE_STYLE)
            message_label.setWordWrap(True)
            
            condition_layout.addWidget(type_label)
            condition_layout.addWidget(status_label)
            condition_layout.addWidget(message_label, 1)
            
            self.conditions_container_layout.addWidget(condition_widget)
    
    def update_labels(self):
        metadata = self.current_data.get("metadata", {})
        labels = metadata.get("labels", {})
        
        if not labels:
            self.labels_content.setText("No labels")
            return
        
        labels_text = "\n".join([f"{k}={v}" for k, v in labels.items()])
        self.labels_content.setText(labels_text)
    
    def add_resource_specific_fields(self):
        for i in reversed(range(self.specific_layout.count())):
            item = self.specific_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        if self.resource_type == "pods":
            self.add_pod_specific_fields()
        elif self.resource_type == "services":
            self.add_service_specific_fields()
        elif self.resource_type == "deployments":
            self.add_deployment_specific_fields()
        elif self.resource_type == "persistentvolumes" or self.resource_type == "persistentvolumeclaims":
            self.add_volume_specific_fields()
        elif self.resource_type == "nodes":
            self.add_node_specific_fields()
        elif self.resource_type == "configmaps":
            self.add_configmap_specific_fields()
        elif self.resource_type == "secrets":
            self.add_secret_specific_fields()
        else:
            self.specific_section.hide()
            return
        
        self.specific_section.show()
    
    def add_pod_specific_fields(self):
        spec = self.current_data.get("spec", {})
        status = self.current_data.get("status", {})
        
        section_header = QLabel("POD DETAILS")
        section_header.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        self.specific_layout.addWidget(section_header)
        
        containers = spec.get("containers", [])
        init_containers = spec.get("initContainers", [])
        
        container_info = QLabel(f"Containers: {len(containers)}")
        container_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
        self.specific_layout.addWidget(container_info)
        
        if init_containers:
            init_container_info = QLabel(f"Init Containers: {len(init_containers)}")
            init_container_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(init_container_info)
        
        node_name = spec.get("nodeName", "")
        if node_name:
            node_info = QLabel(f"Node: {node_name}")
            node_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(node_info)
        
        pod_ip = status.get("podIP", "")
        if pod_ip:
            ip_info = QLabel(f"Pod IP: {pod_ip}")
            ip_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(ip_info)
        
        qos_class = status.get("qosClass", "")
        if qos_class:
            qos_info = QLabel(f"QoS Class: {qos_class}")
            qos_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(qos_info)
    
    def add_service_specific_fields(self):
        spec = self.current_data.get("spec", {})
        status = self.current_data.get("status", {})
        
        section_header = QLabel("SERVICE DETAILS")
        section_header.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        self.specific_layout.addWidget(section_header)
        
        service_type = spec.get("type", "ClusterIP")
        type_info = QLabel(f"Type: {service_type}")
        type_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
        self.specific_layout.addWidget(type_info)
        
        cluster_ip = spec.get("clusterIP", "")
        if cluster_ip:
            ip_info = QLabel(f"Cluster IP: {cluster_ip}")
            ip_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(ip_info)
        
        external_ips = spec.get("externalIPs", [])
        if external_ips:
            ext_ip_info = QLabel(f"External IPs: {', '.join(external_ips)}")
            ext_ip_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(ext_ip_info)
        
        lb_ingress = status.get("loadBalancer", {}).get("ingress", [])
        if lb_ingress:
            lb_ips = []
            for ing in lb_ingress:
                if "ip" in ing:
                    lb_ips.append(ing["ip"])
                elif "hostname" in ing:
                    lb_ips.append(ing["hostname"])
            
            if lb_ips:
                lb_info = QLabel(f"Load Balancer: {', '.join(lb_ips)}")
                lb_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                self.specific_layout.addWidget(lb_info)
        
        ports = spec.get("ports", [])
        if ports:
            port_lines = []
            for port in ports:
                port_str = f"{port.get('port')}/{port.get('protocol', 'TCP')}"
                if 'targetPort' in port:
                    port_str += f" -> {port.get('targetPort')}"
                if 'nodePort' in port and service_type in ["NodePort", "LoadBalancer"]:
                    port_str += f" (NodePort: {port.get('nodePort')})"
                port_lines.append(port_str)
            
            ports_info = QLabel(f"Ports: {', '.join(port_lines)}")
            ports_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            ports_info.setWordWrap(True)
            self.specific_layout.addWidget(ports_info)
        
        selector = spec.get("selector", {})
        if selector:
            selector_text = ", ".join([f"{k}={v}" for k, v in selector.items()])
            selector_info = QLabel(f"Selector: {selector_text}")
            selector_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            selector_info.setWordWrap(True)
            self.specific_layout.addWidget(selector_info)
    
    def add_deployment_specific_fields(self):
        spec = self.current_data.get("spec", {})
        status = self.current_data.get("status", {})
        
        section_header = QLabel("DEPLOYMENT DETAILS")
        section_header.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        self.specific_layout.addWidget(section_header)
        
        replicas = spec.get("replicas", 0)
        replicas_info = QLabel(f"Desired Replicas: {replicas}")
        replicas_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
        self.specific_layout.addWidget(replicas_info)
        
        current_replicas = status.get("replicas", 0)
        current_info = QLabel(f"Current Replicas: {current_replicas}")
        current_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
        self.specific_layout.addWidget(current_info)
        
        ready_replicas = status.get("readyReplicas", 0)
        ready_info = QLabel(f"Ready Replicas: {ready_replicas}")
        ready_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
        self.specific_layout.addWidget(ready_info)
        
        strategy = spec.get("strategy", {}).get("type", "RollingUpdate")
        strategy_info = QLabel(f"Update Strategy: {strategy}")
        strategy_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
        self.specific_layout.addWidget(strategy_info)
        
        selector = spec.get("selector", {}).get("matchLabels", {})
        if selector:
            selector_text = ", ".join([f"{k}={v}" for k, v in selector.items()])
            selector_info = QLabel(f"Selector: {selector_text}")
            selector_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            selector_info.setWordWrap(True)
            self.specific_layout.addWidget(selector_info)
    
    def add_volume_specific_fields(self):
        spec = self.current_data.get("spec", {})
        
        if self.resource_type == "persistentvolumes":
            section_header = QLabel("PERSISTENT VOLUME DETAILS")
        else:
            section_header = QLabel("PERSISTENT VOLUME CLAIM DETAILS")
        section_header.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        self.specific_layout.addWidget(section_header)
        
        capacity = spec.get("capacity", {}).get("storage", "")
        if capacity:
            capacity_info = QLabel(f"Capacity: {capacity}")
            capacity_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(capacity_info)
        
        storage_class = spec.get("storageClassName", "")
        if storage_class:
            sc_info = QLabel(f"Storage Class: {storage_class}")
            sc_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(sc_info)
        
        access_modes = spec.get("accessModes", [])
        if access_modes:
            modes_info = QLabel(f"Access Modes: {', '.join(access_modes)}")
            modes_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(modes_info)
        
        volume_mode = spec.get("volumeMode", "")
        if volume_mode:
            mode_info = QLabel(f"Volume Mode: {volume_mode}")
            mode_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(mode_info)
        
        if self.resource_type == "persistentvolumes":
            persistent_volume_source = None
            for source_type in [
                "hostPath", "nfs", "awsElasticBlockStore", "gcePersistentDisk",
                "azureDisk", "csi", "fc", "iscsi", "cephfs"
            ]:
                if source_type in spec:
                    persistent_volume_source = source_type
                    break
            
            if persistent_volume_source:
                source_info = QLabel(f"Volume Source: {persistent_volume_source}")
                source_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                self.specific_layout.addWidget(source_info)
            
            reclaim_policy = spec.get("persistentVolumeReclaimPolicy", "")
            if reclaim_policy:
                policy_info = QLabel(f"Reclaim Policy: {reclaim_policy}")
                policy_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                self.specific_layout.addWidget(policy_info)
            
            claim_ref = spec.get("claimRef", {})
            if claim_ref:
                claim_name = claim_ref.get("name", "")
                claim_namespace = claim_ref.get("namespace", "")
                if claim_name:
                    claim_info = QLabel(f"Bound to: {claim_namespace}/{claim_name}")
                    claim_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                    self.specific_layout.addWidget(claim_info)
        
        elif self.resource_type == "persistentvolumeclaims":
            volume_name = spec.get("volumeName", "")
            if volume_name:
                volume_info = QLabel(f"Volume: {volume_name}")
                volume_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                self.specific_layout.addWidget(volume_info)
            
            resources = spec.get("resources", {})
            requests = resources.get("requests", {})
            storage_request = requests.get("storage", "")
            if storage_request:
                request_info = QLabel(f"Requested Storage: {storage_request}")
                request_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                self.specific_layout.addWidget(request_info)
    
    def add_node_specific_fields(self):
        status = self.current_data.get("status", {})
        
        section_header = QLabel("NODE DETAILS")
        section_header.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        self.specific_layout.addWidget(section_header)
        
        node_info = status.get("nodeInfo", {})
        
        os_image = node_info.get("osImage", "")
        architecture = node_info.get("architecture", "")
        if os_image and architecture:
            os_info = QLabel(f"OS: {os_image} ({architecture})")
            os_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(os_info)
        
        kernel_version = node_info.get("kernelVersion", "")
        if kernel_version:
            kernel_info = QLabel(f"Kernel Version: {kernel_version}")
            kernel_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(kernel_info)
        
        container_runtime = node_info.get("containerRuntimeVersion", "")
        if container_runtime:
            runtime_info = QLabel(f"Container Runtime: {container_runtime}")
            runtime_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(runtime_info)
        
        kubelet_version = node_info.get("kubeletVersion", "")
        if kubelet_version:
            kubelet_info = QLabel(f"Kubelet Version: {kubelet_version}")
            kubelet_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            self.specific_layout.addWidget(kubelet_info)
        
        capacity = status.get("capacity", {})
        if capacity:
            cpu = capacity.get("cpu", "")
            memory = capacity.get("memory", "")
            pods = capacity.get("pods", "")
            
            if cpu:
                cpu_info = QLabel(f"CPU Capacity: {cpu}")
                cpu_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                self.specific_layout.addWidget(cpu_info)
            
            if memory:
                memory_info = QLabel(f"Memory Capacity: {memory}")
                memory_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                self.specific_layout.addWidget(memory_info)
            
            if pods:
                pods_info = QLabel(f"Pod Capacity: {pods}")
                pods_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                self.specific_layout.addWidget(pods_info)
        
        addresses = status.get("addresses", [])
        if addresses:
            address_lines = []
            for addr in addresses:
                addr_type = addr.get("type", "")
                addr_value = addr.get("address", "")
                if addr_type and addr_value:
                    address_lines.append(f"{addr_type}: {addr_value}")
            
            if address_lines:
                addr_info = QLabel("Addresses:\n" + "\n".join(address_lines))
                addr_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                addr_info.setWordWrap(True)
                self.specific_layout.addWidget(addr_info)
        
        taints = self.current_data.get("spec", {}).get("taints", [])
        if taints:
            taint_lines = []
            for taint in taints:
                key = taint.get("key", "")
                value = taint.get("value", "")
                effect = taint.get("effect", "")
                taint_lines.append(f"{key}={value}:{effect}")
            
            if taint_lines:
                taint_info = QLabel("Taints:\n" + "\n".join(taint_lines))
                taint_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                taint_info.setWordWrap(True)
                self.specific_layout.addWidget(taint_info)
    
    def add_configmap_specific_fields(self):
        data = self.current_data.get("data", {})
        binary_data = self.current_data.get("binaryData", {})
        
        section_header = QLabel("CONFIGMAP DETAILS")
        section_header.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        self.specific_layout.addWidget(section_header)
        
        if data:
            data_keys = list(data.keys())
            keys_info = QLabel(f"Data Keys: {', '.join(data_keys)}")
            keys_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            keys_info.setWordWrap(True)
            self.specific_layout.addWidget(keys_info)
            
            for key in data_keys[:3]:
                value = data[key]
                if len(value) > 100:
                    value = value[:100] + "..."
                
                value = value.replace("\n", " ").replace("\r", " ")
                
                preview = QLabel(f"{key}: {value}")
                preview.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                preview.setWordWrap(True)
                self.specific_layout.addWidget(preview)
            
            if len(data_keys) > 3:
                more_keys = QLabel(f"... and {len(data_keys) - 3} more keys")
                more_keys.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
                self.specific_layout.addWidget(more_keys)
        
        if binary_data:
            binary_keys = list(binary_data.keys())
            binary_info = QLabel(f"Binary Data Keys: {', '.join(binary_keys)}")
            binary_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            binary_info.setWordWrap(True)
            self.specific_layout.addWidget(binary_info)
    
    def add_secret_specific_fields(self):
        data = self.current_data.get("data", {})
        
        section_header = QLabel("SECRET DETAILS")
        section_header.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        self.specific_layout.addWidget(section_header)
        
        secret_type = self.current_data.get("type", "Opaque")
        type_info = QLabel(f"Type: {secret_type}")
        type_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
        self.specific_layout.addWidget(type_info)
        
        if data:
            data_keys = list(data.keys())
            keys_info = QLabel(f"Data Keys: {', '.join(data_keys)}")
            keys_info.setStyleSheet(AppStyles.DETAIL_PAGE_RESOURCE_INFO_STYLE)
            keys_info.setWordWrap(True)
            self.specific_layout.addWidget(keys_info)
    
    def update_details_tab(self):
        for i in reversed(range(self.details_layout.count())):
            item = self.details_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.current_data:
            return
        
        metadata_title = QLabel("METADATA")
        metadata_title.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
        self.details_layout.addWidget(metadata_title)
        
        metadata = self.current_data.get("metadata", {})
        
        metadata_fields = [
            ("Name", metadata.get("name", "")),
            ("Namespace", metadata.get("namespace", "")),
            ("UID", metadata.get("uid", "")),
            ("Creation Timestamp", metadata.get("creationTimestamp", "")),
            ("Resource Version", metadata.get("resourceVersion", ""))
        ]
        
        annotations = metadata.get("annotations", {})
        if annotations:
            annotations_text = "\n".join([f"{k}={v}" for k, v in annotations.items()])
            metadata_fields.append(("Annotations", annotations_text))
        
        finalizers = metadata.get("finalizers", [])
        if finalizers:
            metadata_fields.append(("Finalizers", ", ".join(finalizers)))
        
        for field_name, field_value in metadata_fields:
            if field_value:
                field_container = QWidget()
                field_layout = QHBoxLayout(field_container)
                field_layout.setContentsMargins(0, 0, 0, 0)
                
                name_label = QLabel(field_name + ":")
                name_label.setFixedWidth(150)
                name_label.setStyleSheet("font-weight: bold; color: #aaaaaa;")
                
                value_label = QLabel(str(field_value))
                value_label.setStyleSheet("color: #ffffff;")
                value_label.setWordWrap(True)
                
                field_layout.addWidget(name_label)
                field_layout.addWidget(value_label, 1)
                
                self.details_layout.addWidget(field_container)
        
        spec = self.current_data.get("spec", {})
        if spec:
            spec_title = QLabel("SPEC")
            spec_title.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
            self.details_layout.addWidget(spec_title)
            
            self.add_object_fields(spec, self.details_layout)
        
        status = self.current_data.get("status", {})
        if status:
            status_title = QLabel("STATUS")
            status_title.setStyleSheet(AppStyles.DETAIL_PAGE_SECTION_TITLE_STYLE)
            self.details_layout.addWidget(status_title)
            
            self.add_object_fields(status, self.details_layout)
    
    def add_object_fields(self, obj, parent_layout, prefix="", depth=0):
        if depth > 3:
            return
            
        for key, value in obj.items():
            field_name = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict) and value:
                field_title = QLabel(field_name.upper())
                field_title.setStyleSheet(f"""
                    font-weight: bold;
                    color: #aaaaaa;
                    margin-left: {depth * 10}px;
                """)
                parent_layout.addWidget(field_title)
                
                self.add_object_fields(value, parent_layout, field_name, depth + 1)
            
            elif isinstance(value, list) and value:
                if all(isinstance(item, dict) for item in value):
                    field_title = QLabel(field_name.upper())
                    field_title.setStyleSheet(f"""
                        font-weight: bold;
                        color: #aaaaaa;
                        margin-left: {depth * 10}px;
                    """)
                    parent_layout.addWidget(field_title)
                    
                    for i, item in enumerate(value[:5]):
                        item_title = QLabel(f"{field_name}[{i}]")
                        item_title.setStyleSheet(f"""
                            font-weight: normal;
                            color: #aaaaaa;
                            margin-left: {(depth + 1) * 10}px;
                        """)
                        parent_layout.addWidget(item_title)
                        
                        self.add_object_fields(item, parent_layout, "", depth + 2)
                    
                    if len(value) > 5:
                        more_items = QLabel(f"... and {len(value) - 5} more items")
                        more_items.setStyleSheet(f"""
                            color: #aaaaaa;
                            margin-left: {(depth + 1) * 10}px;
                        """)
                        parent_layout.addWidget(more_items)
                
                else:
                    field_container = QWidget()
                    field_layout = QHBoxLayout(field_container)
                    field_layout.setContentsMargins(0, 0, 0, 0)
                    
                    name_label = QLabel(field_name + ":")
                    name_label.setFixedWidth(150)
                    name_label.setStyleSheet(f"""
                        font-weight: bold; 
                        color: #aaaaaa;
                        margin-left: {depth * 10}px;
                    """)
                    
                    if all(isinstance(item, str) for item in value):
                        value_str = ", ".join(value)
                    else:
                        value_str = str(value)
                    
                    value_label = QLabel(value_str)
                    value_label.setStyleSheet("color: #ffffff;")
                    value_label.setWordWrap(True)
                    
                    field_layout.addWidget(name_label)
                    field_layout.addWidget(value_label, 1)
                    
                    parent_layout.addWidget(field_container)
            
            else:
                field_container = QWidget()
                field_layout = QHBoxLayout(field_container)
                field_layout.setContentsMargins(0, 0, 0, 0)
                
                name_label = QLabel(field_name + ":")
                name_label.setFixedWidth(150)
                name_label.setStyleSheet(f"""
                    font-weight: bold; 
                    color: #aaaaaa;
                    margin-left: {depth * 10}px;
                """)
                
                value_label = QLabel(str(value))
                value_label.setStyleSheet("color: #ffffff;")
                value_label.setWordWrap(True)
                
                field_layout.addWidget(name_label)
                field_layout.addWidget(value_label, 1)
                
                parent_layout.addWidget(field_container)
    
    def update_yaml_tab(self):
        """Update the YAML tab with resource data including helm charts"""
        if not self.current_data:
            return
        
        try:
            # Special handling for helm charts - check if helmOutput exists
            if "helmOutput" in self.current_data:
                # Display the raw helm output
                self.yaml_editor.setPlainText(self.current_data["helmOutput"])
                self.original_yaml = self.current_data["helmOutput"]
            else:
                # Normal YAML display for other resources
                import yaml
                yaml_text = yaml.dump(self.current_data, default_flow_style=False)
                self.yaml_editor.setPlainText(yaml_text)
                self.original_yaml = yaml_text
                
        except Exception as e:
            self.yaml_editor.setPlainText(f"Error rendering YAML: {str(e)}")
    
    def load_events(self):
        """Load events for the current resource with improved error handling"""
        if not self.resource_type or not self.resource_name:
            return
        
        self.events_list.clear()
        
        try:
            import subprocess
            import json
            import re
            
            # Sanitize resource name and namespace to prevent command injection
            resource_name = re.sub(r'[^\w\-\.]', '', self.resource_name)
            namespace = re.sub(r'[^\w\-\.]', '', self.resource_namespace) if self.resource_namespace else None
            
            # Map the resource type to a proper Kind for the field selector
            kind_mapping = {
                "pod": "Pod",
                "endpoint": "Endpoints",  # Note: singular resource_type but plural Kind
                "priorityclass": "PriorityClass",
                "deployment": "Deployment",
                "service": "Service",
                "node": "Node",
                # Add other mappings as needed
            }
            
            # Get the correct Kind for the field selector
            resource_type_singular = self.resource_type
            if resource_type_singular.endswith('s'):
                resource_type_singular = resource_type_singular[:-1]
                
            kind = kind_mapping.get(resource_type_singular, resource_type_singular.capitalize())
            
            # Build field selector carefully
            field_selector = f"involvedObject.name={resource_name},involvedObject.kind={kind}"
            
            cmd = ["kubectl", "get", "events", "--field-selector", field_selector]
            
            if namespace:
                cmd.extend(["-n", namespace])
            
            cmd.extend(["-o", "json"])
            
            # Increase timeout to prevent command timeout issues
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # Don't raise exceptions on non-zero exit
                timeout=15  # Increased timeout
            )
            
            # Check for errors
            if result.returncode != 0:
                error_item = QListWidgetItem(f"Error loading events: {result.stderr}")
                error_item.setForeground(QColor("#ff4d4f"))
                self.events_list.addItem(error_item)
                return
            
            events_data = json.loads(result.stdout)
            events = events_data.get("items", [])
            
            if not events:
                no_events_item = QListWidgetItem("No events found for this resource")
                no_events_item.setForeground(QColor("#8e9ba9"))
                self.events_list.addItem(no_events_item)
                return
            
            events.sort(key=lambda e: e.get("lastTimestamp", ""), reverse=True)
            
            for event in events:
                self.add_event_to_list(event)
                
        except json.JSONDecodeError:
            error_item = QListWidgetItem("Error: Invalid JSON response from Kubernetes API")
            error_item.setForeground(QColor("#ff4d4f"))
            self.events_list.addItem(error_item)
        except subprocess.TimeoutExpired:
            error_item = QListWidgetItem("Error: Command timed out while fetching events")
            error_item.setForeground(QColor("#ff4d4f"))
            self.events_list.addItem(error_item)
        except Exception as e:
            error_item = QListWidgetItem(f"Error loading events: {str(e)}")
            error_item.setForeground(QColor("#ff4d4f"))
            self.events_list.addItem(error_item)

    def add_event_to_list(self, event):
        event_widget = QWidget()
        event_widget.setStyleSheet("background-color: transparent;")
        
        layout = QVBoxLayout(event_widget)
        layout.setContentsMargins(
            AppStyles.DETAIL_PAGE_EVENT_ITEM_MARGIN,
            AppStyles.DETAIL_PAGE_EVENT_ITEM_MARGIN,
            AppStyles.DETAIL_PAGE_EVENT_ITEM_MARGIN,
            AppStyles.DETAIL_PAGE_EVENT_ITEM_MARGIN
        )
        layout.setSpacing(3)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        event_type = event.get("type", "Normal")
        type_label = QLabel(event_type)
        if event_type == "Warning":
            type_label.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_TYPE_WARNING_STYLE)
        else:
            type_label.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_TYPE_NORMAL_STYLE)
        
        reason = event.get("reason", "")
        if reason:
            reason_label = QLabel(reason)
            reason_label.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_REASON_STYLE)
        else:
            reason_label = QLabel("")
        
        last_timestamp = event.get("lastTimestamp", event.get("eventTime", ""))
        if last_timestamp:
            import datetime
            from dateutil import parser
            try:
                event_time = parser.parse(last_timestamp)
                now = datetime.datetime.now(datetime.timezone.utc)
                delta = now - event_time
                
                days = delta.days
                seconds = delta.seconds
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                
                if days > 0:
                    age_str = f"{days}d"
                elif hours > 0:
                    age_str = f"{hours}h"
                else:
                    age_str = f"{minutes}m"
                
                age_label = QLabel(age_str)
                age_label.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_AGE_STYLE)
            except Exception:
                age_label = QLabel("")
        else:
            age_label = QLabel("")
        
        header_layout.addWidget(type_label)
        header_layout.addWidget(reason_label)
        header_layout.addStretch()
        header_layout.addWidget(age_label)
        
        message = event.get("message", "")
        message_label = QLabel(message)
        message_label.setStyleSheet(AppStyles.DETAIL_PAGE_EVENT_MESSAGE_STYLE)
        message_label.setWordWrap(True)
        
        layout.addLayout(header_layout)
        layout.addWidget(message_label)
        
        item = QListWidgetItem()
        item.setSizeHint(event_widget.sizeHint())
        self.events_list.addItem(item)
        self.events_list.setItemWidget(item, event_widget)
    
    def close_detail(self):
        self.hide_with_animation()
    
    def show_with_animation(self):
        if self.isVisible():
            return
            
        if self.parent():
            self.move(self.parent().width(), 0)
            target_x = self.parent().width() - self.width()
            parent_height = self.parent().height()
        else:
            screen_width = QApplication.primaryScreen().geometry().width()
            screen_height = QApplication.primaryScreen().geometry().height()
            self.move(screen_width, 0)
            target_x = screen_width - self.width()
            parent_height = screen_height
        
        self.setFixedHeight(parent_height)
        self.show()
        self.raise_()
        
        self.slide_animation.setStartValue(self.geometry())
        self.slide_animation.setEndValue(QRect(target_x, 0, self.width(), parent_height))
        
        self.animation_group.setDirection(QAbstractAnimation.Direction.Forward)
        self.animation_group.start()
    
    def hide_with_animation(self):
        """Hide the detail page with animation sliding to the right"""
        if not self.isVisible():
            return
            
        # Create animation
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(AppStyles.DETAIL_PAGE_ANIMATION_DURATION)
        self.animation.setStartValue(self.geometry())
        
        if self.parent():
            end_rect = QRect(self.parent().width(), 0, self.width(), self.height())
        else:
            screen_width = QApplication.primaryScreen().geometry().width()
            end_rect = QRect(screen_width, 0, self.width(), self.height())
            
        self.animation.setEndValue(end_rect)
        self.animation.setEasingCurve(QEasingCurve.Type.InQuint)
        
        # Connect finished signal to hide
        self.animation.finished.connect(self.hide)
        
        # Start animation
        self.animation.start()
        
        # Emit back signal
        self.back_signal.emit()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'resize_handle'):
            self.resize_handle.setFixedHeight(self.height())
            self.resize_handle.move(0, 0)
    
    def moveEvent(self, event):
        super().moveEvent(event)
        if self.parent() and self.height() != self.parent().height():
            self.setFixedHeight(self.parent().height())
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Use globalPosition() instead of globalPos()
            global_pos = event.globalPosition().toPoint()
            if not self.geometry().contains(global_pos):
                self.close_detail()
        super().mousePressEvent(event)

    def closeEvent(self, event):
        """Handle close event - hide with animation"""
        self.hide_with_animation()
        event.accept()
    
    def eventFilter(self, obj, event):
        """Filter events to close detail page when clicking outside"""
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            # Use globalPosition() to get coordinates in screen space
            global_pos = event.globalPosition().toPoint()
            
            # Check if click is outside detail page bounds
            if not self.geometry().contains(global_pos):
                # Check if the click is on a UI element we want to ignore
                # (where we want to keep the detail page open)
                widget = QApplication.widgetAt(global_pos)
                
                # Keep detail open if clicking on the resource table itself
                # as this will handle resource switching
                if widget and hasattr(widget, 'objectName'):
                    parent_widgets = []
                    parent = widget
                    
                    # Check parent chain to identify table and relevant widgets
                    while parent:
                        parent_widgets.append(parent)
                        if parent.inherits('QTableWidget') or parent.inherits('QTreeWidget'):
                            # Don't close when clicking directly on tables/trees (resources)
                            return super().eventFilter(obj, event)
                        parent = parent.parent()
                
                # For all other clicks outside, close the detail
                self.close_detail()
                return True  # Event handled
        
        return super().eventFilter(obj, event)