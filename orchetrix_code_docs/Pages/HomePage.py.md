# HomePage.py Documentation

## File Information
- **File Path**: `/home/arun/Projects/orchetrix/Pages/HomePage.py`
- **Purpose**: Main home page UI for Orchestrix showing cluster list and management
- **Lines of Code**: 1366

---

## Overview

`HomePage.py` implements the `OrchestrixGUI` class, which serves as the main landing page of the application. It displays a list of available Kubernetes clusters, allows users to pin/unpin clusters, connect to clusters, and manage cluster connections. The page features a modern card-based UI with search functionality, cluster status indicators, and action buttons.

The home page integrates with cluster management services, handles user preferences for pinned clusters, and provides smooth transitions to the cluster detail view.

---

## Key Features

1. **Cluster Discovery**: Automatically loads available Kubernetes clusters from kubeconfig
2. **Cluster Cards**: Visual representation of clusters with status, labels, and actions
3. **Pin Management**: Allow users to pin/unpin frequently used clusters
4. **Search Functionality**: Real-time search filtering of cluster list
5. **Status Indicators**: Color-coded badges showing cluster connection status
6. **Async Operations**: Non-blocking cluster loading and connection handling
7. **Error Handling**: Graceful error messages for connection failures
8. **Responsive Layout**: Adapts to window size changes with flow layout
9. **Loading States**: Shows loading indicators during async operations

---

## Dependencies and Imports

### PyQt6 Imports
```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QMessageBox,
    QSizePolicy, QApplication
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QSize, QPoint, QRect,
    QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen,
    QPainterPath, QLinearGradient, QFont
)
```

### Application Imports
```python
from UI.Styles import AppStyles, AppColors
from UI.Icons import resource_path
from UI.LoadingSpinner import create_compact_spinner
from Utils.cluster_connector import get_cluster_connector
from Utils.cluster_state_manager import get_cluster_state_manager, ClusterState
from Utils.kubernetes_client import get_kubernetes_client
from Utils.error_handler import error_handler, get_error_handler
from log_handler import method_logger, class_logger
```

---

## Classes

### `FlowLayout(QVBoxLayout)`

**Purpose**: Custom layout that arranges widgets in a flowing grid pattern, wrapping to new rows as needed.

#### Methods

##### `__init__(self, parent=None, margin=0, spacing=-1)`

**Purpose**: Initialize the flow layout with margin and spacing settings.

**Parameters**:
- `parent`: Parent widget
- `margin` (int): Layout margin in pixels
- `spacing` (int): Spacing between items

**Code Explanation**:
```python
def __init__(self, parent=None, margin=0, spacing=-1):
    super().__init__(parent)
    # Don't use parent in QVBoxLayout for custom layout
    self.setContentsMargins(margin, margin, margin, margin)
    self.setSpacing(spacing if spacing >= 0 else 10)
    self._item_list = []  # Store items
```

---

##### `addItem(self, item)`

**Purpose**: Add an item to the layout.

**Code Explanation**:
```python
def addItem(self, item):
    """Add item to layout"""
    self._item_list.append(item)
```

---

##### `count(self)`

**Purpose**: Return the number of items in the layout.

**Returns**: `int` - Number of items

---

##### `itemAt(self, index)`

**Purpose**: Get item at specified index.

**Parameters**:
- `index` (int): Item index

**Returns**: Layout item or None

---

##### `takeAt(self, index)`

**Purpose**: Remove and return item at specified index.

**Parameters**:
- `index` (int): Item index

**Returns**: Removed layout item or None

---

##### `doLayout(self, rect)`

**Purpose**: Arrange items in a flowing grid pattern within the given rectangle.

**Parameters**:
- `rect` (QRect): Available rectangle for layout

