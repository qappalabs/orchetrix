"""
Optimized BaseResourcePage with performance improvements:
- Virtual scrolling for large datasets
- Batch table updates
- Debounced search and namespace changes
- Efficient memory management
- Lazy loading with progressive rendering
"""

import os
import logging
import weakref
from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QLabel, QProgressBar, QHBoxLayout, QPushButton, QApplication, QTableWidgetItem,
    QAbstractItemView, QStackedWidget, QHeaderView, QFrame, QSizePolicy
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QProcess, QRect
from base_components.base_components import BaseTablePage
from UI.Styles import AppStyles, AppColors
from utils.kubernetes_client import get_kubernetes_client

from kubernetes import client
from kubernetes.client.rest import ApiException

from utils.enhanced_worker import EnhancedBaseWorker
from utils.thread_manager import get_thread_manager
from log_handler import method_logger, class_logger

# Constants for performance tuning
BATCH_SIZE = 50  # Number of items to render in each batch
SCROLL_DEBOUNCE_MS = 100  # Debounce time for scroll events
SEARCH_DEBOUNCE_MS = 300  # Debounce time for search input
CACHE_TTL_SECONDS = 300  # Cache time-to-live

class KubernetesResourceLoader(EnhancedBaseWorker):
    """Optimized resource loader with incremental loading support"""
    
    def __init__(self, resource_type, namespace=None, limit=None, continue_token=None):
        super().__init__(f"resource_load_{resource_type}_{namespace or 'all'}")
        self.resource_type = resource_type
        self.namespace = namespace
        self.limit = limit or 100  # Increased default limit
        self.continue_token = continue_token
        self.kube_client = get_kubernetes_client()
        self._timeout = 15  # Reduced timeout for faster failure

    def execute(self):
        if self.is_cancelled():
            return ([], self.resource_type, "")
        
        try:
            # Use optimized loading method
            resources, next_token = self._load_resources()
            
            if self.is_cancelled():
                return ([], self.resource_type, "")
            
            return (resources, self.resource_type, next_token or "")
            
        except Exception as e:
            if self.is_cancelled():
                return ([], self.resource_type, "")
            logging.error(f"Error loading {self.resource_type}: {e}")
            raise e
        
    def _load_resources(self):
        """Optimized resource loading with minimal API calls"""
        # Map resource type to loader method
        loaders = {
            "pods": self._load_pods,
            "services": self._load_services,
            "deployments": self._load_deployments,
            "nodes": self._load_nodes,
            "namespaces": self._load_namespaces,
            "configmaps": self._load_configmaps,
            "secrets": self._load_secrets,
            "events": self._load_events,
            "persistentvolumes": self._load_persistent_volumes,
            "persistentvolumeclaims": self._load_persistent_volume_claims,
            "ingresses": self._load_ingresses,
            "daemonsets": self._load_daemonsets,
            "statefulsets": self._load_statefulsets,
            "replicasets": self._load_replicasets,
            "jobs": self._load_jobs,
            "cronjobs": self._load_cronjobs,
            "replicationcontrollers": self._load_replication_controllers,
            "resourcequotas": self._load_resource_quotas,
            "limitranges": self._load_limit_ranges,
            "horizontalpodautoscalers": self._load_horizontal_pod_autoscalers,
            "poddisruptionbudgets": self._load_pod_disruption_budgets,
            "priorityclasses": self._load_priority_classes,
            "runtimeclasses": self._load_runtime_classes,
            "leases": self._load_leases,
            "mutatingwebhookconfigurations": self._load_mutating_webhook_configurations,
            "validatingwebhookconfigurations": self._load_validating_webhook_configurations,
            "endpoints": self._load_endpoints,
            "ingressclasses": self._load_ingress_classes,
            "networkpolicies": self._load_network_policies,
            "storageclasses": self._load_storage_classes,
            "serviceaccounts": self._load_service_accounts,
            "clusterroles": self._load_cluster_roles,
            "roles": self._load_roles,
            "clusterrolebindings": self._load_cluster_role_bindings,
            "rolebindings": self._load_role_bindings,
            "customresourcedefinitions": self._load_custom_resource_definitions,
            # Add more resource types as needed
        }
        
        loader = loaders.get(self.resource_type)
        if loader:
            return loader()
        else:
            # Fallback to generic loader
            return self._load_generic_optimized()
        
    def _get_continue_token(self, response_object):
        """Helper to extract continue token from response metadata."""
        if hasattr(response_object, 'metadata') and hasattr(response_object.metadata, '_continue') and response_object.metadata._continue:
            return response_object.metadata._continue
        return None

    def _load_pods(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        # Remove None values from kwargs to avoid issues with the API client
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            pods_list = self.kube_client.v1.list_namespaced_pod(namespace=self.namespace, **api_kwargs)
        else:
            pods_list = self.kube_client.v1.list_pod_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(pods_list)
        for pod in pods_list.items:
            resource = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace or "default",
                "age": self._format_age(pod.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pod)
            }
            if pod.spec and pod.spec.containers:
                resource["containers"] = len(pod.spec.containers)
            if pod.status and pod.status.container_statuses:
                restart_count = sum(cs.restart_count or 0 for cs in pod.status.container_statuses)
                resource["restarts"] = restart_count
            if pod.spec and pod.spec.node_name:
                resource["node"] = pod.spec.node_name
            resources.append(resource)
        return resources, next_token

    def _load_services(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            services_list = self.kube_client.v1.list_namespaced_service(namespace=self.namespace, **api_kwargs)
        else:
            services_list = self.kube_client.v1.list_service_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(services_list)
        for service in services_list.items:
            resource = {
                "name": service.metadata.name,
                "namespace": service.metadata.namespace or "default",
                "age": self._format_age(service.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(service)
            }
            if service.spec:
                resource["type"] = service.spec.type or "ClusterIP"
                resource["cluster_ip"] = service.spec.cluster_ip or "<none>"
                if service.spec.ports:
                    ports_desc = [f"{p.port}:{p.target_port}/{p.protocol}" for p in service.spec.ports if p.port and p.target_port and p.protocol]
                    resource["ports"] = ", ".join(ports_desc) if ports_desc else "<none>"
                else:
                    resource["ports"] = "<none>"
            resources.append(resource)
        return resources, next_token

    def _load_deployments(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}

        if self.namespace and self.namespace != "all":
            deployments_list = self.kube_client.apps_v1.list_namespaced_deployment(namespace=self.namespace, **api_kwargs)
        else:
            deployments_list = self.kube_client.apps_v1.list_deployment_for_all_namespaces(**api_kwargs)

        next_token = self._get_continue_token(deployments_list)
        for deployment in deployments_list.items:
            resource = {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace or "default",
                "age": self._format_age(deployment.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(deployment)
            }
            if deployment.spec:
                resource["replicas"] = deployment.spec.replicas or 0
            if deployment.status:
                resource["ready_replicas"] = deployment.status.ready_replicas or 0
                resource["available_replicas"] = deployment.status.available_replicas or 0
            resources.append(resource)
        return resources, next_token

    def _load_nodes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        nodes_list = self.kube_client.v1.list_node(**api_kwargs)
        next_token = self._get_continue_token(nodes_list)
        for node in nodes_list.items:
            resource = {
                "name": node.metadata.name, "namespace": "",
                "age": self._format_age(node.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(node)
            }
            if node.status:
                status = "Unknown"
                if node.status.conditions:
                    for condition in node.status.conditions:
                        if condition.type == "Ready":
                            status = "Ready" if condition.status == "True" else "NotReady"
                            break
                resource["status"] = status
                roles = [label.split("/")[1] for label in node.metadata.labels if label.startswith("node-role.kubernetes.io/")]
                resource["roles"] = ", ".join(roles) if roles else "<none>"
                if node.status.node_info:
                    resource["version"] = node.status.node_info.kubelet_version
            resources.append(resource)
        return resources, next_token

    def _load_namespaces(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        namespaces_list = self.kube_client.v1.list_namespace(**api_kwargs)
        next_token = self._get_continue_token(namespaces_list)
        for namespace in namespaces_list.items:
            resource = {
                "name": namespace.metadata.name, "namespace": "",
                "age": self._format_age(namespace.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(namespace)
            }
            if namespace.status:
                resource["status"] = namespace.status.phase or "Active"
            resources.append(resource)
        return resources, next_token

    def _load_configmaps(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            configmaps_list = self.kube_client.v1.list_namespaced_config_map(namespace=self.namespace, **api_kwargs)
        else:
            configmaps_list = self.kube_client.v1.list_config_map_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(configmaps_list)
        for cm in configmaps_list.items:
            resource = {
                "name": cm.metadata.name, "namespace": cm.metadata.namespace or "default",
                "age": self._format_age(cm.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(cm)
            }
            if cm.data:
                resource["keys"] = ", ".join(list(cm.data.keys())) if cm.data else "<none>"
            else:
                resource["keys"] = "<none>"
            resources.append(resource)
        return resources, next_token

    def _load_secrets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            secrets_list = self.kube_client.v1.list_namespaced_secret(namespace=self.namespace, **api_kwargs)
        else:
            secrets_list = self.kube_client.v1.list_secret_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(secrets_list)
        for secret in secrets_list.items:
            resource = {
                "name": secret.metadata.name, "namespace": secret.metadata.namespace or "default",
                "age": self._format_age(secret.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(secret),
                "type": secret.type or "Opaque",
                "keys": ", ".join(list(secret.data.keys())) if secret.data else "<none>"
            }
            resources.append(resource)
        return resources, next_token

    def _load_events(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token, 'watch': False}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            events_list = self.kube_client.v1.list_namespaced_event(namespace=self.namespace, **api_kwargs)
        else:
            events_list = self.kube_client.v1.list_event_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(events_list)
        for event in events_list.items:
            resource = {
                "name": event.metadata.name or f"event-{event.involved_object.name if event.involved_object else 'unknown'}",
                "namespace": event.metadata.namespace or "default",
                "age": self._format_age(event.last_timestamp or event.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(event),
                "type": event.type or "Normal", "reason": event.reason or "Unknown",
                "message": event.message or "No message",
                "object": f"{event.involved_object.kind}/{event.involved_object.name}" if event.involved_object else "Unknown"
            }
            resources.append(resource)
        return resources, next_token

    def _load_persistent_volumes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        pvs_list = self.kube_client.v1.list_persistent_volume(**api_kwargs)
        next_token = self._get_continue_token(pvs_list)
        for pv in pvs_list.items:
            resource = {
                "name": pv.metadata.name, "namespace": "",
                "age": self._format_age(pv.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pv),
                "capacity": pv.spec.capacity.get("storage", "Unknown") if pv.spec.capacity else "Unknown",
                "access_modes": ", ".join(pv.spec.access_modes) if pv.spec.access_modes else "",
                "reclaim_policy": pv.spec.persistent_volume_reclaim_policy or "Retain",
                "status": pv.status.phase or "Unknown"
            }
            resources.append(resource)
        return resources, next_token

    def _load_persistent_volume_claims(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            pvcs_list = self.kube_client.v1.list_namespaced_persistent_volume_claim(namespace=self.namespace, **api_kwargs)
        else:
            pvcs_list = self.kube_client.v1.list_persistent_volume_claim_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(pvcs_list)
        for pvc in pvcs_list.items:
            resource = {
                "name": pvc.metadata.name, "namespace": pvc.metadata.namespace or "default",
                "age": self._format_age(pvc.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pvc),
                "status": pvc.status.phase or "Unknown",
                "volume": pvc.spec.volume_name if pvc.spec else "",
                "capacity": pvc.spec.resources.requests.get("storage", "Unknown") if pvc.spec and pvc.spec.resources and pvc.spec.resources.requests else "Unknown"
            }
            resources.append(resource)
        return resources, next_token

    def _load_ingresses(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            ingresses_list = self.kube_client.networking_v1.list_namespaced_ingress(namespace=self.namespace, **api_kwargs)
        else:
            ingresses_list = self.kube_client.networking_v1.list_ingress_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(ingresses_list)
        for ingress in ingresses_list.items:
            resource = {
                "name": ingress.metadata.name, "namespace": ingress.metadata.namespace or "default",
                "age": self._format_age(ingress.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(ingress),
                "hosts": ", ".join([rule.host for rule in ingress.spec.rules if rule.host]) if ingress.spec and ingress.spec.rules else "*"
            }
            resources.append(resource)
        return resources, next_token

    def _load_daemonsets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            ds_list = self.kube_client.apps_v1.list_namespaced_daemon_set(namespace=self.namespace, **api_kwargs)
        else:
            ds_list = self.kube_client.apps_v1.list_daemon_set_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(ds_list)
        for ds in ds_list.items:
            resource = {
                "name": ds.metadata.name, "namespace": ds.metadata.namespace or "default",
                "age": self._format_age(ds.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(ds),
                "desired": ds.status.desired_number_scheduled or 0 if ds.status else 0,
                "current": ds.status.current_number_scheduled or 0 if ds.status else 0,
                "ready": ds.status.number_ready or 0 if ds.status else 0
            }
            resources.append(resource)
        return resources, next_token

    def _load_statefulsets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            sts_list = self.kube_client.apps_v1.list_namespaced_stateful_set(namespace=self.namespace, **api_kwargs)
        else:
            sts_list = self.kube_client.apps_v1.list_stateful_set_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(sts_list)
        for sts in sts_list.items:
            resource = {
                "name": sts.metadata.name, "namespace": sts.metadata.namespace or "default",
                "age": self._format_age(sts.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(sts),
                "replicas": sts.spec.replicas or 0 if sts.spec else 0,
                "ready": sts.status.ready_replicas or 0 if sts.status else 0
            }
            resources.append(resource)
        return resources, next_token

    def _load_replicasets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            rs_list = self.kube_client.apps_v1.list_namespaced_replica_set(namespace=self.namespace, **api_kwargs)
        else:
            rs_list = self.kube_client.apps_v1.list_replica_set_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(rs_list)
        for rs in rs_list.items:
            resource = {
                "name": rs.metadata.name, "namespace": rs.metadata.namespace or "default",
                "age": self._format_age(rs.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rs),
                "desired": rs.spec.replicas or 0 if rs.spec else 0,
                "current": rs.status.replicas or 0 if rs.status else 0,
                "ready": rs.status.ready_replicas or 0 if rs.status else 0
            }
            resources.append(resource)
        return resources, next_token

    def _load_jobs(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            jobs_list = self.kube_client.batch_v1.list_namespaced_job(namespace=self.namespace, **api_kwargs)
        else:
            jobs_list = self.kube_client.batch_v1.list_job_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(jobs_list)
        for job in jobs_list.items:
            resource = {
                "name": job.metadata.name, "namespace": job.metadata.namespace or "default",
                "age": self._format_age(job.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(job),
                "completions": f"{job.status.succeeded or 0}/{job.spec.completions or 1}" if job.status and job.spec else "0/1",
                "duration": self._calculate_duration(job.status.start_time, job.status.completion_time) if job.status and job.status.start_time else ""
            }
            resources.append(resource)
        return resources, next_token

    def _load_cronjobs(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            cj_list = self.kube_client.batch_v1.list_namespaced_cron_job(namespace=self.namespace, **api_kwargs)
        else:
            cj_list = self.kube_client.batch_v1.list_cron_job_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(cj_list)
        for cj in cj_list.items:
            resource = {
                "name": cj.metadata.name, "namespace": cj.metadata.namespace or "default",
                "age": self._format_age(cj.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(cj),
                "schedule": cj.spec.schedule or "" if cj.spec else "",
                "suspend": "True" if cj.spec and cj.spec.suspend else "False",
                "active": len(cj.status.active) if cj.status and cj.status.active else 0,
                "last_schedule": self._format_age(cj.status.last_schedule_time) if cj.status and cj.status.last_schedule_time else "<none>"
            }
            resources.append(resource)
        return resources, next_token

    def _load_replication_controllers(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            rc_list = self.kube_client.v1.list_namespaced_replication_controller(namespace=self.namespace, **api_kwargs)
        else:
            rc_list = self.kube_client.v1.list_replication_controller_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(rc_list)
        for rc in rc_list.items:
            resource = {
                "name": rc.metadata.name, "namespace": rc.metadata.namespace or "default",
                "age": self._format_age(rc.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rc),
                "desired_replicas": rc.spec.replicas or 0 if rc.spec else 0,
                "replicas": rc.status.replicas or 0 if rc.status else 0,
                "ready_replicas": rc.status.ready_replicas or 0 if rc.status else 0
            }
            resources.append(resource)
        return resources, next_token

    def _load_resource_quotas(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            rq_list = self.kube_client.v1.list_namespaced_resource_quota(namespace=self.namespace, **api_kwargs)
        else:
            # ResourceQuotas are namespaced. If "all", this needs iteration or specific handling.
            # Assuming namespaced context for simplicity or error if 'all' without specific logic.
            rq_list = self.kube_client.v1.list_namespaced_resource_quota(namespace=self.namespace, **api_kwargs) if self.namespace else client.models.V1ResourceQuotaList(items=[])
        next_token = self._get_continue_token(rq_list)
        for rq in rq_list.items:
            resource = {
                "name": rq.metadata.name, "namespace": rq.metadata.namespace or "default",
                "age": self._format_age(rq.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rq)
            }
            resources.append(resource)
        return resources, next_token

    def _load_limit_ranges(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            lr_list = self.kube_client.v1.list_namespaced_limit_range(namespace=self.namespace, **api_kwargs)
        else:
            lr_list = self.kube_client.v1.list_namespaced_limit_range(namespace=self.namespace, **api_kwargs) if self.namespace else client.models.V1LimitRangeList(items=[])
        next_token = self._get_continue_token(lr_list)
        for lr in lr_list.items:
            resource = {
                "name": lr.metadata.name, "namespace": lr.metadata.namespace or "default",
                "age": self._format_age(lr.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(lr)
            }
            resources.append(resource)
        return resources, next_token

    def _load_horizontal_pod_autoscalers(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            hpa_list = self.kube_client.autoscaling_v1.list_namespaced_horizontal_pod_autoscaler(namespace=self.namespace, **api_kwargs)
        else:
            hpa_list = self.kube_client.autoscaling_v1.list_horizontal_pod_autoscaler_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(hpa_list)
        for hpa in hpa_list.items:
            resource = {
                "name": hpa.metadata.name, "namespace": hpa.metadata.namespace or "default",
                "age": self._format_age(hpa.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(hpa),
                "min_replicas": hpa.spec.min_replicas or 0 if hpa.spec else 0,
                "max_replicas": hpa.spec.max_replicas or 0 if hpa.spec else 0,
                "target_cpu": hpa.spec.target_cpu_utilization_percentage or 0 if hpa.spec else 0,
                "current_replicas": hpa.status.current_replicas or 0 if hpa.status else 0,
                "current_cpu": hpa.status.current_cpu_utilization_percentage or 0 if hpa.status else 0
            }
            resources.append(resource)
        return resources, next_token

    def _load_pod_disruption_budgets(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        try:
            policy_api = client.PolicyV1Api(self.kube_client.v1.api_client)
            if self.namespace and self.namespace != "all":
                pdb_list = policy_api.list_namespaced_pod_disruption_budget(namespace=self.namespace, **api_kwargs)
            else:
                pdb_list = policy_api.list_pod_disruption_budget_for_all_namespaces(**api_kwargs)
        except AttributeError:
            policy_api = client.PolicyV1beta1Api(self.kube_client.v1.api_client)
            if self.namespace and self.namespace != "all":
                pdb_list = policy_api.list_namespaced_pod_disruption_budget(namespace=self.namespace, **api_kwargs)
            else:
                pdb_list = policy_api.list_pod_disruption_budget_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(pdb_list)
        for pdb in pdb_list.items:
            resource = {
                "name": pdb.metadata.name, "namespace": pdb.metadata.namespace or "default",
                "age": self._format_age(pdb.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(pdb)
            }
            resources.append(resource)
        return resources, next_token

    def _load_priority_classes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        next_token = None
        try:
            scheduling_api = client.SchedulingV1Api(self.kube_client.v1.api_client)
            pc_list = scheduling_api.list_priority_class(**api_kwargs)
            next_token = self._get_continue_token(pc_list)
            for pc in pc_list.items:
                resource = {
                    "name": pc.metadata.name, "namespace": "",
                    "age": self._format_age(pc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(pc),
                    "value": pc.value or 0, "global_default": pc.global_default or False
                }
                resources.append(resource)
        except AttributeError: logging.warning("SchedulingV1Api not available for priority classes")
        return resources, next_token

    def _load_runtime_classes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        next_token = None
        try:
            node_api = client.NodeV1Api(self.kube_client.v1.api_client)
            rc_list = node_api.list_runtime_class(**api_kwargs)
            next_token = self._get_continue_token(rc_list)
            for rc in rc_list.items:
                resource = {
                    "name": rc.metadata.name, "namespace": "",
                    "age": self._format_age(rc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(rc),
                    "handler": rc.handler or ""
                }
                resources.append(resource)
        except AttributeError: logging.warning("NodeV1Api not available for runtime classes")
        return resources, next_token

    def _load_leases(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        next_token = None
        try:
            coordination_api = client.CoordinationV1Api(self.kube_client.v1.api_client)
            if self.namespace and self.namespace != "all":
                lease_list = coordination_api.list_namespaced_lease(namespace=self.namespace, **api_kwargs)
            else:
                lease_list = coordination_api.list_lease_for_all_namespaces(**api_kwargs)
            next_token = self._get_continue_token(lease_list)
            for lease in lease_list.items:
                resource = {
                    "name": lease.metadata.name, "namespace": lease.metadata.namespace or "default",
                    "age": self._format_age(lease.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(lease),
                    "holder": lease.spec.holder_identity or "" if lease.spec else ""
                }
                resources.append(resource)
        except AttributeError: logging.warning("CoordinationV1Api not available for leases")
        return resources, next_token

    def _load_mutating_webhook_configurations(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        next_token = None
        try:
            admission_api = client.AdmissionregistrationV1Api(self.kube_client.v1.api_client)
            mwc_list = admission_api.list_mutating_webhook_configuration(**api_kwargs)
            next_token = self._get_continue_token(mwc_list)
            for mwc in mwc_list.items:
                resource = {
                    "name": mwc.metadata.name, "namespace": "",
                    "age": self._format_age(mwc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(mwc)
                }
                resources.append(resource)
        except AttributeError: logging.warning("AdmissionregistrationV1Api not available for mutating webhook configurations")
        return resources, next_token

    def _load_validating_webhook_configurations(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        next_token = None
        try:
            admission_api = client.AdmissionregistrationV1Api(self.kube_client.v1.api_client)
            vwc_list = admission_api.list_validating_webhook_configuration(**api_kwargs)
            next_token = self._get_continue_token(vwc_list)
            for vwc in vwc_list.items:
                resource = {
                    "name": vwc.metadata.name, "namespace": "",
                    "age": self._format_age(vwc.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(vwc)
                }
                resources.append(resource)
        except AttributeError: logging.warning("AdmissionregistrationV1Api not available for validating webhook configurations")
        return resources, next_token

    def _load_endpoints(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            ep_list = self.kube_client.v1.list_namespaced_endpoints(namespace=self.namespace, **api_kwargs)
        else:
            ep_list = self.kube_client.v1.list_endpoints_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(ep_list)
        for ep in ep_list.items:
            endpoints_str_list = []
            if ep.subsets:
                for subset in ep.subsets:
                    addresses = subset.addresses or []
                    ports = subset.ports or []
                    for addr in addresses:
                        for port_obj in ports:
                            endpoints_str_list.append(f"{addr.ip}:{port_obj.port}")
            resource = {
                "name": ep.metadata.name, "namespace": ep.metadata.namespace or "default",
                "age": self._format_age(ep.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(ep),
                "endpoints": ", ".join(endpoints_str_list) if endpoints_str_list else "<none>"
            }
            resources.append(resource)
        return resources, next_token

    def _load_ingress_classes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        next_token = None
        try:
            ic_list = self.kube_client.networking_v1.list_ingress_class(**api_kwargs)
            next_token = self._get_continue_token(ic_list)
            for ic in ic_list.items:
                resource = {
                    "name": ic.metadata.name, "namespace": "",
                    "age": self._format_age(ic.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(ic),
                    "controller": ic.spec.controller or "" if ic.spec else ""
                }
                resources.append(resource)
        except AttributeError: logging.warning("Ingress classes not available in this Kubernetes version")
        return resources, next_token

    def _load_network_policies(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            np_list = self.kube_client.networking_v1.list_namespaced_network_policy(namespace=self.namespace, **api_kwargs)
        else:
            np_list = self.kube_client.networking_v1.list_network_policy_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(np_list)
        for np in np_list.items:
            resource = {
                "name": np.metadata.name, "namespace": np.metadata.namespace or "default",
                "age": self._format_age(np.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(np)
            }
            resources.append(resource)
        return resources, next_token

    def _load_storage_classes(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        sc_list = self.kube_client.storage_v1.list_storage_class(**api_kwargs)
        next_token = self._get_continue_token(sc_list)
        for sc in sc_list.items:
            resource = {
                "name": sc.metadata.name, "namespace": "",
                "age": self._format_age(sc.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(sc),
                "provisioner": sc.provisioner or "", "reclaim_policy": sc.reclaim_policy or "Delete",
                "volume_binding_mode": sc.volume_binding_mode or "Immediate"
            }
            resources.append(resource)
        return resources, next_token

    def _load_service_accounts(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            sa_list = self.kube_client.v1.list_namespaced_service_account(namespace=self.namespace, **api_kwargs)
        else:
            sa_list = self.kube_client.v1.list_service_account_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(sa_list)
        for sa in sa_list.items:
            resource = {
                "name": sa.metadata.name, "namespace": sa.metadata.namespace or "default",
                "age": self._format_age(sa.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(sa),
                "secrets": len(sa.secrets) if sa.secrets else 0
            }
            resources.append(resource)
        return resources, next_token

    def _load_cluster_roles(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        cr_list = self.kube_client.rbac_v1.list_cluster_role(**api_kwargs)
        next_token = self._get_continue_token(cr_list)
        for cr in cr_list.items:
            resource = {
                "name": cr.metadata.name, "namespace": "",
                "age": self._format_age(cr.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(cr)
            }
            resources.append(resource)
        return resources, next_token

    def _load_roles(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            role_list = self.kube_client.rbac_v1.list_namespaced_role(namespace=self.namespace, **api_kwargs)
        else:
            role_list = self.kube_client.rbac_v1.list_role_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(role_list)
        for role in role_list.items:
            resource = {
                "name": role.metadata.name, "namespace": role.metadata.namespace or "default",
                "age": self._format_age(role.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(role)
            }
            resources.append(resource)
        return resources, next_token

    def _load_cluster_role_bindings(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        crb_list = self.kube_client.rbac_v1.list_cluster_role_binding(**api_kwargs)
        next_token = self._get_continue_token(crb_list)
        for crb in crb_list.items:
            resource = {
                "name": crb.metadata.name, "namespace": "",
                "age": self._format_age(crb.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(crb),
                "role": crb.role_ref.name or "" if crb.role_ref else "",
                "subjects": len(crb.subjects) if crb.subjects else 0
            }
            resources.append(resource)
        return resources, next_token

    def _load_role_bindings(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        if self.namespace and self.namespace != "all":
            rb_list = self.kube_client.rbac_v1.list_namespaced_role_binding(namespace=self.namespace, **api_kwargs)
        else:
            rb_list = self.kube_client.rbac_v1.list_role_binding_for_all_namespaces(**api_kwargs)
        next_token = self._get_continue_token(rb_list)
        for rb in rb_list.items:
            resource = {
                "name": rb.metadata.name, "namespace": rb.metadata.namespace or "default",
                "age": self._format_age(rb.metadata.creation_timestamp),
                "raw_data": client.ApiClient().sanitize_for_serialization(rb),
                "role": rb.role_ref.name or "" if rb.role_ref else "",
                "subjects": len(rb.subjects) if rb.subjects else 0
            }
            resources.append(resource)
        return resources, next_token

    def _load_custom_resource_definitions(self):
        resources = []
        api_kwargs = {'limit': self.limit, '_continue': self.continue_token}
        api_kwargs = {k: v for k, v in api_kwargs.items() if v is not None}
        next_token = None
        try:
            apiextensions_api = client.ApiextensionsV1Api(self.kube_client.v1.api_client)
            crd_list = apiextensions_api.list_custom_resource_definition(**api_kwargs)
            next_token = self._get_continue_token(crd_list)
            for crd in crd_list.items:
                resource = {
                    "name": crd.metadata.name, "namespace": "",
                    "age": self._format_age(crd.metadata.creation_timestamp),
                    "raw_data": client.ApiClient().sanitize_for_serialization(crd),
                    "group": crd.spec.group or "" if crd.spec else "",
                    "scope": crd.spec.scope or "" if crd.spec else "",
                    "version": crd.spec.versions[0].name or "" if crd.spec and crd.spec.versions else ""
                }
                resources.append(resource)
        except AttributeError: logging.warning("ApiextensionsV1Api not available for custom resource definitions")
        return resources, next_token

    def _load_generic_resource(self):
        logging.warning(f"Generic resource loading not implemented for {self.resource_type}")
        return [], None

    def _format_age(self, timestamp):
        if not timestamp: return "Unknown"
        try:
            import datetime
            if isinstance(timestamp, str):
                try:
                    created_time = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    if created_time.tzinfo is None:
                        created_time = created_time.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    try:
                        created_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f%z")
                    except ValueError:
                        try:
                            created_time = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
                        except ValueError:
                            logging.warning(f"Could not parse timestamp string: {timestamp}")
                            return "Unknown"
            elif isinstance(timestamp, datetime.datetime):
                if timestamp.tzinfo is None:
                    created_time = timestamp.replace(tzinfo=datetime.timezone.utc)
                else:
                    created_time = timestamp
            else:
                return "Unknown"
            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - created_time
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            if days > 0: return f"{days}d"
            if hours > 0: return f"{hours}h"
            return f"{minutes}m"
        except Exception as e:
            logging.error(f"Error formatting age for timestamp {timestamp}: {e}")
            return "Unknown"

    def _calculate_duration(self, start_time_str, end_time_str):
        if not start_time_str or not end_time_str: return ""
        try:
            import datetime
            start_time = datetime.datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            if start_time.tzinfo is None: start_time = start_time.replace(tzinfo=datetime.timezone.utc)
            if end_time.tzinfo is None: end_time = end_time.replace(tzinfo=datetime.timezone.utc)
            diff = end_time - start_time
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 0: return f"{days}d{hours}h"
            if hours > 0: return f"{hours}h{minutes}m"
            if minutes > 0: return f"{minutes}m{seconds}s"
            return f"{seconds}s"
        except Exception as e:
            logging.error(f"Error calculating duration: {e}")
            return ""


class ResourceDeleterThread(QThread):
    delete_completed = pyqtSignal(bool, str, str, str)
    def __init__(self, resource_type, resource_name, namespace, parent=None):
        super().__init__(parent)
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.kube_client = get_kubernetes_client()
        self._is_running = True

    def stop(self): self._is_running = False

    def run(self):
        if not self._is_running: return
        try:
            delete_options = client.V1DeleteOptions()

            if self.resource_type == "pods":
                if self.namespace:
                    self.kube_client.v1.delete_namespaced_pod(name=self.resource_name, namespace=self.namespace, body=delete_options)
            elif self.resource_type == "services":
                self.kube_client.v1.delete_namespaced_service(name=self.resource_name, namespace=self.namespace, body=delete_options)
            elif self.resource_type == "deployments":
                self.kube_client.apps_v1.delete_namespaced_deployment(name=self.resource_name, namespace=self.namespace, body=delete_options)

            else:
                if not self._is_running: return
                self.delete_completed.emit(False, f"Deletion not implemented for {self.resource_type}", self.resource_name, self.namespace)
                return
            if not self._is_running: return
            self.delete_completed.emit(True, f"{self.resource_type}/{self.resource_name} deleted", self.resource_name, self.namespace)
        except ApiException as e:
            if not self._is_running: return
            self.delete_completed.emit(False, f"API error deleting: {e.reason}", self.resource_name, self.namespace)
        except Exception as e:
            if not self._is_running: return
            self.delete_completed.emit(False, f"Error deleting: {str(e)}", self.resource_name, self.namespace)


class BatchResourceDeleterThread(QThread):
    batch_delete_progress = pyqtSignal(int, int)
    batch_delete_completed = pyqtSignal(list, list)
    def __init__(self, resource_type, resources_to_delete, parent=None):
        super().__init__(parent)
        self.resource_type = resource_type
        self.resources_to_delete = resources_to_delete
        self.kube_client = get_kubernetes_client()
        self._is_running = True
    def stop(self): self._is_running = False
    def run(self):
        successes, errors = [], []
        total = len(self.resources_to_delete)
        for i, (name, ns) in enumerate(self.resources_to_delete):
            if not self._is_running: break
            try:
                delete_options = client.V1DeleteOptions()
                if self.resource_type == "pods":
                    self.kube_client.v1.delete_namespaced_pod(name=name, namespace=ns, body=delete_options)
                else: raise NotImplementedError(f"Batch delete not implemented for {self.resource_type}")
                successes.append((name, ns))
            except Exception as e: errors.append((name, ns, str(e)))
            if self._is_running: self.batch_delete_progress.emit(i + 1, total)
        if self._is_running: self.batch_delete_completed.emit(successes, errors)

CLUSTER_SCOPED_RESOURCES = {
    'nodes', 'persistentvolumes', 'clusterroles', 'clusterrolebindings',
    'storageclasses', 'ingressclasses', 'priorityclasses', 'runtimeclasses',
    'mutatingwebhookconfigurations', 'validatingwebhookconfigurations',
    'customresourcedefinitions', 'namespaces'
}


class VirtualScrollTable(QWidget):
    """Virtual scrolling table for handling large datasets efficiently"""
    
    def __init__(self, headers, parent=None):
        super().__init__(parent)
        self.headers = headers
        self.all_data = []
        self.visible_range = (0, 0)
        self.row_height = 40
        self.viewport_rows = 20
        
        # Setup UI
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the virtual scroll table UI"""
        # Implementation of virtual scrolling table
        pass
    
    def set_data(self, data):
        """Set data for virtual scrolling"""
        self.all_data = data
        self._update_visible_range()
        
    def _update_visible_range(self):
        """Update visible range based on scroll position"""
        # Calculate visible range
        pass


@class_logger(log_level=logging.INFO, exclude_methods=['__init__', 'clear_table', 'update_table_row', 'load_more_complete', 'all_items_loaded_signal'])
class BaseResourcePage(BaseTablePage):
    load_more_complete = pyqtSignal()
    all_items_loaded_signal = pyqtSignal()

    # Class-level cache for formatted ages
    _age_cache = {}
    _age_cache_timestamps = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = None
        self.resources = []
        self.namespace_filter = "default"
        self.search_bar = None
        self.namespace_combo = None

        self.loading_thread = None
        self.delete_thread = None
        self.batch_delete_thread = None

        # Performance optimizations
        self.is_loading_initial = False
        self.is_loading_more = False
        self.all_data_loaded = False
        self.current_continue_token = None
        self.items_per_page = 25 # User specified
        self.selected_items = set()
        self.reload_on_show = True


        self.is_showing_skeleton = False

        # Caching
        self._data_cache = {}
        self._cache_timestamps = {}
        self._shutting_down = False

                # Virtual scrolling
        self._visible_start = 0
        self._visible_end = 50
        self._render_buffer = 10  # Extra rows to render for smooth scrolling
        
        # Debouncing timers
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)
        
        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._handle_scroll_debounced)
        
        # Progressive rendering
        self._render_timer = QTimer()
        self._render_timer.timeout.connect(self._render_next_batch)
        self._render_queue = []

        self.kube_client = get_kubernetes_client()
        self._load_more_indicator_widget = None
        # self._all_loaded_label = None

        self._message_widget_container = None
        self._table_stack = None


    def setup_ui(self, title, headers, sortable_columns=None):
        page_main_layout = QVBoxLayout(self)
        page_main_layout.setContentsMargins(16, 16, 16, 16)
        page_main_layout.setSpacing(16)

        header_controls_layout = QHBoxLayout()
        self._create_title_and_count(header_controls_layout, title)
        page_main_layout.addLayout(header_controls_layout)
        self._add_controls_to_header(header_controls_layout)

        self._table_stack = QStackedWidget()
        page_main_layout.addWidget(self._table_stack)

        self.table = self._create_table(headers, sortable_columns)
        self._table_stack.addWidget(self.table)

        # Create a dedicated container for messages (empty/error)
        self._message_widget_container = QWidget()
        message_container_layout = QVBoxLayout(self._message_widget_container)
        message_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center content
        message_container_layout.setContentsMargins(20,20,20,20) # Add some padding
        self._table_stack.addWidget(self._message_widget_container)

        self._table_stack.setCurrentWidget(self.table)

        select_all_checkbox = self._create_select_all_checkbox()
        self._set_header_widget(0, select_all_checkbox)

        if hasattr(self, 'table') and self.table:
            self.table.verticalScrollBar().valueChanged.connect(self._handle_scroll)
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.installEventFilter(self)
        return page_main_layout


    @classmethod
    def _format_age_cached(cls, timestamp):
        """Format age with caching to avoid repeated calculations"""
        if not timestamp:
            return "Unknown"
        
        # Check cache
        cache_key = str(timestamp)
        if cache_key in cls._age_cache:
            # Check if cache is still valid (update every 60 seconds)
            import time
            if time.time() - cls._age_cache_timestamps.get(cache_key, 0) < 60:
                return cls._age_cache[cache_key]
        
        # Calculate age
        try:
            import datetime
            if isinstance(timestamp, str):
                created_time = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if created_time.tzinfo is None:
                    created_time = created_time.replace(tzinfo=datetime.timezone.utc)
            else:
                created_time = timestamp.replace(tzinfo=datetime.timezone.utc)
            
            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - created_time
            
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                result = f"{days}d"
            elif hours > 0:
                result = f"{hours}h"
            else:
                result = f"{minutes}m"
            
            # Cache result
            cls._age_cache[cache_key] = result
            cls._age_cache_timestamps[cache_key] = time.time()
            
            # Clean old cache entries periodically
            if len(cls._age_cache) > 1000:
                cls._clean_age_cache()
            
            return result
            
        except Exception as e:
            logging.error(f"Error formatting age: {e}")
            return "Unknown"

    @classmethod
    def _clean_age_cache(cls):
        """Clean old entries from age cache"""
        import time
        current_time = time.time()
        
        # Remove entries older than 5 minutes
        keys_to_remove = [
            key for key, timestamp in cls._age_cache_timestamps.items()
            if current_time - timestamp > 300
        ]
        
        for key in keys_to_remove:
            cls._age_cache.pop(key, None)
            cls._age_cache_timestamps.pop(key, None)

    def _create_title_and_count(self, layout, title_text):
        title_label = QLabel(title_text)
        title_label_style = getattr(AppStyles, "TITLE_STYLE", "font-size: 20px; font-weight: bold; color: #ffffff;")
        title_label.setStyleSheet(title_label_style)

        self.items_count = QLabel("0 items")
        items_count_style = getattr(AppStyles, "COUNT_STYLE", "color: #9ca3af; font-size: 12px; margin-left: 8px;")
        self.items_count.setStyleSheet(items_count_style)
        self.items_count.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(title_label)
        layout.addWidget(self.items_count)

    def _add_controls_to_header(self, header_layout):
        self._add_filter_controls(header_layout)
        header_layout.addStretch(1)

        refresh_btn = QPushButton("Refresh")
        refresh_style = getattr(AppStyles, "SECONDARY_BUTTON_STYLE",
                                """QPushButton { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d;
                                               border-radius: 4px; padding: 5px 10px; }
                                   QPushButton:hover { background-color: #3d3d3d; }
                                   QPushButton:pressed { background-color: #1e1e1e; }"""
                                )
        refresh_btn.setStyleSheet(refresh_style)
        refresh_btn.clicked.connect(self.force_load_data)
        header_layout.addWidget(refresh_btn)

    def _add_filter_controls(self, header_layout):
        filters_widget = QWidget()
        filters_layout = QHBoxLayout(filters_widget)
        filters_layout.setContentsMargins(0,0,0,0)
        filters_layout.setSpacing(10)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search resources...")
        search_bar_height = getattr(AppStyles, "SEARCH_BAR_HEIGHT", 30)
        search_bar_min_width = getattr(AppStyles, "SEARCH_BAR_MIN_WIDTH", 200)
        search_bar_style = getattr(AppStyles, "SEARCH_BAR_STYLE", "QLineEdit { padding: 5px; border: 1px solid #555; border-radius: 4px; background-color: #333; color: white; }")
        self.search_bar.setFixedHeight(search_bar_height)
        self.search_bar.setMinimumWidth(search_bar_min_width)
        self.search_bar.setStyleSheet(search_bar_style)
        self.search_bar.textChanged.connect(self._handle_search)
        filters_layout.addWidget(self.search_bar)

        if self.resource_type not in CLUSTER_SCOPED_RESOURCES:
            namespace_label = QLabel("Namespace:")
            namespace_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-right: 5px;")
            filters_layout.addWidget(namespace_label)

            self.namespace_combo = QComboBox()
            self.namespace_combo.setFixedHeight(search_bar_height)
            self.namespace_combo.setMinimumWidth(150)
            
            # Apply the corrected combo box style
            combo_box_style = getattr(AppStyles, "COMBO_BOX_STYLE")
            self.namespace_combo.setStyleSheet(combo_box_style)
            
            # Configure dropdown behavior to prevent upward opening
            self._configure_dropdown_behavior(self.namespace_combo)
            
            self.namespace_combo.addItem("default")
            self.namespace_combo.setCurrentText("default")
            self.namespace_combo.currentTextChanged.connect(self._handle_namespace_change)
            filters_layout.addWidget(self.namespace_combo)
            QTimer.singleShot(100, self._load_namespaces)

        header_layout.addWidget(filters_widget)

    def _configure_dropdown_behavior(self, combo_box):
        """Configure dropdown to ensure consistent downward opening and proper sizing"""
        # Set maximum visible items to control popup height
        combo_box.setMaxVisibleItems(10)
        
        # Configure the view to prevent unwanted scrollbars for small lists
        view = combo_box.view()
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)   
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Apply the combo box style to ensure consistency
        combo_box.setStyleSheet(getattr(AppStyles, "COMBO_BOX_STYLE"))
        view.setStyleSheet("border: none; background-color: #2d2d2d;")
        
        # Override the showPopup method to force downward opening
        original_show_popup = combo_box.showPopup
        
        def custom_show_popup():
            # Store original size policy
            original_policy = combo_box.sizePolicy()
            
            # Temporarily set size policy to prevent upward expansion
            combo_box.setSizePolicy(
                original_policy.horizontalPolicy(),
                QSizePolicy.Policy.Fixed
            )
            
            # Call original popup method
            original_show_popup()
            
            # Get the popup widget and remove borders
            popup = combo_box.findChild(QFrame)
            if popup:
                popup.setStyleSheet("border: none; background-color: #2d2d2d;")
                combo_pos = combo_box.mapToGlobal(combo_box.rect().bottomLeft())
                popup.move(combo_pos)
                popup.setFixedWidth(combo_box.width())
            
            # Restore original size policy
            combo_box.setSizePolicy(original_policy)
        
        combo_box.showPopup = custom_show_popup

    def _show_message_in_table_area(self, message_text, description_text=None, is_error=False):
        """Display a clean text message within the table area while preserving headers"""
        if not self.table:
            return
        
        # Clear table rows but maintain headers
        self.table.setRowCount(0)
        
        # Ensure table is visible to show headers
        self._show_table_area()
        
        # Create simple empty state display
        self._display_empty_state_message(message_text, description_text, is_error)

    def _display_empty_state_message(self, message_text, description_text=None, is_error=False):
        """Create and display a simple empty state message"""
        # Remove any existing empty state
        self._remove_empty_state_message()
        
        # Create empty state widget as child of table viewport
        viewport = self.table.viewport()
        self.empty_state_widget = QWidget(viewport)
        self.empty_state_widget.setObjectName("emptyStateWidget")
        
        # Set up layout
        layout = QVBoxLayout(self.empty_state_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        # Apply clean styling
        self.empty_state_widget.setStyleSheet("""
            QWidget#emptyStateWidget {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Create icon
        icon_label = QLabel()
        
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            font-size: 48px;
            background-color: transparent;
            border: none;
            margin-bottom: 10px;
        """)
        layout.addWidget(icon_label)
        
        # Create main message
        message_label = QLabel(message_text)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        
        text_color = "#E53935" if is_error else "#6B7280"
        message_label.setStyleSheet(f"""
            color: {text_color};
            font-size: 16px;
            font-weight: 600;
            background-color: transparent;
            border: none;
            margin-bottom: 8px;
        """)
        layout.addWidget(message_label)
        
        # Create description if provided
        if description_text:
            desc_label = QLabel(description_text)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                color: #9CA3AF;
                font-size: 14px;
                background-color: transparent;
                border: none;
                line-height: 1.4;
            """)
            layout.addWidget(desc_label)
        
        # Position and show the widget
        self._position_empty_state_widget()
        self.empty_state_widget.show()
        
        # Disable table sorting while empty state is visible
        self.table.setSortingEnabled(False)

    def _position_empty_state_widget(self):
        """Position the empty state widget to fill the table viewport"""
        if not hasattr(self, 'empty_state_widget') or not self.empty_state_widget:
            return
        
        viewport = self.table.viewport()
        self.empty_state_widget.setGeometry(viewport.rect())

    def _remove_empty_state_message(self):
        """Remove the empty state message widget"""
        if hasattr(self, 'empty_state_widget') and self.empty_state_widget:
            self.empty_state_widget.hide()
            self.empty_state_widget.deleteLater()
            self.empty_state_widget = None

    def _clear_empty_state(self):
        """Clear empty state and restore normal table functionality"""
        self._remove_empty_state_message()
        if self.table:
            self.table.setRowCount(0)
            self.table.setSortingEnabled(True)

    def _show_skeleton_loader(self, rows=10):
        if not hasattr(self, 'table') or self._shutting_down: return
        self.is_showing_skeleton = True
        self._show_table_area()
        self.table.setRowCount(0)

        for i in range(rows):
            self.table.insertRow(i)
            for j in range(self.table.columnCount()):
                if j == 0:
                    empty_widget = QWidget(); empty_widget.setStyleSheet("background-color: #2d2d2d; border-radius: 3px;")
                    self.table.setCellWidget(i, j, empty_widget)
                elif j == self.table.columnCount() - 1:
                    empty_widget = QWidget(); empty_widget.setStyleSheet("background-color: #2d2d2d; border-radius: 3px;")
                    self.table.setCellWidget(i, j, empty_widget)
                else:
                    item = QTableWidgetItem(""); item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setBackground(QColor("#2d2d2d")); self.table.setItem(i, j, item)
            self.table.setRowHeight(i, 40)

        self.table.setSortingEnabled(False)
        QApplication.processEvents()

        if not hasattr(self, 'skeleton_timer'):
            self.skeleton_timer = QTimer(self)
            self.skeleton_timer.timeout.connect(self._animate_skeleton)
            self.skeleton_animation_step = 0
        if not self.skeleton_timer.isActive(): self.skeleton_timer.start(250)

    def _animate_skeleton(self):
        if not self.is_showing_skeleton or not hasattr(self, 'table'):
            if hasattr(self, 'skeleton_timer'): self.skeleton_timer.stop()
            return
        colors = ["#2d2d2d", "#313131", "#353535", "#313131"]
        current_color_hex = colors[self.skeleton_animation_step % len(colors)]
        for i in range(self.table.rowCount()):
            for j in [0, self.table.columnCount() -1]:
                widget = self.table.cellWidget(i,j)
                if widget: widget.setStyleSheet(f"background-color: {current_color_hex}; border-radius: 3px;")
            for j in range(1, self.table.columnCount() - 1):
                item = self.table.item(i, j)
                if item: item.setBackground(QColor(current_color_hex))
        self.skeleton_animation_step += 1

    def _load_namespaces(self):
        if not self.namespace_combo: return
        try:
            namespaces_list_obj = self.kube_client.v1.list_namespace()
            namespaces = [ns.metadata.name for ns in namespaces_list_obj.items]
            current_selection = self.namespace_combo.currentText()
            self.namespace_combo.blockSignals(True)
            self.namespace_combo.clear()
            self.namespace_combo.addItem("All Namespaces")
            self.namespace_combo.addItems(sorted(namespaces))
            if current_selection in namespaces: self.namespace_combo.setCurrentText(current_selection)
            elif "default" in namespaces: self.namespace_combo.setCurrentText("default")
            elif namespaces: self.namespace_combo.setCurrentIndex(1)
            else: self.namespace_combo.setCurrentText("All Namespaces")
            self.namespace_combo.blockSignals(False)
        except Exception as e:
            logging.error(f"Error loading namespaces: {e}")
            self.namespace_combo.blockSignals(True)
            self.namespace_combo.clear()
            self.namespace_combo.addItem("All Namespaces"); self.namespace_combo.addItem("default")
            self.namespace_combo.setCurrentText("default")
            self.namespace_combo.blockSignals(False)


    def _handle_search(self, text):
        """Debounced search handler"""
        self._search_timer.stop()
        self._search_timer.start(SEARCH_DEBOUNCE_MS)

    def _perform_search(self):
        """Perform the actual search"""
        self.force_load_data()

    def _handle_namespace_change(self, namespace):
        if not namespace: return
        new_filter = "all" if namespace == "All Namespaces" else namespace
        if self.namespace_filter != new_filter:
            self.namespace_filter = new_filter
            self.force_load_data()

    
    def _handle_scroll_debounced(self):
        """Handle scroll after debounce period"""
        if not self.table:
            return
            
        scrollbar = self.table.verticalScrollBar()
        value = scrollbar.value()
        
        # Check if we need to load more data
        if value >= scrollbar.maximum() - (2 * self.table.rowHeight(0) if self.table.rowCount() > 0 else 0):
            self.load_data(load_more=True)
        
        # Update visible range for virtual scrolling
        self._update_visible_range()
    
    def _update_visible_range(self):
        """Update the visible range for virtual scrolling"""
        if not self.table:
            return
            
        # Calculate visible rows
        viewport_height = self.table.viewport().height()
        row_height = self.table.rowHeight(0) if self.table.rowCount() > 0 else 40
        visible_rows = (viewport_height // row_height) + self._render_buffer * 2
        
        scrollbar = self.table.verticalScrollBar()
        first_visible = scrollbar.value() // row_height
        
        self._visible_start = max(0, first_visible - self._render_buffer)
        self._visible_end = min(len(self.resources), first_visible + visible_rows)


    def showEvent(self, event):
        super().showEvent(event)
        if self.reload_on_show and not self.is_loading_initial and not self.resources:
            self.force_load_data()

    def cleanup_threads(self):
        threads_to_stop = [
            self.loading_thread, self.delete_thread, self.batch_delete_thread
        ]
        for thread in threads_to_stop:
            if thread and thread.isRunning():
                if hasattr(thread, 'stop'): thread.stop()
                thread.quit()
                if not thread.wait(500):
                    logging.warning(f"Thread {thread} did not terminate gracefully, forcing.")
                    thread.terminate()
        self.loading_thread = None; self.delete_thread = None; self.batch_delete_thread = None

    def cleanup_on_destroy(self):
        """Enhanced cleanup to prevent memory leaks"""
        try:
            self._shutting_down = True
            
            # Stop all timers
            for timer in [self._search_timer, self._scroll_timer, self._render_timer]:
                if timer.isActive():
                    timer.stop()
            
            # Clear caches
            self._data_cache.clear()
            self._cache_timestamps.clear()
            self.resources.clear()
            self.selected_items.clear()
            self._render_queue.clear()
            
            # Clear class-level caches periodically
            if len(self._age_cache) > 1000:
                self._age_cache.clear()
                self._age_cache_timestamps.clear()
            
            # Cleanup threads
            self.cleanup_threads()
            
            logging.debug(f"Cleanup completed for {self.__class__.__name__}")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")


    def closeEvent(self, event):
        """Handle close event with proper cleanup"""
        self.cleanup_on_destroy()
        if hasattr(super(), 'closeEvent'):
            super().closeEvent(event)
        else:
            event.accept()

    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup_on_destroy()
        except:
            pass

    def load_data(self, load_more=False):
        if self._shutting_down:
            return

        if load_more:
            if self.is_loading_more or self.all_data_loaded:
                return
            self.is_loading_more = True
            self._show_load_more_indicator_ui(True)
        else:
            if self.is_loading_initial:
                return
            self.is_loading_initial = True
            self.resources = []
            self.selected_items.clear()
            self.current_continue_token = None
            self.all_data_loaded = False
            if self.table:
                self.table.setRowCount(0)
            if hasattr(self, '_show_skeleton_loader') and self.table.rowCount() == 0:
                self._show_skeleton_loader()
            else:
                self._show_table_area()

        worker = KubernetesResourceLoader(
            self.resource_type, 
            self.namespace_filter,
            limit=self.items_per_page,
            continue_token=self.current_continue_token if load_more else None
        )
        
        worker.signals.finished.connect(
            lambda result: self.on_resources_loaded(result[0], result[1], result[2], load_more)
        )
        worker.signals.error.connect(
            lambda err_msg: self.on_load_error(err_msg, load_more)
        )
        
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"resource_load_{self.resource_type}_{load_more}", worker)


    def on_resources_loaded(self, new_resources, resource_type, next_continue_token, load_more=False):
        """Optimized resource loading handler with corrected state management"""
        if self._shutting_down:
            return
        
        # Store original scroll position for load more operations
        current_scroll_pos = 0
        if self.table and self.table.verticalScrollBar():
            current_scroll_pos = self.table.verticalScrollBar().value()

        # Apply search filter to new resources
        search_text = self.search_bar.text().lower() if self.search_bar and self.search_bar.text() else ""
        
        if search_text:
            filtered_new_resources = [
                r for r in new_resources
                if search_text in r.get("name", "").lower() or
                search_text in r.get("namespace", "").lower()
            ]
        else:
            filtered_new_resources = new_resources

        # Handle skeleton loading state
        if self.is_showing_skeleton:
            self.is_showing_skeleton = False
            if hasattr(self, 'skeleton_timer') and self.skeleton_timer.isActive():
                self.skeleton_timer.stop()

        # Process load more operations
        if load_more:
            self.is_loading_more = False
            self._show_load_more_indicator_ui(False)
            
            # Check if we actually received new data
            if not new_resources and not next_continue_token:
                self.all_data_loaded = True
                self.all_items_loaded_signal.emit()
                return
            
            # Append new resources if any were found
            if filtered_new_resources:
                start_row = len(self.resources)
                self.resources.extend(filtered_new_resources)
                
                # Update table with new rows
                self.table.setUpdatesEnabled(False)
                current_row_count = self.table.rowCount()
                self.table.setRowCount(current_row_count + len(filtered_new_resources))
                
                for i, resource_item in enumerate(filtered_new_resources):
                    self.populate_resource_row(current_row_count + i, resource_item)
                
                self.table.setUpdatesEnabled(True)
            
            self.load_more_complete.emit()
        else:
            # Handle initial load operations
            self.is_loading_initial = False
            self.resources = filtered_new_resources
            
            # Clear any existing empty state
            self._clear_empty_state()
            
            # Determine appropriate display state
            has_unfiltered_data = len(new_resources) > 0
            has_filtered_data = len(filtered_new_resources) > 0
            
            if has_filtered_data:
                # Display resources normally
                self.table.setRowCount(0)
                self.populate_table(self.resources)
                self._show_table_area()
                self.table.setSortingEnabled(True)
            elif has_unfiltered_data and search_text:
                # Resources exist but none match search criteria
                empty_message = f"No {self.resource_type} found matching '{search_text}'"
                description = "Try adjusting your search criteria or check if resources exist in other namespaces."
                self._show_message_in_table_area(empty_message, description)
            elif not has_unfiltered_data:
                # No resources exist at all
                empty_message = f"No {self.resource_type} found"
                description = f"No {self.resource_type} are currently available in the selected namespace."
                self._show_message_in_table_area(empty_message, description)

        # Update continuation token and completion status
        self.current_continue_token = next_continue_token
        
        # Set completion status based on token availability and resource count
        if not self.current_continue_token or not next_continue_token:
            self.all_data_loaded = True
            self.all_items_loaded_signal.emit()
        else:
            self.all_data_loaded = False

        # Update item count display
        self.items_count.setText(f"{len(self.resources)} items")

        # Process events and restore scroll position for load more
        QApplication.processEvents()
        if self.table and self.table.verticalScrollBar() and load_more:
            self.table.verticalScrollBar().setValue(current_scroll_pos)

    def _handle_scroll(self, value):
        """Enhanced scroll handler with proper completion checking"""
        if self.is_loading_initial or self.is_loading_more:
            return
        
        # Only trigger load more if we haven't loaded all data
        if self.all_data_loaded:
            return
        
        scrollbar = self.table.verticalScrollBar()
        
        # Check if we're near the bottom and have more data to load
        if (value >= scrollbar.maximum() - (2 * self.table.rowHeight(0) if self.table.rowCount() > 0 else 0) and
            self.current_continue_token):
            self.load_data(load_more=True)

    def _show_load_more_indicator_ui(self, show):
        """Enhanced load more indicator with completion awareness"""
        if self._shutting_down or not self.table:
            return
        
        # Only show indicator if we actually have more data to load
        if show and self.all_data_loaded:
            return
            
        if show and not self.all_data_loaded:
            if not self._load_more_indicator_widget:
                self._load_more_indicator_widget = QWidget(self)
                layout = QHBoxLayout(self._load_more_indicator_widget)
                layout.setContentsMargins(10, 5, 10, 5)
                
                spinner = QLabel("Loading more...")
                spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
                spinner.setStyleSheet("color: #ffffff; font-size: 12px; background: transparent;")
                layout.addWidget(spinner)
                
                self._load_more_indicator_widget.setStyleSheet("""
                    background-color: rgba(45, 45, 45, 0.9);
                    border-radius: 3px;
                """)
                self._load_more_indicator_widget.setFixedHeight(25)
            
            self._position_load_more_indicator()
            self._load_more_indicator_widget.show()
            self._load_more_indicator_widget.raise_()
            
        elif self._load_more_indicator_widget:
            self._load_more_indicator_widget.hide()

    def force_load_data(self):
        """Enhanced force load with proper state reset"""
        # Reset all loading states
        self.is_loading_initial = False
        self.is_loading_more = False
        self.all_data_loaded = False
        self.current_continue_token = None
        
        # Clear existing resources and UI state
        self.resources = []
        self.selected_items.clear()
        
        # Hide any load more indicators
        self._show_load_more_indicator_ui(False)
        
        # Clear empty state and prepare for loading
        self._clear_empty_state()
        
        if hasattr(self, '_show_skeleton_loader') and not self.resources:
            self._show_skeleton_loader()
        elif self.table:
            self.table.setRowCount(0)
        
        # Start fresh data load
        QTimer.singleShot(50, lambda: self.load_data(load_more=False))

    def _show_empty_state(self):
        """Improved empty state display with better condition checking"""
        try:
            # Only show empty state if we truly have no resources
            if hasattr(self, 'resources') and self.resources:
                logging.debug("Not showing empty state - resources exist")
                return
            
            # Clear any existing content
            self._clear_empty_state()
            
            # Determine appropriate empty state message
            search_text = self.search_bar.text().lower() if self.search_bar and self.search_bar.text() else ""
            
            if search_text:
                empty_message = f"No {self.resource_type} found matching '{search_text}'"
                description = "Try adjusting your search criteria or check if resources exist in other namespaces."
            else:
                empty_message = f"No {self.resource_type} found"
                description = f"No {self.resource_type} are currently available in the selected namespace."
            
            # Show the empty state message in the table area
            self._show_message_in_table_area(empty_message, description)
            
        except Exception as e:
            logging.error(f"Error showing empty state: {e}")
            # Fallback to simple message
            if hasattr(self, 'table'):
                self.table.setRowCount(0)

    def on_load_error(self, error_message, load_more=False):
        if self._shutting_down:
            return

        if self.is_showing_skeleton:
            self.is_showing_skeleton = False
            if hasattr(self, 'skeleton_timer') and self.skeleton_timer.isActive():
                self.skeleton_timer.stop()

        if load_more:
            self.is_loading_more = False
            self._show_load_more_indicator_ui(False)
            logging.error(f"Error loading more items for {self.resource_type}: {error_message}")
            if hasattr(self, 'show_transient_error_message'):
                self.show_transient_error_message(f"Failed to load more: {error_message}")
        else:
            self.is_loading_initial = False
            self.resources = []
            
            # Clear any existing content and show error within table
            self._clear_empty_state()
            
            error_title = f"Error loading {self.resource_type}"
            error_description = f"{error_message}\n\nClick Refresh to try again."
            
            self._show_message_in_table_area(error_title, error_description, is_error=True)
            
            logging.error(f"Initial load error for {self.resource_type}: {error_message}")

    def _show_table_area(self):
        """Ensure the table is visible in the stacked widget"""
        if self._table_stack:
            self._table_stack.setCurrentWidget(self.table)

    def _position_load_more_indicator(self):
        """Position the load more indicator at the bottom of the table"""
        if not self._load_more_indicator_widget or not self.table:
            return
            
        table_geometry = self.table.geometry()
        indicator_width = table_geometry.width() - 40
        indicator_x = table_geometry.x() + 20
        indicator_y = table_geometry.bottom() - 30
        
        self._load_more_indicator_widget.setFixedWidth(indicator_width)
        self._load_more_indicator_widget.move(indicator_x, indicator_y)

    def reset_default_column_widths(self):
        """Reset columns to their default widths"""
        if hasattr(self, 'configure_columns'):
            self.configure_columns()
            
    def fit_columns_to_content(self):
        """Automatically resize columns to fit their content"""
        if not hasattr(self, 'table') or not self.table:
            return
            
        header = self.table.horizontalHeader()
        
        # Temporarily change resizable columns to ResizeToContents
        original_modes = {}
        for i in range(self.table.columnCount()):
            if header.sectionResizeMode(i) == QHeaderView.ResizeMode.Interactive:
                original_modes[i] = QHeaderView.ResizeMode.Interactive
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        # Allow Qt to calculate optimal sizes
        QApplication.processEvents()
        
        # Restore Interactive mode with calculated widths
        for col, mode in original_modes.items():
            calculated_width = header.sectionSize(col)
            header.setSectionResizeMode(col, mode)
            # Ensure minimum width while using calculated optimal width
            final_width = max(80, calculated_width)
            header.resizeSection(col, final_width)

    def _adapt_columns_to_screen(self):
        """Adapt column widths to utilize full screen width"""
        if not hasattr(self, 'table') or not self.table:
            return
            
        # Get the actual usable width of the table viewport
        viewport_width = self.table.viewport().width()
        if viewport_width <= 0:
            return
        
        header = self.table.horizontalHeader()
        
        # Calculate space used by fixed columns and identify interactive columns
        fixed_width = 0
        interactive_columns = []
        stretch_column = None
        
        for i in range(self.table.columnCount()):
            if self.table.isColumnHidden(i):
                continue
                
            resize_mode = header.sectionResizeMode(i)
            if resize_mode == QHeaderView.ResizeMode.Fixed:
                fixed_width += header.sectionSize(i)
            elif resize_mode == QHeaderView.ResizeMode.Interactive:
                interactive_columns.append(i)
            elif resize_mode == QHeaderView.ResizeMode.Stretch:
                stretch_column = i
        
        # Calculate remaining space for interactive columns
        remaining_width = viewport_width - fixed_width
        
        if interactive_columns and remaining_width > 0:
            # Ensure interactive columns have reasonable widths
            min_width_per_column = 80
            total_min_width = len(interactive_columns) * min_width_per_column
            
            if stretch_column is not None:
                # Reserve minimum space for stretch column
                total_min_width += 100
            
            if remaining_width >= total_min_width:
                # Distribute width among interactive columns, leaving space for stretch column
                available_for_interactive = remaining_width - (100 if stretch_column is not None else 0)
                width_per_column = max(min_width_per_column, available_for_interactive // len(interactive_columns))
                
                for col in interactive_columns:
                    header.resizeSection(col, width_per_column)
            else:
                # Set minimum widths if space is limited
                for col in interactive_columns:
                    header.resizeSection(col, min_width_per_column)

    def resizeEvent(self, event):
        """Handle window resize for optimal column layout with full width utilization"""
        super().resizeEvent(event)
        
        # Ensure immediate adaptation to new size
        if hasattr(self, 'table') and self.table:
            if not hasattr(self, '_resize_timer'):
                self._resize_timer = QTimer()
                self._resize_timer.setSingleShot(True)
                self._resize_timer.timeout.connect(self._ensure_full_width_utilization)
            
            self._resize_timer.stop()
            self._resize_timer.start(150)

    def _ensure_full_width_utilization(self):
        """Ensure the table uses the complete available width"""
        if not hasattr(self, 'table') or not self.table:
            return
        
        # Force the table to recalculate its layout
        self.table.updateGeometry()
        QApplication.processEvents()
        
        # Apply width adaptation
        self._adapt_columns_to_screen()
        
        # Additional check to eliminate any remaining space
        self._eliminate_rightmost_space()

    def _eliminate_rightmost_space(self):
        """Eliminate any remaining space on the right side of the table"""
        if not hasattr(self, 'table') or not self.table:
            return
            
        header = self.table.horizontalHeader()
        viewport_width = self.table.viewport().width()
        
        # Calculate current total width of all visible columns
        current_total_width = 0
        stretch_column = None
        last_interactive_column = None
        
        for i in range(self.table.columnCount()):
            if self.table.isColumnHidden(i):
                continue
                
            current_total_width += header.sectionSize(i)
            
            if header.sectionResizeMode(i) == QHeaderView.ResizeMode.Stretch:
                stretch_column = i
            elif header.sectionResizeMode(i) == QHeaderView.ResizeMode.Interactive:
                last_interactive_column = i
        
        # If there is remaining space, add it to the stretch column or last interactive column
        remaining_space = viewport_width - current_total_width
        
        if remaining_space > 0:
            target_column = stretch_column if stretch_column is not None else last_interactive_column
            
            if target_column is not None:
                current_width = header.sectionSize(target_column)
                new_width = current_width + remaining_space
                
                # Temporarily change to interactive mode to set exact width
                original_mode = header.sectionResizeMode(target_column)
                header.setSectionResizeMode(target_column, QHeaderView.ResizeMode.Interactive)
                header.resizeSection(target_column, new_width)
                
                # Restore original mode if it was stretch
                if original_mode == QHeaderView.ResizeMode.Stretch:
                    header.setSectionResizeMode(target_column, QHeaderView.ResizeMode.Stretch)

    def showEvent(self, event):
        """Ensure proper sizing when page becomes visible"""
        super().showEvent(event)

        if self.reload_on_show and not self.is_loading_initial and not self.resources:
            self.force_load_data()

        # Apply screen adaptation after the widget is fully displayed
        if hasattr(self, 'table') and self.table:
            QTimer.singleShot(100, self._adapt_columns_to_screen)

    def populate_table(self, resources_to_populate):
        """Optimized table population with progressive rendering"""
        if not self.table:
            return
            
        self.table.setUpdatesEnabled(False)
        try:
            # Clear existing content
            self.table.setRowCount(0)
            
            # Set total row count
            total_rows = len(resources_to_populate)
            self.table.setRowCount(total_rows)
            
            # Queue resources for progressive rendering
            self._render_queue = list(enumerate(resources_to_populate))
            
            # Start progressive rendering
            if not self._render_timer.isActive():
                self._render_timer.start(10)  # Render every 10ms
                
        finally:
            self.table.setUpdatesEnabled(True)

    def _render_next_batch(self):
        """Render next batch of rows progressively"""
        if not self._render_queue:
            self._render_timer.stop()
            return
        
        # Disable updates for batch
        self.table.setUpdatesEnabled(False)
        
        try:
            # Render a batch of rows
            batch = self._render_queue[:BATCH_SIZE]
            self._render_queue = self._render_queue[BATCH_SIZE:]
            
            for row, resource in batch:
                self.populate_resource_row(row, resource)
                
            # Process events to keep UI responsive
            if len(self._render_queue) % 100 == 0:
                QApplication.processEvents()
                
        finally:
            self.table.setUpdatesEnabled(True)


    def populate_resource_row(self, row, resource):
        raise NotImplementedError("Subclasses must implement populate_resource_row")


    def _handle_action(self, action, row):
        """Handle action button clicks with pod-specific logic."""
        if row >= len(self.resources):
            return

        resource = self.resources[row]
        resource_name = resource.get("name", "")
        resource_namespace = resource.get("namespace", "")

        if action == "View Logs":
            # Double-check this is a pod resource
            if self.resource_type == "pods":
                self._handle_view_logs(resource_name, resource_namespace, resource)
            else:
                self._show_logs_error("Logs are only available for pod resources.")
        if action == "SSH":
            # SSH action - only available for pods
            if self.resource_type == "pods":
                self._handle_ssh_into_pod(resource_name, resource_namespace, resource)
            else:
                self._show_ssh_error("SSH is only available for pod resources.")

        elif action == "Edit":
            self._handle_edit_resource(resource_name, resource_namespace, resource)
        elif action == "Delete":
            self.delete_resource(resource_name, resource_namespace)

    def _handle_edit_resource(self, resource_name, resource_namespace, resource):
        """Handle edit resource action - placeholder for future implementation"""
        # TODO: Implement resource editing functionality
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Edit Resource",
                                f"Edit functionality for {resource_name} will be implemented soon.")

    def _handle_ssh_into_pod(self, resource_name, resource_namespace, resource):
        """Handle SSH into pod action with validation"""
        try:
            # Validate this is actually a pod and it's running
            is_valid, message = self._validate_pod_for_ssh(resource_name, resource_namespace)
            if not is_valid:
                self._show_ssh_error(f"Cannot SSH into pod: {message}")
                return

            # Get the terminal panel
            terminal_panel = self._get_terminal_panel()
            if not terminal_panel:
                self._show_ssh_error("Terminal panel not available. Please ensure you're in cluster view.")
                return

            # Show the terminal if it's hidden
            if not terminal_panel.is_visible:
                terminal_panel.show_terminal()

            # Create or switch to SSH tab
            self._create_ssh_tab(terminal_panel, resource_name, resource_namespace, resource)

        except Exception as e:
            logging.error(f"Error handling SSH for {resource_name}: {e}")
            self._show_ssh_error(f"Error opening SSH session: {str(e)}")

    def _validate_pod_for_ssh(self, resource_name, resource_namespace):
        """Validate that the pod is suitable for SSH access"""
        try:
            kube_client = get_kubernetes_client()
            if not kube_client or not kube_client.v1:
                return False, "Kubernetes client not available"
              
            # Get the pod to validate it exists and is running
            try:
                pod = kube_client.v1.read_namespaced_pod(name=resource_name, namespace=resource_namespace)

                # Check if pod is running
                if pod.status.phase != "Running":
                    return False, f"Pod is not running (status: {pod.status.phase})"

                # Check if pod has at least one container
                if not pod.spec.containers:
                    return False, "Pod has no containers"

                return True, "Pod validated successfully"

            except ApiException as e:
                if e.status == 404:
                    return False, f"Pod '{resource_name}' not found in namespace '{resource_namespace}'"
                elif e.status == 403:
                    return False, "Access denied. Check RBAC permissions for pod access."
                else:
                    return False, f"API error: {e.reason}"
                  
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def _create_ssh_tab(self, terminal_panel, pod_name, namespace, resource):
        """Create an SSH tab for pod access"""
        try:
            # Check if an SSH tab for this pod already exists
            ssh_tab_name = f"SSH: {pod_name}"
            existing_tab_index = None

            for i, tab_data in enumerate(terminal_panel.terminal_tabs):
                if tab_data.get('is_ssh_tab') and tab_data.get('pod_name') == pod_name:
                    existing_tab_index = i
                    break

            if existing_tab_index is not None:
                # Switch to existing SSH tab
                terminal_panel.switch_to_terminal_tab(existing_tab_index)
                # Optionally reconnect or refresh the session
                ssh_session = terminal_panel.terminal_tabs[existing_tab_index].get('ssh_session')
                if ssh_session and hasattr(ssh_session, 'reconnect'):
                    ssh_session.reconnect()
            else:
                # Create new SSH tab
                new_tab_index = terminal_panel.create_ssh_tab(pod_name, namespace)
                if new_tab_index is not None:
                    terminal_panel.switch_to_terminal_tab(new_tab_index)

        except Exception as e:
            logging.error(f"Error creating SSH tab for {pod_name}: {e}")
            self._show_ssh_error(f"Error creating SSH tab: {str(e)}")

    def _show_ssh_error(self, error_message):
        """Show error message for SSH functionality"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "SSH Error", error_message)
        except Exception as e:
            logging.error(f"Error showing SSH error message: {e}")


    def _validate_pod_resource(self, resource_name, resource_namespace):
        """Validate that the resource is actually a pod using Kubernetes API"""
        try:
            kube_client = get_kubernetes_client()
            if not kube_client or not kube_client.v1:
                return False, "Kubernetes client not available"

            # Try to get the pod to validate it exists
            try:
                pod = kube_client.v1.read_namespaced_pod(name=resource_name, namespace=resource_namespace)
                return True, "Pod validated successfully"
            except ApiException as e:
                if e.status == 404:
                    return False, f"Pod '{resource_name}' not found in namespace '{resource_namespace}'"
                elif e.status == 403:
                    return False, "Access denied. Check RBAC permissions for pod access."
                else:
                    return False, f"API error: {e.reason}"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def _handle_view_logs(self, resource_name, resource_namespace, resource):
        """Handle View Logs action for pods with validation"""
        try:
            # Validate this is actually a pod
            is_valid, message = self._validate_pod_resource(resource_name, resource_namespace)
            if not is_valid:
                self._show_logs_error(f"Cannot view logs: {message}")
                return

            # Get the terminal panel with better error handling

            terminal_panel = self._get_terminal_panel()
            if not terminal_panel:
                self._show_logs_error("Terminal panel not available. Please ensure you're in cluster view.")
                return
              
            # Show the terminal if it's hidden
            if hasattr(terminal_panel, 'is_visible') and not terminal_panel.is_visible:
                terminal_panel.show_terminal()

            # Create or switch to logs tab with error handling
            try:
                self._create_enhanced_logs_tab(terminal_panel, resource_name, resource_namespace, resource)
            except Exception as e:
                logging.error(f"Error creating logs tab: {e}")
                self._show_logs_error(f"Failed to create logs tab: {str(e)}")

        except Exception as e:
            logging.error(f"Error handling view logs for {resource_name}: {e}")
            self._show_logs_error(f"Error opening logs: {str(e)}")

    def _get_terminal_panel(self):
        """Get the terminal panel from the cluster view"""
        try:
            # Navigate up the widget hierarchy to find the cluster view
            parent = self.parent()
            while parent:
                if hasattr(parent, 'terminal_panel'):
                    return parent.terminal_panel
                parent = parent.parent()

            # Alternative: check if we can access through the main window
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.allWidgets():
                    if hasattr(widget, 'terminal_panel') and widget.terminal_panel:
                        return widget.terminal_panel

            return None
        except Exception as e:
            logging.error(f"Error getting terminal panel: {e}")
            return None

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

    # Updated base_resource_page.py - Integration with Enhanced Logs Viewer

    def _create_enhanced_logs_tab(self, terminal_panel, pod_name, namespace, resource):
        """Create an enhanced logs tab with search, filter and live streaming"""
        try:
            # Check if a logs tab for this pod already exists
            logs_tab_name = f"Logs: {pod_name}"
            existing_tab_index = None

            for i, tab_data in enumerate(terminal_panel.terminal_tabs):
                if tab_data.get('is_logs_tab') and tab_data.get('pod_name') == pod_name:
                    existing_tab_index = i
                    break

            if existing_tab_index is not None:
                # Switch to existing logs tab and refresh
                terminal_panel.switch_to_terminal_tab(existing_tab_index)
                logs_viewer = terminal_panel.terminal_tabs[existing_tab_index].get('logs_viewer')
                if logs_viewer:
                    logs_viewer.refresh_logs()
            else:
                # Create new enhanced logs tab
                new_tab_index = self._create_new_enhanced_logs_tab(terminal_panel, logs_tab_name, pod_name, namespace)
                if new_tab_index is not None:
                    terminal_panel.switch_to_terminal_tab(new_tab_index)

        except Exception as e:
            logging.error(f"Error creating enhanced logs tab for {pod_name}: {e}")
            self._show_logs_error(f"Error creating logs tab: {str(e)}")

    def _show_logs_error(self, error_message):
        """Show error message for logs functionality"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "View Logs Error", error_message)
        except Exception as e:
            logging.error(f"Error showing logs error message: {e}")

    def _create_new_enhanced_logs_tab(self, terminal_panel, tab_name, pod_name, namespace):
        """Create a new enhanced logs tab with search and streaming capabilities"""
        try:
            from PyQt6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QWidget
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QFont

            tab_index = len(terminal_panel.terminal_tabs)

            # Create tab widget
            tab_widget = QWidget()
            tab_widget.setFixedHeight(28)
            tab_widget.setCursor(Qt.CursorShape.PointingHandCursor)
            tab_layout = QHBoxLayout(tab_widget)
            tab_layout.setContentsMargins(8, 0, 8, 0)
            tab_layout.setSpacing(6)

            # Create label with enhanced logs icon and name
            label = QLabel(f"📋 {pod_name}")
            label.setStyleSheet("""
                color: #4CAF50;
                background: transparent;
                font-size: 12px;
                font-weight: bold;
                text-decoration: none;
                border: none;
                outline: none;
            """)
            
            # Create close button
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(16, 16)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #9ca3af;
                    border: none;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #FF4D4D;
                    color: white;
                    border-radius: 8px;
                }
            """)

            tab_layout.addWidget(label)
            tab_layout.addWidget(close_btn)

            # Create tab button
            tab_btn = QPushButton()
            tab_btn.setCheckable(True)
            tab_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-right: 1px solid #3d3d3d;
                    border-left: 1px solid #3d3d3d;
                    border-bottom: 1px solid #3d3d3d;
                    border-top: 1px solid #3d3d3d;
                    padding: 0px 35px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(76, 175, 80, 0.1);
                }
                QPushButton:checked {
                    background-color: #1E1E1E;
                    border-bottom: 2px solid #4CAF50;
                }
            """)
            tab_btn.setLayout(tab_layout)

            # Create tab container
            tab_container = QWidget()
            container_layout = QHBoxLayout(tab_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            container_layout.addWidget(tab_btn)

            # Connect signals
            close_btn.clicked.connect(lambda: self._close_enhanced_logs_tab(terminal_panel, tab_index))
            tab_btn.clicked.connect(lambda: terminal_panel.switch_to_terminal_tab(tab_index))

            # Add tab to header
            terminal_panel.unified_header.add_tab(tab_container)

            # Create enhanced logs viewer widget
            from UI.TerminalPanel import EnhancedLogsViewer  # Import the enhanced viewer
            logs_viewer = EnhancedLogsViewer(pod_name, namespace)

            # Add the logs viewer to terminal stack
            terminal_panel.stack_layout.addWidget(logs_viewer)
            logs_viewer.setVisible(False)

            # Store tab data with enhanced information
            terminal_data = {
                'tab_button': tab_btn,
                'tab_container': tab_container,
                'content_widget': logs_viewer,  # Use logs_viewer as content
                'logs_viewer': logs_viewer,     # Direct reference to logs viewer
                'terminal_widget': None,        # No terminal widget for logs tabs
                'process': None,                # No process for logs tabs
                'started': True,                # Always "started" for logs
                'active': False,
                'is_logs_tab': True,           # Mark as enhanced logs tab
                'pod_name': pod_name,
                'namespace': namespace
            }
            terminal_panel.terminal_tabs.append(terminal_data)

            return tab_index

        except Exception as e:
            logging.error(f"Error creating new enhanced logs tab: {e}")
            return None

    def _close_enhanced_logs_tab(self, terminal_panel, tab_index):
        """Close an enhanced logs tab and cleanup resources"""
        try:
            if tab_index >= len(terminal_panel.terminal_tabs):
                return

            terminal_data = terminal_panel.terminal_tabs[tab_index]
            logs_viewer = terminal_data.get('logs_viewer')

            # Stop log streaming before closing
            if logs_viewer and hasattr(logs_viewer, 'stop_log_stream'):
                logs_viewer.stop_log_stream()

            # Close the tab using terminal panel's method
            terminal_panel.close_terminal_tab(tab_index)

        except Exception as e:
            logging.error(f"Error closing enhanced logs tab: {e}")

    # Update the terminal panel switch method to handle enhanced logs tabs
    def switch_to_enhanced_logs_tab(self, tab_index):
        """Switch to enhanced logs tab - add this to TerminalPanel class"""
        if tab_index >= len(self.terminal_tabs):
            return

        # Hide all content widgets
        for i, tab_data in enumerate(self.terminal_tabs):
            content_widget = tab_data.get('content_widget')
            if content_widget:
                content_widget.setVisible(i == tab_index)

            # Update tab button states
            tab_button = tab_data.get('tab_button')
            if tab_button:
                tab_button.setChecked(i == tab_index)

            tab_data['active'] = i == tab_index

        # Set focus and update active index
        self.active_terminal_index = tab_index
        terminal_data = self.terminal_tabs[tab_index]

        # Handle different tab types
        if terminal_data.get('is_logs_tab'):
            # For logs tabs, focus the logs viewer
            logs_viewer = terminal_data.get('logs_viewer')
            if logs_viewer:
                logs_viewer.setFocus()
        else:
            # For regular terminal tabs, focus the terminal widget
            terminal_widget = terminal_data.get('terminal_widget')
            if terminal_widget:
                terminal_widget.setFocus()
                terminal_widget.ensure_cursor_at_input()

            # Start process if not started
            if not terminal_data.get('started', False):
                self.start_terminal_process(tab_index)

    # Enhanced close method for terminal panel
    def close_enhanced_terminal_tab(self, tab_index):
        """Enhanced close method that handles both regular and logs tabs"""
        if tab_index >= len(self.terminal_tabs):
            return

        if len(self.terminal_tabs) <= 1:
            self.hide_terminal()
            return

        terminal_data = self.terminal_tabs[tab_index]

        # Handle enhanced logs tab cleanup
        if terminal_data.get('is_logs_tab'):
            logs_viewer = terminal_data.get('logs_viewer')
            if logs_viewer and hasattr(logs_viewer, 'stop_log_stream'):
                logs_viewer.stop_log_stream()
        else:
            # Handle regular terminal tab cleanup
            process = terminal_data.get('process')
            if process and process.state() == QProcess.ProcessState.Running:
                try:
                    process.terminate()
                    if not process.waitForFinished(500):
                        process.kill()
                except Exception as e:
                    print(f"Error terminating process: {e}")

        # Remove tab from UI
        tab_container = terminal_data.get('tab_container')
        if tab_container:
            self.unified_header.remove_tab(tab_container)

        content_widget = terminal_data.get('content_widget')
        if content_widget:
            self.stack_layout.removeWidget(content_widget)
            content_widget.deleteLater()

        # Remove from tabs list
        self.terminal_tabs.pop(tab_index)
        self.active_terminal_index = min(max(0, self.active_terminal_index), len(self.terminal_tabs) - 1)

        # Update remaining tabs' close button connections
        for i, tab_data in enumerate(self.terminal_tabs):
            tab_container = tab_data.get('tab_container')
            if tab_container:
                for child in tab_container.findChildren(QPushButton):
                    if child.text() == "✕":
                        try:
                            child.clicked.disconnect()
                        except TypeError:
                            pass
                        child.clicked.connect(lambda checked=False, idx=i: self.close_terminal_tab(idx))

        # Switch to active tab if tabs remain
        if self.terminal_tabs:
            self.switch_to_terminal_tab(self.active_terminal_index)

        self.renumber_tabs()

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
        if hasattr(self, 'delete_thread') and self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.wait(300)
        if not self.selected_items:
            QMessageBox.information(self, "No Selection", "No resources selected for deletion.")
            return
        count = len(self.selected_items)
        result = QMessageBox.warning(self, "Confirm Deletion",
                                     f"Are you sure you want to delete {count} selected {self.resource_type}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes: return

        resources_list = list(self.selected_items)

        from PyQt6.QtWidgets import QProgressDialog
        progress = QProgressDialog(f"Deleting {count} {self.resource_type}...", "Cancel", 0, count, self)
        progress.setWindowTitle("Deleting Resources"); progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0); progress.setAutoClose(False); progress.setValue(0)

        self.batch_delete_thread = BatchResourceDeleterThread(self.resource_type, resources_list)
        self.batch_delete_thread.batch_delete_progress.connect(progress.setValue)
        self.batch_delete_thread.batch_delete_completed.connect(
            lambda success, errors: self.on_batch_delete_completed(success, errors, progress))
        self.batch_delete_thread.start()

    def on_batch_delete_completed(self, success_list, error_list, progress_dialog):
        progress_dialog.close()
        success_count = len(success_list)
        error_count = len(error_list)
        result_message = f"Deleted {success_count} of {success_count + error_count} {self.resource_type}."
        if error_count > 0:
            result_message += f"\n\nFailed to delete {error_count} resources:"
            for name, namespace, error in error_list[:5]:
                ns_text = f" in namespace {namespace}" if namespace else ""
                result_message += f"\n- {name}{ns_text}: {error}"
            if error_count > 5: result_message += f"\n... and {error_count - 5} more."
        QMessageBox.information(self, "Deletion Results", result_message)
        self.force_load_data()

    def delete_resource(self, resource_name, resource_namespace):
        if hasattr(self, 'delete_thread') and self.delete_thread and self.delete_thread.isRunning():
            self.delete_thread.wait(300)
        ns_text = f" in namespace {resource_namespace}" if resource_namespace else ""
        result = QMessageBox.warning(self, "Confirm Deletion",
                                     f"Are you sure you want to delete {self.resource_type}/{resource_name}{ns_text}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes: return

        self.delete_thread = ResourceDeleterThread(self.resource_type, resource_name, resource_namespace)
        self.delete_thread.delete_completed.connect(self.on_delete_completed)
        self.delete_thread.start()

    def on_delete_completed(self, success, message, resource_name, resource_namespace):
        if success:
            QMessageBox.information(self, "Deletion Successful", message)
            self.selected_items.discard((resource_name, resource_namespace))
            self.force_load_data()
        else:
            QMessageBox.critical(self, "Deletion Failed", message)