""" Globally patch the subprocess module to prevent console windows on all platforms """
import os
import sys
import subprocess
import logging

# Keep references to the original subprocess functions
original_run = subprocess.run
original_popen = subprocess.Popen

# Windows-specific flag to prevent console window
CREATE_NO_WINDOW = 0x08000000

def silent_run(*args, **kwargs):
    """
    A replacement for subprocess.run that prevents console windows on Windows
    and redirects output on Unix-like systems
    """
    if sys.platform == 'win32':
        # Windows-specific: Hide console window
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
    
    elif sys.platform in ('linux', 'darwin'):
        # FIX: Only set stdout/stderr if capture_output is not being used
        if not kwargs.get('capture_output', False):
            # For Linux and macOS: Redirect output to /dev/null if not specified
            if 'stdout' not in kwargs:
                kwargs['stdout'] = subprocess.DEVNULL
            if 'stderr' not in kwargs:
                kwargs['stderr'] = subprocess.DEVNULL
            
        # For GUI apps on macOS, we can use LSBackgroundOnly=1
        if sys.platform == 'darwin' and 'env' in kwargs:
            if kwargs['env'] is None:
                kwargs['env'] = os.environ.copy()
            kwargs['env']['LSBackgroundOnly'] = '1'
    
    try:
        return original_run(*args, **kwargs)
    except Exception as e:
        logging.error(f"Error in patched subprocess.run: {str(e)}")
        raise

def silent_popen(*args, **kwargs):
    """
    A replacement for subprocess.Popen that prevents console windows on Windows
    and redirects output on Unix-like systems
    """
    if sys.platform == 'win32':
        # Windows-specific: Hide console window
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
    
    elif sys.platform in ('linux', 'darwin'):
        # FIX: Be more careful about setting stdout/stderr
        # Check for PIPE settings first, don't override if already set
        if kwargs.get('stdout') not in (subprocess.PIPE, subprocess.STDOUT):
            kwargs['stdout'] = subprocess.DEVNULL
        if kwargs.get('stderr') not in (subprocess.PIPE, subprocess.STDOUT):
            kwargs['stderr'] = subprocess.DEVNULL
            
        # For GUI apps on macOS, we can use LSBackgroundOnly=1
        if sys.platform == 'darwin' and 'env' in kwargs:
            if kwargs['env'] is None:
                kwargs['env'] = os.environ.copy()
            kwargs['env']['LSBackgroundOnly'] = '1'
    
    try:
        return original_popen(*args, **kwargs)
    except Exception as e:
        logging.error(f"Error in patched subprocess.Popen: {str(e)}")
        raise

def debug_run(*args, **kwargs):
    """Debug version to trace all subprocess calls"""
    cmd = args[0] if args else kwargs.get('args', 'Unknown command')
    logging.info(f"SUBPROCESS CALL: {cmd}")
    return silent_run(*args, **kwargs)

# Patch the subprocess module
subprocess.run = silent_run
logging.info("Subprocess.run patched to hide output on all platforms")

# Patch Popen as well
subprocess.Popen = silent_popen
logging.info("Subprocess.Popen patched to hide output on all platforms")