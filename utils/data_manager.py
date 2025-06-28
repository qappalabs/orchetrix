from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from utils.enhanced_worker import EnhancedBaseWorker
import time
import threading
from typing import Dict, Any, Optional, Callable
import logging

class DataFetchWorker(EnhancedBaseWorker):
    def __init__(self, data_type, fetch_function):
        super().__init__(f"data_fetch_{data_type}")
        self.data_type = data_type
        self.fetch_function = fetch_function
        
    def execute(self):
        try:
            result = self.fetch_function()
            # Ensure we always return a dictionary, never None
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logging.error(f"Error in data fetch worker for {self.data_type}: {e}")
            return {}

class DataManager(QObject):
    data_updated = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self.cache = {}
        self.cache_timestamps = {}
        self.update_strategies = {}
        self.lock = threading.RLock()
        self._shutdown_requested = False
        
    def shutdown(self):
        """Request shutdown and clear resources"""
        with self.lock:
            self._shutdown_requested = True
            self.cache.clear()
            self.cache_timestamps.clear()
            self.update_strategies.clear()
        
    def register_data_source(self, data_type: str, fetch_function: Callable, 
                           update_interval: int = 30, cache_duration: int = 300):
        with self.lock:
            if self._shutdown_requested:
                return
                
            self.update_strategies[data_type] = {
                'fetch_function': fetch_function,
                'update_interval': update_interval,
                'cache_duration': cache_duration,
                'last_fetch_attempt': 0,
                'consecutive_failures': 0
            }
            
    def get_data(self, data_type: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        with self.lock:
            if self._shutdown_requested:
                return {}
                
            current_time = time.time()
            
            if not force_refresh and data_type in self.cache:
                cache_time = self.cache_timestamps.get(data_type, 0)
                strategy = self.update_strategies.get(data_type, {})
                cache_duration = strategy.get('cache_duration', 300)
                
                if current_time - cache_time < cache_duration:
                    return self.cache[data_type]
                    
            if data_type in self.update_strategies:
                self._fetch_data_async(data_type)
                
            return self.cache.get(data_type, {})
            
    def _fetch_data_async(self, data_type: str):
        if self._shutdown_requested:
            return
            
        strategy = self.update_strategies.get(data_type)
        if not strategy:
            return
            
        current_time = time.time()
        
        backoff_delay = min(60, 2 ** strategy['consecutive_failures'])
        if current_time - strategy['last_fetch_attempt'] < backoff_delay:
            return
            
        strategy['last_fetch_attempt'] = current_time
        
        try:
            from utils.thread_manager import get_thread_manager
            thread_manager = get_thread_manager()
            
            worker = DataFetchWorker(data_type, strategy['fetch_function'])
            worker.signals.finished.connect(lambda result: self._handle_fetch_result(data_type, result))
            worker.signals.error.connect(lambda error: self._handle_fetch_error(data_type, error))
            
            thread_manager.submit_worker(f"data_fetch_{data_type}", worker)
        except Exception as e:
            logging.error(f"Error starting data fetch worker for {data_type}: {e}")
            self._handle_fetch_error(data_type, str(e))
        
    def _handle_fetch_result(self, data_type: str, result: Any):
        with self.lock:
            if self._shutdown_requested:
                return
                
            # Ensure result is always a dictionary
            if result is None:
                result = {}
            elif not isinstance(result, dict):
                logging.warning(f"Data fetch for {data_type} returned non-dict result: {type(result)}")
                result = {}
                
            self.cache[data_type] = result
            self.cache_timestamps[data_type] = time.time()
            
            if data_type in self.update_strategies:
                self.update_strategies[data_type]['consecutive_failures'] = 0
                
            try:
                self.data_updated.emit(data_type, result)
            except RuntimeError as e:
                # Signal emission failed, likely due to shutdown
                logging.debug(f"Signal emission failed for {data_type}: {e}")
            
    def _handle_fetch_error(self, data_type: str, error: str):
        with self.lock:
            if self._shutdown_requested:
                return
                
            strategy = self.update_strategies.get(data_type)
            if strategy:
                strategy['consecutive_failures'] += 1
                
            logging.warning(f"Data fetch failed for {data_type}: {error}")
            
    def clear_cluster_data(self, cluster_name: str):
        with self.lock:
            if self._shutdown_requested:
                return
                
            keys_to_remove = [key for key in self.cache.keys() if cluster_name in key]
            for key in keys_to_remove:
                self.cache.pop(key, None)
                self.cache_timestamps.pop(key, None)

_data_manager_instance = None

def get_data_manager():
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = DataManager()
    return _data_manager_instance

def shutdown_data_manager():
    """Shutdown the data manager singleton safely"""
    global _data_manager_instance
    if _data_manager_instance is not None:
        try:
            _data_manager_instance.shutdown()
            _data_manager_instance = None
            logging.info("Data manager singleton shut down successfully")
        except Exception as e:
            logging.error(f"Error shutting down data manager: {e}")
            _data_manager_instance = None