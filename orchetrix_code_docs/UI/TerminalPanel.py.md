# TerminalPanel.py Documentation

## File Information
- **Path**: `orchetrix/UI/TerminalPanel.py`
- **Purpose**: **TERMINAL MANAGER** - Manages bottom terminal panel with multiple tabs for shells, logs, and SSH
- **Lines**: ~1,000+
- **Pattern**: Multi-tab Terminal + Process Management + Animation

## Overview
TerminalPanel is the bottom panel providing interactive terminals, pod log viewers, and SSH sessions. It supports multiple tabs, different shell types (bash, zsh, PowerShell), slide-up/down animation, and resize functionality.

---

## Key Features

1. ✅ **Multiple Terminal Types**: Regular shell, SSH sessions, log viewers
2. ✅ **Tab Management**: Add/close/switch between terminal tabs
3. ✅ **Shell Selection**: bash, zsh, fish, PowerShell
4. ✅ **Slide Animation**: Smooth slide-up/down from bottom
5. ✅ **Resizable**: Drag top edge to resize height
6. ✅ **Pod Logs**: Stream logs from Kubernetes pods
7. ✅ **SSH into Pods**: Interactive SSH session into pod containers
8. ✅ **Process Management**: Proper cleanup on close

---

## Constructor

```python
def __init__(self, parent, working_directory=""):
    super().__init__(parent)
    self.parent_window = parent
    self.active_terminal_index = 0
    self.is_visible = False
    self.terminal_tabs = []
    self.working_directory = working_directory
    self.normal_height = 300
    
    self.setup_ui()
    self.add_terminal_tab()
```

---

## UI Structure

```
TerminalPanel (height: 300px, resizable)
├── UnifiedTerminalHeader
│   ├── Tab buttons (Terminal 1, Terminal 2, Logs, SSH)
│   ├── Shell selector (bash, zsh, PowerShell)
│   ├── Add tab button (+)
│   ├── Clear/Restart buttons
│   └── Minimize/Maximize/Close buttons
├── Resize Handle (top edge, 5px)
└── Terminal Stack (QWidget)
    ├── Terminal Tab 1 (UnifiedTerminalWidget + QProcess)
    ├── Terminal Tab 2 (UnifiedTerminalWidget + QProcess)
    ├── Logs Tab (EnhancedLogsViewer)
    └── SSH Tab (SSHTerminalWidget)
```

---

## Terminal Types

### 1. Regular Terminal (UnifiedTerminalWidget)

```python
def add_terminal_tab(self, shell=None):
    """Add new terminal tab with shell"""
    terminal_widget = UnifiedTerminalWidget()
    process = QProcess(self)
    
    # Connect signals
    process.readyReadStandardOutput.connect(lambda: self.handle_stdout(tab_index))
    terminal_widget.commandEntered.connect(lambda cmd: self.execute_command(cmd, tab_index))
    
    # Start shell process
    process.start(shell)  # bash, zsh, etc.
```

**Features**:
- Interactive shell (bash, zsh, PowerShell)
- Command history (up/down arrows)
- Output coloring
- Clear/exit commands

---

### 2. Pod Logs Viewer (EnhancedLogsViewer)

```python
def show_logs(self, pod_name: str, namespace: str, container: str = None):
    """Show logs for a pod"""
    logs_viewer = EnhancedLogsViewer(self.kubernetes_client)
    
    # Start streaming logs
    logs_viewer.start_log_stream(pod_name, namespace, container)
    
    # Add as new tab
    tab_data = {
        'logs_viewer': logs_viewer,
        'is_logs_tab': True,
        'tab_button': tab_btn
    }
    self.terminal_tabs.append(tab_data)
```

**Features**:
- Real-time log streaming
- Auto-scroll
- Search/filter
- Download logs
- Tail lines control

---

### 3. SSH Terminal (SSHTerminalWidget)

