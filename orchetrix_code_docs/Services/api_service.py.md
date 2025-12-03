# api_service.py Documentation

## File Information
- **Path**: `orchetrix/Services/kubernetes/api_service.py`
- **Purpose**: **KUBERNETES API CLIENT MANAGER** - Thread-safe wrapper for Kubernetes Python Client library
- **Lines**: 369
- **Pattern**: Singleton + Lazy Initialization + Thread Safety

## Overview
KubernetesAPIService manages all Kubernetes API clients (CoreV1Api, AppsV1Api, etc.) with thread-safe lazy initialization. It handles kubeconfig loading, connection pooling, timeout detection, and provides a clean interface for all Kubernetes API operations.

**Why Critical**: This is the gateway to the Kubernetes cluster. Every API call goes through these clients.

---

## Architecture: API Client Management

```
Application
   ↓
KubernetesAPIService (singleton)
   ↓ manages
16 ThreadSafeAPIClient wrappers
   ↓ wrap
Kubernetes Python Client library
   ↓ calls
Kubernetes API Server
```

---

## Class: ThreadSafeAPIClient

### Purpose
Thread-safe lazy wrapper for Kubernetes API client classes. Ensures each client is initialized only once and safely across multiple threads.

### Constructor

```python
def __init__(self, api_class):
    self.api_class = api_class
    self._instance = None
    self._lock = threading.RLock()  # Reentrant lock
    self._initialization_failed = False
    self._initialization_error = None
    self._creation_attempts = 0
    self._max_attempts = 3
```

**Key Fields**:
- `api_class`: The Kubernetes API class to wrap (e.g., `client.CoreV1Api`)
- `_instance`: Cached instance (created on first access)
- `_lock`: RLock for thread-safe initialization
- `_initialization_failed`: Permanent failure flag
- `_creation_attempts`: Retry counter (max 3 attempts)

---

### `get_instance()` - **THREAD-SAFE LAZY INITIALIZATION**

```python
def get_instance(self):
    """Thread-safe instance getter with proper error isolation"""
    # Fast path: if we already have an instance, return it
    if self._instance is not None:
        return self._instance
        
    # Slow path: need to create instance
    with self._lock:
        # Double-check pattern
        if self._instance is not None:
            return self._instance
            
        # Check if we've permanently failed
        if self._initialization_failed:
            raise self._initialization_error
            
        # Attempt to create instance
        try:
            self._creation_attempts += 1
            if self._creation_attempts > self._max_attempts:
                self._initialization_failed = True
                self._initialization_error = Exception(
                    f"Max initialization attempts ({self._max_attempts}) exceeded for {self.api_class.__name__}"
                )
                raise self._initialization_error
            
            logging.debug(f"Creating API client instance: {self.api_class.__name__} (attempt {self._creation_attempts})")
            self._instance = self.api_class()
            logging.debug(f"Successfully initialized {self.api_class.__name__}")
            return self._instance
            
        except Exception as e:
            logging.error(f"Failed to initialize {self.api_class.__name__} (attempt {self._creation_attempts}): {e}")
            
            # On final attempt, mark as permanently failed
            if self._creation_attempts >= self._max_attempts:
                self._initialization_failed = True
                self._initialization_error = Exception(
                    f"Failed to initialize {self.api_class.__name__} after {self._creation_attempts} attempts: {str(e)}"
                )
                raise self._initialization_error
            
            raise
```

**Double-Check Locking Pattern**:
1. **Fast path** (no lock): Return if instance exists
2. **Slow path** (with lock): Create if needed
3. **Double-check**: Check again inside lock (another thread may have created it)
4. **Retry logic**: Up to 3 attempts
5. **Permanent failure**: After 3 failures, stop trying

**Why RLock**: Allows same thread to acquire lock multiple times (prevents deadlock)

---

### `__getattr__()` - Transparent Delegation

```python
def __getattr__(self, name):
    """Delegate attribute access to the API client instance"""
    instance = self.get_instance()
    return getattr(instance, name)
```

**Usage**:
```python
wrapper = ThreadSafeAPIClient(client.CoreV1Api)
pods = wrapper.list_pod_for_all_namespaces()
# ↑ Calls get_instance(), then list_pod_for_all_namespaces() on real client
```

---

### `reset()` - Context Switch Support

