"""
YAML section for DetailPage component - with preferences support
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, QTextEdit, QLabel
)
from PyQt6.QtCore import Qt, QTimer, QSize, QRect
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QPainter
from typing import Dict, Any
import yaml
import logging
import re

from .base_detail_section import BaseDetailSection
from UI.Styles import AppStyles, AppColors

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
    """YAML editor with line numbers support and preferences integration"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        # Preferences settings with defaults
        self.show_line_numbers = True
        self.tab_size = 2
        self.font_family = "Consolas"
        self.font_size = 9  # Default to 9 as per preferences

        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.verticalScrollBar().valueChanged.connect(self.update_line_number_area)
        self.textChanged.connect(lambda: self.update_line_number_area(0))
        self.update_line_number_area_width(0)
        self.update_line_number_visibility()

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

    def keyPressEvent(self, event):
        """Override key press event to handle tab with configurable size"""
        if event.key() == Qt.Key.Key_Tab:
            # Insert spaces based on tab_size setting
            spaces = " " * self.tab_size
            self.insertPlainText(spaces)
        else:
            super().keyPressEvent(event)

    def line_number_area_paint_event(self, event):
        if not self.show_line_numbers:
            return

        painter = QPainter(self.line_number_area)

        # Get visible blocks
        block = self.document().firstBlock()
        block_number = 0

        # Get viewport offset for proper text alignment
        viewport_offset = self.verticalScrollBar().value()

        while block.isValid():
            # Get block position in viewport coordinates
            block_rect = self.document().documentLayout().blockBoundingRect(block)
            block_top = int(block_rect.translated(0, -viewport_offset).top())

            # Only paint if block is visible
            if block_top >= 0 and block_top < self.height():
                number = str(block_number + 1)
                painter.setPen(QColor(AppColors.TEXT_SUBTLE))
                painter.drawText(0, block_top, self.line_number_area.width() - 5,
                                 self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            block_number += 1

    def update_line_number_visibility(self):
        """Update line number area visibility"""
        self.line_number_area.setVisible(self.show_line_numbers)
        self.update_line_number_area_width(0)
        self.update()

    def set_line_numbers_visible(self, visible):
        """Set line numbers visibility from preferences"""
        self.show_line_numbers = visible
        self.update_line_number_visibility()
        logging.debug(f"YAML Editor: Line numbers set to {visible}")

    def set_tab_size(self, size):
        """Set tab size from preferences"""
        if 1 <= size <= 8:
            self.tab_size = size
            logging.debug(f"YAML Editor: Tab size set to {size}")

    def set_font_family(self, family):
        """Set font family from preferences"""
        self.font_family = family
        self.update_font()
        logging.debug(f"YAML Editor: Font family set to {family}")

    def set_font_size(self, size):
        """Set font size from preferences"""
        if 6 <= size <= 72:
            self.font_size = size
            self.update_font()
            logging.debug(f"YAML Editor: Font size set to {size}")

    def update_font(self):
        """Update the editor font with current family and size"""
        font = QFont(self.font_family, self.font_size)
        self.setFont(font)
        self.update_line_number_area_width(0)  # Recalculate width with new font

class DetailPageYAMLSection(BaseDetailSection):
    """YAML section showing resource YAML representation with preferences support"""

    def __init__(self, kubernetes_client, parent=None):
        super().__init__("YAML", kubernetes_client, parent)
        self.original_yaml = None
        self.yaml_edited = False
        self.setup_yaml_ui()

    def setup_yaml_ui(self):
        """Setup YAML-specific UI"""
        # Create toolbar
        yaml_toolbar = QWidget()
        yaml_toolbar.setFixedHeight(40)
        yaml_toolbar.setStyleSheet(f"""
            background-color: {AppColors.BG_DARK};
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
        """)

        toolbar_layout = QHBoxLayout(yaml_toolbar)
        toolbar_layout.setContentsMargins(10, 0, 10, 0)

        # Edit button
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

        # Save button
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

        # Cancel button
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

        toolbar_layout.addWidget(self.yaml_edit_button)
        toolbar_layout.addWidget(self.yaml_save_button)
        toolbar_layout.addWidget(self.yaml_cancel_button)
        toolbar_layout.addStretch()

        # Use custom editor with line numbers support
        self.yaml_editor = YamlEditorWithLineNumbers()
        self.yaml_editor.setReadOnly(True)

        # Set font using defaults (will be updated by preferences)
        font = QFont(self.yaml_editor.font_family, self.yaml_editor.font_size)
        self.yaml_editor.setFont(font)

        # Apply syntax highlighting
        self.yaml_highlighter = YamlHighlighter(self.yaml_editor.document())

        # Basic stylesheet
        base_yaml_style = f"""
            QTextEdit {{
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                selection-background-color: #264F78;
                selection-color: #D4D4D4;
                padding: 20px;
            }}
            {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
        """
        self.yaml_editor.setStyleSheet(base_yaml_style)

        # Add to main layout
        self.content_layout.addWidget(yaml_toolbar)
        self.content_layout.addWidget(self.yaml_editor)

    # Methods for preferences integration
    def update_yaml_font_size(self, font_size):
        """Update YAML editor font size from preferences"""
        if hasattr(self, 'yaml_editor'):
            self.yaml_editor.set_font_size(font_size)
            logging.debug(f"DetailPageYAMLSection: Updated font size to {font_size}")

    def update_yaml_font_family(self, font_family):
        """Update YAML editor font family from preferences"""
        if hasattr(self, 'yaml_editor'):
            self.yaml_editor.set_font_family(font_family)
            logging.debug(f"DetailPageYAMLSection: Updated font family to {font_family}")

    def update_yaml_line_numbers(self, show_line_numbers):
        """Update YAML editor line numbers visibility from preferences"""
        if hasattr(self, 'yaml_editor'):
            self.yaml_editor.set_line_numbers_visible(show_line_numbers)
            logging.debug(f"DetailPageYAMLSection: Updated line numbers to {show_line_numbers}")

    def update_yaml_tab_size(self, tab_size):
        """Update YAML editor tab size from preferences"""
        if hasattr(self, 'yaml_editor'):
            self.yaml_editor.set_tab_size(tab_size)
            logging.debug(f"DetailPageYAMLSection: Updated tab size to {tab_size}")

    def _load_data_async(self):
        """Load overview data using Kubernetes API"""
        try:
            self.connect_api_signals()
            self.kubernetes_client.get_resource_detail_async(
                self.resource_type,
                self.resource_name,
                self.resource_namespace or "default"
            )
        except Exception as e:
            self.handle_error(f"Failed to start data loading: {str(e)}")

    def handle_api_data_loaded(self, data):
        """Handle data loaded from Kubernetes API"""
        try:
            self.disconnect_api_signals()
            self.handle_data_loaded(data)
        except Exception as e:
            self.handle_error(f"Error processing loaded data: {str(e)}")

    def handle_api_error(self, error_message):
        """Handle API error"""
        self.disconnect_api_signals()
        self.handle_error(error_message)

    def update_ui_with_data(self, data: Dict[str, Any]):
        """Update YAML UI with loaded resource data"""
        try:
            # Convert data to YAML
            yaml_text = yaml.dump(data, default_flow_style=False, sort_keys=False)
            self.yaml_editor.setPlainText(yaml_text)
            self.original_yaml = yaml_text

        except Exception as e:
            self.yaml_editor.setPlainText(f"Error rendering YAML: {str(e)}")
            self.handle_error(f"Error rendering YAML: {str(e)}")

    def toggle_yaml_edit_mode(self):
        """Toggle between read-only and edit mode"""
        if self.yaml_editor.isReadOnly():
            # Enter edit mode
            self.yaml_editor.setReadOnly(False)
            self.yaml_edit_button.hide()
            self.yaml_save_button.show()
            self.yaml_cancel_button.show()

            self.yaml_editor.setStyleSheet(f"""
                QTextEdit {{
                    background-color: #1E1E1E;
                    color: #D4D4D4;
                    border: 1px solid #0078d7;
                    selection-background-color: #264F78;
                    selection-color: #D4D4D4;
                    padding: 20px;
                }}
                {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
            """)

            self.original_yaml = self.yaml_editor.toPlainText()
        else:
            # Exit edit mode
            self.yaml_editor.setReadOnly(True)
            self.yaml_edit_button.show()
            self.yaml_save_button.hide()
            self.yaml_cancel_button.hide()

            self.yaml_editor.setStyleSheet(f"""
                QTextEdit {{
                    background-color: #1E1E1E;
                    color: #D4D4D4;
                    border: none;
                    selection-background-color: #264F78;
                    selection-color: #D4D4D4;
                    padding: 20px;
                }}
                {AppStyles.UNIFIED_SCROLL_BAR_STYLE}
            """)

    def save_yaml_changes(self):
        """Save YAML changes (placeholder - implement with kubectl apply)"""
        yaml_text = self.yaml_editor.toPlainText()

        if yaml_text == self.original_yaml:
            self.toggle_yaml_edit_mode()
            return

        try:
            # Validate YAML
            yaml_data = yaml.safe_load(yaml_text)

            # TODO: Implement actual save using Kubernetes API
            # For now, just toggle back to read mode
            self.toggle_yaml_edit_mode()

            # Show success message (you might want to emit a signal here)
            logging.info("YAML changes saved successfully")

        except yaml.YAMLError as e:
            self.handle_error(f"Invalid YAML: {str(e)}")
        except Exception as e:
            self.handle_error(f"Error saving YAML: {str(e)}")

    def cancel_yaml_edit(self):
        """Cancel YAML editing and restore original content"""
        if self.original_yaml:
            self.yaml_editor.setPlainText(self.original_yaml)
        self.toggle_yaml_edit_mode()

    def clear_content(self):
        """Clear YAML content"""
        self.yaml_editor.clear()
        self.original_yaml = None
        self.yaml_edited = False

        if not self.yaml_editor.isReadOnly():
            self.toggle_yaml_edit_mode()