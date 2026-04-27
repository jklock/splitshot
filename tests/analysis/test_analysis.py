from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from splitshot.analysis.detection import (
    DetectionResult,
    _apply_refinement_confidence,
    _filter_false_positive_shots,
    _refine_shot_times,
    _sound_profile_outlier_mask,
    _suggest_timing_review_actions,
    analyze_video_audio,
)
from splitshot.config import AppSettings
from splitshot.analysis.sync import compute_sync_offset
from splitshot.domain.models import (
    BadgeSize,
    MergeLayout,
    MergeSource,
    OverlayPosition,
    ScoreLetter,
    ShotEvent,
    ShotMLSettings,
    ShotSource,
    VideoAsset,
)
from splitshot.media.ffmpeg import run_ffprobe_json
from splitshot.media.probe import probe_video
from splitshot.timeline.model import average_split_ms, compute_split_rows, draw_time_ms, stage_time_ms
from splitshot.ui.controller import ProjectController
from splitshot.utils.time import seconds_to_ms


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "example_data"


def _changed_place_idpa_results(tmp_path: Path) -> Path:
    source = (EXAMPLES_DIR / "IDPA" / "IDPA.csv").read_text(encoding="utf-8")
    source = source.replace(
        "4,CO,UN,Klockenkemper,John,A1035577,,1,1,0,,83.01,11,1,1,,,,14.55,1,,,,,,,29.83,5,1,,,,,,18.62,5,,,,,,,20.01,,,1,,,,",
        "6,CO,UN,Klockenkemper,John,A1035577,,1,1,0,,83.01,11,1,1,,,,14.55,1,,,,,,,20.57,5,1,,,,,,18.62,5,,,,,,,20.01,,,1,,,,",
    )
    path = tmp_path / "thursday-night.csv"
    path.write_text(source, encoding="utf-8")
    return path


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


