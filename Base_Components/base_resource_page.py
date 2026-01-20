"""
Base Resource Page - Main base class for Kubernetes resource pages
Consolidated from multiple duplicate implementations for better maintainability
"""


from Utils.resource_utils import singularize_resource_type


import logging
import time  # FIXED: Add missing time import
from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout,
    QLabel, QHBoxLayout, QPushButton, QApplication, QTableWidgetItem,
    QAbstractItemView, QStackedWidget, QHeaderView, QProgressDialog, QCheckBox
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from typing import List, Dict

# Import optimized unified components
from .resource_deleters import ResourceDeleterThread, BatchResourceDeleterThread
from .virtual_scroll_table import VirtualScrollTable

from Base_Components.base_components import BaseTablePage
from UI.Styles import AppStyles, AppColors
from UI.Icons import resource_path
from UI.ThemeManager import get_theme_manager
import Styles.BaseTablePageStyles as BaseTablePageStyles
import Styles.BaseResourcePageStyles as BaseResourcePageStyles
from UI.LoadingSpinner import create_loading_overlay
from Utils.unified_resource_loader import get_unified_resource_loader, LoadResult
from Utils.error_handler import get_error_handler
from Utils.kubernetes_client import get_kubernetes_client
from log_handler import class_logger


# Constants for performance tuning - optimized for large datasets - FIXED
BATCH_SIZE = 100  # FIXED: Increased batch size for better large data performance
SCROLL_DEBOUNCE_MS = 150   # FIXED: Optimized debounce for large data stability
SEARCH_DEBOUNCE_MS = 500  # FIXED: Longer debounce for large dataset search performance
MAX_ITEMS_IN_MEMORY = 2000  # FIXED: Increased memory limit for large datasets
# FIXED: Lower threshold to activate optimizations earlier
LARGE_DATASET_THRESHOLD = 200

# Cache system removed

@class_logger(log_level=logging.INFO, exclude_methods=['__init__', 'clear_table', 'update_table_row', 'load_more_complete', 'all_items_loaded_signal', 'force_load_data'])


