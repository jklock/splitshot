#!/usr/bin/env python3
"""Launch the actual packaged Electron artifact for the current platform and verify it starts."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DEFAULT_VALIDATION_SCRIPT = REPO / "scripts" / "testing" / "test_electron_app.py"


class InstalledArtifact:
    def __init__(self, executable: Path, cleanup_paths: list[Path] | None = None, env: dict[str, str] | None = None):
        self.executable = executable
        self.cleanup_paths = cleanup_paths or []
        self.env = env or {}

    def cleanup(self) -> None:
        for path in self.cleanup_paths:
            try:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                elif path.exists():
                    path.unlink()
            except Exception:
                continue


def _prepend_path(env: dict[str, str], *entries: str) -> dict[str, str]:
    merged = dict(env)
    current = merged.get("PATH", "")
    merged["PATH"] = os.pathsep.join([*(entry for entry in entries if entry), current] if current else [*(entry for entry in entries if entry)])
    return merged


def _media_tool_free_path(preferred_dir: Path) -> str:
    ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    filtered: list[str] = []
    seen: set[str] = set()
    for raw_entry in os.environ.get("PATH", "").split(os.pathsep):
        entry = raw_entry.strip()
        if not entry:
            continue
        candidate = Path(entry)
        if candidate.resolve() == preferred_dir.resolve():
            continue
        if (candidate / ffmpeg_name).exists() or (candidate / ffprobe_name).exists():
            continue
        if entry not in seen:
            filtered.append(entry)
            seen.add(entry)
    return os.pathsep.join([str(preferred_dir), *filtered])


def _run(command: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd or REPO,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _default_artifact() -> Path:
    build_dir = REPO / "electron" / "build"
    if sys.platform == "darwin":
        candidates = sorted(build_dir.glob("*.dmg"))
    elif sys.platform == "win32":
        candidates = sorted(build_dir.glob("*.exe"))
    else:
        candidates = sorted(build_dir.glob("*.AppImage"))
    if not candidates:
        raise FileNotFoundError("No packaged artifact found in electron/build/")
    return candidates[0]


def _install_windows_artifact(artifact: Path) -> InstalledArtifact:
    _run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Start-Process -FilePath '{artifact}' -ArgumentList '/S' -Wait",
        ]
    )
    locator = (
        "$paths = @(); "
        "if ($env:LOCALAPPDATA) { $paths += (Join-Path $env:LOCALAPPDATA 'Programs') }; "
        "if ($env:ProgramFiles) { $paths += $env:ProgramFiles }; "
        "if (${env:ProgramFiles(x86)}) { $paths += ${env:ProgramFiles(x86)} }; "
        "$match = Get-ChildItem -Path $paths -Filter SplitShot.exe -File -Recurse -ErrorAction SilentlyContinue | "
        "Select-Object -First 1 -ExpandProperty FullName; "
        "if ($match) { Write-Output $match }"
    )
    result = _run(["powershell", "-NoProfile", "-Command", locator])
    executable = Path(result.stdout.strip())
    if not executable.exists():
        raise FileNotFoundError("Installed SplitShot.exe not found after NSIS install")
    ffmpeg_dir = executable.parent / "resources" / "bundle" / "src" / "splitshot" / "resources" / "ffmpeg" / "windows"
    env = {"PATH": _media_tool_free_path(ffmpeg_dir)}
    env["SPLITSHOT_PACKAGED_FFPROBE"] = str(ffmpeg_dir / "ffprobe.exe")
    return InstalledArtifact(executable=executable, env=env)


def _install_macos_artifact(artifact: Path) -> InstalledArtifact:
    mount_dir = Path(tempfile.mkdtemp(prefix="splitshot-dmg-mount-"))
    app_copy_root = Path(tempfile.mkdtemp(prefix="splitshot-dmg-app-"))
    _run(
        [
            "hdiutil",
            "attach",
            str(artifact),
            "-nobrowse",
            "-readonly",
            "-mountpoint",
            str(mount_dir),
        ]
    )
    try:
        apps = sorted(mount_dir.glob("*.app"))
        if not apps:
            raise FileNotFoundError("No .app found inside mounted DMG")
        mounted_app = apps[0]
        copied_app = app_copy_root / mounted_app.name
        _run(["ditto", str(mounted_app), str(copied_app)])
    finally:
        subprocess.run(
            ["hdiutil", "detach", str(mount_dir)],
            check=False,
            capture_output=True,
            text=True,
        )
    executable = copied_app / "Contents" / "MacOS" / "SplitShot"
    if not executable.exists():
        raise FileNotFoundError(f"Mounted DMG app executable not found at {executable}")
    ffmpeg_dir = copied_app / "Contents" / "Resources" / "bundle" / "src" / "splitshot" / "resources" / "ffmpeg" / "macos"
    env = {"PATH": _media_tool_free_path(ffmpeg_dir)}
    env["SPLITSHOT_PACKAGED_FFPROBE"] = str(ffmpeg_dir / "ffprobe")
    return InstalledArtifact(executable=executable, cleanup_paths=[mount_dir, app_copy_root], env=env)


def _install_linux_artifact(artifact: Path) -> InstalledArtifact:
    copied_artifact = Path(tempfile.mkdtemp(prefix="splitshot-appimage-")) / artifact.name
    shutil.copy2(artifact, copied_artifact)
    copied_artifact.chmod(copied_artifact.stat().st_mode | stat.S_IXUSR)
    extracted_root = Path(tempfile.mkdtemp(prefix="splitshot-appimage-extract-"))
    _run([str(copied_artifact), "--appimage-extract"], cwd=extracted_root)
    squashfs_root = extracted_root / "squashfs-root"
    ffmpeg_dir = squashfs_root / "resources" / "bundle" / "src" / "splitshot" / "resources" / "ffmpeg" / "linux"
    env = {"APPIMAGE_EXTRACT_AND_RUN": "1"}
    env["PATH"] = _media_tool_free_path(ffmpeg_dir)
    env["SPLITSHOT_PACKAGED_FFPROBE"] = str(ffmpeg_dir / "ffprobe")
    return InstalledArtifact(executable=copied_artifact, cleanup_paths=[copied_artifact.parent, extracted_root], env=env)


def _install_artifact(artifact: Path) -> InstalledArtifact:
    if sys.platform == "darwin":
        if artifact.suffix.lower() != ".dmg":
            raise ValueError(f"Expected DMG artifact on macOS, got {artifact.name}")
        return _install_macos_artifact(artifact)
    if sys.platform == "win32":
        if artifact.suffix.lower() != ".exe":
            raise ValueError(f"Expected NSIS installer on Windows, got {artifact.name}")
        return _install_windows_artifact(artifact)
    if artifact.suffix.lower() != ".appimage":
        raise ValueError(f"Expected AppImage artifact on Linux, got {artifact.name}")
    return _install_linux_artifact(artifact)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=None, help="Packaged artifact to validate")
    parser.add_argument(
        "--script",
        type=Path,
        default=DEFAULT_VALIDATION_SCRIPT,
        help="Validation script that accepts --app <installed executable>",
    )
    args = parser.parse_args()

    artifact = (args.artifact or _default_artifact()).resolve()
    if not artifact.exists():
        print(f"FAIL: artifact not found at {artifact}", file=sys.stderr)
        return 1
    validation_script = args.script.resolve()
    if not validation_script.exists():
        print(f"FAIL: validation script not found at {validation_script}", file=sys.stderr)
        return 1

    installed: InstalledArtifact | None = None
    try:
        installed = _install_artifact(artifact)
        env = {**os.environ, **installed.env}
        command = [sys.executable, str(validation_script), "--app", str(installed.executable)]
        result = subprocess.run(command, cwd=REPO, env=env, check=False)
        return int(result.returncode)
    finally:
        if installed is not None:
            installed.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
