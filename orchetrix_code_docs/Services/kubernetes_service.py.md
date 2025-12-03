# kubernetes_service.py Documentation

## File Information
- **Path**: `orchetrix/Services/kubernetes/kubernetes_service.py`
- **Purpose**: **MAIN KUBERNETES COORDINATOR** - Orchestrates all Kubernetes operations through specialized services
- **Lines**: 453
- **Pattern**: Service Coordinator + Singleton

## Overview
KubernetesService is the main entry point for all Kubernetes operations in Orchetrix. It delegates work to specialized services (APIService, LogService, MetricsService, EventsService) and coordinates cluster connections, polling, and cleanup.

**New Architecture** (modular):
```
KubernetesService (coordinator)
├── APIService (Kubernetes API access)
├── LogService (pod logs and streaming)
├── MetricsService (cluster metrics)
└── EventsService (cluster events and issues)
```

---

## Data Class: KubeCluster

```python
@dataclass
class KubeCluster:
    """Data class for Kubernetes cluster information"""
    name: str
    context: str
    kind: str = "Kubernetes Cluster"
    source: str = "local"
    label: str = "General"
    status: str = "available"  # "connected", "available", "disconnect"
    badge_color: Optional[str] = None
    server: Optional[str] = None
    user: Optional[str] = None
    namespace: Optional[str] = None
    version: Optional[str] = None
```

**Usage**: Represents a cluster in the sidebar cluster list

**Status Values**:
- **"connected"**: Currently active cluster
- **"available"**: Can connect to this cluster
- **"disconnect"**: Connection failed

---

## Worker Classes

### AsyncMetricsWorker

```python
class AsyncMetricsWorker(EnhancedBaseWorker):
    """Worker for async metrics collection"""
    def __init__(self, metrics_service, cluster_name):
        super().__init__(f"metrics_{cluster_name}")
        self.metrics_service = metrics_service
        self.cluster_name = cluster_name

    def execute(self):
        return self.metrics_service.get_cluster_metrics(self.cluster_name)
```

**Purpose**: Background polling of cluster metrics (CPU, memory, pod counts)

---

### AsyncIssuesWorker

```python
class AsyncIssuesWorker(EnhancedBaseWorker):
    """Worker for async issues collection"""
    def __init__(self, events_service, cluster_name):
        super().__init__(f"issues_{cluster_name}")
        self.events_service = events_service
        self.cluster_name = cluster_name

    def execute(self):
        return self.events_service.get_cluster_issues(self.cluster_name)
```

**Purpose**: Background polling of cluster issues (failed pods, warnings, errors)

---

## Class: KubernetesService (extends QObject)

### Signals

```python
# Signals for UI integration
clusters_loaded = pyqtSignal(list)              # List of available clusters
cluster_info_loaded = pyqtSignal(dict)          # Cluster details
cluster_metrics_updated = pyqtSignal(dict)      # CPU, memory, pods
cluster_issues_updated = pyqtSignal(list)       # Warnings, errors
resource_detail_loaded = pyqtSignal(dict)       # Resource YAML
resource_updated = pyqtSignal(dict)             # After update
pod_logs_loaded = pyqtSignal(dict)              # Pod logs
error_occurred = pyqtSignal(str)                # Error messages
```

**Signal Flow**:
```
KubernetesService → Signal → UI Component → Update display
```

---

### Constructor

```python
def __init__(self):
    super().__init__()
    self.clusters = []
    self.current_cluster = None
    self._shutting_down = False
    
    # Initialize services
    self._init_services()
    
    # Thread management
    self.threadpool = QThreadPool()
    self.threadpool.setMaxThreadCount(4)
    self.thread_manager = get_thread_manager()
    self._active_workers = weakref.WeakSet()
    
    # Setup timers for polling
    self._setup_timers()
```

**Key Components**:
- **Specialized services**: APIService, LogService, MetricsService, EventsService
- **Thread pool**: 4 threads for background operations
- **Timers**: Periodic polling of metrics and issues
- **WeakSet**: Weak references to workers (prevents leaks)

---

### Service Initialization

```python
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
```

**Service Dependencies**:
```
KubernetesService
   ↓ creates
APIService (Kubernetes Python Client wrapper)
   ↓ passed to
LogService, MetricsService, EventsService
```

