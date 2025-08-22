"""
High-Performance Unified Resource Loader
Consolidates 3 duplicate resource loaders into one optimized system.
Designed for speed, efficiency, and smooth user experience.
"""

import asyncio
import logging
import time
import threading
# Use unified thread manager instead of separate ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Set
from functools import lru_cache, wraps
from collections import defaultdict

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from kubernetes.client.rest import ApiException
from Utils.kubernetes_client import get_kubernetes_client
from Utils.error_handler import get_error_handler, safe_execute, log_performance
from Utils.unified_cache_system import get_unified_cache
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager


@dataclass
class ResourceConfig:
    """Configuration for resource loading operations"""
    resource_type: str
    api_method: str
    namespace: Optional[str] = None
    batch_size: int = 30  # Further reduced for stability
    timeout_seconds: int = 30  # Longer timeout for Docker Desktop Kubernetes
    cache_ttl: int = 600  # 10 minutes for much better cache performance
    enable_streaming: bool = False  # Disabled streaming to reduce complexity
    enable_pagination: bool = False  # Disabled pagination to reduce load
    max_concurrent_requests: int = 2  # Further reduced to prevent API overload


@dataclass
class LoadResult:
    """Result of a resource loading operation"""
    success: bool
    resource_type: str
    items: List[Any] = field(default_factory=list)
    total_count: int = 0
    load_time_ms: float = 0
    from_cache: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SearchResourceLoadWorker(EnhancedBaseWorker):
    """Worker specifically for search operations across all resources"""
    
    def __init__(self, config: ResourceConfig, loader_instance, search_query: str):
        super().__init__(f"search_resource_load_{config.resource_type}")
        self.config = config
        self.loader = loader_instance
        self.search_query = search_query.lower() if search_query else ""
        self._start_time = time.time()
    
    def execute(self) -> LoadResult:
        """Execute search across all resources with filtering"""
        start_time = time.time()
        
        try:
            # Check cache first (but search results are cached separately)
            cached_result = self._try_search_cache_first()
            if cached_result:
                return cached_result
            
            # Load from API with comprehensive search
            items = self._load_and_filter_from_api()
            
            if self.is_cancelled():
                return LoadResult(
                    success=False, 
                    resource_type=self.config.resource_type,
                    error_message="Search operation cancelled"
                )
            
            # Process search results using the parent loader's processing logic
            processed_items = self._process_search_items(items)
            self._cache_search_results(processed_items)
            
            load_time = (time.time() - start_time) * 1000
            
            return LoadResult(
                success=True,
                resource_type=self.config.resource_type,
                items=processed_items,
                total_count=len(processed_items),
                load_time_ms=load_time,
                from_cache=False,
                metadata={'search_query': self.search_query}
            )
            
        except ApiException as api_error:
            # Handle Kubernetes API exceptions during search
            if api_error.status == 404:
                logging.info(f"Resource type {self.config.resource_type} not available for search in this cluster")
                return LoadResult(
                    success=True,
                    resource_type=self.config.resource_type,
                    items=[],
                    total_count=0,
                    load_time_ms=(time.time() - start_time) * 1000,
                    from_cache=False,
                    metadata={'search_query': self.search_query}
                )
            else:
                error_message = f"Search API Error {api_error.status}: {api_error.reason}"
                return LoadResult(
                    success=False,
                    resource_type=self.config.resource_type,
                    error_message=f"Search failed: {error_message}",
                    load_time_ms=(time.time() - start_time) * 1000
                )
        except Exception as e:
            error_handler = get_error_handler()
            error_message = error_handler.format_connection_error(str(e), self.config.resource_type)
            
            return LoadResult(
                success=False,
                resource_type=self.config.resource_type,
                error_message=f"Search failed: {error_message}",
                load_time_ms=(time.time() - start_time) * 1000
            )
    
    def _try_search_cache_first(self) -> Optional[LoadResult]:
        """Try to get search results from cache"""
        try:
            cache_service = get_unified_cache()
            # Use search-specific cache key
            cache_key = f"{self._generate_cache_key()}_search_{hash(self.search_query)}"
            
            cached_items = cache_service.get_cached_resources(
                self.config.resource_type, 
                cache_key,
                max_age_seconds=self.config.cache_ttl
            )
            
            if cached_items:
                logging.debug(f"Search cache hit for {self.config.resource_type}: {len(cached_items)} items")
                return LoadResult(
                    success=True,
                    resource_type=self.config.resource_type,
                    items=cached_items,
                    total_count=len(cached_items),
                    load_time_ms=0,
                    from_cache=True,
                    metadata={'search_query': self.search_query}
                )
                
        except Exception as e:
            logging.debug(f"Search cache lookup failed for {self.config.resource_type}: {e}")
        
        return None
    
    def _load_and_filter_from_api(self) -> List[Any]:
        """Load from API and filter by search query"""
        # Use the same loading mechanism as the parent class
        if not self.config.namespace:
            # Search all namespaces
            all_items = self._load_from_multiple_namespaces_with_search()
        else:
            # Search specific namespace
            all_items = self._load_from_single_namespace_with_search()
        
        # Filter results by search query
        if self.search_query:
            filtered_items = []
            for item in all_items:
                if self._item_matches_search(item):
                    filtered_items.append(item)
            return filtered_items
        
        return all_items
    
    def _load_from_single_namespace_with_search(self) -> List[Any]:
        """Load from single namespace for search"""
        kube_client = get_kubernetes_client()
        api_client = self._get_api_client(kube_client)
        
        # Get the correct namespaced API method
        namespaced_method_name = self.loader._get_namespaced_api_method(self.config.resource_type)
        api_method = getattr(api_client, namespaced_method_name)
        
        kwargs = {
            'namespace': self.config.namespace,
            'timeout_seconds': self.config.timeout_seconds,
            '_request_timeout': self.config.timeout_seconds + 5,
            'limit': 200  # Larger limit for search
        }
        
        response = api_method(**kwargs)
        return response.items if hasattr(response, 'items') else []
    
    def _load_from_multiple_namespaces_with_search(self) -> List[Any]:
        """Load from multiple namespaces for comprehensive search"""
        all_items = []
        
        try:
            # Get namespaces first
            namespaces_response = get_kubernetes_client().v1.list_namespace(limit=100)
            namespace_names = [ns.metadata.name for ns in namespaces_response.items]
            
            # Search in all namespaces (not limited to 20 for search)
            kube_client = get_kubernetes_client()
            api_client = self._get_api_client(kube_client)
            namespaced_method_name = self.loader._get_namespaced_api_method(self.config.resource_type)
            api_method = getattr(api_client, namespaced_method_name)
            
            for namespace in namespace_names:
                if self.is_cancelled():
                    break
                    
                try:
                    kwargs = {
                        'namespace': namespace,
                        'timeout_seconds': 30,
                        '_request_timeout': 35,
                        'limit': 100  # Reasonable limit per namespace
                    }
                    
                    response = api_method(**kwargs)
                    if hasattr(response, 'items'):
                        all_items.extend(response.items)
                        
                except ApiException as api_error:
                    # Handle API exceptions gracefully during search
                    if api_error.status == 404:
                        logging.debug(f"Resource {self.config.resource_type} not found in namespace {namespace} during search")
                    elif api_error.status == 403:
                        logging.debug(f"Access denied for {self.config.resource_type} in namespace {namespace} during search")
                    continue
                except Exception as e:
                    # Continue with other namespaces silently
                    logging.debug(f"Search error in namespace {namespace}: {e}")
                    continue
            
            logging.info(f"Search loaded {len(all_items)} {self.config.resource_type} from {len(namespace_names)} namespaces")
            return all_items
            
        except Exception as e:
            logging.warning(f"Error in multi-namespace search: {e}")
            # Fallback to default namespace
            return self._load_from_single_namespace_with_search()
    
    def _item_matches_search(self, item: Any) -> bool:
        """Check if item matches the search query"""
        if not self.search_query:
            return True
        
        try:
            # Search in name
            if hasattr(item, 'metadata') and item.metadata:
                name = getattr(item.metadata, 'name', '').lower()
                if self.search_query in name:
                    return True
                
                # Search in namespace
                namespace = getattr(item.metadata, 'namespace', '').lower()
                if self.search_query in namespace:
                    return True
                
                # Search in labels
                labels = getattr(item.metadata, 'labels', {}) or {}
                for key, value in labels.items():
                    if (self.search_query in key.lower() or 
                        self.search_query in str(value).lower()):
                        return True
            
            # Search in spec fields (for certain resources)
            if hasattr(item, 'spec') and item.spec:
                # Convert spec to string and search
                spec_str = str(item.spec).lower()
                if self.search_query in spec_str:
                    return True
            
        except Exception:
            pass
        
        return False
    
    def _cache_search_results(self, processed_items: List[Dict[str, Any]]):
        """Cache search results separately from regular cache"""
        try:
            cache_service = get_unified_cache()
            cache_key = f"{self._generate_cache_key()}_search_{hash(self.search_query)}"
            
            cache_service.cache_resources(
                self.config.resource_type,
                cache_key,
                processed_items,
                ttl_seconds=self.config.cache_ttl
            )
            
        except Exception as e:
            logging.debug(f"Failed to cache search results: {e}")
    
    def _process_search_items(self, items: List[Any]) -> List[Dict[str, Any]]:
        """Process search results using simplified processing for speed"""
        if not items:
            return []
        
        processed_items = []
        
        for item in items:
            if self.is_cancelled():
                break
            
            try:
                # Use basic processing for search results (faster)
                processed_item = self._process_single_search_item(item)
                if processed_item:
                    processed_items.append(processed_item)
            except Exception as e:
                logging.debug(f"Error processing search item: {e}")
                continue
        
        return processed_items
    
    def _process_single_search_item(self, item: Any) -> Optional[Dict[str, Any]]:
        """Process a single search result item with full data consistency"""
        try:
            # Extract common fields efficiently (same as regular processing)
            metadata = item.metadata
            name = metadata.name
            namespace = getattr(metadata, 'namespace', None)
            creation_timestamp = metadata.creation_timestamp
            
            # Use the same age calculation as regular processing for consistency
            age = self._format_age_fast(creation_timestamp)
            
            # Build complete resource data (matching regular processing structure)
            resource_data = {
                'name': name,
                'namespace': namespace,
                'age': age,
                'created': creation_timestamp,  # Keep as timestamp object for consistency
                'labels': metadata.labels or {},
                'annotations': metadata.annotations or {},
                'resource_type': self.config.resource_type,
                'uid': metadata.uid,
                'search_matched': True  # Mark as search result
            }
            
            # Add complete resource-specific fields using the same method as regular processing
            self._add_resource_specific_fields(resource_data, item)
            
            # Add raw_data for UI components that need detailed information
            # Serialize the raw Kubernetes object for components that need it
            try:
                kube_client = get_kubernetes_client()
                if hasattr(kube_client, 'v1') and hasattr(kube_client.v1, 'api_client'):
                    resource_data['raw_data'] = kube_client.v1.api_client.sanitize_for_serialization(item)
                else:
                    # Fallback: create a basic raw_data structure
                    resource_data['raw_data'] = {
                        'metadata': {
                            'name': name,
                            'namespace': namespace,
                            'labels': metadata.labels,
                            'annotations': metadata.annotations,
                            'creation_timestamp': str(creation_timestamp) if creation_timestamp else None
                        }
                    }
            except Exception as e:
                logging.debug(f"Error serializing raw data: {e}")
                resource_data['raw_data'] = {}
            
            return resource_data
            
        except Exception as e:
            logging.debug(f"Error processing single search item: {e}")
            return None
    
    def _generate_cache_key(self) -> str:
        """Generate cache key for search results"""
        namespace_key = self.config.namespace or "all_namespaces"
        return f"{self.config.resource_type}_{namespace_key}"
    
    def _get_api_client(self, kube_client):
        """Get the appropriate API client for the resource type"""
        api_mapping = {
            # Core v1 resources
            'pods': kube_client.v1,
            'nodes': kube_client.v1,
            'services': kube_client.v1,
            'serviceaccounts': kube_client.v1,
            'configmaps': kube_client.v1,
            'secrets': kube_client.v1,
            'namespaces': kube_client.v1,
            'events': kube_client.v1,
            'endpoints': kube_client.v1,
            'persistentvolumes': kube_client.v1,
            'persistentvolumeclaims': kube_client.v1,
            'replicationcontrollers': kube_client.v1,
            'resourcequotas': kube_client.v1,
            'limitranges': kube_client.v1,
            
            # Apps v1 resources
            'deployments': kube_client.apps_v1,
            'replicasets': kube_client.apps_v1,
            'daemonsets': kube_client.apps_v1,
            'statefulsets': kube_client.apps_v1,
            
            # Networking v1 resources  
            'ingresses': kube_client.networking_v1,
            'networkpolicies': kube_client.networking_v1,
            'ingressclasses': kube_client.networking_v1,
            
            # Storage v1 resources
            'storageclasses': kube_client.storage_v1,
            
            # Batch v1 resources
            'jobs': kube_client.batch_v1,
            'cronjobs': kube_client.batch_v1,
            
            # RBAC v1 resources
            'roles': kube_client.rbac_v1,
            'rolebindings': kube_client.rbac_v1,
            'clusterroles': kube_client.rbac_v1,
            'clusterrolebindings': kube_client.rbac_v1,
        }
        
        # For new API clients that might not be available in older instances,
        # use fallbacks to prevent application crashes
        try:
            if self.config.resource_type == 'horizontalpodautoscalers':
                return getattr(kube_client, 'autoscaling_v1', kube_client.v1)
            elif self.config.resource_type == 'poddisruptionbudgets':
                return getattr(kube_client, 'policy_v1', kube_client.v1)
            elif self.config.resource_type in ['validatingwebhookconfigurations', 'mutatingwebhookconfigurations']:
                return getattr(kube_client, 'admissionregistration_v1', kube_client.v1)
            elif self.config.resource_type == 'runtimeclasses':
                return getattr(kube_client, 'node_v1', kube_client.v1)
            elif self.config.resource_type == 'leases':
                return getattr(kube_client, 'coordination_v1', kube_client.v1)
            elif self.config.resource_type == 'priorityclasses':
                return getattr(kube_client, 'scheduling_v1', kube_client.v1)
            elif self.config.resource_type == 'customresourcedefinitions':
                return getattr(kube_client, 'apiextensions_v1', kube_client.v1)
        except AttributeError:
            pass
        
        return api_mapping.get(self.config.resource_type, kube_client.v1)
    
    def _format_age_fast(self, creation_timestamp) -> str:
        """Fast age calculation with caching (same as ResourceLoadWorker)"""
        if not creation_timestamp:
            return 'Unknown'
        
        try:
            from datetime import datetime, timezone
            if hasattr(creation_timestamp, 'timestamp'):
                created = datetime.fromtimestamp(creation_timestamp.timestamp(), tz=timezone.utc)
            else:
                created = creation_timestamp
            
            now = datetime.now(timezone.utc)
            age_delta = now - created
            
            days = age_delta.days
            hours = age_delta.seconds // 3600
            minutes = (age_delta.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
                
        except Exception:
            return 'Unknown'
    
    def _add_resource_specific_fields(self, processed_item: Dict[str, Any], item: Any):
        """Add resource-specific fields efficiently (same as ResourceLoadWorker)"""
        resource_type = self.config.resource_type
        
        if resource_type == 'pods':
            self._add_pod_fields(processed_item, item)
        elif resource_type == 'nodes':
            self._add_node_fields(processed_item, item)
        elif resource_type == 'services':
            self._add_service_fields(processed_item, item)
        elif resource_type == 'configmaps':
            self._add_configmap_fields(processed_item, item)
        elif resource_type == 'secrets':
            self._add_secret_fields(processed_item, item)
        elif resource_type == 'leases':
            self._add_lease_fields(processed_item, item)
        elif resource_type == 'priorityclasses':
            self._add_priorityclass_fields(processed_item, item)
        elif resource_type in ['deployments', 'replicasets', 'statefulsets', 'daemonsets']:
            self._add_workload_fields(processed_item, item)
    
    def _add_pod_fields(self, processed_item: Dict[str, Any], pod: Any):
        """Add pod-specific fields efficiently"""
        status = pod.status
        spec = pod.spec
        
        # Enhanced status determination with more detail
        pod_status = 'Unknown'
        if status:
            pod_status = status.phase or 'Unknown'
            
            # Check for more specific container states
            if status.container_statuses:
                for cs in status.container_statuses:
                    if cs.state:
                        if cs.state.waiting:
                            reason = cs.state.waiting.reason
                            if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                                pod_status = reason
                                break
                        elif cs.state.terminated:
                            if cs.state.terminated.exit_code != 0:
                                pod_status = "Error"
                                break
        
        processed_item.update({
            'status': pod_status,
            'ready': self._get_pod_ready_status(status),
            'restarts': self._get_pod_restart_count(status),
            'node_name': spec.node_name if spec else None,
            'host_ip': status.host_ip if status else None,
            'pod_ip': status.pod_ip if status else None,
            'containers': len(spec.containers) if spec and spec.containers else 0,
            'init_containers': len(spec.init_containers) if spec and spec.init_containers else 0,
        })
    
    def _add_node_fields(self, processed_item: Dict[str, Any], node: Any):
        """Add node-specific fields efficiently"""
        status = node.status
        
        # Get node status efficiently
        node_status = 'Unknown'
        if status and status.conditions:
            for condition in status.conditions:
                if condition.type == 'Ready':
                    node_status = 'Ready' if condition.status == 'True' else 'NotReady'
                    break
        
        # Get node roles efficiently
        roles = []
        if node.metadata.labels:
            for label_key in node.metadata.labels:
                if 'node-role.kubernetes.io/' in label_key:
                    role = label_key.replace('node-role.kubernetes.io/', '')
                    if role:
                        roles.append(role)
        
        # Get taints count
        taints_count = 0
        if node.spec and node.spec.taints:
            taints_count = len(node.spec.taints)
        
        processed_item.update({
            'status': node_status,
            'roles': roles if roles else ['<none>'],
            'version': status.node_info.kubelet_version if status and status.node_info else 'Unknown',
            'os': status.node_info.operating_system if status and status.node_info else 'Unknown',
            'kernel': status.node_info.kernel_version if status and status.node_info else 'Unknown',
            'taints': str(taints_count),
        })
        
        # Add capacity information
        if status and status.capacity:
            processed_item.update({
                'cpu_capacity': status.capacity.get('cpu', ''),
                'memory_capacity': status.capacity.get('memory', ''),
                'disk_capacity': status.capacity.get('ephemeral-storage', ''),
                'pods_capacity': status.capacity.get('pods', ''),
            })
    
    def _add_service_fields(self, processed_item: Dict[str, Any], service: Any):
        """Add service-specific fields efficiently"""
        try:
            spec = getattr(service, 'spec', None)
            
            # Basic service info with safe attribute access
            service_type = getattr(spec, 'type', 'ClusterIP') if spec else 'ClusterIP'
            cluster_ip = getattr(spec, 'cluster_ip', '<none>') if spec else '<none>'
            
            # Port information with robust attribute access
            ports = []
            if spec and hasattr(spec, 'ports') and spec.ports:
                for port in spec.ports:
                    try:
                        port_num = getattr(port, 'port', '')
                        protocol = getattr(port, 'protocol', 'TCP')
                        port_str = f"{port_num}/{protocol}"
                        ports.append(port_str)
                    except Exception as e:
                        logging.debug(f"Error processing port: {e}")
                        continue
            port_text = ", ".join(ports) if ports else "<none>"
            
            # Selector information with safe access
            selector = getattr(spec, 'selector', {}) if spec else {}
            selector_text = ", ".join([f"{k}={v}" for k, v in selector.items()]) if selector else "<none>"
            
            processed_item.update({
                'type': service_type,
                'cluster_ip': cluster_ip,
                'external_ip': '<none>',
                'ports': len(spec.ports) if spec and hasattr(spec, 'ports') and spec.ports else 0,
                'port_text': port_text,
                'selector': selector_text,
            })
            
        except Exception as e:
            logging.error(f"Error processing service fields: {e}")
            processed_item.update({
                'type': 'Unknown',
                'cluster_ip': '<error>',
                'external_ip': '<error>',
                'ports': 0,
                'port_text': '<error>',
                'selector': '<error>',
            })
    
    def _add_configmap_fields(self, processed_item: Dict[str, Any], configmap: Any):
        """Add configmap-specific fields efficiently"""
        data = configmap.data
        binary_data = configmap.binary_data
        
        # Get keys from both data and binaryData
        keys = []
        if data:
            keys.extend(data.keys())
        if binary_data:
            keys.extend(binary_data.keys())
        
        processed_item.update({
            'keys': ', '.join(keys) if keys else '<none>',
            'data_keys_count': len(keys),
        })
    
    def _add_secret_fields(self, processed_item: Dict[str, Any], secret: Any):
        """Add secret-specific fields efficiently"""
        data = secret.data
        
        # Get keys but don't display values for security
        keys = list(data.keys()) if data else []
        
        processed_item.update({
            'keys': ', '.join(keys) if keys else '<none>',
            'data_keys_count': len(keys),
            'type': secret.type if secret.type else 'Opaque',
        })
    
    def _add_lease_fields(self, processed_item: Dict[str, Any], lease: Any):
        """Add lease-specific fields efficiently"""
        spec = lease.spec
        
        holder_identity = '<none>'
        lease_duration_seconds = 0
        
        if spec:
            holder_identity = spec.holder_identity if spec.holder_identity else '<none>'
            lease_duration_seconds = spec.lease_duration_seconds if spec.lease_duration_seconds else 0
        
        processed_item.update({
            'holder': holder_identity,
            'lease_duration': f"{lease_duration_seconds}s",
        })
    
    def _add_priorityclass_fields(self, processed_item: Dict[str, Any], priority_class: Any):
        """Add priority class-specific fields efficiently"""
        value = priority_class.value if priority_class.value is not None else 0
        global_default = priority_class.global_default if priority_class.global_default is not None else False
        description = priority_class.description if priority_class.description else ""
        
        processed_item.update({
            'value': str(value),
            'global_default': str(global_default).lower(),
            'description': description,
        })
    
    def _add_workload_fields(self, processed_item: Dict[str, Any], workload: Any):
        """Add workload-specific fields efficiently"""
        spec = workload.spec
        status = workload.status
        
        # Get replicas info
        replicas = getattr(spec, 'replicas', 1) if spec else 1
        ready_replicas = getattr(status, 'ready_replicas', 0) if status else 0
        
        processed_item.update({
            'replicas': f"{ready_replicas}/{replicas}",
            'ready_replicas': ready_replicas,
            'total_replicas': replicas,
        })
    
    def _get_pod_ready_status(self, status) -> str:
        """Get pod ready status efficiently"""
        if not status or not status.container_statuses:
            return '0/0'
        
        ready_count = sum(1 for cs in status.container_statuses if cs.ready)
        total_count = len(status.container_statuses)
        
        return f"{ready_count}/{total_count}"
    
    def _get_pod_restart_count(self, status) -> int:
        """Get pod restart count efficiently"""
        if not status or not status.container_statuses:
            return 0
        
        return sum(cs.restart_count for cs in status.container_statuses if cs.restart_count)


class ResourceLoadWorker(EnhancedBaseWorker):
    """High-performance worker for loading Kubernetes resources"""
    
    # Shared constant for cluster-scoped resources to avoid duplication
    CLUSTER_SCOPED_RESOURCES = {
        'nodes', 'namespaces', 'persistentvolumes', 'storageclasses',
        'ingressclasses', 'clusterroles', 'clusterrolebindings',
        'customresourcedefinitions', 'priorityclasses', 'runtimeclasses',
        'validatingwebhookconfigurations', 'mutatingwebhookconfigurations'
    }
    
    def __init__(self, config: ResourceConfig, loader_instance):
        super().__init__(f"resource_load_{config.resource_type}")
        self.config = config
        self.loader = loader_instance
        self._start_time = time.time()
    
    def execute(self) -> LoadResult:
        """Execute resource loading with performance optimizations"""
        start_time = time.time()
        
        try:
            # Check cache first for speed
            cached_result = self._try_cache_first()
            if cached_result:
                return cached_result
            
            # Load from Kubernetes API with optimizations
            items = self._load_from_api()
            
            if self.is_cancelled():
                return LoadResult(
                    success=False, 
                    resource_type=self.config.resource_type,
                    error_message="Operation cancelled"
                )
            
            # Process and cache results
            processed_items = self._process_items(items)
            self._cache_results(processed_items)
            
            load_time = (time.time() - start_time) * 1000
            
            return LoadResult(
                success=True,
                resource_type=self.config.resource_type,
                items=processed_items,
                total_count=len(processed_items),
                load_time_ms=load_time,
                from_cache=False
            )
            
        except ApiException as api_error:
            # Handle Kubernetes API exceptions gracefully
            if api_error.status == 404:
                # Resource type not found - return empty result, not error
                logging.info(f"Resource type {self.config.resource_type} not available in this cluster")
                return LoadResult(
                    success=True,
                    resource_type=self.config.resource_type,
                    items=[],
                    total_count=0,
                    load_time_ms=(time.time() - start_time) * 1000,
                    from_cache=False
                )
            elif api_error.status == 403:
                # Forbidden - insufficient permissions
                logging.warning(f"Insufficient permissions to access {self.config.resource_type}")
                return LoadResult(
                    success=False,
                    resource_type=self.config.resource_type,
                    error_message=f"Access denied to {self.config.resource_type} - check cluster permissions",
                    load_time_ms=(time.time() - start_time) * 1000
                )
            else:
                error_message = f"API Error {api_error.status}: {api_error.reason}"
                logging.error(f"API error loading {self.config.resource_type}: {error_message}")
                return LoadResult(
                    success=False,
                    resource_type=self.config.resource_type,
                    error_message=error_message,
                    load_time_ms=(time.time() - start_time) * 1000
                )
        except Exception as e:
            error_handler = get_error_handler()
            error_message = str(e)
            
            # Handle specific timeout and connection errors gracefully
            if "timeout" in error_message.lower() or "read timed out" in error_message.lower():
                # For timeout-prone resources, try a fallback approach or return cached data
                fallback_result = self._handle_timeout_fallback()
                if fallback_result:
                    return fallback_result
                
                error_message = f"Connection timeout - {self.config.resource_type} may be slow to respond"
                logging.warning(f"Timeout loading {self.config.resource_type}: {error_message}")
            elif "connection" in error_message.lower():
                error_message = f"Connection error loading {self.config.resource_type}"
                logging.warning(f"Connection error loading {self.config.resource_type}: {error_message}")
            else:
                error_message = error_handler.format_connection_error(str(e), self.config.resource_type)
            
            return LoadResult(
                success=False,
                resource_type=self.config.resource_type,
                error_message=error_message,
                load_time_ms=(time.time() - start_time) * 1000
            )
    
    def _try_cache_first(self) -> Optional[LoadResult]:
        """Try to get results from cache first for speed"""
        try:
            cache_service = get_unified_cache()
            cache_key = self._generate_cache_key()
            
            cached_items = cache_service.get_cached_resources(
                self.config.resource_type, 
                cache_key,
                max_age_seconds=self.config.cache_ttl
            )
            
            if cached_items:
                logging.debug(f"Cache hit for {self.config.resource_type}: {len(cached_items)} items")
                return LoadResult(
                    success=True,
                    resource_type=self.config.resource_type,
                    items=cached_items,
                    total_count=len(cached_items),
                    load_time_ms=0,
                    from_cache=True
                )
                
        except Exception as e:
            logging.debug(f"Cache lookup failed for {self.config.resource_type}: {e}")
        
        return None
    
    def _load_from_api(self) -> List[Any]:
        """Load resources from Kubernetes API with performance optimizations"""
        kube_client = get_kubernetes_client()
        
        # Get the appropriate API client
        api_client = self._get_api_client(kube_client)
        
        # Build method parameters for optimal performance and fast failure
        kwargs = {
            'timeout_seconds': 30,  # Longer timeout for Docker Desktop
            '_request_timeout': 35  # Longer request timeout for slow clusters
        }
        
        # Handle cluster scoped vs namespaced resources
        is_cluster_scoped = self.config.resource_type in self.CLUSTER_SCOPED_RESOURCES
        
        # Handle "All Namespaces" case efficiently
        if not self.config.namespace and not is_cluster_scoped:
            # For "All Namespaces", use optimized multi-namespace approach
            return self._load_from_multiple_namespaces(api_client, kwargs)
        elif self.config.namespace and not is_cluster_scoped:
            # Specific namespace
            kwargs['namespace'] = self.config.namespace
        
        # Get the API method
        api_method = getattr(api_client, self.config.api_method)
        
        # Enable streaming for large datasets
        if self.config.enable_streaming:
            kwargs['watch'] = False  # We handle our own streaming
        
        # Optimize field selection for better performance
        if self.config.resource_type in ['pods', 'nodes', 'services']:
            # Only get essential fields to reduce network overhead
            kwargs['field_selector'] = self._get_field_selector()
        
        # Execute API call with timeout
        response = api_method(**kwargs)
        
        return response.items if hasattr(response, 'items') else []
    
    def _load_from_multiple_namespaces(self, api_client, base_kwargs) -> List[Any]:
        """Load resources from multiple namespaces efficiently for 'All Namespaces' option"""
        all_items = []
        
        try:
            # Get namespaces first (with caching)
            namespaces_response = get_kubernetes_client().v1.list_namespace(limit=100)
            namespace_names = [ns.metadata.name for ns in namespaces_response.items]
            
            # Prioritize important namespaces and limit total namespaces for performance
            important_namespaces = ["default", "kube-system", "kube-public"]
            other_namespaces = [ns for ns in namespace_names if ns not in important_namespaces]
            
            # Limit to first 20 namespaces to prevent excessive API calls
            selected_namespaces = important_namespaces + other_namespaces[:17]  # Total of 20
            
            # Get the correct namespaced API method for multi-namespace loading
            namespaced_method_name = self.loader._get_namespaced_api_method(self.config.resource_type)
            api_method = getattr(api_client, namespaced_method_name)
            
            for namespace in selected_namespaces:
                if self.is_cancelled():
                    break
                    
                try:
                    # Create kwargs for this namespace
                    ns_kwargs = base_kwargs.copy()
                    ns_kwargs['namespace'] = namespace
                    ns_kwargs['limit'] = 50  # Limit per namespace for performance
                    
                    # Execute API call for this namespace
                    response = api_method(**ns_kwargs)
                    if hasattr(response, 'items'):
                        all_items.extend(response.items)
                        
                except ApiException as api_error:
                    # Handle API exceptions gracefully - log but continue
                    if api_error.status == 404:
                        logging.debug(f"Resource {self.config.resource_type} not found in namespace {namespace} - skipping")
                    elif api_error.status == 403:
                        logging.debug(f"Access denied for {self.config.resource_type} in namespace {namespace} - skipping")
                    else:
                        logging.warning(f"API error loading {self.config.resource_type} from namespace {namespace}: {api_error.reason}")
                    continue
                except Exception as ns_error:
                    # Continue with other namespaces silently for better performance
                    logging.debug(f"Error loading {self.config.resource_type} from namespace {namespace}: {ns_error}")
                    continue
            
            if all_items:
                logging.info(f"Loaded {len(all_items)} {self.config.resource_type} from {len(selected_namespaces)} namespaces")
            return all_items
            
        except Exception as e:
            logging.warning(f"Error loading from multiple namespaces, falling back to specific namespaces: {e}")
            # Fallback to loading from default namespace only
            try:
                fallback_kwargs = base_kwargs.copy()
                fallback_kwargs['namespace'] = 'default'
                fallback_kwargs['limit'] = 100
                
                namespaced_method_name = self.loader._get_namespaced_api_method(self.config.resource_type)
                api_method = getattr(api_client, namespaced_method_name)
                response = api_method(**fallback_kwargs)
                return response.items if hasattr(response, 'items') else []
            except Exception as fallback_error:
                logging.error(f"Fallback namespace loading also failed: {fallback_error}")
                return []
    
    def _get_api_client(self, kube_client):
        """Get the appropriate API client for the resource type"""
        api_mapping = {
            # Core v1 resources
            'pods': kube_client.v1,
            'nodes': kube_client.v1,
            'services': kube_client.v1,
            'serviceaccounts': kube_client.v1,
            'configmaps': kube_client.v1,
            'secrets': kube_client.v1,
            'namespaces': kube_client.v1,
            'events': kube_client.v1,
            'endpoints': kube_client.v1,
            'persistentvolumes': kube_client.v1,
            'persistentvolumeclaims': kube_client.v1,
            'replicationcontrollers': kube_client.v1,
            'resourcequotas': kube_client.v1,
            'limitranges': kube_client.v1,
            
            # Apps v1 resources
            'deployments': kube_client.apps_v1,
            'replicasets': kube_client.apps_v1,
            'daemonsets': kube_client.apps_v1,
            'statefulsets': kube_client.apps_v1,
            
            # Networking v1 resources  
            'ingresses': kube_client.networking_v1,
            'networkpolicies': kube_client.networking_v1,
            'ingressclasses': kube_client.networking_v1,
            
            # Storage v1 resources
            'storageclasses': kube_client.storage_v1,
            
            # Batch v1 resources
            'jobs': kube_client.batch_v1,
            'cronjobs': kube_client.batch_v1,
            
            # RBAC v1 resources
            'roles': kube_client.rbac_v1,
            'rolebindings': kube_client.rbac_v1,
            'clusterroles': kube_client.rbac_v1,
            'clusterrolebindings': kube_client.rbac_v1,
        }
        
        # For new API clients that might not be available in older instances,
        # use fallbacks to prevent application crashes
        try:
            if self.config.resource_type == 'horizontalpodautoscalers':
                return getattr(kube_client, 'autoscaling_v1', kube_client.v1)
            elif self.config.resource_type == 'poddisruptionbudgets':
                return getattr(kube_client, 'policy_v1', kube_client.v1)
            elif self.config.resource_type in ['validatingwebhookconfigurations', 'mutatingwebhookconfigurations']:
                return getattr(kube_client, 'admissionregistration_v1', kube_client.v1)
            elif self.config.resource_type == 'runtimeclasses':
                return getattr(kube_client, 'node_v1', kube_client.v1)
            elif self.config.resource_type == 'leases':
                return getattr(kube_client, 'coordination_v1', kube_client.v1)
            elif self.config.resource_type == 'priorityclasses':
                return getattr(kube_client, 'scheduling_v1', kube_client.v1)
            elif self.config.resource_type == 'customresourcedefinitions':
                return getattr(kube_client, 'apiextensions_v1', kube_client.v1)
        except AttributeError:
            pass
        
        return api_mapping.get(self.config.resource_type, kube_client.v1)
    
    def _get_field_selector(self) -> str:
        """Get optimized field selector for common resources"""
        if self.config.resource_type == 'pods':
            return 'status.phase!=Succeeded,status.phase!=Failed'
        elif self.config.resource_type == 'nodes':
            return 'spec.unschedulable!=true'
        return ''
    
    def _process_items(self, items: List[Any]) -> List[Dict[str, Any]]:
        """Process raw API items into optimized format for UI consumption"""
        if not items:
            return []
        
        processed_items = []
        
        # Use optimized batch processing for better performance
        batch_size = min(self.config.batch_size, len(items))
        
        # Process in smaller batches to prevent API overload
        from concurrent.futures import ThreadPoolExecutor
        import math
        
        # Use smaller batches and fewer workers for stability
        optimal_batch_size = max(25, batch_size // 2)
        num_batches = math.ceil(len(items) / optimal_batch_size)
        
        with ThreadPoolExecutor(max_workers=min(2, num_batches)) as executor:
            futures = []
            
            for i in range(0, len(items), optimal_batch_size):
                if self.is_cancelled():
                    break
                    
                batch = items[i:i + optimal_batch_size]
                future = executor.submit(self._process_batch, batch)
                futures.append(future)
            
            # Collect results
            for future in futures:
                if self.is_cancelled():
                    break
                try:
                    batch_result = future.result(timeout=10)
                    processed_items.extend(batch_result)
                except Exception as e:
                    logging.debug(f"Error in batch processing: {e}")
                    continue
        
        return processed_items
    
    def _process_batch(self, batch: List[Any]) -> List[Dict[str, Any]]:
        """Process a batch of items efficiently"""
        processed_batch = []
        
        for item in batch:
            if self.is_cancelled():
                break
            
            try:
                processed_item = self._process_single_item(item)
                if processed_item:
                    processed_batch.append(processed_item)
            except Exception as e:
                logging.debug(f"Error processing item: {e}")
                continue
        
        return processed_batch
    
    def _process_single_item(self, item: Any) -> Optional[Dict[str, Any]]:
        """Process a single Kubernetes resource item"""
        try:
            # Extract common fields efficiently
            metadata = item.metadata
            name = metadata.name
            namespace = getattr(metadata, 'namespace', None)
            creation_timestamp = metadata.creation_timestamp
            
            # Calculate age efficiently using cached formatter
            age = self._format_age_fast(creation_timestamp)
            
            # Build base item dictionary
            processed_item = {
                'name': name,
                'namespace': namespace,
                'age': age,
                'created': creation_timestamp,
                'labels': metadata.labels or {},
                'annotations': metadata.annotations or {},
                'resource_type': self.config.resource_type,
                'uid': metadata.uid,
            }
            
            # Add resource-specific fields for performance
            self._add_resource_specific_fields(processed_item, item)
            
            # Add raw_data for UI components that need detailed information
            # Serialize the raw Kubernetes object for components that need it
            try:
                kube_client = get_kubernetes_client()
                if hasattr(kube_client, 'v1') and hasattr(kube_client.v1, 'api_client'):
                    processed_item['raw_data'] = kube_client.v1.api_client.sanitize_for_serialization(item)
                else:
                    # Fallback: create a basic raw_data structure
                    processed_item['raw_data'] = {
                        'metadata': {
                            'name': name,
                            'namespace': namespace,
                            'labels': metadata.labels,
                            'annotations': metadata.annotations,
                            'creation_timestamp': str(creation_timestamp) if creation_timestamp else None
                        }
                    }
            except Exception as e:
                logging.debug(f"Error serializing raw data: {e}")
                processed_item['raw_data'] = {}
            
            return processed_item
            
        except Exception as e:
            logging.debug(f"Error processing single item: {e}")
            return None
    
    def _add_resource_specific_fields(self, processed_item: Dict[str, Any], item: Any):
        """Add resource-specific fields efficiently"""
        resource_type = self.config.resource_type
        
        if resource_type == 'pods':
            self._add_pod_fields(processed_item, item)
        elif resource_type == 'nodes':
            self._add_node_fields(processed_item, item)
        elif resource_type == 'services':
            self._add_service_fields(processed_item, item)
        elif resource_type == 'configmaps':
            self._add_configmap_fields(processed_item, item)
        elif resource_type == 'secrets':
            self._add_secret_fields(processed_item, item)
        elif resource_type == 'leases':
            self._add_lease_fields(processed_item, item)
        elif resource_type == 'priorityclasses':
            self._add_priorityclass_fields(processed_item, item)
        elif resource_type in ['deployments', 'replicasets', 'statefulsets', 'daemonsets']:
            self._add_workload_fields(processed_item, item)
    
    def _add_pod_fields(self, processed_item: Dict[str, Any], pod: Any):
        """Add pod-specific fields efficiently"""
        status = pod.status
        spec = pod.spec
        
        # Enhanced status determination with more detail
        pod_status = 'Unknown'
        if status:
            pod_status = status.phase or 'Unknown'
            
            # Check for more specific container states
            if status.container_statuses:
                for cs in status.container_statuses:
                    if cs.state:
                        if cs.state.waiting:
                            reason = cs.state.waiting.reason
                            if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                                pod_status = reason
                                break
                        elif cs.state.terminated:
                            if cs.state.terminated.exit_code != 0:
                                pod_status = "Error"
                                break
        
        processed_item.update({
            'status': pod_status,
            'ready': self._get_pod_ready_status(status),
            'restarts': self._get_pod_restart_count(status),
            'node_name': spec.node_name if spec else None,
            'host_ip': status.host_ip if status else None,
            'pod_ip': status.pod_ip if status else None,
            'containers': len(spec.containers) if spec and spec.containers else 0,
            'init_containers': len(spec.init_containers) if spec and spec.init_containers else 0,
        })
    
    def _add_node_fields(self, processed_item: Dict[str, Any], node: Any):
        """Add node-specific fields efficiently"""
        status = node.status
        
        # Get node status efficiently
        node_status = 'Unknown'
        if status and status.conditions:
            for condition in status.conditions:
                if condition.type == 'Ready':
                    node_status = 'Ready' if condition.status == 'True' else 'NotReady'
                    break
        
        # Get node roles efficiently
        roles = []
        if node.metadata.labels:
            for label_key in node.metadata.labels:
                if 'node-role.kubernetes.io/' in label_key:
                    role = label_key.replace('node-role.kubernetes.io/', '')
                    if role:
                        roles.append(role)
        
        # Get taints count
        taints_count = 0
        if node.spec and node.spec.taints:
            taints_count = len(node.spec.taints)
        
        # Format memory capacity for display
        memory_capacity = ''
        if status and status.capacity and status.capacity.get('memory'):
            memory_raw = status.capacity.get('memory', '')
            if 'Ki' in memory_raw:
                # Convert from Ki to GB
                ki_value = int(memory_raw.replace('Ki', ''))
                gb_value = ki_value / (1024 * 1024)
                memory_capacity = f"{gb_value:.1f}GB"
            else:
                memory_capacity = memory_raw
        
        processed_item.update({
            'status': node_status,
            'roles': roles if roles else ['<none>'],
            'version': status.node_info.kubelet_version if status and status.node_info else 'Unknown',
            'os': status.node_info.operating_system if status and status.node_info else 'Unknown',
            'kernel': status.node_info.kernel_version if status and status.node_info else 'Unknown',
            'taints': str(taints_count),
            'cpu_usage': None,  # Will be filled by metrics if available
            'memory_usage': None,  # Will be filled by metrics if available
            'disk_usage': None,  # Will be filled by metrics if available
        })
        
        # Add capacity information
        if status and status.capacity:
            processed_item.update({
                'cpu_capacity': status.capacity.get('cpu', ''),
                'memory_capacity': memory_capacity,
                'disk_capacity': status.capacity.get('ephemeral-storage', ''),
                'pods_capacity': status.capacity.get('pods', ''),
            })
        
        # Try to populate actual usage metrics from metrics service
        try:
            kube_client = get_kubernetes_client()
            if hasattr(kube_client, 'get_node_metrics'):
                node_metrics = kube_client.get_node_metrics(processed_item['name'])
                if node_metrics:
                    # Extract usage percentages from metrics
                    if 'cpu' in node_metrics:
                        processed_item['cpu_usage'] = node_metrics['cpu'].get('usage', 0)
                    if 'memory' in node_metrics:
                        processed_item['memory_usage'] = node_metrics['memory'].get('usage', 0)
                    if 'disk' in node_metrics:
                        processed_item['disk_usage'] = node_metrics['disk'].get('usage', 0)
                        
                    logging.debug(f"Populated metrics for node {processed_item['name']}: "
                                f"CPU {processed_item.get('cpu_usage', 0):.1f}%, "
                                f"Memory {processed_item.get('memory_usage', 0):.1f}%, "
                                f"Disk {processed_item.get('disk_usage', 0):.1f}%")
        except Exception as e:
            logging.debug(f"Could not fetch metrics for node {processed_item['name']}: {e}")
            # Keep the defaults (None values)
    
    def _add_service_fields(self, processed_item: Dict[str, Any], service: Any):
        """Add service-specific fields efficiently"""
        try:
            spec = getattr(service, 'spec', None)
            status = getattr(service, 'status', None)
            
            # Basic service info with safe attribute access
            service_type = getattr(spec, 'type', 'ClusterIP') if spec else 'ClusterIP'
            cluster_ip = getattr(spec, 'cluster_ip', '<none>') if spec else '<none>'
            
            # Port information with robust attribute access
            ports = []
            if spec and hasattr(spec, 'ports') and spec.ports:
                for port in spec.ports:
                    try:
                        port_num = getattr(port, 'port', '')
                        protocol = getattr(port, 'protocol', 'TCP')
                        port_str = f"{port_num}/{protocol}"
                        
                        # Try different target port attribute names
                        target_port = getattr(port, 'target_port', None) or getattr(port, 'targetPort', None)
                        if target_port:
                            port_str += f"→{target_port}"
                        ports.append(port_str)
                    except Exception as e:
                        logging.debug(f"Error processing port: {e}")
                        continue
            port_text = ", ".join(ports) if ports else "<none>"
            
            # External IPs with safe access
            external_ips = []
            if spec and hasattr(spec, 'external_ips') and spec.external_ips:
                external_ips.extend(spec.external_ips)
            
            # Load balancer IPs with safe access
            if status and hasattr(status, 'load_balancer') and status.load_balancer:
                if hasattr(status.load_balancer, 'ingress') and status.load_balancer.ingress:
                    for ingress in status.load_balancer.ingress:
                        try:
                            ip = getattr(ingress, 'ip', None)
                            hostname = getattr(ingress, 'hostname', None)
                            if ip:
                                external_ips.append(ip)
                            elif hostname:
                                external_ips.append(hostname)
                        except Exception as e:
                            logging.debug(f"Error processing ingress: {e}")
                            continue
            
            external_ip_text = ", ".join(external_ips) if external_ips else "<none>"
            
            # Selector information with safe access
            selector = getattr(spec, 'selector', {}) if spec else {}
            selector_text = ", ".join([f"{k}={v}" for k, v in selector.items()]) if selector else "<none>"
            
            processed_item.update({
                'type': service_type,
                'cluster_ip': cluster_ip,
                'external_ip': external_ip_text,
                'ports': len(spec.ports) if spec and hasattr(spec, 'ports') and spec.ports else 0,
                'port_text': port_text,
                'selector': selector_text,
            })
            
        except Exception as e:
            logging.error(f"Error processing service fields: {e}")
            # Set safe defaults if processing fails
            processed_item.update({
                'type': 'Unknown',
                'cluster_ip': '<error>',
                'external_ip': '<error>',
                'ports': 0,
                'port_text': '<error>',
                'selector': '<error>',
            })
    
    def _add_configmap_fields(self, processed_item: Dict[str, Any], configmap: Any):
        """Add configmap-specific fields efficiently"""
        data = configmap.data
        binary_data = configmap.binary_data
        
        # Get keys from both data and binaryData
        keys = []
        if data:
            keys.extend(data.keys())
        if binary_data:
            keys.extend(binary_data.keys())
        
        processed_item.update({
            'keys': ', '.join(keys) if keys else '<none>',
            'data_keys_count': len(keys),
        })
    
    def _add_secret_fields(self, processed_item: Dict[str, Any], secret: Any):
        """Add secret-specific fields efficiently"""
        data = secret.data
        
        # Get keys but don't display values for security
        keys = list(data.keys()) if data else []
        
        processed_item.update({
            'keys': ', '.join(keys) if keys else '<none>',
            'data_keys_count': len(keys),
            'type': secret.type if secret.type else 'Opaque',
        })
    
    def _add_lease_fields(self, processed_item: Dict[str, Any], lease: Any):
        """Add lease-specific fields efficiently"""
        spec = lease.spec
        
        holder_identity = '<none>'
        lease_duration_seconds = 0
        
        if spec:
            holder_identity = spec.holder_identity if spec.holder_identity else '<none>'
            lease_duration_seconds = spec.lease_duration_seconds if spec.lease_duration_seconds else 0
        
        processed_item.update({
            'holder': holder_identity,
            'lease_duration': f"{lease_duration_seconds}s",
        })
    
    def _add_priorityclass_fields(self, processed_item: Dict[str, Any], priority_class: Any):
        """Add priority class-specific fields efficiently"""
        value = priority_class.value if priority_class.value is not None else 0
        global_default = priority_class.global_default if priority_class.global_default is not None else False
        description = priority_class.description if priority_class.description else ""
        
        processed_item.update({
            'value': str(value),
            'global_default': str(global_default).lower(),
            'description': description,
        })
    
    def _add_workload_fields(self, processed_item: Dict[str, Any], workload: Any):
        """Add workload-specific fields efficiently"""
        spec = workload.spec
        status = workload.status
        
        # Get replicas info
        replicas = getattr(spec, 'replicas', 1) if spec else 1
        ready_replicas = getattr(status, 'ready_replicas', 0) if status else 0
        
        processed_item.update({
            'replicas': f"{ready_replicas}/{replicas}",
            'ready_replicas': ready_replicas,
            'total_replicas': replicas,
        })
    
    @lru_cache(maxsize=1000)
    def _format_age_fast(self, creation_timestamp) -> str:
        """Fast age calculation with caching"""
        if not creation_timestamp:
            return 'Unknown'
        
        try:
            if hasattr(creation_timestamp, 'timestamp'):
                created = datetime.fromtimestamp(creation_timestamp.timestamp(), tz=timezone.utc)
            else:
                created = creation_timestamp
            
            now = datetime.now(timezone.utc)
            age_delta = now - created
            
            days = age_delta.days
            hours = age_delta.seconds // 3600
            minutes = (age_delta.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
                
        except Exception:
            return 'Unknown'
    
    def _get_pod_ready_status(self, status) -> str:
        """Get pod ready status efficiently"""
        if not status or not status.container_statuses:
            return '0/0'
        
        ready_count = sum(1 for cs in status.container_statuses if cs.ready)
        total_count = len(status.container_statuses)
        
        return f"{ready_count}/{total_count}"
    
    def _get_pod_restart_count(self, status) -> int:
        """Get pod restart count efficiently"""
        if not status or not status.container_statuses:
            return 0
        
        return sum(cs.restart_count for cs in status.container_statuses if cs.restart_count)
    
    def _get_service_external_ip(self, spec, status) -> Optional[str]:
        """Get service external IP efficiently"""
        if spec and spec.external_ips:
            return ', '.join(spec.external_ips)
        
        if spec and spec.type == 'LoadBalancer' and status and status.load_balancer:
            if status.load_balancer.ingress:
                ips = [ing.ip for ing in status.load_balancer.ingress if ing.ip]
                if ips:
                    return ', '.join(ips)
        
        return None
    
    def _generate_cache_key(self) -> str:
        """Generate cache key for this resource loading operation"""
        key_parts = [
            self.config.resource_type,
            self.config.namespace or 'all-namespaces',
            str(self.config.batch_size),
        ]
        return ':'.join(key_parts)
    
    def _cache_results(self, processed_items: List[Dict[str, Any]]):
        """Cache processed results for performance"""
        try:
            cache_service = get_unified_cache()
            cache_key = self._generate_cache_key()
            
            cache_service.cache_resources(
                self.config.resource_type,
                cache_key,
                processed_items,
                ttl_seconds=self.config.cache_ttl
            )
            
        except Exception as e:
            logging.debug(f"Failed to cache results: {e}")
    
    def _handle_timeout_fallback(self) -> Optional[LoadResult]:
        """Handle timeout fallback for timeout-prone resources"""
        # Apply fallback to ALL resources for Docker Desktop Kubernetes
        # Docker Desktop often has slow API responses
        
        try:
            # Try to get stale cached data as a fallback
            cache_service = get_unified_cache()
            cache_key = self._generate_cache_key()
            
            # Look for stale cache data (up to 1 hour old)
            stale_cached_items = cache_service.get_cached_resources(
                self.config.resource_type, 
                cache_key,
                max_age_seconds=3600  # Allow 1 hour old data as fallback
            )
            
            if stale_cached_items:
                logging.info(f"Using stale cache fallback for {self.config.resource_type}: {len(stale_cached_items)} items")
                return LoadResult(
                    success=True,
                    resource_type=self.config.resource_type,
                    items=stale_cached_items,
                    total_count=len(stale_cached_items),
                    from_cache=True,
                    load_time_ms=0
                )
            
            # If no cache available, return empty result for ALL resources to avoid blocking
            # This is better than showing nothing - at least the UI doesn't freeze
            logging.info(f"Returning empty fallback for timed-out resource: {self.config.resource_type}")
            return LoadResult(
                success=True,
                resource_type=self.config.resource_type,
                items=[],
                total_count=0,
                from_cache=False,
                load_time_ms=0,
                error_message=f"Timeout - returning empty result to avoid blocking UI"
            )
                
        except Exception as e:
            logging.debug(f"Fallback handling failed for {self.config.resource_type}: {e}")
        
        return None
    
# cancel() method inherited from EnhancedBaseWorker


class HighPerformanceResourceLoader(QObject):
    """
    High-Performance Unified Resource Loader
    Consolidates 3 duplicate loaders into one optimized system.
    Designed for maximum speed and smooth user experience.
    """
    
    # Signals for UI updates
    loading_started = pyqtSignal(str)  # resource_type
    loading_progress = pyqtSignal(str, int, int)  # resource_type, current, total
    loading_completed = pyqtSignal(str, object)  # resource_type, LoadResult
    loading_error = pyqtSignal(str, str)  # resource_type, error_message
    
    def __init__(self):
        super().__init__()
        
        # Use unified thread manager for consistency
        self._thread_manager = get_thread_manager()
        self._active_workers: Dict[str, ResourceLoadWorker] = {}
        self._worker_lock = threading.RLock()
        
        # Configuration cache for performance
        self._config_cache: Dict[str, ResourceConfig] = {}
        
        # Performance monitoring
        self._load_stats = defaultdict(list)
        self._stats_lock = threading.RLock()
        
        # Initialize default configurations for all resource types
        self._initialize_default_configs()
        
        logging.info("High-Performance Resource Loader initialized")
    
    def _initialize_default_configs(self):
        """Initialize optimized default configurations for all resource types"""
        
        # High-frequency resources (need faster loading)
        high_frequency_resources = ['pods', 'events', 'nodes']
        
        # Medium-frequency resources
        medium_frequency_resources = ['deployments', 'services', 'configmaps', 'secrets']
        
        # Low-frequency resources (can cache longer)
        low_frequency_resources = ['storageclasses', 'clusterroles', 'namespaces']
        
        # Configure high-frequency resources for speed
        for resource_type in high_frequency_resources:
            self._config_cache[resource_type] = ResourceConfig(
                resource_type=resource_type,
                api_method=self._get_api_method(resource_type),
                batch_size=100,
                timeout_seconds=15,
                cache_ttl=60,  # 1 minute cache
                enable_streaming=True,
                max_concurrent_requests=8
            )
        
        # Configure medium-frequency resources
        for resource_type in medium_frequency_resources:
            self._config_cache[resource_type] = ResourceConfig(
                resource_type=resource_type,
                api_method=self._get_api_method(resource_type),
                batch_size=50,
                timeout_seconds=20,
                cache_ttl=300,  # 5 minute cache
                enable_streaming=True,
                max_concurrent_requests=5
            )
        
        # Configure low-frequency resources for efficiency
        for resource_type in low_frequency_resources:
            self._config_cache[resource_type] = ResourceConfig(
                resource_type=resource_type,
                api_method=self._get_api_method(resource_type),
                batch_size=25,
                timeout_seconds=30,
                cache_ttl=900,  # 15 minute cache
                enable_streaming=False,
                max_concurrent_requests=3
            )
    
    def _get_api_method(self, resource_type: str) -> str:
        """Get the appropriate API method name for the resource type"""
        method_mapping = {
            # Core v1 resources
            'pods': 'list_pod_for_all_namespaces',
            'nodes': 'list_node',
            'services': 'list_service_for_all_namespaces',
            'serviceaccounts': 'list_service_account_for_all_namespaces',
            'configmaps': 'list_config_map_for_all_namespaces',
            'secrets': 'list_secret_for_all_namespaces',
            'namespaces': 'list_namespace',
            'events': 'list_event_for_all_namespaces',
            'endpoints': 'list_endpoints_for_all_namespaces',
            'persistentvolumes': 'list_persistent_volume',
            'persistentvolumeclaims': 'list_persistent_volume_claim_for_all_namespaces',
            'resourcequotas': 'list_resource_quota_for_all_namespaces',
            'limitranges': 'list_limit_range_for_all_namespaces',
            
            # Apps v1 resources
            'deployments': 'list_deployment_for_all_namespaces',
            'replicasets': 'list_replica_set_for_all_namespaces',
            'replicationcontrollers': 'list_replication_controller_for_all_namespaces',
            'daemonsets': 'list_daemon_set_for_all_namespaces',
            'statefulsets': 'list_stateful_set_for_all_namespaces',
            
            # Networking v1 resources
            'ingresses': 'list_ingress_for_all_namespaces',
            'networkpolicies': 'list_network_policy_for_all_namespaces',
            'ingressclasses': 'list_ingress_class',
            
            # Storage v1 resources
            'storageclasses': 'list_storage_class',
            
            # Batch v1 resources
            'jobs': 'list_job_for_all_namespaces',
            'cronjobs': 'list_cron_job_for_all_namespaces',
            
            # RBAC v1 resources
            'roles': 'list_role_for_all_namespaces',
            'rolebindings': 'list_role_binding_for_all_namespaces',
            'clusterroles': 'list_cluster_role',
            'clusterrolebindings': 'list_cluster_role_binding',
            
            # Autoscaling v1 resources
            'horizontalpodautoscalers': 'list_horizontal_pod_autoscaler_for_all_namespaces',
            
            # Policy v1 resources
            'poddisruptionbudgets': 'list_namespaced_pod_disruption_budget',
            
            # Admission registration v1 resources
            'validatingwebhookconfigurations': 'list_validating_webhook_configuration',
            'mutatingwebhookconfigurations': 'list_mutating_webhook_configuration',
            
            # Node v1 resources
            'runtimeclasses': 'list_runtime_class',
            
            # Coordination v1 resources
            'leases': 'list_lease_for_all_namespaces',
            
            # Scheduling v1 resources
            'priorityclasses': 'list_priority_class',
            
            # Custom Resources
            'customresourcedefinitions': 'list_custom_resource_definition',
        }
        
        # For Config resources that might need special handling
        if resource_type in ['poddisruptionbudgets', 'horizontalpodautoscalers', 
                           'validatingwebhookconfigurations', 'mutatingwebhookconfigurations',
                           'runtimeclasses', 'leases', 'priorityclasses']:
            # If the resource type isn't in the mapping, fall back to a safe default
            if resource_type not in method_mapping:
                logging.warning(f"API method for {resource_type} not found, using fallback")
                return 'list_pod_for_all_namespaces'
        
        return method_mapping.get(resource_type, 'list_pod_for_all_namespaces')
    
    def _get_namespaced_api_method(self, resource_type: str) -> str:
        """Get the appropriate namespaced API method name for the resource type"""
        namespaced_method_mapping = {
            # Core v1 resources
            'pods': 'list_namespaced_pod',
            'services': 'list_namespaced_service',
            'serviceaccounts': 'list_namespaced_service_account',
            'configmaps': 'list_namespaced_config_map',
            'secrets': 'list_namespaced_secret',
            'events': 'list_namespaced_event',
            'endpoints': 'list_namespaced_endpoints',
            'persistentvolumeclaims': 'list_namespaced_persistent_volume_claim',
            'resourcequotas': 'list_namespaced_resource_quota',
            'limitranges': 'list_namespaced_limit_range',
            
            # Apps v1 resources
            'deployments': 'list_namespaced_deployment',
            'replicasets': 'list_namespaced_replica_set',
            'replicationcontrollers': 'list_namespaced_replication_controller',
            'daemonsets': 'list_namespaced_daemon_set',
            'statefulsets': 'list_namespaced_stateful_set',
            
            # Networking v1 resources
            'ingresses': 'list_namespaced_ingress',
            'networkpolicies': 'list_namespaced_network_policy',
            
            # Batch v1 resources
            'jobs': 'list_namespaced_job',
            'cronjobs': 'list_namespaced_cron_job',
            
            # RBAC v1 resources
            'roles': 'list_namespaced_role',
            'rolebindings': 'list_namespaced_role_binding',
            
            # Autoscaling v1 resources
            'horizontalpodautoscalers': 'list_namespaced_horizontal_pod_autoscaler',
            
            # Policy v1 resources
            'poddisruptionbudgets': 'list_namespaced_pod_disruption_budget',
            
            # Coordination v1 resources
            'leases': 'list_namespaced_lease',
        }
        
        # For cluster-scoped resources, return the original all-namespaces method
        if resource_type in ResourceLoadWorker.CLUSTER_SCOPED_RESOURCES:
            return self._get_api_method(resource_type)
        
        return namespaced_method_mapping.get(resource_type, 'list_namespaced_pod')
    
    @log_performance
    def load_resources_with_search_async(
        self,
        resource_type: str,
        namespace: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> str:
        """Load resources with search filtering across all namespaces"""
        if not resource_type:
            logging.error("Resource type is required for search loading")
            return ""
        
        # Create search-enabled configuration
        config = ResourceConfig(
            resource_type=resource_type,
            api_method=self._get_api_method(resource_type),
            namespace=namespace,
            batch_size=50,  # Larger batch for search
            timeout_seconds=45,  # Longer timeout for search
            cache_ttl=300,  # 5 minutes cache for search results
            enable_pagination=True,  # Enable pagination for comprehensive search
            max_concurrent_requests=3  # More requests for search
        )
        
        operation_id = f"search_{resource_type}_{int(time.time())}"
        
        # Emit loading started signal for search
        self.loading_started.emit(resource_type)
        
        # Create and submit search worker
        worker = SearchResourceLoadWorker(config, self, search_query)
        
        # Connect worker signals to emit search results through main loader signals
        worker.signals.finished.connect(
            lambda result: self._handle_search_completion_success(result, resource_type, namespace, operation_id)
        )
        worker.signals.error.connect(
            lambda error: self._handle_search_completion_error(error, resource_type, namespace, operation_id)
        )
        
        # Submit to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(operation_id, worker)
        
        return operation_id
    
    def _handle_search_completion_success(self, result: LoadResult, resource_type: str, namespace: Optional[str], operation_id: str):
        """Handle successful search completion"""
        try:
            # Emit the search results through the main loader signals
            self.loading_completed.emit(resource_type, result)
            logging.info(
                f"Search completed: found {result.total_count} {resource_type} "
                f"in {result.load_time_ms:.1f}ms "
                f"({'cached' if result.from_cache else 'fresh'})"
            )
        except Exception as e:
            logging.error(f"Error emitting search completion signal: {e}")
    
    def _handle_search_completion_error(self, error_message: str, resource_type: str, namespace: Optional[str], operation_id: str):
        """Handle error in search completion"""
        try:
            self.loading_error.emit(resource_type, error_message)
            logging.error(f"Search failed for {resource_type}: {error_message}")
        except Exception as e:
            logging.error(f"Error emitting search error signal: {e}")

    @log_performance
    def load_resources_async(
        self, 
        resource_type: str, 
        namespace: Optional[str] = None,
        custom_config: Optional[ResourceConfig] = None
    ) -> str:
        """
        Load Kubernetes resources asynchronously with high performance.
        Returns operation ID for tracking.
        """
        
        # Get or create configuration
        config = custom_config or self._get_config_for_resource(resource_type, namespace)
        
        # Generate operation ID
        operation_id = f"{resource_type}_{namespace or 'all'}_{int(time.time() * 1000)}"
        
        # Cancel any existing load for this resource type
        self._cancel_existing_load(resource_type, namespace)
        
        # Emit loading started signal
        self.loading_started.emit(resource_type)
        
        # Create and start worker
        worker = ResourceLoadWorker(config, self)
        
        # Track the worker
        with self._worker_lock:
            worker_key = f"{resource_type}_{namespace or 'all'}"
            self._active_workers[worker_key] = worker
        
        # Connect worker signals for completion handling
        worker.signals.finished.connect(
            lambda result: self._handle_load_completion_success(result, resource_type, namespace, operation_id)
        )
        worker.signals.error.connect(
            lambda error: self._handle_load_completion_error(error, resource_type, namespace, operation_id)
        )
        
        # Submit to unified thread manager
        self._thread_manager.submit_worker(operation_id, worker)
        
        return operation_id
    
    def _get_config_for_resource(self, resource_type: str, namespace: Optional[str]) -> ResourceConfig:
        """Get optimized configuration for resource type"""
        base_config = self._config_cache.get(resource_type)
        
        if not base_config:
            # Create default config for unknown resource types
            base_config = ResourceConfig(
                resource_type=resource_type,
                api_method=self._get_api_method(resource_type)
            )
            self._config_cache[resource_type] = base_config
        
        # Create a copy with namespace if specified
        if namespace:
            # Get the correct namespaced API method
            namespaced_api_method = self._get_namespaced_api_method(resource_type)
            
            config = ResourceConfig(
                resource_type=base_config.resource_type,
                api_method=namespaced_api_method,
                namespace=namespace,
                batch_size=base_config.batch_size,
                timeout_seconds=base_config.timeout_seconds,
                cache_ttl=base_config.cache_ttl,
                enable_streaming=base_config.enable_streaming,
                max_concurrent_requests=base_config.max_concurrent_requests
            )
            return config
        
        return base_config
    
    def _cancel_existing_load(self, resource_type: str, namespace: Optional[str]):
        """Cancel any existing load operation for the same resource"""
        worker_key = f"{resource_type}_{namespace or 'all'}"
        
        with self._worker_lock:
            if worker_key in self._active_workers:
                existing_worker = self._active_workers[worker_key]
                existing_worker.cancel()
                logging.debug(f"Cancelled existing load for {resource_type}")
    
# Method removed - monitoring is now handled by EnhancedBaseWorker signals
    
    def _handle_load_completion_success(self, result: LoadResult, resource_type: str, namespace: Optional[str], operation_id: str):
        """Handle successful load completion"""
        try:
            self.loading_completed.emit(resource_type, result)
            logging.info(
                f"Loaded {result.total_count} {resource_type} "
                f"in {result.load_time_ms:.1f}ms "
                f"({'cached' if result.from_cache else 'fresh'})"
            )
        except Exception as e:
            logging.error(f"Error emitting load completion signal: {e}")
        finally:
            # Cleanup worker reference
            self._cleanup_worker(resource_type, namespace)
    
    def _handle_load_completion_error(self, error_message: str, resource_type: str, namespace: Optional[str], operation_id: str):
        """Handle error in load completion"""
        try:
            self.loading_error.emit(resource_type, error_message)
            logging.error(f"Failed to load {resource_type}: {error_message}")
        except Exception as e:
            logging.error(f"Error emitting load error signal: {e}")
        finally:
            # Cleanup worker reference
            self._cleanup_worker(resource_type, namespace)
    
    def _cleanup_worker(self, resource_type: str, namespace: Optional[str]):
        """Cleanup worker reference"""
        worker_key = f"{resource_type}_{namespace or 'all'}"
        with self._worker_lock:
            self._active_workers.pop(worker_key, None)
    
    def _record_performance_stats(self, resource_type: str, load_time_ms: float, success: bool):
        """Record performance statistics for monitoring"""
        with self._stats_lock:
            stats = self._load_stats[resource_type]
            stats.append({
                'timestamp': time.time(),
                'load_time_ms': load_time_ms,
                'success': success
            })
            
            # Keep only last 100 entries per resource type
            if len(stats) > 100:
                stats.pop(0)
    
    def get_performance_stats(self, resource_type: str) -> Dict[str, Any]:
        """Get performance statistics for a resource type"""
        with self._stats_lock:
            stats = self._load_stats.get(resource_type, [])
            
            if not stats:
                return {'avg_load_time_ms': 0, 'success_rate': 0, 'total_loads': 0}
            
            successful_loads = [s for s in stats if s['success']]
            total_loads = len(stats)
            
            if successful_loads:
                avg_load_time = sum(s['load_time_ms'] for s in successful_loads) / len(successful_loads)
            else:
                avg_load_time = 0
            
            success_rate = len(successful_loads) / total_loads if total_loads > 0 else 0
            
            return {
                'avg_load_time_ms': round(avg_load_time, 1),
                'success_rate': round(success_rate * 100, 1),
                'total_loads': total_loads,
                'last_load_time': max(s['timestamp'] for s in stats) if stats else 0
            }
    
    def cancel_all_loads(self):
        """Cancel all active loading operations"""
        with self._worker_lock:
            for worker in self._active_workers.values():
                worker.cancel()
            self._active_workers.clear()
        
        logging.info("Cancelled all active resource loading operations")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            cache_service = get_unified_cache()
            return cache_service.get_global_stats()
        except Exception as e:
            logging.error(f"Error getting cache stats: {e}")
            return {}
    
    def clear_cache(self, resource_type: Optional[str] = None):
        """Clear cache for specific resource type or optimize all caches"""
        try:
            cache_service = get_unified_cache()
            if resource_type:
                cache_service.clear_resource_cache(resource_type)
                logging.info(f"Cleared cache for {resource_type}")
            else:
                # Don't clear all caches - this destroys performance
                # Instead, optimize existing caches
                cache_service.optimize_caches()
                logging.info("Optimized resource caches instead of clearing all")
        except Exception as e:
            logging.error(f"Error clearing cache: {e}")
    
    def cleanup(self):
        """Cleanup resources and shutdown thread pool"""
        logging.info("Shutting down High-Performance Resource Loader")
        
        # Cancel all active loads
        self.cancel_all_loads()
        
        # Cleanup is handled by thread manager
        # No need to shutdown thread pool as it's managed globally
        
        # Clear stats
        with self._stats_lock:
            self._load_stats.clear()
        
        logging.info("Resource Loader cleanup completed")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_thread_manager'):
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in Resource Loader destructor: {e}")


# Singleton management
_unified_loader_instance = None

def get_unified_resource_loader() -> HighPerformanceResourceLoader:
    """Get or create the unified resource loader singleton"""
    global _unified_loader_instance
    if _unified_loader_instance is None:
        _unified_loader_instance = HighPerformanceResourceLoader()
    return _unified_loader_instance

def shutdown_unified_resource_loader():
    """Shutdown the unified resource loader"""
    global _unified_loader_instance
    if _unified_loader_instance is not None:
        _unified_loader_instance.cleanup()
        _unified_loader_instance = None