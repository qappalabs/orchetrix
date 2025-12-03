# data_formatters.py - Brief Documentation

**Path**: `orchetrix/Utils/data_formatters.py`
**Lines**: ~150
**Purpose**: Data formatting utilities for display

## Key Functions
- `format_age(timestamp)` - Format as "2d", "3h", "5m", "30s"
- `format_memory(bytes)` - Format as "2.5Gi", "1024Mi", "512Ki"
- `format_cpu(millicores)` - Format as "500m", "2", "1.5"
- `format_timestamp(datetime)` - Format as ISO string
- `format_bytes(bytes)` - Human-readable bytes

## Examples
```python
format_age(datetime.now() - timedelta(hours=2))  # "2h"
format_memory(2684354560)  # "2.5Gi"
format_cpu(500)  # "500m"
```

## Used By
- All resource pages
- unified_resource_loader
- Detail sections
