import json
import subprocess
from pathlib import Path


def ffprobe_info(path: str | Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {result.stderr}")
    return json.loads(result.stdout)


def assert_video_file(
    path: str | Path,
    *,
    expected_duration_s: float | None = None,
    min_duration_s: float = 0.0,
    expected_codec: str | None = None,
    expected_width: int | None = None,
    expected_height: int | None = None,
    tolerance_s: float = 0.5,
) -> dict:
    path = Path(path)
    assert path.exists(), f"File does not exist: {path}"
    assert path.stat().st_size > 0, f"File is empty: {path}"

    info = ffprobe_info(path)
    assert "format" in info, f"No format in ffprobe output for {path}"
    fmt = info["format"]
    assert fmt.get("duration"), f"No duration in format for {path}"
    duration = float(fmt["duration"])

    assert "streams" in info, f"No streams in ffprobe output for {path}"
    streams = info["streams"]

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    assert video_streams, f"No video stream in {path}"

    vs = video_streams[0]
    codec = vs.get("codec_name", "?")
    width = vs.get("width", 0)
    height = vs.get("height", 0)

    if expected_duration_s is not None:
        assert abs(duration - expected_duration_s) <= tolerance_s, (
            f"Expected duration {expected_duration_s}s, got {duration:.3f}s"
        )
    else:
        assert duration >= min_duration_s, (
            f"Expected duration >= {min_duration_s}s, got {duration:.3f}s"
        )

    if expected_codec is not None:
        assert codec == expected_codec, f"Expected codec {expected_codec}, got {codec}"

    if expected_width is not None:
        assert width == expected_width, f"Expected width {expected_width}, got {width}"

    if expected_height is not None:
        assert height == expected_height, f"Expected height {expected_height}, got {height}"

    return {
        "path": str(path),
        "duration_s": duration,
        "codec": codec,
        "width": width,
        "height": height,
    }
