# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Get absolute path to icon
icon_path = os.path.abspath(os.path.join('icons', 'logoIcon.ico'))

def collect_icons():
    """Collect all icon files from the icons directory"""
    icon_files = []
    icons_dir = Path('icons')
    
    if icons_dir.exists():
        # Get all icon file types
        for ext in ['*.svg', '*.png', '*.ico', '*.jpg', '*.jpeg', '*.gif']:
            for icon_file in icons_dir.glob(ext):
                icon_files.append((str(icon_file), 'icons'))
        
        print(f"Found {len(icon_files)} icon files to include")
    else:
        print("Icons directory not found!")
    
    return icon_files

def collect_ui_files():
    """Collect UI-related files"""
    ui_files = []
    
    # Collect any additional UI files if they exist
    ui_dirs = ['images', 'logos', 'styles']
    for ui_dir in ui_dirs:
        ui_path = Path(ui_dir)
        if ui_path.exists():
            for file in ui_path.rglob('*'):
                if file.is_file():
                    ui_files.append((str(file), ui_dir))
    
    return ui_files

# Get all resource files
icon_data = collect_icons()
ui_data = collect_ui_files()
def collect_data_files():
    """Collect all data files, filtering out non-existent directories"""
    data_files = []
    
    # Add collected icons and UI files
    data_files.extend(icon_data)
    data_files.extend(ui_data)
    
    # Add directories that exist
    directories_to_check = [
        ('icons', 'icons'),
        ('images', 'images'), 
        ('logos', 'logos'),
        ('UI', 'UI'),
        ('Pages', 'Pages'),
        ('utils', 'utils'),
        ('base_components', 'base_components'),
    ]
    
    for src_dir, dest_dir in directories_to_check:
        if os.path.exists(src_dir) and os.path.isdir(src_dir):
            data_files.append((src_dir, dest_dir))
            print(f"Including directory: {src_dir} -> {dest_dir}")
        else:
            print(f"Skipping missing directory: {src_dir}")
    
    return data_files
# Comprehensive hidden imports list
hidden_imports = [
    # PyQt6 modules
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtSvg',
    'PyQt6.QtSvgWidgets',
    'PyQt6.sip',
    
    # Standard library modules
    'yaml',
    'logging',
    'datetime',
    'json',
    'subprocess',
    'threading',
    'socket',
    'time',
    'os',
    'sys',
    'traceback',
    'gc',
    'webbrowser',
    'tempfile',
    'shutil',
    'random',
    'string',
    'math',
    'queue',
    'weakref',
    'functools',
    'typing',
    'dataclasses',
    'enum',
    're',
    'platform',
    'select',
    
    # Third-party modules
    'requests',
    'requests.auth',
    'requests.models',
    'requests.sessions',
    'requests.adapters',
    'requests.exceptions',
    'urllib3',
    'urllib3.util',
    'urllib3.util.retry',
    'urllib3.exceptions',
    'certifi',
    'psutil',
    
    # Kubernetes client modules
    'kubernetes',
    'kubernetes.client',
    'kubernetes.client.rest',
    'kubernetes.client.api',
    'kubernetes.client.models',
    'kubernetes.client.api_client',
    'kubernetes.client.configuration',
    'kubernetes.config',
    'kubernetes.config.config_exception',
    'kubernetes.stream',
    'kubernetes.watch',
    
    # Kubernetes API modules
    'kubernetes.client.CoreV1Api',
    'kubernetes.client.AppsV1Api',
    'kubernetes.client.NetworkingV1Api',
    'kubernetes.client.StorageV1Api',
    'kubernetes.client.RbacAuthorizationV1Api',
    'kubernetes.client.BatchV1Api',
    'kubernetes.client.AutoscalingV1Api',
    'kubernetes.client.CustomObjectsApi',
    'kubernetes.client.VersionApi',
    'kubernetes.client.ApiextensionsV1Api',
    'kubernetes.client.AdmissionregistrationV1Api',
    'kubernetes.client.CoordinationV1Api',
    'kubernetes.client.PolicyV1Api',
    'kubernetes.client.SchedulingV1Api',
    'kubernetes.client.NodeV1Api',
    'kubernetes.client.EventsV1Api',
    
    # Additional Kubernetes modules
    'kubernetes.client.V1Pod',
    'kubernetes.client.V1Service',
    'kubernetes.client.V1Deployment',
    'kubernetes.client.V1Node',
    'kubernetes.client.V1Namespace',
    'kubernetes.client.V1Event',
    'kubernetes.client.V1DeleteOptions',
    
    # PyYAML
    'yaml.loader',
    'yaml.dumper',
    'yaml.constructor',
    'yaml.representer',
    'yaml.resolver',
    'yaml.scanner',
    'yaml.parser',
    'yaml.composer',
    'yaml.emitter',
    'yaml.serializer',
    
    # Additional networking modules
    'socket',
    'ssl',
    'http',
    'http.client',
    'http.server',
    
    # Date/time modules
    'datetime',
    'time',
    'calendar',
    
    # Logging modules
    'logging.handlers',
    'logging.config',
    
    # File handling
    'pathlib',
    'glob',
    'fnmatch',
    
    # JSON handling
    'json.encoder',
    'json.decoder',
    
    # Base64 and encoding
    'base64',
    'encodings',
    'encodings.utf_8',
    'encodings.ascii',
    
    # Collections
    'collections',
    'collections.abc',
    
    # Crypto/security (for kubernetes)
    'cryptography',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.backends',
    'cryptography.x509',
    
    # Additional dependencies that might be dynamically imported
    'pkg_resources',
    'setuptools',
    'six',
    'google',
    'google.auth',
    'oauthlib',
    'cachetools',
    'pyasn1',
    'rsa',
]

a = Analysis(
    ['main.py'],  # Main entry point
    pathex=['.'],  # Add current directory to path
    binaries=[],
    datas=collect_data_files(),  # Use the function that properly filters None values
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Filter out None values from datas
a.datas = [(dest, source, kind) for dest, source, kind in a.datas if dest is not None]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Orchetrix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging if needed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Orchetrix',
)
