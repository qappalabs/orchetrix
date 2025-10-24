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
    """Collect only essential data files (excluding logs, sample screenshots, and development files)"""
    data_files = []
    
    # Add Icons directory (essential for UI)
    if os.path.exists('Icons') and os.path.isdir('Icons'):
        data_files.append(('Icons', 'Icons'))
    
    # Add only essential images (exclude screenshot samples)
    if os.path.exists('Images') and os.path.isdir('Images'):
        essential_images = [
            'Orchetrix_splash.png',  # App splash screen
            'SignupBG.png',          # Background
            'checkmark.png',         # UI element
            'github_icon.png',       # Icon
            'google_icon.png'        # Icon
        ]
        for img in essential_images:
            img_path = os.path.join('Images', img)
            if os.path.exists(img_path):
                data_files.append((img_path, 'Images'))
    
    # Add code directories (these don't contain data files)
    code_dirs = ['UI', 'Pages', 'Utils', 'Services', 'Base_Components']
    for dir_name in code_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            data_files.append((dir_name, dir_name))
    
    return data_files

# Comprehensive hidden imports
hidden_imports = [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtSvg',
    'kubernetes', 'kubernetes.client', 'kubernetes.config', 'kubernetes.stream',
    'yaml', 'requests', 'psutil', 'logging', 'json', 'datetime', 'threading',
    'tempfile', 'shutil', 'base64', 'ssl', 'socket', 'subprocess', 'time',
    'dataclasses', 'functools', 'select', 'asyncio'
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
    excludes=[
        'logs', 'data', '.git', '__pycache__', 
        '*.log', '*.tmp', 'build_*', 'windows_*',
        'README.md', '.gitignore'
    ],
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
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='Orchetrix',
)
