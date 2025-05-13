import os
import sys
import logging
import traceback
from datetime import datetime

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
        file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Add console handler only when running in development (not in PyInstaller)
        if not getattr(sys, 'frozen', False):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter('%(levelname)s: %(message)s')
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