from __future__ import annotations

import pytest

from splitshot.domain.models import PopupBubble, PopupMotionPoint, Project, ScoreLetter, ScoreMark, ShotEvent, ShotSource
from splitshot.presentation.popups import (
    popup_bubble_display_text,
    popup_bubble_is_visible_at,
    popup_bubble_point,
    popup_bubble_time_ms,
    popup_bubble_visible_window,
)


def test_popup_bubble_time_uses_shot_anchor_when_available() -> None:
    project = Project()
    project.analysis.shots = [
        ShotEvent(id="late-shot", time_ms=1300, source=ShotSource.AUTO),
        ShotEvent(id="early-shot", time_ms=420, source=ShotSource.AUTO),
    ]
    popup = PopupBubble(anchor_mode="shot", shot_id="early-shot", time_ms=9999, duration_ms=600)

    assert popup_bubble_time_ms(project, popup) == 420
    assert popup_bubble_visible_window(project, popup) == (420, 1020)
    assert not popup_bubble_is_visible_at(project, popup, 419)
    assert popup_bubble_is_visible_at(project, popup, 420)
    assert popup_bubble_is_visible_at(project, popup, 1020)
    assert not popup_bubble_is_visible_at(project, popup, 1021)


def test_popup_bubble_display_text_uses_live_shot_score_and_penalties() -> None:
    project = Project()
    project.scoring.ruleset = "idpa_time_plus"
    project.analysis.shots = [
        ShotEvent(
            id="shot-score",
            time_ms=500,
            source=ShotSource.AUTO,
            score=ScoreMark(letter=ScoreLetter.DOWN_1, penalty_counts={"procedural_errors": 1}),
        )
    ]
    popup = PopupBubble(anchor_mode="shot", shot_id="shot-score", text="fallback")

    assert popup_bubble_display_text(project, popup) == "-1 | PE x1"


def test_popup_bubble_display_text_falls_back_for_missing_shot_or_time_anchor() -> None:
    project = Project()

    assert popup_bubble_display_text(project, PopupBubble(anchor_mode="time", text="Manual")) == "Manual"
    assert popup_bubble_display_text(project, PopupBubble(anchor_mode="shot", shot_id="missing", text="Fallback")) == "Fallback"


def test_popup_bubble_motion_interpolates_and_dedupes_points() -> None:
    project = Project()
    popup = PopupBubble(
        anchor_mode="time",
        time_ms=100,
        duration_ms=2000,
        quadrant="custom",
        x=0.2,
        y=0.3,
        follow_motion=True,
        motion_path=[
            PopupMotionPoint(offset_ms=1000, x=0.8, y=0.9),
            PopupMotionPoint(offset_ms=1000, x=0.6, y=0.7),
            PopupMotionPoint(offset_ms=2000, x=2.0, y=-1.0),
        ],
    )

    assert popup_bubble_point(project, popup, 100) == pytest.approx((0.2, 0.3))
    assert popup_bubble_point(project, popup, 600) == pytest.approx((0.4, 0.5))
    assert popup_bubble_point(project, popup, 1100) == pytest.approx((0.6, 0.7))
    assert popup_bubble_point(project, popup, 2100) == pytest.approx((1.0, 0.0))


@pytest.mark.parametrize(
    ("easing", "position_ms", "expected"),
    [
        ("hold", 500, (0.2, 0.3)),
        ("ease_in", 500, (0.35, 0.45)),
        ("ease_out", 500, (0.65, 0.75)),
        ("ease_in_out", 500, (0.5, 0.6)),
        ("bogus", 500, (0.5, 0.6)),
    ],
)
def test_popup_bubble_motion_supports_easing_modes(easing: str, position_ms: int, expected: tuple[float, float]) -> None:
    project = Project()
    popup = PopupBubble(
        anchor_mode="time",
        time_ms=0,
        duration_ms=1000,
        quadrant="custom",
        x=0.2,
        y=0.3,
        follow_motion=True,
        motion_path=[PopupMotionPoint(offset_ms=1000, x=0.8, y=0.9, easing=easing)],
    )

    assert popup_bubble_point(project, popup, position_ms) == pytest.approx(expected)
