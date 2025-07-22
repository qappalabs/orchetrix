"""
Optimized ClusterConnector with performance improvements:
- Adaptive polling intervals based on cluster activity
- Connection pooling for reuse
- Intelligent caching with TTL
- Request batching for metrics and issues
- Memory leak prevention with automatic cleanup
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from utils.enhanced_worker import EnhancedBaseWorker
from utils.thread_manager import get_thread_manager

# Performance tuning constants
INITIAL_POLL_INTERVAL = 5000  # 5 seconds
MAX_POLL_INTERVAL = 60000     # 60 seconds  
MIN_POLL_INTERVAL = 2000      # 2 seconds
CACHE_TTL_SECONDS = 300       # 5 minutes
MAX_CACHE_SIZE_MB = 50        # Maximum cache size in MB
CONNECTION_POOL_SIZE = 5      # Number of pooled connections
BATCH_REQUEST_DELAY = 100     # Delay for batching requests in ms

class AdaptivePoller:
    """Manages adaptive polling intervals based on data change frequency"""
    
    def __init__(self, initial_interval=INITIAL_POLL_INTERVAL):
        self.current_interval = initial_interval
        self.min_interval = MIN_POLL_INTERVAL
        self.max_interval = MAX_POLL_INTERVAL
        self.change_history = deque(maxlen=10)  # Track last 10 polling results
        self.last_data_hash = None
        
    def record_poll_result(self, data_hash):
        """Record polling result and adjust interval"""
        current_time = time.time()
        data_changed = data_hash != self.last_data_hash
        
        self.change_history.append({
            'time': current_time,
            'changed': data_changed
        })
        
        self.last_data_hash = data_hash
        
        # Adjust interval based on change frequency
        if len(self.change_history) >= 3:
            recent_changes = sum(1 for h in list(self.change_history)[-5:] if h['changed'])
            
            if recent_changes >= 3:
                # Frequent changes - decrease interval
                self.current_interval = max(
                    self.min_interval,
                    int(self.current_interval * 0.8)
                )
            elif recent_changes == 0:
                # No recent changes - increase interval
                self.current_interval = min(
                    self.max_interval,
                    int(self.current_interval * 1.5)
                )
        
        return self.current_interval
    
    def reset(self):
        """Reset to initial state"""
        self.current_interval = INITIAL_POLL_INTERVAL
        self.change_history.clear()
        self.last_data_hash = None

class ConnectionPool:
    """Manages a pool of cluster connections for reuse"""
    
    def __init__(self, max_size=CONNECTION_POOL_SIZE):
        self.max_size = max_size
        self.connections = {}
        self.last_used = {}
        self.connection_timeout = 300  # 5 minutes
        
    def get_connection(self, cluster_name):
        """Get a connection from the pool"""
        self._cleanup_stale_connections()
        
        if cluster_name in self.connections:
            self.last_used[cluster_name] = time.time()
            return self.connections[cluster_name]
        
        return None
    
    def add_connection(self, cluster_name, connection):
        """Add a connection to the pool"""
        # Remove oldest connection if at capacity
        if len(self.connections) >= self.max_size:
            oldest = min(self.last_used.items(), key=lambda x: x[1])[0]
            self.remove_connection(oldest)
        
        self.connections[cluster_name] = connection
        self.last_used[cluster_name] = time.time()
    
    def remove_connection(self, cluster_name):
        """Remove a connection from the pool"""
        self.connections.pop(cluster_name, None)
        self.last_used.pop(cluster_name, None)
    
    def _cleanup_stale_connections(self):
        """Remove connections that haven't been used recently"""
        current_time = time.time()
        stale_clusters = [
            cluster for cluster, last_time in self.last_used.items()
            if current_time - last_time > self.connection_timeout
        ]
        
        for cluster in stale_clusters:
            self.remove_connection(cluster)


