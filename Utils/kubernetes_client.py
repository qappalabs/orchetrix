"""
Optimized Kubernetes Client - Streamlined backward compatibility wrapper
Provides high-performance access to the new service architecture while maintaining API compatibility.
Designed for minimal overhead and maximum performance.
"""

import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

# Import the new service architecture
from Services.kubernetes.kubernetes_service import get_kubernetes_service, KubeCluster
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager


class ResourceUpdateWorker(EnhancedBaseWorker):
    """Worker for async resource updates"""
    
    def __init__(self, client_instance, resource_type, resource_name, namespace, yaml_data):
        super().__init__(f"resource_update_{resource_type}_{resource_name}")
        self.client_instance = client_instance
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.yaml_data = yaml_data

    def execute(self):
        return self.client_instance._update_resource_sync(
            self.resource_type,
            self.resource_name,
            self.namespace,
            self.yaml_data
        )


class KubernetesClient(QObject):
    """
    Backward compatibility wrapper for KubernetesService
    Maintains the same API as the original monolithic client
    """
    
    # Signals - same as before for compatibility
    clusters_loaded = pyqtSignal(list)
    cluster_info_loaded = pyqtSignal(dict)
    cluster_metrics_updated = pyqtSignal(dict)
    cluster_issues_updated = pyqtSignal(list)
    resource_detail_loaded = pyqtSignal(dict)
    resource_updated = pyqtSignal(dict)
    pod_logs_loaded = pyqtSignal(dict)
    pods_data_loaded = pyqtSignal(list)
    api_error = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    # Deployment rollback signals
    deployment_history_loaded = pyqtSignal(list)
    deployment_rollback_completed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        
        # Get the new service architecture
        self.service = get_kubernetes_service()
        
        # Connect signals for backward compatibility
        self._connect_service_signals()
        
        # Maintain backward compatibility attributes
        self.clusters = []
        self.current_cluster = None
        self._shutting_down = False
        
        logging.info("KubernetesClient initialized with new service architecture")
    
    def _connect_service_signals(self):
        """Connect service signals to maintain backward compatibility"""
        self.service.clusters_loaded.connect(self.clusters_loaded.emit)
        self.service.cluster_info_loaded.connect(self.cluster_info_loaded.emit)
        self.service.cluster_metrics_updated.connect(self.cluster_metrics_updated.emit)
        self.service.cluster_issues_updated.connect(self.cluster_issues_updated.emit)
        self.service.resource_detail_loaded.connect(self.resource_detail_loaded.emit)
        self.service.resource_updated.connect(self.resource_updated.emit)
        self.service.pod_logs_loaded.connect(self.pod_logs_loaded.emit)
        self.service.error_occurred.connect(self.error_occurred.emit)
    
    # Backward compatibility API methods
    
    @property
    def v1(self):
        """Access to CoreV1Api - backward compatibility"""
        return self.service.api_service.v1
    
    @property
    def apps_v1(self):
        """Access to AppsV1Api - backward compatibility"""
        return self.service.api_service.apps_v1
    
    @property
    def networking_v1(self):
        """Access to NetworkingV1Api - backward compatibility"""
        return self.service.api_service.networking_v1
    
    @property
    def storage_v1(self):
        """Access to StorageV1Api - backward compatibility"""
        return self.service.api_service.storage_v1
    
    @property
    def rbac_v1(self):
        """Access to RbacAuthorizationV1Api - backward compatibility"""
        return self.service.api_service.rbac_v1
    
    @property
    def batch_v1(self):
        """Access to BatchV1Api - backward compatibility"""
        return self.service.api_service.batch_v1
    
    @property
    def autoscaling_v1(self):
        """Access to AutoscalingV1Api - backward compatibility"""
        return self.service.api_service.autoscaling_v1
    
    @property
    def autoscaling_v2(self):
        """Access to AutoscalingV2Api - backward compatibility"""
        return self.service.api_service.autoscaling_v2
    
    @property
    def policy_v1(self):
        """Access to PolicyV1Api - backward compatibility"""
        return self.service.api_service.policy_v1
    
    @property
    def scheduling_v1(self):
        """Access to SchedulingV1Api - backward compatibility"""
        return self.service.api_service.scheduling_v1
    
    @property
    def node_v1(self):
        """Access to NodeV1Api - backward compatibility"""
        return self.service.api_service.node_v1
    
    @property
    def admissionregistration_v1(self):
        """Access to AdmissionregistrationV1Api - backward compatibility"""
        return self.service.api_service.admissionregistration_v1
    
    @property
    def coordination_v1(self):
        """Access to CoordinationV1Api - backward compatibility"""
        return self.service.api_service.coordination_v1
    
    @property
    def apiextensions_v1(self):
        """Access to ApiextensionsV1Api - backward compatibility"""
        return self.service.api_service.apiextensions_v1
    
    @property
    def custom_objects_api(self):
        """Access to CustomObjectsApi - backward compatibility"""
        return self.service.api_service.custom_objects_api
    
    @property
    def version_api(self):
        """Access to VersionApi - backward compatibility"""
        return self.service.api_service.version_api
    
    @property
    def log_streamer(self):
        """Access to log streamer - backward compatibility"""
        return self.service.get_log_streamer()
    
    def load_kube_config(self, context_name: str = None) -> bool:
        """Load kubeconfig - backward compatibility"""
        return self.service.api_service.load_kube_config(context_name)
    
    def connect_to_cluster(self, cluster_name: str, context: str = None) -> bool:
        """Connect to cluster - backward compatibility"""
        result = self.service.connect_to_cluster(cluster_name, context)
        if result:
            self.current_cluster = cluster_name
        return result
    
    def disconnect_from_cluster(self):
        """Disconnect from cluster - backward compatibility"""
        self.service.disconnect_from_cluster()
        self.current_cluster = None
    
    def get_cluster_metrics(self) -> Optional[Dict[str, Any]]:
        """Get cluster metrics - backward compatibility"""
        metrics = self.service.get_cluster_metrics()
        if metrics:
            # Update current_cluster for compatibility
            self.current_cluster = self.service.get_current_cluster()
        return metrics
    
    def get_cluster_issues(self) -> List[Dict[str, Any]]:
        """Get cluster issues - backward compatibility"""
        return self.service.get_cluster_issues()
    
    def get_pod_logs(self, pod_name: str, namespace: str, container: str = None, 
                     tail_lines: int = 100) -> Optional[str]:
        """Get pod logs - backward compatibility"""
        return self.service.get_pod_logs(pod_name, namespace, container, tail_lines)
    
    def start_log_stream(self, pod_name: str, namespace: str, container: str = None, 
                        tail_lines: int = 200):
        """Start log stream - backward compatibility"""
        self.service.start_log_stream(pod_name, namespace, container, tail_lines)
    
    def stop_log_stream(self, pod_name: str, namespace: str, container: str = None):
        """Stop log stream - backward compatibility"""
        self.service.stop_log_stream(pod_name, namespace, container)
    
    def get_events_for_resource(self, resource_type: str, resource_name: str, 
                               namespace: str = "default") -> List[Dict[str, Any]]:
        """Get events for resource - backward compatibility"""
        return self.service.get_events_for_resource(resource_type, resource_name, namespace)
    
    def get_node_metrics(self, node_name: str) -> Optional[Dict[str, Any]]:
        """Get node metrics - backward compatibility"""
        return self.service.get_node_metrics(node_name)
    
    def get_cluster_version(self) -> Optional[str]:
        """Get cluster version - backward compatibility"""
        return self.service.get_cluster_version()
    
    def is_connected(self) -> bool:
        """Check if connected - backward compatibility"""
        return self.service.is_connected()
    
    def start_metrics_polling(self, interval_ms: int = 5000):
        """Start metrics polling - backward compatibility"""
        self.service.start_polling(metrics_interval=interval_ms)
    
    def stop_metrics_polling(self):
        """Stop metrics polling - backward compatibility"""
        self.service.stop_polling()
    
    def start_issues_polling(self, interval_ms: int = 10000):
        """Start issues polling - backward compatibility"""
        self.service.start_polling(issues_interval=interval_ms)
    
    def stop_issues_polling(self):
        """Stop issues polling - backward compatibility"""
        self.service.stop_polling()
    
    def refresh_metrics(self):
        """Refresh metrics - backward compatibility"""
        # Trigger immediate polling
        if self.service.current_cluster:
            self.service._poll_metrics_async()
    
    def refresh_issues(self):
        """Refresh issues - backward compatibility"""
        # Trigger immediate polling
        if self.service.current_cluster:
            self.service._poll_issues_async()
    
    def load_clusters_async(self):
        """Load clusters asynchronously - backward compatibility"""
        self.service.load_clusters_async()
    
    # Deployment rollback functionality
    def get_deployment_rollout_history_async(self, deployment_name: str, namespace: str = "default"):
        """Get deployment rollout history asynchronously using QThread"""
        logging.info(f"Getting rollout history for deployment {deployment_name} in namespace {namespace}")
        
        from Utils.enhanced_worker import EnhancedBaseWorker
        
        class RolloutHistoryWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, deployment_name, namespace):
                super().__init__(f"rollout_history_{deployment_name}")
                self.client_instance = client_instance
                self.deployment_name = deployment_name
                self.namespace = namespace
            
            def execute(self):
                return self.client_instance._get_deployment_rollout_history_sync(
                    self.deployment_name, self.namespace
                )
        
        worker = RolloutHistoryWorker(self, deployment_name, namespace)
        
        # Connect signals with proper error handling
        def handle_success(result):
            try:
                self.deployment_history_loaded.emit(result)
            except Exception as e:
                logging.error(f"Error emitting history result: {str(e)}")
                self.api_error.emit(f"Failed to emit rollout history: {str(e)}")
        
        def handle_error(error):
            try:
                self.api_error.emit(f"Failed to get rollout history: {str(error)}")
            except Exception as e:
                logging.error(f"Error emitting history error: {str(e)}")
        
        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)
        
        # Submit to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"rollout_history_{deployment_name}", worker)
    
    def rollback_deployment_async(self, deployment_name: str, revision: int, namespace: str = "default"):
        """Rollback deployment to specific revision asynchronously using QThread"""
        logging.info(f"Rolling back deployment {deployment_name} to revision {revision} in namespace {namespace}")
        
        from Utils.enhanced_worker import EnhancedBaseWorker
        
        class RollbackWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, deployment_name, revision, namespace):
                super().__init__(f"rollback_{deployment_name}")
                self.client_instance = client_instance
                self.deployment_name = deployment_name
                self.revision = revision
                self.namespace = namespace
            
            def execute(self):
                return self.client_instance._rollback_deployment_sync(
                    self.deployment_name, self.revision, self.namespace
                )
        
        worker = RollbackWorker(self, deployment_name, revision, namespace)
        
        # Connect signals with proper error handling
        def handle_success(result):
            try:
                self.deployment_rollback_completed.emit(result)
            except Exception as e:
                logging.error(f"Error emitting rollback result: {str(e)}")
                error_result = {
                    "success": False,
                    "message": f"Signal emission failed: {str(e)}",
                    "deployment": deployment_name,
                    "revision": revision,
                    "namespace": namespace
                }
                self.deployment_rollback_completed.emit(error_result)
        
        def handle_error(error):
            try:
                error_result = {
                    "success": False,
                    "message": str(error),
                    "deployment": deployment_name,
                    "revision": revision,
                    "namespace": namespace
                }
                self.deployment_rollback_completed.emit(error_result)
            except Exception as e:
                logging.error(f"Error emitting rollback error: {str(e)}")
        
        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)
        
        # Submit to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"rollback_{deployment_name}", worker)
    
    def get_cluster_metrics_async(self):
        """Get cluster metrics asynchronously - backward compatibility"""
        # Trigger async metrics polling
        self.service._poll_metrics_async()
    
    def get_cluster_issues_async(self):
        """Get cluster issues asynchronously - backward compatibility"""
        # Trigger async issues polling
        self.service._poll_issues_async()
    
    def update_resource_async(self, resource_type: str, resource_name: str, namespace: str, resource_data: dict):
        """Update resource asynchronously using worker threads"""
        logging.info(f"Starting async update for {resource_type}/{resource_name} in namespace {namespace}")
        
        worker = ResourceUpdateWorker(self, resource_type, resource_name, namespace, resource_data)
        
        # Connect worker signals
        worker.signals.finished.connect(
            lambda result: self.resource_updated.emit(result) if result else None
        )
        worker.signals.error.connect(
            lambda error: self.resource_updated.emit({
                'success': False,
                'message': f"Update failed: {error}"
            })
        )
        
        # Submit worker to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"resource_update_{resource_type}_{resource_name}", worker)
    
    def _update_resource_sync(self, resource_type: str, resource_name: str, namespace: str, resource_data: dict):
        """Synchronous resource update - used by worker"""
        try:
            # Convert dict to proper Kubernetes object
            resource_body = resource_data
            
            # Map resource type to appropriate API call
            result = None
            
            if resource_type.lower() == "pod":
                result = self.v1.patch_namespaced_pod(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "service":
                result = self.v1.patch_namespaced_service(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "deployment":
                result = self.apps_v1.patch_namespaced_deployment(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "configmap":
                result = self.v1.patch_namespaced_config_map(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "secret":
                result = self.v1.patch_namespaced_secret(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "statefulset":
                result = self.apps_v1.patch_namespaced_stateful_set(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "daemonset":
                result = self.apps_v1.patch_namespaced_daemon_set(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "replicaset":
                result = self.apps_v1.patch_namespaced_replica_set(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "ingress":
                result = self.networking_v1.patch_namespaced_ingress(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() == "networkpolicy":
                result = self.networking_v1.patch_namespaced_network_policy(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            # Non-namespaced resources
            elif resource_type.lower() == "node":
                result = self.v1.patch_node(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() == "namespace":
                result = self.v1.patch_namespace(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() == "serviceaccount":
                result = self.v1.patch_namespaced_service_account(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["job", "jobs"]:
                result = self.batch_v1.patch_namespaced_job(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["cronjob", "cronjobs"]:
                result = self.batch_v1.patch_namespaced_cron_job(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["persistentvolumeclaim", "persistentvolumeclaims", "pvc"]:
                result = self.v1.patch_namespaced_persistent_volume_claim(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["persistentvolume", "persistentvolumes", "pv"]:
                result = self.v1.patch_persistent_volume(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() in ["endpoints"]:
                result = self.v1.patch_namespaced_endpoints(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["limitrange", "limitranges"]:
                result = self.v1.patch_namespaced_limit_range(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["resourcequota", "resourcequotas"]:
                result = self.v1.patch_namespaced_resource_quota(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["replicationcontroller", "replicationcontrollers", "rc"]:
                result = self.v1.patch_namespaced_replication_controller(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["role", "roles"]:
                result = self.rbac_v1.patch_namespaced_role(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["rolebinding", "rolebindings"]:
                result = self.rbac_v1.patch_namespaced_role_binding(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["clusterrole", "clusterroles"]:
                result = self.rbac_v1.patch_cluster_role(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() in ["clusterrolebinding", "clusterrolebindings"]:
                result = self.rbac_v1.patch_cluster_role_binding(
                    name=resource_name,
                    body=resource_body
                )
            elif resource_type.lower() in ["horizontalpodautoscaler", "horizontalpodautoscalers", "hpa"]:
                result = self.autoscaling_v2.patch_namespaced_horizontal_pod_autoscaler(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            elif resource_type.lower() in ["poddisruptionbudget", "poddisruptionbudgets", "pdb"]:
                result = self.policy_v1.patch_namespaced_pod_disruption_budget(
                    name=resource_name,
                    namespace=namespace,
                    body=resource_body
                )
            else:
                return {
                    "success": False,
                    "message": f"Resource type '{resource_type}' is not supported for updates"
                }
            
            if result:
                logging.info(f"Successfully updated {resource_type}/{resource_name}")
                return {
                    "success": True,
                    "message": f"Successfully updated {resource_type}/{resource_name}",
                    "resource": result.to_dict() if hasattr(result, 'to_dict') else str(result)
                }
            else:
                return {
                    "success": False,
                    "message": f"No result returned for {resource_type}/{resource_name} update"
                }
            
        except Exception as e:
            # Extract more readable error from Kubernetes API exceptions
            error_message = self._extract_readable_error(e)
            logging.error(f"Failed to update {resource_type}/{resource_name}: {error_message}")
            return {
                "success": False,
                "message": error_message
            }
    
    def _extract_readable_error(self, error) -> str:
        """Extract readable error message from Kubernetes API exceptions"""
        try:
            # Handle Kubernetes API exceptions
            if hasattr(error, 'body'):
                import json
                body = json.loads(error.body)
                if 'message' in body:
                    message = body['message']
                    
                    # Make common errors more user-friendly
                    if "forbidden" in message.lower():
                        return f"Permission denied: {message}\n\nTip: Check if you have the necessary RBAC permissions to edit this resource."
                    elif "invalid" in message.lower() and "immutable" in message.lower():
                        return f"Field cannot be changed: {message}\n\nTip: Some fields cannot be modified after resource creation."
                    elif "conflict" in message.lower():
                        return f"Resource conflict: {message}\n\nTip: Another process may have modified this resource. Try refreshing and editing again."
                    elif "not found" in message.lower():
                        return f"Resource not found: {message}\n\nTip: The resource may have been deleted by another process."
                    else:
                        return message
            
            # Handle standard exceptions with better context
            error_str = str(error)
            if "connection" in error_str.lower():
                return f"Connection error: {error_str}\n\nTip: Check your cluster connection and try again."
            elif "timeout" in error_str.lower():
                return f"Request timeout: {error_str}\n\nTip: The cluster may be slow to respond. Try again in a moment."
            else:
                return error_str
            
        except Exception:
            # Fallback to string representation
            return str(error)
    
    def validate_kubernetes_schema(self, resource_data: dict) -> tuple[bool, str]:
        """Enhanced validation of Kubernetes resource schema"""
        try:
            # Basic validation - check for required fields
            if not isinstance(resource_data, dict):
                return False, "Resource data must be a dictionary"
            
            if 'apiVersion' not in resource_data:
                return False, "Missing required field: apiVersion"
            
            if 'kind' not in resource_data:
                return False, "Missing required field: kind"
            
            if 'metadata' not in resource_data:
                return False, "Missing required field: metadata"
            
            # Validate metadata has name
            metadata = resource_data.get('metadata', {})
            if not isinstance(metadata, dict):
                return False, "metadata field must be a dictionary"
                
            if not metadata.get('name'):
                return False, "Missing required field: metadata.name"
            
            # Check for invalid field values
            name = metadata.get('name', '')
            if not isinstance(name, str) or not name.strip():
                return False, "metadata.name must be a non-empty string"
            
            # For Pod validation, be more lenient with container validation
            if resource_data.get('kind') == 'Pod':
                spec = resource_data.get('spec', {})
                containers = spec.get('containers', [])
                
                if containers:
                    container_names = [c.get('name', '') for c in containers]
                    # Only check for empty names, allow duplicate names (some use cases need this)
                    if any(not name for name in container_names):
                        return False, "All containers must have names"
                
                # Check for basic container structure
                for container in containers:
                    if not isinstance(container, dict):
                        return False, "Each container must be a dictionary"
                    if not container.get('image'):
                        return False, "All containers must have an image specified"
            
            return True, "Valid Kubernetes resource"
            
        except Exception as e:
            return False, f"Schema validation error: {str(e)}"

    def get_resource_detail_async(self, resource_type: str, resource_name: str, namespace: str = None):
        """Get resource detail asynchronously - backward compatibility"""
        try:
            # Map resource type to appropriate API call
            resource_detail = None
            
            if resource_type.lower() == "pod":
                if namespace:
                    resource_detail = self.v1.read_namespaced_pod(name=resource_name, namespace=namespace)
                else:
                    # Search efficiently in common namespaces instead of all namespaces
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.v1.read_namespaced_pod(name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            # Only log if it's not a simple "not found" error
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(f"Error searching for {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "service":
                if namespace:
                    resource_detail = self.v1.read_namespaced_service(name=resource_name, namespace=namespace)
                else:
                    # Search efficiently in common namespaces instead of all namespaces
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.v1.read_namespaced_service(name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(f"Error searching for service {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "deployment":
                if namespace:
                    resource_detail = self.apps_v1.read_namespaced_deployment(name=resource_name, namespace=namespace)
                else:
                    # Search efficiently in common namespaces instead of all namespaces
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.apps_v1.read_namespaced_deployment(name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(f"Error searching for deployment {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "replicaset":
                if namespace:
                    resource_detail = self.apps_v1.read_namespaced_replica_set(name=resource_name, namespace=namespace)
                else:
                    # Search efficiently in common namespaces instead of all namespaces
                    common_namespaces = ["default", "kube-system", "kube-public"]
                    for ns in common_namespaces:
                        try:
                            resource_detail = self.apps_v1.read_namespaced_replica_set(name=resource_name, namespace=ns)
                            break
                        except Exception as ns_error:
                            if "404" not in str(ns_error) and "not found" not in str(ns_error).lower():
                                logging.debug(f"Error searching for replicaset {resource_name} in namespace {ns}: {ns_error}")
                            continue
            elif resource_type.lower() == "node":
                resource_detail = self.v1.read_node(name=resource_name)
            elif resource_type.lower() == "namespace":
                resource_detail = self.v1.read_namespace(name=resource_name)
            elif resource_type.lower() == "configmap":
                if namespace:
                    resource_detail = self.v1.read_namespaced_config_map(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "secret":
                if namespace:
                    resource_detail = self.v1.read_namespaced_secret(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "ingress":
                if namespace:
                    resource_detail = self.networking_v1.read_namespaced_ingress(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "persistentvolume":
                resource_detail = self.v1.read_persistent_volume(name=resource_name)
            elif resource_type.lower() == "persistentvolumeclaim":
                if namespace:
                    resource_detail = self.v1.read_namespaced_persistent_volume_claim(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "replicationcontroller":
                if namespace:
                    resource_detail = self.v1.read_namespaced_replication_controller(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "limitrange":
                if namespace:
                    resource_detail = self.v1.read_namespaced_limit_range(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "resourcequota":
                if namespace:
                    resource_detail = self.v1.read_namespaced_resource_quota(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "serviceaccount":
                if namespace:
                    resource_detail = self.v1.read_namespaced_service_account(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "endpoint":
                if namespace:
                    resource_detail = self.v1.read_namespaced_endpoints(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "lease":
                if namespace:
                    resource_detail = self.coordination_v1.read_namespaced_lease(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "horizontalpodautoscaler":
                if namespace:
                    resource_detail = self.autoscaling_v2.read_namespaced_horizontal_pod_autoscaler(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "poddisruptionbudget":
                if namespace:
                    resource_detail = self.policy_v1.read_namespaced_pod_disruption_budget(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "priorityclass":
                resource_detail = self.scheduling_v1.read_priority_class(name=resource_name)
            elif resource_type.lower() == "runtimeclass":
                resource_detail = self.node_v1.read_runtime_class(name=resource_name)
            elif resource_type.lower() == "mutatingwebhookconfiguration":
                resource_detail = self.admissionregistration_v1.read_mutating_webhook_configuration(name=resource_name)
            elif resource_type.lower() == "validatingwebhookconfiguration":
                resource_detail = self.admissionregistration_v1.read_validating_webhook_configuration(name=resource_name)
            elif resource_type.lower() == "role":
                if namespace:
                    resource_detail = self.rbac_v1.read_namespaced_role(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "clusterrole":
                resource_detail = self.rbac_v1.read_cluster_role(name=resource_name)
            elif resource_type.lower() == "rolebinding":
                if namespace:
                    resource_detail = self.rbac_v1.read_namespaced_role_binding(name=resource_name, namespace=namespace)
            elif resource_type.lower() == "clusterrolebinding":
                resource_detail = self.rbac_v1.read_cluster_role_binding(name=resource_name)
            elif resource_type.lower() == "customresourcedefinition":
                resource_detail = self.apiextensions_v1.read_custom_resource_definition(name=resource_name)
            
            if resource_detail:
                # Convert to dictionary format for compatibility
                detail_dict = self.v1.api_client.sanitize_for_serialization(resource_detail)
                # Emit signal with the resource detail
                self.resource_detail_loaded.emit(detail_dict)
                return detail_dict
            else:
                logging.debug(f"Resource {resource_type}/{resource_name} not found - may not exist or be accessible")
                return None
                
        except Exception as e:
            # Handle API exceptions more gracefully
            error_str = str(e)
            if "404" in error_str or "not found" in error_str.lower():
                logging.debug(f"Resource {resource_type}/{resource_name} not found in cluster")
                return None
            elif "403" in error_str or "forbidden" in error_str.lower():
                logging.debug(f"Access denied to resource {resource_type}/{resource_name}")
                return None
            else:
                logging.error(f"Error getting resource detail for {resource_type}/{resource_name}: {e}")
                self.error_occurred.emit(f"Failed to get resource detail: {str(e)}")
                return None
    
    def _get_nodes(self):
        """Legacy compatibility method for getting nodes"""
        import time
        from Utils import get_timestamp_with_ms
        start_time = time.time()
        logging.info(f"🚀 [API FETCH] {get_timestamp_with_ms()} - Kubernetes Client: Starting to fetch nodes from API")
        try:
            api_call_start = time.time()
            logging.debug(f"📡 [API CALL] {get_timestamp_with_ms()} - Kubernetes Client: Calling v1.list_node() API")
            nodes = self.v1.list_node().items
            api_call_time = (time.time() - api_call_start) * 1000
            
            logging.info(f"✅ [API SUCCESS] {get_timestamp_with_ms()} - Kubernetes Client: Successfully fetched {len(nodes)} nodes from API in {api_call_time:.1f}ms")
            
            # Log detailed node data
            for i, node in enumerate(nodes[:5]):  # Log first 5 nodes in detail
                node_name = node.metadata.name if hasattr(node.metadata, 'name') else f'unknown-{i}'
                node_status = 'Unknown'
                if hasattr(node, 'status') and node.status and hasattr(node.status, 'conditions'):
                    for condition in node.status.conditions:
                        if condition.type == 'Ready':
                            node_status = 'Ready' if condition.status == 'True' else 'NotReady'
                            break
                
                logging.debug(f"📊 [NODE DATA] {get_timestamp_with_ms()} - Node {i+1}: name='{node_name}', status='{node_status}', has_capacity={hasattr(node.status, 'capacity') if hasattr(node, 'status') and node.status else False}")
            
            if len(nodes) > 5:
                logging.debug(f"📊 [NODE DATA] {get_timestamp_with_ms()} - ... and {len(nodes) - 5} more nodes")
                
            total_time = (time.time() - start_time) * 1000
            logging.info(f"⏱️  [API COMPLETE] {get_timestamp_with_ms()} - Total API fetch time: {total_time:.1f}ms")
            return nodes
        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            logging.error(f'❌ [API ERROR] {get_timestamp_with_ms()} - Kubernetes Client: Failed to get nodes from API after {error_time:.1f}ms: {e}')
            return []
    
    def _get_namespaces(self):
        """Legacy compatibility method for getting namespaces"""
        try:
            return self.v1.list_namespace().items
        except Exception as e:
            logging.error(f'Failed to get namespaces: {e}')
            return []
    
    def _get_pods(self, namespace=None):
        """Legacy compatibility method for getting pods with pagination"""
        try:
            if namespace and namespace != "all":
                return self.v1.list_namespaced_pod(namespace=namespace, limit=100).items
            else:
                # Get pods from common namespaces only for performance
                all_pods = []
                common_namespaces = ["default", "kube-system", "kube-public"]
                for ns in common_namespaces:
                    try:
                        pods = self.v1.list_namespaced_pod(namespace=ns, limit=50).items
                        all_pods.extend(pods)
                    except Exception as e:
                        logging.debug(f"Could not get pods from namespace {ns}: {e}")
                return all_pods
        except Exception as e:
            logging.error(f'Failed to get pods: {e}')
            return []
    
    def _get_services(self, namespace=None):
        """Legacy compatibility method for getting services with pagination"""
        try:
            if namespace and namespace != "all":
                return self.v1.list_namespaced_service(namespace=namespace, limit=100).items
            else:
                # Get services from common namespaces only for performance
                all_services = []
                common_namespaces = ["default", "kube-system", "kube-public"]
                for ns in common_namespaces:
                    try:
                        services = self.v1.list_namespaced_service(namespace=ns, limit=50).items
                        all_services.extend(services)
                    except Exception as e:
                        logging.debug(f"Could not get services from namespace {ns}: {e}")
                return all_services
        except Exception as e:
            logging.error(f'Failed to get services: {e}')
            return []
    
    def _get_deployments(self, namespace=None):
        """Legacy compatibility method for getting deployments with pagination"""
        try:
            if namespace and namespace != "all":
                return self.apps_v1.list_namespaced_deployment(namespace=namespace, limit=100).items
            else:
                # Get deployments from common namespaces only for performance
                all_deployments = []
                common_namespaces = ["default", "kube-system", "kube-public"]
                for ns in common_namespaces:
                    try:
                        deployments = self.apps_v1.list_namespaced_deployment(namespace=ns, limit=50).items
                        all_deployments.extend(deployments)
                    except Exception as e:
                        logging.debug(f"Could not get deployments from namespace {ns}: {e}")
                return all_deployments
        except Exception as e:
            logging.error(f'Failed to get deployments: {e}')
            return []
    
    def _get_events(self, namespace=None):
        """Legacy compatibility method for getting events with pagination"""
        try:
            if namespace and namespace != "all":
                return self.v1.list_namespaced_event(namespace=namespace, limit=100).items
            else:
                # Get events from common namespaces only for performance
                all_events = []
                common_namespaces = ["default", "kube-system", "kube-public"]
                for ns in common_namespaces:
                    try:
                        events = self.v1.list_namespaced_event(namespace=ns, limit=50).items
                        all_events.extend(events)
                    except Exception as e:
                        logging.debug(f"Could not get events from namespace {ns}: {e}")
                return all_events
        except Exception as e:
            logging.error(f'Failed to get events: {e}')
            return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics - backward compatibility"""
        return self.service.get_cache_stats()
    
    def get_pods_for_node_async(self, node_name: str):
        """Get all pods running on a specific node asynchronously"""
        logging.info(f"Getting pods for node {node_name}")
        
        from Utils.enhanced_worker import EnhancedBaseWorker
        
        class NodePodsWorker(EnhancedBaseWorker):
            def __init__(self, client_instance, node_name):
                super().__init__(f"node_pods_{node_name}")
                self.client_instance = client_instance
                self.node_name = node_name
            
            def execute(self):
                try:
                    # Get all pods for the specific node using field selector
                    all_pods = self.client_instance.v1.list_pod_for_all_namespaces(
                        field_selector=f"spec.nodeName={self.node_name}"
                    )
                    
                    node_pods = []
                    for pod in all_pods.items:
                        pod_data = {
                            'name': pod.metadata.name,
                            'namespace': pod.metadata.namespace,
                            'status': pod.status.phase if pod.status and pod.status.phase else 'Unknown',
                            'cpu_usage': "N/A",
                            'memory_usage': "N/A"
                        }
                        node_pods.append(pod_data)
                    
                    return node_pods
                    
                except Exception as e:
                    logging.error(f"Failed to get pods for node {self.node_name}: {str(e)}")
                    raise Exception(f"Failed to get pods for node {self.node_name}: {str(e)}")
        
        worker = NodePodsWorker(self, node_name)
        
        # Connect signals with proper error handling
        def handle_success(result):
            try:
                self.pods_data_loaded.emit(result)
            except Exception as e:
                logging.error(f"Error emitting node pods result: {str(e)}")
                self.api_error.emit(f"Failed to emit node pods: {str(e)}")
        
        def handle_error(error):
            try:
                self.api_error.emit(f"Failed to get pods for node: {str(error)}")
            except Exception as e:
                logging.error(f"Error emitting node pods error: {str(e)}")
        
        worker.signals.finished.connect(handle_success)
        worker.signals.error.connect(handle_error)
        
        # Submit to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"node_pods_{node_name}", worker)

    def _calculate_age(self, creation_timestamp):
        """Calculate age from creation timestamp"""
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            created = creation_timestamp.replace(tzinfo=timezone.utc)
            delta = now - created

            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"

    def _get_deployment_rollout_history_sync(self, deployment_name: str, namespace: str = "default"):
        """Get deployment rollout history synchronously with optimized async patterns"""
        try:
            logging.debug(f"Fetching deployment {deployment_name} from namespace {namespace}")
            
            # Get deployment with timeout protection
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, 
                namespace=namespace,
                _request_timeout=10.0  # 10 second timeout
            )
            
            # Build more robust label selector
            deployment_labels = deployment.metadata.labels or {}
            app_label = deployment_labels.get('app', deployment_name)
            
            # Try multiple label selectors for better compatibility
            selectors = [
                f"app={app_label}",
                f"app.kubernetes.io/name={deployment_name}",
                f"app.kubernetes.io/instance={deployment_name}"
            ]
            
            all_replica_sets = []
            for selector in selectors:
                try:
                    logging.debug(f"Trying label selector: {selector}")
                    replica_sets = self.apps_v1.list_namespaced_replica_set(
                        namespace=namespace,
                        label_selector=selector,
                        _request_timeout=10.0  # 10 second timeout
                    )
                    all_replica_sets.extend(replica_sets.items)
                except Exception as e:
                    logging.debug(f"Label selector {selector} failed: {str(e)}")
                    continue
            
            # Remove duplicates by name
            unique_rs = {rs.metadata.name: rs for rs in all_replica_sets}
            
            history = []
            for rs_name, rs in unique_rs.items():
                # Verify ownership more thoroughly
                owner_refs = rs.metadata.owner_references or []
                is_owned_by_deployment = any(
                    ref.kind == "Deployment" and ref.name == deployment_name 
                    for ref in owner_refs
                )
                
                if is_owned_by_deployment:
                    # Get revision and other metadata
                    annotations = rs.metadata.annotations or {}
                    revision_str = annotations.get("deployment.kubernetes.io/revision", "1")
                    
                    try:
                        revision = int(revision_str)
                    except (ValueError, TypeError):
                        revision = 1
                    
                    # Get creation timestamp with safe handling
                    creation_time = rs.metadata.creation_timestamp
                    
                    # Determine if this is the current revision
                    current_replicas = rs.spec.replicas or 0
                    ready_replicas = (rs.status.ready_replicas or 0) if rs.status else 0
                    
                    history_item = {
                        "revision": revision,
                        "name": rs.metadata.name,
                        "creation_time": creation_time.isoformat() if creation_time else "",
                        "replicas": current_replicas,
                        "ready_replicas": ready_replicas,
                        "current": current_replicas > 0 and ready_replicas > 0,
                        "change_cause": annotations.get("kubernetes.io/change-cause", "No change cause recorded"),
                        "template_hash": annotations.get("pod-template-hash", ""),
                        "status": "Active" if current_replicas > 0 else "Inactive"
                    }
                    history.append(history_item)
            
            # Sort by revision number (descending)
            history.sort(key=lambda x: x["revision"], reverse=True)
            
            # Mark the most recent active revision as current
            if history:
                active_revisions = [h for h in history if h["current"]]
                if active_revisions:
                    # Reset all current flags
                    for h in history:
                        h["current"] = False
                    # Mark the highest revision that's active
                    active_revisions[0]["current"] = True
            
            logging.info(f"Successfully found {len(history)} revisions for deployment {deployment_name}")
            return history
            
        except Exception as e:
            error_msg = f"Failed to get rollout history for deployment {deployment_name}: {str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg)
    
    def _rollback_deployment_sync(self, deployment_name: str, revision: int, namespace: str = "default"):
        """Rollback deployment to specific revision synchronously with enhanced async compatibility"""
        try:
            logging.info(f"Starting rollback of deployment {deployment_name} to revision {revision}")
            
            # Step 1: Get current deployment with timeout
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, 
                namespace=namespace,
                _request_timeout=10.0
            )
            
            original_template_hash = deployment.spec.template.metadata.labels.get("pod-template-hash", "")
            logging.debug(f"Current deployment template hash: {original_template_hash}")
            
            # Step 2: Find target ReplicaSet more robustly
            deployment_labels = deployment.metadata.labels or {}
            app_label = deployment_labels.get('app', deployment_name)
            
            # Try multiple label selectors
            selectors = [
                f"app={app_label}",
                f"app.kubernetes.io/name={deployment_name}",
                f"app.kubernetes.io/instance={deployment_name}"
            ]
            
            target_rs = None
            for selector in selectors:
                try:
                    replica_sets = self.apps_v1.list_namespaced_replica_set(
                        namespace=namespace,
                        label_selector=selector,
                        _request_timeout=10.0
                    )
                    
                    for rs in replica_sets.items:
                        # Verify ownership
                        owner_refs = rs.metadata.owner_references or []
                        is_owned = any(
                            ref.kind == "Deployment" and ref.name == deployment_name 
                            for ref in owner_refs
                        )
                        
                        if is_owned:
                            annotations = rs.metadata.annotations or {}
                            rs_revision_str = annotations.get("deployment.kubernetes.io/revision", "1")
                            try:
                                rs_revision = int(rs_revision_str)
                                if rs_revision == revision:
                                    target_rs = rs
                                    break
                            except (ValueError, TypeError):
                                continue
                    
                    if target_rs:
                        break
                        
                except Exception as e:
                    logging.debug(f"Selector {selector} failed during rollback: {str(e)}")
                    continue
            
            if not target_rs:
                raise Exception(f"Revision {revision} not found for deployment {deployment_name}. Available revisions might be limited.")
            
            target_template_hash = target_rs.spec.template.metadata.labels.get("pod-template-hash", "")
            logging.info(f"Found target ReplicaSet {target_rs.metadata.name} with template hash: {target_template_hash}")
            
            # Step 3: Prepare rollback patch
            # Clone the deployment spec to avoid mutations
            import copy
            rollback_deployment = copy.deepcopy(deployment)
            
            # Update the deployment template with target ReplicaSet template
            rollback_deployment.spec.template = target_rs.spec.template
            
            # Update annotations
            if not rollback_deployment.metadata.annotations:
                rollback_deployment.metadata.annotations = {}
            
            # Add rollback metadata
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            rollback_deployment.metadata.annotations.update({
                "kubernetes.io/change-cause": f"Rolled back to revision {revision} at {timestamp}",
                "deployment.kubernetes.io/rollback-revision": str(revision),
                "orchetrix.io/rollback-timestamp": timestamp
            })
            
            # Step 4: Perform the rollback with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logging.debug(f"Rollback attempt {attempt + 1}/{max_retries}")
                    
                    result = self.apps_v1.patch_namespaced_deployment(
                        name=deployment_name,
                        namespace=namespace,
                        body=rollback_deployment,
                        _request_timeout=15.0
                    )
                    
                    logging.info(f"Rollback patch applied successfully on attempt {attempt + 1}")
                    break
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logging.warning(f"Rollback attempt {attempt + 1} failed: {str(e)}, retrying...")
                    import time
                    time.sleep(1)  # Brief delay before retry
            
            # Step 5: Verify rollback success
            success_msg = f"Successfully rolled back deployment {deployment_name} to revision {revision}"
            
            return {
                "success": True,
                "message": success_msg,
                "deployment": deployment_name,
                "revision": revision,
                "namespace": namespace,
                "original_template_hash": original_template_hash,
                "target_template_hash": target_template_hash,
                "target_replicaset": target_rs.metadata.name,
                "timestamp": timestamp
            }
            
        except Exception as e:
            error_msg = f"Failed to rollback deployment {deployment_name} to revision {revision}: {str(e)}"
            logging.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "deployment": deployment_name,
                "revision": revision,
                "namespace": namespace,
                "error_type": type(e).__name__
            }

    def cleanup(self):
        """Cleanup resources - backward compatibility"""
        self._shutting_down = True
        self.service.cleanup()
        logging.info("KubernetesClient cleanup completed")
    
    def __del__(self):
        """Destructor - backward compatibility"""
        try:
            if hasattr(self, '_shutting_down') and not self._shutting_down:
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesClient destructor: {e}")


# Singleton management - backward compatibility
_instance = None

def get_kubernetes_client():
    """Get or create Kubernetes client singleton - backward compatibility"""
    global _instance
    if _instance is None:
        _instance = KubernetesClient()
    return _instance

def reset_kubernetes_client():
    """Reset the singleton instance - backward compatibility"""
    global _instance
    if _instance:
        _instance.cleanup()
    _instance = None


class KubernetesPodSSH(QObject):
    """
    SSH session manager for Kubernetes pods using kubectl exec
    """
    
    # Signals for SSH session management
    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    session_status = pyqtSignal(str)
    session_closed = pyqtSignal()
    
    def __init__(self, pod_name: str, namespace: str):
        super().__init__()
        self.pod_name = pod_name
        self.namespace = namespace
        self.process = None
        self.is_connected = False
        
    def connect_to_pod(self) -> bool:
        """
        Connect to pod using kubectl exec
        """
        try:
            from PyQt6.QtCore import QProcess
            
            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self._handle_stdout)
            self.process.readyReadStandardError.connect(self._handle_stderr)
            self.process.finished.connect(self._handle_finished)
            self.process.errorOccurred.connect(self._handle_error)
            
            # kubectl exec command to start interactive shell
            cmd = "kubectl"
            args = ["exec", "-it", self.pod_name, "-n", self.namespace, "--", "/bin/bash"]
            
            self.process.start(cmd, args)
            
            if self.process.waitForStarted(3000):
                self.is_connected = True
                self.session_status.emit("connected")
                return True
            else:
                self.error_occurred.emit("Failed to start kubectl process")
                return False
                
        except Exception as e:
            logging.error(f"Error connecting to pod {self.pod_name}: {e}")
            self.error_occurred.emit(f"Connection error: {str(e)}")
            return False
    
    def send_command(self, command: str):
        """Send command to the SSH session"""
        if self.process and self.is_connected:
            try:
                self.process.write(command.encode('utf-8'))
                return True
            except Exception as e:
                self.error_occurred.emit(f"Failed to send command: {str(e)}")
                return False
        return False
    
    def disconnect(self):
        """Disconnect from the SSH session"""
        if self.process:
            self.process.terminate()
            self.is_connected = False
            self.session_status.emit("disconnected")
    
    def cleanup_ssh_session(self):
        """Clean up SSH session resources"""
        self.disconnect()
    
    def _handle_stdout(self):
        """Handle standard output from kubectl process"""
        if self.process:
            data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            if data:
                self.data_received.emit(data)
    
    def _handle_stderr(self):
        """Handle standard error from kubectl process"""
        if self.process:
            data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
            if data:
                self.error_occurred.emit(data)
    
    def _handle_finished(self, exit_code, exit_status):
        """Handle process finished"""
        self.is_connected = False
        self.session_status.emit("finished")
        self.session_closed.emit()
        logging.info(f"SSH session to {self.pod_name} finished with exit code {exit_code}")
    
    def _handle_error(self, error):
        """Handle process error"""
        self.is_connected = False
        error_msg = f"Process error: {error}"
        self.error_occurred.emit(error_msg)
        logging.error(f"SSH process error for {self.pod_name}: {error_msg}")