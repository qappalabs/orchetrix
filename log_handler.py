import os
import sys
import logging
import traceback
import time
import functools
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional

def setup_logging():
    """Set up logging with only file-based logging for PyInstaller environments"""
    # Determine application base directory
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running in normal Python environment
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create logs directory
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(logs_dir, f"orchestrix_{timestamp}.log")
    
    # Create a root logger and remove any existing handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove all handlers to avoid issues with existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create file handler - this is the only handler we'll use for PyInstaller builds
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Clean, readable format
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Add console handler only when running in development (not in PyInstaller)
        if not getattr(sys, 'frozen', False):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Even cleaner console format
            console_formatter = logging.Formatter(
                '%(levelname)-8s | %(name)-15s | %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Log startup message
        logging.info(f"Application started. Log file: {log_file}")
        return log_file
        
    except Exception as e:
        # Last resort if even logging setup fails
        error_log = os.path.join(base_dir, "orchestrix_error.log")
        with open(error_log, "w") as f:
            f.write(f"CRITICAL ERROR SETTING UP LOGGING: {str(e)}\n")
            f.write(traceback.format_exc())
        return error_log

def log_exception(e, message="An error occurred"):
    """Log an exception safely without relying on sys.stdout/stderr"""
    try:
        logging.error(f"{message}: {str(e)}")
        logging.error(traceback.format_exc())
    except Exception:
        # If even this fails, we can't do much more
        pass

def serialize_for_logging(obj: Any, max_length: int = 500) -> str:
    """Safely serialize objects for logging with size limits"""
    try:
        if obj is None:
            return "None"
        elif isinstance(obj, (str, int, float, bool)):
            result = str(obj)
        elif isinstance(obj, (list, tuple)):
            if len(obj) > 10:
                result = f"[{', '.join(serialize_for_logging(item, 50) for item in obj[:10])}...] (length: {len(obj)})"
            else:
                result = f"[{', '.join(serialize_for_logging(item, 50) for item in obj)}]"
        elif isinstance(obj, dict):
            if len(obj) > 10:
                items = list(obj.items())[:10]
                result = f"{{{', '.join(f'{k}: {serialize_for_logging(v, 50)}' for k, v in items)}...}} (keys: {len(obj)})"
            else:
                result = f"{{{', '.join(f'{k}: {serialize_for_logging(v, 50)}' for k, v in obj.items())}}}"
        else:
            result = f"<{type(obj).__name__}:{str(obj)[:100]}{'...' if len(str(obj)) > 100 else ''}>"
        
        if len(result) > max_length:
            result = result[:max_length] + "..."
        return result
    except Exception:
        return f"<{type(obj).__name__}:unprintable>"

def method_logger(
    log_level: int = logging.DEBUG,  # Changed to DEBUG to reduce noise
    log_inputs: bool = False,        # Disabled by default
    log_outputs: bool = False,       # Disabled by default  
    log_timing: bool = False,        # Disabled by default
    log_exceptions: bool = True,     # Keep exception logging
    max_input_length: int = 100,     # Reduced length
    max_output_length: int = 100,    # Reduced length
    exclude_params: Optional[list] = None
) -> Callable:
    """
    Decorator to add detailed logging to methods with input, output, timing information
    
    Args:
        log_level: Logging level to use
        log_inputs: Whether to log method inputs
        log_outputs: Whether to log method outputs  
        log_timing: Whether to log execution timing
        log_exceptions: Whether to log exceptions
        max_input_length: Maximum length for input serialization
        max_output_length: Maximum length for output serialization
        exclude_params: List of parameter names to exclude from logging
    """
    if exclude_params is None:
        exclude_params = ['self', 'password', 'token', 'secret', 'key']
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            func_name = f"{func.__qualname__}"
            
            # Generate unique call ID for tracking
            call_id = f"{func_name}_{int(time.time() * 1000000) % 1000000}"
            
            # Log method entry
            start_time = time.time()
            start_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            
            # Prepare input logging
            input_info = ""
            if log_inputs and (args or kwargs):
                try:
                    # Get function signature for parameter names
                    import inspect
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    
                    # Filter out excluded parameters
                    filtered_args = {
                        k: v for k, v in bound_args.arguments.items() 
                        if k not in exclude_params
                    }
                    
                    if filtered_args:
                        serialized_args = {
                            k: serialize_for_logging(v, max_input_length) 
                            for k, v in filtered_args.items()
                        }
                        input_info = f" | INPUTS: {json.dumps(serialized_args, default=str)}"
                except Exception as e:
                    input_info = f" | INPUTS: <serialization_error: {str(e)}>"
            
            # Log method entry (only if DEBUG level)
            if log_level <= logging.DEBUG:
                logger.log(log_level, f"{func_name}() called{input_info}")
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate execution time
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                # Prepare output logging
                output_info = ""
                if log_outputs and result is not None and log_level <= logging.DEBUG:
                    try:
                        serialized_result = serialize_for_logging(result, max_output_length)
                        output_info = f" -> {serialized_result}"
                    except Exception as e:
                        output_info = f" -> <error: {str(e)}>"
                
                # Prepare timing info  
                timing_info = ""
                if log_timing and execution_time > 100:  # Only log slow operations
                    timing_info = f" ({execution_time:.1f}ms)"
                
                # Log method exit (only if DEBUG level or slow)
                if log_level <= logging.DEBUG or execution_time > 100:
                    logger.log(log_level, f"{func_name}() completed{timing_info}{output_info}")
                
                return result
                
            except Exception as e:
                # Calculate execution time for failed calls
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000
                end_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                
                # Log exception (always log exceptions)
                if log_exceptions:
                    timing_info = f" ({execution_time:.1f}ms)" if log_timing else ""
                    logger.error(f"{func_name}() failed{timing_info}: {type(e).__name__}: {str(e)}")
                    # Only show traceback for non-expected errors
                    if not isinstance(e, (ValueError, KeyError, AttributeError)):
                        logger.error(f"Traceback: {traceback.format_exc()}")
                
                raise
        
        return wrapper
    return decorator

def class_logger(
    log_level: int = logging.DEBUG,  # Changed to DEBUG to reduce noise
    exclude_methods: Optional[list] = None,
    exclude_private: bool = True,
    exclude_dunder: bool = True,
    **decorator_kwargs
) -> Callable:
    """
    Class decorator to automatically add method logging to all methods in a class
    
    Args:
        log_level: Logging level to use
        exclude_methods: List of method names to exclude
        exclude_private: Whether to exclude private methods (starting with _)
        exclude_dunder: Whether to exclude dunder methods (starting and ending with __)
        **decorator_kwargs: Additional arguments to pass to method_logger
    """
    if exclude_methods is None:
        exclude_methods = ['__init__', '__str__', '__repr__']
    
    # Add common Qt event methods and property setters to exclusion list
    qt_event_methods = [
        'event', 'childEvent', 'timerEvent', 'connectNotify', 'disconnectNotify',
        'eventFilter', 'paintEvent', 'resizeEvent', 'moveEvent', 'closeEvent',
        'showEvent', 'hideEvent', 'enterEvent', 'leaveEvent', 'mousePressEvent',
        'mouseReleaseEvent', 'mouseMoveEvent', 'wheelEvent', 'keyPressEvent',
        'keyReleaseEvent', 'focusInEvent', 'focusOutEvent', 'changeEvent',
        'contextMenuEvent', 'dragEnterEvent', 'dragMoveEvent', 'dragLeaveEvent',
        'dropEvent', 'customEvent', 'setWindowTitle', 'setGeometry', 'setWindowFlags',
        'setStyleSheet', 'setCentralWidget', 'setFont', 'setText', 'setIcon',
        'setFixedSize', 'setMinimumSize', 'setMaximumSize', 'setVisible',
        'setEnabled', 'setObjectName', 'setAttribute', 'setProperty'
    ]
    exclude_methods.extend(qt_event_methods)
    
    def decorator(cls):
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            
            # Skip if not callable
            if not callable(attr):
                continue
                
            # Skip if in exclude list
            if attr_name in exclude_methods:
                continue
                
            # Skip private methods if requested
            if exclude_private and attr_name.startswith('_') and not attr_name.startswith('__'):
                continue
                
            # Skip dunder methods if requested
            if exclude_dunder and attr_name.startswith('__') and attr_name.endswith('__'):
                continue
            
            # Skip PyQt6 signals and other Qt objects
            try:
                if hasattr(attr, '__class__'):
                    class_name = attr.__class__.__name__
                    module_name = getattr(attr.__class__, '__module__', '')
                    
                    # Skip PyQt6 signals
                    if 'pyqtSignal' in class_name or 'pyqtBoundSignal' in class_name:
                        continue
                    
                    # Skip PyQt6 module objects
                    if module_name.startswith('PyQt6'):
                        continue
                    
                    # Check for signal-like attributes
                    if hasattr(attr, 'emit') and hasattr(attr, 'connect') and hasattr(attr, 'disconnect'):
                        continue
                        
                    # Skip property objects
                    if isinstance(attr, property):
                        continue
            except:
                pass
            
            # Apply the method logger decorator
            decorated_method = method_logger(log_level=log_level, **decorator_kwargs)(attr)
            setattr(cls, attr_name, decorated_method)
        
        return cls
    return decorator

def log_method_call(func_name: str, inputs: Dict[str, Any] = None, outputs: Any = None, 
                   duration_ms: float = None, exception: Exception = None):
    """
    Manual logging function for cases where decorator cannot be used
    
    Args:
        func_name: Name of the function/method
        inputs: Dictionary of input parameters
        outputs: Output/return value
        duration_ms: Execution duration in milliseconds
        exception: Exception if one occurred
    """
    logger = logging.getLogger(__name__)
    call_id = f"{func_name}_{int(time.time() * 1000000) % 1000000}"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    # Log inputs
    if inputs:
        try:
            serialized_inputs = {k: serialize_for_logging(v) for k, v in inputs.items()}
            logger.info(f"[{call_id}] CALL {func_name} | TIME: {timestamp} | INPUTS: {json.dumps(serialized_inputs, default=str)}")
        except Exception as e:
            logger.info(f"[{call_id}] CALL {func_name} | TIME: {timestamp} | INPUTS: <serialization_error: {str(e)}>")
    
    # Log outputs or exception
    if exception:
        logger.error(f"[{call_id}] ERROR {func_name} | DURATION: {duration_ms:.2f}ms | EXCEPTION: {type(exception).__name__}: {str(exception)}")
    elif outputs is not None:
        try:
            serialized_output = serialize_for_logging(outputs)
            logger.info(f"[{call_id}] RESULT {func_name} | DURATION: {duration_ms:.2f}ms | OUTPUT: {serialized_output}")
        except Exception as e:
            logger.info(f"[{call_id}] RESULT {func_name} | DURATION: {duration_ms:.2f}ms | OUTPUT: <serialization_error: {str(e)}>")
    else:
        logger.info(f"[{call_id}] COMPLETE {func_name} | DURATION: {duration_ms:.2f}ms")