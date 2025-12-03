# base_components.py Documentation

## File Information
- **Path**: `orchetrix/Base_Components/base_components.py`
- **Purpose**: Reusable UI components to reduce code duplication - sortable tables, status labels, custom headers

## Overview
This module contains foundational UI components used throughout Orchetrix. These components provide consistent styling, behavior, and performance optimizations across all resource pages.

---

## Class: SortableTableWidgetItem

### Purpose
Custom QTableWidgetItem that enables **numeric sorting** instead of alphabetical sorting.

### Problem It Solves
```python
# Without SortableTableWidgetItem (WRONG):
# Alphabetical sort: "1", "10", "2", "20", "3" (wrong order!)

# With SortableTableWidgetItem (CORRECT):
# Numeric sort: "1", "2", "3", "10", "20" (correct order!)
```

### Implementation

```python
class SortableTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, value=None):
        super().__init__(str(text))
        self.value = value  # Numeric value for sorting
        
    def __lt__(self, other):
        # Compare using numeric value if both have one
        if isinstance(other, SortableTableWidgetItem) and self.value is not None and other.value is not None:
            return self.value < other.value
        # Fall back to string comparison
        return super().__lt__(other)
```

### Usage Examples

**Age Column**:
```python
# Display: "5d", but sort by minutes (7200)
age_str = "5d"
age_minutes = 5 * 1440  # Convert days to minutes
item = SortableTableWidgetItem(age_str, age_minutes)
table.setItem(row, col, item)

# Sorts correctly: "1h" < "5h" < "1d" < "5d"
```

**Pods Column**:
```python
# Display: "3/5", but sort by percentage (60%)
pods_str = "3/5"
percentage = 3 / 5  # 0.6
item = SortableTableWidgetItem(pods_str, percentage)
table.setItem(row, col, item)

# Sorts correctly: "1/5" (20%) < "3/5" (60%) < "5/5" (100%)
```

**Restart Count**:
```python
# Display: "10", sort by numeric value
restart_count = "10"
item = SortableTableWidgetItem(restart_count, int(restart_count))
table.setItem(row, col, item)

# Sorts correctly: 2 < 10 < 20 (not "10" < "2" < "20")
```

---

## Class: StatusLabel

### Purpose
Widget that displays color-coded status text **without being affected by table row selection**.

### Problem It Solves
```python
# Without StatusLabel:
# - Status text in QTableWidgetItem
# - When row selected, text becomes white (unreadable)
# - Status colors lost

# With StatusLabel:
# - Status widget with transparent background
# - Row selection doesn't affect color
# - Status colors always visible
```

### Implementation

```python
class StatusLabel(QWidget):
    clicked = pyqtSignal()  # Emitted when clicked
    
    def __init__(self, status_text, color=None, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create label
        self.label = QLabel(status_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set color
        if color:
            self.label.setStyleSheet(f"color: {QColor(color).name()}; background-color: transparent;")
        
        layout.addWidget(self.label)
        
        # Transparent background (doesn't block selection highlight)
        self.setStyleSheet("background-color: transparent;")
    
    def mousePressEvent(self, event):
        """Emit clicked signal when widget is clicked"""
        self.clicked.emit()
        super().mousePressEvent(event)
```

### Usage Examples

**Pod Status with Colors**:
```python
# Running = Green
if pod_status == "Running":
    color = AppColors.STATUS_ACTIVE
    status_widget = StatusLabel("Running", color)
    table.setCellWidget(row, status_col, status_widget)

# Failed = Red
elif pod_status == "Failed":
    color = AppColors.STATUS_DISCONNECTED
    status_widget = StatusLabel("Failed", color)
    table.setCellWidget(row, status_col, status_widget)
```

**Deployment Conditions**:
```python
# Multiple conditions with different colors
conditions_widget = MultiColorStatusLabel()
conditions_widget.set_status_text("Available Progressing")
# Shows: [Available (green)] [Progressing (blue)]
```

**With Click Handler**:
```python
status_widget = StatusLabel("Running", AppColors.STATUS_ACTIVE)
status_widget.clicked.connect(lambda: table.selectRow(row))
table.setCellWidget(row, status_col, status_widget)

# Clicking status selects the row
```

---

## Class: CustomHeader

### Purpose
Table header that **only allows sorting on specific columns** and shows hover indicators.

### Features
1. **Selective Sorting**: Only sortable columns respond to clicks
2. **Hover Indicators**: Visual feedback on sortable columns
3. **Custom Sort Arrows**: Draws custom sort indicators
4. **Consistent Styling**: Matches application theme

### Implementation

```python
class CustomHeader(QHeaderView):
    def __init__(self, orientation, sortable_columns=None, parent=None):
        super().__init__(orientation, parent)
        self.sortable_columns = sortable_columns or set()  # e.g., {1, 2, 3, 4}
        self.hovered_section = -1  # Track mouse hover
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Disable default sort indicators
        self.setSortIndicatorShown(False)
        
        # Enable mouse tracking for hover
        self.setMouseTracking(True)
        
        # Apply custom styling
        self.setStyleSheet(self._get_header_style())
```

### Styling

```python
def _get_header_style(self):
    return f"""
        QHeaderView::section {{
            background-color: {AppColors.HEADER_BG};
            color: {AppColors.TEXT_SECONDARY};
            padding: 8px;
            border: none;
            border-bottom: 1px solid {AppColors.BORDER_COLOR};
            font-size: 12px;
            text-align: center;
            font-weight: bold;
        }}
        
        QHeaderView::section:hover {{
            background-color: {AppColors.BG_MEDIUM};
        }}
        
        /* Hide default Qt sort arrows */
        QHeaderView::down-arrow, QHeaderView::up-arrow {{
            image: none;
            width: 0px;
            height: 0px;
        }}
    """
```

