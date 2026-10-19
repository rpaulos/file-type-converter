# -*- mode: python ; coding: utf-8 -*-
# PyInstaller's recipe for FileTypeConverter.exe. Build with:
#     pyinstaller --noconfirm FileTypeConverter.spec

ICON = 'src/file_converter/icon.ico'

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[(ICON, 'file_converter')],   # the window icon, next to gui.py inside the .exe
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='FileTypeConverter',
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
    icon=ICON,                          # the .exe's own icon in File Explorer and the taskbar
)
