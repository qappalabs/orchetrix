"""
Base Resource Page - Main base class for Kubernetes resource pages
Consolidated from multiple duplicate implementations for better maintainability
"""

import os
import logging
import weakref
import time  # FIXED: Add missing time import
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
from UI.Icons import resource_path
from UI.LoadingSpinner import LoadingOverlay, create_loading_overlay, create_compact_spinner
from Utils.unified_resource_loader import get_unified_resource_loader, LoadResult
from Utils.data_formatters import format_age, parse_memory_value, format_percentage, truncate_string
from Utils.error_handler import get_error_handler, safe_execute, error_handler
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager
from Utils.kubernetes_client import get_kubernetes_client
from log_handler import method_logger, class_logger



# Constants for performance tuning - optimized for large datasets - FIXED
BATCH_SIZE = 100  # FIXED: Increased batch size for better large data performance
SCROLL_DEBOUNCE_MS = 150   # FIXED: Optimized debounce for large data stability
SEARCH_DEBOUNCE_MS = 500  # FIXED: Longer debounce for large dataset search performance
MAX_ITEMS_IN_MEMORY = 2000  # FIXED: Increased memory limit for large datasets
LARGE_DATASET_THRESHOLD = 200  # FIXED: Lower threshold to activate optimizations earlier
MAX_TABLE_ROWS_BEFORE_VIRTUAL = 100  # FIXED: New constant for virtual scrolling

