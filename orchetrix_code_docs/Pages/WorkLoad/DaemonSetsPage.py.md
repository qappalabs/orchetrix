# DaemonSetsPage.py Documentation

## File Information
- **Path**: `orchetrix/Pages/WorkLoad/DaemonSetsPage.py`
- **Lines**: 252
- **Purpose**: Kubernetes DaemonSets management page with node selector display

## Overview
DaemonSetsPage displays and manages Kubernetes DaemonSets. DaemonSets ensure that all (or some) nodes run a copy of a pod - commonly used for cluster-level services like logging agents, monitoring agents, and node networking. This page shows pod scheduling status, node selectors, and age with detail page integration.

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

## Class: DaemonSetsPage

### Constructor: `__init__()`

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.resource_type = "daemonsets"
    self.setup_page_ui()
```

**Initialization**:
- Sets resource_type to "daemonsets" for Kubernetes API
- Calls setup_page_ui() to create table and UI

---

### Method: `setup_page_ui()`

```python
def setup_page_ui(self):
    headers = ["", "Name", "Namespace", "Pods", "Node Selector", "Age", ""]
    sortable_columns = {1, 2, 3, 5}
    
    layout = super().setup_ui("Daemon Sets", headers, sortable_columns)
    
    self.table.setStyleSheet(AppStyles.TABLE_STYLE)
    self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
    
    self.configure_columns()
