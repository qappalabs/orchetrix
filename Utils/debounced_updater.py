"""
Debounced Update Manager with Throttling - Prevents excessive UI updates and API calls
"""

from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from typing import Dict, Callable, Any
import logging

class DebouncedUpdater(QObject):
    """Manages debounced updates and throttling to prevent UI flooding and API overload"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._timers = {}  # Dict of update_key -> QTimer
        self._pending_updates = {}  # Dict of update_key -> (callback, args)
        self._default_delay = 200  # Default delay in milliseconds
        self._call_history = {}  # For compatibility with clear_throttle_history()
        
    def schedule_update(self, update_key: str, callback: Callable, 
                       delay_ms: int = None, *args, **kwargs):
        """Schedule an update with debouncing"""
        if delay_ms is None:
            delay_ms = self._default_delay
            
        # Cancel existing timer if any
        if update_key in self._timers:
            self._timers[update_key].stop()
        else:
            # Create new timer
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._execute_update(update_key))
            self._timers[update_key] = timer
        
        # Store the update details
        self._pending_updates[update_key] = (callback, args, kwargs)
        
        # Start the timer
        self._timers[update_key].start(delay_ms)
        
        logging.debug(f"Scheduled debounced update: {update_key} (delay: {delay_ms}ms)")
    
    def _execute_update(self, update_key: str):
        """Execute the pending update"""
        if update_key in self._pending_updates:
            callback, args, kwargs = self._pending_updates[update_key]
            
            try:
                callback(*args, **kwargs)
                logging.debug(f"Executed debounced update: {update_key}")
            except Exception as e:
                logging.error(f"Error executing debounced update {update_key}: {e}")
            finally:
                # Clean up
                self._pending_updates.pop(update_key, None)
    
    def cancel_update(self, update_key: str):
        """Cancel a scheduled update"""
        if update_key in self._timers:
            self._timers[update_key].stop()
            self._pending_updates.pop(update_key, None)
            logging.debug(f"Cancelled debounced update: {update_key}")

    def clear_throttle_history(self, throttle_key: str = None):
        """Clear throttle history for a key or all keys"""
        if throttle_key:
            if throttle_key in self._call_history:
                self._call_history[throttle_key].clear()
        else:
            self._call_history.clear()

    def cleanup(self):
        """Clean up all timers and pending updates"""
        for timer in self._timers.values():
            if timer.isActive():
                timer.stop()
        
        self._timers.clear()
        self._pending_updates.clear()
        self._call_history.clear()

# Global debounced updater instance
_debounced_updater = None

def get_debounced_updater() -> DebouncedUpdater:
    """Get the global debounced updater instance"""
    global _debounced_updater
    if _debounced_updater is None:
        _debounced_updater = DebouncedUpdater()
    return _debounced_updater