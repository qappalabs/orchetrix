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
    error_occurred = pyqtSignal(str)

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
                    return body['message']
            
            # Handle standard exceptions
            return str(error)
            
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
            
            metadata = resource_data.get('metadata', {})
            if not isinstance(metadata, dict):
                return False, "metadata field must be a dictionary"
            
            if 'name' not in metadata:
                return False, "Missing required field: metadata.name"
            
            # Check for invalid field values
            name = metadata.get('name', '')
            if not isinstance(name, str) or not name.strip():
                return False, "metadata.name must be a non-empty string"
            
            # Validate Kubernetes DNS-1123 name format
            if not self._is_valid_kubernetes_name(name):
                return False, f"metadata.name '{name}' is not a valid Kubernetes name (must be lowercase alphanumeric with hyphens)"
            
            # Resource-specific validation
            kind = resource_data.get('kind', '').lower()
            spec = resource_data.get('spec', {})
            
            if kind in ['deployment', 'pod', 'daemonset', 'statefulset', 'replicaset']:
                # Validate container ports for duplicate names
                validation_result = self._validate_container_ports(spec)
                if not validation_result[0]:
                    return validation_result
                
                # Validate container names for duplicates
                validation_result = self._validate_container_names(spec)
                if not validation_result[0]:
                    return validation_result
            
            return True, "Schema validation passed"
            
        except Exception as e:
            return False, f"Schema validation error: {str(e)}"
    
    def _is_valid_kubernetes_name(self, name: str) -> bool:
        """Validate Kubernetes DNS-1123 name format"""
        if len(name) > 253:
            return False
        if not name.replace('-', '').replace('.', '').isalnum():
            return False
        if name.startswith('-') or name.endswith('-'):
            return False
        return name.islower()
    
    def _validate_container_ports(self, spec: dict) -> tuple[bool, str]:
        """Validate container ports for duplicates"""
        try:
            containers = []
            
            # Get containers from different locations based on resource type
            if 'template' in spec and 'spec' in spec['template']:
                # Deployment, StatefulSet, DaemonSet
                template_spec = spec['template']['spec']
                containers = template_spec.get('containers', [])
                containers.extend(template_spec.get('initContainers', []))
            elif 'containers' in spec:
                # Pod
                containers = spec.get('containers', [])
                containers.extend(spec.get('initContainers', []))
            
            for container in containers:
                if not isinstance(container, dict):
                    continue
                    
                ports = container.get('ports', [])
                if not isinstance(ports, list):
                    continue
                    
                # Check for duplicate port names within this container
                port_names = []
                port_numbers = []
                
                for port in ports:
                    if not isinstance(port, dict):
                        continue
                        
                    # Check for duplicate port names
                    if 'name' in port:
                        port_name = port['name']
                        if port_name in port_names:
                            return False, f"Duplicate port name '{port_name}' in container '{container.get('name', 'unknown')}'"
                        port_names.append(port_name)
                    
                    # Check for duplicate port numbers with same protocol
                    if 'containerPort' in port:
                        port_number = port['containerPort']
                        protocol = port.get('protocol', 'TCP')
                        port_key = f"{port_number}/{protocol}"
                        if port_key in port_numbers:
                            return False, f"Duplicate port {port_number}/{protocol} in container '{container.get('name', 'unknown')}'"
                        port_numbers.append(port_key)
            
            return True, "Container ports validation passed"
            
        except Exception as e:
            return False, f"Container ports validation error: {str(e)}"
    
    def _validate_container_names(self, spec: dict) -> tuple[bool, str]:
        """Validate container names for duplicates"""
        try:
            all_container_names = []
            
            # Get containers from different locations
            if 'template' in spec and 'spec' in spec['template']:
                template_spec = spec['template']['spec']
                containers = template_spec.get('containers', [])
                init_containers = template_spec.get('initContainers', [])
            elif 'containers' in spec:
                containers = spec.get('containers', [])
                init_containers = spec.get('initContainers', [])
            else:
                return True, "No containers to validate"
            
            # Check regular containers
            for container in containers:
                if isinstance(container, dict) and 'name' in container:
                    name = container['name']
                    if name in all_container_names:
                        return False, f"Duplicate container name '{name}'"
                    all_container_names.append(name)
            
            # Check init containers
            for container in init_containers:
                if isinstance(container, dict) and 'name' in container:
                    name = container['name']
                    if name in all_container_names:
                        return False, f"Duplicate container name '{name}' (conflicts with regular or init container)"
                    all_container_names.append(name)
            
            return True, "Container names validation passed"
            
        except Exception as e:
            return False, f"Container names validation error: {str(e)}"

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
        try:
            return self.v1.list_node().items
        except Exception as e:
            logging.error(f'Failed to get nodes: {e}')
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