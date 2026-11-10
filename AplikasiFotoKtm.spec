
# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_all

# ==========================================
# CONFIGURATION
# ==========================================

APP_NAME = "AplikasiFotoKtm"
ENTRY_SCRIPT = "main.py"

datas = []
binaries = []
hiddenimports = []

# ==========================================
# COLLECT PYTHON PACKAGES
# ==========================================

packages = [
    "flet",
    "cv2",
    "httpx",
]

for package in packages:
    d, b, h = collect_all(package)

    datas.extend(d)
    binaries.extend(b)
    hiddenimports.extend(h)

# ==========================================
# GPHOTO2
# ==========================================
# Aplikasi menggunakan CLI sistem `/usr/bin/gphoto2` via subprocess.
# Jangan mem-bundle `gphoto2` Python wheel karena membawa `libgphoto2.so.6`
# dan `libgphoto2_port.so.12` ke dalam `_internal/` yang membuat `/usr/bin/gphoto2`
# gagal memuat driver USB sistem (Devices found: -2).

# ==========================================
# ASSETS
# ==========================================

assets_dir = os.path.abspath("assets")

if os.path.isdir(assets_dir):

    for root, dirs, files in os.walk(assets_dir):

        for file in files:

            source = os.path.join(root, file)

            destination = os.path.relpath(
                root,
                os.path.dirname(assets_dir)
            )

            datas.append((
                source,
                destination
            ))

# ==========================================
# HIDDEN IMPORTS
# ==========================================

hiddenimports.extend([
    "gphoto2",

    "cv2",

    "httpx",
    "httpcore",
    "anyio",
    "sniffio",
    "certifi",

    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
])

# ==========================================
# EXCLUDES
# ==========================================

excludes = [
    "flet.testing",
]

# ==========================================
# REMOVE DUPLICATES
# ==========================================

datas = list(dict.fromkeys(datas))
binaries = list(dict.fromkeys(binaries))
hiddenimports = list(dict.fromkeys(hiddenimports))

# ==========================================
# VALIDATE DATAS
# ==========================================

for item in datas:

    if not isinstance(item, tuple) or len(item) != 2:

        raise ValueError(
            f"Invalid datas entry: {item!r}"
        )

# ==========================================
# ANALYSIS
# ==========================================

a = Analysis(
    [ENTRY_SCRIPT],

    pathex=["."],

    binaries=binaries,

    datas=datas,

    hiddenimports=hiddenimports,

    hookspath=[],

    hooksconfig={},

    runtime_hooks=[],

    excludes=excludes,

    noarchive=False,
)

# ==========================================
# PYZ
# ==========================================

pyz = PYZ(a.pure)

# ==========================================
# EXECUTABLE
# ==========================================

exe = EXE(
    pyz,

    a.scripts,

    [],

    exclude_binaries=True,

    name=APP_NAME,

    debug=False,

    bootloader_ignore_signals=False,

    strip=False,

    upx=False,

    console=False,
)

# ==========================================
# COLLECT - ONEDIR
# ==========================================

coll = COLLECT(
    exe,

    a.binaries,

    a.datas,

    strip=False,

    upx=False,

    name=APP_NAME,
)
