from __future__ import annotations

import json
from pathlib import Path

from splitshot.domain.models import ImportedStageScore, Project, VideoAsset
from splitshot.persistence.projects import (
    INPUT_DIRNAME,
    OUTPUT_DIRNAME,
    PRACTISCORE_DIRNAME,
    delete_project,
    missing_required_project_dirs,
    normalize_project_path,
    project_has_metadata,
    save_project,
    load_project,
)


def test_normalize_project_path_strips_metadata_filename_and_expands_user() -> None:
    normalized = normalize_project_path("~/splitshot/example.ssproj/project.json")

    assert normalized == (Path.home() / "splitshot" / "example.ssproj").resolve(strict=False)


def test_project_metadata_detection_accepts_normalized_project_json_path(tmp_path: Path) -> None:
    project_path = tmp_path / "metadata-probe.ssproj"
    save_project(Project(), project_path)

    assert project_has_metadata(normalize_project_path(project_path / "project.json")) is True
    assert project_has_metadata(normalize_project_path(project_path)) is True


def test_save_project_stages_practiscore_source_once_and_load_resolves_path(tmp_path: Path) -> None:
    project_path = tmp_path / "practiscore-bundle.ssproj"
    source_csv = tmp_path / "IDPA.csv"
    source_csv.write_text("stage data", encoding="utf-8")

    project = Project(name="PractiScore Bundle")
    project.scoring.match_type = "idpa"
    project.scoring.stage_number = 2
    project.scoring.competitor_name = "John Klockenkemper"
    project.scoring.competitor_place = 4
    project.scoring.practiscore_source_path = str(source_csv)
    project.scoring.practiscore_source_name = "IDPA.csv"
    project.scoring.imported_stage = ImportedStageScore(
        source_name="IDPA.csv",
        source_path=str(source_csv),
        match_type="idpa",
        competitor_name="John Klockenkemper",
        competitor_place=4,
        stage_number=2,
        raw_seconds=19.83,
        aggregate_points=5.0,
        final_time=29.83,
    )

    save_project(project, project_path)
    saved = json.loads((project_path / "project.json").read_text(encoding="utf-8"))
    staged_path = project_path / PRACTISCORE_DIRNAME / "IDPA.csv"

    assert staged_path.read_text(encoding="utf-8") == "stage data"
    assert saved["scoring"]["practiscore_source_path"] == f"{PRACTISCORE_DIRNAME}/IDPA.csv"
    assert saved["scoring"]["imported_stage"]["source_path"] == f"{PRACTISCORE_DIRNAME}/IDPA.csv"

    loaded = load_project(project_path / "project.json")

    assert loaded.scoring.practiscore_source_path == str(staged_path.resolve())
    assert loaded.scoring.imported_stage is not None
    assert loaded.scoring.imported_stage.source_path == str(staged_path.resolve())
    assert loaded.scoring.imported_stage.final_time == 29.83


def test_save_project_preserves_details_and_primary_after_project_json_path_round_trip(tmp_path: Path) -> None:
    project_path = tmp_path / "details-round-trip.ssproj"
    primary = tmp_path / "primary.mp4"
    primary.write_bytes(b"not a real video but enough for persistence staging")

    project = Project(name="Classifier Template", description="Carry these settings forward")
    project.primary_video = VideoAsset(path=str(primary), duration_ms=1234, width=640, height=360, fps=30.0)

    save_project(project, project_path / "project.json")
    loaded = load_project(project_path / "project.json")

    assert loaded.name == "Classifier Template"
    assert loaded.description == "Carry these settings forward"
    assert Path(loaded.primary_video.path).parent == (project_path / "Input").resolve()
    assert Path(loaded.primary_video.path).name == "primary.mp4"


def test_missing_required_project_dirs_reports_only_missing_entries(tmp_path: Path) -> None:
    project_path = tmp_path / "partial.ssproj"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / INPUT_DIRNAME).mkdir()

    assert missing_required_project_dirs(project_path) == [PRACTISCORE_DIRNAME, OUTPUT_DIRNAME]


def test_delete_project_removes_only_project_metadata(tmp_path: Path) -> None:
    project_path = tmp_path / "metadata-only-delete.ssproj"
    save_project(Project(), project_path)
    staged_csv = project_path / PRACTISCORE_DIRNAME / "results.csv"
    staged_csv.write_text("data", encoding="utf-8")

    delete_project(project_path)

    assert project_path.exists()
    assert not (project_path / "project.json").exists()
    assert (project_path / INPUT_DIRNAME).is_dir()
    assert (project_path / PRACTISCORE_DIRNAME).is_dir()
    assert (project_path / OUTPUT_DIRNAME).is_dir()
    assert staged_csv.read_text(encoding="utf-8") == "data"
