from __future__ import annotations

from splitshot.domain.models import Project, ShotEvent, TimingEvent
from splitshot.presentation.stage import build_stage_presentation


def test_stage_presentation_exposes_full_beep_to_final_timing() -> None:
    project = Project()
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [
        ShotEvent(time_ms=250, confidence=0.9),
        ShotEvent(time_ms=400, confidence=0.8),
        ShotEvent(time_ms=750, confidence=0.7),
    ]

    presentation = build_stage_presentation(project)

    assert presentation.metrics.draw_ms == 150
    assert presentation.metrics.raw_time_ms == 650
    assert presentation.metrics.stage_time_ms == 650
    assert presentation.metrics.final_shot_ms == 750

    segments = presentation.timing_segments
    assert [segment.label for segment in segments] == ["Shot 1", "Shot 2", "Shot 3"]
    assert [segment.interval_label for segment in segments] == ["Draw", "Split", "Split"]
    assert [segment.segment_ms for segment in segments] == [150, 150, 350]
    assert [segment.cumulative_ms for segment in segments] == [150, 300, 650]
    assert [segment.sequence_total_ms for segment in segments] == [150, 300, 650]
    assert segments[0].card_title == "Shot 1"
    assert segments[-1].card_value == "0.35"
    assert "Split 0.35s" in segments[-1].card_meta
    assert "Run 0.65s" in segments[-1].card_meta
    assert "Stage 0.65s" in segments[-1].card_meta
    assert "ShotML" in segments[-1].card_meta


def test_stage_presentation_keeps_following_shot_split_after_timing_event() -> None:
    project = Project()
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [
        ShotEvent(time_ms=250, confidence=0.9),
        ShotEvent(time_ms=480, confidence=0.8),
        ShotEvent(time_ms=720, confidence=0.7),
    ]
    project.analysis.events = [
        TimingEvent(
            kind="reload",
            label="Reload",
            after_shot_id=project.analysis.shots[0].id,
            before_shot_id=project.analysis.shots[1].id,
        )
    ]

    presentation = build_stage_presentation(project)

    assert [segment.label for segment in presentation.timing_segments] == ["Shot 1", "Shot 2", "Shot 3"]
    assert [segment.interval_label for segment in presentation.timing_segments] == ["Draw", "Reload", "Split"]
    assert [segment.segment_ms for segment in presentation.timing_segments] == [150, 230, 240]
    assert [segment.sequence_total_ms for segment in presentation.timing_segments] == [150, 230, 470]
