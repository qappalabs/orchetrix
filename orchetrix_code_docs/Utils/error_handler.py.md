# error_handler.py - Brief Documentation

**Path**: `orchetrix/Utils/error_handler.py`
**Lines**: ~200
**Purpose**: Centralized error handling and user-friendly messages

## Key Functions
- `format_error(exception)` - Convert exception to user-friendly message
- `is_connection_error(exception)` - Detect connection issues
- `is_timeout_error(exception)` - Detect timeout errors
- `handle_api_error(api_exception)` - Handle Kubernetes API errors
- `log_error(error, context)` - Log with context

## Error Types
- Connection errors → "Cannot connect to cluster"
- Timeout errors → "Request timed out"
- 404 errors → "Resource not found"
- 403 errors → "Access denied"
- 500 errors → "Server error"

## Used By
- All API calls
- Resource loaders
- Service classes
