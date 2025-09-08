import time
from datetime import datetime

def get_timestamp_with_ms():
    """Get timestamp with milliseconds that works cross-platform (Windows/Linux)"""
    now = datetime.now()
    ms = int(now.microsecond / 1000)
    return f"{now.strftime('%H:%M:%S')}.{ms:03d}"

def get_full_timestamp_with_ms():
    """Get full timestamp with milliseconds that works cross-platform"""
    now = datetime.now()
    ms = int(now.microsecond / 1000)
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')}.{ms:03d}"