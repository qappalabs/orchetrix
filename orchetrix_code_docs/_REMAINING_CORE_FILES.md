# Remaining Core Files - Brief Documentation

This document provides brief overviews of remaining core architecture files that have not yet received full documentation.

---

## Services (4 remaining)

### events_service.py
**Purpose**: Manages Kubernetes events and cluster issues
**Lines**: ~200
**Key Features**:
- Fetches events for specific resources
- Aggregates cluster-wide issues
- Filters warning/error events
- Used by: DetailPageComponent Events tab, Overview dashboard

**Main Methods**:
- `get_events_for_resource(type, name, namespace)` - Get events for resource
- `get_cluster_issues(cluster_name)` - Get cluster-wide warnings/errors

---

### log_service.py
**Purpose**: Manages pod log streaming and retrieval
**Lines**: ~300
**Key Features**:
- Stream real-time pod logs
- Fetch historical logs
- Multi-container support
- Tail lines configuration

**Main Methods**:
- `get_pod_logs(pod_name, namespace, container, tail_lines)` - Get logs
- `start_log_stream(pod_name, namespace, container)` - Stream logs
- `stop_log_stream(pod_name, namespace, container)` - Stop streaming

**Used by**: TerminalPanel logs viewer, PodsPage log actions

---

### metrics_service.py
**Purpose**: Collects cluster and node metrics
**Lines**: ~250
**Key Features**:
- Cluster-wide CPU/memory metrics
- Node-level metrics
- Pod count aggregation
- Metrics API integration

**Main Methods**:
- `get_cluster_metrics(cluster_name)` - Aggregate metrics
- `get_node_metrics(node_name)` - Node-specific metrics

**Used by**: Overview dashboard, NodesPage

---

### resource_delete_service.py
**Purpose**: Handles resource deletion operations
**Lines**: ~150
**Key Features**:
- Single resource deletion
- Bulk deletion
- Progress tracking
- Error handling

**Main Methods**:
- `delete_resource(type, name, namespace)` - Delete single
- `delete_resources(type, items)` - Bulk delete

**Used by**: All resource pages bulk delete, resource_deleters.py

---

## Utils (13 remaining)

### port_forward_manager.py
**Purpose**: Manages Kubernetes port forwarding
**Lines**: ~400
**Key Features**:
- Forward pod ports to localhost
- Multiple concurrent forwards
- Auto-cleanup on close
- Status tracking

**Used by**: PodsPage, ServicesPage port forward actions

---

### cluster_state_manager.py
**Purpose**: Tracks global cluster state
**Lines**: ~200
**Key Features**:
- Current cluster tracking
- Namespace tracking
- State persistence
- Change notifications

**Pattern**: Singleton

---

### debounced_updater.py
**Purpose**: Debounces UI updates to prevent flicker
**Lines**: ~100
**Key Features**:
- Delays rapid updates
- Coalesces multiple updates
- Timer-based debouncing

**Used by**: BaseResourcePage auto-refresh

---

### data_formatters.py
**Purpose**: Format data for display
**Lines**: ~150
**Key Features**:
- Age formatting (2d, 3h, 5m)
- Memory formatting (2.5Gi, 1024Mi)
- Status formatting
- CPU formatting

**Used by**: All resource pages, unified_resource_loader

---

### error_handler.py
**Purpose**: Centralized error handling and formatting
**Lines**: ~200
**Key Features**:
- User-friendly error messages
- Connection error detection
- Timeout handling
- Error classification

**Used by**: All API calls, resource loaders

---

### performance_optimizer.py
**Purpose**: Runtime performance optimizations
**Lines**: ~150
**Key Features**:
- Memory optimization
- GC tuning
- Object pooling

---

### performance_config.py
**Purpose**: Performance configuration constants
**Lines**: ~50
**Key Features**:
- Batch sizes
- Timeout values
- Thread counts
- Cache sizes

---

### search_index.py
**Purpose**: Fast search indexing for resources
**Lines**: ~200
**Key Features**:
- Index resource names/labels
- Fast search queries
- Incremental updates

**Used by**: SearchResourceLoadWorker

---

### cluster_connector.py
**Purpose**: Manages cluster connections
**Lines**: ~150
**Key Features**:
- Connect to clusters
- Validate connections
- Connection pooling

---

### pin_storage.py
**Purpose**: Stores pinned resources
**Lines**: ~100
**Key Features**:
- Persist pinned items
- Load on startup
- JSON storage

**Used by**: Sidebar pinned resources

---

### helm_utils.py
**Purpose**: Helm chart utilities
**Lines**: ~300
**Key Features**:
- Parse Helm charts
- List releases
- Install/upgrade/delete
- Values.yaml handling

**Used by**: Helm-related pages

---

### port_forward_dialog.py
**Purpose**: Port forward configuration dialog
**Lines**: ~200
**Key Features**:
- Select pod port
- Choose local port
- Port validation
- Dialog UI

---

## UI (6 remaining)

### Icons.py
**Purpose**: Icon resource paths and loading
**Lines**: ~100
**Key Features**:
- Icon path resolution
- SVG icon loading
- Theme-aware icons

---

### LoadingSpinner.py
**Purpose**: Loading spinner widget
**Lines**: ~80
**Key Features**:
- Animated spinner
- Overlay mode
- Size variants

**Used by**: All pages during data loading

---

### SplashScreen.py
**Purpose**: Application startup splash screen
**Lines**: ~150
**Key Features**:
- Logo display
- Loading progress
- Fade in/out animation

**Used by**: main.py application startup

---

### TitleBar.py
**Purpose**: Custom window title bar
**Lines**: ~250
**Key Features**:
- Custom minimize/maximize/close
- Window dragging
- Theme styling

**Used by**: main.py main window

---

## Business_Logic (2 files)

### app_flow_business.py
**Purpose**: Application flow and navigation logic
**Lines**: ~300
**Key Features**:
- Page navigation
- State management
- Flow control

**Used by**: ClusterView, main.py

---

## Summary Statistics

### Documented Files (29 total):
- ✅ Main: main.py, HomePage.py
- ✅ WorkLoad Pages: 9 files
- ✅ Base_Components: 5 files
- ✅ UI: 5 files (ClusterView, Styles, DetailManager, DetailPageComponent, TerminalPanel)
- ✅ Utils: 4 files (kubernetes_client, thread_manager, unified_resource_loader, enhanced_worker)
- ✅ Services: 2 files (kubernetes_service, api_service)

### Remaining Files (~30 total):
- ⏳ Services: 4 files
- ⏳ Utils: 13 files
- ⏳ UI: 6 files
- ⏳ Business_Logic: 2 files
- ⏳ Pages/Config: 12 files
- ⏳ Pages/Network: 7 files
- ⏳ Pages/Storage: 4 files

---

## Priority Order for Remaining Documentation

1. **High Priority** (Core Infrastructure):
   - events_service.py, log_service.py, metrics_service.py
   - error_handler.py, data_formatters.py
   - Icons.py, LoadingSpinner.py

2. **Medium Priority** (Features):
   - port_forward_manager.py, helm_utils.py
   - cluster_state_manager.py, search_index.py
   - app_flow_business.py

3. **Low Priority** (Optional/Pages):
   - Pages/Config files (similar to WorkLoad pattern)
   - Pages/Network files (similar to WorkLoad pattern)
   - Pages/Storage files (similar to WorkLoad pattern)

---

**Note**: Most Pages files follow the same BaseResourcePage pattern documented in base_resource_page.py.md. They differ mainly in column definitions and resource-specific fields.
