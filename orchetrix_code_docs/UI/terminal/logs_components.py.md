# logs_components.py - Brief Documentation

**Path**: `orchetrix/UI/terminal/logs_components.py`
**Lines**: ~350

## Purpose
Pod logs viewer component

## Features
- Real-time log streaming
- Search and filter logs
- Download logs to file
- Tail lines control (50, 100, 500, 1000, all)
- Auto-scroll toggle
- Timestamp display

## Main Methods
- `start_log_stream(pod, namespace, container)` - Start streaming
- `stop_log_stream()` - Stop streaming
- `download_logs()` - Save to file
- `search_logs(query)` - Search/filter

## Used By
TerminalPanel (logs tabs)
