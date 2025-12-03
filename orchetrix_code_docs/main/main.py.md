# main.py Documentation

## File Information
- **Path**: `orchetrix/main.py`
- **Lines**: 1,033
- **Purpose**: Application entry point and main window implementation for Orchetrix

## Overview
This is the core entry point file for the Orchetrix Kubernetes management application. It contains the MainWindow class which serves as the primary UI container and orchestrates the entire application lifecycle, including initialization, cluster switching, periodic cleanup, and memory management.

---

## Imports

### Standard Library
```python
import sys
import os
import logging
import gc
from datetime import datetime
```
- `sys`: System operations, exit codes, exception handling
- `os`: File path operations for resource loading
- `logging`: Application-wide logging
- `gc`: Garbage collection for memory management
- `datetime`: Timestamp generation for logging

### PyQt6 Framework
```python
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QSplashScreen
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
```
- **QApplication**: Main application object, event loop
- **QMainWindow**: Main window container with menu bar, status bar
- **QStackedWidget**: Widget stack for view switching (Home ↔ Cluster)
- **QSplashScreen**: Splash screen during initialization
- **QTimer**: Periodic cleanup timer (30-second intervals)
- **pyqtSignal**: Signal-slot pattern for event communication

### Internal Components
```python
from UI.HomeView import HomeView
from UI.ClusterView import ClusterView
from Services.kubernetes.cluster_manager import ClusterManager
from Services.kubernetes.cluster_state_manager import ClusterStateManager
from Utils.thread_manager import ThreadManager
```

---

## Global Functions

### 1. resource_path()
```python
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        return os.path.join(base_path, relative_path)
    except Exception:
        return os.path.join(os.path.abspath("."), relative_path)
```

**Purpose**: Resolves resource file paths for both development and PyInstaller bundled environments.

**How it works**:
- Checks if `sys._MEIPASS` exists (set by PyInstaller when bundled)
- If bundled: Uses `_MEIPASS` as base path (temporary extraction folder)
- If development: Uses current directory as base path
- Returns absolute path to requested resource

**Usage Example**:
```python
icon_path = resource_path("Resources/icon.png")
```

---

### 2. global_exception_handler()
```python
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Global handler for uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
```

**Purpose**: Catches all unhandled exceptions globally to prevent crashes and log errors.

**How it works**:
- Intercepts exceptions before they crash the application
- Special handling for KeyboardInterrupt (Ctrl+C)
- Logs all other exceptions with full traceback
- Prevents silent failures

**When it triggers**: Any exception not caught by try-except blocks

---

### 3. initialize_resources()
```python
def initialize_resources():
    """Initialize application resources and managers"""
    try:
        _ = ThreadManager()
        _ = ClusterStateManager()
        logging.info("Application resources initialized successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to initialize resources: {e}")
        return False
```

**Purpose**: Pre-initializes singleton managers before main window creation.

**What it initializes**:
1. **ThreadManager**: Manages background worker threads
2. **ClusterStateManager**: Maintains current cluster state and configuration

**Why it's important**: Ensures managers are ready before UI needs them

---

## MainWindow Class

### Class Definition
```python
class MainWindow(QMainWindow):
    """Main application window"""
    cluster_switched = pyqtSignal(str)  # Signal when cluster changes
```

**Inheritance**: `QMainWindow` (PyQt6 main window with menu/status bars)

**Signals**:
- `cluster_switched`: Emitted when user switches clusters (passes cluster name)

---

### Constructor: `__init__()`

```python
def __init__(self):
    super().__init__()
    self.setWindowTitle("Orchetrix - Kubernetes Management")
    self.setMinimumSize(1400, 900)
```

**Window Setup**:
- Sets window title
- Minimum size: 1400x900 pixels
- Responsive resizing enabled

#### Manager Initialization
```python
self.cluster_manager = ClusterManager()
self.cluster_state_manager = ClusterStateManager()
self.thread_manager = ThreadManager()
```

