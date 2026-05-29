from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import quote

from splitshot.domain.models import MERGE_SOURCE_ANGLE_ROLE_VALUES, Project, project_to_dict
from splitshot.export.presets import export_presets_for_api
from splitshot.presentation.stage import build_stage_presentation
from splitshot.scoring.logic import (
    normalize_penalty_counts_for_ruleset,
    normalize_score_letter_for_ruleset,
    scoring_presets_for_api,
)
from splitshot.timeline.model import compute_split_rows


def _default_workspace_context() -> dict[str, Any]:
    return {
        "editor_scope": "single",
        "active_match_id": None,
        "active_stage_id": None,
        "workspace_path": None,
        "return_to_match_available": False,
        "workspace": None,
        "match_workspace_summary": None,
        "workspace_stage_entries": [],
        "workspace_shared_defaults": {},
        "workspace_override_summary": {},
        "output_profiles": [],
        "inherited_setting_status": {},
        "opened_from_match": None,
        "stage_workspace_status": {},
        "output_profile_summary": [],
        "returned_stage_id": None,
    }


def _build_workspace_context(
    controller: Any | None,
    *,
    media_cache_token: str | None = None,
) -> dict[str, Any]:
    """Build workspace/scope context from controller state."""
    context = _default_workspace_context()
    if controller is None:
        return context

    workspace = getattr(controller, "workspace", None)
    context.update(
        {
        "editor_scope": getattr(controller, "editor_scope", "single"),
        "active_match_id": workspace.match_id if workspace else None,
        "active_stage_id": getattr(controller, "active_stage_id", None),
        "workspace_path": str(getattr(controller, "workspace_path", "") or "") or None,
        "return_to_match_available": getattr(controller, "_return_to_workspace_available", False),
        "opened_from_match": (
            workspace.match_id
            if workspace
            and controller
            and getattr(controller, "_return_to_workspace_available", False)
            else None
        ),
        "returned_stage_id": getattr(controller, "_last_returned_stage_id", None)
        if controller
        else None,
        }
    )

    if workspace is not None:
        context["match_workspace_summary"] = {
            "match_id": workspace.match_id,
            "path": context["workspace_path"],
            "name": workspace.name,
            "description": workspace.description,
            "stage_count": len(workspace.stage_entries),
            "updated_at": workspace.updated_at.isoformat() if workspace.updated_at else None,
        }
        context["workspace"] = dict(context["match_workspace_summary"])
        context["workspace_shared_defaults"] = dict(workspace.shared_defaults)

        entries = []
        override_summary = {}
        stage_status = {}
        for index, stage_id in enumerate(workspace.stage_order, start=1):
            entry = workspace.stage_entries.get(stage_id)
            if entry is not None:
                preview_url = None
                stage_project_file = None
                resolve_stage_project = getattr(controller, "_workspace_stage_project_file", None)
                if entry.source_media_present and callable(resolve_stage_project):
                    try:
                        stage_project_file = resolve_stage_project(entry.stage_id, entry=entry)
                    except TypeError:
                        stage_project_file = resolve_stage_project(entry.stage_id)
                    except Exception:
                        stage_project_file = None
                if stage_project_file is not None and Path(stage_project_file).is_file():
                    cache_suffix = f"?v={quote(str(media_cache_token))}" if media_cache_token else ""
                    preview_url = f"/media/workspace-stage/{quote(entry.stage_id)}{cache_suffix}"
                entries.append(
                    {
                        "stage_id": entry.stage_id,
                        "name": entry.display_name,
                        "display_name": entry.display_name,
                        "stage_number": entry.stage_number,
                        "order_index": index,
                        "status": entry.status,
                        "media_loaded": entry.source_media_present,
                        "source_media_present": entry.source_media_present,
                        "override_count": len(entry.override_values),
                        "override_values": dict(entry.override_values),
                        "has_overrides": bool(entry.override_values),
                        "inherited_from_first": entry.inherited_from_first,
                        "preview_url": preview_url,
                        "last_reviewed_at": entry.last_reviewed_at.isoformat()
                        if entry.last_reviewed_at
                        else None,
                    }
                )
                if entry.override_values:
                    override_summary[stage_id] = dict(entry.override_values)
                stage_status[stage_id] = {
                    "status": entry.status,
                    "has_overrides": bool(entry.override_values),
                    "source_media_present": entry.source_media_present,
                    "last_reviewed_at": entry.last_reviewed_at.isoformat()
                    if entry.last_reviewed_at
                    else None,
                }
        context["workspace_stage_entries"] = entries
        context["workspace_override_summary"] = override_summary
        context["stage_workspace_status"] = stage_status

        profiles = []
        profile_summary = []
        for profile in workspace.match_output_profiles:
            profiles.append(
                {
                    "output_id": profile.output_id,
                    "profile_name": profile.profile_name,
                    "profile_kind": profile.profile_kind,
                    "frame_profile": profile.frame_profile,
                    "scope_type": profile.scope_type,
                    "scope_id": profile.scope_id,
                }
            )
            profile_summary.append(
                {
                    "output_id": profile.output_id,
                    "profile_name": profile.profile_name,
                    "profile_kind": profile.profile_kind,
                    "scope_type": profile.scope_type,
                }
            )
        context["output_profiles"] = profiles
        context["output_profile_summary"] = profile_summary

        inherited_status = {}
        for stage_id in workspace.stage_order:
            entry = workspace.stage_entries.get(stage_id)
            if entry and entry.override_values:
                for key in entry.override_values:
                    inherited_status[f"{stage_id}.{key}"] = {
                        "stage_id": stage_id,
                        "key": key,
                        "inherited": False,
                        "value": entry.override_values[key],
                    }
        context["inherited_setting_status"] = inherited_status

    return context


