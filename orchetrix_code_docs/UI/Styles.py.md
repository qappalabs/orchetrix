# Styles.py Documentation

## File Information
- **Path**: `orchetrix/UI/Styles.py`
- **Purpose**: **CENTRAL THEME CONFIGURATION** - All colors, styles, and constants for the entire application

## Overview
This file is the **single source of truth** for all visual styling in Orchetrix. Every color, font, spacing, and CSS style is defined here, ensuring consistent theming across all 50+ pages.

---

## Class: AppColors

**Purpose**: Central color palette for dark theme

### Base Colors
```python
BG_DARK = "#1A1A1A"        # Main background
BG_DARKER = "#0D1117"      # Darker background (cards)
BG_SIDEBAR = "#1e1e1e"     # Sidebar background
BG_HEADER = "#1e1e1e"      # Header background
BG_MEDIUM = "#2d2d2d"      # Medium background (inputs)
BG_LIGHT = "#3a3a3a"       # Light background (hover)
```

### Text Colors
```python
TEXT_LIGHT = "#ffffff"     # Primary text (white)
TEXT_SECONDARY = "#888888" # Secondary text (gray)
TEXT_SUBTLE = "#8e9ba9"    # Subtle text (light gray)
TEXT_LINK = "#4FC3F7"      # Links (light blue)
TEXT_DANGER = "#FF5252"    # Danger text (red)
TEXT_TABLE = "#e2e8f0"     # Table text (off-white)
TEXT_SUCCESS = "#4CAF50"   # Success text (green)
TEXT_WARNING = "#E81123"   # Warning text (red-orange)
```

### Accent Colors
```python
ACCENT_BLUE = "#0095ff"    # Primary accent
ACCENT_GREEN = "#4CAF50"   # Success/active
ACCENT_ORANGE = "#FF5733"  # Warning
ACCENT_RED = "#E81123"     # Danger/error
ACCENT_PURPLE = "#8C33FF"  # Special features
```

### Border Colors
```python
BORDER_COLOR = "#2d2d2d"   # Default border
BORDER_LIGHT = "#454545"   # Light border
BORDER_DARK = "#2a2a2a"    # Dark border
```

### UI Element Colors
```python
CARD_BG = "#1e1e1e"        # Card backgrounds
TAB_INACTIVE = "#2d2d2d"   # Inactive tab
HEADER_BG = "#252525"      # Headers
TABLE_HEADER = "#323232"   # Table headers
```

### Hover States
```python
HOVER_BG = "rgba(255, 255, 255, 0.1)"           # Light hover
HOVER_BG_DARKER = "rgba(255, 255, 255, 0.05)"  # Subtle hover
SELECTED_BG = "rgba(33, 150, 243, 0.2)"         # Selected item (blue)
DANGER_HOVER_BG = "rgba(255, 68, 68, 0.1)"     # Danger hover (red)
```

### Status Colors (CRITICAL for Resource Status)
```python
STATUS_ACTIVE = "#4CAF50"        # Green - Running, Healthy
STATUS_AVAILABLE = "#00FF00"     # Bright green - Available
STATUS_DISCONNECTED = "#FF0000"  # Red - Failed, Error
STATUS_PENDING = "#FFA500"       # Orange - Pending, Waiting
STATUS_WARNING = "#FFC107"       # Yellow - Warning
STATUS_PROGRESS = "#969efa"      # Blue - Progressing
STATUS_ERROR = STATUS_DISCONNECTED  # Alias for error
```

**Usage Example**:
```python
# In PodsPage
if pod_status == "Running":
    color = AppColors.STATUS_ACTIVE  # Green
elif pod_status == "Pending":
    color = AppColors.STATUS_PENDING  # Orange
elif pod_status == "Failed":
    color = AppColors.STATUS_DISCONNECTED  # Red

status_widget = StatusLabel(pod_status, color)
```

