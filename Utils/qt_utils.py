"""
Utility functions for safely interacting with Qt objects across the Python/C++ boundary.
"""

def is_valid(widget):
    """
    Check if a PyQt/PySide widget's C++ object still exists.
    
    This acts as a centralized validation gateway to prevent 
    'RuntimeError: wrapped C/C++ object has been deleted'.
    
    Args:
        widget: The Qt object wrapper to check
        
    Returns:
        bool: True if the underlying C++ object is alive and valid, False otherwise.
    """
    if widget is None:
        return False
    try:
        # Attempting to call any C++ method will trigger the internal binding registry check.
        # If the C++ object is destroyed, a RuntimeError is raised before segmentation fault.
        widget.parent()
        return True
    except Exception:
        # Any failure (deleted C++ object -> RuntimeError, non-Qt object -> AttributeError/
        # TypeError, etc.) means the widget is not safe to use. Honor the "False otherwise"
        # contract rather than letting the exception escape this safety gateway.
        return False