class SmartCache:
    """Intelligent cache with TTL and size management"""
    
    def __init__(self, ttl_seconds=CACHE_TTL_SECONDS, max_size_mb=MAX_CACHE_SIZE_MB):
        self.cache = {}
        self.timestamps = {}
        self.access_counts = {}
        self.ttl_seconds = ttl_seconds
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
    def get(self, key):
        """Get item from cache if valid"""
        if key not in self.cache:
            return None
        
        # Check TTL
        if time.time() - self.timestamps[key] > self.ttl_seconds:
            self.remove(key)
            return None
        
        # Update access count
        self.access_counts[key] = self.access_counts.get(key, 0) + 1
        return self.cache[key]
    
    def set(self, key, value):
        """Set item in cache with automatic cleanup"""
        # Estimate size and cleanup if needed
        self._ensure_capacity()
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
        self.access_counts[key] = 1
    
    def remove(self, key):
        """Remove item from cache"""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)
        self.access_counts.pop(key, None)
    
    def clear_cluster(self, cluster_name):
        """Clear all cache entries for a specific cluster"""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{cluster_name}:")]
        for key in keys_to_remove:
            self.remove(key)
    
    def _ensure_capacity(self):
        """Ensure cache doesn't exceed size limit using LRU eviction"""
        # Simplified size check - in production, use sys.getsizeof
        if len(self.cache) > 1000:  # Arbitrary limit
            # Remove least recently used items
            sorted_items = sorted(
                self.access_counts.items(),
                key=lambda x: (x[1], self.timestamps.get(x[0], 0))
            )
            
            # Remove bottom 20%
            to_remove = len(sorted_items) // 5
            for key, _ in sorted_items[:to_remove]:
                self.remove(key)


class ConnectionWorker(EnhancedBaseWorker):

    def __init__(self, client, cluster_name, connection_pool):
        super().__init__(f"cluster_connection_{cluster_name}")
        self.client = client
        self.cluster_name = cluster_name
        self.connection_pool = connection_pool
        self._timeout = 10  # Reduced timeout
    
    def execute(self):
        if self.is_cancelled():
            return None
        
        # Check connection pool first
        existing_conn = self.connection_pool.get_connection(self.cluster_name)
        if existing_conn and self._validate_connection(existing_conn):
            return (self.cluster_name, True, "Connected (cached)")
        
        # Create new connection
        try:
            success = self.client.switch_context(self.cluster_name)
            if not success:
                raise Exception("Failed to switch cluster context")
            
            # Validate connection
            version_info = self.client.version_api.get_code()
            
            # Store in connection pool
            connection_info = {
                'context': self.cluster_name,
                'version': version_info.git_version,
                'connected_at': time.time()
            }
            self.connection_pool.add_connection(self.cluster_name, connection_info)
            
            return (self.cluster_name, True, f"Connected to Kubernetes {version_info.git_version}")
            
        except Exception as e:
            error_msg = self._get_user_friendly_error(e)
            raise Exception(error_msg)
        
    def _validate_connection(self, connection_info):
        """Validate cached connection is still good"""
        # Simple validation - check if connection is recent
        return time.time() - connection_info.get('connected_at', 0) < 300
    
    def _get_user_friendly_error(self, error):
        """Convert technical errors to user-friendly messages"""
        error_str = str(error).lower()
        
        if "docker-desktop" in self.cluster_name.lower() and "refused" in error_str:
            return "Docker Desktop Kubernetes is not running. Please start Docker Desktop and enable Kubernetes."
        elif "timeout" in error_str:
            return f"Connection timeout. Check if cluster '{self.cluster_name}' is accessible."
        elif "certificate" in error_str:
            return f"Certificate error. Check your kubeconfig for '{self.cluster_name}'."
        
        return f"Connection failed: {str(error)[:100]}..."


class NodesWorker(EnhancedBaseWorker):
    def __init__(self, client, parent):
        super().__init__("nodes_fetch")
        self.client = client
        self.parent = parent
        
    def execute(self):
        if self.is_cancelled():
            return []
        return self.client._get_nodes()
    
