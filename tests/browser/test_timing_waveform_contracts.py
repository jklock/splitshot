from __future__ import annotations

from pathlib import Path

import splitshot.ui.controller as controller_module

from splitshot.analysis.detection import DetectionResult
from splitshot.browser.state import browser_state
from splitshot.domain.models import ShotEvent, ShotSource, VideoAsset
from splitshot.ui.controller import ProjectController


def _shots(*times: int) -> list[ShotEvent]:
    return [ShotEvent(time_ms=time_ms, confidence=0.9) for time_ms in times]


def test_delete_selected_shot_falls_back_to_surviving_timing_row() -> None:
    controller = ProjectController()
    first, selected, fallback = _shots(250, 480, 720)
    controller.project.analysis.beep_time_ms_primary = 100
    controller.project.analysis.shots = [first, selected, fallback]
    controller.project.ui_state.selected_shot_id = selected.id
    controller.project.ui_state.scoring_shot_expansion = {
        selected.id: True,
        fallback.id: False,
    }
    controller.project.ui_state.waveform_shot_amplitudes = {
        selected.id: 1.5,
        fallback.id: 1.2,
    }
    controller.project.ui_state.timing_edit_shot_ids = [selected.id, fallback.id]

    controller.delete_shot(selected.id)

    payload = browser_state(controller.project, controller.status_message)
    shot_ids = {shot["id"] for shot in payload["project"]["analysis"]["shots"]}
    segment_ids = {segment["shot_id"] for segment in payload["timing_segments"]}
    row_ids = {row["shot_id"] for row in payload["split_rows"]}

    assert payload["project"]["ui_state"]["selected_shot_id"] == fallback.id
    assert payload["project"]["ui_state"]["scoring_shot_expansion"] == {fallback.id: False}
    assert payload["project"]["ui_state"]["waveform_shot_amplitudes"] == {fallback.id: 1.2}
    assert payload["project"]["ui_state"]["timing_edit_shot_ids"] == [fallback.id]
    assert fallback.id in shot_ids
    assert fallback.id in segment_ids
    assert fallback.id in row_ids


def test_threshold_reanalysis_restores_selection_by_nearest_time(monkeypatch) -> None:
    controller = ProjectController()
    controller.project.primary_video = VideoAsset(path="primary.mp4")
    initial_shots = _shots(250, 500, 900)
    reanalyzed_shots = _shots(260, 515, 880)
    detections = [
        DetectionResult(beep_time_ms=100, shots=initial_shots, waveform=[0.1], sample_rate=22050),
        DetectionResult(beep_time_ms=100, shots=reanalyzed_shots, waveform=[0.2], sample_rate=22050),
    ]

    def fake_analyze_video_audio(path: str, threshold: float) -> DetectionResult:
        return detections.pop(0)

    monkeypatch.setattr(controller_module, "analyze_video_audio", fake_analyze_video_audio)

    controller.analyze_primary()
    previous_selected_shot = controller.project.analysis.shots[1]
    controller.select_shot(previous_selected_shot.id)

    controller.set_detection_threshold(0.75)

    selected_shot_id = controller.project.ui_state.selected_shot_id
    selected_shot = next(shot for shot in controller.project.analysis.shots if shot.id == selected_shot_id)
    assert selected_shot.id == reanalyzed_shots[1].id
    assert selected_shot.time_ms == 515
    assert selected_shot.id != previous_selected_shot.id


