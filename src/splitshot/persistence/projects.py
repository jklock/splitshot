from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from splitshot.domain.models import (
    Project,
    VideoAsset,
    _video_from_dict,
    ensure_merge_source_composition_truth,
    project_from_dict,
    project_to_dict,
)

PROJECT_FILENAME = "project.json"
INPUT_DIRNAME = "Input"
PRACTISCORE_DIRNAME = "CSV"
OUTPUT_DIRNAME = "Output"
POPUP_DIRNAME = "Markers"
REQUIRED_PROJECT_DIRNAMES = (INPUT_DIRNAME, PRACTISCORE_DIRNAME, OUTPUT_DIRNAME)

_BROWSER_UPLOAD_PREFIX = re.compile(r"^[A-Fa-f0-9]{32}_")
_BROWSER_SESSION_DIR_PREFIX = "splitshot-browser-"
UTC = timezone.utc


def _projects_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root).expanduser()
    env_root = os.environ.get("SPLITSHOT_PROJECTS_ROOT")
    if env_root:
        return Path(env_root).expanduser()
    return Path.home() / ".splitshot" / "projects"


def _parse_activity_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        try:
            parsed = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _recent_project_timestamp(metadata: dict[str, object], fallback_timestamp: float) -> tuple[float, str]:
    for key in ("last_opened", "updated_at", "modified_at", "created_at"):
        parsed = _parse_activity_datetime(metadata.get(key))
        if parsed is not None:
            return parsed.timestamp(), parsed.isoformat()
    if fallback_timestamp > 0:
        fallback = datetime.fromtimestamp(fallback_timestamp, UTC)
        return fallback.timestamp(), fallback.isoformat()
    return 0.0, ""


def _recent_project_entry(project_path: Path) -> dict[str, object] | None:
    metadata_path = project_metadata_path(project_path)
    if not metadata_path.is_file():
        return None
    try:
        metadata = json.loads(metadata_path.read_text())
    except Exception:
        return None
    if not isinstance(metadata, dict):
        return None
    try:
        fallback_timestamp = project_path.stat().st_mtime
    except OSError:
        fallback_timestamp = 0.0
    timestamp, date_value = _recent_project_timestamp(metadata, fallback_timestamp)
    normalized_path = str(resolve_project_path(project_path).resolve(strict=False))
    return {
        "name": str(metadata.get("name") or project_path.name),
        "path": normalized_path,
        "date": date_value,
        "last_opened": date_value,
        "project_id": str(metadata.get("id") or ""),
        "description": str(metadata.get("description") or ""),
        "updated_at": str(metadata.get("updated_at") or ""),
        "type": "stage",
        "surface": "single",
        "timestamp": timestamp,
    }


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


def _resolve_saved_path_value(path_value: str, project_path: Path) -> str:
    if not path_value:
        return path_value
    path_obj = Path(path_value).expanduser()
    if path_obj.is_absolute():
        return str(path_obj)
    return str((project_path / path_obj).resolve())


def _merge_source_id_for_video_asset(project: Project, asset: VideoAsset | None) -> str | None:
    if asset is None:
        return None
    asset_path = str(asset.path or "").strip()
    for source in project.merge_sources:
        if source.asset is asset:
            return source.id
        if asset_path and str(source.asset.path or "").strip() == asset_path:
            return source.id
    return None


def _restore_explicit_secondary_video(
    project: Project,
    secondary_video: VideoAsset | None,
    *,
    source_id: str | None = None,
) -> None:
    if secondary_video is None:
        project.secondary_video = None
        return

    if source_id:
        for source in project.merge_sources:
            if source.id == source_id:
                project.secondary_video = source.asset
                return

    secondary_path = str(secondary_video.path or "").strip()
    if secondary_path:
        for source in project.merge_sources:
            if str(source.asset.path or "").strip() == secondary_path:
                project.secondary_video = source.asset
                return

    project.secondary_video = secondary_video


def _explicit_secondary_video_from_payload(
    payload: object,
    project_path: Path,
) -> VideoAsset | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        return None
    secondary_video = _video_from_dict(payload)
    secondary_video.path = _resolve_saved_path_value(secondary_video.path, project_path)
    return secondary_video


def _is_browser_upload_compatibility_path(project_path: Path, source_path: str) -> bool:
    if not source_path:
        return False
    source = Path(source_path).expanduser()
    if not source.is_absolute() or not source.exists() or not source.is_file():
        return False
    if _is_within_project(project_path, source):
        return False
    return source.parent.name.startswith(_BROWSER_SESSION_DIR_PREFIX) and bool(
        _BROWSER_UPLOAD_PREFIX.match(source.name)
    )


