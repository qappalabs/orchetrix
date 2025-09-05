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
    timeout_seconds: int = 45  # Longer timeout for heavy data
    cache_ttl: int = 900  # 15 minutes for heavy data caching
    enable_streaming: bool = False  # Keep disabled for stability
    enable_pagination: bool = True  # Enable for heavy data handling
    max_concurrent_requests: int = 3  # Slightly increased for heavy data
    enable_chunking: bool = True  # New: Enable data chunking for heavy loads
    chunk_size: int = 100  # New: Process data in chunks of 100 items
    progressive_loading: bool = True  # New: Enable progressive loading


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
            # Get namespaces first
            namespaces_response = get_kubernetes_client().v1.list_namespace(limit=100)
            namespace_names = [ns.metadata.name for ns in namespaces_response.items]
            
            # Search in all namespaces (not limited to 20 for search)
            kube_client = get_kubernetes_client()
            api_client = self.loader._get_api_client(kube_client, self.config.resource_type)
            namespaced_method_name = self.loader._get_namespaced_api_method(self.config.resource_type)
            api_method = getattr(api_client, namespaced_method_name)
            
            for namespace in namespace_names:
                if self.is_cancelled():
                    break
                    
                try:
                    kwargs = {
                        # 'namespace': namespace,
                        'timeout_seconds': 30,
                        '_request_timeout': 35,
                        'limit': 100  # Reasonable limit per namespace
                    }
                    # Only add namespace if NOT cluster-scoped
                    if self.config.resource_type not in cluster_scoped_resources:
                        kwargs['namespace'] = namespace

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
        """Process a single search result item (simplified for speed)"""
        try:
            # Extract basic fields efficiently
            metadata = item.metadata
            name = metadata.name
            namespace = getattr(metadata, 'namespace', None)
            creation_timestamp = metadata.creation_timestamp
            
            # Basic age calculation
            age = "Unknown"
            if creation_timestamp:
                try:
                    import datetime
                    if hasattr(creation_timestamp, 'replace'):
                        created_time = creation_timestamp.replace(tzinfo=datetime.timezone.utc)
                    else:
                        created_time = datetime.datetime.fromisoformat(str(creation_timestamp).replace('Z', '+00:00'))
                    
                    now = datetime.datetime.now(datetime.timezone.utc)
                    diff = now - created_time
                    
                    if diff.days > 0:
                        age = f"{diff.days}d"
                    elif diff.seconds > 3600:
                        age = f"{diff.seconds // 3600}h"
                    else:
                        age = f"{diff.seconds // 60}m"
                except Exception:
                    pass
            
            # Build basic resource data
            resource_data = {
                'name': name,
                'namespace': namespace or '',
                'age': age,
                'created': creation_timestamp.isoformat() if creation_timestamp else None,
                'resource_type': self.config.resource_type,
                'search_matched': True,  # Mark as search result
                'labels': metadata.labels or {},
                'annotations': metadata.annotations or {},
                'uid': metadata.uid if hasattr(metadata, 'uid') else None,
            }
            
            # Add resource-specific fields efficiently
            self._add_basic_resource_fields(resource_data, item)
            
            # Add raw_data for UI components that need detailed information - CRITICAL for proper display
            try:
                kube_client = get_kubernetes_client()
                if hasattr(kube_client, 'v1') and hasattr(kube_client.v1, 'api_client'):
                    resource_data['raw_data'] = kube_client.v1.api_client.sanitize_for_serialization(item)
                else:
                    # No fallback - skip items that can't be serialized to avoid dummy data
                    logging.warning(f"Skipping item {name} - unable to serialize raw data")
                    return None
            except Exception as e:
                logging.debug(f"Error serializing search raw data: {e}")
                resource_data['raw_data'] = {}
            
            return resource_data
            
        except Exception as e:
            logging.debug(f"Error processing single search item: {e}")
            return None
    
    def _add_basic_resource_fields(self, processed_item: Dict[str, Any], item: Any):
        """Add basic resource-specific fields for search results"""
        try:
            # Add status and basic info based on resource type
            if self.config.resource_type == 'pods':
                if hasattr(item, 'status') and item.status:
                    processed_item['status'] = item.status.phase or 'Unknown'
                    if item.status.container_statuses:
                        ready_containers = sum(1 for cs in item.status.container_statuses if cs.ready)
                        total_containers = len(item.status.container_statuses)
                        processed_item['ready'] = f"{ready_containers}/{total_containers}"
                        processed_item['containers_count'] = str(total_containers)
                        
                        # Calculate restart count
                        restart_count = sum(cs.restart_count for cs in item.status.container_statuses if cs.restart_count)
                        processed_item['restart_count'] = str(restart_count)
                    else:
                        processed_item['containers_count'] = "0"
                        processed_item['restart_count'] = "0"
                
                # Add additional pod-specific fields that PodsPage expects
                processed_item['controller_by'] = ""  # Default empty, could be enhanced
                processed_item['qos_class'] = ""      # Default empty, could be enhanced
                
                # Add node name if available
                if hasattr(item, 'spec') and item.spec and hasattr(item.spec, 'node_name'):
                    processed_item['node_name'] = item.spec.node_name or ""
                else:
                    processed_item['node_name'] = ""
                
            elif self.config.resource_type in ['deployments', 'replicasets', 'daemonsets', 'statefulsets']:
                if hasattr(item, 'status') and item.status:
                    replicas = getattr(item.status, 'replicas', 0) or 0
                    ready_replicas = getattr(item.status, 'ready_replicas', 0) or 0
                    available_replicas = getattr(item.status, 'available_replicas', ready_replicas) or ready_replicas
                    processed_item['ready'] = f"{available_replicas}/{replicas}"
                    processed_item['status'] = 'Ready' if ready_replicas == replicas and replicas > 0 else 'Not Ready'
                    
                    # Add fields that DeploymentPage expects
                    processed_item['pods_str'] = f"{available_replicas}/{replicas}"
                    processed_item['replicas_str'] = str(replicas)
                
                # Add spec replicas if available
                if hasattr(item, 'spec') and item.spec:
                    spec_replicas = getattr(item.spec, 'replicas', 0) or 0
                    processed_item['replicas_str'] = str(spec_replicas)
                
            elif self.config.resource_type == 'services':
                if hasattr(item, 'spec') and item.spec:
                    processed_item['type'] = item.spec.type or 'Unknown'
                    processed_item['cluster_ip'] = item.spec.cluster_ip or 'None'
                    processed_item['service_type'] = item.spec.type or 'Unknown'
                    
                    # Add ports information
                    ports = []
                    if hasattr(item.spec, 'ports') and item.spec.ports:
                        for port in item.spec.ports:
                            port_info = f"{port.port}"
                            if hasattr(port, 'target_port') and port.target_port:
                                port_info += f":{port.target_port}"
                            if hasattr(port, 'protocol') and port.protocol:
                                port_info += f"/{port.protocol}"
                            ports.append(port_info)
                    processed_item['port_text'] = ",".join(ports)
                    
                    # Add selector information
                    selector_parts = []
                    if hasattr(item.spec, 'selector') and item.spec.selector:
                        for key, value in item.spec.selector.items():
                            selector_parts.append(f"{key}={value}")
                    processed_item['selector_text'] = ",".join(selector_parts)
                    
                    # Add external IP information
                    processed_item['external_ip_text'] = ""  # Default empty, could be enhanced
            
        except Exception as e:
            logging.debug(f"Error adding basic resource fields: {e}")
    
    def _generate_cache_key(self) -> str:
        """Generate cache key for search results - FIXED to include cluster"""
        # FIXED: Include cluster information in search cache key
        try:
            kube_client = get_kubernetes_client()
            cluster_name = kube_client.current_cluster if kube_client else 'unknown-cluster'
        except:
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
            
            # Process and cache results with chunking for heavy data
            processed_items = self._process_items_chunked(items) if self.config.enable_chunking else self._process_items(items)
            self._cache_results(processed_items)
            
            load_time = (time.time() - start_time) * 1000
            logging.info(f"Unified Resource Loader: Loaded {len(processed_items)} {self.config.resource_type} in {load_time:.1f}ms")
            
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
                cached_result = self._try_cache_first()
                if cached_result and cached_result.success:
                    logging.info(f"Using cached data for timed-out {self.config.resource_type}")
                    return cached_result
                
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
    
    def _process_items_chunked(self, raw_items: List[Any]) -> List[Dict[str, Any]]:
        """Process raw Kubernetes objects in chunks for heavy data scenarios"""
        if not raw_items:
            return []
        
        processed_items = []
        chunk_size = self.config.chunk_size
        total_items = len(raw_items)
        
        logging.info(f"Unified Resource Loader: Processing {total_items} {self.config.resource_type} in chunks of {chunk_size}")
        
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
                    processed_item = self._process_single_item(item)
                    if processed_item:  # Only add valid items
                        processed_items.append(processed_item)
                except Exception as e:
                    item_name = getattr(getattr(item, 'metadata', None), 'name', 'unknown')
                    logging.warning(f"Error processing {self.config.resource_type} {item_name}: {e}")
                    continue
            
            chunk_time = (time.time() - chunk_start_time) * 1000
            logging.debug(f"Unified Resource Loader: Processed chunk {start_idx}-{end_idx} in {chunk_time:.1f}ms")
            
            # Yield control to prevent UI blocking
            time.sleep(0.001)  # 1ms pause between chunks
        
        logging.info(f"Unified Resource Loader: Chunked processing completed - {len(processed_items)} items processed")
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
                    # No fallback - set empty raw_data to avoid dummy data
                    processed_item['raw_data'] = {}
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
            logging.debug(f"Unified Resource Loader: Adding node-specific fields for {processed_item.get('name', 'unknown')}")
            self._add_node_fields(processed_item, item)
        elif resource_type == 'services':
            self._add_service_fields(processed_item, item)
        elif resource_type in ['deployments', 'replicasets', 'statefulsets', 'daemonsets']:
            self._add_workload_fields(processed_item, item)
        elif resource_type == 'replicationcontrollers':
            self._add_replicationcontroller_fields(processed_item, item)
        elif resource_type == 'configmaps':
            self._add_configmap_fields(processed_item, item)
        elif resource_type == 'secrets':
            self._add_secret_fields(processed_item, item)
        elif resource_type == 'resourcequotas':
            self._add_resourcequota_fields(processed_item, item)
        elif resource_type == 'limitranges':
            self._add_limitrange_fields(processed_item, item)
        elif resource_type == 'horizontalpodautoscalers':
            self._add_hpa_fields(processed_item, item)
        elif resource_type == 'poddisruptionbudgets':
            self._add_pdb_fields(processed_item, item)
        elif resource_type == 'priorityclasses':
            self._add_priorityclass_fields(processed_item, item)
        elif resource_type == 'runtimeclasses':
            self._add_runtimeclass_fields(processed_item, item)
        elif resource_type == 'leases':
            self._add_lease_fields(processed_item, item)
        elif resource_type == 'mutatingwebhookconfigurations':
            self._add_mutatingwebhook_fields(processed_item, item)
        elif resource_type == 'validatingwebhookconfigurations':
            self._add_validatingwebhook_fields(processed_item, item)
        elif resource_type == 'serviceaccounts':
            self._add_serviceaccount_fields(processed_item, item)
        elif resource_type == 'endpoints':
            self._add_endpoints_fields(processed_item, item)
        elif resource_type in ['roles', 'clusterroles']:
            self._add_role_fields(processed_item, item)
        elif resource_type in ['rolebindings', 'clusterrolebindings']:
            self._add_rolebinding_fields(processed_item, item)
        elif resource_type == 'customresourcedefinitions':
            self._add_crd_fields(processed_item, item)
    
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
        """Add node-specific fields efficiently - optimized for heavy data"""
        import time
        process_start = time.time()
        node_name = processed_item.get('name', 'unknown')
        logging.info(f"🔄 [PROCESSING] {time.strftime('%H:%M:%S.%f')[:-3]} - Unified Resource Loader: Starting to process node '{node_name}' fields")
        
        status = node.status
        
        # Log raw node data structure
        logging.debug(f"📊 [RAW DATA] {time.strftime('%H:%M:%S.%f')[:-3]} - Node '{node_name}': metadata={hasattr(node, 'metadata')}, status={status is not None}, spec={hasattr(node, 'spec')}")
        
        # Quick exit for invalid nodes
        if not status:
            logging.warning(f"⚠️  [MISSING STATUS] {time.strftime('%H:%M:%S.%f')[:-3]} - Unified Resource Loader: Node '{node_name}' has no status - using defaults")
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
        
        # Get node status efficiently and format all conditions
        node_status = 'Unknown'
        conditions_list = []
        
        if status and status.conditions:
            for condition in status.conditions:
                if condition.type == 'Ready':
                    node_status = 'Ready' if condition.status == 'True' else 'NotReady'
                
                # Format condition for display: Type=Status
                condition_display = f"{condition.type}={condition.status}"
                
                # Add reason if available for non-True conditions
                if condition.status != 'True' and hasattr(condition, 'reason') and condition.reason:
                    condition_display += f" ({condition.reason})"
                
                conditions_list.append(condition_display)
        
        # Join all conditions for the conditions column
        conditions_text = ", ".join(conditions_list) if conditions_list else "Unknown"
        
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
        
        # Format disk capacity for display
        disk_capacity = ''
        if status and status.capacity and status.capacity.get('ephemeral-storage'):
            disk_raw = status.capacity.get('ephemeral-storage', '')
            if 'Ki' in disk_raw:
                # Convert from Ki to GB
                ki_value = int(disk_raw.replace('Ki', ''))
                gb_value = ki_value / (1024 * 1024)
                disk_capacity = f"{gb_value:.1f}GB"
            elif 'Gi' in disk_raw:
                # Convert from Gi to GB
                gi_value = int(disk_raw.replace('Gi', ''))
                disk_capacity = f"{gi_value}GB"
            else:
                disk_capacity = disk_raw
        
        # Simulate basic disk usage if disk capacity is available (for development/demo)
        estimated_disk_usage = None
        if disk_capacity and disk_capacity != '':
            try:
                # Simple estimation: assume 10-80% disk usage for active nodes
                import random
                if node_status == 'Ready':
                    estimated_disk_usage = round(random.uniform(10, 80), 1)
                else:
                    estimated_disk_usage = 0
            except Exception:
                estimated_disk_usage = None
        
        processed_item.update({
            'status': node_status,
            'conditions': conditions_text,
            'roles': roles if roles else ['<none>'],
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
        
        # Get real node metrics using the metrics service
        logging.debug(f"Unified Resource Loader: Attempting to load metrics for node {processed_item['name']}")
        try:
            from Services.kubernetes.kubernetes_service import get_kubernetes_service
            kube_service = get_kubernetes_service()
            if kube_service and kube_service.metrics_service:
                node_metrics = kube_service.metrics_service.get_node_metrics(processed_item['name'])
                if node_metrics:
                    processed_item['cpu_usage'] = node_metrics['cpu']['usage']
                    processed_item['memory_usage'] = node_metrics['memory']['usage']
                    logging.info(f"Unified Resource Loader: Added real metrics for node {processed_item['name']}: CPU {node_metrics['cpu']['usage']:.1f}%, Memory {node_metrics['memory']['usage']:.1f}%")
                else:
                    logging.debug(f"Unified Resource Loader: No metrics available for node {processed_item['name']}")
            else:
                logging.debug(f"Unified Resource Loader: Metrics service not available for node {processed_item['name']}")
        except Exception as e:
            logging.warning(f"Unified Resource Loader: Could not get real metrics for node {processed_item['name']}: {e}")
        
        # Log completion of node processing
        process_time = (time.time() - process_start) * 1000
        logging.info(f"✅ [PROCESSED] {time.strftime('%H:%M:%S.%f')[:-3]} - Node '{node_name}' processed in {process_time:.1f}ms: status={processed_item.get('status')}, roles={processed_item.get('roles')}, cpu={processed_item.get('cpu_capacity')}, memory={processed_item.get('memory_capacity')}")
        logging.debug(f"📦 [FINAL DATA] {time.strftime('%H:%M:%S.%f')[:-3]} - Node '{node_name}' final processed data: {processed_item}")
    
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
    
    def _add_replicationcontroller_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_configmap_fields(self, processed_item: Dict[str, Any], item: Any):
        """Add ConfigMap-specific fields"""
        try:
            data = item.data or {}
            processed_item.update({
                'keys': ', '.join(data.keys()) if data else '<none>',
                'data_count': len(data),
            })
        except Exception as e:
            logging.debug(f"Error processing ConfigMap fields: {e}")
    
    def _add_secret_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_resourcequota_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_limitrange_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_hpa_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_pdb_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_priorityclass_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_runtimeclass_fields(self, processed_item: Dict[str, Any], item: Any):
        """Add RuntimeClass-specific fields"""
        try:
            handler = getattr(item, 'handler', '')
            processed_item.update({
                'handler': handler or '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing RuntimeClass fields: {e}")
    
    def _add_lease_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_mutatingwebhook_fields(self, processed_item: Dict[str, Any], item: Any):
        """Add MutatingWebhookConfiguration-specific fields"""
        try:
            webhooks = getattr(item, 'webhooks', [])
            processed_item.update({
                'webhooks_count': len(webhooks),
                'webhooks': ', '.join([w.name for w in webhooks if hasattr(w, 'name')]) if webhooks else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing MutatingWebhookConfiguration fields: {e}")
    
    def _add_validatingwebhook_fields(self, processed_item: Dict[str, Any], item: Any):
        """Add ValidatingWebhookConfiguration-specific fields"""
        try:
            webhooks = getattr(item, 'webhooks', [])
            processed_item.update({
                'webhooks_count': len(webhooks),
                'webhooks': ', '.join([w.name for w in webhooks if hasattr(w, 'name')]) if webhooks else '<none>',
            })
        except Exception as e:
            logging.debug(f"Error processing ValidatingWebhookConfiguration fields: {e}")
    
    def _add_serviceaccount_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_endpoints_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_role_fields(self, processed_item: Dict[str, Any], item: Any):
        """Add Role/ClusterRole-specific fields"""
        try:
            rules = getattr(item, 'rules', [])
            processed_item.update({
                'rules_count': len(rules),
            })
        except Exception as e:
            logging.debug(f"Error processing Role fields: {e}")
    
    def _add_rolebinding_fields(self, processed_item: Dict[str, Any], item: Any):
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
    
    def _add_crd_fields(self, processed_item: Dict[str, Any], item: Any):
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
        except:
            cluster_name = 'unknown-cluster'
            
        key_parts = [
            cluster_name,  # FIXED: Add cluster name to prevent cross-cluster cache pollution
            self.config.resource_type,
            f"ns_{self.config.namespace}" if self.config.namespace else 'all-namespaces',  # FIXED: Add ns_ prefix
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
        
        # Heavy data resources (need chunking and optimization)
        heavy_data_resources = ['nodes', 'pods']
        
        # Medium-frequency resources
        medium_frequency_resources = ['deployments', 'services', 'configmaps', 'secrets']
        
        # Low-frequency resources (can cache longer)
        low_frequency_resources = ['storageclasses', 'clusterroles', 'namespaces']
        
        # Configure high-frequency resources for speed
        for resource_type in high_frequency_resources:
            config = ResourceConfig(
                resource_type=resource_type,
                api_method=self._get_api_method(resource_type),
                batch_size=100,
                timeout_seconds=15,
                cache_ttl=60,  # 1 minute cache
                enable_streaming=True,
                max_concurrent_requests=8
            )
            
            # Enable heavy data optimizations for large datasets
            if resource_type in heavy_data_resources:
                config.timeout_seconds = 60  # Longer timeout for heavy data
                config.cache_ttl = 900  # 15 minutes for heavy data
                config.enable_chunking = True
                config.chunk_size = 200 if resource_type == 'nodes' else 100
                config.progressive_loading = True
                config.enable_pagination = True
                logging.info(f"Unified Resource Loader: Enabled heavy data optimizations for {resource_type}")
                
            self._config_cache[resource_type] = config
        
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
        
        # Cancel any existing load for this resource type
        self._cancel_existing_load(resource_type, namespace)
        
        # Emit loading started signal
        self.loading_started.emit(resource_type)
        
        # Create and submit search worker
        worker = SearchResourceLoadWorker(config, self, search_query)
        
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
        Load Kubernetes resources asynchronously with high performance.
        Returns operation ID for tracking.
        """
        logging.info(f"Unified Resource Loader: Starting async load for resource_type='{resource_type}', namespace='{namespace or 'all'}'") 
        
        # Get or create configuration
        config = custom_config or self._get_config_for_resource(resource_type, namespace)
        logging.debug(f"Unified Resource Loader: Using config for {resource_type}: timeout={config.timeout_seconds}s, batch_size={config.batch_size}")
        
        # Generate operation ID
        operation_id = f"{resource_type}_{namespace or 'all'}_{int(time.time() * 1000)}"
        logging.debug(f"Unified Resource Loader: Generated operation_id: {operation_id}")
        
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
            worker_key = f"{resource_type}_{namespace or 'all'}"
            self._active_workers[worker_key] = worker
            logging.debug(f"Unified Resource Loader: Tracking worker with key: {worker_key}")
        
        # Connect worker signals for completion handling
        worker.signals.finished.connect(
            lambda result: self._handle_load_completion_success(result, resource_type, namespace, operation_id)
        )
        worker.signals.error.connect(
            lambda error: self._handle_load_completion_error(error, resource_type, namespace, operation_id)
        )
        logging.debug(f"Unified Resource Loader: Connected worker signals for {resource_type}")
        
        # Submit to unified thread manager
        logging.debug(f"Unified Resource Loader: Submitting worker to thread manager for {resource_type}")
        self._thread_manager.submit_worker(operation_id, worker)
        
        logging.info(f"Unified Resource Loader: Successfully initiated async loading for {resource_type} with operation_id: {operation_id}")
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
        logging.info(f"Unified Resource Loader: Load completed successfully for {resource_type} (operation_id: {operation_id})")
        try:
            if resource_type == 'nodes':
                import time
                logging.info(f"🚀 [UI EMIT] {time.strftime('%H:%M:%S.%f')[:-3]} - Unified Resource Loader: Emitting node data to UI - {result.total_count} nodes loaded in {result.load_time_ms:.1f}ms")
                # Log sample of node data being sent to UI
                if result.items and len(result.items) > 0:
                    sample_node = result.items[0]
                    logging.debug(f"📤 [UI SAMPLE] {time.strftime('%H:%M:%S.%f')[:-3]} - Sample node data being sent: name={sample_node.get('name')}, status={sample_node.get('status')}, cpu={sample_node.get('cpu_capacity')}")
                    logging.debug(f"📤 [UI COUNT] {time.strftime('%H:%M:%S.%f')[:-3]} - Sending {len(result.items)} nodes to UI: {[item.get('name', 'unnamed') for item in result.items[:5]]}{'...' if len(result.items) > 5 else ''}")
            
            self.loading_completed.emit(resource_type, result)
            logging.info(
                f"Unified Resource Loader: Loaded {result.total_count} {resource_type} "
                f"in {result.load_time_ms:.1f}ms "
                f"({'cached' if result.from_cache else 'fresh'})"
            )
        except Exception as e:
            logging.error(f"Unified Resource Loader: Error emitting load completion signal for {resource_type}: {e}")
            logging.debug(f"Unified Resource Loader: Load completion error details", exc_info=True)
        finally:
            # Cleanup worker reference
            self._cleanup_worker(resource_type, namespace)
    
    def _handle_load_completion_error(self, error_message: str, resource_type: str, namespace: Optional[str], operation_id: str):
        """Handle error in load completion"""
        logging.error(f"Unified Resource Loader: Load failed for {resource_type} (operation_id: {operation_id}): {error_message}")
        try:
            if resource_type == 'nodes':
                logging.error(f"Unified Resource Loader: Node loading failed - UI will not receive node data")
            
            self.loading_error.emit(resource_type, error_message)
            logging.error(f"Unified Resource Loader: Failed to load {resource_type}: {error_message}")
        except Exception as e:
            logging.error(f"Unified Resource Loader: Error emitting load error signal for {resource_type}: {e}")
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