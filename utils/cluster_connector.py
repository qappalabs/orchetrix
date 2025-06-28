from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot, QTimer
from utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException
import logging
import traceback
from utils.enhanced_worker import EnhancedBaseWorker
from utils.thread_manager import get_thread_manager
from utils.data_manager import get_data_manager


class ConnectionWorker(EnhancedBaseWorker):
    def __init__(self, client, cluster_name):
        super().__init__(f"cluster_connection_{cluster_name}")
        self.client = client
        self.cluster_name = cluster_name
        
    def execute(self):
        logging.info(f"Starting connection worker for cluster: {self.cluster_name}")
        
        if self.is_cancelled():
            return None
            
        try:
            success = self.client.switch_context(self.cluster_name)
            
            if not success:
                raise Exception("Failed to switch to cluster context")
            
            if self.is_cancelled():
                return None
            
            # Test connection by getting version info
            if self.client.version_api:
                version_info = self.client.version_api.get_code()
                logging.info(f"Connected to cluster {self.cluster_name}, version: {version_info.git_version}")
                return (self.cluster_name, True, f"Connected to Kubernetes {version_info.git_version}")
            else:
                return (self.cluster_name, True, "Connected successfully")
                
        except Exception as conn_error:
            if self.is_cancelled():
                return None
                
            error_msg = self._get_connection_error_message(conn_error)
            raise Exception(error_msg)

    # def _get_connection_error_message(self, error):
    #     """Convert connection errors to user-friendly messages"""
    #     error_str = str(error).lower()
        
    #     if "no connection could be made" in error_str or "connection refused" in error_str:
    #         return f"Cannot connect to cluster '{self.cluster_name}'. The cluster appears to be offline or unreachable."
    #     elif "timeout" in error_str:
    #         return f"Connection to cluster '{self.cluster_name}' timed out. Check your network connection and cluster status."
    #     elif "certificate" in error_str or "ssl" in error_str:
    #         return f"SSL/Certificate error connecting to cluster '{self.cluster_name}'. Check your cluster certificates."
    #     elif "authentication" in error_str or "unauthorized" in error_str:
    #         return f"Authentication failed for cluster '{self.cluster_name}'. Check your credentials."
    #     elif "forbidden" in error_str:
    #         return f"Access denied to cluster '{self.cluster_name}'. Check your permissions."
    #     elif "not found" in error_str:
    #         return f"Cluster '{self.cluster_name}' configuration not found. Check your kubeconfig."
    #     elif "name resolution" in error_str or "dns" in error_str:
    #         return f"Cannot resolve cluster '{self.cluster_name}' address. Check your DNS settings."
    #     else:
    #         return f"Failed to connect to cluster '{self.cluster_name}': {str(error)}"

    def _get_connection_error_message(self, error):
        """Convert technical errors to user-friendly messages"""
        error_str = str(error).lower()
        
        # Docker Desktop specific errors
        if "docker-desktop" in self.cluster_name.lower():
            if "connection refused" in error_str or "no connection could be made" in error_str:
                return (
                    "Docker Desktop Kubernetes is not running.\n\n"
                    "Please start Docker Desktop and enable Kubernetes in the settings."
                )
        
        # Generic connection errors
        if "connection refused" in error_str or "no connection could be made" in error_str:
            return f"Cannot connect to cluster '{self.cluster_name}'. The cluster appears to be offline."
        
        elif "timeout" in error_str:
            return f"Connection to cluster '{self.cluster_name}' timed out. Check your network connection."
        
        elif "certificate" in error_str or "ssl" in error_str:
            return f"Certificate error connecting to '{self.cluster_name}'. Check your kubeconfig."
        
        elif "authentication" in error_str or "unauthorized" in error_str:
            return f"Authentication failed for '{self.cluster_name}'. Check your credentials."
        
        elif "not found" in error_str:
            return f"Cluster '{self.cluster_name}' not found. Check your kubeconfig."
        
        # Fallback with cleaned error
        return f"Failed to connect to '{self.cluster_name}': {str(error)[:100]}..."

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
        self.threadpool = QThreadPool()
        self._active_workers = set()
        
        self.data_cache = {}
        self.loading_complete = {}
        self.connection_states = {}  # Track connection states
        
        # Connect signals from the Kubernetes client with error handling
        try:
            self.kube_client.cluster_info_loaded.connect(self.handle_cluster_info_loaded)
            self.kube_client.cluster_metrics_updated.connect(self.handle_metrics_updated)
            self.kube_client.cluster_issues_updated.connect(self.handle_issues_updated)
            self.kube_client.error_occurred.connect(self.handle_kubernetes_error)
        except Exception as e:
            logging.error(f"Error connecting kubernetes client signals: {e}")
        
        # Create timers for polling
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self.load_metrics)
        
        self.issues_timer = QTimer(self)
        self.issues_timer.timeout.connect(self.load_issues)

        self._is_being_destroyed = False
        self._shutting_down = False
    
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
            
            # Wait for threadpool to finish
            if hasattr(self, 'threadpool'):
                self.threadpool.waitForDone(300)
                self.threadpool.clear()
                
            if hasattr(self, '_active_workers'):
                self._active_workers.clear()
                
        except Exception as e:
            logging.error(f"Error during ClusterConnection cleanup: {str(e)}")

    def connect_to_cluster(self, cluster_name):
        if self._shutting_down:
            return
                
        if not cluster_name:
            self.error_occurred.emit("validation", "No cluster name provided")
            return
        
        try:
            logging.info(f"Starting connection process for cluster: {cluster_name}")
            
            self.connection_states[cluster_name] = "connecting"
            self.connection_started.emit(cluster_name)
            
            worker = ConnectionWorker(self.kube_client, cluster_name)
            
            worker.signals.finished.connect(self.on_connection_complete)
            worker.signals.error.connect(lambda error: self.handle_connection_error(cluster_name, error))
            
            thread_manager = get_thread_manager()
            thread_manager.submit_worker(f"cluster_connect_{cluster_name}", worker)
            
        except Exception as e:
            logging.error(f"Error starting connection to cluster {cluster_name}: {e}")
            self.handle_connection_error(cluster_name, f"Failed to start connection: {str(e)}")

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

    def on_connection_complete(self, result):
        """Handle connection completion with enhanced feedback"""
        if self._is_being_destroyed or self._shutting_down:
            return
                
        try:
            cluster_name, success, message = result
            
            if success:
                self.connection_states[cluster_name] = "connected" 
                logging.info(f"Successfully connected to cluster: {cluster_name}")
            else:
                self.connection_states[cluster_name] = "failed"
                logging.error(f"Failed to connect to cluster {cluster_name}: {message}")
            
            self.connection_complete.emit(cluster_name, success, message)
            
            if success:
                try:
                    # Set the current cluster in the client
                    self.kube_client.current_cluster = cluster_name
                    
                    # Initialize cache for this cluster
                    if cluster_name not in self.data_cache:
                        self.data_cache[cluster_name] = {}
                    
                    # Load initial data
                    self.load_cluster_info()
                    
                    # Start polling timers
                    self.start_polling()
                    
                except Exception as e:
                    error_msg = f"Error initializing cluster data: {str(e)}"
                    logging.error(f"Error in connection complete handler: {e}")
                    self.connection_states[cluster_name] = "failed"
                    self.handle_connection_error(cluster_name, error_msg)
                    return
            
        except Exception as e:
            logging.error(f"Error in connection complete handler: {e}")
            if len(result) >= 1:
                cluster_name = result[0]
                self.connection_states[cluster_name] = "failed"
                self.handle_connection_error(cluster_name, f"Connection processing error: {str(e)}")

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

    def disconnect_cluster(self, cluster_name):
        """Disconnect from a specific cluster"""
        try:
            logging.info(f"Disconnecting from cluster: {cluster_name}")
            
            # Stop any workers for this cluster
            self._stop_workers_for_cluster(cluster_name)
            
            # Update connection state
            self.connection_states[cluster_name] = "disconnected"
            
            # Clean up cached data
            if cluster_name in self.data_cache:
                del self.data_cache[cluster_name]
            
            if cluster_name in self.loading_complete:
                del self.loading_complete[cluster_name]
            
            # Stop polling if this is the current cluster
            if (hasattr(self.kube_client, 'current_cluster') and 
                self.kube_client.current_cluster == cluster_name):
                self.stop_polling()
                
        except Exception as e:
            logging.error(f"Error disconnecting from cluster {cluster_name}: {e}")

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
    
    def stop_polling(self):
        """Stop all polling timers"""
        try:
            if hasattr(self, 'metrics_timer') and self.metrics_timer.isActive():
                self.metrics_timer.stop()
                
            if hasattr(self, 'issues_timer') and self.issues_timer.isActive():
                self.issues_timer.stop()
                
        except Exception as e:
            logging.error(f"Error stopping polling: {e}")
    
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
                
                # Check if we have all required data now
                self._check_data_completeness(cluster_name)
                
            self.cluster_data_loaded.emit(info)
            
        except Exception as e:
            logging.error(f"Error handling cluster info loaded: {e}")

    def handle_metrics_updated(self, metrics):
        """Handle when metrics are received from the client"""
        if self._is_being_destroyed or self._shutting_down:
            return
            
        try:
            cluster_name = self.kube_client.current_cluster
            if cluster_name:
                if cluster_name not in self.data_cache:
                    self.data_cache[cluster_name] = {}
                self.data_cache[cluster_name]['metrics'] = metrics
                
                # Check if we have all required data now
                self._check_data_completeness(cluster_name)
                
            self.metrics_data_loaded.emit(metrics)
            
        except Exception as e:
            logging.error(f"Error handling metrics updated: {e}")

    def handle_issues_updated(self, issues):
        """Handle when issues are received from the client"""
        if self._is_being_destroyed or self._shutting_down:
            return
            
        try:
            cluster_name = self.kube_client.current_cluster
            if cluster_name:
                if cluster_name not in self.data_cache:
                    self.data_cache[cluster_name] = {}
                self.data_cache[cluster_name]['issues'] = issues
                
                # Check if we have all required data now
                self._check_data_completeness(cluster_name)
                
            self.issues_data_loaded.emit(issues)
            
        except Exception as e:
            logging.error(f"Error handling issues updated: {e}")

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

    def handle_error(self, error_type, error_message):
        """Handle general errors"""
        try:
            if not self._is_being_destroyed and not self._shutting_down:
                logging.error(f"Cluster connector error ({error_type}): {error_message}")
                self.error_occurred.emit(error_type, error_message)
        except Exception as e:
            logging.error(f"Error in error handler: {e}")

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
            return self.data_cache.get(cluster_name, {})
        except Exception as e:
            logging.error(f"Error getting cached data for {cluster_name}: {e}")
            return {}

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
            
            self.threadpool.start(worker)
            
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

# Singleton instance
_connector_instance = None

def get_cluster_connector():
    """Get or create the cluster connector singleton"""
    global _connector_instance
    if _connector_instance is None:
        _connector_instance = ClusterConnection()
    return _connector_instance