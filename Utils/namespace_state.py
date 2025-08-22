"""
Simple Namespace State Management
Manages namespace selection persistence across resource pages
"""

import threading


class NamespaceState:
    """Simple namespace state manager for persistence across pages"""
    
    def __init__(self):
        self._current_namespace = "default"
        self._lock = threading.RLock()
        
    def get_current_namespace(self) -> str:
        """Get the currently selected namespace"""
        with self._lock:
            return self._current_namespace
    
    def set_current_namespace(self, namespace: str):
        """Set the current namespace"""
        with self._lock:
            self._current_namespace = namespace


# Global singleton instance
_namespace_state = None
_state_lock = threading.Lock()


def get_namespace_state() -> NamespaceState:
    """Get the global namespace state singleton"""
    global _namespace_state
    if _namespace_state is None:
        with _state_lock:
            if _namespace_state is None:
                _namespace_state = NamespaceState()
    return _namespace_state