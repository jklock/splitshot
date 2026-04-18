from __future__ import annotations

from pathlib import Path

from splitshot.scoring.practiscore import (
    describe_practiscore_file,
    infer_practiscore_context,
    import_practiscore_stage,
)


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "example_data"
WORKSPACE_IDPA_RESULTS = Path(__file__).resolve().parent.parent / "IDPA.csv"


def test_infer_practiscore_context_from_idpa_csv() -> None:
    result = infer_practiscore_context(EXAMPLES_DIR / "IDPA" / "IDPA.csv")

    assert result.match_type == "idpa"
    assert result.stage_number == 1
    assert result.competitor_name == "Jeff Graff"
    assert result.competitor_place == 1


def test_infer_practiscore_context_from_uspsa_report_text() -> None:
    result = infer_practiscore_context(EXAMPLES_DIR / "USPSA" / "report.txt")

    assert result.match_type == "uspsa"
    assert result.stage_number == 1
    assert result.competitor_name == "Ben Rice"
    assert result.competitor_place == 1


def test_describe_practiscore_file_lists_idpa_stage_and_competitor_options() -> None:
    result = describe_practiscore_file(EXAMPLES_DIR / "IDPA" / "IDPA.csv")

    assert result.source_name == "IDPA.csv"
    assert result.match_type == "idpa"
    assert result.stage_numbers == [1, 2, 3, 4]
    assert result.competitors[0].name == "Jeff Graff"
    assert result.competitors[0].place == 1
    assert any(option.name == "John Klockenkemper" and option.place == 4 for option in result.competitors)


def test_describe_practiscore_file_lists_hit_factor_stage_and_competitor_options() -> None:
    result = describe_practiscore_file(EXAMPLES_DIR / "USPSA" / "report.txt")

    assert result.source_name == "report.txt"
    assert result.match_type == "uspsa"
    assert result.stage_numbers == [1, 2, 3, 4, 5, 6]
    assert result.competitors[0].name == "Ben Rice"
    assert result.competitors[0].place == 1
    assert any(option.name == "Stephen Lutman" and option.place == 1 for option in result.competitors)


def test_import_idpa_stage_results_from_csv() -> None:
    result = import_practiscore_stage(
        EXAMPLES_DIR / "IDPA" / "IDPA.csv",
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
    assert result.imported_stage.raw_seconds == 19.83
    assert result.imported_stage.aggregate_points == 5.0
    assert result.imported_stage.final_time == 29.83
    assert result.imported_stage.score_counts == {"Points Down": 5.0}


def test_import_idpa_stage_time_is_treated_as_final_time() -> None:
    result = import_practiscore_stage(
        EXAMPLES_DIR / "IDPA" / "IDPA.csv",
        match_type="idpa",
        stage_number=1,
        competitor_name="John Klockenkemper",
        competitor_place=4,
        source_name="IDPA.csv",
    )

    assert result.imported_stage.stage_number == 1
    assert result.imported_stage.final_time == 14.55
    assert result.imported_stage.raw_seconds == 13.55
    assert result.imported_stage.aggregate_points == 1.0
    assert result.penalty_counts == {}


def test_import_uspsa_stage_results_from_report_text() -> None:
    result = import_practiscore_stage(
        EXAMPLES_DIR / "USPSA" / "report.txt",
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


def test_describe_practiscore_file_handles_idpa_dnf_place_rows() -> None:
    result = describe_practiscore_file(WORKSPACE_IDPA_RESULTS, source_name="thursday-night.csv")

    assert result.source_name == "thursday-night.csv"
    assert result.match_type == "idpa"
    assert result.stage_numbers == [1, 2, 3, 4]
    assert any(option.name == "John Klockenkemper" and option.place == 6 for option in result.competitors)
    assert any(option.name == "Ben Brown" and option.place is None for option in result.competitors)


def test_infer_practiscore_context_falls_back_to_name_when_place_changes() -> None:
    result = infer_practiscore_context(
        WORKSPACE_IDPA_RESULTS,
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )

    assert result.match_type == "idpa"
    assert result.stage_number == 2
    assert result.competitor_name == "John Klockenkemper"
    assert result.competitor_place == 6