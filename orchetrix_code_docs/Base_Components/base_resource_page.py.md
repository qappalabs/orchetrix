# base_resource_page.py Documentation

## File Information
- **Path**: `orchetrix/Base_Components/base_resource_page.py`
- **Purpose**: **CORE FOUNDATION CLASS** - Base class for all Kubernetes resource pages with optimized performance, virtual scrolling, and unified resource loading

## Overview
BaseResourcePage is the **most important base class** in Orchetrix. Every resource page (Pods, Deployments, Services, ConfigMaps, etc.) extends this class. It provides:
- Unified resource loading with pagination
- Virtual scrolling for large datasets (1000+ resources)
- Search and namespace filtering
- Bulk delete operations
- Loading states and progress indicators
- Thread management and cleanup
- Performance optimizations for large clusters

---

## Key Constants

```python
BATCH_SIZE = 100  # Items loaded per batch
SCROLL_DEBOUNCE_MS = 150  # Scroll event debounce time
SEARCH_DEBOUNCE_MS = 500  # Search input debounce time
MAX_ITEMS_IN_MEMORY = 2000  # Memory limit for cached items
LARGE_DATASET_THRESHOLD = 200  # When to activate large dataset optimizations
MAX_TABLE_ROWS_BEFORE_VIRTUAL = 100  # When to enable virtual scrolling
```

---

## Class: BaseResourcePage (extends BaseTablePage)

### Signals
```python
load_more_complete = pyqtSignal()  # Emitted when more data loaded
all_items_loaded_signal = pyqtSignal()  # Emitted when all data loaded
```

### Constructor: `__init__()`

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.resource_type = None  # e.g., "pods", "deployments"
    self.resources = []  # List of all loaded resources
    self.namespace_filter = "default"  # Current namespace filter
    self.search_bar = None  # Search input widget
    self.namespace_combo = None  # Namespace dropdown
    
    self.loading_thread = None  # Resource loading thread
    self.delete_thread = None  # Single resource delete thread
    self.batch_delete_thread = None  # Bulk delete thread
    
    # Performance optimizations
    self.is_loading_initial = False
    self.is_loading_more = False
    self.all_data_loaded = False
    self.current_continue_token = None  # Pagination token
    self.items_per_page = 200
    self.selected_items = set()
    self.reload_on_show = True
    self._large_dataset_mode = False
    self._total_item_count = 0
    self._loaded_item_count = 0
    self._enable_virtual_scrolling = False
    self._progressive_loading = True
    
    # Thread safety
    import threading
    self._data_lock = threading.RLock()
    self._loading_lock = threading.Lock()
    
    # Virtual scrolling
    self._visible_start = 0
    self._visible_end = 100
    self._render_buffer = 20  # Extra rows for smooth scrolling
    self._remaining_resources = []  # Lazy loading queue
    
    # Debouncing
    from Utils.debounced_updater import get_debounced_updater
    self._debounced_updater = get_debounced_updater()
    
    self.kube_client = get_kubernetes_client()
    self._loading_overlay = None
    self._initial_load_done = False
```

**Key Attributes**:
- **resource_type**: Must be set by subclass (e.g., "pods", "deployments")
- **resources**: In-memory cache of all loaded resources
- **namespace_filter**: Current namespace (default, kube-system, all, etc.)
- **Pagination**: `current_continue_token` tracks where to load next batch
- **Virtual Scrolling**: Only renders visible rows for performance
- **Thread Safety**: RLock allows recursive locking, Lock for loading state

---

## Key Methods

### Lifecycle: `showEvent()`

```python
def showEvent(self, event):
    """Override showEvent to automatically load data when page becomes visible"""
    super().showEvent(event)
    
    # Load immediately for better performance
    self._handle_normal_show_event()
```

**Purpose**: Auto-loads data when page becomes visible

**Flow**:
1. Check if app is still starting (< 6 seconds since launch)
2. If starting: Defer load to avoid splash screen lag
3. If ready: Load immediately

### Namespace Loading: `_load_namespaces_async()`

```python
def _load_namespaces_async(self):
    """Load namespaces asynchronously"""
    # Sets namespace_combo to "Loading namespaces..."
    # Starts background worker to fetch namespaces
    # Populates dropdown when complete
