# pin_storage.py - Brief Documentation

**Path**: `orchetrix/Utils/pin_storage.py`
**Lines**: ~100
**Purpose**: Store and manage pinned resources

## Key Features
- Persist pinned items to JSON file
- Load pinned items on startup
- Add/remove pins
- Organize by category

## Main Methods
- `add_pin(resource_type, name, namespace)` - Add pinned resource
- `remove_pin(resource_type, name, namespace)` - Remove pin
- `get_pins()` - Get all pinned resources
- `save()` - Persist to disk
- `load()` - Load from disk

## Storage Format
```json
{
  "pins": [
    {"type": "pods", "name": "nginx-abc", "namespace": "default"},
    {"type": "services", "name": "api", "namespace": "prod"}
  ]
}
```

## Used By
- Sidebar (pinned resources section)
- Resource pages (pin/unpin actions)