class BaseResourcePage(BaseTablePage):
    # Signals for resource loading
    all_items_loaded_signal = pyqtSignal()
    load_more_complete = pyqtSignal()

    # Use bounded cache system instead of unbounded class variables

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.resource_type = None
        self.resources = []
        # Start with default namespace, will be updated when namespaces are loaded
        self.namespace_filter = "default"
        self.search_bar = None
        self.search_label = None
        self.namespace_combo = None
        self.namespace_label = None
        self._delete_btn = None

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
        self._last_load_time = 0  # FIXED: Track last load time
        self.is_showing_skeleton = False  # FIXED: Add skeleton loading state
        self._is_searching = False  # FIXED: Add search state tracking
        self._current_search_query = None  # FIXED: Add current search query tracking

        # Cache system removed
        self._shutting_down = False

        # Thread safety
        import threading
        self._data_lock = threading.RLock()  # Allow recursive locking
        self._loading_lock = threading.Lock()

        self._remaining_resources = []  # Store remaining resources for lazy loading

        # Debouncing timers
        # Use unified debounced updater instead of individual timers
        from Utils.debounced_updater import get_debounced_updater
        self._debounced_updater = get_debounced_updater()

        self.kube_client = get_kubernetes_client()

        self._message_widget_container = None
        self._table_stack = None

        # Loading spinner overlay
        self._loading_overlay = None
        self._is_showing_loading = False
        self._spinner_type = "circular"  # Default spinner type, can be overridden

        # Track if data has been loaded at least once
        self._initial_load_done = False

        # Helper Managers
        from Base_Components.resource_page_style_manager import ResourcePageStyleManager
        from Base_Components.resource_deletion_manager import ResourceDeletionManager
        from Base_Components.resource_search_handler import ResourceSearchHandler

        self.style_manager = ResourcePageStyleManager
        self.deletion_manager = ResourceDeletionManager(self)
        self.search_handler = ResourceSearchHandler(self)

    def showEvent(self, event):
        """Override showEvent to automatically load data when page becomes visible"""
        super().showEvent(event)

        # OPTIMIZED: Load immediately for better performance like AppChart
        # Removed startup delay that was causing slow namespace loading

        # Check if this page has its own loading mechanism (like NodesPage)
        has_custom_loading = (
            hasattr(self, 'cluster_connector') or 
            self.__class__.__name__ in ['NodesPage', 'AppsChart', 'ChartsPage'] or
            # Check if load_data method is overridden
            self.__class__.load_data is not BaseResourcePage.load_data
        )
        
        # Most resource pages should load immediately - only defer for very specific cases
        # The startup deferral was causing "loading resources" issues in PodsPage and others
        should_defer_startup = (
            not has_custom_loading and 
            self._is_app_starting() and
            # Only defer for pages that explicitly need it (none currently)
            self.__class__.__name__ in []  # Empty list - no pages need deferral
        )
        
        if has_custom_loading:
            # Pages with their own loading mechanisms should load immediately
            self._handle_normal_show_event()
        elif should_defer_startup:
            # Only defer for standard resource pages during app startup (currently none)
            QTimer.singleShot(500, self._deferred_startup_load)
        else:
            # Normal show event handling - load immediately (most pages)
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
            return time_since_startup < 1.5  # Very conservative - only 1.5 seconds
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

        # Load namespaces dynamically - check if they need refreshing after cluster change
        if not hasattr(self, '_namespaces_loaded') or not self._namespaces_loaded:
            self._namespaces_loaded = True
            self._load_namespaces_async()  # Load namespaces immediately like AppChart
        else:
            # Check if namespace dropdown is empty (could happen after cluster change)
            if (hasattr(self, 'namespace_combo') and self.namespace_combo
                and self.namespace_combo.count() <= 1
                    and self.namespace_combo.itemText(0) == "Loading namespaces..."):
                logging.debug(
                    f"Detected empty namespace dropdown in {self.__class__.__name__}, refreshing")
                self._load_namespaces_async()

        # Always try to load data when page becomes visible if we don't have current data
        if not self.is_loading_initial and (not self.resources or not self._initial_load_done):
            # Reduced delay for faster loading
            QTimer.singleShot(50, self._auto_load_data)

    def _auto_load_data(self):
        """Auto-load data when page is shown - FIXED for large data performance"""
        if hasattr(self, 'resource_type') and self.resource_type and not self.is_loading_initial:
            # FIXED: Check if we have recent data to avoid redundant loads
            if (hasattr(self, '_last_load_time') and self._last_load_time > 0 and
                    time.time() - self._last_load_time < 5.0):  # 5 second throttle
                logging.debug(
                    f"Recent data available for {self.__class__.__name__}, skipping auto-load")
                return

            logging.debug(f"Auto-loading data for {self.__class__.__name__}")  # Reduced to debug
            self._initial_load_done = True  # Mark as done to prevent repeated attempts
            self._last_load_time = time.time()  # FIXED: Track load time
            self.load_data()

    def setup_ui(self, title, headers, sortable_columns=None):

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

        # Create a dedicated container for messages (empty / error)
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
            self.table.setSelectionMode(
                QAbstractItemView.SelectionMode.SingleSelection)
            self.table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows)

        self.installEventFilter(self)
        return page_main_layout

    def _format_age(self, timestamp):

        if not timestamp:
            return "Unknown"

        # Calculate age directly (no caching)
        try:
            import datetime
            if isinstance(timestamp, str):
                created_time = datetime.datetime.fromisoformat(
                    timestamp.replace('Z', '+00:00'))
                if created_time.tzinfo is None:
                    created_time = created_time.replace(
                        tzinfo=datetime.timezone.utc)
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

                logging.info(
                    f"Memory management: Trimmed {items_to_remove} items from display")

            # Force garbage collection
            import gc
            gc.collect()

        except Exception as e:
            logging.error(f"Error in memory management: {e}")

    # Thread - safe data access methods
    # Cache methods removed

    def get_resources_safely(self) -> List[Dict]:

        with self._data_lock:
            return self.resources.copy() if self.resources else []

    def set_resources_safely(self, resources: List[Dict]):

        with self._data_lock:
            self.resources = resources

    def is_currently_loading(self) -> bool:

        with self._loading_lock:
            return self.is_loading_initial or self.is_loading_more

    def set_loading_state(self, is_loading: bool, is_initial: bool = True) -> bool:

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

        with self._data_lock:
            if not self.resources:
                self.resources = []
            self.resources.extend(new_resources)

    # Loading Spinner Methods
    def _create_loading_overlay(self):

        if not self._loading_overlay:
            self._loading_overlay = create_loading_overlay(
                self, "Loading data...", self._spinner_type)
            # Position overlay to cover the entire page
            self._loading_overlay.setGeometry(self.rect())

    def _resize_loading_overlay(self):

        if self._loading_overlay:
            self._loading_overlay.setGeometry(self.rect())

    def show_loading_indicator(self, message="Loading data..."):

        if not self._is_showing_loading:
            self._create_loading_overlay()
            self._resize_loading_overlay()
            self._loading_overlay.show_loading(message)
            self._is_showing_loading = True

    def hide_loading_indicator(self):

        if self._is_showing_loading and self._loading_overlay:
            self._loading_overlay.hide_loading()
            self._is_showing_loading = False

    def update_loading_message(self, message):

        if self._is_showing_loading and self._loading_overlay:
            self._loading_overlay.set_message(message)

    def resizeEvent(self, event):

        super().resizeEvent(event)
        self._resize_loading_overlay()

    def _create_title_and_count(self, layout, title_text):
        """Create title and count labels (theme-aware colors, same sizes)"""
        theme = get_theme_manager().get_current_theme()
        
        self.title_label = QLabel(title_text)
        # Preserve original font size/weight, only make color theme-aware
        self.title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {theme.colors.TEXT_LIGHT};")
        
        self.items_count = QLabel("0 items")
        # Preserve original size/margin, only make color theme-aware
        self.items_count.setStyleSheet(f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px; margin-left: 8px;")
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.items_count)

    def _add_controls_to_header(self, header_layout):

        self._add_filter_controls(header_layout)
        header_layout.addStretch(1)

        # Add delete selected button
        self._delete_btn = self._create_delete_selected_button()
        header_layout.addWidget(self._delete_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(BaseResourcePageStyles.get_refresh_button_style())
        self.refresh_btn.clicked.connect(lambda: self.force_load_data())
        header_layout.addWidget(self.refresh_btn)

    def _create_delete_selected_button(self):

        delete_btn = QPushButton("Delete Selected")
        delete_btn.setObjectName("deleteSelectedBtn")

        # Use centralized styling
        delete_btn.setStyleSheet(self._get_delete_button_style())
        delete_btn.clicked.connect(self._handle_delete_selected)

        return delete_btn

    def _get_delete_button_style(self):

        return self.style_manager.get_delete_button_style()

    def _handle_delete_selected(self):
        self.deletion_manager.handle_delete_selected(self.selected_items)

    def _confirm_deletion(self, selected_items):
        return self.deletion_manager.confirm_deletion(selected_items)

    def _start_deletion_process(self, selected_items):
        self.deletion_manager.start_deletion_process(selected_items)

    def _add_filter_controls(self, header_layout):
        self.search_handler.add_filter_controls(header_layout)

    def _on_search_text_changed(self, text):
        self.search_handler.on_search_text_changed(text)

    def _perform_search(self):
        self.search_handler.perform_search()

    def _clear_search_and_reload(self):
        self.search_handler.clear_search_and_reload()

    def _perform_global_search(self, search_text):
        self.search_handler.perform_global_search(search_text)

    def _show_search_loading_message(self, search_query):
        self.search_handler.show_search_loading_message(search_query)

    def _start_global_search_thread(self, search_text):
        self.search_handler.start_global_search_thread(search_text)

    def _on_search_results_loaded(self, resource_type, result):
        self.search_handler.on_search_results_loaded(resource_type, result)

    def _on_search_error(self, resource_type, error_message):
        self.search_handler.on_search_error(resource_type, error_message)

    def _filter_resources_linear(self, search_text):
        self.search_handler.filter_resources_linear(search_text)

    def _load_namespaces_async(self):

        try:
            # REMOVED startup check for better performance - load namespaces immediately like AppChart

            # Use unified resource loader for better performance and caching (like AppsChart)
            from Utils.unified_resource_loader import get_unified_resource_loader
            unified_loader = get_unified_resource_loader()

            # Connect signals if not already connected
            if not hasattr(self, '_namespace_signals_connected'):
                unified_loader.loading_completed.connect(
                    self._on_namespaces_loaded_unified)
                unified_loader.loading_error.connect(
                    self._on_namespace_error_unified)
                self._namespace_signals_connected = True

            # Load namespaces using unified loader (same as AppsChart for fast performance)
            self._namespace_operation_id = unified_loader.load_resources_async(
                'namespaces')

        except Exception as e:
            logging.error(f"Failed to start namespace loading: {e}")
            # Fallback to default namespaces
            self._on_namespaces_loaded(
                ["default", "kube - system", "kube - public"])

    def _on_namespaces_loaded_unified(self, resource_type: str, result):

        if resource_type != 'namespaces':
            return

        if result.success:
            # Extract namespace names from the processed results
            namespaces = [item.get('name', '')
                          for item in result.items if item.get('name')]

            # Sort namespaces with default first, then alphabetically
            important_namespaces = [
                "default", "kube - system", "kube - public", "kube - node - lease"]
            other_namespaces = sorted(
                [ns for ns in namespaces if ns not in important_namespaces])
            sorted_namespaces = [
                ns for ns in important_namespaces if ns in namespaces] + other_namespaces

            self._on_namespaces_loaded(sorted_namespaces)
        else:
            self._on_namespace_error_unified(
                'namespaces', result.error_message or "Failed to load namespaces")

    def _on_namespace_error_unified(self, resource_type: str, error_message: str):

        if resource_type == 'namespaces':
            logging.error(
                f"Failed to load namespaces via unified loader: {error_message}")
            self._on_namespaces_loaded(
                ["default", "kube - system", "kube - public"])

    def _on_namespaces_loaded(self, namespaces):

        try:
            if not self.namespace_combo:
                # For cluster - scoped resources, set namespace filter to All Namespaces
                self.namespace_filter = "All Namespaces"
                return

            # FIXED: Temporarily disconnect the signal to prevent recursive calls
            try:
                self.namespace_combo.currentTextChanged.disconnect(
                    self._on_namespace_changed)
            except BaseException:
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
                    logging.info(
                        f"Set namespace dropdown to 'default' (index {default_index})")
                else:
                    # If no default namespace, use "All Namespaces"
                    self.namespace_combo.setCurrentIndex(0)
                    self.namespace_filter = "All Namespaces"
                    logging.info(
                        "Set namespace dropdown to 'All Namespaces' (no default found)")
            else:
                # Try to restore the current namespace filter
                current_index = self.namespace_combo.findText(
                    self.namespace_filter)
                if current_index >= 0:
                    self.namespace_combo.setCurrentIndex(current_index)
                    logging.info(
                        f"Restored namespace dropdown to '{self.namespace_filter}' (index {current_index})")
                else:
                    # Fallback to All Namespaces if current filter not found
                    self.namespace_combo.setCurrentIndex(0)
                    self.namespace_filter = "All Namespaces"
                    logging.info(
                        "Fallback: Set namespace dropdown to 'All Namespaces'")

            # FIXED: Reconnect the signal after setting the dropdown
            self.namespace_combo.currentTextChanged.connect(
                self._on_namespace_changed)

            # Re - enable the dropdown after successful loading
            self.namespace_combo.setEnabled(True)

            logging.info(
                f"Loaded {len(namespaces)} namespaces into dropdown, current filter: {self.namespace_filter}")

        except Exception as e:
            logging.error(f"Error updating namespace dropdown: {e}")
            # FIXED: Ensure signal is reconnected and dropdown enabled even on error
            try:
                if self.namespace_combo:
                    self.namespace_combo.currentTextChanged.connect(
                        self._on_namespace_changed)
                    self.namespace_combo.setEnabled(True)
            except BaseException:
                pass
            # Set a default filter to prevent issues
            self.namespace_filter = "All Namespaces"

    def refresh_namespaces(self):

        self._namespaces_loaded = False  # Reset the flag
        self._load_namespaces_async()

    def _on_namespace_changed(self, namespace):

        if namespace == "Loading namespaces...":
            return  # Ignore the loading placeholder

        old_namespace = getattr(self, 'namespace_filter', 'default')

        # FIXED: Only proceed if namespace actually changed
        if old_namespace == namespace:
            logging.debug(
                f"Namespace unchanged ({namespace}), skipping reload")
            return

        logging.info(
            f"Namespace changed from '{old_namespace}' to '{namespace}'")

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

            logging.debug(
                f"Loaded batch: {batch_size} items. Total loaded: {self._loaded_item_count}/{self._total_item_count}")

        except Exception as e:
            logging.error(f"Error loading more data batch: {e}")

    def _handle_scroll(self, value):

        # Use debounced updater for scroll
        self._debounced_updater.schedule_update(
            'scroll_' + self.__class__.__name__,
            self._handle_scroll_debounced,
            delay_ms=SCROLL_DEBOUNCE_MS
        )

    def _handle_scroll_debounced(self):

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

        if self.is_loading_more or self.all_data_loaded or not self.current_continue_token:
            return

        self.is_loading_more = True
        self._start_loading_thread(continue_token=self.current_continue_token)

    def _start_loading_thread(self, continue_token=None):

        # Cancel any existing loading
        if hasattr(self, 'loading_thread') and self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.cancel()
            self.loading_thread.wait(1000)

        # Get the unified resource loader
        unified_loader = get_unified_resource_loader()

        # Connect signals if not already connected
        if not hasattr(self, '_signals_connected'):
            unified_loader.loading_completed.connect(
                self._on_unified_resources_loaded)
            unified_loader.loading_error.connect(
                self._on_unified_loading_error)
            self._signals_connected = True

        # Start loading with optimized configuration
        # Handle "All Namespaces" efficiently by using None (which triggers optimized multi - namespace loading)
        namespace = None if self.namespace_filter == "All Namespaces" else self.namespace_filter
        self._current_operation_id = unified_loader.load_resources_async(
            resource_type=self.resource_type,
            namespace=namespace
        )

        logging.debug(
            f"Started unified loading for {self.resource_type} (operation: {self._current_operation_id})")

    def _on_unified_resources_loaded(self, resource_type: str, result: LoadResult):

        try:
            # Only process if this matches our resource type
            if resource_type != self.resource_type:
                return

            if not result.success:
                self._on_unified_loading_error(
                    resource_type, result.error_message or "Unknown error")
                return

            # Process the optimized result format
            resources = result.items or []

            # Check if we have a large dataset
            self._total_item_count = len(resources)
            self._large_dataset_mode = self._total_item_count > LARGE_DATASET_THRESHOLD

            if self._large_dataset_mode:
                logging.info(
                    f"Large dataset detected: {self._total_item_count} items. Activating optimizations.")
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
            logging.info(
                f"Loaded {self._loaded_item_count}/{self._total_item_count} {resource_type} in {result.load_time_ms:.1f}ms")

        except Exception as e:
            logging.error(f"Error processing unified resources: {e}")
            self._on_unified_loading_error(resource_type, str(e))

    def _on_unified_loading_error(self, resource_type: str, error_message: str):

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

        logging.error(f"Error loading {self.resource_type}: {error}")
        self.is_loading_initial = False
        self.is_loading_more = False

        error_message = f"Failed to load {self.resource_type}: {str(error)}"
        self._show_error_message(error_message)

    def _display_resources(self, resources):

        if not resources:
            self._show_empty_message()
            return

        self._table_stack.setCurrentWidget(self.table)

        # Clear previous selections when displaying new data
        self.selected_items.clear()

        # Log performance info for large datasets
        if len(resources) > 100:
            logging.info(
                f"Displaying {len(resources)} resources (large dataset optimization active)")

        # Optimized rendering for all datasets
        self._render_resources_batch(resources)

    def _render_resources_batch(self, resources, append=False):

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
            # Limit initial render to 200 items
            for i in range(0, min(200, len(resources)), batch_size):
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

        # Re - enable sorting after all rows are added
        self.table.setSortingEnabled(True)

    def _populate_resource_row(self, row, resource):

        from PyQt6.QtWidgets import QTableWidgetItem

        # Default implementation for common fields - can be overridden by subclasses
        # Create checkbox for the first column
        checkbox_container = self._create_checkbox_container(
            row, resource.get("name", "Unknown"))
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

        count = len(self.resources)
        self.items_count.setText(f"{count} items")

    def _show_empty_message(self):

        # Keep table headers visible - don't clear the table completely
        if self.table:
            self.table.setRowCount(0)  # Just clear rows, keep headers
            self.table.show()  # Ensure table is visible

        # Clear and setup the message container
        self._clear_message_container()

        # Check if we're in search mode to show appropriate message
        is_searching = getattr(self, '_is_searching', False)
        current_search_query = getattr(self, '_current_search_query', None)
        search_bar_text = self.search_bar.text().strip() if hasattr(self,
                                                                    'search_bar') else ""

        # Use either the stored search query or current search bar text
        active_search_query = current_search_query or search_bar_text

        if is_searching and active_search_query:
            # Show search - specific empty message
            empty_title = QLabel(
                f"No results found for '{active_search_query}'")
            empty_subtitle = QLabel(
                "Try a different search term or clear the search to see all resources")
        else:
            # Show general empty message
            empty_title = QLabel("No resources found")
            empty_subtitle = QLabel(
                "Connect to a cluster or check your filters")

        # Apply styling to both title and subtitle
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setStyleSheet(self.style_manager.get_empty_title_style())

        empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_subtitle.setStyleSheet(self.style_manager.get_empty_subtitle_style())

        # Add widgets to message container
        self._message_widget_container.layout().addWidget(empty_title)
        self._message_widget_container.layout().addWidget(empty_subtitle)

        # Show the message overlay but keep table visible in background
        self._table_stack.setCurrentWidget(self.table)

        # Switch to message container view
        self._table_stack.setCurrentWidget(self._message_widget_container)

    def _show_error_message(self, message):

        self._clear_message_container()

        error_label = QLabel(f"Error: {message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet(self.style_manager.get_error_label_style())
        error_label.setWordWrap(True)

        self._message_widget_container.layout().addWidget(error_label)
        self._table_stack.setCurrentWidget(self._message_widget_container)

    def _clear_message_container(self):

        layout = self._message_widget_container.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def force_load_data(self):

        # Show loading indicator
        self.show_loading_indicator("Refreshing data...")

        self._clear_resources()  # Use new method to clear resources properly
        self.current_continue_token = None
        self.all_data_loaded = False
        self.is_loading_initial = True
        self._start_loading_thread()

    def _clear_resources(self):

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
                logging.debug(
                    f"Reset namespace loading flag for {self.__class__.__name__}")

            # Clear namespace dropdown to prevent showing stale namespaces
            if hasattr(self, 'namespace_combo') and self.namespace_combo:
                self.namespace_combo.blockSignals(True)
                self.namespace_combo.clear()
                self.namespace_combo.addItem("Loading namespaces...")
                self.namespace_combo.setEnabled(False)
                self.namespace_combo.blockSignals(False)
                # Reset to default namespace, not "All Namespaces"
                self.namespace_filter = "default"
                logging.debug(
                    f"Cleared namespace dropdown for {self.__class__.__name__}")

            # Clear selected items
            self.selected_items.clear()

            # Update UI
            self._update_items_count()

            # Trigger namespace reload for visible pages (fixes stuck "Loading namespaces..." issue)
            if self.isVisible() and hasattr(self, 'namespace_combo') and self.namespace_combo:
                QTimer.singleShot(100, self._load_namespaces_async)
                logging.debug(
                    f"Triggered namespace reload for visible page {self.__class__.__name__}")

            logging.info(
                f"Cleared {self.__class__.__name__} for cluster change")

        except Exception as e:
            logging.error(
                f"Error clearing {self.__class__.__name__} for cluster change: {e}")

    def load_data(self):

        if not self.resources or self.reload_on_show:
            # Show loading indicator for initial load
            if not self.resources:  # Only show for truly initial loads
                self.show_loading_indicator("Loading data...")
            self.force_load_data()

    def _handle_select_all(self, state):

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
                resource_key = (resource["name"], resource_namespace) if resource_namespace else (
                    resource["name"], "")
                self.selected_items.add(resource_key)

        logging.debug(
            f"Select all: {state == Qt.CheckState.Checked.value}, Selected items: {len(self.selected_items)}")

    def _validate_resource_name(self, resource_name):

        if not resource_name or not isinstance(resource_name, str):
            return False

        # Skip validation for cluster - scoped resources that don't have namespaces
        cluster_scoped_resources = {
            'nodes', 'clusterroles', 'clusterrolebindings',
            'storageclasses', 'customresourcedefinitions',
            'ingressclasses', 'persistentvolumes',
            'validatingwebhookconfigurations', 'mutatingwebhookconfigurations',
            'priorityclasses', 'runtimeclasses'
        }

        if hasattr(self, 'resource_type') and self.resource_type in cluster_scoped_resources:
            return True  # Allow all names for cluster - scoped resources

        # For namespaced resources, check for common pod naming patterns that shouldn't appear in other resource types
        if hasattr(self, 'resource_type') and self.resource_type != 'pods':
            # Check for ReplicaSet hash patterns (pod names like "deployment - abc123 - xyz789")
            import re
            # Pattern for pod names generated by ReplicaSets / Deployments
            pod_pattern = r'^.+-[a-f0-9]{8,10}-[a-z0-9]{5}$'
            if re.match(pod_pattern, resource_name):
                logging.warning(
                    f"Resource name '{resource_name}' appears to be a pod name but resource type is '{self.resource_type}'")
                return False

        return True

    def delete_selected_resources(self):
        self.deletion_manager.delete_selected_resources(list(self.selected_items))

    def _delete_selected_resources_no_confirm(self):
        # The manager handles either with or without confirm. delegating.
        self.deletion_manager.delete_selected_resources(list(self.selected_items))

    def on_batch_delete_completed(self, success_list, error_list, progress_dialog):
        self.deletion_manager.on_batch_delete_completed(success_list, error_list, progress_dialog)

    def delete_resource(self, resource_name, resource_namespace):
        self.deletion_manager.delete_resource_single(resource_name, resource_namespace)

    def on_delete_completed(self, success, message, resource_name, resource_namespace):
        self.deletion_manager.on_delete_completed(success, message, resource_name, resource_namespace)

    def cleanup_timers_and_threads(self):
        if hasattr(self, 'deletion_manager'):
            self.deletion_manager.cleanup()

        self._shutting_down = True

        if hasattr(self, '_debounced_updater'):
            self._debounced_updater.cancel_update(
                'search_' + self.__class__.__name__)
            self._debounced_updater.cancel_update(
                'scroll_' + self.__class__.__name__)

        # Stop threads
        for thread in [self.loading_thread, self.delete_thread, self.batch_delete_thread]:
            if thread and thread.isRunning():
                if hasattr(thread, 'cancel'):
                    thread.cancel()
                thread.wait(1000)

    def clear_table(self):

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

            logging.debug(
                "Table UI cleared successfully - resources data preserved")

        except Exception as e:
            logging.error(f"Error clearing table: {e}")

    def _create_table(self, headers, sortable_columns=None):

        from PyQt6.QtWidgets import QTableWidget, QAbstractItemView, QHeaderView
        from Base_Components.base_components import CustomHeader
        from UI.Styles import AppStyles

        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        # Use custom header for selective header - based sorting
        custom_header = CustomHeader(
            Qt.Orientation.Horizontal, sortable_columns, table)
        table.setHorizontalHeader(custom_header)
        table.setSortingEnabled(True)

        # Apply enhanced styling with platform overrides
        table.setStyleSheet(BaseTablePageStyles.get_table_style())
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Configure appearance with explicit settings
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)

        # Force consistent selection behavior
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)

        # Configure resizable columns
        self._configure_table_resizing(table, headers)

        # Connect cell click signal
        table.cellClicked.connect(self.handle_row_click)

        return table

    def _configure_table_resizing(self, table, headers):

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
                header.setSectionResizeMode(
                    i, QHeaderView.ResizeMode.Interactive)

        # Set the second - to - last column to stretch if we have enough columns
        if len(headers) > 2:
            stretch_col = len(headers) - 2
            header.setSectionResizeMode(
                stretch_col, QHeaderView.ResizeMode.Stretch)

    def _create_select_all_checkbox(self):

        from PyQt6.QtWidgets import QCheckBox

        select_all_checkbox = QCheckBox()
        # Use theme - aware checkbox styling (BaseTablePageStyles already imported at line 27)
        select_all_checkbox.setStyleSheet(
            BaseTablePageStyles.get_checkbox_style())
        select_all_checkbox.stateChanged.connect(self._on_select_all_changed)
        return select_all_checkbox

    def _add_select_all_to_header(self):

        if not self.table or not self.select_all_checkbox:
            return

        # Set the header label to empty for column 0
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem(""))

        # Position the checkbox over the header
        def position_checkbox():

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

                position_checkbox()

        QTimer.singleShot(100, safe_position)
        self.table.horizontalHeader().sectionResized.connect(
            lambda: QTimer.singleShot(10, safe_position))

    def _on_select_all_changed(self, state):

        self._handle_select_all(state)

    def handle_row_click(self, row, column):

        # This is a placeholder - implement based on your row click logic
        pass

    def update_table_row(self, row, resource):

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

                for col in stretch_columns:
                    header.setSectionResizeMode(
                        col, QHeaderView.ResizeMode.Stretch)
            else:
                # No stretch columns, make the last column stretch
                if visible_columns:
                    last_col = visible_columns[-1]
                    header.setSectionResizeMode(
                        last_col, QHeaderView.ResizeMode.Stretch)

        except Exception as e:
            logging.debug(f"Error in _ensure_full_width_utilization: {e}")

    def _handle_edit_resource(self, resource_name, resource_namespace, resource):

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
                resource_type_singular = singularize_resource_type(self.resource_type)
                # Show the detail page first
                cluster_view.detail_manager.show_detail(
                    resource_type_singular, resource_name, resource_namespace)

                # After showing detail page, trigger edit mode
                # We need to wait a bit for the detail page to load completely
                QTimer.singleShot(
                    500, lambda: self._trigger_edit_mode(cluster_view))

                logging.info(
                    f"Opening {self.resource_type}/{resource_name} in edit mode")
            else:
                # Fallback: show error if detail manager not found
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "Edit Resource",
                    f"Cannot edit {self.resource_type}/{resource_name}: Detail panel not available"
                )
                logging.warning(
                    f"Detail manager not found for editing {resource_name}")

        except Exception as e:
            logging.error(f"Failed to open {resource_name} for editing: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Error",
                f"Failed to open {resource_name} for editing: {str(e)}"
            )

    def _trigger_edit_mode(self, cluster_view):

        try:
            if hasattr(cluster_view, 'detail_manager') and cluster_view.detail_manager._detail_page:
                detail_page = cluster_view.detail_manager._detail_page

                # Find the YAML section and trigger edit mode
                if hasattr(detail_page, 'yaml_section'):
                    yaml_section = detail_page.yaml_section
                    if hasattr(yaml_section, 'toggle_yaml_edit_mode') and yaml_section.yaml_editor.isReadOnly():
                        yaml_section.toggle_yaml_edit_mode()
                        logging.info(
                            "Successfully activated edit mode in YAML section")
                    else:
                        logging.warning(
                            "YAML section is not in read - only mode or toggle method not found")
                else:
                    logging.warning("YAML section not found in detail page")
            else:
                logging.warning(
                    "Detail page not found or not properly initialized")
        except Exception as e:
            logging.error(f"Error triggering edit mode: {e}")

    def _create_action_button(self, row, resource_name=None, resource_namespace=None):

        from PyQt6.QtWidgets import QToolButton, QMenu
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize
        from functools import partial

        button = QToolButton()

        # Use pre - loaded theme - aware icon from parent class (BaseTablePage)
        try:
            if hasattr(self, 'action_button_icon'):
                button.setIcon(self.action_button_icon)
                button.setIconSize(QSize(16, 16))
        except Exception as e:
            logging.warning(f"Error setting action button icon: {e}")

        # Remove text and change to icon - only style
        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        button.setFixedWidth(30)
        try:
            from UI.Styles import AppStyles
            button.setStyleSheet(AppStyles.HOME_ACTION_BUTTON_STYLE +
                                 """
                QToolButton::menu-indicator { image: none; width: 0px; }
                """
                                 )
        except (ImportError, AttributeError) as e:
            logging.debug(f"Could not load AppStyles for button: {e}")
            # Use theme-aware fallback styling
            button.setStyleSheet(BaseResourcePageStyles.get_action_button_fallback_style())

        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create menu
        menu = QMenu(button)
        try:
            menu.setStyleSheet(BaseTablePageStyles.get_menu_style())
        except (ImportError, AttributeError) as e:
            logging.debug(f"Could not load BaseTablePageStyles for menu: {e}")
            # Use theme-aware fallback styling
            menu.setStyleSheet(BaseResourcePageStyles.get_menu_fallback_style())

        # Connect signals to change row appearance when menu opens / closes
        try:
            menu.aboutToShow.connect(lambda: self._on_menu_show(row))
            menu.aboutToHide.connect(
                lambda: self._highlight_active_row(row, False))
        except Exception as e:
            logging.warning(f"Error connecting menu signals: {e}")

        # Define actions based on resource type - matching old pattern
        actions = []

        # Resource - specific actions based on resource type
        if hasattr(self, 'resource_type') and self.resource_type == "pods":
            actions.extend([
                {"text": "View Logs", "icon": "Icons / logs.png", "dangerous": False},
                {"text": "SSH", "icon": "Icons / terminal.png", "dangerous": False}
            ])
            # Check if pod has ports for port forwarding
            if row < len(self.resources) and self.resources:
                pod_resource = self.resources[row]
                if self._has_pod_ports(pod_resource):
                    actions.append(
                        {"text": "Port Forward", "icon": "Icons / network.png", "dangerous": False})
        elif hasattr(self, 'resource_type') and self.resource_type == "services":
            # Check if service has ports for port forwarding
            if row < len(self.resources) and self.resources:
                service_resource = self.resources[row]
                if self._has_service_ports(service_resource):
                    actions.append(
                        {"text": "Port Forward", "icon": "Icons / network.png", "dangerous": False})
        elif hasattr(self, 'resource_type') and self.resource_type == "nodes":
            # Node - specific actions
            actions.append(
                {"text": "View Metrics", "icon": "Icons / chart.png", "dangerous": False})

        # Standard actions for all resources
        actions.extend([
            {"text": "Edit", "icon": "Icons / edit.png", "dangerous": False},
            {"text": "Delete", "icon": "Icons / delete.png", "dangerous": True}
        ])

        # Add actions to menu with OLD WORKING PATTERN - only pass row index
        for action_info in actions:
            try:
                action = menu.addAction(action_info["text"])
                if "icon" in action_info:
                    try:
                        action.setIcon(
                            QIcon(resource_path(action_info["icon"])))
                    except (OSError, FileNotFoundError) as e:
                        logging.debug(
                            f"Icon loading failed for {action_info['icon']}: {e}")
                    except Exception as e:
                        logging.error(
                            f"Unexpected error loading icon {action_info['icon']}: {e}")
                if action_info.get("dangerous", False):
                    action.setProperty("dangerous", True)

                # OLD WORKING PATTERN: Only pass action and row - no resource data storage
                action.triggered.connect(
                    partial(self._handle_action, action_info["text"], row)
                )
                logging.debug(
                    f"Action button: Connected '{action_info['text']}' for row {row}")
            except Exception as e:
                logging.error(
                    f"Error adding action {action_info['text']}: {e}")

        button.setMenu(menu)
        return button

    def _has_service_ports(self, service_resource):

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
            logging.error(
                f"Unexpected error checking port forward availability: {e}")
            return False

    def _has_pod_ports(self, pod_resource):

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
            logging.debug(
                f"Could not check pod port forward availability: {e}")
            return False
        except Exception as e:
            logging.error(
                f"Unexpected error checking pod port forward availability: {e}")
            return False

    def _create_action_container(self, row, action_button):

        container = QWidget()
        try:
            from UI.Styles import AppStyles
            container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        except (ImportError, AttributeError) as e:
            logging.debug(f"Could not load ACTION_CONTAINER_STYLE: {e}")
            # Use theme-aware fallback styling
            container.setStyleSheet(BaseResourcePageStyles.get_action_container_fallback_style())
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(action_button)
        return container

    def _on_menu_show(self, row):

        logging.info(f"Action button menu opening for row {row}")
        self._highlight_active_row(row, True)

    def _highlight_active_row(self, row, highlight):
        """Highlight row when action menu is open using theme-aware colors"""
        try:
            if hasattr(self, 'table') and self.table and row < self.table.rowCount():
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        if highlight:
                            item.setBackground(QColor(BaseResourcePageStyles.get_hover_bg_color()))
                        else:
                            item.setBackground(QColor(BaseResourcePageStyles.get_transparent_color()))
        except Exception as e:
            logging.debug(f"Error highlighting row {row}: {e}")

    # Removed old _handle_action_with_resource method - replaced with OLD WORKING PATTERN

    def _handle_action(self, action, row):

        logging.info(
            f"BaseResourcePage: Action '{action}' clicked on row {row}")

        # Add debugging for resources array
        logging.info(
            f"BaseResourcePage: Resources array length: {len(self.resources) if hasattr(self, 'resources') else 'No resources attribute'}")

        # FALLBACK: If resources array is empty but table has rows, read from table
        # This handles the case where theme changes or other events temporarily clear resources
        # while table rows still exist
        if not hasattr(self, 'resources') or not self.resources or row >= len(self.resources):
            if hasattr(self, 'table') and self.table and row < self.table.rowCount():
                logging.info(
                    f"BaseResourcePage: Resources empty, reading data from table row {row}")
                # Extract resource name from table (typically column 1)
                resource_name = ""
                resource_namespace = ""

                if self.table.item(row, 1):  # Name column
                    resource_name = self.table.item(row, 1).text()

                # Try to get namespace from table if it exists (varies by resource type)
                # Find the namespace column by checking column headers for "namespace" match
                for col in range(2, self.table.columnCount()):
                    header_item = self.table.horizontalHeaderItem(col)
                    if header_item:
                        header_text = header_item.text().lower().strip()
                        # Check for namespace column (case - insensitive match for "namespace" or variants)
                        if "namespace" in header_text:
                            cell_item = self.table.item(row, col)
                            if cell_item and cell_item.text():
                                resource_namespace = cell_item.text()
                                break

                # Fall back to namespace_filter if not found in table
                if not resource_namespace and self.namespace_filter:
                    resource_namespace = self.namespace_filter

                # Create minimal resource dict from table data
                resource = {
                    "name": resource_name,
                    "namespace": resource_namespace
                }
            else:
                logging.warning(
                    f"BaseResourcePage: No resources available for action '{action}' on row {row}")
                return
        else:
            # Normal path: use resources array
            resource = self.resources[row]
            resource_name = resource.get("name", "")
            resource_namespace = resource.get("namespace", "")

        logging.info(f"BaseResourcePage: Processing action '{action}' for {resource_name}" + (
            f" in {resource_namespace}" if resource_namespace else ""))

        # Handle actions with fresh resource data - matching old working pattern
        if action == "View Logs":
            if hasattr(self, 'resource_type') and self.resource_type == "pods":
                self._handle_view_logs(
                    resource_name, resource_namespace, resource)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Logs Error", "Logs are only available for pod resources.")
        elif action == "SSH":
            if hasattr(self, 'resource_type') and self.resource_type == "pods":
                self._handle_ssh_into_pod(
                    resource_name, resource_namespace, resource)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "SSH Error",
                                    "SSH is only available for pod resources.")
        elif action == "Port Forward":
            if hasattr(self, 'resource_type') and self.resource_type in ["pods", "services"]:
                self._handle_port_forward(
                    resource_name, resource_namespace, resource)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Port Forward Error", "Port forwarding is only available for pods and services.")
        elif action == "Edit":
            try:
                logging.info(f"Starting edit for resource: {resource_name}")
                self._handle_edit_resource(
                    resource_name, resource_namespace, resource)
            except Exception as e:
                logging.error(f"Error in edit action: {e}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self, "Error", f"Failed to edit {resource_name}: {str(e)}")
        elif action == "Delete":
            try:
                logging.info(f"Starting delete for resource: {resource_name}")
                self.delete_resource(resource_name, resource_namespace)
            except Exception as e:
                logging.error(f"Error in delete action: {e}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self, "Error", f"Failed to delete {resource_name}: {str(e)}")
        elif action == "View Metrics":
            # Handle node - specific View Metrics action
            if hasattr(self, 'select_node_for_graphs'):
                self.select_node_for_graphs(row)
            else:
                logging.warning(
                    f"View Metrics action not supported for resource type: {self.resource_type}")
        else:
            logging.warning(f"BaseResourcePage: Unknown action: {action}")

    def _handle_port_forward(self, resource_name, namespace, resource):

        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Port Forward", f"Port forwarding for {resource_name} - functionality implemented by specific pages")
        logging.info(
            f"Port forward requested for {resource_name} - using placeholder implementation")

    def _handle_view_logs(self, pod_name, namespace, resource):

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
                cluster_view.terminal_panel.create_enhanced_logs_tab(
                    pod_name, namespace)

                # Show the terminal panel if it's hidden
                if not cluster_view.terminal_panel.is_visible:
                    if hasattr(cluster_view, 'toggle_terminal'):
                        cluster_view.toggle_terminal()
                    elif hasattr(cluster_view.terminal_panel, 'show_terminal'):
                        cluster_view.terminal_panel.show_terminal()

                logging.info(
                    f"Created logs tab for pod: {pod_name} in namespace: {namespace}")
            else:
                # Fallback: show error if terminal panel not found
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "Logs",
                    f"Opening logs for pod: {pod_name} in namespace: {namespace}\n\n"
                    f"Terminal panel will show logs. Use kubectl logs {pod_name} -n {namespace} if needed."
                )
                logging.warning(
                    "Terminal panel not found for logs tab creation")

        except Exception as e:
            logging.error(f"Failed to create logs tab for pod {pod_name}: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Error",
                f"Failed to open logs for pod {pod_name}: {str(e)}"
            )

    def _handle_ssh_into_pod(self, pod_name, namespace, resource):

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

                logging.info(
                    f"Created SSH tab for pod: {pod_name} in namespace: {namespace}")
            else:
                # Fallback: show error if terminal panel not found
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "SSH",
                    f"Opening SSH for pod: {pod_name} in namespace: {namespace}\n\n"
                    f"Terminal panel will show SSH session. Use kubectl exec -it {pod_name} -n {namespace} -- /bin/bash if needed."
                )
                logging.warning(
                    "Terminal panel not found for SSH tab creation")

        except Exception as e:
            logging.error(f"Failed to create SSH tab for pod {pod_name}: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Error",
                f"Failed to open SSH for pod {pod_name}: {str(e)}"
            )

    def _create_checkbox_container(self, row, resource_name):

        from PyQt6.QtWidgets import QCheckBox, QWidget, QHBoxLayout

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        checkbox = QCheckBox()
        checkbox.setProperty("row", row)
        checkbox.setProperty("resource_name", resource_name)
        checkbox.stateChanged.connect(self._on_row_checkbox_changed)

        # Apply theme - aware checkbox styling
        checkbox.setStyleSheet(BaseTablePageStyles.get_checkbox_style())

        layout.addWidget(checkbox)
        return container

    def _on_row_checkbox_changed(self, state):

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
                # Handle both namespaced and cluster - scoped resources
                resource_namespace = resource.get("namespace", "")
                resource_key = (resource["name"], resource_namespace) if resource_namespace else (
                    resource["name"], "")

                if state == Qt.CheckState.Checked.value:
                    self.selected_items.add(resource_key)
                    logging.debug(f"Selected resource: {resource_key}")
                else:
                    self.selected_items.discard(resource_key)
                    logging.debug(f"Deselected resource: {resource_key}")

                # Update select - all checkbox state
                self._update_select_all_state()
            else:
                logging.warning(
                    f"Resource not found for checkbox: {resource_name}")

        except Exception as e:
            logging.error(f"Error handling checkbox change: {e}")

    def _update_select_all_state(self):

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
            logging.debug(f"Error updating select - all state: {e}")

    def __del__(self):

        try:
            if hasattr(self, '_shutting_down') and not self._shutting_down:
                logging.debug(
                    "BaseResourcePage destructor called, performing cleanup")
                self.cleanup_timers_and_threads()
                # Cache cleanup is handled automatically by bounded cache system
                # No manual cache cleanup needed
        except Exception as e:
            logging.error(f"Error in BaseResourcePage destructor: {e}")

    def _on_theme_changed(self, theme_name):
        """Refresh resource page specific styles when theme changes"""
        # Call parent's theme change handler first
        super()._on_theme_changed(theme_name)

        # Get current theme for color updates
        theme = get_theme_manager().get_current_theme()

        # Refresh resource-specific widgets
        # Note: Most widgets (table, checkboxes, action buttons) are already handled by BaseTablePage

        # Update title label with theme-aware color
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.setStyleSheet(
                f"font-size: 20px; font-weight: bold; color: {theme.colors.TEXT_LIGHT};"
            )

        # Update count label with theme-aware color
        if hasattr(self, 'items_count') and self.items_count:
            self.items_count.setStyleSheet(
                f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px; margin-left: 8px;"
            )

        # Refresh search label if it exists
        if hasattr(self, 'search_label') and self.search_label:
            self.search_label.setStyleSheet(
                BaseResourcePageStyles.get_search_label_style())

        # Refresh search bar if it exists
        if hasattr(self, 'search_bar') and self.search_bar:
            self.search_bar.setStyleSheet(
                BaseResourcePageStyles.get_search_input_style())

        # Refresh namespace combo if it exists
        if hasattr(self, 'namespace_combo') and self.namespace_combo:
            self.namespace_combo.setStyleSheet(BaseResourcePageStyles.get_namespace_combo_style())

        # Refresh delete button if it exists
        if hasattr(self, '_delete_btn') and self._delete_btn:
            self._delete_btn.setStyleSheet(BaseResourcePageStyles.get_delete_button_style())

        # Refresh refresh button if it exists
        if hasattr(self, 'refresh_btn') and self.refresh_btn:
            self.refresh_btn.setStyleSheet(BaseResourcePageStyles.get_refresh_button_style())

        # Note: Search/namespace labels and empty state widgets are recreated when shown,
        # so they will automatically use the current theme
        logging.debug(f"BaseResourcePage: Theme refresh complete for {theme_name}")

        # Refresh namespace label if it exists
        if hasattr(self, 'namespace_label') and self.namespace_label:
            self.namespace_label.setStyleSheet(
                BaseResourcePageStyles.get_namespace_label_style())

        # Refresh namespace combo if it exists
        if hasattr(self, 'namespace_combo') and self.namespace_combo:
            self.namespace_combo.setStyleSheet(
                BaseResourcePageStyles.get_namespace_combo_style())

        # Refresh delete button if it exists
        if hasattr(self, '_delete_btn') and self._delete_btn:
            self._delete_btn.setStyleSheet(
                BaseResourcePageStyles.get_delete_button_style())

        logging.debug(
            f"BaseResourcePage: Theme refresh complete for {theme_name}")

    def cleanup(self):

        try:
            self._shutting_down = True

            # Stop all timers
            if hasattr(self, '_debounced_updater'):
                self._debounced_updater.cancel_update(
                    'search_' + self.__class__.__name__)
                self._debounced_updater.cancel_update(
                    'scroll_' + self.__class__.__name__)
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
            logging.error(f"Error in cleanup: {e}")

# Factory function for creating resource pages


def create_base_resource_page(resource_type, title, headers, parent=None):

    page = BaseResourcePage(parent)
    page.resource_type = resource_type
    page.setup_ui(title, headers)
    return page

# Export all classes for backward compatibility
__all__ = [
    'ResourceDeleterThread',
    'BatchResourceDeleterThread',
    'VirtualScrollTable',
    'BaseResourcePage',
    'create_base_resource_page',
    'BATCH_SIZE',
    'SCROLL_DEBOUNCE_MS',
    'SEARCH_DEBOUNCE_MS'
]
