# DetailPageComponent.py Documentation

## File Information
- **Path**: `orchetrix/UI/DetailPageComponent.py`
- **Purpose**: **DETAIL PANEL MANAGER** - Manages the slide-in detail panel showing resource information
- **Lines**: ~800+
- **Pattern**: Tabbed Interface + Animation + Signal-based Communication

## Overview
DetailPageComponent is the right-side detail panel that slides in when a user clicks on a resource (pod, deployment, service, etc.). It shows 4 tabs: Overview, Details, YAML, and Events. The panel supports resize, animation, and can handle special resources like Helm charts and custom resources.

---

## Key Features

1. ✅ **4 Tabbed Sections**: Overview, Details, YAML, Events
2. ✅ **Slide Animation**: Smooth slide-in/out from right side
3. ✅ **Resizable Panel**: Drag handle to resize width
4. ✅ **Special Resource Support**: Helm charts, releases, custom resources
5. ✅ **YAML Editing**: Edit and apply resource YAML
6. ✅ **Event Display**: Show Kubernetes events for resource

---

## Signals

```python
detail_closed_signal = pyqtSignal()                        # Detail panel closed
back_signal = pyqtSignal()                                  # Back button clicked
resource_updated_signal = pyqtSignal(str, str, str)         # Resource updated (type, name, ns)
refresh_main_page_signal = pyqtSignal(str, str, str)        # Refresh main page
```

---

## Constructor

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.resource_type = None
    self.resource_name = None
    self.resource_namespace = None
    self.kubernetes_client = get_kubernetes_client()
    
    self.setup_ui()
    self.setup_sections()
    self.setup_animations()
    self.hide()
```

---

## UI Structure

```
DetailPageComponent (fixed width: 600px)
├── Header (60px)
│   ├── Back/Close button (icon)
│   ├── Title label ("pods: nginx-abc123 (ns: default)")
│   └── Action button (Install/Upgrade for Helm)
├── Resize Handle (5px, left edge)
└── Content Area (QTabWidget)
    ├── Tab 1: Overview (DetailPageOverviewSection)
    ├── Tab 2: Details (DetailPageDetailsSection)
    ├── Tab 3: YAML (DetailPageYAMLSection)
    └── Tab 4: Events (DetailPageEventsSection)
```

---

## Main Methods

### `show_detail()` - **SHOW RESOURCE DETAILS**

```python
def show_detail(self, resource_type: str, resource_name: str, namespace: Optional[str] = None):
    """Show detail for specified resource"""
    self.resource_type = resource_type
    self.resource_name = resource_name
    self.resource_namespace = namespace
    
    # Update title
    title_text = f"{resource_type}: {resource_name}"
    if namespace:
        title_text += f" (ns: {namespace})"
    self.title_label.setText(title_text)
    
    # Setup sections
    self.clear_all_sections()
    self.set_resource_for_all_sections(resource_type, resource_name, namespace)
    
    # Handle special resources (charts, releases, CRs)
    self._handle_special_resource_data(resource_type)
    
    # Show with animation
    if not self.isVisible():
        self.show_with_animation()
    
    # Load current tab data
    QTimer.singleShot(300, self.load_current_tab_data)
```

**Usage**:
```python
# From PodsPage when user double-clicks a pod
detail_manager = get_detail_manager()
detail_manager.show_detail("pods", "nginx-abc123", "default")
```

---

### `show_with_animation()` - Slide In

```python
def show_with_animation(self):
    """Slide in from right with animation"""
    # Calculate start and end positions
    parent_rect = self.parent().geometry()
    start_x = parent_rect.width()
    end_x = parent_rect.width() - self.width()
    
    # Setup animation
    self.slide_animation.setStartValue(QRect(start_x, 0, self.width(), parent_rect.height()))
    self.slide_animation.setEndValue(QRect(end_x, 0, self.width(), parent_rect.height()))
    
    # Show and animate
    self.show()
    self.animation_group.start()