### Search Bar Configuration
```python
SEARCH_BAR_HEIGHT = 30
SEARCH_BAR_MIN_WIDTH = 200

SEARCH_BAR_STYLE = """
    QLineEdit, QComboBox {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 5px 10px;
        font-size: 13px;
    }
    QLineEdit:hover, QComboBox:hover {
        border: 1px solid #555555;
    }
    QLineEdit:focus, QComboBox:focus {
        border: 1px solid #0078d7;  # Blue focus border
    }
"""
```

---

## Class: AppConstants

**Purpose**: Layout and sizing constants

### Layout Sizes
```python
SIZES = {
    "SIDEBAR_WIDTH": 180,    # Expanded sidebar width
    "TOPBAR_HEIGHT": 40,     # Top bar height
    "ROW_HEIGHT": 32,        # Table row height
    "ICON_SIZE": 16,         # Icon size
    "ACTION_WIDTH": 40       # Action column width
}
```

### Events Table Column Indices
```python
EVENTS_TABLE_COLUMNS = {
    "TYPE": 0,
    "MESSAGE": 1,
    "NAMESPACE": 2,
    "INVOLVED_OBJECT": 3,
    "SOURCE": 4,
    "COUNT": 5,
    "AGE": 6,
    "LAST_SEEN": 7,
    "ACTIONS": 8
}
```

### Releases Table Column Indices
```python
RELEASES_TABLE_COLUMNS = {
    "CHECKBOX": 0,
    "NAME": 1,
    "NAMESPACE": 2,
    "CHART": 3,
    "REVISION": 4,
    "VERSION": 5,
    "APP_VERSION": 6,
    "STATUS": 7,
    "UPDATED": 8,
    "ACTIONS": 9
}
```

### Spacing System
```python
SPACING = {
    "TINY": 4,      # 4px - tight spacing
    "SMALL": 8,     # 8px - small gaps
    "MEDIUM": 16,   # 16px - default spacing
    "LARGE": 24,    # 24px - section spacing
    "XLARGE": 32    # 32px - large gaps
}
```

**Usage**:
```python
layout.setSpacing(AppConstants.SPACING["MEDIUM"])  # 16px spacing
layout.setContentsMargins(AppConstants.SPACING["SMALL"], 
                         AppConstants.SPACING["SMALL"],
                         AppConstants.SPACING["SMALL"],
                         AppConstants.SPACING["SMALL"])  # 8px margins
```

---

## Class: AppStyles

**Purpose**: Pre-defined CSS stylesheets for common components

### Main Application Style
```python
MAIN_STYLE = f"""
    QMainWindow, QWidget {{
        background-color: {AppColors.BG_DARK};
        color: {AppColors.TEXT_LIGHT};
        font-family: 'Segoe UI', sans-serif;
    }}
    QTabWidget::pane {{
        border: none;
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {AppColors.TEXT_SECONDARY};
        padding: 8px 24px;
        border: none;
        margin-right: 2px;
        font-size: 13px;
    }}
    QTabBar::tab:selected {{
        color: {AppColors.TEXT_LIGHT};
        border-bottom: 2px solid {AppColors.ACCENT_BLUE};
    }}
    QTabBar::tab:hover:!selected {{
        color: {AppColors.TEXT_LIGHT};
    }}
"""
```

### Unified Scroll Bar Style
```python
UNIFIED_SCROLL_BAR_STYLE = """
    QScrollBar:vertical {
        background-color: transparent;
        width: 12px;
        margin: 0px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background-color: #6B7280;  # Gray handle
        min-height: 30px;
        border-radius: 4px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #9CA3AF;  # Lighter on hover
    }
    QScrollBar::handle:vertical:pressed {
        background-color: #4B5563;  # Darker when pressed
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;  # Hide arrows
        width: 0px;
        background: none;
    }
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
        background: none;  # Hide track background
    }
    /* Same for horizontal */
    QScrollBar:horizontal { ... }
"""
```

