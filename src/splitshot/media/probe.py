from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from PySide6.QtGui import QImage

from splitshot.domain.models import VideoAsset
from splitshot.media.ffmpeg import run_ffprobe_json
from splitshot.utils.time import seconds_to_ms


_STILL_IMAGE_CODEC_NAMES = {
    "apng",
    "bmp",
    "gif",
    "heic",
    "heif",
    "jpeg",
    "jpg",
    "mjpeg",
    "mjpg",
    "png",
    "qoi",
    "svg",
    "tif",
    "tiff",
    "webp",
    "avif",
}


def _parse_fraction(value: str | None, fallback: float) -> float:
    if not value or value in {"0/0", "N/A"}:
        return fallback
    return float(Fraction(value))


def _still_image_asset(path: Path, width: int, height: int) -> VideoAsset:
    return VideoAsset(
        path=str(path),
        duration_ms=0,
        width=width,
        height=height,
        fps=30.0,
        audio_sample_rate=22050,
        rotation=0,
        is_still_image=True,
    )


def _video_stream_looks_like_still_image(video_stream: dict[str, object], format_info: dict[str, object]) -> bool:
    codec_name = str(video_stream.get("codec_name", "")).lower()
    codec_long_name = str(video_stream.get("codec_long_name", "")).lower()
    format_name = str(format_info.get("format_name", "")).lower()
    return (
        codec_name in _STILL_IMAGE_CODEC_NAMES
        or "image" in codec_long_name
        or format_name.endswith("_pipe")
    )


def probe_video(path: str | Path) -> VideoAsset:
    input_path = Path(path)
    image = QImage(str(input_path))
    if not image.isNull():
        return _still_image_asset(input_path, int(image.width()), int(image.height()))

    metadata = run_ffprobe_json(input_path)
    streams = metadata.get("streams", [])
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    format_info = metadata.get("format", {})

    if video_stream is None:
        raise ValueError(f"No video stream found in {input_path}")

    if _video_stream_looks_like_still_image(video_stream, format_info):
        return _still_image_asset(
            input_path,
            int(video_stream.get("width", 0)),
            int(video_stream.get("height", 0)),
        )

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
        is_still_image=False,
    )
