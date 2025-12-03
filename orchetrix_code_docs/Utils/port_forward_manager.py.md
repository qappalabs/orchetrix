# port_forward_manager.py - Brief Documentation

**Path**: `orchetrix/Utils/port_forward_manager.py`
**Lines**: ~400
**Purpose**: Manage Kubernetes port forwarding
**Pattern**: Singleton

## Key Features
- Start port forward (pod → localhost)
- Stop active port forwards
- Track multiple forwards
- Auto-cleanup on application close
- Status monitoring

## Main Methods
- `start_port_forward(pod, namespace, local_port, remote_port, container)` - Start forward
- `stop_port_forward(forward_id)` - Stop specific forward
- `stop_all_forwards()` - Stop all active forwards
- `get_active_forwards()` - List active forwards
- `get_forward_status(forward_id)` - Check status

## Forward Data
```python
{
    'id': 'uuid',
    'pod': 'nginx-abc',
    'namespace': 'default',
    'local_port': 8080,
    'remote_port': 80,
    'status': 'active',
    'process': QProcess
}
```

## Used By
- PodsPage
- ServicesPage
- PortForwardingPage