**Managers**:
- `cluster_manager`: Loads kubeconfig, lists clusters, switches contexts
- `cluster_state_manager`: Tracks active cluster, namespace, resource states
- `thread_manager`: Manages worker thread lifecycle and cleanup

#### View Stack Setup
```python
self.stacked_widget = QStackedWidget()
self.setCentralWidget(self.stacked_widget)

self.home_view = HomeView()
self.cluster_view = None  # Lazy loaded
```

**Stacked Widget Pattern**:
- Central widget that holds multiple views
- Only one view visible at a time
- Views: HomeView (index 0), ClusterView (index 1)
- ClusterView lazy-loaded on first cluster selection

#### Periodic Cleanup Timer
```python
self._cleanup_timer = QTimer(self)
self._cleanup_timer.timeout.connect(self._periodic_cleanup)
self._cleanup_timer.start(30000)  # 30 seconds
```

**Cleanup System**:
- Runs every 30 seconds
- Prevents memory leaks from long-running sessions
- Calls `_periodic_cleanup()` method

---

### Method: `_periodic_cleanup()`

```python
def _periodic_cleanup(self):
    """Periodic cleanup of resources"""
    try:
        # Force garbage collection
        collected = gc.collect()

        # Cleanup finished workers
        self._cleanup_finished_workers()

        # Cleanup caches if cluster view exists
        if self.cluster_view:
            self._cleanup_cluster_view_caches()

        logging.debug(f"Periodic cleanup completed. Collected {collected} objects")
    except Exception as e:
        logging.error(f"Error in periodic cleanup: {e}")
```

**Cleanup Operations**:
1. **Garbage Collection**: Forces Python GC to free unused objects
2. **Worker Cleanup**: Removes finished worker threads
3. **Cache Cleanup**: Clears old data from virtual scroll caches
4. **Logging**: Reports objects collected

**Performance Impact**: Prevents memory growth over time

---

### Method: `_cleanup_finished_workers()`

```python
def _cleanup_finished_workers(self):
    """Cleanup finished worker threads"""
    try:
        self.thread_manager.cleanup_finished_workers()
    except Exception as e:
        logging.error(f"Error cleaning up workers: {e}")
```

**Purpose**: Removes worker threads that have completed execution from ThreadManager's tracking.

---

### Method: `_cleanup_cluster_view_caches()`

```python
def _cleanup_cluster_view_caches(self):
    """Cleanup caches in cluster view pages"""
    try:
        for page in self.cluster_view.pages.values():
            if hasattr(page, 'virtual_table') and page.virtual_table:
                page.virtual_table.cleanup_cache()
    except Exception as e:
        logging.error(f"Error cleaning up cluster view caches: {e}")
```

**Purpose**: Clears cached data from virtual scroll tables in all resource pages.

**How it works**:
- Iterates through all loaded pages (Pods, Deployments, etc.)
- Each page has a `virtual_table` with cached row data
- Calls `cleanup_cache()` to remove old entries

---

### Method: `init_ui()`

```python
def init_ui(self):
    """Initialize UI components"""
    self.stacked_widget.addWidget(self.home_view)
    self.stacked_widget.setCurrentIndex(0)  # Start on home view
```

**UI Initialization**:
- Adds HomeView to stacked widget
- Sets HomeView as initial view (index 0)
- ClusterView added later when needed

---

### Method: `setup_connections()`

```python
def setup_connections(self):
    """Setup signal-slot connections"""
    self.home_view.cluster_selected.connect(self.switch_to_cluster_view)
```

**Signal Connection**:
- `home_view.cluster_selected` → `switch_to_cluster_view()`
- When user clicks cluster in HomeView, switches to ClusterView

---

### Method: `switch_to_cluster_view()`

