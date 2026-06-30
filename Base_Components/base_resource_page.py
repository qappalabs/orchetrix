"""
Base Resource Page - Main base class for Kubernetes resource pages

Consolidated from multiple duplicate implementations for better maintainability
"""

import gc
import logging
import re
import threading
import time
from functools import partial
from typing import List, Dict
from Utils.qt_utils import is_valid

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QTableWidgetItem,
    QAbstractItemView,
    QStackedWidget,
    QHeaderView,
    QCheckBox,
    QMessageBox,
    QToolButton,
    QMenu,
    QTableWidget,
    QFrame,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject, QEvent

from Base_Components.base_components import BaseTablePage, CustomHeader
from .resource_deleters import ResourceDeleterThread, BatchResourceDeleterThread
from .virtual_scroll_table import VirtualScrollTable, HighPerformanceDelegate
from .resource_page_style_manager import ResourcePageStyleManager
from .resource_deletion_manager import ResourceDeletionManager
from .resource_search_handler import ResourceSearchHandler

from UI.Icons import resource_path
from UI.ThemeManager import get_theme_manager
from UI.Styles import AppStyles
from UI.LoadingSpinner import create_loading_overlay

import Styles.BaseTablePageStyles as BaseTablePageStyles
import Styles.BaseResourcePageStyles as BaseResourcePageStyles

from Utils.unified_resource_loader import get_unified_resource_loader, LoadResult
from Utils.error_handler import get_error_handler
from Utils.kubernetes_client import get_kubernetes_client
from Utils.debounced_updater import get_debounced_updater
from Utils.resource_utils import singularize_resource_type

from log_handler import class_logger
from Base_Components.table_diff_engine import RowCache, compute_diff

# Constants for performance tuning - optimized for large datasets
BATCH_SIZE = 100  # Increased batch size for better large data performance

SCROLL_DEBOUNCE_MS = 150  # Optimized debounce for large data stability

SEARCH_DEBOUNCE_MS = 500  # Longer debounce for large dataset search performance

MAX_ITEMS_IN_MEMORY = 2000  # Increased memory limit for large datasets

# Lower threshold to activate optimizations earlier
LARGE_DATASET_THRESHOLD = 200


