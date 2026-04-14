from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class MediaError(RuntimeError):
    pass


def _platform_key() -> str:
    if sys.platform.startswith("darwin"):
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def _binary_name(tool: str) -> str:
    if sys.platform.startswith("win") and not tool.endswith(".exe"):
        return f"{tool}.exe"
    return tool


def _resource_roots() -> list[Path]:
    roots: list[Path] = []
    if override := os.environ.get("SPLITSHOT_FFMPEG_DIR"):
        roots.append(Path(override))
    roots.append(Path(__file__).resolve().parents[1] / "resources" / "ffmpeg")
    return roots


def resolve_media_binary(tool: str) -> str:
    executable = _binary_name(tool)
    platform = _platform_key()
    for root in _resource_roots():
        for candidate in (root / platform / executable, root / executable):
            if candidate.exists() and candidate.is_file():
                return str(candidate)
    resolved = shutil.which(executable)
    if resolved:
        return resolved
    raise MediaError(
        f"Could not find {tool}. Add {executable} to PATH, set SPLITSHOT_FFMPEG_DIR, "
        f"or place it under splitshot/resources/ffmpeg/{platform}."
    )


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    resolved_command = command[:]
    if resolved_command and resolved_command[0] in {"ffmpeg", "ffprobe"}:
        resolved_command[0] = resolve_media_binary(resolved_command[0])
    process = subprocess.run(resolved_command, check=False, capture_output=True, text=True)
    if process.returncode != 0:
        raise MediaError(process.stderr.strip() or "FFmpeg command failed")
    return process


def run_ffprobe_json(input_path: Path) -> dict:
    process = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(input_path),
        ]
    )
    return json.loads(process.stdout)


def run_ffmpeg(command: list[str]) -> None:
    _run(["ffmpeg", "-y", *command])


def ffmpeg_command(command: list[str]) -> list[str]:
    return [resolve_media_binary("ffmpeg"), "-y", *command]
