"""
Optimized Detail Manager for ClusterView that handles showing and managing resource detail pages.
Improved version with better performance, error handling, and code organization.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from typing import Optional, Dict, Any

from .DetailPageComponent import DetailPageComponent
from Utils.resource_utils import singularize_resource_type
from Utils.kubernetes_client import get_kubernetes_client
from Utils.qt_utils import is_valid

import logging

class DetailManager(QObject):
    """
    Manages the detail page component for ClusterView with optimized performance.
    Handles showing and hiding resource details with improved caching and state management.
    """

    # Signals
    resource_updated = pyqtSignal(str, str, str)  # Resource type, name, namespace
    refresh_main_page = pyqtSignal(str, str, str)  # resource_type, resource_name, namespace

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.parent_window = parent

        # Initialize core attributes
        self._detail_page: Optional[DetailPageComponent] = None  # Fixed: Changed DetailPage to DetailPageComponent
        self._current_resource: Dict[str, Optional[str]] = {
            'type': None,
            'name': None,
            'namespace': None
        }

        # Performance optimization: Pre-calculate sizes
        self._cached_height: Optional[int] = None

        # Lazy initialization flag
        self._is_initialized = False

        # Phase 4: subscription state for the global watch firehose.
        # Connected on show_detail (UniqueConnection prevents duplicate
        # bindings during rapid re-show), disconnected on hide_detail.
        self._watch_subscribed: bool = False
        self._watch_client = None
        # Trailing-edge debounce timer so 50 burst events for one scale
        # operation collapse into a single refresh.  300ms is the same
        # window the table-side throttle uses for visual consistency.
        self._refresh_debounce_timer: QTimer = QTimer(self)
        self._refresh_debounce_timer.setSingleShot(True)
        self._refresh_debounce_timer.setInterval(300)
        self._refresh_debounce_timer.timeout.connect(self._flush_debounced_refresh)
        # The latest watch payload (set by _on_watch_event, consumed by
        # _flush_debounced_refresh).  None means "no pending update".
        self._pending_watch_payload: Optional[Dict[str, Any]] = None

    def _ensure_detail_page(self) -> DetailPageComponent:
        """Lazy initialization of detail page for better startup performance"""
        if self._detail_page is None:
            self._detail_page = DetailPageComponent(self.parent_window)
            self._detail_page.resource_updated_signal.connect(self._handle_resource_updated)

            # Connect the new refresh signal
            self._detail_page.refresh_main_page_signal.connect(self._handle_refresh_main_page)

            self._init_sizing()
            self._is_initialized = True

        return self._detail_page

    def _handle_refresh_main_page(self, resource_type: str, resource_name: str, namespace: str):
        """Handle request to refresh main page after YAML update"""
        logging.info(f"DetailManager: Requesting main page refresh for {resource_type}/{resource_name}")
        self.refresh_main_page.emit(resource_type, resource_name, namespace)

    def _init_sizing(self) -> None:
        """Pre-calculate sizes to improve animation performance"""
        if self.parent_window:
            self._cached_height = self.parent_window.height()
            if self._detail_page:
                self._detail_page.setFixedHeight(self._cached_height)

    def _update_cached_height(self) -> None:
        """Update cached height if parent window size changed"""
        if self.parent_window:
            new_height = self.parent_window.height()
            if new_height != self._cached_height:
                self._cached_height = new_height
                if self._detail_page:
                    self._detail_page.setFixedHeight(new_height)

    def show_detail(self, resource_type: str, resource_name: str,
                    namespace: Optional[str] = None, raw_data: Optional[Dict[str, Any]] = None) -> None:
        """Show detail view for the specified resource with optimized performance"""
        resource_type_singular = singularize_resource_type(resource_type)

        # Ensure detail page is created
        detail_page = self._ensure_detail_page()

        # Check if we're already viewing the same resource
        if self._is_same_resource(resource_type_singular, resource_name, namespace) and detail_page.isVisible():
            self.update_detail_position()
            return

        # Switching to a different resource: drop any debounced watch refresh
        # queued for the previous one so its snapshot can't be flushed into the
        # panel we are about to display.
        self._refresh_debounce_timer.stop()
        self._pending_watch_payload = None

        # Update current resource tracking
        self._current_resource.update({
            'type': resource_type_singular,
            'name': resource_name,
            'namespace': namespace
        })

        # Handle special data for different resource types - CLEAR ALL FIRST
        # Clear all raw data attributes to prevent interference between resources
        if hasattr(detail_page, 'event_raw_data'):
            detail_page.event_raw_data = None
        if hasattr(detail_page, 'chart_raw_data'):
            detail_page.chart_raw_data = None
        if hasattr(detail_page, 'release_raw_data'):
            detail_page.release_raw_data = None
        if hasattr(detail_page, 'resource_raw_data'):
            detail_page.resource_raw_data = None

        # Now set the appropriate raw data if provided
        if raw_data:
            if resource_type.lower() == "event":
                detail_page.event_raw_data = raw_data
            elif resource_type.lower() in ["chart", "helmchart"]:
                detail_page.chart_raw_data = raw_data
            elif resource_type.lower() in ["helmrelease", "release"]:
                detail_page.release_raw_data = raw_data
            else:
                detail_page.resource_raw_data = raw_data

        # Update height before showing
        self._update_cached_height()

        # Show the detail page with singular resource type
        detail_page.show_detail(resource_type_singular, resource_name, namespace)

        # Phase 4: subscribe to the global watch firehose so live deltas
        # (from any source: action menu, kubectl, controller manager)
        # refresh the open detail panel.  UniqueConnection guards against
        # rapid re-shows stacking duplicate slots.
        self._subscribe_to_watch_bus()

        # Position correctly with minimal delay
        QTimer.singleShot(25, self.update_detail_position)  # Reduced from 50ms

    def hide_detail(self) -> None:
        """Hide the detail view with proper cleanup"""
        if not self._detail_page:
            return

        # Phase 4: tear down the watch subscription BEFORE clearing tracking
        # state so any in-flight event is ignored cleanly.  Also cancels
        # any pending debounced refresh.
        self._unsubscribe_from_watch_bus()

        # Remove event filter from parent if installed
        if self.parent_window:
            self.parent_window.removeEventFilter(self._detail_page)

        # Close detail page
        self._detail_page.close_detail()

        # Clear current resource tracking
        self._current_resource.update({
            'type': None,
            'name': None,
            'namespace': None
        })

    # ── Phase 4: live watch subscription lifecycle ────────────────────────

    def _subscribe_to_watch_bus(self) -> None:
        """Connect _on_watch_event to the kubernetes_client global firehose.

        UniqueConnection is critical: rapid re-shows (clicking between two
        deployments without closing the panel) would otherwise stack
        duplicate handler bindings, causing exponential repaint costs.
        """
        try:
            kc = get_kubernetes_client()
            if kc is None or not hasattr(kc, "global_resource_watch_event"):
                return
            kc.global_resource_watch_event.connect(
                self._on_watch_event,
                Qt.ConnectionType.UniqueConnection,
            )
            self._watch_client = kc
            self._watch_subscribed = True
        except TypeError:
            # UniqueConnection raises TypeError when the slot is already
            # connected — meaning we already subscribed.  No-op.
            self._watch_subscribed = True
        except Exception as e:
            logging.debug(f"DetailManager: watch subscribe failed: {e}")

    def _unsubscribe_from_watch_bus(self) -> None:
        """Sever the global firehose connection on hide / teardown."""
        # Cancel any pending debounced refresh — the panel is about to close.
        try:
            self._refresh_debounce_timer.stop()
        except Exception:
            pass
        self._pending_watch_payload = None
        if not self._watch_subscribed:
            return
        try:
            kc = getattr(self, "_watch_client", None) or get_kubernetes_client()
            if kc is not None and hasattr(kc, "global_resource_watch_event"):
                kc.global_resource_watch_event.disconnect(self._on_watch_event)
        except (TypeError, RuntimeError):
            # TypeError: already disconnected.  RuntimeError: receiver C++
            # object already destroyed.  Either way the binding is gone.
            pass
        except Exception as e:
            logging.debug(f"DetailManager: watch unsubscribe failed: {e}")
        finally:
            self._watch_subscribed = False
            self._watch_client = None

    def _on_watch_event(self, payload: Dict[str, Any]) -> None:
        """Filter the firehose down to events matching the displayed resource.

        O(1) short-circuit on (resource_type, namespace, name) mismatch.  Even
        on a busy cluster emitting thousands of events/sec, this slot stays
        cheap — only matching events advance to the debouncer + repaint.
        """
        try:
            if not is_valid(self):
                return
            current_type = self._current_resource.get("type")
            current_name = self._current_resource.get("name")
            if not current_type or not current_name:
                return
            # Loader emits the plural resource_type ("deployments"); current
            # tracking is the singular form ("deployment").  Normalise both
            # to plural-strip for comparison.
            payload_type_raw = payload.get("resource_type") or ""
            payload_type = singularize_resource_type(payload_type_raw)
            if payload_type != current_type:
                return
            if payload.get("name") != current_name:
                return
            # Namespace may be None for cluster-scoped resources; compare
            # as-is (None == None passes).
            if payload.get("namespace") != self._current_resource.get("namespace"):
                return
            # Match — queue for debounced refresh.  Always keep the latest
            # payload so the final flush uses the freshest cluster state.
            self._pending_watch_payload = payload
            self._refresh_debounce_timer.start()
        except Exception as e:
            logging.debug(f"DetailManager: _on_watch_event error: {e}")

    def _flush_debounced_refresh(self) -> None:
        """Apply the latest pending watch payload to the open detail panel.

        Primary path: direct payload injection (no extra GET) into each
        section via handle_data_loaded.  Fallback: force_refresh_current
        if the payload is malformed.
        """
        payload = self._pending_watch_payload
        self._pending_watch_payload = None
        if payload is None or not self._detail_page:
            return
        try:
            if not is_valid(self):
                return
            # The displayed resource may have changed between this event being
            # queued and the flush firing.  Re-verify identity (same normalise
            # as _on_watch_event) so a stale payload never lands in the wrong
            # panel.
            payload_type = singularize_resource_type(payload.get("resource_type") or "")
            if (payload_type != self._current_resource.get("type") or
                    payload.get("name") != self._current_resource.get("name") or
                    payload.get("namespace") != self._current_resource.get("namespace")):
                return
            raw_object = payload.get("raw_object") or {}
            if not raw_object:
                # Payload lacks the resource snapshot — fall back to a full
                # re-fetch via the existing invalidate-and-reload path.
                self.force_refresh_current()
                return
            # Direct payload injection: feed the fresh resource dict to
            # each resource-consuming section's handle_data_loaded.  This
            # sets current_data AND triggers update_ui_with_data, bypassing
            # the section's "data is current, skip load" short-circuit.
            #
            # The events section is the exception: it consumes an
            # {"events": [...]} payload, not the raw resource object.  Handing
            # it raw_object blanks the list to "No events found".  Instead we
            # re-run its own loader so it rebuilds the correct events payload
            # from the current cluster events.
            for attr in ("overview_section", "details_section",
                         "yaml_section", "events_section"):
                section = getattr(self._detail_page, attr, None)
                if section is None:
                    continue
                try:
                    if attr == "events_section":
                        if hasattr(section, "load_data"):
                            section.load_data()
                    elif hasattr(section, "handle_data_loaded"):
                        section.handle_data_loaded(raw_object)
                except Exception as e:
                    logging.debug(
                        f"DetailManager: section {type(section).__name__} "
                        f"refresh failed: {e}"
                    )
        except Exception as e:
            logging.debug(f"DetailManager: debounced refresh failed: {e}")

    def is_detail_visible(self) -> bool:
        """Check if the detail view is currently visible"""
        return self._detail_page is not None and self._detail_page.isVisible()

    def update_detail_position(self) -> None:
        """Update the position of the detail page when parent geometry changes"""
        if not self.is_detail_visible() or not self.parent_window:
            return

        detail_page = self._detail_page

        # Update height to match parent
        self._update_cached_height()

        # Calculate position based on minimized state
        parent_width = self.parent_window.width()

        # Note: The new DetailPageComponent might not have isMinimized() method
        # Check if method exists before calling it
        if hasattr(detail_page, 'isMinimized') and detail_page.isMinimized():
            target_x = parent_width - getattr(detail_page, 'minimized_width', detail_page.width())
        else:
            target_x = parent_width - detail_page.width()

        detail_page.move(target_x, 0)

    def get_current_resource_info(self) -> Dict[str, Optional[str]]:
        """Get information about the currently displayed resource"""
        return self._current_resource.copy()

    def refresh_current_detail(self) -> None:
        """Refresh the current detail view if one is open.

        Bypasses show_detail's same-resource early-return by resetting the
        tracking dict's values to None (NOT replacing the dict — that would
        delete the 'type'/'name'/'namespace' keys and break _is_same_resource
        for the rest of the session).
        """
        current_type = self._current_resource.get('type')
        if self.is_detail_visible() and current_type:
            current = dict(self._current_resource)
            self._current_resource.update({'type': None, 'name': None, 'namespace': None})
            self.show_detail(current['type'], current['name'], current['namespace'])

    def force_refresh_current(self) -> None:
        """Force a re-fetch of the currently displayed detail.

        Used by post-mutation handlers (Phase 3 Scale / Restart Rollout)
        when the displayed (type, name, namespace) tuple is unchanged but
        the underlying resource state has been mutated.

        show_detail alone is insufficient: detail sections cache
        ``current_data`` and the section's _load_data_async early-returns
        when ``current_data is not None``, reusing the stale snapshot.  We
        therefore explicitly null each section's current_data BEFORE
        re-triggering the tab load so the fresh API fetch actually fires.
        """
        if not self.is_detail_visible() or not self._detail_page:
            return
        detail_page = self._detail_page
        # Mirror DetailPageComponent.load_current_tab_data's section list.
        for attr in ("overview_section", "details_section",
                     "yaml_section", "events_section"):
            section = getattr(detail_page, attr, None)
            if section is not None and hasattr(section, "current_data"):
                section.current_data = None
        try:
            detail_page.load_current_tab_data()
        except Exception as e:
            logging.warning(f"force_refresh_current failed: {e}", exc_info=True)

    # Private helper methods
    def _is_same_resource(self, resource_type: str, resource_name: str,
                          namespace: Optional[str]) -> bool:
        """Check if the given resource is the same as currently displayed.

        Uses .get() so that a partially-cleared _current_resource (e.g. after
        an explicit refresh that nulled the tracking keys) returns False
        instead of raising KeyError and breaking every subsequent show_detail.
        """
        current = self._current_resource
        return (current.get('type') == resource_type and
                current.get('name') == resource_name and
                current.get('namespace') == namespace)

    def _handle_resource_updated(self, resource_type: str, resource_name: str, namespace: str) -> None:
        """Handle when a resource is updated in the detail view"""
        self.resource_updated.emit(resource_type, resource_name, namespace)

    # Properties for external access
    @property
    def current_resource_type(self) -> Optional[str]:
        """Get the current resource type"""
        return self._current_resource['type']

    @property
    def current_resource_name(self) -> Optional[str]:
        """Get the current resource name"""
        return self._current_resource['name']

    @property
    def current_resource_namespace(self) -> Optional[str]:
        """Get the current resource namespace"""
        return self._current_resource['namespace']

    def cleanup(self) -> None:
        """Clean up resources when manager is being destroyed"""
        if self._detail_page:
            self._detail_page.close()
            self._detail_page.deleteLater()
            self._detail_page = None

        self._current_resource.clear()
        self._cached_height = None