---

### Timer Setup

```python
def _setup_timers(self):
    """Setup polling timers"""
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
    
    # Cache cleanup timer
    self.cache_cleanup_timer = QTimer(self)
    self.cache_cleanup_timer.timeout.connect(self._periodic_cache_cleanup)
    self.cache_cleanup_timer.start(600000)  # Every 10 minutes
```

**Thread Safety**: Same pattern as ThreadManager - defer to main thread if needed

**Polling Timers**:
- **Metrics**: Every 60 seconds (configurable)
- **Issues**: Every 120 seconds (configurable)
- **Cache cleanup**: Every 10 minutes

---

## Core Operations

### `connect_to_cluster()` - **MAIN CONNECTION METHOD**

```python
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
        
        # Start polling
        self.start_polling()
        
        logging.info(f"Successfully connected to cluster: {cluster_name}")
        return True
        
    except Exception as e:
        error_msg = f"Failed to connect to cluster: {cluster_name}. Error: {str(e)}"
        logging.error(error_msg)
        self.error_occurred.emit(error_msg)
        return False
```

**Connection Flow**:
1. Load kubeconfig for context
2. Test API connection
3. Update current cluster
4. Start metrics/issues polling
5. Return success/failure

**Error Handling**: Emits error signal on failure (UI shows error message)

---

### `disconnect_from_cluster()` - Clean Disconnection

```python
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
            
            logging.info(f"Disconnected from cluster: {old_cluster}")
            
    except Exception as e:
        logging.error(f"Error disconnecting from cluster: {e}")
```

**Cleanup Steps**:
1. Stop polling timers
2. Stop all log streams
3. Clear current cluster reference

---

## Polling System

### `start_polling()` - Enable Background Updates

```python
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
```

**Default Intervals**:
- Metrics: 60 seconds (1 minute)
- Issues: 120 seconds (2 minutes)

**Purpose**: Keep dashboard updated with latest cluster state

---

### `_poll_metrics_async()` - Background Metrics Collection

```python
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
```

**Flow**:
1. Timer fires every 60 seconds
2. Creates AsyncMetricsWorker
3. Submits to thread pool
4. On completion, emits `cluster_metrics_updated` signal

---

### `_poll_issues_async()` - Background Issues Collection

```python
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
```

**Similar to metrics polling**, but collects cluster issues

---

## Public API Methods

### Metrics

```python
def get_cluster_metrics(self, cluster_name: str = None) -> Optional[Dict[str, Any]]:
    """Get cluster metrics (synchronous)"""
    cluster = cluster_name or self.current_cluster
    if not cluster:
        return None
    return self.metrics_service.get_cluster_metrics(cluster)
```

**Returns**: 
```python
{
    'cpu_usage': 45.2,
    'memory_usage': 60.1,
    'pod_count': 127,
    'node_count': 3
}
```

---

### Issues

```python
def get_cluster_issues(self, cluster_name: str = None) -> List[Dict[str, Any]]:
    """Get cluster issues (synchronous)"""
    cluster = cluster_name or self.current_cluster
    if not cluster:
        return []
    return self.events_service.get_cluster_issues(cluster)
```

**Returns**:
```python
[
    {
        'type': 'Warning',
        'reason': 'BackOff',
        'message': 'Back-off restarting failed container',
        'resource': 'pod/nginx-abc123'
    }
]
```

---

### Logs

```python
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
```

**Log Streaming**:
- Start stream → logs continuously emit signals
- Stop stream → stops background thread

---

### Events

```python
def get_events_for_resource(self, resource_type: str, resource_name: str, 
                           namespace: str = "default") -> List[Dict[str, Any]]:
    """Get events for a specific resource"""
    return self.events_service.get_events_for_resource(resource_type, resource_name, namespace)
```

**Usage**: Show events in DetailPageComponent for selected resource

---

### Cluster Info

```python
def get_cluster_version(self) -> Optional[str]:
    """Get Kubernetes cluster version"""
    return self.api_service.get_cluster_version()

def is_connected(self) -> bool:
    """Check if connected to a cluster"""
    return self.api_service.is_connected() and self.current_cluster is not None

def get_current_cluster(self) -> Optional[str]:
    """Get current cluster name"""
    return self.current_cluster
```

