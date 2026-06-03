from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from splitshot.domain.models import (
    AngleDirectorCutDecision,
    MatchWorkspace,
    OutputProfile,
    StageClipSource,
    StageEntry,
    _camera_role_payload_value,
    _promote_camera_role_key,
    _serialize,
)

WORKSPACE_FILENAME = "workspace.json"
STAGES_DIRNAME = "Stages"
MATCH_OUTPUT_DIRNAME = "Output/Match"

UTC = timezone.utc


def resolve_workspace_path(path: str | Path) -> Path:
    workspace_path = Path(path)
    if workspace_path.name == WORKSPACE_FILENAME:
        return workspace_path.parent
    return workspace_path


def normalize_workspace_path(path: str | Path) -> Path:
    return resolve_workspace_path(path).expanduser().resolve(strict=False)


def workspace_metadata_path(path: str | Path) -> Path:
    return resolve_workspace_path(path) / WORKSPACE_FILENAME


def workspace_has_metadata(path: str | Path) -> bool:
    return workspace_metadata_path(path).is_file()


def ensure_workspace_structure(path: str | Path) -> Path:
    workspace_path = resolve_workspace_path(path)
    workspace_path.mkdir(parents=True, exist_ok=True)
    return workspace_path


def ensure_workspace_stage_path(workspace_path: str | Path, stage_id: str) -> Path:
    stage_dir = resolve_workspace_path(workspace_path) / STAGES_DIRNAME / stage_id
    stage_dir.mkdir(parents=True, exist_ok=True)
    return stage_dir


def default_workspace_match_output_path(path: str | Path) -> Path:
    workspace_path = resolve_workspace_path(path)
    return workspace_path / MATCH_OUTPUT_DIRNAME


def workspace_stage_project_path(workspace_path: str | Path, stage_id: str) -> Path:
    return resolve_workspace_path(workspace_path) / STAGES_DIRNAME / stage_id / "project.json"


def workspace_stage_path(workspace_path: str | Path, stage_id: str) -> Path:
    return resolve_workspace_path(workspace_path) / STAGES_DIRNAME / stage_id


def _workspace_to_dict(workspace: MatchWorkspace) -> dict:
    data = _promote_camera_role_key(_serialize(workspace))
    data["match_output_profiles"] = [
        _output_profile_to_dict(p) for p in workspace.match_output_profiles
    ]
    return data


def _stage_entry_to_dict(entry: StageEntry) -> dict:
    return _promote_camera_role_key(_serialize(entry))


def _output_profile_to_dict(profile: OutputProfile) -> dict:
    """Serialize an OutputProfile to a plain dict."""
    return _promote_camera_role_key(
        {
            "output_id": profile.output_id,
            "scope_type": profile.scope_type,
            "scope_id": profile.scope_id,
            "profile_name": profile.profile_name,
            "profile_kind": profile.profile_kind,
            "frame_profile": profile.frame_profile,
            "metric_caption_preset": profile.metric_caption_preset,
            "lead_in_card": profile.lead_in_card,
            "brand_mark": profile.brand_mark,
            "subject_track_crop": profile.subject_track_crop,
            "visibility_recipe": profile.visibility_recipe,
            "angle_director_plan": [_serialize(item) for item in profile.angle_director_plan],
            "retained_proxy_id": profile.retained_proxy_id,
            "last_rendered_at": profile.last_rendered_at.isoformat()
            if profile.last_rendered_at
            else None,
        }
    )


def _stage_entry_from_dict(data: dict) -> StageEntry:
    last_reviewed_at = data.get("last_reviewed_at")
    stage_number = data.get("stage_number")
    raw_clip_sources = data.get("clip_sources")
    clip_sources: list[StageClipSource] = []
    if isinstance(raw_clip_sources, list):
        for item in raw_clip_sources:
            if isinstance(item, dict):
                clip_sources.append(
                    StageClipSource(
                        clip_id=str(item.get("clip_id", "")),
                        source_path=str(item.get("source_path", "")),
                        angle_role=str(_camera_role_payload_value(item, "primary") or "primary"),
                        sync_offset_ms=int(item.get("sync_offset_ms", 0)),
                        audio_gain=float(item.get("audio_gain", 1.0)),
                        audio_muted=bool(item.get("audio_muted", False)),
                        audio_primary=bool(item.get("audio_primary", False)),
                        angle_aligned=bool(item.get("angle_aligned", False)),
                    )
                )
    return StageEntry(
        stage_id=str(data.get("stage_id", "")),
        relative_project_path=str(data.get("relative_project_path", "")),
        display_name=str(data.get("display_name", "")),
        stage_number=None if stage_number in {None, ""} else int(stage_number),
        status=str(data.get("status", "incomplete")),
        override_values=(
            data.get("override_values", {}) if isinstance(data.get("override_values"), dict) else {}
        ),
        last_reviewed_at=(
            None
            if last_reviewed_at in {None, ""}
            else datetime.fromisoformat(str(last_reviewed_at))
        ),
        source_media_present=bool(data.get("source_media_present", False)),
        clip_sources=clip_sources,
        inherited_from_first=bool(data.get("inherited_from_first", False)),
    )


