# DeploymentsPage.py Documentation

## File Information
- **Path**: `orchetrix/Pages/WorkLoad/DeploymentsPage.py`
- **Lines**: 309
- **Purpose**: Kubernetes Deployments management page with multi-color status conditions display

## Overview
DeploymentsPage displays and manages Kubernetes Deployments. It extends BaseResourcePage and features a custom MultiColorStatusLabel widget that shows deployment conditions (Available, Progressing) with different colors in a single column. Supports viewing, editing, and deleting deployments with detail page integration.

---

## Imports

### PyQt6 Framework
```python
from PyQt6.QtWidgets import QHeaderView, QPushButton, QLabel, QWidget, QHBoxLayout
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

## Class: MultiColorStatusLabel

```python
class MultiColorStatusLabel(QWidget):
    """Widget that displays status conditions with different colors in a single label."""
```

### Constructor: `__init__()`
```python
def __init__(self, parent=None):
    super().__init__(parent)
    
    self.layout = QHBoxLayout(self)
    self.layout.setContentsMargins(0, 0, 0, 0)
    self.layout.setSpacing(5)  # Space between different status text
    self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    self.setStyleSheet("background-color: transparent;")
```

**Features**:
- Horizontal layout with 5px spacing
- Transparent background (doesn't block table selection)
- Center-aligned content

---

### Method: `set_status_text()`

```python
def set_status_text(self, status_text):
    # Clear any existing labels
    while self.layout.count():
        item = self.layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    
    if not status_text:
        label = QLabel("<none>")
        label.setStyleSheet(f"color: {QColor(AppColors.TEXT_TABLE).name()};")
        self.layout.addWidget(label)
        return
        
    # Parse status text - split by space
    statuses = status_text.split()
    
    for status in statuses:
        label = QLabel(status)
        
        # Set color based on status type
        if status == "Available":
            label.setStyleSheet(f"color: {QColor(AppColors.STATUS_ACTIVE).name()};")
        elif status == "Progressing":
            label.setStyleSheet(f"color: {QColor(AppColors.STATUS_PROGRESS).name()};")
        else:
            label.setStyleSheet(f"color: {QColor(AppColors.TEXT_TABLE).name()};")
            
        self.layout.addWidget(label)
```

**How it works**:
1. **Clears existing labels**: Removes old status text
2. **Empty status handling**: Shows `<none>` if no status
3. **Parse statuses**: Splits by space (e.g., "Available Progressing")
4. **Color mapping**:
   - `Available` → Green (STATUS_ACTIVE)
   - `Progressing` → Blue (STATUS_PROGRESS)
   - Other → Default (TEXT_TABLE)
5. **Create labels**: Each status gets its own colored label

**Example**: 
- Input: "Available Progressing"
- Output: ["Available" (green)] ["Progressing" (blue)]

---

## Class: DeploymentsPage

### Constructor: `__init__()`

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.resource_type = "deployments"
    self.setup_page_ui()
```

**Initialization**:
- Sets resource_type to "deployments" for Kubernetes API
- Calls setup_page_ui() to create table and UI

---

### Method: `setup_page_ui()`

```python
def setup_page_ui(self):
    headers = ["", "Name", "Namespace", "Pods", "Replicas", "Age", "Conditions", ""]
    sortable_columns = {1, 2, 3, 4, 5, 6}
    
    layout = super().setup_ui("Deployments", headers, sortable_columns)
    
    self.table.setStyleSheet(AppStyles.TABLE_STYLE)
    self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
    
    self.configure_columns()
```

**UI Setup**:
- **8 columns**: Checkbox, Name, Namespace, Pods, Replicas, Age, Conditions, Actions
- **Sortable**: All columns except checkbox and actions
- **Styles**: Table and header styles from AppStyles
- **Configure columns**: Sets widths and resize modes

---

### Method: `configure_columns()`

```python
def configure_columns(self):
    column_specs = [
        (0, 40, "fixed"),        # Checkbox
        (1, 220, "interactive"), # Name
        (2, 120, "interactive"), # Namespace
        (3, 80, "interactive"),  # Pods
        (4, 100, "interactive"), # Replicas
        (5, 50, "interactive"),  # Age
        (6, 90, "stretch"),      # Conditions - stretches to fill
        (7, 40, "fixed"),        # Actions
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
- **Interactive**: Name (220px), Namespace (120px), Pods (80px), Replicas (100px), Age (50px)
- **Stretch**: Conditions (90px base) - fills remaining space

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
    available_replicas = status.get("availableReplicas", 0)
    replicas = status.get("replicas", 0)
    pods_str = f"{available_replicas}/{replicas}"
```
Shows available pods vs total pods (e.g., "3/3" or "2/3")