class ClusterConnection(QObject):
    """
    Enhanced cluster connection manager with better error handling and user feedback
    """
    connection_started = pyqtSignal(str)
    connection_progress = pyqtSignal(str, str)  # cluster_name, progress_message
    connection_complete = pyqtSignal(str, bool, str)  # cluster_name, success, message
    cluster_data_loaded = pyqtSignal(dict)
    node_data_loaded = pyqtSignal(list)
    issues_data_loaded = pyqtSignal(list)
    metrics_data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str, str)  # error_type, error_message
    
    def __init__(self):
        super().__init__()
        self.kube_client = get_kubernetes_client()
        self.thread_manager = get_thread_manager()
        
        # Performance optimizations
        self.connection_pool = ConnectionPool()
        self.smart_cache = SmartCache()
        self.adaptive_pollers = {}  # Per-cluster adaptive polling
        
        # Request batching
        self._pending_requests = deque()
        self._batch_timer = QTimer()
        self._batch_timer.timeout.connect(self._process_batch_requests)
        self._batch_timer.setSingleShot(True)

        self._is_being_destroyed = False
        self._active_workers = set()
        
        # Polling timers with adaptive intervals
        self.metrics_poller = AdaptivePoller(5000)
        self.issues_poller = AdaptivePoller(10000)
        
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self._poll_metrics_adaptive)
        
        self.issues_timer = QTimer(self)
        self.issues_timer.timeout.connect(self._poll_issues_adaptive)
        
        # State tracking
        self.current_cluster = None
        self.connection_states = {}
        self._shutting_down = False

        # Data cache for cluster information
        self.data_cache = {}
        self.loading_complete = {}
        self.cache_timestamps = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Connect signals
        self._connect_signals()
    
    def _connect_signals(self):
        """Connect Kubernetes client signals"""
        try:
            self.kube_client.cluster_info_loaded.connect(self.handle_cluster_info_loaded)
            self.kube_client.cluster_metrics_updated.connect(self.handle_metrics_updated)
            self.kube_client.cluster_issues_updated.connect(self.handle_issues_updated)
            self.kube_client.error_occurred.connect(self.handle_kubernetes_error)
        except Exception as e:
            logging.error(f"Error connecting signals: {e}")
    
    
    def __del__(self):
        """Clean up resources when object is deleted"""
        try:
            self._is_being_destroyed = True
            self._shutting_down = True
            
            # Stop all timers
            if hasattr(self, 'metrics_timer') and self.metrics_timer.isActive():
                self.metrics_timer.stop()
            
            if hasattr(self, 'issues_timer') and self.issues_timer.isActive():
                self.issues_timer.stop()
            
            # Stop all workers
            for worker in list(self._active_workers):
                if hasattr(worker, 'stop'):
                    worker.stop()
            
            # Cancel all active workers
            if hasattr(self, 'thread_manager') and self.thread_manager:
                for worker in list(self._active_workers):
                    if hasattr(worker, 'cancel'):
                        worker.cancel()
                
            if hasattr(self, '_active_workers'):
                self._active_workers.clear()
                
        except Exception as e:
            logging.error(f"Error during ClusterConnection cleanup: {str(e)}")


    def connect_to_cluster(self, cluster_name):
        """Connect to cluster with optimizations"""
        if self._shutting_down or not cluster_name:
            return
        
        # Check cache first
        cache_key = f"{cluster_name}:info"
        cached_info = self.smart_cache.get(cache_key)
        if cached_info:
            self.cluster_data_loaded.emit(cached_info)
            self.connection_complete.emit(cluster_name, True, "Connected (cached)")
            self._start_adaptive_polling(cluster_name)
            return
        
        # Start connection
        self.connection_states[cluster_name] = "connecting"
        self.connection_started.emit(cluster_name)
        
        # Create optimized worker
        worker = ConnectionWorker(
            self.kube_client,
            cluster_name,
            self.connection_pool
        )
        
        worker.signals.finished.connect(self.on_connection_complete)
        worker.signals.error.connect(
            lambda error: self.handle_connection_error(cluster_name, error)
        )
        
        self.thread_manager.submit_worker(f"connect_{cluster_name}", worker)
    
    def on_connection_complete(self, result):
        """Handle connection completion"""
        if self._shutting_down or not result:
            return
        
        cluster_name, success, message = result
        
        if success:
            self.connection_states[cluster_name] = "connected"
            self.current_cluster = cluster_name
            self.connection_complete.emit(cluster_name, success, message)
            
            # Queue initial data load requests
            self._queue_request('cluster_info', cluster_name)
            self._queue_request('metrics', cluster_name)
            self._queue_request('issues', cluster_name)
            
            # Start adaptive polling
            self._start_adaptive_polling(cluster_name)
        else:
            self.connection_states[cluster_name] = "failed"
            self.connection_complete.emit(cluster_name, success, message)
    
    def _queue_request(self, request_type, cluster_name):
        """Queue a request for batch processing"""
        self._pending_requests.append((request_type, cluster_name))
        
        if not self._batch_timer.isActive():
            self._batch_timer.start(BATCH_REQUEST_DELAY)
    
    def _process_batch_requests(self):
        """Process queued requests in batch"""
        if not self._pending_requests:
            return
        
        # Group requests by type
        requests_by_type = {}
        while self._pending_requests:
            req_type, cluster = self._pending_requests.popleft()
            if req_type not in requests_by_type:
                requests_by_type[req_type] = []
            requests_by_type[req_type].append(cluster)
        
        # Process each type
        for req_type, clusters in requests_by_type.items():
            if req_type == 'cluster_info':
                self._batch_load_cluster_info(clusters)
            elif req_type == 'metrics':
                self._batch_load_metrics(clusters)
            elif req_type == 'issues':
                self._batch_load_issues(clusters)

    def _batch_load_cluster_info(self, clusters):
        """Load cluster info for multiple clusters"""
        for cluster_name in clusters:
            try:
                if cluster_name == self.current_cluster:
                    self.load_cluster_info()
            except Exception as e:
                logging.error(f"Error in batch load cluster info for {cluster_name}: {e}")

    def _batch_load_metrics(self, clusters):
        """Load metrics for multiple clusters"""
        for cluster_name in clusters:
            try:
                if cluster_name == self.current_cluster:
                    self.load_metrics()
            except Exception as e:
                logging.error(f"Error in batch load metrics for {cluster_name}: {e}")

    def _batch_load_issues(self, clusters):
        """Load issues for multiple clusters"""
        for cluster_name in clusters:
            try:
                if cluster_name == self.current_cluster:
                    self.load_issues()
            except Exception as e:
                logging.error(f"Error in batch load issues for {cluster_name}: {e}")
    
    def _start_adaptive_polling(self, cluster_name):
        """Start polling with adaptive intervals"""
        if cluster_name not in self.adaptive_pollers:
            self.adaptive_pollers[cluster_name] = {
                'metrics': AdaptivePoller(5000),
                'issues': AdaptivePoller(10000)
            }
        
        # Start timers with initial intervals
        if not self.metrics_timer.isActive():
            interval = self.adaptive_pollers[cluster_name]['metrics'].current_interval
            self.metrics_timer.start(interval)
        
        if not self.issues_timer.isActive():
            interval = self.adaptive_pollers[cluster_name]['issues'].current_interval
            self.issues_timer.start(interval)
    
    def _poll_metrics_adaptive(self):
        """Poll metrics with adaptive interval"""
        if self._shutting_down or not self.current_cluster:
            return
        
        # Get metrics
        self.kube_client.get_cluster_metrics_async()
        
        # Adjust polling interval will be done when metrics are received
    
    def _poll_issues_adaptive(self):
        """Poll issues with adaptive interval"""
        if self._shutting_down or not self.current_cluster:
            return
        
        # Get issues
        self.kube_client.get_cluster_issues_async()
    
    def handle_metrics_updated(self, metrics):
        """Handle metrics update with adaptive polling adjustment"""
        if self._shutting_down:
            return
        
        cluster_name = self.current_cluster
        if not cluster_name:
            return
        
        # Cache metrics
        cache_key = f"{cluster_name}:metrics"
        self.smart_cache.set(cache_key, metrics)
        
        # Calculate data hash for change detection
        data_hash = hash(str(metrics))
        
        # Adjust polling interval
        if cluster_name in self.adaptive_pollers:
            poller = self.adaptive_pollers[cluster_name]['metrics']
            new_interval = poller.record_poll_result(data_hash)
            
            # Update timer interval
            if self.metrics_timer.isActive():
                self.metrics_timer.setInterval(new_interval)
        
        # Emit signal
        self.metrics_data_loaded.emit(metrics)
    
    def handle_issues_updated(self, issues):
        """Handle issues update with adaptive polling adjustment"""
        if self._shutting_down:
            return
        
        cluster_name = self.current_cluster
        if not cluster_name:
            return
        
        # Cache issues
        cache_key = f"{cluster_name}:issues"
        self.smart_cache.set(cache_key, issues)
        
        # Calculate data hash
        data_hash = hash(str(issues))
        
        # Adjust polling interval
        if cluster_name in self.adaptive_pollers:
            poller = self.adaptive_pollers[cluster_name]['issues']
            new_interval = poller.record_poll_result(data_hash)
            
            # Update timer interval
            if self.issues_timer.isActive():
                self.issues_timer.setInterval(new_interval)
        
        # Emit signal
        self.issues_data_loaded.emit(issues)
    
    def disconnect_cluster(self, cluster_name):
        """Disconnect from cluster and cleanup resources"""
        try:
            logging.info(f"Disconnecting from cluster: {cluster_name}")
            
            # Update state
            self.connection_states[cluster_name] = "disconnected"
            
            # Clear caches
            self.smart_cache.clear_cluster(cluster_name)
            
            # Reset adaptive pollers
            if cluster_name in self.adaptive_pollers:
                del self.adaptive_pollers[cluster_name]
            
            # Stop polling if this is current cluster
            if self.current_cluster == cluster_name:
                self.stop_polling()
                self.current_cluster = None
            
        except Exception as e:
            logging.error(f"Error disconnecting cluster: {e}")
    
    def stop_polling(self):
        """Stop all polling timers"""
        for timer in [self.metrics_timer, self.issues_timer]:
            if timer.isActive():
                timer.stop()

    def handle_connection_error(self, cluster_name, error_message):
        """Enhanced connection error handling"""
        try:
            logging.error(f"Connection error for cluster {cluster_name}: {error_message}")
            
            # Update connection state to failed
            self.connection_states[cluster_name] = "failed"
            
            # Emit connection complete with failure
            self.connection_complete.emit(cluster_name, False, error_message)
            
            # Emit specific error
            self.error_occurred.emit("connection", error_message)
            
        except Exception as e:
            logging.error(f"Error in connection error handler: {e}")


    def _stop_workers_for_cluster(self, cluster_name):
        """Stop any active workers for a specific cluster"""
        try:
            workers_to_stop = []
            for worker in self._active_workers:
                if (hasattr(worker, 'cluster_name') and 
                    worker.cluster_name == cluster_name):
                    workers_to_stop.append(worker)
            
            for worker in workers_to_stop:
                if hasattr(worker, 'stop'):
                    worker.stop()
                    
        except Exception as e:
            logging.error(f"Error stopping workers for cluster {cluster_name}: {e}")

    def get_connection_state(self, cluster_name):
        """Get current connection state for a cluster"""
        return self.connection_states.get(cluster_name, "disconnected")

    def start_polling(self):
        """Start polling for metrics and issues"""
        if self._shutting_down:
            return
            
        try:
            if not self.metrics_timer.isActive():
                self.metrics_timer.start(5000)  # Poll every 5 seconds
                
            if not self.issues_timer.isActive():
                self.issues_timer.start(10000)  # Poll every 10 seconds
                
        except Exception as e:
            logging.error(f"Error starting polling: {e}")
    
    def load_cluster_info(self):
        """Load basic cluster info safely"""
        if self._shutting_down:
            return
            
        try:
            info = self.kube_client.get_cluster_info(self.kube_client.current_cluster)
            if info:
                self.cluster_data_loaded.emit(info)
                # Also load nodes data
                self.load_nodes()
        except Exception as e:
            self.error_occurred.emit("data_loading", f"Error loading cluster info: {str(e)}")

    def load_metrics(self):
        """Load cluster metrics safely"""
        if self._is_being_destroyed or self._shutting_down:
            return
        
        try:
            # Use the kubernetes client to get metrics
            self.kube_client.get_cluster_metrics_async()
        except Exception as e:
            if not self._is_being_destroyed and not self._shutting_down:
                logging.warning(f"Error loading metrics: {str(e)}")
                # Don't emit error for metrics failures as they're not critical

    def load_issues(self):
        """Load cluster issues safely"""
        if self._is_being_destroyed or self._shutting_down:
            return
        
        try:
            # Use the kubernetes client to get issues
            self.kube_client.get_cluster_issues_async()
        except Exception as e:
            if not self._is_being_destroyed and not self._shutting_down:
                logging.warning(f"Error loading issues: {str(e)}")
                # Don't emit error for issues failures as they're not critical

    def load_nodes(self):
        """Load nodes data from the connected cluster"""
        if self._shutting_down:
            return
            
        try:
            # Create and start the worker
            worker = NodesWorker(self.kube_client, self)
            
            # Track the worker
            self._active_workers.add(worker)
            
            # Set up cleanup for when the worker is done
            def cleanup_worker(result=None):
                if worker in self._active_workers:
                    self._active_workers.remove(worker)
                    
            worker.signals.finished.connect(cleanup_worker)
            worker.signals.error.connect(lambda _: cleanup_worker())
            
            # Connect signals
            worker.signals.finished.connect(self.on_nodes_loaded)
            worker.signals.error.connect(lambda error: self.handle_error("nodes", error))
            
            # Submit worker to thread manager
            self.thread_manager.submit_worker(f"nodes_load_{id(worker)}", worker)
            
        except Exception as e:
            logging.error(f"Error loading nodes: {e}")
            self.handle_error("nodes", f"Failed to load nodes: {str(e)}")

    def on_nodes_loaded(self, nodes):
        """Handle nodes data loaded from worker thread"""
        try:
            if not self._is_being_destroyed and not self._shutting_down:
                self.node_data_loaded.emit(nodes)
        except Exception as e:
            logging.error(f"Error handling nodes loaded: {e}")

    def handle_error(self, error_type, error_message):
        """Handle general errors"""
        try:
            if not self._is_being_destroyed and not self._shutting_down:
                logging.error(f"Cluster connector error ({error_type}): {error_message}")
                self.error_occurred.emit(error_type, error_message)
        except Exception as e:
            logging.error(f"Error in error handler: {e}")

    def _update_cache_timestamp(self, cluster_name):
        """Update cache timestamp for a cluster"""
        import time
        self.cache_timestamps[cluster_name] = time.time()

    def _check_data_completeness(self, cluster_name):
        """Check if we have sufficient data for a cluster (more flexible)"""
        try:
            if cluster_name not in self.data_cache:
                return False
                
            cache = self.data_cache[cluster_name]
            
            # We need at least cluster_info to consider it "loaded"
            # Metrics and issues are nice to have but not required
            if 'cluster_info' in cache:
                self.loading_complete[cluster_name] = True
                return True
                
            # If we have any data at all, consider it partially loaded
            if cache:
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"Error checking data completeness for {cluster_name}: {e}")
            return False

    def is_data_loaded(self, cluster_name):
        """Check if essential data is loaded for a cluster (more flexible)"""
        try:
            # Check if marked as complete
            if self.loading_complete.get(cluster_name, False):
                return True
                
            # Check if we have any useful data
            cached_data = self.data_cache.get(cluster_name, {})
            return bool(cached_data.get('cluster_info'))
            
        except Exception as e:
            logging.error(f"Error checking if data is loaded for {cluster_name}: {e}")
            return False

    def get_cached_data(self, cluster_name):
        """Get cached data for a cluster if available"""
        try:
            # Check cache validity first
            self._cleanup_expired_cache()
            return self.data_cache.get(cluster_name, {})
        except Exception as e:
            logging.error(f"Error getting cached data for {cluster_name}: {e}")
            return {}

    def _cleanup_expired_cache(self):
        """Clean up expired cache entries to prevent memory leaks"""
        try:
            import time
            current_time = time.time()
            expired_keys = []
            
            for cluster_name, timestamp in self.cache_timestamps.items():
                if current_time - timestamp > self.cache_ttl:
                    expired_keys.append(cluster_name)
            
            for key in expired_keys:
                self.data_cache.pop(key, None)
                self.cache_timestamps.pop(key, None)
                self.loading_complete.pop(key, None)
                logging.debug(f"Cleaned up expired cache for cluster: {key}")
                
        except Exception as e:
            logging.error(f"Error cleaning up expired cache: {e}")
    
    def handle_cluster_info_loaded(self, info):
        """Handle when cluster info is loaded from the client"""
        if self._is_being_destroyed or self._shutting_down:
            return
            
        try:
            cluster_name = self.kube_client.current_cluster
            if cluster_name:
                if cluster_name not in self.data_cache:
                    self.data_cache[cluster_name] = {}
                self.data_cache[cluster_name]['cluster_info'] = info
                self._update_cache_timestamp(cluster_name)
                
                # Check if we have all required data now
                self._check_data_completeness(cluster_name)
                
            self.cluster_data_loaded.emit(info)
            
        except Exception as e:
            logging.error(f"Error handling cluster info loaded: {e}")

    def handle_kubernetes_error(self, error_message):
        """Handle Kubernetes client errors with filtering"""
        try:
            if not self._is_being_destroyed and not self._shutting_down:
                # Filter out non-critical errors to avoid spam
                error_lower = error_message.lower()
                
                # Only emit critical errors that users should know about
                if any(keyword in error_lower for keyword in [
                    'connection refused', 'timeout', 'certificate', 'authentication',
                    'authorization', 'permission denied', 'config'
                ]):
                    self.error_occurred.emit("kubernetes", error_message)
                else:
                    # Log other errors but don't emit signals
                    logging.warning(f"Kubernetes client error (suppressed): {error_message}")
                    
        except Exception as e:
            logging.error(f"Error handling kubernetes error: {e}")

    def cleanup(self):
        """Cleanup resources"""
        self._shutting_down = True
        self.stop_polling()
        self._batch_timer.stop()
        self.smart_cache.cache.clear()
        self.connection_pool.connections.clear()

# Singleton instance management
_connector_instance = None

def get_cluster_connector():
    """Get or create the cluster connector singleton"""
    global _connector_instance
    if _connector_instance is None:
        _connector_instance = ClusterConnection()
    return _connector_instance

def shutdown_cluster_connector():
    """Shutdown the cluster connector"""
    global _connector_instance
    if _connector_instance is not None:
        _connector_instance.cleanup()
        _connector_instance = None