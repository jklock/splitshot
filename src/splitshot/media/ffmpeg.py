from __future__ import annotations

from functools import lru_cache
import json
import shutil
import subprocess
import sys
from pathlib import Path


class MediaError(RuntimeError):
    pass

def _binary_name(tool: str) -> str:
    if sys.platform.startswith("win") and not tool.endswith(".exe"):
        return f"{tool}.exe"
    return tool


def resolve_media_binary(tool: str) -> str:
    executable = _binary_name(tool)
    resolved = shutil.which(executable)
    if resolved:
        return resolved
    raise MediaError(f"Could not find {tool}. Add {executable} to PATH.")


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    resolved_command = command[:]
    if resolved_command and resolved_command[0] in {"ffmpeg", "ffprobe"}:
        resolved_command[0] = resolve_media_binary(resolved_command[0])
    process = subprocess.run(resolved_command, check=False, capture_output=True, text=True)
    if process.returncode != 0:
        raise MediaError(process.stderr.strip() or "FFmpeg command failed")
    return process


@lru_cache(maxsize=64)
def _run_ffprobe_json_cached(path_str: str, file_size: int, modified_ns: int) -> str:
    process = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            path_str,
        ]
    )
    return process.stdout


def run_ffprobe_json(input_path: Path) -> dict:
    resolved_path = Path(input_path)
    try:
        stats = resolved_path.stat()
    except OSError:
        process = _run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(resolved_path),
            ]
        )
        return json.loads(process.stdout)
    payload = _run_ffprobe_json_cached(str(resolved_path), stats.st_size, stats.st_mtime_ns)
    return json.loads(payload)


def run_ffmpeg(command: list[str]) -> None:
    _run(["ffmpeg", "-y", *command])


def ffmpeg_command(command: list[str]) -> list[str]:
    return [resolve_media_binary("ffmpeg"), "-y", *command]
