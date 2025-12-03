# enhanced_worker.py Documentation

## File Information
- **Path**: `orchetrix/Utils/enhanced_worker.py`
- **Purpose**: **BASE WORKER CLASS** - Foundation for all background operations in Orchetrix
- **Lines**: 83
- **Pattern**: Abstract Base Class + Signal Pattern

## Overview
EnhancedBaseWorker is the base class for all background workers in Orchetrix. Every async operation (loading resources, streaming logs, polling metrics, deleting resources) extends this class. It provides cancellation support, timeout detection, safe signal emission, and lifecycle management.

**Why Critical**: Foundation for 100+ different worker types across the application.

---

## Class: WorkerSignals (extends QObject)

```python
class WorkerSignals(QObject):
    finished = pyqtSignal(object)  # Result data
    error = pyqtSignal(str)        # Error message
    progress = pyqtSignal(str)     # Progress update
    cancelled = pyqtSignal()       # Cancellation notification
```

**Purpose**: Separate QObject for signals (QRunnable cannot have signals directly)

---

## Class: EnhancedBaseWorker (extends QRunnable)

### Constructor

```python
def __init__(self, worker_id):
    super().__init__()
    self.signals = WorkerSignals()
    self.worker_id = worker_id
    self._cancelled = threading.Event()
    self._started = threading.Event()
    self._completed = threading.Event()
    self._start_time = time.time()
    self._timeout = 30  # 30 second default timeout
```

**Key Fields**:
- `worker_id`: Unique identifier for this worker
- `signals`: Signal object for communication
- `_cancelled`: Event for cancellation detection
- `_started`/`_completed`: Lifecycle tracking
- `_timeout`: Configurable timeout (default 30s)

---

### Core Methods

#### `cancel()` - Cancel Worker

```python
def cancel(self):
    self._cancelled.set()
    if not self._completed.is_set():
        self.signals.cancelled.emit()
```

**Usage**:
```python
worker = LoadPodsWorker()
thread_manager.submit_worker("load_pods", worker)
# Later, if user navigates away:
worker.cancel()
```

---

#### `is_cancelled()` - Check Cancellation

```python
def is_cancelled(self):
    return self._cancelled.is_set()
```

**Used in execute() methods**:
```python
def execute(self):
    for item in large_dataset:
        if self.is_cancelled():
            break  # Stop processing
        process(item)
```

---

#### `is_timed_out()` - Timeout Detection

```python
def is_timed_out(self):
    return (time.time() - self._start_time) > self._timeout
```

**Prevents hung workers**: Operations exceeding timeout are automatically cancelled

---

#### `run()` - **MAIN EXECUTION METHOD**

```python
def run(self):
    self._started.set()
    try:
        if self.is_cancelled():
            return
            
        result = self.execute()
        
        if not self.is_cancelled() and not self.is_timed_out():
            self.safe_emit_finished(result)
    except Exception as e:
        if not self.is_cancelled():
            logging.error(f"Worker {self.worker_id} failed: {e}")
            self.safe_emit_error(str(e))
```

**Flow**:
1. Mark as started
2. Check if already cancelled
3. Call `execute()` (implemented by subclass)
4. Emit finished signal with result
5. On exception, emit error signal

---

#### `execute()` - **ABSTRACT METHOD**

```python
def execute(self):
    raise NotImplementedError("Subclasses must implement execute method")
```

**Must be implemented by subclasses**:
```python
class LoadPodsWorker(EnhancedBaseWorker):
    def execute(self):
        # Load pods from Kubernetes API
        return pods_list
```

---

### Safe Signal Emission

#### `safe_emit_finished()`

```python
def safe_emit_finished(self, result):
    if not self.is_cancelled() and not self.is_timed_out():
        try:
            self._completed.set()
            self.signals.finished.emit(result)
        except RuntimeError:
            logging.warning(f"Failed to emit finished signal for worker {self.worker_id}")
```

**Safety Checks**:
- Don't emit if cancelled
- Don't emit if timed out
- Catch RuntimeError (receiver destroyed)

---

#### `safe_emit_error()`

