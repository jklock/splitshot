from __future__ import annotations

from pathlib import Path

from splitshot.domain.models import (
    OverlayPosition,
    Project,
    ScoreLetter,
    ScoreMark,
    ShotEvent,
    ShotSource,
    VideoAsset,
)
from splitshot.persistence.projects import load_project, save_project


def test_project_round_trip_preserves_feature_state(tmp_path: Path) -> None:
    project = Project(name="Round Trip")
    project.primary_video = VideoAsset(path="/tmp/input.mp4", duration_ms=2000, width=640, height=360, fps=30.0)
    project.analysis.beep_time_ms_primary = 400
    project.analysis.waveform_primary = [0.1, 0.2, 0.3]
    project.analysis.shots = [
        ShotEvent(
            time_ms=800,
            source=ShotSource.MANUAL,
            confidence=1.0,
            score=ScoreMark(letter=ScoreLetter.C, x_norm=0.2, y_norm=0.8),
        )
    ]
    project.scoring.enabled = True
    project.scoring.penalties = 10
    project.overlay.position = OverlayPosition.TOP
    project.merge.enabled = True
    project.export.output_path = "/tmp/export.mp4"

    bundle = save_project(project, tmp_path / "round-trip.ssproj")
    loaded = load_project(bundle)

    assert loaded.name == project.name
    assert loaded.primary_video.path == project.primary_video.path
    assert loaded.analysis.beep_time_ms_primary == 400
    assert loaded.analysis.waveform_primary == [0.1, 0.2, 0.3]
    assert len(loaded.analysis.shots) == 1
    assert loaded.analysis.shots[0].score is not None
    assert loaded.analysis.shots[0].score.letter == ScoreLetter.C
    assert loaded.scoring.enabled is True
    assert loaded.scoring.penalties == 10
    assert loaded.overlay.position == OverlayPosition.TOP
    assert loaded.merge.enabled is True
    assert loaded.export.output_path == "/tmp/export.mp4"
