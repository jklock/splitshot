from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from splitshot.domain.models import MergeSource, Project, project_from_dict, project_to_dict

PROJECT_FILENAME = "project.json"
INPUT_DIRNAME = "Input"
PRACTISCORE_DIRNAME = "CSV"
OUTPUT_DIRNAME = "Output"

_BROWSER_UPLOAD_PREFIX = re.compile(r"^[A-Fa-f0-9]{32}_")


def resolve_project_path(path: str | Path) -> Path:
    project_path = Path(path)
    if project_path.name == PROJECT_FILENAME:
        return project_path.parent
    return project_path


def normalize_project_path(path: str | Path) -> Path:
    return resolve_project_path(path).expanduser().resolve(strict=False)


def ensure_project_suffix(path: str | Path) -> Path:
    return resolve_project_path(path)


def project_metadata_path(path: str | Path) -> Path:
    return resolve_project_path(path) / PROJECT_FILENAME


def project_has_metadata(path: str | Path) -> bool:
    return project_metadata_path(path).is_file()


def ensure_project_structure(path: str | Path) -> Path:
    project_path = resolve_project_path(path)
    project_path.mkdir(parents=True, exist_ok=True)
    for dirname in (INPUT_DIRNAME, PRACTISCORE_DIRNAME, OUTPUT_DIRNAME):
        (project_path / dirname).mkdir(parents=True, exist_ok=True)
    return project_path


def default_project_output_path(path: str | Path, filename: str = "output.mp4") -> Path:
    project_path = ensure_project_structure(path)
    return project_path / OUTPUT_DIRNAME / filename


def _clean_preferred_name(source_path: Path, preferred_name: str | None = None) -> str:
    raw_name = preferred_name or source_path.name
    clean_name = _BROWSER_UPLOAD_PREFIX.sub("", Path(raw_name).name)
    if clean_name:
        return clean_name
    fallback_name = _BROWSER_UPLOAD_PREFIX.sub("", source_path.name)
    return fallback_name or "asset.bin"


def _unique_target_path(directory: Path, name: str) -> Path:
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem or "asset"
    suffix = candidate.suffix
    counter = 1
    while True:
        next_candidate = directory / f"{stem}_{counter}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        counter += 1


def _is_within_project(project_path: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(project_path.resolve())
    except ValueError:
        return False
    return True


def copy_path_to_project_subdir(
    project_path: str | Path,
    source_path: str,
    subdir: str,
    *,
    preferred_name: str | None = None,
) -> str:
    if not source_path:
        return source_path
    source = Path(source_path).expanduser()
    if not source.exists() or not source.is_file():
        return source_path

    project_root = ensure_project_structure(project_path)
    if _is_within_project(project_root, source):
        return str(source.resolve())

    target_dir = project_root / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = _unique_target_path(target_dir, _clean_preferred_name(source, preferred_name))
    shutil.copy2(source, target)
    return str(target.resolve())


def _project_to_disk_dict(project: Project, project_path: Path) -> dict[str, object]:
    payload = project_to_dict(project)

    def relativize(path_value: object) -> object:
        if path_value in {None, ""}:
            return path_value
        path_obj = Path(str(path_value)).expanduser()
        if not path_obj.is_absolute():
            return str(path_obj)
        try:
            return str(path_obj.resolve().relative_to(project_path.resolve()))
        except ValueError:
            return str(path_obj)

    payload["primary_video"]["path"] = relativize(payload["primary_video"].get("path"))
    secondary_video = payload.get("secondary_video")
    if isinstance(secondary_video, dict):
        secondary_video["path"] = relativize(secondary_video.get("path"))
    for source in payload.get("merge_sources", []):
        asset = source.get("asset")
        if isinstance(asset, dict):
            asset["path"] = relativize(asset.get("path"))
    scoring = payload.get("scoring", {})
    if isinstance(scoring, dict):
        scoring["practiscore_source_path"] = relativize(scoring.get("practiscore_source_path"))
        imported_stage = scoring.get("imported_stage")
        if isinstance(imported_stage, dict):
            imported_stage["source_path"] = relativize(imported_stage.get("source_path"))
    export = payload.get("export", {})
    if isinstance(export, dict):
        export["output_path"] = relativize(export.get("output_path"))
    return payload


def _resolve_saved_paths(project: Project, project_path: Path) -> None:
    def resolve(path_value: str) -> str:
        if not path_value:
            return path_value
        path_obj = Path(path_value).expanduser()
        if path_obj.is_absolute():
            return str(path_obj)
        return str((project_path / path_obj).resolve())

    project.primary_video.path = resolve(project.primary_video.path)
    if project.secondary_video is not None:
        project.secondary_video.path = resolve(project.secondary_video.path)
    for source in project.merge_sources:
        source.asset.path = resolve(source.asset.path)
    project.scoring.practiscore_source_path = resolve(project.scoring.practiscore_source_path)
    if project.scoring.imported_stage is not None:
        project.scoring.imported_stage.source_path = resolve(project.scoring.imported_stage.source_path)
    if project.export.output_path:
        project.export.output_path = resolve(project.export.output_path)


def _normalize_project_assets(project: Project, project_path: Path) -> None:
    project.primary_video.path = copy_path_to_project_subdir(project_path, project.primary_video.path, INPUT_DIRNAME)

    bundled_sources: list[MergeSource] = []
    for source in project.merge_sources:
        if source.asset.path:
            source.asset.path = copy_path_to_project_subdir(project_path, source.asset.path, INPUT_DIRNAME)
        bundled_sources.append(source)
    project.merge_sources = bundled_sources

    if project.secondary_video is not None and project.secondary_video.path:
        project.secondary_video.path = copy_path_to_project_subdir(project_path, project.secondary_video.path, INPUT_DIRNAME)
    if project.merge_sources:
        project.secondary_video = project.merge_sources[0].asset

    practiscore_source_path = project.scoring.practiscore_source_path
    practiscore_source_name = project.scoring.practiscore_source_name or None
    imported_stage = project.scoring.imported_stage
    if not practiscore_source_path and imported_stage is not None:
        practiscore_source_path = imported_stage.source_path
        practiscore_source_name = imported_stage.source_name or practiscore_source_name
    if practiscore_source_path:
        copied_practiscore_path = copy_path_to_project_subdir(
            project_path,
            practiscore_source_path,
            PRACTISCORE_DIRNAME,
            preferred_name=practiscore_source_name,
        )
        project.scoring.practiscore_source_path = copied_practiscore_path
        if imported_stage is not None:
            imported_stage.source_path = copied_practiscore_path

    if not project.export.output_path:
        project.export.output_path = str(default_project_output_path(project_path))


def save_project(project: Project, bundle_path: str | Path) -> Path:
    project_path = ensure_project_structure(bundle_path)
    _normalize_project_assets(project, project_path)
    metadata_path = project_metadata_path(project_path)
    metadata_path.write_text(json.dumps(_project_to_disk_dict(project, project_path), indent=2))
    return project_path


def load_project(bundle_path: str | Path) -> Project:
    project_path = ensure_project_structure(bundle_path)
    metadata_path = project_metadata_path(project_path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"No {PROJECT_FILENAME} found in {project_path}.")
    project = project_from_dict(json.loads(metadata_path.read_text()))
    _resolve_saved_paths(project, project_path)
    return project


def delete_project(bundle_path: str | Path) -> None:
    project_path = resolve_project_path(bundle_path)
    if project_path.exists():
        shutil.rmtree(project_path)
