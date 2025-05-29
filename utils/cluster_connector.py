from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot, QTimer
from utils.kubernetes_client import get_kubernetes_client
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException
import logging
import traceback

class WorkerSignals(QObject):
    """Signals for worker threads with proper lifecycle management"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # New signal for progress updates
    
    def __init__(self):
        super().__init__()
        self._is_valid = True
    
    def is_valid(self):
        return self._is_valid
    
    def invalidate(self):
        self._is_valid = False

class BaseWorker(QRunnable):
    """Base worker class with safe signal handling"""
    
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self._should_stop = False
        
    def __del__(self):
        if hasattr(self, 'signals'):
            self.signals.invalidate()

    def stop(self):
        """Signal the worker to stop gracefully"""
        self._should_stop = True

    def safe_emit_finished(self, result):
        if hasattr(self, 'signals') and self.signals.is_valid() and not self._should_stop:
            try:
                self.signals.finished.emit(result)
            except RuntimeError:
                logging.warning("Unable to emit finished signal - receiver may have been deleted")
                
    def safe_emit_error(self, error_message):
        if hasattr(self, 'signals') and self.signals.is_valid() and not self._should_stop:
            try:
                self.signals.error.emit(error_message)
            except RuntimeError:
                logging.warning(f"Unable to emit error signal: {error_message}")
    
    def safe_emit_progress(self, message):
        if hasattr(self, 'signals') and self.signals.is_valid() and not self._should_stop:
            try:
                self.signals.progress.emit(message)
            except RuntimeError:
                logging.warning(f"Unable to emit progress signal: {message}")

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

    class ConnectionWorker(BaseWorker):
        def __init__(self, client, cluster_name, parent):
            super().__init__()
            self.client = client
            self.cluster_name = cluster_name
            self.parent = parent
            
        @pyqtSlot()
        def run(self):
            try:
                if self._should_stop:
                    return
                    
                logging.info(f"Starting connection worker for cluster: {self.cluster_name}")
                
                # Step 1: Check if cluster context exists
                self.safe_emit_progress("Checking cluster configuration...")
                
                # Step 2: Attempt context switch
                self.safe_emit_progress("Switching to cluster context...")
                
                if self._should_stop:
                    return
                
                success = self.client.switch_context(self.cluster_name)
                
                if not success:
                    self.safe_emit_error("Failed to switch to cluster context")
                    self.safe_emit_finished((self.cluster_name, False, "Context switch failed"))
                    return
                
                if self._should_stop:
                    return
                
                # Step 3: Test basic connectivity
                self.safe_emit_progress("Testing cluster connectivity...")
                
                try:
                    if self.client.version_api:
                        version_info = self.client.version_api.get_code()
                        logging.info(f"Connected to cluster {self.cluster_name}, version: {version_info.git_version}")
                        self.safe_emit_progress("Connection established successfully")
                        self.safe_emit_finished((self.cluster_name, True, f"Connected to Kubernetes {version_info.git_version}"))
                    else:
                        self.safe_emit_finished((self.cluster_name, True, "Connected successfully"))
                        
                except Exception as conn_error:
                    if self._should_stop:
                        return
                        
                    # Provide specific error messages based on error type
                    error_msg = self._get_connection_error_message(conn_error)
                    
                    logging.warning(f"Connection test failed for {self.cluster_name}: {conn_error}")
                    self.safe_emit_finished((self.cluster_name, False, error_msg))
                    
            except ConfigException as e:
                if not self._should_stop:
                    error_msg = f"Configuration error: {str(e)}"
                    self.safe_emit_error(error_msg)
                    self.safe_emit_finished((self.cluster_name, False, error_msg))
            except ApiException as e:
                if not self._should_stop:
                    error_msg = self._get_api_error_message(e)
                    self.safe_emit_error(error_msg)
                    self.safe_emit_finished((self.cluster_name, False, error_msg))
            except Exception as e:
                if not self._should_stop:
                    error_msg = f"Unexpected error: {str(e)}"
                    logging.error(f"Unexpected error in connection worker: {e}")
                    logging.error(traceback.format_exc())
                    self.safe_emit_error(error_msg)
                    self.safe_emit_finished((self.cluster_name, False, error_msg))

        def _get_connection_error_message(self, error):
            """Get user-friendly connection error message"""
            error_str = str(error).lower()
            
            if "connection refused" in error_str:
                return "Cluster is not running or unreachable. Please start your Kubernetes cluster."
            elif "timeout" in error_str:
                return "Connection timeout. Check your network connection and cluster status."
            elif "certificate" in error_str or "tls" in error_str:
                return "Certificate verification failed. Check cluster certificates."
            elif "name resolution" in error_str or "dns" in error_str:
                return "DNS resolution failed. Check cluster endpoint configuration."
            elif "permission denied" in error_str:
                return "Permission denied. Check cluster access permissions."
            elif "no such host" in error_str:
                return "Cluster endpoint not found. Check cluster configuration."
            else:
                return f"Connection test failed: {str(error)}"

        def _get_api_error_message(self, api_error):
            """Get user-friendly API error message"""
            if api_error.status == 401:
                return "Authentication failed. Check your cluster credentials."
            elif api_error.status == 403:
                return "Access denied. Check your cluster permissions."
            elif api_error.status == 404:
                return "Cluster endpoint not found. Check cluster configuration."
            elif api_error.status == 500:
                return "Cluster internal error. The cluster may be experiencing issues."
            elif api_error.status == 503:
                return "Cluster unavailable. The cluster may be starting up or under heavy load."
            else:
                return f"API error ({api_error.status}): {api_error.reason or str(api_error)}"

    def connect_to_cluster(self, cluster_name):
        """Start the cluster connection process with enhanced feedback"""
        if self._shutting_down:
            return
                
        if not cluster_name:
            self.error_occurred.emit("validation", "No cluster name provided")
            return
        
        try:
            logging.info(f"Starting connection process for cluster: {cluster_name}")
            
            # Update connection state
            self.connection_states[cluster_name] = "connecting"
            self.connection_started.emit(cluster_name)
            
            # Stop any existing worker for this cluster
            self._stop_workers_for_cluster(cluster_name)
            
            # Create and start the worker
            worker = self.ConnectionWorker(self.kube_client, cluster_name, self)
            
            # Track the worker
            self._active_workers.add(worker)
            
            # Set up cleanup for when the worker is done
            def cleanup_worker(result=None):
                if worker in self._active_workers:
                    self._active_workers.remove(worker)
                    
            worker.signals.finished.connect(cleanup_worker)
            worker.signals.error.connect(lambda _: cleanup_worker())
            
            # Connect signals for progress updates
            worker.signals.progress.connect(
                lambda msg: self.connection_progress.emit(cluster_name, msg)
            )
            
            # Connect signals
            worker.signals.finished.connect(self.on_connection_complete)
            worker.signals.error.connect(lambda error: self.handle_error("connection", error))
            
            self.threadpool.start(worker)
            
        except Exception as e:
            logging.error(f"Error starting connection to cluster {cluster_name}: {e}")
            self.error_occurred.emit("connection", f"Failed to start connection: {str(e)}")

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

    def on_connection_complete(self, result):
        """Handle connection completion with enhanced feedback"""
        if self._is_being_destroyed or self._shutting_down:
            return
                
        try:
            cluster_name, success, message = result
            self.connection_states[cluster_name] = "connected" if success else "failed"
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
                    self.error_occurred.emit("initialization", error_msg)
                    self.connection_states[cluster_name] = "failed"
                    return
            else:
                logging.warning(f"Connection failed for cluster {cluster_name}: {message}")
                
        except Exception as e:
            logging.error(f"Error in connection complete handler: {e}")
            if len(result) >= 1:
                cluster_name = result[0]
                self.connection_states[cluster_name] = "failed"
    
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
    
    class NodesWorker(BaseWorker):
        def __init__(self, client, parent):
            super().__init__()
            self.client = client
            self.parent = parent
            
        @pyqtSlot()
        def run(self):
            try:
                if self._should_stop:
                    return
                    
                # Get nodes using kubernetes client
                nodes = self.client._get_nodes()
                
                if not self._should_stop:
                    self.safe_emit_finished(nodes)
            except Exception as e:
                if not self._should_stop:
                    self.safe_emit_error(f"Error loading nodes: {str(e)}")
                    self.safe_emit_finished([])
    
    def load_nodes(self):
        """Load nodes data from the connected cluster"""
        if self._shutting_down:
            return
            
        try:
            # Create and start the worker
            worker = self.NodesWorker(self.kube_client, self)
            
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