```

---

### `close_detail()` - Slide Out

```python
def close_detail(self):
    """Close detail panel with animation"""
    # Slide out to right
    parent_rect = self.parent().geometry()
    self.slide_animation.setStartValue(self.geometry())
    self.slide_animation.setEndValue(QRect(parent_rect.width(), 0, self.width(), parent_rect.height()))
    
    # Animate and hide
    self.animation_group.start()
    self.animation_group.finished.connect(self.hide)
    
    # Emit signal
    self.detail_closed_signal.emit()
```

---

## Section Components

### 1. DetailPageOverviewSection
- Shows key information (status, age, labels, annotations)
- Resource-specific widgets (pod containers, deployment replicas, etc.)
- Quick actions

### 2. DetailPageDetailsSection
- Detailed field-by-field breakdown
- Expandable sections (spec, status, metadata)
- Copy-to-clipboard buttons

### 3. DetailPageYAMLSection
- Syntax-highlighted YAML editor
- Edit and Apply functionality
- Validates YAML before applying

### 4. DetailPageEventsSection
- Shows Kubernetes events for the resource
- Filtered by resource name
- Color-coded by event type (Normal, Warning)

---

## Special Resource Handling

### Helm Charts

```python
def _handle_special_resource_data(self, resource_type: str):
    if resource_type.lower() in ["chart", "helmchart"]:
        raw_data = self.chart_raw_data
        # Pass to all sections
        for section in sections:
            section.set_raw_data(raw_data)
```

**Shows**: Chart metadata, values.yaml, install button

---

### Custom Resources

```python
def _handle_custom_resource_instance(self, cr_metadata: dict):
    """Fetch custom resource from API"""
    api_group = cr_metadata.get('api_group')
    api_version = cr_metadata.get('api_version')
    plural = cr_metadata.get('plural')
    
    # Use CustomObjectsApi
    cr_data = custom_objects_api.get_namespaced_custom_object(
        group=api_group,
        version=api_version,
        namespace=self.resource_namespace,
        plural=plural,
        name=self.resource_name
    )
    
    # Pass to sections
    for section in sections:
        section.set_raw_data(cr_data)
```

---

## Resize Functionality

```python
def create_resize_handle(self):
    """Create resize handle for panel resizing"""
    self.resize_handle = QFrame(self)
    self.resize_handle.setFixedWidth(5)
    self.resize_handle.setCursor(Qt.CursorShape.SizeHorCursor)
    
    # Connect mouse events
    self.resize_handle.mousePressEvent = self.resize_handle_mousePressEvent
    self.resize_handle.mouseMoveEvent = self.resize_handle_mouseMoveEvent
    self.resize_handle.mouseReleaseEvent = self.resize_handle_mouseReleaseEvent
```

**User can drag left edge to resize panel width** (400px - 800px)

---

## Tab Management

```python
def handle_tab_changed(self, index):
    """Load data when tab is switched"""
    if index == 0:
        self.overview_section.load_data()
    elif index == 1:
        self.details_section.load_data()
    elif index == 2:
        self.yaml_section.load_data()
    elif index == 3:
        self.events_section.load_data()
```

**Lazy loading**: Only loads data when tab becomes visible

---

## Usage Flow

```
User double-clicks pod "nginx-abc123"
   ↓
PodsPage.handle_row_double_clicked()
   ↓
detail_manager.show_detail("pods", "nginx-abc123", "default")
   ↓
DetailPageComponent.show_detail()
   ↓
Panel slides in from right (animation)
   ↓
Overview tab loads pod data
   ↓
User switches to YAML tab
   ↓
YAML section loads and displays pod YAML
   ↓
User edits YAML and clicks Apply
   ↓
YAML section applies changes to cluster
   ↓
resource_updated_signal emitted
   ↓
PodsPage refreshes to show updated pod
```

---

## Key Dependencies

- UI/detail_sections/detailpage_overviewsection.py
- UI/detail_sections/detailpage_detailsection.py
- UI/detail_sections/detailpage_yamlsection.py
- UI/detail_sections/detailpage_eventssection.py
- Utils/kubernetes_client.py
- UI/Styles.py

---

## Total Lines**: ~800+ lines managing tabbed detail panel with animations and special resource support.