```python
def ssh_into_pod(self, pod_name: str, namespace: str, container: str = None):
    """SSH into pod container"""
    ssh_terminal = SSHTerminalWidget(self.kubernetes_client)
    
    # Connect to pod
    ssh_terminal.connect_to_pod(pod_name, namespace, container)
    
    # Add as new tab
    tab_data = {
        'terminal_widget': ssh_terminal,
        'is_ssh_tab': True,
        'tab_button': tab_btn
    }
    self.terminal_tabs.append(tab_data)
```

**Features**:
- Interactive shell in pod
- Execute commands in container
- Full terminal emulation
- Proper cleanup on disconnect

---

## Main Methods

### `add_terminal_tab()` - Add New Terminal

```python
def add_terminal_tab(self, shell=None):
    """Add new terminal tab"""
    # Create terminal widget
    terminal_widget = UnifiedTerminalWidget()
    terminal_widget.set_copy_paste_enabled(self.copy_paste_enabled)
    
    # Create process
    process = QProcess(self)
    process.setWorkingDirectory(self.working_directory)
    
    # Connect signals
    process.readyReadStandardOutput.connect(lambda: self.handle_stdout(tab_index))
    terminal_widget.commandEntered.connect(lambda cmd: self.execute_command(cmd, tab_index))
    
    # Add to tabs
    self.terminal_tabs.append({
        'terminal_widget': terminal_widget,
        'process': process,
        'shell': shell,
        'tab_button': tab_btn
    })
    
    # Start process
    process.start(shell)
```

---

### `execute_command()` - Execute Shell Command

```python
def execute_command(self, command, tab_index=None):
    """Execute command in terminal"""
    terminal_data = self.terminal_tabs[tab_index]
    process = terminal_data['process']
    
    # Handle special commands
    if command == "clear":
        terminal_widget.clear_output()
        return
    
    if command in ["exit", "quit"]:
        self.close_terminal_tab(tab_index)
        return
    
    # Send to process
    if process.state() == QProcess.ProcessState.Running:
        process.write((command + "\n").encode())
```

**Special Commands**:
- `clear` - Clears terminal output
- `exit`/`quit` - Closes terminal tab

---

### `switch_to_terminal_tab()` - Switch Tab

```python
def switch_to_terminal_tab(self, tab_index):
    """Switch to specified terminal tab"""
    # Hide all tabs
    for i, tab_data in enumerate(self.terminal_tabs):
        is_selected = (i == tab_index)
        tab_data['content_widget'].setVisible(is_selected)
        tab_data['tab_button'].setChecked(is_selected)
    
    # Update active index
    self.active_terminal_index = tab_index
    
    # Start process if not started
    if not terminal_data['started']:
        self.start_terminal_process(tab_index)
```

---

### `close_terminal_tab()` - Close Tab

```python
def close_terminal_tab(self, tab_index):
    """Close terminal tab and cleanup"""
    terminal_data = self.terminal_tabs[tab_index]
    
    # Cleanup based on tab type
    if terminal_data.get('is_logs_tab'):
        # Stop log streaming
        logs_viewer = terminal_data['logs_viewer']
        logs_viewer.stop_log_stream()
    elif terminal_data.get('is_ssh_tab'):
        # Cleanup SSH session
        ssh_terminal = terminal_data['terminal_widget']
        ssh_terminal.cleanup_ssh_session()
    else:
        # Terminate process
        process = terminal_data['process']
        if process.state() == QProcess.ProcessState.Running:
            process.write(b"exit\n")
            process.waitForFinished(500)
            process.terminate()
    
    # Remove from tabs
    self.terminal_tabs.pop(tab_index)
    self.renumber_tabs()
```

---

## Process Management

### Starting Processes

```python
def start_terminal_process(self, tab_index):
    """Start shell process for terminal"""
    terminal_data = self.terminal_tabs[tab_index]
    process = terminal_data['process']
    shell = terminal_data['shell']
    
    # Set working directory
    process.setWorkingDirectory(self.working_directory)
    
    # Start shell
    process.start(shell)
    
    if process.waitForStarted(1000):
        terminal_data['started'] = True
        print(f"Started {shell} in {self.working_directory}")
```

---

### Terminating Processes

