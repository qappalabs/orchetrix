# Icons.py - Brief Documentation

**Path**: `orchetrix/UI/Icons.py`
**Lines**: ~100

## Purpose
Icon resource management

## Main Function
```python
def resource_path(relative_path):
    """Get absolute path to resource (works for dev and PyInstaller)"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
```

## Usage
```python
icon = QIcon(resource_path("Icons/pod.svg"))
```

## Icon Files
All SVG icons stored in `Icons/` directory
