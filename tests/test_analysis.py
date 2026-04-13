from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from splitshot.analysis.detection import analyze_video_audio
from splitshot.analysis.sync import compute_sync_offset
from splitshot.domain.models import BadgeSize, MergeLayout, OverlayPosition, ScoreLetter
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


def test_badge_size_updates_overlay_font_size_preset() -> None:
    controller = ProjectController()

    controller.set_badge_size(BadgeSize.XL)
    assert controller.project.overlay.badge_size == BadgeSize.XL
    assert controller.project.overlay.font_size == 20

    controller.set_overlay_display_options({"font_size": 18})
    assert controller.project.overlay.font_size == 18

    controller.set_badge_size(BadgeSize.S)
    assert controller.project.overlay.badge_size == BadgeSize.S
    assert controller.project.overlay.font_size == 12


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


def test_primary_replacement_preserves_reusable_settings_and_resets_video_state(
    synthetic_video_factory,
) -> None:
    controller = ProjectController()
    first_primary = synthetic_video_factory(name="primary-one", beep_ms=400)
    second_primary = synthetic_video_factory(name="primary-two", beep_ms=520)
    secondary = synthetic_video_factory(name="secondary-angle", beep_ms=680)

    controller.ingest_primary_video(str(first_primary))
    first_shot_id = controller.project.analysis.shots[0].id

    controller.set_project_details(name="Classifier Template", description="Carry these settings forward")
    controller.set_detection_threshold(0.35)
    controller.set_overlay_position(OverlayPosition.TOP)
    controller.set_overlay_display_options(
        {
            "custom_box_enabled": True,
            "custom_box_text": "Stage review",
            "custom_box_x": 0.45,
            "custom_box_y": 0.55,
        }
    )
    controller.apply_export_preset("universal_vertical")
    controller.set_export_settings({"video_bitrate_mbps": 18, "two_pass": True})
    controller.set_scoring_enabled(True)
    controller.set_scoring_preset("uspsa_major")
    controller.set_penalties(5.0)
    controller.set_penalty_counts({"procedural_errors": 1})
    controller.assign_score(first_shot_id, ScoreLetter.C)
    controller.add_timing_event("reload", after_shot_id=first_shot_id, note="Old review note")
    controller.ingest_secondary_video(str(secondary))
    controller.set_merge_layout(MergeLayout.PIP)
    controller.set_pip_size_percent(50)
    controller.set_pip_position(0.2, 0.8)
    controller.select_shot(first_shot_id)
    controller.project.ui_state.timeline_offset_ms = 1234
    controller.project.export.output_path = "/tmp/classifier-export.mp4"
    controller.project.export.last_log = "previous export log"
    controller.project.export.last_error = "previous export error"

    controller.ingest_primary_video(str(second_primary))

    assert controller.project.primary_video.path == str(second_primary)
    assert controller.project.name == "Classifier Template"
    assert controller.project.description == "Carry these settings forward"
    assert controller.project.analysis.detection_threshold == 0.35
    assert controller.project.analysis.beep_time_ms_primary is not None
    assert controller.project.analysis.beep_time_ms_secondary is None
    assert controller.project.analysis.sync_offset_ms == 0
    assert controller.project.analysis.events == []
    assert len(controller.project.analysis.shots) == 3
    assert all(shot.score is None for shot in controller.project.analysis.shots)
    assert controller.project.scoring.enabled is True
    assert controller.project.scoring.ruleset == "uspsa_major"
    assert controller.project.scoring.point_map[ScoreLetter.C.value] == 4
    assert controller.project.scoring.penalties == 0.0
    assert controller.project.scoring.penalty_counts == {}
    assert controller.project.scoring.hit_factor == 0.0
    assert controller.project.overlay.position == OverlayPosition.TOP
    assert controller.project.overlay.custom_box_enabled is True
    assert controller.project.overlay.custom_box_text == ""
    assert controller.project.overlay.custom_box_x == 0.45
    assert controller.project.overlay.custom_box_y == 0.55
    assert controller.project.secondary_video is None
    assert controller.project.merge_sources == []
    assert controller.project.merge.enabled is False
    assert controller.project.merge.layout == MergeLayout.SIDE_BY_SIDE
    assert controller.project.merge.pip_size_percent == 35
    assert controller.project.merge.pip_x == 1.0
    assert controller.project.merge.pip_y == 1.0
    assert controller.project.export.target_width == 1080
    assert controller.project.export.target_height == 1920
    assert controller.project.export.video_bitrate_mbps == 18.0
    assert controller.project.export.two_pass is True
    assert controller.project.export.output_path == "/tmp/classifier-export.mp4"
    assert controller.project.export.last_log == ""
    assert controller.project.export.last_error is None
    assert controller.project.ui_state.selected_shot_id is None
    assert controller.project.ui_state.timeline_offset_ms == 0


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
