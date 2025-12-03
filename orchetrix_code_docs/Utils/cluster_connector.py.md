# cluster_connector.py - Brief Documentation

**Path**: `orchetrix/Utils/cluster_connector.py`
**Lines**: ~150
**Purpose**: Cluster connection management

## Key Features
- Connect to Kubernetes clusters
- Validate connections
- Connection pooling
- Context switching

## Main Methods
- `connect(context_name)` - Connect to cluster
- `disconnect()` - Disconnect from cluster
- `validate_connection()` - Test connection
- `get_current_context()` - Get active context

## Used By
- KubernetesService
- ClusterPage
- Sidebar (cluster selection)
