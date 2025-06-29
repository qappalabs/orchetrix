# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

# Get absolute path to icon
icon_path = os.path.abspath(os.path.join('icons', 'logoIcon.ico'))

def collect_icons():
    """Collect all icon files from the icons directory"""
    icon_files = []
    icons_dir = Path('icons')
    
    if icons_dir.exists():
        # Get all icon file types
        for ext in ['*.svg', '*.png', '*.ico', '*.jpg', '*.jpeg']:
            for icon_file in icons_dir.glob(ext):
                icon_files.append((str(icon_file), 'icons'))
        
        print(f"Found {len(icon_files)} icon files to include")
    else:
        print("Icons directory not found!")
    
    return icon_files

# Get all icon files
icon_data = collect_icons()

a = Analysis(
    ['main.py'],  # Only include main entry point
    pathex=[],
    binaries=[],
    datas=[
        # Include all collected icons explicitly
        *icon_data,
        # Only include directories that exist
        ('icons/*', 'icons'),  # Ensure all icon files are included
        ('images/*', 'images'),
    ],
    hiddenimports=[
        'PyQt6'
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'yaml',
        'logging',
        'datetime',
        'json',
        'subprocess',
        'psutil',
        'kubernetes',
        'requests',
        'kubernetes.client',
        'kubernetes.config',
        'urllib3',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
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