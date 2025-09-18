"""
Kubernetes Service - Main coordinator for all Kubernetes operations
Split from kubernetes_client.py for better architecture
"""

import gc
import logging
import weakref
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThreadPool

from .api_service import get_kubernetes_api_service, reset_kubernetes_api_service
from .log_service import create_kubernetes_log_service
from .metrics_service import create_kubernetes_metrics_service
from .events_service import create_kubernetes_events_service
from Utils.thread_manager import get_thread_manager
from Utils.enhanced_worker import EnhancedBaseWorker


@dataclass
class KubeCluster:
    """Data class for Kubernetes cluster information"""
    name: str
    context: str
    kind: str = "Kubernetes Cluster"
    source: str = "local"
    label: str = "General"
    status: str = "available"  # Default to available instead of disconnect
    badge_color: Optional[str] = None
    server: Optional[str] = None
    user: Optional[str] = None
    namespace: Optional[str] = None
    version: Optional[str] = None


class AsyncMetricsWorker(EnhancedBaseWorker):
    """Worker for async metrics collection"""
    def __init__(self, metrics_service, cluster_name):
        super().__init__(f"metrics_{cluster_name}")
        self.metrics_service = metrics_service
        self.cluster_name = cluster_name

    def execute(self):
        return self.metrics_service.get_cluster_metrics(self.cluster_name)


class AsyncIssuesWorker(EnhancedBaseWorker):
    """Worker for async issues collection"""
    def __init__(self, events_service, cluster_name):
        super().__init__(f"issues_{cluster_name}")
        self.events_service = events_service
        self.cluster_name = cluster_name

    def execute(self):
        return self.events_service.get_cluster_issues(self.cluster_name)