**Code Explanation**:
```python
def doLayout(self, rect):
    """Arrange items in a flowing grid pattern"""
    x = rect.x()
    y = rect.y()
    line_height = 0
    spacing = self.spacing()

    for item in self._item_list:
        widget = item.widget()
        if not widget or not widget.isVisible():
            continue

        # Get widget size
        wid_width = widget.sizeHint().width()
        wid_height = widget.sizeHint().height()

        # Check if we need to wrap to next line
        next_x = x + wid_width + spacing
        if next_x - spacing > rect.right() and line_height > 0:
            x = rect.x()
            y = y + line_height + spacing
            next_x = x + wid_width + spacing
            line_height = 0

        # Position the widget
        widget.setGeometry(QRect(QPoint(x, y), QSize(wid_width, wid_height)))

        # Update position for next widget
        x = next_x
        line_height = max(line_height, wid_height)
```

---

### `ClusterCard(QFrame)`

**Purpose**: Visual card widget representing a single Kubernetes cluster with status, actions, and pin functionality.

#### Signals
- `connect_clicked`: Emitted when connect button is clicked
- `pin_toggled`: Emitted when pin button is toggled (bool)

#### Attributes
- `cluster_data` (dict): Cluster information
- `is_pinned` (bool): Pin state
- `_hover_animation`: Animation for hover effects
- `_pin_button`: Pin toggle button
- `_status_badge`: Status indicator badge
- `_connect_button`: Connection action button

---

#### Methods

##### `__init__(self, cluster_data, is_pinned=False, parent=None)`

**Purpose**: Initialize a cluster card with data and pin state.

**Parameters**:
- `cluster_data` (dict): Cluster information (name, status, label, etc.)
- `is_pinned` (bool): Whether the cluster is pinned
- `parent`: Parent widget

**Code Explanation**:
```python
def __init__(self, cluster_data, is_pinned=False, parent=None):
    super().__init__(parent)
    self.cluster_data = cluster_data
    self.is_pinned = is_pinned
    self.setFixedSize(280, 200)
    self.setFrameShape(QFrame.Shape.StyledPanel)
    self.setCursor(Qt.CursorShape.PointingHandCursor)

    # Apply card styling
    self.setStyleSheet(self._get_card_style())

    # Setup hover animation
    self._setup_hover_animation()

    # Create UI
    self._create_ui()
```

---

##### `_create_ui(self)`

**Purpose**: Create the internal UI elements of the cluster card.

**Code Explanation**:
```python
def _create_ui(self):
    """Create card UI elements"""
    layout = QVBoxLayout(self)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    # Header with icon and pin button
    header_layout = QHBoxLayout()

    # Cluster icon
    icon_label = QLabel()
    icon_pixmap = QPixmap(resource_path("logos/kubernetes-icon.png"))
    if not icon_pixmap.isNull():
        scaled_pixmap = icon_pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
        icon_label.setPixmap(scaled_pixmap)
    icon_label.setFixedSize(40, 40)
    header_layout.addWidget(icon_label)

    header_layout.addStretch()

    # Pin button
    self._pin_button = self._create_pin_button()
    header_layout.addWidget(self._pin_button)

    layout.addLayout(header_layout)

    # Cluster name
    name_label = QLabel(self.cluster_data.get('name', 'Unknown'))
    name_label.setStyleSheet("""
        QLabel {
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
        }
    """)
    name_label.setWordWrap(True)
    layout.addWidget(name_label)

    # Status badge
    self._status_badge = self._create_status_badge()
    layout.addWidget(self._status_badge)

    # Label
    label = self.cluster_data.get('label', 'General')
    label_widget = QLabel(f"Label: {label}")
    label_widget.setStyleSheet("color: #9ca3af; font-size: 12px;")
    layout.addWidget(label_widget)

    layout.addStretch()

    # Connect button
    self._connect_button = self._create_connect_button()
    layout.addWidget(self._connect_button)
```

---

##### `_create_status_badge(self)`

**Purpose**: Create a status badge showing cluster connection state.

**Returns**: `QLabel` - Status badge widget

