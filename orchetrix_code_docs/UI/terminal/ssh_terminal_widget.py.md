# ssh_terminal_widget.py - Brief Documentation

**Path**: `orchetrix/UI/terminal/ssh_terminal_widget.py`
**Lines**: ~400

## Purpose
SSH terminal widget for pod connections

## Features
- SSH into pod containers
- Interactive shell (bash/sh)
- PTY allocation
- Proper cleanup on disconnect

## Main Methods
- `connect_to_pod(pod, namespace, container)` - Establish connection
- `disconnect()` - Close connection
- `cleanup_ssh_session()` - Cleanup resources

## Used By
TerminalPanel (SSH tabs)
