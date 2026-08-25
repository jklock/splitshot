from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any

from splitshot.domain.models import Project, project_stage_name_overlay_text, project_to_dict
from splitshot.export.presets import export_presets_for_api
from splitshot.presentation.stage import build_stage_presentation
from splitshot.scoring.logic import (
    competition_placement,
    imported_stage_penalty_count,
    normalize_penalty_counts_for_ruleset,
    normalize_score_letter_for_ruleset,
    scoring_presets_for_api,
    stage_competition_placement,
)
from splitshot.timeline.model import compute_split_rows


def _project_view_for_stage(project: Project, stage) -> Project:
    view = deepcopy(project)
    view.active_stage_id = stage.id
    view.primary_video = deepcopy(stage.primary_media)
    view.primary_trim_derivative = deepcopy(stage.primary_trim_derivative)
    view.secondary_video = None
    view.merge_sources = deepcopy(stage.added_media)
    view.analysis = deepcopy(stage.analysis)
    view.scoring = deepcopy(stage.scoring)
    view.overlay = deepcopy(stage.overlay)
    view.popups = deepcopy(stage.popups)
    view.popup_template = deepcopy(stage.popup_template)
    view.merge = deepcopy(stage.merge)
    view.export = deepcopy(stage.export)
    return view


def _build_stage_metrics(project: Project) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    stages = sorted(project.stages, key=lambda item: item.order_index)
    for stage in stages:
        view = _project_view_for_stage(project, stage)
        presentation = build_stage_presentation(view)
        scoring_summary = dict(presentation.metrics.scoring_summary)
        imported = scoring_summary.get("imported_stage") or {}
        is_idpa = str(imported.get("match_type") or "").casefold() == "idpa"
        official_result = imported.get("final_time") if is_idpa else imported.get("hit_factor")
        official_metrics = {
            "raw_time_ms": (
                None
                if imported.get("raw_seconds") is None
                else round(float(imported["raw_seconds"]) * 1000)
            ),
            "result_label": "Final" if is_idpa else scoring_summary.get("display_label", "Result"),
            "result_value": official_result,
            "display_value": ("--" if official_result is None else f"{float(official_result):.2f}"),
            "score_label": "Points Down" if is_idpa else "Shot Points",
            "score_value": (
                imported.get("aggregate_points") if is_idpa else scoring_summary.get("shot_points")
            ),
            "points_down": imported.get("aggregate_points") if is_idpa else None,
            "penalties": imported_stage_penalty_count(view),
            "division": imported.get("division") or stage.scoring.division,
            "classification": imported.get("classification") or stage.scoring.classification,
            "division_placement": stage_competition_placement(view, dimension="division"),
            "class_placement": stage_competition_placement(view, dimension="classification"),
            "overall_placement": stage_competition_placement(view),
            "spreadsheet_authoritative": bool(imported),
        }
        rows = [asdict(row) for row in compute_split_rows(view)]
        result.append(
            {
                "stage_id": stage.id,
                "order_index": stage.order_index,
                "stage_number": stage.imported_stage_number or stage.order_index,
                "stage_name": stage.label or stage.imported_stage_name,
                "metrics": asdict(presentation.metrics),
                "scoring_summary": scoring_summary,
                "official_metrics": official_metrics,
                "scoring": asdict(stage.scoring),
                "comparison_competitors": deepcopy(stage.scoring.comparison_competitors),
                "split_rows": rows,
                "timing_segments": [asdict(segment) for segment in presentation.timing_segments],
            }
        )
    if not result:
        presentation = build_stage_presentation(project)
        imported = presentation.metrics.scoring_summary.get("imported_stage") or {}
        result.append(
            {
                "stage_id": project.active_stage_id or "active-stage",
                "stage_number": imported.get("stage_number") or project.scoring.stage_number or 1,
                "stage_name": imported.get("stage_name") or "Stage 1",
                "metrics": asdict(presentation.metrics),
                "scoring_summary": dict(presentation.metrics.scoring_summary),
                "scoring": asdict(project.scoring),
                "comparison_competitors": deepcopy(project.scoring.comparison_competitors),
                "split_rows": [asdict(row) for row in compute_split_rows(project)],
                "timing_segments": [asdict(segment) for segment in presentation.timing_segments],
            }
        )
    return result