**Code Explanation**:
```python
def _create_status_badge(self):
    """Create status badge with color coding"""
    status = self.cluster_data.get('status', 'unknown')

    # Status color mapping
    status_colors = {
        'connected': '#10b981',      # Green
        'available': '#3b82f6',      # Blue
        'connecting': '#f59e0b',     # Amber
        'disconnect': '#6b7280',     # Gray
        'error': '#ef4444',          # Red
        'manually_disconnected': '#6b7280'  # Gray
    }

    color = status_colors.get(status.lower(), '#6b7280')

    badge = QLabel(status.capitalize())
    badge.setStyleSheet(f"""
        QLabel {{
            background-color: {color};
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }}
    """)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setFixedHeight(24)

    return badge
```

---

##### `_create_connect_button(self)`

**Purpose**: Create the connect/disconnect action button.

**Returns**: `QPushButton` - Action button

**Code Explanation**:
```python
def _create_connect_button(self):
    """Create connect/disconnect button based on status"""
    status = self.cluster_data.get('status', 'unknown').lower()

    button = QPushButton()
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(self._handle_connect_click)

    # Button text based on status
    if status == 'connected':
        button.setText("Disconnect")
        button.setStyleSheet(self._get_disconnect_button_style())
    else:
        button.setText("Connect")
        button.setStyleSheet(self._get_connect_button_style())

    return button
```

---

##### `update_status(self, new_status)`

**Purpose**: Update the card's status and refresh UI accordingly.

**Parameters**:
- `new_status` (str): New cluster status

**Code Explanation**:
```python
def update_status(self, new_status):
    """Update card status and refresh UI"""
    self.cluster_data['status'] = new_status

    # Update status badge
    if self._status_badge:
        self._status_badge.deleteLater()
    self._status_badge = self._create_status_badge()

    # Find and replace badge in layout
    layout = self.layout()
    layout.insertWidget(3, self._status_badge)

    # Update connect button
    status_lower = new_status.lower()
    if status_lower == 'connected':
        self._connect_button.setText("Disconnect")
        self._connect_button.setStyleSheet(self._get_disconnect_button_style())
    else:
        self._connect_button.setText("Connect")
        self._connect_button.setStyleSheet(self._get_connect_button_style())
```

---

##### `set_pinned(self, pinned)`

**Purpose**: Set the pin state of the cluster card.

**Parameters**:
- `pinned` (bool): New pin state

**Code Explanation**:
```python
def set_pinned(self, pinned):
    """Set pin state and update UI"""
    self.is_pinned = pinned
    if self._pin_button:
        icon_path = resource_path("Icons/pinned.svg" if pinned else "Icons/pin.svg")
        self._pin_button.setIcon(QIcon(icon_path))
```

---

### `OrchestrixGUI(QWidget)`

**Purpose**: Main home page widget that displays and manages the cluster list.

#### Signals
- `open_cluster_signal` (str): Emitted when user requests to open a cluster
- `open_preferences_signal`: Emitted when user opens preferences
- `update_pinned_items_signal` (list): Emitted when pinned items list changes

#### Attributes
- `cluster_cards` (list): List of ClusterCard widgets
- `pinned_clusters` (set): Set of pinned cluster names
- `search_bar` (QLineEdit): Search input widget
- `cluster_container_widget` (QWidget): Container for cluster cards
- `cluster_layout` (FlowLayout): Layout for arranging cluster cards
- `loading_spinner` (QWidget): Loading indicator
- `empty_state_widget` (QWidget): Widget shown when no clusters found

---

#### Methods

##### `__init__(self, parent=None)`

**Purpose**: Initialize the home page with cluster list and UI components.

