# cluster_state_manager.py - Brief Documentation

**Path**: `orchetrix/Utils/cluster_state_manager.py`
**Lines**: ~200
**Purpose**: Global cluster state tracking
**Pattern**: Singleton

## Key Features
- Track current cluster/namespace
- State persistence
- Change notifications via signals
- State history

## Main Methods
- `set_current_cluster(name)` - Set active cluster
- `set_current_namespace(name)` - Set active namespace
- `get_current_cluster()` - Get active cluster
- `get_current_namespace()` - Get active namespace

## Signals
- `cluster_changed` - Emitted when cluster changes
- `namespace_changed` - Emitted when namespace changes

## Used By
- All resource pages (namespace filtering)
- ClusterView
- Sidebar
