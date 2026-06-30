import subprocess
import sys
from datetime import datetime

if sys.platform == 'win32':
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0


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
