"""
Centralized Error Handling and Resource Management Utility
Replaces scattered error handling with consistent patterns.
"""

import logging
import traceback
import threading
import gc
from datetime import datetime
from typing import Optional, Callable, Any, Dict, List
from functools import wraps
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import QTimer, QThread


class ErrorHandler:
    """Centralized error handler with consistent patterns"""
    
    def __init__(self):
        self._error_shown_recently = False
        self._error_lock = threading.RLock()
        self._last_error_time = 0
        self._error_cooldown = 2.0  # seconds between error dialogs
        self._recent_errors = {}  # Track recent error messages to prevent duplicates
        self._error_message_cooldown = 10.0  # seconds before showing same error again
        
    def handle_error(self, error: Exception, context: str = "", show_dialog: bool = True) -> None:
        """Handle errors with consistent logging and optional user notification"""
        error_message = str(error)
        
        # Log the error with full context
        logging.error(f"Error in {context}: {error_message}")
        logging.debug(f"Full traceback: {traceback.format_exc()}")
        
        # Show user dialog if requested and not recently shown
        if show_dialog and self._should_show_dialog(error_message):
            self._show_error_dialog(context, error_message)
    
    def _should_show_dialog(self, error_message: str) -> bool:
        """Check if we should show error dialog (with cooldown and duplicate prevention)"""
        import time
        with self._error_lock:
            current_time = time.time()
            
            # Check if this exact error message was shown recently
            error_hash = hash(error_message)
            if error_hash in self._recent_errors:
                last_shown = self._recent_errors[error_hash]
                if current_time - last_shown < self._error_message_cooldown:
                    logging.debug(f"Suppressing duplicate error dialog: {error_message[:50]}...")
                    return False
            
            # Check general cooldown
            if current_time - self._last_error_time > self._error_cooldown:
                self._last_error_time = current_time
                self._recent_errors[error_hash] = current_time
                
                # Clean up old entries
                old_entries = [k for k, v in self._recent_errors.items() 
                              if current_time - v > self._error_message_cooldown * 2]
                for k in old_entries:
                    del self._recent_errors[k]
                
                return True
            return False
    
    def _show_error_dialog(self, context: str, error_message: str) -> None:
        """Show enhanced error dialog with better UX"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            # Create custom styled message box
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Orchestrix - Error")
            
            # Format error message for better readability
            formatted_message = self._format_user_friendly_message(context, error_message)
            msg.setText(formatted_message)
            
            # Add helpful details section
            detailed_text = self._generate_helpful_details(context, error_message)
            if detailed_text:
                msg.setDetailedText(detailed_text)
            
            # Add action buttons
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Retry)
            msg.setDefaultButton(QMessageBox.StandardButton.Ok)
            
            # Style the dialog for better UX
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #f0f0f0;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QMessageBox QLabel {
                    font-size: 12px;
                    padding: 10px;
                }
                QMessageBox QPushButton {
                    min-width: 80px;
                    padding: 6px 12px;
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    border-radius: 3px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #106ebe;
                }
            """)
            
            # Auto-close after 15 seconds with countdown
            self._setup_auto_close_with_countdown(msg, 15)
            
            result = msg.exec()
            
            # Handle retry action
            if result == QMessageBox.StandardButton.Retry:
                self._handle_retry_action(context)
            
        except Exception as e:
            logging.error(f"Error showing enhanced error dialog: {e}")
    
    def _format_user_friendly_message(self, context: str, error_message: str) -> str:
        """Format error message to be more user-friendly"""
        # Clean up technical jargon
        user_message = error_message
        
        # Common error patterns and user-friendly alternatives
        friendly_patterns = {
            'connection refused': 'Unable to connect to Kubernetes cluster. Please check if the cluster is running.',
            'timeout': 'Connection timeout. The operation took too long to complete.',
            'permission denied': 'Access denied. Please check your authentication credentials.',
            'not found': 'Resource not found. It may have been deleted or moved.',
            'unauthorized': 'Authentication failed. Please verify your cluster credentials.',
            'certificate': 'SSL certificate issue. Please check your cluster configuration.',
            'dns': 'Network connectivity issue. Please check your internet connection.',
        }
        
        error_lower = error_message.lower()
        for pattern, friendly_msg in friendly_patterns.items():
            if pattern in error_lower:
                user_message = friendly_msg
                break
        
        return f"An error occurred while {context}:\n\n{user_message}"
    
    def _generate_helpful_details(self, context: str, error_message: str) -> str:
        """Generate helpful troubleshooting details"""
        details = []
        
        # Add timestamp
        details.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        details.append(f"Context: {context}")
        details.append(f"Original Error: {error_message}")
        
        # Add context-specific troubleshooting tips
        error_lower = error_message.lower()
        
        if 'connection' in error_lower or 'timeout' in error_lower:
            details.extend([
                "",
                "Troubleshooting Tips:",
                "• Check if Docker Desktop is running (for local clusters)",
                "• Verify your kubeconfig file is correct",
                "• Test network connectivity to your cluster",
                "• Try refreshing the connection"
            ])
        
        elif 'permission' in error_lower or 'unauthorized' in error_lower:
            details.extend([
                "",
                "Troubleshooting Tips:",
                "• Check your Kubernetes authentication credentials",
                "• Verify RBAC permissions for your user/service account", 
                "• Try re-authenticating to your cluster",
                "• Contact your cluster administrator if needed"
            ])
        
        elif 'certificate' in error_lower:
            details.extend([
                "",
                "Troubleshooting Tips:",
                "• Check if your cluster certificates are valid",
                "• Try updating your kubeconfig file",
                "• Verify cluster endpoint URL is correct",
                "• Contact your cluster administrator for certificate issues"
            ])
        
        return "\n".join(details)
    
    def _setup_auto_close_with_countdown(self, msg: QMessageBox, seconds: int):
        """Setup auto-close with countdown display"""
        original_title = msg.windowTitle()
        countdown = seconds
        
        def update_countdown():
            nonlocal countdown
            if countdown > 0:
                msg.setWindowTitle(f"{original_title} (Auto-close in {countdown}s)")
                countdown -= 1
                QTimer.singleShot(1000, update_countdown)
            else:
                # Use accept() instead of close() for exec'd dialogs
                msg.accept()
        
        QTimer.singleShot(1000, update_countdown)
    
    def _handle_retry_action(self, context: str):
        """Handle retry action from error dialog"""
        logging.info(f"User requested retry for {context}")
        # This could trigger a retry mechanism if implemented
        # For now, just log the retry request
    
    def format_connection_error(self, error: str, cluster_name: str = "") -> str:
        """Format connection errors for user display"""
        error_lower = error.lower()
        
        if "docker-desktop" in cluster_name.lower() and "refused" in error_lower:
            return "Docker Desktop Kubernetes is not running. Please start Docker Desktop and enable Kubernetes."
        elif "timeout" in error_lower:
            return f"Connection timeout. Check if cluster '{cluster_name}' is accessible."
        elif "certificate" in error_lower:
            return f"Certificate error. Check your kubeconfig for '{cluster_name}'."
        elif "authentication" in error_lower or "permission" in error_lower:
            return f"Authentication failed. Check your credentials for '{cluster_name}'."
        else:
            return f"Connection failed: {error[:100]}{'...' if len(error) > 100 else ''}"