```python
def reset(self):
    """Reset the cached instance and error state"""
    with self._lock:
        self._instance = None
        self._initialization_failed = False
        self._initialization_error = None
        self._creation_attempts = 0
        logging.debug(f"Reset {self.api_class.__name__} API client")
```

**When Called**: When switching Kubernetes contexts/clusters

---

## Class: KubernetesAPIService

### Constructor

```python
def __init__(self):
    self._api_clients: Dict[str, ThreadSafeAPIClient] = {}
    self._cached_clients = False
    self._cached_context = None
    self._api_timeout_detected = False
    self._consecutive_timeouts = 0
    self._max_consecutive_timeouts = 3
    self._setup_lazy_clients()
```

**Timeout Detection**: Tracks consecutive timeouts to avoid wasting resources

---

### `_setup_lazy_clients()` - Initialize All API Clients

```python
def _setup_lazy_clients(self):
    """Initialize thread-safe API clients"""
    self._api_clients = {
        'CoreV1Api': ThreadSafeAPIClient(client.CoreV1Api),
        'AppsV1Api': ThreadSafeAPIClient(client.AppsV1Api),
        'NetworkingV1Api': ThreadSafeAPIClient(client.NetworkingV1Api),
        'StorageV1Api': ThreadSafeAPIClient(client.StorageV1Api),
        'RbacAuthorizationV1Api': ThreadSafeAPIClient(client.RbacAuthorizationV1Api),
        'BatchV1Api': ThreadSafeAPIClient(client.BatchV1Api),
        'AutoscalingV1Api': ThreadSafeAPIClient(client.AutoscalingV1Api),
        'AutoscalingV2Api': ThreadSafeAPIClient(client.AutoscalingV2Api),
        'PolicyV1Api': ThreadSafeAPIClient(client.PolicyV1Api),
        'SchedulingV1Api': ThreadSafeAPIClient(client.SchedulingV1Api),
        'NodeV1Api': ThreadSafeAPIClient(client.NodeV1Api),
        'AdmissionregistrationV1Api': ThreadSafeAPIClient(client.AdmissionregistrationV1Api),
        'CoordinationV1Api': ThreadSafeAPIClient(client.CoordinationV1Api),
        'ApiextensionsV1Api': ThreadSafeAPIClient(client.ApiextensionsV1Api),
        'CustomObjectsApi': ThreadSafeAPIClient(client.CustomObjectsApi),
        'VersionApi': ThreadSafeAPIClient(client.VersionApi),
    }
```

**16 API Clients** for different Kubernetes resource groups:
- **Core**: pods, services, nodes, configmaps, secrets
- **Apps**: deployments, replicasets, statefulsets, daemonsets
- **Networking**: services, ingresses, networkpolicies
- **Storage**: persistentvolumes, storageclasses
- **RBAC**: roles, rolebindings, clusterroles
- **Batch**: jobs, cronjobs
- **Policy**: poddisruptionbudgets
- **Autoscaling**: horizontalpodautoscalers
- **Custom**: CRDs and custom resources

---

### `load_kube_config()` - **CONNECTION SETUP**

```python
def load_kube_config(self, context_name: Optional[str] = None):
    """Load kubernetes configuration with connection optimization"""
    try:
        if context_name:
            config.load_kube_config(context=context_name)
            logging.info(f"Loaded kubeconfig for context: {context_name}")
        else:
            config.load_kube_config()
            logging.info("Loaded default kubeconfig")
        
        # Configure API client settings
        configuration = client.Configuration.get_default_copy()
        
        # Connection pooling
        configuration.connection_pool_maxsize = 10
        
        # Timeout settings
        configuration.socket_timeout = 15
        configuration.request_timeout = 30
        
        # Retry settings
        configuration.retries = 5
        
        # Connection timeout
        if hasattr(configuration, 'connect_timeout'):
            configuration.connect_timeout = 10
        
        # Apply configuration
        client.Configuration.set_default(configuration)
        logging.debug("Applied optimized Kubernetes API client configuration")
        
        # Reset clients when context changes
        if self._cached_context != context_name:
            self.reset_clients()
            self._cached_context = context_name
            self._cached_clients = True
            
        return True
        
    except ConfigException as e:
        logging.error(f"Failed to load kubeconfig: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error loading kubeconfig: {e}")
        return False
```

