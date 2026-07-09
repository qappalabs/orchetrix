"""
Resource Page Mixins - Extracted logic from BaseResourcePage for better modularity.
"""

import datetime
import gc
import logging
import time
from typing import List, Dict, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget
from PyQt6 import sip

from UI.LoadingSpinner import create_loading_overlay
from UI.ThemeManager import get_theme_manager
from Utils.unified_resource_loader import get_unified_resource_loader, LoadResult


class ResourceNamespaceMixin:
    """Mixin for handling Kubernetes namespace selection and loading."""
    
    def _load_namespaces_async(self):
        """Asynchronously load namespaces using the unified loader."""
        try:
            unified_loader = get_unified_resource_loader()
            # Connect signals if not already connected
            if not hasattr(self, "_namespace_signals_connected"):
                unified_loader.loading_completed.connect(self._on_namespaces_loaded_unified)
                unified_loader.loading_error.connect(self._on_namespace_error_unified)
                self._namespace_signals_connected = True
            
            self._namespace_operation_id = unified_loader.load_resources_async("namespaces")
        except Exception as e:
            logging.error(f"Failed to start namespace loading: {e}")
            self._on_namespaces_loaded(["default", "kube-system", "kube-public"])

    def _on_namespaces_loaded_unified(self, resource_type: str, result: LoadResult):
        """Callback for successful namespace loading."""
        if resource_type != "namespaces" or getattr(self, "_was_hidden", False):
            return
            
        if result.success:
            namespaces = [item.get("name", "") for item in result.items if item.get("name")]
            important = ["default", "kube-system", "kube-public", "kube-node-lease"]
            other = sorted([ns for ns in namespaces if ns not in important])
            sorted_namespaces = [ns for ns in important if ns in namespaces] + other
            self._on_namespaces_loaded(sorted_namespaces)
        else:
            self._on_namespace_error_unified("namespaces", result.error_message or "Failed to load")

    def _on_namespace_error_unified(self, resource_type: str, error_message: str):
        """Callback for failed namespace loading."""
        if resource_type != "namespaces" or getattr(self, "_was_hidden", False):
            return
        logging.error(f"Namespace loading error: {error_message}")
        self._on_namespaces_loaded(["default", "kube-system", "kube-public"])

    def _on_namespaces_loaded(self, namespaces):
        """Update the namespace combo box with loaded namespaces."""
        if not hasattr(self, 'namespace_combo') or not self.namespace_combo:
            self.namespace_filter = "All Namespaces"
            return

        try:
            self.namespace_combo.blockSignals(True)
            self.namespace_combo.clear()
            self.namespace_combo.addItem("All Namespaces")
            for ns in namespaces:
                if ns: self.namespace_combo.addItem(ns)

            # Set current selection
            current_filter = getattr(self, "namespace_filter", "All Namespaces")
            index = self.namespace_combo.findText(current_filter)
            if index < 0 and current_filter == "default":
                index = self.namespace_combo.findText("default")
            
            self.namespace_combo.setCurrentIndex(max(0, index))
            self.namespace_filter = self.namespace_combo.currentText()
            
            self.namespace_combo.blockSignals(False)
            self.namespace_combo.setEnabled(True)
        except Exception as e:
            logging.error(f"Error updating namespace dropdown: {e}")
            if hasattr(self, 'namespace_combo'):
                self.namespace_combo.blockSignals(False)
                self.namespace_combo.setEnabled(True)

    def refresh_namespaces(self):
        """Trigger a refresh of namespaces."""
        self._namespaces_loaded = False
        self._load_namespaces_async()

    def _on_namespace_changed(self, namespace):
        """Handle namespace selection change."""
        if namespace == "Loading namespaces...":
            return
            
        old_ns = getattr(self, "namespace_filter", "default")
        if old_ns == namespace:
            return
            
        logging.info(f"Namespace changed: {old_ns} -> {namespace}")

        # Release the watch bound to the previous namespace before switching so
        # the loader stops streaming stale data for the namespace we are leaving.
        if hasattr(self, '_stop_resource_watch'):
            self._stop_resource_watch()

        self.namespace_filter = namespace

        if hasattr(self, 'current_continue_token'):
            self.current_continue_token = None
        if hasattr(self, 'all_data_loaded'):
            self.all_data_loaded = False

        # Bind a fresh watch to the newly selected namespace scope.
        if hasattr(self, '_start_resource_watch'):
            self._start_resource_watch()

        if hasattr(self, 'force_load_data'):
            self.force_load_data()


