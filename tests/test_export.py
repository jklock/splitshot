from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from splitshot.analysis.detection import analyze_video_audio
from splitshot.analysis.sync import compute_sync_offset
from splitshot.domain.models import AspectRatio, MergeLayout, OverlayPosition, Project
from splitshot.export.pipeline import export_project
from splitshot.media.probe import probe_video


def _ffprobe_json(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _frame_rgb(path: Path, timestamp: float) -> np.ndarray:
    metadata = _ffprobe_json(path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(height, width, 3)


def test_export_writes_mp4_with_requested_crop(synthetic_video_factory, tmp_path: Path) -> None:
    video_path = synthetic_video_factory()
    project = Project(name="Export Test")
    project.primary_video = probe_video(video_path)
    analysis = analyze_video_audio(video_path, threshold=0.35)
    project.analysis.beep_time_ms_primary = analysis.beep_time_ms
    project.analysis.waveform_primary = analysis.waveform
    project.analysis.shots = analysis.shots
    project.overlay.position = OverlayPosition.TOP
    project.export.aspect_ratio = AspectRatio.SQUARE
    project.export.crop_center_x = 0.5
    project.export.crop_center_y = 0.5

    output_path = tmp_path / "export.mp4"
    export_project(project, output_path)

    assert output_path.exists()
    metadata = _ffprobe_json(output_path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    assert int(video_stream["width"]) == int(video_stream["height"])
    assert output_path.stat().st_size > 0
    frame = _frame_rgb(output_path, 0.9)
    assert int(frame.sum()) > 0


def test_merge_export_writes_combined_canvas(synthetic_video_factory, tmp_path: Path) -> None:
    primary_path = synthetic_video_factory(name="primary", resolution=(640, 360), beep_ms=400)
    secondary_path = synthetic_video_factory(name="secondary", resolution=(640, 360), beep_ms=650)
    project = Project(name="Merge Export")
    project.primary_video = probe_video(primary_path)
    project.secondary_video = probe_video(secondary_path)
    primary_analysis = analyze_video_audio(primary_path, threshold=0.35)
    secondary_analysis = analyze_video_audio(secondary_path, threshold=0.35)
    project.analysis.beep_time_ms_primary = primary_analysis.beep_time_ms
    project.analysis.beep_time_ms_secondary = secondary_analysis.beep_time_ms
    project.analysis.waveform_primary = primary_analysis.waveform
    project.analysis.waveform_secondary = secondary_analysis.waveform
    project.analysis.shots = primary_analysis.shots
    project.analysis.sync_offset_ms = compute_sync_offset(
        primary_analysis.beep_time_ms,
        secondary_analysis.beep_time_ms,
    )
    project.merge.enabled = True
    project.merge.layout = MergeLayout.SIDE_BY_SIDE
    project.overlay.position = OverlayPosition.TOP

    output_path = tmp_path / "merge-export.mp4"
    export_project(project, output_path)

    metadata = _ffprobe_json(output_path)
    video_stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
    assert int(video_stream["width"]) > 640
    assert int(video_stream["height"]) == 360
