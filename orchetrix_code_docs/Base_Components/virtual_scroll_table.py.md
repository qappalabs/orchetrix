# virtual_scroll_table.py Documentation

## File Information
- **Path**: `orchetrix/Base_Components/virtual_scroll_table.py`
- **Purpose**: High-performance virtual scrolling table for handling 1000+ resources without lag

## Overview
VirtualScrollTable uses QTableView + VirtualizedResourceModel to achieve true virtual scrolling. Only visible rows are rendered, enabling smooth performance with massive datasets.

## Performance Impact
```
Without Virtual Scrolling (QTableWidget):
- 1000 pods = 1000 widgets created = 5-10 seconds load time + lag
- Memory: ~50MB+ for widgets

With Virtual Scrolling (VirtualScrollTable):
- 1000 pods = ~100 visible widgets = <1 second load time + smooth scrolling
- Memory: ~5MB for visible widgets
```

## Class: HighPerformanceDelegate

### Purpose
Custom cell renderer for optimized painting.

```python
class HighPerformanceDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index: QModelIndex):
        if option.state & QApplication.State.State_Selected:
            # Custom selection color (light blue)
            painter.fillRect(option.rect, QColor(227, 242, 253))
        
        # Use default painting for text
        super().paint(painter, option, index)
```

---

## Class: VirtualScrollTable (extends QTableView)

### Constructor
```python
def __init__(self, headers: List[str], parent=None):
    self.headers = headers
    self._model = None
    self._formatters = {}
    
    # Enable virtual scrolling
    self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    
    # Set custom delegate
    self.delegate = HighPerformanceDelegate(self)
    self.setItemDelegate(self.delegate)
    
    # Initialize with empty model
    self.set_resource_data([], self.headers)
```

### Key Features
1. **True Virtual Scrolling**: Only renders visible rows
2. **Responsive Columns**: Auto-adjusts to screen width
3. **High Performance Delegate**: Optimized cell rendering
4. **Selection Tracking**: Emits signals on selection changes
5. **Sorting Enabled**: Built-in sort support

### Method: `set_resource_data()`
```python
def set_resource_data(self, resources: List[Dict], headers: List[str]):
    """Set resource data using VirtualizedResourceModel"""
    self._model = VirtualizedResourceModel(resources, headers, self)
    self.setModel(self._model)
    
    # Adjust columns to fit
    self._adjust_columns_to_screen()
    
    # Emit data changed signal
    self.data_changed.emit()
```

**Usage**:
```python
# Load 1000 pods
resources = [{"name": "pod-1", ...}, {"name": "pod-2", ...}, ...]  # 1000 items
table.set_resource_data(resources, ["Name", "Namespace", "Status"])

# Result: Instant load, smooth scrolling
```

### Method: `_adjust_columns_to_screen()`
```python
def _adjust_columns_to_screen(self):
    """Auto-size columns based on available width"""
    available_width = self.viewport().width() - 20  # Account for scrollbar
    column_count = len(self.headers)
    base_width = max(80, available_width // column_count)
    
    # Priority columns get more space
    priority_columns = ['name', 'namespace', 'status', 'age']
    
    for i, column_name in enumerate(self.headers):
        if column_name.lower() in priority_columns:
            width = min(int(base_width * 1.2), 200)  # 20% wider
        else:
            width = min(base_width, 150)
        
        width = max(width, 80)  # Minimum 80px
        header.resizeSection(i, width)
    
    # Stretch last column to fill
    header.setSectionResizeMode(column_count - 1, QHeaderView.ResizeMode.Stretch)
```

### Signals
```python
item_selected = pyqtSignal(int)  # Row selected
item_double_clicked = pyqtSignal(int)  # Row double-clicked
data_changed = pyqtSignal()  # Data changed
selection_changed = pyqtSignal(list)  # Selection changed (list of row indices)
```

---

## Virtual Scrolling Mechanism

### How It Works
```
Table with 1000 rows:
┌─────────────────┐
│ Row 0    ← Visible (rendered)
│ Row 1    ← Visible (rendered)
│ Row 2    ← Visible (rendered)
│ ...
│ Row 99   ← Visible (rendered)
├─────────────────┤ ← Viewport boundary
│ Row 100  ← Not visible (NOT rendered)
│ Row 101  ← Not visible (NOT rendered)
│ ...
│ Row 999  ← Not visible (NOT rendered)
└─────────────────┘

Scrolling down:
- Rows 0-99 removed from rendering
- Rows 100-199 rendered
- Memory usage stays constant!
```

### Comparison

**QTableWidget (Old Approach)**:
```python
# Creates 1000 widgets
for i in range(1000):
    item = QTableWidgetItem(pods[i]["name"])
    table.setItem(i, 0, item)  # 1000 widgets in memory
```

**VirtualScrollTable (New Approach)**:
```python
# Creates ~100 visible widgets
table.set_resource_data(pods, headers)  # Model holds data, view renders visible
```

---

## Use Cases

### Large Pod Lists
```python
# 500 pods across all namespaces
pods = kubernetes_api.list_all_pods()  # 500 items
table.set_resource_data(pods, ["Name", "Namespace", "Status", "Age"])
# Instant load, smooth scrolling
```

### Cluster-Wide Resources
```python
# All events in cluster (1000+)
events = kubernetes_api.list_all_events()  # 1000+ items
table.set_resource_data(events, ["Type", "Reason", "Message", "Age"])
# No lag
```

---

## Dependencies
- VirtualizedResourceModel (data model)
- QTableView (view layer)
- HighPerformanceDelegate (rendering)
- PyQt6.QtCore (Qt framework)

## Benefits
1. ✅ Handles 1000+ rows smoothly
2. ✅ Constant memory usage
3. ✅ Instant load times
4. ✅ Responsive scrolling
5. ✅ Auto-sizing columns