def _build_match_metrics(
    stage_metrics: list[dict[str, Any]], project: Project | None = None
) -> dict[str, Any]:
    metric_rows = [entry.get("metrics", {}) for entry in stage_metrics]
    summaries = [entry.get("scoring_summary", {}) for entry in stage_metrics]
    draws = [
        float(metrics["draw_ms"]) for metrics in metric_rows if metrics.get("draw_ms") is not None
    ]
    split_values = [
        float(row["split_ms"])
        for entry in stage_metrics
        for row in entry.get("split_rows", [])
        if row.get("shot_id") and row.get("split_ms") is not None
    ]
    raw_values = [
        float(metrics["raw_time_ms"])
        for metrics in metric_rows
        if metrics.get("raw_time_ms") is not None
    ]
    shot_points = sum(float(summary.get("shot_points") or 0.0) for summary in summaries)
    total_penalties = sum(float(summary.get("total_penalties") or 0.0) for summary in summaries)
    final_times = [
        float(summary["final_time"])
        for summary in summaries
        if summary.get("final_time") is not None
    ]
    first_summary = next((summary for summary in summaries if summary), {})
    imported_match = next(
        (
            summary.get("imported_stage", {})
            for summary in summaries
            if (summary.get("imported_stage") or {}).get("match_final_time") is not None
        ),
        {},
    )
    mode = str(first_summary.get("mode") or "")
    raw_seconds = sum(raw_values) / 1000.0
    if imported_match:
        result_value = float(imported_match["match_final_time"])
        result_label = "Final"
        display_value = f"{result_value:.2f}"
    elif mode == "hit_factor":
        adjusted_points = max(0.0, shot_points - total_penalties)
        result_value = None if raw_seconds <= 0 else adjusted_points / raw_seconds
        result_label = "Combined HF"
        display_value = "--" if result_value is None else f"{result_value:.2f}"
    else:
        result_value = sum(final_times) if final_times else None
        result_label = "Final"
        display_value = "--" if result_value is None else f"{result_value:.2f}"
    points_down = (
        float(imported_match.get("match_points_down") or 0.0)
        if imported_match
        else sum(
            float((summary.get("imported_stage") or {}).get("aggregate_points") or 0.0)
            for summary in summaries
            if (summary.get("imported_stage") or {}).get("match_type") == "idpa"
        )
    )
    direct_penalties = (
        float(imported_match.get("match_penalties") or 0.0) if imported_match else None
    )
    score_label = "Points Down" if imported_match.get("match_type") == "idpa" else "Shot Points"
    score_value = points_down if score_label == "Points Down" else shot_points
    return {
        "stage_count": int(imported_match.get("match_stage_count") or len(stage_metrics)),
        "draw_ms": None if not draws else round(sum(draws) / len(draws)),
        "raw_time_ms": (
            None if imported_match else (None if not raw_values else round(sum(raw_values)))
        ),
        "total_shots": sum(int(metrics.get("total_shots") or 0) for metrics in metric_rows),
        "average_split_ms": (
            None if not split_values else round(sum(split_values) / len(split_values))
        ),
        "beep_ms": None,
        "shot_points": shot_points,
        "points_down": points_down,
        "score_label": score_label,
        "score_value": score_value,
        "total_penalties": total_penalties if direct_penalties is None else direct_penalties,
        "penalty_counts": dict(imported_match.get("match_penalty_counts") or {}),
        "result_label": result_label,
        "result_value": result_value,
        "display_value": display_value,
        "ruleset": first_summary.get("ruleset", ""),
        "sport": first_summary.get("sport", ""),
        "spreadsheet_authoritative": bool(imported_match),
        "competitor": imported_match.get("competitor_name", ""),
        "division": imported_match.get("division", ""),
        "classification": imported_match.get("classification", ""),
        "overall_place": imported_match.get("competitor_place"),
        "division_placement": (
            competition_placement(project, dimension="division") if project else ""
        ),
        "class_placement": (
            competition_placement(project, dimension="classification") if project else ""
        ),
        "overall_placement": competition_placement(project) if project else "",
    }


def _trim_payload_is_active(trim_payload: dict[str, Any] | None) -> bool:
    return bool(
        isinstance(trim_payload, dict)
        and trim_payload.get("active_path_kind") == "local_derivative"
        and trim_payload.get("derivative_path")
    )


