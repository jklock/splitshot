from __future__ import annotations

import json
import shutil
from pathlib import Path

from splitshot.domain.models import MergeSource, Project, project_from_dict, project_to_dict

PROJECT_FILENAME = "project.json"
MEDIA_DIRNAME = "media"


def ensure_project_suffix(path: str | Path) -> Path:
    project_path = Path(path)
    if project_path.name == PROJECT_FILENAME:
        return project_path.parent
    if project_path.suffix != ".ssproj":
        project_path = project_path.with_suffix(".ssproj")
    return project_path


def _is_browser_session_media(path: Path) -> bool:
    return any(part.startswith("splitshot-browser-") for part in path.parts)


def _copy_project_media_if_needed(project: Project, project_path: Path) -> Project:
    cloned = project_from_dict(project_to_dict(project))
    media_dir = project_path / MEDIA_DIRNAME
    used_names: set[str] = set()

    def bundle_path(source_path: str, prefix: str) -> str:
        source = Path(source_path)
        if not source.exists() or not source.is_file() or not _is_browser_session_media(source):
            return source_path
        media_dir.mkdir(parents=True, exist_ok=True)
        stem = source.stem or prefix
        suffix = source.suffix or ".bin"
        candidate = f"{prefix}_{stem}{suffix}"
        counter = 1
        while candidate in used_names or (media_dir / candidate).exists():
            candidate = f"{prefix}_{stem}_{counter}{suffix}"
            counter += 1
        used_names.add(candidate)
        target = media_dir / candidate
        shutil.copy2(source, target)
        return str(target)

    if cloned.primary_video.path:
        cloned.primary_video.path = bundle_path(cloned.primary_video.path, "primary")

    bundled_sources: list[MergeSource] = []
    for index, source in enumerate(cloned.merge_sources, start=1):
        if source.asset.path:
            source.asset.path = bundle_path(source.asset.path, f"merge_{index}")
        bundled_sources.append(source)
    cloned.merge_sources = bundled_sources
    cloned.secondary_video = cloned.merge_sources[0].asset if cloned.merge_sources else None
    return cloned


def save_project(project: Project, bundle_path: str | Path) -> Path:
    project_path = ensure_project_suffix(bundle_path)
    project_path.mkdir(parents=True, exist_ok=True)
    persisted_project = _copy_project_media_if_needed(project, project_path)
    metadata_path = project_path / PROJECT_FILENAME
    metadata_path.write_text(json.dumps(project_to_dict(persisted_project), indent=2))
    return project_path


def load_project(bundle_path: str | Path) -> Project:
    project_path = ensure_project_suffix(bundle_path)
    metadata_path = project_path / PROJECT_FILENAME
    return project_from_dict(json.loads(metadata_path.read_text()))


def delete_project(bundle_path: str | Path) -> None:
    project_path = ensure_project_suffix(bundle_path)
    if project_path.exists():
        shutil.rmtree(project_path)
