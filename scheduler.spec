# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('src/db/schema.sql', 'src/db'),
        ('src', 'src'),
    ],
    hiddenimports=[
        'ortools.sat.python.cp_model',
        'ortools',
        'flask',
        'openpyxl',
        'jinja2',
        'werkzeug',
        'click',
        'pandas',
        'numpy',
        'python_dateutil',
        'six',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NanaScheduler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NanaScheduler',
)
