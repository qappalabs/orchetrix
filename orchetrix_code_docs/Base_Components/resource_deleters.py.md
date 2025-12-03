# resource_deleters.py Documentation

## File Information
- **Path**: `orchetrix/Base_Components/resource_deleters.py`
- **Purpose**: Background threads for deleting Kubernetes resources (single and batch)

## Overview
Provides two thread classes for non-blocking resource deletion:
1. **ResourceDeleterThread**: Delete single resource
2. **BatchResourceDeleterThread**: Delete multiple resources in parallel

---

## Class: ResourceDeleterThread

### Purpose
Deletes a single Kubernetes resource in a background thread to prevent UI freezing.

### Constructor
```python
def __init__(self, resource_type, resource_name, namespace, parent=None):
    self.resource_type = resource_type  # e.g., "pods", "deployments"
    self.resource_name = resource_name  # e.g., "nginx-abc123"
    self.namespace = namespace  # e.g., "default"
    self.kube_client = get_kubernetes_client()
    self._is_running = True
```

### Signal
```python
delete_completed = pyqtSignal(bool, str, str, str)
# Parameters: (success, resource_type, resource_name, error_message)
```

### Method: `run()`
```python
def run(self):
    """Execute resource deletion"""
    try:
        delete_options = client.V1DeleteOptions()
        
        if self.resource_type == "pods":
            self.kube_client.v1.delete_namespaced_pod(
                name=self.resource_name,
                namespace=self.namespace,
                body=delete_options
            )
        elif self.resource_type == "deployments":
            self.kube_client.apps_v1.delete_namespaced_deployment(
                name=self.resource_name,
                namespace=self.namespace,
                body=delete_options
            )
        # ... 20+ more resource types
        
        self.delete_completed.emit(True, self.resource_type, self.resource_name, "")
    
    except ApiException as e:
        error_msg = f"API error: {e.status} - {e.reason}"
        self.delete_completed.emit(False, self.resource_type, self.resource_name, error_msg)
```

### Supported Resource Types
```python
# Core resources
"pods", "services", "configmaps", "secrets", "namespaces", "nodes", "serviceaccounts",
"endpoints", "limitranges", "resourcequotas", "podtemplates"

# Workloads
"deployments", "replicasets", "statefulsets", "daemonsets", "jobs", "cronjobs",
"replicationcontrollers"

# Storage
"persistentvolumes", "persistentvolumeclaims", "storageclasses"

# Networking
"ingresses", "networkpolicies"

# RBAC
"roles", "rolebindings", "clusterroles", "clusterrolebindings"

# Config
"horizontalpodautoscalers", "priorityclasses", "runtimeclasses", "leases",
"poddisruptionbudgets", "mutatingwebhookconfigurations", "validatingwebhookconfigurations"
```

### Usage Example
```python
# Delete a pod
thread = ResourceDeleterThread("pods", "nginx-abc123", "default")
thread.delete_completed.connect(on_delete_complete)
thread.start()

def on_delete_complete(success, resource_type, resource_name, error):
    if success:
        print(f"Deleted {resource_type}/{resource_name}")
    else:
        print(f"Failed to delete: {error}")
```

---

## Class: BatchResourceDeleterThread

### Purpose
Deletes multiple Kubernetes resources in parallel with progress tracking.

### Constructor
```python
def __init__(self, resource_type, resources, parent=None):
    self.resource_type = resource_type  # e.g., "pods"
    self.resources = resources  # List of {"name": "...", "namespace": "..."}
    self.kube_client = get_kubernetes_client()
    self._is_running = True
    self._stop_requested = False
```

### Signals
```python
progress_updated = pyqtSignal(int, int, str)
# Parameters: (completed_count, total_count, current_resource_name)

delete_complete = pyqtSignal(int, int, list)
# Parameters: (successful_count, failed_count, error_messages)

error_occurred = pyqtSignal(str)
# Parameter: error_message
```

