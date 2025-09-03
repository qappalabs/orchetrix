"""
Events section for DetailPage component
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor
from typing import Dict, Any, List
from datetime import datetime, timezone
import logging

from .base_detail_section import BaseDetailSection
from UI.Styles import AppStyles, AppColors


class DetailPageEventsSection(BaseDetailSection):
    """Events section showing resource-related events"""

    def __init__(self, kubernetes_client, parent=None):
        super().__init__("Events", kubernetes_client, parent)
        self.setup_events_ui()

    def setup_events_ui(self):
        """Setup events-specific UI"""
        # Create events list
        self.events_list = QListWidget()
        self.events_list.setStyleSheet(AppStyles.DETAIL_PAGE_EVENTS_LIST_STYLE)
        self.events_list.setFrameShape(QListWidget.Shape.NoFrame)
        self.events_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        self.content_layout.addWidget(self.events_list)

    def _load_data_async(self):
        """Load overview data using Kubernetes API"""
        try:
            self.connect_api_signals()
            self.kubernetes_client.get_resource_detail_async(
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
                no_events_item.setForeground(QColor(AppColors.TEXT_SUBTLE))
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
            event_widget.setStyleSheet("background-color: transparent;")

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
                type_label.setStyleSheet(f"""
                    color: {AppColors.TEXT_WARNING};
                    font-weight: bold;
                    padding: 2px 6px;
                    background-color: rgba(255, 152, 0, 0.1);
                    border-radius: 3px;
                """)
            else:
                type_label.setStyleSheet(f"""
                    color: {AppColors.TEXT_SUCCESS};
                    font-weight: bold;
                    padding: 2px 6px;
                    background-color: rgba(76, 175, 80, 0.1);
                    border-radius: 3px;
                """)

            # Event reason
            reason = event.get("reason", "")
            reason_label = QLabel(reason)
            reason_label.setStyleSheet(f"""
                color: {AppColors.TEXT_LIGHT};
                font-weight: bold;
            """)

            # Event age
            age = event.get("age", "Unknown")
            age_label = QLabel(age)
            age_label.setStyleSheet(f"""
                color: {AppColors.TEXT_SUBTLE};
                font-size: 11px;
            """)

            header_layout.addWidget(type_label)
            header_layout.addWidget(reason_label)
            header_layout.addStretch()
            header_layout.addWidget(age_label)

            # Event message
            message = event.get("message", "")
            message_label = QLabel(message)
            message_label.setStyleSheet(f"""
                color: {AppColors.TEXT_SECONDARY};
                font-size: 12px;
                line-height: 1.4;
            """)
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
        self.events_list.clear()