**Result**: Modern, minimal scrollbars without arrows

### Additional Styles (mentioned but not fully shown)
- `TABLE_STYLE` - Table styling
- `CUSTOM_HEADER_STYLE` - Table header styling
- `CHECKBOX_STYLE` - Checkbox styling
- `ACTION_BUTTON_STYLE` - Action menu button (⋮)
- `ACTION_CONTAINER_STYLE` - Action button container
- `NAV_MENU_DROPDOWN_STYLE` - Sidebar dropdown menus
- `SIDEBAR_TOGGLE_BUTTON_STYLE` - Sidebar collapse button

---

## Visual Theme Overview

### Dark Theme Palette
```
┌─────────────────────────────────────┐
│ Background Hierarchy:               │
│ BG_DARKER (#0D1117) ← Darkest       │
│    ↓                                │
│ BG_DARK (#1A1A1A) ← Main            │
│    ↓                                │
│ BG_SIDEBAR/HEADER (#1e1e1e)         │
│    ↓                                │
│ BG_MEDIUM (#2d2d2d) ← Inputs        │
│    ↓                                │
│ BG_LIGHT (#3a3a3a) ← Hover          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Status Color Coding:                │
│ 🟢 Green (#4CAF50) - Running/Active │
│ 🟠 Orange (#FFA500) - Pending       │
│ 🔴 Red (#FF0000) - Failed/Error     │
│ 🔵 Blue (#969efa) - Progressing     │
│ 🟡 Yellow (#FFC107) - Warning       │
└─────────────────────────────────────┘
```

---

## Usage Patterns

### Pattern 1: Apply Main Style to Window
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(AppStyles.MAIN_STYLE)
```

### Pattern 2: Use Colors for Status
```python
# In any resource page
status_color = AppColors.STATUS_ACTIVE  # Green
if resource_status == "Pending":
    status_color = AppColors.STATUS_PENDING  # Orange
elif resource_status == "Failed":
    status_color = AppColors.STATUS_DISCONNECTED  # Red

status_label.setStyleSheet(f"color: {status_color};")
```

### Pattern 3: Use Spacing Constants
```python
layout = QVBoxLayout()
layout.setSpacing(AppConstants.SPACING["MEDIUM"])  # 16px
layout.setContentsMargins(
    AppConstants.SPACING["LARGE"],   # 24px left
    AppConstants.SPACING["MEDIUM"],  # 16px top
    AppConstants.SPACING["LARGE"],   # 24px right
    AppConstants.SPACING["MEDIUM"]   # 16px bottom
)
```

### Pattern 4: Search Bar Styling
```python
search_bar = QLineEdit()
search_bar.setStyleSheet(AppColors.SEARCH_BAR_STYLE)
search_bar.setMinimumWidth(AppColors.SEARCH_BAR_MIN_WIDTH)
search_bar.setFixedHeight(AppColors.SEARCH_BAR_HEIGHT)
```

---

## Why This File Is Critical

1. **Single Source of Truth**: Change a color here, updates everywhere
2. **Consistent Theming**: All 50+ pages use same colors
3. **Easy Theme Switching**: Could add light theme by changing colors
4. **Maintainability**: No scattered color values in code
5. **Status Standards**: Everyone uses same status colors

---

## Theme Customization Example

**To change primary accent color**:
```python
# Before:
ACCENT_BLUE = "#0095ff"  # Blue accent

# After:
ACCENT_BLUE = "#8C33FF"  # Purple accent

# Result: All blue accents (buttons, links, selections) become purple
```

---

## Dependencies
- PyQt6.QtCore (QSize)
- Used by: ALL UI files (50+ pages, all components)

## Used By
- **Every single file in the project that has UI**
- main.py
- ClusterView.py
- Sidebar.py
- All resource pages
- All base components
- Detail pages
- Terminal panel