**Configuration Optimizations**:
- **connection_pool_maxsize: 10**: Reuse connections for better performance
- **socket_timeout: 15s**: Detect failed connections quickly
- **request_timeout: 30s**: Allow time for slow API calls
- **retries: 5**: Retry failed requests automatically
- **connect_timeout: 10s**: Quick connection establishment

**Context Switching**: Resets all clients when switching clusters

---

### `is_connected()` - **CONNECTION CHECK**

```python
def is_connected(self) -> bool:
    """Check if API clients are properly initialized"""
    # Skip check if we've had too many consecutive timeouts
    if self._consecutive_timeouts >= self._max_consecutive_timeouts:
        logging.debug("Skipping connectivity check due to consecutive timeout limit")
        return False
        
    try:
        # Try to access version API as connectivity test
        version_info = self.version_api.get_code(_request_timeout=10)
        logging.info("Successfully connected to Kubernetes API")
        
        # Reset timeout counters on success
        self._consecutive_timeouts = 0
        self._api_timeout_detected = False
        
        return version_info is not None
    except Exception as e:
        # Classify error types
        if "timeout" in str(e).lower():
            self._consecutive_timeouts += 1
            self._api_timeout_detected = True
            logging.warning(f"Kubernetes API connectivity timeout #{self._consecutive_timeouts}")
            
            # Stop trying after max consecutive timeouts
            if self._consecutive_timeouts >= self._max_consecutive_timeouts:
                logging.error(f"Maximum consecutive timeouts reached. Stopping connection attempts.")
                return False
        elif "connection" in str(e).lower():
            logging.warning(f"Kubernetes API connection refused - cluster may be down")
        elif "unauthorized" in str(e).lower() or "forbidden" in str(e).lower():
            logging.error(f"Kubernetes API authentication/authorization error")
        else:
            logging.error(f"Kubernetes API connectivity check failed: {e}")
        return False
```

**Timeout Protection**:
- Tracks consecutive timeouts
- After 3 consecutive timeouts, stops checking (prevents resource exhaustion)
- Resets counter on successful connection

**Error Classification**:
- **Timeout**: Slow/unresponsive cluster
- **Connection refused**: Cluster down
- **Unauthorized/Forbidden**: Permission issue
- **Other**: Unknown error

---

### API Client Properties

```python
@property
def v1(self):
    """Get CoreV1Api client"""
    return self.get_api_client('CoreV1Api').get_instance()

@property
def apps_v1(self):
    """Get AppsV1Api client"""
    return self.get_api_client('AppsV1Api').get_instance()

@property
def networking_v1(self):
    """Get NetworkingV1Api client"""
    return self.get_api_client('NetworkingV1Api').get_instance()

# ... 13 more properties
```

**Usage**:
```python
api_service = get_kubernetes_api_service()
pods = api_service.v1.list_pod_for_all_namespaces()
deployments = api_service.apps_v1.list_deployment_for_all_namespaces()
services = api_service.v1.list_service_for_all_namespaces()
```

**All 16 Properties**:
- `v1` → CoreV1Api
- `apps_v1` → AppsV1Api
- `networking_v1` → NetworkingV1Api
- `storage_v1` → StorageV1Api
- `rbac_v1` → RbacAuthorizationV1Api
- `batch_v1` → BatchV1Api
- `autoscaling_v1` → AutoscalingV1Api
- `autoscaling_v2` → AutoscalingV2Api
- `policy_v1` → PolicyV1Api
- `scheduling_v1` → SchedulingV1Api
- `node_v1` → NodeV1Api
- `admissionregistration_v1` → AdmissionregistrationV1Api
- `coordination_v1` → CoordinationV1Api
- `apiextensions_v1` → ApiextensionsV1Api
- `custom_objects_api` → CustomObjectsApi
- `version_api` → VersionApi

---

### `reset_clients()` - Context Switch

```python
def reset_clients(self):
    """Reset all API clients - useful when switching contexts"""
    logging.debug("Resetting all API clients")
    for client_name, api_client in self._api_clients.items():
        try:
            api_client.reset()
        except Exception as e:
            logging.error(f"Error resetting {client_name}: {e}")
    
    self._cached_clients = False
    self._cached_context = None
```

**When Called**: User switches from cluster A to cluster B

