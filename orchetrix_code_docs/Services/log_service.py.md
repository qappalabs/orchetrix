# log_service.py - Brief Documentation

**Path**: `orchetrix/Services/kubernetes/log_service.py`
**Lines**: ~300
**Purpose**: Manages pod log streaming and retrieval

## Key Features
- Stream real-time pod logs
- Fetch historical logs
- Multi-container support
- Tail lines configuration
- Follow mode

## Main Methods
- `get_pod_logs(pod_name, namespace, container, tail_lines)` - Get logs
- `start_log_stream(pod_name, namespace, container)` - Stream logs
- `stop_log_stream(pod_name, namespace, container)` - Stop streaming
- `stop_all_streams()` - Stop all active streams

## Used By
- TerminalPanel (logs viewer)
- PodsPage (view logs action)

## Pattern
Service class with background streaming workers
