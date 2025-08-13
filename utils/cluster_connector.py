"""
Enhanced Kubernetes Cluster Connector - Single Responsibility Version
Replaces the complex monolithic cluster_connector.py with a clean, maintainable solution.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from utils.kubernetes_client import get_kubernetes_client
from utils.enhanced_worker import EnhancedBaseWorker
from utils.thread_manager import get_thread_manager
from utils.unified_resource_loader import get_unified_resource_loader
from log_handler import method_logger, class_logger


@dataclass
class ClusterMetrics:
    """Data structure for cluster metrics"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    pods_count: int = 0
    nodes_count: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class NodeInfo:
    """Data structure for processed node information"""
    name: str
    status: str
    roles: List[str]
    cpu_capacity: str
    memory_capacity: str
    disk_capacity: str
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    taints: str = "0"
    version: str = "Unknown"
    age: str = "Unknown"
    raw_data: Optional[Dict] = None


@dataclass  
class ConnectionState:
    """Thread-safe connection state"""
    cluster_name: str
    is_connected: bool = False
    is_connecting: bool = False
    last_error: Optional[str] = None
    connected_at: Optional[float] = None
    
    def __post_init__(self):
        self._lock = threading.RLock()
    
    def update_state(self, connected: bool, connecting: bool = False, error: str = None):
        """Thread-safe state update"""
        with self._lock:
            self.is_connected = connected
            self.is_connecting = connecting
            if error:
                self.last_error = error
            if connected:
                self.connected_at = time.time()
                self.last_error = None


# DataCache class replaced by unified cache system
# Now using get_unified_cache() for all caching needs


class ClusterConnectionWorker(EnhancedBaseWorker):
    """Worker for establishing cluster connections"""
    
    def __init__(self, client, cluster_name: str):
        super().__init__(f"cluster_connection_{cluster_name}")
        self.client = client
        self.cluster_name = cluster_name
        self._timeout = 30
    
    def execute(self) -> Tuple[str, bool, str]:
        """Execute connection attempt"""
        try:
            # Attempt to switch context
            success = self.client.switch_context(self.cluster_name)
            if not success:
                return self.cluster_name, False, "Failed to switch cluster context"
            
            # Validate connection with version check
            version_info = self.client.version_api.get_code()
            if not version_info:
                return self.cluster_name, False, "Failed to validate cluster connection"
            
            message = f"Connected to Kubernetes {version_info.git_version}"
            return self.cluster_name, True, message
            
        except Exception as e:
            error_msg = self._format_error(str(e))
            return self.cluster_name, False, error_msg
    
    def _format_error(self, error: str) -> str:
        """Format error message for user display"""
        error_lower = error.lower()
        
        if "docker-desktop" in self.cluster_name.lower() and "refused" in error_lower:
            return "Docker Desktop Kubernetes is not running. Please start Docker Desktop and enable Kubernetes."
        elif "timeout" in error_lower:
            return f"Connection timeout. Check if cluster '{self.cluster_name}' is accessible."
        elif "certificate" in error_lower:
            return f"Certificate error. Check your kubeconfig for '{self.cluster_name}'."
        else:
            return f"Connection failed: {error[:100]}"


class DataLoadWorker(EnhancedBaseWorker):
    """Worker for loading various types of cluster data"""
    
    def __init__(self, client, data_type: str, cluster_name: str, processor: Callable = None):
        super().__init__(f"{data_type}_load_{cluster_name}")
        self.client = client
        self.data_type = data_type
        self.cluster_name = cluster_name
        self.processor = processor or self._default_processor
    
    def execute(self) -> Tuple[str, Any]:
        """Execute data loading"""
        try:
            if self.data_type == "nodes":
                data = self.client._get_nodes()
            elif self.data_type == "metrics":
                self.client.get_cluster_metrics_async()
                return self.data_type, None  # Metrics are handled via signals
            elif self.data_type == "issues":
                self.client.get_cluster_issues_async()
                return self.data_type, None  # Issues are handled via signals
            elif self.data_type == "cluster_info":
                data = self.client.get_cluster_info(self.cluster_name)
            else:
                raise ValueError(f"Unknown data type: {self.data_type}")
            
            processed_data = self.processor(data) if data else None
            return self.data_type, processed_data
            
        except Exception as e:
            logging.error(f"Error loading {self.data_type} for {self.cluster_name}: {e}")
            raise
    
    def _default_processor(self, data: Any) -> Any:
        """Default data processor - returns data as-is"""
        return data