# Cache for library/proxy summaries (avoids disk I/O on every /api/state poll)
_library_summary_cache: dict[str, Any] = {}
_library_summary_cache_time: float = 0.0
_proxy_summary_cache: dict[str, Any] = {}
_proxy_summary_cache_time: float = 0.0
_CACHE_TTL_SECONDS = 5.0

_MERGE_SOURCE_ROLE_PRIORITY = {
    role: index for index, role in enumerate(MERGE_SOURCE_ANGLE_ROLE_VALUES)
}


def _build_library_summary(controller: Any | None) -> dict[str, Any]:
    """Build library summary with caching."""
    global _library_summary_cache, _library_summary_cache_time
    import time

    now = time.monotonic()
    if _library_summary_cache and (now - _library_summary_cache_time) < _CACHE_TTL_SECONDS:
        return _library_summary_cache

    try:
        from splitshot.persistence.library import read_stage_metrics, read_match_metrics

        stage_metrics = read_stage_metrics()
        match_metrics = read_match_metrics()
        _library_summary_cache = {
            "stage_count": len(stage_metrics),
            "match_count": len(match_metrics),
            "last_updated": stage_metrics[-1]["event_date"] if stage_metrics else None,
            "filters_available": ["discipline", "competitor", "match_id", "stage_id", "sort_by"],
            "selection": None,
        }
        _library_summary_cache_time = now
        return _library_summary_cache
    except Exception:
        return {
            "stage_count": 0,
            "match_count": 0,
            "last_updated": None,
            "filters_available": ["discipline", "competitor", "match_id", "stage_id", "sort_by"],
            "selection": None,
        }


def _build_proxy_summary(controller: Any | None) -> dict[str, Any]:
    """Build proxy status summary with caching."""
    global _proxy_summary_cache, _proxy_summary_cache_time
    import time

    now = time.monotonic()
    if _proxy_summary_cache and (now - _proxy_summary_cache_time) < _CACHE_TTL_SECONDS:
        return _proxy_summary_cache

    if controller is not None:
        try:
            status = controller.proxy_status()
            _proxy_summary_cache = {
                "active_proxy_id": status.get("scope_id"),
                "proxy_stale": status.get("stale", True),
                "proxy_available": status.get("exists", False),
                "proxy_path": status.get("proxy_path"),
                "last_generated": status.get("last_generated"),
            }
            _proxy_summary_cache_time = now
            return _proxy_summary_cache
        except Exception:
            pass
    return {
        "active_proxy_id": None,
        "proxy_stale": False,
        "proxy_available": False,
        "proxy_path": None,
        "last_generated": None,
    }


