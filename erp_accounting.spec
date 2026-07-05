# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file — تحويل المشروع إلى ملف تنفيذي

Usage:
    pyinstaller erp_accounting.spec

Output: dist/ERP_Accounting/ (folder) or dist/ERP_Accounting.exe (single file)
"""

import os
from pathlib import Path

block_cipher = None

# Collect all data files (fonts, .ui files, etc.)
datas = []
fonts_dir = Path("assets/fonts")
if fonts_dir.exists():
    for font_file in fonts_dir.glob("*.ttf"):
        datas.append((str(font_file), "fonts"))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'sqlalchemy.dialects.sqlite',
        'bcrypt',
        'reportlab',
        'openpyxl',
        'PIL',
        'loguru',
        'qdarktheme',
        'qtawesome',
        'arabic_reshaper',
        'bidi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
        'numpy',
        'scipy',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ERP_Accounting',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application — no console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available
)