@class_logger(
    log_level=logging.INFO,
    exclude_methods=[
        "__init__",
        "clear_table",
        "update_table_row",
        "load_more_complete",
        "all_items_loaded_signal",
        "force_load_data",
    ],
)
class BaseResourcePage(BaseTablePage):
    # Signals for resource loading
    all_items_loaded_signal = pyqtSignal()
    load_more_complete = pyqtSignal()

    # Subclasses with synthetic resource_type values (e.g. "helmreleases",
    # "portforwarding") or no real K8s API resource should set this to False.
    # When False, the inherited search bar will not call the unified loader;
    # if the subclass also defines local_search(query), the bar routes there
    # instead, otherwise it is hidden.
    uses_unified_search = True

    # If True, the diff-based in-place watch update is bypassed.
    # Useful for high-velocity resource logs/events that thrash the cache.
    REQUIRES_FULL_RESET = False

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
        # Performance optimizations for large datasets
        self.is_loading_initial = False
        self.is_loading_more = False
        self.all_data_loaded = False
        self.current_continue_token = None
        self.items_per_page = 200  # Increased for better large data performance
        self.selected_items = set()
        self.reload_on_show = True
        self._large_dataset_mode = False
        self._total_item_count = 0
        self._loaded_item_count = 0
        self._last_load_time = 0  # Track last load time
        self.is_showing_skeleton = False  # Add skeleton loading state
        self._is_searching = False  # Add search state tracking
        self._current_search_query = None  # Add current search query tracking
        # Cache system removed
        self._shutting_down = False
        # ── Diff-engine row cache ─────────────────────────────────────
        # UID-keyed cache of projected row data.  Rebuilt on full loads;
        # diffed on watch-driven updates to emit surgical table mutations.
        self._row_cache = RowCache()
        # Thread safety
        self._data_lock = threading.RLock()  # Allow recursive locking
        self._loading_lock = threading.Lock()
        self._remaining_resources = []  # Store remaining resources for lazy loading
        # Debouncing timers
        # Use unified debounced updater instead of individual timers
        self._debounced_updater = get_debounced_updater()
        self.kube_client = get_kubernetes_client()
        # Phase 4: subscribe the namespace dropdown to live ADDED/DELETED
        # signals so namespaces created or deleted out-of-band (kubectl,
        # CI/CD, controllers) flow into every page without an app restart.
        # The initial bulk load via _namespaces_loaded gate stays in place
        # for cheap cross-page navigation — these signals just keep it
        # in sync afterward.
        self._connect_namespace_lifecycle_signals()
        self._message_widget_container = None
        self._table_stack = None
        # Loading spinner overlay
        self._loading_overlay = None
        self._is_showing_loading = False
        self._spinner_type = "circular"  # Default spinner type, can be overridden
        # Track if data has been loaded at least once
        self._initial_load_done = False
        # Generation counter for stale-signal rejection.  Incremented on every
        # context change (namespace switch, cluster switch).  Watch emissions
        # carry the generation they were started under; the receiver slot
        # discards any payload whose generation doesn't match the current one.
        self._watch_generation = 0
        # True while this page currently holds a reference-counted subscription
        # to its watch stream.  _start_resource_watch is reached more than once
        # per visit (showEvent + the cluster-change restart timer + the
        # namespace-change restart), so this guard ensures exactly one
        # start_watch/stop_watch pair per visit — otherwise the loader's
        # refcount corrupts and the page generation races ahead of the watch's,
        # silently discarding every live update.
        self._holds_watch_ref = False
        # Helper Managers
        self.style_manager = ResourcePageStyleManager
        self.deletion_manager = ResourceDeletionManager(self)
        self.search_handler = ResourceSearchHandler(self)

    def showEvent(self, event):
        """Override showEvent to automatically load data when page becomes visible"""
        super().showEvent(event)
        self._was_hidden = False
        # Phase 5: synchronously validate namespace_filter against the live
        # cluster BEFORE starting the watch.  Without this, pages that were
        # hidden when a namespace was deleted out-of-band would retain
        # their stale filter, fire a watch into a dead namespace, and burn
        # cycles in the loader's exponential-backoff loop until the user
        # manually switched.  Cheap O(1) set check against the daemon's
        # authoritative cache.
        self._validate_namespace_filter_against_cluster()
        # Start (or re-use) the watch stream for this resource type.
        # If a watch is already running and has cached data, _start_resource_watch
        # will render from cache immediately — no API call needed.
        self._start_resource_watch()
        # Load immediately for better performance
        self._handle_normal_show_event()

    def hideEvent(self, event):
        """Stop the watch when the page is hidden to free resources."""
        super().hideEvent(event)
        self._was_hidden = True
        # Stop the watch — daemon threads, HTTP connections, and cache dicts
        # accumulate for every page the user has ever visited otherwise.
        # SWR (_get_stale_cached_items) provides instant render on return,
        # so the user sees cached data immediately while the new LIST completes.
        self._stop_resource_watch()

    def _handle_normal_show_event(self):
        # Load namespaces dynamically - check if they need refreshing after cluster change
        if not hasattr(self, "_namespaces_loaded") or not self._namespaces_loaded:
            self._namespaces_loaded = True
            self._load_namespaces_async()  # Load namespaces immediately like AppChart
        else:
            # Check if namespace dropdown is empty (could happen after cluster change)
            if (
                hasattr(self, "namespace_combo")
                and self.namespace_combo
                and self.namespace_combo.count() <= 1
                and self.namespace_combo.itemText(0) == "Loading namespaces..."
            ):
                logging.debug(
                    f"Detected empty namespace dropdown in {self.__class__.__name__}, refreshing"
                )
                self._load_namespaces_async()
        # Always try to load data when page becomes visible if we don't have current data
        if not self.is_loading_initial and (
            not self.resources or not self._initial_load_done
        ):
            # Reduced delay for faster loading
            QTimer.singleShot(50, self._auto_load_data)

    def _auto_load_data(self):
        """Auto-load data when page is shown - FIXED for large data performance"""
        if (
            hasattr(self, "resource_type")
            and self.resource_type
            and not self.is_loading_initial
        ):
            # Check if we have recent data to avoid redundant loads
            if (
                hasattr(self, "_last_load_time")
                and self._last_load_time > 0
                and time.time() - self._last_load_time < 5.0
            ):  # 5 second throttle
                logging.debug(
                    f"Recent data available for {self.__class__.__name__}, skipping auto-load"
                )
                return
            logging.debug(
                f"Auto-loading data for {self.__class__.__name__}"
            )  # Reduced to debug
            self._initial_load_done = True  # Mark as done to prevent repeated attempts
            self._last_load_time = time.time()  # Track load time
            self.load_data()

    def _start_resource_watch(self):
        """Acquire (or refresh) this page's reference-counted watch stream.

        Reached more than once per visit (showEvent, the cluster-change restart
        timer, namespace-change restart), so it is guarded by _holds_watch_ref:
        a fresh subscription is acquired — and the generation counter bumped —
        only on the first call.  Subsequent calls while the ref is held just
        re-render from cache, which keeps the page generation in lockstep with
        the running watch.  start_watch is reference counted and adopts our
        generation, so an already-active shared stream (e.g. one pre-started by
        the cluster connector) starts emitting under our generation instead of
        having its updates silently discarded.
        """
        if not hasattr(self, 'resource_type') or not self.resource_type:
            return
        skip_types = {'charts', 'helmreleases', 'portforwarding'}
        if self.resource_type in skip_types or not getattr(self, 'uses_unified_search', True):
            return
        try:
            from Utils.unified_resource_loader import cluster_scoped_resources
            loader = get_unified_resource_loader()
            namespace = getattr(self, 'namespace_filter', 'All Namespaces')
            if namespace == 'All Namespaces' or self.resource_type in cluster_scoped_resources:
                watch_ns = None
            else:
                watch_ns = namespace

            if getattr(self, '_holds_watch_ref', False):
                held_ns = getattr(self, '_current_watch_ns', None)
                if watch_ns == held_ns:
                    # Already subscribed to this exact stream — don't re-bump the
                    # generation or double-count the refcount.  Just refresh.
                    cached = loader.get_watch_cached_items(self.resource_type, watch_ns)
                    if cached:
                        self._render_from_cache(cached)
                    return
                # Namespace changed without an explicit stop — release the stale
                # reference before acquiring the new one (defensive; the normal
                # ns-change path stops first).
                loader.stop_watch(self.resource_type, held_ns)
                self._holds_watch_ref = False

            self._watch_generation += 1
            # Reference counted: starts a new stream tagged with our generation,
            # or registers us on an existing one and adopts our generation.
            # State flags are set AFTER a successful start so a raised exception
            # leaves _holds_watch_ref=False and allows the next show() to retry.
            loader.start_watch(self.resource_type, watch_ns,
                               generation=self._watch_generation)
            self._current_watch_ns = watch_ns
            self._holds_watch_ref = True

            # If the stream we joined already had cached data, render instantly.
            cached = loader.get_watch_cached_items(self.resource_type, watch_ns)
            if cached:
                logging.debug(
                    f"{self.__class__.__name__}: rendering {len(cached)} cached "
                    f"{self.resource_type} items instantly (watch already active)"
                )
                self._render_from_cache(cached)
        except Exception as e:
            logging.debug(f"Could not start watch for {self.resource_type}: {e}")

    def _render_from_cache(self, cached_items: list):
        """Render data from the watch cache without an API call."""
        result = LoadResult(
            success=True,
            resource_type=self.resource_type,
            items=cached_items,
            total_count=len(cached_items),
            load_time_ms=0,
            from_cache=True,
            metadata={'generation': self._watch_generation},
        )
        self._on_unified_resources_loaded(self.resource_type, result)

    def _stop_resource_watch(self):
        """Release this page's reference to the watch stream.

        Called from hideEvent (page navigated away) and before namespace
        changes.  Reference counted in the loader, so this only tears the
        stream down if no other consumer (e.g. the connector daemon) still
        holds it.  Guarded by _holds_watch_ref so a stray stop without a
        matching start cannot underflow the loader's refcount, and the flag is
        cleared up-front so each acquire maps to exactly one release.  stop()
        does NOT join the daemon thread, so this returns instantly.
        """
        if not getattr(self, '_holds_watch_ref', False):
            return
        self._holds_watch_ref = False
        watch_ns = getattr(self, '_current_watch_ns', None)
        if not hasattr(self, 'resource_type') or not self.resource_type:
            return
        skip_types = {'charts', 'helmreleases', 'portforwarding'}
        if self.resource_type in skip_types or not getattr(self, 'uses_unified_search', True):
            return
        try:
            loader = get_unified_resource_loader()
            loader.stop_watch(self.resource_type, watch_ns)
        except Exception:
            pass

    @property
    def watch_namespace(self):
        """Public read accessor for the page's current watch namespace.

        Returns the namespace string the active watch is keyed on, or None
        for cluster-scoped resources / "All Namespaces".  Use this from
        other modules instead of reading _current_watch_ns directly so the
        underlying storage can evolve without breaking external callers.
        """
        return getattr(self, '_current_watch_ns', None)

    def setup_ui(self, title, headers, sortable_columns=None):
        page_main_layout = QVBoxLayout(self)
        page_main_layout.setContentsMargins(16, 16, 16, 16)
        page_main_layout.setSpacing(16)
        header_controls_layout = QHBoxLayout()
        # Stored so subclasses can insert page-specific header widgets without
        # traversing the layout tree or matching button text (see PodsPage).
        self.header_layout = header_controls_layout
        self._create_title_and_count(header_controls_layout, title)
        page_main_layout.addLayout(header_controls_layout)
        self._add_controls_to_header(header_controls_layout)
        self._table_stack = QStackedWidget()
        page_main_layout.addWidget(self._table_stack)
        page_main_layout.setStretchFactor(self._table_stack, 10)
        
        self.table = self._create_table(headers, sortable_columns)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.table_container = QFrame()
        self.table_container.setObjectName("table_container")
        self.table_container.setStyleSheet(BaseTablePageStyles.get_table_container_style())
        self.table_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        shadow = QGraphicsDropShadowEffect(self.table_container)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.table_container.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(self.table_container)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        card_layout.addWidget(self.table)
        
        self._table_stack.addWidget(self.table_container)
        
        # Create a dedicated container for messages (empty / error)
        self._message_widget_container = QWidget()
        message_container_layout = QVBoxLayout(self._message_widget_container)
        message_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_container_layout.setContentsMargins(20, 20, 20, 20)
        self._table_stack.addWidget(self._message_widget_container)
        
        self._table_stack.setCurrentWidget(self.table_container)
        self._table_stack.currentChanged.connect(self._on_stack_changed)
            
        self.select_all_checkbox = self._create_select_all_checkbox()
        self._add_select_all_to_header()
        if hasattr(self, "table") and self.table:
            self.table.verticalScrollBar().valueChanged.connect(self._handle_scroll)
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.table.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
        self.installEventFilter(self)
        return page_main_layout

    def _on_stack_changed(self, index):
        """Adjust UI when switching between table and message views."""
        for i in range(self._table_stack.count()):
            widget = self._table_stack.widget(i)
            policy = widget.sizePolicy()
            policy.setVerticalPolicy(QSizePolicy.Policy.Expanding if i == index else QSizePolicy.Policy.Ignored)
            widget.setSizePolicy(policy)
        self._table_stack.adjustSize()

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
                    f"Memory management: Trimmed {items_to_remove} items from display"
                )
            # Force garbage collection
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
                self, "Loading data...", self._spinner_type
            )
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

        # Re-fit columns to the new viewport width (e.g. after maximise).
        if not hasattr(self, '_resize_col_timer'):
            self._resize_col_timer = QTimer(self)
            self._resize_col_timer.setSingleShot(True)
            self._resize_col_timer.timeout.connect(self._on_resize_refit_columns)
        self._resize_col_timer.start(200)

    def _on_resize_refit_columns(self):
        """Called after window resize settles; re-runs Phase 2 viewport-fit only."""
        try:
            if not self.table or not is_valid(self.table):
                return
            if self.table.rowCount() == 0:
                return
            self._auto_resize_columns()
        except Exception:
            pass

    def _create_title_and_count(self, layout, title_text):
        """Create title and count labels (theme-aware colors, same sizes)"""
        theme = get_theme_manager().get_current_theme()
        self.title_label = QLabel(title_text)
        # Preserve original font size/weight, only make color theme-aware
        self.title_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {theme.colors.TEXT_LIGHT};"
        )
        self.items_count = QLabel("0 items")
        # Preserve original size/margin, only make color theme-aware
        self.items_count.setStyleSheet(
            f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px; margin-left: 8px;"
        )
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
        self.refresh_btn.setStyleSheet(
            BaseResourcePageStyles.get_refresh_button_style()
        )
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
            unified_loader = get_unified_resource_loader()
            # Connect signals if not already connected
            if not hasattr(self, "_namespace_signals_connected"):
                unified_loader.loading_completed.connect(
                    self._on_namespaces_loaded_unified
                )
                unified_loader.loading_error.connect(self._on_namespace_error_unified)
                self._namespace_signals_connected = True
            # Load namespaces using unified loader (same as AppsChart for fast performance)
            self._namespace_operation_id = unified_loader.load_resources_async(
                "namespaces"
            )
        except Exception as e:
            logging.error(f"Failed to start namespace loading: {e}")
            # Fallback to default namespaces
            self._on_namespaces_loaded(["default", "kube-system", "kube-public"])

    def _on_namespaces_loaded_unified(self, resource_type: str, result):
        if resource_type != "namespaces":
            return
        # Skip if page is hidden (navigated away)
        if getattr(self, "_was_hidden", False):
            return
        if result.success:
            # Extract namespace names from the processed results
            namespaces = [
                item.get("name", "") for item in result.items if item.get("name")
            ]
            # Sort namespaces with default first, then alphabetically
            important_namespaces = [
                "default",
                "kube-system",
                "kube-public",
                "kube-node-lease",
            ]
            other_namespaces = sorted(
                [ns for ns in namespaces if ns not in important_namespaces]
            )
            sorted_namespaces = [
                ns for ns in important_namespaces if ns in namespaces
            ] + other_namespaces
            self._on_namespaces_loaded(sorted_namespaces)
        else:
            self._on_namespace_error_unified(
                "namespaces", result.error_message or "Failed to load namespaces"
            )

    def _on_namespace_error_unified(self, resource_type: str, error_message: str):
        if resource_type != "namespaces":
            return
        # Skip if page is hidden (navigated away)
        if getattr(self, "_was_hidden", False):
            return
        logging.error(f"Failed to load namespaces via unified loader: {error_message}")
        self._on_namespaces_loaded(["default", "kube-system", "kube-public"])

    def _on_namespaces_loaded(self, namespaces):
        try:
            if not self.namespace_combo:
                # For cluster - scoped resources, set namespace filter to All Namespaces
                self.namespace_filter = "All Namespaces"
                return
            # Temporarily disconnect the signal to prevent recursive calls
            try:
                self.namespace_combo.currentTextChanged.disconnect(
                    self._on_namespace_changed
                )
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
            # Set default selection more carefully
            if (
                not hasattr(self, "namespace_filter")
                or self.namespace_filter == "default"
            ):
                # Set to default namespace if it exists
                default_index = self.namespace_combo.findText("default")
                if default_index >= 0:
                    self.namespace_combo.setCurrentIndex(default_index)
                    self.namespace_filter = "default"
                    logging.debug(
                        f"Set namespace dropdown to 'default' (index {default_index})"
                    )
                else:
                    # If no default namespace, use "All Namespaces"
                    self.namespace_combo.setCurrentIndex(0)
                    self.namespace_filter = "All Namespaces"
                    logging.debug(
                        "Set namespace dropdown to 'All Namespaces' (no default found)"
                    )
            else:
                # Try to restore the current namespace filter
                current_index = self.namespace_combo.findText(self.namespace_filter)
                if current_index >= 0:
                    self.namespace_combo.setCurrentIndex(current_index)
                    logging.debug(
                        f"Restored namespace dropdown to '{self.namespace_filter}' (index {current_index})"
                    )
                else:
                    # Fallback to All Namespaces if current filter not found
                    self.namespace_combo.setCurrentIndex(0)
                    self.namespace_filter = "All Namespaces"
                    logging.debug("Fallback: Set namespace dropdown to 'All Namespaces'")
            # Reconnect the signal after setting the dropdown
            self.namespace_combo.currentTextChanged.connect(self._on_namespace_changed)
            # Re - enable the dropdown after successful loading
            self.namespace_combo.setEnabled(True)
            logging.debug(
                f"Loaded {len(namespaces)} namespaces into dropdown, current filter: {self.namespace_filter}"
            )
        except Exception as e:
            logging.error(f"Error updating namespace dropdown: {e}")
            # Ensure signal is reconnected and dropdown enabled even on error
            try:
                if self.namespace_combo:
                    self.namespace_combo.currentTextChanged.connect(
                        self._on_namespace_changed
                    )
                    self.namespace_combo.setEnabled(True)
            except BaseException:
                pass
            # Set a default filter to prevent issues
            self.namespace_filter = "All Namespaces"

    def refresh_namespaces(self):
        self._namespaces_loaded = False  # Reset the flag
        self._load_namespaces_async()

    # ── Phase 5: pre-show namespace_filter validation ──────────────────────

    def _validate_namespace_filter_against_cluster(self):
        """Reset a stale namespace_filter to 'default' before the watch starts.

        Called from showEvent.  The reactive Phase 4 slot only catches
        deletions while a page is live; pages hidden during the deletion
        retain their stale filter and would otherwise fire a watch into a
        nonexistent namespace.  This synchronous gate closes that gap.

        Cheap: O(1) set membership against the kubernetes_client's
        authoritative _known_namespaces cache, which is maintained by the
        app-lifetime namespace watch daemon.

        Skips validation when:
          - the current filter is a sentinel value ('default' / 'All Namespaces')
            because both are always safe targets
          - the cluster's namespace cache is empty (early startup, pre-connect)
            because we cannot distinguish "namespace gone" from "we don't
            know yet"
        """
        try:
            current = getattr(self, "namespace_filter", None)
            if not current or current in ("default", "All Namespaces"):
                return
            kc = getattr(self, "kube_client", None)
            if kc is None or not hasattr(kc, "get_known_namespaces"):
                return
            live = kc.get_known_namespaces()
            if not live:
                # Daemon hasn't populated yet — don't false-positive every
                # filter as dead on first cluster connect.
                return
            if current in live:
                return
            # Namespace was deleted out-of-band while this page was hidden.
            logging.info(
                f"{self.__class__.__name__}: namespace_filter "
                f"'{current}' is no longer present in the cluster; "
                f"falling back to 'default' before starting watch."
            )
            self.namespace_filter = "default"
            # Sync the visible combo selection if it has been built.  Block
            # the changed-signal so we don't trigger an extra reload — the
            # caller (showEvent) is about to start the watch anyway.
            if getattr(self, "namespace_combo", None) is not None:
                idx = self.namespace_combo.findText("default")
                if idx >= 0:
                    # Block currentTextChanged: setCurrentIndex would
                    # otherwise fire _on_namespace_changed, which calls
                    # _stop_resource_watch + force_load_data — but showEvent
                    # is about to call _start_resource_watch immediately
                    # after this validation returns.  Without this guard
                    # we'd get a stop-start-stop-start cycle on every
                    # stale-filter reset.  Load-bearing — do not remove.
                    self.namespace_combo.blockSignals(True)
                    try:
                        self.namespace_combo.setCurrentIndex(idx)
                    finally:
                        self.namespace_combo.blockSignals(False)
        except Exception as e:
            logging.debug(f"namespace_filter validation failed: {e}")

    # ── Phase 4: live namespace dropdown subscriptions ─────────────────────

    def _connect_namespace_lifecycle_signals(self):
        """Subscribe the dropdown to namespace_added / namespace_deleted on
        the kubernetes_client.  The app-lifetime namespace watch daemon (see
        KubernetesClient.ensure_namespace_watch) drives both signals, so
        out-of-band kubectl create/delete propagates here automatically.
        """
        try:
            if self.kube_client is None:
                return
            if hasattr(self.kube_client, "namespace_added_signal"):
                self.kube_client.namespace_added_signal.connect(
                    self._add_namespace_to_dropdown
                )
            if hasattr(self.kube_client, "namespace_deleted_signal"):
                self.kube_client.namespace_deleted_signal.connect(
                    self._remove_namespace_from_dropdown
                )
        except Exception as e:
            logging.debug(f"namespace signal connect failed: {e}")

    def _add_namespace_to_dropdown(self, namespace_name: str):
        """Insert a newly-created namespace into the dropdown if not present.

        Defensively guarded against pre-init states (combo not yet built)
        and torn-down receivers.
        """
        try:
            if not is_valid(self):
                return
            if not self.namespace_combo or not namespace_name:
                return
            if self.namespace_combo.findText(namespace_name) != -1:
                return  # Already present — bulk-load or duplicate event.
            self.namespace_combo.blockSignals(True)
            try:
                self.namespace_combo.addItem(namespace_name)
            finally:
                self.namespace_combo.blockSignals(False)
            logging.debug(
                f"{self.__class__.__name__}: added namespace '{namespace_name}' to dropdown"
            )
        except Exception as e:
            logging.debug(f"_add_namespace_to_dropdown failed: {e}")

    def _remove_namespace_from_dropdown(self, namespace_name: str):
        """Remove a deleted namespace from the dropdown.

        Critical safety: if the deleted namespace was the active filter,
        fall back to 'default' (or 'All Namespaces' if no default exists)
        and force a table reload so the page stops querying a context
        the cluster has already purged.  Without this guard the page
        would cascade 404s on every refresh.
        """
        try:
            if not is_valid(self):
                return
            if not self.namespace_combo or not namespace_name:
                return
            idx = self.namespace_combo.findText(namespace_name)
            if idx == -1:
                return
            was_active = (
                getattr(self, "namespace_filter", None) == namespace_name
            )
            self.namespace_combo.blockSignals(True)
            try:
                self.namespace_combo.removeItem(idx)
            finally:
                self.namespace_combo.blockSignals(False)
            logging.debug(
                f"{self.__class__.__name__}: removed namespace "
                f"'{namespace_name}' from dropdown"
            )
            if was_active:
                # Fall back to a known-safe filter and reload.  Prefer the
                # real 'default' namespace if it still exists; otherwise
                # use 'All Namespaces'.
                fallback = "default"
                if self.namespace_combo.findText(fallback) == -1:
                    fallback = "All Namespaces"
                logging.warning(
                    f"{self.__class__.__name__}: active namespace "
                    f"'{namespace_name}' deleted out-of-band; falling "
                    f"back to '{fallback}'."
                )
                # Position the combo on the fallback with signals blocked so we
                # invoke the namespace-change handler exactly once below (rather
                # than letting setCurrentIndex fire it implicitly).
                fallback_idx = self.namespace_combo.findText(fallback)
                if fallback_idx != -1:
                    self.namespace_combo.blockSignals(True)
                    try:
                        self.namespace_combo.setCurrentIndex(fallback_idx)
                    finally:
                        self.namespace_combo.blockSignals(False)
                # Delegate to the namespace-change handler so the live watch is
                # unsubscribed from the deleted namespace and re-subscribed to
                # the fallback.  It also sets namespace_filter, resets pagination
                # and reloads the table.  namespace_filter is intentionally left
                # at the (deleted) value here so the handler's old==new guard
                # does not short-circuit the restart.
                if getattr(self, "namespace_filter", None) != fallback:
                    try:
                        self._on_namespace_changed(fallback)
                    except Exception as e:
                        logging.debug(
                            f"namespace-change restart after ns delete failed: {e}"
                        )
        except Exception as e:
            logging.debug(f"_remove_namespace_from_dropdown failed: {e}")

    def _on_namespace_changed(self, namespace):
        if namespace == "Loading namespaces...":
            return  # Ignore the loading placeholder
        old_namespace = getattr(self, "namespace_filter", "default")
        # Only proceed if namespace actually changed
        if old_namespace == namespace:
            logging.debug(f"Namespace unchanged ({namespace}), skipping reload")
            return
        logging.debug(f"Namespace changed from '{old_namespace}' to '{namespace}'")
        # Stop watch for old namespace, start watch for new namespace
        self._stop_resource_watch()
        # Cache system removed - no cache clearing needed
        # Update namespace filter BEFORE clearing resources
        self.namespace_filter = namespace
        # Start watch for new namespace scope
        self._start_resource_watch()
        # Reset pagination state
        self.current_continue_token = None
        self.all_data_loaded = False
        # NOTE: Don't clear resources here - let force_load_data handle backup and clearing
        # This ensures we can restore old data if the load fails (e.g., cluster disconnected)
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
                f"Loaded batch: {batch_size} items. Total loaded: {self._loaded_item_count}/{self._total_item_count}"
            )
        except Exception as e:
            logging.error(f"Error loading more data batch: {e}")

    def _handle_scroll(self, value):
        # Use debounced updater for scroll
        self._debounced_updater.schedule_update(
            "scroll_" + self.__class__.__name__,
            self._handle_scroll_debounced,
            delay_ms=SCROLL_DEBOUNCE_MS,
        )

    def _render_more_visible_rows(self):
        """Append the next batch of already-in-memory rows to the table.
        
        Used for lazy rendering of large datasets: all data is already loaded into
        self.resources but only the first 200 rows are drawn initially. This method
        appends the next 100 rows on each scroll-to-bottom event without clearing
        and re-rendering the entire table.
        """
        try:
            currently_rendered = self.table.rowCount()
            total_in_memory = len(self.resources)
            if currently_rendered >= total_in_memory:
                return  # All in-memory rows are already rendered
            next_batch = self.resources[currently_rendered : currently_rendered + 100]
            if next_batch:
                logging.debug(
                    f"Lazy render: appending rows {currently_rendered}–"
                    f"{currently_rendered + len(next_batch) - 1} "
                    f"(total in memory: {total_in_memory})"
                )
                self._render_resources_batch(next_batch, append=True)
        except Exception as e:
            logging.error(f"Error in _render_more_visible_rows: {e}")

    def _handle_scroll_debounced(self):
        if not self.table or self.is_loading_more:
            return
        scrollbar = self.table.verticalScrollBar()
        if scrollbar.value() >= scrollbar.maximum() - 10:  # Near bottom
            # Priority 1: render more already-loaded rows (lazy visual render for
            # large datasets where all data is in self.resources but only 200 are drawn)
            if self._large_dataset_mode and self.table.rowCount() < len(self.resources):
                self._render_more_visible_rows()
                return
            # Priority 2: load next backend batch from _remaining_resources (>2000 items)
            if self._large_dataset_mode and self._remaining_resources:
                self._load_more_data_batch()
            elif not self.all_data_loaded and self.current_continue_token:
                # For normal pagination, use traditional method
                self._load_more_data()

    def _load_more_data(self):
        if (
            self.is_loading_more
            or self.all_data_loaded
            or not self.current_continue_token
        ):
            return
        self.is_loading_more = True
        self._start_loading_thread(continue_token=self.current_continue_token)

    def _start_loading_thread(self, continue_token=None):
        # Bypass unified loader completely for resource types that don't use it
        if not getattr(self, "uses_unified_search", True):
            if type(self).load_data is not BaseResourcePage.load_data:
                try:
                    self.load_data(load_more=bool(continue_token))
                except TypeError:
                    self.load_data()
            else:
                logging.error(f"{self.__class__.__name__} sets uses_unified_search=False but lacks a custom load_data()")
            return

        # Cancel any existing loading
        if (
            hasattr(self, "loading_thread")
            and self.loading_thread
            and self.loading_thread.isRunning()
        ):
            self.loading_thread.cancel()
            self.loading_thread.wait(1000)
        # Get the unified resource loader
        unified_loader = get_unified_resource_loader()
        # Connect signals if not already connected
        if not hasattr(self, "_signals_connected"):
            unified_loader.loading_completed.connect(self._on_unified_resources_loaded)
            unified_loader.loading_error.connect(self._on_unified_loading_error)
            self._signals_connected = True
        # Start loading with optimized configuration
        # Handle "All Namespaces" efficiently by using None (which triggers optimized multi - namespace loading)
        namespace = (
            None if self.namespace_filter == "All Namespaces" else self.namespace_filter
        )
        self._current_operation_id = unified_loader.load_resources_async(
            resource_type=self.resource_type, namespace=namespace
        )
        logging.debug(
            f"Started unified loading for {self.resource_type} (operation: {self._current_operation_id})"
        )

    def _on_unified_resources_loaded(self, resource_type: str, result: LoadResult):
        try:
            # Only process if this matches our resource type
            if resource_type != self.resource_type:
                return
            # Skip if page is hidden (navigated away)
            if getattr(self, "_was_hidden", False):
                # Surfacing this at WARNING because dropped signals during
                # active-page time means UI staleness.  If you see this in the
                # log for a page you're looking at, _was_hidden got stuck.
                logging.warning(
                    f"{self.__class__.__name__}: dropping {resource_type} signal "
                    f"({len(result.items or [])} items) — _was_hidden=True"
                )
                return
            # Generation counter validation gate — reject stale signals that
            # were already queued in the Qt event loop before a namespace or
            # context change.  Signals without a generation tag (e.g. from
            # non-watch worker loads) are always accepted.
            sig_gen = result.metadata.get('generation') if result.metadata else None
            if sig_gen is not None and sig_gen != self._watch_generation:
                logging.debug(
                    f"{self.__class__.__name__}: discarding stale {resource_type} "
                    f"signal (gen {sig_gen} != current {self._watch_generation})"
                )
                return
            if not result.success:
                self._on_unified_loading_error(
                    resource_type, result.error_message or "Unknown error"
                )
                return
            # Process the optimized result format
            resources = result.items or []
            # If result is empty, it means we genuinely have no items (e.g. empty namespace)
            # We do NOT restore backup here, because this is a SUCCESS handler.
            # Backup restoration is only for ERRORS (handled in _on_unified_loading_error).
            # Clear backup on any successful load (including empty results) so
            # stale rows from a previous namespace are not restored on a later error.
            if hasattr(self, "_backup_resources"):
                self._backup_resources = []
            # Check if we have a large dataset.  Only log on transition into
            # large-dataset mode (or back out) — otherwise every count tick
            # during steady-state churn produces an identical "Activating
            # optimizations" INFO line (~100 per minute on busy event pages).
            self._total_item_count = len(resources)
            was_large_dataset_mode = getattr(self, "_large_dataset_mode", False)
            self._large_dataset_mode = self._total_item_count > LARGE_DATASET_THRESHOLD
            if self._large_dataset_mode and not was_large_dataset_mode:
                logging.info(
                    f"Large dataset detected: {self._total_item_count} items. Activating optimizations."
                )
            elif not self._large_dataset_mode and was_large_dataset_mode:
                logging.info(
                    f"Dataset shrank below threshold ({self._total_item_count} items). Deactivating optimizations."
                )
            if self._large_dataset_mode:
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
            # Always display resources, even if empty.
            # Watch-driven updates (load_time_ms == 0) use an efficient in-place
            # path that avoids clearing and rebuilding the entire table.
            is_watch_update = result.load_time_ms == 0 and self._initial_load_done

            if is_watch_update:
                # ── UI-side coalescing ──
                # Multiple watch signals queue up as QMetaCallEvents.  The main
                # thread processes them sequentially, but rendering 95 rows for
                # EVERY signal (~50ms each × 50 signals = 2.5s freeze) is fatal.
                # Instead, we store the latest data and schedule a single deferred
                # render via QTimer.  All intermediate signals just update the
                # stored reference — O(1) per signal, zero rendering.
                self._pending_watch_data = self.resources
                self.items_count.setText(f"{self._total_item_count} items")
                self._schedule_watch_render()
                # Complete the non-rendering bookkeeping
                self.is_loading_initial = False
                self.is_loading_more = False
                self.hide_loading_indicator()
                return

            # Non-watch path: initial load, full refresh — render immediately
            self._display_resources(self.resources)
            # Update items count directly from the result to avoid timing issues
            # with self.resources not being set when duplicate requests occur
            self.items_count.setText(f"{self._total_item_count} items")
            self.is_loading_initial = False
            self.is_loading_more = False
            self._initial_load_done = True
            # Hide loading indicator
            self.hide_loading_indicator()
            self.all_items_loaded_signal.emit()
            self.load_more_complete.emit()
            # Log performance info — only real API calls (load_time_ms > 0) at INFO;
            # watch/cache updates (0ms) are debug-only to avoid event-driven noise.
            msg = f"Loaded {len(result.items or [])}/{self._total_item_count} {resource_type} in {result.load_time_ms:.1f}ms"
            if result.load_time_ms > 0:
                logging.info(msg)
            else:
                logging.debug(msg)
        except Exception as e:
            logging.error(f"Error processing unified resources: {e}")
            self._on_unified_loading_error(resource_type, str(e))

    def _on_unified_loading_error(self, resource_type: str, error_message: str):
        if resource_type != self.resource_type:
            return
        # Skip if page is hidden (navigated away)
        if getattr(self, "_was_hidden", False):
            return
        self.is_loading_initial = False
        self.is_loading_more = False
        # Hide loading indicator on error
        self.hide_loading_indicator()
        # Restore backup data if available - preserves visible data during transient failures
        if hasattr(self, "_backup_resources") and self._backup_resources:
            logging.warning(
                f"Loading error for {resource_type} - restoring {len(self._backup_resources)} backed up items"
            )
            self.resources = self._backup_resources
            self._backup_resources = []
            self._display_resources(self.resources)
            self._update_items_count()
        else:
            # Only show error if we have no data to display
            error_handler = get_error_handler()
            error_handler.handle_error(
                Exception(error_message), f"loading {resource_type}", show_dialog=True
            )
        self.load_more_complete.emit()

    def _on_resources_loaded(self, result):
        try:
            resources, resource_type, next_token = result
            if getattr(self.loading_thread, "continue_token", None):
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
            self._row_cache = RowCache()  # clear cache for empty state
            self._show_empty_message()
            return
        if self._table_stack:
            if hasattr(self, 'table_container') and self.table_container:
                self._table_stack.setCurrentWidget(self.table_container)
            else:
                self._table_stack.setCurrentWidget(self.table)
        # Clear previous selections when displaying new data
        self.selected_items.clear()
        # Log performance info for large datasets
        if len(resources) > 100:
            logging.info(
                f"Displaying {len(resources)} resources (large dataset optimization active)"
            )
        # Optimized rendering for all datasets
        self._render_resources_batch(resources)
        # ── Rebuild row cache after full render ──────────────────────
        # This populates the diff engine's baseline so subsequent watch
        # updates can compute surgical diffs instead of full rebuilds.
        self._rebuild_row_cache(resources)

    def _render_resources_batch(self, resources, append=False):
        if not append:
            self.clear_table()
        if not resources:
            return
        # Suppress per-row layout recalculations and repaints while populating.
        # All visual updates are flushed in a single frame when re-enabled.
        self.table.setUpdatesEnabled(False)
        try:
            # Disable sorting during batch rendering for better performance
            self.table.setSortingEnabled(False)
            start_row = self.table.rowCount() if append else 0
            # Handle large datasets efficiently
            if len(resources) > 500:
                # For large datasets, render only the first visible batch.
                # FIXED: Only allocate rows we actually populate — prevents blank row slots
                # that were caused by setRowCount(N) + loop capped at 200.
                render_count = min(200, len(resources))
                self.table.setRowCount(start_row + render_count)
                batch_size = 100
                for i in range(0, render_count, batch_size):
                    batch = resources[i : i + batch_size]
                    for j, resource in enumerate(batch):
                        row = start_row + i + j
                        if hasattr(self, "populate_resource_row"):
                            self.populate_resource_row(row, resource)
                        else:
                            self._populate_resource_row(row, resource)
            else:
                # For smaller datasets, render all rows normally
                self.table.setRowCount(start_row + len(resources))
                batch_size = 50
                for i in range(0, len(resources), batch_size):
                    batch = resources[i : i + batch_size]
                    for j, resource in enumerate(batch):
                        row = start_row + i + j
                        if hasattr(self, "populate_resource_row"):
                            self.populate_resource_row(row, resource)
                        else:
                            self._populate_resource_row(row, resource)
            # Re-enable sorting after all rows are added
            self.table.setSortingEnabled(True)
        finally:
            self.table.setUpdatesEnabled(True)
        # Schedule layout updates
        QTimer.singleShot(10, self._update_table_height)
        QTimer.singleShot(150, self._auto_resize_columns)

    # ── Watch-update coalescing ──────────────────────────────────────────
    # The watch thread emits signals that queue as QMetaCallEvents.  The
    # main thread processes them FIFO, BEFORE timer events.  Without
    # coalescing, 50 queued signals → 50 full table re-renders → 2.5s
    # UI freeze.  The QTimer below ensures at most one render per 300ms
    # window.

    _WATCH_RENDER_INTERVAL_MS = 300  # coalesce window

    def _schedule_watch_render(self):
        """Schedule a deferred render of the latest watch data.

        If a timer is already ticking, this is a no-op — the pending data
        reference was already updated by the caller.  When the timer fires,
        _flush_watch_render will render the *most recent* snapshot.
        """
        if not hasattr(self, '_watch_render_timer') or self._watch_render_timer is None:
            self._watch_render_timer = QTimer(self)
            self._watch_render_timer.setSingleShot(True)
            self._watch_render_timer.timeout.connect(self._flush_watch_render)
        # Only start if not already running — avoids resetting the window
        if not self._watch_render_timer.isActive():
            self._watch_render_timer.start(self._WATCH_RENDER_INTERVAL_MS)

    def _flush_watch_render(self):
        """Called by QTimer — render the latest watch snapshot exactly once."""
        data = getattr(self, '_pending_watch_data', None)
        if data is None:
            return
        self._pending_watch_data = None
        logging.debug(f"_flush_watch_render: rendering {len(data)} items")
        if data:
            self._apply_watch_update(data)
        else:
            # All items deleted — show empty state
            self._display_resources(data)

    def _apply_watch_update(self, resources):
        """Apply a watch-driven update using the diff engine for skip-detection.

        Uses the diff engine to detect whether the incoming data actually
        differs from the current table state.  If nothing changed (is_empty),
        the rebuild is skipped entirely — this is the primary performance win,
        avoiding ~50ms of widget churn per coalesced watch tick on idle
        clusters.

        When changes ARE detected (additions, removals, modifications), the
        legacy full-rebuild path is used.  Surgical row-level mutations
        (removeRow/insertRow) were found to cause index-desync and access
        violations during theme switching, so the safe setRowCount() +
        repopulate path is used instead.
        """
        if getattr(self, 'REQUIRES_FULL_RESET', False):
            self._apply_watch_update_legacy(resources)
            return

        if not resources:
            self._row_cache = RowCache()
            self._show_empty_message()
            return
        if self._table_stack:
            if hasattr(self, 'table_container') and self.table_container:
                self._table_stack.setCurrentWidget(self.table_container)
            else:
                self._table_stack.setCurrentWidget(self.table)

        # ── Build new cache and compute diff ─────────────────────────
        new_cache = RowCache()
        try:
            new_cache.rebuild(resources, self._project_row_data)
        except Exception as e:
            logging.warning(
                f"Diff projection failed ({e}), falling back to full rebuild"
            )
            self._apply_watch_update_legacy(resources)
            return

        diff = compute_diff(self._row_cache, new_cache)

        if diff.is_empty:
            # No changes at all — skip the entire rebuild.
            # This is the main performance win: on idle clusters, watch
            # ticks arrive every ~30s with identical data.  Without this
            # check, each tick would destroy and recreate every widget.
            self._row_cache = new_cache
            return

        # Changes detected — log summary at DEBUG for diagnostics
        logging.debug(
            f"Diff engine: {len(diff.removed)} removed, "
            f"{len(diff.modified)} modified, {len(diff.added)} added"
            f"{' (full reset)' if diff.is_full_reset else ''}"
        )

        # Capture scroll position before rebuild
        scroll_pos = self.table.verticalScrollBar().value() if self.table.verticalScrollBar() else 0

        # Use the safe legacy full-rebuild path for ALL changes
        self._apply_watch_update_legacy(resources)

        # Restore scroll position after rebuild
        if self.table.verticalScrollBar() and scroll_pos > 0:
            QTimer.singleShot(10, lambda: (
                self.table.verticalScrollBar().setValue(scroll_pos)
                if self.table.verticalScrollBar() else None
            ))

        # Cache is already rebuilt inside _apply_watch_update_legacy
        QTimer.singleShot(10, self._update_table_height)

    def _apply_watch_update_legacy(self, resources):
        """Legacy full-rebuild path for watch updates.

        Used when the diff engine flags is_full_reset (volumetric guard)
        or when projection fails.  Identical to the original _apply_watch_update.
        """
        if not resources:
            self._show_empty_message()
            return
        # Selection state (selected_items) is intentionally PRESERVED across
        # this rebuild.  The legacy path destroys and recreates every row
        # widget, so checkboxes return unchecked; _restore_row_selection_state()
        # below re-applies the user's selection after repopulation and prunes
        # entries for resources that disappeared in this update.
        new_count = len(resources)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setSortingEnabled(False)
            # Immediately orphan every existing cell widget BEFORE repopulating.
            # setCellWidget() only schedules the old widget for deferred
            # deleteLater(); under heavy churn (e.g. 1000 pods appearing at
            # once) the event loop can't drain that queue, so the old
            # checkbox/status/action widgets stay parented to the viewport and
            # paint as duplicates on top of the new ones until deletion catches
            # up.  _teardown_row_widgets() calls setParent(None), removing them
            # from the widget tree synchronously so no zombie ever paints.
            for row in range(self.table.rowCount()):
                self._teardown_row_widgets(row)
            self.table.setRowCount(new_count)
            for row, resource in enumerate(resources):
                if hasattr(self, "populate_resource_row"):
                    self.populate_resource_row(row, resource)
                else:
                    self._populate_resource_row(row, resource)
            self.table.setSortingEnabled(True)
        finally:
            self.table.setUpdatesEnabled(True)
        # Rebuild row cache after legacy full rebuild
        self._rebuild_row_cache(resources)
        # Re-apply preserved checkbox selections to the freshly-built rows.
        self._restore_row_selection_state()
        # Resize columns after updates are enabled
        QTimer.singleShot(150, self._auto_resize_columns)

    # ── Diff-engine helpers ──────────────────────────────────────────────

    def _rebuild_row_cache(self, resources):
        """Rebuild the UID-keyed row cache from a full resource list.

        Called after initial loads and legacy full-rebuilds to establish
        the baseline that subsequent watch-driven diffs compare against.
        """
        try:
            self._row_cache = RowCache()
            self._row_cache.rebuild(resources or [], self._project_row_data)
            logging.debug(
                f"Row cache rebuilt: {len(self._row_cache)} entries "
                f"for {self.__class__.__name__}"
            )
        except Exception as e:
            logging.warning(f"Row cache rebuild failed: {e}")
            self._row_cache = RowCache()

    def _project_row_data(self, resource):
        """Project a raw resource dict into a flat row dict for diffing.

        The base implementation extracts universally available fields.
        Subclasses should override this to include page-specific columns
        (e.g., pod container count, deployment conditions).

        CRITICAL: This method must NEVER store visual properties (colors,
        styles, font weights).  Only semantic/display-text values that
        determine whether a cell has changed content.

        The returned dict MUST include a "uid" key.  Resources without a
        stable UID are skipped by the diff engine.
        """
        uid = self._build_uid_from_resource(resource)
        return {
            "uid": uid,
            "name": resource.get("name", ""),
            "namespace": resource.get("namespace", ""),
            "age": resource.get("age", ""),
            "status": resource.get("status", ""),
            "_raw": resource,  # internal — excluded from diff comparison
        }

    def _build_uid_from_resource(self, resource):
        """Extract or synthesize a stable UID for a resource.

        Prefers the Kubernetes metadata.uid.  Falls back to a composite
        key of (name, namespace) for resources that lack raw_data (e.g.,
        synthetic entries from port-forwarding or helm).
        """
        # Try Kubernetes UID from raw API response
        raw = resource.get("raw_data") or {}
        uid = ""
        if isinstance(raw, dict):
            uid = raw.get("metadata", {}).get("uid", "")
        # Fallback: composite key
        if not uid:
            name = resource.get("name", "")
            ns = resource.get("namespace", "")
            uid = f"{ns}/{name}" if ns else name
        return uid

    def _teardown_row_widgets(self, row_idx):
        """Strict PyQt memory teardown for a table row.

        Minimal crash-free sequence per cell widget:

          1. removeCellWidget() — detach from the table cell
          2. hide() — stop it painting over the cell immediately
          3. deleteLater() — schedule C++ destruction on the next idle

        This method previously did MORE (setParent(None) to "orphan" the widget,
        plus a recursive blockSignals/findChildren/disconnect sweep).  Both of
        those were proven — deterministically, via stress_harness_theme_crash.py
        — to CAUSE the theme-toggle access violation (0xC0000005) under heavy
        table churn:
          • setParent(None) reparents the widget to nothing, promoting it to a
            TOP-LEVEL widget that app.setStyleSheet() polishes mid-destruction.
          • the recursive disconnect() sweep left the widget in a state the
            style engine segfaulted on during the next repolish.
        The harness A/B is unambiguous: WITH either of those the app segfaults
        within seconds of churn+theme-toggle; with only removeCellWidget()+hide()
        +deleteLater() it survives indefinitely.  Qt auto-disconnects a widget's
        signals when it is destroyed, so the explicit disconnect was redundant;
        removeCellWidget()+hide() already stop duplicate-row painting.
        """
        if not self.table or not hasattr(self.table, 'columnCount'):
            return
        try:
            for col in range(self.table.columnCount()):
                widget = self.table.cellWidget(row_idx, col)
                if widget is not None:
                    # Detach from the cell and hide so it stops painting over
                    # the cell immediately, then schedule C++ destruction on the
                    # next idle.  Qt auto-disconnects all of a widget's signals
                    # when it is destroyed, so no explicit disconnect() is needed.
                    #
                    # Two things deliberately AVOIDED here, both proven to cause
                    # the theme-toggle access violation (0xC0000005) under heavy
                    # table churn via stress_harness_theme_crash.py:
                    #   • setParent(None) — promotes the widget to a TOP-LEVEL
                    #     orphan that app.setStyleSheet() polishes mid-destruction.
                    #   • widget.disconnect()/findChildren()+disconnect() — the
                    #     recursive disconnect sweep left the widget in a state
                    #     the style engine segfaulted on during the next repolish.
                    # removeCellWidget()+hide()+deleteLater() alone is crash-free
                    # under the harness AND still prevents duplicate-row painting.
                    self.table.removeCellWidget(row_idx, col)
                    widget.hide()
                    widget.deleteLater()
        except Exception as e:
            logging.debug(f"Row widget teardown error at row {row_idx}: {e}")

    def _find_row_index_by_uid(self, uid):
        """Find the current table row index for a given UID.

        Walks the row cache's uid list and maps to the current table
        position.  Returns -1 if the UID is not found.

        NOTE: This performs a linear scan.  For tables with <2000 rows
        (our MAX_ITEMS_IN_MEMORY cap) this is sub-millisecond.
        """
        try:
            uids = self._row_cache.uids
            if uid in uids:
                idx = uids.index(uid)
                # Validate against actual table row count
                if idx < self.table.rowCount():
                    return idx
        except (ValueError, AttributeError):
            pass
        return -1

    def _find_resource_by_uid(self, resources, uid):
        """Find a resource dict in a list by its UID.

        Uses _build_uid_from_resource to match against the target UID.
        Returns None if not found.
        """
        for resource in resources:
            if self._build_uid_from_resource(resource) == uid:
                return resource
        return None

    def _populate_resource_row(self, row, resource):
        # Default implementation for common fields - can be overridden by subclasses
        # Create checkbox for the first column
        checkbox_container = self._create_checkbox_container(
            row, resource.get("name", "Unknown")
        )
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
        # The list is now empty, so drop any lingering selection — the rows it
        # referenced are gone and "Delete Selected" must not act on vanished
        # items.  Centralizing the clear here covers every empty-state caller
        # (initial display and watch-driven emptying), each of which returns
        # before its normal selection clear/prune step would run.
        self.selected_items.clear()
        # Keep table headers visible - don't clear the table completely
        if self.table:
            # setRowCount is QTableWidget-only.  Pages migrated to QTableView
            # (model-view) must clear via their own model.set_resources([])
            # which they do in their overridden clear_table().
            if hasattr(self.table, "setRowCount"):
                self.table.setRowCount(0)  # Just clear rows, keep headers
            elif hasattr(self, "clear_table"):
                self.clear_table()
            self.table.show()  # Ensure table is visible
        # Clear and setup the message container
        self._clear_message_container()
        # Check if we're in search mode to show appropriate message
        is_searching = getattr(self, "_is_searching", False)
        current_search_query = getattr(self, "_current_search_query", None)
        search_bar_text = (
            self.search_bar.text().strip() if hasattr(self, "search_bar") else ""
        )
        # Use either the stored search query or current search bar text
        active_search_query = current_search_query or search_bar_text
        if is_searching and active_search_query:
            # Show search - specific empty message
            empty_title = QLabel(f"No results found for '{active_search_query}'")
            empty_subtitle = QLabel(
                "Try a different search term or clear the search to see all resources"
            )
        else:
            # Show general empty message
            empty_title = QLabel("No resources found")
            empty_subtitle = QLabel("Connect to a cluster or check your filters")
        # Apply styling to both title and subtitle
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setStyleSheet(self.style_manager.get_empty_title_style())
        empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_subtitle.setStyleSheet(self.style_manager.get_empty_subtitle_style())
        # Add widgets to message container
        self._message_widget_container.layout().addWidget(empty_title)
        self._message_widget_container.layout().addWidget(empty_subtitle)
        if self._table_stack:
            # Show the message overlay but keep table visible in background
            if hasattr(self, 'table_container') and self.table_container:
                self._table_stack.setCurrentWidget(self.table_container)
            else:
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
        if self._table_stack:
            self._table_stack.setCurrentWidget(self._message_widget_container)

    def _clear_message_container(self):
        layout = self._message_widget_container.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _get_stale_cached_items(self) -> list:
        """Return the most recently cached result for this resource type + namespace,
        or an empty list if nothing is cached.  Used by SWR to render stale data
        instantly while a background refresh is in flight."""
        try:
            from Utils.unified_cache_system import get_unified_cache
            if not self.resource_type:
                return []
            kube_client = self.kube_client
            cluster_name = getattr(kube_client, 'current_cluster', None) if kube_client else None
            if not cluster_name:
                return []
            namespace = (
                None if self.namespace_filter == "All Namespaces"
                else self.namespace_filter
            )
            namespace_key = f"ns_{namespace}" if namespace else "all_namespaces"
            cache_key = f"{cluster_name}_{self.resource_type}_{namespace_key}"
            items = get_unified_cache().get_cached_resources(self.resource_type, cache_key)
            if not items:
                logging.debug(
                    f"SWR cache miss for {self.resource_type} "
                    f"(key={cache_key}, namespace={namespace_key})"
                )
            return items if items else []
        except Exception:
            return []

    def force_load_data(self):
        # Guard: If any load is already in progress, don't clear resources or start a new load.
        # Checking both flags prevents the race condition where a force_load_data call during
        # an active scroll-triggered page load (is_loading_more=True) would overwrite
        # _backup_resources with an empty list and corrupt the loading state machine.
        if self.is_loading_initial or self.is_loading_more:
            logging.debug(
                f"{self.__class__.__name__}: Skipping force_load_data - load already in progress "
                f"(initial={self.is_loading_initial}, more={self.is_loading_more})"
            )
            return

        # SWR: render stale cached data immediately so the user sees content right
        # away while the background refresh is in flight — no loading spinner needed.
        stale_items = self._get_stale_cached_items()
        if stale_items:
            self.resources = list(stale_items)
            self._display_resources(self.resources)
            self.items_count.setText(f"{len(self.resources)} items")
            self._backup_resources = list(self.resources)
            logging.debug(
                f"{self.__class__.__name__}: SWR — rendered {len(stale_items)} "
                f"stale {self.resource_type} items instantly"
            )
            # Keep self.resources aligned with the displayed stale rows so
            # checkbox/action lookups still resolve raw_data while the refresh
            # is in flight.  The background load replaces self.resources
            # wholesale on completion, so nothing accumulates.
            self._clear_resources(keep_data=True)
        else:
            # No previous data — show the loading spinner for a true cold start.
            self.show_loading_indicator("Refreshing data...")
            self._backup_resources = list(self.resources) if self.resources else []
            self._clear_resources()  # clears self.resources list; table display is untouched
        self.current_continue_token = None
        self.all_data_loaded = False
        self.is_loading_initial = True
        self._start_loading_thread()

    def _clear_resources(self, keep_data=False):
        # keep_data=True retains self.resources so SWR-displayed stale rows
        # keep their raw_data for checkbox/action lookups while the refresh is
        # in flight; the large-dataset bookkeeping is still reset below.
        if not keep_data:
            self.resources.clear()
        # Also clear any remaining resources for large datasets
        if hasattr(self, "_remaining_resources"):
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
            # Reset diff-engine row cache for new cluster
            self._row_cache = RowCache()
            # Reset loading states
            self.is_loading_initial = False
            self.is_loading_more = False
            self.all_data_loaded = False
            self.current_continue_token = None
            self._initial_load_done = False
            # Cluster switch force-stops all watches (stop_all_watches), so any
            # reference this page held is gone with the old stream.  Clear the
            # flag so the scheduled restart below re-acquires a fresh reference
            # for the new cluster instead of short-circuiting on a stale held=True.
            self._holds_watch_ref = False
            # Reset namespace loading flag so namespaces get refreshed for new cluster
            if hasattr(self, "_namespaces_loaded"):
                self._namespaces_loaded = False
                logging.debug(
                    f"Reset namespace loading flag for {self.__class__.__name__}"
                )
            # Clear namespace dropdown to prevent showing stale namespaces
            if hasattr(self, "namespace_combo") and self.namespace_combo:
                self.namespace_combo.blockSignals(True)
                self.namespace_combo.clear()
                self.namespace_combo.addItem("Loading namespaces...")
                self.namespace_combo.setEnabled(False)
                self.namespace_combo.blockSignals(False)
                # Reset to default namespace, not "All Namespaces"
                self.namespace_filter = "default"
                logging.debug(
                    f"Cleared namespace dropdown for {self.__class__.__name__}"
                )
            # Clear selected items
            self.selected_items.clear()
            # Update UI
            self._update_items_count()
            # Trigger namespace reload for visible pages (fixes stuck "Loading namespaces..." issue)
            if (
                self.isVisible()
                and hasattr(self, "namespace_combo")
                and self.namespace_combo
            ):
                QTimer.singleShot(100, self._load_namespaces_async)
                logging.debug(
                    f"Triggered namespace reload for visible page {self.__class__.__name__}"
                )
            # Restart the watch stream for the new cluster.  Without this,
            # showEvent never refires (the page was already visible during
            # the cluster switch) so the watch stays dormant — pod
            # ADDED/MODIFIED/DELETED events from the new cluster never
            # reach the UI, and the user has to click Refresh to see new
            # data.  Deferring slightly lets the new cluster's API service
            # finish initialising and any old watches finish stopping.
            if self.isVisible():
                QTimer.singleShot(200, self._start_resource_watch)
                logging.debug(
                    f"Scheduled watch restart for {self.__class__.__name__} "
                    f"after cluster change"
                )
            logging.info(f"Cleared {self.__class__.__name__} for cluster change")
        except Exception as e:
            logging.error(
                f"Error clearing {self.__class__.__name__} for cluster change: {e}"
            )

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
            # Add only the rows actually present in the current view.  In
            # large-dataset mode the table renders a capped subset of
            # self.resources, so keying off the full list would select
            # invisible rows the user never checked (and that "Delete
            # Selected" must not act on).  Resolve each visible checkbox by
            # name, mirroring the per-row handler so keys stay consistent.
            name_to_resource = {}
            for r in self.resources:
                nm = r.get("name")
                if nm not in name_to_resource:
                    name_to_resource[nm] = r
            for row in range(self.table.rowCount()):
                checkbox_container = self.table.cellWidget(row, 0)
                if not checkbox_container:
                    continue
                checkbox = checkbox_container.findChild(QCheckBox)
                if not checkbox:
                    continue
                resource = name_to_resource.get(checkbox.property("resource_name"))
                if resource:
                    self.selected_items.add(self._build_resource_key(resource))
        logging.debug(
            f"Select all: {state == Qt.CheckState.Checked.value}, Selected items: {len(self.selected_items)}"
        )

    def _validate_resource_name(self, resource_name):
        if not resource_name or not isinstance(resource_name, str):
            return False
        # Skip validation for cluster - scoped resources that don't have namespaces
        cluster_scoped_resources = {
            "nodes",
            "clusterroles",
            "clusterrolebindings",
            "storageclasses",
            "customresourcedefinitions",
            "ingressclasses",
            "persistentvolumes",
            "validatingwebhookconfigurations",
            "mutatingwebhookconfigurations",
            "priorityclasses",
            "runtimeclasses",
        }
        if (
            hasattr(self, "resource_type")
            and self.resource_type in cluster_scoped_resources
        ):
            return True  # Allow all names for cluster - scoped resources
        # For namespaced resources, check for common pod naming patterns that shouldn't appear in other resource types
        # Exclude 'portforwarding' since port forwards legitimately use pod names as identifiers
        if hasattr(self, "resource_type") and self.resource_type not in (
            "pods",
            "portforwarding",
        ):
            # Check for ReplicaSet hash patterns (pod names like "deployment - abc123 - xyz789")
            # Pattern for pod names generated by ReplicaSets / Deployments
            pod_pattern = r"^.+-[a-f0-9]{8,10}-[a-z0-9]{5}$"
            if re.match(pod_pattern, resource_name):
                logging.warning(
                    f"Resource name '{resource_name}' appears to be a pod name but resource type is '{self.resource_type}'"
                )
                return False
        return True

    def delete_selected_resources(self):
        self.deletion_manager.delete_selected_resources(list(self.selected_items))

    def _delete_selected_resources_no_confirm(self):
        # The manager handles either with or without confirm. delegating.
        self.deletion_manager.delete_selected_resources(list(self.selected_items))

    def on_batch_delete_completed(self, success_list, error_list, progress_dialog):
        self.deletion_manager.on_batch_delete_completed(
            success_list, error_list, progress_dialog
        )

    def delete_resource(self, resource_name, resource_namespace):
        self.deletion_manager.delete_resource_single(resource_name, resource_namespace)

    def on_delete_completed(self, success, message, resource_name, resource_namespace):
        self.deletion_manager.on_delete_completed(
            success, message, resource_name, resource_namespace
        )

    def cleanup_timers_and_threads(self):
        if hasattr(self, "deletion_manager"):
            self.deletion_manager.cleanup()
        self._shutting_down = True
        if hasattr(self, "_debounced_updater"):
            self._debounced_updater.cancel_update("search_" + self.__class__.__name__)
            self._debounced_updater.cancel_update("scroll_" + self.__class__.__name__)
        # Stop loading thread (delete threads are owned by deletion_manager)
        if self.loading_thread and self.loading_thread.isRunning():
            if hasattr(self.loading_thread, "cancel"):
                self.loading_thread.cancel()
            self.loading_thread.wait(1000)

    def clear_table(self):
        try:
            if hasattr(self.table, "set_data"):
                # For VirtualScrollTable
                self.table.set_data([])
            elif hasattr(self.table, "setRowCount"):
                # For QTableWidget - clear spans and widgets first
                if hasattr(self.table, "clearSpans"):
                    self.table.clearSpans()
                # Orphan every cell widget synchronously (setParent(None) via
                # _teardown_row_widgets) so none linger as zombie duplicates —
                # bare removeCellWidget() only defers deletion via deleteLater().
                for row in range(self.table.rowCount()):
                    self._teardown_row_widgets(row)
                self.table.setRowCount(0)
            elif hasattr(self.table, "clear"):
                # For other table widgets
                self.table.clear()
            # DO NOT clear self.resources array - this was causing action button failures!
            # The resources array must persist so action buttons can reference resource data
            logging.debug("Table UI cleared successfully - resources data preserved")
            # Reset diff-engine row cache so next update does a full rebuild
            self._row_cache = RowCache()
        except Exception as e:
            logging.error(f"Error clearing table: {e}")

    def _create_table(self, headers, sortable_columns=None):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        # Use custom header for selective header - based sorting
        custom_header = CustomHeader(Qt.Orientation.Horizontal, sortable_columns, table)
        table.setHorizontalHeader(custom_header)
        table.setSortingEnabled(True)
        # Apply enhanced styling with platform overrides
        table.setStyleSheet(BaseTablePageStyles.get_table_style())
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Enable mouse tracking for full-row hover and attach delegate
        table.setMouseTracking(True)
        table.viewport().setMouseTracking(True)
        try:
            delegate = HighPerformanceDelegate(table)
            table.setItemDelegate(delegate)
        except Exception:
            delegate = None

        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Configure appearance with explicit settings
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        # Force consistent selection behavior
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Resizing is now handled by _auto_resize_columns
        table.cellClicked.connect(self.handle_row_click)

        # Wire itemEntered to update hovered row in delegate (QTableWidget emits itemEntered)
        try:
            def _on_item_entered(item):
                try:
                    if delegate and item is not None:
                        delegate.hovered_row = item.row()
                        table.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                        table.viewport().update()
                except Exception:
                    pass

            table.itemEntered.connect(_on_item_entered)
        except Exception:
            pass

        # Install viewport event filter to clear hover on leave
        if delegate:
            class _LeaveFilter(QObject):
                def eventFilter(self, obj, event):
                    if event.type() == QEvent.Type.Leave:
                        delegate.hovered_row = -1
                        table.viewport().setCursor(Qt.CursorShape.ArrowCursor)
                        table.viewport().update()
                    return super().eventFilter(obj, event)

            lf = _LeaveFilter(table)
            table.viewport().installEventFilter(lf)

        return table

    def _auto_resize_columns(self, max_col_widths=None, min_col_widths=None):
        """Resize columns to fit content and viewport without clipping."""
        try:
            if not self.table or not is_valid(self.table):
                return
            
            header = self.table.horizontalHeader()
            col_count = self.table.columnCount()
            if col_count == 0:
                return

            # Phase 0: Enforce interactive mode for data columns
            self._enforce_header_resize_modes(header, col_count)

            # Phase 1: Content-fit with constraints
            col_min_widths = self._compute_column_min_widths(header, col_count, min_col_widths)
            self._apply_content_fit(header, col_count, col_min_widths, max_col_widths)

            # Phase 2: Viewport-fit (remove overflow or fill space)
            viewport_width = self.table.viewport().width()
            if viewport_width <= 0:
                QTimer.singleShot(80, lambda: self._auto_resize_columns(max_col_widths, min_col_widths))
                return

            self._adjust_to_viewport(viewport_width, col_min_widths, max_col_widths)
        except Exception as e:
            logging.debug(f"Auto-resize error: {e}")

    def _enforce_header_resize_modes(self, header: QHeaderView, col_count: int):
        """Ensure columns have appropriate resize modes."""
        for col in range(col_count):
            if header.isSectionHidden(col):
                continue
                
            # Identify columns by their header title (supports both QTableWidget and QTableView)
            title = ""
            if hasattr(self.table, "horizontalHeaderItem"):
                item = self.table.horizontalHeaderItem(col)
                if item:
                    title = item.text().lower().strip()
            else:
                model = self.table.model()
                if model:
                    title = str(model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) or "").lower().strip()
                
            if col == 0:
                continue
            elif col == col_count - 1:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            elif title in ["status", "age"]:
                # Ensure Status and Age columns are strictly fit to content
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)

    def _compute_column_min_widths(self, header: QHeaderView, col_count: int, explicit_mins=None):
        """Calculate minimum widths for each column based on header text."""
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(header.font())
        padding = 20
        min_widths = {}
        
        for col in range(col_count):
            if header.isSectionHidden(col):
                min_widths[col] = 0
                continue
            if explicit_mins and col in explicit_mins:
                min_widths[col] = explicit_mins[col]
                continue
            
            # Supports both QTableWidget and QTableView
            text = ""
            if hasattr(self.table, "horizontalHeaderItem"):
                item = self.table.horizontalHeaderItem(col)
                if item:
                    text = item.text()
            else:
                model = self.table.model()
                if model:
                    text = str(model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) or "")
                    
            width = fm.horizontalAdvance(text) if text else 0
            min_widths[col] = max(40, width + padding)
        return min_widths

    def _apply_content_fit(self, header: QHeaderView, col_count: int, min_widths, max_widths=None):
        """Resize columns to fit their content, within min/max constraints."""
        for col in range(col_count):
            if header.isSectionHidden(col):
                continue
            if col == col_count - 1:
                self.table.setColumnWidth(col, 40)
                continue
                
            if header.sectionResizeMode(col) == QHeaderView.ResizeMode.Interactive:
                self.table.resizeColumnToContents(col)
                current = self.table.columnWidth(col)
                
                # Apply min
                if current < min_widths[col]:
                    self.table.setColumnWidth(col, min_widths[col])
                # Apply max
                if max_widths and col in max_widths and current > max_widths[col]:
                    self.table.setColumnWidth(col, max_widths[col])

    def _adjust_to_viewport(self, viewport_width: int, min_widths, max_widths=None):
        """Adjust column widths to perfectly fill the viewport."""
        header = self.table.horizontalHeader()
        visible_cols = [c for c in range(self.table.columnCount()) if not header.isSectionHidden(c)]
        total_width = sum(self.table.columnWidth(c) for c in visible_cols)
        
        target_width = viewport_width - 2
        overflow = total_width - target_width

        if overflow > 0:
            self._shrink_columns(visible_cols, overflow, min_widths)
        elif overflow < 0:
            self._expand_columns(visible_cols, -overflow, max_widths)

    def _shrink_columns(self, visible_cols: List[int], overflow: int, min_widths):
        """Reduce column widths to fit viewport."""
        header = self.table.horizontalHeader()
        shrinkable = sorted(
            [c for c in visible_cols if header.sectionResizeMode(c) == QHeaderView.ResizeMode.Interactive 
             and self.table.columnWidth(c) > min_widths[c]],
            key=lambda c: self.table.columnWidth(c),
            reverse=True
        )
        
        remaining = overflow
        for col in shrinkable:
            if remaining <= 0: break
            current = self.table.columnWidth(col)
            can_give = current - min_widths[col]
            reduce_by = min(remaining, can_give)
            if reduce_by > 0:
                self.table.setColumnWidth(col, int(current - reduce_by))
                remaining -= reduce_by

    def _expand_columns(self, visible_cols: List[int], extra: int, max_widths=None):
        """Increase column widths to fill empty space."""
        header = self.table.horizontalHeader()
        expandable = sorted(
            [c for c in visible_cols if header.sectionResizeMode(c) == QHeaderView.ResizeMode.Interactive],
            key=lambda c: self.table.columnWidth(c),
            reverse=True
        )
        
        remaining = extra
        for col in expandable:
            if remaining <= 0: break
            current = self.table.columnWidth(col)
            limit = max_widths.get(col, float('inf')) if max_widths else float('inf')
            
            can_grow = limit - current
            if can_grow > 0:
                grow_by = min(remaining, can_grow)
                self.table.setColumnWidth(col, int(current + grow_by))
                remaining -= grow_by

    def _update_table_height(self):
        """Scale table bounds natively by summing physically rendered rows."""
        if not self.table or not hasattr(self, "table") or hasattr(self.table, 'set_data'):
            return
            
        try:
            num_rows = self.table.rowCount()
            rows_height = sum(self.table.rowHeight(r) for r in range(num_rows))
            header_height = self.table.horizontalHeader().height() if hasattr(self.table, 'horizontalHeader') else 42
            if header_height <= 0: header_height = 42
            
            exact_height = rows_height + header_height + 12
            
            if hasattr(self.table, 'horizontalScrollBar') and self.table.horizontalScrollBar().isVisible():
                exact_height += self.table.horizontalScrollBar().height()
                
            clamped_height = min(exact_height, 2000)
            if hasattr(self, 'table_container') and self.table_container:
                self.table_container.setMaximumHeight(clamped_height)
            self.table.setMaximumHeight(clamped_height)
        except Exception as e:
            logging.error(f"Error computing _update_table_height physically: {e}")

    def _ensure_full_width_utilization(self):
        """Legacy shim for backward compatibility with subclasses."""
        self._auto_resize_columns()

    def _configure_table_resizing(self, table, headers):
        """Legacy shim for backward compatibility with subclasses."""
        pass

    def _create_select_all_checkbox(self):
        select_all_checkbox = QCheckBox()
        # Use theme - aware checkbox styling (BaseTablePageStyles already imported at line 27)
        select_all_checkbox.setStyleSheet(BaseTablePageStyles.get_checkbox_style())
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
            lambda: QTimer.singleShot(10, safe_position)
        )

    def _on_select_all_changed(self, state):
        self._handle_select_all(state)

    def handle_row_click(self, row, column):
        # This is a placeholder - implement based on your row click logic
        pass

    def update_table_row(self, row, resource):
        try:
            if hasattr(self.table, "set_data") and hasattr(self, "resources"):
                # For VirtualScrollTable, update the data and refresh
                if 0 <= row < len(self.resources):
                    self.resources[row] = resource
                    self.table.set_data(self.resources)
            elif hasattr(self.table, "item"):
                # For QTableWidget, update individual cells
                self._populate_resource_row(row, resource)
            logging.debug(f"Updated table row {row}")
        except Exception as e:
            logging.error(f"Error updating table row {row}: {e}")

    def _handle_edit_resource(self, resource_name, resource_namespace, resource):
        try:
            # Find the ClusterView that contains the detail manager
            parent = self.parent()
            cluster_view = None
            # Walk up the parent tree to find ClusterView
            while parent:
                if parent.__class__.__name__ == "ClusterView" or hasattr(
                    parent, "detail_manager"
                ):
                    cluster_view = parent
                    break
                parent = parent.parent()
            if cluster_view and hasattr(cluster_view, "detail_manager"):
                # Convert plural resource type to singular for detail manager
                resource_type_singular = singularize_resource_type(self.resource_type)
                # Get raw data from resource if available
                raw_data = (
                    resource.get("raw_data") if isinstance(resource, dict) else None
                )
                # Show the detail page first
                cluster_view.detail_manager.show_detail(
                    resource_type_singular,
                    resource_name,
                    resource_namespace,
                    raw_data=raw_data,
                )
                # After showing detail page, trigger edit mode
                # We need to wait a bit for the detail page to load completely
                QTimer.singleShot(500, lambda: self._trigger_edit_mode(cluster_view))
                logging.info(
                    f"Opening {self.resource_type}/{resource_name} in edit mode"
                )
            else:
                # Fallback: show error if detail manager not found

                QMessageBox.information(
                    self,
                    "Edit Resource",
                    f"Cannot edit {self.resource_type}/{resource_name}: Detail panel not available",
                )
                logging.warning(f"Detail manager not found for editing {resource_name}")
        except Exception as e:
            logging.error(f"Failed to open {resource_name} for editing: {e}")

            QMessageBox.critical(
                self, "Error", f"Failed to open {resource_name} for editing: {str(e)}"
            )

    def _trigger_edit_mode(self, cluster_view):
        try:
            if (
                hasattr(cluster_view, "detail_manager")
                and cluster_view.detail_manager._detail_page
            ):
                detail_page = cluster_view.detail_manager._detail_page
                # Find the YAML section and trigger edit mode
                if hasattr(detail_page, "yaml_section"):
                    yaml_section = detail_page.yaml_section
                    if (
                        hasattr(yaml_section, "toggle_yaml_edit_mode")
                        and yaml_section.yaml_editor.isReadOnly()
                    ):
                        yaml_section.toggle_yaml_edit_mode()
                        logging.info("Successfully activated edit mode in YAML section")
                    else:
                        logging.warning(
                            "YAML section is not in read - only mode or toggle method not found"
                        )
                else:
                    logging.warning("YAML section not found in detail page")
            else:
                logging.warning("Detail page not found or not properly initialized")
        except Exception as e:
            logging.error(f"Error triggering edit mode: {e}")

    def _create_action_button(self, row, resource_name=None, resource_namespace=None):
        button = QToolButton()
        # Use pre - loaded theme - aware icon from parent class (BaseTablePage)
        try:
            if hasattr(self, "action_button_icon"):
                button.setIcon(self.action_button_icon)
                button.setIconSize(QSize(16, 16))
        except Exception as e:
            logging.warning(f"Error setting action button icon: {e}")
        # Remove text and change to icon - only style
        button.setText("")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setFixedWidth(30)
        try:
            button.setStyleSheet(
                AppStyles.HOME_ACTION_BUTTON_STYLE
                + """
                QToolButton::menu-indicator { image: none; width: 0px; }
                """
            )
        except (ImportError, AttributeError) as e:
            logging.debug(f"Could not load AppStyles for button: {e}")
            # Use theme-aware fallback styling
            button.setStyleSheet(
                BaseResourcePageStyles.get_action_button_fallback_style()
            )
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
        # Immutable dispatch key captured at button-creation time.  For
        # model/view pages this is the resource UID, so the action targets the
        # correct resource even after watch updates reorder the source rows.
        dispatch_key = self._action_dispatch_key(row)
        # Connect signals to change row appearance when menu opens / closes
        try:
            menu.aboutToShow.connect(lambda: self._on_menu_show(row))
            menu.aboutToHide.connect(lambda: self._highlight_active_row(row, False))
        except Exception as e:
            logging.warning(f"Error connecting menu signals: {e}")
        # Define actions based on resource type - matching old pattern
        actions = []
        # Resource - specific actions based on resource type
        if hasattr(self, "resource_type") and self.resource_type == "pods":
            actions.extend(
                [
                    {
                        "text": "View Logs",
                        "icon": "Icons/logs.png",
                        "dangerous": False,
                    },
                    {"text": "SSH", "icon": "Icons/terminal.png", "dangerous": False},
                ]
            )
            # Check if pod has ports for port forwarding
            resolved = self._get_action_resource(dispatch_key)
            if resolved and self._has_pod_ports(resolved[0]):
                actions.append(
                    {
                        "text": "Port Forward",
                        "icon": "Icons/network.png",
                        "dangerous": False,
                    }
                )
        elif hasattr(self, "resource_type") and self.resource_type == "services":
            # Check if service has ports for port forwarding
            resolved = self._get_action_resource(dispatch_key)
            if resolved and self._has_service_ports(resolved[0]):
                actions.append(
                    {
                        "text": "Port Forward",
                        "icon": "Icons/network.png",
                        "dangerous": False,
                    }
                )
        elif hasattr(self, "resource_type") and self.resource_type == "nodes":
            # Node - specific actions
            actions.append(
                {
                    "text": "View Metrics",
                    "icon": "Icons/chart.png",
                    "dangerous": False,
                }
            )
        elif hasattr(self, "resource_type") and self.resource_type == "deployments":
            # Deployment - specific mutations.  No "icon" key: no scale.png /
            # restart.png assets ship today (the loader would just log and
            # fall through to text-only).  Add the key back when assets exist.
            actions.extend(
                [
                    {"text": "Scale", "dangerous": False},
                    {"text": "Restart Rollout", "dangerous": False},
                ]
            )
        elif hasattr(self, "resource_type") and self.resource_type == "statefulsets":
            # Fork B: StatefulSets get both Scale (via /scale subresource)
            # and Restart Rollout (via spec.template.metadata.annotations).
            # No icon key — same rationale as deployments branch above.
            actions.extend(
                [
                    {"text": "Scale", "dangerous": False},
                    {"text": "Restart Rollout", "dangerous": False},
                ]
            )
        elif hasattr(self, "resource_type") and self.resource_type == "daemonsets":
            # Fork B: DaemonSets get Restart Rollout ONLY — they have no
            # replicas concept (one pod per node), so a Scale action would
            # immediately be rejected by the API.
            actions.append(
                {"text": "Restart Rollout", "dangerous": False},
            )
        # Standard actions for all resources
        actions.extend(
            [
                {"text": "Edit", "icon": "Icons/edit.png", "dangerous": False},
                {"text": "Delete", "icon": "Icons/delete.png", "dangerous": True},
            ]
        )
        # Bind each action to the immutable dispatch key (UID for model/view
        # pages, row index for QTableWidget pages) captured above.
        for action_info in actions:
            try:
                action = menu.addAction(action_info["text"])
                if "icon" in action_info:
                    try:
                        action.setIcon(QIcon(resource_path(action_info["icon"])))
                    except (OSError, FileNotFoundError) as e:
                        logging.debug(
                            f"Icon loading failed for {action_info['icon']}: {e}"
                        )
                    except Exception as e:
                        logging.error(
                            f"Unexpected error loading icon {action_info['icon']}: {e}"
                        )
                if action_info.get("dangerous", False):
                    action.setProperty("dangerous", True)
                action.triggered.connect(
                    partial(self._handle_action, action_info["text"], dispatch_key)
                )
                logging.debug(
                    f"Action button: Connected '{action_info['text']}' (key={dispatch_key})"
                )
            except Exception as e:
                logging.error(f"Error adding action {action_info['text']}: {e}")
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
            logging.error(f"Unexpected error checking port forward availability: {e}")
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
            logging.debug(f"Could not check pod port forward availability: {e}")
            return False
        except Exception as e:
            logging.error(
                f"Unexpected error checking pod port forward availability: {e}"
            )
            return False

    def _create_action_container(self, row, action_button):
        container = QWidget()
        container.setObjectName(
            "actionContainer"
        )  # Required for fallback style selector
        try:
            container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
        except (ImportError, AttributeError) as e:
            logging.debug(f"Could not load ACTION_CONTAINER_STYLE: {e}")
            # Use theme-aware fallback styling
            container.setStyleSheet(
                BaseResourcePageStyles.get_action_container_fallback_style()
            )
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(action_button)
        return container

    def _on_menu_show(self, row):
        logging.debug(f"Action button menu opening for row {row}")
        self._highlight_active_row(row, True)

    def _highlight_active_row(self, row, highlight):
        """Highlight row when action menu is open using theme-aware colors"""
        try:
            if hasattr(self, "table") and self.table and row < self.table.rowCount():
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        if highlight:
                            item.setBackground(
                                QColor(BaseResourcePageStyles.get_hover_bg_color())
                            )
                        else:
                            item.setBackground(
                                QColor(BaseResourcePageStyles.get_transparent_color())
                            )
        except Exception as e:
            logging.debug(f"Error highlighting row {row}: {e}")

    def _action_dispatch_key(self, row):
        """Value bound into an action button's click closure to identify its
        target resource.

        QTableWidget pages key by the row index (this default).  Subclasses
        that reorder rows on watch updates may override this to bind the
        resource's immutable UID, captured at button-creation time, so
        dispatch survives watch-driven row reordering.
        """
        return row

    def _get_action_resource(self, target):
        """Resolve an action-dispatch key to (resource, name, namespace).

        Base implementation treats ``target`` as a row index into
        self.resources, with a table-read fallback for QTableWidget pages.
        Returns None when no resource can be resolved.
        """
        row = target
        if (
            not hasattr(self, "resources")
            or not self.resources
            or not isinstance(row, int)
            or row >= len(self.resources)
        ):
            if (
                isinstance(row, int)
                and hasattr(self, "table")
                and self.table
                and hasattr(self.table, "rowCount")
                and hasattr(self.table, "item")
                and row < self.table.rowCount()
            ):
                # Extract resource name from table (typically column 1)
                resource_name = ""
                resource_namespace = ""
                if self.table.item(row, 1):  # Name column
                    resource_name = self.table.item(row, 1).text()
                # Find the namespace column by checking headers for "namespace"
                for col in range(2, self.table.columnCount()):
                    header_item = self.table.horizontalHeaderItem(col)
                    if header_item:
                        header_text = header_item.text().lower().strip()
                        if "namespace" in header_text:
                            cell_item = self.table.item(row, col)
                            if cell_item and cell_item.text():
                                resource_namespace = cell_item.text()
                                break
                if not resource_namespace and self.namespace_filter:
                    resource_namespace = self.namespace_filter
                resource = {"name": resource_name, "namespace": resource_namespace}
                return resource, resource_name, resource_namespace
            return None
        resource = self.resources[row]
        return resource, resource.get("name", ""), resource.get("namespace", "")

    # Removed old _handle_action_with_resource method - replaced with OLD WORKING PATTERN
    def _handle_action(self, action, target):
        logging.info(f"BaseResourcePage: Action '{action}' clicked (target={target})")
        resolved = self._get_action_resource(target)
        if resolved is None:
            logging.warning(
                f"BaseResourcePage: No resource resolved for action '{action}' (target={target})"
            )
            return
        resource, resource_name, resource_namespace = resolved
        logging.info(
            f"BaseResourcePage: Processing action '{action}' for {resource_name}"
            + (f" in {resource_namespace}" if resource_namespace else "")
        )
        # Handle actions with fresh resource data - matching old working pattern
        if action == "View Logs":
            if hasattr(self, "resource_type") and self.resource_type == "pods":
                self._handle_view_logs(resource_name, resource_namespace, resource)
            else:
                QMessageBox.warning(
                    self, "Logs Error", "Logs are only available for pod resources."
                )
        elif action == "SSH":
            if hasattr(self, "resource_type") and self.resource_type == "pods":
                self._handle_ssh_into_pod(resource_name, resource_namespace, resource)
            else:
                QMessageBox.warning(
                    self, "SSH Error", "SSH is only available for pod resources."
                )
        elif action == "Port Forward":
            if hasattr(self, "resource_type") and self.resource_type in [
                "pods",
                "services",
            ]:
                self._handle_port_forward(resource_name, resource_namespace, resource)
            else:
                QMessageBox.warning(
                    self,
                    "Port Forward Error",
                    "Port forwarding is only available for pods and services.",
                )
        elif action == "Edit":
            try:
                logging.info(f"Starting edit for resource: {resource_name}")
                self._handle_edit_resource(resource_name, resource_namespace, resource)
            except Exception as e:
                logging.error(f"Error in edit action: {e}")

                QMessageBox.critical(
                    self, "Error", f"Failed to edit {resource_name}: {str(e)}"
                )
        elif action == "Delete":
            try:
                logging.info(f"Starting delete for resource: {resource_name}")
                self.delete_resource(resource_name, resource_namespace)
            except Exception as e:
                logging.error(f"Error in delete action: {e}")

                QMessageBox.critical(
                    self, "Error", f"Failed to delete {resource_name}: {str(e)}"
                )
        elif action == "View Metrics":
            # Handle node - specific View Metrics action
            if hasattr(self, "select_node_for_graphs"):
                self.select_node_for_graphs(target)
            else:
                logging.warning(
                    f"View Metrics action not supported for resource type: {self.resource_type}"
                )
        elif action in ("Scale", "Restart Rollout"):
            # Page-owned actions. DeploymentsPage / StatefulSetsPage /
            # DaemonSetsPage override _handle_action and apply workload-
            # specific safeguards (HPA pre-scan, OnDelete warning, in-flight
            # de-dup). Reaching the base dispatcher means a page exposed the
            # menu item without the override — log loudly and do nothing,
            # rather than scale/restart through an unguarded fallback.
            logging.error(
                f"BaseResourcePage: '{action}' reached the base dispatcher for "
                f"resource_type={getattr(self, 'resource_type', '?')}; the page "
                f"must override _handle_action to handle it safely."
            )
        else:
            logging.warning(f"BaseResourcePage: Unknown action: {action}")

    def _handle_port_forward(self, resource_name, namespace, resource):
        QMessageBox.information(
            self,
            "Port Forward",
            f"Port forwarding for {resource_name} - functionality implemented by specific pages",
        )
        logging.info(
            f"Port forward requested for {resource_name} - using placeholder implementation"
        )

    def _handle_view_logs(self, pod_name, namespace, resource):
        try:
            # Find the ClusterView that contains the terminal panel
            parent = self.parent()
            cluster_view = None
            # Walk up the parent tree to find ClusterView
            while parent:
                if parent.__class__.__name__ == "ClusterView" or hasattr(
                    parent, "terminal_panel"
                ):
                    cluster_view = parent
                    break
                parent = parent.parent()
            if cluster_view and hasattr(cluster_view, "terminal_panel"):
                # Create a logs tab in the terminal panel
                cluster_view.terminal_panel.create_enhanced_logs_tab(
                    pod_name, namespace
                )
                # Show the terminal panel if it's hidden
                if not cluster_view.terminal_panel.is_visible:
                    if hasattr(cluster_view, "toggle_terminal"):
                        cluster_view.toggle_terminal()
                    elif hasattr(cluster_view.terminal_panel, "show_terminal"):
                        cluster_view.terminal_panel.show_terminal()
                logging.info(
                    f"Created logs tab for pod: {pod_name} in namespace: {namespace}"
                )
            else:
                # Fallback: show error if terminal panel not found

                QMessageBox.information(
                    self,
                    "Logs",
                    f"Opening logs for pod: {pod_name} in namespace: {namespace}\n\n"
                    f"Terminal panel will show logs. Use kubectl logs {pod_name} -n {namespace} if needed.",
                )
                logging.warning("Terminal panel not found for logs tab creation")
        except Exception as e:
            logging.error(f"Failed to create logs tab for pod {pod_name}: {e}")

            QMessageBox.critical(
                self, "Error", f"Failed to open logs for pod {pod_name}: {str(e)}"
            )

    def _handle_ssh_into_pod(self, pod_name, namespace, resource):
        try:
            # Find the ClusterView that contains the terminal panel
            parent = self.parent()
            cluster_view = None
            # Walk up the parent tree to find ClusterView
            while parent:
                if parent.__class__.__name__ == "ClusterView" or hasattr(
                    parent, "terminal_panel"
                ):
                    cluster_view = parent
                    break
                parent = parent.parent()
            if cluster_view and hasattr(cluster_view, "terminal_panel"):
                # Create an SSH tab in the terminal panel
                cluster_view.terminal_panel.create_ssh_tab(pod_name, namespace)
                # Show the terminal panel if it's hidden
                if not cluster_view.terminal_panel.is_visible:
                    if hasattr(cluster_view, "toggle_terminal"):
                        cluster_view.toggle_terminal()
                    elif hasattr(cluster_view.terminal_panel, "show_terminal"):
                        cluster_view.terminal_panel.show_terminal()
                logging.info(
                    f"Created SSH tab for pod: {pod_name} in namespace: {namespace}"
                )
            else:
                # Fallback: show error if terminal panel not found

                QMessageBox.information(
                    self,
                    "SSH",
                    f"Opening SSH for pod: {pod_name} in namespace: {namespace}\n\n"
                    f"Terminal panel will show SSH session. Use kubectl exec -it {pod_name} -n {namespace} -- /bin/bash if needed.",
                )
                logging.warning("Terminal panel not found for SSH tab creation")
        except Exception as e:
            logging.error(f"Failed to create SSH tab for pod {pod_name}: {e}")

            QMessageBox.critical(
                self, "Error", f"Failed to open SSH for pod {pod_name}: {str(e)}"
            )

    def _create_checkbox_container(self, row, resource_name):
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        container.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        checkbox = QCheckBox()
        checkbox.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        checkbox.setProperty("row", row)
        checkbox.setProperty("resource_name", resource_name)
        checkbox.stateChanged.connect(self._on_row_checkbox_changed)
        # Apply theme-aware checkbox styling
        checkbox.setStyleSheet(BaseTablePageStyles.get_checkbox_style())
        layout.addWidget(checkbox)
        return container

    def _on_row_checkbox_changed(self, state):
        try:
            checkbox = self.sender()
            resource_name = checkbox.property("resource_name")
            # Find the resource by name instead of relying only on row index
            resource = None
            for r in self.resources:
                if r.get("name") == resource_name:
                    resource = r
                    break
            if resource:
                # Identity key shared with select-all and selection restore.
                resource_key = self._build_resource_key(resource)
                if state == Qt.CheckState.Checked.value:
                    self.selected_items.add(resource_key)
                    logging.debug(f"Selected resource: {resource_key}")
                else:
                    self.selected_items.discard(resource_key)
                    logging.debug(f"Deselected resource: {resource_key}")
                # Update select - all checkbox state
                self._update_select_all_state()
            else:
                logging.warning(f"Resource not found for checkbox: {resource_name}")
        except Exception as e:
            logging.error(f"Error handling checkbox change: {e}")

    def _update_select_all_state(self):
        try:
            if (
                hasattr(self, "table")
                and self.table
                and hasattr(self, "select_all_checkbox")
            ):
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

    def _build_resource_key(self, resource):
        """Build the (name, namespace) identity tuple used in selected_items.

        Centralizes the keying shared by the per-row checkbox handler, the
        select-all handler, and selection restoration after rebuilds.  A
        missing or empty namespace normalizes to "" (cluster-scoped).
        """
        name = resource.get("name", "")
        namespace = resource.get("namespace", "") or ""
        return (name, namespace)

    def _restore_row_selection_state(self):
        """Re-apply preserved checkbox selections after a full table rebuild.

        The legacy watch-rebuild path (_apply_watch_update_legacy) destroys
        and recreates every row widget, so the per-row checkboxes are created
        unchecked.  Without this step the user's selection would silently
        vanish every time the cluster data mutates.

        Two things happen here:
          1. PRUNE  — selected_items is intersected with the keys of the
                      resources currently displayed, dropping any selection
                      whose resource was deleted in this update.  This keeps
                      the select-all math and the bulk-delete target accurate.
          2. RESTORE — every rebuilt row whose resource is still selected has
                      its checkbox re-checked (signals blocked so the per-row
                      handler does not re-fire).

        Matching uses the checkbox's own 'resource_name' property, so it stays
        correct regardless of the table's current sort order.
        """
        try:
            if not self.table:
                return
            # Map displayed resource names → identity keys (first occurrence
            # wins, mirroring _on_row_checkbox_changed's name-based lookup).
            name_to_key = {}
            for r in self.resources:
                nm = r.get("name")
                if nm not in name_to_key:
                    name_to_key[nm] = self._build_resource_key(r)

            # PRUNE — drop selections for resources that vanished this update.
            self.selected_items &= set(name_to_key.values())

            # RESTORE — re-check the checkbox on every still-selected row.
            for row in range(self.table.rowCount()):
                container = self.table.cellWidget(row, 0)
                if not container:
                    continue
                checkbox = container.findChild(QCheckBox)
                if not checkbox:
                    continue
                key = name_to_key.get(checkbox.property("resource_name"))
                should_check = key is not None and key in self.selected_items
                if checkbox.isChecked() != should_check:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(should_check)
                    checkbox.blockSignals(False)

            # Sync the header select-all checkbox to the restored count.
            self._update_select_all_state()
        except Exception as e:
            logging.debug(f"Selection restore after rebuild failed: {e}")

    def __del__(self):
        try:
            if hasattr(self, "_shutting_down") and not self._shutting_down:
                logging.debug("BaseResourcePage destructor called, performing cleanup")
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
        if hasattr(self, "title_label") and self.title_label:
            self.title_label.setStyleSheet(
                f"font-size: 20px; font-weight: bold; color: {theme.colors.TEXT_LIGHT};"
            )
        # Update count label with theme-aware color
        if hasattr(self, "items_count") and self.items_count:
            self.items_count.setStyleSheet(
                f"color: {theme.colors.TEXT_SUBTLE}; font-size: 12px; margin-left: 8px;"
            )
        # Refresh search label if it exists
        if hasattr(self, "search_label") and self.search_label:
            self.search_label.setStyleSheet(
                BaseResourcePageStyles.get_search_label_style()
            )
        # Refresh search bar if it exists
        if hasattr(self, "search_bar") and self.search_bar:
            self.search_bar.setStyleSheet(
                BaseResourcePageStyles.get_search_input_style()
            )
        # Refresh namespace label if it exists
        if hasattr(self, "namespace_label") and self.namespace_label:
            self.namespace_label.setStyleSheet(
                BaseResourcePageStyles.get_namespace_label_style()
            )
        # Refresh namespace combo if it exists
        if hasattr(self, "namespace_combo") and self.namespace_combo:
            self.namespace_combo.setStyleSheet(
                BaseResourcePageStyles.get_namespace_combo_style()
            )
        # Refresh delete button if it exists
        if hasattr(self, "_delete_btn") and self._delete_btn:
            self._delete_btn.setStyleSheet(
                BaseResourcePageStyles.get_delete_button_style()
            )
        # Refresh refresh button if it exists
        if hasattr(self, "refresh_btn") and self.refresh_btn:
            self.refresh_btn.setStyleSheet(
                BaseResourcePageStyles.get_refresh_button_style()
            )
        logging.debug(f"BaseResourcePage: Theme refresh complete for {theme_name}")

    def cleanup(self):
        try:
            self._shutting_down = True
            # Stop all timers
            if hasattr(self, "_debounced_updater"):
                self._debounced_updater.cancel_update(
                    "search_" + self.__class__.__name__
                )
                self._debounced_updater.cancel_update(
                    "scroll_" + self.__class__.__name__
                )
            if hasattr(self, "_watch_render_timer"):
                if is_valid(self._watch_render_timer) and self._watch_render_timer.isActive():
                    self._watch_render_timer.stop()
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
    "ResourceDeleterThread",
    "BatchResourceDeleterThread",
    "VirtualScrollTable",
    "BaseResourcePage",
    "create_base_resource_page",
    "BATCH_SIZE",
    "SCROLL_DEBOUNCE_MS",
    "SEARCH_DEBOUNCE_MS",
]