def _active_asset_payload(
    asset_payload: dict[str, Any] | None,
    trim_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if _trim_payload_is_active(trim_payload):
        derivative_asset = trim_payload.get("derivative_asset")
        if isinstance(derivative_asset, dict) and derivative_asset.get("path"):
            return derivative_asset
        if isinstance(asset_payload, dict):
            active_asset = dict(asset_payload)
            active_asset["path"] = str(trim_payload.get("derivative_path") or "")
            return active_asset
    return dict(asset_payload or {})


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


def browser_state(
    project: Project,
    status_message: str,
    settings: dict[str, Any] | None = None,
    settings_layers: dict[str, Any] | None = None,
    practiscore_options: dict[str, Any] | None = None,
    media_cache_token: str | None = None,
    output_profiles: list[dict[str, Any]] | None = None,
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
    stage_metrics = _build_stage_metrics(project)
    match_metrics = _build_match_metrics(stage_metrics, project)
    scoring_summary = dict(presentation.metrics.scoring_summary)
    ruleset = str(scoring_summary.get("ruleset") or project.scoring.ruleset)
    practiscore_payload = deepcopy(practiscore_options or {})
    practiscore_session_payload = _normalize_practiscore_session_payload(
        practiscore_payload.pop("_session_payload", None)
    )
    practiscore_sync_payload = _normalize_practiscore_sync_payload(
        practiscore_payload.pop("_sync_payload", None)
    )
    project_payload = project_to_dict(project)
    project_payload["stage_name_overlay_text"] = project_stage_name_overlay_text(project)
    _normalize_scoring_project_payload(project_payload, ruleset)
    _normalize_timing_project_payload(project_payload, project)
    primary_asset_payload = project_payload.get("primary_video")
    primary_trim_payload = project_payload.get("primary_trim_derivative")
    primary_trim_active = _trim_payload_is_active(primary_trim_payload)
    primary_active_asset = _active_asset_payload(primary_asset_payload, primary_trim_payload)
    primary_effective_media_path = str(primary_active_asset.get("path") or "")
    if isinstance(primary_asset_payload, dict):
        primary_asset_payload["original_path"] = str(primary_asset_payload.get("path") or "")
        primary_asset_payload["effective_media_path"] = primary_effective_media_path
        primary_asset_payload["trim_active"] = primary_trim_active
        primary_asset_payload["active_display_name"] = (
            Path(primary_effective_media_path).name if primary_effective_media_path else ""
        )
        primary_asset_payload["original_display_name"] = (
            Path(str(primary_asset_payload.get("path") or "")).name
            if primary_asset_payload.get("path")
            else ""
        )
        primary_asset_payload["active_duration_ms"] = primary_active_asset.get("duration_ms")
        primary_asset_payload["active_width"] = primary_active_asset.get("width")
        primary_asset_payload["active_height"] = primary_active_asset.get("height")
        primary_asset_payload["active_media_kind"] = str(
            primary_active_asset.get("media_kind")
            or ("still_image" if primary_active_asset.get("is_still_image") else "video")
        )
    merge_sources_payload = project_payload.get("merge_sources")
    analysis_payload = project_payload.get("analysis")
    if isinstance(merge_sources_payload, list) and isinstance(analysis_payload, dict):
        analyzed_source_id = analysis_payload.get("analyzed_secondary_source_id")
        secondary_source_payloads = {
            str(item.get("source_id") or ""): item
            for item in analysis_payload.get("secondary_sources", [])
            if isinstance(item, dict) and str(item.get("source_id") or "").strip()
        }
        active_secondary_path = ""
        active_secondary_trimmed = False
        for item in merge_sources_payload:
            if not isinstance(item, dict):
                continue
            asset_payload = item.get("asset")
            if isinstance(asset_payload, dict):
                item["media_kind"] = str(
                    asset_payload.get("media_kind")
                    or ("still_image" if asset_payload.get("is_still_image") else "video")
                )
            source_id = item.get("id")
            trim_payload = item.get("trim_derivative")
            trim_active = _trim_payload_is_active(trim_payload)
            active_asset_payload = _active_asset_payload(asset_payload, trim_payload)
            effective_media_path = str(active_asset_payload.get("path") or "")
            supports_sync_analysis = bool(
                source_id
                and isinstance(asset_payload, dict)
                and not bool(asset_payload.get("is_still_image"))
                and str(asset_payload.get("media_kind") or "video") != "animated_gif"
            )
            is_analyzed_sync_source = bool(analyzed_source_id and source_id == analyzed_source_id)
            sync_payload = secondary_source_payloads.get(str(source_id or ""), {})
            item["trim_active"] = trim_active
            item["original_media_path"] = str((asset_payload or {}).get("path") or "")
            item["effective_media_path"] = effective_media_path
            item["active_display_name"] = (
                Path(effective_media_path).name if effective_media_path else ""
            )
            item["original_display_name"] = (
                Path(str((asset_payload or {}).get("path") or "")).name
                if (asset_payload or {}).get("path")
                else ""
            )
            item["active_duration_ms"] = active_asset_payload.get("duration_ms")
            item["active_width"] = active_asset_payload.get("width")
            item["active_height"] = active_asset_payload.get("height")
            item["active_media_kind"] = str(
                active_asset_payload.get("media_kind")
                or ("still_image" if active_asset_payload.get("is_still_image") else "video")
            )
            item["is_analyzed_sync_source"] = is_analyzed_sync_source
            item["supports_sync_analysis"] = supports_sync_analysis
            item["can_rerun_sync_analysis"] = supports_sync_analysis
            item["sync_analysis_status"] = (
                str(
                    sync_payload.get("analysis_status")
                    or analysis_payload.get("secondary_analysis_status")
                    or "idle"
                )
                if is_analyzed_sync_source or supports_sync_analysis or sync_payload
                else "idle"
            )
            item["sync_analysis_message"] = (
                str(
                    sync_payload.get("analysis_message")
                    or analysis_payload.get("secondary_analysis_message")
                    or ""
                )
                if is_analyzed_sync_source or supports_sync_analysis or sync_payload
                else ""
            )
            item["secondary_beep_time_ms"] = (
                sync_payload.get("beep_time_ms", analysis_payload.get("beep_time_ms_secondary"))
                if is_analyzed_sync_source or sync_payload
                else None
            )
            item["sync_offset_source"] = (
                str(
                    sync_payload.get("sync_source")
                    or analysis_payload.get("secondary_sync_source")
                    or "manual"
                )
                if is_analyzed_sync_source or supports_sync_analysis or sync_payload
                else "manual"
            )
            item["waveform_sample_count"] = len(sync_payload.get("waveform", []) or [])
            if is_analyzed_sync_source:
                active_secondary_path = effective_media_path
                active_secondary_trimmed = trim_active
    else:
        active_secondary_path = ""
        active_secondary_trimmed = False
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
    primary_path = Path(primary_effective_media_path) if primary_effective_media_path else None
    secondary_path_value = active_secondary_path or (
        project.secondary_video.path
        if project.secondary_video is not None and project.secondary_video.path
        else ""
    )
    secondary_path = Path(secondary_path_value) if secondary_path_value else None
    primary_available = bool(primary_path and primary_path.exists() and primary_path.is_file())
    secondary_available = bool(
        secondary_path and secondary_path.exists() and secondary_path.is_file()
    )
    return {
        "status": status_message,
        "project": project_payload,
        "settings": settings or {},
        "settings_layers": settings_layers or {},
        "metrics": asdict(presentation.metrics),
        "stage_metrics": stage_metrics,
        "match_metrics": match_metrics,
        "timing_segments": timing_segments_payload,
        "split_rows": split_rows_payload,
        "scoring_summary": scoring_summary,
        "scoring_presets": scoring_presets_for_api(),
        "practiscore_session": practiscore_session_payload,
        "practiscore_sync": practiscore_sync_payload,
        "practiscore_options": practiscore_payload
        or {
            "has_source": False,
            "source_name": "",
            "detected_match_type": "",
            "stage_numbers": [],
            "competitors": [],
        },
        "export_presets": export_presets_for_api(),
        "output_profiles": output_profiles or [],
        "default_project_path": str(Path.home() / "splitshot"),
        "media": {
            "primary_available": primary_available,
            "secondary_available": secondary_available,
            "primary_url": "/media/primary" if primary_available else None,
            "secondary_url": ("/media/secondary" if secondary_available else None),
            "primary_active_path": primary_effective_media_path,
            "primary_trimmed": primary_trim_active,
            "secondary_source_id": project.analysis.analyzed_secondary_source_id,
            "secondary_active_path": secondary_path_value,
            "secondary_trimmed": active_secondary_trimmed,
            "cache_token": media_cache_token or "",
        },
    }