#### Replicas Count
```python
replicas_str = "0"
if raw_data:
    spec = raw_data.get("spec", {})
    replicas_str = str(spec.get("replicas", 0))
```
Desired replica count from deployment spec

#### Conditions Parsing
```python
conditions_str = ""
if raw_data:
    status = raw_data.get("status", {})
    conditions = status.get("conditions", [])
    condition_types = []
    for condition in conditions:
        if condition.get("status") == "True":
            condition_types.append(condition.get("type", ""))
    conditions_str = " ".join(condition_types)
```

**Conditions Logic**:
1. Gets all conditions from deployment status
2. Filters only conditions with status="True"
3. Extracts condition type (e.g., "Available", "Progressing")
4. Joins with space: "Available Progressing"

**Common Deployment Conditions**:
- **Available**: Minimum replicas available
- **Progressing**: Deployment is rolling out
- **ReplicaFailure**: ReplicaSet creation failed

#### Age Calculation
```python
age_str = resource["age"]
if raw_data:
    metadata = raw_data.get("metadata", {})
    creation_timestamp = metadata.get("creationTimestamp")
    if creation_timestamp:
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

#### Sortable Column Items

**Pods Column Sorting**:
```python
if col == 2:  # Pods column
    try:
        available, total = value.split("/")
        # Calculate as percentage for better sorting
        pods_value = (float(available) / float(total)) * 100 if float(total) > 0 else 0
    except (ValueError, IndexError, ZeroDivisionError):
        pods_value = 0
    item = SortableTableWidgetItem(value, pods_value)
```
Sorts by percentage availability (3/3 = 100% > 2/3 = 66%)

**Replicas Column Sorting**:
```python
elif col == 3:  # Replicas column
    try:
        replicas_value = float(value)
    except ValueError:
        replicas_value = 0
    item = SortableTableWidgetItem(value, replicas_value)
```
Sorts numerically

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
Converts to minutes for sorting (5d = 7200m > 12h = 720m > 30m)

---

#### Multi-Color Status Widget

```python
conditions_widget = MultiColorStatusLabel()
conditions_widget.set_status_text(conditions_str)
self.table.setCellWidget(row, 6, conditions_widget)
```

**Example Display**:
- "Available Progressing" → [Available (green)] [Progressing (blue)]
- "Available" → [Available (green)]
- "" → [<none> (gray)]

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
1. Click any column except actions to select row
2. Extract deployment name and namespace
3. Walk up parent tree to find ClusterView
4. Convert resource_type "deployments" → "deployment" (singular)
5. Show detail page with full deployment info

---

## Key Features

1. **Multi-Color Status**: Displays multiple conditions with different colors simultaneously
2. **Pod Availability**: Shows available/total pods (e.g., 3/3)
3. **Replica Management**: Displays desired replica count
4. **Age Display**: Human-readable age (5d, 12h, 30m)
5. **Sortable Columns**: Sort by name, pods, replicas, age, conditions
6. **Detail View**: Click row to see full deployment details
7. **Action Menu**: Edit and Delete options
8. **Bulk Selection**: Checkbox for multi-delete

## Action Menu Items
- **Edit**: Edit deployment YAML
- **Delete**: Delete the deployment

## Deployment Conditions
- **Available**: Minimum availability condition met
- **Progressing**: Deployment is making progress (rolling out)
- **ReplicaFailure**: Failed to create ReplicaSet

## Dependencies
- BaseResourcePage (base resource management)
- MultiColorStatusLabel (custom status widget)
- SortableTableWidgetItem (sortable table cells)
- DetailManager (detail page display)

## Example Data Flow

### Deployment with Multiple Conditions
```
Kubernetes API Response:
{
  "status": {
    "conditions": [
      {"type": "Available", "status": "True"},
      {"type": "Progressing", "status": "True"}
    ],
    "availableReplicas": 3,
    "replicas": 3
  },
  "spec": {
    "replicas": 3
  }
}

Display:
Name: nginx-deployment
Pods: 3/3
Replicas: 3
Conditions: [Available (green)] [Progressing (blue)]
```
