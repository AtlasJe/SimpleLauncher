# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

PYTHON_ROOT = sys.base_prefix
PYTHON_DLLS = os.path.join(PYTHON_ROOT, 'DLLs')
PYTHON_TCL = os.path.join(PYTHON_ROOT, 'tcl')

a = Analysis(
    ['launcher_gui.pyw'],
    pathex=[],
    binaries=[
        (os.path.join(PYTHON_DLLS, '_tkinter.pyd'), '.'),
        (os.path.join(PYTHON_DLLS, 'tcl86t.dll'), '.'),
        (os.path.join(PYTHON_DLLS, 'tk86t.dll'), '.'),
    ],
    datas=[
        ('../resources/icon.ico', '.'),
        ('../resources/icon.svg', '.'),
        ('../resources/sounds', 'sounds'),
        ('../resources/Nunito', 'Nunito'),
        ('../resources/MaterialSymbolsOutlined.ttf', '.'),
        (PYTHON_TCL, 'tcl'),
    ],
    hiddenimports=collect_submodules('tkinter'),
    hookspath=['../resources/hooks'],
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
    a.binaries,
    a.datas,
    [],
    name='SimpleLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['../resources/icon.ico'],
)