# Cache system removed

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
        self.namespace_filter = "default"  # Start with default namespace, will be updated when namespaces are loaded
        self.search_bar = None
        self.namespace_combo = None

        self.loading_thread = None
        self.delete_thread = None
        self.batch_delete_thread = None

        # Performance optimizations for large datasets - FIXED
        self.is_loading_initial = False
        self.is_loading_more = False
        self.all_data_loaded = False
        self.current_continue_token = None
        self.items_per_page = 200  # FIXED: Increased for better large data performance
        self.selected_items = set()
        self.reload_on_show = True
        self._large_dataset_mode = False
        self._total_item_count = 0
        self._loaded_item_count = 0
        self._enable_virtual_scrolling = False  # FIXED: Add virtual scrolling control
        self._progressive_loading = True  # FIXED: Enable progressive loading
        self._last_load_time = 0  # FIXED: Track last load time

        self.is_showing_skeleton = False

        # Cache system removed
        self._shutting_down = False
        
        # Thread safety
        import threading
        self._data_lock = threading.RLock()  # Allow recursive locking
        self._loading_lock = threading.Lock()

        # Virtual scrolling - optimized thresholds
        self._visible_start = 0
        self._visible_end = 100  # Increased for better performance
        self._render_buffer = 20  # Extra rows to render for smooth scrolling
        self._remaining_resources = []  # Store remaining resources for lazy loading
        
        # Debouncing timers
        # Use unified debounced updater instead of individual timers
        from Utils.debounced_updater import get_debounced_updater
        self._debounced_updater = get_debounced_updater()
        

        self.kube_client = get_kubernetes_client()
        self._load_more_indicator_widget = None

        self._message_widget_container = None
        self._table_stack = None

        # Loading spinner overlay
        self._loading_overlay = None
        self._is_showing_loading = False
        self._spinner_type = "circular"  # Default spinner type, can be overridden

        # Track if data has been loaded at least once
        self._initial_load_done = False

    def showEvent(self, event):
        """Override showEvent to automatically load data when page becomes visible"""
        super().showEvent(event)
        
        # OPTIMIZED: Load immediately for better performance like AppChart
        # Removed startup delay that was causing slow namespace loading
        
        # Normal show event handling - load immediately if app is already started
        self._handle_normal_show_event()
    
    def _is_app_starting(self):
        """Check if the application is still in startup phase"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if not app:
                return False
            
            # Check if we're still within the first few seconds of app startup
            if not hasattr(app, '_startup_time'):
                import time
                app._startup_time = time.time()
                return True
            
            import time
            time_since_startup = time.time() - app._startup_time
            return time_since_startup < 6  # Consider app starting for first 6 seconds
            
        except Exception:
            return False  # If we can't determine, assume app is ready
    
    def _deferred_startup_load(self):
        """Perform deferred loading after startup to avoid splash screen lag"""
        try:
            # Only proceed if we haven't loaded yet and widget is still visible
            if self.isVisible() and not hasattr(self, '_startup_load_done'):
                self._startup_load_done = True
                
                # Show a subtle loading indicator
                self._show_startup_loading_message()
                
                # Start the actual loading
                self._handle_normal_show_event()
        except Exception as e:
            logging.debug(f"Error in deferred startup load: {e}")
    
    def _show_startup_loading_message(self):
        """Show a subtle message that data is loading"""
        try:
            if hasattr(self, 'table') and self.table:
                # Clear the table completely first to remove any status/action widgets
                self.clear_table()
                
                # Set a loading message in the table temporarily
                self.table.setRowCount(1)
                
                from PyQt6.QtWidgets import QTableWidgetItem
                from PyQt6.QtCore import Qt
                
                item = QTableWidgetItem("🔄 Loading resources...")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(0, 0, item)
                
                # Span the loading message across all columns
                if self.table.columnCount() > 0:
                    self.table.setSpan(0, 0, 1, self.table.columnCount())
                    
        except Exception as e:
            logging.debug(f"Error showing startup loading message: {e}")
    
    def _handle_normal_show_event(self):
        """Handle normal show event loading (after startup) - OPTIMIZED for fast namespace loading"""
        # Load namespaces dynamically - check if they need refreshing after cluster change
        if not hasattr(self, '_namespaces_loaded') or not self._namespaces_loaded:
            self._namespaces_loaded = True
            self._load_namespaces_async()  # Load namespaces immediately like AppChart
        else:
            # Check if namespace dropdown is empty (could happen after cluster change)
            if (hasattr(self, 'namespace_combo') and self.namespace_combo and 
                self.namespace_combo.count() <= 1 and 
                self.namespace_combo.itemText(0) == "Loading namespaces..."):
                logging.debug(f"Detected empty namespace dropdown in {self.__class__.__name__}, refreshing")
                self._load_namespaces_async()
        
        # Always try to load data when page becomes visible if we don't have current data
        if not self.is_loading_initial and (not self.resources or not self._initial_load_done):
            QTimer.singleShot(50, self._auto_load_data)  # Reduced delay for faster loading

    def _auto_load_data(self):
        """Auto-load data when page is shown - FIXED for large data performance"""
        if hasattr(self, 'resource_type') and self.resource_type and not self.is_loading_initial:
            # FIXED: Check if we have recent data to avoid redundant loads
            if (hasattr(self, '_last_load_time') and self._last_load_time > 0 and 
                time.time() - self._last_load_time < 5.0):  # 5 second throttle
                logging.debug(f"Recent data available for {self.__class__.__name__}, skipping auto-load")
                return
                
            logging.debug(f"Auto-loading data for {self.__class__.__name__}")  # Reduced to debug
            self._initial_load_done = True  # Mark as done to prevent repeated attempts
            self._last_load_time = time.time()  # FIXED: Track load time
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

    def _format_age(self, timestamp):
        """Format age for display"""
        if not timestamp:
            return "Unknown"
        
        # Calculate age directly (no caching)
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
            
            return result
            
        except Exception as e:
            logging.error(f"Error formatting age: {e}")
            return "Unknown"

    def _manage_memory_usage(self):
        """Manage memory usage to prevent crashes with large datasets"""
        try:
            if not self._large_dataset_mode:
                return
            
            # If we have too many items loaded, trim the oldest ones
            if len(self.resources) > MAX_ITEMS_IN_MEMORY:
                items_to_remove = len(self.resources) - MAX_ITEMS_IN_MEMORY
                # Move oldest items back to remaining resources for potential reload
                removed_items = self.resources[:items_to_remove]
                self.resources = self.resources[items_to_remove:]
                
                # Add removed items back to the front of remaining resources
                self._remaining_resources = removed_items + self._remaining_resources
                
                # Update display
                self._display_resources(self.resources)
                self._update_items_count()
                
                logging.info(f"Memory management: Trimmed {items_to_remove} items from display")
                
            # Force garbage collection
            import gc
            gc.collect()
            
        except Exception as e:
            logging.error(f"Error in memory management: {e}")

    # Thread-safe data access methods
    # Cache methods removed
    
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

    # Loading Spinner Methods
    def _create_loading_overlay(self):
        """Create the loading overlay widget if it doesn't exist"""
        if not self._loading_overlay:
            self._loading_overlay = create_loading_overlay(self, "Loading data...", self._spinner_type)
            # Position overlay to cover the entire page
            self._loading_overlay.setGeometry(self.rect())

    def _resize_loading_overlay(self):
        """Resize the loading overlay to match the page size"""
        if self._loading_overlay:
            self._loading_overlay.setGeometry(self.rect())

    def show_loading_indicator(self, message="Loading data..."):
        """Show the loading spinner overlay with optional message"""
        if not self._is_showing_loading:
            self._create_loading_overlay()
            self._resize_loading_overlay()
            self._loading_overlay.show_loading(message)
            self._is_showing_loading = True

    def hide_loading_indicator(self):
        """Hide the loading spinner overlay"""
        if self._is_showing_loading and self._loading_overlay:
            self._loading_overlay.hide_loading()
            self._is_showing_loading = False

    def update_loading_message(self, message):
        """Update the loading message while spinner is showing"""
        if self._is_showing_loading and self._loading_overlay:
            self._loading_overlay.set_message(message)

    def resizeEvent(self, event):
        """Handle resize events to reposition loading overlay"""
        super().resizeEvent(event)
        self._resize_loading_overlay()

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
                padding: 5px 16px;
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
        
        # Namespace combo with label - only show for namespaced resources
        namespace_label = None
        if getattr(self, 'show_namespace_dropdown', True):
            namespace_label = QLabel("Namespace:")
            namespace_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: normal;")
            namespace_label.setMinimumWidth(70)
            
            self.namespace_combo = QComboBox()
            # Start with loading indicator, will be populated dynamically
            self.namespace_combo.addItem("Loading namespaces...")
            self.namespace_combo.currentTextChanged.connect(self._on_namespace_changed)
            self.namespace_combo.setFixedWidth(150)
            self.namespace_combo.setFixedHeight(32)
        else:
            self.namespace_combo = None
        
        # Apply consistent styling with proper icon
        import os

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
        if self.namespace_combo:
            self.namespace_combo.setStyleSheet(combo_style)
        
        # Add widgets to layout with proper spacing
        filters_layout.addWidget(search_label)
        filters_layout.addWidget(self.search_bar)
        
        # Only add namespace dropdown if it exists
        if self.namespace_combo and namespace_label:
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
        """Perform comprehensive search across all resources"""
        search_text = self.search_bar.text().strip()
        
        if not search_text:
            # No search query, reload normal resources
            self._clear_search_and_reload()
            return
        
        # Perform global search across all resources
        self._perform_global_search(search_text.lower())

    def _clear_search_and_reload(self):
        """Clear search and reload normal resources"""
        # Mark that we're no longer in search mode
        self._is_searching = False
        self._current_search_query = None
        
        # Reload normal resources
        self.force_load_data()
    
    def _perform_global_search(self, search_text):
        """Perform global search across all resources in cluster"""
        try:
            # Mark that we're in search mode
            self._is_searching = True
            self._current_search_query = search_text
            
            # Show search loading indicator
            self._show_search_loading_message(search_text)
            
            # Start global search using the unified resource loader
            self._start_global_search_thread(search_text)
            
        except Exception as e:
            logging.error(f"Error starting global search: {e}")
            # Fall back to local search
            self._filter_resources_linear(search_text)
    
    def _show_search_loading_message(self, search_query):
        """Show loading message during search"""
        try:
            if hasattr(self, 'table') and self.table:
                # Clear the table completely first to remove any status/action widgets
                self.clear_table()
                
                # Set single row for loading message
                self.table.setRowCount(1)
                
                from PyQt6.QtWidgets import QTableWidgetItem
                from PyQt6.QtCore import Qt
                
                item = QTableWidgetItem(f"🔍 Searching for '{search_query}' across all resources...")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(0, 0, item)
                
                # Span the loading message across all columns
                if self.table.columnCount() > 1:
                    self.table.setSpan(0, 0, 1, self.table.columnCount())
                    
        except Exception as e:
            logging.debug(f"Error showing search loading message: {e}")
    
    def _start_global_search_thread(self, search_text):
        """Start global search using background thread"""
        try:
            # Use the unified resource loader with search parameters
            from Utils.unified_resource_loader import get_unified_resource_loader
            
            unified_loader = get_unified_resource_loader()
            
            # Connect to search results handler
            if not hasattr(self, '_search_signals_connected'):
                unified_loader.loading_completed.connect(self._on_search_results_loaded)
                unified_loader.loading_error.connect(self._on_search_error)
                self._search_signals_connected = True
            
            # Determine namespace for search
            search_namespace = None if self.namespace_filter == "All Namespaces" else self.namespace_filter
            
            # Start comprehensive search
            self._current_search_operation_id = unified_loader.load_resources_with_search_async(
                resource_type=self.resource_type,
                namespace=search_namespace,
                search_query=search_text
            )
            
            logging.info(f"Started global search for '{search_text}' in {self.resource_type}")
            
        except Exception as e:
            logging.error(f"Failed to start global search thread: {e}")
            # Fallback to local search
            self._filter_resources_linear(search_text)
    
    def _on_search_results_loaded(self, resource_type, result):
        """Handle search results from unified loader"""
        try:
            # Only process if this matches our resource type and we're still searching
            if (resource_type != self.resource_type or 
                not getattr(self, '_is_searching', False)):
                return
            
            if not result.success:
                self._on_search_error(resource_type, result.error_message or "Search failed")
                return
            
            # Update resources with search results
            search_results = result.items or []
            
            # Display search results
            self._display_resources(search_results)
            self._update_items_count()
            
            # Log search results
            if search_results:
                logging.info(f"Search found {len(search_results)} {resource_type} matching '{self._current_search_query}'")
            else:
                logging.info(f"Search found no {resource_type} matching '{self._current_search_query}'")
            
        except Exception as e:
            logging.error(f"Error processing search results: {e}")
    
    def _on_search_error(self, resource_type, error_message):
        """Handle search errors"""
        if resource_type != self.resource_type:
            return
            
        logging.error(f"Search error for {resource_type}: {error_message}")
        
        # Show error message in table
        try:
            if hasattr(self, 'table') and self.table:
                # Clear the table completely first to remove any status/action widgets
                self.clear_table()
                
                # Set single row for error message
                self.table.setRowCount(1)
                
                from PyQt6.QtWidgets import QTableWidgetItem
                from PyQt6.QtCore import Qt
                
                item = QTableWidgetItem(f"❌ Search failed: {error_message}")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(0, 0, item)
                
                # Span the error message across all columns
                if self.table.columnCount() > 1:
                    self.table.setSpan(0, 0, 1, self.table.columnCount())
                    
        except Exception as e:
            logging.debug(f"Error showing search error message: {e}")
    
    def _filter_resources_linear(self, search_text):
        """Fallback local search (when global search fails)"""
        if not search_text:
            self._display_resources(self.resources)
            return
        
        # Simple fast search - no indexing overhead
        search_lower = search_text.lower()
        filtered = [r for r in self.resources 
                   if search_lower in r.get("name", "").lower() 
                   or search_lower in r.get("namespace", "").lower()]
        
        self._display_resources(filtered)

    def _load_namespaces_async(self):
        """Load available namespaces dynamically using unified loader for better performance"""
        try:
            # REMOVED startup check for better performance - load namespaces immediately like AppChart

            # Use unified resource loader for better performance and caching (like AppsChart)
            from Utils.unified_resource_loader import get_unified_resource_loader
            unified_loader = get_unified_resource_loader()
            
            # Connect signals if not already connected
            if not hasattr(self, '_namespace_signals_connected'):
                unified_loader.loading_completed.connect(self._on_namespaces_loaded_unified)
                unified_loader.loading_error.connect(self._on_namespace_error_unified)
                self._namespace_signals_connected = True
            
            # Load namespaces using unified loader (same as AppsChart for fast performance)
            self._namespace_operation_id = unified_loader.load_resources_async('namespaces')
            
        except Exception as e:
            logging.error(f"Failed to start namespace loading: {e}")
            # Fallback to default namespaces
            self._on_namespaces_loaded(["default", "kube-system", "kube-public"])

    def _on_namespaces_loaded_unified(self, resource_type: str, result):
        """Handle namespaces loaded from unified loader"""
        if resource_type != 'namespaces':
            return
        
        if result.success:
            # Extract namespace names from the processed results
            namespaces = [item.get('name', '') for item in result.items if item.get('name')]
            
            # Sort namespaces with default first, then alphabetically  
            important_namespaces = ["default", "kube-system", "kube-public", "kube-node-lease"]
            other_namespaces = sorted([ns for ns in namespaces if ns not in important_namespaces])
            sorted_namespaces = [ns for ns in important_namespaces if ns in namespaces] + other_namespaces
            
            self._on_namespaces_loaded(sorted_namespaces)
        else:
            self._on_namespace_error_unified('namespaces', result.error_message or "Failed to load namespaces")

    def _on_namespace_error_unified(self, resource_type: str, error_message: str):
        """Handle namespace loading errors from unified loader"""
        if resource_type == 'namespaces':
            logging.error(f"Failed to load namespaces via unified loader: {error_message}")
            self._on_namespaces_loaded(["default", "kube-system", "kube-public"])
    
    def _on_namespaces_loaded(self, namespaces):
        """Handle loaded namespaces and populate dropdown - FIXED to prevent confusion"""
        try:
            if not self.namespace_combo:
                # For cluster-scoped resources, set namespace filter to All Namespaces
                self.namespace_filter = "All Namespaces"
                return
            
            # FIXED: Temporarily disconnect the signal to prevent recursive calls
            try:
                self.namespace_combo.currentTextChanged.disconnect(self._on_namespace_changed)
            except:
                pass  # Signal might not be connected yet
            
            # Clear existing items
            self.namespace_combo.clear()
            
            # Add "All Namespaces" option first for backward compatibility
            self.namespace_combo.addItem("All Namespaces")
            
            # Add all loaded namespaces
            for namespace in namespaces:
                if namespace:  # Ensure namespace is not empty
                    self.namespace_combo.addItem(namespace)
            
            # FIXED: Set default selection more carefully
            if not hasattr(self, 'namespace_filter') or self.namespace_filter == "default":
                # Set to default namespace if it exists
                default_index = self.namespace_combo.findText("default")
                if default_index >= 0:
                    self.namespace_combo.setCurrentIndex(default_index)
                    self.namespace_filter = "default"
                    logging.info(f"Set namespace dropdown to 'default' (index {default_index})")
                else:
                    # If no default namespace, use "All Namespaces"
                    self.namespace_combo.setCurrentIndex(0)
                    self.namespace_filter = "All Namespaces"
                    logging.info(f"Set namespace dropdown to 'All Namespaces' (no default found)")
            else:
                # Try to restore the current namespace filter
                current_index = self.namespace_combo.findText(self.namespace_filter)
                if current_index >= 0:
                    self.namespace_combo.setCurrentIndex(current_index)
                    logging.info(f"Restored namespace dropdown to '{self.namespace_filter}' (index {current_index})")
                else:
                    # Fallback to All Namespaces if current filter not found
                    self.namespace_combo.setCurrentIndex(0)
                    self.namespace_filter = "All Namespaces"
                    logging.info(f"Fallback: Set namespace dropdown to 'All Namespaces'")
            
            # FIXED: Reconnect the signal after setting the dropdown
            self.namespace_combo.currentTextChanged.connect(self._on_namespace_changed)
            
            # Re-enable the dropdown after successful loading
            self.namespace_combo.setEnabled(True)
                
            logging.info(f"Loaded {len(namespaces)} namespaces into dropdown, current filter: {self.namespace_filter}")
            
        except Exception as e:
            logging.error(f"Error updating namespace dropdown: {e}")
            # FIXED: Ensure signal is reconnected and dropdown enabled even on error
            try:
                if self.namespace_combo:
                    self.namespace_combo.currentTextChanged.connect(self._on_namespace_changed)
                    self.namespace_combo.setEnabled(True)
            except:
                pass
            # Set a default filter to prevent issues
            self.namespace_filter = "All Namespaces"
    
    def refresh_namespaces(self):
        """Refresh the namespace dropdown - can be called externally"""
        self._namespaces_loaded = False  # Reset the flag
        self._load_namespaces_async()

    def _on_namespace_changed(self, namespace):
        """Handle namespace filter changes - FIXED with minimal cache clearing"""
        if namespace == "Loading namespaces...":
            return  # Ignore the loading placeholder
            
        old_namespace = getattr(self, 'namespace_filter', 'default')
        
        # FIXED: Only proceed if namespace actually changed
        if old_namespace == namespace:
            logging.debug(f"Namespace unchanged ({namespace}), skipping reload")
            return
            
        logging.info(f"Namespace changed from '{old_namespace}' to '{namespace}'")
        
        # Cache system removed - no cache clearing needed
            
        # Update namespace filter BEFORE clearing resources
        self.namespace_filter = namespace
        
        # FIXED: Clear current resource data to prevent showing stale data
        self.resources.clear()
        self.current_continue_token = None
        self.all_data_loaded = False
        
        # FIXED: Force immediate reload with new namespace
        self.force_load_data()

    def _load_more_data_batch(self):
        """Load more data for large datasets when needed"""
        if not self._large_dataset_mode or not self._remaining_resources:
            return
        
        try:
            # Load next batch
            batch_size = min(BATCH_SIZE, len(self._remaining_resources))
            next_batch = self._remaining_resources[:batch_size]
            self._remaining_resources = self._remaining_resources[batch_size:]
            
            # Add to existing resources
            self.resources.extend(next_batch)
            self._loaded_item_count = len(self.resources)
            
            # Check if all data is loaded
            if not self._remaining_resources:
                self.all_data_loaded = True
                logging.info(f"All {self._total_item_count} items loaded")
            
            # Manage memory usage to prevent crashes
            self._manage_memory_usage()
            
            # Update display
            self._display_resources(self.resources)
            self._update_items_count()
            
            logging.debug(f"Loaded batch: {batch_size} items. Total loaded: {self._loaded_item_count}/{self._total_item_count}")
            
        except Exception as e:
            logging.error(f"Error loading more data batch: {e}")

    def _handle_scroll(self, value):
        """Handle scroll events with debouncing"""
        # Use debounced updater for scroll
        self._debounced_updater.schedule_update(
            'scroll_' + self.__class__.__name__,
            self._handle_scroll_debounced,
            delay_ms=SCROLL_DEBOUNCE_MS
        )

    def _handle_scroll_debounced(self):
        """Handle debounced scroll events with large dataset support"""
        if not self.table or self.is_loading_more:
            return
        
        scrollbar = self.table.verticalScrollBar()
        if scrollbar.value() >= scrollbar.maximum() - 10:  # Near bottom
            if self._large_dataset_mode and self._remaining_resources:
                # For large datasets, load next batch from memory
                self._load_more_data_batch()
            elif not self.all_data_loaded and self.current_continue_token:
                # For normal pagination, use traditional method
                self._load_more_data()

    def _load_more_data(self):
        """Load more data when scrolling to bottom (traditional pagination)"""
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
        # Handle "All Namespaces" efficiently by using None (which triggers optimized multi-namespace loading)
        namespace = None if self.namespace_filter == "All Namespaces" else self.namespace_filter
        self._current_operation_id = unified_loader.load_resources_async(
            resource_type=self.resource_type,
            namespace=namespace
        )
        
        logging.debug(f"Started unified loading for {self.resource_type} (operation: {self._current_operation_id})")

    def _on_unified_resources_loaded(self, resource_type: str, result: LoadResult):
        """Handle resources loaded from unified loader with large dataset optimizations"""
        try:
            # Only process if this matches our resource type
            if resource_type != self.resource_type:
                return
            
            if not result.success:
                self._on_unified_loading_error(resource_type, result.error_message or "Unknown error")
                return
            
            # Process the optimized result format
            resources = result.items or []
            
            # Check if we have a large dataset
            self._total_item_count = len(resources)
            self._large_dataset_mode = self._total_item_count > LARGE_DATASET_THRESHOLD
            
            if self._large_dataset_mode:
                logging.info(f"Large dataset detected: {self._total_item_count} items. Activating optimizations.")
                # For large datasets, only load the first batch
                self.resources = resources[:MAX_ITEMS_IN_MEMORY]
                self._loaded_item_count = len(self.resources)
                self.all_data_loaded = False
                # Store remaining items for lazy loading
                self._remaining_resources = resources[MAX_ITEMS_IN_MEMORY:]
            else:
                # Small dataset - load everything
                self.resources = resources
                self._loaded_item_count = len(self.resources)
                self.all_data_loaded = True
                self._remaining_resources = []
            
            # Always display resources, even if empty
            self._display_resources(self.resources)
            self._update_items_count()
            
            self.is_loading_initial = False
            self.is_loading_more = False
            self._initial_load_done = True

            # Hide loading indicator
            self.hide_loading_indicator()

            self.all_items_loaded_signal.emit()
            self.load_more_complete.emit()

            # Log performance info
            logging.info(f"Loaded {self._loaded_item_count}/{self._total_item_count} {resource_type} in {result.load_time_ms:.1f}ms")
            
        except Exception as e:
            logging.error(f"Error processing unified resources: {e}")
            self._on_unified_loading_error(resource_type, str(e))

    def _on_unified_loading_error(self, resource_type: str, error_message: str):
        """Handle loading errors from unified loader"""
        if resource_type != self.resource_type:
            return
        
        self.is_loading_initial = False
        self.is_loading_more = False

        # Hide loading indicator on error
        self.hide_loading_indicator()

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
        
        # Check if we're in search mode to show appropriate message
        is_searching = getattr(self, '_is_searching', False)
        current_search_query = getattr(self, '_current_search_query', None)
        search_bar_text = self.search_bar.text().strip() if hasattr(self, 'search_bar') else ""
        
        # Use either the stored search query or current search bar text
        active_search_query = current_search_query or search_bar_text
        
        if is_searching and active_search_query:
            # Show search-specific empty message
            empty_title = QLabel(f"No results found for '{active_search_query}'")
            empty_subtitle = QLabel("Try a different search term or clear the search to see all resources")
        else:
            # Show general empty message
            empty_title = QLabel("No resources found")
            empty_subtitle = QLabel("Connect to a cluster or check your filters")
        
        # Apply styling to both title and subtitle
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold; background-color: transparent; margin: 8px;")
        
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
        # Show loading indicator
        self.show_loading_indicator("Refreshing data...")

        self._clear_resources()  # Use new method to clear resources properly
        self.current_continue_token = None
        self.all_data_loaded = False
        self.is_loading_initial = True
        self._start_loading_thread()
    
    def _clear_resources(self):
        """Clear resources data array - used only for force refresh"""
        self.resources.clear()
        # Also clear any remaining resources for large datasets
        if hasattr(self, '_remaining_resources'):
            self._remaining_resources.clear()
        # Reset large dataset mode
        self._large_dataset_mode = False
        self._total_item_count = 0
        self._loaded_item_count = 0
        logging.debug("Resources data array cleared for refresh")
        
    def clear_for_cluster_change(self):
        """Clear all data when cluster changes to prevent showing stale data"""
        try:
            # Clear the table immediately
            self.clear_table()
            
            # Clear all cached data
            self._clear_resources()
            
            # Reset loading states
            self.is_loading_initial = False
            self.is_loading_more = False
            self.all_data_loaded = False
            self.current_continue_token = None
            self._initial_load_done = False
            
            # Reset namespace loading flag so namespaces get refreshed for new cluster
            if hasattr(self, '_namespaces_loaded'):
                self._namespaces_loaded = False
                logging.debug(f"Reset namespace loading flag for {self.__class__.__name__}")
            
            # Clear namespace dropdown to prevent showing stale namespaces
            if hasattr(self, 'namespace_combo') and self.namespace_combo:
                self.namespace_combo.blockSignals(True)
                self.namespace_combo.clear()
                self.namespace_combo.addItem("Loading namespaces...")
                self.namespace_combo.setEnabled(False)
                self.namespace_combo.blockSignals(False)
                self.namespace_filter = "default"  # Reset to default namespace, not "All Namespaces"
                logging.debug(f"Cleared namespace dropdown for {self.__class__.__name__}")
            
            # Clear selected items
            self.selected_items.clear()
            
            # Update UI
            self._update_items_count()
            
            # Trigger namespace reload for visible pages (fixes stuck "Loading namespaces..." issue)
            if self.isVisible() and hasattr(self, 'namespace_combo') and self.namespace_combo:
                QTimer.singleShot(100, self._load_namespaces_async)
                logging.debug(f"Triggered namespace reload for visible page {self.__class__.__name__}")
            
            logging.info(f"Cleared {self.__class__.__name__} for cluster change")
            
        except Exception as e:
            logging.error(f"Error clearing {self.__class__.__name__} for cluster change: {e}")

    def load_data(self):
        """Load data if not already loaded"""
        if not self.resources or self.reload_on_show:
            # Show loading indicator for initial load
            if not self.resources:  # Only show for truly initial loads
                self.show_loading_indicator("Loading data...")
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

    def _validate_resource_name(self, resource_name):
        """Validate that resource name is appropriate for the current resource type"""
        if not resource_name or not isinstance(resource_name, str):
            return False
        
        # Skip validation for cluster-scoped resources that don't have namespaces
        cluster_scoped_resources = {
            'nodes', 'clusterroles', 'clusterrolebindings', 
            'storageclasses', 'customresourcedefinitions',
            'ingressclasses', 'persistentvolumes',
            'validatingwebhookconfigurations', 'mutatingwebhookconfigurations',
            'priorityclasses', 'runtimeclasses'
        }
        
        if hasattr(self, 'resource_type') and self.resource_type in cluster_scoped_resources:
            return True  # Allow all names for cluster-scoped resources
            
        # For namespaced resources, check for common pod naming patterns that shouldn't appear in other resource types
        if hasattr(self, 'resource_type') and self.resource_type != 'pods':
            # Check for ReplicaSet hash patterns (pod names like "deployment-abc123-xyz789")
            import re
            # Pattern for pod names generated by ReplicaSets/Deployments
            pod_pattern = r'^.+-[a-f0-9]{8,10}-[a-z0-9]{5}$'
            if re.match(pod_pattern, resource_name):
                logging.warning(f"Resource name '{resource_name}' appears to be a pod name but resource type is '{self.resource_type}'")
                return False
                
        return True


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
        
        # Validate selected items have correct resource type format
        validated_items = []
        for resource_name, namespace in self.selected_items:
            if self._validate_resource_name(resource_name):
                validated_items.append((resource_name, namespace))
            else:
                logging.warning(f"Skipping invalid resource name for deletion: {resource_name}")
        
        if not validated_items:
            QMessageBox.information(self, "Invalid Selection", "No valid resources selected for deletion.")
            return
        
        # Update selected items to validated list
        self.selected_items = set(validated_items)
        
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
        
        # Validate selected items have correct resource type format
        validated_items = []
        for resource_name, namespace in self.selected_items:
            if self._validate_resource_name(resource_name):
                validated_items.append((resource_name, namespace))
            else:
                logging.warning(f"Skipping invalid resource name for deletion: {resource_name}")
        
        if not validated_items:
            logging.warning("No valid resources selected for deletion after validation")
            return
        
        # Update selected items to validated list
        self.selected_items = set(validated_items)

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
                # For QTableWidget - clear spans and widgets first
                if hasattr(self.table, 'clearSpans'):
                    self.table.clearSpans()
                
                # Clear any cell widgets that might interfere with new layout
                for row in range(self.table.rowCount()):
                    for col in range(self.table.columnCount()):
                        if self.table.cellWidget(row, col):
                            self.table.removeCellWidget(row, col)
                
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
        # Generate dynamic checkbox style with proper resource path resolution
        unchecked_path = resource_path("Icons/check_box_unchecked.svg")
        checked_path = resource_path("Icons/check_box_checked.svg")
        
        select_all_checkbox.setStyleSheet(f"""
            QCheckBox {{
                margin: 0px;
                padding: 0px;
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                margin: 1px;
                background-color: transparent;
                border: none;
                image: url({unchecked_path.replace(os.sep, '/')});
            }}
            QCheckBox::indicator:checked {{
                background-color: transparent;
                border: none;
                image: url({checked_path.replace(os.sep, '/')});
            }}
            QCheckBox::indicator:hover {{
                border-color: #0078d4;
            }}
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
            # Check if pod has ports for port forwarding
            if row < len(self.resources) and self.resources:
                pod_resource = self.resources[row]
                if self._has_pod_ports(pod_resource):
                    actions.append({"text": "Port Forward", "icon": "Icons/network.png", "dangerous": False})
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

    def _has_pod_ports(self, pod_resource):
        """Check if pod has exposed ports for port forwarding"""
        try:
            if not pod_resource or not pod_resource.get("raw_data"):
                return False
            raw_data = pod_resource["raw_data"]
            
            # Check containers for exposed ports
            containers = raw_data.get("spec", {}).get("containers", [])
            for container in containers:
                ports = container.get("ports", [])
                if ports:  # If any container has ports, allow port forwarding
                    return True
            
            return False
        except (KeyError, TypeError, AttributeError) as e:
            logging.debug(f"Could not check pod port forward availability: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error checking pod port forward availability: {e}")
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
        
        # Apply styling to use proper icons with dynamic resource path resolution
        unchecked_path = resource_path("Icons/check_box_unchecked.svg")
        checked_path = resource_path("Icons/check_box_checked.svg")
        
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                margin: 0px;
                padding: 0px;
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                margin: 1px;
                background-color: transparent;
                border: none;
                image: url({unchecked_path.replace(os.sep, '/')});
            }}
            QCheckBox::indicator:checked {{
                background-color: transparent;
                border: none;
                image: url({checked_path.replace(os.sep, '/')});
            }}
            QCheckBox::indicator:hover {{
                border-color: #0078d4;
            }}
        """)
        
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
            
            # Cache system removed - no cache cleanup needed
                
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