```

**Flow**:
1. Show "Loading namespaces..." in dropdown
2. Start background thread to fetch from Kubernetes API
3. Populate dropdown with namespaces
4. Add "All Namespaces" option
5. Set default to "default" namespace

---

### Data Loading: `load_data()`

```python
def load_data(self, namespace=None, show_loading=True):
    """Load resource data with pagination support"""
    if self.is_loading_initial or self.is_loading_more:
        return  # Prevent concurrent loads
    
    self.is_loading_initial = True
    self.all_data_loaded = False
    self.current_continue_token = None
    
    # Show loading overlay
    if show_loading:
        self._show_loading_overlay()
    
    # Start resource loader thread
    from Utils.unified_resource_loader import get_unified_resource_loader
    loader = get_unified_resource_loader()
    
    # Connect signals
    loader.data_loaded.connect(self._on_data_loaded)
    loader.error_occurred.connect(self._on_load_error)
    
    # Start loading
    loader.load_resources(
        resource_type=self.resource_type,
        namespace=namespace or self.namespace_filter,
        limit=self.items_per_page
    )
```

**Loading Flow**:
```
1. User opens page → showEvent()
2. showEvent() → load_data()
3. load_data() → Shows loading overlay
4. load_data() → Starts UnifiedResourceLoader thread
5. Loader fetches from Kubernetes API (with pagination)
6. Loader emits data_loaded signal
7. _on_data_loaded() → Processes resources
8. _on_data_loaded() → Calls populate_table()
9. populate_table() → Renders visible rows
10. Hides loading overlay
```

---

### Data Processing: `_on_data_loaded()`

```python
def _on_data_loaded(self, result: LoadResult):
    """Handle loaded data from unified resource loader"""
    try:
        # Extract data
        resources = result.items
        continue_token = result.continue_token
        total_count = result.total_count
        
        # Store resources
        with self._data_lock:
            if self.is_loading_initial:
                self.resources = resources
            else:
                self.resources.extend(resources)
            
            self._loaded_item_count = len(self.resources)
            self._total_item_count = total_count
            self.current_continue_token = continue_token
            
            # Check if all data loaded
            if not continue_token:
                self.all_data_loaded = True
        
        # Populate table
        self.populate_table()
        
        # Enable large dataset mode if needed
        if self._loaded_item_count > LARGE_DATASET_THRESHOLD:
            self._enable_large_dataset_optimizations()
        
    finally:
        self.is_loading_initial = False
        self.is_loading_more = False
        self._hide_loading_overlay()
```

**Key Operations**:
1. **Thread-safe storage**: Uses RLock to prevent race conditions
2. **Pagination tracking**: Stores continue_token for next batch
3. **Total count**: Tracks total vs loaded for progress
4. **Large dataset mode**: Enables optimizations for 200+ items
5. **Table population**: Renders data in UI

---

### Table Population: `populate_table()`

```python
def populate_table(self):
    """Populate table with resources - ABSTRACT METHOD"""
    # Must be implemented by subclass
    # Each resource page implements its own row population logic
    pass
```

**Subclass Implementation Example** (PodsPage):
```python
def populate_table(self):
    self.clear_table()
    
    # Filter resources by search
    filtered = self._filter_resources(self.resources)
    
    # Determine visible range for virtual scrolling
    if len(filtered) > MAX_TABLE_ROWS_BEFORE_VIRTUAL:
        visible_resources = filtered[self._visible_start:self._visible_end]
    else:
        visible_resources = filtered
    
    # Populate visible rows
    for row, resource in enumerate(visible_resources):
        self.populate_resource_row(row, resource)
```

---

### Virtual Scrolling: `_enable_large_dataset_optimizations()`

```python
def _enable_large_dataset_optimizations(self):
    """Enable optimizations for large datasets"""
    self._large_dataset_mode = True
    
    # Enable virtual scrolling
    if len(self.resources) > MAX_TABLE_ROWS_BEFORE_VIRTUAL:
        self._enable_virtual_scrolling = True
        self._setup_virtual_scrolling()
    
    # Reduce rendering frequency
    self._debounced_updater.set_delay('scroll', SCROLL_DEBOUNCE_MS)
    self._debounced_updater.set_delay('search', SEARCH_DEBOUNCE_MS)
