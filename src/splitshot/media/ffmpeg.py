from __future__ import annotations

import json
import subprocess
from pathlib import Path


class MediaError(RuntimeError):
    pass


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(command, check=False, capture_output=True, text=True)
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
    return ["ffmpeg", "-y", *command]
