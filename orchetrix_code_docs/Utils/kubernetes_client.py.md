# kubernetes_client.py Documentation

## File Information
- **Path**: `orchetrix/Utils/kubernetes_client.py`
- **Purpose**: **BACKWARD COMPATIBILITY WRAPPER** - Maintains old API while using new service architecture

## Overview
KubernetesClient is a wrapper that provides the same API as the original monolithic client but delegates all work to the new modular service architecture (KubernetesService). This allows gradual migration without breaking existing code.

---

## Architecture Pattern: Adapter/Wrapper

```
Old Code (50+ pages):
   ↓ Uses old API
KubernetesClient (this file) ← Adapter/Wrapper
   ↓ Delegates to new services
KubernetesService (new architecture)
   ↓ Uses specialized services
APIService, EventsService, LogService, etc.
   ↓ Calls
Kubernetes Python Client Library
```

**Why This Pattern**:
- ✅ Don't break 50+ existing resource pages
- ✅ Gradually migrate to new architecture
- ✅ Test new services without rewriting everything
- ✅ Maintain backward compatibility

---

## Class: ResourceUpdateWorker

**Purpose**: Background worker for async resource updates

```python
class ResourceUpdateWorker(EnhancedBaseWorker):
    def __init__(self, client_instance, resource_type, resource_name, 
                 namespace, yaml_data):
        super().__init__(f"resource_update_{resource_type}_{resource_name}")
        self.client_instance = client_instance
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.yaml_data = yaml_data

    def execute(self):
        return self.client_instance._update_resource_sync(
            self.resource_type,
            self.resource_name,
            self.namespace,
            self.yaml_data
        )
```

**Usage**: Updates resource YAML in background thread (e.g., editing pod config)

---

## Class: KubernetesClient (extends QObject)

### Signals (Backward Compatibility)

```python
# All original signals maintained
clusters_loaded = pyqtSignal(list)
cluster_info_loaded = pyqtSignal(dict)
cluster_metrics_updated = pyqtSignal(dict)
cluster_issues_updated = pyqtSignal(list)
resource_detail_loaded = pyqtSignal(dict)
resource_updated = pyqtSignal(dict)
pod_logs_loaded = pyqtSignal(dict)
pods_data_loaded = pyqtSignal(list)
api_error = pyqtSignal(str)
error_occurred = pyqtSignal(str)

# Deployment rollback signals
deployment_history_loaded = pyqtSignal(list)
deployment_rollback_completed = pyqtSignal(dict)
```

**Compatibility**: Old code connects to these signals, still works

---

### Constructor

```python
def __init__(self):
    super().__init__()
    
    # Get new service architecture
    self.service = get_kubernetes_service()
    
    # Connect signals for backward compatibility
    self._connect_service_signals()
    
    # Maintain backward compatibility attributes
    self.clusters = []
    self.current_cluster = None
    self._shutting_down = False
    
    logging.info("KubernetesClient initialized with new service architecture")
```

**Key**: Gets KubernetesService singleton and connects its signals to our signals

---

### Signal Connection

```python
def _connect_service_signals(self):
    """Connect service signals to maintain backward compatibility"""
    self.service.clusters_loaded.connect(self.clusters_loaded.emit)
    self.service.cluster_info_loaded.connect(self.cluster_info_loaded.emit)
    self.service.cluster_metrics_updated.connect(self.cluster_metrics_updated.emit)
    self.service.cluster_issues_updated.connect(self.cluster_issues_updated.emit)
    self.service.resource_detail_loaded.connect(self.resource_detail_loaded.emit)
    self.service.resource_updated.connect(self.resource_updated.emit)
    self.service.pod_logs_loaded.connect(self.pod_logs_loaded.emit)
    self.service.error_occurred.connect(self.error_occurred.emit)
```

**Pattern**: Pass-through signal connections
```
KubernetesService.clusters_loaded 
   → emits → 
KubernetesClient.clusters_loaded 
   → emits → 
Old code receives signal
```

---

### API Properties (Backward Compatibility)

**Direct Access to Kubernetes API Clients**:

