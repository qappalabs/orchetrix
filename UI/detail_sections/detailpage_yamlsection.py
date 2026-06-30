"""
Enhanced YAML section for DetailPage component - with actual deployment capability
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QLineEdit, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QSize, QRect, pyqtSignal
from PyQt6.QtGui import (
    QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QPainter,
    QKeySequence, QShortcut, QTextCursor, QTextDocument, QIcon
)
from typing import Dict, Any
import yaml
import logging
import re

from .base_detail_section import BaseDetailSection
from UI.Styles import AppColors
from UI.Icons import resource_path
import Styles.YamlSectionStyles as YAMLSectionStyles

class YamlHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for YAML content with improved color scheme and error detection"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Format for keys
        key_format = QTextCharFormat()
        key_format.setForeground(QColor(AppColors.YAML_KEY))
        key_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r'^\s*[^:]+:', key_format))

        # Format for values
        value_format = QTextCharFormat()
        value_format.setForeground(QColor(AppColors.YAML_VALUE))
        self.highlighting_rules.append((r':\s*[^{\\[].*$', value_format))

        # Format for lists
        list_format = QTextCharFormat()
        list_format.setForeground(QColor(AppColors.YAML_LIST))
        self.highlighting_rules.append((r'^\s*-\s+', list_format))

        # Format for comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(AppColors.YAML_COMMENT))
        self.highlighting_rules.append((r'#.*$', comment_format))

        # Format for numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(AppColors.YAML_NUMBER))
        self.highlighting_rules.append((r'\b\d+\b', number_format))

        # Format for booleans
        boolean_format = QTextCharFormat()
        boolean_format.setForeground(QColor(AppColors.YAML_BOOLEAN))
        self.highlighting_rules.append((r'\b(true|false|True|False|yes|no|Yes|No)\b', boolean_format))

        # Format for null values
        null_format = QTextCharFormat()
        null_format.setForeground(QColor(AppColors.YAML_NULL))
        self.highlighting_rules.append((r'\b(null|Null|NULL|~)\b', null_format))

        # Format for strings in quotes
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(AppColors.YAML_STRING))
        self.highlighting_rules.append((r'"[^"]*"', string_format))
        self.highlighting_rules.append((r"'[^']*'", string_format))

        # Format for syntax errors
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor("#FF0000"))
        self.error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        self.error_format.setForeground(QColor("#FF4444"))

        self.rules = [(re.compile(pattern), fmt) for pattern, fmt in self.highlighting_rules]

    def highlightBlock(self, text):
        """Apply highlighting to the given block of text"""
        # Apply standard syntax highlighting
        for regex, fmt in self.rules:
            matches = regex.finditer(text)
            for match in matches:
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)

        # Check for syntax errors in this line
        self._highlight_yaml_errors(text)

    def _highlight_yaml_errors(self, text):
        """Highlight YAML syntax errors in real-time"""
        # Skip empty lines, comments, and list items
        stripped = text.strip()
        if not stripped or stripped.startswith('#') or stripped.startswith('-'):
            return

        # Check for the specific "backend:django" type error (missing space after colon)
        colon_match = re.search(r'^\s*(\w+):([\w-]+)', text)
        if colon_match:
            # Found key:value without space after colon
            value = colon_match.group(2)
            colon_pos = text.find(':')
            
            # Highlight the problematic part (from colon to end of value)
            error_start = colon_pos
            error_end = colon_pos + 1 + len(value)
            self.setFormat(error_start, error_end - error_start, self.error_format)
            return

        # Check for other common YAML syntax errors
        error_patterns = [
            # Key without colon at end of line
            (r'^\s*\w+\s*$', "Key without colon"),
            # Multiple colons in key
            (r'^\s*[^:]*:[^:]*:[^:]*:', "Multiple colons in key"),
            # Colon without key
            (r'^\s*:\s*', "Value without key"),
            # Invalid indentation (tabs mixed with spaces - basic check)
            (r'^\t+ +|\s+ \t+', "Mixed tabs and spaces"),
        ]

        for pattern, error_type in error_patterns:
            if re.search(pattern, text):
                # Don't highlight if this looks like a valid YAML structure
                if pattern == r'^\s*\w+\s*$':
                    # Check if next line is properly indented child
                    current_block = self.currentBlock()
                    next_block = current_block.next()
                    if next_block.isValid():
                        next_text = next_block.text().strip()
                        if next_text and (next_text.startswith('- ') or ':' in next_text):
                            continue  # This is likely valid YAML

                self.setFormat(0, len(text), self.error_format)
                break

        # Additional check for malformed key-value pairs
        if ':' in text and not re.search(r'^\s*[\w-]+\s*:\s+', text):
            colon_pos = text.find(':')
            if colon_pos > 0:  # Not at start of line
                # Check if there's proper spacing
                before_colon = text[:colon_pos].strip()
                after_colon = text[colon_pos+1:]
                
                if before_colon and after_colon.strip():  # Both key and value present
                    if not after_colon.startswith(' '):  # No space after colon
                        self.setFormat(colon_pos, len(after_colon.split()[0]) + 1, self.error_format)

class SearchWidget(QFrame):
    """Search widget for YAML editor"""

    search_next = pyqtSignal()
    search_previous = pyqtSignal()
    search_closed = pyqtSignal()

    def __init__(self, parent=None, editor=None):
        super().__init__(parent)
        self.editor = editor
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        """Setup search widget UI"""
        self.setFixedHeight(40)
        self.update_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in YAML...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.search_next.emit)
        layout.addWidget(self.search_input)

        # Results label
        self.results_label = QLabel("0 of 0")
        self.results_label.setFixedWidth(50)
        self.results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.results_label)

        # Previous button with icon
        self.prev_button = QPushButton()
        self.prev_button.setIconSize(QSize(14, 14))
        self.prev_button.setFixedSize(24, 24)
        self.prev_button.setToolTip("Previous (Shift+Enter)")
        self.prev_button.clicked.connect(self.search_previous.emit)
        layout.addWidget(self.prev_button)

        # Next button with icon
        self.next_button = QPushButton()
        self.next_button.setIconSize(QSize(14, 14))
        self.next_button.setFixedSize(24, 24)
        self.next_button.setToolTip("Next (Enter)")
        self.next_button.clicked.connect(self.search_next.emit)
        layout.addWidget(self.next_button)

        # Case sensitive toggle with icon
        self.case_button = QPushButton()
        self.case_button.setIconSize(QSize(14, 14))
        self.case_button.setFixedSize(24, 24)
        self.case_button.setCheckable(True)
        self.case_button.setToolTip("Case Sensitive")
        self.case_button.clicked.connect(self.on_search_text_changed)
        layout.addWidget(self.case_button)

        # Close button with icon
        self.close_button = QPushButton()
        self.close_button.setIconSize(QSize(12, 12))
        self.close_button.setFixedSize(18, 18)
        self.close_button.setToolTip("Close (Escape)")
        self.close_button.clicked.connect(self.close_search)
        layout.addWidget(self.close_button)
        
        # Load theme icons initially
        from UI.ThemeManager import get_theme_manager
        current_theme = get_theme_manager().get_current_theme_name()
        self.update_icons(current_theme)

    def update_style(self):
        """Update widget stylesheet"""
        self.setStyleSheet(YAMLSectionStyles.get_search_widget_style())

    def update_icons(self, theme_name):
        """Update icons based on current theme"""
        from UI.Icons import Icons
        self.prev_button.setIcon(QIcon(Icons.get_theme_icon_path("Yaml_uparrow.svg", theme_name)))
        self.next_button.setIcon(QIcon(Icons.get_theme_icon_path("Yaml_downarrow.svg", theme_name)))
        self.case_button.setIcon(QIcon(Icons.get_theme_icon_path("Yaml_Casesensitive.svg", theme_name)))
        self.close_button.setIcon(QIcon(Icons.get_theme_icon_path("close.svg", theme_name)))

    def update_theme(self, theme_name):
        """Called when theme changes to update everything"""
        self.update_style()
        self.update_icons(theme_name)


    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Escape to close
        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(self.close_search)

        # Shift+Enter for previous
        shift_enter = QShortcut(QKeySequence("Shift+Return"), self)
        shift_enter.activated.connect(self.search_previous.emit)

    def on_search_text_changed(self):
        """Handle search text change"""
        search_text = self.search_input.text()
        # Call perform_search on the editor instead of parent
        if self.editor and hasattr(self.editor, 'perform_search'):
            self.editor.perform_search(search_text, self.case_button.isChecked())

    def close_search(self):
        """Close search widget"""
        self.hide()
        self.search_closed.emit()

    def update_results(self, current, total):
        """Update search results display"""
        if total == 0:
            self.results_label.setText("No results")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
        else:
            self.results_label.setText(f"{current} of {total}")
            self.prev_button.setEnabled(total > 1)
            self.next_button.setEnabled(total > 1)

    def focus_search(self):
        """Focus the search input"""
        self.search_input.setFocus()
        self.search_input.selectAll()

class LineNumberArea(QWidget):
    """Line number area for YAML editor"""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class YamlEditorWithLineNumbers(QTextEdit):
    """Enhanced YAML editor with line numbers and search functionality"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        # Search functionality
        self.search_widget = None
        self.search_results = []
        self.current_search_index = -1
        self.search_format = QTextCharFormat()
        self.current_search_format = QTextCharFormat()

        # Setup search highlighting formats
        self.search_format.setBackground(QColor("#4A90E2"))
        self.search_format.setForeground(QColor("#FFFFFF"))
        self.current_search_format.setBackground(QColor("#F39C12"))
        self.current_search_format.setForeground(QColor("#FFFFFF"))

        # Preferences settings with defaults
        self.show_line_numbers = True
        self.tab_size = 2
        self.font_family = "Consolas"
        self.font_size = 9

        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.verticalScrollBar().valueChanged.connect(self.update_line_number_area)
        self.textChanged.connect(lambda: self.update_line_number_area(0))
        self.update_line_number_area_width(0)
        self.update_line_number_visibility()

        # Setup search shortcut
        self.setup_search_shortcut()

    def setup_search_shortcut(self):
        """Setup Ctrl+F shortcut for search"""
        search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        search_shortcut.activated.connect(self.show_search)

    def show_search(self):
        """Show search widget"""
        if not self.search_widget:
            self.create_search_widget()

        self.search_widget.show()
        self.search_widget.focus_search()

    def create_search_widget(self):
        """Create search widget"""
        # Get the DetailPageYAMLSection parent
        yaml_section = self.parent()
        while yaml_section and not hasattr(yaml_section, 'content_layout'):
            yaml_section = yaml_section.parent()

        if yaml_section and hasattr(yaml_section, 'content_layout'):
            # Create search widget as child of the section, but pass editor reference
            self.search_widget = SearchWidget(yaml_section, editor=self)  # Pass self as editor
            self.search_widget.search_next.connect(self.search_next)
            self.search_widget.search_previous.connect(self.search_previous)
            self.search_widget.search_closed.connect(self.close_search)
            self.search_widget.hide()

            # Insert after toolbar but before editor
            yaml_section.content_layout.insertWidget(1, self.search_widget)
        else:
            # Fallback: create as overlay (this shouldn't happen)
            self.search_widget = SearchWidget(self, editor=self)  # Pass self as editor
            self.search_widget.search_next.connect(self.search_next)
            self.search_widget.search_previous.connect(self.search_previous)
            self.search_widget.search_closed.connect(self.close_search)
            self.search_widget.hide()

    def resizeEvent(self, event):
        """Handle resize event with proper line number positioning"""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def perform_search(self, search_text, case_sensitive=False):
        """Perform search and highlight results"""
        # Clear previous search
        self.clear_search_highlighting()
        self.search_results = []
        self.current_search_index = -1

        if not search_text:
            if self.search_widget:
                self.search_widget.update_results(0, 0)
            return

        # Find all occurrences
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        while True:
            if case_sensitive:
                cursor = self.document().find(search_text, cursor, QTextDocument.FindFlag.FindBackward | QTextDocument.FindFlag.FindCaseSensitively)
            else:
                cursor = self.document().find(search_text, cursor, QTextDocument.FindFlag.FindBackward)

            if cursor.isNull():
                break

            self.search_results.insert(0, cursor)

        # Highlight all results
        for i, result_cursor in enumerate(self.search_results):
            format_to_use = self.current_search_format if i == 0 else self.search_format
            result_cursor.setCharFormat(format_to_use)

        if self.search_results:
            self.current_search_index = 0
            self.setTextCursor(self.search_results[0])
            self.ensureCursorVisible()

        # Update results display
        if self.search_widget:
            total = len(self.search_results)
            current = self.current_search_index + 1 if total > 0 else 0
            self.search_widget.update_results(current, total)

    def search_next(self):
        """Go to next search result"""
        if not self.search_results:
            return

        # Update highlighting
        if self.current_search_index >= 0:
            self.search_results[self.current_search_index].setCharFormat(self.search_format)

        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)

        # Highlight current result
        current_cursor = self.search_results[self.current_search_index]
        current_cursor.setCharFormat(self.current_search_format)
        self.setTextCursor(current_cursor)
        self.ensureCursorVisible()

        # Update display
        if self.search_widget:
            self.search_widget.update_results(self.current_search_index + 1, len(self.search_results))

    def search_previous(self):
        """Go to previous search result"""
        if not self.search_results:
            return

        # Update highlighting
        if self.current_search_index >= 0:
            self.search_results[self.current_search_index].setCharFormat(self.search_format)

        self.current_search_index = (self.current_search_index - 1) % len(self.search_results)

        # Highlight current result
        current_cursor = self.search_results[self.current_search_index]
        current_cursor.setCharFormat(self.current_search_format)
        self.setTextCursor(current_cursor)
        self.ensureCursorVisible()

        # Update display
        if self.search_widget:
            self.search_widget.update_results(self.current_search_index + 1, len(self.search_results))

    def close_search(self):
        """Close search and clear highlighting"""
        self.clear_search_highlighting()
        self.search_results = []
        self.current_search_index = -1
        self.setFocus()  # Return focus to editor

    def clear_search_highlighting(self):
        """Clear all search highlighting"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())  # Clear formatting
        cursor.clearSelection()

    # Line number functionality (existing methods)
    def lineNumberAreaWidth(self):
        """Calculate width needed for line numbers with better spacing"""
        if not self.show_line_numbers:
            return 0

        digits = 1
        max_block = max(1, self.document().blockCount())
        while max_block >= 10:
            max_block /= 10
            digits += 1

        # Increased spacing for better visibility
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits + 10
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def update_line_number_area(self, dy=0):
        """Update line number area"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update()

        if self.height() != self.line_number_area.height():
            self.line_number_area.setFixedHeight(self.height())

        self.update_line_number_area_width(0)

    def keyPressEvent(self, event):
        """Override key press event to handle tab with configurable size and search shortcuts"""
        if event.key() == Qt.Key.Key_Tab:
            # Insert spaces based on tab_size setting
            spaces = " " * self.tab_size
            self.insertPlainText(spaces)
        else:
            super().keyPressEvent(event)

    def line_number_area_paint_event(self, event):
        """Fixed line number painting for QTextEdit"""
        if not self.show_line_numbers:
            return

        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#2d2d2d"))  # Background for line numbers

        # Set font and color for line numbers
        painter.setPen(QColor("#858585"))  # Light gray color for line numbers
        font = self.font()
        painter.setFont(font)

        # Get the document and viewport information
        document = self.document()
        viewport_rect = self.viewport().rect()

        # Get the scroll position
        scroll_y = self.verticalScrollBar().value()

        # Calculate visible area
        visible_top = scroll_y
        visible_bottom = scroll_y + viewport_rect.height()

        # Iterate through all blocks and paint visible ones
        block = document.firstBlock()
        block_number = 0

        while block.isValid():
            # Get block geometry
            block_geometry = document.documentLayout().blockBoundingRect(block)
            block_top = int(block_geometry.top())
            block_bottom = int(block_geometry.bottom())

            # Check if block is in visible area
            if block_bottom >= visible_top and block_top <= visible_bottom:
                # Calculate position relative to viewport
                y_position = block_top - scroll_y

                # Only paint if within the paint event area
                if y_position >= event.rect().top() - 20 and y_position <= event.rect().bottom() + 20:
                    number = str(block_number + 1)

                    # Draw the line number
                    painter.drawText(
                        5,  # Left padding
                        y_position,
                        self.line_number_area.width() - 10,  # Width with right padding
                        int(block_geometry.height()),
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                        number
                    )
            elif block_top > visible_bottom:
                # Early exit optimization: stop if we passed the visible area
                break

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

    def set_tab_size(self, size):
        """Set tab size from preferences"""
        if 1 <= size <= 8:
            self.tab_size = size

    def set_font_family(self, family):
        """Set font family from preferences"""
        self.font_family = family
        self.update_font()

    def set_font_size(self, size):
        """Set font size from preferences"""
        if 6 <= size <= 72:
            self.font_size = size
            self.update_font()

    def update_font(self):
        """Update the editor font with current family and size"""
        font = QFont(self.font_family, self.font_size)
        self.setFont(font)
        self.update_line_number_area_width(0)

