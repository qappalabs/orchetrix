# StatefulSetsPage.py Documentation

## File Information
- **Path**: `orchetrix/Pages/WorkLoad/StatefulSetsPage.py`
- **Lines**: 213
- **Purpose**: Kubernetes StatefulSets management page with pod status tracking

## Overview
StatefulSetsPage displays and manages Kubernetes StatefulSets. StatefulSets are used for stateful applications that require stable network identities and persistent storage (e.g., databases, caches). This page extends BaseResourcePage and shows current/desired pod counts, replica configuration, and age with detail page integration.

---

## Imports

### PyQt6 Framework
```python
from PyQt6.QtWidgets import QHeaderView, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
```

### Internal Components
```python
from Base_Components.base_components import SortableTableWidgetItem
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
```

---

## Class: StatefulSetsPage

### Constructor: `__init__()`

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.resource_type = "statefulsets"
    self.setup_page_ui()
```

**Initialization**:
- Sets resource_type to "statefulsets" for Kubernetes API calls
- Calls setup_page_ui() to create table and UI components

---

### Method: `setup_page_ui()`

```python
def setup_page_ui(self):
    headers = ["", "Name", "Namespace", "Pods", "Replicas", "Age", ""]
    sortable_columns = {1, 2, 3, 4, 5}
    
    layout = super().setup_ui("Stateful Sets", headers, sortable_columns)
    
    self.table.setStyleSheet(AppStyles.TABLE_STYLE)
    self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
    
    self.configure_columns()
```

**UI Setup**:
- **7 columns**: Checkbox, Name, Namespace, Pods, Replicas, Age, Actions
- **Sortable**: All columns except checkbox and actions
- **Styles**: Applied from AppStyles for consistency
- **Page title**: "Stateful Sets"

---

### Method: `configure_columns()`

```python
def configure_columns(self):
    column_specs = [
        (0, 40, "fixed"),        # Checkbox
        (1, 200, "interactive"), # Name
        (2, 100, "interactive"), # Namespace
        (3, 80, "interactive"),  # Pods
        (4, 60, "interactive"),  # Replicas
        (5, 50, "stretch"),      # Age - stretches to fill space
        (6, 40, "fixed")         # Actions
    ]
    
    for col_index, default_width, resize_type in column_specs:
        if col_index < self.table.columnCount():
            if resize_type == "fixed":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col_index, default_width)
            elif resize_type == "interactive":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(col_index, default_width)
            elif resize_type == "stretch":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
                self.table.setColumnWidth(col_index, default_width)
    
    QTimer.singleShot(100, self._ensure_full_width_utilization)
```

**Column Configuration**:
- **Fixed**: Checkbox (40px), Actions (40px) - cannot be resized
- **Interactive**: Name (200px), Namespace (100px), Pods (80px), Replicas (60px) - user can resize
- **Stretch**: Age (50px base) - fills remaining space

---

### Method: `populate_resource_row()`

```python
def populate_resource_row(self, row, resource):
    self.table.setRowHeight(row, 40)
    
    resource_name = resource["name"]
    checkbox_container = self._create_checkbox_container(row, resource_name)
    checkbox_container.setStyleSheet(AppStyles.CHECKBOX_STYLE)
    self.table.setCellWidget(row, 0, checkbox_container)
    
    raw_data = resource.get("raw_data", {})
```

**Data Extraction**:

#### Pods Status
```python
pods_str = "0/0"
if raw_data:
    status = raw_data.get("status", {})
    current_replicas = status.get("currentReplicas", 0)
    replicas = status.get("replicas", 0)
    pods_str = f"{current_replicas}/{replicas}"
```

**Pods Display Format**:
- Shows `current/desired` pod count
- Example: "3/3" means all 3 pods are ready
- Example: "2/3" means only 2 of 3 pods are ready
- For StatefulSets: `currentReplicas` vs `replicas` (not `availableReplicas` like Deployments)

**Why StatefulSets use currentReplicas**:
- StatefulSets create pods sequentially (pod-0, pod-1, pod-2...)
- `currentReplicas` = pods that have been created (may not be ready)
- `readyReplicas` = pods that are ready (better metric, but not shown here)

---

#### Replicas Count
```python
replicas_str = "0"
if raw_data:
    spec = raw_data.get("spec", {})
    replicas_str = str(spec.get("replicas", 0))
```

**Replicas Column**:
- Shows desired replica count from StatefulSet spec
- This is what user configured
- Example: "3" means user wants 3 replicas

---

#### Column Data Assembly
```python
columns = [
    resource["name"],
    resource["namespace"],
    pods_str,
    replicas_str,
    resource["age"]
]
```

---

#### Sortable Column Items

**Pods Column Sorting**:
```python
if col == 2:  # Pods column
    try:
        current, desired = value.split("/")
        pods_value = float(current) / float(desired) if float(desired) > 0 else 0
    except (ValueError, ZeroDivisionError):
        pods_value = 0
    item = SortableTableWidgetItem(value, pods_value)
```

**Sorting Logic**:
- Converts "2/3" to 0.666 (66.6%)
- Converts "3/3" to 1.0 (100%)
- Sorts by readiness percentage
- Sorts "3/3" (100%) above "2/3" (66%)

---

**Replicas Column Sorting**:
```python
elif col == 3:  # Replicas column
    try:
        replicas_value = float(value)
    except ValueError:
        replicas_value = 0
    item = SortableTableWidgetItem(value, replicas_value)
