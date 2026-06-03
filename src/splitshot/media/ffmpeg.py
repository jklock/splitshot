from __future__ import annotations

from functools import lru_cache
import json
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from splitshot.domain.models import (
    ExportFrameRate,
    ExportQuality,
    ExportSettings,
    ExportVideoCodec,
)


_FASTSTART_OUTPUT_EXTENSIONS = {".m4v", ".mov", ".mp4"}


class MediaError(RuntimeError):
    pass


def _quality_crf(quality: ExportQuality) -> str:
    return {
        ExportQuality.HIGH: "18",
        ExportQuality.MEDIUM: "23",
        ExportQuality.LOW: "28",
    }[quality]


def _codec_name(codec: ExportVideoCodec) -> str:
    return {
        ExportVideoCodec.H264: "libx264",
        ExportVideoCodec.HEVC: "libx265",
    }[codec]


def _trim_output_fps(source_fps: float | None, export_settings: ExportSettings) -> float | None:
    if export_settings.frame_rate == ExportFrameRate.FPS_30:
        return 30.0
    if export_settings.frame_rate == ExportFrameRate.FPS_60:
        return 60.0
    if source_fps is None:
        return None
    return float(source_fps) if float(source_fps) > 0 else None


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


def generate_trimmed_derivative(
    input_path: Path,
    output_path: Path,
    *,
    start_ms: int = 0,
    end_ms: int | None = None,
    source_fps: float | None = None,
    export_settings: ExportSettings | None = None,
) -> Path:
    resolved_input = Path(input_path).expanduser().resolve(strict=False)
    resolved_output = Path(output_path).expanduser().resolve(strict=False)
    if not resolved_input.is_file():
        raise MediaError(f"Trim source not found: {resolved_input}")

    safe_start_ms = max(0, int(start_ms))
    safe_end_ms = None if end_ms is None else max(0, int(end_ms))
    if safe_end_ms is not None and safe_end_ms <= safe_start_ms:
        raise ValueError("Trim end must be greater than trim start.")

    effective_settings = export_settings or ExportSettings()
    output_fps = _trim_output_fps(source_fps, effective_settings)
    output_duration_seconds = (
        None if safe_end_ms is None else (safe_end_ms - safe_start_ms) / 1000.0
    )

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = resolved_output.with_name(
        f".{resolved_output.stem}.{uuid4().hex}{resolved_output.suffix}"
    )

    command = [
        "-i",
        str(resolved_input),
        "-ss",
        f"{safe_start_ms / 1000.0:.3f}",
        *(["-t", f"{output_duration_seconds:.3f}"] if output_duration_seconds is not None else []),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        _codec_name(effective_settings.video_codec),
        "-preset",
        effective_settings.ffmpeg_preset,
        "-crf",
        _quality_crf(effective_settings.quality),
        "-b:v",
        f"{effective_settings.video_bitrate_mbps:g}M",
        *(["-r", f"{output_fps:.3f}"] if output_fps is not None else []),
        "-pix_fmt",
        "yuv420p",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-c:a",
        effective_settings.audio_codec.value,
        "-ar",
        str(effective_settings.audio_sample_rate),
        "-b:a",
        f"{effective_settings.audio_bitrate_kbps}k",
        *(
            ["-movflags", "+faststart"]
            if resolved_output.suffix.lower() in _FASTSTART_OUTPUT_EXTENSIONS
            else []
        ),
        "-shortest",
        str(temporary_output),
    ]

    try:
        run_ffmpeg(command)
        temporary_output.replace(resolved_output)
    finally:
        if temporary_output.exists():
            temporary_output.unlink(missing_ok=True)

    return resolved_output
