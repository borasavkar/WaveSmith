# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for WaveSmith (one-folder build).
# Use build.py instead of calling this directly — it also copies FFmpeg and makes the portable zip.

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets/app_icon.ico', 'assets'),
        ('assets/app_icon.png', 'assets'),
        ('assets/check.svg', 'assets'),
    ],
    hiddenimports=['PyQt6.QtMultimedia', 'PyQt6.sip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'PIL', 'cv2',
              'PyQt6.QtWebEngineCore', 'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtPdf',
              'PyQt6.QtBluetooth', 'PyQt6.QtPositioning', 'PyQt6.QtSensors'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WaveSmith',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/app_icon.ico',
    version='build/version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='WaveSmith',
)