class ResourceLoadingIndicatorMixin:
    """Mixin for handling loading spinner/overlay."""
    
    def _create_loading_overlay(self):
        if not hasattr(self, '_loading_overlay') or not self._loading_overlay:
            spinner_type = getattr(self, '_spinner_type', "circular")
            self._loading_overlay = create_loading_overlay(self, "Loading data...", spinner_type)
            self._loading_overlay.setGeometry(self.rect())

    def _resize_loading_overlay(self):
        if hasattr(self, '_loading_overlay') and self._loading_overlay:
            self._loading_overlay.setGeometry(self.rect())

    def show_loading_indicator(self, message="Loading data..."):
        self._create_loading_overlay()
        self._resize_loading_overlay()
        self._loading_overlay.show_loading(message)
        self._is_showing_loading = True

    def hide_loading_indicator(self):
        if hasattr(self, '_is_showing_loading') and self._is_showing_loading and self._loading_overlay:
            self._loading_overlay.hide_loading()
            self._is_showing_loading = False

    def update_loading_message(self, message):
        if hasattr(self, '_is_showing_loading') and self._is_showing_loading and self._loading_overlay:
            self._loading_overlay.set_message(message)


class ResourceUtilityMixin:
    """Utility methods for resource pages."""
    
    def _format_age(self, timestamp):
        """Format a Kubernetes timestamp into a human-readable age string."""
        if not timestamp:
            return "Unknown"
        try:
            if isinstance(timestamp, str):
                created_time = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if created_time.tzinfo is None:
                    created_time = created_time.replace(tzinfo=datetime.timezone.utc)
            else:
                created_time = timestamp.replace(tzinfo=datetime.timezone.utc)
            
            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - created_time
            
            if diff.days > 0: return f"{diff.days}d"
            hours, rem = divmod(diff.seconds, 3600)
            if hours > 0: return f"{hours}h"
            mins, _ = divmod(rem, 60)
            return f"{mins}m"
        except Exception:
            return "Unknown"

    def _manage_memory_usage(self):
        """Trigger garbage collection and optional dataset trimming."""
        try:
            if getattr(self, '_large_dataset_mode', False) and len(self.resources) > 2000:
                # Basic trimming logic if needed, but primarily force GC
                pass
            gc.collect()
        except Exception as e:
            logging.error(f"Memory management error: {e}")


