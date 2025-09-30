# orchetrix/Pages/ComparePage.py
import logging
import yaml

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSizePolicy, QPushButton, QSplitter, QListView
)
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QKeySequence, QShortcut
from PyQt6.QtCore import Qt

from Utils.unified_resource_loader import get_unified_resource_loader
from Utils.cluster_connector import get_cluster_connector

from UI.detail_sections.detailpage_yamlsection import YamlEditorWithLineNumbers

from UI.Styles import AppStyles

LOG = logging.getLogger(__name__)

class YAMLCompareHighlighter(QSyntaxHighlighter):
    """Granular line-by-line highlighter for YAML comparison"""

    def __init__(self, document):
        super().__init__(document)
        self.different_lines = set()
        self.matching_lines = set()
        self.fmt_red = QTextCharFormat()
        self.fmt_red.setForeground(QColor("red"))
        self.fmt_green = QTextCharFormat()
        self.fmt_green.setForeground(QColor("green"))

    def set_comparison_lines(self, different_lines, matching_lines):
        self.different_lines = set(different_lines or [])
        self.matching_lines = set(matching_lines or [])
        self.rehighlight()

    def highlightBlock(self, text: str):
        block_number = self.currentBlock().blockNumber()
        if block_number in self.different_lines:
            self.setFormat(0, len(text), self.fmt_red)
        elif block_number in self.matching_lines:
            self.setFormat(0, len(text), self.fmt_green)


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

        self._build_ui()

        self._populate_namespaces()

        # cluster connector hooks
        cluster_connector = get_cluster_connector()
        cluster_connector.connection_complete.connect(self._on_cluster_switch_completed)
        cluster_connector.connection_started.connect(self._on_cluster_switch_started)

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
        self.resource1_combo = QComboBox()
        self.resource1_combo.setObjectName("resource1_combo")
        self.resource1_combo.setEditable(False)
        self.resource1_combo.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        self.resource1_combo.setFixedHeight(32)
        self.resource1_combo.setMinimumWidth(120)
        self.resource1_combo.addItem("Select resource 1")
        self.resource1_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.resource1_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.resource1_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.resource1_combo.setMinimumContentsLength(1)
        self.resource1_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
        view = QListView()
        self.resource1_combo.setView(view)
        self.resource1_combo.setMaxVisibleItems(10)
        view.setUniformItemSizes(True)
        view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)

        self.resource2_combo = QComboBox()
        self.resource2_combo.setObjectName("resource2_combo")
        self.resource2_combo.setEditable(False)
        self.resource2_combo.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        self.resource2_combo.setFixedHeight(32)
        self.resource2_combo.setMinimumWidth(120)
        self.resource2_combo.addItem("Select resource 2")
        self.resource2_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.resource2_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.resource2_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.resource2_combo.setMinimumContentsLength(1)
        self.resource2_combo.setStyleSheet(AppStyles.get_dropdown_style_with_icon())
        view = QListView()
        self.resource2_combo.setView(view)
        self.resource2_combo.setMaxVisibleItems(10)
        view.setUniformItemSizes(True)
        view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)

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

        # Header row with resource labels
        header_row = QHBoxLayout()
        self.left_label = QLabel("")
        self.right_label = QLabel("")
        header_row.addWidget(self.left_label)
        header_row.addStretch()
        header_row.addWidget(self.right_label)
        header_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        compare_layout.addLayout(header_row)
        
        # Search widgets row (will be populated by _setup_search_widgets)
        self.search_row = QHBoxLayout()
        compare_layout.addLayout(self.search_row)

        # YAML comparison editors inside a splitter with synced scrolling
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_box = YamlEditorWithLineNumbers()
        self.left_box.setFont(QFont(self.font_family, self.font_size))
        self.right_box = YamlEditorWithLineNumbers()
        self.right_box.setFont(QFont(self.font_family, self.font_size))
        self.left_box.setReadOnly(True)
        self.right_box.setReadOnly(True)
        
        # Set focus policy to ensure editors can receive focus
        self.left_box.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.right_box.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Add search functionality with keyboard shortcuts first
        self._setup_search_shortcuts()
        
        # Create search widgets for both editors
        self._setup_search_widgets()

        # Set size policies to expand and fill available space
        self.left_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.right_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Set modest minimum height to avoid double-scrollbar issues
        self.left_box.setMinimumHeight(200)
        self.right_box.setMinimumHeight(200)

        # Create highlighters for granular comparison
        self.left_highlighter = YAMLCompareHighlighter(self.left_box.document())
        self.right_highlighter = YAMLCompareHighlighter(self.right_box.document())

        # Apply styling to make the text areas look better
        self.left_box.setStyleSheet(AppStyles.DETAIL_PAGE_YAML_TEXT_STYLE)
        self.right_box.setStyleSheet(AppStyles.DETAIL_PAGE_YAML_TEXT_STYLE)

        splitter.addWidget(self.left_box)
        splitter.addWidget(self.right_box)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([1, 1])
        compare_layout.addWidget(splitter, 1)

        self.compare_area.hide()
        # Add compare area directly to main layout with stretch factor
        self.main_layout.addWidget(self.compare_area, 1)

        # connects
        self.namespace_combo.currentIndexChanged.connect(self._on_namespace_changed)
        self.resource_type_combo.currentIndexChanged.connect(self._on_namespace_or_type_changed)
        self.resource1_combo.currentIndexChanged.connect(self._update_compare_button_state)
        self.resource2_combo.currentIndexChanged.connect(self._update_compare_button_state)
        self.compare_btn.clicked.connect(self._on_compare_clicked)
        
        # Add click handlers to set focus on editors
        def create_focus_handler(editor):
            original_mouse_press = editor.mousePressEvent
            def mouse_press_with_focus(event):
                editor.setFocus()
                original_mouse_press(event)
            return mouse_press_with_focus
        
        self.left_box.mousePressEvent = create_focus_handler(self.left_box)
        self.right_box.mousePressEvent = create_focus_handler(self.right_box)

    def _setup_search_widgets(self):
        """Create search widgets for both editors"""
        from UI.detail_sections.detailpage_yamlsection import SearchWidget
        
        # Create and configure search widgets
        for side, editor, close_handler in [
            ('left', self.left_box, self._on_left_search_closed),
            ('right', self.right_box, self._on_right_search_closed)
        ]:
            search_widget = SearchWidget(self.compare_area, editor=editor)
            search_widget.search_next.connect(editor.search_next)
            search_widget.search_previous.connect(editor.search_previous)
            search_widget.search_closed.connect(close_handler)
            search_widget.hide()
            
            # Store widget reference
            setattr(self, f'{side}_search_widget', search_widget)
            
            # Add to layout and override editor's search widget
            self.search_row.addWidget(search_widget)
            editor.search_widget = search_widget
            
            # Disable built-in search shortcuts to avoid conflicts
            for child in editor.findChildren(QShortcut):
                if child.key() == QKeySequence.StandardKey.Find:
                    child.setEnabled(False)
    
    def _on_left_search_closed(self):
        """Handle left search widget closed"""
        self.left_box.close_search()
        self.left_box.setFocus()
    
    def _on_right_search_closed(self):
        """Handle right search widget closed"""
        self.right_box.close_search()
        self.right_box.setFocus()

    def _setup_search_shortcuts(self):
        """Setup Ctrl+F shortcuts for both YAML editors"""
        # Create shortcuts for the entire ComparePage
        self.search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.search_shortcut.activated.connect(self._on_search_requested)
        
        # Also create shortcuts directly on the editors as fallback
        self.left_search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self.left_box)
        self.left_search_shortcut.activated.connect(self._show_left_search)
        
        self.right_search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self.right_box)
        self.right_search_shortcut.activated.connect(self._show_right_search)
        
    def _on_search_requested(self):
        """Handle Ctrl+F - determine which editor has focus and show its search"""
        # Check which editor has focus
        focused_widget = self.focusWidget()
        
        if focused_widget == self.left_box or (focused_widget and self.left_box.isAncestorOf(focused_widget)):
            # Left editor has focus
            self._show_left_search()
        elif focused_widget == self.right_box or (focused_widget and self.right_box.isAncestorOf(focused_widget)):
            # Right editor has focus  
            self._show_right_search()
        else:
            # No specific editor focused, default to left
            self.left_box.setFocus()
            self._show_left_search()
    
    def _show_left_search(self):
        """Show search widget for left editor"""
        if hasattr(self, 'right_search_widget'):
            self.right_search_widget.hide()  # Hide right search if visible
        if hasattr(self, 'left_search_widget'):
            self.left_search_widget.show()
            self.left_search_widget.focus_search()
    
    def _show_right_search(self):
        """Show search widget for right editor"""
        if hasattr(self, 'left_search_widget'):
            self.left_search_widget.hide()  # Hide left search if visible
        if hasattr(self, 'right_search_widget'):
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
    
    def _on_namespace_error_unified(self, resource_type: str, error_message: str):
        """Handle namespace loading errors from unified loader"""
        if resource_type == 'namespaces':
            LOG.error(f"Failed to load namespaces via unified loader: {error_message}")
            self._fill_namespace_combo(["default", "kube-system", "kube-public"])

    def _fill_namespace_combo(self, namespaces):
        self.namespace_combo.clear()
        if not namespaces:
            self.namespace_combo.addItem("No namespaces found")
            self.namespace_combo.setEnabled(False)
        else:
            self.namespace_combo.setEnabled(True)
            self.namespace_combo.addItem("Select namespace")
            for ns in namespaces:
                self.namespace_combo.addItem(ns)


    # ---------- namespace/type -> resources ----------
    def _on_namespace_changed(self, _=None):
        ns = self.namespace_combo.currentText().strip()
        if not ns or ns.startswith(("Select", "Loading", "No ", "Unable", "kubernetes package")):
            self._clear_resource_combos()
            return

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
                if self._list_resources_for_namespace(ns, kind):
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
            self.resource_type_combo.setCurrentIndex(0)
        self.resource_type_combo.blockSignals(False)

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
        if not ns or ns.startswith(("Select", "Loading", "No ", "Unable", "kubernetes package")):
            return
        if not rt or rt.startswith(("Select", "Loading", "No ", "Unable", "kubernetes package")):
            return
        names = self._list_resources_for_namespace(ns, rt)
        self._populate_resource_combos(names)

    def _populate_resource_combos(self, names):
        self.resource1_combo.clear()
        self.resource2_combo.clear()
        if not names:
            self.resource1_combo.addItem("No resources found")
            self.resource2_combo.addItem("No resources found")
            self.resource1_combo.setEnabled(False)
            self.resource2_combo.setEnabled(False)
        else:
            # Keep specific labels for each dropdown
            self.resource1_combo.setEnabled(True)
            self.resource1_combo.addItem("Select resource 1")
            self.resource1_combo.addItems(sorted(names))
            
            self.resource2_combo.setEnabled(True)
            self.resource2_combo.addItem("Select resource 2")
            self.resource2_combo.addItems(sorted(names))
        self._update_compare_button_state()

    def _update_compare_button_state(self):
        """Enable Compare button only when two valid resources are selected"""
        r1 = self.resource1_combo.currentText().strip()
        r2 = self.resource2_combo.currentText().strip()
        
        valid_r1 = bool(r1 and not r1.startswith(("Select", "No ", "Error")))
        valid_r2 = bool(r2 and not r2.startswith(("Select", "No ", "Error")))
        
        self.compare_btn.setEnabled(valid_r1 and valid_r2)

    # ---------- comparison functions ----------

    def _clean_resource_data(self, data):
        """Clean resource data exactly like DetailPageYAMLSection does"""
        if not isinstance(data, dict):
            return data

        def snake_to_camel(snake_str):
            if '_' not in snake_str:
                return snake_str
            components = snake_str.split('_')
            return components[0] + ''.join(word.capitalize() for word in components[1:])

        def convert_dict(obj):
            if isinstance(obj, dict):
                new_dict = {}
                for key, value in obj.items():
                    new_key = snake_to_camel(key)
                    if value is not None:
                        new_dict[new_key] = convert_dict(value)
                return new_dict
            elif isinstance(obj, list):
                return [convert_dict(item) for item in obj if item is not None]
            else:
                return obj

        converted_data = convert_dict(data)

        if isinstance(converted_data, dict):
            # Remove read-only metadata fields
            metadata_fields_to_remove = [
                'managedFields', 'resourceVersion', 'uid', 'selfLink',
                'creationTimestamp', 'generation', 'ownerReferences'
            ]

            if 'metadata' in converted_data:
                for field in metadata_fields_to_remove:
                    if field in converted_data['metadata']:
                        del converted_data['metadata'][field]

            # Remove read-only sections
            converted_data.pop('status', None)
            converted_data.pop('events', None)

        return converted_data

    def parse_yaml_string(self, yaml_string):
        """Convert YAML string to dictionary for comparison"""
        try:
            return yaml.safe_load(yaml_string) or {}
        except yaml.YAMLError:
            return {}  # Return empty dict if YAML is invalid

    def build_comprehensive_line_map(self, yaml_string):
        """Build comprehensive mapping tracking all lines with context"""
        lines = yaml_string.splitlines()
        path_to_line = {}
        line_to_path = {}
        path_stack = []
        current_context = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Handle empty lines and comments - inherit context
            if not stripped or stripped.startswith('#'):
                line_to_path[i] = current_context
                continue
                
            indent = len(line) - len(line.lstrip())
            
            if ':' in stripped:
                key = stripped.split(':', 1)[0].strip()
                if key:
                    # Adjust path stack based on indentation
                    while path_stack and path_stack[-1][1] >= indent:
                        path_stack.pop()
                    
                    # Build full path
                    if path_stack:
                        full_path = '.'.join([p[0] for p in path_stack] + [key])
                    else:
                        full_path = key
                    
                    path_to_line[full_path] = i
                    line_to_path[i] = full_path
                    current_context = full_path
                    path_stack.append((key, indent))
            else:
                # Non-key lines (like multi-line values) inherit context
                line_to_path[i] = current_context
        return path_to_line, line_to_path

    def flatten_dict(self, d, parent_key='', sep='.'):
        """Flatten nested dictionary to dot-notation paths"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def compare_yaml_semantically(self, yaml1, yaml2):
        """Compare YAML semantically with parent section detection"""
        # Parse YAML to dictionaries and flatten
        dict1 = self.flatten_dict(self.parse_yaml_string(yaml1))
        dict2 = self.flatten_dict(self.parse_yaml_string(yaml2))
        
        # Build comprehensive line mappings
        paths1, line_to_path1 = self.build_comprehensive_line_map(yaml1)
        paths2, line_to_path2 = self.build_comprehensive_line_map(yaml2)
        
        # Find different paths for parent section detection
        different_paths = set()
        for path in dict1:
            if path not in dict2 or dict1[path] != dict2[path]:
                different_paths.add(path)
        for path in dict2:
            if path not in dict1:
                different_paths.add(path)
        
        matching_lines1 = set()
        matching_lines2 = set()
        different_lines1 = set()
        different_lines2 = set()
        
        lines1 = yaml1.splitlines()
        lines2 = yaml2.splitlines()
        
        for i in range(len(lines1)):
            path = line_to_path1.get(i)
            if path and path in dict1:
                if path in dict2 and dict1[path] == dict2[path]:
                    matching_lines1.add(i)
                else:
                    different_lines1.add(i)
            else:
                line_text = lines1[i].strip()
                # Check if this is a parent section header
                if ':' in line_text and not line_text.split(':', 1)[1].strip():
                    section_key = line_text.split(':', 1)[0].strip()
                    # Count child changes for this section
                    child_changes = [p for p in different_paths if p.startswith(f'{section_key}.')]
                    if len(child_changes) >= 1:  # Threshold: 1+ child changes
                        different_lines1.add(i)
                    else:
                        line2 = lines2[i].strip() if i < len(lines2) else ""
                        if line_text == line2:
                            matching_lines1.add(i)
                        else:
                            different_lines1.add(i)
                else:
                    # Direct line comparison
                    line2 = lines2[i].strip() if i < len(lines2) else ""
                    if line_text == line2:
                        matching_lines1.add(i)
                    else:
                        different_lines1.add(i)
        
        for i in range(len(lines2)):
            path = line_to_path2.get(i)
            if path and path in dict2:
                if path in dict1 and dict1[path] == dict2[path]:
                    matching_lines2.add(i)
                else:
                    different_lines2.add(i)
            else:
                line_text = lines2[i].strip()
                if ':' in line_text and not line_text.split(':', 1)[1].strip():
                    section_key = line_text.split(':', 1)[0].strip()
                    child_changes = [p for p in different_paths if p.startswith(f'{section_key}.')]
                    if len(child_changes) >= 1:
                        different_lines2.add(i)
                    else:
                        line1 = lines1[i].strip() if i < len(lines1) else ""
                        if line_text == line1:
                            matching_lines2.add(i)
                        else:
                            different_lines2.add(i)
                else:
                    line1 = lines1[i].strip() if i < len(lines1) else ""
                    if line_text == line1:
                        matching_lines2.add(i)
                    else:
                        different_lines2.add(i)
        
        return (different_lines1, matching_lines1), (different_lines2, matching_lines2)

    def _apply_comparison_highlighting(self, left_yaml, right_yaml):
        """Apply granular line highlighting to both YAML text boxes"""
        # Set text first
        self.left_box.setPlainText(left_yaml)
        self.right_box.setPlainText(right_yaml)

        # Compare semantically and get different/matching sets
        (left_diff, left_match), (right_diff, right_match) = self.compare_yaml_semantically(left_yaml, right_yaml)



        # Update highlighters with both different and matching lines
        self.left_highlighter.set_comparison_lines(left_diff, left_match)
        self.right_highlighter.set_comparison_lines(right_diff, right_match)

        # Ensure UI sees the change immediately
        self.left_box.viewport().update()
        self.right_box.viewport().update()

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

            # Clean and convert to YAML
            cleaned_data = self._clean_resource_data(data)
            return yaml.dump(
                cleaned_data,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                width=120,
                allow_unicode=True
            )

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

        if not ns or ns.startswith(("Select", "Loading", "No ", "Unable", "kubernetes package")):
            return
        if not rt or rt.startswith(("Select", "Loading", "No ", "Unable", "kubernetes package")):
            return
        if not a or a.startswith(("No ", "Select")) or not b or b.startswith(("No ", "Select")):
            return

        left_yaml = self._get_resource_yaml(ns, rt, a)
        right_yaml = self._get_resource_yaml(ns, rt, b)

        self.left_label.setText(f"{rt} / {a} @ {ns}")
        self.right_label.setText(f"{rt} / {b} @ {ns}")

        self._apply_comparison_highlighting(left_yaml, right_yaml)

        self.compare_area.show()
        self.main_layout.update()
        self.compare_area.updateGeometry()

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
            elif "pod" in rt:
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

    # ---------- cluster switch handlers ----------
    def _on_cluster_switch_started(self, cluster_name: str):
        self.namespace_combo.clear()
        self.namespace_combo.addItem("Loading namespaces…")
        self._clear_resource_combos()
        self.compare_area.hide()
        self._namespaces_loaded = False

    def _on_cluster_switch_completed(self, cluster_name: str, success: bool, message: str):
        if success:
            self._request_namespaces()
    
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
            
            # Reset namespace loading flag
            self._namespaces_loaded = False
            
            # Trigger namespace reload for visible pages
            if self.isVisible():
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, self._populate_namespaces)
                
        except Exception as e:
            LOG.error(f"Error clearing ComparePage for cluster change: {e}")