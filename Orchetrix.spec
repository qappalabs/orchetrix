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
    """Collect all necessary data files"""
    data_files = []
    
    # Add resource directories
    resource_dirs = ['Icons', 'Images', 'UI', 'Pages', 'Utils', 'Services', 'Base_Components']
    for dir_name in resource_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            data_files.append((dir_name, dir_name))
    
    return data_files
# Comprehensive hidden imports list
hidden_imports = [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtSvg',
    'kubernetes', 'kubernetes.client', 'kubernetes.config', 'kubernetes.stream',
    'yaml', 'requests', 'psutil', 'logging', 'json', 'datetime', 'threading',
    'subprocess', 'tempfile', 'shutil', 'base64', 'ssl', 'socket'
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=collect_data_files(),
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if icon_path and os.path.exists(icon_path) else None,
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
