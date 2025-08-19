"""
Base Resource Page - Main base class for Kubernetes resource pages
Consolidated from multiple duplicate implementations for better maintainability
"""

import os
import logging
import weakref
from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QLabel, QProgressBar, QHBoxLayout, QPushButton, QApplication, QTableWidgetItem,
    QAbstractItemView, QStackedWidget, QHeaderView, QFrame, QSizePolicy, QProgressDialog, QCheckBox
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QProcess, QRect
from typing import List, Any, Dict

# Import optimized unified components
from .resource_deleters import ResourceDeleterThread, BatchResourceDeleterThread
from .virtual_scroll_table import VirtualScrollTable

from Base_Components.base_components import BaseTablePage
from UI.Styles import AppStyles, AppColors
from Utils.unified_resource_loader import get_unified_resource_loader, LoadResult
from Utils.data_formatters import format_age, parse_memory_value, format_percentage, truncate_string
from Utils.error_handler import get_error_handler, safe_execute, error_handler
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager
from Utils.kubernetes_client import get_kubernetes_client
from log_handler import method_logger, class_logger

# Constants for performance tuning - optimized values
BATCH_SIZE = 100  # Increased number of items to render in each batch
SCROLL_DEBOUNCE_MS = 50   # Reduced debounce for more responsive scrolling
SEARCH_DEBOUNCE_MS = 200  # Reduced debounce for faster search
CACHE_TTL_SECONDS = 600   # Increased cache time for better performance

# Import performance components  
from Utils.unified_cache_system import get_unified_cache

