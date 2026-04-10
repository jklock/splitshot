from __future__ import annotations

from splitshot.domain.models import (
    MergeLayout,
    PipSize,
    Project,
    ScoreLetter,
    ScoreMark,
    ShotEvent,
    VideoAsset,
)
from splitshot.merge.layouts import calculate_merge_canvas
from splitshot.scoring.logic import calculate_hit_factor, current_shot_index


def test_hit_factor_uses_shot_scores_and_penalties() -> None:
    project = Project()
    project.scoring.enabled = True
    project.scoring.penalties = 5
    project.analysis.shots = [
        ShotEvent(time_ms=800, score=ScoreMark(letter=ScoreLetter.A)),
        ShotEvent(time_ms=1100, score=ScoreMark(letter=ScoreLetter.C)),
        ShotEvent(time_ms=1450, score=ScoreMark(letter=ScoreLetter.D)),
    ]

    hit_factor = calculate_hit_factor(project)
    assert hit_factor is not None
    assert round(hit_factor, 2) == round((5 + 3 + 1 - 5) / 1.45, 2)


def test_current_shot_tracks_playback_position() -> None:
    project = Project()
    project.analysis.shots = [
        ShotEvent(time_ms=800),
        ShotEvent(time_ms=1100),
        ShotEvent(time_ms=1450),
    ]

    assert current_shot_index(project, 799) is None
    assert current_shot_index(project, 1101) == 1
    assert current_shot_index(project, 1600) == 2


def test_merge_canvas_covers_layouts() -> None:
    primary = VideoAsset(path="primary.mp4", width=640, height=360, fps=30.0)
    secondary = VideoAsset(path="secondary.mp4", width=1280, height=720, fps=30.0)

    side = calculate_merge_canvas(primary, secondary, MergeLayout.SIDE_BY_SIDE, PipSize.MEDIUM)
    assert side.width > 640
    assert side.height == 720

    above = calculate_merge_canvas(primary, secondary, MergeLayout.ABOVE_BELOW, PipSize.MEDIUM)
    assert above.width == 1280
    assert above.height > 720

    pip = calculate_merge_canvas(primary, secondary, MergeLayout.PIP, PipSize.LARGE)
    assert pip.width == 640
    assert pip.secondary_rect is not None
    assert pip.secondary_rect.width < pip.width
