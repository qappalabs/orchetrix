# DetailManager.py Documentation

## File Information
- **Path**: `orchetrix/UI/DetailManager.py`
- **Purpose**: Manages resource detail panels that slide in from the right side

## Overview
DetailManager controls the DetailPageComponent that shows detailed information about selected Kubernetes resources. When you click a pod, deployment, service, etc., a panel slides in from the right showing YAML, events, logs, and more.

---

## Class: DetailManager (extends QObject)

### Signals
```python
resource_updated = pyqtSignal(str, str, str)
# Parameters: (resource_type, resource_name, namespace)
# Emitted when resource is updated via YAML edit

refresh_main_page = pyqtSignal(str, str, str)
# Parameters: (resource_type, resource_name, namespace)
# Emitted to tell main page to reload after update
```

### Constructor
```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.parent_window = parent  # ClusterView instance
    
    self._detail_page = None  # Lazy-loaded DetailPageComponent
    self._current_resource = {
        'type': None,
        'name': None,
        'namespace': None
    }
    
    self._cached_height = None  # Cache for performance
    self._is_initialized = False
```

**Lazy Loading**: Detail page only created when first needed

---

## Key Methods

### `_ensure_detail_page()`
```python
def _ensure_detail_page(self) -> DetailPageComponent:
    """Lazy initialization of detail page"""
    if self._detail_page is None:
        self._detail_page = DetailPageComponent(self.parent_window)
        
        # Connect signals
        self._detail_page.resource_updated_signal.connect(self._handle_resource_updated)
        self._detail_page.refresh_main_page_signal.connect(self._handle_refresh_main_page)
        
        self._init_sizing()
        self._is_initialized = True
    
    return self._detail_page
```

**First Call**: Creates DetailPageComponent
**Subsequent Calls**: Returns existing instance

---

### `show_detail()` - MAIN METHOD

```python
def show_detail(self, resource_type: str, resource_name: str,
                namespace: Optional[str] = None, 
                raw_data: Optional[Dict[str, Any]] = None) -> None:
    """Show detail view for the specified resource"""
```

**Flow**:
1. **Convert Plural to Singular**
2. **Ensure Detail Page Exists**
3. **Check if Same Resource** (avoid reload)
4. **Update Current Resource Tracking**
5. **Clear Previous Raw Data**
6. **Set New Raw Data** (if provided)
7. **Load Resource Details**
8. **Show and Position Panel**

#### Step 1: Plural to Singular Conversion

```python
plural_to_singular_mapping = {
    'pods': 'pod',
    'deployments': 'deployment',
    'services': 'service',
    'configmaps': 'configmap',
    'secrets': 'secret',
    'persistentvolumeclaims': 'persistentvolumeclaim',
    'persistentvolumes': 'persistentvolume',
    'ingresses': 'ingress',
    'daemonsets': 'daemonset',
    'statefulsets': 'statefulset',
    'replicasets': 'replicaset',
    'jobs': 'job',
    'cronjobs': 'cronjob',
    'nodes': 'node',
    'namespaces': 'namespace',
    'events': 'event',
    'endpoints': 'endpoint',
    'serviceaccounts': 'serviceaccount',
    'roles': 'role',
    'rolebindings': 'rolebinding',
    'clusterroles': 'clusterrole',
    'clusterrolebindings': 'clusterrolebinding',
    # ... 30+ more mappings
}

resource_type_singular = plural_to_singular_mapping.get(
    resource_type.lower(), 
    resource_type.rstrip('s') if resource_type.endswith('s') else resource_type
)
```

**Why**: Kubernetes API uses singular names (pod, not pods)

#### Step 2-3: Check Same Resource

```python
if self._is_same_resource(resource_type_singular, resource_name, namespace) and detail_page.isVisible():
    self.update_detail_position()  # Just reposition
    return  # Don't reload
```

**Optimization**: If already viewing same resource, don't reload data

#### Step 4: Update Tracking

```python
self._current_resource.update({
    'type': resource_type_singular,
    'name': resource_name,
    'namespace': namespace
})
```

#### Step 5: Clear Previous Data

```python
# Clear all raw data attributes
if hasattr(detail_page, 'event_raw_data'):
    detail_page.event_raw_data = None
if hasattr(detail_page, 'chart_raw_data'):
    detail_page.chart_raw_data = None
if hasattr(detail_page, 'release_raw_data'):
    detail_page.release_raw_data = None
if hasattr(detail_page, 'resource_raw_data'):
    detail_page.resource_raw_data = None
```

**Why**: Prevent data from previous resource interfering

#### Step 6-8: Load and Show

```python
# Load resource details
detail_page.load_resource_details(resource_type_singular, resource_name, namespace)

# Update sizing
self._update_cached_height()

# Position and show
self.update_detail_position()
detail_page.show()
detail_page.raise_()
```

---

## Signal Handlers

### `_handle_resource_updated()`
```python
def _handle_resource_updated(self, resource_type: str, resource_name: str, namespace: str):
    """Handle resource update from detail page"""
    logging.info(f"Resource updated: {resource_type}/{resource_name}")
    self.resource_updated.emit(resource_type, resource_name, namespace)
```