def _build_performance_summary_slice(controller: Any | None) -> dict[str, Any]:
    return {
        "library_summary": deepcopy(_build_library_summary(controller)),
        "proxy_summary": deepcopy(_build_proxy_summary(controller)),
        "library_filters": [
            "discipline",
            "competitor",
            "match_id",
            "stage_id",
            "sort_by",
            "sort_order",
        ],
        "library_selection": None,
        "library_reopen_targets": [],
    }


def _normalize_serialized_score(
    ruleset: str,
    score: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(score, dict):
        return score
    normalized = dict(score)
    normalized_letter = normalize_score_letter_for_ruleset(ruleset, normalized.get("letter"))
    if normalized_letter is not None:
        normalized["letter"] = normalized_letter
    normalized["penalty_counts"] = normalize_penalty_counts_for_ruleset(
        ruleset,
        dict(normalized.get("penalty_counts") or {}),
    )
    return normalized


def _normalize_scoring_project_payload(project_payload: dict[str, Any], ruleset: str) -> None:
    scoring = project_payload.get("scoring")
    if isinstance(scoring, dict):
        scoring["penalty_counts"] = normalize_penalty_counts_for_ruleset(
            ruleset,
            dict(scoring.get("penalty_counts") or {}),
        )

    analysis = project_payload.get("analysis")
    if not isinstance(analysis, dict):
        return
    for shot in analysis.get("shots", []):
        if not isinstance(shot, dict):
            continue
        shot["score"] = _normalize_serialized_score(ruleset, shot.get("score"))


def _normalize_scoring_row_payload(row: dict[str, Any], ruleset: str) -> dict[str, Any]:
    normalized = dict(row)
    score_letter = normalize_score_letter_for_ruleset(ruleset, normalized.get("score_letter"))
    if score_letter is not None:
        normalized["score_letter"] = score_letter
    normalized["penalty_counts"] = normalize_penalty_counts_for_ruleset(
        ruleset,
        dict(normalized.get("penalty_counts") or {}),
    )
    return normalized


def _normalize_timing_project_payload(project_payload: dict[str, Any], project: Project) -> None:
    shot_ids = {shot.id for shot in project.analysis.shots}
    ui_state = project_payload.get("ui_state")
    if not isinstance(ui_state, dict):
        return
    if ui_state.get("selected_shot_id") not in shot_ids:
        ui_state["selected_shot_id"] = None
    raw_timing_edit_ids = ui_state.get("timing_edit_shot_ids")
    if isinstance(raw_timing_edit_ids, list):
        ui_state["timing_edit_shot_ids"] = [
            shot_id for shot_id in raw_timing_edit_ids if shot_id in shot_ids
        ]


def _default_practiscore_session_payload() -> dict[str, Any]:
    return {
        "state": "not_authenticated",
        "message": "Connect PractiScore to use your browser session for background sync.",
        "details": {},
    }


def _normalize_practiscore_session_payload(payload: object) -> dict[str, Any]:
    normalized = _default_practiscore_session_payload()
    if not isinstance(payload, dict):
        return normalized
    normalized["state"] = str(payload.get("state") or normalized["state"])
    normalized["message"] = str(payload.get("message") or normalized["message"])
    details = payload.get("details")
    normalized["details"] = dict(details) if isinstance(details, dict) else {}
    return normalized


def _default_practiscore_sync_payload() -> dict[str, Any]:
    return {
        "state": "idle",
        "message": "No remote PractiScore sync activity yet.",
        "matches": [],
        "selected_remote_id": None,
        "error_category": "",
        "details": {},
    }


def _normalize_practiscore_sync_payload(payload: object) -> dict[str, Any]:
    normalized = _default_practiscore_sync_payload()
    if not isinstance(payload, dict):
        return normalized
    normalized["state"] = str(payload.get("state") or normalized["state"])
    normalized["message"] = str(payload.get("message") or normalized["message"])
    raw_matches = payload.get("matches")
    if isinstance(raw_matches, list):
        normalized["matches"] = [
            {
                "remote_id": str(item.get("remote_id") or ""),
                "label": str(item.get("label") or ""),
                "match_type": str(item.get("match_type") or ""),
                "event_name": str(item.get("event_name") or ""),
                "event_date": str(item.get("event_date") or ""),
            }
            for item in raw_matches
            if isinstance(item, dict) and str(item.get("remote_id") or "").strip()
        ]
    selected_remote_id = payload.get("selected_remote_id")
    normalized["selected_remote_id"] = (
        None if selected_remote_id in {None, ""} else str(selected_remote_id)
    )
    normalized["error_category"] = str(payload.get("error_category") or "")
    details = payload.get("details")
    normalized["details"] = dict(details) if isinstance(details, dict) else {}
    return normalized


def _default_practiscore_options_payload() -> dict[str, Any]:
    return {
        "has_source": False,
        "source_name": "",
        "detected_match_type": "",
        "stage_numbers": [],
        "competitors": [],
    }


def _build_practiscore_summary_slice(
    practiscore_options: dict[str, Any] | None,
) -> dict[str, Any]:
    practiscore_payload = deepcopy(practiscore_options or {})
    practiscore_session_payload = _normalize_practiscore_session_payload(
        practiscore_payload.pop("_session_payload", None)
    )
    practiscore_sync_payload = _normalize_practiscore_sync_payload(
        practiscore_payload.pop("_sync_payload", None)
    )
    return {
        "practiscore_session": practiscore_session_payload,
        "practiscore_sync": practiscore_sync_payload,
        "practiscore_options": practiscore_payload or _default_practiscore_options_payload(),
    }


def _build_stage_media_summary(
    project: Project,
    *,
    media_cache_token: str | None = None,
) -> dict[str, Any]:
    primary_path = Path(project.primary_video.path) if project.primary_video.path else None
    secondary_path = (
        Path(project.secondary_video.path)
        if project.secondary_video is not None and project.secondary_video.path
        else None
    )
    primary_available = bool(primary_path and primary_path.exists() and primary_path.is_file())
    secondary_available = bool(
        secondary_path and secondary_path.exists() and secondary_path.is_file()
    )
    return {
        "primary_available": primary_available,
        "secondary_available": secondary_available,
        "primary_url": "/media/primary" if primary_available else None,
        "secondary_url": "/media/secondary" if secondary_available else None,
        "secondary_source_id": project.analysis.analyzed_secondary_source_id,
        "cache_token": media_cache_token or "",
    }


def _merge_source_payload_id(item: object) -> str | None:
    if not isinstance(item, dict):
        return None
    source_id = item.get("id")
    if source_id in {None, ""}:
        return None
    return str(source_id)


def _merge_source_asset_payload(item: object) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    asset_payload = item.get("asset")
    return asset_payload if isinstance(asset_payload, dict) else {}


def _merge_source_media_kind(item: object) -> str:
    asset_payload = _merge_source_asset_payload(item)
    return str(
        asset_payload.get("media_kind")
        or ("still_image" if asset_payload.get("is_still_image") else "video")
    )


def _merge_source_angle_role(item: object) -> str:
    asset_payload = _merge_source_asset_payload(item)
    default_role = "detail" if asset_payload.get("is_still_image") else "follow"
    if not isinstance(item, dict):
        return default_role
    normalized_role = str(
        item.get("camera_role") or item.get("angle_role") or default_role
    ).strip().lower()
    if normalized_role in _MERGE_SOURCE_ROLE_PRIORITY:
        return normalized_role
    return default_role


def _merge_source_order_index(item: object) -> int | None:
    if not isinstance(item, dict):
        return None
    placement_payload = item.get("placement")
    raw_order_index = None
    if isinstance(placement_payload, dict):
        raw_order_index = placement_payload.get("order_index", placement_payload.get("layer_index"))
    if raw_order_index in {None, ""}:
        raw_order_index = item.get("order_index", item.get("display_order"))
    try:
        return max(0, int(raw_order_index))
    except (TypeError, ValueError):
        return None


def _merge_source_sync_analysis_sort_key(item: object) -> tuple[int, int, int, str]:
    order_index = _merge_source_order_index(item)
    return (
        _MERGE_SOURCE_ROLE_PRIORITY.get(
            _merge_source_angle_role(item),
            len(_MERGE_SOURCE_ROLE_PRIORITY),
        ),
        0 if order_index is not None else 1,
        0 if order_index is None else order_index,
        _merge_source_payload_id(item) or "",
    )


def _merge_source_supports_secondary_analysis(item: object) -> bool:
    asset_payload = _merge_source_asset_payload(item)
    return bool(str(asset_payload.get("path") or "").strip()) and not bool(
        asset_payload.get("is_still_image")
    ) and _merge_source_media_kind(item) != "animated_gif"


def _first_sync_analysis_source_id(merge_sources_payload: list[object]) -> str | None:
    analyzable_sources = [
        item
        for item in merge_sources_payload
        if _merge_source_payload_id(item) is not None
        and _merge_source_supports_secondary_analysis(item)
    ]
    if not analyzable_sources:
        return None
    selected_item = min(
        analyzable_sources,
        key=_merge_source_sync_analysis_sort_key,
    )
    return _merge_source_payload_id(selected_item)


def _inflate_merge_source_placement_truth(
    item: dict[str, Any],
    source: Any,
    index: int,
) -> None:
    placement_payload = item.get("placement")
    if not isinstance(placement_payload, dict):
        placement_payload = {}
        item["placement"] = placement_payload

    order_index = source.placement.order_index
    if order_index is None:
        order_index = index
    layer_index = source.placement.layer_index
    if layer_index is None:
        layer_index = order_index

    placement_payload["mode"] = str(source.placement.mode.value)
    placement_payload["slot"] = str(source.placement.slot.value)
    placement_payload["target_kind"] = str(source.placement.target_kind.value)
    placement_payload["target_source_id"] = (
        None
        if source.placement.target_source_id in {None, ""}
        else str(source.placement.target_source_id)
    )
    placement_payload["order_index"] = order_index
    placement_payload["layer_index"] = layer_index


def _augment_merge_source_summary(project_payload: dict[str, Any], project: Project) -> None:
    merge_sources_payload = project_payload.get("merge_sources")
    analysis_payload = project_payload.get("analysis")
    if not isinstance(merge_sources_payload, list) or not isinstance(analysis_payload, dict):
        return

    available_source_ids = {
        source_id
        for item in merge_sources_payload
        if (source_id := _merge_source_payload_id(item)) is not None
    }
    analyzed_source_id = analysis_payload.get("analyzed_secondary_source_id")
    if analyzed_source_id in {None, ""}:
        analyzed_source_id = None
    else:
        analyzed_source_id = str(analyzed_source_id)
    if analyzed_source_id not in available_source_ids:
        analyzed_source_id = None

    eligible_source_id = _first_sync_analysis_source_id(merge_sources_payload)
    sync_status_source_id = analyzed_source_id or eligible_source_id

    for source_index, item in enumerate(merge_sources_payload):
        if not isinstance(item, dict):
            continue
        if source_index < len(project.merge_sources):
            _inflate_merge_source_placement_truth(item, project.merge_sources[source_index], source_index)
        item["media_kind"] = _merge_source_media_kind(item)
        source_id = _merge_source_payload_id(item)
        supports_sync_analysis = bool(source_id and source_id == eligible_source_id)
        is_analyzed_sync_source = bool(analyzed_source_id and source_id == analyzed_source_id)
        owns_sync_status = bool(sync_status_source_id and source_id == sync_status_source_id)
        item["is_analyzed_sync_source"] = is_analyzed_sync_source
        item["supports_sync_analysis"] = supports_sync_analysis
        item["can_rerun_sync_analysis"] = supports_sync_analysis
        item["sync_analysis_status"] = (
            str(analysis_payload.get("secondary_analysis_status") or "idle")
            if owns_sync_status
            else "idle"
        )
        item["sync_analysis_message"] = (
            str(analysis_payload.get("secondary_analysis_message") or "")
            if owns_sync_status
            else ""
        )
        item["secondary_beep_time_ms"] = (
            analysis_payload.get("beep_time_ms_secondary") if is_analyzed_sync_source else None
        )
        item["sync_offset_source"] = (
            str(analysis_payload.get("secondary_sync_source") or "manual")
            if owns_sync_status
            else "manual"
        )


def _build_stage_project_payload(project: Project, ruleset: str) -> dict[str, Any]:
    project_payload = project_to_dict(project)
    _normalize_scoring_project_payload(project_payload, ruleset)
    _normalize_timing_project_payload(project_payload, project)
    _augment_merge_source_summary(project_payload, project)
    return project_payload


def _build_stage_summary_slice(
    project: Project,
    *,
    media_cache_token: str | None = None,
) -> dict[str, Any]:
    rows = compute_split_rows(project)
    shotml_project = deepcopy(project)
    for shot in shotml_project.analysis.shots:
        if shot.shotml_time_ms is not None:
            shot.time_ms = shot.shotml_time_ms
        if shot.shotml_confidence is not None:
            shot.confidence = shot.shotml_confidence
    shotml_rows_by_id = {
        row.shot_id: row for row in compute_split_rows(shotml_project) if row.shot_id is not None
    }
    presentation = build_stage_presentation(project)
    scoring_summary = dict(presentation.metrics.scoring_summary)
    ruleset = str(scoring_summary.get("ruleset") or project.scoring.ruleset)
    project_payload = _build_stage_project_payload(project, ruleset)

    split_rows_payload = []
    for row in rows:
        row_payload = _normalize_scoring_row_payload(asdict(row), ruleset)
        shotml_row = shotml_rows_by_id.get(row.shot_id)
        if shotml_row is not None:
            row_payload["shotml_time_ms"] = shotml_row.absolute_time_ms
            row_payload["shotml_split_ms"] = shotml_row.split_ms
            row_payload["shotml_cumulative_ms"] = shotml_row.cumulative_ms
            row_payload["shotml_confidence"] = shotml_row.confidence
            row_payload["adjustment_ms"] = (
                None
                if row.split_ms is None or shotml_row.split_ms is None
                else row.split_ms - shotml_row.split_ms
            )
            row_payload["final_time_ms"] = row.cumulative_ms
        split_rows_payload.append(row_payload)

    timing_segments_payload = [
        _normalize_scoring_row_payload(asdict(segment), ruleset)
        for segment in presentation.timing_segments
    ]

    return {
        "project": project_payload,
        "metrics": asdict(presentation.metrics),
        "timing_segments": timing_segments_payload,
        "split_rows": split_rows_payload,
        "scoring_summary": scoring_summary,
        "scoring_presets": scoring_presets_for_api(),
        "export_presets": export_presets_for_api(),
        "media": _build_stage_media_summary(project, media_cache_token=media_cache_token),
    }


def _build_shared_summary_slice(
    status_message: str,
    *,
    settings: dict[str, Any] | None = None,
    settings_layers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status_message,
        "settings": settings or {},
        "settings_layers": settings_layers or {},
        "default_project_path": str(Path.home() / "splitshot"),
    }


def browser_state(
    project: Project,
    status_message: str,
    settings: dict[str, Any] | None = None,
    settings_layers: dict[str, Any] | None = None,
    practiscore_options: dict[str, Any] | None = None,
    media_cache_token: str | None = None,
    controller: Any | None = None,
) -> dict[str, Any]:
    shared_summary = _build_shared_summary_slice(
        status_message,
        settings=settings,
        settings_layers=settings_layers,
    )
    stage_summary = _build_stage_summary_slice(project, media_cache_token=media_cache_token)
    practiscore_summary = _build_practiscore_summary_slice(practiscore_options)
    workspace_summary = _build_workspace_context(controller, media_cache_token=media_cache_token)
    performance_summary = _build_performance_summary_slice(controller)

    return {
        "status": shared_summary["status"],
        "project": stage_summary["project"],
        "settings": shared_summary["settings"],
        "settings_layers": shared_summary["settings_layers"],
        "metrics": stage_summary["metrics"],
        "timing_segments": stage_summary["timing_segments"],
        "split_rows": stage_summary["split_rows"],
        "scoring_summary": stage_summary["scoring_summary"],
        "scoring_presets": stage_summary["scoring_presets"],
        "practiscore_session": practiscore_summary["practiscore_session"],
        "practiscore_sync": practiscore_summary["practiscore_sync"],
        "practiscore_options": practiscore_summary["practiscore_options"],
        "export_presets": stage_summary["export_presets"],
        "default_project_path": shared_summary["default_project_path"],
        "media": stage_summary["media"],
        **workspace_summary,
        **performance_summary,
    }