```
Sorts numerically (3 > 2 > 1)

---

**Age Column Sorting**:
```python
elif col == 4:  # Age column
    try:
        if 'd' in value:
            age_value = int(value.replace('d', '')) * 1440  # days to minutes
        elif 'h' in value:
            age_value = int(value.replace('h', '')) * 60  # hours to minutes
        elif 'm' in value:
            age_value = int(value.replace('m', ''))  # minutes
        else:
            age_value = 0
    except ValueError:
        age_value = 0
    item = SortableTableWidgetItem(value, age_value)
```

**Age Conversion**:
- "5d" → 7200 minutes
- "12h" → 720 minutes
- "30m" → 30 minutes
- Allows proper chronological sorting

---

#### Cell Formatting
```python
# Set text alignment
if col in [1, 2, 3, 4]:  # Pods, Replicas, Age
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
else:
    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

# Make cells non-editable
item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

# Set text color
item.setForeground(QColor(AppColors.TEXT_TABLE))

self.table.setItem(row, cell_col, item)
```

**Formatting Rules**:
- **Center-aligned**: Pods, Replicas, Age (numeric/status data)
- **Left-aligned**: Name, Namespace (text data)
- **Non-editable**: All cells (no inline editing)
- **Default color**: AppColors.TEXT_TABLE

---

#### Action Button
```python
action_button = self._create_action_button(row, resource_name, resource["namespace"])
action_button.setStyleSheet(AppStyles.ACTION_BUTTON_STYLE)
action_container = self._create_action_container(row, action_button)
action_container.setStyleSheet(AppStyles.ACTION_CONTAINER_STYLE)
self.table.setCellWidget(row, len(columns) + 1, action_container)
```

**Action Menu**:
- Vertical three-dot menu (⋮)
- Options: Edit, Delete
- Placed in last column (column 6)

---

### Method: `handle_row_click()`

```python
def handle_row_click(self, row, column):
    if column != self.table.columnCount() - 1:  # Skip action column
        self.table.selectRow(row)
        
        resource_name = None
        namespace = None
        
        if self.table.item(row, 1) is not None:
            resource_name = self.table.item(row, 1).text()
        
        if self.table.item(row, 2) is not None:
            namespace = self.table.item(row, 2).text()
        
        if resource_name:
            parent = self.parent()
            while parent and not hasattr(parent, 'detail_manager'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'detail_manager'):
                resource_type = self.resource_type
                if resource_type.endswith('s'):
                    resource_type = resource_type[:-1]
                
                parent.detail_manager.show_detail(resource_type, resource_name, namespace)
```

**Click Behavior**:
1. Click any column except actions menu
2. Select entire row
3. Extract StatefulSet name and namespace
4. Find ClusterView by walking parent tree
5. Convert "statefulsets" → "statefulset" (singular)
6. Show detail page with full StatefulSet info, YAML, and related pods

---

## Key Features

1. **Pod Status Tracking**: Shows current/desired pod count (e.g., 2/3)
2. **Replica Configuration**: Displays desired replica count
3. **Age Display**: Human-readable format (5d, 12h, 30m)
4. **Sortable Columns**: Sort by name, namespace, pods, replicas, age
5. **Detail View**: Click row to see full StatefulSet details
6. **Action Menu**: Edit and Delete options
7. **Bulk Selection**: Checkbox for multi-delete
8. **Responsive Layout**: Age column stretches to fill space

## Action Menu Items
- **Edit**: Edit StatefulSet YAML configuration
- **Delete**: Delete the StatefulSet (WARNING: deletes all pods)

## StatefulSet Characteristics

### What are StatefulSets?
StatefulSets are used for stateful applications that require:
- **Stable network identities**: Each pod has a persistent hostname (e.g., mysql-0, mysql-1, mysql-2)
- **Ordered deployment**: Pods created sequentially (pod-0 first, then pod-1, etc.)
- **Persistent storage**: Each pod can have its own persistent volume

### Common Use Cases
- **Databases**: MySQL, PostgreSQL, MongoDB
- **Caching**: Redis, Memcached with persistence
- **Distributed systems**: Kafka, ZooKeeper, Cassandra
- **Stateful applications**: Anything requiring stable identity or storage

### Difference from Deployments
| Feature | Deployment | StatefulSet |
|---------|-----------|-------------|
| Pod names | Random (nginx-abc123) | Ordinal (nginx-0, nginx-1) |
| Creation order | Parallel | Sequential |
| Storage | Shared or ephemeral | Per-pod persistent |
| Use case | Stateless apps | Stateful apps |

## Dependencies
- BaseResourcePage (base resource management)
- SortableTableWidgetItem (sortable table cells)
- DetailManager (detail page display)
- AppStyles (UI styling)

## Example Data Flow

### StatefulSet with Partial Readiness
```
Kubernetes API Response:
{
  "metadata": {
    "name": "mysql",
    "namespace": "default"
  },
  "spec": {
    "replicas": 3
  },
  "status": {
    "currentReplicas": 2,
    "replicas": 3,
    "readyReplicas": 2
  }
}

Display:
Name: mysql
Namespace: default
Pods: 2/3 (sorted as 0.666)
Replicas: 3
Age: 5d

Interpretation:
- User wants 3 replicas
- Only 2 pods created so far
- 3rd pod may be pending or starting
```
