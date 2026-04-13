from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from splitshot.analysis.detection import analyze_video_audio
from splitshot.analysis.sync import compute_sync_offset
from splitshot.media.probe import probe_video
from splitshot.timeline.model import average_split_ms, compute_split_rows, draw_time_ms, stage_time_ms
from splitshot.ui.controller import ProjectController


def test_analysis_detects_beep_and_shots(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory()
    result = analyze_video_audio(video_path, threshold=0.35)

    assert result.beep_time_ms is not None
    assert abs(result.beep_time_ms - 400) <= 40
    assert len(result.shots) == 3
    assert abs(result.shots[0].time_ms - 800) <= 50
    assert abs(result.shots[1].time_ms - 1100) <= 50
    assert abs(result.shots[2].time_ms - 1450) <= 50
    assert len(result.waveform) == 4096


def test_threshold_changes_shot_detection_sensitivity(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory()
    low = analyze_video_audio(video_path, threshold=0.2)
    high = analyze_video_audio(video_path, threshold=0.9)

    assert len(low.shots) >= len(high.shots)


def test_model_backed_detection_emits_probability_confidence(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory()
    result = analyze_video_audio(video_path, threshold=0.35)

    confidences = [shot.confidence for shot in result.shots]
    assert confidences
    assert all(confidence is not None for confidence in confidences)
    assert all(0.0 <= float(confidence) <= 1.0 for confidence in confidences)
    assert max(float(confidence) for confidence in confidences) > 0.5


def test_split_times_and_draw_time_are_computed(synthetic_video_factory) -> None:
    controller = ProjectController()
    video_path = synthetic_video_factory()
    controller.load_primary_video(str(video_path))
    controller.analyze_primary()

    rows = compute_split_rows(controller.project)
    assert len(rows) == 3
    assert draw_time_ms(controller.project) is not None
    assert stage_time_ms(controller.project) is not None
    assert average_split_ms(controller.project) is not None
    assert rows[1].split_ms is not None
    assert abs(rows[1].split_ms - 300) <= 60


def test_primary_ingest_runs_detection_automatically(synthetic_video_factory) -> None:
    controller = ProjectController()
    video_path = synthetic_video_factory()

    controller.ingest_primary_video(str(video_path))

    assert controller.project.primary_video.path == str(video_path)
    assert controller.project.analysis.beep_time_ms_primary is not None
    assert len(controller.project.analysis.shots) == 3
    assert controller.status_message.startswith("Primary analysis complete.")


def test_secondary_ingest_runs_sync_automatically(synthetic_video_factory) -> None:
    controller = ProjectController()
    primary = synthetic_video_factory(name="primary", beep_ms=400)
    secondary = synthetic_video_factory(name="secondary", beep_ms=650)

    controller.ingest_primary_video(str(primary))
    controller.ingest_secondary_video(str(secondary))

    assert controller.project.secondary_video is not None
    assert controller.project.merge.enabled is True
    assert controller.project.analysis.beep_time_ms_secondary is not None
    assert abs(controller.project.analysis.sync_offset_ms - 250) <= 40


def test_sync_offset_uses_detected_beeps(synthetic_video_factory) -> None:
    primary = synthetic_video_factory(name="primary", beep_ms=400)
    secondary = synthetic_video_factory(name="secondary", beep_ms=650)

    primary_result = analyze_video_audio(primary, threshold=0.35)
    secondary_result = analyze_video_audio(secondary, threshold=0.35)

    offset = compute_sync_offset(primary_result.beep_time_ms, secondary_result.beep_time_ms)
    assert abs(offset - 250) <= 40


def test_probe_reads_video_metadata(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory()
    asset = probe_video(video_path)
    assert asset.width == 640
    assert asset.height == 360
    assert asset.duration_ms >= 1900


def test_probe_reads_still_image_metadata(tmp_path: Path) -> None:
    image_path = tmp_path / "merge-image.png"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=#00aa55:s=320x180",
            "-frames:v",
            "1",
            str(image_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    asset = probe_video(image_path)

    assert asset.is_still_image is True
    assert asset.width == 320
    assert asset.height == 180
    assert asset.duration_ms == 0


@pytest.mark.parametrize(
    ("suffix", "command"),
    [
        (".mov", ["-c:v", "copy", "-c:a", "copy"]),
        (".m4v", ["-c:v", "copy", "-c:a", "copy"]),
        (".mkv", ["-c:v", "copy", "-c:a", "copy"]),
        (".avi", ["-c:v", "mpeg4", "-c:a", "mp3"]),
        (".webm", ["-c:v", "libvpx-vp9", "-c:a", "libopus"]),
        (".wmv", ["-c:v", "wmv2", "-c:a", "wmav2"]),
        (".mpg", ["-c:v", "mpeg2video", "-c:a", "mp2"]),
        (".mts", ["-c:v", "libx264", "-c:a", "aac", "-f", "mpegts"]),
        (".m2ts", ["-c:v", "libx264", "-c:a", "aac", "-f", "mpegts"]),
    ],
)
def test_probe_reads_common_video_container_metadata(
    synthetic_video_factory,
    tmp_path: Path,
    suffix: str,
    command: list[str],
) -> None:
    source_path = synthetic_video_factory(duration_ms=2000, resolution=(320, 180))
    container_path = tmp_path / f"sample{suffix}"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(source_path),
            *command,
            str(container_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    asset = probe_video(container_path)

    assert asset.path == str(container_path)
    assert asset.width == 320
    assert asset.height == 180
    assert asset.duration_ms > 0