### Method: `run()`
```python
def run(self):
    """Execute batch deletion with progress tracking"""
    total = len(self.resources)
    successful = 0
    failed = 0
    errors = []
    
    for i, resource in enumerate(self.resources):
        if self._stop_requested:
            break
        
        try:
            # Emit progress
            self.progress_updated.emit(i, total, resource["name"])
            
            # Delete resource
            delete_options = client.V1DeleteOptions()
            if self.resource_type == "pods":
                self.kube_client.v1.delete_namespaced_pod(
                    name=resource["name"],
                    namespace=resource["namespace"],
                    body=delete_options
                )
            # ... other resource types
            
            successful += 1
        
        except Exception as e:
            failed += 1
            errors.append(f"{resource['name']}: {str(e)}")
    
    # Emit completion
    self.delete_complete.emit(successful, failed, errors)
```

### Method: `stop()`
```python
def stop(self):
    """Stop batch deletion gracefully"""
    self._stop_requested = True
```

### Usage Example
```python
# Delete 5 selected pods
resources = [
    {"name": "pod-1", "namespace": "default"},
    {"name": "pod-2", "namespace": "default"},
    {"name": "pod-3", "namespace": "kube-system"},
    # ... more
]

thread = BatchResourceDeleterThread("pods", resources)

# Connect signals
thread.progress_updated.connect(update_progress_bar)
thread.delete_complete.connect(on_batch_complete)
thread.error_occurred.connect(show_error)

# Start deletion
thread.start()

def update_progress_bar(completed, total, current):
    progress = (completed / total) * 100
    progress_bar.setValue(progress)
    status_label.setText(f"Deleting {current}...")

def on_batch_complete(successful, failed, errors):
    if failed > 0:
        print(f"Deleted {successful}, Failed {failed}")
        print("Errors:", errors)
    else:
        print(f"Successfully deleted all {successful} resources")
```

---

## Deletion Flow

### Single Resource Deletion
```
User clicks "Delete" on pod → 
Confirmation dialog →
User confirms →
Create ResourceDeleterThread →
Start thread (background) →
Thread calls Kubernetes API →
API deletes resource →
Thread emits delete_completed signal →
UI receives signal →
UI shows success message →
UI reloads resource list
```

### Batch Deletion
```
User selects 5 pods (checkboxes) →
User clicks "Delete Selected" →
Confirmation dialog →
User confirms →
Create BatchResourceDeleterThread →
Start thread (background) →
Thread loops through resources:
  - Delete resource 1 → emit progress (1/5)
  - Delete resource 2 → emit progress (2/5)
  - Delete resource 3 → emit progress (3/5)
  - Delete resource 4 → emit progress (4/5)
  - Delete resource 5 → emit progress (5/5)
Thread emits delete_complete →
UI shows summary (5 successful, 0 failed) →
UI reloads resource list
```

---

## Error Handling

### API Errors
```python
except ApiException as e:
    if e.status == 404:
        error_msg = "Resource not found (may have been already deleted)"
    elif e.status == 403:
        error_msg = "Permission denied (check RBAC)"
    elif e.status == 409:
        error_msg = "Conflict (resource has finalizers or is being deleted)"
    else:
        error_msg = f"API error: {e.status} - {e.reason}"
```

### Graceful Cancellation
```python
# User clicks "Cancel" during batch delete
thread.stop()  # Sets _stop_requested = True

# Thread checks flag in loop
for resource in resources:
    if self._stop_requested:
        break  # Stop deleting, emit partial results
    # ... continue deletion
```

---

## Thread Safety

### Why Threads?
- Deletion can take 1-10 seconds per resource
- Without threads: UI freezes during deletion
- With threads: UI remains responsive, user can continue working

### Signal-Slot Pattern
- Thread runs in background
- Emits signals when events occur
- UI receives signals on main thread
- UI updates safely (no cross-thread GUI access)

---

## Dependencies
- kubernetes.client (Kubernetes API)
- PyQt6.QtCore (QThread, pyqtSignal)
- Utils.kubernetes_client (get_kubernetes_client)

## Used By
- base_resource_page.py (all resource pages)
- Action menu "Delete" option
- "Delete Selected" button