def _output_profile_from_dict(data: dict) -> OutputProfile:
    last_rendered_at = data.get("last_rendered_at")
    retained_proxy_id = data.get("retained_proxy_id")
    raw_angle_director_plan = data.get("angle_director_plan")
    angle_director_plan: list[AngleDirectorCutDecision] = []
    if isinstance(raw_angle_director_plan, list):
        for item in raw_angle_director_plan:
            if isinstance(item, dict):
                angle_director_plan.append(
                    AngleDirectorCutDecision(
                        position=int(item.get("position", 0)),
                        clip_id=str(item.get("clip_id", "")),
                        angle_role=str(_camera_role_payload_value(item, "") or ""),
                        start_ms=int(item.get("start_ms", 0)),
                        duration_ms=int(item.get("duration_ms", 0)),
                        suggested=bool(item.get("suggested", False)),
                    )
                )
    return OutputProfile(
        output_id=str(data.get("output_id", "")),
        scope_type=str(data.get("scope_type", "stage")),
        scope_id=str(data.get("scope_id", "")),
        profile_name=str(data.get("profile_name", "Default")),
        profile_kind=str(data.get("profile_kind", "stage_output")),
        frame_profile=str(data.get("frame_profile", "source")),
        metric_caption_preset=(
            data.get("metric_caption_preset", {})
            if isinstance(data.get("metric_caption_preset"), dict)
            else {}
        ),
        lead_in_card=(
            data.get("lead_in_card", {}) if isinstance(data.get("lead_in_card"), dict) else {}
        ),
        brand_mark=(data.get("brand_mark", {}) if isinstance(data.get("brand_mark"), dict) else {}),
        subject_track_crop=(
            data.get("subject_track_crop", {})
            if isinstance(data.get("subject_track_crop"), dict)
            else {}
        ),
        visibility_recipe=(
            data.get("visibility_recipe", {})
            if isinstance(data.get("visibility_recipe"), dict)
            else {}
        ),
        angle_director_plan=angle_director_plan,
        retained_proxy_id=(None if retained_proxy_id in {None, ""} else str(retained_proxy_id)),
        last_rendered_at=(
            None
            if last_rendered_at in {None, ""}
            else datetime.fromisoformat(str(last_rendered_at))
        ),
    )


def _workspace_from_dict(data: dict) -> MatchWorkspace:
    created_at_str = data.get("created_at")
    updated_at_str = data.get("updated_at")

    workspace = MatchWorkspace(
        match_id=str(data.get("match_id", "")),
        name=str(data.get("name", "Untitled Match")),
        description=str(data.get("description", "")),
        created_at=datetime.now(UTC)
        if created_at_str in {None, ""}
        else datetime.fromisoformat(str(created_at_str)),
        updated_at=datetime.now(UTC)
        if updated_at_str in {None, ""}
        else datetime.fromisoformat(str(updated_at_str)),
        stage_order=[str(item) for item in (data.get("stage_order") or [])],
        shared_defaults=(
            data.get("shared_defaults", {}) if isinstance(data.get("shared_defaults"), dict) else {}
        ),
        first_stage_snapshot=(
            data.get("first_stage_snapshot", {})
            if isinstance(data.get("first_stage_snapshot"), dict)
            else {}
        ),
        ui_state=(data.get("ui_state", {}) if isinstance(data.get("ui_state"), dict) else {}),
        schema_version=int(data.get("schema_version", 1)),
    )

    workspace.stage_entries = {}
    raw_entries = data.get("stage_entries")
    if isinstance(raw_entries, dict):
        for key, value in raw_entries.items():
            if isinstance(value, dict):
                workspace.stage_entries[str(key)] = _stage_entry_from_dict(value)

    workspace.match_output_profiles = []
    raw_profiles = data.get("match_output_profiles")
    if isinstance(raw_profiles, list):
        for item in raw_profiles:
            if isinstance(item, dict):
                workspace.match_output_profiles.append(_output_profile_from_dict(item))

    return workspace


def save_workspace(workspace: MatchWorkspace, bundle_path: str | Path) -> Path:
    workspace_path = ensure_workspace_structure(bundle_path)
    metadata_path = workspace_metadata_path(workspace_path)
    metadata_path.write_text(json.dumps(_workspace_to_dict(workspace), indent=2))
    return workspace_path


def load_workspace(bundle_path: str | Path) -> MatchWorkspace:
    workspace_path = resolve_workspace_path(bundle_path)
    metadata_path = workspace_metadata_path(workspace_path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"No {WORKSPACE_FILENAME} found in {workspace_path}.")
    return _workspace_from_dict(json.loads(metadata_path.read_text()))
