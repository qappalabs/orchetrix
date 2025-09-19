"""
Debounced Update Manager with Throttling - Prevents excessive UI updates and API calls
"""

from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from typing import Dict, Callable, Any
from collections import deque
import logging
import time

class DebouncedUpdater(QObject):
    """Manages debounced updates and throttling to prevent UI flooding and API overload"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._timers = {}  # Dict of update_key -> QTimer
        self._pending_updates = {}  # Dict of update_key -> (callback, args)
        self._default_delay = 200  # Default delay in milliseconds
        
        # Throttling for API calls
        self._call_history = {}  # Dict of throttle_key -> deque of timestamps
        self._throttle_limits = {  # Default throttle limits
            'kubernetes_api': {'max_calls': 30, 'window': 10.0},
            'ui_refresh': {'max_calls': 10, 'window': 1.0},
            'search': {'max_calls': 5, 'window': 2.0},
            'metrics': {'max_calls': 20, 'window': 5.0}
        }
        
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
    
    def flush_update(self, update_key: str):
        """Immediately execute a scheduled update"""
        if update_key in self._timers:
            self._timers[update_key].stop()
            self._execute_update(update_key)
    
    def flush_all_updates(self):
        """Immediately execute all scheduled updates"""
        for update_key in list(self._pending_updates.keys()):
            self.flush_update(update_key)
    
    def is_throttled(self, throttle_key: str) -> bool:
        """Check if a call should be throttled based on recent history"""
        if throttle_key not in self._throttle_limits:
            return False  # No throttling if not configured
            
        now = time.time()
        limit_config = self._throttle_limits[throttle_key]
        max_calls = limit_config['max_calls']
        window = limit_config['window']
        
        # Initialize history if needed
        if throttle_key not in self._call_history:
            self._call_history[throttle_key] = deque()
            
        call_times = self._call_history[throttle_key]
        
        # Remove old calls outside the window
        while call_times and now - call_times[0] > window:
            call_times.popleft()
            
        # Check if we're at the limit
        if len(call_times) >= max_calls:
            logging.debug(f"Throttling {throttle_key}: {len(call_times)}/{max_calls} calls in {window}s")
            return True
            
        # Record this call
        call_times.append(now)
        return False
        
    def set_throttle_limit(self, throttle_key: str, max_calls: int, window_seconds: float):
        """Set custom throttle limit for a specific key"""
        self._throttle_limits[throttle_key] = {
            'max_calls': max_calls,
            'window': window_seconds
        }
        logging.info(f"Set throttle limit for {throttle_key}: {max_calls} calls per {window_seconds}s")
        
    def clear_throttle_history(self, throttle_key: str = None):
        """Clear throttle history for a key or all keys"""
        if throttle_key:
            if throttle_key in self._call_history:
                self._call_history[throttle_key].clear()
        else:
            self._call_history.clear()
            
    def schedule_throttled_update(self, update_key: str, throttle_key: str, callback: Callable,
                                delay_ms: int = None, *args, **kwargs):
        """Schedule an update with both throttling and debouncing"""
        if self.is_throttled(throttle_key):
            logging.debug(f"Skipping throttled update: {update_key}")
            return False
            
        self.schedule_update(update_key, callback, delay_ms, *args, **kwargs)
        return True
        
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

def cleanup_debounced_updater():
    """Clean up the global debounced updater"""
    global _debounced_updater
    if _debounced_updater is not None:
        _debounced_updater.cleanup()
        _debounced_updater = None