**Code Explanation**:
```python
def __init__(self, parent=None):
    super().__init__(parent)

    # Initialize attributes
    self.cluster_cards = []
    self.pinned_clusters = set()
    self.search_bar = None
    self.cluster_container_widget = None
    self.cluster_layout = None
    self.loading_spinner = None
    self.empty_state_widget = None

    # Get cluster state manager
    self.cluster_state_manager = get_cluster_state_manager()

    # Setup UI
    self.setup_ui()

    # Load pinned clusters from settings
    self.load_pinned_clusters()

    # Connect cluster state signals
    self._connect_cluster_state_signals()
```

---

##### `setup_ui(self)`

**Purpose**: Create and layout all UI components for the home page.

**Code Explanation**:
```python
def setup_ui(self):
    """Setup main UI components"""
    main_layout = QVBoxLayout(self)
    main_layout.setContentsMargins(24, 24, 24, 24)
    main_layout.setSpacing(20)

    # Header section
    header_layout = self._create_header()
    main_layout.addLayout(header_layout)

    # Search bar
    self.search_bar = self._create_search_bar()
    main_layout.addWidget(self.search_bar)

    # Scroll area for cluster cards
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.setStyleSheet("QScrollArea { background: transparent; }")

    # Cluster container
    self.cluster_container_widget = QWidget()
    self.cluster_layout = FlowLayout(self.cluster_container_widget, margin=0, spacing=16)

    scroll_area.setWidget(self.cluster_container_widget)
    main_layout.addWidget(scroll_area)

    # Create loading spinner (initially hidden)
    self.loading_spinner = create_compact_spinner(self)
    self.loading_spinner.hide()

    # Create empty state widget (initially hidden)
    self.empty_state_widget = self._create_empty_state()
    main_layout.addWidget(self.empty_state_widget)
    self.empty_state_widget.hide()
```

---

##### `_create_header(self)`

**Purpose**: Create the header section with title and subtitle.

**Returns**: `QVBoxLayout` - Header layout

**Code Explanation**:
```python
def _create_header(self):
    """Create header with title and subtitle"""
    header_layout = QVBoxLayout()
    header_layout.setSpacing(8)

    # Title
    title = QLabel("Kubernetes Clusters")
    title.setStyleSheet("""
        QLabel {
            color: #ffffff;
            font-size: 28px;
            font-weight: bold;
        }
    """)
    header_layout.addWidget(title)

    # Subtitle
    subtitle = QLabel("Select a cluster to manage")
    subtitle.setStyleSheet("""
        QLabel {
            color: #9ca3af;
            font-size: 14px;
        }
    """)
    header_layout.addWidget(subtitle)

    return header_layout
```

---

##### `_create_search_bar(self)`

**Purpose**: Create the search input field with icon.

**Returns**: `QLineEdit` - Search input widget

**Code Explanation**:
```python
def _create_search_bar(self):
    """Create search bar for filtering clusters"""
    search = QLineEdit()
    search.setPlaceholderText("Search clusters...")
    search.setStyleSheet("""
        QLineEdit {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            border-radius: 8px;
            padding: 12px 40px 12px 40px;
            color: #ffffff;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 1px solid #3b82f6;
        }
    """)

    # Add search icon
    search_icon = QLabel(search)
    search_icon.setPixmap(QIcon(resource_path("Icons/search.svg")).pixmap(20, 20))
    search_icon.move(12, 12)

    # Connect search functionality
    search.textChanged.connect(self._filter_clusters)

    return search
```

---

##### `_filter_clusters(self, search_text)`

**Purpose**: Filter displayed cluster cards based on search text.

**Parameters**:
- `search_text` (str): Search query

**Code Explanation**:
```python
def _filter_clusters(self, search_text):
    """Filter cluster cards based on search text"""
    search_lower = search_text.lower().strip()

    visible_count = 0
    for card in self.cluster_cards:
        cluster_name = card.cluster_data.get('name', '').lower()
        cluster_label = card.cluster_data.get('label', '').lower()

        # Show card if name or label matches search
        should_show = (search_lower in cluster_name or
                      search_lower in cluster_label or
                      not search_lower)

        card.setVisible(should_show)
        if should_show:
            visible_count += 1

    # Show empty state if no results
    if visible_count == 0 and search_lower:
        self._show_empty_state(f"No clusters match '{search_text}'")
    else:
        self.empty_state_widget.hide()
```