```python
def switch_to_cluster_view(self, cluster_name):
    """Switch to cluster view for selected cluster"""
    try:
        # Switch kubectl context
        success = self.cluster_manager.switch_cluster(cluster_name)
        if not success:
            return

        # Update state manager
        self.cluster_state_manager.set_current_cluster(cluster_name)

        # Lazy load cluster view if needed
        if self.cluster_view is None:
            self.cluster_view = ClusterView(cluster_name)
            self.stacked_widget.addWidget(self.cluster_view)
            self.cluster_view.back_to_home.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        else:
            self.cluster_view.set_cluster(cluster_name)

        # Switch to cluster view
        self.stacked_widget.setCurrentWidget(self.cluster_view)
        self.cluster_switched.emit(cluster_name)

    except Exception as e:
        logging.error(f"Error switching to cluster view: {e}")
```

**Cluster Switching Process**:

1. **Context Switch**: Calls `cluster_manager.switch_cluster()` to change kubectl context
2. **State Update**: Updates `cluster_state_manager` with new cluster name
3. **Lazy Loading**:
   - First time: Creates ClusterView, adds to stack, connects back button
   - Subsequent times: Updates existing ClusterView with new cluster
4. **View Switch**: Changes stacked widget to show ClusterView
5. **Signal Emission**: Emits `cluster_switched` signal for other components

**Error Handling**: Logs errors but doesn't crash application

---

### Method: `closeEvent()`

```python
def closeEvent(self, event):
    """Handle window close event"""
    try:
        # Stop cleanup timer
        self._cleanup_timer.stop()

        # Cleanup all workers
        self.thread_manager.cleanup_all_workers()

        # Final garbage collection
        gc.collect()

        event.accept()
    except Exception as e:
        logging.error(f"Error in close event: {e}")
        event.accept()
```

**Application Shutdown**:
1. **Stop Timer**: Stops periodic cleanup timer
2. **Worker Cleanup**: Terminates all background workers
3. **Final GC**: Last garbage collection pass
4. **Accept Close**: Allows window to close

**Why it's important**: Ensures clean shutdown without hanging threads

---

## Main Entry Point

```python
def main():
    """Main application entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Set global exception handler
    sys.excepthook = global_exception_handler

    # Initialize resources
    if not initialize_resources():
        sys.exit(1)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Orchetrix")

    # Set application icon
    icon_path = resource_path("Resources/icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Show splash screen
    splash_pix = QPixmap(resource_path("Resources/splash.png"))
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    # Create main window
    window = MainWindow()
    window.init_ui()
    window.setup_connections()

    # Close splash and show window
    splash.close()
    window.show()

    # Start event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
```

**Application Startup Sequence**:

1. **Logging Setup**: Configures log format and level (INFO)
2. **Exception Handler**: Installs global exception handler
3. **Resource Init**: Initializes managers, exits if fails
4. **QApplication**: Creates Qt application object
5. **Icon Setup**: Loads application icon from resources
6. **Splash Screen**: Shows splash screen during initialization
7. **Main Window**: Creates, initializes, and connects MainWindow
8. **Show Window**: Closes splash, shows main window
9. **Event Loop**: Starts Qt event loop (blocks until app exits)

**Exit Codes**:
- `0`: Normal exit
- `1`: Resource initialization failed

---

## Key Takeaways

1. **Entry Point**: This file is the application's entry point (`if __name__ == '__main__'`)
2. **Resource Management**: Handles PyInstaller bundling with `resource_path()`
3. **Memory Management**: 30-second cleanup timer prevents memory leaks
4. **Lazy Loading**: ClusterView only created when first cluster selected
5. **Signal Pattern**: Uses PyQt signals for loose coupling (cluster_switched)
6. **Error Recovery**: Global exception handler prevents crashes
7. **Clean Shutdown**: Proper cleanup in `closeEvent()` ensures no hanging threads
8. **Stacked Views**: Home and Cluster views managed by QStackedWidget

## Dependencies
- PyQt6 (UI framework)
- ClusterManager (Kubernetes context switching)
- ClusterStateManager (Application state)
- ThreadManager (Background workers)
- HomeView (Cluster selection UI)
- ClusterView (Kubernetes resource management UI)
