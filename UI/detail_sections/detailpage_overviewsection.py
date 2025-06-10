"""
Overview section for DetailPage component
"""

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from typing import Dict, Any, Optional
import logging

from .base_detail_section import BaseDetailSection
from UI.Styles import AppStyles, AppColors, EnhancedStyles
from PyQt6.QtWidgets import QFrame, QLabel


class DetailPageOverviewSection(BaseDetailSection):
    """Overview section showing resource summary, status, conditions, and labels"""

    def __init__(self, kubernetes_client, parent=None):
        super().__init__("Overview", kubernetes_client, parent)
        self.setup_overview_ui()

    def setup_overview_ui(self):
        """Setup overview-specific UI"""
        # Create scroll area for overview content
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(AppStyles.DETAIL_PAGE_OVERVIEW_STYLE)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Overview content widget
        overview_content = QWidget()
        overview_content.setStyleSheet(f"background-color: {AppColors.BG_SIDEBAR}; border: none;")
        overview_layout = QVBoxLayout(overview_content)
        overview_layout.setContentsMargins(
            EnhancedStyles.CONTENT_PADDING,
            EnhancedStyles.CONTENT_PADDING,
            EnhancedStyles.CONTENT_PADDING,
            EnhancedStyles.CONTENT_PADDING
        )
        overview_layout.setSpacing(EnhancedStyles.SECTION_GAP)

        self.create_overview_sections(overview_layout)

        scroll_area.setWidget(overview_content)
        self.content_layout.addWidget(scroll_area)

    def create_overview_sections(self, layout):
        """Create all overview sections"""
        # Resource Header Section
        self.create_resource_header(layout)

        # Status Section
        self.create_status_section(layout)

        # Conditions Section
        self.create_conditions_section(layout)

        # Labels Section
        self.create_labels_section(layout)

        # Resource-specific section
        self.create_specific_section(layout)

        layout.addStretch()

    def create_resource_header(self, layout):
        """Create resource header with basic info"""
        header_card = QFrame()
        card_layout = QVBoxLayout(header_card)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        # Left side - Resource info
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)

        self.resource_name_label = QLabel("Resource Name")
        self.resource_name_label.setStyleSheet(EnhancedStyles.get_primary_text_style())

        self.resource_info_label = QLabel("Type / Namespace")
        self.resource_info_label.setStyleSheet(EnhancedStyles.get_secondary_text_style())

        self.creation_time_label = QLabel("Created: unknown")
        self.creation_time_label.setStyleSheet(EnhancedStyles.get_secondary_text_style())

        left_layout.addWidget(self.resource_name_label)
        left_layout.addWidget(self.resource_info_label)
        left_layout.addWidget(self.creation_time_label)

        header_layout.addLayout(left_layout, 1)
        card_layout.addLayout(header_layout)
        layout.addWidget(header_card)

    def create_status_section(self, layout):
        """Create status section"""
        status_header = QLabel("STATUS")
        status_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        layout.addWidget(status_header)

        self.status_card = QFrame()
        status_card_layout = QVBoxLayout(self.status_card)
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(16)

        self.status_badge = QLabel("Unknown")
        self.status_text_label = QLabel("Status not available")
        self.status_text_label.setStyleSheet(EnhancedStyles.get_field_value_style())

        status_layout.addWidget(self.status_badge)
        status_layout.addWidget(self.status_text_label, 1)
        status_card_layout.addLayout(status_layout)
        layout.addWidget(self.status_card)

    def create_conditions_section(self, layout):
        """Create conditions section"""
        conditions_header = QLabel("CONDITIONS")
        conditions_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        layout.addWidget(conditions_header)

        self.conditions_card = QFrame()
        conditions_card_layout = QVBoxLayout(self.conditions_card)  # ✅ ADDED THIS LINE
        self.conditions_container_layout = QVBoxLayout()
        self.conditions_container_layout.setSpacing(EnhancedStyles.FIELD_GAP)

        self.no_conditions_label = QLabel("No conditions available")
        self.no_conditions_label.setStyleSheet(EnhancedStyles.get_secondary_text_style() + """
            font-style: italic;
            padding: 8px;
        """)
        self.conditions_container_layout.addWidget(self.no_conditions_label)

        conditions_card_layout.addLayout(self.conditions_container_layout)  # ✅ FIXED THIS LINE
        layout.addWidget(self.conditions_card)

    def create_labels_section(self, layout):
        """Create labels section"""
        labels_header = QLabel("LABELS")
        labels_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        layout.addWidget(labels_header)

        self.labels_card = QFrame()
        labels_card_layout = QVBoxLayout(self.labels_card)  # ✅ ADDED THIS LINE
        self.labels_content = QLabel("No labels")
        self.labels_content.setStyleSheet(EnhancedStyles.get_field_value_style() + """
            font-family: 'Consolas', 'Courier New', monospace;
            background-color: rgba(255, 255, 255, 0.05);
            padding: 8px;
            border-radius: 4px;
        """)
        self.labels_content.setWordWrap(True)
        labels_card_layout.addWidget(self.labels_content)  # ✅ FIXED THIS LINE
        layout.addWidget(self.labels_card)

    def create_specific_section(self, layout):
        """Create resource-specific section"""
        self.specific_section = QFrame()
        self.specific_layout = QVBoxLayout(self.specific_section)
        self.specific_layout.setContentsMargins(0, 0, 0, 0)
        self.specific_layout.setSpacing(EnhancedStyles.FIELD_GAP)
        self.specific_section.hide()
        layout.addWidget(self.specific_section)

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
        """Update UI with loaded resource data"""
        if not data:
            return

        try:
            metadata = data.get("metadata", {})

            # Update resource header
            self.resource_name_label.setText(metadata.get("name", "Unnamed"))

            resource_info = f"{self.resource_type.capitalize()}"
            if "namespace" in metadata:
                resource_info += f" / {metadata.get('namespace')}"
            self.resource_info_label.setText(resource_info)

            # Update creation time
            creation_timestamp = metadata.get("creationTimestamp", "")
            if creation_timestamp:
                from datetime import datetime
                try:
                    # Simple datetime parsing
                    formatted_time = creation_timestamp.replace('T', ' ').replace('Z', '')
                    self.creation_time_label.setText(f"Created: {formatted_time}")
                except Exception:
                    self.creation_time_label.setText("Created: unknown")

            # Update status
            self.update_resource_status(data)

            # Update conditions
            self.update_conditions(data)

            # Update labels
            self.update_labels(data)

            # Update resource-specific fields
            self.add_resource_specific_fields(data)

        except Exception as e:
            self.handle_error(f"Error updating UI: {str(e)}")

    def update_resource_status(self, data):
        """Update resource status display"""
        status = data.get("status", {})
        status_value = "Unknown"
        status_text = "Status not available"
        status_type = "default"

        # Basic status detection logic
        if self.resource_type == "pods":
            phase = status.get("phase", "Unknown")
            status_value = phase

            if phase == "Running":
                status_text = "Pod is running"
                status_type = "success"
            elif phase == "Pending":
                status_text = "Pod is pending"
                status_type = "warning"
            elif phase == "Failed":
                status_text = "Pod has failed"
                status_type = "error"
            elif phase == "Succeeded":
                status_text = "Pod completed successfully"
                status_type = "success"

        elif self.resource_type == "deployments":
            available_replicas = status.get("availableReplicas", 0)
            replicas = status.get("replicas", 0)

            if available_replicas == replicas and replicas > 0:
                status_value = "Available"
                status_text = f"Deployment is available ({available_replicas}/{replicas} replicas)"
                status_type = "success"
            else:
                status_value = "Progressing"
                status_text = f"Deployment is progressing ({available_replicas}/{replicas} replicas available)"
                status_type = "warning"

        # Add more resource types as needed

        self.status_badge.setText(status_value)
        # Note: QLabel doesn't have set_status_style method, so we'll style it directly
        if status_type == "success":
            self.status_badge.setStyleSheet(f"color: {AppColors.STATUS_ACTIVE}; font-weight: bold;")
        elif status_type == "warning":
            self.status_badge.setStyleSheet(f"color: {AppColors.STATUS_WARNING}; font-weight: bold;")
        elif status_type == "error":
            self.status_badge.setStyleSheet(f"color: {AppColors.TEXT_DANGER}; font-weight: bold;")
        else:
            self.status_badge.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; font-weight: bold;")

        self.status_text_label.setText(status_text)

    def update_conditions(self, data):
        """Update conditions display"""
        # Safe widget clearing
        while self.conditions_container_layout.count():
            item = self.conditions_container_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()

        status = data.get("status", {})
        conditions = status.get("conditions", [])

        if not conditions:
            self.no_conditions_label = QLabel("No conditions available")
            self.no_conditions_label.setStyleSheet(EnhancedStyles.get_secondary_text_style() + """
                font-style: italic;
                padding: 8px;
            """)
            self.conditions_container_layout.addWidget(self.no_conditions_label)
            return

        for condition in conditions:
            condition_type = condition.get("type", "Unknown")
            condition_status = condition.get("status", "Unknown")
            condition_message = condition.get("message", "")

            condition_widget = QLabel(f"{condition_type}: {condition_status} - {condition_message}")
            self.conditions_container_layout.addWidget(condition_widget)

    def update_labels(self, data):
        """Update labels display"""
        metadata = data.get("metadata", {})
        labels = metadata.get("labels", {})

        if not labels:
            self.labels_content.setText("No labels")
            return

        labels_text = "\n".join([f"{k}={v}" for k, v in labels.items()])
        self.labels_content.setText(labels_text)

    def add_resource_specific_fields(self, data):
        """Add resource-specific fields to specific section"""
        # Clear existing content
        for i in reversed(range(self.specific_layout.count())):
            item = self.specific_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        # Add fields based on resource type
        if self.resource_type == "pods":
            self._add_pod_specific_fields(data)
        elif self.resource_type == "services":
            self._add_service_specific_fields(data)
        elif self.resource_type == "deployments":
            self._add_deployment_specific_fields(data)
        # Add more resource types as needed
        else:
            self.specific_section.hide()
            return

        self.specific_section.show()

    def _add_pod_specific_fields(self, data):
        """Add pod-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("POD DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        containers = spec.get("containers", [])
        container_info = QLabel(f"Containers: {len(containers)}")
        container_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(container_info)

        node_name = spec.get("nodeName", "")
        if node_name:
            node_info = QLabel(f"Node: {node_name}")
            node_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(node_info)

        pod_ip = status.get("podIP", "")
        if pod_ip:
            ip_info = QLabel(f"Pod IP: {pod_ip}")
            ip_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(ip_info)

    def _add_service_specific_fields(self, data):
        """Add service-specific fields"""
        spec = data.get("spec", {})

        section_header = QLabel("SERVICE DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        service_type = spec.get("type", "ClusterIP")
        type_info = QLabel(f"Type: {service_type}")
        type_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(type_info)

        cluster_ip = spec.get("clusterIP", "")
        if cluster_ip:
            ip_info = QLabel(f"Cluster IP: {cluster_ip}")
            ip_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(ip_info)

    def _add_deployment_specific_fields(self, data):
        """Add deployment-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("DEPLOYMENT DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        replicas = spec.get("replicas", 0)
        replicas_info = QLabel(f"Desired Replicas: {replicas}")
        replicas_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(replicas_info)

        ready_replicas = status.get("readyReplicas", 0)
        ready_info = QLabel(f"Ready Replicas: {ready_replicas}")
        ready_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(ready_info)

    def clear_content(self):
        """Clear all overview content"""
        self.resource_name_label.setText("Resource Name")
        self.resource_info_label.setText("Type / Namespace")
        self.creation_time_label.setText("Created: unknown")
        self.status_badge.setText("Unknown")
        self.status_text_label.setText("Status not available")
        self.labels_content.setText("No labels")

        # Safe conditions clearing
        while self.conditions_container_layout.count():
            item = self.conditions_container_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()

        # Safe specific section clearing
        while self.specific_layout.count():
            item = self.specific_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()

        self.specific_section.hide()