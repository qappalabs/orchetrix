# thread_manager.py Documentation

## File Information
- **Path**: `orchetrix/Utils/thread_manager.py`
- **Purpose**: **CRITICAL INFRASTRUCTURE** - Manages all background threads across the entire application
- **Lines**: 186
- **Pattern**: Singleton Thread Pool Manager

## Overview
EnhancedThreadPoolManager is the central thread management system for Orchetrix. Every background operation (resource loading, metrics polling, log streaming, etc.) goes through this manager. It handles worker lifecycle, cancellation, timeout monitoring, and graceful shutdown.

**Why Critical**: Without this, the application would freeze on every API call. This enables responsive UI.

---

## Architecture: Centralized Thread Management

```
Application Operations
   ↓
EnhancedThreadPoolManager (Singleton)
   ↓ Manages
QThreadPool (Max 4 threads)
   ↓ Executes
EnhancedBaseWorker instances
   ↓ Emits signals to
Main UI Thread
```

**Benefits**:
- ✅ **Single point of control** for all background operations
- ✅ **Thread limit** prevents overwhelming system
- ✅ **Automatic cleanup** of expired workers
- ✅ **Graceful shutdown** on app exit
- ✅ **Worker cancellation** support

---

## Class: EnhancedThreadPoolManager (extends QObject)

### Constructor

```python
def __init__(self, max_threads=4):
    super().__init__()
    self.thread_pool = QThreadPool()
    self.thread_pool.setMaxThreadCount(max_threads)
    self.active_workers = {}  # worker_id -> worker instance
    self.worker_refs = weakref.WeakValueDictionary()  # Weak references
    self.lock = threading.RLock()  # Thread-safe access
    self._shutdown = False
    
    self._setup_timers()
```

**Key Design Decisions**:
- **Max 4 threads** (reduced from 8): Better CPU utilization
- **RLock**: Reentrant lock allows same thread to acquire multiple times
- **WeakValueDictionary**: Workers can be garbage collected when done
- **_shutdown flag**: Prevents new operations during shutdown

---

### Timer Setup

```python
def _setup_timers(self):
    """Initialize and configure timers with thread safety"""
    from PyQt6.QtWidgets import QApplication
    if self.thread() != QApplication.instance().thread():
        logging.warning("ThreadManager timers being created from non-main thread - deferring to main thread")
        from PyQt6.QtCore import QMetaObject
        QMetaObject.invokeMethod(self, "_setup_timers_on_main_thread", Qt.ConnectionType.QueuedConnection)
        return
    
    # Cleanup timer for expired workers
    self.cleanup_timer = QTimer()
    self.cleanup_timer.timeout.connect(self._cleanup_expired_workers)
    self.cleanup_timer.start(30000)  # Every 30 seconds
```

**Thread Safety Pattern**:
1. Check if called from main thread
2. If not, defer to main thread using `QMetaObject.invokeMethod`
3. This ensures Qt objects (QTimer) are created on main thread

**Why 30 seconds**: Balance between responsiveness and overhead

---

## Core Methods

### `submit_worker()` - **MAIN SUBMISSION METHOD**

```python
def submit_worker(self, worker_id, worker, priority=0):
    if self._shutdown:
        return False
        
    with self.lock:
        # Cancel existing worker with same ID
        if worker_id in self.active_workers:
            old_worker = self.active_workers[worker_id]
            if hasattr(old_worker, 'cancel'):
                old_worker.cancel()
                
        # Set up cleanup handlers
        def cleanup():
            with self.lock:
                self.active_workers.pop(worker_id, None)
                
        def on_finished(result):
            cleanup()
            
        def on_error(error):
            cleanup()
            
        def on_cancelled():
            cleanup()
        
        # Connect signals
        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        if hasattr(worker.signals, 'cancelled'):
            worker.signals.cancelled.connect(on_cancelled)
        
        # Track worker
        self.active_workers[worker_id] = worker
        self.worker_refs[worker_id] = worker
        
        # Submit to thread pool
        worker.setAutoDelete(True)
        if priority != 0:
            self.thread_pool.start(worker, priority)
        else:
            self.thread_pool.start(worker)
        
        return True
```

