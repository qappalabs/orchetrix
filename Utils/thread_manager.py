import gc
import logging
import threading
import time
import weakref
from typing import Dict, List, Optional

from PyQt6.QtCore import QMetaObject, QObject, Qt, QThreadPool, QTimer, pyqtSlot
from PyQt6.QtWidgets import QApplication

# Common stop event for cooperative shutdown
_global_stop_event = threading.Event()

def is_shutdown_requested():
    """Check if application shutdown has been requested"""
    return _global_stop_event.is_set()

class _MainThreadTimerHelper(QObject):
    """Lives on the main thread and creates timers there directly."""
    def __init__(self, manager):
        super().__init__()
        self._manager_ref = weakref.ref(manager)

    @pyqtSlot()
    def _setup_timers_for_manager(self):
        mgr = self._manager_ref()
        if mgr is not None and not hasattr(mgr, 'cleanup_timer'):
            mgr.cleanup_timer = QTimer()
            mgr.cleanup_timer.timeout.connect(mgr._cleanup_expired_workers)
            mgr.cleanup_timer.start(30000)


class EnhancedThreadPoolManager(QObject):
    """Manages thread pools with cooperative shutdown and resource tracking."""
    
    def __init__(self, max_threads: int = 4):  # Reduced from 8 to 4 for better performance
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(max_threads)
        self.active_workers = {}
        self.worker_refs = weakref.WeakValueDictionary()
        self.lock = threading.RLock()
        self._shutdown = False

        # Setup timers with thread safety
        self._setup_timers()

    def _setup_timers(self):
        """Initialize and configure timers with thread safety"""
        if hasattr(self, 'cleanup_timer'):
            return

        app = QApplication.instance()
        if app and self.thread() != app.thread():
            logging.warning("ThreadManager timers being created from non-main thread - deferring to main thread")
            if not hasattr(self, '_timer_helper'):
                self._timer_helper = _MainThreadTimerHelper(self)
                self._timer_helper.moveToThread(app.thread())
            QMetaObject.invokeMethod(
                self._timer_helper,
                "_setup_timers_for_manager",
                Qt.ConnectionType.QueuedConnection
            )
            return

        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_expired_workers)
        self.cleanup_timer.start(30000)

    def _setup_timers_on_main_thread(self):
        """Setup timers on main thread - called via QMetaObject.invokeMethod"""
        self._setup_timers()

    def submit_worker(self, worker_id, worker, priority=0):
        if self._shutdown or is_shutdown_requested():
            return False

        with self.lock:
            # Cancel existing worker with same ID
            if worker_id in self.active_workers:
                old_worker = self.active_workers[worker_id]
                if hasattr(old_worker, 'cancel'):
                    old_worker.cancel()

            # Set up cleanup
            def cleanup():
                with self.lock:
                    self.active_workers.pop(worker_id, None)

            def on_finished(result):
                cleanup()

            def on_error(error):
                cleanup()

            def on_cancelled():
                cleanup()

            worker.signals.finished.connect(on_finished)
            worker.signals.error.connect(on_error)
            if hasattr(worker.signals, 'cancelled'):
                worker.signals.cancelled.connect(on_cancelled)

            self.active_workers[worker_id] = worker
            self.worker_refs[worker_id] = worker

            # Set priority and start
            worker.setAutoDelete(True)
            if hasattr(self.thread_pool, 'start'):
                if priority != 0:
                    self.thread_pool.start(worker, priority)
                else:
                    self.thread_pool.start(worker)

            return True

    def cancel_worker(self, worker_id):
        with self.lock:
            worker = self.active_workers.get(worker_id)
            if worker and hasattr(worker, 'cancel'):
                worker.cancel()

    def _cleanup_expired_workers(self):
        if self._shutdown or is_shutdown_requested():
            return

        with self.lock:
            current_time = time.time()
            expired_workers = []

            # More efficient cleanup - use timestamps dict for faster lookup
            for worker_id, worker in list(self.active_workers.items()):
                if hasattr(worker, '_start_time'):
                    # Dynamic timeout based on worker type
                    timeout = getattr(worker, '_timeout', 120)  # Default 2 minutes
                    if current_time - worker._start_time > timeout:
                        expired_workers.append(worker_id)
                        if hasattr(worker, 'cancel'):
                            worker.cancel()

            # Batch cleanup to reduce lock contention
            if expired_workers:
                for worker_id in expired_workers:
                    self.active_workers.pop(worker_id, None)
                    self.worker_refs.pop(worker_id, None)
                logging.info(f"Cleaned up {len(expired_workers)} expired workers: {expired_workers}")

    def shutdown(self):
        self._shutdown = True
        _global_stop_event.set()

        if hasattr(self, 'cleanup_timer'):
            self.cleanup_timer.stop()

        with self.lock:
            # Cancel all workers
            for worker in list(self.active_workers.values()):
                if hasattr(worker, 'cancel'):
                    try:
                        worker.cancel()
                    except Exception as e:
                        logging.debug(f"Error canceling worker during shutdown: {e}")

            # Fast shutdown approach - reduced timeout for quicker app closing
            if not self.thread_pool.waitForDone(2000):  # Reduced from 3s to 2s
                logging.warning("Thread pool did not shut down gracefully within 2 seconds")
                # Force termination of remaining threads immediately
                self._force_thread_termination()

            self.active_workers.clear()
            self.worker_refs.clear()

    def _force_thread_termination(self):
        """Cooperative termination of remaining threads as last resort"""
        try:
            # First, try to interrupt all running threads
            active_thread_count = self.thread_pool.activeThreadCount()
            if active_thread_count > 0:
                logging.warning(f"Attempting cooperative shutdown for {active_thread_count} active threads")

            # Signal cooperative shutdown
            _global_stop_event.set()

            # Clear the thread pool queue
            self.thread_pool.clear()

            # Iterate through all threads and attempt join
            import threading
            current = threading.current_thread()
            for thread in threading.enumerate():
                if thread != current:
                    # Target only our background threads to avoid interfering with external libs
                    if thread.name.startswith('Thread-') or not thread.daemon:
                        logging.info(f"Joining thread {thread.name} (daemon={thread.daemon})")
                        try:
                            thread.join(timeout=0.5)
                        except Exception as e:
                            logging.error(f"Error joining thread {thread.name}: {e}")

            # Force exit as last resort - but avoid thread._stop()
            gc.collect()  # Force garbage collection to clean up thread references

            logging.info("Forced thread pool clearing completed")
        except Exception as e:
            logging.error(f"Error during forced thread termination: {e}")


# Singleton with better management
_thread_manager_instance = None
_thread_manager_lock = threading.Lock()

def get_thread_manager():
    global _thread_manager_instance
    with _thread_manager_lock:
        if _thread_manager_instance is None:
            _thread_manager_instance = EnhancedThreadPoolManager()
        return _thread_manager_instance

def shutdown_thread_manager():
    global _thread_manager_instance
    with _thread_manager_lock:
        if _thread_manager_instance is not None:
            _thread_manager_instance.shutdown()
            _thread_manager_instance = None


__all__ = [
    "EnhancedThreadPoolManager",
    "get_thread_manager",
    "is_shutdown_requested",
    "shutdown_thread_manager",
]
