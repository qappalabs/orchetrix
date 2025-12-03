# PodsPage.py Documentation

## File Information
- **Path**: `orchetrix/Pages/WorkLoad/PodsPage.py`
- **Lines**: 559
- **Purpose**: Enhanced Pods page with integrated port forwarding, logs viewing, SSH access, and YAML editing functionality

## Overview
PodsPage is a comprehensive resource management page for Kubernetes Pods. It extends BaseResourcePage and adds pod-specific features like port forwarding management, container logs viewing, SSH into containers, and YAML editing. The page displays a sortable table with all pod information including status, containers, restarts, and provides action buttons for various operations.

---

## Imports

### Standard Library
```python
import logging
```
- Application logging for debugging and monitoring

### PyQt6 Framework
```python
from PyQt6.QtWidgets import QHeaderView, QPushButton, QLabel, QWidget, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
```
- **QHeaderView**: Table header customization
- **QPushButton**: Action buttons (Port Forwards, Refresh, Delete)
- **QMessageBox**: Confirmation and error dialogs
- **QTimer**: Delayed operations for UI updates
- **QColor**: Status color styling

### Internal Components
```python
from Base_Components.base_components import SortableTableWidgetItem, StatusLabel
from Base_Components.base_resource_page import BaseResourcePage
from UI.Styles import AppColors, AppStyles
from Utils.port_forward_manager import get_port_forward_manager, PortForwardConfig
from Utils.port_forward_dialog import PortForwardDialog, ActivePortForwardsDialog
from UI.Icons import resource_path
```

---

## Class: PodsPage

### Inheritance
```python
class PodsPage(BaseResourcePage):
```
Extends **BaseResourcePage** for standard resource page functionality (table, refresh, delete, etc.)

---

### Constructor: `__init__()`

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.resource_type = "pods"
    self.port_manager = get_port_forward_manager()
    self.setup_page_ui()
    self.port_manager.port_forward_started.connect(self.on_port_forward_started)
    self.port_manager.port_forward_stopped.connect(self.on_port_forward_stopped)
    self.port_manager.port_forward_error.connect(self.on_port_forward_error)
```

**Initialization Steps**:
1. Calls parent BaseResourcePage constructor
2. Sets `resource_type = "pods"` for API calls
3. Gets singleton PortForwardManager instance
4. Sets up UI with `setup_page_ui()`
5. Connects port forwarding signals:
   - `port_forward_started` → Update UI when port forward starts
   - `port_forward_stopped` → Update UI when port forward stops
   - `port_forward_error` → Show error messages

---

### Method: `setup_page_ui()`

```python
def setup_page_ui(self):
    headers = ["", "Name", "Namespace", "Containers", "Restarts", "Controlled By", "Node", "QoS", "Age", "Status", ""]
    sortable_columns = {1, 2, 3, 4, 5, 6, 7, 8, 9}
    
    layout = super().setup_ui("Pods", headers, sortable_columns)
    
    self.table.setStyleSheet(AppStyles.TABLE_STYLE)
    self.table.horizontalHeader().setStyleSheet(AppStyles.CUSTOM_HEADER_STYLE)
    
    self.configure_columns()
    self._add_port_forward_management_button()
```

**UI Setup Process**:
1. **Define Headers**: 11 columns including checkbox, pod details, and actions
2. **Sortable Columns**: All columns except checkbox (0) and actions (10) are sortable
3. **Base UI Setup**: Calls parent method to create table, refresh button, etc.
4. **Apply Styles**: Sets table and header styles from AppStyles
5. **Configure Columns**: Sets column widths and resize modes
6. **Port Forward Button**: Adds management button next to Refresh

**Column Structure**:
- Column 0: Checkbox for bulk selection
- Columns 1-8: Pod information (Name, Namespace, Containers, etc.)
- Column 9: Status with color-coded StatusLabel
- Column 10: Action menu (⋮)

---

### Method: `_add_port_forward_management_button()`

```python
def _add_port_forward_management_button(self):
    pf_btn = QPushButton("Port Forwards")
    pf_btn.setStyleSheet("""
        QPushButton {
            background-color: #1976D2;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: #1565C0;
        }
        QPushButton:pressed {
            background-color: #0D47A1;
        }
    """)
    pf_btn.clicked.connect(self.show_port_forward_management)
    
    # Find the header layout and add button before Refresh
    for i in range(self.layout().count()):
        item = self.layout().itemAt(i)
        if item.layout():
            for j in range(item.layout().count()):
                widget = item.layout().itemAt(j).widget()
                if isinstance(widget, QPushButton) and widget.text() == "Refresh":
                    item.layout().insertWidget(item.layout().count() - 1, pf_btn)
                    break