def test_analysis_aligns_detections_to_media_timeline_when_audio_starts_late(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(
        name="audio-offset",
        duration_ms=2600,
        audio_stream_offset_ms=500,
    )
    metadata = run_ffprobe_json(video_path)
    audio_stream = next(item for item in metadata["streams"] if item.get("codec_type") == "audio")
    audio_start_ms = seconds_to_ms(float(audio_stream.get("start_time") or 0.0))

    result = analyze_video_audio(video_path, threshold=0.35)

    assert result.beep_time_ms is not None
    assert abs(result.beep_time_ms - (400 + audio_start_ms)) <= 60
    expected_shot_times = [800 + audio_start_ms, 1100 + audio_start_ms, 1450 + audio_start_ms]
    assert len(result.shots) == len(expected_shot_times)
    for shot, expected_time in zip(result.shots, expected_shot_times, strict=True):
        assert abs(shot.time_ms - expected_time) <= 60


def test_threshold_changes_shot_detection_sensitivity(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory()
    low = analyze_video_audio(video_path, threshold=0.2)
    high = analyze_video_audio(video_path, threshold=0.9)

    assert len(low.shots) >= len(high.shots)


def test_default_shotml_settings_match_legacy_threshold_call(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory()

    legacy = analyze_video_audio(video_path, threshold=0.35)
    configured = analyze_video_audio(video_path, threshold=0.35, settings=ShotMLSettings())

    assert legacy.beep_time_ms == configured.beep_time_ms
    assert [(shot.time_ms, shot.source, shot.confidence) for shot in legacy.shots] == [
        (shot.time_ms, shot.source, shot.confidence)
        for shot in configured.shots
    ]
    assert legacy.waveform == configured.waveform


def test_saved_app_threshold_preserves_shotml_defaults_threshold(monkeypatch) -> None:
    settings = AppSettings.from_dict(
        {
            "detection_threshold": 0.75,
            "shotml_defaults": {
                "detection_threshold": 0.75,
                "beep_onset_fraction": 0.31,
            },
        }
    )

    assert settings.detection_threshold == pytest.approx(0.35)
    assert settings.shotml_defaults.detection_threshold == pytest.approx(0.75)
    assert settings.shotml_defaults.beep_onset_fraction == pytest.approx(0.31)

    monkeypatch.setattr("splitshot.ui.controller.load_settings", lambda: settings)
    controller = ProjectController()

    assert controller.project.analysis.detection_threshold == pytest.approx(0.75)
    assert controller.project.analysis.shotml_settings.detection_threshold == pytest.approx(0.75)
    assert controller.project.analysis.shotml_settings.beep_onset_fraction == pytest.approx(0.31)


def test_false_positive_filter_rejects_sub_tenth_second_shots() -> None:
    shots = [
        ShotEvent(time_ms=165, source=ShotSource.AUTO, confidence=0.95),
        ShotEvent(time_ms=280, source=ShotSource.AUTO, confidence=0.61),
        ShotEvent(time_ms=345, source=ShotSource.AUTO, confidence=0.88),
        ShotEvent(time_ms=520, source=ShotSource.AUTO, confidence=0.74),
    ]

    filtered = _filter_false_positive_shots(shots, beep_time_ms=100)

    assert [shot.time_ms for shot in filtered] == [345, 520]
    assert [shot.confidence for shot in filtered] == [0.88, 0.74]


def test_false_positive_filter_prefers_stronger_onset_support_over_louder_echo() -> None:
    samples = np.zeros(900, dtype=np.float32)
    samples[495:505] = np.asarray([0.05, 0.1, 0.3, 0.8, 1.0, 0.7, 0.4, 0.2, 0.1, 0.05], dtype=np.float32)
    samples[560:700] = 0.65
    shots = [
        ShotEvent(time_ms=500, source=ShotSource.AUTO, confidence=0.72),
        ShotEvent(time_ms=620, source=ShotSource.AUTO, confidence=0.98),
    ]

    filtered = _filter_false_positive_shots(
        shots,
        beep_time_ms=100,
        samples=samples,
        sample_rate=1000,
    )

    assert [shot.time_ms for shot in filtered] == [500]
    assert [shot.confidence for shot in filtered] == [0.72]


def test_sound_profile_outlier_mask_rejects_far_terminal_clap() -> None:
    feature_vectors = [
        np.full(20, 0.10, dtype=np.float32),
        np.full(20, 0.14, dtype=np.float32),
        np.full(20, 0.12, dtype=np.float32),
        np.full(20, 0.11, dtype=np.float32),
        np.full(20, 0.15, dtype=np.float32),
        np.full(20, 0.16, dtype=np.float32),
        np.full(20, 0.13, dtype=np.float32),
        np.full(20, 6.50, dtype=np.float32),
    ]
    shot_probabilities = [0.99, 0.98, 0.97, 0.99, 0.98, 0.94, 0.995, 0.983]

    mask = _sound_profile_outlier_mask(feature_vectors, shot_probabilities)

    assert mask == [False, False, False, False, False, False, False, True]


def test_model_backed_detection_emits_probability_confidence(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory()
    result = analyze_video_audio(video_path, threshold=0.35)

    confidences = [shot.confidence for shot in result.shots]
    assert confidences
    assert all(confidence is not None for confidence in confidences)
    assert all(0.0 <= float(confidence) <= 1.0 for confidence in confidences)
    assert max(float(confidence) for confidence in confidences) <= 1.0
    assert max(float(confidence) for confidence in confidences) > 0.5


def test_refinement_confidence_scores_existing_shots_without_moving_timestamps() -> None:
    samples = np.zeros(2000, dtype=np.float32)
    samples[795:805] = np.asarray([0.1, 0.3, 0.6, 1.0, 0.9, 0.6, 0.4, 0.2, 0.1, 0.05], dtype=np.float32)
    shots = [ShotEvent(time_ms=800, source=ShotSource.AUTO, confidence=0.50)]

    refined = _apply_refinement_confidence(samples, sample_rate=1000, shots=shots)

    assert [shot.time_ms for shot in refined] == [800]
    assert refined[0].confidence is not None
    assert refined[0].confidence > 0.50


def test_refinement_confidence_never_lowers_original_detector_confidence() -> None:
    samples = np.zeros(2000, dtype=np.float32)
    samples[1200:1205] = np.asarray([0.05, 0.1, 0.2, 0.1, 0.05], dtype=np.float32)
    shots = [ShotEvent(time_ms=800, source=ShotSource.AUTO, confidence=0.99)]

    refined = _apply_refinement_confidence(samples, sample_rate=1000, shots=shots)

    assert [shot.time_ms for shot in refined] == [800]
    assert refined[0].confidence == pytest.approx(0.99)


def test_refinement_suggests_review_without_changing_timeline() -> None:
    samples = np.zeros(1200, dtype=np.float32)
    samples[498:504] = np.asarray([0.1, 0.4, 1.0, 0.7, 0.3, 0.1], dtype=np.float32)
    samples[610:710] = 0.05
    shots = [
        ShotEvent(time_ms=500, source=ShotSource.AUTO, confidence=0.99),
        ShotEvent(time_ms=640, source=ShotSource.AUTO, confidence=0.92),
    ]

    suggestions = _suggest_timing_review_actions(samples, sample_rate=1000, shots=shots)

    assert [shot.time_ms for shot in shots] == [500, 640]
    assert {suggestion.kind for suggestion in suggestions} >= {"weak_onset_support", "near_cutoff_spacing"}
    assert all(suggestion.suggested_action.startswith("review") for suggestion in suggestions)


def test_refine_shot_times_preserves_raw_model_confidence() -> None:
    samples = np.zeros(400, dtype=np.float32)
    samples[198:202] = np.asarray([0.4, 1.0, 0.7, 0.2], dtype=np.float32)
    shots = [ShotEvent(time_ms=200, source=ShotSource.AUTO, confidence=0.9734)]

    refined = _refine_shot_times(samples, sample_rate=1000, shots=shots)

    assert len(refined) == 1
    assert refined[0].confidence == pytest.approx(0.9734)


def test_shotml_refinement_setting_changes_shot_timestamp() -> None:
    samples = np.zeros(500, dtype=np.float32)
    samples[200:206] = np.asarray([0.1, 0.25, 0.5, 0.75, 1.0, 0.5], dtype=np.float32)
    shots = [ShotEvent(time_ms=204, source=ShotSource.AUTO, confidence=0.8)]

    early = _refine_shot_times(
        samples,
        sample_rate=1000,
        shots=shots,
        settings=ShotMLSettings(shot_onset_fraction=0.2),
    )
    late = _refine_shot_times(
        samples,
        sample_rate=1000,
        shots=shots,
        settings=ShotMLSettings(shot_onset_fraction=0.8),
    )

    assert early[0].time_ms < late[0].time_ms


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
    assert rows[0].split_ms is not None
    assert abs(rows[0].split_ms - draw_time_ms(controller.project)) <= 60
    assert rows[0].row_type == "shot"
    assert rows[0].label == "Shot 1"
    assert rows[0].interval_label == "Draw"
    assert rows[0].sequence_total_ms == rows[0].split_ms
    assert rows[1].split_ms is not None
    assert abs(rows[1].split_ms - 300) <= 60


def test_timing_events_attach_to_the_interval_without_zeroing_the_shot_split() -> None:
    controller = ProjectController()
    controller.project.analysis.beep_time_ms_primary = 100
    controller.project.analysis.shots = [
        ShotEvent(time_ms=250),
        ShotEvent(time_ms=480),
        ShotEvent(time_ms=720),
    ]
    controller.add_timing_event(
        "reload",
        after_shot_id=controller.project.analysis.shots[0].id,
        before_shot_id=controller.project.analysis.shots[1].id,
    )

    rows = compute_split_rows(controller.project)

    assert [row.label for row in rows] == ["Shot 1", "Shot 2", "Shot 3"]
    assert [row.interval_label for row in rows] == ["Draw", "Reload", "Split"]
    assert rows[1].split_ms == 230
    assert rows[1].cumulative_ms == 380
    assert [action.label for action in rows[1].actions] == ["Reload"]
    assert rows[1].sequence_total_ms == 230
    assert rows[2].cumulative_ms == 620
    assert rows[2].sequence_total_ms == 470
    assert rows[2].split_ms == 240


def test_custom_timing_labels_do_not_reset_the_running_split_total() -> None:
    controller = ProjectController()
    controller.project.analysis.beep_time_ms_primary = 100
    controller.project.analysis.shots = [
        ShotEvent(time_ms=250),
        ShotEvent(time_ms=480),
        ShotEvent(time_ms=720),
    ]
    controller.add_timing_event(
        "custom_label",
        after_shot_id=controller.project.analysis.shots[0].id,
        before_shot_id=controller.project.analysis.shots[1].id,
        label="Transition",
    )

    rows = compute_split_rows(controller.project)

    assert [row.interval_label for row in rows] == ["Draw", "Transition", "Split"]
    assert rows[1].sequence_total_ms == 380
    assert rows[2].sequence_total_ms == 620


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
    first_shot_id = controller.project.analysis.shots[0].id
    controller.set_overlay_position(OverlayPosition.TOP)
    controller.set_overlay_display_options(
        {
            "custom_box_enabled": True,
            "custom_box_mode": "imported_summary",
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
    assert all(shot.score is not None for shot in controller.project.analysis.shots)
    assert all(shot.score.letter == ScoreLetter.A for shot in controller.project.analysis.shots)
    assert controller.project.scoring.enabled is True
    assert controller.project.scoring.ruleset == "uspsa_major"
    assert controller.project.scoring.point_map[ScoreLetter.C.value] == 4
    assert controller.project.scoring.penalties == 0.0
    assert controller.project.scoring.penalty_counts == {}
    assert controller.project.scoring.hit_factor is not None
    assert controller.project.scoring.hit_factor > 0.0
    assert controller.project.overlay.position == OverlayPosition.TOP
    assert controller.project.overlay.custom_box_enabled is True
    assert controller.project.overlay.custom_box_mode == "imported_summary"
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


def test_new_shots_default_to_active_preset_score_letter() -> None:
    controller = ProjectController()

    controller.add_shot(1200)
    assert controller.project.analysis.shots[-1].score is not None
    assert controller.project.analysis.shots[-1].score.letter == ScoreLetter.A

    controller.set_scoring_preset("idpa_time_plus")
    controller.add_shot(1600)
    assert controller.project.analysis.shots[-1].score is not None
    assert controller.project.analysis.shots[-1].score.letter == ScoreLetter.DOWN_0


def test_switching_match_type_normalizes_existing_shot_scores_to_sport_default() -> None:
    controller = ProjectController()

    controller.add_shot(1200)
    assert controller.project.analysis.shots[-1].score is not None
    assert controller.project.analysis.shots[-1].score.letter == ScoreLetter.A

    controller.set_practiscore_context(match_type="idpa")

    assert controller.project.scoring.ruleset == "idpa_time_plus"
    assert controller.project.analysis.shots[-1].score is not None
    assert controller.project.analysis.shots[-1].score.letter == ScoreLetter.DOWN_0


def test_primary_analysis_uses_active_sport_default_score_letter(synthetic_video_factory) -> None:
    controller = ProjectController()
    controller.set_practiscore_context(match_type="idpa")

    controller.ingest_primary_video(str(synthetic_video_factory()))

    assert controller.project.scoring.ruleset == "idpa_time_plus"
    assert controller.project.analysis.shots
    assert all(shot.score is not None for shot in controller.project.analysis.shots)
    assert all(shot.score.letter == ScoreLetter.DOWN_0 for shot in controller.project.analysis.shots)


def test_primary_replacement_keeps_imported_stage_scoring_for_same_stage(synthetic_video_factory) -> None:
    controller = ProjectController()
    controller.set_practiscore_context(
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )
    controller.import_practiscore_file(str(EXAMPLES_DIR / "IDPA" / "IDPA.csv"), source_name="IDPA.csv")

    first_primary = synthetic_video_factory(name="stage-two-first", beep_ms=400)
    second_primary = synthetic_video_factory(name="stage-two-second", beep_ms=500)

    controller.ingest_primary_video(str(first_primary))
    imported_before = controller.project.scoring.imported_stage

    controller.ingest_primary_video(str(second_primary))

    assert controller.project.scoring.imported_stage == imported_before
    assert controller.project.scoring.penalty_counts == {"non_threats": 1.0}
    assert controller.project.scoring.penalties == 0.0
    assert controller.project.scoring.ruleset == "idpa_time_plus"


def test_primary_replacement_keeps_staged_practiscore_source_for_stage_switch(synthetic_video_factory) -> None:
    controller = ProjectController()
    controller.set_practiscore_context(
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )
    controller.import_practiscore_file(str(EXAMPLES_DIR / "IDPA" / "IDPA.csv"), source_name="IDPA.csv")

    first_primary = synthetic_video_factory(name="stage-two-first", beep_ms=400)
    second_primary = synthetic_video_factory(name="stage-three-second", beep_ms=500)

    controller.ingest_primary_video(str(first_primary))
    controller.ingest_primary_video(str(second_primary))
    controller.set_practiscore_context(stage_number=3)

    assert controller.practiscore_browser_state()["source_name"] == "IDPA.csv"
    assert controller.project.scoring.imported_stage is not None
    assert controller.project.scoring.imported_stage.stage_number == 3


def test_open_project_restores_practiscore_source_for_stage_switch(tmp_path: Path) -> None:
    controller = ProjectController()
    controller.set_practiscore_context(
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )
    controller.import_practiscore_file(str(EXAMPLES_DIR / "IDPA" / "IDPA.csv"), source_name="IDPA.csv")

    project_path = tmp_path / "stage-browser.ssproj"
    controller.save_project(str(project_path))

    reopened = ProjectController()
    reopened.open_project(str(project_path))
    reopened.set_practiscore_context(stage_number=3)

    browser_state = reopened.practiscore_browser_state()
    assert browser_state["has_source"] is True
    assert browser_state["source_name"] == "IDPA.csv"
    assert browser_state["stage_numbers"] == [1, 2, 3, 4]
    assert reopened.project.scoring.imported_stage is not None
    assert reopened.project.scoring.imported_stage.stage_number == 3


def test_open_project_recovers_practiscore_from_project_csv_folder_when_metadata_missing(tmp_path: Path) -> None:
    controller = ProjectController()
    project_path = tmp_path / "recovered-practiscore.ssproj"
    controller.save_project(str(project_path))

    staged_csv = project_path / "CSV" / "IDPA.csv"
    staged_csv.write_bytes((EXAMPLES_DIR / "IDPA" / "IDPA.csv").read_bytes())

    reopened = ProjectController()
    reopened.open_project(str(project_path))

    browser_state = reopened.practiscore_browser_state()
    assert browser_state["has_source"] is True
    assert browser_state["source_name"] == "IDPA.csv"
    assert browser_state["detected_match_type"] == "idpa"
    assert browser_state["stage_numbers"] == [1, 2, 3, 4]
    assert reopened.project.scoring.practiscore_source_path == str(staged_csv.resolve())
    assert reopened.project.scoring.enabled is True
    assert reopened.project.scoring.ruleset == "idpa_time_plus"
    assert reopened.project.scoring.match_type == "idpa"
    assert reopened.project.scoring.stage_number == 1
    assert reopened.project.scoring.competitor_name == "Jeff Graff"
    assert reopened.project.scoring.competitor_place == 1
    assert reopened.project.scoring.imported_stage is not None
    assert reopened.project.scoring.imported_stage.source_name == "IDPA.csv"
    assert reopened.project.scoring.imported_stage.stage_number == 1
    assert reopened.project.scoring.imported_stage.competitor_name == "Jeff Graff"
    assert reopened.project.scoring.imported_stage.competitor_place == 1


def test_open_project_reimports_practiscore_when_saved_context_exists_but_imported_stage_is_missing(tmp_path: Path) -> None:
    controller = ProjectController()
    project_path = tmp_path / "recovered-practiscore-selection.ssproj"
    controller.save_project(str(project_path))

    staged_csv = project_path / "CSV" / "IDPA.csv"
    staged_csv.write_bytes((EXAMPLES_DIR / "IDPA" / "IDPA.csv").read_bytes())

    metadata_path = project_path / "project.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["scoring"]["match_type"] = "idpa"
    payload["scoring"]["stage_number"] = 1
    payload["scoring"]["competitor_name"] = "Jeff Graff"
    payload["scoring"]["competitor_place"] = 1
    metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    reopened = ProjectController()
    reopened.open_project(str(project_path))

    assert reopened.project.scoring.imported_stage is not None
    assert reopened.project.scoring.imported_stage.source_name == "IDPA.csv"
    assert reopened.project.scoring.imported_stage.stage_number == 1
    assert reopened.project.scoring.imported_stage.competitor_name == "Jeff Graff"
    assert reopened.project.scoring.imported_stage.final_time == 9.15


def test_open_project_recovers_renamed_media_from_project_input_folder(synthetic_video_factory, tmp_path: Path) -> None:
    controller = ProjectController()
    primary_path = synthetic_video_factory(name="Stage1")
    secondary_path = synthetic_video_factory(name="Stage2")

    controller.ingest_primary_video(str(primary_path))
    controller.add_merge_source(str(secondary_path))

    project_path = tmp_path / "renamed-media.ssproj"
    controller.save_project(str(project_path))

    saved_primary = Path(controller.project.primary_video.path)
    assert controller.project.secondary_video is not None
    saved_secondary = Path(controller.project.secondary_video.path)
    renamed_primary = saved_primary.with_name(f"01_{saved_primary.name}")
    renamed_secondary = saved_secondary.with_name(f"02_{saved_secondary.name}")
    saved_primary.rename(renamed_primary)
    saved_secondary.rename(renamed_secondary)

    reopened = ProjectController()
    reopened.open_project(str(project_path))

    assert Path(reopened.project.primary_video.path) == renamed_primary.resolve()
    assert reopened.project.secondary_video is not None
    assert Path(reopened.project.secondary_video.path) == renamed_secondary.resolve()
    assert reopened.project.merge_sources
    assert Path(reopened.project.merge_sources[0].asset.path) == renamed_secondary.resolve()
    assert "restored renamed project media" in reopened.status_message.lower()


def test_open_project_recovers_renamed_media_from_project_root_folder(synthetic_video_factory, tmp_path: Path) -> None:
    controller = ProjectController()
    primary_path = synthetic_video_factory(name="Stage2")

    controller.ingest_primary_video(str(primary_path))
    controller.save_project(str(tmp_path))

    saved_primary = Path(controller.project.primary_video.path)
    assert saved_primary.parent == tmp_path
    renamed_primary = saved_primary.with_name("Stage02.MP4")
    saved_primary.rename(renamed_primary)

    reopened = ProjectController()
    reopened.open_project(str(tmp_path))

    assert Path(reopened.project.primary_video.path) == renamed_primary.resolve()
    assert "restored renamed project media" in reopened.status_message.lower()


def test_delete_timing_event_removes_matching_event() -> None:
    controller = ProjectController()

    controller.add_timing_event("reload", note="Cleanup")
    event_id = controller.project.analysis.events[0].id

    controller.delete_timing_event(event_id)

    assert controller.project.analysis.events == []


def test_delete_shot_revalidates_ui_state_references() -> None:
    controller = ProjectController()
    first_shot = ShotEvent(time_ms=250)
    second_shot = ShotEvent(time_ms=480)
    controller.project.analysis.shots = [first_shot, second_shot]
    controller.project.ui_state.selected_shot_id = first_shot.id
    controller.project.ui_state.scoring_shot_expansion = {
        first_shot.id: True,
        second_shot.id: False,
    }
    controller.project.ui_state.waveform_shot_amplitudes = {
        first_shot.id: 1.5,
        second_shot.id: 1.2,
    }
    controller.project.ui_state.timing_edit_shot_ids = [first_shot.id, second_shot.id]

    controller.delete_shot(first_shot.id)

    assert [shot.id for shot in controller.project.analysis.shots] == [second_shot.id]
    assert controller.project.ui_state.selected_shot_id == second_shot.id
    assert controller.project.ui_state.scoring_shot_expansion == {second_shot.id: False}
    assert controller.project.ui_state.waveform_shot_amplitudes == {second_shot.id: 1.2}
    assert controller.project.ui_state.timing_edit_shot_ids == [second_shot.id]


def test_practiscore_import_auto_enables_summary_only_after_file_import() -> None:
    controller = ProjectController()

    controller.set_practiscore_context(
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )

    assert controller.project.overlay.custom_box_enabled is False
    assert controller.project.overlay.custom_box_mode == "manual"

    controller.import_practiscore_file(str(EXAMPLES_DIR / "IDPA" / "IDPA.csv"), source_name="IDPA.csv")

    assert controller.project.overlay.custom_box_enabled is True
    assert controller.project.overlay.custom_box_mode == "imported_summary"
    imported_box = next(box for box in controller.project.overlay.text_boxes if box.source == "imported_summary")
    assert imported_box.quadrant == "above_final"
    assert imported_box.x is None
    assert imported_box.y is None
    assert imported_box.width == 0
    assert imported_box.height == 0


def test_importing_new_practiscore_csv_preserves_current_selection_when_place_changes(tmp_path: Path) -> None:
    controller = ProjectController()
    controller.set_practiscore_context(
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )
    controller.import_practiscore_file(str(EXAMPLES_DIR / "IDPA" / "IDPA.csv"), source_name="old-results.csv")

    controller.import_practiscore_file(str(_changed_place_idpa_results(tmp_path)), source_name="thursday-night.csv")

    assert controller.project.scoring.match_type == "idpa"
    assert controller.project.scoring.stage_number == 2
    assert controller.project.scoring.competitor_name == "John Klockenkemper"
    assert controller.project.scoring.competitor_place == 6
    assert controller.project.scoring.imported_stage is not None
    assert controller.project.scoring.imported_stage.source_name == "thursday-night.csv"
    assert controller.project.scoring.imported_stage.stage_number == 2
    assert controller.project.scoring.imported_stage.final_time == 20.57


def test_importing_new_practiscore_csv_restores_imported_summary_box_when_missing(tmp_path: Path) -> None:
    controller = ProjectController()
    controller.set_practiscore_context(
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )
    controller.import_practiscore_file(str(EXAMPLES_DIR / "IDPA" / "IDPA.csv"), source_name="old-results.csv")

    controller.project.overlay.text_boxes = []
    controller.project.overlay.custom_box_enabled = False
    controller.project.overlay.custom_box_mode = "manual"

    controller.import_practiscore_file(str(_changed_place_idpa_results(tmp_path)), source_name="thursday-night.csv")

    assert any(
        box.source == "imported_summary" and box.enabled
        for box in controller.project.overlay.text_boxes
    )
    imported_box = next(box for box in controller.project.overlay.text_boxes if box.source == "imported_summary")
    assert imported_box.quadrant == "above_final"
    assert imported_box.width == 0
    assert imported_box.height == 0
    assert controller.project.overlay.custom_box_enabled is True
    assert controller.project.overlay.custom_box_mode == "imported_summary"


def test_overlay_legacy_only_updates_preserve_existing_review_text_box_ids() -> None:
    controller = ProjectController()

    controller.set_overlay_display_options(
        {
            "text_boxes": [
                {
                    "id": "manual-box",
                    "enabled": True,
                    "source": "manual",
                    "text": "Stage note",
                    "quadrant": "top_left",
                    "background_color": "#000000",
                    "text_color": "#ffffff",
                    "opacity": 0.9,
                    "width": 0,
                    "height": 0,
                }
            ]
        }
    )

    controller.set_overlay_display_options(
        {
            "custom_box_enabled": True,
            "custom_box_text_color": "#112233",
            "custom_box_opacity": 0.65,
        }
    )

    assert len(controller.project.overlay.text_boxes) == 1
    assert controller.project.overlay.text_boxes[0].id == "manual-box"
    assert controller.project.overlay.text_boxes[0].text == "Stage note"


def test_sync_offset_uses_detected_beeps(synthetic_video_factory) -> None:
    primary = synthetic_video_factory(name="primary", beep_ms=400)
    secondary = synthetic_video_factory(name="secondary", beep_ms=650)

    primary_result = analyze_video_audio(primary, threshold=0.35)
    secondary_result = analyze_video_audio(secondary, threshold=0.35)

    offset = compute_sync_offset(primary_result.beep_time_ms, secondary_result.beep_time_ms)
    assert abs(offset - 250) <= 40


def test_detection_threshold_reanalyzes_loaded_primary_and_secondary(monkeypatch) -> None:
    controller = ProjectController()
    primary = VideoAsset(path="/tmp/primary.mp4", duration_ms=2000, width=640, height=360, fps=30.0)
    secondary = VideoAsset(path="/tmp/secondary.mp4", duration_ms=2000, width=640, height=360, fps=30.0)
    controller.project.primary_video = primary
    controller.project.secondary_video = secondary
    controller.project.merge_sources = [MergeSource(asset=secondary)]

    calls: list[tuple[str, float]] = []

    def fake_analyze(path: str, threshold: float) -> DetectionResult:
        calls.append((path, threshold))
        if path == primary.path:
            return DetectionResult(
                beep_time_ms=410,
                shots=[ShotEvent(time_ms=820, source=ShotSource.AUTO, confidence=0.9)],
                waveform=[0.1, 0.2],
                sample_rate=48000,
            )
        return DetectionResult(
            beep_time_ms=655,
            shots=[],
            waveform=[0.3, 0.4],
            sample_rate=48000,
        )

    monkeypatch.setattr("splitshot.ui.controller.analyze_video_audio", fake_analyze)
    monkeypatch.setattr("splitshot.ui.controller.compute_sync_offset", lambda primary_ms, secondary_ms: secondary_ms - primary_ms)

    controller.set_detection_threshold(0.35)

    assert calls == [(primary.path, 0.35), (secondary.path, 0.35)]
    assert controller.project.analysis.detection_threshold == 0.35
    assert controller.project.analysis.shotml_settings.detection_threshold == 0.35
    assert controller.project.analysis.beep_time_ms_primary == 410
    assert controller.project.analysis.beep_time_ms_secondary == 655
    assert controller.project.analysis.sync_offset_ms == 245
    assert [shot.time_ms for shot in controller.project.analysis.shots] == [820]
    assert controller.project.analysis.waveform_primary == [0.1, 0.2]
    assert controller.project.analysis.waveform_secondary == [0.3, 0.4]


def test_detection_threshold_reanalysis_preserves_manual_shots_and_timing_events(monkeypatch) -> None:
    controller = ProjectController()
    controller.project.primary_video = VideoAsset(path="/tmp/primary.mp4", duration_ms=2000, width=640, height=360, fps=30.0)

    detections = [
        DetectionResult(
            beep_time_ms=100,
            shots=[
                ShotEvent(time_ms=250, source=ShotSource.AUTO, confidence=0.9),
                ShotEvent(time_ms=500, source=ShotSource.AUTO, confidence=0.9),
                ShotEvent(time_ms=900, source=ShotSource.AUTO, confidence=0.9),
            ],
            waveform=[0.1],
            sample_rate=22050,
        ),
        DetectionResult(
            beep_time_ms=105,
            shots=[
                ShotEvent(time_ms=260, source=ShotSource.AUTO, confidence=0.95),
                ShotEvent(time_ms=515, source=ShotSource.AUTO, confidence=0.95),
                ShotEvent(time_ms=880, source=ShotSource.AUTO, confidence=0.95),
            ],
            waveform=[0.2],
            sample_rate=22050,
        ),
    ]

    def fake_analyze(path: str, threshold: float) -> DetectionResult:
        return detections.pop(0)

    monkeypatch.setattr("splitshot.ui.controller.analyze_video_audio", fake_analyze)

    controller.analyze_primary()
    first_shot_id = controller.project.analysis.shots[0].id
    second_shot_id = controller.project.analysis.shots[1].id
    controller.add_timing_event("reload", after_shot_id=first_shot_id, before_shot_id=second_shot_id, note="Keep me")
    controller.add_shot(1200)
    manual_shot_id = next(shot.id for shot in controller.project.analysis.shots if shot.source == ShotSource.MANUAL)

    controller.set_detection_threshold(0.55)

    shots = controller.project.analysis.shots
    assert [shot.time_ms for shot in shots] == [260, 515, 880, 1200]
    assert any(shot.id == manual_shot_id and shot.source == ShotSource.MANUAL for shot in shots)
    assert len(controller.project.analysis.events) == 1
    assert controller.project.analysis.events[0].note == "Keep me"
    shot_ids = {shot.id for shot in shots}
    assert controller.project.analysis.events[0].after_shot_id in shot_ids
    assert controller.project.analysis.events[0].before_shot_id in shot_ids
    rows = compute_split_rows(controller.project)
    assert rows[1].interval_label == "Reload"


def test_detection_threshold_rerun_does_not_change_future_app_defaults(monkeypatch) -> None:
    monkeypatch.setattr("splitshot.ui.controller.load_settings", lambda: AppSettings())
    saved_settings: list[dict[str, object]] = []
    monkeypatch.setattr(
        "splitshot.ui.controller.save_settings",
        lambda settings: saved_settings.append(settings.to_dict()),
    )

    controller = ProjectController()

    controller.set_detection_threshold(0.75)

    assert controller.project.analysis.detection_threshold == pytest.approx(0.75)
    assert controller.project.analysis.shotml_settings.detection_threshold == pytest.approx(0.75)
    assert controller.settings.detection_threshold == pytest.approx(0.35)
    assert controller.settings.shotml_defaults.detection_threshold == pytest.approx(0.35)
    assert saved_settings == []

    controller.new_project()

    assert controller.project.analysis.detection_threshold == pytest.approx(0.35)
    assert controller.project.analysis.shotml_settings.detection_threshold == pytest.approx(0.35)


def test_shotml_settings_update_reanalyzes_with_full_settings_object(monkeypatch) -> None:
    controller = ProjectController()
    controller.project.primary_video = VideoAsset(path="/tmp/primary.mp4", duration_ms=2000, width=640, height=360, fps=30.0)
    calls: list[tuple[str, float, int]] = []

    def fake_analyze(path: str, threshold: float, settings) -> DetectionResult:
        calls.append((path, threshold, settings.min_shot_interval_ms))
        return DetectionResult(
            beep_time_ms=390,
            shots=[ShotEvent(time_ms=790, source=ShotSource.AUTO, confidence=0.9)],
            waveform=[0.4, 0.5],
            sample_rate=48000,
        )

    monkeypatch.setattr("splitshot.ui.controller.analyze_video_audio", fake_analyze)

    controller.set_shotml_settings(
        {
            "detection_threshold": 0.42,
            "min_shot_interval_ms": 125,
            "shot_peak_min_spacing_ms": 225,
        },
        rerun=True,
    )

    assert calls == [("/tmp/primary.mp4", 0.42, 125)]
    assert controller.project.analysis.shotml_settings.min_shot_interval_ms == 125
    assert controller.project.analysis.shotml_settings.shot_peak_min_spacing_ms == 225
    assert controller.project.analysis.last_shotml_run_summary["shot_count"] == 1


def test_timing_change_proposals_can_be_generated_applied_and_discarded() -> None:
    controller = ProjectController()
    keeper = ShotEvent(time_ms=500, source=ShotSource.AUTO, confidence=0.99)
    duplicate = ShotEvent(time_ms=620, source=ShotSource.AUTO, confidence=0.55)
    controller.project.analysis.beep_time_ms_primary = 100
    controller.project.analysis.shots = [keeper, duplicate]
    controller.project.analysis.detection_review_suggestions = [
        {
            "kind": "near_cutoff_spacing",
            "severity": "review",
            "message": "Shots are close together.",
            "suggested_action": "review_close_pair",
            "shot_number": 2,
            "shot_time_ms": 620,
            "confidence": 0.55,
            "support_confidence": 0.2,
            "interval_ms": 120,
        },
        {
            "kind": "weak_onset_support",
            "severity": "review",
            "message": "Weak onset.",
            "suggested_action": "review_shot",
            "shot_number": 2,
            "shot_time_ms": 620,
            "confidence": 0.55,
            "support_confidence": 0.2,
        },
    ]

    controller.generate_timing_change_proposals()

    proposal_types = {proposal.proposal_type for proposal in controller.project.analysis.timing_change_proposals}
    assert proposal_types == {"choose_close_pair_survivor", "suppress_shot"}

    suppress = next(
        proposal
        for proposal in controller.project.analysis.timing_change_proposals
        if proposal.proposal_type == "suppress_shot"
    )
    controller.discard_timing_change_proposal(suppress.id)
    assert suppress.status == "discarded"

    close_pair = next(
        proposal
        for proposal in controller.project.analysis.timing_change_proposals
        if proposal.proposal_type == "choose_close_pair_survivor"
    )
    controller.apply_timing_change_proposal(close_pair.id)

    assert [shot.id for shot in controller.project.analysis.shots] == [keeper.id]
    assert close_pair.status == "applied"


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