class ResourceLoadingMixin:
    """Mixin for handling Kubernetes resource loading and pagination."""
    
    def _start_loading_thread(self):
        """Start the unified resource loading thread."""
        unified_loader = get_unified_resource_loader()
        
        # Connect signals if not already connected
        if not hasattr(self, "_signals_connected") or not self._signals_connected:
            unified_loader.loading_completed.connect(self._on_unified_resources_loaded)
            unified_loader.loading_error.connect(self._on_unified_loading_error)
            self._signals_connected = True
            
        # Determine namespace
        ns_filter = getattr(self, "namespace_filter", "All Namespaces")
        namespace = None if ns_filter == "All Namespaces" else ns_filter
        
        # Start loading
        self._current_operation_id = unified_loader.load_resources_async(
            resource_type=self.resource_type, 
            namespace=namespace
        )
        logging.debug(f"Started loading {self.resource_type} (op: {self._current_operation_id})")

    def _on_unified_resources_loaded(self, resource_type: str, result: LoadResult):
        """Callback for successful resource loading."""
        if resource_type != self.resource_type or getattr(self, "_was_hidden", False):
            return
            
        try:
            if not result.success:
                self._on_unified_loading_error(resource_type, result.error_message or "Unknown error")
                return

            resources = result.items or []
            self._total_item_count = len(resources)
            
            # Use threshold from base class or default to 200
            threshold = getattr(self, 'LARGE_DATASET_THRESHOLD', 200)
            self._large_dataset_mode = self._total_item_count > threshold
            
            if self._large_dataset_mode:
                # Paginate in memory for performance
                limit = getattr(self, 'MAX_ITEMS_IN_MEMORY', 2000)
                self.resources = resources[:limit]
                self._remaining_resources = resources[limit:]
                self.all_data_loaded = False
            else:
                self.resources = resources
                self._remaining_resources = []
                self.all_data_loaded = True

            # Update UI
            if hasattr(self, '_display_resources'):
                self._display_resources(self.resources)
            
            if hasattr(self, 'items_count'):
                self.items_count.setText(f"{self._total_item_count} items")
                
            self.is_loading_initial = False
            self.is_loading_more = False
            self._initial_load_done = True
            
            if hasattr(self, 'hide_loading_indicator'):
                self.hide_loading_indicator()
                
            if hasattr(self, 'all_items_loaded_signal'):
                self.all_items_loaded_signal.emit()

        except Exception as e:
            logging.error(f"Error processing loaded resources: {e}")
            self._on_unified_loading_error(resource_type, str(e))

    def _on_unified_loading_error(self, resource_type: str, error_message: str):
        """Callback for resource loading errors."""
        if resource_type != self.resource_type or getattr(self, "_was_hidden", False):
            return
            
        self.is_loading_initial = False
        self.is_loading_more = False
        
        if hasattr(self, 'hide_loading_indicator'):
            self.hide_loading_indicator()
            
        if hasattr(self, '_show_error_message'):
            self._show_error_message(error_message)

    def _load_more_data_batch(self):
        """Load next batch of resources from memory (large dataset mode)."""
        if not getattr(self, '_large_dataset_mode', False) or not self._remaining_resources:
            return
            
        try:
            batch_size = 100 # Default batch size
            next_batch = self._remaining_resources[:batch_size]
            self._remaining_resources = self._remaining_resources[batch_size:]
            
            self.resources.extend(next_batch)
            if not self._remaining_resources:
                self.all_data_loaded = True

            if hasattr(self, '_manage_memory_usage'):
                self._manage_memory_usage()
                
            if hasattr(self, '_display_resources'):
                self._display_resources(self.resources)
                
            if hasattr(self, '_update_items_count'):
                self._update_items_count()
        except Exception as e:
            logging.error(f"Error loading more data batch: {e}")

    def _handle_scroll(self, value):
        """Handle vertical scroll changes to trigger lazy loading."""
        if not hasattr(self, '_debounced_updater'):
            return
            
        # Use SCROLL_DEBOUNCE_MS from base class or default to 500
        delay = getattr(self, 'SCROLL_DEBOUNCE_MS', 500)
        
        self._debounced_updater.schedule_update(
            "scroll_" + self.__class__.__name__,
            self._handle_scroll_debounced,
            delay_ms=delay
        )

    def _handle_scroll_debounced(self):
        """Debounced scroll handler to check if we are near the bottom."""
        # Safety check for UI lifecycle
        if not hasattr(self, 'table') or not self.table or sip.isdeleted(self.table):
            return
            
        if getattr(self, 'is_loading_more', False):
            return
            
        scrollbar = self.table.verticalScrollBar()
        # Trigger when within 10 pixels of the bottom
        if scrollbar.value() >= scrollbar.maximum() - 10:
            if getattr(self, '_large_dataset_mode', False) and getattr(self, '_remaining_resources', []):
                self._load_more_data_batch()