```

**Button Features**:
- Blue button with hover and press states
- Inserted before Refresh button in header
- Opens ActivePortForwardsDialog to manage all active port forwards

---

### Method: `configure_columns()`

```python
def configure_columns(self):
    header = self.table.horizontalHeader()
    
    column_specs = [
        (0, 40, "fixed"),        # Checkbox
        (1, 210, "interactive"), # Name
        (2, 100, "interactive"), # Namespace
        (3, 80, "interactive"),  # Containers
        (4, 80, "interactive"),  # Restarts
        (5, 130, "interactive"), # Controlled By
        (6, 110, "interactive"), # Node
        (7, 80, "interactive"),  # QoS
        (8, 50, "stretch"),      # Age
        (9, 70, "fixed"),        # Status
        (10, 40, "fixed")        # Actions
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
- **Fixed**: Checkbox, Status, Actions - cannot be resized
- **Interactive**: All pod info columns - user can resize
- **Stretch**: Age column - fills remaining space
- Delayed width utilization ensures table fills window width

---

### Method: `populate_resource_row()`

```python
def populate_resource_row(self, row, resource):
    self.table.setRowHeight(row, 40)
    name = resource["name"]
    
    # 1) Checkbox
    cb = self._create_checkbox_container(row, name)
    cb.setStyleSheet(AppStyles.CHECKBOX_STYLE)
    self.table.setCellWidget(row, 0, cb)

    # Get data from kubernetes API response
    raw = resource.get("raw_data", {}) or {}
    
    # Extract pod information from raw Kubernetes data
    containers_count = str(len(raw.get("spec", {}).get("containers", [])) + 
                          len(raw.get("spec", {}).get("initContainers", [])))
    
    restart_count = str(sum(cs.get("restartCount", 0) 
                           for cs in raw.get("status", {}).get("containerStatuses", [])))
    
    controller_by = raw.get("metadata", {}).get("ownerReferences", [{}])[0].get("kind", "")
    qos_class = raw.get("status", {}).get("qosClass", "")
    node_name = raw.get("spec", {}).get("nodeName", "")
    age_str = resource.get("age", "Unknown")
```

**Data Extraction from Kubernetes API**:
- **Containers**: Counts both regular containers + init containers
- **Restarts**: Sums restart counts from all container statuses
- **Controlled By**: Gets owner reference (e.g., "ReplicaSet", "DaemonSet")
- **QoS Class**: Gets Quality of Service class (Guaranteed, Burstable, BestEffort)
- **Node Name**: Which node the pod is running on

**Pod Status Determination**:
```python
pod_status = "Unknown"
if raw and raw.get("status"):
    status = raw["status"]
    pod_phase = status.get("phase", "Unknown")
    pod_status = pod_phase
    
    # Check for more specific states from container statuses
    for cs in status.get("containerStatuses", []):
        state = cs.get("state", {})
        if "waiting" in state:
            reason = state["waiting"].get("reason", "")
            if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                pod_status = reason
                break
        elif "terminated" in state:
            if state["terminated"].get("exitCode", 0) != 0:
                pod_status = "Error"
                break
```

**Status Detection Logic**:
1. Gets base phase (Running, Pending, Failed, Succeeded)
2. Checks container statuses for more specific errors
3. Prioritizes error states (CrashLoopBackOff, ImagePullBackOff)
4. Detects non-zero exit codes as "Error"

**Status Color Mapping**:
```python
if pod_status == "Running":
    color = AppColors.STATUS_ACTIVE
elif pod_status == "Pending":
    color = AppColors.STATUS_PENDING
elif pod_status in ("Failed", "Error", "CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
    color = AppColors.STATUS_DISCONNECTED
elif pod_status == "Succeeded":
    color = AppColors.STATUS_AVAILABLE
else:
    color = AppColors.TEXT_TABLE

status_widget = StatusLabel(pod_status, color)
status_widget.clicked.connect(lambda: self.table.selectRow(row))
self.table.setCellWidget(row, status_col, status_widget)
```

**StatusLabel Features**:
- Color-coded based on pod health
- Clickable to select row
- Doesn't get overridden by table selection highlighting

---

### Method: `_get_pod_exposed_ports()`

```python
def _get_pod_exposed_ports(self, pod_resource):
    if not pod_resource or not pod_resource.get("raw_data"):
        return []
    
    exposed_ports = []
    raw_data = pod_resource["raw_data"]
    
    containers = raw_data.get("spec", {}).get("containers", [])
    for container in containers:
        ports = container.get("ports", [])
        for port in ports:
            if port.get("containerPort"):
                exposed_ports.append({
                    'port': port["containerPort"],
                    'protocol': port.get("protocol", "TCP"),
                    'name': port.get("name", f"port-{port['containerPort']}")
                })
    
    return exposed_ports
```

**Purpose**: Extracts all exposed ports from pod's container specs

**Returns**: List of port dictionaries with:
- `port`: Container port number (e.g., 8080)
- `protocol`: TCP or UDP
- `name`: Port name or auto-generated (e.g., "http", "port-8080")

---

### Method: `_handle_port_forward()`

```python
def _handle_port_forward(self, pod_name, namespace, resource):
    try:
        exposed_ports = self._get_pod_exposed_ports(resource)
        
        if not exposed_ports:
            QMessageBox.information(
                self, "No Ports Available",
                f"Pod '{pod_name}' does not expose any ports for forwarding."
            )
            return
        
        available_ports = [port_info['port'] for port_info in exposed_ports]
        
        dialog = PortForwardDialog(
            resource_name=pod_name,
            resource_type='pod',
            namespace=namespace,
            available_ports=available_ports,
            parent=self
        )
        
        dialog.port_forward_requested.connect(self._create_port_forward)
        dialog.exec()
        
    except Exception as e:
        QMessageBox.critical(
            self, "Port Forward Error",
            f"Failed to initiate port forward: {str(e)}"
        )
```

**Port Forward Flow**:
1. Extracts exposed ports from pod
2. Shows error if no ports available
3. Opens PortForwardDialog with available ports
4. User selects target port and local port
5. Dialog emits `port_forward_requested` signal
6. `_create_port_forward()` handles actual creation

---

### Method: `_create_port_forward()`

```python
def _create_port_forward(self, config):
    try:
        port_config = self.port_manager.start_port_forward(
            resource_name=config['resource_name'],
            resource_type=config['resource_type'],
            namespace=config['namespace'],
            target_port=config['target_port'],
            local_port=config.get('local_port'),
            protocol=config.get('protocol', 'TCP')
        )
        
        QMessageBox.information(
            self, "Port Forward Created",
            f"Port forward created successfully!\n\n"
            f"Resource: {config['resource_type']}/{config['resource_name']}\n"
            f"Local: localhost:{port_config.local_port}\n"
            f"Target: {port_config.target_port}\n"
            f"Protocol: {port_config.protocol}\n\n"
            f"Access at: http://localhost:{port_config.local_port}"
        )
        
    except Exception as e:
        QMessageBox.critical(
            self, "Port Forward Failed",
            f"Failed to create port forward: {str(e)}"
        )
```

**Port Forward Creation**:
- Calls PortForwardManager to start kubectl port-forward
- Shows success dialog with connection details
- Includes direct localhost URL for access
- Error handling for failures (port in use, pod not found, etc.)

---

### Method: `show_port_forward_management()`

```python
def show_port_forward_management(self):
    dialog = ActivePortForwardsDialog(self)
    dialog.exec()
```

**Purpose**: Opens dialog showing all active port forwards across all pods

**Dialog Features**:
- List of active forwards with resource names
- Stop individual forwards
- Stop all forwards
- View port forward logs

---

### Signal Handlers

#### `on_port_forward_started()`
```python
def on_port_forward_started(self, config: PortForwardConfig):
    if hasattr(self, 'show_transient_message'):
        self.show_transient_message(
            f"Port forward started: localhost:{config.local_port} -> {config.target_port}"
        )
```

#### `on_port_forward_stopped()`
```python
def on_port_forward_stopped(self, key: str):
    if hasattr(self, 'show_transient_message'):
        self.show_transient_message(f"Port forward stopped: {key}")
```

#### `on_port_forward_error()`
```python
def on_port_forward_error(self, key: str, error_message: str):
    if hasattr(self, 'show_transient_message'):
        self.show_transient_message(f"Port forward error: {error_message}")
```

**Purpose**: Show transient notifications when port forward state changes

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
                parent.detail_manager.show_detail("pod", resource_name, namespace)
```

**Click Behavior**:
1. Clicking any column except actions menu selects row
2. Extracts pod name and namespace from row
3. Walks up parent tree to find ClusterView
4. Shows pod detail page using DetailManager
5. Detail page displays full pod info, YAML, events, and logs

---

### Method: `_handle_view_logs()`

```python
def _handle_view_logs(self, pod_name, namespace, resource):
    try:
        parent = self.parent()
        cluster_view = None
        
        # Walk up parent tree to find ClusterView
        while parent:
            if parent.__class__.__name__ == 'ClusterView' or hasattr(parent, 'terminal_panel'):
                cluster_view = parent
                break
            parent = parent.parent()
        
        if cluster_view and hasattr(cluster_view, 'terminal_panel'):
            cluster_view.terminal_panel.create_enhanced_logs_tab(pod_name, namespace)
            
            # Show terminal panel if hidden
            if not cluster_view.terminal_panel.is_visible:
                if hasattr(cluster_view, 'toggle_terminal'):
                    cluster_view.toggle_terminal()
                elif hasattr(cluster_view.terminal_panel, 'show_terminal'):
                    cluster_view.terminal_panel.show_terminal()
                
            logging.info(f"Created logs tab for pod: {pod_name} in namespace: {namespace}")
        else:
            # Fallback error
            QMessageBox.information(
                self, "Logs",
                f"Opening logs for pod: {pod_name} in namespace: {namespace}\n\n"
                f"Terminal panel will show logs. Use kubectl logs {pod_name} -n {namespace} if needed."
            )
    except Exception as e:
        logging.error(f"Failed to create logs tab for pod {pod_name}: {e}")
        QMessageBox.critical(
            self, "Error", 
            f"Failed to open logs for pod {pod_name}: {str(e)}"
        )
```

**Logs Viewing Process**:
1. Finds ClusterView by walking parent tree
2. Accesses terminal_panel from ClusterView
3. Creates enhanced logs tab with streaming logs
4. Shows terminal panel if currently hidden
5. Fallback message if terminal panel unavailable

---

### Method: `_handle_ssh_into_pod()`

```python
def _handle_ssh_into_pod(self, pod_name, namespace, resource):
    try:
        parent = self.parent()
        cluster_view = None
        
        while parent:
            if parent.__class__.__name__ == 'ClusterView' or hasattr(parent, 'terminal_panel'):
                cluster_view = parent
                break
            parent = parent.parent()
        
        if cluster_view and hasattr(cluster_view, 'terminal_panel'):
            cluster_view.terminal_panel.create_ssh_tab(pod_name, namespace)
            
            if not cluster_view.terminal_panel.is_visible:
                if hasattr(cluster_view, 'toggle_terminal'):
                    cluster_view.toggle_terminal()
                elif hasattr(cluster_view.terminal_panel, 'show_terminal'):
                    cluster_view.terminal_panel.show_terminal()
                
            logging.info(f"Created SSH tab for pod: {pod_name} in namespace: {namespace}")
    except Exception as e:
        logging.error(f"Failed to create SSH tab for pod {pod_name}: {e}")
        QMessageBox.critical(
            self, "Error", 
            f"Failed to open SSH for pod {pod_name}: {str(e)}"
        )
```

**SSH Process**:
1. Similar to logs viewing, finds ClusterView
2. Creates SSH tab in terminal panel
3. Runs `kubectl exec -it` command in interactive terminal
4. User gets shell access inside pod container

---

### Method: `_handle_edit_resource()`

```python
def _handle_edit_resource(self, resource_name, resource_namespace, resource):
    try:
        parent = self.parent()
        cluster_view = None
        
        while parent:
            if parent.__class__.__name__ == 'ClusterView' or hasattr(parent, 'detail_manager'):
                cluster_view = parent
                break
            parent = parent.parent()
        
        if cluster_view and hasattr(cluster_view, 'detail_manager'):
            cluster_view.detail_manager.show_detail(self.resource_type, resource_name, resource_namespace)
            
            # Trigger edit mode after detail page loads
            QTimer.singleShot(500, lambda: self._trigger_edit_mode(cluster_view))
            
            logging.info(f"Opening {self.resource_type}/{resource_name} in edit mode")
    except Exception as e:
        logging.error(f"Failed to open {resource_name} for editing: {e}")
        QMessageBox.critical(
            self, "Error", 
            f"Failed to open {resource_name} for editing: {str(e)}"
        )
```

**Edit Resource Flow**:
1. Shows detail page with pod YAML
2. Waits 500ms for page to load
3. Triggers edit mode in YAML section
4. User can modify YAML and apply changes

---

### Method: `_trigger_edit_mode()`

```python
def _trigger_edit_mode(self, cluster_view):
    try:
        if hasattr(cluster_view, 'detail_manager') and cluster_view.detail_manager._detail_page:
            detail_page = cluster_view.detail_manager._detail_page
            
            if hasattr(detail_page, 'yaml_section'):
                yaml_section = detail_page.yaml_section
                if hasattr(yaml_section, 'toggle_yaml_edit_mode') and yaml_section.yaml_editor.isReadOnly():
                    yaml_section.toggle_yaml_edit_mode()
                    logging.info("Successfully activated edit mode in YAML section")
    except Exception as e:
        logging.error(f"Error triggering edit mode: {e}")
```

**Edit Mode Activation**:
1. Accesses detail page's YAML section
2. Checks if YAML editor is in read-only mode
3. Toggles to edit mode if ready
4. User can now edit and apply YAML changes

---

## Key Features

1. **Port Forwarding**: Integrated port forward management with UI dialogs
2. **Logs Viewing**: Stream logs from containers in terminal panel
3. **SSH Access**: Interactive shell access to pod containers
4. **YAML Editing**: Edit pod configuration directly in app
5. **Status Visualization**: Color-coded status labels (Running, Pending, Error, etc.)
6. **Bulk Operations**: Checkbox selection for deleting multiple pods
7. **Detail View**: Click row to see full pod details, events, and YAML
8. **Sortable Columns**: Sort by any column (name, restarts, age, etc.)
9. **Real-time Updates**: Refresh button to reload pod list
10. **Action Menu**: Context menu with all pod-specific operations

## Action Menu Items
- **View Logs**: Open logs in terminal panel
- **SSH**: Interactive shell into container
- **Port Forward**: Configure port forwarding
- **Edit**: Edit pod YAML
- **Delete**: Delete the pod
- **Refresh**: Reload pod data

## Dependencies
- BaseResourcePage (base resource management)
- PortForwardManager (port forwarding backend)
- PortForwardDialog (port forward UI)
- StatusLabel (color-coded status widget)
- ClusterView (parent container)
- TerminalPanel (logs and SSH)
- DetailManager (detail page display)

## Signal Flow
```
User Action → Action Button → Handler Method → Find ClusterView → Access Manager/Panel → Show UI/Execute Command
```

Example: View Logs
```
Click "View Logs" → _handle_view_logs() → Find ClusterView → terminal_panel.create_enhanced_logs_tab() → Show Terminal
```
