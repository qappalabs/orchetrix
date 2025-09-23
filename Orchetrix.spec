# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Get absolute path to icon
icon_path = os.path.abspath(os.path.join('Icons', 'logoIcon.ico'))
if not os.path.exists(icon_path):
    icon_path = os.path.abspath(os.path.join('Icons', 'logoIcon.png'))
    if not os.path.exists(icon_path):
        icon_path = None

def collect_data_files():
    """Collect all necessary data files"""
    data_files = []
    
    # Add resource directories
    resource_dirs = ['Icons', 'Images', 'UI', 'Pages', 'Utils', 'Services', 'Base_Components']
    for dir_name in resource_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            data_files.append((dir_name, dir_name))
    
    return data_files

# Comprehensive hidden imports
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
