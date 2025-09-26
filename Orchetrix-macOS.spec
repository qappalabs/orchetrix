# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
import platform

# macOS-specific PyInstaller configuration
# This spec file addresses common macOS packaging issues

# Get absolute path to icon
icon_path = os.path.abspath(os.path.join('Icons', 'logoIcon.icns'))  # macOS prefers .icns
if not os.path.exists(icon_path):
    icon_path = os.path.abspath(os.path.join('Icons', 'logoIcon.png'))
    if not os.path.exists(icon_path):
        icon_path = None

def collect_data_files():
    """Collect all necessary data files with enhanced macOS support"""
    data_files = []
    
    # Add resource directories
    resource_dirs = ['Icons', 'Images', 'UI', 'Pages', 'Utils', 'Services', 'Base_Components', 'Business_Logic']
    for dir_name in resource_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            data_files.append((dir_name, dir_name))
    
    return data_files

def get_kubernetes_binaries():
    """Get kubernetes-related binaries that might be missed"""
    binaries = []
    
    # Try to find kubernetes client library binaries
    try:
        import kubernetes
        kubernetes_path = os.path.dirname(kubernetes.__file__)
        print(f"Found kubernetes at: {kubernetes_path}")
        
        # Look for any .so or .dylib files in kubernetes
        for root, dirs, files in os.walk(kubernetes_path):
            for file in files:
                if file.endswith(('.so', '.dylib', '.pyd')):
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, kubernetes_path)
                    binaries.append((src_path, f"kubernetes/{rel_path}"))
                    print(f"Adding kubernetes binary: {src_path}")
    except ImportError:
        print("Warning: kubernetes module not found during spec generation")
    
    return binaries

# Comprehensive hidden imports for macOS
hidden_imports = [
    # PyQt6 - Core GUI framework
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtSvg',
    'PyQt6.sip', 'PyQt6.QtOpenGL', 'PyQt6.QtPrintSupport',
    
    # Kubernetes client library
    'kubernetes', 'kubernetes.client', 'kubernetes.config', 'kubernetes.stream',
    'kubernetes.client.api', 'kubernetes.client.models', 
    'kubernetes.client.rest', 'kubernetes.client.configuration',
    'kubernetes.client.api_client', 'kubernetes.client.exceptions',
    'kubernetes.config.config_exception', 'kubernetes.config.kube_config',
    
    # YAML processing
    'yaml', 'yaml.loader', 'yaml.dumper', 'yaml.representer', 'yaml.resolver',
    
    # HTTP and networking
    'requests', 'requests.adapters', 'requests.auth', 'requests.cookies',
    'requests.models', 'requests.sessions', 'requests.utils',
    'urllib3', 'urllib3.util', 'urllib3.poolmanager',
    
    # System utilities
    'psutil', 'psutil._psplatform', 
    
    # Standard library modules that might be missed
    'logging', 'logging.handlers', 'json', 'datetime', 'threading',
    'subprocess', 'tempfile', 'shutil', 'base64', 'ssl', 'socket',
    'hashlib', 'hmac', 'binascii', 'zlib', 'gzip',
    
    # macOS-specific modules
    'Foundation', 'AppKit', 'Cocoa',
    
    # Certificate handling (important for kubernetes)
    'certifi', 'ssl', 'socket',
    
    # JSON Web Tokens (used by kubernetes)
    'jwt', 'cryptography', 'cryptography.hazmat',
    'cryptography.hazmat.primitives', 'cryptography.hazmat.backends',
    
    # Date/time handling
    'dateutil', 'dateutil.parser', 'dateutil.tz',
    
    # Additional PyQt6 modules that might be needed
    'PyQt6.QtNetwork', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebChannel',
]

# macOS-specific excludes to reduce bundle size
excludes = [
    'tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas',  # Heavy scientific libs
    'IPython', 'jupyter', 'notebook',  # Jupyter components
    'PyQt5', 'PySide2', 'PySide6',  # Other GUI frameworks
    'wx',  # wxPython
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=get_kubernetes_binaries(),
    datas=collect_data_files(),
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
    # macOS-specific options
    cipher=None,
)

# Remove duplicate entries and optimize
a.datas = list(set(a.datas))
a.binaries = list(set(a.binaries))

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Orchetrix',
    debug=False,  # Set to True for debugging
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disabled UPX for macOS compatibility
    console=False,  # GUI app
    disable_windowed_traceback=False,
    argv_emulation=True,  # Important for macOS
    target_arch=None,
    codesign_identity=None,  # Add code signing identity if available
    entitlements_file=None,  # Add entitlements file if needed
    icon=icon_path if icon_path and os.path.exists(icon_path) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,  # Disabled UPX for macOS compatibility
    upx_exclude=[],
    name='Orchetrix',
)

# Create macOS app bundle
app = BUNDLE(
    coll,
    name='Orchetrix.app',
    icon=icon_path if icon_path and os.path.exists(icon_path) else None,
    bundle_identifier='io.orchetrix.app',  # Unique bundle identifier
    version='0.0.2',
    info_plist={
        'CFBundleName': 'Orchetrix',
        'CFBundleDisplayName': 'Orchetrix',
        'CFBundleVersion': '0.0.2',
        'CFBundleShortVersionString': '0.0.2',
        'CFBundleIdentifier': 'io.orchetrix.app',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': 'ORCH',
        'LSMinimumSystemVersion': '10.15.0',  # Minimum macOS version
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
        'LSApplicationCategoryType': 'public.app-category.developer-tools',
        'NSHumanReadableCopyright': 'Copyright © 2024 Orchetrix Team. All rights reserved.',
    },
)