---

### `get_cluster_version()` - Version Info

```python
def get_cluster_version(self) -> Optional[str]:
    """Get Kubernetes cluster version"""
    try:
        version_info = self.version_api.get_code()
        return f"{version_info.major}.{version_info.minor}"
    except Exception as e:
        logging.error(f"Failed to get cluster version: {e}")
        return None
```

**Returns**: "1.28", "1.29", etc.

---

## Singleton Pattern

```python
_api_service_instance = None

def get_kubernetes_api_service() -> KubernetesAPIService:
    """Get or create Kubernetes API service singleton"""
    global _api_service_instance
    if _api_service_instance is None:
        _api_service_instance = KubernetesAPIService()
    return _api_service_instance

def reset_kubernetes_api_service():
    """Reset the singleton instance"""
    global _api_service_instance
    if _api_service_instance:
        _api_service_instance.cleanup()
    _api_service_instance = None
```

---

## Usage Examples

### Load Kubeconfig and Connect

```python
from Services.kubernetes.api_service import get_kubernetes_api_service

api_service = get_kubernetes_api_service()

# Load default context
api_service.load_kube_config()

# Or load specific context
api_service.load_kube_config("minikube")

# Check connection
if api_service.is_connected():
    print("Connected to Kubernetes cluster")
```

### List Pods

```python
api_service = get_kubernetes_api_service()
pods = api_service.v1.list_pod_for_all_namespaces()

for pod in pods.items:
    print(f"{pod.metadata.name} - {pod.status.phase}")
```

### List Deployments

```python
api_service = get_kubernetes_api_service()
deployments = api_service.apps_v1.list_deployment_for_all_namespaces()

for deployment in deployments.items:
    print(f"{deployment.metadata.name} - {deployment.status.replicas} replicas")
```

### Get Cluster Version

```python
api_service = get_kubernetes_api_service()
version = api_service.get_cluster_version()
print(f"Kubernetes version: {version}")
```

---

## Key Features

1. ✅ **Thread-Safe**: RLock protects initialization
2. ✅ **Lazy Loading**: Clients created on first use
3. ✅ **Retry Logic**: Up to 3 initialization attempts
4. ✅ **Connection Pooling**: Reuse HTTP connections
5. ✅ **Timeout Detection**: Stops checking after 3 timeouts
6. ✅ **Context Switching**: Reset clients when changing clusters
7. ✅ **Error Classification**: Different handling for different errors
8. ✅ **Singleton Pattern**: One service instance

---

## Performance Optimizations

**Connection Pooling** (maxsize=10):
- Reuses TCP connections
- Reduces connection overhead
- Faster API calls

**Timeout Settings**:
- **15s socket timeout**: Quick failure detection
- **30s request timeout**: Allow slow operations
- **10s connect timeout**: Fast connection establishment

**Retry Logic** (5 retries):
- Automatically retries failed requests
- Handles transient network issues
- Exponential backoff (built into Kubernetes client)

---

## Error Handling

### Timeout Protection

```python
# After 3 consecutive timeouts, stop checking
if self._consecutive_timeouts >= 3:
    return False  # Don't waste resources
```

**Prevents**: Resource exhaustion from repeated timeout attempts

### Error Classification

```python
if "timeout" in str(e).lower():
    # Handle timeout
elif "connection" in str(e).lower():
    # Handle connection error
elif "unauthorized" in str(e).lower():
    # Handle auth error
```

**Benefits**: Appropriate response for each error type

---

## Dependencies

- kubernetes (Python client library)
- threading (RLock for thread safety)
- logging (error tracking)

## Used By

- KubernetesService (main coordinator)
- LogService, MetricsService, EventsService (specialized services)
- KubernetesClient (backward compatibility wrapper)
- UnifiedResourceLoader (resource loading)

---

## Critical for Application

Without KubernetesAPIService:
- ❌ No connection to Kubernetes cluster
- ❌ Thread-safety issues
- ❌ No connection pooling (slow)
- ❌ No timeout protection (hangs)

With KubernetesAPIService:
- ✅ Clean API access
- ✅ Thread-safe operations
- ✅ Fast API calls (pooling)
- ✅ Robust error handling

---

## Total Lines**: 369 lines managing thread-safe access to 16 Kubernetes API clients.
