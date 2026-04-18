from __future__ import annotations

import pytest

from splitshot.domain.models import ImportedStageScore, Project, ScoreLetter, ScoreMark, ShotEvent
from splitshot.scoring.logic import (
    apply_scoring_preset,
    calculate_scoring_summary,
    normalize_penalty_counts_for_ruleset,
    normalize_score_letter_for_ruleset,
)


def test_imported_stage_precedence_keeps_manual_shots_as_video_context() -> None:
    project = Project()
    project.scoring.enabled = True
    project.scoring.penalties = 2.0
    project.scoring.penalty_counts = {"procedural_errors": 1}
    project.analysis.beep_time_ms_primary = 1_000
    project.analysis.shots = [
        ShotEvent(time_ms=5_000, score=ScoreMark(letter=ScoreLetter.M)),
        ShotEvent(time_ms=13_000, score=ScoreMark(letter=ScoreLetter.D)),
    ]
    project.scoring.imported_stage = ImportedStageScore(
        source_name="report.txt",
        match_type="uspsa",
        competitor_name="Match Shooter",
        competitor_place=3,
        stage_number=2,
        raw_seconds=10.0,
        aggregate_points=100.0,
        total_points=92.0,
        shot_penalties=8.0,
        hit_factor=9.2,
        score_counts={"A": 18.0, "C": 4.0},
    )

    apply_scoring_preset(project, "uspsa_minor")
    summary = calculate_scoring_summary(project)

    assert summary["raw_seconds"] == 12.0
    assert summary["official_raw_seconds"] == 10.0
    assert summary["raw_delta_seconds"] == 2.0
    assert summary["shot_points"] == 100.0
    assert summary["shot_penalties"] == 8.0
    assert summary["field_penalties"] == 10.0
    assert summary["total_penalties"] == 20.0
    assert summary["hit_factor"] == pytest.approx(92.0 / 12.0)
    assert summary["imported_stage"]["competitor_name"] == "Match Shooter"
    assert summary["imported_stage"]["stage_number"] == 2


def test_preset_switch_clears_incompatible_project_and_shot_penalties() -> None:
    project = Project()
    project.scoring.enabled = True
    apply_scoring_preset(project, "idpa_time_plus")
    project.scoring.penalty_counts = {
        "non_threats": 2,
        "procedural_errors": 1,
    }
    project.analysis.shots = [
        ShotEvent(
            time_ms=1_000,
            score=ScoreMark(
                letter=ScoreLetter.DOWN_3,
                penalty_counts={"non_threats": 1, "procedural_errors": 1},
            ),
        ),
    ]

    apply_scoring_preset(project, "steel_challenge")
    summary = calculate_scoring_summary(project)

    assert project.scoring.penalty_counts == {}
    assert project.analysis.shots[0].score is not None
    assert project.analysis.shots[0].score.letter == ScoreLetter.STEEL_HIT
    assert project.analysis.shots[0].score.penalty_counts == {}
    assert summary["penalty_fields"][0]["id"] == "steel_misses"
    assert summary["field_penalties"] == 0


def test_summary_does_not_revive_incompatible_restored_score_state() -> None:
    project = Project()
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = 0
    project.analysis.shots = [
        ShotEvent(
            time_ms=1_000,
            score=ScoreMark(
                letter=ScoreLetter.DOWN_3,
                penalty_counts={"non_threats": 1},
            ),
        ),
    ]
    apply_scoring_preset(project, "uspsa_minor")
    shot = project.analysis.shots[0]
    assert shot.score is not None

    shot.score.letter = ScoreLetter.DOWN_3
    shot.score.penalty_counts = {"non_threats": 1, "manual_misses": 2}
    project.scoring.penalty_counts = {"non_threats": 3, "manual_misses": 1}

    summary = calculate_scoring_summary(project)

    assert normalize_score_letter_for_ruleset("uspsa_minor", shot.score.letter) == "A"
    assert normalize_penalty_counts_for_ruleset("uspsa_minor", shot.score.penalty_counts) == {
        "manual_misses": 2.0,
    }
    assert summary["shot_points"] == 5
    assert summary["shot_penalties"] == 20
    assert summary["field_penalties"] == 10


def test_imported_time_plus_summary_keeps_video_raw_official_raw_and_delta_contract() -> None:
    project = Project()
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = 250
    project.analysis.shots = [
        ShotEvent(time_ms=2_750, score=ScoreMark(letter=ScoreLetter.DOWN_0)),
    ]
    project.scoring.imported_stage = ImportedStageScore(
        source_name="IDPA.csv",
        match_type="idpa",
        competitor_name="John Klockenkemper",
        competitor_place=4,
        stage_number=2,
        raw_seconds=2.25,
        aggregate_points=5.0,
        final_time=7.25,
    )

    apply_scoring_preset(project, "idpa_time_plus")
    summary = calculate_scoring_summary(project)

    assert summary["raw_seconds"] == 2.5
    assert summary["official_raw_seconds"] == 2.25
    assert summary["raw_delta_seconds"] == 0.25
    assert summary["final_time"] == 7.5
    assert summary["official_final_time"] == 7.25
    assert summary["final_delta_seconds"] == 0.25
    assert summary["display_label"] == "Final"
    assert summary["display_value"] == "7.50"
