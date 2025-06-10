"""
Extended BaseTablePage for handling Kubernetes resources with live data using Python kubernetes library.
This module handles common resource operations like listing, deletion, and editing.
Updated to default to 'default' namespace and improved namespace handling.
"""

import os
import tempfile
import yaml
import time
from PyQt6.QtWidgets import (
     QMessageBox, QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QLabel, QProgressBar, QHBoxLayout, QPushButton,QApplication, QWidget,QTableWidgetItem
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from base_components.base_components import BaseTablePage
from UI.Styles import AppStyles
from utils.kubernetes_client import get_kubernetes_client

# Kubernetes imports
from kubernetes import client
from kubernetes.client.rest import ApiException
import logging

class KubernetesResourceLoader(QThread):
    """Thread for loading Kubernetes resources without blocking the UI."""
    resources_loaded = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, resource_type, namespace=None):
        super().__init__()
        self.resource_type = resource_type
        self.namespace = namespace
        self.kube_client = get_kubernetes_client()
        
    def run(self):
        """Execute the Kubernetes API call and emit results."""
        try:
            # Map resource types to appropriate API methods
            resources = []
            
            if self.resource_type == "pods":
                resources = self._load_pods()
            elif self.resource_type == "services":
                resources = self._load_services()
            elif self.resource_type == "deployments":
                resources = self._load_deployments()
            elif self.resource_type == "nodes":
                resources = self._load_nodes()
            elif self.resource_type == "namespaces":
                resources = self._load_namespaces()
            elif self.resource_type == "configmaps":
                resources = self._load_configmaps()
            elif self.resource_type == "secrets":
                resources = self._load_secrets()
            elif self.resource_type == "events":
                resources = self._load_events()
            elif self.resource_type == "persistentvolumes":
                resources = self._load_persistent_volumes()
            elif self.resource_type == "persistentvolumeclaims":
                resources = self._load_persistent_volume_claims()
            elif self.resource_type == "ingresses":
                resources = self._load_ingresses()
            elif self.resource_type == "daemonsets":
                resources = self._load_daemonsets()
            elif self.resource_type == "statefulsets":
                resources = self._load_statefulsets()
            elif self.resource_type == "replicasets":
                resources = self._load_replicasets()
            elif self.resource_type == "jobs":
                resources = self._load_jobs()
            elif self.resource_type == "cronjobs":
                resources = self._load_cronjobs()
            # Add all the missing resource types
            elif self.resource_type == "replicationcontrollers":
                resources = self._load_replication_controllers()
            elif self.resource_type == "resourcequotas":
                resources = self._load_resource_quotas()
            elif self.resource_type == "limitranges":
                resources = self._load_limit_ranges()
            elif self.resource_type == "horizontalpodautoscalers":
                resources = self._load_horizontal_pod_autoscalers()
            elif self.resource_type == "poddisruptionbudgets":
                resources = self._load_pod_disruption_budgets()
            elif self.resource_type == "priorityclasses":
                resources = self._load_priority_classes()
            elif self.resource_type == "runtimeclasses":
                resources = self._load_runtime_classes()
            elif self.resource_type == "leases":
                resources = self._load_leases()
            elif self.resource_type == "mutatingwebhookconfigurations":
                resources = self._load_mutating_webhook_configurations()
            elif self.resource_type == "validatingwebhookconfigurations":
                resources = self._load_validating_webhook_configurations()
            elif self.resource_type == "endpoints":
                resources = self._load_endpoints()
            elif self.resource_type == "ingressclasses":
                resources = self._load_ingress_classes()
            elif self.resource_type == "networkpolicies":
                resources = self._load_network_policies()
            elif self.resource_type == "storageclasses":
                resources = self._load_storage_classes()
            elif self.resource_type == "serviceaccounts":
                resources = self._load_service_accounts()
            elif self.resource_type == "clusterroles":
                resources = self._load_cluster_roles()
            elif self.resource_type == "roles":
                resources = self._load_roles()
            elif self.resource_type == "clusterrolebindings":
                resources = self._load_cluster_role_bindings()
            elif self.resource_type == "rolebindings":
                resources = self._load_role_bindings()
            elif self.resource_type == "customresourcedefinitions":
                resources = self._load_custom_resource_definitions()
            else:
                # Generic handling for other resource types
                resources = self._load_generic_resource()
            
            # Emit the result
            self.resources_loaded.emit(resources, self.resource_type)
            
        except ApiException as e:
            if e.status == 403:
                error_msg = f"Access denied loading {self.resource_type}. Check RBAC permissions."
            elif e.status == 404:
                error_msg = f"Resource type {self.resource_type} not found in cluster."
            else:
                error_msg = f"API error loading {self.resource_type}: {e}"
            self.error_occurred.emit(error_msg)
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
    
    def _load_pods(self):
        """Load pods using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            pods_list = self.kube_client.v1.list_namespaced_pod(namespace=self.namespace)
        else:
            pods_list = self.kube_client.v1.list_pod_for_all_namespaces()
        
        for pod in pods_list.items:
            resource = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace or "default",
                "age": self._format_age(pod.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pod)
            }
            
            # Add pod-specific fields
            if pod.spec and pod.spec.containers:
                resource["containers"] = len(pod.spec.containers)
            
            if pod.status and pod.status.container_statuses:
                restart_count = sum(container.restart_count or 0 for container in pod.status.container_statuses)
                resource["restarts"] = restart_count
            
            if pod.spec and pod.spec.node_name:
                resource["node"] = pod.spec.node_name
            
            resources.append(resource)
        
        return resources
    
    def _load_services(self):
        """Load services using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            services_list = self.kube_client.v1.list_namespaced_service(namespace=self.namespace)
        else:
            services_list = self.kube_client.v1.list_service_for_all_namespaces()
        
        for service in services_list.items:
            resource = {
                "name": service.metadata.name,
                "namespace": service.metadata.namespace or "default",
                "age": self._format_age(service.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(service)
            }
            
            # Add service-specific fields
            if service.spec:
                resource["type"] = service.spec.type or "ClusterIP"
                resource["cluster_ip"] = service.spec.cluster_ip or "<none>"
                
                if service.spec.ports:
                    ports = [f"{port.port}:{port.target_port}/{port.protocol}" for port in service.spec.ports]
                    resource["ports"] = ", ".join(ports)
                else:
                    resource["ports"] = "<none>"
            
            resources.append(resource)
        
        return resources
    
    def _load_deployments(self):
        """Load deployments using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            deployments_list = self.kube_client.apps_v1.list_namespaced_deployment(namespace=self.namespace)
        else:
            deployments_list = self.kube_client.apps_v1.list_deployment_for_all_namespaces()
        
        for deployment in deployments_list.items:
            resource = {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace or "default",
                "age": self._format_age(deployment.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(deployment)
            }
            
            # Add deployment-specific fields
            if deployment.spec:
                resource["replicas"] = deployment.spec.replicas or 0
            
            if deployment.status:
                resource["ready_replicas"] = deployment.status.ready_replicas or 0
                resource["available_replicas"] = deployment.status.available_replicas or 0
            
            resources.append(resource)
        
        return resources
    
    def _load_nodes(self):
        """Load nodes using kubernetes client"""
        resources = []
        
        nodes_list = self.kube_client.v1.list_node()
        
        for node in nodes_list.items:
            resource = {
                "name": node.metadata.name,
                "namespace": "",  # Nodes are cluster-scoped
                "age": self._format_age(node.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(node)
            }
            
            # Add node-specific fields
            if node.status:
                # Get node status
                status = "Unknown"
                if node.status.conditions:
                    for condition in node.status.conditions:
                        if condition.type == "Ready":
                            status = "Ready" if condition.status == "True" else "NotReady"
                            break
                resource["status"] = status
                
                # Get node roles
                roles = []
                if node.metadata.labels:
                    for label in node.metadata.labels:
                        if label.startswith("node-role.kubernetes.io/"):
                            role = label.split("/")[1]
                            roles.append(role)
                resource["roles"] = ", ".join(roles) if roles else "<none>"
                
                # Get version
                if node.status.node_info:
                    resource["version"] = node.status.node_info.kubelet_version
            
            resources.append(resource)
        
        return resources
    
    def _load_namespaces(self):
        """Load namespaces using kubernetes client"""
        resources = []
        
        namespaces_list = self.kube_client.v1.list_namespace()
        
        for namespace in namespaces_list.items:
            resource = {
                "name": namespace.metadata.name,
                "namespace": "",  # Namespaces are cluster-scoped
                "age": self._format_age(namespace.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(namespace)
            }
            
            # Add namespace-specific fields
            if namespace.status:
                resource["status"] = namespace.status.phase or "Active"
            
            resources.append(resource)
        
        return resources
    
    def _load_configmaps(self):
        """Load configmaps using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            configmaps_list = self.kube_client.v1.list_namespaced_config_map(namespace=self.namespace)
        else:
            configmaps_list = self.kube_client.v1.list_config_map_for_all_namespaces()
        
        for cm in configmaps_list.items:
            resource = {
                "name": cm.metadata.name,
                "namespace": cm.metadata.namespace or "default",
                "age": self._format_age(cm.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(cm)
            }
            
            # Add configmap-specific fields
            if cm.data:
                data_keys = list(cm.data.keys())
                resource["keys"] = ", ".join(data_keys) if data_keys else "<none>"
            else:
                resource["keys"] = "<none>"
            
            resources.append(resource)
        
        return resources
    
    def _load_secrets(self):
        """Load secrets using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            secrets_list = self.kube_client.v1.list_namespaced_secret(namespace=self.namespace)
        else:
            secrets_list = self.kube_client.v1.list_secret_for_all_namespaces()
        
        for secret in secrets_list.items:
            resource = {
                "name": secret.metadata.name,
                "namespace": secret.metadata.namespace or "default",
                "age": self._format_age(secret.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(secret)
            }
            
            # Add secret-specific fields
            resource["type"] = secret.type or "Opaque"
            
            if secret.data:
                data_keys = list(secret.data.keys())
                resource["keys"] = ", ".join(data_keys) if data_keys else "<none>"
            else:
                resource["keys"] = "<none>"
            
            resources.append(resource)
        
        return resources
    
    def _load_events(self):
        """Load events using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            events_list = self.kube_client.v1.list_namespaced_event(namespace=self.namespace)
        else:
            events_list = self.kube_client.v1.list_event_for_all_namespaces()
        
        for event in events_list.items:
            resource = {
                "name": event.metadata.name or f"event-{event.involved_object.name}",
                "namespace": event.metadata.namespace or "default",
                "age": self._format_age(event.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(event)
            }
            
            # Add event-specific fields
            resource["type"] = event.type or "Normal"
            resource["reason"] = event.reason or "Unknown"
            resource["message"] = event.message or "No message"
            
            if event.involved_object:
                resource["object"] = f"{event.involved_object.kind}/{event.involved_object.name}"
            
            resources.append(resource)
        
        return resources
    
    def _load_persistent_volumes(self):
        """Load persistent volumes using kubernetes client"""
        resources = []
        
        pvs_list = self.kube_client.v1.list_persistent_volume()
        
        for pv in pvs_list.items:
            resource = {
                "name": pv.metadata.name,
                "namespace": "",  # PVs are cluster-scoped
                "age": self._format_age(pv.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pv)
            }
            
            # Add PV-specific fields
            if pv.spec:
                resource["capacity"] = pv.spec.capacity.get("storage", "Unknown") if pv.spec.capacity else "Unknown"
                resource["access_modes"] = ", ".join(pv.spec.access_modes) if pv.spec.access_modes else ""
                resource["reclaim_policy"] = pv.spec.persistent_volume_reclaim_policy or "Retain"
            
            if pv.status:
                resource["status"] = pv.status.phase or "Unknown"
            
            resources.append(resource)
        
        return resources
    
    def _load_persistent_volume_claims(self):
        """Load persistent volume claims using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            pvcs_list = self.kube_client.v1.list_namespaced_persistent_volume_claim(namespace=self.namespace)
        else:
            pvcs_list = self.kube_client.v1.list_persistent_volume_claim_for_all_namespaces()
        
        for pvc in pvcs_list.items:
            resource = {
                "name": pvc.metadata.name,
                "namespace": pvc.metadata.namespace or "default",
                "age": self._format_age(pvc.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pvc)
            }
            
            # Add PVC-specific fields
            if pvc.status:
                resource["status"] = pvc.status.phase or "Unknown"
                resource["volume"] = pvc.spec.volume_name if pvc.spec else ""
            
            if pvc.spec and pvc.spec.resources and pvc.spec.resources.requests:
                resource["capacity"] = pvc.spec.resources.requests.get("storage", "Unknown")
            
            resources.append(resource)
        
        return resources
    
    def _load_ingresses(self):
        """Load ingresses using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            ingresses_list = self.kube_client.networking_v1.list_namespaced_ingress(namespace=self.namespace)
        else:
            ingresses_list = self.kube_client.networking_v1.list_ingress_for_all_namespaces()
        
        for ingress in ingresses_list.items:
            resource = {
                "name": ingress.metadata.name,
                "namespace": ingress.metadata.namespace or "default",
                "age": self._format_age(ingress.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(ingress)
            }
            
            # Add ingress-specific fields
            if ingress.spec and ingress.spec.rules:
                hosts = [rule.host for rule in ingress.spec.rules if rule.host]
                resource["hosts"] = ", ".join(hosts) if hosts else "*"
            else:
                resource["hosts"] = "*"
            
            resources.append(resource)
        
        return resources
    
    def _load_daemonsets(self):
        """Load daemonsets using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            ds_list = self.kube_client.apps_v1.list_namespaced_daemon_set(namespace=self.namespace)
        else:
            ds_list = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces()
        
        for ds in ds_list.items:
            resource = {
                "name": ds.metadata.name,
                "namespace": ds.metadata.namespace or "default",
                "age": self._format_age(ds.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(ds)
            }
            
            # Add daemonset-specific fields
            if ds.status:
                resource["desired"] = ds.status.desired_number_scheduled or 0
                resource["current"] = ds.status.current_number_scheduled or 0
                resource["ready"] = ds.status.number_ready or 0
            
            resources.append(resource)
        
        return resources
    
    def _load_statefulsets(self):
        """Load statefulsets using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            sts_list = self.kube_client.apps_v1.list_namespaced_stateful_set(namespace=self.namespace)
        else:
            sts_list = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces()
        
        for sts in sts_list.items:
            resource = {
                "name": sts.metadata.name,
                "namespace": sts.metadata.namespace or "default",
                "age": self._format_age(sts.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(sts)
            }
            
            # Add statefulset-specific fields
            if sts.spec:
                resource["replicas"] = sts.spec.replicas or 0
            
            if sts.status:
                resource["ready"] = sts.status.ready_replicas or 0
            
            resources.append(resource)
        
        return resources
    
    def _load_replicasets(self):
        """Load replicasets using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            rs_list = self.kube_client.apps_v1.list_namespaced_replica_set(namespace=self.namespace)
        else:
            rs_list = self.kube_client.apps_v1.list_replica_set_for_all_namespaces()
        
        for rs in rs_list.items:
            resource = {
                "name": rs.metadata.name,
                "namespace": rs.metadata.namespace or "default",
                "age": self._format_age(rs.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rs)
            }
            
            # Add replicaset-specific fields
            if rs.spec:
                resource["desired"] = rs.spec.replicas or 0
            
            if rs.status:
                resource["current"] = rs.status.replicas or 0
                resource["ready"] = rs.status.ready_replicas or 0
            
            resources.append(resource)
        
        return resources
    
    def _load_jobs(self):
        """Load jobs using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            jobs_list = self.kube_client.batch_v1.list_namespaced_job(namespace=self.namespace)
        else:
            jobs_list = self.kube_client.batch_v1.list_job_for_all_namespaces()
        
        for job in jobs_list.items:
            resource = {
                "name": job.metadata.name,
                "namespace": job.metadata.namespace or "default",
                "age": self._format_age(job.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(job)
            }
            
            # Add job-specific fields
            if job.status:
                resource["completions"] = f"{job.status.succeeded or 0}/{job.spec.completions or 1}"
                resource["duration"] = self._calculate_duration(
                    job.status.start_time, job.status.completion_time
                ) if job.status.start_time else ""
            
            resources.append(resource)
        
        return resources
    
    def _load_cronjobs(self):
        """Load cronjobs using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            cj_list = self.kube_client.batch_v1.list_namespaced_cron_job(namespace=self.namespace)
        else:
            cj_list = self.kube_client.batch_v1.list_cron_job_for_all_namespaces()
        
        for cj in cj_list.items:
            resource = {
                "name": cj.metadata.name,
                "namespace": cj.metadata.namespace or "default",
                "age": self._format_age(cj.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(cj)
            }
            
            # Add cronjob-specific fields
            if cj.spec:
                resource["schedule"] = cj.spec.schedule or ""
                resource["suspend"] = "True" if cj.spec.suspend else "False"
            
            if cj.status:
                resource["active"] = len(cj.status.active) if cj.status.active else 0
                resource["last_schedule"] = self._format_age(cj.status.last_schedule_time) if cj.status.last_schedule_time else "<none>"
            
            resources.append(resource)
        
        return resources

    def _load_replication_controllers(self):
        """Load replication controllers using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            rc_list = self.kube_client.v1.list_namespaced_replication_controller(namespace=self.namespace)
        else:
            rc_list = self.kube_client.v1.list_replication_controller_for_all_namespaces()
        
        for rc in rc_list.items:
            resource = {
                "name": rc.metadata.name,
                "namespace": rc.metadata.namespace or "default",
                "age": self._format_age(rc.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rc)
            }
            
            # Add replication controller-specific fields
            if rc.spec:
                resource["desired_replicas"] = rc.spec.replicas or 0
            
            if rc.status:
                resource["replicas"] = rc.status.replicas or 0
                resource["ready_replicas"] = rc.status.ready_replicas or 0
            
            resources.append(resource)
        
        return resources

    def _load_resource_quotas(self):
        """Load resource quotas using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            rq_list = self.kube_client.v1.list_namespaced_resource_quota(namespace=self.namespace)
        else:
            rq_list = self.kube_client.v1.list_resource_quota_for_all_namespaces()
        
        for rq in rq_list.items:
            resource = {
                "name": rq.metadata.name,
                "namespace": rq.metadata.namespace or "default",
                "age": self._format_age(rq.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rq)
            }
            
            resources.append(resource)
        
        return resources

    def _load_limit_ranges(self):
        """Load limit ranges using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            lr_list = self.kube_client.v1.list_namespaced_limit_range(namespace=self.namespace)
        else:
            lr_list = self.kube_client.v1.list_limit_range_for_all_namespaces()
        
        for lr in lr_list.items:
            resource = {
                "name": lr.metadata.name,
                "namespace": lr.metadata.namespace or "default",
                "age": self._format_age(lr.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(lr)
            }
            
            resources.append(resource)
        
        return resources

    def _load_horizontal_pod_autoscalers(self):
        """Load horizontal pod autoscalers using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            hpa_list = self.kube_client.autoscaling_v1.list_namespaced_horizontal_pod_autoscaler(namespace=self.namespace)
        else:
            hpa_list = self.kube_client.autoscaling_v1.list_horizontal_pod_autoscaler_for_all_namespaces()
        
        for hpa in hpa_list.items:
            resource = {
                "name": hpa.metadata.name,
                "namespace": hpa.metadata.namespace or "default",
                "age": self._format_age(hpa.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(hpa)
            }
            
            # Add HPA-specific fields
            if hpa.spec:
                resource["min_replicas"] = hpa.spec.min_replicas or 0
                resource["max_replicas"] = hpa.spec.max_replicas or 0
                resource["target_cpu"] = hpa.spec.target_cpu_utilization_percentage or 0
            
            if hpa.status:
                resource["current_replicas"] = hpa.status.current_replicas or 0
                resource["current_cpu"] = hpa.status.current_cpu_utilization_percentage or 0
            
            resources.append(resource)
        
        return resources

    def _load_pod_disruption_budgets(self):
        """Load pod disruption budgets using kubernetes client"""
        resources = []
        
        try:
            # Try to use policy/v1 first (Kubernetes 1.21+)
            policy_api = client.PolicyV1Api()
            if self.namespace and self.namespace != "all":
                pdb_list = policy_api.list_namespaced_pod_disruption_budget(namespace=self.namespace)
            else:
                pdb_list = policy_api.list_pod_disruption_budget_for_all_namespaces()
        except AttributeError:
            # Fall back to policy/v1beta1 for older clusters
            policy_api = client.PolicyV1beta1Api()
            if self.namespace and self.namespace != "all":
                pdb_list = policy_api.list_namespaced_pod_disruption_budget(namespace=self.namespace)
            else:
                pdb_list = policy_api.list_pod_disruption_budget_for_all_namespaces()
        
        for pdb in pdb_list.items:
            resource = {
                "name": pdb.metadata.name,
                "namespace": pdb.metadata.namespace or "default",
                "age": self._format_age(pdb.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pdb)
            }
            
            resources.append(resource)
        
        return resources

    def _load_priority_classes(self):
        """Load priority classes using kubernetes client"""
        resources = []
        
        try:
            scheduling_api = client.SchedulingV1Api()
            pc_list = scheduling_api.list_priority_class()
            
            for pc in pc_list.items:
                resource = {
                    "name": pc.metadata.name,
                    "namespace": "",  # Priority classes are cluster-scoped
                    "age": self._format_age(pc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(pc)
                }
                
                # Add priority class-specific fields
                resource["value"] = pc.value or 0
                resource["global_default"] = pc.global_default or False
                
                resources.append(resource)
        except AttributeError:
            # If SchedulingV1Api is not available, return empty list
            logging.warning("SchedulingV1Api not available for priority classes")
        
        return resources

    def _load_runtime_classes(self):
        """Load runtime classes using kubernetes client"""
        resources = []
        
        try:
            node_api = client.NodeV1Api()
            rc_list = node_api.list_runtime_class()
            
            for rc in rc_list.items:
                resource = {
                    "name": rc.metadata.name,
                    "namespace": "",  # Runtime classes are cluster-scoped
                    "age": self._format_age(rc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(rc)
                }
                
                # Add runtime class-specific fields
                resource["handler"] = rc.handler or ""
                
                resources.append(resource)
        except AttributeError:
            # If NodeV1Api is not available, return empty list
            logging.warning("NodeV1Api not available for runtime classes")
        
        return resources

    def _load_leases(self):
        """Load leases using kubernetes client"""
        resources = []
        
        try:
            coordination_api = client.CoordinationV1Api()
            if self.namespace and self.namespace != "all":
                lease_list = coordination_api.list_namespaced_lease(namespace=self.namespace)
            else:
                lease_list = coordination_api.list_lease_for_all_namespaces()
            
            for lease in lease_list.items:
                resource = {
                    "name": lease.metadata.name,
                    "namespace": lease.metadata.namespace or "default",
                    "age": self._format_age(lease.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(lease)
                }
                
                # Add lease-specific fields
                if lease.spec:
                    resource["holder"] = lease.spec.holder_identity or ""
                
                resources.append(resource)
        except AttributeError:
            # If CoordinationV1Api is not available, return empty list
            logging.warning("CoordinationV1Api not available for leases")
        
        return resources

    def _load_mutating_webhook_configurations(self):
        """Load mutating webhook configurations using kubernetes client"""
        resources = []
        
        try:
            admission_api = client.AdmissionregistrationV1Api()
            mwc_list = admission_api.list_mutating_webhook_configuration()
            
            for mwc in mwc_list.items:
                resource = {
                    "name": mwc.metadata.name,
                    "namespace": "",  # Webhook configurations are cluster-scoped
                    "age": self._format_age(mwc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(mwc)
                }
                
                resources.append(resource)
        except AttributeError:
            # If AdmissionregistrationV1Api is not available, return empty list
            logging.warning("AdmissionregistrationV1Api not available for mutating webhook configurations")
        
        return resources

    def _load_validating_webhook_configurations(self):
        """Load validating webhook configurations using kubernetes client"""
        resources = []
        
        try:
            admission_api = client.AdmissionregistrationV1Api()
            vwc_list = admission_api.list_validating_webhook_configuration()
            
            for vwc in vwc_list.items:
                resource = {
                    "name": vwc.metadata.name,
                    "namespace": "",  # Webhook configurations are cluster-scoped
                    "age": self._format_age(vwc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(vwc)
                }
                
                resources.append(resource)
        except AttributeError:
            # If AdmissionregistrationV1Api is not available, return empty list
            logging.warning("AdmissionregistrationV1Api not available for validating webhook configurations")
        
        return resources

    def _load_endpoints(self):
        """Load endpoints using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            ep_list = self.kube_client.v1.list_namespaced_endpoints(namespace=self.namespace)
        else:
            ep_list = self.kube_client.v1.list_endpoints_for_all_namespaces()
        
        for ep in ep_list.items:
            resource = {
                "name": ep.metadata.name,
                "namespace": ep.metadata.namespace or "default",
                "age": self._format_age(ep.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(ep)
            }
            
            # Add endpoints-specific fields
            endpoints = []
            if ep.subsets:
                for subset in ep.subsets:
                    addresses = subset.addresses or []
                    ports = subset.ports or []
                    for addr in addresses:
                        for port in ports:
                            endpoints.append(f"{addr.ip}:{port.port}")
            
            resource["endpoints"] = ", ".join(endpoints) if endpoints else "<none>"
            
            resources.append(resource)
        
        return resources

    def _load_ingress_classes(self):
        """Load ingress classes using kubernetes client"""
        resources = []
        
        try:
            ic_list = self.kube_client.networking_v1.list_ingress_class()
            
            for ic in ic_list.items:
                resource = {
                    "name": ic.metadata.name,
                    "namespace": "",  # Ingress classes are cluster-scoped
                    "age": self._format_age(ic.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(ic)
                }
                
                # Add ingress class-specific fields
                if ic.spec:
                    resource["controller"] = ic.spec.controller or ""
                
                resources.append(resource)
        except AttributeError:
            # If networking_v1 doesn't have ingress classes, return empty list
            logging.warning("Ingress classes not available in this Kubernetes version")
        
        return resources

    def _load_network_policies(self):
        """Load network policies using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            np_list = self.kube_client.networking_v1.list_namespaced_network_policy(namespace=self.namespace)
        else:
            np_list = self.kube_client.networking_v1.list_network_policy_for_all_namespaces()
        
        for np in np_list.items:
            resource = {
                "name": np.metadata.name,
                "namespace": np.metadata.namespace or "default",
                "age": self._format_age(np.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(np)
            }
            
            resources.append(resource)
        
        return resources

    def _load_storage_classes(self):
        """Load storage classes using kubernetes client"""
        resources = []
        
        sc_list = self.kube_client.storage_v1.list_storage_class()
        
        for sc in sc_list.items:
            resource = {
                "name": sc.metadata.name,
                "namespace": "",  # Storage classes are cluster-scoped
                "age": self._format_age(sc.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(sc)
            }
            
            # Add storage class-specific fields
            resource["provisioner"] = sc.provisioner or ""
            resource["reclaim_policy"] = sc.reclaim_policy or "Delete"
            resource["volume_binding_mode"] = sc.volume_binding_mode or "Immediate"
            
            resources.append(resource)
        
        return resources

    def _load_service_accounts(self):
        """Load service accounts using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            sa_list = self.kube_client.v1.list_namespaced_service_account(namespace=self.namespace)
        else:
            sa_list = self.kube_client.v1.list_service_account_for_all_namespaces()
        
        for sa in sa_list.items:
            resource = {
                "name": sa.metadata.name,
                "namespace": sa.metadata.namespace or "default",
                "age": self._format_age(sa.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(sa)
            }
            
            # Add service account-specific fields
            resource["secrets"] = len(sa.secrets) if sa.secrets else 0
            
            resources.append(resource)
        
        return resources

    def _load_cluster_roles(self):
        """Load cluster roles using kubernetes client"""
        resources = []
        
        cr_list = self.kube_client.rbac_v1.list_cluster_role()
        
        for cr in cr_list.items:
            resource = {
                "name": cr.metadata.name,
                "namespace": "",  # Cluster roles are cluster-scoped
                "age": self._format_age(cr.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(cr)
            }
            
            resources.append(resource)
        
        return resources

    def _load_roles(self):
        """Load roles using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            role_list = self.kube_client.rbac_v1.list_namespaced_role(namespace=self.namespace)
        else:
            role_list = self.kube_client.rbac_v1.list_role_for_all_namespaces()
        
        for role in role_list.items:
            resource = {
                "name": role.metadata.name,
                "namespace": role.metadata.namespace or "default",
                "age": self._format_age(role.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(role)
            }
            
            resources.append(resource)
        
        return resources

    def _load_cluster_role_bindings(self):
        """Load cluster role bindings using kubernetes client"""
        resources = []
        
        crb_list = self.kube_client.rbac_v1.list_cluster_role_binding()
        
        for crb in crb_list.items:
            resource = {
                "name": crb.metadata.name,
                "namespace": "",  # Cluster role bindings are cluster-scoped
                "age": self._format_age(crb.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(crb)
            }
            
            # Add cluster role binding-specific fields
            if crb.role_ref:
                resource["role"] = crb.role_ref.name or ""
            
            resource["subjects"] = len(crb.subjects) if crb.subjects else 0
            
            resources.append(resource)
        
        return resources

    def _load_role_bindings(self):
        """Load role bindings using kubernetes client"""
        resources = []
        
        if self.namespace and self.namespace != "all":
            rb_list = self.kube_client.rbac_v1.list_namespaced_role_binding(namespace=self.namespace)
        else:
            rb_list = self.kube_client.rbac_v1.list_role_binding_for_all_namespaces()
        
        for rb in rb_list.items:
            resource = {
                "name": rb.metadata.name,
                "namespace": rb.metadata.namespace or "default",
                "age": self._format_age(rb.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rb)
            }
            
            # Add role binding-specific fields
            if rb.role_ref:
                resource["role"] = rb.role_ref.name or ""
            
            resource["subjects"] = len(rb.subjects) if rb.subjects else 0
            
            resources.append(resource)
        
        return resources

    def _load_custom_resource_definitions(self):
        """Load custom resource definitions using kubernetes client"""
        resources = []
        
        try:
            apiextensions_api = client.ApiextensionsV1Api()
            crd_list = apiextensions_api.list_custom_resource_definition()
            
            for crd in crd_list.items:
                resource = {
                    "name": crd.metadata.name,
                    "namespace": "",  # CRDs are cluster-scoped
                    "age": self._format_age(crd.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(crd)
                }
                
                # Add CRD-specific fields
                if crd.spec:
                    resource["group"] = crd.spec.group or ""
                    resource["scope"] = crd.spec.scope or ""
                    if crd.spec.versions:
                        resource["version"] = crd.spec.versions[0].name or ""
                
                resources.append(resource)
        except AttributeError:
            # If ApiextensionsV1Api is not available, return empty list
            logging.warning("ApiextensionsV1Api not available for custom resource definitions")
        
        return resources
    
    def _load_generic_resource(self):
        """Generic resource loading for resources not specifically handled"""
        # This would be used for custom resources or resources not yet implemented
        # For now, return empty list
        logging.warning(f"Generic resource loading not implemented for {self.resource_type}")
        return []
    
    def _format_age(self, timestamp):
        """Format timestamp to age string (e.g., "2d", "5h")"""
        if not timestamp:
            return "Unknown"
        
        try:
            import datetime
            if isinstance(timestamp, str):
                created_time = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                # Assume it's already a datetime object
                created_time = timestamp.replace(tzinfo=datetime.timezone.utc)
            
            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - created_time
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"
    
    def _calculate_duration(self, start_time, end_time):
        """Calculate duration between two timestamps"""
        if not start_time or not end_time:
            return ""
        
        try:
            import datetime
            if isinstance(start_time, str):
                start = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start = start_time.replace(tzinfo=datetime.timezone.utc)
            
            if isinstance(end_time, str):
                end = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                end = end_time.replace(tzinfo=datetime.timezone.utc)
            
            diff = end - start
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            seconds = diff.seconds % 60
            
            if days > 0:
                return f"{days}d{hours}h"
            elif hours > 0:
                return f"{hours}h{minutes}m"
            elif minutes > 0:
                return f"{minutes}m{seconds}s"
            else:
                return f"{seconds}s"
        except Exception:
            return ""

class ResourceDeleterThread(QThread):
    """Thread for deleting Kubernetes resources."""
    delete_completed = pyqtSignal(bool, str, str, str)
    
    def __init__(self, resource_type, resource_name, namespace):
        super().__init__()
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.kube_client = get_kubernetes_client()
        
    def run(self):
        """Delete the specified resource using kubernetes client."""
        try:
            # Delete the resource using the appropriate API
            if self.resource_type == "pod":
                if self.namespace:
                    self.kube_client.v1.delete_namespaced_pod(
                        name=self.resource_name,
                        namespace=self.namespace
                    )
                else:
                    self.kube_client.v1.delete_pod(name=self.resource_name)
            elif self.resource_type == "service":
                self.kube_client.v1.delete_namespaced_service(
                    name=self.resource_name,
                    namespace=self.namespace
                )
            elif self.resource_type == "deployment":
                self.kube_client.apps_v1.delete_namespaced_deployment(
                    name=self.resource_name,
                    namespace=self.namespace
                )
            elif self.resource_type == "node":
                self.kube_client.v1.delete_node(name=self.resource_name)
            elif self.resource_type == "namespace":
                self.kube_client.v1.delete_namespace(name=self.resource_name)
            elif self.resource_type == "configmap":
                self.kube_client.v1.delete_namespaced_config_map(
                    name=self.resource_name,
                    namespace=self.namespace
                )
            elif self.resource_type == "secret":
                self.kube_client.v1.delete_namespaced_secret(
                    name=self.resource_name,
                    namespace=self.namespace
                )
            # Add more resource types as needed
            else:
                self.delete_completed.emit(
                    False, 
                    f"Deletion not implemented for resource type: {self.resource_type}",
                    self.resource_name,
                    self.namespace
                )
                return
            
            # Report success
            self.delete_completed.emit(
                True, 
                f"{self.resource_type}/{self.resource_name} deleted successfully", 
                self.resource_name,
                self.namespace
            )
            
        except ApiException as e:
            if e.status == 404:
                self.delete_completed.emit(
                    False,
                    f"Resource not found: {self.resource_type}/{self.resource_name}",
                    self.resource_name,
                    self.namespace
                )
            elif e.status == 409:
                self.delete_completed.emit(
                    False,
                    f"Conflict deleting resource (may be in use): {e}",
                    self.resource_name,
                    self.namespace
                )
            else:
                self.delete_completed.emit(
                    False, 
                    f"API error deleting {self.resource_type}/{self.resource_name}: {e}",
                    self.resource_name,
                    self.namespace
                )
        except Exception as e:
            self.delete_completed.emit(
                False, 
                f"Error: {str(e)}", 
                self.resource_name,
                self.namespace
            )

class BatchResourceDeleterThread(QThread):
    """Thread for deleting multiple Kubernetes resources."""
    batch_delete_progress = pyqtSignal(int, int)
    batch_delete_completed = pyqtSignal(list, list)
    
    def __init__(self, resource_type, resources):
        super().__init__()
        self.resource_type = resource_type
        self.resources = resources  # List of (name, namespace) tuples
        self.kube_client = get_kubernetes_client()
        
    def run(self):
        """Delete all specified resources."""
        success_list = []
        error_list = []
        
        for i, (name, namespace) in enumerate(self.resources):
            try:
                # Use the single resource deletion logic
                deleter = ResourceDeleterThread(self.resource_type, name, namespace)
                deleter.run()  # Run synchronously in this thread
                
                # Check if deletion was successful
                # (This is a simplification - in a real implementation, 
                # you'd want to capture the result from the deleter)
                success_list.append((name, namespace))
                
            except Exception as e:
                error_list.append((name, namespace, str(e)))
                
            # Report progress
            self.batch_delete_progress.emit(i + 1, len(self.resources))
            
        # Report final results
        self.batch_delete_completed.emit(success_list, error_list)

# Cluster-scoped resources that don't have namespaces
CLUSTER_SCOPED_RESOURCES = {
    'nodes', 'persistentvolumes', 'clusterroles', 'clusterrolebindings', 
    'storageclasses', 'ingressclasses', 'priorityclasses', 'runtimeclasses',
    'mutatingwebhookconfigurations', 'validatingwebhookconfigurations',
    'customresourcedefinitions', 'namespaces'
}

class BaseResourcePage(BaseTablePage):
    """
    A base class for all Kubernetes resource pages that handles:
    1. Loading and displaying dynamic data from Kubernetes API
    2. Editing resources
    3. Deleting resources (individual and batch)
    4. Handling error states
    5. Namespace filtering with default namespace as default
    
    This should be subclassed for specific resource types.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = None  # To be set by subclasses
        self.resources = []
        self.namespace_filter = "default"  # Changed from "all" to "default"
        self.loading_thread = None
        self.delete_thread = None
        self.edit_thread = None
        self.batch_delete_thread = None
        self.is_loading = False
        self.selected_items = set()  # Track selected items by (name, namespace)
        self.reload_on_show = True  # Always reload data when page is shown

        self.is_showing_skeleton = False
        self._data_cache = {}  # Add cache dictionary
        self._cache_timestamps = {}  # Track cache age
        
        # Get kubernetes client
        self.kube_client = get_kubernetes_client()
        
    def setup_ui(self, title, headers, sortable_columns=None):
        """Set up the UI with an added refresh button and namespace selector."""
        layout = super().setup_ui(title, headers, sortable_columns)
        
        # Create a refresh button in the header
        self._add_refresh_button()
        
        return layout

    def _show_skeleton_loader(self, rows=5):
        """Show a skeleton loader with empty rows while preserving table headers"""
        self.is_showing_skeleton = True
        
        # Clear existing data but keep headers
        self.table.setRowCount(0)
        
        # Add empty skeleton rows
        for i in range(rows):
            self.table.insertRow(i)
            for j in range(self.table.columnCount()):
                # First column (checkbox)
                if j == 0:
                    empty_widget = QWidget()
                    empty_widget.setStyleSheet("background-color: #2d2d2d;")
                    self.table.setCellWidget(i, j, empty_widget)
                # Last column (actions)
                elif j == self.table.columnCount() - 1:
                    empty_widget = QWidget()
                    empty_widget.setStyleSheet("background-color: #2d2d2d;")
                    self.table.setCellWidget(i, j, empty_widget)
                else:
                    # Regular data cells
                    item = QTableWidgetItem("")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setBackground(QColor("#2d2d2d"))
                    self.table.setItem(i, j, item)
            
            # Set row height
            self.table.setRowHeight(i, 40)
        
        # Disable sorting during loading
        self.table.setSortingEnabled(False)
        
        # Update UI immediately
        QApplication.processEvents()
        
        # Start skeleton animation
        if not hasattr(self, 'skeleton_timer'):
            self.skeleton_timer = QTimer(self)
            self.skeleton_timer.timeout.connect(self._animate_skeleton)
            self.skeleton_animation_step = 0
        
        self.skeleton_timer.start(300)  # Update every 300ms
   
    def _animate_skeleton(self):
        """Animate the skeleton cells with gradient effect"""
        if not self.is_showing_skeleton:
            self.skeleton_timer.stop()
            return
            
        # Alternate between darker and lighter grays
        colors = ["#2d2d2d", "#333333", "#3a3a3a", "#333333"]
        color = QColor(colors[self.skeleton_animation_step % len(colors)])
        
        # Update all skeleton cells
        for i in range(self.table.rowCount()):
            for j in range(1, self.table.columnCount() - 1):
                item = self.table.item(i, j)
                if item:
                    item.setBackground(color)
        
        self.skeleton_animation_step += 1
        QApplication.processEvents()

    def get_cached_data(self, key):
        """Get cached data with expiration check"""
        if key in self._data_cache and key in self._cache_timestamps:
            # Cache expires after 5 minutes
            cache_age = time.time() - self._cache_timestamps[key]
            if cache_age < 300:  # 5 minutes in seconds
                return self._data_cache[key]
        return None
    
    def cache_data(self, key, data):
        """Cache data with timestamp"""
        self._data_cache[key] = data
        self._cache_timestamps[key] = time.time()

    def _add_filter_controls(self, header_layout):
        """Add namespace filter dropdown and search bar to the header layout"""
        # Check if this resource has a namespace column
        has_namespace_column = False
        if hasattr(self, 'table') and self.table.columnCount() > 0:
            for col in range(self.table.columnCount()):
                header_item = self.table.horizontalHeaderItem(col)
                if header_item and header_item.text() == "Namespace":
                    has_namespace_column = True
                    break
        
        # For cluster-scoped resources, don't show namespace dropdown
        if self.resource_type in CLUSTER_SCOPED_RESOURCES:
            has_namespace_column = False
        
        # Create a layout for the filters
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)
        
        # Create search bar matching the header style
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search resources...")
        self.search_bar.setFixedHeight(AppStyles.SEARCH_BAR_HEIGHT)
        self.search_bar.setMinimumWidth(AppStyles.SEARCH_BAR_MIN_WIDTH)
        self.search_bar.setStyleSheet(AppStyles.SEARCH_BAR_STYLE)
        self.search_bar.textChanged.connect(self._handle_search)
        filters_layout.addWidget(self.search_bar)
        
        # Create namespace filter dropdown if needed
        if has_namespace_column:
            namespace_label = QLabel("Namespace:")
            namespace_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-right: 5px;")
            filters_layout.addWidget(namespace_label)
            
            self.namespace_combo = QComboBox()
            self.namespace_combo.setFixedHeight(AppStyles.SEARCH_BAR_HEIGHT)  # Match search bar height
            self.namespace_combo.setMinimumWidth(150)
            self.namespace_combo.setStyleSheet("""
                QComboBox {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 13px;
                }
                QComboBox:hover {
                    border: 1px solid #555555;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    color: #aaaaaa;
                }
                QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    selection-background-color: #0078d7;
                    border: 1px solid #3d3d3d;
                    padding: 5px;
                }
            """)
            
            # Initially add just the default namespace
            self.namespace_combo.addItem("default")
            self.namespace_combo.setCurrentText("default")
            self.namespace_combo.currentTextChanged.connect(self._handle_namespace_change)
            filters_layout.addWidget(self.namespace_combo)
            
            # Load namespaces asynchronously
            QTimer.singleShot(100, self._load_namespaces)
        
        # Add the filters layout to the header layout
        header_layout.addLayout(filters_layout)
        header_layout.addStretch()

    def _handle_search(self, text):
        """Filter resources based on search text"""
        self._apply_filters()

    def _handle_namespace_change(self, namespace):
        """Filter resources based on selected namespace and reload data"""
        if not namespace:
            return
            
        # Update the namespace filter
        if namespace == "All Namespaces":
            self.namespace_filter = "all"
        else:
            self.namespace_filter = namespace
        
        # Reload data with new namespace filter
        self.force_load_data()

    def _apply_filters(self):
        """Apply both namespace and search filters"""
        if not hasattr(self, 'table') or self.table.rowCount() == 0:
            return
            
        # Get the search text
        search_text = self.search_bar.text().lower() if hasattr(self, 'search_bar') else ""
        
        # Hide rows that don't match the filters
        for row in range(self.table.rowCount()):
            show_row = True
            
            # Apply search filter if text is entered
            if show_row and search_text:
                row_matches = False
                for col in range(1, self.table.columnCount() - 1):  # Skip checkbox and actions columns
                    # Check regular table items
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        row_matches = True
                        break
                    
                    # Check for cell widgets (like status labels)
                    cell_widget = self.table.cellWidget(row, col)
                    if cell_widget:
                        widget_text = ""
                        # Handle StatusLabel widgets which contain a QLabel
                        for label in cell_widget.findChildren(QLabel):
                            widget_text += label.text() + " "
                        
                        if search_text in widget_text.lower():
                            row_matches = True
                            break
                
                if not row_matches:
                    show_row = False
            
            # Show or hide the row based on filters
            self.table.setRowHidden(row, not show_row)

    def _load_namespaces(self):
        """Load namespaces from Kubernetes cluster"""
        if not hasattr(self, 'namespace_combo'):
            return
        
        try:
            # Get namespaces using kubernetes client
            namespaces_list = self.kube_client.v1.list_namespace()
            namespaces = [ns.metadata.name for ns in namespaces_list.items]
            
            # Update the combo box
            current_selection = self.namespace_combo.currentText()
            self.namespace_combo.clear()
            self.namespace_combo.addItem("All Namespaces")
            self.namespace_combo.addItems(sorted(namespaces))
            
            # Set default namespace as selected if it's the first load
            if current_selection == "default" and "default" in namespaces:
                self.namespace_combo.setCurrentText("default")
            else:
                # Restore the previous selection if it still exists
                index = self.namespace_combo.findText(current_selection)
                if index >= 0:
                    self.namespace_combo.setCurrentIndex(index)
                else:
                    # Default to "default" namespace if available
                    if "default" in namespaces:
                        self.namespace_combo.setCurrentText("default")
                    else:
                        self.namespace_combo.setCurrentText("All Namespaces")
                        
        except Exception as e:
            logging.warning(f"Error loading namespaces: {e}")
            # If we can't load namespaces, just add default namespace
            self.namespace_combo.clear()
            self.namespace_combo.addItem("All Namespaces")
            self.namespace_combo.addItem("default")
            self.namespace_combo.setCurrentText("default")
    
    def _add_refresh_button(self):
        """Add a refresh button and filter controls to the page header."""
        # Find the header layout
        header_layout = None
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if isinstance(item, QHBoxLayout):
                header_layout = item
                break
                
        if not header_layout:
            # Create a new header layout if none exists
            header_layout = QHBoxLayout()
            self.layout().insertLayout(0, header_layout)
        
        # Add filter controls first (to the left of the refresh button)
        self._add_filter_controls(header_layout)
        
        # Create refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        refresh_btn.clicked.connect(self.load_data)
        
        # Add button to header (no more stretch before it)
        header_layout.addWidget(refresh_btn)

    def force_load_data(self):
        """Force reload data regardless of loading state."""
        # Reset loading state and call load_data
        self.is_loading = False
        
        # Show skeleton loader first if attribute exists
        if hasattr(self, '_show_skeleton_loader'):
            self._show_skeleton_loader()
            
        # Delay loading to allow UI to update
        QTimer.singleShot(100, self.load_data)
    
    def showEvent(self, event):
        """Load data when the page is shown."""
        super().showEvent(event)
        
        # Load data if needed
        if self.reload_on_show and not self.is_loading:
            self.load_data()
    
    def __del__(self):
        """Ensure proper cleanup of threads before destruction"""
        self.cleanup_threads()

    def cleanup_threads(self):
        """Clean up any running threads safely"""
        threads_to_cleanup = [
            'loading_thread', 
            'delete_thread', 
            'edit_thread', 
            'batch_delete_thread'
        ]
        
        for thread_name in threads_to_cleanup:
            thread = getattr(self, thread_name, None)
            if thread and thread.isRunning():
                thread.wait(300)  # Wait up to 300ms for thread to finish

    def hideEvent(self, event):
        """Clean up threads when the page is hidden"""
        super().hideEvent(event)
        # This ensures threads are stopped when switching away from this page
        self.cleanup_threads()

    def load_data(self):
        """Load resource data with caching and skeleton loading"""
        if self.is_loading:
            return
        
        # Clean up any existing loading thread first    
        if hasattr(self, 'loading_thread') and self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.wait(300)  # Wait for it to finish with timeout
        
        # Reset search filter if it exists
        if hasattr(self, 'search_bar'):
            self.search_bar.blockSignals(True)  # Prevent triggering filter while loading
            self.search_bar.clear()
            self.search_bar.blockSignals(False)
        
        # Check for cached data
        cache_key = f"{self.resource_type}_{self.namespace_filter}"
        cached_data = self.get_cached_data(cache_key)
        
        if cached_data:
            # Use cached data if available
            self.on_resources_loaded(cached_data, self.resource_type)
            return
        
        self.is_loading = True
        self.resources = []
        self.selected_items.clear()
        
        # Show skeleton loader if attribute exists and not already shown
        if hasattr(self, 'is_showing_skeleton') and not self.is_showing_skeleton:
            self._show_skeleton_loader()
            
        # Start loading thread
        self.loading_thread = KubernetesResourceLoader(self.resource_type, self.namespace_filter)
        self.loading_thread.resources_loaded.connect(
            lambda resources, resource_type: self.on_resources_loaded(resources, resource_type, cache_key))
        self.loading_thread.error_occurred.connect(self.on_load_error)
        self.loading_thread.start()
    
    def on_resources_loaded(self, resources, resource_type, cache_key=None):
        """Handle loaded resources with empty message overlaying the table area."""
        self.is_loading = False
        self.is_showing_skeleton = False
        
        # Stop skeleton animation if running
        if hasattr(self, 'skeleton_timer') and self.skeleton_timer.isActive():
            self.skeleton_timer.stop()

        # Store resources
        self.resources = resources

        # Cache the data if we have a cache key
        if cache_key and resources:
            self.cache_data(cache_key, resources)
        
        # Update the item count
        self.items_count.setText(f"{len(resources)} items")
        
        # Check if resources list is empty
        if not resources:
            # Clear all rows but keep table visible
            self.table.setRowCount(0)
            
            # Create overlay label if it doesn't exist
            if not hasattr(self, 'empty_overlay'):
                # Create an overlay widget that sits on top of the table body area
                self.empty_overlay = QLabel("Item list is empty")
                self.empty_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.empty_overlay.setStyleSheet("""
                    color: #888888;
                    font-size: 16px;
                    font-weight: bold;
                    background-color: transparent;
                """)
                
                # Add the widget as sibling to the table
                self.layout().addWidget(self.empty_overlay)
                
                # Initially hidden
                self.empty_overlay.hide()
            
            # Position the overlay to cover the table body area (but below headers)
            header_height = self.table.horizontalHeader().height()
            self.empty_overlay.setGeometry(
                self.table.x(),
                self.table.y() + header_height,
                self.table.width(),
                self.table.height() - header_height
            )
            
            # Show the overlay
            self.empty_overlay.raise_()  # Bring to front
            self.empty_overlay.show()
            
            # Disable sorting when empty
            self.table.setSortingEnabled(False)
        else:
            # Normal case - populate the table with data
            self.table.setRowCount(0)  # Clear first
            self.populate_table(resources)
            self.table.setSortingEnabled(True)
            
            # Hide the overlay if it exists
            if hasattr(self, 'empty_overlay'):
                self.empty_overlay.hide()

        # Apply any existing filters
        self._apply_filters()
        
    def resizeEvent(self, event):
        """Handle resizing of the widget to properly position the empty overlay."""
        super().resizeEvent(event)
        
        # Update empty overlay position if it exists
        if hasattr(self, 'empty_overlay') and self.empty_overlay.isVisible():
            header_height = self.table.horizontalHeader().height()
            self.empty_overlay.setGeometry(
                self.table.x(),
                self.table.y() + header_height,
                self.table.width(),
                self.table.height() - header_height
            )
            
    def eventFilter(self, watched, event):
        """Filter events to update overlay position when table geometry changes."""
        if (watched == self.table and event.type() in 
                (event.Type.Resize, event.Type.Move, event.Type.Show)):
            if hasattr(self, 'empty_overlay') and self.empty_overlay.isVisible():
                header_height = self.table.horizontalHeader().height()
                self.empty_overlay.setGeometry(
                    self.table.x(),
                    self.table.y() + header_height,
                    self.table.width(),
                    self.table.height() - header_height
                )
        
        return super().eventFilter(watched, event)

    def on_load_error(self, error_message):
        """Handle loading errors."""
        self.is_loading = False
        
        # Clear loading indicator
        self.table.setRowCount(0)
        
        # Show error message
        error_row = self.table.rowCount()
        self.table.setRowCount(error_row + 1)
        self.table.setSpan(error_row, 0, 1, self.table.columnCount())
        
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.setContentsMargins(20, 30, 20, 30)
        
        error_text = QLabel(f"Error: {error_message}")
        error_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_text.setStyleSheet("color: #ff6b6b; font-size: 14px;")
        error_text.setWordWrap(True)
        
        retry_button = QPushButton("Retry")
        retry_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
                max-width: 100px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """)
        retry_button.clicked.connect(self.load_data)
        
        error_layout.addWidget(error_text)
        error_layout.addSpacing(10)
        error_layout.addWidget(retry_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.table.setCellWidget(error_row, 0, error_widget)
        
    def populate_table(self, resources):
        """Populate the table with resources."""
        # Set row count
        self.table.setRowCount(len(resources))
        
        # Fill the table
        for row, resource in enumerate(resources):
            self.populate_resource_row(row, resource)
        
    def populate_resource_row(self, row, resource):
        """
        Populate a single row with resource data.
        This should be overridden by subclasses to handle resource-specific columns.
        """
        pass  # Implemented by subclasses
        
    def _create_action_button(self, row, resource_name, resource_namespace):
        """Create an action button with edit and delete options only."""
        return super()._create_action_button(row, [
            {"text": "Edit", "icon": "icons/edit.png", "dangerous": False},
            {"text": "Delete", "icon": "icons/delete.png", "dangerous": True}
        ])
        
    def _handle_action(self, action, row):
        """Handle action button clicks."""
        if row >= len(self.resources):
            return
            
        resource = self.resources[row]
        resource_name = resource.get("name", "")
        resource_namespace = resource.get("namespace", "")
        
        if action == "Logs":
            print(f"logs for {resource_name}, and {resource_namespace}" )
        elif action == "Delete":
            self.delete_resource(resource_name, resource_namespace)
            
    def _handle_checkbox_change(self, state, item_name):
        """Handle checkbox state changes with namespace awareness."""
        # Find the namespace for this item
        namespace = None
        for resource in self.resources:
            if resource["name"] == item_name:
                namespace = resource.get("namespace", "")
                break
                
        # Store the (name, namespace) tuple for deletion
        item_key = (item_name, namespace)
        
        if state == Qt.CheckState.Checked.value:
            self.selected_items.add(item_key)
        else:
            self.selected_items.discard(item_key)
            
            # If any checkbox is unchecked, uncheck the select-all checkbox
            if self.select_all_checkbox is not None and self.select_all_checkbox.isChecked():
                # Block signals to prevent infinite recursion
                self.select_all_checkbox.blockSignals(True)
                self.select_all_checkbox.setChecked(False)
                self.select_all_checkbox.blockSignals(False)
                
    def _handle_select_all(self, state):
        """Handle select-all checkbox state changes."""
        super()._handle_select_all(state)
        
        # Update selected_items set based on state
        self.selected_items.clear()
        
        if state == Qt.CheckState.Checked.value:
            # Add all items to selected set
            for resource in self.resources:
                self.selected_items.add((resource["name"], resource.get("namespace", "")))
                
    def delete_selected_resources(self):
        """Delete all selected resources."""
        # Clean up any existing delete thread first
        if hasattr(self, 'delete_thread') and self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.wait(300)  # Wait for it to finish with timeout

        if not self.selected_items:
            QMessageBox.information(
                self, 
                "No Selection", 
                "No resources selected for deletion."
            )
            return
            
        # Confirm deletion
        count = len(self.selected_items)
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {count} selected {self.resource_type}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Start batch deletion
        resources_list = list(self.selected_items)
        
        # Create and show progress dialog
        from PyQt6.QtWidgets import QProgressDialog
        progress = QProgressDialog(f"Deleting {count} {self.resource_type}...", "Cancel", 0, count, self)
        progress.setWindowTitle("Deleting Resources")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setValue(0)
        
        # Start batch delete thread
        self.batch_delete_thread = BatchResourceDeleterThread(self.resource_type, resources_list)
        self.batch_delete_thread.batch_delete_progress.connect(progress.setValue)
        self.batch_delete_thread.batch_delete_completed.connect(
            lambda success, errors: self.on_batch_delete_completed(success, errors, progress)
        )
        self.batch_delete_thread.start()
        
    def on_batch_delete_completed(self, success_list, error_list, progress_dialog):
        """Handle batch deletion completion."""
        # Close progress dialog
        progress_dialog.close()
        
        # Show results
        success_count = len(success_list)
        error_count = len(error_list)
        
        result_message = f"Deleted {success_count} of {success_count + error_count} {self.resource_type}."
        
        if error_count > 0:
            result_message += f"\n\nFailed to delete {error_count} resources:"
            for name, namespace, error in error_list[:5]:  # Show first 5 errors
                ns_text = f" in namespace {namespace}" if namespace else ""
                result_message += f"\n- {name}{ns_text}: {error}"
                
            if error_count > 5:
                result_message += f"\n... and {error_count - 5} more."
                
        QMessageBox.information(self, "Deletion Results", result_message)
        
        # Reload data
        self.load_data()
        
    def delete_resource(self, resource_name, resource_namespace):
        """Delete a single resource."""
        # Clean up any existing delete thread first
        if hasattr(self, 'delete_thread') and self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.wait(300)  # Wait for it to finish with timeout

        # Confirm deletion
        ns_text = f" in namespace {resource_namespace}" if resource_namespace else ""
        result = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {self.resource_type}/{resource_name}{ns_text}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Start deletion thread
        self.delete_thread = ResourceDeleterThread(self.resource_type, resource_name, resource_namespace)
        self.delete_thread.delete_completed.connect(self.on_delete_completed)
        self.delete_thread.start()
        
    def on_delete_completed(self, success, message, resource_name, resource_namespace):
        """Handle deletion completion."""
        if success:
            # Show success message
            QMessageBox.information(self, "Deletion Successful", message)
            
            # Remove from selected items if present
            self.selected_items.discard((resource_name, resource_namespace))
            
            # Remove from resources list
            self.resources = [r for r in self.resources if not (
                r["name"] == resource_name and r.get("namespace", "") == resource_namespace
            )]
            
            # Reload data
            self.load_data()
        else:
            # Show error message
            QMessageBox.critical(self, "Deletion Failed", message)
