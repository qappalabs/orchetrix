# events_service.py - Brief Documentation

**Path**: `orchetrix/Services/kubernetes/events_service.py`
**Lines**: ~200
**Purpose**: Manages Kubernetes events and cluster issues

## Key Features
- Fetch events for specific resources
- Aggregate cluster-wide issues  
- Filter warning/error events
- Event caching

## Main Methods
- `get_events_for_resource(type, name, namespace)` - Get events for a resource
- `get_cluster_issues(cluster_name)` - Get cluster-wide warnings/errors
- `filter_events_by_type(events, event_type)` - Filter by Normal/Warning

## Used By
- DetailPageComponent (Events tab)
- EventsPage
- Overview dashboard

## Pattern
Service class integrated with KubernetesService