---

##### `initialize_cluster_connector(self)`

**Purpose**: Initialize cluster connector and load available clusters.

**Code Explanation**:
```python
@error_handler("initialize_cluster_connector")
def initialize_cluster_connector(self):
    """Initialize cluster connector and load clusters"""
    try:
        self.cluster_connector = get_cluster_connector()

        # Connect signals
        self.cluster_connector.clusters_loaded.connect(self._on_clusters_loaded)
        self.cluster_connector.cluster_connection_changed.connect(self._on_connection_changed)
        self.cluster_connector.error_occurred.connect(self._on_error_occurred)

        # Load clusters asynchronously
        self._show_loading()
        self.cluster_connector.load_clusters_async()

        logging.info("Cluster connector initialized successfully")

    except Exception as e:
        logging.error(f"Failed to initialize cluster connector: {e}")
        self._show_error_state("Failed to load clusters")
```

---

##### `_on_clusters_loaded(self, clusters)`

**Purpose**: Handle clusters loaded event and create cluster cards.

**Parameters**:
- `clusters` (list): List of cluster data dictionaries

**Code Explanation**:
```python
def _on_clusters_loaded(self, clusters):
    """Handle clusters loaded from connector"""
    try:
        self._hide_loading()

        if not clusters:
            self._show_empty_state("No clusters found")
            return

        # Clear existing cards
        self._clear_cluster_cards()

        # Sort clusters: pinned first, then alphabetically
        sorted_clusters = sorted(
            clusters,
            key=lambda c: (c.get('name', '') not in self.pinned_clusters,
                          c.get('name', '').lower())
        )

        # Create cards for each cluster
        for cluster_data in sorted_clusters:
            cluster_name = cluster_data.get('name', '')
            is_pinned = cluster_name in self.pinned_clusters

            card = ClusterCard(cluster_data, is_pinned)
            card.connect_clicked.connect(lambda n=cluster_name: self._handle_connect_click(n))
            card.pin_toggled.connect(lambda pinned, n=cluster_name: self._handle_pin_toggle(n, pinned))

            self.cluster_cards.append(card)
            self.cluster_layout.addWidget(card)

        logging.info(f"Loaded {len(clusters)} clusters")

    except Exception as e:
        logging.error(f"Error loading clusters: {e}")
        self._show_error_state("Error displaying clusters")
```

---

##### `_handle_connect_click(self, cluster_name)`

**Purpose**: Handle cluster connect/disconnect button click.

**Parameters**:
- `cluster_name` (str): Name of the cluster

**Code Explanation**:
```python
@error_handler("handle_connect_click")
def _handle_connect_click(self, cluster_name):
    """Handle cluster connection request"""
    try:
        # Get current state
        current_state = self.cluster_state_manager.get_cluster_state(cluster_name)

        if current_state == ClusterState.CONNECTED:
            # Disconnect
            logging.info(f"Disconnecting from cluster: {cluster_name}")
            self.cluster_state_manager.disconnect_cluster(cluster_name)
        else:
            # Connect and open cluster view
            logging.info(f"Connecting to cluster: {cluster_name}")
            self.open_cluster_signal.emit(cluster_name)

    except Exception as e:
        logging.error(f"Error handling connect click for {cluster_name}: {e}")
        QMessageBox.critical(self, "Connection Error",
                           f"Failed to connect to {cluster_name}: {str(e)}")
```

---

##### `_handle_pin_toggle(self, cluster_name, pinned)`

**Purpose**: Handle pin/unpin toggle for a cluster.

**Parameters**:
- `cluster_name` (str): Name of the cluster
- `pinned` (bool): New pin state