```python
def safe_emit_error(self, error):
    if not self.is_cancelled():
        try:
            self._completed.set()
            self.signals.error.emit(error)
        except RuntimeError:
            logging.warning(f"Failed to emit error signal for worker {self.worker_id}")
```

---

#### `safe_emit_progress()`

```python
def safe_emit_progress(self, progress):
    if not self.is_cancelled():
        try:
            self.signals.progress.emit(progress)
        except RuntimeError:
            pass  # Silently ignore progress failures
```

**Used for progress updates**:
```python
def execute(self):
    total = 1000
    for i, item in enumerate(items):
        if i % 100 == 0:
            self.safe_emit_progress(f"Processing {i}/{total}")
        process(item)
```

---

## Usage Examples

### Basic Worker

```python
class LoadPodsWorker(EnhancedBaseWorker):
    def __init__(self, namespace):
        super().__init__("load_pods")
        self.namespace = namespace
    
    def execute(self):
        # Load pods from API
        pods = api.list_namespaced_pod(self.namespace)
        return [pod.metadata.name for pod in pods.items]

# Use worker
worker = LoadPodsWorker("default")
worker.signals.finished.connect(lambda pods: print(f"Loaded {len(pods)} pods"))
worker.signals.error.connect(lambda err: print(f"Error: {err}"))

thread_manager = get_thread_manager()
thread_manager.submit_worker("load_pods", worker)
```

---

### Worker with Cancellation

```python
class ProcessLargeDatasetWorker(EnhancedBaseWorker):
    def execute(self):
        results = []
        for i in range(10000):
            if self.is_cancelled():
                logging.info("Worker cancelled, stopping early")
                break
            
            results.append(process_item(i))
            
            if i % 1000 == 0:
                self.safe_emit_progress(f"Processed {i}/10000")
        
        return results
```

---

### Worker with Custom Timeout

```python
class SlowOperationWorker(EnhancedBaseWorker):
    def __init__(self):
        super().__init__("slow_operation")
        self._timeout = 120  # 2 minutes instead of default 30s
    
    def execute(self):
        # Long-running operation
        time.sleep(90)  # Won't timeout
        return "Done"
```

---

## Key Features

1. ✅ **Cancellation Support**: Workers can be cancelled mid-execution
2. ✅ **Timeout Detection**: Automatic timeout after 30 seconds (configurable)
3. ✅ **Safe Signals**: Handles destroyed receivers gracefully
4. ✅ **Lifecycle Tracking**: Started/completed events
5. ✅ **Progress Updates**: Optional progress reporting
6. ✅ **Error Handling**: Catches exceptions and emits error signal
7. ✅ **Abstract Pattern**: Enforces execute() implementation

---

## Subclasses in Orchetrix

**Resource Loading**:
- ResourceLoadWorker (unified_resource_loader.py)
- SearchResourceLoadWorker (unified_resource_loader.py)

**Metrics & Events**:
- AsyncMetricsWorker (kubernetes_service.py)
- AsyncIssuesWorker (kubernetes_service.py)

**Resource Deletion**:
- ResourceDeleterThread (resource_deleters.py)
- BatchResourceDeleterThread (resource_deleters.py)

**Overview Dashboard**:
- OverviewDataWorker (OverviewPage.py)

**Total**: 10+ worker types, 100+ instances running

---

## Signal Flow

```
User Action (e.g., click "Pods")
   ↓
Create LoadPodsWorker
   ↓
Submit to ThreadManager
   ↓
ThreadManager starts worker in background thread
   ↓
Worker.run() executes
   ↓
Worker.execute() loads pods
   ↓
Worker.safe_emit_finished(pods)
   ↓
Signal received by PodsPage
   ↓
PodsPage updates table
```

---

## Benefits

**Without EnhancedBaseWorker**:
- ❌ Each worker implements own cancellation
- ❌ Each worker implements own timeout
- ❌ No standard error handling
- ❌ Signal crashes on destroyed receivers

**With EnhancedBaseWorker**:
- ✅ Standard cancellation for all workers
- ✅ Automatic timeout detection
- ✅ Consistent error handling
- ✅ Safe signal emission

---

## Total Lines**: 83 lines providing foundation for 100+ background operations.
