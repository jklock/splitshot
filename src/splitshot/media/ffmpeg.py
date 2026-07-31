from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from functools import lru_cache
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


def run_ffmpeg(command: list[str], log_callback: Callable[[str], None] | None = None) -> None:
    if log_callback is None:
        _run(["ffmpeg", "-y", *command])
        return
    resolved_command = ffmpeg_command(command)
    log_callback(f"FFmpeg command: {shlex.join(resolved_command)}")
    process = subprocess.Popen(
        resolved_command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    stderr_lines: list[str] = []
    if process.stderr is not None:
        for raw_line in process.stderr:
            line = raw_line.rstrip()
            if not line:
                continue
            stderr_lines.append(line)
            log_callback(line)
    return_code = process.wait()
    if return_code != 0:
        raise MediaError("\n".join(stderr_lines[-40:]) or "FFmpeg command failed")


def ffmpeg_command(command: list[str]) -> list[str]:
    return [resolve_media_binary("ffmpeg"), "-y", *command]


def trim_video(
    source_path: str,
    output_path: str,
    start_s: float | None = None,
    end_s: float | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> None:
    if not source_path:
        raise MediaError("source_path is required for trim")
    if not output_path:
        raise MediaError("output_path is required for trim")
    if start_s is None and end_s is None:
        raise MediaError("At least one of start_s or end_s is required for trim")
    normalized_start_s = max(0.0, float(start_s or 0.0))
    normalized_end_s = None if end_s is None else float(end_s)
    if normalized_end_s is not None and normalized_end_s <= normalized_start_s:
        raise MediaError("end_s must be greater than start_s")
    retained_duration_s = (
        None if normalized_end_s is None else normalized_end_s - normalized_start_s
    )
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = []
    if normalized_start_s > 0:
        cmd.extend(["-ss", f"{normalized_start_s:.3f}"])
    cmd.extend(["-i", source_path])
    if retained_duration_s is not None:
        cmd.extend(["-t", f"{retained_duration_s:.3f}"])
    cmd.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            output_path,
        ]
    )
    try:
        run_ffmpeg(cmd, log_callback=log_callback)
    except MediaError as exc:
        output_path_obj.unlink(missing_ok=True)
        raise MediaError(f"Trim failed for {source_path} -> {output_path}: {exc}") from exc
