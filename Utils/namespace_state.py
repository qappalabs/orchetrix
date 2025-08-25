"""
Simple Namespace State Management
Manages namespace selection persistence across resource pages
"""

import threading


class NamespaceState:
    """Namespace state manager with per-page selection memory"""
    
    def __init__(self):
        self._page_selections = {}  # Track selections per page: {page_name: namespace}
        self._lock = threading.RLock()
        
    def get_namespace_for_page(self, page_name: str) -> str:
        """Get the namespace selection for a specific page"""
        with self._lock:
            return self._page_selections.get(page_name, None)
    
    def set_namespace_for_page(self, page_name: str, namespace: str):
        """Set the namespace selection for a specific page"""
        with self._lock:
            self._page_selections[page_name] = namespace
            
    def has_page_selection(self, page_name: str) -> bool:
        """Check if a page has had a user selection before"""
        with self._lock:
            return page_name in self._page_selections
            
    def reset_page_selection(self, page_name: str):
        """Reset selection for a specific page"""
        with self._lock:
            if page_name in self._page_selections:
                del self._page_selections[page_name]
                
    def reset_all_selections(self):
        """Reset all page selections (for testing/debugging)"""
        with self._lock:
            self._page_selections.clear()
            
    # Legacy methods for backward compatibility
    def get_current_namespace(self) -> str:
        """Legacy method - returns default"""
        return "default"
    
    def set_current_namespace(self, namespace: str):
        """Legacy method - does nothing"""
        pass
        
    def mark_user_selection(self, namespace: str):
        """Legacy method - does nothing"""
        pass
        
    def should_use_stored_selection(self) -> bool:
        """Legacy method - returns False"""
        return False


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