```

**Optimizations**:
- **Virtual Scrolling**: Only renders visible rows (huge performance gain)
- **Debouncing**: Reduces scroll/search event processing
- **Batch Operations**: Groups updates for better performance

---

### Bulk Delete: `delete_selected_resources()`

```python
def delete_selected_resources(self):
    """Delete selected resources in bulk"""
    selected = self.get_selected_resources()
    if not selected:
        return
    
    # Confirm deletion
    reply = QMessageBox.question(
        self, "Confirm Deletion",
        f"Delete {len(selected)} resources?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    
    if reply != QMessageBox.StandardButton.Yes:
        return
    
    # Start bulk delete thread
    self.batch_delete_thread = BatchResourceDeleterThread(
        resource_type=self.resource_type,
        resources=selected
    )
    
    self.batch_delete_thread.progress_updated.connect(self._on_delete_progress)
    self.batch_delete_thread.delete_complete.connect(self._on_delete_complete)
    self.batch_delete_thread.error_occurred.connect(self._on_delete_error)
    
    self.batch_delete_thread.start()
```

**Bulk Delete Flow**:
1. Get selected resources from checkboxes
2. Show confirmation dialog
3. Start BatchResourceDeleterThread
4. Thread deletes resources in parallel
5. Emits progress updates (10%, 50%, 100%)
6. Shows progress dialog with cancel button
7. Reloads data when complete

---

## Performance Features

### 1. Virtual Scrolling
Only renders visible rows instead of all 1000+ rows:
```python
# Without virtual scrolling: Render all 1000 pods (SLOW)
for i in range(1000):
    populate_resource_row(i, pods[i])

# With virtual scrolling: Render only 100 visible pods (FAST)
visible_start = 0
visible_end = 100
for i in range(visible_start, visible_end):
    populate_resource_row(i - visible_start, pods[i])
```

### 2. Pagination
Loads data in chunks instead of all at once:
```python
# Load first 200 items
loader.load_resources(limit=200)
# Returns: items[0:200] + continue_token

# Load next 200 items
loader.load_resources(limit=200, continue_token=token)
# Returns: items[200:400] + new_token
```

### 3. Debouncing
Prevents excessive updates:
```python
# User types "nginx" → Without debouncing: 5 searches ("n", "ng", "ngi", "ngin", "nginx")
# With debouncing: 1 search after 500ms delay
```

### 4. Thread Safety
Prevents race conditions:
```python
with self._data_lock:
    self.resources.extend(new_resources)  # Thread-safe append
```

---

## Subclass Requirements

**Every resource page MUST**:
1. Set `self.resource_type` in `__init__()`
2. Call `self.setup_page_ui()` in `__init__()`
3. Implement `populate_resource_row(row, resource)`
4. Define table headers in `setup_page_ui()`

**Example Subclass** (simplified):
```python
class PodsPage(BaseResourcePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_type = "pods"  # Required
        self.setup_page_ui()  # Required
    
    def setup_page_ui(self):
        headers = ["Name", "Namespace", "Status", "Age"]
        sortable_columns = {0, 1, 2, 3}
        super().setup_ui("Pods", headers, sortable_columns)
    
    def populate_resource_row(self, row, resource):
        # Required implementation
        self.table.setItem(row, 0, QTableWidgetItem(resource["name"]))
        self.table.setItem(row, 1, QTableWidgetItem(resource["namespace"]))
        # ... more columns
```

---

## Key Features Summary

1. ✅ **Unified Resource Loading**: All resources use same loading mechanism
2. ✅ **Virtual Scrolling**: Handles 1000+ items without lag
3. ✅ **Pagination**: Loads data in chunks for fast initial load
4. ✅ **Search & Filter**: Real-time search with debouncing
5. ✅ **Bulk Operations**: Delete multiple resources at once
6. ✅ **Thread Safety**: Prevents race conditions
7. ✅ **Loading States**: Shows spinners and progress
8. ✅ **Error Handling**: Graceful error recovery
9. ✅ **Memory Management**: Limits cached items
10. ✅ **Performance Optimizations**: Large dataset mode

---

## Dependencies
- **BaseTablePage**: Parent class with table setup
- **UnifiedResourceLoader**: Async resource loading
- **ResourceDeleterThread**: Single resource deletion
- **BatchResourceDeleterThread**: Bulk deletion
- **VirtualScrollTable**: Virtual scrolling implementation
- **DebouncedUpdater**: Event debouncing
- **ThreadManager**: Thread lifecycle management
- **KubernetesClient**: API access

---

## Why This Is Critical

BaseResourcePage is used by **50+ resource pages**:
- Pages/WorkLoad/*: Pods, Deployments, StatefulSets, etc.
- Pages/Config/*: ConfigMaps, Secrets, etc.
- Pages/Network/*: Services, Ingresses, etc.
- Pages/Storage/*: PVs, PVCs, etc.

Any bug or performance issue here affects the **entire application**.
