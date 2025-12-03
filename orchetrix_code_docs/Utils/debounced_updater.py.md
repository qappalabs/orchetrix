# debounced_updater.py - Brief Documentation

**Path**: `orchetrix/Utils/debounced_updater.py`
**Lines**: ~100
**Purpose**: Debounce rapid UI updates to prevent flicker

## Key Features
- Delay rapid updates
- Coalesce multiple updates
- Timer-based debouncing
- Configurable delay

## Main Class
```python
class DebouncedUpdater:
    def __init__(self, delay_ms=300):
        self.delay = delay_ms
    
    def schedule_update(self, callback):
        # Delays callback execution
        pass
```

## Used By
- BaseResourcePage (auto-refresh)
- Search functionality
- Live filtering

## Pattern
Debouncing pattern to improve UX
