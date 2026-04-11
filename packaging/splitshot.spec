# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path.cwd()


def platform_key() -> str:
    if sys.platform.startswith("darwin"):
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def binary_name(tool: str) -> str:
    if sys.platform.startswith("win"):
        return f"{tool}.exe"
    return tool


def media_binaries() -> list[tuple[str, str]]:
    platform = platform_key()
    roots: list[Path] = []
    if override := os.environ.get("SPLITSHOT_FFMPEG_DIR"):
        roots.append(Path(override))
    roots.append(ROOT / "src" / "splitshot" / "resources" / "ffmpeg" / platform)
    binaries: list[tuple[str, str]] = []
    for tool in ("ffmpeg", "ffprobe"):
        executable = binary_name(tool)
        source = next((root / executable for root in roots if (root / executable).exists()), None)
        if source is None:
            found = shutil.which(executable)
            if found:
                source = Path(found)
        if source is None:
            raise SystemExit(f"Missing {executable}. See packaging/README.md.")
        binaries.append((str(source), f"splitshot/resources/ffmpeg/{platform}"))
    return binaries


datas = [
    (
        str(ROOT / "src" / "splitshot" / "browser" / "static"),
        "splitshot/browser/static",
    ),
    (
        str(ROOT / "src" / "splitshot" / "resources"),
        "splitshot/resources",
    ),
]

hiddenimports = collect_submodules("PySide6")

a = Analysis(
    [str(ROOT / "src" / "splitshot" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=media_binaries(),
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="SplitShot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name="SplitShot",
)

if sys.platform.startswith("darwin"):
    app = BUNDLE(
        coll,
        name="SplitShot.app",
        icon=None,
        bundle_identifier="com.splitshot.app",
        info_plist={
            "NSHighResolutionCapable": "True",
            "NSRequiresAquaSystemAppearance": "False",
        },
    )