@class_logger(log_level=logging.INFO, exclude_methods=['__init__', 'clear_table', 'update_table_row', 'load_more_complete', 'all_items_loaded_signal', 'force_load_data'])
class BaseResourcePage(BaseTablePage):
    """Base class for Kubernetes resource pages with optimized performance"""
    
    load_more_complete = pyqtSignal()
    all_items_loaded_signal = pyqtSignal()

    # Use bounded cache system instead of unbounded class variables

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = None
        self.resources = []
        self.namespace_filter = "default"
        self.search_bar = None
        self.namespace_combo = None

        self.loading_thread = None
        self.delete_thread = None
        self.batch_delete_thread = None

        # Performance optimizations
        self.is_loading_initial = False
        self.is_loading_more = False
        self.all_data_loaded = False
        self.current_continue_token = None
        self.items_per_page = 100  # Increased for better performance
        self.selected_items = set()
        self.reload_on_show = True

        self.is_showing_skeleton = False

        # Use unified cache system
        from Utils.unified_cache_system import get_unified_cache
        self._cache_manager = get_unified_cache()
        
        # Use specific caches for different data types  
        self._data_cache = self._cache_manager._resource_cache
        self._age_cache = self._cache_manager._formatted_data_cache
        self._formatted_cache = self._cache_manager._formatted_data_cache
        
        self._shutting_down = False
        
        
        # Thread safety
        import threading
        self._data_lock = threading.RLock()  # Allow recursive locking
        self._loading_lock = threading.Lock()
        self._cache_lock = threading.RLock()

        # Virtual scrolling - optimized thresholds
        self._visible_start = 0
        self._visible_end = 100  # Increased for better performance
        self._render_buffer = 20  # Extra rows to render for smooth scrolling
        
        # Debouncing timers
        # Use unified debounced updater instead of individual timers
        from Utils.debounced_updater import get_debounced_updater
        self._debounced_updater = get_debounced_updater()
        

        self.kube_client = get_kubernetes_client()
        self._load_more_indicator_widget = None

        self._message_widget_container = None
        self._table_stack = None
        
        
        # Track if data has been loaded at least once
        self._initial_load_done = False

    def showEvent(self, event):
        """Override showEvent to automatically load data when page becomes visible"""
        super().showEvent(event)
        # Always try to load data when page becomes visible if we don't have current data
        if not self.is_loading_initial and (not self.resources or not self._initial_load_done):
            QTimer.singleShot(50, self._auto_load_data)  # Faster response

    def _auto_load_data(self):
        """Auto-load data when page is shown"""
        if hasattr(self, 'resource_type') and self.resource_type and not self.is_loading_initial:
            logging.debug(f"Auto-loading data for {self.__class__.__name__}")  # Reduced to debug
            self._initial_load_done = True  # Mark as done to prevent repeated attempts
            self.load_data()

    def setup_ui(self, title, headers, sortable_columns=None):
        """Setup the main UI components"""
        page_main_layout = QVBoxLayout(self)
        page_main_layout.setContentsMargins(16, 16, 16, 16)
        page_main_layout.setSpacing(16)

        header_controls_layout = QHBoxLayout()
        self._create_title_and_count(header_controls_layout, title)
        page_main_layout.addLayout(header_controls_layout)
        self._add_controls_to_header(header_controls_layout)

        self._table_stack = QStackedWidget()
        page_main_layout.addWidget(self._table_stack)

        self.table = self._create_table(headers, sortable_columns)
        self._table_stack.addWidget(self.table)

        # Create a dedicated container for messages (empty/error)
        self._message_widget_container = QWidget()
        message_container_layout = QVBoxLayout(self._message_widget_container)
        message_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_container_layout.setContentsMargins(20, 20, 20, 20)
        self._table_stack.addWidget(self._message_widget_container)

        self._table_stack.setCurrentWidget(self.table)

        self.select_all_checkbox = self._create_select_all_checkbox()
        self._add_select_all_to_header()

        if hasattr(self, 'table') and self.table:
            self.table.verticalScrollBar().valueChanged.connect(self._handle_scroll)
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.installEventFilter(self)
        return page_main_layout

    def _format_age_cached(self, timestamp):
        """Format age with bounded caching to avoid repeated calculations"""
        if not timestamp:
            return "Unknown"
        
        # Use instance-level bounded cache
        cache_key = f"age_{hash(str(timestamp))}"
        
        # Check cache first
        cached_age = self._age_cache.get(cache_key)
        if cached_age is not None:
            return cached_age
        
        # Calculate age
        try:
            import datetime
            if isinstance(timestamp, str):
                created_time = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if created_time.tzinfo is None:
                    created_time = created_time.replace(tzinfo=datetime.timezone.utc)
            else:
                created_time = timestamp.replace(tzinfo=datetime.timezone.utc)
            
            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - created_time
            
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                result = f"{days}d"
            elif hours > 0:
                result = f"{hours}h"
            else:
                result = f"{minutes}m"
            
            # Cache result with TTL and size limits
            self._age_cache.set(cache_key, result)
            return result
            
        except Exception as e:
            logging.error(f"Error formatting age: {e}")
            return "Unknown"

    def _clean_age_cache(self):
        """Clean old entries from age cache - now handled automatically by bounded cache"""
        # Bounded cache handles cleanup automatically with TTL and size limits
        # Manual cleanup is no longer needed
        pass

    # Thread-safe data access methods
    def get_cached_data(self, key: str) -> Any:
        """Thread-safe cache data retrieval"""
        with self._cache_lock:
            return self._data_cache.get(key)
    
    def set_cached_data(self, key: str, value: Any) -> bool:
        """Thread-safe cache data storage"""
        with self._cache_lock:
            return self._data_cache.set(key, value)
    
    def get_resources_safely(self) -> List[Dict]:
        """Thread-safe resource list access"""
        with self._data_lock:
            return self.resources.copy() if self.resources else []
    
    def set_resources_safely(self, resources: List[Dict]):
        """Thread-safe resource list update"""
        with self._data_lock:
            self.resources = resources
    
    def is_currently_loading(self) -> bool:
        """Thread-safe loading state check"""
        with self._loading_lock:
            return self.is_loading_initial or self.is_loading_more
    
    def set_loading_state(self, is_loading: bool, is_initial: bool = True) -> bool:
        """Thread-safe loading state management - returns False if already loading"""
        with self._loading_lock:
            if is_loading:
                if self.is_loading_initial or self.is_loading_more:
                    return False  # Already loading
                if is_initial:
                    self.is_loading_initial = True
                else:
                    self.is_loading_more = True
            else:
                if is_initial:
                    self.is_loading_initial = False
                else:
                    self.is_loading_more = False
            return True
    
    def add_resources_safely(self, new_resources: List[Dict]):
        """Thread-safe resource addition (for incremental loading)"""
        with self._data_lock:
            if not self.resources:
                self.resources = []
            self.resources.extend(new_resources)
    

    def _create_title_and_count(self, layout, title_text):
        """Create title and count labels"""
        title_label = QLabel(title_text)
        title_label_style = getattr(AppStyles, "TITLE_STYLE", "font-size: 20px; font-weight: bold; color: #ffffff;")
        title_label.setStyleSheet(title_label_style)

        self.items_count = QLabel("0 items")
        items_count_style = getattr(AppStyles, "COUNT_STYLE", "color: #9ca3af; font-size: 12px; margin-left: 8px;")
        self.items_count.setStyleSheet(items_count_style)
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(title_label)
        layout.addWidget(self.items_count)

    def _add_controls_to_header(self, header_layout):
        """Add filter controls, delete button, and refresh button to header"""
        self._add_filter_controls(header_layout)
        header_layout.addStretch(1)

        # Add delete selected button
        delete_btn = self._create_delete_selected_button()
        header_layout.addWidget(delete_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_style = getattr(AppStyles, "SECONDARY_BUTTON_STYLE",
                                """QPushButton { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d;
                                               border-radius: 4px; padding: 5px 10px; }
                                   QPushButton:hover { background-color: #3d3d3d; }
                                   QPushButton:pressed { background-color: #1e1e1e; }"""
                                )
        refresh_btn.setStyleSheet(refresh_style)
        refresh_btn.clicked.connect(lambda: self.force_load_data())
        header_layout.addWidget(refresh_btn)
    
    def _create_delete_selected_button(self):
        """Create centralized delete selected button with consistent styling"""
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setObjectName("deleteSelectedBtn")
        
        # Use centralized styling
        delete_btn.setStyleSheet(self._get_delete_button_style())
        delete_btn.clicked.connect(self._handle_delete_selected)
        
        return delete_btn
    
    def _get_delete_button_style(self):
        """Centralized delete button styling"""
        return """
            QPushButton#deleteSelectedBtn {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
                margin-right: 8px;
            }
            QPushButton#deleteSelectedBtn:hover {
                background-color: #b71c1c;
            }
            QPushButton#deleteSelectedBtn:pressed {
                background-color: #8d1e1e;
            }
            QPushButton#deleteSelectedBtn:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
    
    def _handle_delete_selected(self):
        """Base implementation for delete selected functionality"""
        # Enhanced debugging for selection
        logging.debug(f"_handle_delete_selected called. Selected items: {len(self.selected_items) if hasattr(self, 'selected_items') else 'No selected_items attribute'}")
        logging.debug(f"Selected items content: {list(self.selected_items) if hasattr(self, 'selected_items') else 'N/A'}")
        
        if not self.selected_items:
            QMessageBox.information(self, "No Selection", 
                                    "Please select resources to delete by checking the checkboxes in the first column.")
            return
        
        # Confirmation dialog
        if not self._confirm_deletion(list(self.selected_items)):
            logging.debug("User cancelled deletion in confirmation dialog")
            return
            
        # Start deletion process (confirmation already done)
        logging.debug("Starting deletion process after confirmation")
        self._start_deletion_process(list(self.selected_items))
    
    def _get_selected_resources(self):
        """Get currently selected resources - to be implemented by subclasses"""
        # Default implementation - subclasses should override
        if hasattr(self, 'table'):
            selected_rows = []
            for row in range(self.table.rowCount()):
                if hasattr(self.table, 'item'):
                    item = self.table.item(row, 0)  # First column
                    if item and item.isSelected():
                        selected_rows.append(row)
            return selected_rows
        return []
    
    def _confirm_deletion(self, selected_items):
        """Confirm deletion with user"""
        count = len(selected_items)
        resource_name = self.resource_type or "resource"
        
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion",
            f"Are you sure you want to delete {count} {resource_name}(s)?\n\n"
            f"This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes
    
    def _start_deletion_process(self, selected_items):
        """Start the deletion process - bypasses confirmation since it's already confirmed"""
        # Default implementation - skip confirmation dialog since we already confirmed
        if hasattr(self, '_perform_deletion_without_confirmation'):
            self._perform_deletion_without_confirmation()
        elif hasattr(self, 'delete_selected_resources'):
            # Call delete_selected_resources but bypass the confirmation
            self._delete_selected_resources_no_confirm()
        else:
            QMessageBox.information(
                self, 
                "Not Implemented", 
                "Delete functionality not implemented for this resource type."
            )

    def _add_filter_controls(self, header_layout):
        """Add search and namespace filter controls with proper layout"""
        from PyQt6.QtWidgets import QLineEdit, QComboBox, QLabel
        from UI.Styles import AppStyles
        
        # Create a separate layout for filters with proper spacing
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(12)  # Add space between elements
        
        # Search bar with label
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: normal;")
        search_label.setMinimumWidth(50)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search resources...")
        self.search_bar.textChanged.connect(self._on_search_text_changed)
        self.search_bar.setFixedWidth(200)
        self.search_bar.setFixedHeight(32)
        
        # Apply consistent styling
        search_style = getattr(AppStyles, 'SEARCH_INPUT', 
            """QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                background-color: #353535;
            }""")
        self.search_bar.setStyleSheet(search_style)
        
        # Namespace combo with label
        namespace_label = QLabel("Namespace:")
        namespace_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: normal;")
        namespace_label.setMinimumWidth(70)
        
        self.namespace_combo = QComboBox()
        self.namespace_combo.addItems(["default", "all", "kube-system", "kube-public", "kube-node-lease"])
        self.namespace_combo.currentTextChanged.connect(self._on_namespace_changed)
        self.namespace_combo.setFixedWidth(150)
        self.namespace_combo.setFixedHeight(32)
        
        # Apply consistent styling with proper icon
        import os
        from UI.Icons import resource_path
        down_arrow_icon = resource_path("Icons/down_btn.svg")
        
        combo_style = getattr(AppStyles, 'NAMESPACE_DROPDOWN',
            f"""QComboBox {{
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: #4d4d4d;
                background-color: #353535;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }}
            QComboBox::down-arrow {{
                image: url({down_arrow_icon.replace(os.sep, '/')});
                width: 12px;
                height: 12px;
                margin-right: 4px;
            }}
            QComboBox::down-arrow:hover {{
                opacity: 0.8;
            }}""")
        self.namespace_combo.setStyleSheet(combo_style)
        
        # Add widgets to layout with proper spacing
        filters_layout.addWidget(search_label)
        filters_layout.addWidget(self.search_bar)
        filters_layout.addSpacing(16)  # Add space between search and namespace
        filters_layout.addWidget(namespace_label)
        filters_layout.addWidget(self.namespace_combo)
        
        # Add the filters layout directly to header layout
        header_layout.addLayout(filters_layout)

    def _on_search_text_changed(self, text):
        """Handle search text changes with debouncing"""
        # Use debounced updater for search
        self._debounced_updater.schedule_update(
            'search_' + self.__class__.__name__,
            self._perform_search,
            delay_ms=SEARCH_DEBOUNCE_MS
        )

    def _perform_search(self):
        """Perform fast linear search"""
        search_text = self.search_bar.text().strip()
        logging.debug(f"Performing search for: '{search_text}', resources count: {len(self.resources)}")
        
        if not search_text:
            # No search query, show all resources
            self._display_resources(self.resources)
            return
        
        # Always use fast linear search - simpler and faster for most cases
        self._filter_resources_linear(search_text.lower())


    def _filter_resources_linear(self, search_text):
        """Fast simple search"""
        if not search_text:
            self._display_resources(self.resources)
            return
        
        # Simple fast search - no indexing overhead
        search_lower = search_text.lower()
        filtered = [r for r in self.resources 
                   if search_lower in r.get("name", "").lower() 
                   or search_lower in r.get("namespace", "").lower()]
        
        self._display_resources(filtered)

    def _on_namespace_changed(self, namespace):
        """Handle namespace filter changes"""
        self.namespace_filter = namespace
        self.force_load_data()

    def _handle_scroll(self, value):
        """Handle scroll events with debouncing"""
        # Use debounced updater for scroll
        self._debounced_updater.schedule_update(
            'scroll_' + self.__class__.__name__,
            self._handle_scroll_debounced,
            delay_ms=SCROLL_DEBOUNCE_MS
        )

    def _handle_scroll_debounced(self):
        """Handle debounced scroll events"""
        if not self.table or self.is_loading_more or self.all_data_loaded:
            return
        
        scrollbar = self.table.verticalScrollBar()
        if scrollbar.value() >= scrollbar.maximum() - 10:  # Near bottom
            self._load_more_data()

    def _load_more_data(self):
        """Load more data when scrolling to bottom"""
        if self.is_loading_more or self.all_data_loaded or not self.current_continue_token:
            return
        
        self.is_loading_more = True
        self._start_loading_thread(continue_token=self.current_continue_token)

    def _start_loading_thread(self, continue_token=None):
        """Start the resource loading using unified high-performance loader"""
        # Cancel any existing loading
        if hasattr(self, 'loading_thread') and self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.cancel()
            self.loading_thread.wait(1000)
        
        # Get the unified resource loader
        unified_loader = get_unified_resource_loader()
        
        # Connect signals if not already connected
        if not hasattr(self, '_signals_connected'):
            unified_loader.loading_completed.connect(self._on_unified_resources_loaded)
            unified_loader.loading_error.connect(self._on_unified_loading_error)
            self._signals_connected = True
        
        # Start loading with optimized configuration
        namespace = self.namespace_filter if self.namespace_filter != "all" else None
        self._current_operation_id = unified_loader.load_resources_async(
            resource_type=self.resource_type,
            namespace=namespace
        )
        
        logging.debug(f"Started unified loading for {self.resource_type} (operation: {self._current_operation_id})")

    def _on_unified_resources_loaded(self, resource_type: str, result: LoadResult):
        """Handle resources loaded from unified loader"""
        try:
            # Only process if this matches our resource type
            if resource_type != self.resource_type:
                return
            
            if not result.success:
                self._on_unified_loading_error(resource_type, result.error_message or "Unknown error")
                return
            
            # Process the optimized result format
            resources = result.items or []
            
            # Replace resources (unified loader loads all at once for better performance)
            self.resources = resources
            self.all_data_loaded = True  # Unified loader loads everything efficiently
            
            # Always display resources, even if empty
            self._display_resources(self.resources)
            self._update_items_count()
            
            self.is_loading_initial = False
            self.is_loading_more = False
            self._initial_load_done = True
            
            self.all_items_loaded_signal.emit()
            self.load_more_complete.emit()
            
            # Log performance info
            if result.from_cache:
                logging.info(f"Loaded {result.total_count} {resource_type} from cache instantly")
            else:
                logging.info(f"Loaded {result.total_count} {resource_type} in {result.load_time_ms:.1f}ms")
            
        except Exception as e:
            logging.error(f"Error processing unified resources: {e}")
            self._on_unified_loading_error(resource_type, str(e))

    def _on_unified_loading_error(self, resource_type: str, error_message: str):
        """Handle loading errors from unified loader"""
        if resource_type != self.resource_type:
            return
        
        self.is_loading_initial = False
        self.is_loading_more = False
        
        # Use centralized error handling
        error_handler = get_error_handler()
        error_handler.handle_error(
            Exception(error_message), 
            f"loading {resource_type}", 
            show_dialog=True
        )
        
        self.load_more_complete.emit()

    def _on_resources_loaded(self, result):
        """Handle loaded resources"""
        try:
            resources, resource_type, next_token = result
            
            if continue_token := getattr(self.loading_thread, 'continue_token', None):
                # Append to existing resources
                self.resources.extend(resources)
            else:
                # Replace resources
                self.resources = resources
            
            self.current_continue_token = next_token
            self.all_data_loaded = not next_token
            
            self._display_resources(self.resources)
            self._update_items_count()
            
            self.is_loading_initial = False
            self.is_loading_more = False
            self._initial_load_done = True
            
            if self.all_data_loaded:
                self.all_items_loaded_signal.emit()
            
            self.load_more_complete.emit()
            
        except Exception as e:
            logging.error(f"Error processing loaded resources: {e}")
            self._on_loading_error(e)

    def _on_loading_error(self, error):
        """Handle loading errors"""
        logging.error(f"Error loading {self.resource_type}: {error}")
        self.is_loading_initial = False
        self.is_loading_more = False
        
        error_message = f"Failed to load {self.resource_type}: {str(error)}"
        self._show_error_message(error_message)

    def _display_resources(self, resources):
        """Display resources in the table with optimized handling for large datasets"""
        if not resources:
            self._show_empty_message()
            return
        
        self._table_stack.setCurrentWidget(self.table)
        
        # Clear previous selections when displaying new data
        self.selected_items.clear()
        
        # Log performance info for large datasets
        if len(resources) > 100:
            logging.info(f"Displaying {len(resources)} resources (large dataset optimization active)")
        
        # Optimized rendering for all datasets
        self._render_resources_batch(resources)


    def _render_resources_batch(self, resources, append=False):
        """Render a batch of resources to the table with optimized performance"""
        if not append:
            self.clear_table()
        
        if not resources:
            return
            
        # Disable sorting during batch rendering for better performance
        self.table.setSortingEnabled(False)
        
        start_row = self.table.rowCount() if append else 0
        
        # Set row count all at once instead of inserting one by one
        total_rows = start_row + len(resources)
        self.table.setRowCount(total_rows)
        
        # Handle large datasets efficiently
        if len(resources) > 500:
            # For large datasets, render only visible items
            batch_size = 100  # Larger batches for better performance with large data
            for i in range(0, min(200, len(resources)), batch_size):  # Limit initial render to 200 items
                batch = resources[i:i + batch_size]
                
                for j, resource in enumerate(batch):
                    row = start_row + i + j
                    if hasattr(self, 'populate_resource_row'):
                        self.populate_resource_row(row, resource)
                    else:
                        self._populate_resource_row(row, resource)
                
                # Process events every other batch for large datasets
                if i % (batch_size * 2) == 0:
                    QApplication.processEvents()
        else:
            # For smaller datasets, render normally in batches
            batch_size = 50
            for i in range(0, len(resources), batch_size):
                batch = resources[i:i + batch_size]
                
                for j, resource in enumerate(batch):
                    row = start_row + i + j
                    if hasattr(self, 'populate_resource_row'):
                        self.populate_resource_row(row, resource)
                    else:
                        self._populate_resource_row(row, resource)
                
                # Process events less frequently to reduce overhead
            if i % (batch_size * 2) == 0:
                QApplication.processEvents()
        
        # Re-enable sorting after all rows are added
        self.table.setSortingEnabled(True)

    def _populate_resource_row(self, row, resource):
        """Populate a table row with resource data - default implementation"""
        from PyQt6.QtWidgets import QTableWidgetItem
        
        # Default implementation for common fields - can be overridden by subclasses
        # Create checkbox for the first column
        checkbox_container = self._create_checkbox_container(row, resource.get("name", "Unknown"))
        self.table.setCellWidget(row, 0, checkbox_container)
        
        # Extract common resource fields
        name = resource.get("name", "Unknown")
        namespace = resource.get("namespace", "")
        age = resource.get("age", "Unknown")
        status = resource.get("status", "Unknown")
        
        # Populate basic columns that most resources have
        columns = []
        if namespace:
            columns = [name, namespace, age, status]
        else:
            columns = [name, age, status]
        
        # Populate table cells
        for col_idx, value in enumerate(columns):
            table_col = col_idx + 1  # Skip checkbox column
            if table_col < self.table.columnCount():
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, table_col, item)

    def _update_items_count(self):
        """Update the items count label"""
        count = len(self.resources)
        self.items_count.setText(f"{count} items")

    def _show_empty_message(self):
        """Show empty state message in center of table section while keeping headers visible"""
        # Keep table headers visible - don't clear the table completely
        if self.table:
            self.table.setRowCount(0)  # Just clear rows, keep headers
            self.table.show()  # Ensure table is visible
        
        # Clear and setup the message container
        self._clear_message_container()
        
        # Create centered empty message with app theme styling
        empty_title = QLabel("No resources found")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold; background-color: transparent; margin: 8px;")
        
        empty_subtitle = QLabel("Connect to a cluster or check your filters")
        empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        empty_subtitle.setStyleSheet("color: #9ca3af; font-size: 14px; background-color: transparent; margin: 4px;")
        
        # Add widgets to message container
        self._message_widget_container.layout().addWidget(empty_title)
        self._message_widget_container.layout().addWidget(empty_subtitle)
        
        # Show the message overlay but keep table visible in background
        self._table_stack.setCurrentWidget(self.table)
        
        # Switch to message container view
        self._table_stack.setCurrentWidget(self._message_widget_container)

    def _show_error_message(self, message):
        """Show error message"""
        self._clear_message_container()
        
        error_label = QLabel(f"Error: {message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("color: #ef4444; font-size: 16px;")
        error_label.setWordWrap(True)
        
        self._message_widget_container.layout().addWidget(error_label)
        self._table_stack.setCurrentWidget(self._message_widget_container)

    def _clear_message_container(self):
        """Clear the message container"""
        layout = self._message_widget_container.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def force_load_data(self):
        """Force reload of data"""
        self._clear_resources()  # Use new method to clear resources properly
        self.current_continue_token = None
        self.all_data_loaded = False
        self.is_loading_initial = True
        self._start_loading_thread()
    
    def _clear_resources(self):
        """Clear resources data array - used only for force refresh"""
        self.resources.clear()
        logging.debug("Resources data array cleared for refresh")

    def load_data(self):
        """Load data if not already loaded"""
        if not self.resources or self.reload_on_show:
            self.force_load_data()

    def _handle_select_all(self, state):
        """Handle select-all checkbox state changes."""
        # Clear current selections
        self.selected_items.clear()

        # Update all row checkboxes
        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                # Find checkbox in container
                checkbox = checkbox_container.findChild(QCheckBox)
                if checkbox:
                    # Block signals to prevent individual handler from firing
                    checkbox.blockSignals(True)
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
                    checkbox.blockSignals(False)

        # Update selected_items based on state
        if state == Qt.CheckState.Checked.value:
            # Add all items to selected set  
            for resource in self.resources:
                resource_namespace = resource.get("namespace", "")
                resource_key = (resource["name"], resource_namespace) if resource_namespace else (resource["name"], "")
                self.selected_items.add(resource_key)
                
        logging.debug(f"Select all: {state == Qt.CheckState.Checked.value}, Selected items: {len(self.selected_items)}")

    def delete_selected_resources(self):
        """Delete selected resources"""
        if hasattr(self, 'delete_thread') and self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.wait(300)
        
        # Enhanced debugging for selection
        logging.info(f"Delete selected called. Selected items: {len(self.selected_items)}")
        logging.info(f"Selected items content: {list(self.selected_items)}")
        
        if not self.selected_items:
            QMessageBox.information(self, "No Selection", "Please select resources to delete by checking the checkboxes in the first column.")
            return
        
        count = len(self.selected_items)
        result = QMessageBox.warning(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {count} selected {self.resource_type}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        resources_list = list(self.selected_items)

        progress = QProgressDialog(f"Deleting {count} {self.resource_type}...", "Cancel", 0, count, self)
        progress.setWindowTitle("Deleting Resources")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setValue(0)
        progress.show()  # Ensure dialog is visible immediately
        
        # Process events to ensure UI responsiveness
        QApplication.processEvents()

        try:
            self.batch_delete_thread = BatchResourceDeleterThread(self.resource_type, resources_list)
            self.batch_delete_thread.batch_delete_progress.connect(lambda current, total: progress.setValue(current))
            self.batch_delete_thread.batch_delete_completed.connect(
                lambda success, errors: self.on_batch_delete_completed(success, errors, progress))
            self.batch_delete_thread.start()
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Delete Error", f"Failed to start deletion process: {str(e)}")
            logging.error(f"Error starting batch delete thread: {e}")

    def _delete_selected_resources_no_confirm(self):
        """Delete selected resources without confirmation dialog (confirmation already done)"""
        if hasattr(self, 'delete_thread') and self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.wait(300)
        
        # Enhanced debugging for selection
        logging.info(f"Delete selected (no confirm) called. Selected items: {len(self.selected_items)}")
        logging.info(f"Selected items content: {list(self.selected_items)}")
        
        if not self.selected_items:
            # This should not happen since we already checked, but log it
            logging.warning("No selected items in _delete_selected_resources_no_confirm - this should not happen")
            return

        count = len(self.selected_items)
        resources_list = list(self.selected_items)

        progress = QProgressDialog(f"Deleting {count} {self.resource_type}...", "Cancel", 0, count, self)
        progress.setWindowTitle("Deleting Resources")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setValue(0)
        progress.show()  # Ensure dialog is visible immediately
        
        # Process events to ensure UI responsiveness
        QApplication.processEvents()

        try:
            self.batch_delete_thread = BatchResourceDeleterThread(self.resource_type, resources_list)
            self.batch_delete_thread.batch_delete_progress.connect(lambda current, total: progress.setValue(current))
            self.batch_delete_thread.batch_delete_completed.connect(
                lambda success, errors: self.on_batch_delete_completed(success, errors, progress))
            self.batch_delete_thread.start()
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Delete Error", f"Failed to start deletion process: {str(e)}")
            logging.error(f"Error starting batch delete thread: {e}")

    def on_batch_delete_completed(self, success_list, error_list, progress_dialog):
        """Handle batch delete completion"""
        try:
            progress_dialog.close()
            success_count = len(success_list)
            error_count = len(error_list)
            result_message = f"Deleted {success_count} of {success_count + error_count} {self.resource_type}."
            
            if error_count > 0:
                result_message += f"\n\nFailed to delete {error_count} resources:"
                for name, namespace, error in error_list[:5]:
                    ns_text = f" in namespace {namespace}" if namespace else ""
                    result_message += f"\n- {name}{ns_text}: {error}"
                if error_count > 5:
                    result_message += f"\n... and {error_count - 5} more."
            
            # Clear selected items after deletion attempt
            self.selected_items.clear()
            
            QMessageBox.information(self, "Deletion Results", result_message)
            
            # Refresh data to show current state
            self.force_load_data()
            
        except Exception as e:
            logging.error(f"Error in batch delete completion handler: {e}")
            QMessageBox.critical(self, "Error", f"Error processing deletion results: {str(e)}")
            # Still try to refresh data even if there was an error
            try:
                self.force_load_data()
            except Exception as e:
                logging.error(f"Failed to refresh data after resource modification: {e}")

    def delete_resource(self, resource_name, resource_namespace):
        """Delete a single resource"""
        if hasattr(self, 'delete_thread') and self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.wait(300)
        
        ns_text = f" in namespace {resource_namespace}" if resource_namespace else ""
        result = QMessageBox.warning(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {self.resource_type}/{resource_name}{ns_text}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        self.delete_thread = ResourceDeleterThread(self.resource_type, resource_name, resource_namespace)
        self.delete_thread.delete_completed.connect(self.on_delete_completed)
        self.delete_thread.start()

    def on_delete_completed(self, success, message, resource_name, resource_namespace):
        """Handle single delete completion"""
        if success:
            QMessageBox.information(self, "Deletion Successful", message)
            self.selected_items.discard((resource_name, resource_namespace))
            self.force_load_data()
        else:
            QMessageBox.critical(self, "Deletion Failed", message)

    def cleanup_timers_and_threads(self):
        """Cleanup timers and threads"""
        self._shutting_down = True
        
        if hasattr(self, '_debounced_updater'):
            self._debounced_updater.cancel_update('search_' + self.__class__.__name__)
            self._debounced_updater.cancel_update('scroll_' + self.__class__.__name__)
        
        # Stop threads
        for thread in [self.loading_thread, self.delete_thread, self.batch_delete_thread]:
            if thread and thread.isRunning():
                if hasattr(thread, 'cancel'):
                    thread.cancel()
                thread.wait(1000)

    def clear_table(self):
        """Clear UI table display only - DO NOT clear resources data array"""
        try:
            if hasattr(self.table, 'set_data'):
                # For VirtualScrollTable
                self.table.set_data([])
            elif hasattr(self.table, 'setRowCount'):
                # For QTableWidget
                self.table.setRowCount(0)
            elif hasattr(self.table, 'clear'):
                # For other table widgets
                self.table.clear()
            
            # DO NOT clear self.resources array - this was causing action button failures!
            # The resources array must persist so action buttons can reference resource data
            
            logging.debug("Table UI cleared successfully - resources data preserved")
            
        except Exception as e:
            logging.error(f"Error clearing table: {e}")
    
    def _create_table(self, headers, sortable_columns=None):
        """Create and configure the table with proper column resizing"""
        from PyQt6.QtWidgets import QTableWidget, QAbstractItemView, QHeaderView
        from Base_Components.base_components import CustomHeader
        from UI.Styles import AppStyles
        
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        # Use custom header for selective header-based sorting
        custom_header = CustomHeader(Qt.Orientation.Horizontal, sortable_columns, table)
        table.setHorizontalHeader(custom_header)
        table.setSortingEnabled(True)

        # Apply enhanced styling with platform overrides
        table.setStyleSheet(AppStyles.TABLE_STYLE)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Configure appearance with explicit settings
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        
        # Force consistent selection behavior
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Configure resizable columns
        self._configure_table_resizing(table, headers)

        # Connect cell click signal
        table.cellClicked.connect(self.handle_row_click)
        
        return table

    def _configure_table_resizing(self, table, headers):
        """Configure table columns for proper resizing with minimal checkbox width"""
        header = table.horizontalHeader()
        
        header.setStretchLastSection(False)
        header.setSectionsMovable(False)
        header.setSectionsClickable(True)
        header.setMinimumSectionSize(20)  # Reduced minimum
        header.setDefaultSectionSize(120)
        
        for i in range(len(headers)):
            if i == 0:  # Checkbox column
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                table.setColumnWidth(i, 20)  # Minimal width for checkbox
            elif i == len(headers) - 1:  # Last column (Actions)
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                table.setColumnWidth(i, 100)  # Fixed width for actions
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # Set the second-to-last column to stretch if we have enough columns
        if len(headers) > 2:
            stretch_col = len(headers) - 2
            header.setSectionResizeMode(stretch_col, QHeaderView.ResizeMode.Stretch)

    def _create_select_all_checkbox(self):
        """Create select all checkbox for table header"""
        from PyQt6.QtWidgets import QCheckBox
        
        select_all_checkbox = QCheckBox()
        select_all_checkbox.setStyleSheet("""
            QCheckBox {
                margin: 0px;
                padding: 0px;
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                margin: 1px;
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
                image: url(Icons/check.svg);
            }
            QCheckBox::indicator:hover {
                border-color: #0078d4;
            }
        """)
        select_all_checkbox.stateChanged.connect(self._on_select_all_changed)
        return select_all_checkbox

    def _add_select_all_to_header(self):
        """Add select all checkbox to table header using viewport overlay"""
        if not self.table or not self.select_all_checkbox:
            return
            
        # Set the header label to empty for column 0
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem(""))
        
        # Position the checkbox over the header
        def position_checkbox():
            if self.table and self.select_all_checkbox:
                header = self.table.horizontalHeader()
                if header:
                    # Get the position and size of the first column header
                    rect = header.sectionPosition(0)
                    width = header.sectionSize(0)
                    height = header.height()
                    
                    # Center the checkbox in the header
                    checkbox_size = self.select_all_checkbox.sizeHint()
                    x = rect + (width - checkbox_size.width()) // 2
                    y = (height - checkbox_size.height()) // 2
                    
                    # Set parent to header and position
                    self.select_all_checkbox.setParent(header)
                    self.select_all_checkbox.move(x, y)
                    self.select_all_checkbox.show()
        
        # Position immediately and on resize - ensure main thread
        def safe_position():
            if self.thread() == QApplication.instance().thread():
                position_checkbox()
                
        QTimer.singleShot(100, safe_position)
        self.table.horizontalHeader().sectionResized.connect(lambda: QTimer.singleShot(10, safe_position))

    def _set_header_widget(self, column, widget):
        """Set widget in table header"""
        from PyQt6.QtWidgets import QTableWidgetItem, QWidget, QHBoxLayout
        
        if hasattr(self.table, 'horizontalHeader') and widget:
            # Create a container widget to center the checkbox
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(widget)
            
            # Set header item and widget
            self.table.setHorizontalHeaderItem(column, QTableWidgetItem(""))
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, 30)
            
            # Set the container as the header widget
            header_view = self.table.horizontalHeader()
            if hasattr(header_view, 'setSectionWidget'):
                header_view.setSectionWidget(column, container)
            else:
                # Fallback: use viewport to position widget
                self.table.setIndexWidget(self.table.model().index(0, column), container)

    def _on_select_all_changed(self, state):
        """Handle select all checkbox state change"""
        self._handle_select_all(state)

    def handle_row_click(self, row, column):
        """Handle table row click"""
        # This is a placeholder - implement based on your row click logic
        pass

    def update_table_row(self, row, resource):
        """Update a specific row in the table - backward compatibility method"""
        try:
            if hasattr(self.table, 'set_data') and hasattr(self, 'resources'):
                # For VirtualScrollTable, update the data and refresh
                if 0 <= row < len(self.resources):
                    self.resources[row] = resource
                    self.table.set_data(self.resources)
            elif hasattr(self.table, 'item'):
                # For QTableWidget, update individual cells
                self._populate_resource_row(row, resource)
            
            logging.debug(f"Updated table row {row}")
            
        except Exception as e:
            logging.error(f"Error updating table row {row}: {e}")

    def _ensure_full_width_utilization(self):
        """Ensure table columns utilize full width effectively"""
        if not self.table or not hasattr(self, 'table'):
            return
            
        try:
            # Skip for VirtualScrollTable as it handles its own layout
            if hasattr(self.table, 'set_data'):
                return
                
            if not hasattr(self.table, 'horizontalHeader'):
                return
                
            header = self.table.horizontalHeader()
            total_width = self.table.viewport().width()
            
            if total_width <= 0:
                # Try again later if width is not available yet
                QTimer.singleShot(100, self._ensure_full_width_utilization)
                return
            
            # Get number of visible columns
            visible_columns = []
            for i in range(header.count()):
                if not header.isSectionHidden(i):
                    visible_columns.append(i)
            
            if not visible_columns:
                return
            
            # Calculate available width (minus scrollbar and margins)
            available_width = total_width - 40  # Account for scrollbar and margins
            
            # Find stretch columns and distribute remaining width
            stretch_columns = []
            fixed_width = 0
            
            for col in visible_columns:
                if header.sectionResizeMode(col) == QHeaderView.ResizeMode.Stretch:
                    stretch_columns.append(col)
                else:
                    fixed_width += header.sectionSize(col)
            
            # If we have stretch columns, let Qt handle it
            if stretch_columns:
                remaining_width = max(100, available_width - fixed_width)
                for col in stretch_columns:
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            else:
                # No stretch columns, make the last column stretch
                if visible_columns:
                    last_col = visible_columns[-1]
                    header.setSectionResizeMode(last_col, QHeaderView.ResizeMode.Stretch)
                    
        except Exception as e:
            logging.debug(f"Error in _ensure_full_width_utilization: {e}")

    def _handle_edit_resource(self, resource_name, resource_namespace, resource):
        """Handle editing a resource by opening it in detail page edit mode"""
        try:
            # Find the ClusterView that contains the detail manager
            parent = self.parent()
            cluster_view = None
            
            # Walk up the parent tree to find ClusterView
            while parent:
                if parent.__class__.__name__ == 'ClusterView' or hasattr(parent, 'detail_manager'):
                    cluster_view = parent
                    break
                parent = parent.parent()
            
            if cluster_view and hasattr(cluster_view, 'detail_manager'):
                # Convert plural resource type to singular for detail manager
                resource_type_singular = self.resource_type.rstrip('s') if self.resource_type.endswith('s') else self.resource_type
                # Show the detail page first  
                cluster_view.detail_manager.show_detail(resource_type_singular, resource_name, resource_namespace)
                
                # After showing detail page, trigger edit mode
                # We need to wait a bit for the detail page to load completely
                QTimer.singleShot(500, lambda: self._trigger_edit_mode(cluster_view))
                
                logging.info(f"Opening {self.resource_type}/{resource_name} in edit mode")
            else:
                # Fallback: show error if detail manager not found
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "Edit Resource",
                    f"Cannot edit {self.resource_type}/{resource_name}: Detail panel not available"
                )
                logging.warning(f"Detail manager not found for editing {resource_name}")
                
        except Exception as e:
            logging.error(f"Failed to open {resource_name} for editing: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Error", 
                f"Failed to open {resource_name} for editing: {str(e)}"
            )
    
    def _trigger_edit_mode(self, cluster_view):
        """Trigger edit mode in the detail page YAML section"""
        try:
            if hasattr(cluster_view, 'detail_manager') and cluster_view.detail_manager._detail_page:
                detail_page = cluster_view.detail_manager._detail_page
                
                # Find the YAML section and trigger edit mode
                if hasattr(detail_page, 'yaml_section'):
                    yaml_section = detail_page.yaml_section
                    if hasattr(yaml_section, 'toggle_yaml_edit_mode') and yaml_section.yaml_editor.isReadOnly():
                        yaml_section.toggle_yaml_edit_mode()
                        logging.info("Successfully activated edit mode in YAML section")
                    else:
                        logging.warning("YAML section is not in read-only mode or toggle method not found")
                else:
                    logging.warning("YAML section not found in detail page")
            else:
                logging.warning("Detail page not found or not properly initialized")
        except Exception as e:
            logging.error(f"Error triggering edit mode: {e}")

    def _create_action_button(self, row, resource_name=None, resource_namespace=None):
        """Create an action button with menu for resource actions - OLD WORKING PATTERN"""
        from PyQt6.QtWidgets import QToolButton, QMenu
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize
        from functools import partial
        from UI.Icons import resource_path
        
        button = QToolButton()

        # Use custom SVG icon
        try:
            icon_path = resource_path("Icons/Moreaction_Button.svg")
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))
                button.setIconSize(QSize(16, 16))
        except Exception as e:
            logging.warning(f"Could not load action button icon: {e}")

        # Remove text and change to icon-only style
        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        button.setFixedWidth(30)
        try:
            from UI.Styles import AppStyles
            button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE)
        except (ImportError, AttributeError) as e:
            logging.debug(f"Could not load AppStyles for button: {e}")
            # Fallback styling
            button.setStyleSheet("""
                QToolButton {
                    background-color: transparent;
                    border: none;
                    padding: 2px;
                }
                QToolButton:hover {
                    background-color: #3d3d3d;
                    border-radius: 2px;
                }
            """)
        
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create menu
        menu = QMenu(button)
        try:
            from UI.Styles import AppStyles
            menu.setStyleSheet(AppStyles.MENU_STYLE)
        except (ImportError, AttributeError) as e:
            logging.debug(f"Could not load AppStyles for menu: {e}")
            # Fallback menu styling
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    color: white;
                }
                QMenu::item {
                    padding: 5px 20px;
                }
                QMenu::item:selected {
                    background-color: #0078d4;
                }
            """)

        # Connect signals to change row appearance when menu opens/closes
        try:
            menu.aboutToShow.connect(lambda: self._on_menu_show(row))
            menu.aboutToHide.connect(lambda: self._highlight_active_row(row, False))
        except Exception as e:
            logging.warning(f"Could not connect menu signals: {e}")

        # Define actions based on resource type - matching old pattern
        actions = []
        
        # Resource-specific actions based on resource type
        if hasattr(self, 'resource_type') and self.resource_type == "pods":
            actions.extend([
                {"text": "View Logs", "icon": "Icons/logs.png", "dangerous": False},
                {"text": "SSH", "icon": "Icons/terminal.png", "dangerous": False}
            ])
        elif hasattr(self, 'resource_type') and self.resource_type == "services":
            # Check if service has ports for port forwarding
            if row < len(self.resources) and self.resources:
                service_resource = self.resources[row]
                if self._has_service_ports(service_resource):
                    actions.append({"text": "Port Forward", "icon": "Icons/network.png", "dangerous": False})
        elif hasattr(self, 'resource_type') and self.resource_type == "nodes":
            # Node-specific actions
            actions.append({"text": "View Metrics", "icon": "Icons/chart.png", "dangerous": False})
        
        # Standard actions for all resources
        actions.extend([
            {"text": "Edit", "icon": "Icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "Icons/delete.png", "dangerous": True}
        ])

        # Add actions to menu with OLD WORKING PATTERN - only pass row index
        for action_info in actions:
            try:
                action = menu.addAction(action_info["text"])
                if "icon" in action_info:
                    try:
                        action.setIcon(QIcon(resource_path(action_info["icon"])))
                    except (OSError, FileNotFoundError) as e:
                        logging.debug(f"Icon loading failed for {action_info['icon']}: {e}")
                    except Exception as e:
                        logging.error(f"Unexpected error loading icon {action_info['icon']}: {e}")
                if action_info.get("dangerous", False):
                    action.setProperty("dangerous", True)
                
                # OLD WORKING PATTERN: Only pass action and row - no resource data storage
                action.triggered.connect(
                    partial(self._handle_action, action_info["text"], row)
                )
                logging.debug(f"Action button: Connected '{action_info['text']}' for row {row}")
            except Exception as e:
                logging.error(f"Error adding action {action_info['text']}: {e}")

        button.setMenu(menu)
        return button
    
    def _has_service_ports(self, service_resource):
        """Check if service has ports for port forwarding"""
        try:
            if not service_resource or not service_resource.get("raw_data"):
                return False
            raw_data = service_resource["raw_data"]
            ports = raw_data.get("spec", {}).get("ports", [])
            return len(ports) > 0
        except (KeyError, TypeError, AttributeError) as e:
            logging.debug(f"Could not check port forward availability: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error checking port forward availability: {e}")
            return False

    def _create_action_container(self, row, action_button):
        """Create container widget for action button"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(action_button)
        return container

    def _on_menu_show(self, row):
        """Handle menu about to show - debugging"""
        logging.info(f"Action button menu opening for row {row}")
        self._highlight_active_row(row, True)
    
    def _highlight_active_row(self, row, highlight):
        """Highlight or unhighlight the active row"""
        try:
            if hasattr(self, 'table') and self.table and row < self.table.rowCount():
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        if highlight:
                            item.setBackground(QColor(AppColors.HOVER_BG))
                        else:
                            item.setBackground(QColor("transparent"))
        except Exception as e:
            logging.debug(f"Error highlighting row {row}: {e}")

    # Removed old _handle_action_with_resource method - replaced with OLD WORKING PATTERN

    def _handle_action(self, action, row):
        """Handle action button clicks - OLD WORKING PATTERN restored"""
        logging.info(f"BaseResourcePage: Action '{action}' clicked on row {row}")
        
        # Add debugging for resources array
        logging.info(f"BaseResourcePage: Resources array length: {len(self.resources) if hasattr(self, 'resources') else 'No resources attribute'}")
        
        if not hasattr(self, 'resources') or not self.resources:
            logging.warning(f"BaseResourcePage: No resources available for action '{action}' on row {row}")
            return
            
        if row >= len(self.resources):
            logging.warning(f"BaseResourcePage: Invalid row {row} for action '{action}' (only {len(self.resources)} resources)")
            return

        # OLD WORKING PATTERN: Fresh resource lookup every time
        resource = self.resources[row]
        resource_name = resource.get("name", "")
        resource_namespace = resource.get("namespace", "")
        
        logging.info(f"BaseResourcePage: Processing action '{action}' for {resource_name}" + (f" in {resource_namespace}" if resource_namespace else ""))
        
        # Handle actions with fresh resource data - matching old working pattern
        if action == "View Logs":
            if hasattr(self, 'resource_type') and self.resource_type == "pods":
                self._handle_view_logs(resource_name, resource_namespace, resource)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Logs Error", "Logs are only available for pod resources.")
        elif action == "SSH":
            if hasattr(self, 'resource_type') and self.resource_type == "pods":
                self._handle_ssh_into_pod(resource_name, resource_namespace, resource)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "SSH Error", "SSH is only available for pod resources.")
        elif action == "Port Forward":
            if hasattr(self, 'resource_type') and self.resource_type in ["pods", "services"]:
                self._handle_port_forward(resource_name, resource_namespace, resource)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Port Forward Error", "Port forwarding is only available for pods and services.")
        elif action == "Edit":
            try:
                logging.info(f"Starting edit for resource: {resource_name}")
                self._handle_edit_resource(resource_name, resource_namespace, resource)
            except Exception as e:
                logging.error(f"Error in edit action: {e}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Failed to edit {resource_name}: {str(e)}")
        elif action == "Delete":
            try:
                logging.info(f"Starting delete for resource: {resource_name}")
                self.delete_resource(resource_name, resource_namespace)
            except Exception as e:
                logging.error(f"Error in delete action: {e}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Failed to delete {resource_name}: {str(e)}")
        elif action == "View Metrics":
            # Handle node-specific View Metrics action
            if hasattr(self, 'select_node_for_graphs'):
                self.select_node_for_graphs(row)
            else:
                logging.warning(f"View Metrics action not supported for resource type: {self.resource_type}")
        else:
            logging.warning(f"BaseResourcePage: Unknown action: {action}")
    
    def _handle_port_forward(self, resource_name, namespace, resource):
        """Handle port forwarding - placeholder that pages can override"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Port Forward", f"Port forwarding for {resource_name} - functionality implemented by specific pages")
        logging.info(f"Port forward requested for {resource_name} - using placeholder implementation")

    def _handle_view_logs(self, pod_name, namespace, resource):
        """Handle viewing logs for a pod - placeholder for override"""
        try:
            # Find the ClusterView that contains the terminal panel
            parent = self.parent()
            cluster_view = None
            
            # Walk up the parent tree to find ClusterView
            while parent:
                if parent.__class__.__name__ == 'ClusterView' or hasattr(parent, 'terminal_panel'):
                    cluster_view = parent
                    break
                parent = parent.parent()
            
            if cluster_view and hasattr(cluster_view, 'terminal_panel'):
                # Create a logs tab in the terminal panel
                cluster_view.terminal_panel.create_enhanced_logs_tab(pod_name, namespace)
                
                # Show the terminal panel if it's hidden
                if not cluster_view.terminal_panel.is_visible:
                    if hasattr(cluster_view, 'toggle_terminal'):
                        cluster_view.toggle_terminal()
                    elif hasattr(cluster_view.terminal_panel, 'show_terminal'):
                        cluster_view.terminal_panel.show_terminal()
                    
                logging.info(f"Created logs tab for pod: {pod_name} in namespace: {namespace}")
            else:
                # Fallback: show error if terminal panel not found
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "Logs",
                    f"Opening logs for pod: {pod_name} in namespace: {namespace}\n\n"
                    f"Terminal panel will show logs. Use kubectl logs {pod_name} -n {namespace} if needed."
                )
                logging.warning(f"Terminal panel not found for logs tab creation")
                
        except Exception as e:
            logging.error(f"Failed to create logs tab for pod {pod_name}: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Error", 
                f"Failed to open logs for pod {pod_name}: {str(e)}"
            )

    def _handle_ssh_into_pod(self, pod_name, namespace, resource):
        """Handle SSH into a pod - placeholder for override"""
        try:
            # Find the ClusterView that contains the terminal panel
            parent = self.parent()
            cluster_view = None
            
            # Walk up the parent tree to find ClusterView
            while parent:
                if parent.__class__.__name__ == 'ClusterView' or hasattr(parent, 'terminal_panel'):
                    cluster_view = parent
                    break
                parent = parent.parent()
            
            if cluster_view and hasattr(cluster_view, 'terminal_panel'):
                # Create an SSH tab in the terminal panel
                cluster_view.terminal_panel.create_ssh_tab(pod_name, namespace)
                
                # Show the terminal panel if it's hidden
                if not cluster_view.terminal_panel.is_visible:
                    if hasattr(cluster_view, 'toggle_terminal'):
                        cluster_view.toggle_terminal()
                    elif hasattr(cluster_view.terminal_panel, 'show_terminal'):
                        cluster_view.terminal_panel.show_terminal()
                    
                logging.info(f"Created SSH tab for pod: {pod_name} in namespace: {namespace}")
            else:
                # Fallback: show error if terminal panel not found
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "SSH",
                    f"Opening SSH for pod: {pod_name} in namespace: {namespace}\n\n"
                    f"Terminal panel will show SSH session. Use kubectl exec -it {pod_name} -n {namespace} -- /bin/bash if needed."
                )
                logging.warning(f"Terminal panel not found for SSH tab creation")
                
        except Exception as e:
            logging.error(f"Failed to create SSH tab for pod {pod_name}: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Error", 
                f"Failed to open SSH for pod {pod_name}: {str(e)}"
            )

    def _create_checkbox_container(self, row, resource_name):
        """Create checkbox container for row selection"""
        from PyQt6.QtWidgets import QCheckBox, QWidget, QHBoxLayout
        
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        checkbox = QCheckBox()
        checkbox.setProperty("row", row)
        checkbox.setProperty("resource_name", resource_name)
        checkbox.stateChanged.connect(self._on_row_checkbox_changed)
        
        layout.addWidget(checkbox)
        return container

    def _on_row_checkbox_changed(self, state):
        """Handle row checkbox state changes"""
        try:
            checkbox = self.sender()
            row = checkbox.property("row")
            resource_name = checkbox.property("resource_name")
            
            # Find the resource by name instead of relying only on row index
            resource = None
            for r in self.resources:
                if r.get("name") == resource_name:
                    resource = r
                    break
            
            if resource:
                # Handle both namespaced and cluster-scoped resources
                resource_namespace = resource.get("namespace", "")
                resource_key = (resource["name"], resource_namespace) if resource_namespace else (resource["name"], "")
                
                if state == Qt.CheckState.Checked.value:
                    self.selected_items.add(resource_key)
                    logging.debug(f"Selected resource: {resource_key}")
                else:
                    self.selected_items.discard(resource_key)
                    logging.debug(f"Deselected resource: {resource_key}")
                    
                # Update select-all checkbox state
                self._update_select_all_state()
            else:
                logging.warning(f"Resource not found for checkbox: {resource_name}")
                    
        except Exception as e:
            logging.error(f"Error handling checkbox change: {e}")
    
    def _update_select_all_state(self):
        """Update the select-all checkbox based on individual selections"""
        try:
            if hasattr(self, 'table') and self.table and hasattr(self, 'select_all_checkbox'):
                total_rows = len(self.resources)
                selected_count = len(self.selected_items)
                
                if selected_count == 0:
                    self.select_all_checkbox.blockSignals(True)
                    self.select_all_checkbox.setChecked(False)
                    self.select_all_checkbox.blockSignals(False)
                elif selected_count == total_rows:
                    self.select_all_checkbox.blockSignals(True)  
                    self.select_all_checkbox.setChecked(True)
                    self.select_all_checkbox.blockSignals(False)
                else:
                    # Partially selected - could set to indeterminate if supported
                    self.select_all_checkbox.blockSignals(True)
                    self.select_all_checkbox.setChecked(False)
                    self.select_all_checkbox.blockSignals(False)
        except Exception as e:
            logging.debug(f"Error updating select-all state: {e}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_shutting_down') and not self._shutting_down:
                logging.debug("BaseResourcePage destructor called, performing cleanup")
                self.cleanup_timers_and_threads()
                # Cache cleanup is handled automatically by bounded cache system
                # No manual cache cleanup needed
        except Exception as e:
            logging.error(f"Error in BaseResourcePage destructor: {e}")

    def cleanup_on_destroy(self):
        """Explicit cleanup method that can be called before destruction"""
        try:
            self._shutting_down = True
            
            # Stop all timers
            if hasattr(self, '_debounced_updater'):
                self._debounced_updater.cancel_update('search_' + self.__class__.__name__)
                self._debounced_updater.cancel_update('scroll_' + self.__class__.__name__)
            if hasattr(self, '_render_timer'):
                try:
                    if self._render_timer is not None and self._render_timer.isActive():
                        self._render_timer.stop()
                except RuntimeError:
                    # QTimer was already deleted by Qt - this is fine during shutdown
                    pass
            
            
            # Cleanup threads
            self.cleanup_timers_and_threads()
            
            # Clear cache references (bounded caches will handle memory cleanup)
            if hasattr(self, '_data_cache'):
                self._data_cache.clear()
            if hasattr(self, '_age_cache'):
                self._age_cache.clear()
            if hasattr(self, '_formatted_cache'):
                self._formatted_cache.clear()
                
            logging.debug(f"Cleanup completed for {self.__class__.__name__}")
            
        except Exception as e:
            logging.error(f"Error in cleanup_on_destroy: {e}")


# Factory function for creating resource pages
def create_base_resource_page(resource_type, title, headers, parent=None):
    """Factory function to create a configured BaseResourcePage"""
    page = BaseResourcePage(parent)
    page.resource_type = resource_type
    page.setup_ui(title, headers)
    return page


# Export all classes for backward compatibility
# Helper classes for eliminating duplication across resource pages
class StandardResourceColumns:
    """Standard column definitions that can be reused across resource pages"""
    NAME = {"name": "Name", "key": "name", "width": 200}
    NAMESPACE = {"name": "Namespace", "key": "namespace", "width": 120}
    AGE = {"name": "Age", "key": "age", "width": 100}
    READY = {"name": "Ready", "key": "ready", "width": 80}
    STATUS = {"name": "Status", "key": "status", "width": 100}
    LABELS = {"name": "Labels", "key": "labels", "width": 250}
    # Resource-specific columns
    RESTARTS = {"name": "Restarts", "key": "restarts", "width": 80}
    NODE = {"name": "Node", "key": "node", "width": 150}
    IP = {"name": "IP", "key": "ip", "width": 120}
    TYPE = {"name": "Type", "key": "type", "width": 120}
    CLUSTER_IP = {"name": "Cluster-IP", "key": "cluster_ip", "width": 130}
    PORTS = {"name": "Port(s)", "key": "ports", "width": 150}


class ResourcePageHelpers:
    """Helper methods for resource pages to reduce duplication"""
    
    @staticmethod
    def extract_standard_field(resource: Dict[str, Any], field_key: str) -> str:
        """Extract common field values from Kubernetes resources"""
        try:
            if field_key == "name":
                return resource.get("metadata", {}).get("name", "")
            elif field_key == "namespace":
                return resource.get("metadata", {}).get("namespace", "default")
            elif field_key == "labels":
                labels = resource.get("metadata", {}).get("labels", {})
                return ", ".join([f"{k}={v}" for k, v in labels.items()]) if labels else ""
            elif field_key == "node":
                return resource.get("spec", {}).get("nodeName", "")
            elif field_key == "ip":
                return resource.get("status", {}).get("podIP", "") or resource.get("spec", {}).get("clusterIP", "")
            elif field_key == "type":
                return resource.get("spec", {}).get("type", "") or resource.get("type", "")
            elif field_key == "ports":
                ports = resource.get("spec", {}).get("ports", [])
                if ports:
                    return ", ".join([f"{p.get('port', '')}/{p.get('protocol', 'TCP')}" for p in ports])
                return ""
            else:
                return ""
        except Exception:
            return ""
    
    @staticmethod
    def setup_standard_table(table_widget, columns):
        """Setup table with standard configuration"""
        try:
            if not table_widget or not columns:
                return
                
            table_widget.setColumnCount(len(columns))
            headers = [col["name"] for col in columns]
            table_widget.setHorizontalHeaderLabels(headers)
            
            # Set column widths
            for i, col in enumerate(columns):
                if "width" in col:
                    table_widget.setColumnWidth(i, col["width"])
                    
            # Standard table properties
            table_widget.setAlternatingRowColors(True)
            table_widget.setSelectionBehavior(table_widget.SelectionBehavior.SelectRows)
            table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            table_widget.setSortingEnabled(True)
            
        except Exception as e:
            logging.error(f"Error setting up standard table: {e}")


__all__ = [
    'ResourceDeleterThread', 
    'BatchResourceDeleterThread',
    'VirtualScrollTable',
    'BaseResourcePage',
    'create_base_resource_page',
    'StandardResourceColumns',
    'ResourcePageHelpers',
    'BATCH_SIZE',
    'SCROLL_DEBOUNCE_MS',
    'SEARCH_DEBOUNCE_MS',
    'CACHE_TTL_SECONDS'
]