```python
@property
def v1(self):
    """Access to CoreV1Api - backward compatibility"""
    return self.service.api_service.v1

@property
def apps_v1(self):
    """Access to AppsV1Api - backward compatibility"""
    return self.service.api_service.apps_v1

@property
def networking_v1(self):
    """Access to NetworkingV1Api - backward compatibility"""
    return self.service.api_service.networking_v1

@property
def storage_v1(self):
    """Access to StorageV1Api - backward compatibility"""
    return self.service.api_service.storage_v1

@property
def rbac_v1(self):
    """Access to RbacAuthorizationV1Api - backward compatibility"""
    return self.service.api_service.rbac_v1

@property
def batch_v1(self):
    """Access to BatchV1Api - backward compatibility"""
    return self.service.api_service.batch_v1

@property
def autoscaling_v1(self):
    """Access to AutoscalingV1Api - backward compatibility"""
    return self.service.api_service.autoscaling_v1

@property
def autoscaling_v2(self):
    """Access to AutoscalingV2Api - backward compatibility"""
    return self.service.api_service.autoscaling_v2

@property
def policy_v1(self):
    """Access to PolicyV1Api - backward compatibility"""
    return self.service.api_service.policy_v1

@property
def scheduling_v1(self):
    """Access to SchedulingV1Api - backward compatibility"""
    return self.service.api_service.scheduling_v1

@property
def node_v1(self):
    """Access to NodeV1Api - backward compatibility"""
    return self.service.api_service.node_v1

@property
def admissionregistration_v1(self):
    """Access to AdmissionregistrationV1Api - backward compatibility"""
    return self.service.api_service.admissionregistration_v1
```

**Usage in Old Code** (still works):
```python
client = get_kubernetes_client()

# Delete pod using old API
client.v1.delete_namespaced_pod(
    name="nginx",
    namespace="default"
)

# List deployments using old API
deployments = client.apps_v1.list_namespaced_deployment(
    namespace="default"
)
```

---

## Singleton Pattern

```python
_kubernetes_client_instance = None

def get_kubernetes_client() -> KubernetesClient:
    """Get singleton instance of KubernetesClient"""
    global _kubernetes_client_instance
    if _kubernetes_client_instance is None:
        _kubernetes_client_instance = KubernetesClient()
    return _kubernetes_client_instance
```

**Ensures**: Only one Kubernetes client instance exists across entire application

---

## Migration Strategy

### Phase 1: Wrapper (Current State)
```python
# Old code still works
client = get_kubernetes_client()
client.v1.list_namespaced_pod(namespace="default")
```

### Phase 2: New API (Future)
```python
# New code uses service directly
service = get_kubernetes_service()
pods = service.list_pods(namespace="default")
```

### Phase 3: Deprecation (Later)
```python
# KubernetesClient marked as deprecated
# All code migrated to new service
# Remove KubernetesClient wrapper
```

---

## Key Features

1. ✅ **Backward Compatibility**: Old code continues working
2. ✅ **Signal Pass-Through**: All signals preserved
3. ✅ **API Access**: Direct access to all Kubernetes APIs
4. ✅ **Singleton**: One instance across application
5. ✅ **Gradual Migration**: Migrate code piece by piece
6. ✅ **No Breaking Changes**: Existing 50+ pages unaffected

---

## Used By
- **Every resource page** (Pods, Deployments, Services, etc.)
- **Resource deleters** (delete operations)
- **Detail pages** (YAML loading/updating)
- **Terminal panel** (logs, exec)
- **Port forwarding** (port forward operations)

**Total**: 50+ files depend on this

---

## Dependencies
- Services.kubernetes.kubernetes_service (new architecture)
- Utils.enhanced_worker (background workers)
- Utils.thread_manager (thread management)
- PyQt6.QtCore (QObject, pyqtSignal)

---

## Example Usage

### Delete Pod (Old API - Still Works)
```python
client = get_kubernetes_client()
client.v1.delete_namespaced_pod(
    name="nginx-abc123",
    namespace="default",
    body=V1DeleteOptions()
)
```

### List Deployments (Old API - Still Works)
```python
client = get_kubernetes_client()
deployments = client.apps_v1.list_namespaced_deployment(
    namespace="default"
)
for deploy in deployments.items:
    print(deploy.metadata.name)
```

### Update Resource (Async with Worker)
```python
client = get_kubernetes_client()
worker = ResourceUpdateWorker(
    client, 
    "pod", 
    "nginx", 
    "default", 
    yaml_data
)
worker.start()
```

---

## Why This Pattern Is Important

Without this wrapper, migrating to new architecture would require:
- ❌ Rewriting 50+ resource pages simultaneously
- ❌ High risk of bugs
- ❌ Difficult testing
- ❌ Long development time

With this wrapper:
- ✅ Migrate gradually
- ✅ Test incrementally  
- ✅ No broken functionality
- ✅ Low risk
