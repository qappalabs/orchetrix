"""
High-Performance Unified Resource Loader
Consolidates 3 duplicate resource loaders into one optimized system.
Designed for speed, efficiency, and smooth user experience.
"""

import atexit
import gc
import logging
import os
import threading
import time
import traceback
# Use unified thread manager instead of separate ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, Qt, QMetaObject
from PyQt6.QtWidgets import QApplication

from kubernetes.client.rest import ApiException
from Utils.kubernetes_client import get_kubernetes_client
from Services.kubernetes.api_config import APIClientConfig
from Utils.error_handler import get_error_handler, log_performance
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager
from Utils.unified_cache_system import get_unified_cache
from Utils.data_formatters import format_age


# For cluster-scoped resources, return the original all-namespaces method
cluster_scoped_resources = {
    'nodes', 'namespaces', 'persistentvolumes', 'storageclasses',
    'ingressclasses', 'clusterroles', 'clusterrolebindings',
    'customresourcedefinitions', 'priorityclasses', 'runtimeclasses',
    'mutatingwebhookconfigurations', 'validatingwebhookconfigurations'
}

@dataclass
class ResourceConfig:
    """Configuration for resource loading operations"""
    resource_type: str
    api_method: str
    namespace: Optional[str] = None
    batch_size: int = 50  # Increased for heavy data handling
    timeout_seconds: int = APIClientConfig.REQUEST_TIMEOUT  # Use centralized timeout
    enable_streaming: bool = False  # Keep disabled for stability
    enable_pagination: bool = True  # Enable for heavy data handling
    max_concurrent_requests: int = 3  # Slightly increased for heavy data
    enable_chunking: bool = True  # New: Enable data chunking for heavy loads
    chunk_size: int = 100  # New: Process data in chunks of 100 items
    progressive_loading: bool = True  # New: Enable progressive loading
    enable_caching: bool = True  # Enable caching by default


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
            # Load directly from API (no caching)

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
            logging.debug(f"Filtering {len(all_items)} items for search query: '{self.search_query}'")
            filtered_items = []
            for item in all_items:
                if self._item_matches_search(item):
                    filtered_items.append(item)
            logging.debug(f"Search filtering result: {len(filtered_items)} items matched out of {len(all_items)} total")
            return filtered_items

        return all_items

    def _load_from_single_namespace_with_search(self) -> List[Any]:
        """Load from single namespace for search"""
        kube_client = get_kubernetes_client()
        api_client = self.loader._get_api_client(kube_client, self.config.resource_type)

        # Get the correct namespaced API method
        namespaced_method_name = self.loader._get_namespaced_api_method(self.config.resource_type)
        api_method = getattr(api_client, namespaced_method_name)

        kwargs = {
            # 'namespace': self.config.namespace,
            'timeout_seconds': self.config.timeout_seconds,
            '_request_timeout': self.config.timeout_seconds + 5,
            'limit': 200  # Larger limit for search
        }
            # Only add namespace if NOT cluster-scoped
        if self.config.resource_type not in cluster_scoped_resources:
            kwargs['namespace'] = self.config.namespace

        response = api_method(**kwargs)
        return response.items if hasattr(response, 'items') else []

    def _load_from_multiple_namespaces_with_search(self) -> List[Any]:
        """Load from multiple namespaces for comprehensive search"""
        all_items = []

        try:
            kube_client = get_kubernetes_client()
            api_client = self.loader._get_api_client(kube_client, self.config.resource_type)

            # Handle cluster-scoped resources differently
            if self.config.resource_type in cluster_scoped_resources:
                # For cluster-scoped resources (like nodes), use cluster-wide API method
                cluster_method_name = self.loader._get_api_method(self.config.resource_type)
                api_method = getattr(api_client, cluster_method_name)

                kwargs = {
                    'timeout_seconds': APIClientConfig.REQUEST_TIMEOUT,
                    '_request_timeout': APIClientConfig.REQUEST_TIMEOUT + 5,
                    'limit': 100
                }

                response = api_method(**kwargs)
                if hasattr(response, 'items'):
                    all_items.extend(response.items)

                logging.info(f"Search loaded {len(all_items)} cluster-scoped {self.config.resource_type}")
                return all_items

            # For namespaced resources, search across namespaces
            namespaces_response = get_kubernetes_client().v1.list_namespace(limit=100)
            namespace_names = [ns.metadata.name for ns in namespaces_response.items]

            namespaced_method_name = self.loader._get_namespaced_api_method(self.config.resource_type)
            api_method = getattr(api_client, namespaced_method_name)

            for namespace in namespace_names:
                if self.is_cancelled():
                    break

                try:
                    kwargs = {
                        'namespace': namespace,
                        'timeout_seconds': APIClientConfig.REQUEST_TIMEOUT,
                        '_request_timeout': APIClientConfig.REQUEST_TIMEOUT + 5,
                        'limit': 100
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
        """Check if item matches the search query (focused search for better UX)"""
        if not self.search_query:
            return True

        try:
            # Get item name for logging
            name = getattr(item.metadata, 'name', 'unknown') if hasattr(item, 'metadata') and item.metadata else 'unknown'

            # PRIMARY SEARCH: Name matching (most important)
            if hasattr(item, 'metadata') and item.metadata:
                item_name = getattr(item.metadata, 'name', '').lower()
                if self.search_query in item_name:
                    logging.debug(f"Search match in name: '{item_name}' contains '{self.search_query}'")
                    return True

                # SECONDARY SEARCH: Namespace matching (less important)
                namespace = getattr(item.metadata, 'namespace', '').lower()
                if self.search_query in namespace:
                    logging.debug(f"Search match in namespace: '{namespace}' contains '{self.search_query}' for item '{name}'")
                    return True

                # TERTIARY SEARCH: Important labels only (very selective)
                labels = getattr(item.metadata, 'labels', {}) or {}
                important_labels = ['app', 'name', 'component', 'tier', 'version', 'k8s-app']
                for label_key in important_labels:
                    if label_key in labels:
                        label_value = str(labels[label_key]).lower()
                        if self.search_query in label_value:
                            logging.debug(f"Search match in important label '{label_key}': '{label_value}' contains '{self.search_query}' for item '{name}'")
                            return True

            # SKIP spec search for now as it's too broad and causes false positives
            # This makes search results more predictable and user-friendly

            # Log what we searched in
            logging.debug(f"No search match for query '{self.search_query}' in item: name='{name}', namespace='{getattr(item.metadata, 'namespace', 'N/A') if hasattr(item, 'metadata') and item.metadata else 'N/A'}'")

        except Exception as e:
            logging.debug(f"Exception in search matching: {e}")
            pass

        return False


    def _process_search_items(self, items: List[Any]) -> List[Dict[str, Any]]:
        """Process search results using simplified processing for speed"""
        if not items:
            logging.debug("No items to process for search")
            return []

        logging.debug(f"Processing {len(items)} search items")
        processed_items = []
        skipped_count = 0

        for item in items:
            if self.is_cancelled():
                break

            try:
                # Use basic processing for search results (faster)
                processed_item = self._process_single_search_item(item)
                if processed_item:
                    processed_items.append(processed_item)
                else:
                    skipped_count += 1
                    item_name = getattr(item.metadata, 'name', 'unknown') if hasattr(item, 'metadata') else 'unknown'
                    logging.debug(f"SKIPPED processing item: {item_name} - _process_single_search_item returned None")
            except Exception as e:
                skipped_count += 1
                item_name = getattr(item.metadata, 'name', 'unknown') if hasattr(item, 'metadata') else 'unknown'
                logging.debug(f"ERROR processing search item {item_name}: {e}")
                continue

        logging.debug(f"Search processing complete: {len(processed_items)} processed, {skipped_count} skipped")
        return processed_items

    def _process_single_search_item(self, item: Any) -> Optional[Dict[str, Any]]:
        """Process a single search result item with comprehensive data"""
        try:
            # Extract basic fields efficiently
            metadata = item.metadata
            if not metadata:
                return None

            name = metadata.name
            if not name:
                return None

            namespace = getattr(metadata, 'namespace', None)
            creation_timestamp = metadata.creation_timestamp

            # Calculate age efficiently
            age = self._format_age_fast(creation_timestamp)

            # Build resource data using the same structure as regular loader
            resource_data = {
                'name': name,
                'namespace': namespace,
                'age': age,
                'created': creation_timestamp,
                'labels': metadata.labels or {},
                'annotations': metadata.annotations or {},
                'resource_type': self.config.resource_type,
                'uid': metadata.uid,
                'search_matched': True,  # Mark as search result
            }

            # Add resource-specific fields
            self._add_resource_specific_fields(resource_data, item)

            # Add raw_data for UI components that need detailed information
            try:
                kube_client = get_kubernetes_client()
                if hasattr(kube_client, 'v1') and hasattr(kube_client.v1, 'api_client'):
                    resource_data['raw_data'] = kube_client.v1.api_client.sanitize_for_serialization(item)
                else:
                    resource_data['raw_data'] = {}
            except Exception as e:
                logging.debug(f"Error serializing search raw data: {e}")
                resource_data['raw_data'] = {}

            return resource_data

        except Exception as e:
            logging.debug(f"Error processing single search item: {e}")
            return None

    def _format_age_fast(self, creation_timestamp) -> str:
        """Format age quickly for search results"""
        return format_age(creation_timestamp)

    def _add_resource_specific_fields(self, processed_item: Dict[str, Any], item: Any):
        """Add resource-specific fields for search results"""
        try:
            ResourceLoadWorker._add_resource_specific_fields(processed_item, item, self.config.resource_type, None)
        except Exception as e:
            logging.debug(f"Error adding resource-specific fields: {e}")
            processed_item['status'] = 'Unknown'

    def _add_pod_fields(self, processed_item: Dict[str, Any], pod: Any):
        """Add pod-specific fields"""
        status = pod.status if hasattr(pod, 'status') else None
        spec = pod.spec if hasattr(pod, 'spec') else None

        # Pod status with enhanced details
        pod_status = 'Unknown'
        if status:
            pod_status = status.phase or 'Unknown'

            # Check for more specific container states
            if hasattr(status, 'container_statuses') and status.container_statuses:
                for cs in status.container_statuses:
                    if hasattr(cs, 'state') and cs.state:
                        if hasattr(cs.state, 'waiting') and cs.state.waiting:
                            reason = cs.state.waiting.reason
                            if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                                pod_status = reason
                                break
                        elif hasattr(cs.state, 'terminated') and cs.state.terminated:
                            # For terminated containers, show more specific status
                            exit_code = cs.state.terminated.exit_code
                            reason = cs.state.terminated.reason
                            if exit_code != 0:
                                pod_status = f"Error ({reason})"
                                break
                            elif reason == "Completed":
                                pod_status = f"Completed ({exit_code})"
                                break

        # Container counts and restart count
        containers_count = 0
        restart_count = 0
        ready_containers = 0

        if spec and hasattr(spec, 'containers') and spec.containers:
            containers_count = len(spec.containers)

        if status and hasattr(status, 'container_statuses') and status.container_statuses:
            ready_containers = sum(1 for cs in status.container_statuses if hasattr(cs, 'ready') and cs.ready)
            restart_count = sum(getattr(cs, 'restart_count', 0) for cs in status.container_statuses)

        processed_item.update({
            'status': pod_status,
            'ready': f"{ready_containers}/{containers_count}",
            'restarts': str(restart_count),
            'containers': containers_count,
            'node_name': getattr(spec, 'node_name', '') if spec else '',
        })

    def _add_service_fields(self, processed_item: Dict[str, Any], service: Any):
        """Add service-specific fields"""
        spec = service.spec if hasattr(service, 'spec') else None

        if spec:
            processed_item.update({
                'type': getattr(spec, 'type', 'Unknown'),
                'cluster_ip': getattr(spec, 'cluster_ip', 'None'),
                'service_type': getattr(spec, 'type', 'Unknown'),
                'status': 'Active'
            })

            # Add ports
            ports = []
            if hasattr(spec, 'ports') and spec.ports:
                for port in spec.ports:
                    port_info = str(getattr(port, 'port', ''))
                    if hasattr(port, 'target_port') and port.target_port:
                        port_info += f":{port.target_port}"
                    if hasattr(port, 'protocol') and port.protocol:
                        port_info += f"/{port.protocol}"
                    ports.append(port_info)
            processed_item['port_text'] = ",".join(ports)
        else:
            processed_item['status'] = 'Unknown'

    def _add_workload_fields(self, processed_item: Dict[str, Any], workload: Any):
        """Add workload-specific fields (deployments, replicasets, etc.)"""
        status = workload.status if hasattr(workload, 'status') else None
        spec = workload.spec if hasattr(workload, 'spec') else None

        if status:
            replicas = getattr(status, 'replicas', 0) or 0
            ready_replicas = getattr(status, 'ready_replicas', 0) or 0
            available_replicas = getattr(status, 'available_replicas', ready_replicas) or ready_replicas

            processed_item.update({
                'ready': f"{available_replicas}/{replicas}",
                'status': 'Ready' if ready_replicas == replicas and replicas > 0 else 'Not Ready',
                'replicas_str': str(replicas)
            })
        else:
            processed_item['status'] = 'Unknown'

        # Add spec replicas if available
        if spec and hasattr(spec, 'replicas'):
            processed_item['replicas_str'] = str(getattr(spec, 'replicas', 0))

    def _add_node_fields(self, processed_item: Dict[str, Any], node: Any):
        """Add node-specific fields"""
        status = node.status if hasattr(node, 'status') else None

        # Node status
        node_status = 'Unknown'
        conditions_list = []
        if status and hasattr(status, 'conditions') and status.conditions:
            for condition in status.conditions:
                if getattr(condition, 'type', '') == 'Ready':
                    node_status = 'Ready' if getattr(condition, 'status', '') == 'True' else 'NotReady'

                # Format condition for display
                condition_display = f"{condition.type}={condition.status}"
                if condition.status != 'True' and hasattr(condition, 'reason') and condition.reason:
                    condition_display += f" ({condition.reason})"
                conditions_list.append(condition_display)

        # Get node roles
        roles = []
        if hasattr(node, 'metadata') and node.metadata and hasattr(node.metadata, 'labels') and node.metadata.labels:
            for label_key in node.metadata.labels:
                if 'node-role.kubernetes.io/' in label_key:
                    role = label_key.replace('node-role.kubernetes.io/', '')
                    if role:
                        roles.append(role)

        roles_text = ",".join(roles) if roles else "<none>"

        # Get Kubernetes version
        version = 'Unknown'
        if status and hasattr(status, 'node_info') and status.node_info:
            version = getattr(status.node_info, 'kubelet_version', 'Unknown')

        # Get capacity information for CPU, Memory, Disk
        cpu_capacity = ''
        memory_capacity = ''
        disk_capacity = ''
        if status and hasattr(status, 'capacity') and status.capacity:
            cpu_capacity = status.capacity.get('cpu', '')
            memory_raw = status.capacity.get('memory', '')
            disk_raw = status.capacity.get('ephemeral-storage', '')

            # Format memory capacity for display
            if memory_raw:
                try:
                    if memory_raw.endswith('Ki'):
                        memory_mb = int(memory_raw[:-2]) / 1024
                        memory_capacity = f"{memory_mb:.1f}GB"
                    else:
                        memory_capacity = memory_raw
                except Exception:
                    memory_capacity = memory_raw

            # Format disk capacity for display
            if disk_raw:
                try:
                    if disk_raw.endswith('Ki'):
                        disk_gb = int(disk_raw[:-2]) / 1024 / 1024
                        disk_capacity = f"{disk_gb:.1f}GB"
                    else:
                        disk_capacity = disk_raw
                except Exception:
                    disk_capacity = disk_raw

        # Get taints count
        taints_count = 0
        if hasattr(node, 'spec') and node.spec and hasattr(node.spec, 'taints') and node.spec.taints:
            taints_count = len(node.spec.taints)

        processed_item.update({
            'status': node_status,
            'roles': roles_text,
            'version': version,
            'conditions': ", ".join(conditions_list) if conditions_list else "Unknown",
            'cpu_capacity': cpu_capacity,
            'memory_capacity': memory_capacity,
            'disk_capacity': disk_capacity,
            'cpu_usage': 0.0,  # Default values for metrics (real metrics would require separate API calls)
            'memory_usage': 0.0,
            'disk_usage': 0.0,
            'taints': str(taints_count),
            'os': getattr(getattr(status, 'node_info', None), 'operating_system', 'Unknown') if status else 'Unknown',
            'kernel': getattr(getattr(status, 'node_info', None), 'kernel_version', 'Unknown') if status else 'Unknown'
        })

    def _add_configmap_fields(self, processed_item: Dict[str, Any], configmap: Any):
        """Add configmap-specific fields"""
        data = configmap.data if hasattr(configmap, 'data') else None
        data_count = len(data) if data else 0

        processed_item.update({
            'status': 'Active',
            'data_count': str(data_count)
        })

    def _add_secret_fields(self, processed_item: Dict[str, Any], secret: Any):
        """Add secret-specific fields"""
        data = secret.data if hasattr(secret, 'data') else None
        data_count = len(data) if data else 0
        secret_type = getattr(secret, 'type', 'Opaque') if hasattr(secret, 'type') else 'Opaque'

        processed_item.update({
            'status': 'Active',
            'type': secret_type,
            'data_count': str(data_count)
        })

    def _generate_cache_key(self) -> str:
        """Generate cache key for search results - FIXED to include cluster"""
        # FIXED: Include cluster information in search cache key
        try:
            kube_client = get_kubernetes_client()
            cluster_name = kube_client.current_cluster if kube_client else 'unknown-cluster'
        except Exception:
            cluster_name = 'unknown-cluster'

        namespace_key = f"ns_{self.config.namespace}" if self.config.namespace else "all_namespaces"
        return f"{cluster_name}_{self.config.resource_type}_{namespace_key}"


class ResourceLoadWorker(EnhancedBaseWorker):
    """High-performance worker for loading Kubernetes resources"""

    def __init__(self, config: ResourceConfig, loader_instance):
        super().__init__(f"resource_load_{config.resource_type}")
        self.config = config
        self.loader = loader_instance
        self._start_time = time.time()

    def execute(self) -> LoadResult:
        """Execute resource loading with performance optimizations and caching"""
        start_time = time.time()

        try:
            # Check cache first if caching is enabled
            cache_key = None
            cached_result = None
            
            if self.config.enable_caching:
                cache_key = self._generate_cache_key()
                cached_result = self.loader._cache.get_cached_resources(self.config.resource_type, cache_key)

                # Treat empty cached data as a cache miss for ALL resource types
                # Empty cache could be from transient errors (cluster disconnect, API timeout, etc.)
                # A legitimate "no resources" scenario is rare and worth re-verifying from API
                if cached_result is not None and cached_result:
                    # Cache hit with actual data - update stats and return
                    with self.loader._cache_lock:
                        self.loader._cache_stats[self.config.resource_type]['hits'] += 1

                    load_time = (time.time() - start_time) * 1000
                    logging.debug(f"Cache hit for {self.config.resource_type}: {len(cached_result)} items in {load_time:.1f}ms")

                    return LoadResult(
                        success=True,
                        resource_type=self.config.resource_type,
                        items=cached_result,
                        total_count=len(cached_result),
                        load_time_ms=load_time,
                        from_cache=True
                    )
                else:
                    # Cache miss or empty cache - update stats and refetch
                    with self.loader._cache_lock:
                        self.loader._cache_stats[self.config.resource_type]['misses'] += 1
                    # Clear empty cache entries to prevent stale empty results
                    if cached_result is not None and not cached_result:
                        logging.debug(f"Clearing empty cache entry for {self.config.resource_type}")
                        self.loader._cache.clear_resource_cache(self.config.resource_type, cache_key)

            # Load from Kubernetes API with optimizations
            items = self._load_from_api()

            if self.is_cancelled():
                return LoadResult(
                    success=False,
                    resource_type=self.config.resource_type,
                    error_message="Operation cancelled"
                )

            # Process results with chunking for heavy data
            processed_items = self._process_items_chunked(items) if self.config.enable_chunking else self._process_items(items)

            # Cache the processed results if caching is enabled
            if self.config.enable_caching and cache_key and processed_items:
                try:
                    self.loader._cache.cache_resources(self.config.resource_type, cache_key, processed_items)
                    with self.loader._cache_lock:
                        self.loader._cache_stats[self.config.resource_type]['size'] = len(processed_items)
                    logging.debug(f"Cached {len(processed_items)} {self.config.resource_type} items with key: {cache_key}")
                except Exception as cache_error:
                    logging.debug(f"Failed to cache {self.config.resource_type}: {cache_error}")

            load_time = (time.time() - start_time) * 1000
            logging.debug(f"Unified Resource Loader: Loaded {len(processed_items)} {self.config.resource_type} in {load_time:.1f}ms")

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
                # For timeout-prone resources, return cached data if available
                if self.config.enable_caching and cache_key:
                    # Try to get any cached data, even if expired, as fallback
                    try:
                        fallback_data = self.loader._cache.get_cached_resources(self.config.resource_type, cache_key)
                        if fallback_data:
                            logging.info(f"Using cached fallback data for timed-out {self.config.resource_type}: {len(fallback_data)} items")
                            return LoadResult(
                                success=True,
                                resource_type=self.config.resource_type,
                                items=fallback_data,
                                total_count=len(fallback_data),
                                load_time_ms=(time.time() - start_time) * 1000,
                                from_cache=True,
                                metadata={'fallback': True, 'reason': 'timeout'}
                            )
                    except Exception as cache_error:
                        logging.debug(f"Cache fallback failed: {cache_error}")

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


    def _load_from_api(self) -> List[Any]:
        """Load resources from Kubernetes API with performance optimizations"""
        kube_client = get_kubernetes_client()

        # Get the appropriate API client
        api_client = self._get_api_client(kube_client)

        # Build method parameters for optimal performance and heavy data handling
        kwargs = {
            'timeout_seconds': self.config.timeout_seconds,  # Use config timeout
            '_request_timeout': self.config.timeout_seconds + 10  # Request timeout with buffer
        }

        # For heavy data scenarios, add pagination support
        if self.config.enable_pagination and self.config.resource_type == 'nodes':
            kwargs['limit'] = min(self.config.chunk_size, 1000)  # Limit for heavy data

        # Handle cluster scoped vs namespaced resources
        # Use the global cluster_scoped_resources set instead of redefining

        is_cluster_scoped = self.config.resource_type in cluster_scoped_resources

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

        # Optimize field selection for better performance with heavy data
        if self.config.resource_type in ['pods', 'nodes', 'services']:
            # Only get essential fields to reduce network overhead for heavy data
            field_selector = self._get_field_selector()
            if field_selector:
                kwargs['field_selector'] = field_selector

        # For nodes, further optimize by reducing unnecessary data
        if self.config.resource_type == 'nodes':
            # Skip some heavy fields that aren't displayed in UI
            logging.debug(f"Unified Resource Loader: Optimizing node API call for heavy data - using limit: {kwargs.get('limit', 'no limit')}")

        # Execute API call with retry logic
        response = self._execute_with_retry(api_method, **kwargs)

        return response.items if hasattr(response, 'items') else []

    def _execute_with_retry(self, api_method, max_retries=3, **kwargs):
        """Execute API call with exponential backoff retry logic"""
        import random

        last_exception = None

        for attempt in range(max_retries):
            try:
                response = api_method(**kwargs)
                if attempt > 0:
                    logging.info(f"API call succeeded on attempt {attempt + 1}")
                return response

            except Exception as e:
                last_exception = e
                error_str = str(e).lower()

                # Don't retry on certain errors
                if any(err in error_str for err in ['unauthorized', 'forbidden', 'not found']):
                    logging.debug(f"Non-retryable error, failing immediately: {e}")
                    raise

                # Calculate exponential backoff with jitter
                if attempt < max_retries - 1:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"API call failed (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s: {e}")
                    time.sleep(delay)

                    # Check if cancelled during delay
                    if self.is_cancelled():
                        raise Exception("Operation cancelled during retry")
                else:
                    logging.error(f"API call failed after {max_retries} attempts: {e}")

        # Re-raise the last exception if all retries failed
        raise last_exception

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
                logging.debug(f"Loaded {len(all_items)} {self.config.resource_type} from {len(selected_namespaces)} namespaces")
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
            'configmaps': kube_client.v1,
            'secrets': kube_client.v1,
            'namespaces': kube_client.v1,
            'events': kube_client.v1,
            'endpoints': kube_client.v1,
            'persistentvolumes': kube_client.v1,
            'persistentvolumeclaims': kube_client.v1,
            'replicationcontrollers': kube_client.v1,
            'limitranges': kube_client.v1,
            'resourcequotas': kube_client.v1,
            'serviceaccounts': kube_client.v1,

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

            # Autoscaling v2 resources
            'horizontalpodautoscalers': kube_client.autoscaling_v2,

            # Policy v1 resources
            'poddisruptionbudgets': kube_client.policy_v1,

            # Scheduling v1 resources
            'priorityclasses': kube_client.scheduling_v1,

            # Node v1 resources
            'runtimeclasses': kube_client.node_v1,

            # Admission registration v1 resources
            'mutatingwebhookconfigurations': kube_client.admissionregistration_v1,
            'validatingwebhookconfigurations': kube_client.admissionregistration_v1,

            # Coordination v1 resources
            'leases': kube_client.coordination_v1,

            # Custom Resources
            'customresourcedefinitions': kube_client.apiextensions_v1,
        }

        return api_mapping.get(self.config.resource_type, kube_client.v1)

    def _get_field_selector(self) -> str:
        """Get optimized field selector for common resources"""
        if self.config.resource_type == 'pods':
            # Show all pods including Succeeded and Failed for better visibility
            # Only filter out pods that are truly not useful
            return ''  # No filtering - show all pods regardless of status
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

        # Use smaller batches for stability
        optimal_batch_size = max(25, batch_size // 2)

        # Process batches sequentially to avoid per-call executor overhead
        # This is more efficient for typical batch sizes and avoids thread pool churn
        for i in range(0, len(items), optimal_batch_size):
            if self.is_cancelled():
                break

            batch = items[i:i + optimal_batch_size]
            try:
                batch_result = self._process_batch(batch)
                processed_items.extend(batch_result)
            except Exception as e:
                logging.debug(f"Error in batch processing: {e}")
                continue

        return processed_items

    def _process_items_chunked(self, raw_items: List[Any]) -> List[Dict[str, Any]]:
        """Process raw Kubernetes objects in chunks for heavy data scenarios - OPTIMIZED FOR NODES"""
        if not raw_items:
            return []

        processed_items = []
        chunk_size = self.config.chunk_size
        total_items = len(raw_items)

        logging.debug(f"Unified Resource Loader: Processing {total_items} {self.config.resource_type} in chunks of {chunk_size}")

        # PERFORMANCE OPTIMIZATION: For nodes, load metrics in background (non-blocking)
        all_node_metrics = {}
        if self.config.resource_type == 'nodes':
            logging.debug(f"Skipping synchronous metrics loading for {total_items} nodes - will load async")
            # Skip metrics loading to avoid 3+ minute delay blocking UI
            # Metrics will be loaded separately and updated in UI when available

        # Process chunks with pre-loaded metrics
        for start_idx in range(0, total_items, chunk_size):
            if self.is_cancelled():
                break

            end_idx = min(start_idx + chunk_size, total_items)
            chunk = raw_items[start_idx:end_idx]

            logging.debug(f"Unified Resource Loader: Processing chunk {start_idx}-{end_idx} ({len(chunk)} items)")

            # Process chunk
            chunk_start_time = time.time()
            for item in chunk:
                if self.is_cancelled():
                    break

                try:
                    # Pass pre-loaded metrics for nodes
                    if self.config.resource_type == 'nodes':
                        node_name = getattr(getattr(item, 'metadata', None), 'name', None)
                        node_metrics = all_node_metrics.get(node_name) if node_name else None
                        processed_item = self._process_single_item(item, preloaded_metrics=node_metrics)
                    else:
                        processed_item = self._process_single_item(item)

                    if processed_item:  # Only add valid items
                        processed_items.append(processed_item)
                    else:
                        logging.warning(f"❌ [SKIPPED] Processed item is None/empty for {self.config.resource_type} {getattr(getattr(item, 'metadata', None), 'name', 'unknown')}")
                except Exception as e:
                    item_name = getattr(getattr(item, 'metadata', None), 'name', 'unknown')
                    logging.warning(f"Error processing {self.config.resource_type} {item_name}: {e}")
                    continue

            chunk_time = (time.time() - chunk_start_time) * 1000
            logging.debug(f"Unified Resource Loader: Processed chunk {start_idx}-{end_idx} in {chunk_time:.1f}ms")

            # Yield control to prevent UI blocking
            time.sleep(0.001)  # 1ms pause between chunks

        logging.debug(f"Unified Resource Loader: Chunked processing completed - {len(processed_items)} items processed")
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

    def _process_single_item(self, item: Any, preloaded_metrics: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Process a single Kubernetes resource item"""
        try:
            # Extract common fields efficiently
            metadata = item.metadata
            if not metadata:
                logging.error(f"❌ [PROCESS] Item has no metadata: {item}")
                return None

            name = metadata.name
            if not name:
                logging.error(f"❌ [PROCESS] Item has no name in metadata: {metadata}")
                return None

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
            ResourceLoadWorker._add_resource_specific_fields(processed_item, item, self.config.resource_type, preloaded_metrics)

            # Add raw_data for UI components that need detailed information
            # Serialize the raw Kubernetes object for components that need it
            try:
                kube_client = get_kubernetes_client()
                if hasattr(kube_client, 'v1') and hasattr(kube_client.v1, 'api_client'):
                    processed_item['raw_data'] = kube_client.v1.api_client.sanitize_for_serialization(item)
                else:
                    # No fallback - set empty raw_data to avoid dummy data
                    processed_item['raw_data'] = {}
            except Exception as e:
                logging.debug(f"Error serializing raw data: {e}")
                processed_item['raw_data'] = {}

            return processed_item

        except Exception as e:
            logging.error(f"❌ [PROCESS ERROR] Error processing single {self.config.resource_type} item: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return None

    @staticmethod
    def _add_resource_specific_fields(processed_item: Dict[str, Any], item: Any, resource_type: str, preloaded_metrics: Optional[Dict[str, Any]] = None):
        """Add resource-specific fields efficiently"""
        if resource_type == 'pods':
            ResourceLoadWorker._add_pod_fields(processed_item, item)
        elif resource_type == 'nodes':
            logging.debug(f"Unified Resource Loader: Adding node-specific fields for {processed_item.get('name', 'unknown')}")
            ResourceLoadWorker._add_node_fields(processed_item, item, preloaded_metrics)
        elif resource_type == 'services':
            ResourceLoadWorker._add_service_fields(processed_item, item)
        elif resource_type == 'deployments':
            ResourceLoadWorker._add_deployment_fields(processed_item, item)
        elif resource_type == 'replicasets':
            ResourceLoadWorker._add_replicaset_fields(processed_item, item)
        elif resource_type == 'statefulsets':
            ResourceLoadWorker._add_statefulset_fields(processed_item, item)
        elif resource_type == 'daemonsets':
            ResourceLoadWorker._add_daemonset_fields(processed_item, item)
        elif resource_type == 'replicationcontrollers':
            ResourceLoadWorker._add_replicationcontroller_fields(processed_item, item)
        elif resource_type == 'jobs':
            ResourceLoadWorker._add_job_fields(processed_item, item)
        elif resource_type == 'cronjobs':
            ResourceLoadWorker._add_cronjob_fields(processed_item, item)
        elif resource_type == 'configmaps':
            ResourceLoadWorker._add_configmap_fields(processed_item, item)
        elif resource_type == 'secrets':
            ResourceLoadWorker._add_secret_fields(processed_item, item)
        elif resource_type == 'resourcequotas':
            ResourceLoadWorker._add_resourcequota_fields(processed_item, item)
        elif resource_type == 'limitranges':
            ResourceLoadWorker._add_limitrange_fields(processed_item, item)
        elif resource_type == 'horizontalpodautoscalers':
            ResourceLoadWorker._add_hpa_fields(processed_item, item)
        elif resource_type == 'poddisruptionbudgets':
            ResourceLoadWorker._add_pdb_fields(processed_item, item)
        elif resource_type == 'priorityclasses':
            ResourceLoadWorker._add_priorityclass_fields(processed_item, item)
        elif resource_type == 'runtimeclasses':
            ResourceLoadWorker._add_runtimeclass_fields(processed_item, item)
        elif resource_type == 'leases':
            ResourceLoadWorker._add_lease_fields(processed_item, item)
        elif resource_type == 'mutatingwebhookconfigurations':
            ResourceLoadWorker._add_mutatingwebhook_fields(processed_item, item)
        elif resource_type == 'validatingwebhookconfigurations':
            ResourceLoadWorker._add_validatingwebhook_fields(processed_item, item)
        elif resource_type == 'serviceaccounts':
            ResourceLoadWorker._add_serviceaccount_fields(processed_item, item)
        elif resource_type == 'endpoints':
            ResourceLoadWorker._add_endpoints_fields(processed_item, item)
        elif resource_type in ['roles', 'clusterroles']:
            ResourceLoadWorker._add_role_fields(processed_item, item)
        elif resource_type in ['rolebindings', 'clusterrolebindings']:
            ResourceLoadWorker._add_rolebinding_fields(processed_item, item)
        elif resource_type == 'customresourcedefinitions':
            ResourceLoadWorker._add_crd_fields(processed_item, item)

    @staticmethod
    def _add_pod_fields(processed_item: Dict[str, Any], pod: Any):
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
            'ready': ResourceLoadWorker._get_pod_ready_status(status),
            'restarts': ResourceLoadWorker._get_pod_restart_count(status),
            'node_name': spec.node_name if spec else None,
            'host_ip': status.host_ip if status else None,
            'pod_ip': status.pod_ip if status else None,
            'containers': len(spec.containers) if spec and spec.containers else 0,
            'init_containers': len(spec.init_containers) if spec and spec.init_containers else 0,
        })

    @staticmethod
    def _add_node_fields(processed_item: Dict[str, Any], node: Any, preloaded_metrics: Optional[Dict[str, Any]] = None):
        """Add node-specific fields efficiently - optimized for heavy data"""
        status = node.status

        # Quick exit for invalid nodes
        if not status:
            processed_item.update({
                'status': 'Unknown',
                'conditions': 'Unknown',
                'roles': ['<none>'],
                'version': 'Unknown',
                'os': 'Unknown',
                'kernel': 'Unknown',
                'taints': '0',
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'disk_usage': 0.0,
                'cpu_capacity': '',
                'memory_capacity': '',
                'disk_capacity': ''
            })
            return

        # Process node conditions using helper method from the loader class
        node_status, conditions_text = HighPerformanceResourceLoader._process_node_conditions(status.conditions if status else None)

        # Extract node roles using helper method from the loader class
        roles = HighPerformanceResourceLoader._extract_node_roles(node.metadata.labels if node.metadata else None)

        # Get taints count
        taints_count = 0
        if node.spec and node.spec.taints:
            taints_count = len(node.spec.taints)

        # Format capacity information using helper method from the loader class
        memory_capacity = ''
        disk_capacity = ''
        if status and status.capacity:
            memory_capacity = HighPerformanceResourceLoader._format_capacity(status.capacity.get('memory', ''))
            disk_capacity = HighPerformanceResourceLoader._format_capacity(status.capacity.get('ephemeral-storage', ''))

        # Don't simulate disk usage - leave as None to be filled by real metrics
        estimated_disk_usage = None

        processed_item.update({
            'status': node_status,
            'conditions': conditions_text,
            'roles': roles,
            'version': status.node_info.kubelet_version if status and status.node_info else 'Unknown',
            'os': status.node_info.operating_system if status and status.node_info else 'Unknown',
            'kernel': status.node_info.kernel_version if status and status.node_info else 'Unknown',
            'taints': str(taints_count),
            'cpu_usage': None,  # Will be filled by metrics if available
            'memory_usage': None,  # Will be filled by metrics if available
            'disk_usage': estimated_disk_usage,  # Estimated usage, will be replaced by real metrics if available
        })

        # Add capacity information
        if status and status.capacity:
            processed_item.update({
                'cpu_capacity': status.capacity.get('cpu', ''),
                'memory_capacity': memory_capacity,
                'disk_capacity': disk_capacity,
                'pods_capacity': status.capacity.get('pods', ''),
            })

        # Use preloaded metrics if available, otherwise set defaults
        cpu_usage = 0.0
        memory_usage = 0.0
        disk_usage = 0.0

        if preloaded_metrics:
            cpu_usage = preloaded_metrics.get("cpu", {}).get("usage", 0.0)
            memory_usage = preloaded_metrics.get("memory", {}).get("usage", 0.0)
            disk_usage_val = preloaded_metrics.get("disk", {}).get("usage")
            disk_usage = disk_usage_val if disk_usage_val is not None else 0.0

            logging.debug(f"Using preloaded metrics for {processed_item.get('name', 'unknown')}: "
                        f"CPU {cpu_usage:.1f}%, Memory {memory_usage:.1f}%, Disk {disk_usage:.1f}%")

        processed_item.update({
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage
        })

    @staticmethod
    def _add_service_fields(processed_item: Dict[str, Any], service: Any):
        """Add service-specific fields efficiently"""
        spec = service.spec
        status = service.status

        processed_item.update({
            'type': spec.type if spec else 'Unknown',
            'cluster_ip': spec.cluster_ip if spec else None,
            'external_ip': ResourceLoadWorker._get_service_external_ip(spec, status),
            'ports': len(spec.ports) if spec and spec.ports else 0,
        })

    @staticmethod
    def _add_deployment_fields(processed_item: Dict[str, Any], item: Any):
        """Add Deployment-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            available = getattr(status, 'available_replicas', 0) or 0
            replicas = getattr(spec, 'replicas', 0) or 0
            pods = f"{available}/{replicas}"

            # Get conditions where status == True
            conditions_list = getattr(status, 'conditions', []) or []
            active_conditions = []
            for cond in conditions_list:
                cond_status = str(getattr(cond, 'status', ''))
                if cond_status == 'True':
                    active_conditions.append(getattr(cond, 'type', ''))
            conditions_str = ' '.join(active_conditions)

            processed_item.update({
                'pods': pods,
                'replicas': str(replicas),
                'conditions': conditions_str,
            })
        except Exception as e:
            logging.debug(f"Error processing Deployment fields: {e}")

    @staticmethod
    def _add_replicaset_fields(processed_item: Dict[str, Any], item: Any):
        """Add ReplicaSet-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            desired = getattr(spec, 'replicas', 0) or 0
            current = getattr(status, 'replicas', 0) or 0
            ready = getattr(status, 'ready_replicas', 0) or 0

            processed_item.update({
                'desired': str(desired),
                'current': str(current),
                'ready': str(ready),
            })
        except Exception as e:
            logging.debug(f"Error processing ReplicaSet fields: {e}")

    @staticmethod
    def _add_statefulset_fields(processed_item: Dict[str, Any], item: Any):
        """Add StatefulSet-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            current = getattr(status, 'current_replicas', 0) or 0
            replicas = getattr(spec, 'replicas', 0) or 0
            pods = f"{current}/{replicas}"

            processed_item.update({
                'pods': pods,
                'replicas': str(replicas),
            })
        except Exception as e:
            logging.debug(f"Error processing StatefulSet fields: {e}")

    @staticmethod
    def _add_daemonset_fields(processed_item: Dict[str, Any], item: Any):
        """Add DaemonSet-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            current = getattr(status, 'current_number_scheduled', 0) or 0
            desired = getattr(status, 'desired_number_scheduled', 0) or 0
            pods = f"{current}/{desired}"

            # node selector
            template = getattr(spec, 'template', None)
            template_spec = getattr(template, 'spec', None) if template else None
            node_selector_dict = getattr(template_spec, 'node_selector', {}) or {}
            node_selector = ", ".join([f"{k}={v}" for k, v in node_selector_dict.items()]) if node_selector_dict else '<none>'

            processed_item.update({
                'pods': pods,
                'node_selector': node_selector,
            })
        except Exception as e:
            logging.debug(f"Error processing DaemonSet fields: {e}")

    def _format_age_fast(self, creation_timestamp) -> str:
        """Fast age calculation with comprehensive timestamp handling"""
        return format_age(creation_timestamp)

    @staticmethod
    def _get_pod_ready_status(status) -> str:
        """Get pod ready status efficiently"""
        if not status or not status.container_statuses:
            return '0/0'

        ready_count = sum(1 for cs in status.container_statuses if cs.ready)
        total_count = len(status.container_statuses)

        return f"{ready_count}/{total_count}"

    @staticmethod
    def _get_pod_restart_count(status) -> int:
        """Get pod restart count efficiently"""
        if not status or not status.container_statuses:
            return 0

        return sum(cs.restart_count for cs in status.container_statuses if cs.restart_count)

    @staticmethod
    def _get_service_external_ip(spec, status) -> Optional[str]:
        """Get service external IP efficiently"""
        external_ips = []

        # Check for explicit external IPs
        if spec and spec.external_i_ps:
            external_ips.extend(spec.external_i_ps)

        # Check for LoadBalancer ingress IPs and hostnames
        if spec and spec.type == 'LoadBalancer' and status and status.load_balancer:
            if status.load_balancer.ingress:
                for ing in status.load_balancer.ingress:
                    if ing.ip:
                        external_ips.append(ing.ip)
                    elif ing.hostname:
                        external_ips.append(ing.hostname)

        # Check for NodePort external access
        if spec and spec.type == 'NodePort':
            # For NodePort services, indicate they are externally accessible
            # We could show actual node IPs but that would require additional API calls
            external_ips.append("<NodePort>")

        # Check for ExternalName services
        if spec and spec.type == 'ExternalName' and spec.external_name:
            external_ips.append(spec.external_name)

        return ', '.join(external_ips) if external_ips else None

    @staticmethod
    def _add_replicationcontroller_fields(processed_item: Dict[str, Any], item: Any):
        """Add ReplicationController-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            replicas = getattr(spec, 'replicas', 0) if spec else 0
            ready_replicas = getattr(status, 'replicas', 0) if status else 0

            processed_item.update({
                'replicas': ready_replicas,
                'desired_replicas': replicas,
                'selector': ', '.join([f"{k}={v}" for k, v in (spec.selector or {}).items()]) if spec and spec.selector else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing ReplicationController fields: {e}")

    @staticmethod
    def _add_job_fields(processed_item: Dict[str, Any], item: Any):
        """Add Job-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            succeeded = getattr(status, 'succeeded', 0) or 0
            # parallelism/completions count
            completions = getattr(spec, 'completions', 1) or 1
            completions_str = f"{succeeded}/{completions}"

            # Extract active conditions
            conditions_list = getattr(status, 'conditions', []) or []
            active_conditions = []
            for cond in conditions_list:
                cond_status = str(getattr(cond, 'status', ''))
                if cond_status == 'True':
                    active_conditions.append(getattr(cond, 'type', ''))
            conditions_str = ' '.join(active_conditions)

            processed_item.update({
                'completions': completions_str,
                'conditions': conditions_str,
            })
        except Exception as e:
            logging.debug(f"Error processing Job fields: {e}")

    @staticmethod
    def _add_cronjob_fields(processed_item: Dict[str, Any], item: Any):
        """Add CronJob-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            schedule = getattr(spec, 'schedule', '') or ''
            suspend = str(getattr(spec, 'suspend', False) or False)
            active_list = getattr(status, 'active', []) or []
            active = str(len(active_list))

            # Format last schedule time
            last_schedule = 'Never'
            last_schedule_time = getattr(status, 'last_schedule_time', None)
            if last_schedule_time:
                from Utils.data_formatters import format_age
                last_schedule = f"{format_age(last_schedule_time)} ago"

            processed_item.update({
                'schedule': schedule,
                'suspend': suspend,
                'active': active,
                'last_schedule': last_schedule,
            })
        except Exception as e:
            logging.debug(f"Error processing CronJob fields: {e}")

    @staticmethod
    def _add_configmap_fields(processed_item: Dict[str, Any], item: Any):
        """Add ConfigMap-specific fields"""
        try:
            data = item.data or {}
            processed_item.update({
                'keys': ', '.join(data.keys()) if data else '<none>',
                'data_count': len(data),
            })
        except Exception as e:
            logging.debug(f"Error processing ConfigMap fields: {e}")

    @staticmethod
    def _add_secret_fields(processed_item: Dict[str, Any], item: Any):
        """Add Secret-specific fields"""
        try:
            data = item.data or {}
            secret_type = getattr(item, 'type', 'Opaque')
            processed_item.update({
                'type': secret_type,
                'keys': ', '.join(data.keys()) if data else '<none>',
                'data_count': len(data),
            })
        except Exception as e:
            logging.debug(f"Error processing Secret fields: {e}")

    @staticmethod
    def _add_resourcequota_fields(processed_item: Dict[str, Any], item: Any):
        """Add ResourceQuota-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            # Get hard limits from spec
            hard_limits = spec.hard if spec and hasattr(spec, 'hard') else {}
            used_resources = status.used if status and hasattr(status, 'used') else {}

            processed_item.update({
                'hard_limits': len(hard_limits),
                'used_resources': len(used_resources),
                'resources': ', '.join(hard_limits.keys()) if hard_limits else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing ResourceQuota fields: {e}")

    @staticmethod
    def _add_limitrange_fields(processed_item: Dict[str, Any], item: Any):
        """Add LimitRange-specific fields"""
        try:
            spec = item.spec
            limits = spec.limits if spec and hasattr(spec, 'limits') else []
            processed_item.update({
                'limits_count': len(limits),
                'types': ', '.join(set(limit.type for limit in limits if hasattr(limit, 'type'))) if limits else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing LimitRange fields: {e}")

    @staticmethod
    def _add_hpa_fields(processed_item: Dict[str, Any], item: Any):
        """Add HorizontalPodAutoscaler-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            min_replicas = getattr(spec, 'min_replicas', 1) if spec else 1
            max_replicas = getattr(spec, 'max_replicas', 1) if spec else 1
            current_replicas = getattr(status, 'current_replicas', 0) if status else 0

            processed_item.update({
                'min_replicas': min_replicas,
                'max_replicas': max_replicas,
                'current_replicas': current_replicas,
                'target_ref': f"{spec.scale_target_ref.kind}/{spec.scale_target_ref.name}" if spec and hasattr(spec, 'scale_target_ref') else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing HPA fields: {e}")

    @staticmethod
    def _add_pdb_fields(processed_item: Dict[str, Any], item: Any):
        """Add PodDisruptionBudget-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            min_available = getattr(spec, 'min_available', None) if spec else None
            max_unavailable = getattr(spec, 'max_unavailable', None) if spec else None

            processed_item.update({
                'min_available': str(min_available) if min_available is not None else '<none>',
                'max_unavailable': str(max_unavailable) if max_unavailable is not None else '<none>',
                'current_healthy': getattr(status, 'current_healthy', 0) if status else 0,
                'desired_healthy': getattr(status, 'desired_healthy', 0) if status else 0,
            })
        except Exception as e:
            logging.debug(f"Error processing PDB fields: {e}")

    @staticmethod
    def _add_priorityclass_fields(processed_item: Dict[str, Any], item: Any):
        """Add PriorityClass-specific fields"""
        try:
            value = getattr(item, 'value', 0)
            global_default = getattr(item, 'global_default', False)
            description = getattr(item, 'description', '')

            processed_item.update({
                'value': value,
                'global_default': global_default,
                'description': description or '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing PriorityClass fields: {e}")

    @staticmethod
    def _add_runtimeclass_fields(processed_item: Dict[str, Any], item: Any):
        """Add RuntimeClass-specific fields"""
        try:
            handler = getattr(item, 'handler', '')
            processed_item.update({
                'handler': handler or '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing RuntimeClass fields: {e}")

    @staticmethod
    def _add_lease_fields(processed_item: Dict[str, Any], item: Any):
        """Add Lease-specific fields"""
        try:
            spec = item.spec
            holder_identity = getattr(spec, 'holder_identity', '') if spec else ''
            lease_duration = getattr(spec, 'lease_duration_seconds', 0) if spec else 0

            processed_item.update({
                'holder_identity': holder_identity or '<none>',
                'holder': holder_identity or '<none>',  # For compatibility with LeasesPage
                'lease_duration': f"{lease_duration}s" if lease_duration else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing Lease fields: {e}")

    @staticmethod
    def _add_mutatingwebhook_fields(processed_item: Dict[str, Any], item: Any):
        """Add MutatingWebhookConfiguration-specific fields"""
        try:
            webhooks = getattr(item, 'webhooks', [])
            processed_item.update({
                'webhooks_count': len(webhooks),
                'webhooks': ', '.join([w.name for w in webhooks if hasattr(w, 'name')]) if webhooks else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing MutatingWebhookConfiguration fields: {e}")

    @staticmethod
    def _add_validatingwebhook_fields(processed_item: Dict[str, Any], item: Any):
        """Add ValidatingWebhookConfiguration-specific fields"""
        try:
            webhooks = getattr(item, 'webhooks', [])
            processed_item.update({
                'webhooks_count': len(webhooks),
                'webhooks': ', '.join([w.name for w in webhooks if hasattr(w, 'name')]) if webhooks else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing ValidatingWebhookConfiguration fields: {e}")

    @staticmethod
    def _add_serviceaccount_fields(processed_item: Dict[str, Any], item: Any):
        """Add ServiceAccount-specific fields"""
        try:
            secrets = getattr(item, 'secrets', [])
            image_pull_secrets = getattr(item, 'image_pull_secrets', [])

            processed_item.update({
                'secrets_count': len(secrets),
                'image_pull_secrets_count': len(image_pull_secrets),
                'automount_token': getattr(item, 'automount_service_account_token', True),
            })
        except Exception as e:
            logging.debug(f"Error processing ServiceAccount fields: {e}")

    @staticmethod
    def _add_endpoints_fields(processed_item: Dict[str, Any], item: Any):
        """Add Endpoints-specific fields"""
        try:
            subsets = getattr(item, 'subsets', [])

            # Get addresses and ports more comprehensively
            all_addresses = []
            all_ports = []

            for subset in subsets:
                addresses = getattr(subset, 'addresses', []) or []
                ports = getattr(subset, 'ports', []) or []

                # Collect IP addresses
                for addr in addresses:
                    if hasattr(addr, 'ip') and addr.ip:
                        all_addresses.append(addr.ip)

                # Collect port information
                for port in ports:
                    port_info = f"{getattr(port, 'port', 'unknown')}"
                    if hasattr(port, 'protocol'):
                        port_info += f"/{port.protocol}"
                    if hasattr(port, 'name') and port.name:
                        port_info += f" ({port.name})"
                    all_ports.append(port_info)

            processed_item.update({
                'endpoints_count': len(all_addresses),
                'endpoints': ', '.join(all_addresses[:3]) + ('...' if len(all_addresses) > 3 else '') if all_addresses else '<none>',
                'ports': ', '.join(all_ports) if all_ports else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing Endpoints fields: {e}")

    @staticmethod
    def _add_role_fields(processed_item: Dict[str, Any], item: Any):
        """Add Role/ClusterRole-specific fields"""
        try:
            rules = getattr(item, 'rules', [])
            processed_item.update({
                'rules_count': len(rules),
            })
        except Exception as e:
            logging.debug(f"Error processing Role fields: {e}")

    @staticmethod
    def _add_rolebinding_fields(processed_item: Dict[str, Any], item: Any):
        """Add RoleBinding/ClusterRoleBinding-specific fields"""
        try:
            subjects = getattr(item, 'subjects', [])
            role_ref = getattr(item, 'role_ref', None)

            processed_item.update({
                'subjects_count': len(subjects),
                'role_ref': f"{role_ref.kind}/{role_ref.name}" if role_ref and hasattr(role_ref, 'kind') and hasattr(role_ref, 'name') else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing RoleBinding fields: {e}")

    @staticmethod
    def _add_crd_fields(processed_item: Dict[str, Any], item: Any):
        """Add CustomResourceDefinition-specific fields"""
        try:
            spec = item.spec
            status = item.status if hasattr(item, 'status') else None

            group = getattr(spec, 'group', '') if spec else ''
            scope = getattr(spec, 'scope', 'Namespaced') if spec else 'Namespaced'

            processed_item.update({
                'group': group or '<none>',
                'scope': scope,
                'established': 'True' if status and hasattr(status, 'conditions') and any(c.type == 'Established' and c.status == 'True' for c in status.conditions) else 'False',
            })
        except Exception as e:
            logging.debug(f"Error processing CRD fields: {e}")

    def _generate_cache_key(self) -> str:
        """Generate cache key for this resource loading operation - FIXED to include cluster"""
        # FIXED: Include cluster information in cache key to prevent cross-cluster data mixing
        try:
            kube_client = get_kubernetes_client()
            cluster_name = kube_client.current_cluster if kube_client else 'unknown-cluster'
        except Exception:
            cluster_name = 'unknown-cluster'

        key_parts = [
            cluster_name,  # FIXED: Add cluster name to prevent cross-cluster cache pollution
            self.config.resource_type,
            f"ns_{self.config.namespace}" if self.config.namespace else 'all-namespaces',  # FIXED: Add ns_ prefix
            str(self.config.batch_size),
        ]
        return ':'.join(key_parts)


    def _handle_timeout_fallback(self) -> Optional[LoadResult]:
        """Handle timeout fallback for timeout-prone resources"""
        # Apply fallback to ALL resources for Docker Desktop Kubernetes
        # Docker Desktop often has slow API responses

        try:
            # No cache fallback available, return empty result
            logging.info(f"No fallback available for {self.config.resource_type}")
            return LoadResult(
                success=False,
                resource_type=self.config.resource_type,
                items=[],
                total_count=0,
                from_cache=False,
                load_time_ms=0,
                error_message="Timeout occurred and no fallback available"
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
                error_message="Timeout - returning empty result to avoid blocking UI"
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

        # Request deduplication to prevent duplicate API calls
        self._pending_operations: Dict[str, str] = {}  # operation_key -> operation_id
        self._operation_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._dedup_lock = threading.RLock()

        # Performance monitoring
        self._load_stats = defaultdict(list)
        self._stats_lock = threading.RLock()

        # Caching system integration
        self._cache = get_unified_cache()
        self._cache_lock = threading.RLock()
        self._cache_stats = defaultdict(lambda: {'hits': 0, 'misses': 0, 'size': 0})
        
        # Memory pressure monitoring for cache management
        self._memory_pressure_threshold = 800  # MB
        self._last_cache_cleanup = time.time()
        self._cache_cleanup_interval = 300  # 5 minutes

        # Resource Watch Managers — event-driven sync instead of periodic LIST
        # Keyed by (resource_type, namespace) tuple
        self._resource_watches: Dict[tuple, ResourceWatchManager] = {}
        self._watches_lock = threading.Lock()

        # Initialize default configurations for all resource types
        self._initialize_default_configs()

        # Setup memory monitoring timer
        self._setup_memory_monitoring()

        logging.info("Unified Resource Loader initialized")

    @pyqtSlot()
    def _setup_memory_monitoring(self):
        """Setup memory monitoring timer"""
        try:
            app = QApplication.instance()
            if not app or self.thread() != app.thread():
                # Defer to main thread if called from worker thread or no QApplication
                if app:
                    QMetaObject.invokeMethod(self, "_setup_memory_monitoring", Qt.ConnectionType.QueuedConnection)
                return

            self._memory_timer = QTimer()
            self._memory_timer.timeout.connect(self._check_memory_usage)
            self._memory_timer.start(60000)  # Check every minute
        except Exception as e:
            logging.debug(f"Could not setup memory monitoring timer: {e}")
            # Continue without timer - not critical for functionality

    def _check_memory_usage(self):
        """Check and log memory usage, cleanup if necessary"""
        try:

            # Get object count
            object_count = len(gc.get_objects())

            # Log warning if object count is high (increased threshold)
            if object_count > 150000:
                logging.warning(f"High object count detected: {object_count} objects in memory")

                # Force cleanup if very high (increased threshold)
                if object_count > 200000:
                    logging.info("Forcing memory cleanup due to high object count")
                    self._force_memory_cleanup()

            # Check memory usage and manage cache accordingly
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                # Memory pressure cache management
                if memory_mb > self._memory_pressure_threshold:
                    logging.warning(f"Memory pressure detected: {memory_mb:.1f} MB - clearing old cache entries")
                    self._clear_old_cache_entries(force=True)
                elif time.time() - self._last_cache_cleanup > self._cache_cleanup_interval:
                    # Regular cache cleanup
                    self._clear_old_cache_entries(force=False)
                
                if memory_mb > 800:  # Log if over 800MB (increased threshold)
                    logging.info(f"Memory usage: {memory_mb:.1f} MB, {object_count} objects")
            except ImportError:
                # Fallback cache cleanup without memory monitoring
                if time.time() - self._last_cache_cleanup > self._cache_cleanup_interval:
                    self._clear_old_cache_entries(force=False)

        except Exception as e:
            logging.debug(f"Error checking memory usage: {e}")

    def _initialize_default_configs(self):
        """Initialize optimized default configurations for all resource types"""

        # High-frequency resources (need faster loading, shorter cache TTL)
        high_frequency_resources = ['pods', 'events']

        # Heavy data resources (need chunking and optimization, medium cache TTL)
        heavy_data_resources = ['nodes', 'pods']

        # Medium-frequency resources (moderate cache TTL)
        medium_frequency_resources = ['deployments', 'services', 'configmaps', 'secrets']

        # Low-frequency resources (longer cache TTL)
        low_frequency_resources = ['storageclasses', 'clusterroles', 'namespaces']

        # Configure high-frequency resources for speed
        for resource_type in high_frequency_resources:
            config = ResourceConfig(
                resource_type=resource_type,
                api_method=self._get_api_method(resource_type),
                batch_size=100,
                timeout_seconds=APIClientConfig.RESOURCE_LIST_TIMEOUT,
                enable_streaming=True,
                max_concurrent_requests=8,
                enable_caching=True
            )

            # Enable heavy data optimizations for large datasets
            if resource_type in heavy_data_resources:
                config.timeout_seconds = APIClientConfig.BATCH_OPERATION_TIMEOUT  # Longer timeout for heavy data
                config.enable_chunking = True
                config.chunk_size = 200 if resource_type == 'nodes' else 100
                config.progressive_loading = True
                config.enable_pagination = True
                logging.debug(f"Unified Resource Loader: Enabled heavy data optimizations for {resource_type}")

            self._config_cache[resource_type] = config

        # Configure medium-frequency resources
        for resource_type in medium_frequency_resources:
            self._config_cache[resource_type] = ResourceConfig(
                resource_type=resource_type,
                api_method=self._get_api_method(resource_type),
                batch_size=50,
                timeout_seconds=APIClientConfig.HEAVY_LOAD_TIMEOUT,
                enable_streaming=True,
                max_concurrent_requests=5,
                enable_caching=True
            )

        # Configure low-frequency resources for efficiency
        for resource_type in low_frequency_resources:
            self._config_cache[resource_type] = ResourceConfig(
                resource_type=resource_type,
                api_method=self._get_api_method(resource_type),
                batch_size=25,
                timeout_seconds=APIClientConfig.REQUEST_TIMEOUT,
                enable_streaming=False,
                max_concurrent_requests=3,
                enable_caching=True
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
            'replicationcontrollers': 'list_replication_controller_for_all_namespaces',
            'limitranges': 'list_limit_range_for_all_namespaces',
            'resourcequotas': 'list_resource_quota_for_all_namespaces',
            'serviceaccounts': 'list_service_account_for_all_namespaces',
            'leases': 'list_lease_for_all_namespaces',

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

            # Autoscaling v2 resources
            'horizontalpodautoscalers': 'list_horizontal_pod_autoscaler_for_all_namespaces',

            # Policy v1 resources
            'poddisruptionbudgets': 'list_pod_disruption_budget_for_all_namespaces',

            # Scheduling v1 resources
            'priorityclasses': 'list_priority_class',

            # Node v1 resources
            'runtimeclasses': 'list_runtime_class',

            # Admission registration v1 resources
            'mutatingwebhookconfigurations': 'list_mutating_webhook_configuration',
            'validatingwebhookconfigurations': 'list_validating_webhook_configuration',

            # Custom Resources
            'customresourcedefinitions': 'list_custom_resource_definition',
        }

        # Fail fast on unknown types instead of silently fetching pods. Previously
        # the .get default of 'list_pod_for_all_namespaces' caused synthetic types
        # like 'helmreleases' to return pod data, crashing the UI downstream.
        if resource_type not in method_mapping:
            raise ValueError(
                f"Unknown resource_type {resource_type!r} not in unified loader's "
                f"API method registry. Either add it to the mapping or have the "
                f"caller bypass the unified loader (e.g. uses_unified_search=False)."
            )
        return method_mapping[resource_type]

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
            'replicationcontrollers': 'list_namespaced_replication_controller',
            'limitranges': 'list_namespaced_limit_range',
            'resourcequotas': 'list_namespaced_resource_quota',
            'serviceaccounts': 'list_namespaced_service_account',
            'leases': 'list_namespaced_lease',

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

            # Autoscaling v2 resources
            'horizontalpodautoscalers': 'list_namespaced_horizontal_pod_autoscaler',

            # Policy v1 resources
            'poddisruptionbudgets': 'list_namespaced_pod_disruption_budget',
        }


        if resource_type in cluster_scoped_resources:
            return self._get_api_method(resource_type)

        # Fail fast on unknown types instead of silently fetching pods.
        if resource_type not in namespaced_method_mapping:
            raise ValueError(
                f"Unknown namespaced resource_type {resource_type!r} not in unified "
                f"loader's API method registry. Either add it to the mapping or have "
                f"the caller bypass the unified loader (e.g. uses_unified_search=False)."
            )
        return namespaced_method_mapping[resource_type]

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
            timeout_seconds=APIClientConfig.BATCH_OPERATION_TIMEOUT,  # Longer timeout for search
            enable_pagination=True,  # Enable pagination for comprehensive search
            max_concurrent_requests=3  # More requests for search
        )

        operation_id = f"search_{resource_type}_{int(time.time())}"

        # Cancel any existing load for this resource type
        self._cancel_existing_load(resource_type, namespace)

        # Emit loading started signal
        self.loading_started.emit(resource_type)

        # Create and submit search worker
        worker = SearchResourceLoadWorker(config, self, search_query)

        # Track the worker
        with self._worker_lock:
            # Use cluster-aware key for worker tracking
            try:
                kube_client = get_kubernetes_client()
                cluster_name = kube_client.current_cluster if kube_client else 'unknown'
            except Exception:
                cluster_name = 'unknown'
                
            worker_key = self._generate_operation_key(resource_type, namespace, cluster_name)
            self._active_workers[worker_key] = worker

        # Connect worker signals for completion handling
        worker.signals.finished.connect(
            lambda result: self._handle_load_completion_success(result, resource_type, namespace, operation_id, cluster_name)
        )
        worker.signals.error.connect(
            lambda error: self._handle_load_completion_error(error, resource_type, namespace, operation_id, cluster_name)
        )

        # Submit to thread manager
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(operation_id, worker)

        return operation_id

    @log_performance
    def load_resources_async(
        self,
        resource_type: str,
        namespace: Optional[str] = None,
        custom_config: Optional[ResourceConfig] = None
    ) -> str:
        """
        Load Kubernetes resources asynchronously with high performance and deduplication.
        Returns operation ID for tracking.
        """
        # Get current cluster name for scoped deduplication
        try:
            kube_client = get_kubernetes_client()
            cluster_name = kube_client.current_cluster if kube_client else 'unknown'
        except Exception:
            cluster_name = 'unknown'

        logging.debug(f"Unified Resource Loader: Starting async load for resource_type='{resource_type}', namespace='{namespace or 'all'}' (cluster: {cluster_name})")

        # If a watch stream is active for this resource, return cached data immediately
        # ATOMIC: Check and retrieve must be under the same lock to prevent TOCTOU race
        watch_key = (resource_type, namespace)
        cached_items = None
        with self._watches_lock:
            watch = self._resource_watches.get(watch_key)
            if watch and watch.is_active:
                cached_items = watch.get_cached_items()
        
        if cached_items:
            logging.debug(f"Watch cache hit for {resource_type}: {len(cached_items)} items")
            # An earlier call for this key may have started a LIST worker before
            # the watch cache was populated. Now that the live watch is serving
            # the data, that worker's result is redundant (and possibly older).
            # Cancel it — this both stops its expensive chunked processing and
            # makes safe_emit_finished suppress its emit — then clear its
            # dedup/worker entries. The cleanup is required because a cancelled
            # worker never reaches the completion handler, so without it the
            # stale _pending_operations entry would dedup-suppress a future load.
            self._cancel_existing_load(resource_type, namespace)
            self._cleanup_worker(resource_type, namespace, cluster_name)
            self._cleanup_pending_operation(resource_type, namespace, cluster_name)
            result = LoadResult(
                success=True,
                resource_type=resource_type,
                items=cached_items,
                total_count=len(cached_items),
                load_time_ms=0,
                from_cache=True,
            )
            self.loading_completed.emit(resource_type, result)
            # This path completes synchronously; the returned id is informational
            # only — callers use it for logging, never to look up or cancel it.
            return f"{resource_type}_watch_cache_{int(time.time() * 1000)}"

        # Generate operation key for deduplication - NOW CLUSTER-AWARE
        operation_key = self._generate_operation_key(resource_type, namespace, cluster_name)

        # Check for duplicate request and deduplicate if necessary
        with self._dedup_lock:
            if operation_key in self._pending_operations:
                existing_operation_id = self._pending_operations[operation_key]
                logging.debug(f"Unified Resource Loader: Duplicate request detected for {operation_key}, returning existing operation_id: {existing_operation_id}")
                return existing_operation_id

        # Get or create configuration
        config = custom_config or self._get_config_for_resource(resource_type, namespace)
        logging.debug(f"Unified Resource Loader: Using config for {resource_type}: timeout={config.timeout_seconds}s, batch_size={config.batch_size}")

        # Generate operation ID
        operation_id = f"{resource_type}_{namespace or 'all'}_{int(time.time() * 1000)}"
        logging.debug(f"Unified Resource Loader: Generated operation_id: {operation_id}")

        # Register this operation to prevent duplicates
        with self._dedup_lock:
            self._pending_operations[operation_key] = operation_id

        # Cancel any existing load for this resource type
        self._cancel_existing_load(resource_type, namespace)

        # Emit loading started signal
        logging.debug(f"Unified Resource Loader: Emitting loading_started signal for {resource_type}")
        self.loading_started.emit(resource_type)

        # Create and start worker
        logging.debug(f"Unified Resource Loader: Creating ResourceLoadWorker for {resource_type}")
        worker = ResourceLoadWorker(config, self)

        # Track the worker
        with self._worker_lock:
            # Use cluster-aware key for worker tracking
            worker_key = self._generate_operation_key(resource_type, namespace, cluster_name)
            self._active_workers[worker_key] = worker
            logging.debug(f"Unified Resource Loader: Tracking worker with key: {worker_key}")

        # Connect worker signals for completion handling
        # Connect worker signals for completion handling
        worker.signals.finished.connect(
            lambda result: self._handle_load_completion_success(result, resource_type, namespace, operation_id, cluster_name)
        )
        worker.signals.error.connect(
            lambda error: self._handle_load_completion_error(error, resource_type, namespace, operation_id, cluster_name)
        )
        logging.debug(f"Unified Resource Loader: Connected worker signals for {resource_type}")

        # Submit to unified thread manager
        logging.debug(f"Unified Resource Loader: Submitting worker to thread manager for {resource_type}")
        self._thread_manager.submit_worker(operation_id, worker)

        logging.debug(f"Unified Resource Loader: Successfully initiated async loading for {resource_type} with operation_id: {operation_id}")
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
                enable_streaming=base_config.enable_streaming,
                max_concurrent_requests=base_config.max_concurrent_requests
            )
            return config

        return base_config

    def _generate_operation_key(self, resource_type: str, namespace: Optional[str], cluster_name: str = 'unknown') -> str:
        """Generate a consistent operation key for deduplication and worker tracking"""
        return f"{cluster_name}_{resource_type}_{namespace or 'all'}"

    def _cancel_existing_load(self, resource_type: str, namespace: Optional[str]):
        """Cancel any existing load operation for the same resource"""
        try:
            kube_client = get_kubernetes_client()
            cluster_name = kube_client.current_cluster if kube_client else 'unknown'
        except Exception:
            cluster_name = 'unknown'
            
        # Use cluster-aware key
        worker_key = self._generate_operation_key(resource_type, namespace, cluster_name)

        with self._worker_lock:
            if worker_key in self._active_workers:
                existing_worker = self._active_workers[worker_key]
                existing_worker.cancel()
                logging.debug(f"Cancelled existing load for {resource_type} (key: {worker_key})")

    def clear_all_pending_operations(self):
        """Clear all pending operations and cache - used when switching clusters"""
        logging.debug("Unified Resource Loader: Clearing all pending operations and worker state")
        
        # 1. Clear pending operations map
        with self._dedup_lock:
            self._pending_operations.clear()
            self._operation_callbacks.clear()
            
        # 2. Cancel all active workers
        with self._worker_lock:
            for key, worker in list(self._active_workers.items()):
                try:
                    worker.cancel()
                    logging.debug(f"Cancelled active worker: {key}")
                except Exception as e:
                    logging.error(f"Error cancelling worker {key}: {e}")
            self._active_workers.clear()
            
        # 3. Stop all active watch streams to prevent stale data from old cluster
        self.stop_all_watches()
        
        logging.debug("Unified Resource Loader: State cleared successfully")

# Method removed - monitoring is now handled by EnhancedBaseWorker signals

    def _handle_load_completion_success(self, result: LoadResult, resource_type: str, namespace: Optional[str], operation_id: str, cluster_name: str = 'unknown'):
        """Handle successful load completion"""
        logging.debug(f"Unified Resource Loader: Load completed successfully for {resource_type} (operation_id: {operation_id})")
        try:
            if resource_type == 'nodes':
                from Utils import get_timestamp_with_ms
                logging.debug(f"[UI EMIT] {get_timestamp_with_ms()} - Unified Resource Loader: Emitting node data to UI - {result.total_count} nodes loaded in {result.load_time_ms:.1f}ms")
                # Log sample of node data being sent to UI
                if result.items and len(result.items) > 0:
                    sample_node = result.items[0]
                    logging.debug(f"📤 [UI SAMPLE] {get_timestamp_with_ms()} - Sample node data being sent: name={sample_node.get('name')}, status={sample_node.get('status')}, cpu={sample_node.get('cpu_capacity')}")
                    logging.debug(f"📤 [UI COUNT] {get_timestamp_with_ms()} - Sending {len(result.items)} nodes to UI: {[item.get('name', 'unnamed') for item in result.items[:5]]}{'...' if len(result.items) > 5 else ''}")

            self.loading_completed.emit(resource_type, result)
            logging.debug(
                f"Loaded {result.total_count} {resource_type} in {result.load_time_ms:.1f}ms"
            )
        except Exception as e:
            logging.error(f"Unified Resource Loader: Error emitting load completion signal for {resource_type}: {e}")
            logging.debug("Unified Resource Loader: Load completion error details", exc_info=True)
        finally:
            # Cleanup worker reference and pending operation
            self._cleanup_worker(resource_type, namespace, cluster_name)
            self._cleanup_pending_operation(resource_type, namespace, cluster_name)

    def _handle_load_completion_error(self, error_message: str, resource_type: str, namespace: Optional[str], operation_id: str, cluster_name: str = 'unknown'):
        """Handle error in load completion"""
        logging.error(f"Unified Resource Loader: Load failed for {resource_type} (operation_id: {operation_id}): {error_message}")
        try:
            if resource_type == 'nodes':
                logging.error("Unified Resource Loader: Node loading failed - UI will not receive node data")

            self.loading_error.emit(resource_type, error_message)
            logging.error(f"Unified Resource Loader: Failed to load {resource_type}: {error_message}")
        except Exception as e:
            logging.error(f"Unified Resource Loader: Error emitting load error signal for {resource_type}: {e}")
        finally:
            # Cleanup worker reference and pending operation
            self._cleanup_worker(resource_type, namespace, cluster_name)
            self._cleanup_pending_operation(resource_type, namespace, cluster_name)

    def _cleanup_worker(self, resource_type: str, namespace: Optional[str], cluster_name: str = 'unknown'):
        """Cleanup worker reference"""
        worker_key = self._generate_operation_key(resource_type, namespace, cluster_name)
        with self._worker_lock:
            self._active_workers.pop(worker_key, None)

    def _cleanup_pending_operation(self, resource_type: str, namespace: Optional[str], cluster_name: str = 'unknown'):
        """Cleanup pending operation to allow future requests"""
        operation_key = self._generate_operation_key(resource_type, namespace, cluster_name)
        with self._dedup_lock:
            self._pending_operations.pop(operation_key, None)
            logging.debug(f"Cleaned up pending operation for {operation_key}")

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

    # ── Resource Watch Management ──

    def start_watch(self, resource_type: str, namespace: Optional[str] = None,
                    list_kwargs: Optional[Dict[str, Any]] = None,
                    on_added=None, on_modified=None, on_deleted=None,
                    generation: int = 0):
        """Start a watch stream for the given resource type and namespace.

        list_kwargs  – extra keyword args forwarded to every LIST / WATCH call
                       (e.g. ``{'field_selector': 'type!=Normal'}``).
        on_added / on_modified / on_deleted  – optional Shared-Informer-style
                       delta callbacks called for each individual change.
        generation   – caller-supplied counter embedded in every LoadResult so
                       the receiver slot can reject stale signals after a
                       context change.

        Reference counted: if a watch already exists for this
        (resource_type, namespace) pair, this registers an additional consumer
        and adopts the caller's generation rather than starting a new stream."""
        watch_key = (resource_type, namespace)
        with self._watches_lock:
            existing = self._resource_watches.get(watch_key)
            if existing and existing.is_active:
                # Shared stream already live.  Register this consumer and adopt
                # its generation so the running watch's emissions match the new
                # caller's expectation — this is what prevents the generation
                # desync that silently discarded live updates.  Reassigning an
                # int is atomic under the GIL, so the watch thread reading
                # _generation in _do_emit needs no additional lock.
                existing._refcount += 1
                existing._generation = generation
                logging.debug(
                    f"start_watch: reused {watch_key} "
                    f"(refcount={existing._refcount}, generation={generation})"
                )
                return
            # Stop any existing (possibly dead) watch for this key
            if existing:
                existing.stop()
            watch = ResourceWatchManager(self, resource_type, namespace,
                                         list_kwargs=list_kwargs,
                                         on_added=on_added,
                                         on_modified=on_modified,
                                         on_deleted=on_deleted,
                                         generation=generation)
            watch._refcount = 1
            self._resource_watches[watch_key] = watch
        watch.start()

    def stop_watch(self, resource_type: str, namespace: Optional[str] = None):
        """Release one consumer's reference to the watch stream.

        Reference counted: the underlying Kubernetes stream is only torn down
        once the last consumer detaches (refcount reaches zero).  This prevents
        a page's hideEvent from killing a watch the cluster connector still
        relies on for background telemetry (e.g. the events/issues delta feed
        or node capacity cache)."""
        watch_key = (resource_type, namespace)
        watch_to_stop = None
        with self._watches_lock:
            watch = self._resource_watches.get(watch_key)
            if watch is None:
                return
            watch._refcount -= 1
            if watch._refcount > 0:
                logging.debug(
                    f"stop_watch: {watch_key} still in use "
                    f"(refcount={watch._refcount}) — keeping stream alive"
                )
                return
            # Last consumer detached — evict and tear the stream down.
            self._resource_watches.pop(watch_key, None)
            watch_to_stop = watch
        if watch_to_stop is not None:
            watch_to_stop.stop()

    def stop_all_watches(self):
        """Stop all active watch streams. Called on cluster disconnect."""
        with self._watches_lock:
            watches = list(self._resource_watches.values())
            self._resource_watches.clear()
        for watch in watches:
            watch.stop()

    def has_active_watch(self, resource_type: str, namespace: Optional[str] = None) -> bool:
        """Check if a watch is active for the given resource type and namespace."""
        watch_key = (resource_type, namespace)
        with self._watches_lock:
            watch = self._resource_watches.get(watch_key)
            return watch is not None and watch.is_active

    def get_watch_cached_items(self, resource_type: str, namespace: Optional[str] = None) -> Optional[list]:
        """Return the current cached items from an active watch, or None if not available.
        
        ATOMIC: Check and retrieve must be under the same lock to prevent TOCTOU race.
        """
        watch_key = (resource_type, namespace)
        with self._watches_lock:
            watch = self._resource_watches.get(watch_key)
            if watch and watch.is_active:
                return watch.get_cached_items()
        return None

    # Backward-compatible aliases for node watch (used by cluster_connector)
    def start_node_watch(self):
        """Start the event-driven node watch stream."""
        self.start_watch('nodes', None)

    def stop_node_watch(self):
        """Stop the node watch stream."""
        self.stop_watch('nodes', None)

    def cancel_all_loads(self):
        """Cancel all active loading operations"""
        with self._worker_lock:
            for worker in self._active_workers.values():
                worker.cancel()
            self._active_workers.clear()

        logging.info("Cancelled all active resource loading operations")

    def _clear_old_cache_entries(self, force: bool = False):
        """Clear old cache entries based on TTL and memory pressure"""
        try:
            with self._cache_lock:
                current_time = time.time()
                
                # Update cleanup timestamp
                self._last_cache_cleanup = current_time
                
                # Use the unified cache system's optimize method
                self._cache.optimize_caches()
                
                if force:
                    logging.info("Aggressive cache cleanup triggered - unified cache optimization applied")

                logging.debug(f"Cache cleanup completed (force={force})")
                
        except Exception as e:
            logging.error(f"Error during cache cleanup: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        try:
            with self._cache_lock:
                stats = {}
                total_hits = 0
                total_misses = 0
                
                for resource_type, type_stats in self._cache_stats.items():
                    stats[resource_type] = {
                        'hits': type_stats['hits'],
                        'misses': type_stats['misses'],
                        'hit_rate': type_stats['hits'] / (type_stats['hits'] + type_stats['misses']) if (type_stats['hits'] + type_stats['misses']) > 0 else 0,
                        'size': type_stats['size']
                    }
                    total_hits += type_stats['hits']
                    total_misses += type_stats['misses']
                
                stats['total'] = {
                    'hits': total_hits,
                    'misses': total_misses,
                    'hit_rate': total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
                }
                
                return stats
        except Exception as e:
            logging.error(f"Error getting cache stats: {e}")
            return {}

    def clear_cache(self, resource_type: Optional[str] = None):
        """Clear cache entries for specific resource type or all"""
        try:
            with self._cache_lock:
                if resource_type:
                    # Clear specific resource type cache
                    # The unified cache system doesn't have a direct method for this
                    # but we can reset our stats
                    if resource_type in self._cache_stats:
                        self._cache_stats[resource_type] = {'hits': 0, 'misses': 0, 'size': 0}
                    logging.info(f"Cleared cache for resource type: {resource_type}")
                else:
                    # Clear all cache
                    self._cache_stats.clear()
                    logging.info("Cleared all cache entries")
        except Exception as e:
            logging.error(f"Error clearing cache: {e}")

    def _get_api_client(self, kube_client, resource_type=None):
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
            'replicationcontrollers': kube_client.v1,
            'limitranges': kube_client.v1,
            'resourcequotas': kube_client.v1,
            'serviceaccounts': kube_client.v1,

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

            # Autoscaling v2 resources
            'horizontalpodautoscalers': kube_client.autoscaling_v2,

            # Policy v1 resources
            'poddisruptionbudgets': kube_client.policy_v1,

            # Scheduling v1 resources
            'priorityclasses': kube_client.scheduling_v1,

            # Node v1 resources
            'runtimeclasses': kube_client.node_v1,

            # Admission registration v1 resources
            'mutatingwebhookconfigurations': kube_client.admissionregistration_v1,
            'validatingwebhookconfigurations': kube_client.admissionregistration_v1,

            # Coordination v1 resources
            'leases': kube_client.coordination_v1,

            # Custom Resources
            'customresourcedefinitions': kube_client.apiextensions_v1,
        }

        # Use the resource_type parameter if provided, otherwise fall back to default
        if resource_type:
            return api_mapping.get(resource_type, kube_client.v1)
        return kube_client.v1  # Default fallback

    def cleanup(self):
        """Cleanup resources and shutdown thread pool"""
        logging.info("Shutting down Unified Resource Loader")

        # Stop all watch streams
        self.stop_all_watches()

        # Cancel all active loads
        self.cancel_all_loads()

        # Force garbage collection of large objects
        self._force_memory_cleanup()

        # Clear all caches and references
        with self._worker_lock:
            self._active_workers.clear()

        with self._dedup_lock:
            self._pending_operations.clear()
            self._operation_callbacks.clear()

        with self._stats_lock:
            self._load_stats.clear()

        # Clear configuration cache
        self._config_cache.clear()

        logging.info("Resource Loader cleanup completed")

    def _force_memory_cleanup(self):
        """Force cleanup of memory-intensive objects"""

        # Single collection — passes 2 and 3 reclaim almost nothing and triple
        # the main-thread stall.  With Qt parent/child ownership + deleteLater(),
        # one pass clears the cyclic Python references; the x3 was cargo-culting.
        collected = gc.collect()
        if collected > 0:
            logging.info(f"Memory cleanup: collected {collected} objects")

        # Log memory stats if available
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            logging.info(f"Memory usage after cleanup: {memory_mb:.1f} MB")
        except ImportError:
            pass

    @staticmethod
    def _format_capacity(raw_value: str) -> str:
        """Format Kubernetes capacity values to human-readable format"""
        if not raw_value:
            return ''

        if 'Ki' in raw_value:
            # Convert from Ki to GB
            ki_value = int(raw_value.replace('Ki', ''))
            gb_value = ki_value / (1024 * 1024)
            return f"{gb_value:.1f}GB"
        elif 'Gi' in raw_value:
            # Convert from Gi to GB
            gi_value = int(raw_value.replace('Gi', ''))
            return f"{gi_value}GB"
        else:
            return raw_value

    @staticmethod
    def _process_node_conditions(conditions) -> tuple:
        """Process node conditions and return (status, conditions_text)"""
        node_status = 'Unknown'
        conditions_list = []

        if conditions:
            for condition in conditions:
                if condition.type == 'Ready':
                    node_status = 'Ready' if condition.status == 'True' else 'NotReady'

                # Format condition for display: Type=Status
                condition_display = f"{condition.type}={condition.status}"

                # Add reason if available for non-True conditions
                if condition.status != 'True' and hasattr(condition, 'reason') and condition.reason:
                    condition_display += f" ({condition.reason})"

                conditions_list.append(condition_display)

        conditions_text = ", ".join(conditions_list) if conditions_list else "Unknown"
        return node_status, conditions_text

    @staticmethod
    def _extract_node_roles(labels) -> list:
        """Extract node roles from Kubernetes labels"""
        roles = []
        if labels:
            for label_key in labels:
                if 'node-role.kubernetes.io/' in label_key:
                    role = label_key.replace('node-role.kubernetes.io/', '')
                    if role:
                        roles.append(role)
        return roles if roles else ['<none>']


# ── Node Watch Manager ──────────────────────────────────────────────
# Replaces periodic LIST calls for nodes with an event-driven Watch stream.
# Maintains a local cache updated via ADDED/MODIFIED/DELETED deltas.


class ItemProcessor:
    """Lightweight processor for item transformation in background threads.
    
    Does not inherit from QObject/QRunnable to avoid threading constraints.
    Created to replace the ResourceLoadWorker.__new__ bypass pattern which
    created incomplete 'zombie' objects missing EnhancedBaseWorker attributes.
    
    This class contains only the minimal attributes and methods needed for
    item processing, without any QObject dependencies that would violate
    PyQt6 threading contracts when instantiated from background threads.
    """
    
    def __init__(self, config: ResourceConfig, loader):
        """Initialize processor with config and loader reference.
        
        Args:
            config: ResourceConfig with resource_type, api_method, namespace
            loader: Reference to HighPerformanceResourceLoader instance
        """
        self.config = config
        self.loader = loader
    
    def _process_single_item(self, item: Any, preloaded_metrics: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Process a single Kubernetes resource item.
        
        This is a copy of ResourceLoadWorker._process_single_item() to ensure
        identical processing behavior while avoiding QObject dependencies.
        """
        try:
            # Extract common fields efficiently
            metadata = item.metadata
            if not metadata:
                logging.error(f"❌ [PROCESS] Item has no metadata: {item}")
                return None

            name = metadata.name
            if not name:
                logging.error(f"❌ [PROCESS] Item has no name in metadata: {metadata}")
                return None

            namespace = getattr(metadata, 'namespace', None)
            creation_timestamp = metadata.creation_timestamp

            # Calculate age efficiently using helper function
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
            self._add_resource_specific_fields(processed_item, item, preloaded_metrics)

            # Add raw_data for UI components that need detailed information
            try:
                kube_client = get_kubernetes_client()
                if hasattr(kube_client, 'v1') and hasattr(kube_client.v1, 'api_client'):
                    processed_item['raw_data'] = kube_client.v1.api_client.sanitize_for_serialization(item)
                else:
                    processed_item['raw_data'] = {}
            except Exception as e:
                logging.debug(f"Error serializing raw data: {e}")
                processed_item['raw_data'] = {}

            return processed_item

        except Exception as e:
            logging.error(f"❌ [PROCESS ERROR] Error processing single {self.config.resource_type} item: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def _format_age_fast(self, creation_timestamp) -> str:
        """Fast age calculation with comprehensive timestamp handling"""
        return format_age(creation_timestamp)
    
    def _add_resource_specific_fields(self, processed_item: Dict[str, Any], item: Any, preloaded_metrics: Optional[Dict[str, Any]] = None):
        """Add resource-specific fields efficiently.
        
        Delegates to the loader's ResourceLoadWorker static methods for consistency.
        """
        ResourceLoadWorker._add_resource_specific_fields(processed_item, item, self.config.resource_type, preloaded_metrics)


class ResourceWatchManager(QObject):
    """Maintains a Kubernetes Watch stream for any resource type, updating a
    local cache and emitting signals compatible with the existing loader pipeline.

    Replaces the former NodeWatchManager with a generic, JIT view-scoped approach.
    Each instance watches a single (resource_type, namespace) pair.
    """

    def __init__(self, loader: 'HighPerformanceResourceLoader',
                 resource_type: str, namespace: Optional[str] = None,
                 list_kwargs: Optional[Dict[str, Any]] = None,
                 on_added=None, on_modified=None, on_deleted=None,
                 cache_size_limit: int = 2000,
                 generation: int = 0):
        super().__init__()
        self._loader = loader
        self._resource_type = resource_type
        # Cluster-scoped resources must never receive a namespace argument
        if resource_type in cluster_scoped_resources:
            namespace = None
        self._namespace = namespace  # None means all namespaces / cluster-scoped
        # Extra kwargs forwarded to every LIST and WATCH call (e.g. field_selector)
        self._list_kwargs: Dict[str, Any] = list_kwargs or {}
        # Optional Shared-Informer-style delta handlers.  When provided these are
        # called for each individual change so callers can maintain incremental
        # state without copying the full cache on every delta.
        self._on_added = on_added      # fn(item: dict)
        self._on_modified = on_modified  # fn(item: dict)
        self._on_deleted = on_deleted   # fn(uid: str)
        self._cache: Dict[str, Dict[str, Any]] = {}  # keyed by resource uid or name
        self._resource_version: Optional[str] = None
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._running = False
        # Maximum number of items retained in the local cache to prevent unbounded
        # memory growth over long sessions (e.g. high-frequency event streams).
        self._cache_size_limit = cache_size_limit
        # Caller-supplied generation counter, embedded in every LoadResult so
        # receiver slots can reject stale signals after a context change.
        self._generation = generation
        # Reference count of distinct consumers (declarative pages + the
        # cluster-connector telemetry daemon) sharing this single stream.
        # Mutated only under the loader's _watches_lock.  The underlying
        # Kubernetes stream is torn down only when this reaches zero, so a
        # page navigating away cannot kill a watch another consumer relies on.
        self._refcount = 0
        # Lightweight processor for reusing _process_single_item
        self._item_processor: Optional[ItemProcessor] = None
        # Reference to the active kubernetes.watch.Watch object, used by stop()
        # to invoke w.stop() and flip the generator's internal _stop boolean
        # so the stream breaks on the very next network event.
        self._active_watch = None
        # ── Emit rate limiter ──
        # Leading-edge + trailing throttle: at most one emit per window, with
        # the first event in a quiet window emitted immediately and a trailing
        # QTimer flushing the tail of a burst. _last_emit_time tracks the last
        # emission so the leading-edge check can tell when a new window opened.
        self._EMIT_THROTTLE_SECS: float = 0.25   # 250ms — max 4 emits/sec
        self._last_emit_time: float = 0.0

        # Trailing-edge throttle timer to guarantee final event emission
        self._emit_timer = QTimer()
        self._emit_timer.setSingleShot(True)
        self._emit_timer.setInterval(int(self._EMIT_THROTTLE_SECS * 1000))  # Convert to milliseconds
        self._emit_timer.timeout.connect(self._do_emit)

    # ── public API ──

    @property
    def resource_type(self) -> str:
        return self._resource_type

    @property
    def namespace(self) -> Optional[str]:
        return self._namespace

    def start(self):
        """Start the watch stream in a daemon thread."""
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        thread_name = f"watch-{self._resource_type}"
        if self._namespace:
            thread_name += f"-{self._namespace}"
        self._watch_thread = threading.Thread(
            target=self._watch_loop, daemon=True, name=thread_name
        )
        self._watch_thread.start()
        logging.info(f"Watch stream started for {self._resource_type}"
                     f"{' in ' + self._namespace if self._namespace else ''}")

    def stop(self):
        """Gracefully stop the watch stream.

        NOTE: intentionally does NOT join the background thread.  The thread is
        a daemon thread, so the OS will reap it automatically.  Calling join()
        here from the Qt main thread (e.g. from hideEvent → stop_watch) would
        block the Qt event loop for up to the join timeout, causing the 5-6 s
        UI freeze observed during page navigation.
        """
        if not self._running:
            return
        self._running = False
        # Signal the internal Kubernetes Watch generator to break its loop
        # on the absolute next yielded event.  Watch.stop() only flips a
        # boolean (_stop = True) — atomic under the GIL, fully thread-safe.
        watch_ref = self._active_watch
        if watch_ref is not None:
            try:
                watch_ref.stop()
            except Exception:
                pass
        self._stop_event.set()
        # Stop the emit timer to prevent emissions after watch stops.
        # _emit_timer is owned by the main thread (created in __init__), but
        # stop() can run off it (e.g. cleanup() reached via atexit, or a
        # cluster switch). Dispatch the stop onto the timer's owner thread the
        # same way _emit_update() does. _do_emit already guards on _running
        # (set False above), so a late fire is a harmless no-op; .stop() on an
        # inactive timer is also a no-op, so the prior isActive() check is moot.
        if self._emit_timer is not None:
            QMetaObject.invokeMethod(
                self._emit_timer, "stop", Qt.ConnectionType.QueuedConnection
            )
        # Do NOT join here — let the daemon thread exit on its own.
        with self._lock:
            self._cache.clear()
            self._resource_version = None
        self._item_processor = None
        logging.debug(f"Watch stream stopped for {self._resource_type}")

    def get_cached_items(self) -> Optional[list]:
        """Return current cache as a list, or None if watch not active."""
        if not self._running:
            return None
        with self._lock:
            if not self._cache:
                return None
            return list(self._cache.values())

    @property
    def is_active(self) -> bool:
        """True while the watch thread is running, regardless of whether the
        initial LIST has completed and the cache has been populated.
        Use get_cached_items() to check whether data is available."""
        return self._running

    # ── internal ──

    def _get_item_processor(self) -> ItemProcessor:
        """Get or create a lightweight processor for item processing.
        
        Returns an ItemProcessor instance (not a QObject) that can be safely
        instantiated from background threads without violating PyQt6 contracts.
        Only config and loader are needed by _process_single_item.
        """
        if self._item_processor is None:
            self._item_processor = ItemProcessor(
                config=ResourceConfig(
                    resource_type=self._resource_type,
                    api_method=self._loader._get_api_method(self._resource_type),
                    namespace=self._namespace,
                ),
                loader=self._loader
            )
        return self._item_processor

    def _resolve_list_function(self, kube_client):
        """Resolve the K8s API list function for this resource type and namespace."""
        api_client = self._loader._get_api_client(kube_client, self._resource_type)

        if self._namespace:
            # Namespaced watch
            method_name = self._loader._get_namespaced_api_method(self._resource_type)
        else:
            # Cluster-scoped or all-namespaces watch
            method_name = self._loader._get_api_method(self._resource_type)

        list_func = getattr(api_client, method_name, None)
        if not list_func:
            raise AttributeError(f"API method '{method_name}' not found on {type(api_client).__name__}")
        return list_func

    def _watch_loop(self):
        """Main loop: LIST once, then WATCH for deltas. Reconnect on errors."""
        from kubernetes import watch as k8s_watch

        backoff = 1  # seconds, for reconnect

        while not self._stop_event.is_set():
            try:
                kube_client = get_kubernetes_client()
                if not kube_client or not hasattr(kube_client, 'v1'):
                    self._stop_event.wait(5)
                    continue

                list_func = self._resolve_list_function(kube_client)

                # 1) Initial LIST to populate cache + get resourceVersion
                self._full_list(list_func)
                backoff = 1  # reset on success

                # If stop() was requested while the initial LIST was in flight
                # (it can block for seconds on a large cluster), abort before
                # opening a watch stream we'd only have to tear down. Without
                # this, stop() racing the `self._active_watch = w` assignment
                # below could leave a freshly-started stream blocking until its
                # first event/bookmark before the per-event stop check fires.
                if self._stop_event.is_set():
                    break

                # 2) WATCH for deltas
                # allow_watch_bookmarks=True: the API server periodically emits
                # synthetic BOOKMARK events that advance our resourceVersion pointer
                # even when the watched namespace is quiet.  This prevents the
                # "resourceVersion too old" (410 Gone) error after reconnects.
                w = k8s_watch.Watch()
                self._active_watch = w
                watch_kwargs = dict(
                    resource_version=self._resource_version,
                    timeout_seconds=300,
                    allow_watch_bookmarks=True,
                    **self._list_kwargs,
                )
                try:
                    if self._namespace:
                        stream = w.stream(list_func, self._namespace, **watch_kwargs)
                    else:
                        stream = w.stream(list_func, **watch_kwargs)

                    for event in stream:
                        if self._stop_event.is_set():
                            w.stop()
                            return

                        event_type = event.get('type')
                        raw_obj = event.get('object')
                        if not raw_obj or not hasattr(raw_obj, 'metadata'):
                            continue

                        # Update resourceVersion from every event including BOOKMARKs
                        rv = getattr(raw_obj.metadata, 'resource_version', None)
                        if rv:
                            self._resource_version = rv

                        # BOOKMARK events only carry a resourceVersion — no object data.
                        # We've already advanced our pointer above; nothing else to do.
                        if event_type == 'BOOKMARK':
                            continue

                        obj_key = raw_obj.metadata.uid or raw_obj.metadata.name
                        if not obj_key:
                            continue

                        if event_type in ('ADDED', 'MODIFIED'):
                            processed = self._process_item(raw_obj)
                            if processed:
                                skip_emit = False
                                with self._lock:
                                    if event_type == 'MODIFIED' and obj_key in self._cache:
                                        old = self._cache[obj_key]
                                        # Always update cache so raw_data stays
                                        # fresh for detail views / YAML inspect.
                                        self._cache[obj_key] = processed
                                        # But only emit if UI-visible fields changed.
                                        if self._ui_fields_equal(old, processed):
                                            skip_emit = True
                                    else:
                                        if (obj_key not in self._cache and
                                                len(self._cache) >= self._cache_size_limit):
                                            try:
                                                self._cache.pop(next(iter(self._cache)))
                                            except StopIteration:
                                                pass
                                        self._cache[obj_key] = processed
                                # Phase 4: always emit on the global watch bus,
                                # even if the table-side _emit_update is skipped
                                # for unchanged UI fields — the detail view may
                                # need the full raw_data update regardless.
                                self._emit_global_watch_event(event_type, processed)
                                if skip_emit:
                                    continue
                                # Shared-Informer delta handlers (called before full emit)
                                if event_type == 'ADDED' and self._on_added:
                                    try:
                                        self._on_added(processed)
                                    except Exception as e:
                                        logging.debug(f"Watch {self._resource_type}: on_added callback error: {e}", exc_info=True)
                                elif event_type == 'MODIFIED' and self._on_modified:
                                    try:
                                        self._on_modified(processed)
                                    except Exception as e:
                                        logging.debug(f"Watch {self._resource_type}: on_modified callback error: {e}", exc_info=True)
                                self._emit_update()

                        elif event_type == 'DELETED':
                            # Build the global event payload BEFORE popping the
                            # cache entry so the consumer can still see the
                            # final raw_data of the just-deleted resource.
                            gone = None
                            with self._lock:
                                gone = self._cache.pop(obj_key, None)
                            if gone is not None:
                                self._emit_global_watch_event('DELETED', gone)
                            if self._on_deleted:
                                try:
                                    self._on_deleted(obj_key)
                                except Exception as e:
                                    logging.debug(f"Watch {self._resource_type}: on_deleted callback error: {e}", exc_info=True)
                            self._emit_update()

                        elif event_type == 'ERROR':
                            logging.warning(f"Watch {self._resource_type} received ERROR event, will re-list")
                            break
                finally:
                    self._active_watch = None

                # Stream ended normally (server closed) — restart
                logging.debug(f"Watch stream ended for {self._resource_type}, reconnecting")

            except ApiException as e:
                if e.status == 410:
                    logging.info(f"Watch {self._resource_type}: resourceVersion expired (410 Gone), re-listing")
                    self._resource_version = None
                else:
                    logging.warning(f"Watch {self._resource_type} API error: {e.status} {e.reason}")
                    self._stop_event.wait(min(backoff, 30))
                    backoff = min(backoff * 2, 60)

            except Exception as e:
                if self._stop_event.is_set():
                    return
                logging.warning(f"Watch {self._resource_type} error: {e}")
                self._stop_event.wait(min(backoff, 30))
                backoff = min(backoff * 2, 60)

    def _full_list(self, list_func):
        """Execute a full LIST to populate the cache and capture resourceVersion.

        Watches that registered delta callbacks (on_added/on_modified/on_deleted)
        also get state reconciliation here: the new LIST is diffed against the
        previous cache and the missing deltas are synthesized. This closes the
        gap where re-LIST (every 300s timeout or after 410 Gone) would otherwise
        leave a delta-driven consumer with a stale incremental cache — both
        missed DELETEs (zombie entries) and missed ADDs (invisible events).
        Watches without callbacks (pods/nodes/etc.) skip the diff entirely and
        keep the prior O(1) swap behavior.
        """
        start = time.time()

        if self._namespace:
            response = list_func(self._namespace,
                                 _request_timeout=APIClientConfig.REQUEST_TIMEOUT,
                                 **self._list_kwargs)
        else:
            response = list_func(_request_timeout=APIClientConfig.REQUEST_TIMEOUT,
                                 **self._list_kwargs)

        self._resource_version = response.metadata.resource_version

        new_cache = {}
        for item in response.items:
            processed = self._process_item(item)
            if processed:
                key = processed.get('uid') or processed['name']
                new_cache[key] = processed

        # Snapshot the old cache and swap under the lock; only copy when a delta
        # consumer is registered to avoid the cost on high-volume watches.
        has_delta_consumers = any((self._on_added, self._on_modified, self._on_deleted))
        with self._lock:
            old_cache = self._cache.copy() if has_delta_consumers else None
            self._cache = new_cache

        # Fire reconciling deltas OUTSIDE self._lock — the callbacks may acquire
        # their own locks (e.g. _issues_delta_lock in cluster_connector), and we
        # must not nest unrelated locks under self._lock. This mirrors the live
        # delta path in _watch_loop, which also fires callbacks post-lock.
        if has_delta_consumers:
            old_keys = set(old_cache.keys())
            new_keys = set(new_cache.keys())

            for key in (new_keys - old_keys):
                if self._on_added:
                    try:
                        self._on_added(new_cache[key])
                    except Exception as e:
                        logging.debug(f"Watch {self._resource_type}: on_added reconciliation error: {e}", exc_info=True)

            for key in (old_keys - new_keys):
                if self._on_deleted:
                    try:
                        self._on_deleted(key)
                    except Exception as e:
                        logging.debug(f"Watch {self._resource_type}: on_deleted reconciliation error: {e}", exc_info=True)

            if self._on_modified:
                for key in (new_keys & old_keys):
                    if not self._ui_fields_equal(old_cache[key], new_cache[key]):
                        try:
                            self._on_modified(new_cache[key])
                        except Exception as e:
                            logging.debug(f"Watch {self._resource_type}: on_modified reconciliation error: {e}", exc_info=True)

        load_time = (time.time() - start) * 1000
        # DEBUG: repetitive — fires on every re-LIST cycle (every 300s) per watch.
        # Useful for diagnosing watch behaviour but noisy at INFO.
        logging.debug(f"Watch {self._resource_type}: listed {len(new_cache)} items in {load_time:.0f}ms")
        self._emit_update()

    def _process_item(self, raw_obj) -> Optional[Dict[str, Any]]:
        """Process a raw K8s object using the existing ResourceLoadWorker pipeline.

        managedFields and the last-applied-configuration annotation are stripped
        before processing.  These fields are never rendered in the UI and can be
        very large (especially on objects managed by server-side apply), so
        removing them keeps the in-memory cache lean.
        """
        try:
            # Strip heavy metadata fields that are never shown in the UI.
            if hasattr(raw_obj, 'metadata') and raw_obj.metadata:
                raw_obj.metadata.managed_fields = None
                annotations = getattr(raw_obj.metadata, 'annotations', None)
                if annotations and 'kubectl.kubernetes.io/last-applied-configuration' in annotations:
                    del annotations['kubectl.kubernetes.io/last-applied-configuration']
            processor = self._get_item_processor()
            return processor._process_single_item(raw_obj)
        except Exception as e:
            logging.warning(f"Watch {self._resource_type}: error processing item: {e}")
            return None

    # Fields that change on every K8s MODIFIED event but don't affect the
    # table view.  raw_data includes resourceVersion, lastProbeTime, etc.
    # age is recomputed from wall-clock time on every call.
    _VOLATILE_KEYS = frozenset({'raw_data', 'age'})

    def _ui_fields_equal(self, old_item: Dict[str, Any], new_item: Dict[str, Any]) -> bool:
        """Compare two processed items ignoring volatile, non-UI fields."""
        for key in set(old_item) | set(new_item):
            if key in self._VOLATILE_KEYS:
                continue
            if old_item.get(key) != new_item.get(key):
                return False
        return True

    def _emit_global_watch_event(self, event_type: str, processed: Dict[str, Any]):
        """Phase 4: push a single watch event onto the global firehose.

        Called from the watch background thread.  Qt's automatic
        QueuedConnection serialises the signal payload onto the main
        thread's event queue, so this is safe to invoke from off-main.
        Best-effort — failures are swallowed because the table-side
        emit pipeline is the authoritative source of truth for the row.
        """
        if not self._running:
            return
        try:
            kc = get_kubernetes_client()
            if kc is None or not hasattr(kc, "global_resource_watch_event"):
                return
            raw_data = processed.get("raw_data") if isinstance(processed, dict) else None
            # For all-namespace / cluster-scoped watches self._namespace is None.
            # Emit the object's own namespace (from the processed item) so
            # consumers that filter by payload namespace (e.g. DetailManager)
            # don't drop every event for a namespaced resource being viewed
            # under an all-namespaces watch. Scoped watches keep self._namespace.
            item_namespace = processed.get("namespace") if isinstance(processed, dict) else None
            payload = {
                "type": event_type,
                "resource_type": self._resource_type,
                "namespace": self._namespace if self._namespace is not None else item_namespace,
                "name": processed.get("name") if isinstance(processed, dict) else None,
                "uid": processed.get("uid") if isinstance(processed, dict) else None,
                "raw_object": raw_data if isinstance(raw_data, dict) else {},
            }
            kc.global_resource_watch_event.emit(payload)
        except Exception as e:
            logging.debug(
                f"global watch emit failed for {self._resource_type}: {e}"
            )

    def _emit_update(self):
        """Rate-limited emit: leading-edge immediate + trailing-edge catch-up.

        The first event after a quiet throttle window emits immediately, so a
        steady stream of deltas keeps the table fresh at up to one emit per
        _EMIT_THROTTLE_SECS instead of stalling until the stream goes quiet
        (the failure mode of a pure debounce during a rollout/scale storm).
        Events arriving while the window is still open re-arm the trailing
        timer so the final state of a burst is always emitted once it settles.

        Thread-safety: _emit_update runs on the watch background thread (from
        _full_list and the WATCH event loop).  ALL cross-thread interactions
        are dispatched via QMetaObject.invokeMethod(QueuedConnection) so they
        execute on the main thread.  This is critical on Windows: calling
        _do_emit() directly from the background thread touches Qt internals
        linked to the main thread's COM STA, triggering 0x8001010d
        (RPC_E_CANTCALLOUT_ININPUTSYNCCALL) when the main thread is inside
        an input-synchronous dispatch.  Routing through QueuedConnection
        posts a QMetaCallEvent to the main thread's event queue, completely
        avoiding cross-apartment COM transitions.
        _last_emit_time is a plain float touched from both threads; reads and
        writes are atomic under the GIL and the throttle tolerates minor skew.
        """
        if not self._running:
            return
        now = time.monotonic()
        if now - self._last_emit_time >= self._EMIT_THROTTLE_SECS:
            # Leading edge: the window has elapsed — emit now. Cancel any
            # pending trailing fire so it doesn't double-emit right after.
            QMetaObject.invokeMethod(
                self._emit_timer, "stop", Qt.ConnectionType.QueuedConnection
            )
            # Route through QueuedConnection so _do_emit() executes on the
            # main thread.  Never call _do_emit() directly from a background
            # thread — see docstring above for the Windows COM rationale.
            QMetaObject.invokeMethod(
                self, "_do_emit", Qt.ConnectionType.QueuedConnection
            )
        else:
            # Inside the window: (re)arm the single-shot trailing timer so the
            # burst's final state is emitted once it quiets down.
            QMetaObject.invokeMethod(
                self._emit_timer, "start", Qt.ConnectionType.QueuedConnection
            )

    @pyqtSlot()
    def _do_emit(self):
        """Emit the current cache snapshot as a LoadResult signal.

        Decorated with @pyqtSlot() so QMetaObject.invokeMethod can resolve
        the method by its string name during dynamic dispatch from the
        background thread.  Always runs on the main thread (either via the
        trailing-edge QTimer timeout or via the leading-edge invokeMethod
        QueuedConnection posted by _emit_update).
        """
        if not self._running:
            return
        # Stamp the emit time so the leading-edge check in _emit_update opens a
        # fresh throttle window from this emission, whether it fired from the
        # leading-edge call above or from the trailing timer.
        self._last_emit_time = time.monotonic()
        with self._lock:
            items = list(self._cache.values())
        logging.debug(f"Watch {self._resource_type}: emitting {len(items)} items to UI")

        result = LoadResult(
            success=True,
            resource_type=self._resource_type,
            items=items,
            total_count=len(items),
            load_time_ms=0,
            from_cache=False,
            metadata={'generation': self._generation},
        )
        try:
            self._loader.loading_completed.emit(self._resource_type, result)
        except Exception as e:
            logging.warning(f"Watch {self._resource_type}: error emitting update: {e}")


# Singleton management
_unified_loader_instance = None
_unified_loader_lock = threading.Lock()

def get_unified_resource_loader() -> HighPerformanceResourceLoader:
    """Get or create the unified resource loader singleton (thread-safe)."""
    global _unified_loader_instance
    if _unified_loader_instance is None:
        with _unified_loader_lock:
            if _unified_loader_instance is None:
                _unified_loader_instance = HighPerformanceResourceLoader()
                # Explicit, deterministic cleanup at interpreter exit. atexit
                # handlers run on the main thread before module teardown,
                # unlike a __del__ destructor which could run on a GC/finalizer
                # thread and touch Qt objects (e.g. _emit_timer) off-thread.
                atexit.register(shutdown_unified_resource_loader)
    return _unified_loader_instance

def shutdown_unified_resource_loader():
    """Shutdown the unified resource loader"""
    global _unified_loader_instance
    if _unified_loader_instance is not None:
        _unified_loader_instance.cleanup()
        _unified_loader_instance = None