---

## Cluster Discovery

### `load_clusters_async()` - Load Available Clusters

```python
def load_clusters_async(self):
    """Load available Kubernetes clusters/contexts asynchronously"""
    try:
        from kubernetes import config
        
        # Get available contexts from kubeconfig
        contexts, active_context = config.list_kube_config_contexts()
        
        # Convert contexts to KubeCluster objects
        clusters = []
        for context_info in contexts:
            context_name = context_info['name']
            cluster_info = context_info.get('context', {})
            
            # Determine status
            if active_context and context_name == active_context['name'] and self.current_cluster == context_name:
                status = "connected"
            else:
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
```

**Flow**:
1. Read `~/.kube/config` file
2. Parse all contexts (clusters)
3. Mark current cluster as "connected"
4. Emit `clusters_loaded` signal
5. Sidebar displays cluster list

---

## Cleanup

### `cleanup()` - Graceful Shutdown

```python
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
        self.api_service.cleanup()
        
        # Clear active workers
        self._active_workers.clear()
        
        # Force garbage collection
        gc.collect()
        
        logging.info("KubernetesService cleanup completed")
        
    except Exception as e:
        logging.error(f"Error during KubernetesService cleanup: {e}")
```

**Cleanup Order**:
1. Stop all polling timers
2. Cleanup specialized services
3. Clear active workers
4. Force garbage collection

---

## Singleton Pattern

```python
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
```

**Usage**:
```python
from Services.kubernetes.kubernetes_service import get_kubernetes_service

service = get_kubernetes_service()
service.connect_to_cluster("minikube")
metrics = service.get_cluster_metrics()
```

---

## Key Features

1. ✅ **Modular Architecture**: Delegates to specialized services
2. ✅ **Automatic Polling**: Keeps metrics and issues updated
3. ✅ **Thread-Safe**: Uses QObject signals and thread pool
4. ✅ **Cluster Switching**: Clean disconnect and reconnect
5. ✅ **Log Streaming**: Real-time log updates
6. ✅ **Error Handling**: Emits error signals to UI
7. ✅ **Graceful Shutdown**: Cleans up all resources
8. ✅ **Singleton Pattern**: One service across application

---

## Signal Flow Examples

### Metrics Update Flow

```
Timer fires (60s)
   ↓
_poll_metrics_async()
   ↓
Creates AsyncMetricsWorker
   ↓
Worker executes in background
   ↓
_handle_metrics_result()
   ↓
Emits cluster_metrics_updated signal
   ↓
OverviewPage receives signal
   ↓
Updates dashboard display
```

---

### Cluster Connection Flow

```
User clicks cluster in sidebar
   ↓
connect_to_cluster("minikube")
   ↓
api_service.load_kube_config("minikube")
   ↓
Test connection: api_service.is_connected()
   ↓
start_polling()
   ↓
Metrics and issues update every 60s/120s
```

---

## Dependencies

- Services.kubernetes.api_service (Kubernetes API access)
- Services.kubernetes.log_service (Pod logs)
- Services.kubernetes.metrics_service (Cluster metrics)
- Services.kubernetes.events_service (Events and issues)
- Utils.thread_manager (Background operations)
- Utils.enhanced_worker (Worker base class)
- PyQt6.QtCore (QObject, pyqtSignal, QTimer, QThreadPool)
- kubernetes (Python client library)

## Used By

- ClusterView (main application view)
- OverviewPage (dashboard)
- All resource pages (indirect via KubernetesClient wrapper)
- DetailManager (resource details)
- TerminalPanel (logs and SSH)

---

## Architecture Benefits

**Old Architecture** (monolithic):
- One giant KubernetesClient class
- 3000+ lines of code
- Hard to maintain
- Hard to test

**New Architecture** (modular):
- KubernetesService coordinates
- Specialized services handle specific concerns
- 453 lines in coordinator
- Easy to maintain and test
- Clean separation of concerns

**Backward Compatibility**: KubernetesClient wrapper maintains old API

---

## Total Lines**: 453 lines orchestrating all Kubernetes operations through 4 specialized services.
