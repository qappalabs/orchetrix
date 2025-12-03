# performance_config.py - Brief Documentation

**Path**: `orchetrix/Utils/performance_config.py`
**Lines**: ~50
**Purpose**: Performance configuration constants

## Constants
```python
BATCH_SIZE = 100
MAX_TABLE_ROWS_BEFORE_VIRTUAL = 100
LARGE_DATASET_THRESHOLD = 200
THREAD_POOL_SIZE = 4
CACHE_TTL_SECONDS = 300
MAX_CONCURRENT_REQUESTS = 3
TIMEOUT_SECONDS = 30
```

## Used By
- unified_resource_loader
- thread_manager
- base_resource_page
- All performance-critical components