**Flow**:
1. **Check shutdown state**: Don't accept new workers if shutting down
2. **Cancel existing worker**: Only one worker per ID
3. **Setup automatic cleanup**: Connect to all completion signals
4. **Track worker**: Add to both active_workers dict and weak refs
5. **Submit to pool**: With optional priority
6. **Auto-delete**: Worker deleted after execution completes

**Cleanup Pattern**:
- Worker removed from tracking when finished, error, or cancelled
- This prevents memory leaks

---

### `start_worker()` - Backward Compatibility

```python
def start_worker(self, worker, priority=0):
    """Start a worker - backward compatibility method"""
    worker_id = getattr(worker, 'worker_id', f"worker_{id(worker)}")
    return self.submit_worker(worker_id, worker, priority)
```

**Purpose**: Old code used `start_worker()`, new code uses `submit_worker()`

---

### `cancel_worker()` - Cancel Specific Worker

```python
def cancel_worker(self, worker_id):
    with self.lock:
        worker = self.active_workers.get(worker_id)
        if worker and hasattr(worker, 'cancel'):
            worker.cancel()
```

**Usage**:
```python
thread_manager = get_thread_manager()
operation_id = thread_manager.submit_worker("load_pods", pod_loader)
# Later, if user switches pages:
thread_manager.cancel_worker("load_pods")
```

---

## Automatic Cleanup System

### `_cleanup_expired_workers()` - Timeout Monitoring

```python
def _cleanup_expired_workers(self):
    if self._shutdown:
        return
        
    with self.lock:
        current_time = time.time()
        expired_workers = []
        
        # Find expired workers
        for worker_id, worker in list(self.active_workers.items()):
            if hasattr(worker, '_start_time'):
                timeout = getattr(worker, '_timeout', 120)  # Default 2 minutes
                if current_time - worker._start_time > timeout:
                    expired_workers.append(worker_id)
                    if hasattr(worker, 'cancel'):
                        worker.cancel()
        
        # Batch cleanup
        if expired_workers:
            for worker_id in expired_workers:
                self.active_workers.pop(worker_id, None)
                self.worker_refs.pop(worker_id, None)
            logging.info(f"Cleaned up {len(expired_workers)} expired workers: {expired_workers}")
```

**Timeout Detection**:
- Each worker has `_start_time` set when created
- Each worker can override `_timeout` (default 120s)
- Workers exceeding timeout are cancelled and removed

**Batch Cleanup**: Removes multiple workers at once for efficiency

---

## Graceful Shutdown

### `shutdown()` - Application Exit

```python
def shutdown(self):
    self._shutdown = True
    self.cleanup_timer.stop()
    
    with self.lock:
        # Cancel all workers
        for worker in list(self.active_workers.values()):
            if hasattr(worker, 'cancel'):
                worker.cancel()
        
        # Wait for thread pool to finish (3 seconds max)
        if not self.thread_pool.waitForDone(3000):
            logging.warning("Thread pool did not shut down gracefully within 3 seconds")
            self._force_thread_termination()
        
        self.active_workers.clear()
        self.worker_refs.clear()
```

**Shutdown Flow**:
1. Set shutdown flag (prevents new workers)
2. Stop cleanup timer
3. Cancel all active workers
4. Wait 3 seconds for clean shutdown
5. If still running, force termination
6. Clear all references

**Why 3 seconds**: Fast enough for user, long enough for most operations

---

### `_force_thread_termination()` - Last Resort

```python
def _force_thread_termination(self):
    """Force termination of remaining threads as last resort"""
    try:
        active_thread_count = self.thread_pool.activeThreadCount()
        if active_thread_count > 0:
            logging.warning(f"Force terminating {active_thread_count} active threads")
        
        # Clear the thread pool queue
        self.thread_pool.clear()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        logging.info("Forced thread pool clearing completed")
    except Exception as e:
        logging.error(f"Error during forced thread termination: {e}")
        # Last resort - kill threads directly
        try:
            import threading
            for thread in threading.enumerate():
                if thread != threading.current_thread() and thread.name.startswith('Thread-'):
                    logging.warning(f"Force stopping thread: {thread.name}")
                    thread._stop()  # Dangerous but necessary
        except:
            pass
```

