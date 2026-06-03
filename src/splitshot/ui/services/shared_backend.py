"""Shared backend support helpers extracted from the UI controller."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from splitshot.persistence.library import list_recent_library_activity
from splitshot.persistence.projects import list_recent_project_activity

if TYPE_CHECKING:
    from splitshot.ui.controller import ProjectController


UTC = timezone.utc
_WORKSPACE_METADATA_FILENAME = "workspace.json"


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


def _recent_workspace_timestamp(
    metadata: dict[str, object],
    fallback_timestamp: float,
) -> tuple[float, str]:
    for key in ("last_opened", "updated_at", "modified_at", "created_at"):
        parsed = _parse_activity_datetime(metadata.get(key))
        if parsed is not None:
            return parsed.timestamp(), parsed.isoformat()
    if fallback_timestamp > 0:
        fallback = datetime.fromtimestamp(fallback_timestamp, UTC)
        return fallback.timestamp(), fallback.isoformat()
    return 0.0, ""


def _recent_workspace_entry(workspace_path: Path) -> dict[str, object] | None:
    metadata_path = workspace_path / _WORKSPACE_METADATA_FILENAME
    if not metadata_path.is_file():
        return None
    try:
        metadata = json.loads(metadata_path.read_text())
    except Exception:
        return None
    if not isinstance(metadata, dict):
        return None
    try:
        fallback_timestamp = workspace_path.stat().st_mtime
    except OSError:
        fallback_timestamp = 0.0
    timestamp, date_value = _recent_workspace_timestamp(metadata, fallback_timestamp)
    return {
        "name": str(metadata.get("name") or workspace_path.name),
        "path": str(workspace_path.resolve(strict=False)),
        "date": date_value,
        "type": "match",
        "surface": "multi",
        "timestamp": timestamp,
    }


def _scan_recent_workspaces(
    limit: int = 20,
    *,
    root: str | Path | None = None,
) -> list[dict[str, object]]:
    workspace_root = (
        Path(root).expanduser() if root is not None else Path.home() / ".splitshot" / "workspaces"
    )
    if not workspace_root.is_dir():
        return []

    recent_entries: list[dict[str, object]] = []
    for entry in workspace_root.iterdir():
        if not entry.is_dir():
            continue
        recent_entry = _recent_workspace_entry(entry)
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


def _recent_sort_timestamp(item: dict[str, object]) -> float:
    date_value = str(item.get("date") or "").strip()
    if date_value:
        parsed = _parse_activity_datetime(date_value)
        if parsed is not None:
            return parsed.timestamp()
    return float(item.get("timestamp") or 0.0)


def _is_stage_recent_entry(item: dict[str, object]) -> bool:
    surface = str(item.get("surface") or "").strip().lower()
    if surface == "single":
        return True
    recent_type = str(item.get("type") or "").strip().lower()
    return recent_type in {"stage", "single"}


def landing_recent(controller: ProjectController | None = None) -> dict[str, object]:
    """Return recent landing activity using persistence helpers where available."""
    del controller

    recent: list[dict[str, object]] = []

    try:
        recent.extend(list_recent_project_activity(limit=20))
    except Exception:
        pass

    try:
        recent.extend(_scan_recent_workspaces(limit=20))
    except Exception:
        pass

    try:
        recent.extend(list_recent_library_activity(limit=8, stage_limit=5, match_limit=3))
    except Exception:
        pass

    recent = [item for item in recent if _is_stage_recent_entry(item)]
    recent.sort(key=_recent_sort_timestamp, reverse=True)
    return {"recent": recent[:15]}


def proxy_status(
    controller: ProjectController,
    scope_type: str = "stage",
    scope_id: str | None = None,
) -> dict[str, object]:
    """Check retained proxy status and staleness."""
    sid = scope_id or controller.project.id
    try:
        from splitshot.persistence.library import (
            load_proxy_record,
            match_proxy_path,
            stage_proxy_path,
        )

        record = load_proxy_record(scope_type, sid)
        current_hash = (
            controller._compute_truth_hash()
            if scope_type == "stage"
            else controller._compute_workspace_truth_hash()
        )

        if record is None:
            return {
                "exists": False,
                "stale": True,
                "truth_hash": current_hash,
                "proxy_path": None,
                "last_generated": None,
                "scope_type": scope_type,
                "scope_id": sid,
            }

        stale = record.generated_from_truth_hash != current_hash
        proxy_path = (
            stage_proxy_path(sid, record.generated_from_truth_hash)
            if scope_type == "stage"
            else match_proxy_path(sid, record.generated_from_truth_hash)
        )

        return {
            "exists": True,
            "stale": stale,
            "truth_hash": current_hash,
            "proxy_path": str(proxy_path) if proxy_path else None,
            "last_generated": (record.generated_at.isoformat() if record.generated_at else None),
            "scope_type": scope_type,
            "scope_id": sid,
            "width": record.width,
            "height": record.height,
            "duration_ms": record.duration_ms,
            "file_size_bytes": record.file_size_bytes,
        }
    except Exception:
        return {
            "exists": False,
            "stale": True,
            "truth_hash": "",
            "proxy_path": None,
            "last_generated": None,
            "scope_type": scope_type,
            "scope_id": sid,
        }


def generate_default_render_plan(scope_type: str = "stage") -> dict[str, object]:
    """Generate a minimal default render plan when no output profile is specified."""
    del scope_type
    return {
        "steps": ["source_copy", "proxy_encode"],
        "estimated_duration_ms": 0,
        "output_path": "",
        "dimensions": {"width": 1920, "height": 1080},
        "frame_rate": 30,
        "has_warnings": False,
        "warnings": [],
    }


def proxy_refresh(
    controller: ProjectController,
    scope_type: str = "stage",
    scope_id: str | None = None,
) -> dict[str, object]:
    """Request proxy regeneration."""
    sid = scope_id or controller.project.id

    if scope_type == "stage" and not controller.project.primary_video.path:
        return {
            "status": "no_media",
            "message": "No primary video available for proxy generation.",
            "scope_type": scope_type,
            "scope_id": sid,
        }

    current_hash = (
        controller._compute_truth_hash()
        if scope_type == "stage"
        else controller._compute_workspace_truth_hash()
    )

    try:
        from splitshot.persistence.library import load_proxy_record

        existing = load_proxy_record(scope_type, sid)
        if existing and existing.generated_from_truth_hash == current_hash:
            return {
                "status": "skipped_current",
                "message": "Proxy is already current for this truth hash.",
                "truth_hash": current_hash,
                "scope_type": scope_type,
                "scope_id": sid,
            }
    except Exception:
        pass

    try:
        from splitshot.domain.models import RetainedProxyRecord
        from splitshot.export.pipeline import export_output_profile
        from splitshot.persistence.library import (
            match_proxy_path,
            save_proxy_record,
            stage_proxy_path,
        )

        proxy_path = (
            stage_proxy_path(sid, current_hash)
            if scope_type == "stage"
            else match_proxy_path(sid, current_hash)
        )
        if proxy_path:
            Path(proxy_path).parent.mkdir(parents=True, exist_ok=True)

        record = RetainedProxyRecord(
            scope_type=scope_type,
            scope_id=sid,
            generated_from_truth_hash=current_hash,
            generated_at=datetime.now(timezone.utc),
            codec_profile="h264_aac",
            relative_path=str(proxy_path) if proxy_path else "",
            width=0,
            height=0,
            duration_ms=0,
            file_size_bytes=0,
        )
        save_proxy_record(record)

        video_path = None
        if scope_type == "stage" and controller.project.primary_video.path:
            video_path = Path(controller.project.primary_video.path)
        elif scope_type == "match" and controller.project.primary_video.path:
            video_path = Path(controller.project.primary_video.path)

        if video_path and video_path.exists() and proxy_path:
            render_plan = generate_default_render_plan(scope_type)
            try:
                result = export_output_profile(controller.project, proxy_path, render_plan)
                if result and result.exists():
                    record.width = 0
                    record.height = 0
                    record.duration_ms = 0
                    record.file_size_bytes = result.stat().st_size
                    record.relative_path = str(proxy_path)
                    save_proxy_record(record)
                    return {
                        "status": "rendered",
                        "message": "Proxy rendered successfully.",
                        "truth_hash": current_hash,
                        "proxy_path": str(result),
                        "scope_type": scope_type,
                        "scope_id": sid,
                    }
            except Exception:
                pass
    except Exception:
        pass

    return {
        "status": "scheduled",
        "message": (
            "Proxy refresh scheduled. Render will occur via export pipeline "
            "when media is available."
        ),
        "truth_hash": current_hash,
        "scope_type": scope_type,
        "scope_id": sid,
    }


def proxy_open_target(
    controller: ProjectController,
    scope_type: str = "stage",
    scope_id: str | None = None,
) -> dict[str, object]:
    """Get the path to open a retained proxy for playback."""
    sid = scope_id or controller.project.id
    try:
        from splitshot.persistence.library import (
            load_proxy_record,
            match_proxy_path,
            stage_proxy_path,
        )

        record = load_proxy_record(scope_type, sid)
        if record is None:
            return {
                "success": False,
                "error": "No proxy record found. Generate a proxy first.",
                "scope_type": scope_type,
                "scope_id": sid,
            }

        proxy_path = (
            stage_proxy_path(sid, record.generated_from_truth_hash)
            if scope_type == "stage"
            else match_proxy_path(sid, record.generated_from_truth_hash)
        )
        proxy_exists = Path(proxy_path).exists() if proxy_path else False

        return {
            "success": proxy_exists,
            "proxy_path": str(proxy_path) if proxy_path else None,
            "error": None if proxy_exists else "Proxy file not found on disk. Try regenerating.",
            "stale": record.generated_from_truth_hash
            != (
                controller._compute_truth_hash()
                if scope_type == "stage"
                else controller._compute_workspace_truth_hash()
            ),
            "scope_type": scope_type,
            "scope_id": sid,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "scope_type": scope_type,
            "scope_id": sid,
        }


def library_backup_create() -> dict[str, object]:
    """Create a persisted backup of the library."""
    stages: list[dict[str, object]] = []
    matches: list[dict[str, object]] = []
    try:
        from splitshot.persistence.library import (
            read_match_metrics,
            read_match_records,
            read_stage_metrics,
            read_stage_records,
        )

        stages = read_stage_records() or read_stage_metrics() or []
        matches = read_match_records() or read_match_metrics() or []
    except Exception:
        pass

    manifest = {
        "backup_id": uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "total_stages": len(stages),
        "total_matches": len(matches),
        "stage_records": list(stages),
        "match_records": list(matches),
    }

    try:
        backup_dir = Path.home() / ".splitshot" / "library" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = backup_dir / f"backup_{timestamp}.json"
        backup_path.write_text(json.dumps(manifest, indent=2))
        backup_path_str = str(backup_path)
    except Exception:
        backup_path_str = ""

    return {
        "manifest": manifest,
        "backup_path": backup_path_str,
        "total_stages": len(stages),
        "total_matches": len(matches),
    }


def library_backup_restore(manifest: dict[str, object]) -> dict[str, object]:
    """Restore library from a backup manifest."""
    if not manifest:
        return {
            "error": "No backup manifest provided",
            "stages_restored": 0,
            "matches_restored": 0,
        }

    schema_version = manifest.get("schema_version", 0)
    if schema_version != 1:
        return {
            "error": f"Unsupported schema version: {schema_version}",
            "stages_restored": 0,
            "matches_restored": 0,
        }

    restored_stages = 0
    restored_matches = 0
    errors: list[dict[str, object]] = []

    def parse_datetime(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    def normalize_stage_index_row(stage_data: dict[str, object]) -> dict[str, object]:
        metric_summary = stage_data.get("metric_summary")
        summary = metric_summary if isinstance(metric_summary, dict) else {}
        row = dict(stage_data)
        row["metric_summary"] = summary
        if row.get("score") in {None, ""}:
            row["score"] = summary.get(
                "score",
                summary.get("score_total", summary.get("hit_factor")),
            )
        return row

    def normalize_match_index_row(match_data: dict[str, object]) -> dict[str, object]:
        aggregate_summary = match_data.get("aggregate_metric_summary")
        summary = aggregate_summary if isinstance(aggregate_summary, dict) else {}
        row = dict(match_data)
        row["aggregate_metric_summary"] = summary
        if row.get("stage_count") in {None, ""}:
            row["stage_count"] = summary.get(
                "stage_count",
                len(row.get("stage_ids") or []),
            )
        return row

    for stage_data in manifest.get("stage_records", []):
        try:
            if not isinstance(stage_data, dict):
                raise ValueError("Stage record must be an object")

            from splitshot.domain.models import LibraryStageRecord
            from splitshot.persistence.library import append_stage_metric, save_stage_record

            has_full_stage_payload = any(
                key in stage_data
                for key in (
                    "metric_summary",
                    "editor_target",
                    "notes",
                    "tags",
                    "output_profile_refs",
                )
            )
            if has_full_stage_payload and stage_data.get("library_record_id"):
                save_stage_record(
                    LibraryStageRecord(
                        library_record_id=str(stage_data.get("library_record_id") or ""),
                        stage_id=str(stage_data.get("stage_id") or ""),
                        match_id=(
                            None
                            if stage_data.get("match_id") in {None, ""}
                            else str(stage_data.get("match_id"))
                        ),
                        display_name=str(stage_data.get("display_name") or ""),
                        event_date=parse_datetime(stage_data.get("event_date")),
                        discipline=str(stage_data.get("discipline") or ""),
                        competitor_name=str(stage_data.get("competitor_name") or ""),
                        metric_summary=dict(stage_data.get("metric_summary") or {}),
                        output_profile_refs=list(stage_data.get("output_profile_refs") or []),
                        active_retained_proxy=(
                            None
                            if stage_data.get("active_retained_proxy") in {None, ""}
                            else str(stage_data.get("active_retained_proxy"))
                        ),
                        editor_target=dict(stage_data.get("editor_target") or {}),
                        truth_hash=str(stage_data.get("truth_hash") or ""),
                        tags=[str(tag) for tag in (stage_data.get("tags") or [])],
                        notes=str(stage_data.get("notes") or ""),
                    )
                )

            append_stage_metric(normalize_stage_index_row(stage_data))
            restored_stages += 1
        except Exception as exc:
            errors.append(
                {
                    "kind": "stage",
                    "library_record_id": (
                        stage_data.get("library_record_id")
                        if isinstance(stage_data, dict)
                        else None
                    ),
                    "error": str(exc),
                }
            )

    for match_data in manifest.get("match_records", []):
        try:
            if not isinstance(match_data, dict):
                raise ValueError("Match record must be an object")

            from splitshot.domain.models import LibraryMatchRecord
            from splitshot.persistence.library import append_match_metric, save_match_record

            has_full_match_payload = any(
                key in match_data
                for key in (
                    "aggregate_metric_summary",
                    "editor_target",
                    "notes",
                    "tags",
                    "output_profile_refs",
                )
            )
            if has_full_match_payload and match_data.get("library_record_id"):
                save_match_record(
                    LibraryMatchRecord(
                        library_record_id=str(match_data.get("library_record_id") or ""),
                        match_id=str(match_data.get("match_id") or ""),
                        display_name=str(match_data.get("display_name") or ""),
                        event_date=parse_datetime(match_data.get("event_date")),
                        discipline=str(match_data.get("discipline") or ""),
                        stage_ids=[
                            str(stage_id) for stage_id in (match_data.get("stage_ids") or [])
                        ],
                        aggregate_metric_summary=dict(
                            match_data.get("aggregate_metric_summary") or {}
                        ),
                        output_profile_refs=list(match_data.get("output_profile_refs") or []),
                        active_retained_proxy=(
                            None
                            if match_data.get("active_retained_proxy") in {None, ""}
                            else str(match_data.get("active_retained_proxy"))
                        ),
                        editor_target=dict(match_data.get("editor_target") or {}),
                        truth_hash=str(match_data.get("truth_hash") or ""),
                        tags=[str(tag) for tag in (match_data.get("tags") or [])],
                        notes=str(match_data.get("notes") or ""),
                    )
                )

            append_match_metric(normalize_match_index_row(match_data))
            restored_matches += 1
        except Exception as exc:
            errors.append(
                {
                    "kind": "match",
                    "library_record_id": (
                        match_data.get("library_record_id")
                        if isinstance(match_data, dict)
                        else None
                    ),
                    "error": str(exc),
                }
            )

    return {
        "restored": len(errors) == 0,
        "stages_restored": restored_stages,
        "matches_restored": restored_matches,
        "errors": errors,
    }
