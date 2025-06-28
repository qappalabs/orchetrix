from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, QTimer
import threading
import logging
import weakref
import time

class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    cancelled = pyqtSignal()

class EnhancedBaseWorker(QRunnable):
    def __init__(self, worker_id):
        super().__init__()
        self.signals = WorkerSignals()
        self.worker_id = worker_id
        self._cancelled = threading.Event()
        self._started = threading.Event()
        self._completed = threading.Event()
        self._start_time = time.time()
        self._timeout = 30  # 30 second timeout
        
    def cancel(self):
        self._cancelled.set()
        if not self._completed.is_set():
            self.signals.cancelled.emit()
        
    def is_cancelled(self):
        return self._cancelled.is_set()
    
    def is_timed_out(self):
        return (time.time() - self._start_time) > self._timeout
        
    def safe_emit_finished(self, result):
        if not self.is_cancelled() and not self.is_timed_out():
            try:
                self._completed.set()
                self.signals.finished.emit(result)
            except RuntimeError:
                logging.warning(f"Failed to emit finished signal for worker {self.worker_id}")
            
    def safe_emit_error(self, error):
        if not self.is_cancelled():
            try:
                self._completed.set()
                self.signals.error.emit(error)
            except RuntimeError:
                logging.warning(f"Failed to emit error signal for worker {self.worker_id}")
    
    def safe_emit_progress(self, progress):
        if not self.is_cancelled():
            try:
                self.signals.progress.emit(progress)
            except RuntimeError:
                pass
            
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
                
    def execute(self):
        raise NotImplementedError("Subclasses must implement execute method")