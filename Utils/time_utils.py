import logging
import os
import platform
import threading
import time
from datetime import datetime, timezone as dt_timezone
from typing import Union
import zoneinfo

from PyQt6.QtCore import QObject, QSettings, pyqtSignal

__all__ = ["TimezoneManager"]

class TimezoneManager(QObject):
    """
    Singleton manager for handling application-wide timezone settings and time conversions.
    """
    timezone_changed = pyqtSignal(str)
    
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                # Re-check inside the lock: another thread may have created it
                # while we were waiting to acquire the lock.
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        # Construction is finalized solely by get_instance() under the lock.
        # This is only a defensive guard against direct instantiation; it must
        # not assign _instance (get_instance() owns that assignment).
        if TimezoneManager._instance is not None:
            raise RuntimeError("TimezoneManager is a singleton. Use get_instance() instead.")

        self.settings = QSettings("Orchetrix", "OX")
        self._current_tz_name = self.settings.value("timezone", "UTC")
        self._current_tz = self._load_tz(self._current_tz_name)
        
    def _load_tz(self, tz_name):
        try:
            return zoneinfo.ZoneInfo(tz_name)
        except Exception as e:
            logging.debug(f"Failed to load timezone {tz_name}: {e}. Falling back to UTC.")
            return dt_timezone.utc

    def get_current_timezone_name(self) -> str:
        return self._current_tz_name

    def set_timezone(self, tz_name: str):
        try:
            new_tz = zoneinfo.ZoneInfo(tz_name)
        except Exception as e:
            logging.error(f"Failed to set timezone {tz_name}: {e}")
            return False
            
        self._current_tz_name = tz_name
        self._current_tz = new_tz
        self.settings.setValue("timezone", tz_name)
        
        # For subprocesses and CLI tools that look at TZ
        if platform.system() in ("Linux", "Darwin"):
            os.environ["TZ"] = tz_name
            time.tzset()
            
        self.timezone_changed.emit(tz_name)
        logging.info(f"Timezone changed to {tz_name}")
        return True

    def get_now(self) -> datetime:
        """Get the current time in the user's selected timezone."""
        return datetime.now(self._current_tz)
        
    def format_time(self, timestamp_str: Union[str, datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Takes a Kubernetes UTC timestamp string, a unix timestamp string, or a
        datetime object and formats it to the user's selected timezone.
        """
        if not timestamp_str or timestamp_str == "Unknown":
            return "Unknown"
            
        try:
            if isinstance(timestamp_str, str):
                if 'T' in timestamp_str:
                    # Parse ISO 8601 UTC
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    # Try to parse as float unix timestamp
                    dt = datetime.fromtimestamp(float(timestamp_str), tz=dt_timezone.utc)
            else:
                 dt = timestamp_str
                 
            # Ensure it is timezone aware
            if dt.tzinfo is None:
                 dt = dt.replace(tzinfo=dt_timezone.utc)
                 
            # Convert to local timezone
            local_dt = dt.astimezone(self._current_tz)
            return local_dt.strftime(format_str)
            
        except Exception as e:
            logging.debug(f"TimezoneManager: Error formatting time for '{timestamp_str}': {e}")
            return str(timestamp_str)
