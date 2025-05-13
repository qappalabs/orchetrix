# -*- mode: python ; coding: utf-8 -*-
import os

# Linux doesn't use Windows-specific version info
icon_path = os.path.abspath(os.path.join('icons', 'logoIcon.png'))  # Use PNG for Linux

a = Analysis(
    ['main.py', 'log_handler.py', 'subprocess_patch.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icons/*.svg', 'icons'),
        ('icons/*.png', 'icons'),
        ('icons/*.ico', 'icons'),  # Keep ico files in case they're referenced in code
        ('images', 'images'),
        ('logos', 'logos')
    ],
    hiddenimports=[
        'PyQt6.QtCore', 
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets', 
        'PyQt6.QtSvg', 
        'yaml',
        'logging',
        'datetime',
        'json',
        'subprocess'
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
    console=False,  # Keep console=False for windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,  # Optional - Linux handles icons differently
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