**Triggered By**: User editing YAML and clicking "Apply"

### `_handle_refresh_main_page()`
```python
def _handle_refresh_main_page(self, resource_type: str, resource_name: str, namespace: str):
    """Handle request to refresh main page after YAML update"""
    logging.info(f"Requesting main page refresh for {resource_type}/{resource_name}")
    self.refresh_main_page.emit(resource_type, resource_name, namespace)
```

**Result**: Main resource page reloads to show updated data

---

## Helper Methods

### `_init_sizing()`
```python
def _init_sizing(self) -> None:
    """Pre-calculate sizes for performance"""
    if self.parent_window:
        self._cached_height = self.parent_window.height()
        if self._detail_page:
            self._detail_page.setFixedHeight(self._cached_height)
```

### `_update_cached_height()`
```python
def _update_cached_height(self) -> None:
    """Update cached height if window resized"""
    if self.parent_window:
        new_height = self.parent_window.height()
        if new_height != self._cached_height:
            self._cached_height = new_height
            if self._detail_page:
                self._detail_page.setFixedHeight(new_height)
```

**Performance**: Caching prevents recalculating height every frame

### `_is_same_resource()`
```python
def _is_same_resource(self, resource_type: str, resource_name: str, namespace: Optional[str]) -> bool:
    """Check if we're already viewing this resource"""
    return (
        self._current_resource['type'] == resource_type and
        self._current_resource['name'] == resource_name and
        self._current_resource['namespace'] == namespace
    )
```

### `update_detail_position()`
```python
def update_detail_position(self) -> None:
    """Position detail panel on right side"""
    if not self._detail_page or not self.parent_window:
        return
    
    # Position on right edge
    parent_width = self.parent_window.width()
    detail_width = 600  # Fixed width
    
    self._detail_page.setGeometry(
        parent_width - detail_width,  # X (right edge)
        0,                            # Y (top)
        detail_width,                 # Width
        self._cached_height           # Height
    )
```

---

## Usage Flow

### From Resource Page (e.g., PodsPage)

```python
# In PodsPage.handle_row_click()
def handle_row_click(self, row, column):
    # Get resource info
    resource_name = self.table.item(row, 1).text()
    namespace = self.table.item(row, 2).text()
    
    # Find ClusterView
    parent = self.parent()
    while parent and not hasattr(parent, 'detail_manager'):
        parent = parent.parent()
    
    # Show detail
    if parent and hasattr(parent, 'detail_manager'):
        parent.detail_manager.show_detail("pod", resource_name, namespace)
```

**Result**:
```
1. User clicks pod row
2. PodsPage finds ClusterView
3. ClusterView.detail_manager.show_detail() called
4. DetailManager creates/shows DetailPageComponent
5. Panel slides in from right
6. Shows pod YAML, events, logs, etc.
```

---

## Detail Panel Structure

```
┌─────────────────────────────────────────────────────┐
│ ClusterView                                         │
│ ┌────────────────────────┬──────────────────────┐  │
│ │ PodsPage               │ DetailPageComponent  │  │
│ │ ┌────────────────────┐ │ ┌─────────────────┐  │  │
│ │ │ Pod List           │ │ │ Pod: nginx      │  │  │
│ │ │ ┌──────┬─────────┐ │ │ │ ─────────────── │  │  │
│ │ │ │ Name │ Status  │ │ │ │                 │  │  │
│ │ │ ├──────┼─────────┤ │ │ │ Overview ▾      │  │  │
│ │ │ │nginx │ Running │←┼─┼─│ - Name: nginx   │  │  │
│ │ │ │      │         │ │ │ │ - Namespace: ..│  │  │
│ │ │ └──────┴─────────┘ │ │ │                 │  │  │
│ │ └────────────────────┘ │ │ YAML ▾          │  │  │
│ │                        │ │ [Edit] [Apply]  │  │  │
│ │                        │ │                 │  │  │
│ │                        │ │ Events ▾        │  │  │
│ │                        │ │ Logs ▾          │  │  │
│ │                        │ │                 │  │  │
│ │                        │ │ [Close]         │  │  │
│ │                        │ └─────────────────┘  │  │
│ └────────────────────────┴──────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Key Features

1. ✅ **Lazy Loading**: Detail page created only when first needed
2. ✅ **Caching**: Avoids reloading same resource
3. ✅ **Height Caching**: Performance optimization
4. ✅ **Signal Propagation**: Updates flow back to main page
5. ✅ **Plural→Singular**: Automatic conversion for 30+ resource types
6. ✅ **Clean State**: Clears previous data before loading new
7. ✅ **Positioning**: Automatic right-side positioning
8. ✅ **YAML Editing**: Full edit and apply workflow

---

## Dependencies
- DetailPageComponent (the actual detail panel)
- PyQt6.QtCore (QObject, pyqtSignal)
- logging (error tracking)

## Used By
- ClusterView (parent container)
- All resource pages (Pods, Deployments, Services, etc.)
