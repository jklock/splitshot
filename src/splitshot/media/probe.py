from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from splitshot.domain.models import VideoAsset
from splitshot.media.ffmpeg import run_ffprobe_json
from splitshot.utils.time import seconds_to_ms


def _parse_fraction(value: str | None, fallback: float) -> float:
    if not value or value in {"0/0", "N/A"}:
        return fallback
    return float(Fraction(value))


def probe_video(path: str | Path) -> VideoAsset:
    input_path = Path(path)
    metadata = run_ffprobe_json(input_path)
    streams = metadata.get("streams", [])
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    format_info = metadata.get("format", {})

    if video_stream is None:
        raise ValueError(f"No video stream found in {input_path}")

    duration_seconds = float(
        video_stream.get("duration")
        or format_info.get("duration")
        or 0.0
    )
    rotation_tags = video_stream.get("tags", {})
    rotation = int(rotation_tags.get("rotate", 0)) if rotation_tags else 0

    return VideoAsset(
        path=str(input_path),
        duration_ms=seconds_to_ms(duration_seconds),
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        fps=_parse_fraction(video_stream.get("avg_frame_rate"), 30.0),
        audio_sample_rate=int(audio_stream.get("sample_rate", 22050)) if audio_stream else 22050,
        rotation=rotation,
    )