### Mouse Event Handling

**Click Event**:
```python
def mousePressEvent(self, event):
    logicalIndex = self.logicalIndexAt(event.pos())
    if logicalIndex in self.sortable_columns:
        super().mousePressEvent(event)  # Allow sort
    else:
        event.ignore()  # Ignore click
```

**Hover Event**:
```python
def mouseMoveEvent(self, event):
    logical_index = self.logicalIndexAt(event.pos())
    
    # Only update hover for sortable columns
    if logical_index in self.sortable_columns:
        if self.hovered_section != logical_index:
            self.hovered_section = logical_index
            self.update()  # Trigger repaint
    else:
        if self.hovered_section != -1:
            self.hovered_section = -1
            self.update()
```

### Custom Sort Indicator

```python
def _draw_custom_sort_indicator(self, painter, section):
    """Draw custom sort indicator for active sort or hover"""
    is_sorted_section = (self.sortIndicatorSection() == section)
    is_hovered_section = (self.hovered_section == section)
    
    # Only draw if sorted or hovered
    if not (is_sorted_section or is_hovered_section):
        return
        
    # Draw custom arrow
    arrow_size = 8
    arrow_x = section_rect.right() - arrow_size - 5
    arrow_y = section_rect.center().y()
    
    # Full opacity for active sort, reduced for hover
    if is_sorted_section:
        painter.setPen(QPen(QColor(AppColors.TEXT_SECONDARY), 2))
    else:
        hover_color = QColor(AppColors.TEXT_SECONDARY)
        hover_color.setAlpha(128)  # 50% opacity
        painter.setPen(QPen(hover_color, 2))
    
    # Draw arrow shape
    if self.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder:
        # Up arrow: ^
        painter.drawLine(arrow_x, arrow_y, arrow_x + arrow_size/2, arrow_y - arrow_size/2)
        painter.drawLine(arrow_x + arrow_size/2, arrow_y - arrow_size/2, arrow_x + arrow_size, arrow_y)
    else:
        # Down arrow: v
        painter.drawLine(arrow_x, arrow_y, arrow_x + arrow_size/2, arrow_y + arrow_size/2)
        painter.drawLine(arrow_x + arrow_size/2, arrow_y + arrow_size/2, arrow_x + arrow_size, arrow_y)
```

### Usage Example

```python
# Define which columns can be sorted
sortable_columns = {1, 2, 3, 4}  # Name, Namespace, Age, Status

# Create custom header
header = CustomHeader(Qt.Orientation.Horizontal, sortable_columns, table)
table.setHorizontalHeader(header)

# Result:
# - Columns 1,2,3,4: Clickable, sortable, show hover/sort indicators
# - Column 0 (checkbox): Not sortable, no hover effect
# - Column 5 (actions): Not sortable, no hover effect
```

---

## Additional Components

### BaseTablePage
Base class with common table functionality (mentioned but not in the read portion).

### StandardResourceColumns
Standard column definitions for resource pages (mentioned but not in the read portion).

### ResourcePageHelpers
Helper functions for resource page operations (mentioned but not in the read portion).

---

## Common Usage Patterns

### Pattern 1: Resource Page Table Setup

```python
class PodsPage(BaseResourcePage):
    def setup_page_ui(self):
        # Define headers and sortable columns
        headers = ["", "Name", "Namespace", "Status", "Age", ""]
        sortable_columns = {1, 2, 3, 4}  # All except checkbox and actions
        
        # Setup base UI
        super().setup_ui("Pods", headers, sortable_columns)
        
        # Table automatically gets CustomHeader with sortable columns
```

### Pattern 2: Populate Table Row with Sortable Items

```python
def populate_resource_row(self, row, resource):
    # Checkbox column (not sortable)
    checkbox = self._create_checkbox_container(row, resource["name"])
    table.setCellWidget(row, 0, checkbox)
    
    # Name column (sortable, string)
    name_item = SortableTableWidgetItem(resource["name"])
    table.setItem(row, 1, name_item)
    
    # Age column (sortable, numeric)
    age_str = "5d"
    age_minutes = 7200
    age_item = SortableTableWidgetItem(age_str, age_minutes)
    table.setItem(row, 4, age_item)
    
    # Status column (not sortable, colored widget)
    status_widget = StatusLabel("Running", AppColors.STATUS_ACTIVE)
    table.setCellWidget(row, 3, status_widget)
```

---

## Key Benefits

1. **Code Reusability**: Used by 50+ resource pages
2. **Consistent UI**: Same look and feel everywhere
3. **Performance**: Custom sorting is fast
4. **User Experience**: Clear visual feedback
5. **Maintainability**: Change styling in one place

---

## Dependencies
- PyQt6.QtWidgets (QWidget, QTableWidgetItem, QLabel, etc.)
- PyQt6.QtCore (Qt, QSize, pyqtSignal, etc.)
- PyQt6.QtGui (QColor, QPainter, QPen, etc.)
- UI.Styles (AppStyles, AppColors, AppConstants)
- UI.Icons (resource_path)

---

## Used By
- All resource pages (Pods, Deployments, Services, etc.)
- Base_Components.base_resource_page
- UI components with tables
