# orchetrix/Pages/ComparePage.py
import logging
import yaml
import json
import os
import sys
import tempfile
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSizePolicy, QPushButton, QSplitter, QListView, QLineEdit, QMenu, QWidgetAction
)
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QKeySequence, QShortcut, QAction
from PyQt6.QtCore import Qt, QPoint, QTimer

from Utils.unified_resource_loader import get_unified_resource_loader
from Utils.cluster_connector import get_cluster_connector

from UI.detail_sections.detailpage_yamlsection import YamlEditorWithLineNumbers, DetailPageYAMLSection

from UI.Styles import AppStyles

LOG = logging.getLogger(__name__)


class YAMLCompareHighlighter(QSyntaxHighlighter):
    """Granular line-by-line highlighter for YAML comparison with syntax error detection"""

    def __init__(self, document):
        super().__init__(document)
        self.different_lines = set()
        self.matching_lines = set()
        self.granular_highlights = {}  # {line_number: [(start, end, format)]}
        LOG.info(f"[HIGHLIGHTER_LOG] YAMLCompareHighlighter created for document: {type(document).__name__ if document else 'None'}")
        
        self.fmt_red = QTextCharFormat()
        self.fmt_red.setForeground(QColor("red"))
        self.fmt_green = QTextCharFormat()
        self.fmt_green.setForeground(QColor("green"))
        
        # Format for syntax errors
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor("#FF0000"))
        self.error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        self.error_format.setForeground(QColor("#FF4444"))

    def set_comparison_lines(self, different_lines, matching_lines, granular_highlights=None):
        LOG.info(f"[HIGHLIGHTER_LOG] === set_comparison_lines START ===")
        LOG.info(f"[HIGHLIGHTER_LOG] Document info: {self.document() is not None}, blocks: {self.document().blockCount() if self.document() else 'N/A'}")
        LOG.info(f"[HIGHLIGHTER_LOG]   - different_lines: {different_lines}")
        LOG.info(f"[HIGHLIGHTER_LOG]   - different_lines type: {type(different_lines)}")
        LOG.info(f"[HIGHLIGHTER_LOG]   - matching_lines: {matching_lines}")
        LOG.info(f"[HIGHLIGHTER_LOG]   - matching_lines type: {type(matching_lines)}")
        LOG.info(f"[HIGHLIGHTER_LOG]   - granular_highlights: {granular_highlights}")
        LOG.info(f"[HIGHLIGHTER_LOG]   - granular_highlights type: {type(granular_highlights)}")
        
        # Log current highlighter state before changes
        LOG.info(f"[HIGHLIGHTER_LOG] BEFORE - Current different_lines: {getattr(self, 'different_lines', 'NOT_SET')}")
        LOG.info(f"[HIGHLIGHTER_LOG] BEFORE - Current matching_lines: {getattr(self, 'matching_lines', 'NOT_SET')}")
        LOG.info(f"[HIGHLIGHTER_LOG] BEFORE - Current granular_highlights: {getattr(self, 'granular_highlights', 'NOT_SET')}")
        
        # Detailed inspection of granular_highlights
        if granular_highlights:
            LOG.info(f"[HIGHLIGHTER_LOG] Granular highlights detailed inspection:")
            for line_num, highlight_data in granular_highlights.items():
                LOG.info(f"[HIGHLIGHTER_LOG]   - Line {line_num}: {highlight_data}")
                LOG.info(f"[HIGHLIGHTER_LOG]   - Line {line_num} data type: {type(highlight_data)}")
                if isinstance(highlight_data, (list, tuple)):
                    for i, item in enumerate(highlight_data):
                        LOG.info(f"[HIGHLIGHTER_LOG]     - Item {i}: {item} (type: {type(item)})")
                        if isinstance(item, (list, tuple)) and len(item) >= 3:
                            LOG.info(f"[HIGHLIGHTER_LOG]       - Element 0: {item[0]} (type: {type(item[0])})")
                            LOG.info(f"[HIGHLIGHTER_LOG]       - Element 1: {item[1]} (type: {type(item[1])})")
                            LOG.info(f"[HIGHLIGHTER_LOG]       - Element 2: {item[2]} (type: {type(item[2])})")
                        else:
                            LOG.error(f"[HIGHLIGHTER_LOG]       - INVALID ITEM STRUCTURE: {item}")
                else:
                    LOG.error(f"[HIGHLIGHTER_LOG]   - INVALID HIGHLIGHT DATA TYPE: {type(highlight_data)}")
        
        self.different_lines = set(different_lines or [])
        self.matching_lines = set(matching_lines or [])
        self.granular_highlights = granular_highlights or {}
        
        LOG.info(f"[HIGHLIGHTER_LOG] Data assigned to instance variables:")
        LOG.info(f"[HIGHLIGHTER_LOG]   - self.different_lines: {self.different_lines}")
        LOG.info(f"[HIGHLIGHTER_LOG]   - self.matching_lines: {self.matching_lines}")
        LOG.info(f"[HIGHLIGHTER_LOG]   - self.granular_highlights: {self.granular_highlights}")
        
        LOG.info(f"[HIGHLIGHTER_LOG] About to call rehighlight() to apply changes")
        LOG.info(f"[HIGHLIGHTER_LOG] Document state before rehighlight: blocks={self.document().blockCount()}, chars={self.document().characterCount()}")
        
        try:
            self.rehighlight()
            LOG.info(f"[HIGHLIGHTER_LOG] rehighlight() completed successfully")
        except Exception as rehighlight_error:
            LOG.error(f"[HIGHLIGHTER_LOG] ERROR in rehighlight(): {rehighlight_error}")
            import traceback
            LOG.error(f"[HIGHLIGHTER_LOG] rehighlight() traceback: {traceback.format_exc()}")
        
        LOG.info(f"[HIGHLIGHTER_LOG] Document state after rehighlight: blocks={self.document().blockCount()}, chars={self.document().characterCount()}")
        LOG.info(f"[HIGHLIGHTER_LOG] === set_comparison_lines END ===")

    def highlightBlock(self, text: str):
        try:
            block_number = self.currentBlock().blockNumber()
            
            # Only log first 20 blocks to avoid spam, but log all errors
            should_log_detail = block_number < 20
            
            if should_log_detail:
                LOG.info(f"[HIGHLIGHTER_LOG] === highlightBlock START for block {block_number} ===")
                LOG.info(f"[HIGHLIGHTER_LOG]   - text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                LOG.info(f"[HIGHLIGHTER_LOG]   - text length: {len(text)}")
                LOG.info(f"[HIGHLIGHTER_LOG]   - block in different_lines: {block_number in self.different_lines}")
                LOG.info(f"[HIGHLIGHTER_LOG]   - block in matching_lines: {block_number in self.matching_lines}")
                LOG.info(f"[HIGHLIGHTER_LOG]   - block in granular_highlights: {block_number in self.granular_highlights}")
                LOG.info(f"[HIGHLIGHTER_LOG]   - TIMING: About to apply highlighting at {datetime.now().strftime('%H:%M:%S.%f')}")
            elif block_number == 20:
                LOG.info(f"[HIGHLIGHTER_LOG] Processed first 20 blocks, switching to error-only logging...")
            
            # Check for granular highlighting first
            if block_number in self.granular_highlights:
                if should_log_detail:
                    LOG.info(f"[HIGHLIGHTER_LOG] === GRANULAR HIGHLIGHTING START for block {block_number} ===")
                granular_data = self.granular_highlights[block_number]
                if should_log_detail:
                    LOG.info(f"[HIGHLIGHTER_LOG]   - granular data: {granular_data}")
                    LOG.info(f"[HIGHLIGHTER_LOG]   - granular data type: {type(granular_data)}")
                
                if not isinstance(granular_data, (list, tuple)):
                    LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR: granular_data is not list/tuple: {type(granular_data)} for block {block_number}")
                    LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR: granular_data content: {repr(granular_data)}")
                    LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR: This is likely the 'int object is not subscriptable' bug!")
                    return
                
                # Apply granular character-level highlighting
                for i, highlight_data in enumerate(granular_data):
                    try:
                        LOG.info(f"[HIGHLIGHTER_LOG]   - processing highlight {i}: {highlight_data}")
                        LOG.info(f"[HIGHLIGHTER_LOG]   - highlight_data type: {type(highlight_data)}")
                        
                        # CRITICAL: Add detailed type checking and error handling
                        if highlight_data is None:
                            LOG.error(f"[HIGHLIGHTER_LOG] ERROR: highlight_data is None at index {i}")
                            continue
                        
                        if not isinstance(highlight_data, (tuple, list)):
                            LOG.error(f"[HIGHLIGHTER_LOG] ERROR: highlight_data is not tuple/list: {type(highlight_data)}")
                            continue
                        
                        if len(highlight_data) < 3:
                            LOG.error(f"[HIGHLIGHTER_LOG] ERROR: highlight_data has insufficient elements: {len(highlight_data)}")
                            continue
                        
                        # CRITICAL: Add individual element checking before subscripting
                        try:
                            start_element = highlight_data[0]
                            end_element = highlight_data[1]
                            format_element = highlight_data[2]
                            
                            LOG.info(f"[HIGHLIGHTER_LOG]   - start_element: {start_element} (type: {type(start_element)})")
                            LOG.info(f"[HIGHLIGHTER_LOG]   - end_element: {end_element} (type: {type(end_element)})")
                            LOG.info(f"[HIGHLIGHTER_LOG]   - format_element: {format_element} (type: {type(format_element)})")
                            
                        except (IndexError, TypeError) as subscript_error:
                            LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR: Failed to subscript highlight_data[{i}] for block {block_number}: {subscript_error}")
                            LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR: highlight_data content: {repr(highlight_data)}")
                            LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR: granular_data full content: {repr(granular_data)}")
                            LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR: This is the 'int' object is not subscriptable error source!")
                            continue
                        
                        # Ensure start and end are integers
                        if not isinstance(start_element, int) or not isinstance(end_element, int):
                            LOG.error(f"[HIGHLIGHTER_LOG] ERROR: start/end not integers: start={type(start_element)}, end={type(end_element)}")
                            continue
                        
                        start, end, format_type = start_element, end_element, format_element
                        LOG.info(f"[HIGHLIGHTER_LOG]   - granular highlight {i}: start={start}, end={end}, type={format_type}")
                        
                        # Validate range
                        if start < 0 or end < 0 or start > len(text) or end > len(text) or start >= end:
                            LOG.error(f"[HIGHLIGHTER_LOG] ERROR: Invalid range start={start}, end={end}, text_len={len(text)}")
                            continue
                        
                        if format_type == 'red':
                            self.setFormat(start, end - start, self.fmt_red)
                            if should_log_detail:
                                LOG.info(f"[HIGHLIGHTER_LOG]   - APPLIED RED format to chars {start}-{end} at {datetime.now().strftime('%H:%M:%S.%f')}")
                        elif format_type == 'green':
                            self.setFormat(start, end - start, self.fmt_green)
                            if should_log_detail:
                                LOG.info(f"[HIGHLIGHTER_LOG]   - APPLIED GREEN format to chars {start}-{end} at {datetime.now().strftime('%H:%M:%S.%f')}")
                        else:
                            if should_log_detail:
                                LOG.info(f"[HIGHLIGHTER_LOG]   - skipping unknown format type: {format_type}")
                            
                    except Exception as highlight_error:
                        LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR processing highlight {i}: {highlight_error}")
                        LOG.error(f"[HIGHLIGHTER_LOG] highlight_data: {repr(highlight_data)}")
                        import traceback
                        LOG.error(f"[HIGHLIGHTER_LOG] Traceback: {traceback.format_exc()}")
                        continue
                        
                if should_log_detail:
                    LOG.info(f"[HIGHLIGHTER_LOG] === GRANULAR HIGHLIGHTING END for block {block_number} ===")
            else:
                # Fall back to line-level highlighting
                if should_log_detail:
                    LOG.info(f"[HIGHLIGHTER_LOG] === LINE-LEVEL HIGHLIGHTING for block {block_number} ===")
                if block_number in self.different_lines:
                    if should_log_detail:
                        LOG.info(f"[HIGHLIGHTER_LOG] Applying DIFFERENT line highlighting for block {block_number}")
                    self.setFormat(0, len(text), self.fmt_red)
                    if should_log_detail:
                        LOG.info(f"[HIGHLIGHTER_LOG]   - APPLIED FULL RED to entire line at {datetime.now().strftime('%H:%M:%S.%f')}")
                elif block_number in self.matching_lines:
                    if should_log_detail:
                        LOG.info(f"[HIGHLIGHTER_LOG] Applying MATCHING line highlighting for block {block_number}")
                    self.setFormat(0, len(text), self.fmt_green)
                    if should_log_detail:
                        LOG.info(f"[HIGHLIGHTER_LOG]   - APPLIED FULL GREEN to entire line at {datetime.now().strftime('%H:%M:%S.%f')}")
                else:
                    if should_log_detail:
                        LOG.info(f"[HIGHLIGHTER_LOG] No highlighting applied for block {block_number} - WHITE/DEFAULT")
            
            if should_log_detail:
                LOG.info(f"[HIGHLIGHTER_LOG] === highlightBlock END for block {block_number} at {datetime.now().strftime('%H:%M:%S.%f')} ===")
            
        except Exception as main_error:
            LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR in highlightBlock for block {block_number}: {main_error}")
            LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR: text content: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            import traceback
            LOG.error(f"[HIGHLIGHTER_LOG] CRITICAL ERROR: Full traceback: {traceback.format_exc()}")
            # Don't re-raise to avoid breaking the UI
        
        # VERIFICATION: Comment out YAML error highlighting to test if this is the root cause
        # Check for syntax errors in this line
        # LOG.info(f"[HIGHLIGHTER_LOG] Calling _highlight_yaml_errors for block {block_number}")
        # self._highlight_yaml_errors(text)
        # LOG.info(f"[HIGHLIGHTER_LOG] _highlight_yaml_errors completed for block {block_number}")
    
    def _highlight_yaml_errors(self, text):
        """Highlight YAML syntax errors in real-time"""
        import re
        
        LOG.info(f"[YAML_ERROR_LOG] _highlight_yaml_errors called with text: '{text[:100]}'")
        
        # Skip empty lines, comments, and list items
        stripped = text.strip()
        if not stripped or stripped.startswith('#') or stripped.startswith('-'):
            LOG.info(f"[YAML_ERROR_LOG] Skipping line - empty/comment/list item")
            return

        # Check for the specific "backeend:django" type error (missing space after colon)
        colon_match = re.search(r'^\s*(\w+):([\w-]+)', text)
        if colon_match:
            # Found key:value without space after colon
            key = colon_match.group(1)
            value = colon_match.group(2)
            colon_pos = text.find(':')
            
            LOG.warning(f"[YAML_ERROR_LOG] FOUND COLON ERROR! key='{key}', value='{value}', colon_pos={colon_pos}")
            LOG.warning(f"[YAML_ERROR_LOG] Text: '{text}'")
            
            # Highlight the problematic part (from colon to end of value)
            error_start = colon_pos
            error_end = colon_pos + 1 + len(value)
            
            LOG.warning(f"[YAML_ERROR_LOG] APPLYING RED ERROR FORMAT: start={error_start}, length={error_end - error_start}")
            LOG.warning(f"[YAML_ERROR_LOG] Red highlighted text: '{text[error_start:error_end]}'")
            
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
                LOG.warning(f"[YAML_ERROR_LOG] FOUND ERROR PATTERN: '{error_type}' in text: '{text}'")
                
                # Don't highlight if this looks like a valid YAML structure
                if pattern == r'^\s*\w+\s*$':
                    # Check if next line is properly indented child
                    current_block = self.currentBlock()
                    next_block = current_block.next()
                    if next_block.isValid():
                        next_text = next_block.text().strip()
                        if next_text and (next_text.startswith('- ') or ':' in next_text):
                            LOG.info(f"[YAML_ERROR_LOG] Skipping error - valid YAML structure detected")
                            continue  # This is likely valid YAML
                
                LOG.warning(f"[YAML_ERROR_LOG] APPLYING RED ERROR FORMAT to entire line: '{text}'")
                self.setFormat(0, len(text), self.error_format)
                break

        # Additional check for malformed key-value pairs
        if ':' in text and not re.search(r'^\s*[\w-]+\s*:\s+', text):
            colon_pos = text.find(':')
            if colon_pos > 0:  # Not at start of line
                # Check if there's proper spacing
                before_colon = text[:colon_pos].strip()
                after_colon = text[colon_pos+1:]
                
                LOG.info(f"[YAML_ERROR_LOG] Checking malformed key-value: before='{before_colon}', after='{after_colon}'")
                
                if before_colon and after_colon.strip():  # Both key and value present
                    if not after_colon.startswith(' '):  # No space after colon
                        highlight_length = len(after_colon.split()[0]) + 1
                        LOG.warning(f"[YAML_ERROR_LOG] FOUND MALFORMED KEY-VALUE! No space after colon")
                        LOG.warning(f"[YAML_ERROR_LOG] APPLYING RED ERROR FORMAT: start={colon_pos}, length={highlight_length}")
                        LOG.warning(f"[YAML_ERROR_LOG] Red highlighted text: '{text[colon_pos:colon_pos+highlight_length]}'")
                        
                        self.setFormat(colon_pos, highlight_length, self.error_format)
        
        LOG.info(f"[YAML_ERROR_LOG] _highlight_yaml_errors completed - no errors found")


class ComparePage(QWidget):
    """
    ComparePage with defensive handling of unified loader results:
      - populates namespaces via unified loader
      - rejects stale/irrelevant loader responses
      - refreshes on showEvent and after cluster switches
      - simple YAML side-by-side view for Compare button
    """

    KNOWN_KINDS = [
        "Pod", "Service", "ConfigMap", "Secret", "PersistentVolumeClaim",
        "Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job",
        "CronJob", "Ingress", "Node"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.font_family = "Consolas"
        self.font_size = 9

        # Simple loader state
        self._namespaces_loaded = False
        self.namespace_filter = "default"  # Initialize namespace filter for state persistence

        # Edit state management
        self._left_edit_mode = False
        self._right_edit_mode = False
        self._left_original_yaml = None
        self._right_original_yaml = None
        self._left_resource_info = None  # (namespace, resource_type, name)
        self._right_resource_info = None
        
        # Real-time highlighting state
        self._highlight_timer = QTimer()
        self._highlight_timer.setSingleShot(True)
        self._highlight_timer.timeout.connect(self._update_realtime_highlighting)
        self._realtime_highlighting_enabled = True

        # Initialize cluster connector
        self.cluster_connector = get_cluster_connector()

        self._build_ui()

        # Connect to app shutdown signal for reliable cleanup
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(self._clear_all_local_saves)

        self._populate_namespaces()

        # Remove redundant cluster signal handlers to prevent conflicts with ClusterView clearing

    def _request_namespaces(self):
        """Request namespaces using unified loader."""
        try:
            loader = get_unified_resource_loader()
            # Connect signals if not already connected (same pattern as BaseResourcePage)
            if not hasattr(self, '_namespace_signals_connected'):
                loader.loading_completed.connect(self._on_unified_loader_completed)
                loader.loading_error.connect(self._on_namespace_error_unified)
                self._namespace_signals_connected = True
            loader.load_resources_async("namespaces")
        except Exception:
            LOG.exception("ComparePage: Failed to request namespaces")

    # ---------------------- UI building ----------------------
    def _build_ui(self):
        # Top-level layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)
        self.setLayout(self.main_layout)

        # Section header label (will be placed in a top bar with controls)
        self.header = QLabel("Compare")
        self.header.setObjectName("header")
        self.header.setStyleSheet(AppStyles.TITLE_STYLE)
        self.header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header.setFixedHeight(32)

        # Controls row (below header)
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        controls_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        def add_control(label_text, combo_name, placeholder):
            lbl = QLabel(label_text)
            lbl.setObjectName("form_label")
            lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            lbl.setFixedHeight(32)
            lbl.setMinimumWidth(70)
            lbl.setContentsMargins(0, 0, 8, 0)
            lbl.setStyleSheet(AppStyles.TEXT_STYLE)

            combo = QComboBox()
            combo.setObjectName(combo_name)
            combo.setEditable(False)
            combo.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
            combo.setFixedHeight(32)
            combo.setMinimumWidth(120)
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(1)
            combo.addItem(placeholder)

            # Match other pages: use dropdown style with visible arrow
            combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())

            # Configure dropdown behavior to match other pages
            view = QListView()
            combo.setView(view)
            combo.setMaxVisibleItems(10)
            view.setUniformItemSizes(True)
            view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)

            controls_layout.addWidget(lbl)
            controls_layout.addWidget(combo)
            return combo

        self.namespace_combo = add_control("Namespace:", "namespace_combo", "Loading namespaces…")
        self.resource_type_combo = add_control("Resource Type:", "resource_type_combo", "Select resource type")

        # Add stretch to push the Compare button to the right
        controls_layout.addStretch(1)
        controls_layout.addSpacing(12)

        self.compare_btn = QPushButton("Compare")
        self.compare_btn.setStyleSheet(AppStyles.BUTTON_PRIMARY_STYLE)
        self.compare_btn.setMinimumHeight(32)
        self.compare_btn.setContentsMargins(0, 0, 0, 0)
        self.compare_btn.setObjectName("compare_button")
        self.compare_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.compare_btn.setEnabled(False)
        controls_layout.addWidget(self.compare_btn)

        # Build a single top bar with title on the left and controls on the right
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(12)
        top_bar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        top_bar.setMinimumHeight(72)
        top_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        top_bar_layout.addWidget(self.header)
        top_bar_layout.addStretch(1)
        top_bar_layout.addWidget(controls_widget)

        self.main_layout.addWidget(top_bar)

        # Create resource combos (will be placed in always-visible row)
        self.resource1_combo = self._create_searchable_combo("Select resource 1", "resource1")
        self.resource1_combo.setObjectName("resource1_combo")

        self.resource2_combo = self._create_searchable_combo("Select resource 2", "resource2")
        self.resource2_combo.setObjectName("resource2_combo")

        # Resource selector row - always visible (moved out of compare_area)
        resource_select_row = QWidget()
        resource_select_layout = QHBoxLayout(resource_select_row)
        resource_select_layout.setContentsMargins(0, 0, 0, 0)
        resource_select_layout.setSpacing(12)
        resource_select_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        resource_select_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Left selector (label + existing combo)
        left_group = QWidget()
        left_group_layout = QHBoxLayout(left_group)
        left_group_layout.setContentsMargins(0, 0, 0, 0)
        left_group_layout.setSpacing(8)
        left_label = QLabel("Resource 1:")
        left_label.setFixedHeight(32)
        left_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        left_label.setStyleSheet(AppStyles.TEXT_STYLE)
        left_group_layout.addWidget(left_label)
        left_group_layout.addWidget(self.resource1_combo)
        left_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Right selector (existing combo + label)
        right_group = QWidget()
        right_group_layout = QHBoxLayout(right_group)
        right_group_layout.setContentsMargins(0, 0, 0, 0)
        right_group_layout.setSpacing(8)
        right_label = QLabel("Resource 2:")
        right_label.setFixedHeight(32)
        right_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        right_label.setStyleSheet(AppStyles.TEXT_STYLE)
        right_group_layout.addWidget(right_label)
        right_group_layout.addWidget(self.resource2_combo)
        right_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        resource_select_layout.addWidget(left_group)
        resource_select_layout.addStretch()
        resource_select_layout.addWidget(right_group)

        # add the always-visible selectors row to main layout (above compare_area)
        self.main_layout.addWidget(resource_select_row)

        # Compare area - expanded to fill available space
        self.compare_area = QWidget()
        compare_layout = QVBoxLayout(self.compare_area)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        compare_layout.setSpacing(8)
        compare_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.compare_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Header row with resource labels and edit buttons
        header_row = QHBoxLayout()

        # Left side: label + edit buttons
        left_container = QHBoxLayout()
        self.left_label = QLabel("")
        self.left_edit_btn = QPushButton("Edit")
        self.left_save_btn = QPushButton("Save")
        self.left_deploy_btn = QPushButton("Deploy")
        self.left_cancel_btn = QPushButton("Cancel")

        # Style buttons like DetailPageYAMLSection
        self.left_edit_btn.setStyleSheet("""
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
        """)
        # Save button uses refresh button style (SECONDARY_BUTTON_STYLE)
        self.left_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """)
        self.left_deploy_btn.setStyleSheet("""
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
        """)
        self.left_cancel_btn.setStyleSheet("""
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
        """)

        # Initially hide save/deploy/cancel buttons
        self.left_save_btn.hide()
        self.left_deploy_btn.hide()
        self.left_cancel_btn.hide()

        left_container.addWidget(self.left_label)
        left_container.addWidget(self.left_edit_btn)
        left_container.addWidget(self.left_save_btn)
        left_container.addWidget(self.left_deploy_btn)
        left_container.addWidget(self.left_cancel_btn)
        left_container.addStretch()

        # Right side: label + edit buttons
        right_container = QHBoxLayout()
        self.right_label = QLabel("")
        self.right_edit_btn = QPushButton("Edit")
        self.right_save_btn = QPushButton("Save")
        self.right_deploy_btn = QPushButton("Deploy")
        self.right_cancel_btn = QPushButton("Cancel")

        # Style buttons like DetailPageYAMLSection
        self.right_edit_btn.setStyleSheet("""
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
        """)
        # Save button uses refresh button style (SECONDARY_BUTTON_STYLE)
        self.right_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """)
        self.right_deploy_btn.setStyleSheet("""
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
        """)
        self.right_cancel_btn.setStyleSheet("""
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
        """)

        # Initially hide save/deploy/cancel buttons
        self.right_save_btn.hide()
        self.right_deploy_btn.hide()
        self.right_cancel_btn.hide()

        right_container.addStretch()
        right_container.addWidget(self.right_label)
        right_container.addWidget(self.right_edit_btn)
        right_container.addWidget(self.right_save_btn)
        right_container.addWidget(self.right_deploy_btn)
        right_container.addWidget(self.right_cancel_btn)

        header_row.addLayout(left_container)
        header_row.addStretch()
        header_row.addLayout(right_container)
        header_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        compare_layout.addLayout(header_row)

        # YAML comparison editors inside a splitter with individual search widgets
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Create left editor container with search widget
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.left_box = YamlEditorWithLineNumbers()
        self.left_box.setFont(QFont(self.font_family, self.font_size))
        self.left_box.setReadOnly(True)
        self.left_box.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.left_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.left_box.setMinimumHeight(200)
        self.left_box.setStyleSheet(AppStyles.DETAIL_PAGE_YAML_TEXT_STYLE)

        left_layout.addWidget(self.left_box)

        # Create right editor container with search widget
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.right_box = YamlEditorWithLineNumbers()
        self.right_box.setFont(QFont(self.font_family, self.font_size))
        self.right_box.setReadOnly(True)
        self.right_box.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.right_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.right_box.setMinimumHeight(200)
        self.right_box.setStyleSheet(AppStyles.DETAIL_PAGE_YAML_TEXT_STYLE)

        right_layout.addWidget(self.right_box)

        # Add search functionality with keyboard shortcuts first
        self._setup_search_shortcuts()

        # Create search widgets for both editors
        self._setup_search_widgets(left_layout, right_layout)

        # Create error widgets for both editors
        self._setup_error_widgets(left_layout, right_layout)

        # Create highlighters for granular comparison
        self.left_highlighter = YAMLCompareHighlighter(self.left_box.document())
        self.right_highlighter = YAMLCompareHighlighter(self.right_box.document())

        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([1, 1])
        compare_layout.addWidget(splitter, 1)

        self.compare_area.hide()
        # Add compare area directly to main layout with stretch factor
        self.main_layout.addWidget(self.compare_area, 1)

        # connects
        self.namespace_combo.currentTextChanged.connect(self._on_namespace_changed)
        self.resource_type_combo.currentIndexChanged.connect(self._on_namespace_or_type_changed)
        self.resource1_combo.currentIndexChanged.connect(self._on_resource_selection_changed)
        self.resource2_combo.currentIndexChanged.connect(self._on_resource_selection_changed)
        self.compare_btn.clicked.connect(self._on_compare_clicked)

        # Connect edit button signals
        self.left_edit_btn.clicked.connect(self._toggle_left_edit_mode)
        self.left_save_btn.clicked.connect(self._save_left_changes)
        self.left_deploy_btn.clicked.connect(self._deploy_left_changes)
        self.left_cancel_btn.clicked.connect(self._cancel_left_edit)
        self.right_edit_btn.clicked.connect(self._toggle_right_edit_mode)
        self.right_save_btn.clicked.connect(self._save_right_changes)
        self.right_deploy_btn.clicked.connect(self._deploy_right_changes)
        self.right_cancel_btn.clicked.connect(self._cancel_right_edit)

        # Add click handlers to set focus on editors
        def create_focus_handler(editor):
            original_mouse_press = editor.mousePressEvent

            def mouse_press_with_focus(event):
                editor.setFocus()
                original_mouse_press(event)
            return mouse_press_with_focus

        self.left_box.mousePressEvent = create_focus_handler(self.left_box)
        self.right_box.mousePressEvent = create_focus_handler(self.right_box)
        
        # Connect real-time highlighting
        self._setup_realtime_highlighting()

    def _setup_realtime_highlighting(self):
        """Setup real-time highlighting for both editors"""
        # Connect textChanged signals with debouncing
        self.left_box.textChanged.connect(self._on_text_changed)
        self.right_box.textChanged.connect(self._on_text_changed)
    
    def _on_text_changed(self):
        """Handle text change with debouncing"""
        if not self._realtime_highlighting_enabled:
            return
            
        # Only trigger during edit mode
        if not (self._left_edit_mode or self._right_edit_mode):
            return
            
        # Debounce: restart timer on each change
        self._highlight_timer.stop()
        self._highlight_timer.start(200)  # 200ms delay
    
    def _update_realtime_highlighting(self):
        """Update highlighting in real-time"""
        try:
            left_yaml = self.left_box.toPlainText()
            right_yaml = self.right_box.toPlainText()
            
            # Skip if either editor is empty
            if not left_yaml.strip() or not right_yaml.strip():
                return
            
            # Apply comparison highlighting
            self._apply_comparison_highlighting(left_yaml, right_yaml)
            
        except Exception as e:
            LOG.info(f"Error in real-time highlighting: {e}")

    def _setup_search_widgets(self, left_layout, right_layout):
        """Create search widgets for both editors positioned above each editor"""
        from UI.detail_sections.detailpage_yamlsection import SearchWidget

        # Create and configure search widgets
        for side, editor, layout, close_handler in [
            ('left', self.left_box, left_layout, self._on_left_search_closed),
            ('right', self.right_box, right_layout, self._on_right_search_closed)
        ]:
            search_widget = SearchWidget(self.compare_area, editor=editor)
            search_widget.search_next.connect(editor.search_next)
            search_widget.search_previous.connect(editor.search_previous)
            search_widget.search_closed.connect(close_handler)
            search_widget.hide()

            # Store widget reference
            setattr(self, f'{side}_search_widget', search_widget)

            # Insert search widget at position 0 (above editor) following DetailPageYAMLSection pattern
            layout.insertWidget(0, search_widget)
            editor.search_widget = search_widget

            # Disable built-in search shortcuts to avoid conflicts
            for child in editor.findChildren(QShortcut):
                if child.key() == QKeySequence.StandardKey.Find:
                    child.setEnabled(False)

    def _setup_error_widgets(self, left_layout, right_layout):
        """Create error widgets for both editors positioned above each editor"""
        from PyQt6.QtWidgets import QLabel

        # Create and configure error widgets
        for side, layout in [('left', left_layout), ('right', right_layout)]:
            error_widget = QLabel()
            error_widget.setStyleSheet(f"""
                QLabel {{
                    color: #ff4444;
                    background-color: rgba(255, 68, 68, 0.1);
                    padding: 10px;
                    border-radius: 4px;
                    border: 1px solid rgba(255, 68, 68, 0.3);
                }}
            """)
            error_widget.setWordWrap(True)
            error_widget.hide()

            # Store widget reference
            setattr(self, f'{side}_error_widget', error_widget)

            # Insert error widget at position 0 (above search and editor)
            layout.insertWidget(0, error_widget)

    def _on_left_search_closed(self):
        """Handle left search widget closed"""
        self.left_box.close_search()
        self.left_box.setFocus()

    def _on_right_search_closed(self):
        """Handle right search widget closed"""
        self.right_box.close_search()
        self.right_box.setFocus()

    def _setup_search_shortcuts(self):
        """Setup Ctrl+F and Ctrl+Shift+F shortcuts for both YAML editors"""
        # Ctrl+F: Open/refocus search on focused editor
        self.search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.search_shortcut.activated.connect(self._on_search_requested)

        # Ctrl+Shift+F: Switch to other editor's search
        self.switch_search_shortcut = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        self.switch_search_shortcut.activated.connect(self._on_switch_search_requested)

        # Also create shortcuts directly on the editors as fallback
        self.left_search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self.left_box)
        self.left_search_shortcut.activated.connect(self._show_left_search)

        self.right_search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self.right_box)
        self.right_search_shortcut.activated.connect(self._show_right_search)

    def _on_search_requested(self):
        """Handle Ctrl+F - open/refocus search on focused editor (traditional behavior)"""
        focused_widget = self.focusWidget()

        # Check which search is already visible
        left_visible = hasattr(self, 'left_search_widget') and self.left_search_widget.isVisible()
        right_visible = hasattr(self, 'right_search_widget') and self.right_search_widget.isVisible()

        # Check if search input has focus (search widget is ancestor of focused widget)
        left_search_focused = left_visible and self.left_search_widget.isAncestorOf(focused_widget)
        right_search_focused = right_visible and self.right_search_widget.isAncestorOf(focused_widget)

        # Traditional behavior: refocus if search input already focused
        if left_search_focused:
            # Left search input has focus - just refocus it
            self.left_search_widget.focus_search()
        elif right_search_focused:
            # Right search input has focus - just refocus it
            self.right_search_widget.focus_search()
        elif focused_widget == self.left_box or (focused_widget and self.left_box.isAncestorOf(focused_widget)):
            # Left editor has focus - show left search
            self._show_left_search()
        elif focused_widget == self.right_box or (focused_widget and self.right_box.isAncestorOf(focused_widget)):
            # Right editor has focus - show right search
            self._show_right_search()
        else:
            # Default to left editor
            self.left_box.setFocus()
            self._show_left_search()

    def _on_switch_search_requested(self):
        """Handle Ctrl+Shift+F - switch to other editor's search"""
        left_visible = hasattr(self, 'left_search_widget') and self.left_search_widget.isVisible()
        right_visible = hasattr(self, 'right_search_widget') and self.right_search_widget.isVisible()

        if left_visible:
            # Left search is open, switch to right
            self._show_right_search()
        elif right_visible:
            # Right search is open, switch to left
            self._show_left_search()
        else:
            # No search open, determine by focus and switch to other
            focused_widget = self.focusWidget()
            if focused_widget == self.left_box or (focused_widget and self.left_box.isAncestorOf(focused_widget)):
                self._show_right_search()
            else:
                self._show_left_search()

    def _show_left_search(self):
        """Show search widget for left editor"""
        if hasattr(self, 'left_search_widget'):
            # Hide right search if visible
            if hasattr(self, 'right_search_widget') and self.right_search_widget.isVisible():
                self.right_search_widget.hide()

            self.left_search_widget.show()
            self.left_search_widget.focus_search()

    def _show_right_search(self):
        """Show search widget for right editor"""
        if hasattr(self, 'right_search_widget'):
            # Hide left search if visible
            if hasattr(self, 'left_search_widget') and self.left_search_widget.isVisible():
                self.left_search_widget.hide()

            self.right_search_widget.show()
            self.right_search_widget.focus_search()

    # ------------- font prefs -------------
    def update_yaml_font_size(self, font_size):
        self.font_size = int(font_size)
        font = QFont(self.font_family, self.font_size)
        self.left_box.setFont(font)
        self.right_box.setFont(font)

    def update_yaml_font_family(self, font_family):
        if font_family:
            self.font_family = str(font_family)
        font = QFont(self.font_family, self.font_size)
        self.left_box.setFont(font)
        self.right_box.setFont(font)

    # ------------- namespaces: request & handler -------------
    def _populate_namespaces(self):
        self.namespace_combo.clear()
        self.namespace_combo.addItem("Loading namespaces…")
        self._request_namespaces()

    def _on_unified_loader_completed(self, resource_type, result_obj):
        if resource_type != "namespaces":
            return

        if result_obj.success:
            # Extract namespace names from the processed results (same as BaseResourcePage)
            namespaces = [item.get('name', '') for item in result_obj.items if item.get('name')]

            # Sort namespaces with default first, then alphabetically (same as BaseResourcePage)
            important_namespaces = ["default", "kube-system", "kube-public", "kube-node-lease"]
            other_namespaces = sorted([ns for ns in namespaces if ns not in important_namespaces])
            sorted_namespaces = [ns for ns in important_namespaces if ns in namespaces] + other_namespaces

            self._fill_namespace_combo(sorted_namespaces)
        else:
            self._on_namespace_error_unified('namespaces', result_obj.error_message or "Failed to load namespaces")

        self._namespaces_loaded = True
        LOG.info(f"ComparePage: Loaded namespaces, current filter: {getattr(self, 'namespace_filter', 'not set')}")

    def _on_namespace_error_unified(self, resource_type: str, error_message: str):
        """Handle namespace loading errors from unified loader"""
        if resource_type == 'namespaces':
            LOG.error(f"Failed to load namespaces via unified loader: {error_message}")
            self._fill_namespace_combo(["default", "kube-system", "kube-public"])
            # Ensure namespace filter is set even on error
            if not hasattr(self, 'namespace_filter'):
                self.namespace_filter = "default"

    def _fill_namespace_combo(self, namespaces):
        # Store current selection to restore it
        current_namespace = self.namespace_combo.currentText() if self.namespace_combo.count() > 0 else None

        # Temporarily disconnect signal to prevent unwanted triggers
        try:
            self.namespace_combo.currentTextChanged.disconnect(self._on_namespace_changed)
        except:
            pass

        self.namespace_combo.clear()
        if not namespaces:
            self.namespace_combo.addItem("No namespaces found")
            self.namespace_combo.setEnabled(False)
        else:
            self.namespace_combo.setEnabled(True)
            # Add "All Namespaces" first (like other pages)
            self.namespace_combo.addItem("All Namespaces")
            for ns in namespaces:
                self.namespace_combo.addItem(ns)

            # Enhanced state persistence logic - default to "default" namespace (like other pages)
            if current_namespace and current_namespace not in ["Loading namespaces…", "No namespaces found"]:
                restore_index = self.namespace_combo.findText(current_namespace)
                if restore_index >= 0:
                    self.namespace_combo.setCurrentIndex(restore_index)
                    self.namespace_filter = current_namespace
                else:
                    # If previous selection not found, try default namespace
                    default_index = self.namespace_combo.findText("default")
                    if default_index >= 0:
                        self.namespace_combo.setCurrentIndex(default_index)
                        self.namespace_filter = "default"
                    else:
                        self.namespace_combo.setCurrentIndex(0)
                        self.namespace_filter = "All Namespaces"
            else:
                # No previous selection, try default namespace first (like other pages)
                default_index = self.namespace_combo.findText("default")
                if default_index >= 0:
                    self.namespace_combo.setCurrentIndex(default_index)
                    self.namespace_filter = "default"
                else:
                    self.namespace_combo.setCurrentIndex(0)
                    self.namespace_filter = "All Namespaces"

        # Reconnect the signal
        self.namespace_combo.currentTextChanged.connect(self._on_namespace_changed)

    # ---------- namespace/type -> resources ----------
    def _on_namespace_changed(self, namespace=None):
        # Handle both direct calls and signal calls
        if namespace is None:
            namespace = self.namespace_combo.currentText().strip()
        
        LOG.info(f"[COMPARE_LOG] Namespace changed to: '{namespace}'")

        # Skip if loading placeholder or invalid namespace
        if not namespace or namespace.startswith(("Loading", "No ", "Unable", "kubernetes package")):
            LOG.info(f"[COMPARE_LOG] Skipping invalid namespace: '{namespace}'")
            self._clear_resource_combos()
            return

        # Enhanced state persistence - only proceed if namespace actually changed
        old_namespace = getattr(self, 'namespace_filter', 'default')
        if old_namespace == namespace:
            return  # No change, skip reload

        # Update internal filter
        self.namespace_filter = namespace

        # Store current resource type selection to restore it
        current_resource_type = self.resource_type_combo.currentText() if self.resource_type_combo.count() > 0 else None

        self.resource_type_combo.blockSignals(True)
        self.resource_type_combo.clear()
        self.resource_type_combo.addItem("Scanning…")
        self.resource_type_combo.setEnabled(False)
        self.resource1_combo.clear()
        self.resource1_combo.addItem("Select resource 1")
        self.resource1_combo.setEnabled(False)
        self.resource2_combo.clear()
        self.resource2_combo.addItem("Select resource 2")
        self.resource2_combo.setEnabled(False)

        available = []
        for kind in self.KNOWN_KINDS:
            try:
                if self._list_resources_for_namespace(namespace, kind):
                    available.append(kind)
            except Exception:
                continue

        self.resource_type_combo.clear()
        if not available:
            self.resource_type_combo.addItem("No resource types found")
            self.resource_type_combo.setEnabled(False)
        else:
            self.resource_type_combo.addItem("Select resource type")
            for k in sorted(available):
                self.resource_type_combo.addItem(k)
            self.resource_type_combo.setEnabled(True)

            # Enhanced state persistence for resource type
            if current_resource_type and current_resource_type not in ["Scanning…", "Select resource type", "No resource types found"]:
                restore_index = self.resource_type_combo.findText(current_resource_type)
                if restore_index >= 0:
                    self.resource_type_combo.setCurrentIndex(restore_index)
                else:
                    self.resource_type_combo.setCurrentIndex(0)
            else:
                self.resource_type_combo.setCurrentIndex(0)
        self.resource_type_combo.blockSignals(False)

        # Force resource population after namespace change to ensure resource dropdowns are updated
        # This handles the case where resource type stays the same but namespace changes
        self._on_namespace_or_type_changed()

    def _clear_resource_combos(self):
        self.resource_type_combo.clear()
        self.resource_type_combo.addItem("Select resource type")
        self.resource_type_combo.setEnabled(False)
        self.resource1_combo.clear()
        self.resource1_combo.addItem("Select resource 1")
        self.resource1_combo.setEnabled(False)
        self.resource2_combo.clear()
        self.resource2_combo.addItem("Select resource 2")
        self.resource2_combo.setEnabled(False)

    def _on_namespace_or_type_changed(self, _=None):
        ns = self.namespace_combo.currentText().strip()
        rt = self.resource_type_combo.currentText().strip()
        LOG.info(f"[COMPARE_LOG] Resource type changed - Namespace: '{ns}', Type: '{rt}'")
        
        if not ns or ns.startswith(("Loading", "No ", "Unable", "kubernetes package")):
            LOG.info(f"[COMPARE_LOG] Invalid namespace, skipping: '{ns}'")
            return
        if not rt or rt.startswith(("Select", "Loading", "No ", "Unable", "kubernetes package")):
            LOG.info(f"[COMPARE_LOG] Invalid resource type, skipping: '{rt}'")
            return
        
        names = self._list_resources_for_namespace(ns, rt)
        LOG.info(f"[COMPARE_LOG] Found {len(names)} resources of type '{rt}' in namespace '{ns}'")
        self._populate_resource_combos(names)

    def _populate_resource_combos(self, names):
        # Enhanced state persistence - store current selections to restore them
        current_resource1 = self.resource1_combo.currentText() if self.resource1_combo.count() > 0 else None
        current_resource2 = self.resource2_combo.currentText() if self.resource2_combo.count() > 0 else None

        # Block signals to prevent unwanted triggers during population
        self.resource1_combo.blockSignals(True)
        self.resource2_combo.blockSignals(True)

        self.resource1_combo.clear()
        self.resource2_combo.clear()
        if not names:
            self.resource1_combo.addItem("No resources found")
            self.resource2_combo.addItem("No resources found")
            self.resource1_combo.setEnabled(False)
            self.resource2_combo.setEnabled(False)
            # Clear original items for search
            self.resource1_combo._original_items = []
            self.resource2_combo._original_items = []
        else:
            # Keep specific labels for each dropdown
            self.resource1_combo.setEnabled(True)
            self.resource1_combo.addItem("Select resource 1")
            self.resource1_combo.addItems(sorted(names))

            self.resource2_combo.setEnabled(True)
            self.resource2_combo.addItem("Select resource 2")
            self.resource2_combo.addItems(sorted(names))

            # Store original items for search functionality
            self.resource1_combo._original_items = ["Select resource 1"] + sorted(names)
            self.resource2_combo._original_items = ["Select resource 2"] + sorted(names)

            # Enhanced state persistence - restore previous selections if they exist in the new list
            if current_resource1 and current_resource1 not in ["Select resource 1", "No resources found"]:
                restore_index1 = self.resource1_combo.findText(current_resource1)
                if restore_index1 >= 0:
                    self.resource1_combo.setCurrentIndex(restore_index1)
                else:
                    self.resource1_combo.setCurrentIndex(0)  # Fallback to default
            else:
                self.resource1_combo.setCurrentIndex(0)

            if current_resource2 and current_resource2 not in ["Select resource 2", "No resources found"]:
                restore_index2 = self.resource2_combo.findText(current_resource2)
                if restore_index2 >= 0:
                    self.resource2_combo.setCurrentIndex(restore_index2)
                else:
                    self.resource2_combo.setCurrentIndex(0)  # Fallback to default
            else:
                self.resource2_combo.setCurrentIndex(0)

        # Re-enable signals
        self.resource1_combo.blockSignals(False)
        self.resource2_combo.blockSignals(False)

        self._update_compare_button_state()

    def _on_resource_selection_changed(self):
        """Handle resource selection changes - update compare button and auto-recompare"""
        r1 = self.resource1_combo.currentText().strip()
        r2 = self.resource2_combo.currentText().strip()
        LOG.info(f"[COMPARE_LOG] Resource selection changed - Resource1: '{r1}', Resource2: '{r2}'")
        
        self._update_compare_button_state()
        self._try_auto_recompare()

    def _update_compare_button_state(self):
        """Enable Compare button only when two valid resources are selected"""
        r1 = self.resource1_combo.currentText().strip()
        r2 = self.resource2_combo.currentText().strip()

        valid_r1 = bool(r1 and not r1.startswith(("Select", "No ", "Error")))
        valid_r2 = bool(r2 and not r2.startswith(("Select", "No ", "Error")))

        self.compare_btn.setEnabled(valid_r1 and valid_r2)

    def _try_auto_recompare(self):
        """Auto-recompare if conditions are met (same logic as Compare button)"""
        # Block auto-recompare if either editor is in edit mode
        if self._left_edit_mode or self._right_edit_mode:
            return

        # Use same validation logic as Compare button
        ns = self.namespace_combo.currentText().strip()
        rt = self.resource_type_combo.currentText().strip()
        a = self.resource1_combo.currentText().strip()
        b = self.resource2_combo.currentText().strip()

        if not ns or ns.startswith(("Loading", "No ", "Unable", "kubernetes package")):
            return
        if not rt or rt.startswith(("Select", "Loading", "No ", "Unable", "kubernetes package")):
            return
        if not a or a.startswith(("No ", "Select")) or not b or b.startswith(("No ", "Select")):
            return

        # Only auto-recompare if compare area is already visible (user has compared before)
        if self.compare_area.isVisible():
            self._on_compare_clicked()

    # ---------- comparison functions ----------

    def _clean_resource_data(self, data):
        """Clean resource data for display"""
        if not isinstance(data, dict):
            return data
        return data

    def parse_yaml_string(self, yaml_string):
        """Convert YAML string to dictionary for comparison"""
        try:
            LOG.info(f"[PARSE_LOG] parse_yaml_string called with string length: {len(yaml_string) if yaml_string else 'None'}")
            if not yaml_string:
                LOG.warning(f"[PARSE_LOG] Empty YAML string provided")
                return {}
            
            result = yaml.safe_load(yaml_string)
            if result is None:
                LOG.warning(f"[PARSE_LOG] YAML parsing returned None, using empty dict")
                return {}
            
            LOG.info(f"[PARSE_LOG] YAML parsed successfully: {type(result)}")
            return result
            
        except yaml.YAMLError as yaml_error:
            LOG.error(f"[PARSE_LOG] YAML parsing error: {yaml_error}")
            return {}  # Return empty dict if YAML is invalid
        except Exception as parse_error:
            LOG.error(f"[PARSE_LOG] Unexpected error in parse_yaml_string: {parse_error}")
            return {}

    def build_comprehensive_line_map(self, yaml_string):
        """Build comprehensive mapping tracking all lines with context - FIXED for array items"""
        LOG.info(f"[PATH_MAP_LOG] ===== STARTING build_comprehensive_line_map ===== (FIXED VERSION)")
        LOG.info(f"[PATH_MAP_LOG] Input YAML length: {len(yaml_string)} characters")
        
        lines = yaml_string.splitlines()
        LOG.info(f"[PATH_MAP_LOG] Total lines to process: {len(lines)}")
        
        path_to_line = {}
        line_to_path = {}
        path_stack = []  # Stack of (path_component, indent_level, is_array_item)
        current_context = None
        in_quoted_string = False
        quoted_string_path = None
        array_index_stack = []  # Track array indices at each level

        LOG.info(f"[PATH_MAP_LOG] Initialized data structures:")
        LOG.info(f"[PATH_MAP_LOG]   - path_stack: {path_stack}")
        LOG.info(f"[PATH_MAP_LOG]   - array_index_stack: {array_index_stack}")
        LOG.info(f"[PATH_MAP_LOG]   - current_context: {current_context}")

        for i, line in enumerate(lines):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            
            LOG.info(f"[PATH_MAP_LOG] ===== Processing Line {i} =====")
            LOG.info(f"[PATH_MAP_LOG] Line {i}: '{line}'")
            LOG.info(f"[PATH_MAP_LOG] Line {i}: stripped='{stripped}', indent={indent}")
            LOG.info(f"[PATH_MAP_LOG] Line {i}: path_stack={path_stack}")
            LOG.info(f"[PATH_MAP_LOG] Line {i}: array_index_stack={array_index_stack}")
            LOG.info(f"[PATH_MAP_LOG] Line {i}: current_context='{current_context}'")

            # Handle empty lines and comments - inherit context
            if not stripped or stripped.startswith('#'):
                LOG.info(f"[PATH_MAP_LOG] Line {i}: EMPTY/COMMENT - inheriting context")
                if in_quoted_string:
                    line_to_path[i] = quoted_string_path
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Inherited quoted string path: '{quoted_string_path}'")
                else:
                    line_to_path[i] = current_context
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Inherited current context: '{current_context}'")
                continue

            # If we're in a quoted string, all lines get the same path
            if in_quoted_string:
                LOG.info(f"[PATH_MAP_LOG] Line {i}: IN QUOTED STRING - using path '{quoted_string_path}'")
                line_to_path[i] = quoted_string_path
                # Check if this line closes the quoted string
                if '"' in stripped and stripped.rstrip().endswith('"'):
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: QUOTED STRING ENDED")
                    in_quoted_string = False
                    quoted_string_path = None
                continue

            # CRITICAL FIX: Handle array items (lines starting with '-')
            if stripped.startswith('-'):
                LOG.info(f"[PATH_MAP_LOG] Line {i}: ARRAY ITEM DETECTED - '{stripped}'")
                
                # Adjust path stack based on indentation - pop items with same or greater indent
                original_stack_size = len(path_stack)
                while path_stack and path_stack[-1][1] >= indent:
                    popped = path_stack.pop()
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Popped from path_stack: {popped}")
                
                # Also adjust array index stack
                while len(array_index_stack) > len(path_stack):
                    popped_index = array_index_stack.pop()
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Popped from array_index_stack: {popped_index}")
                
                LOG.info(f"[PATH_MAP_LOG] Line {i}: Stack after popping - path_stack={path_stack}, array_index_stack={array_index_stack}")
                
                # Determine array index for this level
                current_array_level = len(path_stack)
                
                # Safe array index handling
                if current_array_level >= len(array_index_stack):
                    # Extend array_index_stack to have enough elements
                    array_index_stack.extend([0] * (current_array_level - len(array_index_stack) + 1))
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Extended array_index_stack to: {array_index_stack}")

                # Increment the array index at this level
                array_index_stack[current_array_level] = array_index_stack[current_array_level] + 1
                current_array_index = array_index_stack[current_array_level]
                LOG.info(f"[PATH_MAP_LOG] Line {i}: Incremented array index to: {current_array_index} at level {current_array_level}")
                LOG.info(f"[PATH_MAP_LOG] Line {i}: Current array index: {current_array_index}")
                
                # Build path up to this array item
                if path_stack:
                    array_parent_path = '.'.join([p[0] for p in path_stack])
                    array_item_path = f"{array_parent_path}.{current_array_index}"
                else:
                    array_item_path = str(current_array_index)
                
                LOG.info(f"[PATH_MAP_LOG] Line {i}: Built array item path: '{array_item_path}'")
                
                # Check if this array item has a key-value pair on the same line
                array_content = stripped[1:].strip()  # Remove the '-' and whitespace
                LOG.info(f"[PATH_MAP_LOG] Line {i}: Array content after '-': '{array_content}'")
                
                if ':' in array_content:
                    # Array item with key-value on same line: "- name: value"
                    key = array_content.split(':', 1)[0].strip()
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Array item with key '{key}' on same line")
                    
                    if key:
                        full_path = f"{array_item_path}.{key}"
                        LOG.info(f"[PATH_MAP_LOG] Line {i}: Full path for array item key: '{full_path}'")
                        
                        path_to_line[full_path] = i
                        line_to_path[i] = full_path
                        current_context = full_path
                        
                        # Add to path stack for potential children
                        path_stack.append((str(current_array_index), indent, True))  # Array item marker
                        path_stack.append((key, indent, False))  # The key within the array item
                        
                        LOG.info(f"[PATH_MAP_LOG] Line {i}: Added to path_stack: {path_stack[-2:]}")
                        LOG.info(f"[PATH_MAP_LOG] Line {i}: Set current_context: '{current_context}'")
                        
                        # Check for quoted string
                        value_part = array_content.split(':', 1)[1].strip()
                        if '"' in value_part:
                            quote_count = value_part.count('"')
                            if quote_count == 1 or (quote_count > 1 and not value_part.rstrip().endswith('"')):
                                in_quoted_string = True
                                quoted_string_path = full_path
                                LOG.info(f"[PATH_MAP_LOG] Line {i}: Started quoted string with path '{quoted_string_path}'")
                else:
                    # Array item without key-value: just "- " (children will follow)
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Array item without key-value, expecting children")
                    
                    line_to_path[i] = array_item_path
                    current_context = array_item_path
                    
                    # Add array item to path stack
                    path_stack.append((str(current_array_index), indent, True))
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Added array item to path_stack: {path_stack[-1]}")
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Set current_context: '{current_context}'")
                
                LOG.info(f"[PATH_MAP_LOG] Line {i}: ARRAY ITEM PROCESSING COMPLETE")
                continue

            # Check if we're starting a multiline string
            if ':' in stripped and ('|' in stripped or '>' in stripped):
                LOG.info(f"[PATH_MAP_LOG] Line {i}: MULTILINE STRING DETECTED - '{stripped}'")
                key = stripped.split(':', 1)[0].strip()
                if key:
                    # Adjust path stack based on indentation
                    while path_stack and path_stack[-1][1] >= indent:
                        popped = path_stack.pop()
                        LOG.info(f"[PATH_MAP_LOG] Line {i}: Popped from path_stack: {popped}")
                    
                    # Adjust array index stack
                    while len(array_index_stack) > len(path_stack):
                        popped_index = array_index_stack.pop()
                        LOG.info(f"[PATH_MAP_LOG] Line {i}: Popped from array_index_stack: {popped_index}")

                    # Build full path
                    if path_stack:
                        full_path = '.'.join([p[0] for p in path_stack] + [key])
                    else:
                        full_path = key
                    
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Built multiline string path: '{full_path}'")

                    path_to_line[full_path] = i
                    line_to_path[i] = full_path
                    current_context = full_path
                    path_stack.append((key, indent, False))
                    
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: MULTILINE STRING PROCESSING COMPLETE")
                continue

            # Regular key-value processing
            if ':' in stripped:
                LOG.info(f"[PATH_MAP_LOG] Line {i}: REGULAR KEY-VALUE DETECTED - '{stripped}'")
                key = stripped.split(':', 1)[0].strip()
                if key:
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Extracted key: '{key}'")
                    
                    # Check if this line starts a quoted string value
                    value_part = stripped.split(':', 1)[1].strip()
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Value part: '{value_part}'")
                    
                    if '"' in value_part:
                        quote_count = value_part.count('"')
                        # Check if quote opens but doesn't close on same line
                        if quote_count == 1 or (quote_count > 1 and not value_part.rstrip().endswith('"')):
                            in_quoted_string = True
                            LOG.info(f"[PATH_MAP_LOG] Line {i}: Detected start of quoted string")

                    # Adjust path stack based on indentation
                    original_stack_size = len(path_stack)
                    while path_stack and path_stack[-1][1] >= indent:
                        popped = path_stack.pop()
                        LOG.info(f"[PATH_MAP_LOG] Line {i}: Popped from path_stack: {popped}")
                    
                    # Adjust array index stack
                    while len(array_index_stack) > len(path_stack):
                        popped_index = array_index_stack.pop()
                        LOG.info(f"[PATH_MAP_LOG] Line {i}: Popped from array_index_stack: {popped_index}")
                    
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Stack after adjustment - path_stack={path_stack}, array_index_stack={array_index_stack}")

                    # Build full path
                    if path_stack:
                        full_path = '.'.join([p[0] for p in path_stack] + [key])
                    else:
                        full_path = key
                    
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Built full path: '{full_path}'")

                    path_to_line[full_path] = i
                    line_to_path[i] = full_path
                    current_context = full_path
                    path_stack.append((key, indent, False))
                    
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Added to path_stack: {path_stack[-1]}")
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: Set current_context: '{current_context}'")
                    
                    # If this line started a quoted string, save its path
                    if in_quoted_string:
                        quoted_string_path = full_path
                        LOG.info(f"[PATH_MAP_LOG] Line {i}: Set quoted_string_path: '{quoted_string_path}'")
                    
                    LOG.info(f"[PATH_MAP_LOG] Line {i}: REGULAR KEY-VALUE PROCESSING COMPLETE")
            else:
                # Non-key lines (like multi-line values) inherit context
                LOG.info(f"[PATH_MAP_LOG] Line {i}: NON-KEY LINE - inheriting context '{current_context}'")
                line_to_path[i] = current_context
        
        LOG.info(f"[PATH_MAP_LOG] ===== FINAL RESULTS =====")
        LOG.info(f"[PATH_MAP_LOG] Total paths created: {len(path_to_line)}")
        LOG.info(f"[PATH_MAP_LOG] Total lines mapped: {len(line_to_path)}")
        
        # Log first 20 line mappings for debugging
        LOG.info(f"[PATH_MAP_LOG] First 20 line-to-path mappings:")
        for i in range(min(20, len(lines))):
            path = line_to_path.get(i, "NO_PATH")
            line_text = lines[i][:60] if i < len(lines) else "NO_LINE"
            LOG.info(f"[PATH_MAP_LOG]   Line {i:2d}: '{path}' | '{line_text}'")
        
        # Log all paths for debugging
        LOG.info(f"[PATH_MAP_LOG] All created paths:")
        for path, line_num in sorted(path_to_line.items()):
            LOG.info(f"[PATH_MAP_LOG]   Path '{path}' -> Line {line_num}")
        
        LOG.info(f"[PATH_MAP_LOG] ===== build_comprehensive_line_map COMPLETE =====")
        return path_to_line, line_to_path

    def flatten_dict(self, d, parent_key='', sep='.'):
        """Flatten nested dictionary to dot-notation paths"""
        try:
            LOG.info(f"[FLATTEN_LOG] flatten_dict called with: {type(d)}, parent_key='{parent_key}'")
            
            if not isinstance(d, dict):
                LOG.error(f"[FLATTEN_LOG] ERROR: Expected dict, got {type(d)}")
                return {}
            
            items = []
            for k, v in d.items():
                try:
                    LOG.info(f"[FLATTEN_LOG] Processing key: '{k}' (type: {type(k)}), value type: {type(v)}")
                    
                    if not isinstance(k, (str, int, float)):
                        LOG.warning(f"[FLATTEN_LOG] Unusual key type: {type(k)}, converting to string")
                        k = str(k)
                    
                    new_key = f"{parent_key}{sep}{k}" if parent_key else str(k)
                    
                    if isinstance(v, dict):
                        LOG.info(f"[FLATTEN_LOG] Recursing into dict for key '{new_key}'")
                        items.extend(self.flatten_dict(v, new_key, sep=sep).items())
                    elif isinstance(v, list):
                        LOG.info(f"[FLATTEN_LOG] Processing list for key '{new_key}' with {len(v)} items")
                        # Flatten list items instead of treating list as leaf value
                        for i, item in enumerate(v):
                            try:
                                if isinstance(item, dict):
                                    items.extend(self.flatten_dict(item, f"{new_key}.{i}", sep=sep).items())
                                else:
                                    items.append((f"{new_key}.{i}", item))
                            except Exception as list_item_error:
                                LOG.error(f"[FLATTEN_LOG] Error processing list item {i}: {list_item_error}")
                                continue
                    else:
                        items.append((new_key, v))
                        
                except Exception as key_error:
                    LOG.error(f"[FLATTEN_LOG] Error processing key '{k}': {key_error}")
                    continue
            
            result = dict(items)
            LOG.info(f"[FLATTEN_LOG] flatten_dict completed: {len(result)} flattened keys")
            return result
            
        except Exception as flatten_error:
            LOG.error(f"[FLATTEN_LOG] CRITICAL ERROR in flatten_dict: {flatten_error}")
            import traceback
            LOG.error(f"[FLATTEN_LOG] Traceback: {traceback.format_exc()}")
            return {}



    def _get_direct_children(self, parent_path, flattened_dict):
        """Get direct child keys for a given parent path with edge case handling - optimized"""
        if not flattened_dict:
            return set()
            
        if not parent_path or parent_path.strip() == "":
            # Return top-level keys (everything before first dot)
            children = set()
            for key in flattened_dict:
                if key and '.' in key:
                    top_key = key.split('.', 1)[0]  # Only split once
                    if top_key:
                        children.add(top_key)
                elif key:
                    children.add(key)
            return children
        
        prefix = f"{parent_path}."
        prefix_len = len(prefix)
        children = set()
        
        for key in flattened_dict:
            if key and key.startswith(prefix):
                remainder = key[prefix_len:]
                if remainder:
                    dot_pos = remainder.find('.')
                    child_key = remainder[:dot_pos] if dot_pos != -1 else remainder
                    if child_key:
                        children.add(child_key)
        
        return children

    def _is_parent_only_line(self, line):
        """Check if line is a parent-only line with edge case handling"""
        if not line:
            return False
            
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or ':' not in stripped:
            return False
        
        colon_pos = stripped.find(':')
        if colon_pos == -1 or colon_pos == len(stripped) - 1:
            # Colon at end of line = parent-only
            is_parent = colon_pos == len(stripped) - 1
        else:
            after_colon = stripped[colon_pos + 1:].strip()
            # Handle edge cases: empty objects {}, arrays [], null values
            is_parent = not after_colon or after_colon in ['{}', '[]', 'null', '~']
            
        return is_parent

    def compare_yaml_semantically(self, yaml1, yaml2):
        """Compare YAML semantically with granular value highlighting - optimized"""
        try:
            LOG.info(f"[SEMANTIC_LOG] === compare_yaml_semantically START ===")
            LOG.info(f"[SEMANTIC_LOG] Method called with parameters:")
            LOG.info(f"[SEMANTIC_LOG]   - yaml1 type: {type(yaml1)}")
            LOG.info(f"[SEMANTIC_LOG]   - yaml2 type: {type(yaml2)}")
            LOG.info(f"[SEMANTIC_LOG]   - yaml1 length: {len(yaml1) if yaml1 else 'None'}")
            LOG.info(f"[SEMANTIC_LOG]   - yaml2 length: {len(yaml2) if yaml2 else 'None'}")
            
            if not yaml1 or not yaml2:
                LOG.error(f"[SEMANTIC_LOG] ERROR: One or both YAMLs are empty/None")
                return (set(), set(), {}), (set(), set(), {})
            
            LOG.info(f"[COMPARE_LOG] === SEMANTIC COMPARISON START ===")
            
            # Test YAML parsing first
            LOG.info(f"[SEMANTIC_LOG] Testing YAML parsing...")
            try:
                parsed1 = self.parse_yaml_string(yaml1)
                LOG.info(f"[SEMANTIC_LOG] yaml1 parsed successfully: {type(parsed1)}")
            except Exception as parse1_error:
                LOG.error(f"[SEMANTIC_LOG] ERROR parsing yaml1: {parse1_error}")
                return (set(), set(), {}), (set(), set(), {})
            
            try:
                parsed2 = self.parse_yaml_string(yaml2)
                LOG.info(f"[SEMANTIC_LOG] yaml2 parsed successfully: {type(parsed2)}")
            except Exception as parse2_error:
                LOG.error(f"[SEMANTIC_LOG] ERROR parsing yaml2: {parse2_error}")
                return (set(), set(), {}), (set(), set(), {})
            
            # Test flattening
            LOG.info(f"[SEMANTIC_LOG] Testing dictionary flattening...")
            try:
                flattened1 = self.flatten_dict(parsed1)
                LOG.info(f"[SEMANTIC_LOG] yaml1 flattened successfully: {len(flattened1)} keys")
            except Exception as flatten1_error:
                LOG.error(f"[SEMANTIC_LOG] ERROR flattening yaml1: {flatten1_error}")
                return (set(), set(), {}), (set(), set(), {})
            
            try:
                flattened2 = self.flatten_dict(parsed2)
                LOG.info(f"[SEMANTIC_LOG] yaml2 flattened successfully: {len(flattened2)} keys")
            except Exception as flatten2_error:
                LOG.error(f"[SEMANTIC_LOG] ERROR flattening yaml2: {flatten2_error}")
                return (set(), set(), {}), (set(), set(), {})
            
        except Exception as semantic_error:
            LOG.error(f"[SEMANTIC_LOG] CRITICAL ERROR in compare_yaml_semantically setup: {semantic_error}")
            import traceback
            LOG.error(f"[SEMANTIC_LOG] Traceback: {traceback.format_exc()}")
            return (set(), set(), {}), (set(), set(), {})
        
        # Use already tested flattened dictionaries
        dict1 = flattened1
        dict2 = flattened2
        
        LOG.info(f"[COMPARE_LOG] Dict1 keys: {list(dict1.keys())}")
        LOG.info(f"[COMPARE_LOG] Dict2 keys: {list(dict2.keys())}")
        LOG.info(f"[COMPARE_LOG] Dicts identical: {dict1 == dict2}")

        # Build comprehensive line mappings
        paths1, line_to_path1 = self.build_comprehensive_line_map(yaml1)
        paths2, line_to_path2 = self.build_comprehensive_line_map(yaml2)
        
        LOG.info(f"[COMPARE_LOG] Line mappings built - Lines1: {len(line_to_path1)}, Lines2: {len(line_to_path2)}")
        
        # Log line-to-path mapping for debugging
        lines1 = yaml1.splitlines()
        for i in range(min(10, len(lines1))):
            path = line_to_path1.get(i, "NO_PATH")
            LOG.info(f"[COMPARE_LOG] Line {i}: path='{path}' | text='{lines1[i][:60]}'")
        
        # DEBUG: Check if Corefile values are actually different
        if 'data.Corefile' in dict1 and 'data.Corefile' in dict2:
            corefile1 = dict1['data.Corefile']
            corefile2 = dict2['data.Corefile']
            if corefile1 != corefile2:
                LOG.warning(f"=== COREFILE VALUES ARE DIFFERENT ===")
                LOG.warning(f"Left Corefile length: {len(corefile1)}")
                LOG.warning(f"Right Corefile length: {len(corefile2)}")
                LOG.warning(f"Left Corefile (first 200 chars): {repr(corefile1[:200])}")
                LOG.warning(f"Right Corefile (first 200 chars): {repr(corefile2[:200])}")
            else:
                LOG.warning(f"=== COREFILE VALUES ARE IDENTICAL ===")
        elif 'data.Corefile' in dict1:
            LOG.warning(f"=== COREFILE ONLY IN LEFT YAML ===")
        elif 'data.Corefile' in dict2:
            LOG.warning(f"=== COREFILE ONLY IN RIGHT YAML ===")

        # LOG ACTUAL DATA for first 30 lines
        lines1 = yaml1.splitlines()
        LOG.warning("=== ACTUAL LINE-TO-PATH MAPPING (LEFT YAML) ===")
        for i in range(min(30, len(lines1))):
            line_text = lines1[i][:60]
            path = line_to_path1.get(i, "NO_PATH")
            LOG.warning(f"Line {i:3d}: path='{path}' | text='{line_text}'")
        LOG.warning("=== END ACTUAL MAPPING ===")
        


        lines2 = yaml2.splitlines()

        # Cache for memoizing direct children lookups
        children_cache = {}
        
        def get_cached_children(path, flattened_dict, cache_key):
            """Get direct children with memoization"""
            if cache_key not in children_cache:
                children_cache[cache_key] = self._get_direct_children(path, flattened_dict) or set()
            return children_cache[cache_key]

        # Pre-identify parent-only lines to avoid repeated checks
        parent_lines1 = {i for i in range(len(lines1)) if self._is_parent_only_line(lines1[i])}
        parent_lines2 = {i for i in range(len(lines2)) if self._is_parent_only_line(lines2[i])}
        LOG.info(f"[PARENT_LOG] Identified parent lines1: {sorted(parent_lines1)}")
        LOG.info(f"[PARENT_LOG] Identified parent lines2: {sorted(parent_lines2)}")

        matching_lines1 = set()
        matching_lines2 = set()
        different_lines1 = set()
        different_lines2 = set()
        granular_highlights1 = {}
        granular_highlights2 = {}

        # Process lines1 with optimizations
        for i in range(len(lines1)):
            path = line_to_path1.get(i)
            
            if i in parent_lines1 and path:
                LOG.info(f"[PARENT_LOG] Line {i} is PARENT LINE with path '{path}'")
                children1 = get_cached_children(path, dict1, f"1_{path}")
                children2 = get_cached_children(path, dict2, f"2_{path}")
                LOG.info(f"[PARENT_LOG] Children1: {children1}")
                LOG.info(f"[PARENT_LOG] Children2: {children2}")
                
                if not children1 and not children2:
                    LOG.info(f"[PARENT_LOG] Both parents have NO children -> MATCHING")
                    matching_lines1.add(i)
                else:
                    intersection = children1 & children2
                    if intersection:
                        LOG.info(f"[PARENT_LOG] Parents have COMMON children {intersection} -> MATCHING")
                        matching_lines1.add(i)
                    else:
                        LOG.info(f"[PARENT_LOG] Parents have NO common children -> DIFFERENT")
                        different_lines1.add(i)
            else:
                if path and path in dict1:
                    if path in dict2:
                        if dict1[path] == dict2[path]:
                            LOG.info(f"[COMPARE_LOG] Line {i} path '{path}': VALUES IDENTICAL -> MATCHING")
                            matching_lines1.add(i)
                        else:
                            LOG.info(f"[COMPARE_LOG] Line {i} path '{path}': VALUES DIFFERENT -> GRANULAR")
                            # CRITICAL FIX: Safe logging with type checking to prevent 'int' object is not subscriptable
                            try:
                                value1_preview = repr(dict1[path][:100]) if isinstance(dict1[path], (str, list, tuple)) else repr(dict1[path])
                                value2_preview = repr(dict2[path][:100]) if isinstance(dict2[path], (str, list, tuple)) else repr(dict2[path])
                                LOG.info(f"[COMPARE_LOG] Value1: {value1_preview}")
                                LOG.info(f"[COMPARE_LOG] Value2: {value2_preview}")
                            except Exception as log_error:
                                LOG.error(f"[COMPARE_LOG] ERROR in value logging: {log_error}")
                                LOG.info(f"[COMPARE_LOG] Value1 type: {type(dict1[path])}, Value2 type: {type(dict2[path])}")
                            # Apply granular or full highlighting for different values
                            LOG.info(f"[COMPARE_LOG] Calling _create_granular_highlight for line {i}...")
                            granular_highlight = self._create_granular_highlight(lines1[i], dict1[path], dict2[path])
                            LOG.info(f"[COMPARE_LOG] _create_granular_highlight returned: {granular_highlight}")
                            LOG.info(f"[COMPARE_LOG] Return type: {type(granular_highlight)}")
                            
                            if granular_highlight:
                                LOG.info(f"[COMPARE_LOG] Line {i}: GRANULAR HIGHLIGHT APPLIED -> {granular_highlight}")
                                LOG.info(f"[COMPARE_LOG] Assigning to granular_highlights1[{i}]...")
                                granular_highlights1[i] = granular_highlight
                                LOG.info(f"[COMPARE_LOG] Assignment completed. granular_highlights1[{i}] = {granular_highlights1[i]}")
                            else:
                                LOG.info(f"[COMPARE_LOG] Line {i}: NO GRANULAR, USING FULL RED")
                                different_lines1.add(i)
                    else:
                        different_lines1.add(i)
                else:
                    # Check if this is a multiline string content line without a path
                    line_text = lines1[i]
                    is_multiline_content = (not line_text.strip().startswith('-') and 
                                          not line_text.strip().startswith('#') and 
                                          line_text.strip() != '' and
                                          not line_text.lstrip().endswith(':'))
                    
                    if is_multiline_content:
                        # For multiline content lines, check if they exist in both YAMLs at same position
                        line2_text = lines2[i] if i < len(lines2) else ""
                        if line_text.strip() == line2_text.strip():
                            matching_lines1.add(i)
                        else:
                            different_lines1.add(i)
                    else:
                        # Direct line comparison
                        line2 = lines2[i].strip() if i < len(lines2) else ""
                        if line_text.strip() == line2:
                            matching_lines1.add(i)
                        else:
                            different_lines1.add(i)

        # Process lines2 with optimizations
        for i in range(len(lines2)):
            path = line_to_path2.get(i)
            
            if i in parent_lines2 and path:
                LOG.info(f"[PARENT_LOG] Line {i} is PARENT LINE with path '{path}'")
                children1 = get_cached_children(path, dict1, f"1_{path}")
                children2 = get_cached_children(path, dict2, f"2_{path}")
                LOG.info(f"[PARENT_LOG] Children1: {children1}")
                LOG.info(f"[PARENT_LOG] Children2: {children2}")
                
                if not children1 and not children2:
                    LOG.info(f"[PARENT_LOG] Both parents have NO children -> MATCHING")
                    matching_lines2.add(i)
                else:
                    intersection = children1 & children2
                    if intersection:
                        LOG.info(f"[PARENT_LOG] Parents have COMMON children {intersection} -> MATCHING")
                        matching_lines2.add(i)
                    else:
                        LOG.info(f"[PARENT_LOG] Parents have NO common children -> DIFFERENT")
                        different_lines2.add(i)
            elif path and path in dict2:
                if path in dict1:
                    if dict1[path] == dict2[path]:
                        matching_lines2.add(i)
                    else:
                        # Apply granular or full highlighting for different values
                        LOG.info(f"[COMPARE_LOG] Calling _create_granular_highlight for RIGHT line {i}...")
                        granular_highlight = self._create_granular_highlight(lines2[i], dict2[path], dict1[path])
                        LOG.info(f"[COMPARE_LOG] RIGHT _create_granular_highlight returned: {granular_highlight}")
                        LOG.info(f"[COMPARE_LOG] RIGHT Return type: {type(granular_highlight)}")
                        
                        if granular_highlight:
                            LOG.info(f"[COMPARE_LOG] RIGHT Line {i}: GRANULAR HIGHLIGHT APPLIED -> {granular_highlight}")
                            LOG.info(f"[COMPARE_LOG] Assigning to granular_highlights2[{i}]...")
                            granular_highlights2[i] = granular_highlight
                            LOG.info(f"[COMPARE_LOG] RIGHT Assignment completed. granular_highlights2[{i}] = {granular_highlights2[i]}")
                        else:
                            LOG.info(f"[COMPARE_LOG] RIGHT Line {i}: NO GRANULAR, USING FULL RED")
                            different_lines2.add(i)
                else:
                    different_lines2.add(i)
            else:
                # Check if this is a multiline string content line without a path
                line_text = lines2[i]
                is_multiline_content = (not line_text.strip().startswith('-') and 
                                      not line_text.strip().startswith('#') and 
                                      line_text.strip() != '' and
                                      not line_text.lstrip().endswith(':'))
                
                if is_multiline_content:
                    # For multiline content lines, check if they exist in both YAMLs at same position
                    line1_text = lines1[i] if i < len(lines1) else ""
                    if line_text.strip() == line1_text.strip():
                        matching_lines2.add(i)
                    else:
                        different_lines2.add(i)
                else:
                    # Direct line comparison
                    line1 = lines1[i].strip() if i < len(lines1) else ""
                    if line_text.strip() == line1:
                        matching_lines2.add(i)
                    else:
                        different_lines2.add(i)

        # Diagnostic summary - only log problematic cases
        problematic_lines = []
        for i in different_lines1:
            line_text = lines1[i] if i < len(lines1) else ""
            path = line_to_path1.get(i, "NO_PATH")
            
            # Check if this might be a false positive (shouldn't be red)
            if i < len(lines2):
                line2_text = lines2[i] if i < len(lines2) else ""
                
                # Case 1: Line starts with "- name:" or "  - name:"
                if "- name:" in line_text or "name:" in line_text:
                    problematic_lines.append({
                        'line': i,
                        'text': line_text[:60],
                        'path': path,
                        'reason': 'Contains "name:" - might be array item issue'
                    })
                
                # Case 2: Line is part of potential multiline (no colon, not array marker)
                elif ':' not in line_text.strip() and not line_text.strip().startswith('-'):
                    if line_text.strip() and not line_text.strip().startswith('#'):
                        problematic_lines.append({
                            'line': i,
                            'text': line_text[:60],
                            'path': path,
                            'reason': 'No colon - might be multiline continuation'
                        })
                
                # Case 3: Very similar lines marked as different
                elif line_text.strip() == line2_text.strip():
                    problematic_lines.append({
                        'line': i,
                        'text': line_text[:60],
                        'path': path,
                        'reason': 'IDENTICAL text but marked RED - BUG!'
                    })

        if problematic_lines:
            LOG.warning(f"Found {len(problematic_lines)} potentially incorrect RED lines:")
            for item in problematic_lines[:10]:  # Only log first 10
                LOG.warning(f"  Line {item['line']}: {item['text']}")
                LOG.warning(f"    Path: {item['path']}, Reason: {item['reason']}")

        # Return the comparison results
        LOG.info(f"[COMPARE_LOG] Final results - Left: {len(different_lines1)} diff, {len(matching_lines1)} match, {len(granular_highlights1)} granular")
        LOG.info(f"[COMPARE_LOG] Final results - Right: {len(different_lines2)} diff, {len(matching_lines2)} match, {len(granular_highlights2)} granular")
        LOG.info(f"[COMPARE_LOG] === SEMANTIC COMPARISON END ===")

        return ((different_lines1, matching_lines1, granular_highlights1), 
                (different_lines2, matching_lines2, granular_highlights2))

    def _create_granular_highlight(self, line, value1, value2):
        """Create granular highlighting for same-key-different-values scenario with edge case handling"""
        try:
            LOG.info(f"[GRANULAR_LOG] === _create_granular_highlight START ===")
            LOG.info(f"[GRANULAR_LOG]   - line: '{line[:100]}'")
            LOG.info(f"[GRANULAR_LOG]   - line type: {type(line)}")
            LOG.info(f"[GRANULAR_LOG]   - value1: {repr(value1)[:100]}")
            LOG.info(f"[GRANULAR_LOG]   - value1 type: {type(value1)}")
            LOG.info(f"[GRANULAR_LOG]   - value2: {repr(value2)[:100]}")
            LOG.info(f"[GRANULAR_LOG]   - value2 type: {type(value2)}")
            LOG.info(f"[GRANULAR_LOG]   - values equal: {value1 == value2}")
            
            # CRITICAL FIX: Return None if values are identical
            if value1 == value2:
                LOG.info(f"[GRANULAR_LOG] VALUES IDENTICAL -> RETURNING None")
                return None
            
            LOG.info(f"[GRANULAR_LOG] VALUES DIFFERENT -> CREATING GRANULAR HIGHLIGHT")
            
            if not line or not isinstance(line, str):
                LOG.info(f"[GRANULAR_LOG] Invalid line (not string or empty) -> RETURNING None")
                return None
                
            # Find the colon position
            colon_pos = line.find(':')
            LOG.info(f"[GRANULAR_LOG] Colon position: {colon_pos}")
            if colon_pos == -1 or colon_pos == 0:
                LOG.info(f"[GRANULAR_LOG] No colon or colon at start -> RETURNING None")
                return None
            
            # Find the value part after colon
            value_start = colon_pos + 1
            while value_start < len(line) and line[value_start] in ' \t':
                value_start += 1
            
            LOG.info(f"[GRANULAR_LOG] Value start position: {value_start}, line length: {len(line)}")
            
            # Must have actual value content to apply granular highlighting
            if value_start >= len(line):
                LOG.info(f"[GRANULAR_LOG] No value content -> RETURNING None")
                return None
                
            # Skip granular highlighting for parent-only lines
            if self._is_parent_only_line(line):
                LOG.info(f"[GRANULAR_LOG] Parent-only line -> RETURNING None")
                return None
            
            # Create highlighting: key part green, value part red
            LOG.info(f"[GRANULAR_LOG] Creating highlight tuples...")
            
            # CRITICAL: Create tuples with explicit validation
            green_tuple = (0, colon_pos + 1, 'green')
            red_tuple = (value_start, len(line), 'red')
            
            LOG.info(f"[GRANULAR_LOG] Green tuple: {green_tuple} (types: {[type(x) for x in green_tuple]})")
            LOG.info(f"[GRANULAR_LOG] Red tuple: {red_tuple} (types: {[type(x) for x in red_tuple]})")
            
            # Validate tuple elements
            if not isinstance(green_tuple[0], int) or not isinstance(green_tuple[1], int):
                LOG.error(f"[GRANULAR_LOG] ERROR: Green tuple has non-int positions: {green_tuple}")
                return None
            
            if not isinstance(red_tuple[0], int) or not isinstance(red_tuple[1], int):
                LOG.error(f"[GRANULAR_LOG] ERROR: Red tuple has non-int positions: {red_tuple}")
                return None
            
            result = [green_tuple, red_tuple]
            
            LOG.info(f"[GRANULAR_LOG] GRANULAR HIGHLIGHT CREATED: {result}")
            LOG.info(f"[GRANULAR_LOG] Result type: {type(result)}")
            LOG.info(f"[GRANULAR_LOG] Result length: {len(result)}")
            
            # Final validation of result structure
            for i, item in enumerate(result):
                LOG.info(f"[GRANULAR_LOG] Result[{i}]: {item} (type: {type(item)})")
                if isinstance(item, (tuple, list)) and len(item) >= 3:
                    LOG.info(f"[GRANULAR_LOG]   - Element 0: {item[0]} (type: {type(item[0])})")
                    LOG.info(f"[GRANULAR_LOG]   - Element 1: {item[1]} (type: {type(item[1])})")
                    LOG.info(f"[GRANULAR_LOG]   - Element 2: {item[2]} (type: {type(item[2])})")
                else:
                    LOG.error(f"[GRANULAR_LOG] ERROR: Invalid result item structure: {item}")
            
            LOG.info(f"[GRANULAR_LOG] === _create_granular_highlight END ===")
            return result
            
        except Exception as e:
            LOG.error(f"[GRANULAR_LOG] CRITICAL ERROR in _create_granular_highlight: {e}")
            import traceback
            LOG.error(f"[GRANULAR_LOG] Traceback: {traceback.format_exc()}")
            return None

    def _apply_comparison_highlighting(self, left_yaml, right_yaml):
        """Apply granular line highlighting to both YAML text boxes"""
        try:
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] === _apply_comparison_highlighting START ===")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Method called with parameters:")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - left_yaml type: {type(left_yaml)}")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - right_yaml type: {type(right_yaml)}")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - left_yaml length: {len(left_yaml) if left_yaml else 'None'}")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - right_yaml length: {len(right_yaml) if right_yaml else 'None'}")
            
            if not left_yaml or not right_yaml:
                LOG.error(f"[APPLY_HIGHLIGHT_LOG] ERROR: One or both YAMLs are empty/None")
                return
            
            yamls_identical = left_yaml == right_yaml
            LOG.info(f"[COMPARE_LOG] === HIGHLIGHTING ANALYSIS START ===")
            LOG.info(f"[COMPARE_LOG] YAMLs identical: {yamls_identical}")
            LOG.info(f"[COMPARE_LOG] Left YAML length: {len(left_yaml)}")
            LOG.info(f"[COMPARE_LOG] Right YAML length: {len(right_yaml)}")
            LOG.info(f"[COMPARE_LOG] Left YAML lines: {len(left_yaml.splitlines())}")
            LOG.info(f"[COMPARE_LOG] Right YAML lines: {len(right_yaml.splitlines())}")
            
        except Exception as apply_error:
            LOG.error(f"[APPLY_HIGHLIGHT_LOG] CRITICAL ERROR in _apply_comparison_highlighting setup: {apply_error}")
            import traceback
            LOG.error(f"[APPLY_HIGHLIGHT_LOG] Traceback: {traceback.format_exc()}")
            return
        
        # Only set text if not called from real-time highlighting
        if not hasattr(self, '_realtime_highlighting_enabled') or not self._realtime_highlighting_enabled or not (self._left_edit_mode or self._right_edit_mode):
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Setting text content in editors...")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Setting left text widget content (length: {len(left_yaml)})")
            
            # Force process events before setting text
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            self.left_box.setPlainText(left_yaml)
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Left text widget content set")
            
            # Force process events after setting left text
            QApplication.processEvents()
            
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Setting right text widget content (length: {len(right_yaml)})")
            self.right_box.setPlainText(right_yaml)
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Right text widget content set")
            
            # Force process events after setting right text
            QApplication.processEvents()
            
            # Verify the content was set correctly
            left_verify = self.left_box.toPlainText()
            right_verify = self.right_box.toPlainText()
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Left widget verification - length: {len(left_verify)}, matches: {left_verify == left_yaml}")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Right widget verification - length: {len(right_verify)}, matches: {right_verify == right_yaml}")
            
            # Log document state after text is set
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] AFTER TEXT SET - Left document block count: {self.left_box.document().blockCount()}")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] AFTER TEXT SET - Right document block count: {self.right_box.document().blockCount()}")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] AFTER TEXT SET - Left document character count: {self.left_box.document().characterCount()}")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] AFTER TEXT SET - Right document character count: {self.right_box.document().characterCount()}")
        else:
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Skipping text content setting (real-time highlighting or edit mode)")

        # Compare semantically and get different/matching sets with granular highlights
        LOG.info(f"[COMPARE_LOG] Starting semantic comparison...")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] About to call compare_yaml_semantically()")
        
        try:
            comparison_result = self.compare_yaml_semantically(left_yaml, right_yaml)
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] compare_yaml_semantically returned: {type(comparison_result)}")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] comparison_result: {comparison_result}")
            
            # Validate the result structure
            if not isinstance(comparison_result, (tuple, list)) or len(comparison_result) != 2:
                LOG.error(f"[APPLY_HIGHLIGHT_LOG] ERROR: Invalid comparison result structure: {comparison_result}")
                return
            
            left_result, right_result = comparison_result
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] left_result: {left_result} (type: {type(left_result)})")
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] right_result: {right_result} (type: {type(right_result)})")
            
            # Validate individual result structures
            if not isinstance(left_result, (tuple, list)) or len(left_result) != 3:
                LOG.error(f"[APPLY_HIGHLIGHT_LOG] ERROR: Invalid left_result structure: {left_result}")
                return
            
            if not isinstance(right_result, (tuple, list)) or len(right_result) != 3:
                LOG.error(f"[APPLY_HIGHLIGHT_LOG] ERROR: Invalid right_result structure: {right_result}")
                return
            
            left_diff, left_match, left_granular = left_result
            right_diff, right_match, right_granular = right_result
            
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Successfully unpacked comparison results")
            LOG.info(f"[COMPARE_LOG] Semantic comparison completed")
            
        except Exception as comparison_error:
            LOG.error(f"[APPLY_HIGHLIGHT_LOG] CRITICAL ERROR in semantic comparison: {comparison_error}")
            import traceback
            LOG.error(f"[APPLY_HIGHLIGHT_LOG] Traceback: {traceback.format_exc()}")
            return
        
        # Log highlighting results
        LOG.info(f"[COMPARE_LOG] Left different lines: {sorted(left_diff)}")
        LOG.info(f"[COMPARE_LOG] Left matching lines: {sorted(left_match)}")
        LOG.info(f"[COMPARE_LOG] Left granular highlights: {left_granular}")
        LOG.info(f"[COMPARE_LOG] Right different lines: {sorted(right_diff)}")
        LOG.info(f"[COMPARE_LOG] Right matching lines: {sorted(right_match)}")
        LOG.info(f"[COMPARE_LOG] Right granular highlights: {right_granular}")
        
        if yamls_identical and (left_diff or right_diff or left_granular or right_granular):
            LOG.error(f"[COMPARE_LOG] BUG DETECTED: Identical YAMLs have differences!")
            LOG.error(f"[COMPARE_LOG] Left diff: {left_diff}, Right diff: {right_diff}")
            LOG.error(f"[COMPARE_LOG] Left granular: {left_granular}, Right granular: {right_granular}")
        
        # Check for identical YAML bug before applying highlighting
        if yamls_identical:
            if left_granular:
                LOG.error(f"[COMPARE_LOG] BUG: Identical YAMLs have granular highlights: {left_granular}")
                lines = left_yaml.splitlines()
                for line_num, highlights in left_granular.items():
                    if line_num < len(lines):
                        LOG.error(f"[COMPARE_LOG] GRANULAR Line {line_num}: '{lines[line_num][:100]}' -> {highlights}")
        
        # Update highlighters with both different and matching lines plus granular highlights
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] === SETTING HIGHLIGHTER DATA ===")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Left highlighter data: diff={len(left_diff)} lines, match={len(left_match)} lines, granular={len(left_granular)} lines")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Left diff lines: {sorted(list(left_diff)[:10])}{'...' if len(left_diff) > 10 else ''}")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Left match lines: {sorted(list(left_match)[:10])}{'...' if len(left_match) > 10 else ''}")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Left granular lines: {list(left_granular.keys())[:5]}{'...' if len(left_granular) > 5 else ''}")
        
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] About to call left_highlighter.set_comparison_lines()...")
        try:
            self.left_highlighter.set_comparison_lines(left_diff, left_match, left_granular)
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Left highlighter.set_comparison_lines() completed successfully")
        except Exception as left_highlight_error:
            LOG.error(f"[APPLY_HIGHLIGHT_LOG] ERROR in left highlighter.set_comparison_lines(): {left_highlight_error}")
            import traceback
            LOG.error(f"[APPLY_HIGHLIGHT_LOG] Left highlighter traceback: {traceback.format_exc()}")
        
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Right highlighter data: diff={len(right_diff)} lines, match={len(right_match)} lines, granular={len(right_granular)} lines")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Right diff lines: {sorted(list(right_diff)[:10])}{'...' if len(right_diff) > 10 else ''}")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Right match lines: {sorted(list(right_match)[:10])}{'...' if len(right_match) > 10 else ''}")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Right granular lines: {list(right_granular.keys())[:5]}{'...' if len(right_granular) > 5 else ''}")
        
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] About to call right_highlighter.set_comparison_lines()...")
        try:
            self.right_highlighter.set_comparison_lines(right_diff, right_match, right_granular)
            LOG.info(f"[APPLY_HIGHLIGHT_LOG] Right highlighter.set_comparison_lines() completed successfully")
        except Exception as right_highlight_error:
            LOG.error(f"[APPLY_HIGHLIGHT_LOG] ERROR in right highlighter.set_comparison_lines(): {right_highlight_error}")
            import traceback
            LOG.error(f"[APPLY_HIGHLIGHT_LOG] Right highlighter traceback: {traceback.format_exc()}")
        
        # Log the current text content to verify what's being highlighted
        LOG.info(f"[COMPARE_LOG] === TEXT WIDGET CONTENT VERIFICATION ===")
        left_content = self.left_box.toPlainText()
        right_content = self.right_box.toPlainText()
        LOG.info(f"[COMPARE_LOG] Left widget content length: {len(left_content)}")
        LOG.info(f"[COMPARE_LOG] Right widget content length: {len(right_content)}")
        LOG.info(f"[COMPARE_LOG] Content identical: {left_content == right_content}")
        
        # Log first few lines of actual widget content
        left_widget_lines = left_content.split('\n')[:5]
        right_widget_lines = right_content.split('\n')[:5]
        for i, (left_line, right_line) in enumerate(zip(left_widget_lines, right_widget_lines)):
            LOG.info(f"[COMPARE_LOG] Widget line {i}: LEFT='{left_line}' | RIGHT='{right_line}'")

        # Ensure UI sees the change immediately
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] === FORCING UI UPDATES ===")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Calling viewport().update() on both text widgets")
        
        # Force process events before viewport update
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        self.left_box.viewport().update()
        self.right_box.viewport().update()
        
        # Force process events after viewport update
        QApplication.processEvents()
        
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Viewport updates completed")
        
        # Add a small delay and then verify highlighting was applied
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._verify_highlighting_applied(left_diff, left_match, left_granular, right_diff, right_match, right_granular))
        
        # Final verification of highlighter state
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] === FINAL VERIFICATION ===")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Final left highlighter state:")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - different_lines: {len(self.left_highlighter.different_lines)} items")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - matching_lines: {len(self.left_highlighter.matching_lines)} items")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - granular_highlights: {len(self.left_highlighter.granular_highlights)} items")
        
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] Final right highlighter state:")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - different_lines: {len(self.right_highlighter.different_lines)} items")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - matching_lines: {len(self.right_highlighter.matching_lines)} items")
        LOG.info(f"[APPLY_HIGHLIGHT_LOG]   - granular_highlights: {len(self.right_highlighter.granular_highlights)} items")
        
        LOG.info(f"[APPLY_HIGHLIGHT_LOG] === _apply_comparison_highlighting END ===")
    
    def _verify_highlighting_applied(self, left_diff, left_match, left_granular, right_diff, right_match, right_granular):
        """Verify highlighting was actually applied after a delay"""
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG] === VERIFYING HIGHLIGHTING AFTER 100ms DELAY ===")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG] Timestamp: {datetime.now().strftime('%H:%M:%S.%f')}")
        
        # Check if highlighters still have the expected data
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG] Left highlighter final state:")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG]   - different_lines: {len(self.left_highlighter.different_lines)} items: {sorted(list(self.left_highlighter.different_lines)[:5])}")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG]   - matching_lines: {len(self.left_highlighter.matching_lines)} items: {sorted(list(self.left_highlighter.matching_lines)[:5])}")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG]   - granular_highlights: {len(self.left_highlighter.granular_highlights)} items: {list(self.left_highlighter.granular_highlights.keys())[:5]}")
        
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG] Right highlighter final state:")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG]   - different_lines: {len(self.right_highlighter.different_lines)} items: {sorted(list(self.right_highlighter.different_lines)[:5])}")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG]   - matching_lines: {len(self.right_highlighter.matching_lines)} items: {sorted(list(self.right_highlighter.matching_lines)[:5])}")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG]   - granular_highlights: {len(self.right_highlighter.granular_highlights)} items: {list(self.right_highlighter.granular_highlights.keys())[:5]}")
        
        # Check if the expected highlighting data matches what we passed in
        left_diff_match = set(left_diff) == self.left_highlighter.different_lines
        left_match_match = set(left_match) == self.left_highlighter.matching_lines
        left_granular_match = left_granular == self.left_highlighter.granular_highlights
        
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG] Data consistency check:")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG]   - Left diff data matches: {left_diff_match}")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG]   - Left match data matches: {left_match_match}")
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG]   - Left granular data matches: {left_granular_match}")
        
        if not (left_diff_match and left_match_match and left_granular_match):
            LOG.error(f"[VERIFY_HIGHLIGHT_LOG] DATA MISMATCH DETECTED!")
            LOG.error(f"[VERIFY_HIGHLIGHT_LOG] Expected left_diff: {sorted(list(left_diff)[:10])}")
            LOG.error(f"[VERIFY_HIGHLIGHT_LOG] Actual left_diff: {sorted(list(self.left_highlighter.different_lines)[:10])}")
            LOG.error(f"[VERIFY_HIGHLIGHT_LOG] Expected left_granular keys: {list(left_granular.keys())[:5]}")
            LOG.error(f"[VERIFY_HIGHLIGHT_LOG] Actual left_granular keys: {list(self.left_highlighter.granular_highlights.keys())[:5]}")
        
        LOG.info(f"[VERIFY_HIGHLIGHT_LOG] === VERIFICATION COMPLETE ===")

    # ---------- resource YAML reading & compare ----------
    def _get_resource_yaml(self, namespace: str, kind: str, name: str) -> str:
        rt = (kind or "").strip().lower()

        try:
            from Utils.kubernetes_client import get_kubernetes_client
            kube = get_kubernetes_client()
            resource_type = self._map_kind_to_resource_type(rt)
            obj = kube.get_resource_detail_async(resource_type, name, namespace)

            if obj is None:
                return f"# Unable to read resource {kind}/{name} in {namespace}"

            # Convert to serializable dict
            if hasattr(obj, "to_dict"):
                data = obj.to_dict()
            else:
                from kubernetes.client import ApiClient
                data = ApiClient().sanitize_for_serialization(obj)

            # DEBUG: Log data keys for comparison
            data_keys = list(data.get('data', {}).keys()) if 'data' in data else []
            LOG.warning(f"YAML FETCH: {kind}/{name} has data keys: {data_keys}")

            # Convert to YAML using the same method as DetailPageYAMLSection
            kubernetes_yaml = self._convert_to_kubernetes_yaml(data)
            yaml_result = yaml.dump(
                kubernetes_yaml,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                width=120,
                allow_unicode=True
            )
            
            LOG.warning(f"YAML FETCH: {kind}/{name} YAML length: {len(yaml_result)}")
            return yaml_result

        except Exception:
            LOG.exception("ComparePage: Error reading resource YAML")
            return f"# Error fetching {kind}/{name} in {namespace}"

    def _map_kind_to_resource_type(self, rt: str) -> str:
        """Map a kind (lowercase) to a resource_type for get_resource_detail_async"""
        # Simple mapping of our internal kind to resource types
        if "pod" in rt:
            return "pod"
        elif "service" in rt or rt == "svc":
            return "service"
        elif "deploy" in rt:
            return "deployment"
        elif "stateful" in rt:
            return "statefulset"
        elif "daemon" in rt:
            return "daemonset"
        elif "replica" in rt:
            return "replicaset"
        elif "job" in rt and "cron" not in rt:
            return "job"
        elif "cron" in rt:
            return "cronjob"
        elif "ingress" in rt:
            return "ingress"
        elif "node" in rt:
            return "node"
        elif ("config" in rt and "map" in rt) or "configmap" in rt:
            return "configmap"
        elif "secret" in rt:
            return "secret"
        elif "persistentvolumeclaim" in rt or "pvc" in rt:
            return "persistentvolumeclaim"
        # Return the original if no mapping found
        return rt

    def _on_compare_clicked(self):
        ns = self.namespace_combo.currentText().strip()
        rt = self.resource_type_combo.currentText().strip()
        a = self.resource1_combo.currentText().strip()
        b = self.resource2_combo.currentText().strip()
        
        LOG.info(f"[COMPARE_LOG] ===== COMPARE BUTTON CLICKED =====")
        LOG.info(f"[COMPARE_LOG] Namespace: '{ns}', Type: '{rt}', Resource1: '{a}', Resource2: '{b}'")
        LOG.info(f"[COMPARE_LOG] Left editor current content length: {len(self.left_box.toPlainText())}")
        LOG.info(f"[COMPARE_LOG] Right editor current content length: {len(self.right_box.toPlainText())}")
        LOG.info(f"[COMPARE_LOG] Left highlighter state: different={len(getattr(self.left_highlighter, 'different_lines', set()))}, matching={len(getattr(self.left_highlighter, 'matching_lines', set()))}, granular={len(getattr(self.left_highlighter, 'granular_highlights', {}))}")
        LOG.info(f"[COMPARE_LOG] Right highlighter state: different={len(getattr(self.right_highlighter, 'different_lines', set()))}, matching={len(getattr(self.right_highlighter, 'matching_lines', set()))}, granular={len(getattr(self.right_highlighter, 'granular_highlights', {}))}")

        if not ns or ns.startswith(("Loading", "No ", "Unable", "kubernetes package")):
            LOG.info(f"[COMPARE_LOG] Invalid namespace, aborting: '{ns}'")
            return
        if not rt or rt.startswith(("Select", "Loading", "No ", "Unable", "kubernetes package")):
            LOG.info(f"[COMPARE_LOG] Invalid resource type, aborting: '{rt}'")
            return
        if not a or a.startswith(("No ", "Select")) or not b or b.startswith(("No ", "Select")):
            LOG.info(f"[COMPARE_LOG] Invalid resources, aborting - Resource1: '{a}', Resource2: '{b}'")
            return

        # Parse resource names and namespaces for All Namespaces mode
        if ns == "All Namespaces":
            # Extract resource name and namespace from "name (namespace)" format
            a_name, a_ns = self._parse_resource_name(a)
            b_name, b_ns = self._parse_resource_name(b)
        else:
            # Use selected namespace for both resources
            a_name, a_ns = a, ns
            b_name, b_ns = b, ns

        # Get current cluster name for saved YAML lookup
        cluster = self._get_current_cluster_name()

        # Try to load saved YAML first, fallback to cluster
        LOG.info(f"[COMPARE_LOG] Loading YAML for left resource: {rt}/{a_name} @ {a_ns}")
        left_yaml = self._load_saved_yaml(cluster, a_ns, rt, a_name) or self._get_resource_yaml(a_ns, rt, a_name)
        LOG.info(f"[COMPARE_LOG] Left YAML loaded, length: {len(left_yaml)}")
        
        LOG.info(f"[COMPARE_LOG] Loading YAML for right resource: {rt}/{b_name} @ {b_ns}")
        right_yaml = self._load_saved_yaml(cluster, b_ns, rt, b_name) or self._get_resource_yaml(b_ns, rt, b_name)
        LOG.info(f"[COMPARE_LOG] Right YAML loaded, length: {len(right_yaml)}")
        
        LOG.info(f"[COMPARE_LOG] YAMLs identical: {left_yaml == right_yaml}")
        if a_name == b_name and a_ns == b_ns:
            LOG.info(f"[COMPARE_LOG] COMPARING SAME RESOURCE TO ITSELF!")
        
        # SPECIFIC TEST: Check if comparing kube-controller-manager-desktop-control-plane to itself
        if (a_name == "kube-controller-manager-desktop-control-plane" and 
            b_name == "kube-controller-manager-desktop-control-plane" and
            a_ns == "kube-system" and b_ns == "kube-system"):
            LOG.debug("=== TESTING kube-controller-manager-desktop-control-plane self-comparison ===")
            LOG.debug(f"Left YAML length: {len(left_yaml)}")
            LOG.debug(f"Right YAML length: {len(right_yaml)}")
            LOG.debug(f"YAMLs identical: {left_yaml == right_yaml}")
            if left_yaml != right_yaml:
                LOG.debug("YAMLs are different - finding differences...")
                left_lines = left_yaml.splitlines()
                right_lines = right_yaml.splitlines()
                for i, (l1, l2) in enumerate(zip(left_lines, right_lines)):
                    if l1 != l2:
                        LOG.debug(f"Diff line {i}: LEFT='{l1}' RIGHT='{l2}'")
            LOG.debug("=== END TEST ===")

        self.left_label.setText(f"{rt} / {a_name} @ {a_ns}")
        self.right_label.setText(f"{rt} / {b_name} @ {b_ns}")

        # Store resource info for editing
        self._left_resource_info = (a_ns, rt, a_name)
        self._right_resource_info = (b_ns, rt, b_name)
        
        LOG.info(f"[COMPARE_LOG] About to apply comparison highlighting...")
        LOG.info(f"[COMPARE_LOG] Left YAML length: {len(left_yaml)}, Right YAML length: {len(right_yaml)}")
        LOG.info(f"[COMPARE_LOG] YAMLs identical: {left_yaml == right_yaml}")
        self._apply_comparison_highlighting(left_yaml, right_yaml)
        LOG.info(f"[COMPARE_LOG] Comparison highlighting completed")
        
        # Log final highlighter state after highlighting
        LOG.info(f"[COMPARE_LOG] FINAL Left highlighter state: different={len(getattr(self.left_highlighter, 'different_lines', set()))}, matching={len(getattr(self.left_highlighter, 'matching_lines', set()))}, granular={len(getattr(self.left_highlighter, 'granular_highlights', {}))}")
        LOG.info(f"[COMPARE_LOG] FINAL Right highlighter state: different={len(getattr(self.right_highlighter, 'different_lines', set()))}, matching={len(getattr(self.right_highlighter, 'matching_lines', set()))}, granular={len(getattr(self.right_highlighter, 'granular_highlights', {}))}")
        
        # Verify text content after highlighting
        final_left_content = self.left_box.toPlainText()
        final_right_content = self.right_box.toPlainText()
        LOG.info(f"[COMPARE_LOG] FINAL Left editor content length: {len(final_left_content)}")
        LOG.info(f"[COMPARE_LOG] FINAL Right editor content length: {len(final_right_content)}")
        LOG.info(f"[COMPARE_LOG] FINAL Content matches input: left={final_left_content == left_yaml}, right={final_right_content == right_yaml}")

        self.compare_area.show()
        self.main_layout.update()
        self.compare_area.updateGeometry()
        LOG.info(f"[COMPARE_LOG] ===== COMPARE COMPLETED =====")

    def _list_resources_for_namespace(self, namespace: str, resource_type: str):
        rt = (resource_type or "").strip().lower()
        if not rt:
            return []

        try:
            from Utils.kubernetes_client import get_kubernetes_client
            kube = get_kubernetes_client()
            v1 = kube.v1
            apps_v1 = kube.apps_v1
            batch_v1 = kube.batch_v1
            net_v1 = kube.networking_v1

            if "node" in rt:
                items = v1.list_node().items
            elif namespace == "All Namespaces":
                # Handle All Namespaces - get resources from all namespaces
                if "pod" in rt:
                    items = v1.list_pod_for_all_namespaces().items
                elif "service" in rt or rt == "svc":
                    items = v1.list_service_for_all_namespaces().items
                elif "configmap" in rt or ("config" in rt and "map" in rt):
                    items = v1.list_config_map_for_all_namespaces().items
                elif "secret" in rt:
                    items = v1.list_secret_for_all_namespaces().items
                elif "persistentvolumeclaim" in rt or "pvc" in rt:
                    items = v1.list_persistent_volume_claim_for_all_namespaces().items
                elif "deploy" in rt:
                    items = apps_v1.list_deployment_for_all_namespaces().items
                elif "stateful" in rt:
                    items = apps_v1.list_stateful_set_for_all_namespaces().items
                elif "daemon" in rt:
                    items = apps_v1.list_daemon_set_for_all_namespaces().items
                elif "replica" in rt:
                    items = apps_v1.list_replica_set_for_all_namespaces().items
                elif "job" in rt and "cron" not in rt:
                    items = batch_v1.list_job_for_all_namespaces().items
                elif "cron" in rt:
                    items = batch_v1.list_cron_job_for_all_namespaces().items
                elif "ingress" in rt:
                    items = net_v1.list_ingress_for_all_namespaces().items
                else:
                    return []
            else:
                # Handle specific namespace
                if "pod" in rt:
                    items = v1.list_namespaced_pod(namespace).items
                elif "service" in rt or rt == "svc":
                    items = v1.list_namespaced_service(namespace).items
                elif "configmap" in rt or ("config" in rt and "map" in rt):
                    items = v1.list_namespaced_config_map(namespace).items
                elif "secret" in rt:
                    items = v1.list_namespaced_secret(namespace).items
                elif "persistentvolumeclaim" in rt or "pvc" in rt:
                    items = v1.list_namespaced_persistent_volume_claim(namespace).items
                elif "deploy" in rt:
                    items = apps_v1.list_namespaced_deployment(namespace).items
                elif "stateful" in rt:
                    items = apps_v1.list_namespaced_stateful_set(namespace).items
                elif "daemon" in rt:
                    items = apps_v1.list_namespaced_daemon_set(namespace).items
                elif "replica" in rt:
                    items = apps_v1.list_namespaced_replica_set(namespace).items
                elif "job" in rt and "cron" not in rt:
                    items = batch_v1.list_namespaced_job(namespace).items
                elif "cron" in rt:
                    items = batch_v1.list_namespaced_cron_job(namespace).items
                elif "ingress" in rt:
                    items = net_v1.list_namespaced_ingress(namespace).items
                else:
                    return []

            # Return resource names with namespace info for All Namespaces mode
            if namespace == "All Namespaces":
                return [f"{item.metadata.name} ({item.metadata.namespace})" for item in items if item and item.metadata and item.metadata.name]
            else:
                return [item.metadata.name for item in items if item and item.metadata and item.metadata.name]
        except Exception:
            return []

    # ---------- show/hide guards ----------
    def showEvent(self, event):
        super().showEvent(event)
        # Check if namespace dropdown is empty (could happen after cluster change)
        if (hasattr(self, 'namespace_combo') and self.namespace_combo and
                self.namespace_combo.count() <= 1 and
                self.namespace_combo.itemText(0) == "Loading namespaces..."):
            self._populate_namespaces()
        # Only populate namespaces if not already loaded to preserve selections
        elif not self._namespaces_loaded:
            self._populate_namespaces()
        # Ensure namespace filter is initialized
        if not hasattr(self, 'namespace_filter'):
            self.namespace_filter = "default"

    # Cluster switch handling now done via clear_for_cluster_change() method (called by ClusterView)

    def _parse_resource_name(self, resource_display_name):
        """Parse resource name from 'name (namespace)' format"""
        if ' (' in resource_display_name and resource_display_name.endswith(')'):
            name = resource_display_name.split(' (')[0]
            namespace = resource_display_name.split(' (')[1][:-1]  # Remove closing parenthesis
            return name, namespace
        else:
            # Fallback for resources without namespace info
            return resource_display_name, "default"

    def clear_for_cluster_change(self):
        """Clear data when cluster changes to prevent showing stale data"""
        try:
            # Clear namespace dropdown
            if hasattr(self, 'namespace_combo') and self.namespace_combo:
                self.namespace_combo.blockSignals(True)
                self.namespace_combo.clear()
                self.namespace_combo.addItem("Loading namespaces...")
                self.namespace_combo.setEnabled(False)
                self.namespace_combo.blockSignals(False)

            # Clear resource combos
            self._clear_resource_combos()

            # Hide compare area
            if hasattr(self, 'compare_area'):
                self.compare_area.hide()

            # Reset namespace loading flag and filter for new cluster
            self._namespaces_loaded = False
            self.namespace_filter = "default"  # Reset to default for new cluster

            # Trigger namespace reload after clearing
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._populate_namespaces)

        except Exception as e:
            LOG.error(f"Error clearing ComparePage for cluster change: {e}")

    # ---------- edit functionality ----------
    def _toggle_left_edit_mode(self):
        """Toggle left editor edit mode"""
        if self._left_edit_mode:
            # Exit edit mode - clear any errors
            self._clear_error('left')
            self.left_box.setReadOnly(True)
            self.left_box.setStyleSheet(AppStyles.DETAIL_PAGE_YAML_TEXT_STYLE)
            self.left_edit_btn.show()
            self.left_save_btn.hide()
            self.left_deploy_btn.hide()
            self.left_cancel_btn.hide()
            self._left_edit_mode = False
            # Re-enable resource dropdowns when exiting edit mode
            self._update_resource_dropdowns_state()
        else:
            # Enter edit mode - clear any errors
            self._clear_error('left')
            self.left_box.setReadOnly(False)
            self.left_box.setStyleSheet(f"""
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
            self._left_original_yaml = self.left_box.toPlainText()
            self.left_edit_btn.hide()
            self.left_save_btn.show()
            self.left_deploy_btn.show()
            self.left_cancel_btn.show()
            self._left_edit_mode = True
            # Disable resource dropdowns when entering edit mode
            self._update_resource_dropdowns_state()

    def _toggle_right_edit_mode(self):
        """Toggle right editor edit mode"""
        if self._right_edit_mode:
            # Exit edit mode - clear any errors
            self._clear_error('right')
            self.right_box.setReadOnly(True)
            self.right_box.setStyleSheet(AppStyles.DETAIL_PAGE_YAML_TEXT_STYLE)
            self.right_edit_btn.show()
            self.right_save_btn.hide()
            self.right_deploy_btn.hide()
            self.right_cancel_btn.hide()
            self._right_edit_mode = False
            # Re-enable resource dropdowns when exiting edit mode
            self._update_resource_dropdowns_state()
        else:
            # Enter edit mode - clear any errors
            self._clear_error('right')
            self.right_box.setReadOnly(False)
            self.right_box.setStyleSheet(f"""
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
            self._right_original_yaml = self.right_box.toPlainText()
            self.right_edit_btn.hide()
            self.right_save_btn.show()
            self.right_deploy_btn.show()
            self.right_cancel_btn.show()
            self._right_edit_mode = True
            # Disable resource dropdowns when entering edit mode
            self._update_resource_dropdowns_state()

    def _cancel_left_edit(self):
        """Cancel left editor changes"""
        if self._left_original_yaml:
            self.left_box.setPlainText(self._left_original_yaml)
        self._toggle_left_edit_mode()

    def _cancel_right_edit(self):
        """Cancel right editor changes"""
        if self._right_original_yaml:
            self.right_box.setPlainText(self._right_original_yaml)
        self._toggle_right_edit_mode()

    def _deploy_left_changes(self):
        """Deploy left editor changes"""
        if not self._left_resource_info:
            return

        yaml_text = self.left_box.toPlainText()
        if yaml_text == self._left_original_yaml:
            self._toggle_left_edit_mode()
            return

        try:
            yaml_data = yaml.safe_load(yaml_text)
            if not yaml_data:
                LOG.error("Invalid YAML: Empty or null document")
                return

            # Clean YAML data like DetailPageYAMLSection does
            cleaned_yaml_data = self._convert_to_kubernetes_yaml(yaml_data)

            self.left_deploy_btn.setEnabled(False)
            self.left_deploy_btn.setText("Deploying...")

            namespace, resource_type, name = self._left_resource_info
            self._update_resource(namespace, resource_type, name, cleaned_yaml_data, 'left')

        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML syntax: {str(e)}"
            self._show_error('left', error_msg)
            LOG.error(error_msg)
            self.left_deploy_btn.setEnabled(True)
            self.left_deploy_btn.setText("Deploy")

    def _deploy_right_changes(self):
        """Deploy right editor changes"""
        if not self._right_resource_info:
            return

        yaml_text = self.right_box.toPlainText()
        if yaml_text == self._right_original_yaml:
            self._toggle_right_edit_mode()
            return

        try:
            yaml_data = yaml.safe_load(yaml_text)
            if not yaml_data:
                LOG.error("Invalid YAML: Empty or null document")
                return

            # Clean YAML data like DetailPageYAMLSection does
            cleaned_yaml_data = self._convert_to_kubernetes_yaml(yaml_data)

            self.right_deploy_btn.setEnabled(False)
            self.right_deploy_btn.setText("Deploying...")

            namespace, resource_type, name = self._right_resource_info
            self._update_resource(namespace, resource_type, name, cleaned_yaml_data, 'right')

        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML syntax: {str(e)}"
            self._show_error('right', error_msg)
            LOG.error(error_msg)
            self.right_deploy_btn.setEnabled(True)
            self.right_deploy_btn.setText("Deploy")

    def _update_resource(self, namespace: str, resource_type: str, name: str, yaml_data: dict, side: str):
        """Update Kubernetes resource"""
        try:
            from Utils.kubernetes_client import get_kubernetes_client
            kube = get_kubernetes_client()

            # Connect to update result signal if not already connected
            if not hasattr(self, '_update_signals_connected'):
                kube.resource_updated.connect(self._handle_update_result)
                self._update_signals_connected = True

            # Store which side is being updated
            self._updating_side = side

            # Call async update
            kube.update_resource_async(
                self._map_kind_to_resource_type(resource_type.lower()),
                name,
                namespace,
                yaml_data
            )

        except Exception as e:
            error_msg = f"Error updating resource: {str(e)}"
            self._show_error(side, error_msg)
            LOG.error(error_msg)
            self._reset_deploy_button(side)

    def _handle_update_result(self, result):
        """Handle deployment result - copied from DetailPageYAMLSection"""
        try:
            side = getattr(self, '_updating_side', None)
            if not side:
                return

            # Reset button state first
            self._reset_deploy_button(side)

            # Handle result - exact same logic as DetailPageYAMLSection
            if not result or not isinstance(result, dict):
                LOG.error(f"Deployment failed: Invalid update result received")
                return

            if result.get('success', False):
                # Success - clear any existing errors and refresh
                self._clear_error(side)
                message = result.get('message', 'Resource updated successfully')
                LOG.info(f"Successfully deployed {side} resource changes: {message}")

                # Exit edit mode and refresh content
                if side == 'left':
                    self._toggle_left_edit_mode()
                    if self._left_resource_info:
                        self._refresh_yaml_content('left')
                else:
                    self._toggle_right_edit_mode()
                    if self._right_resource_info:
                        self._refresh_yaml_content('right')

            else:
                # Error - show error above the failing editor
                error_message = result.get('message', 'Unknown error occurred')
                self._show_error(side, f"Deployment failed: {error_message}")
                LOG.error(f"Deployment failed: {error_message}")

        except Exception as e:
            LOG.error(f"Critical error in _handle_update_result: {str(e)}")
            self._reset_deploy_button(getattr(self, '_updating_side', None))

    def _refresh_yaml_content(self, side: str):
        """Refresh YAML content after successful deployment"""
        try:
            if side == 'left' and self._left_resource_info:
                ns, rt, name = self._left_resource_info
                updated_yaml = self._get_resource_yaml(ns, rt, name)
                self.left_box.setPlainText(updated_yaml)
            elif side == 'right' and self._right_resource_info:
                ns, rt, name = self._right_resource_info
                updated_yaml = self._get_resource_yaml(ns, rt, name)
                self.right_box.setPlainText(updated_yaml)

            # Reapply comparison highlighting
            left_yaml = self.left_box.toPlainText()
            right_yaml = self.right_box.toPlainText()
            self._apply_comparison_highlighting(left_yaml, right_yaml)

        except Exception as e:
            LOG.error(f"Error refreshing {side} YAML content: {str(e)}")

    def _convert_to_kubernetes_yaml(self, data):
        """Convert Python client dict format to Kubernetes YAML format"""
        return DetailPageYAMLSection._convert_to_kubernetes_yaml(self, data)

    def _show_error(self, side: str, error_message: str):
        """Show error message above the specified editor"""
        if side == 'left' and hasattr(self, 'left_error_widget'):
            self.left_error_widget.setText(error_message)
            self.left_error_widget.show()
        elif side == 'right' and hasattr(self, 'right_error_widget'):
            self.right_error_widget.setText(error_message)
            self.right_error_widget.show()

    def _clear_error(self, side: str):
        """Clear error message for the specified editor"""
        if side == 'left' and hasattr(self, 'left_error_widget'):
            self.left_error_widget.hide()
        elif side == 'right' and hasattr(self, 'right_error_widget'):
            self.right_error_widget.hide()

    def _save_left_changes(self):
        """Save left editor changes without deploying"""
        if not self._left_resource_info:
            return

        yaml_text = self.left_box.toPlainText()
        if yaml_text == self._left_original_yaml:
            # No changes to save
            return

        try:
            # Validate YAML syntax
            yaml_data = yaml.safe_load(yaml_text)
            if not yaml_data:
                LOG.error("Invalid YAML: Empty or null document")
                return

            # Save locally to disk
            self._save_yaml_locally('left', yaml_text)

            # Update the original YAML to current content (save changes)
            self._left_original_yaml = yaml_text
            self._clear_error('left')
            LOG.info("Left editor changes saved successfully")

            # Update comparison highlighting with current editor content
            left_yaml = self.left_box.toPlainText()
            right_yaml = self.right_box.toPlainText()
            self._apply_comparison_highlighting(left_yaml, right_yaml)

        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML syntax: {str(e)}"
            self._show_error('left', error_msg)
            LOG.error(error_msg)

    def _save_right_changes(self):
        """Save right editor changes without deploying"""
        if not self._right_resource_info:
            return

        yaml_text = self.right_box.toPlainText()
        if yaml_text == self._right_original_yaml:
            # No changes to save
            return

        try:
            # Validate YAML syntax
            yaml_data = yaml.safe_load(yaml_text)
            if not yaml_data:
                LOG.error("Invalid YAML: Empty or null document")
                return

            # Save locally to disk
            self._save_yaml_locally('right', yaml_text)

            # Update the original YAML to current content (save changes)
            self._right_original_yaml = yaml_text
            self._clear_error('right')
            LOG.info("Right editor changes saved successfully")

            # Update comparison highlighting with current editor content
            left_yaml = self.left_box.toPlainText()
            right_yaml = self.right_box.toPlainText()
            self._apply_comparison_highlighting(left_yaml, right_yaml)

        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML syntax: {str(e)}"
            self._show_error('right', error_msg)
            LOG.error(error_msg)

    def _reset_deploy_button(self, side: str):
        """Reset deploy button after error"""
        if side == 'left':
            self.left_deploy_btn.setEnabled(True)
            self.left_deploy_btn.setText("Deploy")
        elif side == 'right':
            self.right_deploy_btn.setEnabled(True)
            self.right_deploy_btn.setText("Deploy")

    def _update_resource_dropdowns_state(self):
        """Enable/disable resource dropdowns based on edit mode state"""
        # Disable dropdowns if either editor is in edit mode
        enable_dropdowns = not (self._left_edit_mode or self._right_edit_mode)

        self.resource1_combo.setEnabled(enable_dropdowns)
        self.resource2_combo.setEnabled(enable_dropdowns)

    def _create_searchable_combo(self, placeholder_text: str, combo_id: str):
        """Create a searchable combo box using QMenu approach"""
        combo = QComboBox()
        combo.setEditable(False)
        combo.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        combo.setFixedHeight(32)
        combo.setMinimumWidth(120)
        combo.addItem(placeholder_text)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(1)
        combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())

        view = QListView()
        combo.setView(view)
        combo.setMaxVisibleItems(10)
        view.setUniformItemSizes(True)
        view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)

        # Store search state for this combo
        setattr(combo, '_search_menu', None)
        setattr(combo, '_search_input', None)
        setattr(combo, '_search_action', None)
        setattr(combo, '_original_items', [])
        setattr(combo, '_combo_id', combo_id)

        # Override showPopup to show QMenu instead
        combo.showPopup = lambda: self._show_search_menu(combo)

        return combo

    def _show_search_menu(self, combo):
        """Show QMenu with search functionality instead of popup"""
        # Store original items on first use
        if not combo._original_items:
            combo._original_items = [combo.itemText(i) for i in range(combo.count())]

        # Create or update the search menu
        if not combo._search_menu:
            combo._search_menu = QMenu(self)
            combo._search_menu.setStyleSheet(f"""
                QMenu {{
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 5px;
                }}
                QMenu::item {{
                    padding: 5px 20px;
                    border-radius: 3px;
                }}
                QMenu::item:selected {{
                    background-color: #0078d7;
                }}
            """)

        # Create search input if not exists
        if not combo._search_input:
            combo._search_input = QLineEdit(self)
            combo._search_input.setPlaceholderText("Search resources...")
            combo._search_input.setFixedWidth(combo.width() - 10)
            combo._search_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 3px;
                    padding: 5px;
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border: 1px solid #0078d7;
                }}
            """)
            combo._search_input.textChanged.connect(lambda text: self._filter_menu_items(combo, text))
            combo._search_action = QWidgetAction(self)
            combo._search_action.setDefaultWidget(combo._search_input)

        # Update menu with current items
        self._update_search_menu(combo)

        # Show menu below combo
        button_pos = combo.mapToGlobal(QPoint(0, combo.height()))
        combo._search_menu.move(button_pos)
        combo._search_menu.show()

        # Focus search input
        combo._search_input.setFocus()
        combo._search_input.clear()

    def _update_search_menu(self, combo):
        """Update the search menu with current items"""
        combo._search_menu.clear()
        combo._search_menu.addAction(combo._search_action)

        # Add items as actions
        if combo._original_items:
            for item in combo._original_items:
                if not item.startswith("Select resource"):
                    action = QAction(item, combo._search_menu)
                    action.triggered.connect(lambda checked, i=item: self._handle_menu_selection(combo, i))
                    combo._search_menu.addAction(action)
        else:
            action = QAction("No resources found", combo._search_menu)
            action.setEnabled(False)
            combo._search_menu.addAction(action)

    def _filter_menu_items(self, combo, search_text):
        """Filter menu items based on search text"""
        if not combo._original_items:
            return

        combo._search_menu.clear()
        combo._search_menu.addAction(combo._search_action)

        search_lower = search_text.lower()
        filtered_items = [item for item in combo._original_items
                          if not item.startswith("Select resource") and search_lower in item.lower()]

        if filtered_items:
            for item in filtered_items:
                action = QAction(item, combo._search_menu)
                action.triggered.connect(lambda checked, i=item: self._handle_menu_selection(combo, i))
                combo._search_menu.addAction(action)
        else:
            action = QAction("No matching resources", combo._search_menu)
            action.setEnabled(False)
            combo._search_menu.addAction(action)

        # Keep focus on search input
        combo._search_input.setFocus()

    def _handle_menu_selection(self, combo, item):
        """Handle selection from search menu"""
        # Find the item in the combo and select it
        index = combo.findText(item)
        if index >= 0:
            combo.setCurrentIndex(index)
        combo._search_menu.hide()

    # ---------- Local Save Functionality ----------

    def _get_current_cluster_name(self):
        """Get current cluster name with simplified fallback"""
        try:
            cluster_name = getattr(self.cluster_connector, 'current_cluster', None) or 'unknown-cluster'
            return cluster_name
        except Exception as e:
            LOG.error(f"Error getting cluster name: {e}")
            return 'unknown-cluster'

    def _get_save_directory(self):
        """Get or create save directory with fallback"""
        try:
            # Try application directory first
            if getattr(sys, 'frozen', False):
                # Running as executable
                app_dir = os.path.dirname(sys.executable)
            else:
                # Running as script
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            save_dir = os.path.join(app_dir, 'saved_yamls')

            # Test write permissions
            os.makedirs(save_dir, exist_ok=True)
            test_file = os.path.join(save_dir, '.test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)

            return save_dir

        except (OSError, PermissionError):
            # Fallback to temp directory
            temp_dir = tempfile.gettempdir()
            save_dir = os.path.join(temp_dir, 'orchetrix_saved_yamls')
            os.makedirs(save_dir, exist_ok=True)
            return save_dir

    def _get_save_file_path(self, cluster, namespace, resource_type, resource_name):
        """Generate file path for saved YAML"""
        save_dir = self._get_save_directory()
        # Clean filename components
        clean_cluster = ''.join(c for c in cluster if c.isalnum() or c in '-_')
        clean_namespace = ''.join(c for c in namespace if c.isalnum() or c in '-_')
        clean_type = ''.join(c for c in resource_type if c.isalnum() or c in '-_')
        clean_name = ''.join(c for c in resource_name if c.isalnum() or c in '-_')

        filename = f"{clean_cluster}_{clean_namespace}_{clean_type}_{clean_name}.json"
        return os.path.join(save_dir, filename)

    def _save_yaml_locally(self, side, yaml_content):
        """Save YAML to local file"""
        try:
            if side == 'left' and self._left_resource_info:
                namespace, resource_type, resource_name = self._left_resource_info
            elif side == 'right' and self._right_resource_info:
                namespace, resource_type, resource_name = self._right_resource_info
            else:
                return

            cluster = self._get_current_cluster_name()
            file_path = self._get_save_file_path(cluster, namespace, resource_type, resource_name)

            # Create save data
            save_data = {
                "cluster": cluster,
                "namespace": namespace,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "yaml_content": yaml_content,
                "original_yaml": getattr(self, f'_{side}_original_yaml', yaml_content),
                "timestamp": datetime.now().isoformat()
            }

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            LOG.info(f"Saved {side} YAML locally: {file_path}")

        except Exception as e:
            LOG.error(f"Error saving {side} YAML locally: {e}")

    def _load_saved_yaml(self, cluster, namespace, resource_type, resource_name):
        """Load saved YAML if exists"""
        try:
            file_path = self._get_save_file_path(cluster, namespace, resource_type, resource_name)

            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)

            # Verify the saved data matches current resource
            if (save_data.get('cluster') == cluster and
                    save_data.get('namespace') == namespace and
                    save_data.get('resource_type') == resource_type and
                    save_data.get('resource_name') == resource_name):

                return save_data.get('yaml_content')

            return None

        except Exception as e:
            LOG.debug(f"Error loading saved YAML: {e}")
            return None

    def _clear_all_local_saves(self):
        """Clear all saved files on app shutdown"""
        try:
            save_dir = self._get_save_directory()
            if os.path.exists(save_dir):
                for filename in os.listdir(save_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(save_dir, filename)
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            LOG.debug(f"Error removing saved file {filename}: {e}")

                LOG.info("Cleared all local save files")

        except Exception as e:
            LOG.error(f"Error clearing local saves: {e}")