def error_handler(context: str = "", show_dialog: bool = False):
    """Decorator for consistent error handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _global_error_handler.handle_error(
                    e, 
                    context or func.__name__, 
                    show_dialog
                )
                # Re-raise for critical errors
                if any(keyword in str(e).lower() for keyword in ['critical', 'fatal', 'import']):
                    raise
                return None
        return wrapper
    return decorator


class ResourceCleaner:
    """Utility for cleaning up application resources"""
    
    @staticmethod
    def cleanup_timers(timers: List[QTimer]) -> int:
        """Clean up QTimer objects safely"""
        stopped_count = 0
        for timer in timers:
            try:
                if timer and hasattr(timer, 'isActive') and timer.isActive():
                    timer.stop()
                    stopped_count += 1
            except RuntimeError as e:
                logging.debug(f"Timer cleanup RuntimeError (expected): {e}")
            except Exception as e:
                logging.error(f"Unexpected error stopping timer: {e}")
        
        logging.debug(f"Stopped {stopped_count} active timers")
        return stopped_count
    
    @staticmethod
    def cleanup_threads(threads: List[QThread]) -> int:
        """Clean up QThread objects safely"""
        cleaned_count = 0
        for thread in threads:
            try:
                if thread and thread.isRunning():
                    thread.quit()
                    if not thread.wait(2000):  # Wait up to 2 seconds
                        thread.terminate()
                        thread.wait(1000)  # Wait 1 more second for termination
                    cleaned_count += 1
            except RuntimeError as e:
                logging.debug(f"Thread cleanup RuntimeError (expected): {e}")
            except Exception as e:
                logging.error(f"Unexpected error cleaning thread: {e}")
        
        logging.debug(f"Cleaned up {cleaned_count} threads")
        return cleaned_count
    
    @staticmethod
    def force_garbage_collection() -> int:
        """Force garbage collection and return collected count"""
        try:
            collected = gc.collect()
            if collected > 0:
                logging.debug(f"Garbage collection: {collected} objects collected")
            return collected
        except Exception as e:
            logging.error(f"Error during garbage collection: {e}")
            return 0
    
    @staticmethod
    def cleanup_widgets(parent_widgets: List) -> int:
        """Clean up widget children safely"""
        cleaned_count = 0
        for parent in parent_widgets:
            if not parent:
                continue
            
            try:
                # Clean up timers
                timers = parent.findChildren(QTimer)
                cleaned_count += ResourceCleaner.cleanup_timers(timers)
                
                # Clean up threads  
                threads = parent.findChildren(QThread)
                cleaned_count += ResourceCleaner.cleanup_threads(threads)
                
            except RuntimeError as e:
                logging.debug(f"Widget cleanup RuntimeError (expected): {e}")
            except Exception as e:
                logging.error(f"Error cleaning widget {type(parent).__name__}: {e}")
        
        return cleaned_count


class ConnectionStateManager:
    """Thread-safe connection state management"""
    
    def __init__(self):
        self._states: Dict[str, str] = {}
        self._lock = threading.RLock()
    
    def set_state(self, cluster_name: str, state: str) -> None:
        """Set connection state thread-safely"""
        with self._lock:
            self._states[cluster_name] = state
            logging.debug(f"Connection state for {cluster_name}: {state}")
    
    def get_state(self, cluster_name: str) -> str:
        """Get connection state thread-safely"""
        with self._lock:
            return self._states.get(cluster_name, "disconnected")
    
    def remove_state(self, cluster_name: str) -> None:
        """Remove connection state thread-safely"""
        with self._lock:
            self._states.pop(cluster_name, None)
    
    def clear_all(self) -> None:
        """Clear all connection states"""
        with self._lock:
            self._states.clear()


# Global instances
_global_error_handler = ErrorHandler()
_global_connection_manager = ConnectionStateManager()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    return _global_error_handler


def get_connection_manager() -> ConnectionStateManager:
    """Get the global connection state manager"""
    return _global_connection_manager


def safe_execute(func: Callable, context: str = "", default_return: Any = None) -> Any:
    """Execute function with error handling, return default on error"""
    try:
        return func()
    except Exception as e:
        _global_error_handler.handle_error(e, context, show_dialog=False)
        return default_return


def log_performance(func: Callable) -> Callable:
    """Decorator to log function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            if execution_time > 100:  # Log if takes more than 100ms
                logging.debug(f"{func.__name__} took {execution_time:.1f}ms")
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logging.error(f"{func.__name__} failed after {execution_time:.1f}ms: {e}")
            raise
    return wrapper