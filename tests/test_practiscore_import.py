from __future__ import annotations

from pathlib import Path

from splitshot.scoring.practiscore import import_practiscore_stage


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_import_idpa_stage_results_from_csv() -> None:
    result = import_practiscore_stage(
        EXAMPLES_DIR / "IDPA.csv",
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
        source_name="IDPA.csv",
    )

    assert result.ruleset == "idpa_time_plus"
    assert result.manual_penalties == 0.0
    assert result.penalty_counts == {"non_threats": 1.0}
    assert result.imported_stage.source_name == "IDPA.csv"
    assert result.imported_stage.match_type == "idpa"
    assert result.imported_stage.competitor_name == "John Klockenkemper"
    assert result.imported_stage.competitor_place == 4
    assert result.imported_stage.stage_number == 2
    assert result.imported_stage.raw_seconds == 29.83
    assert result.imported_stage.aggregate_points == 5.0
    assert result.imported_stage.final_time == 39.83
    assert result.imported_stage.score_counts == {"Points Down": 5.0}


def test_import_uspsa_stage_results_from_report_text() -> None:
    result = import_practiscore_stage(
        EXAMPLES_DIR / "report.txt",
        match_type="uspsa",
        stage_number=1,
        competitor_name="Lutman, Stephen",
        competitor_place=1,
        source_name="report.txt",
    )

    assert result.ruleset == "uspsa_minor"
    assert result.manual_penalties == 0.0
    assert result.penalty_counts == {}
    assert result.imported_stage.source_name == "report.txt"
    assert result.imported_stage.match_type == "uspsa"
    assert result.imported_stage.competitor_name == "Stephen Lutman"
    assert result.imported_stage.competitor_place == 1
    assert result.imported_stage.stage_number == 1
    assert result.imported_stage.stage_name == "Stage 1 Swangin’"
    assert result.imported_stage.division == "Limited"
    assert result.imported_stage.classification == "M"
    assert result.imported_stage.power_factor == "Minor"
    assert result.imported_stage.raw_seconds == 23.24
    assert result.imported_stage.aggregate_points == 101.0
    assert result.imported_stage.total_points == 101.0
    assert result.imported_stage.shot_penalties == 0.0
    assert result.imported_stage.hit_factor == 4.346
    assert result.imported_stage.stage_points == 125.0
    assert result.imported_stage.stage_place == 1
    assert result.imported_stage.score_counts == {"A": 15.0, "C": 8.0, "D": 2.0}