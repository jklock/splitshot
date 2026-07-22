from __future__ import annotations

import filecmp
import json
import re
import shutil
from pathlib import Path
from uuid import uuid4

from splitshot.domain.models import Project, project_from_dict, project_to_dict

PROJECT_FILENAME = "project.json"
INPUT_DIRNAME = "Input"
PRACTISCORE_DIRNAME = "CSV"
OUTPUT_DIRNAME = "Output"
MARKERS_DIRNAME = "Markers"
POPUP_DIRNAME = MARKERS_DIRNAME
REQUIRED_PROJECT_DIRNAMES = (
    INPUT_DIRNAME,
    PRACTISCORE_DIRNAME,
    MARKERS_DIRNAME,
    OUTPUT_DIRNAME,
)

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


def missing_required_project_dirs(path: str | Path) -> list[str]:
    project_path = resolve_project_path(path)
    return [
        dirname for dirname in REQUIRED_PROJECT_DIRNAMES if not (project_path / dirname).is_dir()
    ]


def ensure_project_structure(path: str | Path) -> Path:
    project_path = resolve_project_path(path)
    project_path.mkdir(parents=True, exist_ok=True)
    for dirname in REQUIRED_PROJECT_DIRNAMES:
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


def _is_within_directory(directory: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(directory.resolve())
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
    target_dir = project_root / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    if _is_within_directory(target_dir, source):
        return str(source.resolve())

    preferred_target = target_dir / _clean_preferred_name(source, preferred_name)
    if preferred_target.is_file() and filecmp.cmp(source, preferred_target, shallow=False):
        return str(preferred_target.resolve())
    target = _unique_target_path(target_dir, preferred_target.name)
    partial = target.with_name(f".{target.name}.{uuid4().hex}.part")
    try:
        shutil.copy2(source, partial)
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return str(target.resolve())


def _project_to_disk_dict(project: Project, project_path: Path) -> dict[str, object]:
    payload = project_to_dict(project)

    def relativize(path_value: object) -> object:
        if path_value in {None, ""}:
            return path_value
        path_obj = Path(str(path_value)).expanduser()
        if not path_obj.is_absolute():
            return path_obj.as_posix()
        try:
            return path_obj.resolve().relative_to(project_path.resolve()).as_posix()
        except ValueError:
            return str(path_obj)

    def relativize_asset(asset: object) -> None:
        if isinstance(asset, dict):
            asset["path"] = relativize(asset.get("path"))

    def relativize_trim(trim: object) -> None:
        if not isinstance(trim, dict):
            return
        trim["original_path"] = relativize(trim.get("original_path"))
        trim["derivative_path"] = relativize(trim.get("derivative_path"))
        relativize_asset(trim.get("derivative_asset"))

    def relativize_scoring(scoring: object) -> None:
        if not isinstance(scoring, dict):
            return
        scoring["practiscore_source_path"] = relativize(scoring.get("practiscore_source_path"))
        imported_stage = scoring.get("imported_stage")
        if isinstance(imported_stage, dict):
            imported_stage["source_path"] = relativize(imported_stage.get("source_path"))

    def relativize_project_state(state: dict[str, object]) -> None:
        relativize_asset(state.get("primary_video") or state.get("primary_media"))
        relativize_trim(state.get("primary_trim_derivative"))
        relativize_asset(state.get("secondary_video"))
        for source in state.get("merge_sources", state.get("added_media", [])):
            if not isinstance(source, dict):
                continue
            relativize_asset(source.get("asset"))
            relativize_trim(source.get("trim_derivative"))
        relativize_scoring(state.get("scoring"))
        export = state.get("export")
        if isinstance(export, dict):
            export["output_path"] = relativize(export.get("output_path"))
        for popup in state.get("popups", []):
            if isinstance(popup, dict):
                popup["image_path"] = relativize(popup.get("image_path"))

    relativize_project_state(payload)
    for stage in payload.get("stages", []):
        if isinstance(stage, dict):
            relativize_project_state(stage)
    payload["practiscore_source_file"] = relativize(payload.get("practiscore_source_file"))
    return payload


def _resolve_saved_paths(project: Project, project_path: Path) -> None:
    def resolve(path_value: str) -> str:
        if not path_value:
            return path_value
        path_obj = Path(path_value).expanduser()
        if path_obj.is_absolute():
            return str(path_obj)
        return str((project_path / path_obj).resolve())

    def resolve_asset(asset: object) -> None:
        if asset is not None and hasattr(asset, "path"):
            asset.path = resolve(asset.path)

    def resolve_trim(trim: object) -> None:
        if trim is None:
            return
        trim.original_path = resolve(trim.original_path)
        if trim.derivative_path:
            trim.derivative_path = resolve(trim.derivative_path)
        resolve_asset(trim.derivative_asset)

    def resolve_scoring(scoring: object) -> None:
        scoring.practiscore_source_path = resolve(scoring.practiscore_source_path)
        if scoring.imported_stage is not None:
            scoring.imported_stage.source_path = resolve(scoring.imported_stage.source_path)

    def resolve_project_state(state: object) -> None:
        primary = getattr(state, "primary_video", None) or getattr(state, "primary_media", None)
        resolve_asset(primary)
        resolve_trim(getattr(state, "primary_trim_derivative", None))
        resolve_asset(getattr(state, "secondary_video", None))
        sources = getattr(state, "merge_sources", None)
        if sources is None:
            sources = getattr(state, "added_media", [])
        for source in sources:
            resolve_asset(source.asset)
            resolve_trim(source.trim_derivative)
        resolve_scoring(state.scoring)
        if state.export.output_path:
            state.export.output_path = resolve(state.export.output_path)
        for popup in state.popups:
            if popup.image_path:
                popup.image_path = resolve(popup.image_path)

    resolve_project_state(project)
    for stage in project.stages:
        resolve_project_state(stage)
    project.practiscore_source_file = resolve(project.practiscore_source_file)


def save_project(project: Project, bundle_path: str | Path) -> Path:
    project_path = ensure_project_structure(bundle_path)
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
    metadata_path = project_metadata_path(bundle_path)
    if metadata_path.exists():
        metadata_path.unlink()
