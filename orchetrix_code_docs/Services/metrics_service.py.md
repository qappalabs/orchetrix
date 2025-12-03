# metrics_service.py - Brief Documentation

**Path**: `orchetrix/Services/kubernetes/metrics_service.py`
**Lines**: ~250
**Purpose**: Collects cluster and node metrics

## Key Features
- Cluster-wide CPU/memory metrics
- Node-level metrics
- Pod count aggregation
- Metrics API integration

## Main Methods
- `get_cluster_metrics(cluster_name)` - Aggregate cluster metrics
- `get_node_metrics(node_name)` - Node-specific metrics
- `collect_metrics()` - Collect from Metrics API

## Returns
```python
{
    'cpu_usage': 45.2,
    'memory_usage': 60.1,
    'pod_count': 127,
    'node_count': 3
}
```

## Used By
- Overview dashboard
- NodesPage
- KubernetesService (polling)

## Pattern
Service class with metrics API integration
