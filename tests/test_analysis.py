from __future__ import annotations

from splitshot.analysis.detection import analyze_video_audio
from splitshot.analysis.sync import compute_sync_offset
from splitshot.media.probe import probe_video
from splitshot.timeline.model import compute_split_rows, draw_time_ms
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


def test_split_times_and_draw_time_are_computed(synthetic_video_factory) -> None:
    controller = ProjectController()
    video_path = synthetic_video_factory()
    controller.load_primary_video(str(video_path))
    controller.analyze_primary()

    rows = compute_split_rows(controller.project)
    assert len(rows) == 3
    assert draw_time_ms(controller.project) is not None
    assert rows[1].split_ms is not None
    assert abs(rows[1].split_ms - 300) <= 60


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
