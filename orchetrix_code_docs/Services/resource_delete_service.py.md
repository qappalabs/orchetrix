# resource_delete_service.py - Brief Documentation

**Path**: `orchetrix/Services/kubernetes/resource_delete_service.py`
**Lines**: ~150
**Purpose**: Handles resource deletion operations

## Key Features
- Single resource deletion
- Bulk deletion support
- Progress tracking
- Error handling
- Graceful deletion options

## Main Methods
- `delete_resource(type, name, namespace)` - Delete single resource
- `delete_resources(type, items)` - Bulk delete multiple resources
- `delete_with_options(type, name, namespace, grace_period)` - Delete with options

## Used By
- All resource pages (delete actions)
- resource_deleters.py workers
- Bulk delete operations

## Pattern
Service class integrated with KubernetesService