```

**UI Setup**:
- **7 columns**: Checkbox, Name, Namespace, Pods, Node Selector, Age, Actions
- **Sortable**: Name, Namespace, Pods, Age (Node Selector is not sortable)
- **Page title**: "Daemon Sets"
- **Styles**: Applied from AppStyles

---

### Method: `configure_columns()`

```python
def configure_columns(self):
    column_specs = [
        (0, 40, "fixed"),        # Checkbox
        (1, 200, "interactive"), # Name
        (2, 100, "interactive"), # Namespace
        (3, 90, "interactive"),  # Pods
        (4, 180, "interactive"), # Node Selector
        (5, 50, "stretch"),      # Age - stretches
        (6, 40, "fixed"),        # Actions
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
- **Fixed**: Checkbox (40px), Actions (40px)
- **Interactive**: Name (200px), Namespace (100px), Pods (90px), Node Selector (180px)
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
    current_number_scheduled = status.get("currentNumberScheduled", 0)
    desired_number_scheduled = status.get("desiredNumberScheduled", 0)
    pods_str = f"{current_number_scheduled}/{desired_number_scheduled}"
```

**Pods Display Format**:
- Shows `current/desired` scheduled pods
- Example: "5/5" means pods running on all targeted nodes
- Example: "3/5" means pods running on only 3 of 5 targeted nodes
- **currentNumberScheduled**: Pods currently scheduled and running
- **desiredNumberScheduled**: Number of nodes that should run the daemon pod

**Why DaemonSets use currentNumberScheduled**:
- DaemonSets schedule one pod per node
- `desiredNumberScheduled` = number of nodes matching nodeSelector
- `currentNumberScheduled` = pods actually running
- If 3/5, it means 2 pods failed to schedule or are pending

---

#### Node Selector Extraction
```python
node_selector = "<none>"
if raw_data:
    spec = raw_data.get("spec", {})
    
    # DaemonSets have nodeSelector in spec.template.spec
    template = spec.get("template", {})
    template_spec = template.get("spec", {})
    
    # First try to get from template.spec.nodeSelector
    selectors = template_spec.get("nodeSelector", {})
    
    # If that's empty, try to get from spec.nodeSelector directly (old format)
    if not selectors:
        selectors = spec.get("nodeSelector", {})
        
    # Format the node selectors as a string
    if selectors:
        node_selector = ", ".join([f"{k}={v}" for k, v in selectors.items()])
```

**Node Selector Logic**:

1. **Check new format**: `spec.template.spec.nodeSelector` (standard location)
2. **Fallback to old format**: `spec.nodeSelector` (backwards compatibility)
3. **Format as string**: "key1=value1, key2=value2"
4. **Default**: "<none>" if no selectors

**Example Node Selectors**:
- `"disk=ssd"` - Run only on nodes with SSD
- `"gpu=true"` - Run only on nodes with GPU
- `"zone=us-west-1a, tier=frontend"` - Multiple constraints
- `"<none>"` - Run on all nodes

**Common Use Cases**:
- `kubernetes.io/os=linux` - Linux nodes only
- `node.kubernetes.io/instance-type=m5.large` - Specific instance type
- `topology.kubernetes.io/zone=us-east-1a` - Specific availability zone

---

#### Age Calculation
```python
age_str = resource["age"]
if raw_data:
    metadata = raw_data.get("metadata", {})
    creation_timestamp = metadata.get("creationTimestamp")
    if creation_timestamp:
        import datetime
        from dateutil import parser
        try:
            creation_time = parser.parse(creation_timestamp)
            now = datetime.datetime.now(datetime.timezone.utc)
            delta = now - creation_time
            
            days = delta.days
            seconds = delta.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            
            if days > 0:
                age_str = f"{days}d"
            elif hours > 0:
                age_str = f"{hours}h"
            else:
                age_str = f"{minutes}m"
        except Exception:
            pass
```

**Age Format**:
- Days: "5d"
- Hours: "12h"
- Minutes: "30m"

---

#### Column Data Assembly
```python
columns = [
    resource["name"],
    resource["namespace"],
    pods_str,
    node_selector,
    age_str
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
- Converts "5/5" to 1.0 (100%)
- Converts "3/5" to 0.6 (60%)
- Sorts by coverage percentage
- Fully deployed DaemonSets (5/5) appear before partially deployed (3/5)

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

---

#### Cell Formatting
```python
# Set text alignment
if col in [1, 2, 3, 4]:  # Pods, Age
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
- **Center-aligned**: Namespace, Pods, Node Selector, Age
- **Left-aligned**: Name
- **Non-editable**: All cells
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
1. Click any column except actions
2. Select row
3. Extract DaemonSet name and namespace
4. Find ClusterView
5. Convert "daemonsets" → "daemonset"
6. Show detail page

---

## Key Features

1. **Node Coverage**: Shows pod deployment across nodes (e.g., 5/5)
2. **Node Selector Display**: Shows which nodes the DaemonSet targets
3. **Age Display**: Human-readable format (5d, 12h, 30m)
4. **Sortable Columns**: Sort by name, namespace, pods, age
5. **Detail View**: Click row to see full DaemonSet details
6. **Action Menu**: Edit and Delete options
7. **Bulk Selection**: Checkbox for multi-delete
8. **Responsive Layout**: Age column stretches to fill space

## Action Menu Items
- **Edit**: Edit DaemonSet YAML configuration
- **Delete**: Delete the DaemonSet (removes all daemon pods)

## DaemonSet Characteristics

### What are DaemonSets?
DaemonSets ensure that all (or some) nodes run a copy of a pod. As nodes are added to the cluster, pods are added to them. As nodes are removed, pods are garbage collected.

### Common Use Cases
1. **Logging Agents**: Fluentd, Filebeat - collect logs from all nodes
2. **Monitoring Agents**: Node exporters, Datadog agent - monitor all nodes
3. **Storage Daemons**: Ceph, GlusterFS - provide storage on all nodes
4. **Network Plugins**: Calico, Weave Net - node networking
5. **Security Agents**: Falco, Aqua Security - security monitoring

### Node Selector Examples

**Run on Linux nodes only**:
```yaml
nodeSelector:
  kubernetes.io/os: linux
```
Display: `kubernetes.io/os=linux`

**Run on GPU nodes**:
```yaml
nodeSelector:
  gpu: "true"
```
Display: `gpu=true`

**Run on specific zone and tier**:
```yaml
nodeSelector:
  topology.kubernetes.io/zone: us-west-1a
  tier: frontend
```
Display: `topology.kubernetes.io/zone=us-west-1a, tier=frontend`

### Difference from Deployments/StatefulSets
| Feature | Deployment | StatefulSet | DaemonSet |
|---------|-----------|-------------|-----------|
| Pods per node | Variable | Variable | One per node |
| Replica count | User-defined | User-defined | Auto (based on nodes) |
| Node selection | Scheduler decides | Scheduler decides | nodeSelector or all nodes |
| Use case | Stateless apps | Stateful apps | Node-level services |

## Dependencies
- BaseResourcePage (base resource management)
- SortableTableWidgetItem (sortable table cells)
- DetailManager (detail page display)
- AppStyles (UI styling)

## Example Data Flow

### DaemonSet with Node Selector
```
Kubernetes API Response:
{
  "metadata": {
    "name": "fluentd",
    "namespace": "kube-system"
  },
  "spec": {
    "template": {
      "spec": {
        "nodeSelector": {
          "kubernetes.io/os": "linux",
          "logging": "enabled"
        }
      }
    }
  },
  "status": {
    "currentNumberScheduled": 5,
    "desiredNumberScheduled": 5,
    "numberReady": 5
  }
}

Display:
Name: fluentd
Namespace: kube-system
Pods: 5/5 (sorted as 1.0)
Node Selector: kubernetes.io/os=linux, logging=enabled
Age: 12h

Interpretation:
- Fluentd logging agent
- Targets Linux nodes with logging=enabled label
- Running on all 5 matching nodes
- Fully deployed (5/5 = 100%)
```

### DaemonSet without Node Selector
```
Display:
Name: node-exporter
Node Selector: <none>
Pods: 10/10

Interpretation:
- Runs on ALL nodes in cluster (no selector)
- 10 nodes total, all have the daemon pod
```
