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
# Comprehensive hidden imports list
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
        # Python modules to exclude from bundle (excludes applies only to Python modules)
        # PyInstaller excludes the package and all submodules when given top-level name
        'matplotlib',
        'pandas',
        'numpy',
        'scipy',

        # Development/testing modules (not needed in production)
        'IPython', 'jupyter', 'notebook',
        'tkinter', 'unittest', 'test', 'tests',
        'distutils', 'setuptools', 'sphinx', 'docutils'
    ],
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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if icon_path and os.path.exists(icon_path) else None,
    # Additional Windows configuration to prevent subprocess terminal windows
    runtime_tmpdir=None,
    # Ensure subprocess calls don't create visible windows
    uac_admin=False,
    uac_uiaccess=False,
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
