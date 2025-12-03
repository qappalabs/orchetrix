# log_handler.py - Brief Documentation

**Path**: `orchetrix/log_handler.py`
**Lines**: ~50

## Purpose
Custom logging handler for application logs

## Features
- File logging to `logs/orchetrix.log`
- Console logging
- Log rotation (10MB max, 5 backups)
- Configurable log levels
- Timestamp formatting

## Configuration
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler, console_handler]
)
```

## Used By
All modules via `logging.info()`, `logging.error()`, etc.