**Escalation Levels**:
1. Clear thread pool queue
2. Force garbage collection
3. If still running, call `thread._stop()` (dangerous)

**Dangerous Operation**: `thread._stop()` is not safe but needed for clean app exit

---

## Singleton Pattern

```python
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
```

**Thread-Safe Singleton**:
- Lock protects instance creation
- Only one manager exists across entire application
- Shutdown sets instance to None (allows recreation if needed)

---

## Usage Examples

### Submit Worker

```python
from Utils.thread_manager import get_thread_manager
from Utils.enhanced_worker import EnhancedBaseWorker

class LoadPodsWorker(EnhancedBaseWorker):
    def __init__(self):
        super().__init__("load_pods_worker")
    
    def execute(self):
        # Load pods from Kubernetes API
        return pods_list

# Submit worker
thread_manager = get_thread_manager()
worker = LoadPodsWorker()
worker.signals.finished.connect(self.handle_pods_loaded)
thread_manager.submit_worker("load_pods", worker)
```

### Cancel Worker

```python
# User switched pages, cancel loading
thread_manager = get_thread_manager()
thread_manager.cancel_worker("load_pods")
```

### Get Active Count

```python
thread_manager = get_thread_manager()
active_count = thread_manager.get_active_count()
print(f"{active_count} workers currently running")
```

### Application Shutdown

```python
# In main.py or app close handler
from Utils.thread_manager import shutdown_thread_manager

shutdown_thread_manager()
```

---

## Key Features

1. ✅ **Thread Limiting**: Max 4 concurrent threads prevents CPU overload
2. ✅ **Automatic Cleanup**: Expired workers removed every 30 seconds
3. ✅ **Worker Cancellation**: Cancel operations when no longer needed
4. ✅ **Graceful Shutdown**: 3-second timeout with force termination fallback
5. ✅ **Thread Safety**: RLock protects all operations
6. ✅ **Weak References**: Workers can be garbage collected
7. ✅ **Priority Support**: High-priority workers executed first
8. ✅ **Singleton Pattern**: One manager for entire application

---

## Performance Characteristics

**Thread Count**: 4 (optimal for most systems)
- Too few: Operations queue up
- Too many: CPU thrashing

**Cleanup Interval**: 30 seconds
- Frequent enough to prevent leaks
- Infrequent enough to avoid overhead

**Shutdown Timeout**: 3 seconds
- Fast app closing
- Allows most operations to complete

---

## Dependencies

- PyQt6.QtCore (QObject, QThreadPool, QTimer)
- threading (RLock, Lock)
- weakref (WeakValueDictionary)
- logging (error tracking)
- time (timeout calculation)

## Used By

- **Every resource loader** (pods, deployments, services, etc.)
- **Metrics service** (polling metrics)
- **Events service** (polling events)
- **Log service** (streaming logs)
- **Port forwarding** (establishing connections)
- **Delete operations** (background deletion)

**Total**: 50+ different operations across the application

---

## Critical for Application Health

Without EnhancedThreadPoolManager:
- ❌ UI freezes on every API call
- ❌ No way to cancel operations
- ❌ Memory leaks from lingering threads
- ❌ Application hangs on exit
- ❌ CPU overload from unlimited threads

With EnhancedThreadPoolManager:
- ✅ Responsive UI at all times
- ✅ Cancellable operations
- ✅ Automatic cleanup
- ✅ Clean application shutdown
- ✅ Controlled resource usage

---

## Design Patterns Used

1. **Singleton Pattern**: One manager instance
2. **Thread Pool Pattern**: Fixed number of reusable threads
3. **Observer Pattern**: Signal/slot for completion notification
4. **Resource Acquisition Is Initialization (RAII)**: Auto-cleanup on completion
5. **Timeout Pattern**: Automatic expiration of long-running operations

---

## Total Lines**: 186 lines of critical infrastructure code managing thousands of background operations across 50+ resource types.
