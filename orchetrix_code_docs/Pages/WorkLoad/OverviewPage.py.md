# OverviewPage.py Documentation

## File Information
- **Path**: `orchetrix/Pages/WorkLoad/OverviewPage.py`
- **Purpose**: Cluster overview page with async data loading and metrics dashboard

## Overview
OverviewPage provides a high-level dashboard view of the Kubernetes cluster. Shows summary metrics for all workload types (Pods, Deployments, StatefulSets, DaemonSets, Jobs, CronJobs) with counts and status. Uses background worker thread to prevent UI freezing during data loading.

---

## Class: OverviewDataWorker (QThread)

### Purpose
Background worker that loads cluster overview data asynchronously to keep UI responsive.

### Signals
```python
data_loaded = pyqtSignal(dict)          # Emits loaded overview data
error_occurred = pyqtSignal(str)        # Emits error message
progress_update = pyqtSignal(int, str)  # Emits progress % and status
```

### Methods

#### `set_client(kube_client)`
Sets the Kubernetes client for API calls

#### `stop()`
Stops the worker thread gracefully

#### `run()`
Main worker thread execution:
1. **Connection Test**: Tests Kubernetes API connectivity with 5s timeout
2. **Progress Updates**: Emits progress (10%, 30%, 100%)
3. **Data Loading**: Loads overview data with 60s timeout
4. **Thread Safety**: Uses separate thread with timeout protection
5. **Error Handling**: Catches and emits errors

**Timeout Protection**:
```python
load_thread = threading.Thread(target=load_with_timeout)
load_thread.daemon = True
load_thread.start()
load_thread.join(timeout=60)  # 60 second timeout

if load_thread.is_alive():
    raise TimeoutError("Data loading timeout")
```

**Progress Flow**:
```
10% → "Connecting to Kubernetes API..."
30% → "Loading cluster metrics..."
100% → "Data loaded successfully"
```

---

## Class: OverviewPage (QWidget)

### Purpose
Displays cluster overview dashboard with workload metrics.

### Layout Structure
```
┌─────────────────────────────────────┐
│  Overview Dashboard                 │
├─────────────────────────────────────┤
│  Progress Bar (during loading)      │
├─────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐      │
│  │ Pods      │  │Deployments│      │
│  │ Count: 25 │  │ Count: 5  │      │
│  └───────────┘  └───────────┘      │
│                                     │
│  ┌───────────┐  ┌───────────┐      │
│  │StatefulSets│ │ DaemonSets│      │
│  │ Count: 3  │  │ Count: 4  │      │
│  └───────────┘  └───────────┘      │
│                                     │
│  ┌───────────┐  ┌───────────┐      │
│  │ Jobs      │  │ CronJobs  │      │
│  │ Count: 2  │  │ Count: 6  │      │
│  └───────────┘  └───────────┘      │
└─────────────────────────────────────┘
```

### Typical Metrics Displayed
- **Pods**: Total count, Running/Pending/Failed breakdown
- **Deployments**: Count, Available/Progressing status
- **StatefulSets**: Count, Ready replicas
- **DaemonSets**: Count, Desired vs Current
- **Jobs**: Count, Completed/Failed
- **CronJobs**: Count, Active/Suspended
- **Nodes**: Count, Ready/NotReady
- **Namespaces**: Count

---

## Key Features

1. **Non-Blocking UI**: Background worker prevents freezing
2. **Progress Indicator**: Shows loading progress with status text
3. **Timeout Protection**: 60s timeout prevents infinite hangs
4. **Connection Test**: Validates cluster connectivity before loading
5. **Error Handling**: Graceful error messages for connection issues
6. **Metrics Dashboard**: Visual cards for each workload type
7. **Scrollable**: Handles many metrics with scroll area
8. **Responsive**: Adapts to window size

## Use Cases
- **Cluster Health Check**: Quick view of cluster status
- **Resource Monitoring**: See total workload counts
- **Troubleshooting**: Identify issues (e.g., many failed pods)
- **Capacity Planning**: Monitor resource usage trends

## Error Scenarios

**Connection Timeout**:
```
Progress: 10% → "Connecting to Kubernetes API..."
Error: "Connection test failed: timeout"
Fallback: Continues with data load attempt
```

**Data Load Timeout**:
```
Progress: 30% → "Loading cluster metrics..."
Error: "Data loading timeout" (after 60s)
Result: Shows error message, no data displayed
```

**API Errors**:
```
Error: "Kubernetes client not available"
Result: Cannot load overview
```

## Dependencies
- QThread (background worker)
- kubernetes.client (API calls)
- AppStyles (UI styling)
- threading (timeout handling)
- logging (error tracking)

## Performance Optimization
- **Async Loading**: Doesn't block main UI thread
- **Timeout Protection**: Prevents hung requests
- **Daemon Thread**: Worker thread stops with app
- **Progress Updates**: User knows loading is happening
- **Connection Test**: Fast fail for unreachable clusters

## Example Data Structure
```python
overview_data = {
    "pods": {
        "total": 25,
        "running": 20,
        "pending": 3,
        "failed": 2
    },
    "deployments": {
        "total": 5,
        "available": 4,
        "progressing": 1
    },
    "nodes": {
        "total": 3,
        "ready": 3
    }
    # ... more workload types
}
```

This data is emitted via `data_loaded` signal and used to populate dashboard cards.
