"""
Events section for DetailPage component
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QHBoxLayout
)
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor
from typing import Dict, Any
import logging

from .base_detail_section import BaseDetailSection
import Styles.EventsSectionStyles as EventsSectionStyles


class DetailPageEventsSection(BaseDetailSection):
    """Events section showing resource-related events"""

    def __init__(self, kubernetes_client, parent=None):
        super().__init__("Events", kubernetes_client, parent)
        # Initialize data state explicitly to avoid AttributeError
        self.current_data = None
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
        logging.info(f"Events section: Received raw data for {self.resource_type}, keys: {list(raw_data.keys()) if raw_data else 'None'}")
        self.current_data = raw_data
        # For charts and releases, we don't have Kubernetes events
        # Show a message indicating this
        self.events_list.clear()
        no_events_item = QListWidgetItem("No Kubernetes events available for this resource type")
        no_events_item.setForeground(QColor(EventsSectionStyles.get_no_events_color()))
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
        """Load overview data using Kubernetes API"""
        try:
            # CRITICAL FIX: Check if we already have raw_data from the page (e.g., CustomResourcePages, NodesPage)
            # This prevents unnecessary API calls and empty detail sections
            if self.current_data is not None:
                logging.info(f"Events section: Using existing raw_data for {self.resource_type}/{self.resource_name}")
                # Use the existing data directly instead of making API call
                self.handle_data_loaded(self.current_data)
                return
            
            # Only make API call if we don't have current_data
            logging.info(f"Events section: No raw_data available, fetching from API for {self.resource_type}/{self.resource_name}")
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
            self.handle_data_loaded(data)
        except Exception as e:
            self.handle_error(f"Error processing loaded data: {str(e)}")

    def handle_api_error(self, error_message):
        """Handle API error"""
        self.disconnect_api_signals()
        self.handle_error(error_message)

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

            # Sort events by age (newest first)
            sorted_events = sorted(events, key=lambda e: e.get("age", ""), reverse=True)

            for event in sorted_events:
                self.add_event_to_list(event)

        except Exception as e:
            self.handle_error(f"Error updating events UI: {str(e)}")

    def add_event_to_list(self, event):
        """Add an event to the events list"""
        try:
            event_widget = QWidget()
            event_widget.setStyleSheet(EventsSectionStyles.get_event_widget_style())

            layout = QVBoxLayout(event_widget)
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(3)

            # Header layout with type, reason, and age
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(8)

            # Event type
            event_type = event.get("type", "Normal")
            type_label = QLabel(event_type)
            if event_type == "Warning":
                type_label.setStyleSheet(EventsSectionStyles.get_event_type_warning_style())
            else:
                type_label.setStyleSheet(EventsSectionStyles.get_event_type_normal_style())

            # Event reason
            reason = event.get("reason", "")
            reason_label = QLabel(reason)
            reason_label.setStyleSheet(EventsSectionStyles.get_event_reason_style())

            # Event age
            age = event.get("age", "Unknown")
            age_label = QLabel(age)
            age_label.setStyleSheet(EventsSectionStyles.get_event_age_style())

            header_layout.addWidget(type_label)
            header_layout.addWidget(reason_label)
            header_layout.addStretch()
            header_layout.addWidget(age_label)

            # Event message
            message = event.get("message", "")
            message_label = QLabel(message)
            message_label.setStyleSheet(EventsSectionStyles.get_event_message_style())
            message_label.setWordWrap(True)

            layout.addLayout(header_layout)
            layout.addWidget(message_label)

            # Add to list
            item = QListWidgetItem()
            # Calculate minimum height for the event item
            min_height = 80  # Minimum height to ensure content is visible
            current_size = event_widget.sizeHint()
            adjusted_height = max(min_height, current_size.height())
            item.setSizeHint(QSize(current_size.width(), adjusted_height))
            self.events_list.addItem(item)
            self.events_list.setItemWidget(item, event_widget)

        except Exception as e:
            logging.error(f"Error adding event to list: {str(e)}")

    def clear_content(self):
        """Clear events content"""
        # Defensive: Clear cached data
        self.current_data = None

        self.events_list.clear()
