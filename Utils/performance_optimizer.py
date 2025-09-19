"""
Performance Optimizer - Utilities for memory management and performance optimization
Added as part of the architectural refactoring improvements
"""

import gc
import sys
import time
import logging
import psutil
import threading
from typing import Dict, Any, Optional
from functools import wraps
from PyQt6.QtCore import QTimer, QObject, pyqtSignal


class MemoryMonitor(QObject):
    """Monitor and report memory usage"""
    
    memory_warning = pyqtSignal(float)  # Emitted when memory usage exceeds threshold
    
    def __init__(self, warning_threshold_mb: float = 500.0):
        super().__init__()
        self.warning_threshold = warning_threshold_mb * 1024 * 1024  # Convert to bytes
        self.monitor_timer = QTimer(self)  # Fixed: Added self as parent
        self.monitor_timer.timeout.connect(self._check_memory)
        self.last_gc_time = time.time()
        self.gc_interval = 60  # Run garbage collection every 60 seconds
        
    def start_monitoring(self, interval_ms: int = 30000):
        """Start memory monitoring"""
        self.monitor_timer.start(interval_ms)
        logging.info(f"Memory monitoring started with {interval_ms}ms interval")
        
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitor_timer.stop()
        logging.info("Memory monitoring stopped")
        
    def _check_memory(self):
        """Check current memory usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Log memory usage periodically
            logging.debug(f"Current memory usage: {memory_mb:.1f} MB")
            
            # Trigger warning if threshold exceeded
            if memory_info.rss > self.warning_threshold:
                logging.warning(f"Memory usage high: {memory_mb:.1f} MB")
                self.memory_warning.emit(memory_mb)
                
            # Periodic garbage collection
            current_time = time.time()
            if current_time - self.last_gc_time > self.gc_interval:
                self._run_garbage_collection()
                self.last_gc_time = current_time
                
        except Exception as e:
            logging.error(f"Error checking memory usage: {e}")
            
    def _run_garbage_collection(self):
        """Run garbage collection and report results"""
        before_objects = len(gc.get_objects())
        collected = gc.collect()
        after_objects = len(gc.get_objects())
        
        if collected > 0:
            logging.info(f"Garbage collection: {collected} objects collected, "
                        f"{before_objects - after_objects} objects freed")


class PerformanceProfiler:
    """Simple performance profiler for method timing"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.timing_data = {}
        self.call_counts = {}
        
    def record_timing(self, method_name: str, duration: float):
        """Record timing for a method"""
        if method_name not in self.timing_data:
            self.timing_data[method_name] = []
            self.call_counts[method_name] = 0
            
        self.timing_data[method_name].append(duration)
        self.call_counts[method_name] += 1
        
        # Keep only last 100 measurements to prevent memory growth
        if len(self.timing_data[method_name]) > 100:
            self.timing_data[method_name] = self.timing_data[method_name][-100:]
    
    def get_stats(self, method_name: str) -> Dict[str, Any]:
        """Get performance statistics for a method"""
        if method_name not in self.timing_data:
            return {}
            
        timings = self.timing_data[method_name]
        if not timings:
            return {}
            
        return {
            'count': self.call_counts[method_name],
            'avg_ms': sum(timings) / len(timings) * 1000,
            'min_ms': min(timings) * 1000,
            'max_ms': max(timings) * 1000,
            'recent_avg_ms': sum(timings[-10:]) / min(len(timings), 10) * 1000
        }
    
    def get_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get performance summary for all methods"""
        return {method: self.get_stats(method) for method in self.timing_data.keys()}
    
    def reset_stats(self):
        """Reset all performance statistics"""
        self.timing_data.clear()
        self.call_counts.clear()


def performance_monitor(func):
    """Decorator to monitor method performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = PerformanceProfiler()
        method_name = f"{func.__module__}.{func.__qualname__}"
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            profiler.record_timing(method_name, duration)
            
            # Log slow methods
            if duration > 1.0:  # Log methods taking more than 1 second
                logging.warning(f"Slow method: {method_name} took {duration:.2f}s")
    
    return wrapper


class ResourceCleaner:
    """Utility for cleaning up resources and preventing memory leaks"""
    
    @staticmethod
    def cleanup_threads(threads, timeout_ms: int = 5000):
        """Cleanup a list of QThread objects"""
        cleaned_count = 0
        for thread in threads:
            if thread and thread.isRunning():
                try:
                    if hasattr(thread, 'cancel'):
                        thread.cancel()
                    thread.quit()
                    if thread.wait(timeout_ms):
                        cleaned_count += 1
                    else:
                        logging.warning(f"Thread {thread} did not finish within timeout")
                        thread.terminate()
                except Exception as e:
                    logging.error(f"Error cleaning up thread {thread}: {e}")
        
        if cleaned_count > 0:
            logging.info(f"Cleaned up {cleaned_count} threads")
    
    @staticmethod
    def cleanup_timers(timers):
        """Cleanup a list of QTimer objects"""
        cleaned_count = 0
        for timer in timers:
            if timer and timer.isActive():
                try:
                    timer.stop()
                    cleaned_count += 1
                except Exception as e:
                    logging.error(f"Error cleaning up timer {timer}: {e}")
        
        if cleaned_count > 0:
            logging.info(f"Cleaned up {cleaned_count} timers")
    
    @staticmethod
    def cleanup_objects(objects):
        """Cleanup a list of objects with deleteLater method"""
        cleaned_count = 0
        for obj in objects:
            if obj:
                try:
                    if hasattr(obj, 'deleteLater'):
                        obj.deleteLater()
                    elif hasattr(obj, 'cleanup'):
                        obj.cleanup()
                    cleaned_count += 1
                except Exception as e:
                    logging.error(f"Error cleaning up object {obj}: {e}")
        
        if cleaned_count > 0:
            logging.info(f"Cleaned up {cleaned_count} objects")
    
    @staticmethod
    def force_garbage_collection():
        """Force garbage collection and report results"""
        # Clear circular references
        gc.collect()
        
        # Force collection of all generations
        collected = 0
        for i in range(3):
            collected += gc.collect()
        
        if collected > 0:
            logging.info(f"Force garbage collection: {collected} objects collected")
        
        return collected


def optimize_pyqt_performance():
    """Apply PyQt-specific performance optimizations"""
    try:
        from PyQt6.QtCore import QCoreApplication
        
        # Set thread pool size based on CPU count
        import os
        cpu_count = os.cpu_count() or 4
        thread_pool_size = min(cpu_count * 2, 16)  # Limit to reasonable maximum
        
        app = QCoreApplication.instance()
        if app:
            app.thread().setProperty("threadPoolSize", thread_pool_size)
            logging.info(f"Set thread pool size to {thread_pool_size}")
            
        # Enable high DPI scaling
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        
    except Exception as e:
        logging.error(f"Error applying PyQt optimizations: {e}")


# Global instances
_memory_monitor = None
_performance_profiler = None

def get_memory_monitor() -> MemoryMonitor:
    """Get global memory monitor instance"""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor()
    return _memory_monitor

def get_performance_profiler() -> PerformanceProfiler:
    """Get global performance profiler instance"""
    global _performance_profiler
    if _performance_profiler is None:
        _performance_profiler = PerformanceProfiler()
    return _performance_profiler

def shutdown_performance_monitoring():
    """Shutdown performance monitoring"""
    global _memory_monitor, _performance_profiler
    
    if _memory_monitor:
        _memory_monitor.stop_monitoring()
        _memory_monitor = None
        
    if _performance_profiler:
        _performance_profiler.reset_stats()
        _performance_profiler = None
        
    logging.info("Performance monitoring shutdown complete")