class KubernetesService(QObject):
    """Main Kubernetes service coordinator"""
    
    # Signals for UI integration
    clusters_loaded = pyqtSignal(list)
    cluster_info_loaded = pyqtSignal(dict)
    cluster_metrics_updated = pyqtSignal(dict)
    cluster_issues_updated = pyqtSignal(list)
    resource_detail_loaded = pyqtSignal(dict)
    resource_updated = pyqtSignal(dict)
    pod_logs_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.clusters = []
        self.current_cluster = None
        self._shutting_down = False
        
        # Initialize services
        self._init_services()
        
        # Thread management - reduced for better performance
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(4)  # Reduced from 8 to 4 threads
        self.thread_manager = get_thread_manager()
        self._active_workers = weakref.WeakSet()
        
        # Setup timers for polling
        self._setup_timers()
        
        logging.info("KubernetesService initialized with modular architecture")
    
    def _init_services(self):
        """Initialize all service dependencies"""
        try:
            # Core services
            self.api_service = get_kubernetes_api_service()
            
            # Specialized services
            self.log_service = create_kubernetes_log_service(self.api_service)
            self.metrics_service = create_kubernetes_metrics_service(self.api_service)
            self.events_service = create_kubernetes_events_service(self.api_service)
            
            logging.debug("All Kubernetes services initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize Kubernetes services: {e}")
            raise
    
    def _setup_timers(self):
        """Setup polling timers"""
        # Ensure timers are created on main thread
        from PyQt6.QtWidgets import QApplication
        if self.thread() != QApplication.instance().thread():
            logging.warning("KubernetesService timers being created from non-main thread - deferring to main thread")
            from PyQt6.QtCore import QMetaObject
            QMetaObject.invokeMethod(self, "_setup_timers_on_main_thread", Qt.ConnectionType.QueuedConnection)
            return
        
        # Metrics polling timer
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self._poll_metrics_async)
        
        # Issues polling timer  
        self.issues_timer = QTimer(self)
        self.issues_timer.timeout.connect(self._poll_issues_async)
        
        # Cache cleanup timer - less frequent for better performance
        self.cache_cleanup_timer = QTimer(self)
        self.cache_cleanup_timer.timeout.connect(self._periodic_cache_cleanup)
        self.cache_cleanup_timer.start(600000)  # Cleanup every 10 minutes for better performance
    
    def _setup_timers_on_main_thread(self):
        """Setup timers on main thread - called via QMetaObject.invokeMethod"""
        self._setup_timers()
    
    def connect_to_cluster(self, cluster_name: str, context: str = None) -> bool:
        """Connect to a Kubernetes cluster"""
        try:
            logging.info(f"Connecting to cluster: {cluster_name}")
            
            # Load kubeconfig for the context
            if not self.api_service.load_kube_config(context or cluster_name):
                error_msg = f"Failed to load kubeconfig for cluster: {cluster_name}"
                logging.error(error_msg)
                self.error_occurred.emit(error_msg)
                return False
            
            # Test connection
            if not self.api_service.is_connected():
                error_msg = f"Failed to connect to cluster API: {cluster_name}. Check if the cluster is running and accessible."
                logging.error(error_msg)
                self.error_occurred.emit(error_msg)
                return False
            
            # Update current cluster
            self.current_cluster = cluster_name
            
            # Cache system removed
            
            # Start polling
            self.start_polling()
            
            logging.info(f"Successfully connected to cluster: {cluster_name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to connect to cluster: {cluster_name}. Error: {str(e)}"
            logging.error(f"Error connecting to cluster {cluster_name}: {e}")
            self.error_occurred.emit(error_msg)
            return False
    
    def disconnect_from_cluster(self):
        """Disconnect from current cluster"""
        try:
            if self.current_cluster:
                logging.info(f"Disconnecting from cluster: {self.current_cluster}")
                
                # Stop polling
                self.stop_polling()
                
                # Stop log streams
                self.log_service.stop_all_streams()
                
                # Clear current cluster
                old_cluster = self.current_cluster
                self.current_cluster = None
                
                # Cache system removed
                
                logging.info(f"Disconnected from cluster: {old_cluster}")
                
        except Exception as e:
            logging.error(f"Error disconnecting from cluster: {e}")
    
    def start_polling(self, metrics_interval: int = 60000, issues_interval: int = 120000):
        """Start polling for metrics and issues"""
        if not self.current_cluster:
            return
        
        # Start metrics polling
        if hasattr(self, 'metrics_timer') and self.metrics_timer and not self.metrics_timer.isActive():
            self.metrics_timer.start(metrics_interval)
            logging.debug(f"Started metrics polling every {metrics_interval}ms")
        
        # Start issues polling
        if hasattr(self, 'issues_timer') and self.issues_timer and not self.issues_timer.isActive():
            self.issues_timer.start(issues_interval)
            logging.debug(f"Started issues polling every {issues_interval}ms")
    
    def stop_polling(self):
        """Stop all polling timers"""
        timers = []
        if hasattr(self, 'metrics_timer') and self.metrics_timer:
            timers.append(self.metrics_timer)
        if hasattr(self, 'issues_timer') and self.issues_timer:
            timers.append(self.issues_timer)
            
        for timer in timers:
            if timer and hasattr(timer, 'isActive') and timer.isActive():
                timer.stop()
        
        logging.debug("Stopped all polling timers")
    
    def _poll_metrics_async(self):
        """Poll metrics asynchronously"""
        if self._shutting_down or not self.current_cluster:
            return
        
        try:
            worker = AsyncMetricsWorker(self.metrics_service, self.current_cluster)
            worker.signals.finished.connect(self._handle_metrics_result)
            worker.signals.error.connect(self._handle_worker_error)
            
            self._active_workers.add(worker)
            self.threadpool.start(worker)
            
        except Exception as e:
            logging.error(f"Error starting metrics polling: {e}")
    
    def _poll_issues_async(self):
        """Poll issues asynchronously"""
        if self._shutting_down or not self.current_cluster:
            return
        
        try:
            worker = AsyncIssuesWorker(self.events_service, self.current_cluster)
            worker.signals.finished.connect(self._handle_issues_result)
            worker.signals.error.connect(self._handle_worker_error)
            
            self._active_workers.add(worker)
            self.threadpool.start(worker)
            
        except Exception as e:
            logging.error(f"Error starting issues polling: {e}")
    
    def _handle_metrics_result(self, metrics):
        """Handle metrics result from worker"""
        if not self._shutting_down and metrics:
            try:
                self.cluster_metrics_updated.emit(metrics)
                logging.debug("Emitted cluster metrics update")
            except Exception as e:
                logging.error(f"Error emitting metrics signal: {e}")
    
    def _handle_issues_result(self, issues):
        """Handle issues result from worker"""
        if not self._shutting_down and issues is not None:
            try:
                self.cluster_issues_updated.emit(issues)
                logging.debug("Emitted cluster issues update")
            except Exception as e:
                logging.error(f"Error emitting issues signal: {e}")
    
    def _handle_worker_error(self, error_info):
        """Handle worker errors"""
        error_msg = f"Worker error: {error_info}"
        logging.error(error_msg)
        if not self._shutting_down:
            self.error_occurred.emit(error_msg)
    
    def _periodic_cache_cleanup(self):
        """Cache cleanup removed"""
        pass
    
    # Public API methods
    
    def get_cluster_metrics(self, cluster_name: str = None) -> Optional[Dict[str, Any]]:
        """Get cluster metrics (synchronous)"""
        cluster = cluster_name or self.current_cluster
        if not cluster:
            return None
        return self.metrics_service.get_cluster_metrics(cluster)
    
    def get_cluster_issues(self, cluster_name: str = None) -> List[Dict[str, Any]]:
        """Get cluster issues (synchronous)"""
        cluster = cluster_name or self.current_cluster
        if not cluster:
            return []
        return self.events_service.get_cluster_issues(cluster)
    
    def get_pod_logs(self, pod_name: str, namespace: str, container: str = None, 
                     tail_lines: int = 100) -> Optional[str]:
        """Get pod logs (synchronous)"""
        return self.log_service.get_pod_logs(pod_name, namespace, container, tail_lines)
    
    def start_log_stream(self, pod_name: str, namespace: str, container: str = None, 
                        tail_lines: int = 200):
        """Start streaming logs for a pod"""
        self.log_service.start_log_stream(pod_name, namespace, container, tail_lines)
    
    def stop_log_stream(self, pod_name: str, namespace: str, container: str = None):
        """Stop streaming logs for a pod"""
        self.log_service.stop_log_stream(pod_name, namespace, container)
    
    def get_log_streamer(self):
        """Get log streamer for signal connections"""
        return self.log_service.get_log_streamer()
    
    def get_events_for_resource(self, resource_type: str, resource_name: str, 
                               namespace: str = "default") -> List[Dict[str, Any]]:
        """Get events for a specific resource"""
        return self.events_service.get_events_for_resource(resource_type, resource_name, namespace)
    
    def get_node_metrics(self, node_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific node"""
        return self.metrics_service.get_node_metrics(node_name)
    
    def get_cluster_version(self) -> Optional[str]:
        """Get Kubernetes cluster version"""
        return self.api_service.get_cluster_version()
    
    def is_connected(self) -> bool:
        """Check if connected to a cluster"""
        return self.api_service.is_connected() and self.current_cluster is not None
    
    def get_current_cluster(self) -> Optional[str]:
        """Get current cluster name"""
        return self.current_cluster
    
    def load_clusters_async(self):
        """Load available Kubernetes clusters/contexts asynchronously"""
        try:
            # Import here to avoid circular imports
            from kubernetes import config
            
            # Get available contexts from kubeconfig
            contexts, active_context = config.list_kube_config_contexts()
            
            # Convert contexts to KubeCluster objects
            clusters = []
            for context_info in contexts:
                context_name = context_info['name']
                cluster_info = context_info.get('context', {})
                
                # Determine correct status for the cluster
                if active_context and context_name == active_context['name'] and self.current_cluster == context_name:
                    # This is the currently connected cluster
                    status = "connected"
                else:
                    # All other clusters are available to connect to
                    status = "available"
                
                cluster = KubeCluster(
                    name=context_name,
                    context=context_name,
                    kind="Kubernetes Cluster",
                    source="kubeconfig",
                    label="General",
                    status=status,
                    server=cluster_info.get('cluster'),
                    user=cluster_info.get('user'),
                    namespace=cluster_info.get('namespace', 'default')
                )
                
                clusters.append(cluster)
            
            # Emit signal with clusters
            self.clusters_loaded.emit(clusters)
            logging.info(f"Loaded {len(clusters)} clusters from kubeconfig")
            
        except Exception as e:
            error_msg = f"Failed to load clusters: {str(e)}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Cache statistics removed"""
        return {}
    
    def cleanup(self):
        """Cleanup all resources"""
        if self._shutting_down:
            return
        
        logging.info("Starting KubernetesService cleanup")
        self._shutting_down = True
        
        try:
            # Stop polling
            self.stop_polling()
            
            # Stop cache cleanup timer
            if hasattr(self, 'cache_cleanup_timer') and self.cache_cleanup_timer:
                self.cache_cleanup_timer.stop()
            
            # Cleanup services
            self.log_service.cleanup()
            self.metrics_service.cleanup()
            self.events_service.cleanup()
            # Cache system removed
            self.api_service.cleanup()
            
            # Clear active workers
            self._active_workers.clear()
            
            # Force garbage collection
            gc.collect()
            
            logging.info("KubernetesService cleanup completed")
            
        except Exception as e:
            logging.error(f"Error during KubernetesService cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            if hasattr(self, '_shutting_down') and not self._shutting_down:
                logging.debug("KubernetesService destructor called, performing cleanup")
                self.cleanup()
        except Exception as e:
            logging.error(f"Error in KubernetesService destructor: {e}")


# Singleton management
_kubernetes_service_instance = None

def get_kubernetes_service() -> KubernetesService:
    """Get or create Kubernetes service singleton"""
    global _kubernetes_service_instance
    if _kubernetes_service_instance is None:
        _kubernetes_service_instance = KubernetesService()
    return _kubernetes_service_instance

def reset_kubernetes_service():
    """Reset the singleton instance"""
    global _kubernetes_service_instance
    if _kubernetes_service_instance:
        _kubernetes_service_instance.cleanup()
    _kubernetes_service_instance = None
    
    # Also reset dependent services
    reset_kubernetes_api_service()
    # Note: Unified cache system is a singleton and doesn't need explicit reset