def test_threshold_reanalysis_resets_adjusted_shotml_splits_but_keeps_user_added_shots(monkeypatch) -> None:
    controller = ProjectController()
    controller.project.primary_video = VideoAsset(path="primary.mp4")
    initial_shots = _shots(250, 500, 900)
    reanalyzed_shots = _shots(260, 515, 880)
    detections = [
        DetectionResult(beep_time_ms=100, shots=initial_shots, waveform=[0.1], sample_rate=22050),
        DetectionResult(beep_time_ms=100, shots=reanalyzed_shots, waveform=[0.2], sample_rate=22050),
    ]

    def fake_analyze_video_audio(path: str, threshold: float) -> DetectionResult:
        return detections.pop(0)

    monkeypatch.setattr(controller_module, "analyze_video_audio", fake_analyze_video_audio)

    controller.analyze_primary()
    first = controller.project.analysis.shots[0]
    controller.move_shot(first.id, first.time_ms - 30, preserve_following_splits=True)
    controller.add_shot(1300)

    controller.set_detection_threshold(0.75)

    detected_times = [shot.time_ms for shot in controller.project.analysis.shots if not shot.user_added]
    user_added_times = [shot.time_ms for shot in controller.project.analysis.shots if shot.user_added]
    assert detected_times == [260, 515, 880]
    assert user_added_times == [1300]


def test_browser_state_filters_stale_timing_selection_references() -> None:
    controller = ProjectController()
    surviving = _shots(350)[0]
    controller.project.analysis.shots = [surviving]
    controller.project.ui_state.selected_shot_id = "deleted-shot"
    controller.project.ui_state.timing_edit_shot_ids = ["deleted-shot", surviving.id]

    payload = browser_state(controller.project, controller.status_message)

    assert payload["project"]["ui_state"]["selected_shot_id"] is None
    assert payload["project"]["ui_state"]["timing_edit_shot_ids"] == [surviving.id]


def test_split_adjustment_preserves_shotml_split_baseline_and_following_splits() -> None:
    controller = ProjectController()
    first, second, third = _shots(250, 480, 720)
    controller.project.analysis.beep_time_ms_primary = 100
    controller.project.analysis.shots = [first, second, third]
    controller._remember_original_shots()

    controller.move_shot(first.id, 220, preserve_following_splits=True)

    assert [shot.time_ms for shot in controller.project.analysis.shots] == [220, 450, 690]
    assert [shot.source for shot in controller.project.analysis.shots] == [
        ShotSource.AUTO,
        ShotSource.AUTO,
        ShotSource.AUTO,
    ]
    assert [shot.confidence for shot in controller.project.analysis.shots] == [0.9, 0.9, 0.9]
    payload = browser_state(controller.project, controller.status_message)
    assert [row["split_ms"] for row in payload["split_rows"]] == [120, 230, 240]
    assert [row["cumulative_ms"] for row in payload["split_rows"]] == [120, 350, 590]
    assert [row["shotml_split_ms"] for row in payload["split_rows"]] == [150, 230, 240]
    assert [row["shotml_cumulative_ms"] for row in payload["split_rows"]] == [150, 380, 620]
    assert [row["shotml_confidence"] for row in payload["split_rows"]] == [0.9, 0.9, 0.9]
    assert [row["adjustment_ms"] for row in payload["split_rows"]] == [-30, 0, 0]
    assert [row["final_time_ms"] for row in payload["split_rows"]] == [120, 350, 590]

    controller.restore_original_shot_timing(first.id, preserve_following_splits=True)

    assert [shot.time_ms for shot in controller.project.analysis.shots] == [250, 480, 720]
    assert [shot.source for shot in controller.project.analysis.shots] == [
        ShotSource.AUTO,
        ShotSource.AUTO,
        ShotSource.AUTO,
    ]
    assert [shot.confidence for shot in controller.project.analysis.shots] == [0.9, 0.9, 0.9]


def test_app_uses_single_resolved_selection_for_timing_and_waveform() -> None:
    app_js = (Path(__file__).resolve().parents[2] / "src/splitshot/browser/static/app.js").read_text(
        encoding="utf-8"
    )

    assert "function resolveSelectedShotId" in app_js
    assert "function syncSelectedShotId" in app_js
    assert "syncSelectedShotId();" in app_js
    assert "pendingSelectionFallback = shotSelectionContext(selectedShotId, state, \"time\");" in app_js
