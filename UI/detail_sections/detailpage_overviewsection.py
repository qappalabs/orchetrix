"""
Overview section for DetailPage component
"""

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
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

        # Pod status with enhanced container state checking
        if resource_type_lower in ["pod", "pods"]:
            phase = status.get("phase", "Unknown")
            status_value = phase
            
            # Check container statuses for more detailed information
            container_statuses = status.get("containerStatuses", [])
            if container_statuses:
                for cs in container_statuses:
                    if cs.get("state"):
                        state = cs["state"]
                        if "waiting" in state:
                            waiting = state["waiting"]
                            reason = waiting.get("reason", "")
                            if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                                status_value = reason
                                break
                        elif "terminated" in state:
                            terminated = state["terminated"]
                            exit_code = terminated.get("exitCode", 0)
                            reason = terminated.get("reason", "")
                            if exit_code != 0:
                                status_value = f"Error ({reason})"
                                break
                            elif reason == "Completed":
                                status_value = f"Completed ({exit_code})"
                                break

            if status_value in ["Running"]:
                status_text = "Pod is running"
                status_type = "success"
            elif status_value in ["Pending"]:
                status_text = "Pod is pending"
                status_type = "warning"
            elif status_value in ["Failed"] or "Error" in status_value:
                status_text = "Pod has failed"
                status_type = "error"
            elif status_value in ["Succeeded"] or "Completed" in status_value:
                status_text = "Pod completed successfully"
                status_type = "success"
            elif status_value in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"]:
                status_text = f"Pod error: {status_value}"
                status_type = "error"

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

        # Add rollback section
        self._add_deployment_rollback_section(data)

    def _add_deployment_rollback_section(self, data):
        """Add deployment rollback section with history and rollback buttons"""
        metadata = data.get("metadata", {})
        deployment_name = metadata.get("name", "")
        namespace = metadata.get("namespace", "default")
        
        if not deployment_name:
            return
        
        # Create rollback section header
        rollback_header = QLabel("ROLLBACK HISTORY")
        rollback_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(rollback_header)
        
        # Create loading label for history
        self.history_loading_label = QLabel("Loading rollback history...")
        self.history_loading_label.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(self.history_loading_label)
        
        # Create container for history table
        self.history_container = QWidget()
        history_layout = QVBoxLayout(self.history_container)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(8)
        
        # Create table for rollback history
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Revision", "Age", "Status", "Change Cause", "Action"])
        
        # Style the table
        self.history_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {AppColors.BG_SIDEBAR};
                color: {AppColors.TEXT_LIGHT};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                gridline-color: {AppColors.BORDER_COLOR};
                selection-background-color: {AppColors.SELECTED_BG};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {AppColors.BORDER_COLOR};
            }}
            QTableWidget::item:selected {{
                background-color: {AppColors.SELECTED_BG};
            }}
            QHeaderView::section {{
                background-color: {AppColors.BG_MEDIUM};
                color: {AppColors.TEXT_LIGHT};
                padding: 8px;
                border: 1px solid {AppColors.BORDER_COLOR};
                font-weight: bold;
            }}
        """)
        
        # Configure table properties
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        
        # Set consistent row height to accommodate widgets
        self.history_table.verticalHeader().setDefaultSectionSize(40)
        
        # Ensure the table shows widgets properly
        self.history_table.setShowGrid(True)
        self.history_table.setWordWrap(False)
        
        # Set column widths and resize modes
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)     # Revision
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Age (dynamic)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)     # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)   # Change Cause (stretches)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)     # Action
        
        # Set fixed column widths
        self.history_table.setColumnWidth(0, 80)   # Revision
        self.history_table.setColumnWidth(2, 120)  # Status (wider for better visibility)
        self.history_table.setColumnWidth(4, 120)  # Action (wider for button)
        
        # Set reasonable height for table (dynamic based on content)
        self.history_table.setMinimumHeight(100)
        self.history_table.setMaximumHeight(300)  # Allow more space for multiple revisions
        
        history_layout.addWidget(self.history_table)
        self.history_container.hide()  # Hide initially
        self.specific_layout.addWidget(self.history_container)
        
        # Store deployment info for rollback operations
        self.current_deployment_name = deployment_name
        self.current_deployment_namespace = namespace
        
        # Connect to kubernetes client signals with safe handling
        try:
            # Disconnect any existing connections first
            try:
                self.kubernetes_client.deployment_history_loaded.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            
            try:
                self.kubernetes_client.deployment_rollback_completed.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            
            # Connect new handlers
            self.kubernetes_client.deployment_history_loaded.connect(self._handle_deployment_history_loaded)
            self.kubernetes_client.deployment_rollback_completed.connect(self._handle_deployment_rollback_completed)
            
        except Exception as e:
            logging.error(f"Error connecting rollback signals: {str(e)}")
        
        # Fetch rollback history
        logging.info(f"Requesting rollout history for deployment {deployment_name} in namespace {namespace}")
        self.kubernetes_client.get_deployment_rollout_history_async(deployment_name, namespace)

    def _handle_deployment_history_loaded(self, history_data):
        """Handle when deployment history is loaded"""
        try:
            # Safely disconnect the signal to avoid multiple calls
            try:
                self.kubernetes_client.deployment_history_loaded.disconnect(self._handle_deployment_history_loaded)
            except (TypeError, RuntimeError):
                pass  # Signal already disconnected or object deleted
            
            # Hide loading label and show container
            self.history_loading_label.hide()
            self.history_container.show()
            
            if not history_data:
                no_history_label = QLabel("No rollback history available")
                no_history_label.setStyleSheet(EnhancedStyles.get_secondary_text_style())
                self.specific_layout.addWidget(no_history_label)
                return
            
            # Populate the table
            self.history_table.setRowCount(len(history_data))
            
            logging.info(f"Processing {len(history_data)} rollback history items for display")
            
            for row, revision_data in enumerate(history_data):
                revision = revision_data.get("revision", 1)
                creation_time = revision_data.get("creation_time", "")
                age = self._calculate_age_from_timestamp(creation_time)
                change_cause = revision_data.get("change_cause", "No change cause recorded")
                current = revision_data.get("current", False)
                status = revision_data.get("status", "Unknown")
                images = revision_data.get("images", [])
                
                logging.debug(f"Row {row}: Revision {revision}, Current: {current}, Status: {status}")
                
                # Add revision cell
                revision_text = str(revision)
                revision_item = QTableWidgetItem(revision_text)
                revision_item.setFlags(revision_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if current:
                    revision_item.setForeground(QColor(AppColors.STATUS_ACTIVE))
                    revision_item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.history_table.setItem(row, 0, revision_item)
                
                # Add age cell
                age_item = QTableWidgetItem(age)
                age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row, 1, age_item)
                
                # Add status cell
                status_item = QTableWidgetItem(status)
                status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if current:
                    status_item.setForeground(QColor(AppColors.STATUS_ACTIVE))
                    status_item.setFont(QFont("", -1, QFont.Weight.Bold))
                elif status == "Available":
                    status_item.setForeground(QColor("#4CAF50"))
                elif status == "Inactive":
                    status_item.setForeground(QColor(AppColors.TEXT_SECONDARY))
                self.history_table.setItem(row, 2, status_item)
                
                # Add change cause cell with enhanced tooltip
                truncated_cause = change_cause[:50] + "..." if len(change_cause) > 50 else change_cause
                cause_item = QTableWidgetItem(truncated_cause)
                cause_item.setFlags(cause_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Create detailed tooltip
                tooltip_text = f"Change Cause: {change_cause}"
                if images:
                    tooltip_text += f"\nImages: {', '.join(images[:3])}"  # Show first 3 images
                    if len(images) > 3:
                        tooltip_text += f"\n... and {len(images)-3} more"
                cause_item.setToolTip(tooltip_text)
                self.history_table.setItem(row, 3, cause_item)
                
                # Add action cell (rollback button or current label)
                logging.debug(f"Setting action widget for row {row}, current={current}, revision={revision}")
                
                
                if not current:  # Don't show rollback button for current revision
                    rollback_btn = QPushButton("Rollback")
                    # Simplified styling first to test basic functionality
                    rollback_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            padding: 6px 12px;
                            font-weight: bold;
                        }
                    """)
                    rollback_btn.clicked.connect(lambda checked, rev=revision: self._rollback_to_revision(rev))
                    self.history_table.setCellWidget(row, 4, rollback_btn)
                    logging.debug(f"Added rollback button for row {row}")
                else:
                    # Show "Current" label for current revision
                    current_label = QLabel("Current")
                    current_label.setStyleSheet("""
                        QLabel {
                            color: #4CAF50;
                            font-weight: bold;
                            padding: 6px 12px;
                        }
                    """)
                    current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.history_table.setCellWidget(row, 4, current_label)
                    logging.debug(f"Added current label for row {row}")
                
                # Verify the widget was set
                test_widget = self.history_table.cellWidget(row, 4)
                if test_widget:
                    logging.debug(f"Successfully set action widget for row {row}: {type(test_widget).__name__}")
                else:
                    logging.error(f"Failed to set action widget for row {row}")
                    # If widget setting failed, at least keep the text item
                    if not current:
                        fallback_item = QTableWidgetItem("Rollback (Fallback)")
                        self.history_table.setItem(row, 4, fallback_item)
            
            # Ensure Age column adjusts to content (already set to ResizeToContents)
            # Other columns maintain their fixed/stretch settings from table setup
            
            # Adjust table height based on content
            self._adjust_table_height(len(history_data))
            
            logging.info(f"Populated rollback history table with {len(history_data)} revisions")
            
        except Exception as e:
            logging.error(f"Error handling deployment history: {str(e)}")
            error_label = QLabel("Error loading rollback history")
            error_label.setStyleSheet(f"color: {AppColors.TEXT_DANGER};")
            self.specific_layout.addWidget(error_label)

    def _calculate_age_from_timestamp(self, timestamp_str):
        """Calculate age from ISO timestamp string"""
        if not timestamp_str:
            return "Unknown"
        
        try:
            from datetime import datetime
            from dateutil import parser
            
            creation_time = parser.parse(timestamp_str)
            now = datetime.now(creation_time.tzinfo)
            delta = now - creation_time
            
            days = delta.days
            seconds = delta.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
                
        except Exception:
            return "Unknown"

    def _adjust_table_height(self, row_count):
        """Adjust table height based on number of rows"""
        try:
            # Calculate height: header + rows + padding
            header_height = 35  # Header row height
            row_height = 40     # Each row height (matches defaultSectionSize)
            padding = 10        # Extra padding
            
            # Calculate optimal height
            calculated_height = header_height + (row_count * row_height) + padding
            
            # Ensure it's within our min/max bounds
            min_height = 120    # Minimum to show at least header + one row
            max_height = 350    # Allow more space for widget containers
            final_height = max(min_height, min(calculated_height, max_height))
            
            self.history_table.setFixedHeight(final_height)
            logging.debug(f"Adjusted table height to {final_height}px for {row_count} rows")
        except Exception as e:
            logging.error(f"Error adjusting table height: {str(e)}")

    def _rollback_to_revision(self, revision):
        """Initiate rollback to specific revision"""
        from PyQt6.QtWidgets import QMessageBox
        
        # Show confirmation dialog
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Confirm Rollback")
        msg_box.setText(f"Are you sure you want to rollback deployment '{self.current_deployment_name}' to revision {revision}?")
        msg_box.setInformativeText("This action will update the deployment and trigger a new rollout.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        # Apply dark theme styling
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {AppColors.BG_SIDEBAR};
                color: {AppColors.TEXT_LIGHT};
            }}
            QMessageBox QPushButton {{
                background-color: {AppColors.BG_MEDIUM};
                color: {AppColors.TEXT_LIGHT};
                border: 1px solid {AppColors.BORDER_COLOR};
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {AppColors.ACCENT_BLUE};
            }}
        """)
        
        result = msg_box.exec()
        
        if result == QMessageBox.StandardButton.Yes:
            logging.info(f"User confirmed rollback of {self.current_deployment_name} to revision {revision}")
            
            # Show progress indicator
            for i in range(self.history_table.rowCount()):
                widget = self.history_table.cellWidget(i, 4)  # Action column widget
                if isinstance(widget, QPushButton):
                    widget.setText("Rolling back...")
                    widget.setEnabled(False)
            
            # Trigger rollback
            self.kubernetes_client.rollback_deployment_async(
                self.current_deployment_name, 
                revision, 
                self.current_deployment_namespace
            )

    def _handle_deployment_rollback_completed(self, result):
        """Handle when deployment rollback is completed"""
        try:
            # Safely disconnect the signal
            try:
                self.kubernetes_client.deployment_rollback_completed.disconnect(self._handle_deployment_rollback_completed)
            except (TypeError, RuntimeError):
                pass  # Signal already disconnected or object deleted
            
            # Re-enable buttons
            for i in range(self.history_table.rowCount()):
                widget = self.history_table.cellWidget(i, 4)  # Action column widget
                if isinstance(widget, QPushButton):
                    widget.setText("Rollback")
                    widget.setEnabled(True)
            
            # Show result message
            from PyQt6.QtWidgets import QMessageBox
            
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Rollback Result")
            
            if result.get("success", False):
                msg_box.setText("Rollback completed successfully!")
                msg_box.setInformativeText(result.get("message", ""))
                msg_box.setIcon(QMessageBox.Icon.Information)
                
                # Refresh the deployment details after successful rollback
                QTimer.singleShot(2000, lambda: self._refresh_deployment_details())
                
            else:
                msg_box.setText("Rollback failed!")
                msg_box.setInformativeText(result.get("message", "Unknown error"))
                msg_box.setIcon(QMessageBox.Icon.Critical)
            
            # Apply dark theme styling
            msg_box.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {AppColors.BG_SIDEBAR};
                    color: {AppColors.TEXT_LIGHT};
                }}
                QMessageBox QPushButton {{
                    background-color: {AppColors.BG_MEDIUM};
                    color: {AppColors.TEXT_LIGHT};
                    border: 1px solid {AppColors.BORDER_COLOR};
                    padding: 8px 16px;
                    border-radius: 4px;
                    min-width: 80px;
                }}
                QMessageBox QPushButton:hover {{
                    background-color: {AppColors.ACCENT_BLUE};
                }}
            """)
            
            msg_box.exec()
            
            logging.info(f"Rollback completed with result: {result}")
            
        except Exception as e:
            logging.error(f"Error handling rollback completion: {str(e)}")

    def _refresh_deployment_details(self):
        """Refresh deployment details after rollback"""
        try:
            # Trigger a refresh of the current resource
            if hasattr(self, 'resource_name') and hasattr(self, 'resource_namespace'):
                self.load_data(self.resource_type, self.resource_name, self.resource_namespace)
        except Exception as e:
            logging.error(f"Error refreshing deployment details: {str(e)}")

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
        """Add pods table for this node"""
        node_name = data.get("metadata", {}).get("name", "")
        if not node_name:
            return

        # Create pods section header
        pods_header = QLabel("PODS RUNNING ON THIS NODE")
        pods_header.setStyleSheet(EnhancedStyles.get_section_header_style())
        self.specific_layout.addWidget(pods_header)

        # Create loading label
        self.pods_loading_label = QLabel("Loading pods...")
        self.pods_loading_label.setStyleSheet(EnhancedStyles.get_field_value_style())
        self.specific_layout.addWidget(self.pods_loading_label)

        # Create container for pods table
        self.pods_container = QWidget()
        pods_layout = QVBoxLayout(self.pods_container)
        pods_layout.setContentsMargins(0, 0, 0, 0)
        pods_layout.setSpacing(8)

        # Create table for pods
        self.pods_table = QTableWidget()
        self.pods_table.setColumnCount(5)
        self.pods_table.setHorizontalHeaderLabels(["Pod Name", "Namespace", "Status", "CPU", "Memory"])

        # Style the table
        self.pods_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {AppColors.BG_SIDEBAR};
                color: {AppColors.TEXT_LIGHT};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                gridline-color: {AppColors.BORDER_COLOR};
                selection-background-color: {AppColors.SELECTED_BG};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {AppColors.BORDER_COLOR};
            }}
            QTableWidget::item:selected {{
                background-color: {AppColors.SELECTED_BG};
            }}
            QHeaderView::section {{
                background-color: {AppColors.BG_MEDIUM};
                color: {AppColors.TEXT_LIGHT};
                padding: 8px;
                border: 1px solid {AppColors.BORDER_COLOR};
                font-weight: bold;
            }}
        """)

        # Configure table properties
        self.pods_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pods_table.setAlternatingRowColors(True)
        self.pods_table.verticalHeader().setVisible(False)
        
        # Connect single-click event to navigate to pod
        self.pods_table.itemClicked.connect(self._on_pod_clicked)

        # Set column widths
        header = self.pods_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)    # Pod Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Namespace
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # CPU
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Memory

        self.pods_table.setColumnWidth(0, 250)  # Pod Name - made larger
        self.pods_table.setColumnWidth(1, 120)  # Namespace
        self.pods_table.setColumnWidth(2, 100)  # Status
        self.pods_table.setColumnWidth(3, 80)   # CPU
        # Memory column will stretch to fill remaining space

        # Set maximum height for table (show max 8 rows)
        self.pods_table.setMaximumHeight(250)

        pods_layout.addWidget(self.pods_table)
        self.pods_container.hide()  # Hide initially
        self.specific_layout.addWidget(self.pods_container)

        # Store node name for pod operations
        self.current_node_name = node_name

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
            # Safely disconnect signals
            try:
                self.kubernetes_client.pods_data_loaded.disconnect(self._handle_node_pods_loaded)
            except (TypeError, RuntimeError):
                pass
            
            try:
                self.kubernetes_client.api_error.disconnect(self._handle_node_pods_error)
            except (TypeError, RuntimeError):
                pass

            # Hide loading label and show table container
            self.pods_loading_label.hide()
            self.pods_container.show()

            if not pods_data:
                # Show empty state in table
                self.pods_table.setRowCount(1)
                empty_item = QTableWidgetItem("No pods running on this node")
                empty_item.setFlags(empty_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.pods_table.setItem(0, 0, empty_item)
                
                # Span across all columns
                self.pods_table.setSpan(0, 0, 1, 5)
                return

            # Populate the table
            self.pods_table.setRowCount(len(pods_data))

            for row, pod in enumerate(pods_data):
                pod_name = pod.get("name", "Unknown")
                namespace = pod.get("namespace", "Unknown") 
                status = pod.get("status", "Unknown")
                
                # Get resource usage if available
                cpu_usage = pod.get("cpu_usage", "N/A")
                memory_usage = pod.get("memory_usage", "N/A")
                
                # Format resource usage
                if cpu_usage != "N/A" and isinstance(cpu_usage, (int, float)):
                    cpu_display = f"{cpu_usage:.0f}m"
                else:
                    cpu_display = str(cpu_usage)
                    
                if memory_usage != "N/A" and isinstance(memory_usage, (int, float)):
                    if memory_usage > 1024:
                        memory_display = f"{memory_usage/1024:.1f}Gi"
                    else:
                        memory_display = f"{memory_usage:.0f}Mi"
                else:
                    memory_display = str(memory_usage)

                # Add pod name cell
                name_item = QTableWidgetItem(pod_name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.pods_table.setItem(row, 0, name_item)

                # Add namespace cell
                namespace_item = QTableWidgetItem(namespace)
                namespace_item.setFlags(namespace_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.pods_table.setItem(row, 1, namespace_item)

                # Add status cell with color coding
                status_item = QTableWidgetItem(status)
                status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Color code status
                if status.lower() == "running":
                    status_item.setForeground(QColor(AppColors.STATUS_ACTIVE))
                elif status.lower() in ["pending", "containercreating"]:
                    status_item.setForeground(QColor(AppColors.STATUS_WARNING))
                elif status.lower() in ["failed", "crashloopbackoff", "error"]:
                    status_item.setForeground(QColor(AppColors.TEXT_DANGER))
                else:
                    status_item.setForeground(QColor(AppColors.TEXT_SECONDARY))
                    
                self.pods_table.setItem(row, 2, status_item)

                # Add CPU cell
                cpu_item = QTableWidgetItem(cpu_display)
                cpu_item.setFlags(cpu_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.pods_table.setItem(row, 3, cpu_item)

                # Add Memory cell
                memory_item = QTableWidgetItem(memory_display)
                memory_item.setFlags(memory_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                memory_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.pods_table.setItem(row, 4, memory_item)

            logging.info(f"Populated pods table with {len(pods_data)} pods for node")

        except Exception as e:
            logging.error(f"Error handling node pods data: {str(e)}")
            self._handle_node_pods_error(str(e))

    def _handle_node_pods_error(self, error_message):
        """Handle error when fetching pods for node"""
        try:
            # Safely disconnect signals
            try:
                self.kubernetes_client.pods_data_loaded.disconnect(self._handle_node_pods_loaded)
            except (TypeError, RuntimeError):
                pass
            
            try:
                self.kubernetes_client.api_error.disconnect(self._handle_node_pods_error)
            except (TypeError, RuntimeError):
                pass
        except:
            pass

        # Hide loading label and show error in table
        self.pods_loading_label.hide()
        self.pods_container.show()
        
        # Show error in table
        self.pods_table.setRowCount(1)
        error_item = QTableWidgetItem(f"Error loading pods: {error_message}")
        error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        error_item.setForeground(QColor(AppColors.TEXT_DANGER))
        self.pods_table.setItem(0, 0, error_item)
        
        # Span across all columns
        self.pods_table.setSpan(0, 0, 1, 5)

        logging.error(f"Node pods error: {error_message}")
    
    def _on_pod_clicked(self, item):
        """Handle single-click on pod item to navigate to pods page"""
        try:
            if not item:
                return
            
            # Get the row that was clicked
            row = item.row()
            
            # Get pod name from the first column (Pod Name)
            pod_name_item = self.pods_table.item(row, 0)
            if not pod_name_item:
                return
                
            pod_name = pod_name_item.text()
            
            # Get namespace from the second column (Namespace)
            namespace_item = self.pods_table.item(row, 1)
            namespace = namespace_item.text() if namespace_item else ""
            
            # Skip if this is an empty row or error message
            if pod_name in ["No pods running on this node", "Error loading pods"] or "Error loading pods" in pod_name:
                return
            
            logging.info(f"Navigating to pod '{pod_name}' in namespace '{namespace}'")
            
            # Navigate to the pods page and search for this specific pod
            self._navigate_to_pods_page(pod_name, namespace)
            
        except Exception as e:
            logging.error(f"Error handling pod click: {e}")
    
    def _navigate_to_pods_page(self, pod_name: str, namespace: str):
        """Navigate to the pods page and search for the specific pod"""
        try:
            # Get the main cluster view (parent window)
            detail_page = self.parent()
            while detail_page and not hasattr(detail_page, 'parent_window'):
                detail_page = detail_page.parent()
            
            if not detail_page or not hasattr(detail_page, 'parent_window'):
                logging.error("Could not find detail page with parent_window")
                return
            
            main_window = detail_page.parent_window
            logging.info(f"Found main_window: {type(main_window).__name__}")
            
            # Get the actual cluster view from the main window
            cluster_view = None
            if hasattr(main_window, 'cluster_view'):
                cluster_view = main_window.cluster_view
                logging.info(f"Found cluster_view: {type(cluster_view).__name__}")
                logging.info(f"Cluster view has handle_dropdown_selection: {hasattr(cluster_view, 'handle_dropdown_selection')}")
            else:
                logging.error("MainWindow does not have cluster_view attribute")
                return
            
            # Close the detail page first
            if hasattr(detail_page, 'close_detail'):
                detail_page.close_detail()
            elif hasattr(detail_page, 'hide'):
                detail_page.hide()
            
            # Navigate to pods page - try multiple methods
            navigation_success = False
            
            if hasattr(cluster_view, 'handle_dropdown_selection'):
                try:
                    cluster_view.handle_dropdown_selection("Pods")
                    logging.info("Called handle_dropdown_selection for Pods page")
                    navigation_success = True
                except Exception as e:
                    logging.error(f"Error calling handle_dropdown_selection: {e}")
            
            # Try alternative navigation method
            if not navigation_success and hasattr(cluster_view, 'pages') and 'Pods' in cluster_view.pages:
                try:
                    pods_page = cluster_view.pages['Pods']
                    if hasattr(cluster_view, 'stacked_widget'):
                        cluster_view.stacked_widget.setCurrentWidget(pods_page)
                        logging.info("Navigated to Pods page using direct stacked widget")
                        navigation_success = True
                        
                        # Load data for the pods page
                        if hasattr(cluster_view, '_load_page_data'):
                            cluster_view._load_page_data(pods_page)
                        elif hasattr(pods_page, 'force_load_data'):
                            pods_page.force_load_data()
                except Exception as e:
                    logging.error(f"Error with direct navigation: {e}")
            
            if not navigation_success:
                logging.error("All navigation methods failed")
                return
            
            # Wait longer for the page to load, then set search filter
            QTimer.singleShot(1000, lambda: self._set_pod_search_filter(cluster_view, pod_name, namespace))
            
        except Exception as e:
            logging.error(f"Error navigating to pods page: {e}")
    
    def _set_pod_search_filter(self, cluster_view, pod_name: str, namespace: str):
        """Set search filter on the pods page to show the specific pod"""
        try:
            # Check if we have stacked_widget
            if not hasattr(cluster_view, 'stacked_widget'):
                logging.error("ClusterView does not have stacked_widget")
                return
            
            # Get the current page (should be pods page)
            current_widget = cluster_view.stacked_widget.currentWidget()
            
            if not current_widget:
                logging.error("No current widget found in cluster view")
                return
            
            # Check if it's the pods page and has search functionality
            widget_type = type(current_widget).__name__
            logging.info(f"Current widget type: {widget_type}")
            logging.info(f"Has search_bar attribute: {hasattr(current_widget, 'search_bar')}")
            
            # If we still get ClusterView instead of PodsPage, try a different approach
            if widget_type == "ClusterView":
                logging.warning("Still showing ClusterView instead of PodsPage, trying alternative navigation")
                # Try to force navigate to pods page directly
                if hasattr(cluster_view, 'pages') and 'Pods' in cluster_view.pages:
                    pods_page = cluster_view.pages['Pods']
                    cluster_view.stacked_widget.setCurrentWidget(pods_page)
                    logging.info("Switched to pods page directly")
                    # Try again with the pods page
                    QTimer.singleShot(500, lambda: self._apply_search_to_pods_page(pods_page, pod_name, namespace))
                else:
                    logging.error("Could not find Pods page in cluster view pages")
                return
            
            # We have the right page, now try to apply search
            self._apply_search_to_pods_page(current_widget, pod_name, namespace)
                
        except Exception as e:
            logging.error(f"Error setting pod search filter: {e}")
    
    def _apply_search_to_pods_page(self, pods_page, pod_name: str, namespace: str):
        """Apply search to the pods page widget"""
        try:
            logging.info(f"Applying search to pods page: {type(pods_page).__name__}")
            
            if hasattr(pods_page, 'search_bar'):
                logging.info(f"search_bar found: {pods_page.search_bar}")
                
                if pods_page.search_bar:
                    # Set the search text to find the specific pod
                    search_text = pod_name
                    pods_page.search_bar.setText(search_text)
                    
                    # If the pods page has namespace filtering, try to set that too
                    if hasattr(pods_page, 'namespace_combo') and pods_page.namespace_combo:
                        # Try to find and select the namespace
                        combo = pods_page.namespace_combo
                        for i in range(combo.count()):
                            if combo.itemText(i) == namespace:
                                combo.setCurrentIndex(i)
                                break
                    
                    logging.info(f"Set pods page search filter to '{search_text}' in namespace '{namespace}'")
                    return
            
            # Try alternative methods to trigger search
            if hasattr(pods_page, '_perform_global_search'):
                logging.info(f"Using alternative search method for pod '{pod_name}'")
                pods_page._perform_global_search(pod_name.lower())
            elif hasattr(pods_page, 'force_load_data'):
                logging.info(f"Triggering data reload for pods page")
                pods_page.force_load_data()
            else:
                logging.warning("Pods page does not have search functionality")
                
        except Exception as e:
            logging.error(f"Error applying search to pods page: {e}")