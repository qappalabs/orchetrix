from PyQt6.QtCore import QObject, pyqtSignal
from enum import Enum
from Utils.enhanced_worker import EnhancedBaseWorker
import threading
import logging
import time

class ClusterState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    MANUALLY_DISCONNECTED = "manually_disconnected"

# Fixed ClusterStateManager - Improved error handling and connection logic

class ClusterConnectionWorker(EnhancedBaseWorker):
    def __init__(self, cluster_name):
        super().__init__(f"cluster_connect_{cluster_name}")
        self.cluster_name = cluster_name
        self._timeout = 30  # 30 second timeout
        
    def execute(self):
        try:
            from Utils.kubernetes_client import get_kubernetes_client
            
            start_time = time.time()
            
            kube_client = get_kubernetes_client()
            if not kube_client:
                raise Exception("Kubernetes client not available")
            
            # FIXED: Add progress updates and better error handling
            # Progress messages removed - silent operation
            
            # Check if we're already connected to this cluster and verify connectivity
            if (hasattr(kube_client, 'current_cluster') and 
                kube_client.current_cluster == self.cluster_name):
                try:
                    # Verify the connection is actually working
                    kube_client.version_api.get_code()
                    logging.info(f"Already connected to {self.cluster_name}")
                    return {
                        'cluster_info': {'name': self.cluster_name, 'already_connected': True},
                        'initial_data': {},
                        'timestamp': time.time()
                    }
                except Exception as e:
                    logging.warning(f"Connection verification failed for {self.cluster_name}, proceeding with fresh connection: {e}")
                    # Continue with fresh connection attempt
            
            # Connect to cluster with timeout check
            success = kube_client.connect_to_cluster(self.cluster_name, self.cluster_name)
            
            if not success:
                raise Exception(f"Failed to connect to cluster: {self.cluster_name}")
                
            if self.is_cancelled():
                return None
                
            # FIXED: Better connectivity test with timeout
            # Progress messages removed - silent operation
            remaining_time = self._timeout - (time.time() - start_time)
            if remaining_time <= 0:
                raise Exception("Connection timeout during context switch")
                
            cluster_info = self._test_cluster_connectivity(kube_client, remaining_time)
            
            if self.is_cancelled():
                return None
                
            # FIXED: Load initial data with timeout
            # Progress messages removed - silent operation
            remaining_time = self._timeout - (time.time() - start_time)
            if remaining_time <= 5:  # Need at least 5 seconds for data loading
                logging.warning(f"Insufficient time remaining for data loading: {remaining_time}s")
                initial_data = {}
            else:
                initial_data = self._load_initial_data(kube_client, remaining_time)
            
            return {
                'cluster_info': cluster_info,
                'initial_data': initial_data,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logging.error(f"ClusterConnectionWorker failed for {self.cluster_name}: {e}")
            raise e
        
    def _test_cluster_connectivity(self, kube_client, remaining_timeout):
        """Test cluster connectivity with improved error handling"""
        if remaining_timeout <= 0:
            raise Exception("Connection timeout")
            
        try:
            # FIXED: Use version API which is typically most reliable
            version_info = kube_client.version_api.get_code()
            
            return {
                'name': self.cluster_name,
                'version': f"{version_info.major}.{version_info.minor}",
                'git_version': version_info.git_version,
                'connected_at': time.time()
            }
        except Exception as e:
            logging.error(f"Cluster connectivity test failed for {self.cluster_name}: {e}")
            raise Exception(f"Cluster connectivity test failed: {str(e)}")
            
    def _load_initial_data(self, kube_client, remaining_timeout):
        """Load initial data with better error handling"""
        if remaining_timeout <= 0:
            raise Exception("Timeout loading initial data")
            
        try:
            initial_data = {}
            
            # FIXED: Load data with individual error handling
            try:
                nodes = kube_client._get_nodes()
                initial_data['nodes_count'] = len(nodes)
            except Exception as e:
                logging.warning(f"Failed to load nodes: {e}")
                initial_data['nodes_count'] = 0
            
            try:
                namespaces = kube_client._get_namespaces()
                initial_data['namespaces_count'] = len(namespaces)
            except Exception as e:
                logging.warning(f"Failed to load namespaces: {e}")
                initial_data['namespaces_count'] = 0
            
            initial_data['loaded_at'] = time.time()
            return initial_data
            
        except Exception as e:
            logging.warning(f"Failed to load initial data for {self.cluster_name}: {e}")
            return {'error': str(e), 'loaded_at': time.time()}


class ClusterStateManager(QObject):
    state_changed = pyqtSignal(str, ClusterState)
    switch_completed = pyqtSignal(str, bool)
    
    def __init__(self):
        super().__init__()
        self.current_cluster = None
        self.cluster_states = {}
        self.cluster_data = {}
        self.switching_lock = threading.Lock()
        self.pending_switch = None
        
    def request_cluster_switch(self, cluster_name: str) -> bool:
        """Request cluster switch with improved logic"""
        try:
            with self.switching_lock:
                if self.pending_switch is not None:
                    logging.warning(f"Switch already in progress to {self.pending_switch}")
                    return False
                    
                # FIXED: Better state checking
                cluster_state = self.cluster_states.get(cluster_name, ClusterState.DISCONNECTED)
                
                # If we think we're connected but the state shows disconnected, reset current_cluster
                if self.current_cluster == cluster_name and cluster_state not in [ClusterState.CONNECTED, ClusterState.CONNECTING]:
                    logging.info(f"Resetting current_cluster for {cluster_name} due to state mismatch")
                    self.current_cluster = None
                
                # If we're truly connected and it's the current cluster, verify connectivity first
                if self.current_cluster == cluster_name and cluster_state == ClusterState.CONNECTED:
                    # Verify the connection is actually working before allowing switch
                    try:
                        from Utils.kubernetes_client import get_kubernetes_client
                        kube_client = get_kubernetes_client()
                        if kube_client:
                            # Quick connectivity test
                            kube_client.version_api.get_code()
                            logging.info(f"Already connected to {cluster_name}, switching to cluster view")
                            self.switch_completed.emit(cluster_name, True)
                            return True
                        else:
                            logging.warning(f"No kubernetes client available for {cluster_name}")
                    except Exception as e:
                        logging.warning(f"Connection verification failed for {cluster_name}: {e}")
                        # Reset state and proceed with fresh connection
                        self.current_cluster = None
                        self.cluster_states[cluster_name] = ClusterState.DISCONNECTED
                    
                self.pending_switch = cluster_name
                self._initiate_cluster_switch(cluster_name)
                return True
                
        except Exception as e:
            logging.error(f"Error in request_cluster_switch for {cluster_name}: {e}")
            return False
    
    def _initiate_cluster_switch(self, cluster_name: str):
        """Initiate cluster switch with better error handling"""
        try:
            self.cluster_states[cluster_name] = ClusterState.CONNECTING
            self.state_changed.emit(cluster_name, ClusterState.CONNECTING)
            
            self._connect_to_cluster(cluster_name)
            
        except Exception as e:
            logging.error(f"Error initiating cluster switch to {cluster_name}: {e}")
            self._handle_connection_error(cluster_name, str(e))
        
    def _connect_to_cluster(self, cluster_name: str):
        """Connect to cluster with improved error handling"""
        try:
            from Utils.thread_manager import get_thread_manager
            
            worker = ClusterConnectionWorker(cluster_name)
            worker.signals.finished.connect(lambda result: self._handle_connection_result(cluster_name, result))
            worker.signals.error.connect(lambda error: self._handle_connection_error(cluster_name, error))
            # worker.signals.progress.connect(lambda msg: logging.info(f"Connection progress for {cluster_name}: {msg}"))  # Removed progress logging
            
            thread_manager = get_thread_manager()
            thread_manager.submit_worker(f"cluster_connect_{cluster_name}", worker)
            
        except Exception as e:
            logging.error(f"Error creating connection worker for {cluster_name}: {e}")
            self._handle_connection_error(cluster_name, str(e))
            
    def _handle_connection_result(self, cluster_name: str, result: dict):
        """Handle connection result with better error checking"""
        try:
            with self.switching_lock:
                if self.pending_switch != cluster_name:
                    logging.warning(f"Received result for {cluster_name} but pending switch is {self.pending_switch}")
                    return
                    
                if not result:
                    self._handle_connection_error(cluster_name, "Connection returned no result")
                    return
                
                self.current_cluster = cluster_name
                self.cluster_states[cluster_name] = ClusterState.CONNECTED
                self.cluster_data[cluster_name] = result
                self.pending_switch = None
                
                self.state_changed.emit(cluster_name, ClusterState.CONNECTED)
                self.switch_completed.emit(cluster_name, True)
                
                logging.info(f"Successfully connected to cluster: {cluster_name}")
                
        except Exception as e:
            logging.error(f"Error handling connection result for {cluster_name}: {e}")
            self._handle_connection_error(cluster_name, str(e))
            
    def _handle_connection_error(self, cluster_name: str, error: str):
        """Handle connection error with proper cleanup"""
        try:
            with self.switching_lock:
                if self.pending_switch != cluster_name:
                    return
                    
                # Reset cluster state completely on error
                self.cluster_states[cluster_name] = ClusterState.ERROR
                if self.current_cluster == cluster_name:
                    self.current_cluster = None
                    logging.info(f"Reset current_cluster due to connection error for {cluster_name}")
                
                # Clear any cached data
                if cluster_name in self.cluster_data:
                    del self.cluster_data[cluster_name]
                    
                self.pending_switch = None
                
                self.state_changed.emit(cluster_name, ClusterState.ERROR)
                self.switch_completed.emit(cluster_name, False)
                
                logging.error(f"Connection failed for {cluster_name}: {error}")
                
        except Exception as e:
            logging.error(f"Error in error handler for {cluster_name}: {e}")
            
    def get_cluster_state(self, cluster_name: str) -> ClusterState:
        """Get cluster state safely"""
        return self.cluster_states.get(cluster_name, ClusterState.DISCONNECTED)
        
    def is_switching(self) -> bool:
        """Check if currently switching"""
        return self.pending_switch is not None
        
    def reset_cluster_state(self, cluster_name: str):
        """Reset cluster state to disconnected - useful for cleanup"""
        try:
            with self.switching_lock:
                if cluster_name in self.cluster_states:
                    old_state = self.cluster_states[cluster_name]
                    self.cluster_states[cluster_name] = ClusterState.DISCONNECTED
                    
                    if self.current_cluster == cluster_name:
                        self.current_cluster = None
                        
                    if cluster_name in self.cluster_data:
                        del self.cluster_data[cluster_name]
                        
                    if old_state != ClusterState.DISCONNECTED:
                        self.state_changed.emit(cluster_name, ClusterState.DISCONNECTED)
                        
                    logging.info(f"Reset cluster state for {cluster_name}")
                    
        except Exception as e:
            logging.error(f"Error resetting cluster state for {cluster_name}: {e}")
            
    def disconnect_cluster(self, cluster_name: str):
        """Disconnect from cluster and reset all states"""
        try:
            with self.switching_lock:
                logging.info(f"Disconnecting cluster: {cluster_name}")
                
                # Set to manually disconnected state (will show as "disconnect" in UI)
                old_state = self.cluster_states.get(cluster_name, ClusterState.DISCONNECTED)
                self.cluster_states[cluster_name] = ClusterState.MANUALLY_DISCONNECTED
                
                # Clear current cluster
                if self.current_cluster == cluster_name:
                    self.current_cluster = None
                    logging.info(f"Cleared current_cluster for {cluster_name}")
                    
                # Clear cached data
                if cluster_name in self.cluster_data:
                    del self.cluster_data[cluster_name]
                    logging.info(f"Cleared cached data for {cluster_name}")
                    
                # Cancel any pending switch
                if self.pending_switch == cluster_name:
                    self.pending_switch = None
                    logging.info(f"Cancelled pending switch for {cluster_name}")
                    
                # Emit state change if needed
                if old_state != ClusterState.MANUALLY_DISCONNECTED:
                    self.state_changed.emit(cluster_name, ClusterState.MANUALLY_DISCONNECTED)
                    
                # Reset kubernetes client
                try:
                    from Utils.kubernetes_client import get_kubernetes_client
                    kube_client = get_kubernetes_client()
                    if kube_client and hasattr(kube_client, 'current_cluster') and kube_client.current_cluster == cluster_name:
                        kube_client.current_cluster = None
                        logging.info(f"Reset kubernetes client current_cluster for {cluster_name}")
                except Exception as e:
                    logging.warning(f"Failed to reset kubernetes client for {cluster_name}: {e}")
                    
                logging.info(f"Successfully disconnected cluster: {cluster_name}")
                
        except Exception as e:
            logging.error(f"Error disconnecting cluster {cluster_name}: {e}")

_cluster_state_manager_instance = None

def get_cluster_state_manager():
    global _cluster_state_manager_instance
    if _cluster_state_manager_instance is None:
        _cluster_state_manager_instance = ClusterStateManager()
    return _cluster_state_manager_instance