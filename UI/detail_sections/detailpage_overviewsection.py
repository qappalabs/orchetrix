"""
Overview section for DetailPage component
"""

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
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
            if data:
                self.handle_data_loaded(data)
            else:
                # Resource exists in list but not accessible individually
                self.handle_resource_not_accessible()
        except Exception as e:
            self.handle_error(f"Error processing loaded data: {str(e)}")
            
    def handle_resource_not_accessible(self):
        """Handle case where resource exists in list but not accessible individually"""
        self.hide_loading()
        # Create basic info from what we know
        basic_data = {
            'metadata': {
                'name': self.resource_name,
                'namespace': self.resource_namespace
            },
            'kind': self.resource_type.capitalize(),
            '_note': 'Resource details not accessible individually'
        }
        self.update_ui_with_basic_info(basic_data)

    def handle_api_error(self, error_message):
        """Handle API error with better error messages"""
        self.disconnect_api_signals()

        # Provide more specific error messages for common issues
        if "customresourcedefinition" in error_message.lower() and "not found" in error_message.lower():
            error_message = f"CustomResourceDefinition '{self.resource_name}' not found. It may have been deleted or you may not have permission to view it."
        elif "forbidden" in error_message.lower():
            error_message = f"Access denied. You don't have permission to view {self.resource_type} '{self.resource_name}'."

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
            
    def update_ui_with_basic_info(self, data: Dict[str, Any]):
        """Update UI with basic info when full details aren't available"""
        try:
            metadata = data.get("metadata", {})
            
            # Update resource header
            self.resource_name_label.setText(metadata.get("name", "Unnamed"))
            
            resource_info = f"{self.resource_type.capitalize()}"
            if "namespace" in metadata:
                resource_info += f" / {metadata.get('namespace')}"
            self.resource_info_label.setText(resource_info)
            
            # Set creation time as unavailable
            self.creation_time_label.setText("Created: Details not available")
            
            # Set status as limited info
            self.clear_status_content()
            self.add_status_item("Status", "Available in cluster list", "limited")
            self.add_status_item("Details", "Not accessible individually", "info")
            
            # Clear other sections
            self.clear_conditions_content()
            self.clear_labels_content()
            
            # Add note about limited access
            if data.get('_note'):
                self.add_status_item("Note", data['_note'], "info")
                
        except Exception as e:
            self.handle_error(f"Error updating UI with basic info: {str(e)}")

    def update_resource_status(self, data):
        """Update resource status display"""
        status = data.get("status", {})
        status_value = "Unknown"
        status_text = "Status not available"
        status_type = "default"

        resource_type_lower = self.resource_type.lower()

        # Pod status
        if resource_type_lower in ["pod", "pods"]:
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

        # NetworkPolicy status
        elif resource_type_lower in ["networkpolicy", "networkpolicies", "netpol"]:
            # NetworkPolicies don't have a traditional status, but we can show if they're active
            spec = data.get("spec", {})
            pod_selector = spec.get("podSelector", {})

            status_value = "Active"
            if pod_selector:
                match_labels = pod_selector.get("matchLabels", {})
                if match_labels:
                    status_text = f"NetworkPolicy active for pods matching {len(match_labels)} labels"
                else:
                    status_text = "NetworkPolicy active for all pods"
            else:
                status_text = "NetworkPolicy active for all pods"
            status_type = "success"

        # CustomResourceDefinition status - FIXED
        elif resource_type_lower in ["customresourcedefinition", "customresourcedefinitions", "crd", "definitions"]:
            conditions = status.get("conditions", [])
            if conditions:
                established_condition = next((c for c in conditions if c.get("type") == "Established"), None)
                names_accepted_condition = next((c for c in conditions if c.get("type") == "NamesAccepted"), None)

                if established_condition and established_condition.get("status") == "True":
                    status_value = "Established"
                    status_text = "CustomResourceDefinition is established and ready"
                    status_type = "success"
                elif names_accepted_condition and names_accepted_condition.get("status") == "True":
                    status_value = "Names Accepted"
                    status_text = "CustomResourceDefinition names are accepted"
                    status_type = "warning"
                else:
                    status_value = "Pending"
                    status_text = "CustomResourceDefinition is being processed"
                    status_type = "warning"
            else:
                # Check accepted names from spec
                spec = data.get("spec", {})
                names = spec.get("names", {})
                if names.get("kind"):
                    status_value = "Available"
                    status_text = f"CustomResourceDefinition for {names.get('kind')} is available"
                    status_type = "success"
                else:
                    status_value = "Invalid"
                    status_text = "CustomResourceDefinition has invalid configuration"
                    status_type = "error"

        # Deployment status
        elif resource_type_lower in ["deployment", "deployments", "deploy"]:
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

        # ReplicaSet status
        elif resource_type_lower in ["replicaset", "replicasets", "rs"]:
            ready_replicas = status.get("readyReplicas", 0)
            replicas = status.get("replicas", 0)

            if ready_replicas == replicas and replicas > 0:
                status_value = "Ready"
                status_text = f"ReplicaSet is ready ({ready_replicas}/{replicas} replicas)"
                status_type = "success"
            else:
                status_value = "Not Ready"
                status_text = f"ReplicaSet not ready ({ready_replicas}/{replicas} replicas ready)"
                status_type = "warning"

        # DaemonSet status
        elif resource_type_lower in ["daemonset", "daemonsets", "ds"]:
            desired = status.get("desiredNumberScheduled", 0)
            ready = status.get("numberReady", 0)

            if ready == desired and desired > 0:
                status_value = "Ready"
                status_text = f"DaemonSet is ready ({ready}/{desired} pods)"
                status_type = "success"
            else:
                status_value = "Not Ready"
                status_text = f"DaemonSet not ready ({ready}/{desired} pods ready)"
                status_type = "warning"

        # StatefulSet status
        elif resource_type_lower in ["statefulset", "statefulsets", "sts"]:
            ready_replicas = status.get("readyReplicas", 0)
            replicas = status.get("replicas", 0)

            if ready_replicas == replicas and replicas > 0:
                status_value = "Ready"
                status_text = f"StatefulSet is ready ({ready_replicas}/{replicas} replicas)"
                status_type = "success"
            else:
                status_value = "Not Ready"
                status_text = f"StatefulSet not ready ({ready_replicas}/{replicas} replicas ready)"
                status_type = "warning"

        # Job status
        elif resource_type_lower in ["job", "jobs"]:
            conditions = status.get("conditions", [])
            if conditions:
                last_condition = conditions[-1]
                condition_type = last_condition.get("type", "Unknown")
                condition_status = last_condition.get("status", "Unknown")

                if condition_type == "Complete" and condition_status == "True":
                    status_value = "Complete"
                    status_text = "Job completed successfully"
                    status_type = "success"
                elif condition_type == "Failed" and condition_status == "True":
                    status_value = "Failed"
                    status_text = "Job failed"
                    status_type = "error"
                else:
                    status_value = "Running"
                    status_text = "Job is running"
                    status_type = "warning"

        # CronJob status
        elif resource_type_lower in ["cronjob", "cronjobs", "cj"]:
            spec = data.get("spec", {})
            suspend = spec.get("suspend", False)

            if suspend:
                status_value = "Suspended"
                status_text = "CronJob is suspended"
                status_type = "warning"
            else:
                status_value = "Active"
                status_text = "CronJob is active"
                status_type = "success"

        # Service status
        elif resource_type_lower in ["service", "services", "svc"]:
            spec = data.get("spec", {})
            service_type = spec.get("type", "ClusterIP")

            status_value = service_type
            status_text = f"Service is available (type: {service_type})"
            status_type = "success"

        # ConfigMap status
        elif resource_type_lower in ["configmap", "configmaps", "cm"]:
            data_section = data.get("data", {})
            data_count = len(data_section)

            status_value = "Available"
            status_text = f"ConfigMap available with {data_count} data entries"
            status_type = "success"

        # Secret status
        elif resource_type_lower in ["secret", "secrets"]:
            data_section = data.get("data", {})
            data_count = len(data_section)

            status_value = "Available"
            status_text = f"Secret available with {data_count} data entries"
            status_type = "success"

        # PersistentVolume status
        elif resource_type_lower in ["persistentvolume", "persistentvolumes", "pv"]:
            phase = status.get("phase", "Unknown")
            status_value = phase

            if phase == "Available":
                status_text = "PersistentVolume is available"
                status_type = "success"
            elif phase == "Bound":
                status_text = "PersistentVolume is bound"
                status_type = "success"
            elif phase == "Released":
                status_text = "PersistentVolume is released"
                status_type = "warning"
            elif phase == "Failed":
                status_text = "PersistentVolume failed"
                status_type = "error"

        # PersistentVolumeClaim status
        elif resource_type_lower in ["persistentvolumeclaim", "persistentvolumeclaims", "pvc"]:
            phase = status.get("phase", "Unknown")
            status_value = phase

            if phase == "Bound":
                status_text = "PersistentVolumeClaim is bound"
                status_type = "success"
            elif phase == "Pending":
                status_text = "PersistentVolumeClaim is pending"
                status_type = "warning"
            elif phase == "Lost":
                status_text = "PersistentVolumeClaim is lost"
                status_type = "error"

        # Ingress status
        elif resource_type_lower in ["ingress", "ingresses", "ing"]:
            load_balancer = status.get("loadBalancer", {})
            ingress_ips = load_balancer.get("ingress", [])

            if ingress_ips:
                status_value = "Ready"
                status_text = f"Ingress ready with {len(ingress_ips)} endpoints"
                status_type = "success"
            else:
                status_value = "Pending"
                status_text = "Ingress is pending"
                status_type = "warning"

        # Node status
        elif resource_type_lower in ["node", "nodes"]:
            conditions = status.get("conditions", [])
            ready_condition = next((c for c in conditions if c.get("type") == "Ready"), None)

            if ready_condition and ready_condition.get("status") == "True":
                status_value = "Ready"
                status_text = "Node is ready"
                status_type = "success"
            else:
                status_value = "NotReady"
                status_text = "Node is not ready"
                status_type = "error"

        # Namespace status
        elif resource_type_lower in ["namespace", "namespaces", "ns"]:
            phase = status.get("phase", "Unknown")
            status_value = phase

            if phase == "Active":
                status_text = "Namespace is active"
                status_type = "success"
            elif phase == "Terminating":
                status_text = "Namespace is terminating"
                status_type = "warning"

        # HelmRelease status
        elif resource_type_lower in ["helmrelease", "helmreleases", "hr", "chart", "charts"]:
            conditions = status.get("conditions", [])
            if conditions:
                ready_condition = next((c for c in conditions if c.get("type") == "Ready"), None)
                if ready_condition:
                    condition_status = ready_condition.get("status", "Unknown")
                    if condition_status == "True":
                        status_value = "Ready"
                        status_text = "Helm release is ready"
                        status_type = "success"
                    else:
                        status_value = "Not Ready"
                        status_text = "Helm release is not ready"
                        status_type = "warning"

        # PriorityClass status
        elif resource_type_lower in ["priorityclass", "priorityclasses", "pc"]:
            value = data.get("value", 0)
            status_value = "Available"
            status_text = f"PriorityClass available with value {value}"
            status_type = "success"

        # Lease status
        elif resource_type_lower in ["lease", "leases"]:
            spec = data.get("spec", {})
            holder = spec.get("holderIdentity", "Unknown")
            status_value = "Active"
            status_text = f"Lease held by {holder}"
            status_type = "success"

        # ValidatingWebhookConfiguration status
        elif resource_type_lower in ["validatingwebhookconfiguration", "validatingwebhookconfigurations", "vwc"]:
            webhooks = data.get("webhooks", [])
            if webhooks:
                status_value = "Active"
                status_text = f"ValidatingWebhookConfiguration active with {len(webhooks)} webhooks"
                status_type = "success"
            else:
                status_value = "No Webhooks"
                status_text = "ValidatingWebhookConfiguration has no webhooks configured"
                status_type = "warning"

        # MutatingWebhookConfiguration status
        elif resource_type_lower in ["mutatingwebhookconfiguration", "mutatingwebhookconfigurations", "mwc"]:
            webhooks = data.get("webhooks", [])
            if webhooks:
                status_value = "Active"
                status_text = f"MutatingWebhookConfiguration active with {len(webhooks)} webhooks"
                status_type = "success"
            else:
                status_value = "No Webhooks"
                status_text = "MutatingWebhookConfiguration has no webhooks configured"
                status_type = "warning"

        # ReplicationController status
        elif resource_type_lower in ["replicationcontroller", "replicationcontrollers", "rc"]:
            replicas = data.get("spec", {}).get("replicas", 0)
            ready_replicas = data.get("status", {}).get("readyReplicas", 0)

            if ready_replicas == replicas and replicas > 0:
                status_value = "Ready"
                status_text = f"ReplicationController ready ({ready_replicas}/{replicas} replicas)"
                status_type = "success"
            else:
                status_value = "Not Ready"
                status_text = f"ReplicationController not ready ({ready_replicas}/{replicas} replicas ready)"
                status_type = "warning"

        # IngressClass status
        elif resource_type_lower in ["ingressclass", "ingressclasses", "ic"]:
            spec = data.get("spec", {})
            controller = spec.get("controller", "Unknown")
            status_value = "Available"
            status_text = f"IngressClass available (controller: {controller})"
            status_type = "success"

        # Generic custom resource status
        else:
            # Try to detect status from common fields
            conditions = status.get("conditions", [])
            if conditions:
                ready_condition = next((c for c in conditions if c.get("type") == "Ready"), None)
                if ready_condition:
                    condition_status = ready_condition.get("status", "Unknown")
                    status_value = condition_status
                    status_text = f"Resource status: {condition_status}"
                    status_type = "success" if condition_status == "True" else "warning"
            else:
                phase = status.get("phase", status.get("state", "Unknown"))
                status_value = phase
                status_text = f"Resource phase: {phase}"
                status_type = "default"

        # Apply styling
        self.status_badge.setText(status_value)
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

        resource_type_lower = self.resource_type.lower()

        # Add fields based on resource type
        if resource_type_lower in ["pod", "pods"]:
            self._add_pod_specific_fields(data)
        elif resource_type_lower in ["service", "services", "svc"]:
            self._add_service_specific_fields(data)
        elif resource_type_lower in ["deployment", "deployments", "deploy"]:
            self._add_deployment_specific_fields(data)
        elif resource_type_lower in ["configmap", "configmaps", "cm"]:
            self._add_configmap_specific_fields(data)
        elif resource_type_lower in ["secret", "secrets"]:
            self._add_secret_specific_fields(data)
        elif resource_type_lower in ["ingress", "ingresses", "ing"]:
            self._add_ingress_specific_fields(data)
        # ADD THESE TWO NEW LINES HERE:
        elif resource_type_lower in ["networkpolicy", "networkpolicies", "netpol"]:
            self._add_networkpolicy_specific_fields(data)
        elif resource_type_lower in ["customresourcedefinition", "customresourcedefinitions", "crd"]:
            self._add_customresourcedefinition_specific_fields(data)
        # END OF NEW LINES
        elif resource_type_lower in ["persistentvolume", "persistentvolumes", "pv"]:
            self._add_persistentvolume_specific_fields(data)
        elif resource_type_lower in ["persistentvolumeclaim", "persistentvolumeclaims", "pvc"]:
            self._add_persistentvolumeclaim_specific_fields(data)
        elif resource_type_lower in ["replicaset", "replicasets", "rs"]:
            self._add_replicaset_specific_fields(data)
        elif resource_type_lower in ["daemonset", "daemonsets", "ds"]:
            self._add_daemonset_specific_fields(data)
        elif resource_type_lower in ["statefulset", "statefulsets", "sts"]:
            self._add_statefulset_specific_fields(data)
        elif resource_type_lower in ["job", "jobs"]:
            self._add_job_specific_fields(data)
        elif resource_type_lower in ["cronjob", "cronjobs", "cj"]:
            self._add_cronjob_specific_fields(data)
        elif resource_type_lower in ["node", "nodes"]:
            self._add_node_specific_fields(data)
        elif resource_type_lower in ["namespace", "namespaces", "ns"]:
            self._add_namespace_specific_fields(data)
        elif resource_type_lower in ["helmrelease", "helmreleases", "hr"]:
            self._add_helmrelease_specific_fields(data)
        elif resource_type_lower in ["chart", "charts"]:
            self._add_helmrelease_specific_fields(data)  # Use same method for charts
        elif resource_type_lower in ["priorityclass", "priorityclasses", "pc"]:
            self._add_priorityclass_specific_fields(data)
        elif resource_type_lower in ["lease", "leases"]:
            self._add_lease_specific_fields(data)
        elif resource_type_lower in ["validatingwebhookconfiguration", "validatingwebhookconfigurations", "vwc"]:
            self._add_validating_webhook_specific_fields(data)
        elif resource_type_lower in ["mutatingwebhookconfiguration", "mutatingwebhookconfigurations", "mwc"]:
            self._add_mutating_webhook_specific_fields(data)
        elif resource_type_lower in ["replicationcontroller", "replicationcontrollers", "rc"]:
            self._add_replicationcontroller_specific_fields(data)
        elif resource_type_lower in ["ingressclass", "ingressclasses", "ic"]:
            self._add_ingressclass_specific_fields(data)
        else:
            # Generic custom resource handling
            self._add_generic_custom_resource_fields(data)

        if self.specific_layout.count() > 0:
            self.specific_section.show()
        else:
            self.specific_section.hide()

    def _add_networkpolicy_specific_fields(self, data):
        """Add NetworkPolicy-specific fields"""
        spec = data.get("spec", {})

        section_header = QLabel("NETWORK POLICY DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        # Pod selector
        pod_selector = spec.get("podSelector", {})
        if pod_selector:
            match_labels = pod_selector.get("matchLabels", {})
            if match_labels:
                labels_text = ", ".join([f"{k}={v}" for k, v in match_labels.items()])
                selector_info = QLabel(f"Pod Selector: {labels_text}")
            else:
                selector_info = QLabel("Pod Selector: All pods")
        else:
            selector_info = QLabel("Pod Selector: All pods")

        selector_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        selector_info.setWordWrap(True)
        self.specific_layout.addWidget(selector_info)

        # Policy types
        policy_types = spec.get("policyTypes", [])
        if policy_types:
            types_info = QLabel(f"Policy Types: {', '.join(policy_types)}")
            types_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(types_info)

        # Ingress rules
        ingress_rules = spec.get("ingress", [])
        ingress_info = QLabel(f"Ingress Rules: {len(ingress_rules)}")
        ingress_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(ingress_info)

        # Egress rules
        egress_rules = spec.get("egress", [])
        egress_info = QLabel(f"Egress Rules: {len(egress_rules)}")
        egress_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(egress_info)

    def _add_customresourcedefinition_specific_fields(self, data):
        """Add CustomResourceDefinition-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("CUSTOM RESOURCE DEFINITION DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        # Group and versions
        group = spec.get("group", "Unknown")
        group_info = QLabel(f"Group: {group}")
        group_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(group_info)

        versions = spec.get("versions", [])
        if versions:
            version_names = [v.get("name", "unknown") for v in versions]
            versions_info = QLabel(f"Versions: {', '.join(version_names)}")
            versions_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(versions_info)

        # Names
        names = spec.get("names", {})
        if names:
            kind = names.get("kind", "Unknown")
            kind_info = QLabel(f"Kind: {kind}")
            kind_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(kind_info)

            plural = names.get("plural", "Unknown")
            plural_info = QLabel(f"Plural: {plural}")
            plural_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(plural_info)

            singular = names.get("singular", "Unknown")
            singular_info = QLabel(f"Singular: {singular}")
            singular_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(singular_info)

        # Scope
        scope = spec.get("scope", "Unknown")
        scope_info = QLabel(f"Scope: {scope}")
        scope_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(scope_info)

        # Status
        conditions = status.get("conditions", [])
        if conditions:
            established_condition = next((c for c in conditions if c.get("type") == "Established"), None)
            if established_condition:
                established_status = established_condition.get("status", "Unknown")
                established_info = QLabel(f"Established: {established_status}")
                established_info.setStyleSheet(EnhancedStyles.get_field_value_style())
                self.specific_layout.addWidget(established_info)

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

    def _add_configmap_specific_fields(self, data):
        """Add ConfigMap-specific fields"""
        spec = data.get("spec", {})

        section_header = QLabel("CONFIGMAP DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        data_section = data.get("data", {})
        data_count = len(data_section)
        data_info = QLabel(f"Data entries: {data_count}")
        data_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(data_info)

        if data_section:
            data_keys = list(data_section.keys())[:5]  # Show first 5 keys
            keys_text = ", ".join(data_keys)
            if len(data_section) > 5:
                keys_text += f"... and {len(data_section) - 5} more"

            keys_info = QLabel(f"Keys: {keys_text}")
            keys_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            keys_info.setWordWrap(True)
            self.specific_layout.addWidget(keys_info)

    def _add_secret_specific_fields(self, data):
        """Add Secret-specific fields"""
        section_header = QLabel("SECRET DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        secret_type = data.get("type", "Opaque")
        type_info = QLabel(f"Type: {secret_type}")
        type_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(type_info)

        data_section = data.get("data", {})
        data_count = len(data_section)
        data_info = QLabel(f"Data entries: {data_count}")
        data_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(data_info)

    def _add_ingress_specific_fields(self, data):
        """Add Ingress-specific fields"""
        spec = data.get("spec", {})

        section_header = QLabel("INGRESS DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        ingress_class = spec.get("ingressClassName", "default")
        class_info = QLabel(f"Ingress Class: {ingress_class}")
        class_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(class_info)

        rules = spec.get("rules", [])
        rules_info = QLabel(f"Rules: {len(rules)}")
        rules_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(rules_info)

        if rules:
            hosts = [rule.get("host", "no-host") for rule in rules[:3]]
            hosts_text = ", ".join(hosts)
            if len(rules) > 3:
                hosts_text += f"... and {len(rules) - 3} more"

            hosts_info = QLabel(f"Hosts: {hosts_text}")
            hosts_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            hosts_info.setWordWrap(True)
            self.specific_layout.addWidget(hosts_info)

    def _add_persistentvolume_specific_fields(self, data):
        """Add PersistentVolume-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("PERSISTENT VOLUME DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        capacity = spec.get("capacity", {}).get("storage", "Unknown")
        capacity_info = QLabel(f"Capacity: {capacity}")
        capacity_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(capacity_info)

        access_modes = spec.get("accessModes", [])
        access_info = QLabel(f"Access Modes: {', '.join(access_modes)}")
        access_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(access_info)

        reclaim_policy = spec.get("persistentVolumeReclaimPolicy", "Unknown")
        reclaim_info = QLabel(f"Reclaim Policy: {reclaim_policy}")
        reclaim_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(reclaim_info)

        phase = status.get("phase", "Unknown")
        phase_info = QLabel(f"Phase: {phase}")
        phase_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(phase_info)

    def _add_persistentvolumeclaim_specific_fields(self, data):
        """Add PersistentVolumeClaim-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("PERSISTENT VOLUME CLAIM DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        access_modes = spec.get("accessModes", [])
        access_info = QLabel(f"Access Modes: {', '.join(access_modes)}")
        access_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(access_info)

        requests = spec.get("resources", {}).get("requests", {}).get("storage", "Unknown")
        requests_info = QLabel(f"Requested Storage: {requests}")
        requests_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(requests_info)

        storage_class = spec.get("storageClassName", "default")
        storage_info = QLabel(f"Storage Class: {storage_class}")
        storage_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(storage_info)

        phase = status.get("phase", "Unknown")
        phase_info = QLabel(f"Phase: {phase}")
        phase_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(phase_info)

    def _add_replicaset_specific_fields(self, data):
        """Add ReplicaSet-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("REPLICASET DETAILS")
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

        available_replicas = status.get("availableReplicas", 0)
        available_info = QLabel(f"Available Replicas: {available_replicas}")
        available_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(available_info)

    def _add_daemonset_specific_fields(self, data):
        """Add DaemonSet-specific fields"""
        status = data.get("status", {})

        section_header = QLabel("DAEMONSET DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        desired = status.get("desiredNumberScheduled", 0)
        desired_info = QLabel(f"Desired: {desired}")
        desired_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(desired_info)

        current = status.get("currentNumberScheduled", 0)
        current_info = QLabel(f"Current: {current}")
        current_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(current_info)

        ready = status.get("numberReady", 0)
        ready_info = QLabel(f"Ready: {ready}")
        ready_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(ready_info)

    def _add_statefulset_specific_fields(self, data):
        """Add StatefulSet-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("STATEFULSET DETAILS")
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

        service_name = spec.get("serviceName", "Unknown")
        service_info = QLabel(f"Service Name: {service_name}")
        service_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(service_info)

    def _add_job_specific_fields(self, data):
        """Add Job-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("JOB DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        parallelism = spec.get("parallelism", 1)
        parallelism_info = QLabel(f"Parallelism: {parallelism}")
        parallelism_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(parallelism_info)

        completions = spec.get("completions", 1)
        completions_info = QLabel(f"Completions: {completions}")
        completions_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(completions_info)

        succeeded = status.get("succeeded", 0)
        succeeded_info = QLabel(f"Succeeded: {succeeded}")
        succeeded_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(succeeded_info)

    def _add_cronjob_specific_fields(self, data):
        """Add CronJob-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("CRONJOB DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        schedule = spec.get("schedule", "Unknown")
        schedule_info = QLabel(f"Schedule: {schedule}")
        schedule_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(schedule_info)

        suspend = spec.get("suspend", False)
        suspend_info = QLabel(f"Suspended: {'Yes' if suspend else 'No'}")
        suspend_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(suspend_info)

        last_schedule = status.get("lastScheduleTime", "Never")
        last_info = QLabel(f"Last Schedule: {last_schedule}")
        last_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(last_info)

    def _add_node_specific_fields(self, data):
        """Add Node-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("NODE DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        # Node info
        node_info = status.get("nodeInfo", {})
        os_image = node_info.get("osImage", "Unknown")
        os_info = QLabel(f"OS Image: {os_image}")
        os_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(os_info)

        kernel_version = node_info.get("kernelVersion", "Unknown")
        kernel_info = QLabel(f"Kernel Version: {kernel_version}")
        kernel_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(kernel_info)

        container_runtime = node_info.get("containerRuntimeVersion", "Unknown")
        runtime_info = QLabel(f"Container Runtime: {container_runtime}")
        runtime_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(runtime_info)

        # Add pods section for this node
        self._add_node_pods_section(data)

    def _add_namespace_specific_fields(self, data):
        """Add Namespace-specific fields"""
        status = data.get("status", {})

        section_header = QLabel("NAMESPACE DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        phase = status.get("phase", "Unknown")
        phase_info = QLabel(f"Phase: {phase}")
        phase_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(phase_info)

    def _add_helmrelease_specific_fields(self, data):
        """Add HelmRelease-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("HELM RELEASE DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        chart = spec.get("chart", {})
        chart_name = chart.get("spec", {}).get("chart", "Unknown")
        chart_info = QLabel(f"Chart: {chart_name}")
        chart_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(chart_info)

        version = chart.get("spec", {}).get("version", "Unknown")
        version_info = QLabel(f"Version: {version}")
        version_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(version_info)

        release_status = status.get("conditions", [])
        if release_status:
            last_condition = release_status[-1]
            condition_type = last_condition.get("type", "Unknown")
            condition_status = last_condition.get("status", "Unknown")
            status_info = QLabel(f"Status: {condition_type} = {condition_status}")
            status_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(status_info)

    def _add_generic_custom_resource_fields(self, data):
        """Add generic fields for custom resources"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("CUSTOM RESOURCE DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        api_version = data.get("apiVersion", "Unknown")
        api_info = QLabel(f"API Version: {api_version}")
        api_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(api_info)

        kind = data.get("kind", "Unknown")
        kind_info = QLabel(f"Kind: {kind}")
        kind_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(kind_info)

        # Show some basic spec fields if available
        if spec:
            spec_keys = list(spec.keys())[:3]
            spec_text = ", ".join(spec_keys)
            if len(spec) > 3:
                spec_text += f"... and {len(spec) - 3} more"

            spec_info = QLabel(f"Spec fields: {spec_text}")
            spec_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(spec_info)

    def _add_priorityclass_specific_fields(self, data):
        """Add PriorityClass-specific fields"""
        section_header = QLabel("PRIORITY CLASS DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        value = data.get("value", 0)
        value_info = QLabel(f"Priority Value: {value}")
        value_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(value_info)

        global_default = data.get("globalDefault", False)
        default_info = QLabel(f"Global Default: {'Yes' if global_default else 'No'}")
        default_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(default_info)

        description = data.get("description", "")
        if description:
            desc_info = QLabel(f"Description: {description}")
            desc_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            desc_info.setWordWrap(True)
            self.specific_layout.addWidget(desc_info)

    def _add_lease_specific_fields(self, data):
        """Add Lease-specific fields"""
        spec = data.get("spec", {})

        section_header = QLabel("LEASE DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        holder_identity = spec.get("holderIdentity", "Unknown")
        holder_info = QLabel(f"Holder Identity: {holder_identity}")
        holder_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(holder_info)

        lease_duration = spec.get("leaseDurationSeconds", "Unknown")
        duration_info = QLabel(f"Lease Duration: {lease_duration}s")
        duration_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(duration_info)

        acquire_time = spec.get("acquireTime", "")
        if acquire_time:
            acquire_info = QLabel(f"Acquire Time: {acquire_time}")
            acquire_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(acquire_info)

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
        
    def clear_status_content(self):
        """Clear status items"""
        self.status_badge.setText("Unknown")
        self.status_text_label.setText("Status not available")
                
    def clear_conditions_content(self):
        """Clear conditions items"""
        while self.conditions_container_layout.count():
            item = self.conditions_container_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
                
    def clear_labels_content(self):
        """Clear labels items"""
        self.labels_content.setText("No labels")
                
    def clear_specific_content(self):
        """Clear specific items"""
        while self.specific_layout.count():
            item = self.specific_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
        self.specific_section.hide()

    def _add_validating_webhook_specific_fields(self, data):
        """Add ValidatingWebhookConfiguration-specific fields"""
        section_header = QLabel("VALIDATING WEBHOOK DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        webhooks = data.get("webhooks", [])
        webhooks_info = QLabel(f"Webhooks: {len(webhooks)}")
        webhooks_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(webhooks_info)

        if webhooks:
            first_webhook = webhooks[0]
            name = first_webhook.get("name", "Unknown")
            name_info = QLabel(f"First Webhook Name: {name}")
            name_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            self.specific_layout.addWidget(name_info)

    def _add_mutating_webhook_specific_fields(self, data):
        """Add MutatingWebhookConfiguration-specific fields"""
        section_header = QLabel("MUTATING WEBHOOK DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        webhooks = data.get("webhooks", [])
        webhooks_info = QLabel(f"Webhooks: {len(webhooks)}")
        webhooks_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(webhooks_info)

    def _add_replicationcontroller_specific_fields(self, data):
        """Add ReplicationController-specific fields"""
        spec = data.get("spec", {})
        status = data.get("status", {})

        section_header = QLabel("REPLICATION CONTROLLER DETAILS")
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

    def _add_ingressclass_specific_fields(self, data):
        """Add IngressClass-specific fields"""
        spec = data.get("spec", {})

        section_header = QLabel("INGRESS CLASS DETAILS")
        section_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(section_header)

        controller = spec.get("controller", "Unknown")
        controller_info = QLabel(f"Controller: {controller}")
        controller_info.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(controller_info)

        parameters = spec.get("parameters", {})
        if parameters:
            params_info = QLabel(f"Parameters: {parameters}")
            params_info.setStyleSheet(EnhancedStyles.get_field_value_style())
            params_info.setWordWrap(True)
            self.specific_layout.addWidget(params_info)

    def _add_node_pods_section(self, data):
        """Add simple pods info for this node"""
        node_name = data.get("metadata", {}).get("name", "")
        if not node_name:
            return

        # Create pods section header
        pods_header = QLabel("PODS")
        pods_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(pods_header)

        # Create loading label
        self.pods_loading_label = QLabel("Loading pods...")
        self.pods_loading_label.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(self.pods_loading_label)

        # Fetch pods for this node
        self._fetch_node_pods(node_name)

    def _fetch_node_pods(self, node_name):
        """Fetch pods running on the specified node"""
        try:
            # Connect to kubernetes client signals for pods
            self.kubernetes_client.pods_data_loaded.connect(self._handle_node_pods_loaded)
            self.kubernetes_client.api_error.connect(self._handle_node_pods_error)

            # Request pods for this node
            self.kubernetes_client.get_pods_for_node_async(node_name)

        except Exception as e:
            self._handle_node_pods_error(f"Failed to fetch pods: {str(e)}")

    def _handle_node_pods_loaded(self, pods_data):
        """Handle when pods data is loaded"""
        try:
            # Disconnect signals
            self.kubernetes_client.pods_data_loaded.disconnect(self._handle_node_pods_loaded)
            self.kubernetes_client.api_error.disconnect(self._handle_node_pods_error)

            self.pods_loading_label.hide()

            if not pods_data:
                pods_info = QLabel("No pods running on this node")
                pods_info.setStyleSheet(EnhancedStyles.get_field_value_style())
                self.specific_layout.addWidget(pods_info)
                return

            # Create vertical list of pod names
            for pod in pods_data:
                name = pod.get("name", "Unknown")
                status = pod.get("status", "Unknown")

                if status.lower() == "running":
                    pod_text = name
                else:
                    pod_text = f"{name} ({status})"

                pod_label = QLabel(pod_text)
                pod_label.setStyleSheet(EnhancedStyles.get_field_value_style())
                self.specific_layout.addWidget(pod_label)

        except Exception as e:
            logging.error(f"Error handling node pods data: {str(e)}")
            self._handle_node_pods_error(str(e))

    def _handle_node_pods_error(self, error_message):
        """Handle error when fetching pods for node"""
        try:
            # Disconnect signals
            if hasattr(self.kubernetes_client, 'pods_data_loaded'):
                self.kubernetes_client.pods_data_loaded.disconnect(self._handle_node_pods_loaded)
            if hasattr(self.kubernetes_client, 'api_error'):
                self.kubernetes_client.api_error.disconnect(self._handle_node_pods_error)
        except:
            pass

        self.pods_loading_label.hide()

        error_label = QLabel("Error loading pods")
        error_label.setStyleSheet(EnhancedStyles.get_field_value_style() + f"""
            color: {AppColors.TEXT_DANGER};
        """)
        self.specific_layout.addWidget(error_label)