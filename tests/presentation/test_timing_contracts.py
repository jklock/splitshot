from __future__ import annotations

import pytest

from splitshot.domain.models import Project, ShotEvent, TimingEvent
from splitshot.presentation.stage import build_stage_presentation
from splitshot.timeline.model import compute_split_rows, normalize_project_timing_events
from splitshot.ui.controller import ProjectController


def _timed_project() -> Project:
    project = Project()
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [
        ShotEvent(time_ms=250, confidence=0.9),
        ShotEvent(time_ms=480, confidence=0.8),
        ShotEvent(time_ms=720, confidence=0.7),
    ]
    return project


def test_timing_event_keeps_valid_after_anchor_when_before_shot_is_deleted() -> None:
    project = _timed_project()
    first, second, third = project.analysis.shots
    project.analysis.events = [
        TimingEvent(
            kind="reload",
            label="Reload",
            after_shot_id=first.id,
            before_shot_id=second.id,
        )
    ]
    project.analysis.shots = [first, third]

    changed = normalize_project_timing_events(project)
    rows = compute_split_rows(project)
    presentation = build_stage_presentation(project)

    assert changed is True
    assert project.analysis.events[0].after_shot_id == first.id
    assert project.analysis.events[0].before_shot_id is None
    assert [row.interval_label for row in rows] == ["Draw", "Reload"]
    assert [segment.interval_label for segment in presentation.timing_segments] == ["Draw", "Reload"]


def test_timing_event_keeps_valid_before_anchor_when_shot_movement_breaks_pair() -> None:
    project = _timed_project()
    first, second, _third = project.analysis.shots
    project.analysis.events = [
        TimingEvent(
            kind="reload",
            label="Reload",
            after_shot_id=first.id,
            before_shot_id=second.id,
        )
    ]
    second.time_ms = 900

    changed = normalize_project_timing_events(project)
    rows = compute_split_rows(project)

    assert changed is True
    assert project.analysis.events[0].after_shot_id is None
    assert project.analysis.events[0].before_shot_id == second.id
    assert [row.shot_id for row in rows] == [first.id, project.analysis.shots[2].id, second.id]
    assert rows[-1].interval_label == "Reload"


def test_timing_event_with_only_invalid_anchors_is_rejected() -> None:
    controller = ProjectController()
    controller.project.analysis.shots = [ShotEvent(time_ms=250)]

    with pytest.raises(ValueError, match="Timing event anchor is invalid"):
        controller.add_timing_event("reload", after_shot_id="missing-shot")
