from __future__ import annotations

import json
from pathlib import Path

from splitshot.domain.models import (
    ImportedStageScore,
    MergeSource,
    Project,
    ProjectStage,
    VideoAsset,
)
from splitshot.persistence.projects import (
    INPUT_DIRNAME,
    INTRO_OUTRO_DIRNAME,
    MARKERS_DIRNAME,
    OUTPUT_DIRNAME,
    PRACTISCORE_DIRNAME,
    copy_path_to_project_subdir,
    delete_project,
    load_project,
    missing_required_project_dirs,
    normalize_project_path,
    project_has_metadata,
    save_project,
)


def test_normalize_project_path_strips_metadata_filename_and_expands_user() -> None:
    normalized = normalize_project_path("~/splitshot/example.ssproj/project.json")

    assert normalized == (Path.home() / "splitshot" / "example.ssproj").resolve(strict=False)


def test_project_metadata_detection_accepts_normalized_project_json_path(tmp_path: Path) -> None:
    project_path = tmp_path / "metadata-probe.ssproj"
    save_project(Project(), project_path)

    assert project_has_metadata(normalize_project_path(project_path / "project.json")) is True
    assert project_has_metadata(normalize_project_path(project_path)) is True


def test_save_project_persists_project_local_practiscore_path_without_copying(tmp_path: Path) -> None:
    project_path = tmp_path / "practiscore-bundle.ssproj"
    source_csv = tmp_path / "IDPA.csv"
    source_csv.write_text("stage data", encoding="utf-8")

    staged_path = Path(
        copy_path_to_project_subdir(
            project_path, str(source_csv), PRACTISCORE_DIRNAME, preferred_name="IDPA.csv"
        )
    )
    project = Project(name="PractiScore Bundle")
    project.scoring.match_type = "idpa"
    project.scoring.stage_number = 2
    project.scoring.competitor_name = "John Klockenkemper"
    project.scoring.competitor_place = 4
    project.scoring.practiscore_source_path = str(staged_path)
    project.scoring.practiscore_source_name = "IDPA.csv"
    project.scoring.imported_stage = ImportedStageScore(
        source_name="IDPA.csv",
        source_path=str(staged_path),
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
    assert staged_path.read_text(encoding="utf-8") == "stage data"
    assert Path(saved["scoring"]["practiscore_source_path"]) == Path(
        f"{PRACTISCORE_DIRNAME}/IDPA.csv"
    )
    assert Path(saved["scoring"]["imported_stage"]["source_path"]) == Path(
        f"{PRACTISCORE_DIRNAME}/IDPA.csv"
    )

    loaded = load_project(project_path / "project.json")

    assert loaded.scoring.practiscore_source_path == str(staged_path.resolve())
    assert loaded.scoring.imported_stage is not None
    assert loaded.scoring.imported_stage.source_path == str(staged_path.resolve())
    assert loaded.scoring.imported_stage.final_time == 29.83


def test_save_project_preserves_details_and_external_primary_without_copying(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "details-round-trip.ssproj"
    primary = tmp_path / "primary.mp4"
    primary.write_bytes(b"not a real video but enough for persistence staging")

    project = Project(name="Classifier Template", description="Carry these settings forward")
    project.primary_video = VideoAsset(
        path=str(primary), duration_ms=1234, width=640, height=360, fps=30.0
    )

    save_project(project, project_path / "project.json")
    loaded = load_project(project_path / "project.json")

    assert loaded.name == "Classifier Template"
    assert loaded.description == "Carry these settings forward"
    assert loaded.primary_video.path == str(primary.resolve())
    assert not (project_path / "Input" / "primary.mp4").exists()


def test_save_and_load_normalize_media_paths_for_every_stage(tmp_path: Path) -> None:
    project_path = tmp_path / "all-stages.ssproj"
    input_path = project_path / INPUT_DIRNAME
    input_path.mkdir(parents=True)
    first_path = input_path / "first.mp4"
    second_path = input_path / "second.mp4"
    added_path = input_path / "added.mp4"
    for path in (first_path, second_path, added_path):
        path.write_bytes(path.name.encode("utf-8"))

    first = ProjectStage(
        label="Stage 1",
        order_index=1,
        primary_media=VideoAsset(path=str(first_path)),
    )
    second = ProjectStage(
        label="Stage 2",
        order_index=2,
        primary_media=VideoAsset(path=str(second_path)),
        added_media=[MergeSource(asset=VideoAsset(path=str(added_path)))],
    )
    project = Project(stages=[first, second], active_stage_id=first.id)
    project.primary_video = VideoAsset(path=str(first_path))

    save_project(project, project_path)
    saved = json.loads((project_path / "project.json").read_text(encoding="utf-8"))

    assert saved["primary_video"]["path"] == "Input/first.mp4"
    assert saved["stages"][0]["primary_media"]["path"] == "Input/first.mp4"
    assert saved["stages"][1]["primary_media"]["path"] == "Input/second.mp4"
    assert saved["stages"][1]["added_media"][0]["asset"]["path"] == "Input/added.mp4"

    loaded = load_project(project_path)
    assert loaded.stages[0].primary_media.path == str(first_path.resolve())
    assert loaded.stages[1].primary_media.path == str(second_path.resolve())
    assert loaded.stages[1].added_media[0].asset.path == str(added_path.resolve())


def test_project_import_copy_reuses_identical_file_and_suffixes_different_content(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "imports.ssproj"
    first = tmp_path / "one" / "stage.mp4"
    duplicate = tmp_path / "two" / "stage.mp4"
    different = tmp_path / "three" / "stage.mp4"
    for path, content in ((first, b"same"), (duplicate, b"same"), (different, b"different")):
        path.parent.mkdir()
        path.write_bytes(content)

    first_import = copy_path_to_project_subdir(project_path, str(first), INPUT_DIRNAME)
    duplicate_import = copy_path_to_project_subdir(project_path, str(duplicate), INPUT_DIRNAME)
    different_import = copy_path_to_project_subdir(project_path, str(different), INPUT_DIRNAME)

    assert duplicate_import == first_import
    assert Path(different_import).name == "stage_1.mp4"


def test_missing_required_project_dirs_reports_only_missing_entries(tmp_path: Path) -> None:
    project_path = tmp_path / "partial.ssproj"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / INPUT_DIRNAME).mkdir()

    assert missing_required_project_dirs(project_path) == [
        PRACTISCORE_DIRNAME,
        MARKERS_DIRNAME,
        INTRO_OUTRO_DIRNAME,
        OUTPUT_DIRNAME,
    ]


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
    assert (project_path / MARKERS_DIRNAME).is_dir()
    assert (project_path / OUTPUT_DIRNAME).is_dir()
    assert staged_csv.read_text(encoding="utf-8") == "data"