class DetailPageYAMLSection(BaseDetailSection):
    """Enhanced YAML section with actual deployment capability"""

    RELOAD_DELAY_MS = 2000  # Configurable delay for post-update reload
    MAX_RELOAD_RETRIES = 3

    def __init__(self, kubernetes_client, parent=None):
        super().__init__("YAML", kubernetes_client, parent)
        self.original_yaml = None
        self.yaml_edited = False
        self.is_helm_resource = False
        self.reload_retry_count = 0
        self._reload_success = False  # Track whether reload has succeeded
        self._reload_in_progress = False  # Force API fetch during post-deploy reloads
        self.setup_yaml_ui()

    def _on_theme_changed(self, theme_name):
        """Handle theme changes by updating all styling"""
        # Update toolbar styling
        if hasattr(self, 'yaml_toolbar'):
            self.yaml_toolbar.setStyleSheet(YAMLSectionStyles.get_yaml_toolbar_style())

        # Update button styling
        if hasattr(self, 'yaml_edit_button'):
            self.yaml_edit_button.setStyleSheet(YAMLSectionStyles.get_yaml_edit_button_style())
        if hasattr(self, 'yaml_save_button'):
            self.yaml_save_button.setStyleSheet(YAMLSectionStyles.get_yaml_save_button_style())
        if hasattr(self, 'yaml_cancel_button'):
            self.yaml_cancel_button.setStyleSheet(YAMLSectionStyles.get_yaml_cancel_button_style())
        if hasattr(self, 'helm_status_label'):
            self.helm_status_label.setStyleSheet(YAMLSectionStyles.get_helm_status_label_style())

        # Update editor styling based on current mode
        if hasattr(self, 'yaml_editor'):
            if self.yaml_editor.isReadOnly():
                self.yaml_editor.setStyleSheet(YAMLSectionStyles.get_yaml_editor_readonly_style())
            else:
                self.yaml_editor.setStyleSheet(YAMLSectionStyles.get_yaml_editor_edit_style())
                
        # Update search widget styling and icons if it exists
        if hasattr(self, 'yaml_editor') and hasattr(self.yaml_editor, 'search_widget') and self.yaml_editor.search_widget:
            self.yaml_editor.search_widget.update_theme(theme_name)

    def setup_yaml_ui(self):
        """Setup YAML-specific UI"""
        # Create toolbar
        self.yaml_toolbar = QWidget()
        self.yaml_toolbar.setFixedHeight(40)
        self.yaml_toolbar.setStyleSheet(YAMLSectionStyles.get_yaml_toolbar_style())

        toolbar_layout = QHBoxLayout(self.yaml_toolbar)
        toolbar_layout.setContentsMargins(10, 0, 10, 0)

        # Edit button
        self.yaml_edit_button = QPushButton("Edit")
        self.yaml_edit_button.setStyleSheet(YAMLSectionStyles.get_yaml_edit_button_style())
        self.yaml_edit_button.clicked.connect(self.toggle_yaml_edit_mode)

        # Save button
        self.yaml_save_button = QPushButton("Deploy")
        self.yaml_save_button.setStyleSheet(YAMLSectionStyles.get_yaml_save_button_style())
        self.yaml_save_button.clicked.connect(self.save_yaml_changes)
        self.yaml_save_button.hide()

        # Cancel button
        self.yaml_cancel_button = QPushButton("Cancel")
        self.yaml_cancel_button.setStyleSheet(YAMLSectionStyles.get_yaml_cancel_button_style())
        self.yaml_cancel_button.clicked.connect(self.cancel_yaml_edit)
        self.yaml_cancel_button.hide()

        # Status label for helm resources
        self.helm_status_label = QLabel("⚠️ Helm resources cannot be edited via YAML")
        self.helm_status_label.setStyleSheet(YAMLSectionStyles.get_helm_status_label_style())
        self.helm_status_label.hide()

        toolbar_layout.addWidget(self.yaml_edit_button)
        toolbar_layout.addWidget(self.yaml_save_button)
        toolbar_layout.addWidget(self.yaml_cancel_button)
        toolbar_layout.addWidget(self.helm_status_label)
        toolbar_layout.addStretch()

        # Use custom editor with line numbers support
        self.yaml_editor = YamlEditorWithLineNumbers()
        self.yaml_editor.setReadOnly(True)

        # Set font using defaults (will be updated by preferences)
        font = QFont(self.yaml_editor.font_family, self.yaml_editor.font_size)
        self.yaml_editor.setFont(font)

        # Apply syntax highlighting
        self.yaml_highlighter = YamlHighlighter(self.yaml_editor.document())

        # Apply theme-aware editor styling
        self.yaml_editor.setStyleSheet(YAMLSectionStyles.get_yaml_editor_readonly_style())

        # Add to main layout
        self.content_layout.addWidget(self.yaml_toolbar)
        self.content_layout.addWidget(self.yaml_editor)

        # Connect kubernetes client signals for updates using queued connection for thread safety
        try:
            if hasattr(self.kubernetes_client, 'resource_updated'):
                self.kubernetes_client.resource_updated.connect(
                    self.handle_resource_update_result,
                    Qt.ConnectionType.QueuedConnection
                )
                logging.debug("YAML section: Connected to resource_updated signal with queued connection")
            else:
                logging.warning("YAML section: kubernetes_client does not have resource_updated signal")
        except Exception as e:
            logging.error(f"YAML section: Failed to connect resource_updated signal: {str(e)}")

    def set_resource(self, resource_type: str, resource_name: str, namespace=None):
        """Set the resource information and check if it's a helm resource"""
        super().set_resource(resource_type, resource_name, namespace)

        # Check if this is a helm resource
        self.is_helm_resource = resource_type.lower() in [
            "helmrelease", "helmreleases", "hr", "chart", "charts"
        ]

        if self.is_helm_resource:
            self.yaml_edit_button.setEnabled(False)
            self.helm_status_label.show()
        else:
            self.yaml_edit_button.setEnabled(True)
            self.helm_status_label.hide()

    def set_raw_data(self, raw_data):
        """Set raw data for special resources like nodes and custom resources"""
        logging.info(f"YAML section: Received raw data for {self.resource_type}, keys: {list(raw_data.keys()) if raw_data else 'None'}")
        self.current_data = raw_data
        self.update_ui_with_data(raw_data)

    def _load_data_async(self):
        """Load overview data using Kubernetes API"""
        try:
            # CRITICAL FIX: Check if we already have raw_data from the page (e.g., NodesPage)
            # This prevents unnecessary API calls and empty YAML sections
            # However, after a deploy we MUST bypass the cache to fetch fresh server state
            if self.current_data is not None and not self._reload_in_progress:
                logging.info(f"YAML section: Using existing raw_data for {self.resource_type}/{self.resource_name}")
                # Use the existing data directly instead of making API call
                self.handle_data_loaded(self.current_data)
                return
            
            # Only make API call if we don't have current_data
            logging.info(f"YAML section: No raw_data available, fetching from API for {self.resource_type}/{self.resource_name}")
            self.connect_api_signals()
            self.kubernetes_client.get_resource_detail(
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
            self._reload_in_progress = False  # Reset: fresh data received
            self.handle_data_loaded(data)
        except Exception as e:
            self._reload_in_progress = False
            self.handle_error(f"Error processing loaded data: {str(e)}")

    def handle_api_error(self, error_message):
        """Handle API error"""
        self.disconnect_api_signals()
        self._reload_in_progress = False  # Reset to restore normal cache behavior
        self.handle_error(error_message)

    def update_ui_with_data(self, data: Dict[str, Any]):
        """Update YAML UI with loaded resource data"""
        try:
            if not data:
                self.yaml_editor.setPlainText("# No data available for this resource")
                return

            # Convert snake_case back to camelCase for proper Kubernetes YAML
            kubernetes_yaml = self._convert_to_kubernetes_yaml(data)

            # Use better YAML dump settings for readability
            yaml_text = yaml.dump(
                kubernetes_yaml,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                width=120,
                allow_unicode=True
            )
            self.yaml_editor.setPlainText(yaml_text)
            self.original_yaml = yaml_text

            logging.debug(f"Successfully rendered YAML for {self.resource_type}/{self.resource_name}")
            
            # Set success flag after successful data load (thread-safe via QTimer)
            QTimer.singleShot(0, lambda: setattr(self, '_reload_success', True))

        except Exception as e:
            error_message = f"Error rendering YAML: {str(e)}"
            logging.error(f"YAML rendering error for {self.resource_type}/{self.resource_name}: {e}")
            self.yaml_editor.setPlainText(f"# {error_message}\n# Raw data:\n{str(data)}")
            self.handle_error(error_message)

    def _convert_to_kubernetes_yaml(self, data):
        """Convert Python client dict format to Kubernetes YAML format - Pod-safe version"""
        def snake_to_camel(snake_str):
            """Convert snake_case to camelCase"""
            if '_' not in snake_str:
                return snake_str

            components = snake_str.split('_')
            return components[0] + ''.join(word.capitalize() for word in components[1:])

        def convert_dict(obj):
            """Recursively convert dict keys from snake_case to camelCase"""
            if isinstance(obj, dict):
                new_dict = {}
                for key, value in obj.items():
                    # Convert snake_case keys to camelCase
                    new_key = snake_to_camel(key)
                    # Skip null values to avoid sending them in patch
                    if value is not None:
                        new_dict[new_key] = convert_dict(value)
                return new_dict
            elif isinstance(obj, list):
                return [convert_dict(item) for item in obj if item is not None]
            else:
                return obj

        converted_data = convert_dict(data)

        # Clean up the YAML by removing fields that shouldn't be edited
        if isinstance(converted_data, dict):
            # Remove read-only metadata fields
            metadata_fields_to_remove = [
                'managedFields',
                'resourceVersion',
                'uid',
                'selfLink',
                'creationTimestamp',
                'generation',
                'ownerReferences'  # Add this - Pods owned by ReplicaSets shouldn't be edited
            ]

            if 'metadata' in converted_data:
                for field in metadata_fields_to_remove:
                    if field in converted_data['metadata']:
                        del converted_data['metadata'][field]

            # Remove the entire status section as it's read-only
            if 'status' in converted_data:
                del converted_data['status']

            # Remove events as they're read-only
            if 'events' in converted_data:
                del converted_data['events']

            # Add apiVersion if missing for better YAML completeness
            if 'apiVersion' not in converted_data and 'kind' in converted_data:
                kind = converted_data['kind']
                # Add appropriate apiVersion based on resource kind
                api_version_mapping = {
                    'PriorityClass': 'scheduling.k8s.io/v1',
                    'RuntimeClass': 'node.k8s.io/v1',
                    'HorizontalPodAutoscaler': 'autoscaling/v2',
                    'PodDisruptionBudget': 'policy/v1',
                    'MutatingWebhookConfiguration': 'admissionregistration.k8s.io/v1',
                    'ValidatingWebhookConfiguration': 'admissionregistration.k8s.io/v1',
                    'Lease': 'coordination.k8s.io/v1',
                    'CustomResourceDefinition': 'apiextensions.k8s.io/v1',
                    # Common v1 resources
                    'ReplicationController': 'v1',
                    'LimitRange': 'v1',
                    'ResourceQuota': 'v1',
                    'ServiceAccount': 'v1',
                    'Endpoints': 'v1',
                    'Role': 'rbac.authorization.k8s.io/v1',
                    'RoleBinding': 'rbac.authorization.k8s.io/v1',
                    'ClusterRole': 'rbac.authorization.k8s.io/v1',
                    'ClusterRoleBinding': 'rbac.authorization.k8s.io/v1',
                }
                if kind in api_version_mapping:
                    converted_data['apiVersion'] = api_version_mapping[kind]

            # For Pods specifically, clean up the spec to only include editable fields
            if converted_data.get('kind') == 'Pod' and 'spec' in converted_data:
                spec = converted_data['spec']

                # Keep only the fields that are allowed to be changed in Pods
                editable_pod_spec = {}

                # Only send name (strategic merge key) + image (only mutable container field)
                # Sending full container objects (ports, env, resources, etc.) causes:
                # 1. Strategic merge patch ambiguity on duplicate containerPort values → "Duplicate value" error
                # 2. Kubernetes immutability rejection → "Forbidden: pod updates may not change fields other than..."
                if 'containers' in spec:
                    editable_pod_spec['containers'] = [
                        {k: c[k] for k in ('name', 'image') if k in c}
                        for c in spec['containers']
                    ]

                # Keep initContainers if present (same restriction applies)
                if 'initContainers' in spec:
                    editable_pod_spec['initContainers'] = [
                        {k: c[k] for k in ('name', 'image') if k in c}
                        for c in spec['initContainers']
                    ]

                # Keep activeDeadlineSeconds if present
                if 'activeDeadlineSeconds' in spec:
                    editable_pod_spec['activeDeadlineSeconds'] = spec['activeDeadlineSeconds']

                # Keep terminationGracePeriodSeconds if present
                if 'terminationGracePeriodSeconds' in spec:
                    editable_pod_spec['terminationGracePeriodSeconds'] = spec['terminationGracePeriodSeconds']

                # Keep tolerations if present (only additions allowed)
                if 'tolerations' in spec:
                    editable_pod_spec['tolerations'] = spec['tolerations']

                # Replace the spec with only editable fields
                converted_data['spec'] = editable_pod_spec

        return converted_data

    def toggle_yaml_edit_mode(self):
        """Toggle between read-only and edit mode"""
        if self.is_helm_resource:
            return  # Should not reach here, but safety check

        if self.yaml_editor.isReadOnly():
            # Enter edit mode
            self.yaml_editor.setReadOnly(False)
            self.yaml_edit_button.hide()
            self.yaml_save_button.show()
            self.yaml_cancel_button.show()

            self.yaml_editor.setStyleSheet(YAMLSectionStyles.get_yaml_editor_edit_style())
            self.original_yaml = self.yaml_editor.toPlainText()
        else:
            # Exit edit mode
            self.yaml_editor.setReadOnly(True)
            self.yaml_edit_button.show()
            self.yaml_save_button.hide()
            self.yaml_cancel_button.hide()

            self.yaml_editor.setStyleSheet(YAMLSectionStyles.get_yaml_editor_readonly_style())

    def save_yaml_changes(self):
        """Save YAML changes using Kubernetes API"""
        try:
            if self.is_helm_resource:
                self.handle_error("Helm resources cannot be edited via YAML")
                return

            # Check if editor exists
            if not hasattr(self, 'yaml_editor') or not self.yaml_editor:
                self.handle_error("YAML editor not available")
                return

            yaml_text = self.yaml_editor.toPlainText()

            if yaml_text == self.original_yaml:
                self.toggle_yaml_edit_mode()
                return

            # Check if kubernetes client is available
            if not self.kubernetes_client:
                self.handle_error("Kubernetes client not available")
                return

            try:
                # Step 1: Validate YAML syntax
                yaml_data = yaml.safe_load(yaml_text)
                if not yaml_data:
                    self.handle_error("Invalid YAML: Empty or null document")
                    return

                # Step 2: Validate Kubernetes schema
                if hasattr(self.kubernetes_client, 'validate_kubernetes_schema'):
                    schema_valid, schema_error = self.kubernetes_client.validate_kubernetes_schema(yaml_data)
                    if not schema_valid:
                        self.handle_error(f"Schema validation failed: {schema_error}")
                        return
                else:
                    logging.warning("Schema validation not available, proceeding without validation")

                # Step 3: Show loading state
                if hasattr(self, 'show_loading'):
                    self.show_loading()

                if hasattr(self, 'yaml_save_button') and self.yaml_save_button:
                    self.yaml_save_button.setEnabled(False)
                    self.yaml_save_button.setText("Deploying...")

                # Step 4: Update resource asynchronously
                if hasattr(self.kubernetes_client, 'update_resource_async'):
                    self.kubernetes_client.update_resource_async(
                        self.resource_type,
                        self.resource_name,
                        self.resource_namespace,
                        yaml_data
                    )
                    logging.info(f"YAML update initiated for {self.resource_type}/{self.resource_name}")
                else:
                    self.handle_error("Resource update functionality not available")
                    self._reset_save_button()

            except yaml.YAMLError as e:
                self.handle_error(f"Invalid YAML syntax: {str(e)}")
                self._reset_save_button()
            except Exception as e:
                self.handle_error(f"Error preparing YAML update: {str(e)}")
                self._reset_save_button()

        except Exception as e:
            logging.error(f"Critical error in save_yaml_changes: {str(e)}")
            self.handle_error(f"Critical error: {str(e)}")
            self._reset_save_button()

    def _reset_save_button(self):
        """Reset save button state after error"""
        try:
            if hasattr(self, 'hide_loading'):
                self.hide_loading()
            if hasattr(self, 'yaml_save_button') and self.yaml_save_button:
                self.yaml_save_button.setEnabled(True)
                self.yaml_save_button.setText("Deploy")
        except Exception as e:
            logging.error(f"Error resetting save button: {str(e)}")

    def handle_resource_update_result(self, result):
        """Handle the result of resource update operation"""
        try:
            # Reset UI state safely
            if hasattr(self, 'hide_loading'):
                try:
                    self.hide_loading()
                except Exception as e:
                    logging.error(f"Error hiding loading state: {str(e)}")

            if hasattr(self, 'yaml_save_button') and self.yaml_save_button:
                try:
                    self.yaml_save_button.setEnabled(True)
                    self.yaml_save_button.setText("Deploy")
                except Exception as e:
                    logging.error(f"Error resetting save button: {str(e)}")

            # Handle result
            if not result or not isinstance(result, dict):
                self.handle_error("Invalid update result received")
                return

            if result.get('success', False):
                # Success
                message = result.get('message', 'Resource updated successfully')
                logging.info(f"YAML update successful: {message}")

                try:
                    # Exit edit mode
                    self.toggle_yaml_edit_mode()
                except Exception as e:
                    logging.error(f"Error toggling edit mode: {str(e)}")

                try:
                    # Refresh the current YAML content - now thread-safe with queued connection
                    if hasattr(self, 'load_data'):
                        self.schedule_data_reload()
                except Exception as e:
                    logging.error(f"Error scheduling data reload: {str(e)}")

                try:
                    # Emit signal to refresh main resource list page - now thread-safe with queued connection
                    if hasattr(self, 'data_loaded') and hasattr(self, 'section_name'):
                        self.data_loaded.emit(self.section_name, {
                            'action': 'refresh_main_page',
                            'resource_type': getattr(self, 'resource_type', ''),
                            'resource_name': getattr(self, 'resource_name', ''),
                            'namespace': getattr(self, 'resource_namespace', '')
                        })
                except Exception as e:
                    logging.error(f"Error emitting refresh signal: {str(e)}")

            else:
                # Error
                error_message = result.get('message', 'Unknown error occurred')
                self.handle_error(f"Deployment failed: {error_message}")

        except Exception as e:
            logging.error(f"Critical error in handle_resource_update_result: {str(e)}")
            try:
                self.handle_error(f"Error handling update result: {str(e)}")
            except Exception as inner_e:
                logging.error(f"Failed to show error message: {str(inner_e)}")

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
        self.is_helm_resource = False

        if not self.yaml_editor.isReadOnly():
            self.toggle_yaml_edit_mode()

    def schedule_data_reload(self):
        """Schedule a data reload with a configurable delay to allow changes to propagate"""
        # Reset retry counter and success flag when starting a new reload sequence
        self.reload_retry_count = 0
        self._reload_success = False
        self._reload_in_progress = True  # Force API fetch, bypass current_data cache
        self._perform_scheduled_reload()

    def _perform_scheduled_reload(self):
        """Execute the scheduled reload and handle retries"""
        if hasattr(self, 'load_data'):
            logging.debug(f"YAML section: Scheduled data reload (attempt {self.reload_retry_count + 1}/{self.MAX_RELOAD_RETRIES})")
            # Use QTimer for thread safety and delay
            QTimer.singleShot(self.RELOAD_DELAY_MS, self.load_data)
            
            # Simple retry mechanism: schedule another reload if we haven't maxed out
            # This helps catch updates that might take longer than the initial delay
            self.reload_retry_count += 1
            if self.reload_retry_count < self.MAX_RELOAD_RETRIES:
                # Schedule next check with increased delay (backoff)
                backoff_delay = self.RELOAD_DELAY_MS * (self.reload_retry_count + 1)
                QTimer.singleShot(backoff_delay, self._check_and_reload_again)

    def _check_and_reload_again(self):
        """Helper to continue the reload sequence"""
        # Short-circuit if reload has already succeeded
        if self._reload_success:
            return
        
        if self.isVisible(): # Only reload if still visible
            self._reload_in_progress = True  # Force API fetch, bypass current_data cache
            self.load_data()

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
