import logging
import threading
import time
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from Utils.thread_manager import is_shutdown_requested

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
            try:
                self.signals.cancelled.emit()
            except RuntimeError:
                # Page/widget might already be deleted
                pass

    def is_cancelled(self):
        return self._cancelled.is_set() or is_shutdown_requested()

    def is_timed_out(self):
        return (time.time() - self._start_time) > self._timeout

    def isRunning(self):
        """Check if worker is currently running - backward compatibility method"""
        return self._started.is_set() and not self._completed.is_set() and not self.is_cancelled()

    def wait(self, timeout_ms=30000):
        """Wait for worker to complete - backward compatibility method"""
        timeout_seconds = timeout_ms / 1000.0
        return self._completed.wait(timeout_seconds)

    def safe_emit_finished(self, result):
        if not self.is_cancelled() and not self.is_timed_out():
            try:
                self._completed.set()
                self.signals.finished.emit(result)
            except RuntimeError:
                logging.debug(f"Failed to emit finished signal for worker {self.worker_id} - already deleted")

    def safe_emit_error(self, error):
        if not self.is_cancelled():
            try:
                self._completed.set()
                self.signals.error.emit(error)
            except RuntimeError:
                logging.debug(f"Failed to emit error signal for worker {self.worker_id} - already deleted")

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
        finally:
            self._completed.set()

    def execute(self) -> Any:
        raise NotImplementedError("Subclasses must implement execute method")


__all__ = ["EnhancedBaseWorker", "WorkerSignals"]
