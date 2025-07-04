from PyQt6.QtCore import QObject, QThreadPool, QTimer
import threading
import weakref
import logging
import time

class EnhancedThreadPoolManager(QObject):
    def __init__(self, max_threads=8):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(max_threads)
        self.active_workers = {}
        self.worker_refs = weakref.WeakValueDictionary()
        self.lock = threading.RLock()
        self._shutdown = False
        
        # Cleanup timer for expired workers
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_expired_workers)
        self.cleanup_timer.start(5000)  # Cleanup every 5 seconds
        
    def submit_worker(self, worker_id, worker, priority=0):
        if self._shutdown:
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
        if self._shutdown:
            return
            
        with self.lock:
            expired_workers = []
            current_time = time.time()
            
            for worker_id, worker in list(self.active_workers.items()):
                if hasattr(worker, '_start_time'):
                    if current_time - worker._start_time > 60:  # 60 second timeout
                        expired_workers.append(worker_id)
                        if hasattr(worker, 'cancel'):
                            worker.cancel()
            
            for worker_id in expired_workers:
                self.active_workers.pop(worker_id, None)
                logging.warning(f"Cleaned up expired worker: {worker_id}")
    
    def get_active_count(self):
        with self.lock:
            return len(self.active_workers)
    
    def shutdown(self):
        self._shutdown = True
        self.cleanup_timer.stop()
        
        with self.lock:
            # Cancel all workers
            for worker in list(self.active_workers.values()):
                if hasattr(worker, 'cancel'):
                    worker.cancel()
            
            # Wait for completion
            self.thread_pool.waitForDone(3000)
            self.active_workers.clear()

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