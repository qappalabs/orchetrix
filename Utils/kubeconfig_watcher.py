"""
Kubeconfig File Watcher - Debounce-Validate-Reload Pattern
Combines QFileSystemWatcher responsiveness with mtime-based deduplication
to prevent signal storms from causing duplicate error dialogs.
"""

import os
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher, QTimer


class KubeconfigWatcher(QObject):
    """
    A hybrid file watcher that combines QFileSystemWatcher responsiveness
    with mtime-based validation from polling approaches.
    
    This implements the "Debounce-Validate-Reload" pattern:
    1. QFileSystemWatcher detects OS events immediately
    2. Events are coalesced via a debounce timer (200ms)
    3. After debounce, mtime is checked to filter duplicate signals
    4. Only genuine changes (new mtime) trigger the signal
    
    This eliminates the "signal storm" that causes stacked error dialogs.
    """
    
    # Emitted when kubeconfig file genuinely changes (after debounce + mtime validation)
    kubeconfig_changed = pyqtSignal()
    
    # Emitted with the path that changed (for debugging/logging)
    kubeconfig_path_changed = pyqtSignal(str)
    
    def __init__(self, debounce_ms: int = 300, parent=None):
        """
        Initialize the kubeconfig watcher.
        
        Args:
            debounce_ms: Milliseconds to wait before validating change.
                        300ms is optimal - fast enough to feel instant,
                        slow enough to coalesce write bursts.
            parent: Optional QObject parent.
        """
        super().__init__(parent)
        
        self._debounce_ms = debounce_ms
        self._watcher = QFileSystemWatcher(self)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._on_debounce_complete)
        
        self._kubeconfig_path = self._get_kubeconfig_path()
        self._is_watching = False
        
        # MTIME DEDUPLICATION STATE (The "Backup Code" Logic)
        self._last_mtime = 0.0  # Last known modification time
        self._pending_event = False  # Whether an event is pending validation
        
        # Connect file watcher signals
        self._watcher.fileChanged.connect(self._on_raw_event)
        self._watcher.directoryChanged.connect(self._on_directory_event)
        
        # Start watching if file exists
        self._start_watching()
    
    def _get_kubeconfig_path(self) -> str:
        """Get the kubeconfig path, respecting KUBECONFIG env var."""
        # Check KUBECONFIG environment variable first
        kubeconfig_env = os.environ.get('KUBECONFIG', '')
        
        if kubeconfig_env:
            # KUBECONFIG can contain multiple paths separated by : (Unix) or ; (Windows)
            separator = ';' if os.name == 'nt' else ':'
            paths = kubeconfig_env.split(separator)
            # Use the first path that exists
            for path in paths:
                path = path.strip()
                if path and os.path.exists(path):
                    return path
            # If none exist, use the first one (will be created later perhaps)
            if paths:
                return paths[0].strip()
        
        # Default to ~/.kube/config
        return os.path.expanduser("~/.kube/config")
    
    def _start_watching(self) -> bool:
        """Start watching the kubeconfig file and its parent directory."""
        if self._is_watching:
            return True
            
        if not os.path.exists(self._kubeconfig_path):
            logging.warning(f"Kubeconfig file not found at {self._kubeconfig_path}, cannot watch")
            return False
        
        # 1. Watch the file itself
        if self._watcher.addPath(self._kubeconfig_path):
            self._is_watching = True
            logging.info(f"Kubeconfig watcher started for: {self._kubeconfig_path}")
        else:
            logging.error(f"Failed to add kubeconfig to file watcher: {self._kubeconfig_path}")
            return False
        
        # 2. Watch parent directory for atomic write recovery
        # This ensures we detect file replacements (mv temp config)
        parent_dir = os.path.dirname(os.path.abspath(self._kubeconfig_path))
        if parent_dir and parent_dir not in self._watcher.directories():
            if self._watcher.addPath(parent_dir):
                logging.debug(f"Watching parent directory for atomic writes: {parent_dir}")
            else:
                logging.warning(f"Could not watch parent directory: {parent_dir}")
        
        # 3. Initialize mtime baseline
        try:
            self._last_mtime = os.path.getmtime(self._kubeconfig_path)
            logging.debug(f"Initial mtime baseline: {self._last_mtime}")
        except OSError as e:
            logging.warning(f"Could not get initial mtime: {e}")
            self._last_mtime = 0.0
        
        return True
    
    def _on_raw_event(self, path: str):
        """
        Handle raw file change event from QFileSystemWatcher.
        
        We do NOT process this immediately. We simply restart the debounce timer.
        This coalesces the burst of events (e.g., 5 signals from a single save)
        into one timer expiration.
        """
        logging.debug(f"Raw file event received: {path}")
        
        # Mark that we have a pending event
        self._pending_event = True
        
        # Restart debounce timer (this is the key to coalescing)
        self._debounce_timer.start()
    
    def _on_directory_event(self, path: str):
        """
        Handle directory change event.
        
        This catches atomic writes (file replaced via rename) which may cause
        QFileSystemWatcher to lose track of the file.
        """
        # Only care about the parent of our watched file
        parent_dir = os.path.dirname(os.path.abspath(self._kubeconfig_path))
        if path != parent_dir:
            return
        
        logging.debug(f"Directory event received (potential atomic write): {path}")
        
        # Mark pending and restart timer
        self._pending_event = True
        self._debounce_timer.start()
    
    def _on_debounce_complete(self):
        """
        Called when file system has been silent for debounce_ms.
        
        This is where we apply the "Backup Code" mtime validation logic.
        Only if the mtime has actually changed do we emit the signal.
        """
        if not self._pending_event:
            return
        
        self._pending_event = False
        path = self._kubeconfig_path
        
        # 1. EXISTENCE CHECK (Handle atomic write gap)
        if not os.path.exists(path):
            # File is missing - might be mid-rename during atomic write
            # Don't emit error, just wait for next event
            logging.debug(f"File missing during debounce check (atomic write in progress?): {path}")
            self._is_watching = False
            return
        
        try:
            # 2. MTIME DEDUPLICATION (The Core "Backup Code" Logic)
            current_mtime = os.path.getmtime(path)
            
            if current_mtime != self._last_mtime:
                # GENUINE CHANGE DETECTED - mtime is different
                logging.info(f"Kubeconfig change validated (mtime {self._last_mtime} -> {current_mtime})")
                self._last_mtime = current_mtime
                
                # 3. WATCH REPAIR (Critical for atomic writes)
                # If the file was replaced, QFileSystemWatcher might have dropped it
                if path not in self._watcher.files():
                    if self._watcher.addPath(path):
                        logging.debug(f"Re-added file to watcher after atomic write: {path}")
                    else:
                        logging.warning(f"Failed to re-add file to watcher: {path}")
                
                # 4. EMIT THE CLEAN, DEDUPLICATED SIGNAL
                self.kubeconfig_path_changed.emit(path)
                self.kubeconfig_changed.emit()
            else:
                # Same mtime - this is a duplicate signal, suppress it
                logging.debug(f"Suppressing duplicate signal (mtime unchanged: {current_mtime})")
                
                # Still ensure watcher is attached
                if path not in self._watcher.files():
                    self._watcher.addPath(path)
                    
        except OSError as e:
            # File might be locked or permission denied during write
            # Suppress error to avoid "Dialog Redirect" loop
            # Wait for next event when file is ready
            logging.debug(f"OSError during mtime check (file busy?): {e}")
    
    def stop(self):
        """Stop watching the kubeconfig file."""
        if self._debounce_timer.isActive():
            self._debounce_timer.stop()
        
        # Remove file watch
        if self._is_watching and self._kubeconfig_path in self._watcher.files():
            self._watcher.removePath(self._kubeconfig_path)
        
        # Remove directory watch
        parent_dir = os.path.dirname(os.path.abspath(self._kubeconfig_path))
        if parent_dir in self._watcher.directories():
            self._watcher.removePath(parent_dir)
        
        self._is_watching = False
        logging.info("Kubeconfig watcher stopped")
    
    def get_kubeconfig_path(self) -> str:
        """Get the path being watched."""
        return self._kubeconfig_path
    
    def is_watching(self) -> bool:
        """Check if the watcher is active."""
        return self._is_watching
    
    def force_check(self):
        """
        Force a kubeconfig change check.
        Useful for manual refresh or testing.
        
        Note: This bypasses mtime deduplication intentionally.
        """
        if os.path.exists(self._kubeconfig_path):
            try:
                self._last_mtime = os.path.getmtime(self._kubeconfig_path)
            except OSError:
                pass
            self.kubeconfig_path_changed.emit(self._kubeconfig_path)
            self.kubeconfig_changed.emit()


# Singleton instance
_kubeconfig_watcher_instance = None


def get_kubeconfig_watcher() -> KubeconfigWatcher:
    """Get or create the singleton KubeconfigWatcher instance."""
    global _kubeconfig_watcher_instance
    if _kubeconfig_watcher_instance is None:
        _kubeconfig_watcher_instance = KubeconfigWatcher()
    return _kubeconfig_watcher_instance


def cleanup_kubeconfig_watcher():
    """Cleanup the singleton instance (call on app shutdown)."""
    global _kubeconfig_watcher_instance
    if _kubeconfig_watcher_instance is not None:
        _kubeconfig_watcher_instance.stop()
        _kubeconfig_watcher_instance = None
        logging.info("Kubeconfig watcher cleaned up")
