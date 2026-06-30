"""
Events section for DetailPage component
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QHBoxLayout
)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor
from typing import Dict, Any
import logging

from .base_detail_section import BaseDetailSection
import Styles.EventsSectionStyles as EventsSectionStyles
from Styles.BaseDetailSectionStyles import get_status_badge_style
from Utils.time_utils import TimezoneManager


class DetailPageEventsSection(BaseDetailSection):
    """Events section showing resource-related events"""

    def __init__(self, kubernetes_client, parent=None):
        super().__init__("Events", kubernetes_client, parent)
        # Initialize data state explicitly to avoid AttributeError
        self.current_data = None
        # Initialize deterministic state flag to prevent UI desynchronization
        self._skip_async_load = False
        self.setup_events_ui()
        # Note: Theme signals connected via ThemeAwareMixin in BaseDetailSection

    def _on_theme_changed(self, theme_name):
        """Refresh styles when theme changes"""
        # Refresh the list container
        if hasattr(self, 'events_list'):
            self.events_list.setStyleSheet(EventsSectionStyles.get_events_list_style())

        # Refresh all event item widgets
        self._refresh_event_widgets()

        # DO NOT call update_ui_with_data() - eliminates race condition

    def _refresh_event_widgets(self):
        """Iterate through QListWidget and refresh all event item widgets"""
        if not hasattr(self, 'events_list'):
            return

        for i in range(self.events_list.count()):
            item = self.events_list.item(i)
            if item:
                widget = self.events_list.itemWidget(item)
                if widget:
                    # Re-apply the event widget stylesheet
                    widget.setStyleSheet(EventsSectionStyles.get_event_widget_style())
                    # Also refresh child widgets if they exist
                    for child in widget.findChildren(QLabel):
                        # Re-apply stylesheet to child labels
                        # Note: This applies generic styling - specific styles (type badges)
                        # are already theme-aware from their style functions
                        child.setStyleSheet(child.styleSheet())

    def set_raw_data(self, raw_data):
        """Set raw data for special resources like charts and releases"""
        if isinstance(raw_data, dict):
            keys_repr = list(raw_data.keys())
        else:
            keys_repr = type(raw_data).__name__ if raw_data is not None else 'None'
        
        logging.debug("Events section: Received raw data for %s, keys/type: %s", 
                      self.resource_type, keys_repr)
        
        self.current_data = raw_data
        
        # CRITICAL FIX: Establish that the UI has been definitively handled for this resource.
        # This acts as a circuit breaker for subsequent async lifecycle hooks.
        self._skip_async_load = True
        
        # For charts and releases, we don't have Kubernetes events
        # Show a message indicating this
        self.events_list.clear()
        no_events_item = QListWidgetItem("No Kubernetes events available for this resource type")
        no_events_item.setForeground(QColor(EventsSectionStyles.get_no_events_foreground_color()))
        self.events_list.addItem(no_events_item)

    def setup_events_ui(self):
        """Setup events-specific UI"""
        # Create events list
        self.events_list = QListWidget()
        self.events_list.setStyleSheet(EventsSectionStyles.get_events_list_style())
        self.events_list.setFrameShape(QListWidget.Shape.NoFrame)
        self.events_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        self.content_layout.addWidget(self.events_list)

    def _load_data_async(self):
        """Fetch events for this resource using list_namespaced_event in a background thread."""
        try:
            # State check: If the UI has already been definitively populated by special handlers
            # return early to prevent the UI message flip and redundant processing
            if getattr(self, '_skip_async_load', False):
                logging.debug(f"Events section: Skipping async load and handler for {self.resource_type}/{self.resource_name} as UI is already terminal.")
                self.hide_loading()  # Resolve FSM: clear is_loading and emit loading_finished so parent UI is unblocked
                return
        except Exception as e:
            self.handle_error(f"Failed to check async load state: {str(e)}")
            return

        import threading
        from PyQt6.QtCore import QObject, pyqtSignal

        resource_type  = self.resource_type or ""
        resource_name  = self.resource_name or ""
        namespace      = self.resource_namespace or "default"

        # Map lower-case resource_type to the Kind used by Kubernetes events
        kind_map = {
            "pod": "Pod", "pods": "Pod",
            "deployment": "Deployment", "deployments": "Deployment",
            "statefulset": "StatefulSet", "statefulsets": "StatefulSet",
            "daemonset": "DaemonSet", "daemonsets": "DaemonSet",
            "replicaset": "ReplicaSet", "replicasets": "ReplicaSet",
            "job": "Job", "jobs": "Job",
            "cronjob": "CronJob", "cronjobs": "CronJob",
            "node": "Node", "nodes": "Node",
            "service": "Service", "services": "Service",
            "configmap": "ConfigMap", "configmaps": "ConfigMap",
            "secret": "Secret", "secrets": "Secret",
            "persistentvolumeclaim": "PersistentVolumeClaim",
            "persistentvolume": "PersistentVolume",
            "namespace": "Namespace", "namespaces": "Namespace",
        }
        kind = kind_map.get(resource_type.lower(), resource_type.capitalize())

        logging.info(f"Events section API fetch: Starting for {kind}/{resource_name} in {namespace}")

        class EventFetcherSignals(QObject):
            success = pyqtSignal(list)
            error = pyqtSignal(str)

        # Create signals object and connect to main thread slots
        self._fetch_signals = EventFetcherSignals()
        self._fetch_signals.success.connect(self._on_events_received)
        self._fetch_signals.error.connect(self._on_events_error)

        def _fetch():
            try:
                v1 = self.kubernetes_client.v1
                field_selector = (
                    f"involvedObject.name={resource_name}"
                    f",involvedObject.kind={kind}"
                )
                
                # Check if resource is cluster-scoped
                cluster_scoped_kinds = ["Node", "Namespace", "PersistentVolume", "StorageClass", "ClusterRole", "ClusterRoleBinding"]
                
                if kind in cluster_scoped_kinds or not namespace:
                    event_list = v1.list_event_for_all_namespaces(
                        field_selector=field_selector
                    )
                else:
                    event_list = v1.list_namespaced_event(
                        namespace=namespace,
                        field_selector=field_selector
                    )
                    
                events = []
                for evt in event_list.items:
                    raw_age = str(evt.last_timestamp or evt.event_time or "")
                    local_age = raw_age
                    if raw_age:
                        try:
                            local_age = TimezoneManager.get_instance().format_time(raw_age)
                        except Exception:
                            pass
                            
                    events.append({
                        "type":    evt.type or "Normal",
                        "reason":  evt.reason or "",
                        "message": evt.message or "",
                        "age":     local_age,
                        "count":   evt.count or 1,
                    })
                logging.info(f"Events section API fetch: Found {len(events)} events")
                self._fetch_signals.success.emit(events)
            except Exception as e:
                logging.error(f"Events section API fetch: Failed: {e}")
                self._fetch_signals.error.emit(str(e))

        t = threading.Thread(target=_fetch, daemon=True)
        t.start()

    def _on_events_received(self, events):
        """Called on main thread when events have been fetched."""
        try:
            # This calls update_ui_with_data
            self.handle_data_loaded({"events": events})
        except Exception as e:
            self.handle_error(f"Error displaying events: {str(e)}")

    def _on_events_error(self, error_message):
        self.handle_error(f"Could not fetch events: {error_message}")

    def handle_api_data_loaded(self, data):
        pass

    def handle_api_error(self, error_message):
        pass

    def update_ui_with_data(self, data: Dict[str, Any]):
        """Update events UI with loaded data"""
        try:
            events = data.get("events", [])

            self.events_list.clear()

            if not events:
                no_events_item = QListWidgetItem("No events found for this resource")
                no_events_item.setForeground(QColor(EventsSectionStyles.get_no_events_foreground_color()))
                self.events_list.addItem(no_events_item)
                return

            sorted_events = sorted(events, key=lambda e: e.get("age", ""), reverse=True)

            for event in sorted_events:
                self.add_event_to_list(event)

        except Exception as e:
            logging.error(f"Error updating events UI: {str(e)}")


    def add_event_to_list(self, event):
        """Add an event to the events list using Card UI"""
        try:
            # We use QFrame to allow styling it as a card
            from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QSizePolicy
            from PyQt6.QtGui import QColor
            
            event_widget = QFrame()
            event_widget.setObjectName("event_card")
            event_widget.setStyleSheet(EventsSectionStyles.get_event_widget_style())
            
            # Add subtle 3D shadow effect
            shadow = QGraphicsDropShadowEffect(event_widget)
            shadow.setBlurRadius(8)
            shadow.setXOffset(0)
            shadow.setYOffset(2)
            shadow.setColor(QColor(0, 0, 0, 15)) # Very subtle semi-transparent black shadow
            event_widget.setGraphicsEffect(shadow)

            layout = QVBoxLayout(event_widget)
            layout.setContentsMargins(16, 12, 16, 12)  # Increased margins for card look
            layout.setSpacing(8)

            # Header layout with type, reason, and age
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(12)

            # Event type badge (Warning or Normal)
            event_type = event.get("type", "Normal")
            type_label = QLabel(event_type)
            # Use unified status badges from the app
            # The User specifically requested Warning events to use the red 'error' badge color
            badge_type = 'error' if event_type == 'Warning' else 'success'
            type_label.setStyleSheet(get_status_badge_style(badge_type, is_small=True))
            type_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            
            # Prevent the badge from stretching vertically to fill space
            type_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            type_label.setFixedHeight(22)
            
            # Event reason
            reason = event.get("reason", "")
            reason_label = QLabel(reason)
            reason_label.setStyleSheet(EventsSectionStyles.get_event_reason_style())
            reason_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            # Event age
            age = event.get("age", "Unknown")
            age_label = QLabel(age)
            age_label.setStyleSheet(EventsSectionStyles.get_event_age_style())
            age_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            header_layout.addWidget(type_label)
            header_layout.addWidget(reason_label)
            header_layout.addStretch()
            header_layout.addWidget(age_label)

            # Event message
            message = event.get("message", "")
            message_label = QLabel(message)
            message_label.setStyleSheet(EventsSectionStyles.get_event_message_style())
            # We must set word wrap so text causes vertical expansion
            message_label.setWordWrap(True)
            message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            layout.addLayout(header_layout)
            layout.addWidget(message_label)

            # Add to list
            item = QListWidgetItem()
            self.events_list.addItem(item)
            self.events_list.setItemWidget(item, event_widget)
            
            # Use real sizeHint of the widget layout to fit varying lines of text
            item.setSizeHint(event_widget.sizeHint())

        except Exception as e:
            logging.error(f"Error adding event to list: {str(e)}")

    def clear_content(self):
        """Clear events content and completely reset FSM states"""
        # Defensive: Clear cached data
        self.current_data = None
        # Defensive: Reset the early-return circuit breaker
        self._skip_async_load = False

        self.events_list.clear()
