from PyQt6.QtCore import QObject, pyqtSignal
from enum import Enum
from utils.enhanced_worker import EnhancedBaseWorker
import threading
import logging
import time

class ClusterState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class ClusterConnectionWorker(EnhancedBaseWorker):
    def __init__(self, cluster_name):
        super().__init__(f"cluster_connect_{cluster_name}")
        self.cluster_name = cluster_name
        
    def execute(self):
        from utils.kubernetes_client import get_kubernetes_client
        
        start_time = time.time()
        timeout = 30
        
        kube_client = get_kubernetes_client()
        
        self.signals.progress.emit("Switching cluster context...")
        success = kube_client.switch_context(self.cluster_name)
        
        if not success:
            raise Exception(f"Failed to switch to cluster context: {self.cluster_name}")
            
        if self.is_cancelled():
            return None
            
        self.signals.progress.emit("Testing cluster connectivity...")
        cluster_info = self._test_cluster_connectivity(kube_client, timeout - (time.time() - start_time))
        
        if self.is_cancelled():
            return None
            
        self.signals.progress.emit("Loading initial cluster data...")
        initial_data = self._load_initial_data(kube_client, timeout - (time.time() - start_time))
        
        return {
            'cluster_info': cluster_info,
            'initial_data': initial_data,
            'timestamp': time.time()
        }
        
    def _test_cluster_connectivity(self, kube_client, remaining_timeout):
        if remaining_timeout <= 0:
            raise Exception("Connection timeout")
            
        try:
            version_info = kube_client.version_api.get_code()
            return {
                'name': self.cluster_name,
                'version': f"{version_info.major}.{version_info.minor}",
                'connected_at': time.time()
            }
        except Exception as e:
            raise Exception(f"Cluster connectivity test failed: {str(e)}")
            
    def _load_initial_data(self, kube_client, remaining_timeout):
        if remaining_timeout <= 0:
            raise Exception("Timeout loading initial data")
            
        try:
            nodes = kube_client._get_nodes()
            namespaces = kube_client._get_namespaces()
            
            return {
                'nodes_count': len(nodes),
                'namespaces_count': len(namespaces),
                'loaded_at': time.time()
            }
        except Exception as e:
            logging.warning(f"Failed to load initial data: {e}")
            return {}

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
        with self.switching_lock:
            if self.pending_switch is not None:
                logging.warning(f"Switch already in progress to {self.pending_switch}")
                return False
                
            # Check if we're actually connected to this cluster
            cluster_state = self.cluster_states.get(cluster_name, ClusterState.DISCONNECTED)
            
            # If we think we're connected but the state shows disconnected, reset current_cluster
            if self.current_cluster == cluster_name and cluster_state != ClusterState.CONNECTED:
                logging.info(f"Resetting current_cluster for {cluster_name} due to state mismatch")
                self.current_cluster = None
            
            # If we're truly connected and it's the current cluster, allow reconnection
            if self.current_cluster == cluster_name and cluster_state == ClusterState.CONNECTED:
                logging.info(f"Already connected to {cluster_name}, but allowing switch to cluster view")
                # Emit the switch completed signal to ensure UI switches to cluster view
                self.switch_completed.emit(cluster_name, True)
                return True
                
            self.pending_switch = cluster_name
            self._initiate_cluster_switch(cluster_name)
            return True
    
    def disconnect_cluster(self, cluster_name: str):
        """Disconnect from a cluster and update state"""
        with self.switching_lock:
            logging.info(f"Disconnecting cluster: {cluster_name}")
            
            # Update cluster state
            self.cluster_states[cluster_name] = ClusterState.DISCONNECTED
            self.state_changed.emit(cluster_name, ClusterState.DISCONNECTED)
            
            # Reset current cluster if it matches
            if self.current_cluster == cluster_name:
                self.current_cluster = None
                logging.info(f"Reset current_cluster to None after disconnecting {cluster_name}")
            
            # Clean up cluster data
            self._cleanup_cluster_resources(cluster_name)
            
    def _initiate_cluster_switch(self, cluster_name: str):
        if self.current_cluster and self.current_cluster != cluster_name:
            self._cleanup_cluster_resources(self.current_cluster)
            
        self.cluster_states[cluster_name] = ClusterState.CONNECTING
        self.state_changed.emit(cluster_name, ClusterState.CONNECTING)
        
        self._connect_to_cluster(cluster_name)
        
    def _connect_to_cluster(self, cluster_name: str):
        from utils.thread_manager import get_thread_manager
        
        worker = ClusterConnectionWorker(cluster_name)
        worker.signals.finished.connect(lambda result: self._handle_connection_result(cluster_name, result))
        worker.signals.error.connect(lambda error: self._handle_connection_error(cluster_name, error))
        
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"cluster_connect_{cluster_name}", worker)
        
    def _handle_connection_result(self, cluster_name: str, result: dict):
        with self.switching_lock:
            if self.pending_switch != cluster_name:
                return
                
            self.current_cluster = cluster_name
            self.cluster_states[cluster_name] = ClusterState.CONNECTED
            self.cluster_data[cluster_name] = result
            self.pending_switch = None
            
            self.state_changed.emit(cluster_name, ClusterState.CONNECTED)
            self.switch_completed.emit(cluster_name, True)
            
    def _handle_connection_error(self, cluster_name: str, error: str):
        with self.switching_lock:
            if self.pending_switch != cluster_name:
                return
                
            self.cluster_states[cluster_name] = ClusterState.ERROR
            self.pending_switch = None
            
            self.state_changed.emit(cluster_name, ClusterState.ERROR)
            self.switch_completed.emit(cluster_name, False)
            
    def _cleanup_cluster_resources(self, cluster_name: str):
        self.cluster_data.pop(cluster_name, None)
        
        from utils.data_manager import get_data_manager
        data_manager = get_data_manager()
        data_manager.clear_cluster_data(cluster_name)
        
    def get_cluster_state(self, cluster_name: str) -> ClusterState:
        return self.cluster_states.get(cluster_name, ClusterState.DISCONNECTED)
        
    def is_switching(self) -> bool:
        return self.pending_switch is not None

_cluster_state_manager_instance = None

def get_cluster_state_manager():
    global _cluster_state_manager_instance
    if _cluster_state_manager_instance is None:
        _cluster_state_manager_instance = ClusterStateManager()
    return _cluster_state_manager_instance