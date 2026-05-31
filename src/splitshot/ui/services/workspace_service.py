"""Workspace lifecycle and inheritance helpers extracted from the UI controller."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from splitshot.domain.models import MatchWorkspace, StageEntry
from splitshot.persistence.projects import normalize_project_path
from splitshot.persistence.workspaces import (
    load_workspace as load_workspace_bundle,
    normalize_workspace_path,
    save_workspace as save_workspace_bundle,
    workspace_has_metadata,
    workspace_stage_project_path,
)

if TYPE_CHECKING:
    from splitshot.ui.controller import ProjectController


def _utc_now():
    return datetime.now(timezone.utc)


def _workspace_to_dict_safe(workspace) -> dict | None:
    if workspace is None:
        return None
    try:
        from splitshot.persistence.workspaces import _workspace_to_dict

        return _workspace_to_dict(workspace)
    except Exception:
        return None


def seed_workspace_defaults(
    controller: ProjectController,
    workspace: MatchWorkspace,
    inheritance_eligible_fields: set[str] | frozenset[str],
) -> None:
    effective = controller.effective_settings()
    for field in inheritance_eligible_fields:
        if hasattr(effective, field):
            value = getattr(effective, field)
            if value is not None:
                workspace.shared_defaults[field] = value


def workspace_stage_entry(controller: ProjectController, stage_id: str) -> StageEntry | None:
    if controller.workspace is None:
        return None
    return controller.workspace.stage_entries.get(stage_id)


def workspace_stage_project_file(
    controller: ProjectController,
    stage_id: str,
    *,
    workspace_path: str | Path | None = None,
    entry: StageEntry | None = None,
) -> Path | None:
    stage_entry = entry or controller._workspace_stage_entry(stage_id)
    workspace_root = None
    if workspace_path is not None:
        workspace_root = normalize_workspace_path(workspace_path)
    elif controller.workspace_path is not None:
        workspace_root = normalize_workspace_path(controller.workspace_path)

    canonical_path = None
    if workspace_root is not None:
        canonical_path = workspace_stage_project_path(workspace_root, stage_id)
        if canonical_path.is_file():
            return canonical_path
        if stage_entry and stage_entry.relative_project_path:
            candidate = (workspace_root / stage_entry.relative_project_path).resolve(strict=False)
            if candidate.is_dir() or candidate.name != "project.json":
                candidate = candidate / "project.json"
            if candidate.is_file():
                return candidate

    if stage_entry and stage_entry.relative_project_path:
        candidate = Path(stage_entry.relative_project_path).expanduser().resolve(strict=False)
        if candidate.is_dir() or candidate.name != "project.json":
            candidate = candidate / "project.json"
        if candidate.is_file():
            return candidate

    return canonical_path


def find_workspace_stage_for_project_path(
    controller: ProjectController,
    project_path: str | Path,
    *,
    workspace: MatchWorkspace | None = None,
    workspace_path: str | Path | None = None,
) -> str | None:
    active_workspace = workspace or controller.workspace
    if active_workspace is None:
        return None
    normalized_project_path = normalize_project_path(project_path)
    for stage_id, entry in active_workspace.stage_entries.items():
        candidate = controller._workspace_stage_project_file(
            stage_id,
            workspace_path=workspace_path,
            entry=entry,
        )
        if candidate is None:
            continue
        if normalize_project_path(candidate) == normalized_project_path:
            return stage_id
    return None


def ensure_project_workspace_membership(
    controller: ProjectController,
    project_path: str | Path,
    inheritance_eligible_fields: set[str] | frozenset[str],
) -> str | None:
    normalized_project_path = normalize_project_path(project_path)
    owner_workspace = None
    owner_workspace_path: Path | None = None
    stage_id = controller._find_workspace_stage_for_project_path(normalized_project_path)

    if stage_id is not None and controller.workspace is not None:
        owner_workspace = controller.workspace
        if controller.workspace_path is not None:
            owner_workspace_path = normalize_workspace_path(controller.workspace_path)

    if owner_workspace is None:
        for candidate in [normalized_project_path, *normalized_project_path.parents]:
            if not workspace_has_metadata(candidate):
                continue
            owner_workspace_path = normalize_workspace_path(candidate)
            owner_workspace = load_workspace_bundle(owner_workspace_path)
            stage_id = controller._find_workspace_stage_for_project_path(
                normalized_project_path,
                workspace=owner_workspace,
                workspace_path=owner_workspace_path,
            )
            if stage_id is None:
                relative_project_path = normalized_project_path.relative_to(owner_workspace_path)
                if len(relative_project_path.parts) >= 2 and relative_project_path.parts[0] == "Stages":
                    stage_id = relative_project_path.parts[1]
            break

    if owner_workspace is None:
        if controller.workspace is not None and controller.workspace_path is None:
            owner_workspace = controller.workspace
        elif controller.workspace is not None and controller.workspace_path is not None:
            return None
        else:
            owner_workspace = MatchWorkspace()
            owner_workspace.name = (
                f"{(controller.project.name or normalized_project_path.name).strip()} Match"
            )
            seed_workspace_defaults(controller, owner_workspace, inheritance_eligible_fields)

    resolved_stage_id = stage_id or controller.project.id or normalized_project_path.name
    entry = owner_workspace.stage_entries.get(resolved_stage_id)
    if entry is None:
        entry = StageEntry(stage_id=resolved_stage_id)
        owner_workspace.stage_entries[resolved_stage_id] = entry
    if resolved_stage_id not in owner_workspace.stage_order:
        owner_workspace.stage_order.append(resolved_stage_id)
    if entry.stage_number is None:
        entry.stage_number = owner_workspace.stage_order.index(resolved_stage_id) + 1

    entry.display_name = controller.project.name or entry.display_name or normalized_project_path.name
    if owner_workspace_path is not None:
        try:
            entry.relative_project_path = str(normalized_project_path.relative_to(owner_workspace_path))
        except ValueError:
            entry.relative_project_path = str(normalized_project_path)
    else:
        entry.relative_project_path = str(normalized_project_path)
    entry.source_media_present = bool(str(controller.project.primary_video.path or "").strip())
    if not entry.override_values:
        entry.status = "complete" if entry.source_media_present else "incomplete"

    owner_workspace.updated_at = _utc_now()
    controller.workspace = owner_workspace
    controller.workspace_path = owner_workspace_path
    controller.active_stage_id = resolved_stage_id
    controller._return_to_workspace_available = owner_workspace_path is not None

    if owner_workspace_path is not None:
        controller._load_workspace_stage_profiles()
        save_workspace_bundle(owner_workspace, owner_workspace_path)

    controller._workspace_saved_snapshot = controller._workspace_persistence_snapshot()
    return resolved_stage_id


def workspace_persistence_snapshot(controller: ProjectController) -> dict | None:
    if controller.workspace is None:
        return None
    workspace_snapshot = _workspace_to_dict_safe(controller.workspace)
    if workspace_snapshot is None:
        return None
    stage_profiles = {}
    for output_id, profile in controller._output_profiles.items():
        if profile.scope_type == "stage" and profile.scope_id in controller.workspace.stage_entries:
            stage_profiles[output_id] = controller._output_profile_to_dict_safe(profile)
    return {
        "workspace": workspace_snapshot,
        "stage_profiles": stage_profiles,
    }


def persist_workspace_stage_profiles(controller: ProjectController) -> None:
    if controller.workspace is None:
        return
    for stage_id in controller.workspace.stage_entries:
        bundle_path = controller._workspace_stage_bundle_path(stage_id)
        if bundle_path is None:
            continue
        controller._save_stage_profiles(bundle_path, stage_id=stage_id)


def load_workspace_stage_profiles(controller: ProjectController) -> None:
    if controller.workspace is None:
        return
    controller._output_profiles = {
        output_id: profile
        for output_id, profile in controller._output_profiles.items()
        if not (
            profile.scope_type == "stage" and profile.scope_id in controller.workspace.stage_entries
        )
    }
    for stage_id in controller.workspace.stage_entries:
        bundle_path = controller._workspace_stage_bundle_path(stage_id)
        if bundle_path is not None:
            controller._load_stage_profiles(bundle_path)


def new_workspace(
    controller: ProjectController,
    inheritance_eligible_fields: set[str] | frozenset[str],
) -> None:
    controller.workspace = MatchWorkspace()
    controller.workspace_path = None
    controller.editor_scope = "multi"
    controller.active_stage_id = None
    controller._return_to_workspace_available = False

    seed_workspace_defaults(controller, controller.workspace, inheritance_eligible_fields)

    controller._workspace_saved_snapshot = controller._workspace_persistence_snapshot()
    controller._set_status("New match workspace created.")
    controller.project_changed.emit()


def save_workspace(controller: ProjectController, path: str | None = None) -> None:
    if controller.workspace is None:
        return
    save_path = Path(path) if path else controller.workspace_path
    if save_path is None:
        return
    controller.workspace_path = save_workspace_bundle(controller.workspace, save_path)
    controller._persist_workspace_stage_profiles()
    controller._workspace_saved_snapshot = controller._workspace_persistence_snapshot()
    controller._sync_workspace_to_library()
    controller._set_status(f"Workspace saved to {controller.workspace_path}")


def open_workspace(controller: ProjectController, path: str) -> None:
    ws_path = Path(path)
    if not workspace_has_metadata(ws_path):
        controller._set_status(f"No workspace found at {path}")
        return
    controller.workspace = load_workspace_bundle(ws_path)
    controller.workspace_path = ws_path
    controller.editor_scope = "multi"
    controller.active_stage_id = None
    controller._return_to_workspace_available = False
    controller._load_workspace_stage_profiles()
    controller._workspace_saved_snapshot = controller._workspace_persistence_snapshot()
    controller._set_status(f"Opened workspace: {controller.workspace.name}")


def workspace_add_stage(
    controller: ProjectController,
    stage_id: str,
    display_name: str = "",
    project_path: str = "",
) -> None:
    if controller.workspace is None:
        return
    entry = StageEntry(
        stage_id=stage_id,
        display_name=display_name or f"Stage {len(controller.workspace.stage_entries) + 1}",
        relative_project_path=project_path,
    )
    controller.workspace.stage_entries[stage_id] = entry
    if stage_id not in controller.workspace.stage_order:
        controller.workspace.stage_order.append(stage_id)
    controller.workspace.updated_at = _utc_now()
    controller._set_status(f"Added stage {stage_id} to workspace.")
    controller.project_changed.emit()


def workspace_remove_stage(controller: ProjectController, stage_id: str) -> None:
    if controller.workspace is None:
        return
    controller.workspace.stage_entries.pop(stage_id, None)
    if stage_id in controller.workspace.stage_order:
        controller.workspace.stage_order.remove(stage_id)
    controller.workspace.updated_at = _utc_now()
    controller._set_status(f"Removed stage {stage_id} from workspace.")
    controller.project_changed.emit()


def workspace_open_stage(controller: ProjectController, stage_id: str) -> dict | None:
    if controller.workspace is None:
        return {"match_id": None, "stage_id": stage_id, "reason": "No workspace is open"}
    if stage_id not in controller.workspace.stage_entries:
        return {
            "match_id": controller.workspace.match_id,
            "stage_id": stage_id,
            "reason": "Stage not found in workspace",
        }
    if controller.workspace_path is not None:
        controller.save_workspace()
    if controller.workspace_path is not None:
        stage_project = controller._workspace_stage_project_file(stage_id)
        if stage_project is not None and stage_project.exists():
            controller.open_project(str(stage_project.parent))
            controller._load_stage_profiles(Path(controller.project_path))
    controller.active_stage_id = stage_id
    controller.editor_scope = "multi"
    controller._return_to_workspace_available = True
    controller._set_status(f"Editing stage: {controller.workspace.stage_entries[stage_id].display_name}")
    return None


def workspace_return_to_workspace(controller: ProjectController) -> None:
    previous_stage_id = controller.active_stage_id
    controller.active_stage_id = None
    controller._return_to_workspace_available = False
    if controller.workspace_path is not None and workspace_has_metadata(controller.workspace_path):
        controller.workspace = load_workspace_bundle(controller.workspace_path)
    controller._last_returned_stage_id = previous_stage_id
    controller._set_status(
        f"Returned to workspace: {controller.workspace.name if controller.workspace else 'Unknown'}"
    )


def workspace_set_defaults(
    controller: ProjectController,
    payload: dict,
    inheritance_eligible_fields: set[str] | frozenset[str],
) -> None:
    if controller.workspace is None:
        return
    filtered = {k: v for k, v in payload.items() if k in inheritance_eligible_fields}
    controller.workspace.shared_defaults.update(filtered)
    controller.workspace.updated_at = _utc_now()
    controller._set_status("Updated workspace shared defaults.")
    controller.project_changed.emit()


def workspace_set_stage_override(
    controller: ProjectController,
    stage_id: str,
    payload: dict,
    inheritance_eligible_fields: set[str] | frozenset[str],
) -> None:
    if controller.workspace is None or stage_id not in controller.workspace.stage_entries:
        return
    filtered = {k: v for k, v in payload.items() if k in inheritance_eligible_fields}
    if not filtered:
        return
    entry = controller.workspace.stage_entries[stage_id]
    entry.override_values.update(filtered)
    entry.status = "overridden"
    controller.workspace.updated_at = _utc_now()
    controller._set_status(f"Set override for stage {stage_id}.")
    controller.project_changed.emit()


def workspace_reset_stage_override(
    controller: ProjectController,
    stage_id: str,
    keys: list[str] | None = None,
) -> None:
    if controller.workspace is None or stage_id not in controller.workspace.stage_entries:
        return
    entry = controller.workspace.stage_entries[stage_id]
    if keys is None:
        entry.override_values.clear()
    else:
        for key in keys:
            entry.override_values.pop(key, None)
    if not entry.override_values:
        entry.status = "complete" if entry.source_media_present else "incomplete"
    controller.workspace.updated_at = _utc_now()
    controller._set_status(f"Reset overrides for stage {stage_id}.")
    controller.project_changed.emit()


def workspace_reset_defaults(controller: ProjectController) -> dict[str, object]:
    if not controller.workspace:
        return {"error": "No workspace open"}
    controller.workspace.shared_defaults.clear()
    controller.workspace.updated_at = _utc_now()
    controller.autosave_project_if_needed()
    controller.project_changed.emit()
    return {"reset": True}
