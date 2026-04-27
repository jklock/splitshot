from __future__ import annotations

from pathlib import Path

from splitshot.scoring.practiscore_sync_normalize import normalize_downloaded_practiscore_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "example_data"


def _changed_place_idpa_results(tmp_path: Path) -> Path:
    source = (EXAMPLES_DIR / "IDPA" / "IDPA.csv").read_text(encoding="utf-8")
    source = source.replace(
        "4,CO,UN,Klockenkemper,John,A1035577,,1,1,0,,83.01,11,1,1,,,,14.55,1,,,,,,,29.83,5,1,,,,,,18.62,5,,,,,,,20.01,,,1,,,,",
        "6,CO,UN,Klockenkemper,John,A1035577,,1,1,0,,83.01,11,1,1,,,,14.55,1,,,,,,,20.57,5,1,,,,,,18.62,5,,,,,,,20.01,,,1,,,,",
    )
    source = source.replace(
        "8,PCC,NV,Brown,Ben,A598326,,1,1,0,,88.21,15,,,,,,19.21,7,,,,,,,32.95,4,,,,,,,15.32,2,,,,,,,20.73,2,,,,,,",
        ",PCC,NV,Brown,Ben,A598326,,1,0,1,,88.21,15,,,,,,19.21,7,,,,,,,32.95,4,,,,,,,15.32,2,,,,,,,20.73,2,,,,,,",
    )
    path = tmp_path / "thursday-night.csv"
    path.write_text(source, encoding="utf-8")
    return path


def test_normalize_downloaded_idpa_artifact_matches_existing_import_semantics() -> None:
    normalized = normalize_downloaded_practiscore_artifact(
        EXAMPLES_DIR / "IDPA" / "IDPA.csv",
        source_name="remote-idpa.csv",
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )

    assert normalized.options.match_type == "idpa"
    assert normalized.resolved_context.stage_number == 2
    assert normalized.resolved_context.competitor_name == "John Klockenkemper"
    assert normalized.stage_import.imported_stage.source_name == "remote-idpa.csv"
    assert normalized.stage_import.imported_stage.final_time == 29.83
    assert normalized.stage_import.imported_stage.raw_seconds == 19.83
    assert normalized.stage_import.imported_stage.score_counts == {"Points Down": 5.0}


def test_normalize_downloaded_artifact_preserves_place_change_name_fallback(tmp_path: Path) -> None:
    normalized = normalize_downloaded_practiscore_artifact(
        _changed_place_idpa_results(tmp_path),
        source_name="thursday-night.csv",
        match_type="idpa",
        stage_number=2,
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )

    assert normalized.resolved_context.competitor_name == "John Klockenkemper"
    assert normalized.resolved_context.competitor_place == 6
    assert normalized.stage_import.imported_stage.competitor_place == 6


def test_normalize_downloaded_artifact_handles_last_first_name_equivalence() -> None:
    normalized = normalize_downloaded_practiscore_artifact(
        EXAMPLES_DIR / "USPSA" / "report.txt",
        source_name="remote-report.txt",
        match_type="uspsa",
        stage_number=1,
        competitor_name="Lutman, Stephen",
        competitor_place=1,
    )

    assert normalized.resolved_context.match_type == "uspsa"
    assert normalized.resolved_context.competitor_name == "Stephen Lutman"
    assert normalized.stage_import.imported_stage.competitor_name == "Stephen Lutman"
    assert normalized.stage_import.imported_stage.stage_number == 1