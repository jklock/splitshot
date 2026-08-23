"""Safe repair helpers for persisted SplitShot projects."""

from __future__ import annotations

import json
import os
import shutil
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RECOVERED_FIELDS = ("primary_media", "primary_trim_derivative", "added_media", "analysis")


def _media_paths(stage: dict[str, Any], project_root: Path | None) -> list[Path]:
    paths: list[Path] = []
    primary_path = str(stage.get("primary_media", {}).get("path", "") or "")
    if primary_path:
        paths.append(Path(primary_path))
    for source in stage.get("added_media", []):
        source_path = str(source.get("asset", {}).get("path", "") or "")
        if source_path:
            paths.append(Path(source_path))
    if project_root is None:
        return paths
    return [path if path.is_absolute() else project_root / path for path in paths]


def _sanitize_missing_derivative(stage: dict[str, Any], project_root: Path | None) -> None:
    trim = stage.get("primary_trim_derivative")
    if not isinstance(trim, dict):
        return
    derivative_path = str(trim.get("derivative_path", "") or "")
    resolved = Path(derivative_path)
    if project_root is not None and not resolved.is_absolute():
        resolved = project_root / resolved
    if derivative_path and not resolved.is_file():
        trim["derivative_path"] = None
        trim["derivative_asset"] = {}
        trim["active_path_kind"] = "original"


def recover_project_payload(
    payload: dict[str, Any], *, project_root: Path | None = None
) -> tuple[dict[str, Any], list[str]]:
    """Return a repaired copy and labels of stages recovered from same-id snapshots."""
    repaired = deepcopy(payload)
    queue_by_stage = {
        str(entry.get("stage_id", "")): entry
        for entry in repaired.get("queue", [])
        if isinstance(entry, dict) and isinstance(entry.get("snapshot"), dict)
    }
    recovered_labels: list[str] = []
    for stage in repaired.get("stages", []):
        if not isinstance(stage, dict):
            continue
        if str(stage.get("primary_media", {}).get("path", "") or ""):
            continue
        entry = queue_by_stage.get(str(stage.get("id", "")))
        snapshot = entry.get("snapshot") if entry else None
        if not isinstance(snapshot, dict):
            continue
        if not str(snapshot.get("primary_media", {}).get("path", "") or ""):
            continue
        recovered = deepcopy(snapshot)
        _sanitize_missing_derivative(recovered, project_root)
        missing = [path for path in _media_paths(recovered, project_root) if not path.is_file()]
        if missing:
            rendered = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(f"Cannot recover {stage.get('label', stage.get('id'))}: {rendered}")
        for field in RECOVERED_FIELDS:
            stage[field] = deepcopy(recovered.get(field))
        stage["queue_status"] = "stale"
        entry["status"] = "stale"
        entry["snapshot"] = deepcopy(stage)
        entry["processed_at"] = ""
        entry["output_path"] = ""
        entry["error_message"] = ""
        recovered_labels.append(str(stage.get("label") or stage.get("id") or "stage"))

    active_stage_id = str(repaired.get("active_stage_id", ""))
    active = next(
        (
            stage
            for stage in repaired.get("stages", [])
            if isinstance(stage, dict) and str(stage.get("id", "")) == active_stage_id
        ),
        None,
    )
    if isinstance(active, dict) and active_stage_id in queue_by_stage and active.get("primary_media"):
        repaired["primary_video"] = deepcopy(active["primary_media"])
        repaired["primary_trim_derivative"] = deepcopy(active["primary_trim_derivative"])
        repaired["merge_sources"] = deepcopy(active["added_media"])
        repaired["analysis"] = deepcopy(active["analysis"])
    return repaired, recovered_labels


def apply_stage_queue_recovery(project_file: Path) -> tuple[Path | None, list[str]]:
    """Back up and atomically repair a project.json file."""
    payload = json.loads(project_file.read_text(encoding="utf-8"))
    repaired, labels = recover_project_payload(payload, project_root=project_file.parent)
    if not labels:
        return None, []
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup = project_file.with_name(f"project.pre-stage-state-recovery-{timestamp}.json")
    shutil.copy2(project_file, backup)
    temporary = project_file.with_name(f".{project_file.name}.recovery-{os.getpid()}.tmp")
    temporary.write_text(json.dumps(repaired, indent=2) + "\n", encoding="utf-8")
    temporary.replace(project_file)
    return backup, labels
