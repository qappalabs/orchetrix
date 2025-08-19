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


class ResourceLoadWorker(EnhancedBaseWorker):
    """High-performance worker for loading Kubernetes resources"""
    
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
        
        # Get the API method
        api_method = getattr(api_client, self.config.api_method)
        
        # Build method parameters for optimal performance and fast failure
        kwargs = {
            'timeout_seconds': 30,  # Longer timeout for Docker Desktop
            '_request_timeout': 35  # Longer request timeout for slow clusters
        }
        
        # Add namespace if specified and resource is namespaced
        cluster_scoped_resources = {
            'nodes', 'namespaces', 'persistentvolumes', 'storageclasses',
            'ingressclasses', 'clusterroles', 'clusterrolebindings',
            'customresourcedefinitions'
        }
        
        if (self.config.namespace and 
            self.config.resource_type not in cluster_scoped_resources):
            kwargs['namespace'] = self.config.namespace
        
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
    
    def _get_api_client(self, kube_client):
        """Get the appropriate API client for the resource type"""
        api_mapping = {
            # Core v1 resources
            'pods': kube_client.v1,
            'nodes': kube_client.v1,
            'services': kube_client.v1,
            'configmaps': kube_client.v1,
            'secrets': kube_client.v1,
            'namespaces': kube_client.v1,
            'events': kube_client.v1,
            'endpoints': kube_client.v1,
            'persistentvolumes': kube_client.v1,
            'persistentvolumeclaims': kube_client.v1,
            
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
            
            # Custom Resources
            'customresourcedefinitions': kube_client.apiextensions_v1,
        }
        
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
    
    def _add_service_fields(self, processed_item: Dict[str, Any], service: Any):
        """Add service-specific fields efficiently"""
        spec = service.spec
        status = service.status
        
        processed_item.update({
            'type': spec.type if spec else 'Unknown',
            'cluster_ip': spec.cluster_ip if spec else None,
            'external_ip': self._get_service_external_ip(spec, status),
            'ports': len(spec.ports) if spec and spec.ports else 0,
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
        if spec and spec.external_i_ps:
            return ', '.join(spec.external_i_ps)
        
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
        from Utils.thread_manager import get_thread_manager
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
            'configmaps': 'list_config_map_for_all_namespaces',
            'secrets': 'list_secret_for_all_namespaces',
            'namespaces': 'list_namespace',
            'events': 'list_event_for_all_namespaces',
            'endpoints': 'list_endpoints_for_all_namespaces',
            'persistentvolumes': 'list_persistent_volume',
            'persistentvolumeclaims': 'list_persistent_volume_claim_for_all_namespaces',
            
            # Apps v1 resources
            'deployments': 'list_deployment_for_all_namespaces',
            'replicasets': 'list_replica_set_for_all_namespaces',
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
            
            # Custom Resources
            'customresourcedefinitions': 'list_custom_resource_definition',
        }
        
        return method_mapping.get(resource_type, 'list_pod_for_all_namespaces')
    
    def _get_namespaced_api_method(self, resource_type: str) -> str:
        """Get the appropriate namespaced API method name for the resource type"""
        namespaced_method_mapping = {
            # Core v1 resources
            'pods': 'list_namespaced_pod',
            'services': 'list_namespaced_service',
            'configmaps': 'list_namespaced_config_map',
            'secrets': 'list_namespaced_secret',
            'events': 'list_namespaced_event',
            'endpoints': 'list_namespaced_endpoints',
            'persistentvolumeclaims': 'list_namespaced_persistent_volume_claim',
            
            # Apps v1 resources
            'deployments': 'list_namespaced_deployment',
            'replicasets': 'list_namespaced_replica_set',
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
        }
        
        # For cluster-scoped resources, return the original all-namespaces method
        cluster_scoped_resources = {
            'nodes', 'namespaces', 'persistentvolumes', 'storageclasses',
            'ingressclasses', 'clusterroles', 'clusterrolebindings',
            'customresourcedefinitions'
        }
        
        if resource_type in cluster_scoped_resources:
            return self._get_api_method(resource_type)
        
        return namespaced_method_mapping.get(resource_type, 'list_namespaced_pod')
    
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