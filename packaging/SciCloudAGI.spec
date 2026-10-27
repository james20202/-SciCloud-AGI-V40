# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a standalone macOS SciCloud AGI V40 client.

Build it with packaging/build_macos.sh (macOS only). Do NOT run this
spec by hand on another platform and expect a macOS bundle.

Design decisions, all deliberate:

- onedir, not onefile: PySide6 in onefile mode is slow to start and
  fragile around Qt plugins. onedir keeps the Qt plugins next to the
  executable, which is what PySide6's PyInstaller hooks expect.
- windowed (console=False): double-clicking the .app must not open a
  Terminal window. Logs still go to the app's data directory, not to
  a terminal the user never sees.
- No user data is bundled. projects/, data/, output/, logs/ and
  backups/ are deliberately NOT listed in datas: the packaged app
  resolves them at runtime via core/config.py (SCICLOUD_HOME, or
  ~/SciCloud AGI V40 when frozen), never inside the .app bundle.
- Only one shipped code resource is bundled: ui/assets/bg_main.png,
  which ui/pages/production_dashboard.py loads via a path relative
  to its own file. Under PyInstaller that file lives in
  _internal/ui/pages/, so its dirname(dirname()) is _internal/ui,
  and datas destination 'ui/assets' puts bg_main.png exactly where
  that code looks for it. The load is guarded by os.path.exists(),
  so a missing image degrades to no background instead of a crash.
- No icon is declared: the repository ships no .icns file, and
  inventing one here would only break the build. macOS falls back
  to the generic app icon until a real icon is added.
- This is an unsigned, personal-use build. There is no signing,
  notarization, DMG or distribution step in this spec.
"""

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # Code resource only (see module docstring). Never user data.
        (os.path.join(ROOT, "ui", "assets"), "ui/assets"),
    ],
    hiddenimports=[
        # PySide6's hooks normally find these, but the app imports
        # QtWidgets/QtGui/QtCore from dozens of pages, so pin them
        # explicitly rather than relying on hook coverage alone.
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Nothing the app imports. Keeps the bundle smaller and avoids
        # pulling in test-only / desktop-toolkit baggage.
        "tkinter",
        "matplotlib",
        "pytest",
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
    name="SciCloudAGI",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SciCloud AGI V40",
)

app = BUNDLE(
    coll,
    name="SciCloud AGI V40.app",
    icon=None,
    bundle_identifier="com.scicloud.agi.v40",
    info_plist={
        "CFBundleName": "SciCloud AGI V40",
        "CFBundleDisplayName": "SciCloud AGI V40",
        "CFBundleShortVersionString": "40.412.0",
        "CFBundleVersion": "40.412.0",
        "LSMinimumSystemVersion": "13.0",
        "NSHighResolutionCapable": True,
    },
)
