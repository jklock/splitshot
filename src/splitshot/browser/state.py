from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from splitshot.domain.models import Project, project_to_dict
from splitshot.export.presets import export_presets_for_api
from splitshot.presentation.stage import build_stage_presentation
from splitshot.scoring.logic import (
    normalize_penalty_counts_for_ruleset,
    normalize_score_letter_for_ruleset,
    scoring_presets_for_api,
)
from splitshot.timeline.model import compute_split_rows


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


def browser_state(
    project: Project,
    status_message: str,
    settings: dict[str, Any] | None = None,
    settings_layers: dict[str, Any] | None = None,
    practiscore_options: dict[str, Any] | None = None,
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
        row.shot_id: row
        for row in compute_split_rows(shotml_project)
        if row.shot_id is not None
    }
    presentation = build_stage_presentation(project)
    scoring_summary = dict(presentation.metrics.scoring_summary)
    ruleset = str(scoring_summary.get("ruleset") or project.scoring.ruleset)
    project_payload = project_to_dict(project)
    _normalize_scoring_project_payload(project_payload, ruleset)
    _normalize_timing_project_payload(project_payload, project)
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
                None if row.split_ms is None or shotml_row.split_ms is None else row.split_ms - shotml_row.split_ms
            )
            row_payload["final_time_ms"] = row.cumulative_ms
        split_rows_payload.append(row_payload)
    timing_segments_payload = [
        _normalize_scoring_row_payload(asdict(segment), ruleset)
        for segment in presentation.timing_segments
    ]
    primary_path = Path(project.primary_video.path) if project.primary_video.path else None
    secondary_path = (
        Path(project.secondary_video.path)
        if project.secondary_video is not None and project.secondary_video.path
        else None
    )
    primary_available = bool(primary_path and primary_path.exists() and primary_path.is_file())
    secondary_available = bool(secondary_path and secondary_path.exists() and secondary_path.is_file())
    return {
        "status": status_message,
        "project": project_payload,
        "settings": settings or {},
        "settings_layers": settings_layers or {},
        "metrics": asdict(presentation.metrics),
        "timing_segments": timing_segments_payload,
        "split_rows": split_rows_payload,
        "scoring_summary": scoring_summary,
        "scoring_presets": scoring_presets_for_api(),
        "practiscore_options": practiscore_options or {
            "has_source": False,
            "source_name": "",
            "detected_match_type": "",
            "stage_numbers": [],
            "competitors": [],
        },
        "export_presets": export_presets_for_api(),
        "default_project_path": str(Path.home() / "splitshot"),
        "media": {
            "primary_available": primary_available,
            "secondary_available": secondary_available,
            "primary_url": "/media/primary" if primary_available else None,
            "secondary_url": (
                "/media/secondary"
                if secondary_available
                else None
            ),
            "cache_token": media_cache_token or "",
        },
    }