**Code Explanation**:
```python
def _handle_pin_toggle(self, cluster_name, pinned):
    """Handle pin toggle for cluster"""
    if pinned:
        self.pinned_clusters.add(cluster_name)
        logging.info(f"Pinned cluster: {cluster_name}")
    else:
        self.pinned_clusters.discard(cluster_name)
        logging.info(f"Unpinned cluster: {cluster_name}")

    # Save to settings
    self.save_pinned_clusters()

    # Emit signal to update other components
    self.update_pinned_items_signal.emit(list(self.pinned_clusters))

    # Re-sort cluster cards
    self._resort_cluster_cards()
```

---

##### `load_pinned_clusters(self)`

**Purpose**: Load pinned clusters from saved settings file.

**Code Explanation**:
```python
def load_pinned_clusters(self):
    """Load pinned clusters from settings"""
    try:
        import json
        settings_path = self._get_settings_path()

        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                pinned = settings.get('pinned_clusters', [])
                self.pinned_clusters = set(pinned)
                logging.info(f"Loaded {len(pinned)} pinned clusters")
        else:
            logging.info("No pinned clusters settings found")

    except Exception as e:
        logging.error(f"Error loading pinned clusters: {e}")
```

---

##### `save_pinned_clusters(self)`

**Purpose**: Save pinned clusters to settings file.

**Code Explanation**:
```python
def save_pinned_clusters(self):
    """Save pinned clusters to settings"""
    try:
        import json
        settings_path = self._get_settings_path()

        # Load existing settings or create new
        settings = {}
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                settings = json.load(f)

        # Update pinned clusters
        settings['pinned_clusters'] = list(self.pinned_clusters)

        # Save settings
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)

        logging.info(f"Saved {len(self.pinned_clusters)} pinned clusters")

    except Exception as e:
        logging.error(f"Error saving pinned clusters: {e}")
```

---

## Usage Examples

### Creating and Displaying the Home Page
```python
from Pages.HomePage import OrchestrixGUI

# Create home page
home_page = OrchestrixGUI()

# Connect signals
home_page.open_cluster_signal.connect(lambda name: switch_to_cluster(name))
home_page.update_pinned_items_signal.connect(lambda items: update_titlebar(items))

# Initialize cluster loading
home_page.initialize_cluster_connector()

# Show the page
home_page.show()
```

### Handling Cluster Connection
```python
# Connect to a cluster
home_page.open_cluster_signal.emit("my-cluster")

# Update cluster status
home_page._on_connection_changed("my-cluster", ClusterState.CONNECTED)
```

### Managing Pinned Clusters
```python
# Pin a cluster
home_page._handle_pin_toggle("my-cluster", True)

# Get list of pinned clusters
pinned = list(home_page.pinned_clusters)

# Save pinned state
home_page.save_pinned_clusters()
```

---

## Architecture Notes

### State Management
- Cluster states managed by `ClusterStateManager`
- Pin state persisted in JSON settings file
- Real-time UI updates based on cluster state changes

### Async Operations
- Cluster loading is asynchronous to prevent UI blocking
- Loading spinner shown during async operations
- Error handling with user-friendly messages

### UI Components
- Custom `FlowLayout` for responsive grid
- `ClusterCard` widgets for visual representation
- Search filtering with real-time updates
- Empty states for no results/errors

### Performance
- Lazy loading of cluster data
- Efficient search filtering
- Minimal redraws with targeted updates

---

## Related Files

- `/home/arun/Projects/orchetrix/Utils/cluster_connector.py` - Cluster loading logic
- `/home/arun/Projects/orchetrix/Utils/cluster_state_manager.py` - Cluster state management
- `/home/arun/Projects/orchetrix/UI/Styles.py` - Application styling
- `/home/arun/Projects/orchetrix/UI/LoadingSpinner.py` - Loading indicators
- `/home/arun/Projects/orchetrix/main.py` - Main window integration
