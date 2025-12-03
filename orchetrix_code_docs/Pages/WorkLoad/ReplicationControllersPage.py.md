# ReplicationControllersPage.py Documentation

## File Information
- **Path**: `orchetrix/Pages/WorkLoad/ReplicationControllersPage.py`  
- **Purpose**: Legacy ReplicationControllers management (predecessor to ReplicaSets)

## Overview
ReplicationControllersPage displays and manages Kubernetes ReplicationControllers. ReplicationControllers are the older generation of replica management, now superseded by ReplicaSets and Deployments. Still exists for backward compatibility with legacy workloads.

## Key Differences from ReplicaSets
- **Legacy API**: Uses v1 API (ReplicaSets use apps/v1)
- **Label Selector**: Equality-based only (ReplicaSets support set-based)
- **Rolling Updates**: Manual (ReplicaSets/Deployments automate this)

## Class: ReplicaControllersPage

### Headers
```python
headers = ["", "Name", "Namespace", "Replicas", "Desired Replicas", "Selector", ""]
```

### Column Configuration
- Checkbox (40px fixed)
- Name (200px interactive)
- Namespace (100px interactive)
- Replicas (90px interactive) - current count
- Desired Replicas (70px interactive) - configured count
- Selector (70px stretch) - pod label selector
- Actions (40px fixed)

## Data Fields
- **Replicas**: Current running replicas
- **Desired Replicas**: User-configured target
- **Selector**: Label selector (e.g., `app=nginx, tier=frontend`)

## Migration Path
Kubernetes recommends migrating to Deployments:
```
ReplicationController → ReplicaSet → Deployment
```

## Dependencies
- BaseResourcePage
- SortableTableWidgetItem
- AppStyles

---

**Note**: This is a legacy resource type. New applications should use Deployments instead.