@class_logger(log_level=logging.INFO)
class EnhancedClusterConnector(QObject):
    """
    Enhanced Kubernetes Cluster Connector with single responsibility design.
    Replaces the complex monolithic cluster_connector.py.
    """
    
    # Signals
    connection_started = pyqtSignal(str)
    connection_complete = pyqtSignal(str, bool, str)
    cluster_data_loaded = pyqtSignal(dict)
    node_data_loaded = pyqtSignal(list)
    metrics_data_loaded = pyqtSignal(dict)
    issues_data_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        
        # Core dependencies
        self.kube_client = get_kubernetes_client()
        self.thread_manager = get_thread_manager()
        
        # State management (thread-safe)
        self._connection_states: Dict[str, ConnectionState] = {}
        self._current_cluster: Optional[str] = None
        self._state_lock = threading.RLock()
        
        # Data management
        # Use unified cache system instead of custom DataCache
        from utils.unified_cache_system import get_unified_cache
        self._cache = get_unified_cache()
        
        # Polling management
        self._polling_active = False
        self._polling_lock = threading.RLock()
        self._metrics_timer = QTimer()
        self._issues_timer = QTimer()
        self._cleanup_timer = QTimer()
        
        # Shutdown management
        self._shutting_down = False
        self._active_workers = set()
        self._workers_lock = threading.RLock()
        
        # Initialize
        self._setup_timers()
        self._connect_client_signals()
        self._connect_resource_loader_signals()
        
        logging.info("Enhanced Cluster Connector initialized")
    
    def _setup_timers(self):
        """Initialize and configure timers"""
        # Metrics polling timer
        self._metrics_timer.timeout.connect(self._poll_metrics)
        
        # Issues polling timer  
        self._issues_timer.timeout.connect(self._poll_issues)
        
        # Cache cleanup timer
        self._cleanup_timer.timeout.connect(self._cleanup_cache)
        self._cleanup_timer.start(60000)  # Cleanup every minute
    
    def _connect_client_signals(self):
        """Connect to Kubernetes client signals"""
        try:
            # Disconnect existing connections first
            try:
                self.kube_client.cluster_info_loaded.disconnect()
                self.kube_client.cluster_metrics_updated.disconnect()  
                self.kube_client.cluster_issues_updated.disconnect()
                self.kube_client.error_occurred.disconnect()
            except (TypeError, RuntimeError):
                pass  # No existing connections
            
            # Connect signals
            self.kube_client.cluster_info_loaded.connect(self._handle_cluster_info)
            self.kube_client.cluster_metrics_updated.connect(self._handle_metrics_update)
            self.kube_client.cluster_issues_updated.connect(self._handle_issues_update)
            self.kube_client.error_occurred.connect(self._handle_client_error)
            
        except Exception as e:
            logging.error(f"Error connecting client signals: {e}")
    
    def _connect_resource_loader_signals(self):
        """Connect to unified resource loader signals"""
        try:
            from utils.unified_resource_loader import get_unified_resource_loader
            unified_loader = get_unified_resource_loader()
            
            # Connect to resource loading completion signal
            unified_loader.loading_completed.connect(self._handle_resource_loading_completed)
            unified_loader.loading_error.connect(self._handle_resource_loading_error)
            
            logging.info("Connected to unified resource loader signals")
        except Exception as e:
            logging.error(f"Error connecting resource loader signals: {e}")
    
    def _handle_resource_loading_completed(self, resource_type: str, load_result):
        """Handle completion of resource loading from unified loader"""
        try:
            if resource_type == "nodes" and load_result.success:
                # The unified loader already processed the data into dictionaries
                # No need to process again - just emit the processed data
                nodes_data = load_result.items
                
                logging.info(f"Received {len(nodes_data)} processed nodes from unified loader")
                
                # Emit the processed data directly
                self.node_data_loaded.emit(nodes_data)
                logging.info(f"Emitted {len(nodes_data)} processed nodes to UI")
                
        except Exception as e:
            logging.error(f"Error handling resource loading completion: {e}")
            self.error_occurred.emit(resource_type, str(e))
    
    def _handle_resource_loading_error(self, resource_type: str, error_message: str):
        """Handle resource loading errors from unified loader"""
        logging.error(f"Resource loading error for {resource_type}: {error_message}")
        self.error_occurred.emit(resource_type, error_message)
    
    @property
    def current_cluster(self) -> Optional[str]:
        """Thread-safe current cluster getter"""
        with self._state_lock:
            return self._current_cluster
    
    def connect_to_cluster(self, cluster_name: str) -> None:
        """Connect to a Kubernetes cluster"""
        if self._shutting_down:
            return
        
        with self._state_lock:
            # Initialize connection state if needed
            if cluster_name not in self._connection_states:
                self._connection_states[cluster_name] = ConnectionState(cluster_name)
            
            connection_state = self._connection_states[cluster_name]
            
            # Check if already connected
            if connection_state.is_connected:
                logging.info(f"Already connected to {cluster_name}")
                self.connection_complete.emit(cluster_name, True, "Already connected")
                return
            
            # Check if currently connecting
            if connection_state.is_connecting:
                logging.info(f"Already connecting to {cluster_name}")
                return
            
            # Update state and start connection
            connection_state.update_state(connected=False, connecting=True)
        
        self.connection_started.emit(cluster_name)
        self._start_connection_worker(cluster_name)
    
    def _start_connection_worker(self, cluster_name: str) -> None:
        """Start connection worker for cluster"""
        worker = ClusterConnectionWorker(self.kube_client, cluster_name)
        
        # Setup worker callbacks
        worker.signals.finished.connect(self._handle_connection_complete)
        worker.signals.error.connect(lambda error: self._handle_connection_error(cluster_name, str(error)))
        
        # Track worker
        with self._workers_lock:
            self._active_workers.add(worker)
        
        # Submit to thread manager
        self.thread_manager.submit_worker(f"connect_{cluster_name}", worker)
    
    def _handle_connection_complete(self, result: Tuple[str, bool, str]) -> None:
        """Handle connection completion"""
        if self._shutting_down:
            return
        
        cluster_name, success, message = result
        
        with self._state_lock:
            if cluster_name in self._connection_states:
                self._connection_states[cluster_name].update_state(
                    connected=success, 
                    connecting=False,
                    error=None if success else message
                )
                
                if success:
                    self._current_cluster = cluster_name
        
        self.connection_complete.emit(cluster_name, success, message)
        
        # Start data loading and polling if successful
        if success:
            self._start_data_loading(cluster_name)
            self._start_polling()
    
    def _handle_connection_error(self, cluster_name: str, error_message: str) -> None:
        """Handle connection errors"""
        with self._state_lock:
            if cluster_name in self._connection_states:
                self._connection_states[cluster_name].update_state(
                    connected=False, 
                    connecting=False, 
                    error=error_message
                )
        
        self.connection_complete.emit(cluster_name, False, error_message)
        self.error_occurred.emit("connection", error_message)
    
    def _start_data_loading(self, cluster_name: str) -> None:
        """Start loading initial data for cluster"""
        # Load cluster info
        self._start_data_worker("cluster_info", cluster_name)
        
        # Load nodes
        self._start_data_worker("nodes", cluster_name, self._process_nodes_data)
        
        # Start metrics and issues loading (via signals)
        self._start_data_worker("metrics", cluster_name)
        self._start_data_worker("issues", cluster_name)
    
    def _start_data_worker(self, data_type: str, cluster_name: str, processor: Callable = None) -> None:
        """Start a data loading worker"""
        worker = DataLoadWorker(self.kube_client, data_type, cluster_name, processor)
        
        # Setup callbacks
        worker.signals.finished.connect(self._handle_data_loaded)
        worker.signals.error.connect(lambda error: self._handle_data_error(data_type, str(error)))
        
        # Track worker
        with self._workers_lock:
            self._active_workers.add(worker)
        
        # Submit to thread manager
        self.thread_manager.submit_worker(f"{data_type}_{cluster_name}", worker)
    
    def _handle_data_loaded(self, result: Tuple[str, Any]) -> None:
        """Handle data loading completion"""
        if self._shutting_down:
            return
        
        data_type, data = result
        
        if data is None:
            return  # Some data types (metrics, issues) are handled via signals
        
        # Cache the data
        cache_key = f"{self.current_cluster}:{data_type}"
        self._cache.cache_resources('cluster_data', cache_key, data)
        
        # Emit appropriate signal
        if data_type == "cluster_info":
            self.cluster_data_loaded.emit(data)
        elif data_type == "nodes":
            self.node_data_loaded.emit(data)
    
    def _handle_data_error(self, data_type: str, error_message: str) -> None:
        """Handle data loading errors"""
        logging.error(f"Error loading {data_type}: {error_message}")
        self.error_occurred.emit(f"{data_type}_loading", error_message)
    
    def _process_nodes_data(self, raw_nodes: List) -> List[NodeInfo]:
        """Process raw Kubernetes node objects into NodeInfo objects"""
        if not raw_nodes:
            return []
        
        processed_nodes = []
        
        for node in raw_nodes:
            try:
                # Extract basic information
                node_name = node.metadata.name
                node_labels = node.metadata.labels or {}
                
                # Determine status
                conditions = node.status.conditions or []
                status = "Unknown"
                for condition in conditions:
                    if condition.type == "Ready":
                        status = "Ready" if condition.status == "True" else "NotReady"
                        break
                
                # Extract capacity
                capacity = node.status.capacity or {}
                cpu_capacity = capacity.get("cpu", "")
                memory_capacity = self._format_memory_capacity(capacity.get("memory", ""))
                storage_capacity = self._format_storage_capacity(capacity.get("ephemeral-storage", ""))
                
                # Extract roles
                roles = self._extract_node_roles(node_labels)
                
                # Extract other info
                taints_count = len(node.spec.taints) if node.spec.taints else 0
                kubelet_version = node.status.node_info.kubelet_version if node.status.node_info else "Unknown"
                age = self._calculate_age(node.metadata.creation_timestamp)
                
                # Create NodeInfo object
                node_info = NodeInfo(
                    name=node_name,
                    status=status,
                    roles=roles,
                    cpu_capacity=cpu_capacity,
                    memory_capacity=memory_capacity,
                    disk_capacity=storage_capacity,
                    taints=str(taints_count),
                    version=kubelet_version,
                    age=age,
                    raw_data=self.kube_client.v1.api_client.sanitize_for_serialization(node)
                )
                
                processed_nodes.append(node_info)
                
            except Exception as e:
                logging.error(f"Error processing node {getattr(node, 'metadata', {}).get('name', 'unknown')}: {e}")
                continue
        
        logging.info(f"Processed {len(processed_nodes)} nodes")
        return processed_nodes
    
    def _format_memory_capacity(self, memory_str: str) -> str:
        """Format memory capacity for display"""
        if not memory_str:
            return ""
        
        try:
            if "Ki" in memory_str:
                memory_ki = int(memory_str.replace("Ki", ""))
                memory_gb = round(memory_ki / 1024 / 1024, 1)
                return f"{memory_gb}GB"
            elif "Mi" in memory_str:
                memory_mi = int(memory_str.replace("Mi", ""))
                memory_gb = round(memory_mi / 1024, 1)
                return f"{memory_gb}GB"
            elif "Gi" in memory_str:
                memory_gi = int(memory_str.replace("Gi", ""))
                return f"{memory_gi}GB"
        except (ValueError, TypeError):
            pass
        
        return memory_str
    
    def _format_storage_capacity(self, storage_str: str) -> str:
        """Format storage capacity for display"""
        return self._format_memory_capacity(storage_str)  # Same logic
    
    def _extract_node_roles(self, labels: Dict[str, str]) -> List[str]:
        """Extract node roles from labels"""
        roles = []
        for label_key in labels:
            if "node-role.kubernetes.io/" in label_key:
                role = label_key.replace("node-role.kubernetes.io/", "")
                if role:
                    roles.append(role)
        
        return roles if roles else ["<none>"]
    
    def _calculate_age(self, creation_timestamp) -> str:
        """Calculate age string from creation timestamp"""
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
        except Exception as e:
            logging.error(f"Error calculating age: {e}")
            return "Unknown"
    
    def _start_polling(self) -> None:
        """Start polling for metrics and issues"""
        with self._polling_lock:
            if self._polling_active or self._shutting_down:
                return
            
            self._polling_active = True
            self._metrics_timer.start(5000)   # Poll metrics every 5 seconds
            self._issues_timer.start(10000)   # Poll issues every 10 seconds
    
    def _stop_polling(self) -> None:
        """Stop all polling"""
        with self._polling_lock:
            self._polling_active = False
            self._metrics_timer.stop()
            self._issues_timer.stop()
    
    def _poll_metrics(self) -> None:
        """Poll for cluster metrics"""
        if self._shutting_down or not self.current_cluster:
            return
        
        try:
            self.kube_client.get_cluster_metrics_async()
        except Exception as e:
            logging.warning(f"Error polling metrics: {e}")
    
    def _poll_issues(self) -> None:
        """Poll for cluster issues"""
        if self._shutting_down or not self.current_cluster:
            return
        
        try:
            self.kube_client.get_cluster_issues_async()
        except Exception as e:
            logging.warning(f"Error polling issues: {e}")
    
    def _handle_cluster_info(self, info: Dict) -> None:
        """Handle cluster info updates from client"""
        if self._shutting_down:
            return
        
        cluster_name = getattr(self.kube_client, 'current_cluster', self.current_cluster)
        if cluster_name:
            cache_key = f"{cluster_name}:cluster_info"
            self._cache.cache_resources('cluster_info', cache_key, info)
        
        self.cluster_data_loaded.emit(info)
    
    def _handle_metrics_update(self, metrics: Dict) -> None:
        """Handle metrics updates from client"""
        if self._shutting_down:
            return
        
        cluster_name = getattr(self.kube_client, 'current_cluster', self.current_cluster)
        if cluster_name:
            cache_key = f"{cluster_name}:metrics"
            self._cache.cache_resources('metrics', cache_key, metrics)
        
        self.metrics_data_loaded.emit(metrics)
    
    def _handle_issues_update(self, issues: List) -> None:
        """Handle issues updates from client"""
        if self._shutting_down:
            return
        
        cluster_name = getattr(self.kube_client, 'current_cluster', self.current_cluster)
        if cluster_name:
            cache_key = f"{cluster_name}:issues"
            self._cache.cache_resources('issues', cache_key, issues)
        
        self.issues_data_loaded.emit(issues)
    
    def _handle_client_error(self, error_message: str) -> None:
        """Handle Kubernetes client errors"""
        if self._shutting_down:
            return
        
        # Filter out non-critical errors
        error_lower = error_message.lower()
        if any(keyword in error_lower for keyword in [
            'connection refused', 'timeout', 'certificate', 'authentication',
            'authorization', 'permission denied', 'config'
        ]):
            self.error_occurred.emit("kubernetes", error_message)
        else:
            logging.warning(f"Kubernetes client error (suppressed): {error_message}")
    
    def _cleanup_cache(self) -> None:
        """Periodic cache cleanup - handled by unified cache system"""
        try:
            self._cache.optimize_caches()
            logging.debug("Cache optimization completed")
        except Exception as e:
            logging.error(f"Error during cache cleanup: {e}")
    
    def disconnect_cluster(self, cluster_name: str) -> None:
        """Disconnect from a cluster"""
        with self._state_lock:
            if cluster_name in self._connection_states:
                self._connection_states[cluster_name].update_state(connected=False)
            
            if self._current_cluster == cluster_name:
                self._current_cluster = None
                self._stop_polling()
        
        # Clear cache for this cluster
        # Clear cluster data from unified cache
        self._cache.clear_resource_cache(f'cluster_{cluster_name}')
        
        logging.info(f"Disconnected from cluster: {cluster_name}")
    
    def load_nodes(self):
        """Load nodes data using unified resource loader"""
        try:
            unified_loader = get_unified_resource_loader()
            operation_id = unified_loader.load_resources_async('nodes')
            logging.info(f"Started loading nodes, operation_id: {operation_id}")
        except Exception as e:
            error_msg = f"Failed to load nodes: {e}"
            logging.error(error_msg)
            self.error_occurred.emit("nodes", error_msg)
    
    def get_cached_data(self, cluster_name: str) -> Dict[str, Any]:
        """Get cached data for a cluster"""
        cached_data = {}
        
        data_types = ["cluster_info", "metrics", "issues", "nodes"]
        for data_type in data_types:
            cache_key = f"{cluster_name}:{data_type}"
            data = self._cache.get_cached_resources('cluster_data', cache_key)
            if data:
                cached_data[data_type] = data
        
        return cached_data
    
    def get_connection_state(self, cluster_name: str) -> str:
        """Get current connection state for a cluster"""
        with self._state_lock:
            if cluster_name not in self._connection_states:
                return "disconnected"
            
            state = self._connection_states[cluster_name]
            if state.is_connected:
                return "connected"
            elif state.is_connecting:
                return "connecting"
            else:
                return "disconnected"
    
    def set_current_cluster(self, cluster_name: str) -> None:
        """Set the current cluster (called from ClusterView)"""
        with self._state_lock:
            if cluster_name != self._current_cluster:
                logging.info(f"Setting current cluster to {cluster_name}")
                self._current_cluster = cluster_name
                
                if cluster_name in self._connection_states:
                    self._connection_states[cluster_name].update_state(connected=True)
    
    def cleanup(self) -> None:
        """Cleanup all resources"""
        logging.info("Starting Enhanced Cluster Connector cleanup")
        self._shutting_down = True
        
        # Stop polling
        self._stop_polling()
        self._cleanup_timer.stop()
        
        # Cancel active workers
        with self._workers_lock:
            for worker in list(self._active_workers):
                if hasattr(worker, 'cancel'):
                    worker.cancel()
            self._active_workers.clear()
        
        # Clear cache
        # Clear all caches using unified cache system
        self._cache.clear_all_caches()
        
        # Reset state
        with self._state_lock:
            self._connection_states.clear()
            self._current_cluster = None
        
        logging.info("Enhanced Cluster Connector cleanup completed")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_shutting_down') and not self._shutting_down:
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in Enhanced Cluster Connector destructor: {e}")


# Singleton management
_connector_instance = None

def get_cluster_connector() -> EnhancedClusterConnector:
    """Get or create the cluster connector singleton"""
    global _connector_instance
    if _connector_instance is None:
        _connector_instance = EnhancedClusterConnector()
    return _connector_instance

def shutdown_cluster_connector():
    """Shutdown the cluster connector"""
    global _connector_instance
    if _connector_instance is not None:
        _connector_instance.cleanup()
        _connector_instance = None

# Backward compatibility aliases
get_enhanced_cluster_connector = get_cluster_connector
shutdown_enhanced_cluster_connector = shutdown_cluster_connector
ClusterConnection = EnhancedClusterConnector