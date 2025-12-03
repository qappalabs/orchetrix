# ReplicaSetsPage.py Documentation

## File Information
- **Path**: `orchetrix/Pages/WorkLoad/ReplicaSetsPage.py`
- **Lines**: 207
- **Purpose**: Kubernetes ReplicaSets management page with desired/current/ready pod tracking

## Overview
ReplicaSetsPage displays and manages Kubernetes ReplicaSets. ReplicaSets ensure a specified number of pod replicas are running at any time. They are typically created and managed by Deployments, but can also be created standalone. This page shows three key metrics: desired replicas, current replicas, and ready replicas.

---

## Class: ReplicaSetsPage

### Constructor
```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.resource_type = "replicasets"
    self.setup_page_ui()
```

### UI Setup
```python
def setup_page_ui(self):
    headers = ["", "Name", "Namespace", "Desired", "Current", "Ready", "Age", ""]
    sortable_columns = {1, 2, 3, 4, 5, 6}
```

**8 columns**: Checkbox, Name, Namespace, Desired, Current, Ready, Age, Actions

### Column Configuration
```python
column_specs = [
    (0, 40, "fixed"),        # Checkbox
    (1, 200, "interactive"), # Name
    (2, 100, "interactive"), # Namespace
    (3, 90, "interactive"),  # Desired
    (4, 70, "interactive"),  # Current
    (5, 70, "interactive"),  # Ready
    (6, 50, "stretch"),      # Age
    (7, 40, "fixed")         # Actions
]
```

---

## Data Extraction

### Replica Counts
```python
desired = "0"
current = "0"
ready = "0"

if raw_data:
    spec = raw_data.get("spec", {})
    status = raw_data.get("status", {})
    
    desired = str(spec.get("replicas", 0))
    current = str(status.get("replicas", 0))
    ready = str(status.get("readyReplicas", 0))
```

**Three Key Metrics**:
1. **Desired**: User-configured replica count from spec
2. **Current**: Actual number of pods created (may not be ready)
3. **Ready**: Number of pods fully ready to serve traffic

**Example States**:
- `Desired: 3, Current: 3, Ready: 3` → Healthy, all pods running
- `Desired: 3, Current: 3, Ready: 2` → 1 pod not ready yet
- `Desired: 3, Current: 2, Ready: 2` → Missing 1 pod (being created)
- `Desired: 3, Current: 0, Ready: 0` → ReplicaSet not working

---

## Sortable Columns

### Numeric Columns (Desired, Current, Ready)
```python
if col >= 2 and col <= 4:  # Desired, Current, Ready columns
    try:
        num = int(value)
    except ValueError:
        num = 0
    item = SortableTableWidgetItem(value, num)
```
Sorts numerically (10 > 5 > 1)

### Age Column
```python
elif col == 5:  # Age column
    try:
        if 'd' in value:
            age_value = int(value.replace('d', '')) * 1440
        elif 'h' in value:
            age_value = int(value.replace('h', '')) * 60
        elif 'm' in value:
            age_value = int(value.replace('m', ''))
        else:
            age_value = 0
    except ValueError:
        age_value = 0
    item = SortableTableWidgetItem(value, age_value)
```
Converts to minutes for chronological sorting

---

## Key Features

1. **Three-Level Status**: Desired, Current, Ready metrics
2. **Pod Health Tracking**: See which replicas are ready
3. **Sortable Columns**: Sort by any metric
4. **Detail View**: Click row for full ReplicaSet details
5. **Action Menu**: Edit and Delete options
6. **Bulk Selection**: Multi-delete via checkbox
7. **Responsive Layout**: Age column stretches

## Action Menu Items
- **Edit**: Edit ReplicaSet YAML
- **Delete**: Delete the ReplicaSet (deletes all pods)

## ReplicaSet Characteristics

### What are ReplicaSets?
ReplicaSets maintain a stable set of replica pods running at any given time. They are the next-generation Replication Controller.

### Relationship with Deployments
- **Deployments manage ReplicaSets**: When you create a Deployment, it creates a ReplicaSet
- **ReplicaSets manage Pods**: The ReplicaSet ensures pods are running
- **Hierarchy**: Deployment → ReplicaSet → Pods

**Example**:
```
nginx-deployment (Deployment)
  └── nginx-deployment-abc123 (ReplicaSet)
       ├── nginx-deployment-abc123-pod1
       ├── nginx-deployment-abc123-pod2
       └── nginx-deployment-abc123-pod3
```

### When to Use Standalone ReplicaSets
- Legacy applications
- Direct pod management without Deployment features
- Advanced use cases requiring ReplicaSet-only features

### Difference from Deployments
| Feature | Deployment | ReplicaSet |
|---------|-----------|------------|
| Rolling updates | Yes | No |
| Rollback | Yes | No |
| Multiple ReplicaSets | Yes (versions) | No |
| Use case | Production apps | Deployment backend |

## Example Data Display

### Healthy ReplicaSet
```
Name: nginx-rs
Desired: 5
Current: 5
Ready: 5
Age: 3d

Interpretation: All 5 pods running and ready
```

### Scaling Up
```
Name: nginx-rs
Desired: 10
Current: 7
Ready: 7
Age: 3d

Interpretation: Scaled from 5 to 10, still creating 3 pods
```

### Unhealthy Pods
```
Name: nginx-rs
Desired: 5
Current: 5
Ready: 3
Age: 3d

Interpretation: 2 pods exist but not ready (CrashLoopBackOff, ImagePullBackOff, etc.)
```

## Dependencies
- BaseResourcePage
- SortableTableWidgetItem
- DetailManager
- AppStyles
