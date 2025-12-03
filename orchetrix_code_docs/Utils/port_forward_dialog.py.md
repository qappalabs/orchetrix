# port_forward_dialog.py - Brief Documentation

**Path**: `orchetrix/Utils/port_forward_dialog.py`
**Lines**: ~200
**Purpose**: Port forward configuration dialog UI

## Key Features
- Select pod and container
- Choose local port (8080-65535)
- Choose remote port
- Port validation
- Dialog UI with OK/Cancel

## UI Components
- Pod selector dropdown
- Container selector dropdown
- Local port input
- Remote port input
- Protocol selector (TCP/UDP)

## Returns
```python
{
    'pod_name': 'nginx-abc123',
    'container': 'nginx',
    'local_port': 8080,
    'remote_port': 80
}
```

## Used By
- PodsPage (port forward action)
- ServicesPage (port forward action)
- port_forward_manager
