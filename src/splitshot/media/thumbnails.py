from __future__ import annotations

from pathlib import Path

from splitshot.media.ffmpeg import run_ffmpeg


def generate_thumbnail(video_path: str | Path, image_path: str | Path, timestamp_seconds: float = 1.0) -> Path:
    output_path = Path(image_path)
    run_ffmpeg(
        [
            "-ss",
            f"{timestamp_seconds:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output_path),
        ]
    )
    return output_path