```python
def terminate_all_processes(self):
    """Cleanup all processes on close"""
    for terminal_data in self.terminal_tabs:
        process = terminal_data.get('process')
        if process and process.state() == QProcess.ProcessState.Running:
            # Try graceful exit
            process.write(b"exit\n")
            process.waitForFinished(500)
            
            # Force terminate if still running
            if process.state() == QProcess.ProcessState.Running:
                process.terminate()
                process.waitForFinished(500)
            
            # Force kill if still running
            if process.state() == QProcess.ProcessState.Running:
                process.kill()
```

**Cleanup Order**:
1. Send "exit" command (graceful)
2. Terminate process (SIGTERM)
3. Kill process (SIGKILL)

---

## Animation

### Show Terminal

```python
def show_terminal(self):
    """Slide up from bottom"""
    # Animate from bottom to visible position
    start_y = self.parent_window.height()
    end_y = self.parent_window.height() - self.height()
    
    self.animation.setStartValue(QPoint(0, start_y))
    self.animation.setEndValue(QPoint(0, end_y))
    
    self.show()
    self.animation.start()
```

---

### Hide Terminal

```python
def hide_terminal(self):
    """Slide down to bottom"""
    # Animate from visible to bottom
    start_y = self.y()
    end_y = self.parent_window.height()
    
    self.animation.setStartValue(QPoint(0, start_y))
    self.animation.setEndValue(QPoint(0, end_y))
    
    self.animation.start()
    self.animation.finished.connect(self.hide)
```

---

## Resize Functionality

```python
def eventFilter(self, obj, event):
    """Handle resize events on top edge"""
    if obj == self.unified_header.resize_handle:
        if event.type() == QEvent.Type.MouseMove:
            # Resize panel height
            delta = event.globalPosition().y() - self.resize_start_y
            new_height = max(200, min(800, self.resize_start_height - delta))
            self.setFixedHeight(new_height)
            return True
    
    return super().eventFilter(obj, event)
```

**User can drag top edge** to resize height (200px - 800px)

---

## Preferences Integration

```python
def set_preferences(self, preferences):
    """Connect to preferences for font/copy-paste settings"""
    self.preferences = preferences
    self.preferences.copy_paste_changed.connect(self.apply_copy_paste_to_terminals)
    self.preferences.font_changed.connect(self.apply_font_to_terminals)
    self.preferences.font_size_changed.connect(self.apply_font_size_to_terminals)
```

**Syncs with global preferences**:
- Font family (Courier New, Consolas, Monaco)
- Font size (10-20px)
- Copy/paste enable/disable

---

## Usage Examples

### Show Pod Logs

```python
# From PodsPage
terminal_panel = self.parent_window.terminal_panel
terminal_panel.show_logs("nginx-abc123", "default", "nginx")
terminal_panel.show_terminal()
```

---

### SSH into Pod

```python
# From PodsPage context menu
terminal_panel = self.parent_window.terminal_panel
terminal_panel.ssh_into_pod("nginx-abc123", "default", "nginx")
terminal_panel.show_terminal()
```

---

### Add New Terminal

```python
# User clicks + button
terminal_panel.add_terminal_tab(shell="zsh")
```

---

## Key Features Summary

1. ✅ **Multi-tab**: Multiple terminals, logs, SSH in same panel
2. ✅ **Shell Types**: bash, zsh, fish, PowerShell support
3. ✅ **Process Management**: Proper cleanup and lifecycle
4. ✅ **Animations**: Smooth slide-up/down
5. ✅ **Resizable**: Drag to resize height
6. ✅ **Logs Streaming**: Real-time pod logs
7. ✅ **SSH Sessions**: Interactive shell in pods
8. ✅ **Preferences**: Font and copy-paste settings

---

## Dependencies

- UI/terminal/terminal_widget.py - Terminal widget
- UI/terminal/ssh_terminal_widget.py - SSH terminal
- UI/terminal/logs_components.py - Logs viewer
- UI/terminal/terminal_components.py - Header components
- Utils/kubernetes_client.py - Kubernetes API

---

## Total Lines**: ~1,000+ lines managing multi-tab terminal panel with shells, logs, and SSH support.