def _bundle_browser_upload_compatibility_media(project: Project, project_path: Path) -> None:
    def bundle_if_needed(path_value: str) -> str:
        if not _is_browser_upload_compatibility_path(project_path, path_value):
            return path_value
        return copy_path_to_project_subdir(project_path, path_value, INPUT_DIRNAME)

    if project.primary_video.path:
        project.primary_video.path = bundle_if_needed(project.primary_video.path)

    if project.secondary_video is not None and project.secondary_video.path and not project.merge_sources:
        project.secondary_video.path = bundle_if_needed(project.secondary_video.path)

    for source in project.merge_sources:
        if source.asset.path:
            source.asset.path = bundle_if_needed(source.asset.path)


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
        trim_derivative = source.get("trim_derivative")
        if isinstance(trim_derivative, dict):
            trim_derivative["original_path"] = relativize(trim_derivative.get("original_path"))
            trim_derivative["derivative_path"] = relativize(
                trim_derivative.get("derivative_path")
            )
    scoring = payload.get("scoring", {})
    if isinstance(scoring, dict):
        scoring["practiscore_source_path"] = relativize(scoring.get("practiscore_source_path"))
        imported_stage = scoring.get("imported_stage")
        if isinstance(imported_stage, dict):
            imported_stage["source_path"] = relativize(imported_stage.get("source_path"))
    export = payload.get("export", {})
    if isinstance(export, dict):
        export["output_path"] = relativize(export.get("output_path"))
    for popup in payload.get("popups", []):
        if isinstance(popup, dict):
            popup["image_path"] = relativize(popup.get("image_path"))
    return payload


def _resolve_saved_paths(project: Project, project_path: Path) -> None:
    def resolve(path_value: str) -> str:
        return _resolve_saved_path_value(path_value, project_path)

    project.primary_video.path = resolve(project.primary_video.path)
    if project.secondary_video is not None:
        project.secondary_video.path = resolve(project.secondary_video.path)
    for source in project.merge_sources:
        source.asset.path = resolve(source.asset.path)
        if source.trim_derivative.original_path:
            source.trim_derivative.original_path = resolve(source.trim_derivative.original_path)
        if source.trim_derivative.derivative_path:
            source.trim_derivative.derivative_path = resolve(source.trim_derivative.derivative_path)
    project.scoring.practiscore_source_path = resolve(project.scoring.practiscore_source_path)
    if project.scoring.imported_stage is not None:
        project.scoring.imported_stage.source_path = resolve(
            project.scoring.imported_stage.source_path
        )
    if project.export.output_path:
        project.export.output_path = resolve(project.export.output_path)
    for popup in project.popups:
        if popup.image_path:
            popup.image_path = resolve(popup.image_path)


def _normalize_project_assets(project: Project, project_path: Path) -> None:
    _bundle_browser_upload_compatibility_media(project, project_path)

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
    for popup in project.popups:
        if popup.image_path:
            popup.image_path = copy_path_to_project_subdir(
                project_path,
                popup.image_path,
                POPUP_DIRNAME,
            )


def save_project(project: Project, bundle_path: str | Path) -> Path:
    project_path = ensure_project_structure(bundle_path)
    ensure_merge_source_composition_truth(project)
    _normalize_project_assets(project, project_path)
    metadata_path = project_metadata_path(project_path)
    metadata_path.write_text(json.dumps(_project_to_disk_dict(project, project_path), indent=2))
    return project_path


def load_project(bundle_path: str | Path) -> Project:
    project_path = ensure_project_structure(bundle_path)
    metadata_path = project_metadata_path(project_path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"No {PROJECT_FILENAME} found in {project_path}.")
    raw_payload = json.loads(metadata_path.read_text())
    project = project_from_dict(raw_payload)
    _resolve_saved_paths(project, project_path)
    return project


def list_recent_projects(limit: int = 10, root: str | Path | None = None) -> list[dict]:
    """List recently opened projects from the splitshot datadir."""
    return list_recent_project_activity(limit=limit, root=root)


def list_recent_project_activity(
    limit: int = 10,
    root: str | Path | None = None,
) -> list[dict[str, object]]:
    """Return normalized recent Stage project entries for landing/shared backend support."""
    datadir = _projects_root(root)
    if not datadir.is_dir():
        return []

    recent_entries: list[dict[str, object]] = []
    for entry in datadir.iterdir():
        if not entry.is_dir():
            continue
        recent_entry = _recent_project_entry(entry)
        if recent_entry is not None:
            recent_entries.append(recent_entry)

    recent_entries.sort(
        key=lambda item: (
            float(item.get("timestamp") or 0.0),
            str(item.get("path") or ""),
        ),
        reverse=True,
    )
    return recent_entries[: max(0, int(limit))]


def delete_project(bundle_path: str | Path) -> None:
    metadata_path = project_metadata_path(bundle_path)
    if metadata_path.exists():
        metadata_path.unlink()
