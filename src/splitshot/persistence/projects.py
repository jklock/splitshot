from __future__ import annotations

import json
import shutil
from pathlib import Path

from splitshot.domain.models import Project, project_from_dict, project_to_dict

PROJECT_FILENAME = "project.json"


def ensure_project_suffix(path: str | Path) -> Path:
    project_path = Path(path)
    if project_path.suffix != ".ssproj":
        project_path = project_path.with_suffix(".ssproj")
    return project_path


def save_project(project: Project, bundle_path: str | Path) -> Path:
    project_path = ensure_project_suffix(bundle_path)
    project_path.mkdir(parents=True, exist_ok=True)
    metadata_path = project_path / PROJECT_FILENAME
    metadata_path.write_text(json.dumps(project_to_dict(project), indent=2))
    return project_path


def load_project(bundle_path: str | Path) -> Project:
    project_path = ensure_project_suffix(bundle_path)
    metadata_path = project_path / PROJECT_FILENAME
    return project_from_dict(json.loads(metadata_path.read_text()))


def delete_project(bundle_path: str | Path) -> None:
    project_path = ensure_project_suffix(bundle_path)
    if project_path.exists():
        shutil.rmtree(project_path)
