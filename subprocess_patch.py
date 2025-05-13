"""
Globally patch the subprocess module to prevent console windows
"""
import os
import sys
import subprocess
import logging

# Keep a reference to the original subprocess.run
original_run = subprocess.run

# Windows-specific flag to prevent console window
CREATE_NO_WINDOW = 0x08000000

def silent_run(*args, **kwargs):
    """
    A replacement for subprocess.run that prevents console windows on Windows
    """
    if sys.platform == 'win32':
        # Create startupinfo to hide the console window
        if 'startupinfo' not in kwargs:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            kwargs['startupinfo'] = startupinfo
        
        # Add the CREATE_NO_WINDOW flag
        if 'creationflags' in kwargs:
            kwargs['creationflags'] |= CREATE_NO_WINDOW
        else:
            kwargs['creationflags'] = CREATE_NO_WINDOW
    
    try:
        return original_run(*args, **kwargs)
    except Exception as e:
        # Log the error but don't crash
        logging.error(f"Error in patched subprocess.run: {str(e)}")
        raise

# Patch the subprocess module
subprocess.run = silent_run
logging.info("Subprocess module patched to hide console windows")

# Also patch Popen for good measure
original_popen = subprocess.Popen

def silent_popen(*args, **kwargs):
    """
    A replacement for subprocess.Popen that prevents console windows on Windows
    """
    if sys.platform == 'win32':
        # Create startupinfo to hide the console window
        if 'startupinfo' not in kwargs:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            kwargs['startupinfo'] = startupinfo
        
        # Add the CREATE_NO_WINDOW flag
        if 'creationflags' in kwargs:
            kwargs['creationflags'] |= CREATE_NO_WINDOW
        else:
            kwargs['creationflags'] = CREATE_NO_WINDOW
    
    try:
        return original_popen(*args, **kwargs)
    except Exception as e:
        logging.error(f"Error in patched subprocess.Popen: {str(e)}")
        raise

# Patch Popen as well
subprocess.Popen = silent_popen
logging.info("Subprocess.Popen patched to hide console windows")


def debug_run(*args, **kwargs):
    """Debug version to trace all subprocess calls"""
    cmd = args[0] if args else kwargs.get('args', 'Unknown command')
    logging.info(f"SUBPROCESS CALL: {cmd}")
    return silent_run(*args, **kwargs)
