from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import get_args, get_type_hints

from splitshot.domain.models import (
    LibraryStageRecord,
    LibraryMatchRecord,
    LibraryOutputRecord,
    RetainedProxyRecord,
)

UTC = timezone.utc


def _library_root() -> Path:
    env_root = os.environ.get("SPLITSHOT_LIBRARY_ROOT")
    if env_root:
        return Path(env_root)
    return Path.home() / ".splitshot" / "library"


def library_root() -> Path:
    root = _library_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_library_structure() -> Path:
    root = library_root()
    (root / "records" / "stages").mkdir(parents=True, exist_ok=True)
    (root / "records" / "matches").mkdir(parents=True, exist_ok=True)
    (root / "records" / "outputs").mkdir(parents=True, exist_ok=True)
    (root / "index").mkdir(parents=True, exist_ok=True)
    (root / "proxies" / "stages").mkdir(parents=True, exist_ok=True)
    (root / "proxies" / "matches").mkdir(parents=True, exist_ok=True)
    return root


def stage_record_path(library_record_id: str) -> Path:
    return library_root() / "records" / "stages" / f"{library_record_id}.json"


def match_record_path(library_record_id: str) -> Path:
    return library_root() / "records" / "matches" / f"{library_record_id}.json"


def output_record_path(library_record_id: str) -> Path:
    return library_root() / "records" / "outputs" / f"{library_record_id}.json"


def stage_proxy_path(stage_id: str, truth_hash: str) -> Path:
    return library_root() / "proxies" / "stages" / stage_id / f"{truth_hash}.mp4"


def match_proxy_path(match_id: str, truth_hash: str) -> Path:
    return library_root() / "proxies" / "matches" / match_id / f"{truth_hash}.mp4"


def stage_metrics_path() -> Path:
    return library_root() / "index" / "stage_metrics.jsonl"


def match_metrics_path() -> Path:
    return library_root() / "index" / "match_metrics.jsonl"


def search_catalog_path() -> Path:
    return library_root() / "index" / "search_catalog.json"


def _record_to_dict(record: object) -> dict:
    result: dict = {}
    for field_name in record.__dataclass_fields__:
        value = getattr(record, field_name)
        if isinstance(value, datetime):
            result[field_name] = value.isoformat()
        else:
            result[field_name] = value
    return result


def _dict_to_record(cls: type, data: dict) -> object:
    type_hints = get_type_hints(cls)
    kwargs: dict = {}
    for field_name, field_def in cls.__dataclass_fields__.items():
        value = data.get(field_name, field_def.default)
        field_type = type_hints.get(field_name)
        if isinstance(value, str) and (
            field_type is datetime or datetime in get_args(field_type)
        ):
            value = datetime.fromisoformat(value)
        kwargs[field_name] = value
    return cls(**kwargs)


def save_stage_record(record: LibraryStageRecord) -> None:
    path = stage_record_path(record.library_record_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_record_to_dict(record), indent=2))


def load_stage_record(library_record_id: str) -> LibraryStageRecord | None:
    path = stage_record_path(library_record_id)
    if not path.is_file():
        return None
    return _dict_to_record(LibraryStageRecord, json.loads(path.read_text()))


def save_match_record(record: LibraryMatchRecord) -> None:
    path = match_record_path(record.library_record_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_record_to_dict(record), indent=2))


def load_match_record(library_record_id: str) -> LibraryMatchRecord | None:
    path = match_record_path(library_record_id)
    if not path.is_file():
        return None
    return _dict_to_record(LibraryMatchRecord, json.loads(path.read_text()))


def save_output_record(record: LibraryOutputRecord) -> None:
    path = output_record_path(record.library_record_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_record_to_dict(record), indent=2))


def load_output_record(library_record_id: str) -> LibraryOutputRecord | None:
    path = output_record_path(library_record_id)
    if not path.is_file():
        return None
    return _dict_to_record(LibraryOutputRecord, json.loads(path.read_text()))


def append_stage_metric(metric_row: dict) -> None:
    path = stage_metrics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(metric_row) + "\n")


def append_match_metric(metric_row: dict) -> None:
    path = match_metrics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(metric_row) + "\n")


def read_stage_metrics() -> list[dict]:
    path = stage_metrics_path()
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text().strip().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def read_match_metrics() -> list[dict]:
    path = match_metrics_path()
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text().strip().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _read_record_directory(record_dir: Path) -> list[dict]:
    if not record_dir.is_dir():
        return []
    rows: list[dict] = []
    for record_path in sorted(record_dir.glob("*.json")):
        try:
            rows.append(json.loads(record_path.read_text()))
        except Exception:
            continue
    return rows


def read_stage_records() -> list[dict]:
    return _read_record_directory(library_root() / "records" / "stages")


def read_match_records() -> list[dict]:
    return _read_record_directory(library_root() / "records" / "matches")


_LIBRARY_FILTERS_AVAILABLE = ["discipline", "competitor", "match_id", "stage_id", "sort_by"]


def _parse_record_datetime(value: object) -> datetime | None:
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


def _record_timestamp(row: dict) -> float:
    parsed = _parse_record_datetime(row.get("event_date"))
    if parsed is None:
        return 0.0
    return parsed.timestamp()


def _record_event_date(row: dict) -> str:
    parsed = _parse_record_datetime(row.get("event_date"))
    if parsed is not None:
        return parsed.isoformat()
    raw_value = row.get("event_date")
    return "" if raw_value in {None, ""} else str(raw_value)


def _support_rows(records: list[dict], metrics: list[dict]) -> list[dict]:
    return list(records or metrics or [])


def _limit_rows(rows: list[dict], limit: int | None) -> list[dict]:
    if limit is None:
        return list(rows)
    return list(rows[: max(0, int(limit))])


def _sort_rows_by_recency(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda row: (
            _record_timestamp(row),
            str(row.get("library_record_id") or row.get("stage_id") or row.get("match_id") or ""),
        ),
        reverse=True,
    )


def _stage_editor_target(row: dict) -> dict[str, str]:
    editor_target = row.get("editor_target")
    normalized_target = dict(editor_target) if isinstance(editor_target, dict) else {}
    return {
        "project_path": str(
            normalized_target.get("project_path") or row.get("project_path") or ""
        ),
        "stage_id": str(normalized_target.get("stage_id") or row.get("stage_id") or ""),
        "type": "single",
        "workspace_path": str(
            normalized_target.get("workspace_path") or row.get("workspace_path") or ""
        ),
    }


def _match_editor_target(row: dict) -> dict[str, str]:
    editor_target = row.get("editor_target")
    normalized_target = dict(editor_target) if isinstance(editor_target, dict) else {}
    return {
        "workspace_path": str(
            normalized_target.get("workspace_path") or row.get("workspace_path") or ""
        ),
        "match_id": str(normalized_target.get("match_id") or row.get("match_id") or ""),
        "type": "multi",
    }


def _normalize_stage_activity_row(row: dict) -> dict[str, object]:
    editor_target = _stage_editor_target(row)
    return {
        "library_record_id": str(row.get("library_record_id") or ""),
        "name": str(row.get("display_name") or "Untitled Stage"),
        "path": editor_target["project_path"],
        "date": _record_event_date(row),
        "type": "stage",
        "surface": "single",
        "stage_id": editor_target["stage_id"],
        "match_id": None if row.get("match_id") in {None, ""} else str(row.get("match_id")),
        "discipline": str(row.get("discipline") or ""),
        "project_path": editor_target["project_path"],
        "workspace_path": editor_target["workspace_path"],
        "editor_target": editor_target,
        "timestamp": _record_timestamp(row),
    }


def _normalize_match_activity_row(row: dict) -> dict[str, object]:
    editor_target = _match_editor_target(row)
    return {
        "library_record_id": str(row.get("library_record_id") or ""),
        "name": str(row.get("display_name") or "Untitled Match"),
        "path": editor_target["workspace_path"],
        "date": _record_event_date(row),
        "type": "match",
        "surface": "multi",
        "match_id": editor_target["match_id"],
        "discipline": str(row.get("discipline") or ""),
        "workspace_path": editor_target["workspace_path"],
        "editor_target": editor_target,
        "timestamp": _record_timestamp(row),
    }


def _normalized_library_activity_rows(
    *,
    stage_limit: int | None = None,
    match_limit: int | None = None,
) -> list[dict[str, object]]:
    stage_rows = _support_rows(read_stage_records(), read_stage_metrics())
    match_rows = _support_rows(read_match_records(), read_match_metrics())
    normalized_rows = [
        *[
            _normalize_stage_activity_row(row)
            for row in _limit_rows(_sort_rows_by_recency(stage_rows), stage_limit)
        ],
        *[
            _normalize_match_activity_row(row)
            for row in _limit_rows(_sort_rows_by_recency(match_rows), match_limit)
        ],
    ]
    normalized_rows.sort(
        key=lambda row: (
            float(row.get("timestamp") or 0.0),
            str(row.get("library_record_id") or ""),
        ),
        reverse=True,
    )
    return normalized_rows


def build_library_summary() -> dict[str, object]:
    """Return summary-only library support data for shared backend state."""
    stage_rows = _support_rows(read_stage_records(), read_stage_metrics())
    match_rows = _support_rows(read_match_records(), read_match_metrics())
    latest_row = max(
        [*stage_rows, *match_rows],
        key=_record_timestamp,
        default=None,
    )
    last_updated = None if latest_row is None else (_record_event_date(latest_row) or None)
    return {
        "stage_count": len(stage_rows),
        "match_count": len(match_rows),
        "last_updated": last_updated,
        "filters_available": list(_LIBRARY_FILTERS_AVAILABLE),
        "selection": None,
    }


def list_recent_library_activity(
    limit: int = 8,
    *,
    stage_limit: int = 5,
    match_limit: int = 3,
) -> list[dict[str, object]]:
    """Return normalized recent library items for landing/shared backend support."""
    recent_rows = _normalized_library_activity_rows(
        stage_limit=stage_limit,
        match_limit=match_limit,
    )
    return recent_rows[: max(0, int(limit))]


def build_library_reopen_targets(limit: int = 10) -> list[dict[str, object]]:
    """Return deterministic library reopen targets keyed by stable record ids."""
    targets: list[dict[str, object]] = []
    for row in _normalized_library_activity_rows(stage_limit=limit, match_limit=limit)[
        : max(0, int(limit))
    ]:
        editor_target = row.get("editor_target")
        normalized_target = dict(editor_target) if isinstance(editor_target, dict) else {}
        targets.append(
            {
                "library_record_id": str(row.get("library_record_id") or ""),
                "name": str(row.get("name") or ""),
                "type": str(row.get("type") or ""),
                "surface": str(row.get("surface") or ""),
                "date": str(row.get("date") or ""),
                "editor_target": normalized_target,
            }
        )
    return targets


def save_search_catalog(catalog_data: dict) -> None:
    path = search_catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog_data, indent=2))


def load_search_catalog() -> dict:
    path = search_catalog_path()
    if not path.is_file():
        return {}
    return json.loads(path.read_text())


def _proxy_metadata_path(scope_type: str, scope_id: str) -> Path:
    return library_root() / "proxies" / scope_type / scope_id / "metadata.json"


def save_proxy_record(record: RetainedProxyRecord) -> None:
    path = _proxy_metadata_path(record.scope_type, record.scope_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_record_to_dict(record), indent=2))


def load_proxy_record(scope_type: str, scope_id: str) -> RetainedProxyRecord | None:
    path = _proxy_metadata_path(scope_type, scope_id)
    if not path.is_file():
        return None
    return _dict_to_record(RetainedProxyRecord, json.loads(path.read_text()))


def update_record_tags(record_id: str, tags: list[str]) -> None:
    """Update tags on a library stage or match record."""
    record = load_stage_record(record_id)
    if record:
        record.tags = tags
        save_stage_record(record)
        return
    match_record = load_match_record(record_id)
    if match_record:
        match_record.tags = tags
        save_match_record(match_record)


def update_record_notes(record_id: str, notes: str) -> None:
    """Update notes on a library stage or match record."""
    record = load_stage_record(record_id)
    if record:
        record.notes = notes
        save_stage_record(record)
        return
    match_record = load_match_record(record_id)
    if match_record:
        match_record.notes = notes
        save_match_record(match_record)


def _library_archive_dir() -> Path:
    return library_root() / "archives"


def generate_archive(stage_id: str, output_path: str | None = None) -> dict:
    """Generate a compressed video archive for a library stage record.

    Uses ffmpeg to create a compressed H.264 archive suitable for long-term storage.
    Target: 480p-720p, 2-4 Mbps, with overlay if available.
    """
    import subprocess

    record = load_stage_record(stage_id)
    if not record:
        for record_data in read_stage_records():
            if record_data.get("stage_id") != stage_id:
                continue
            record = _dict_to_record(LibraryStageRecord, record_data)
            break
    if not record:
        return {"error": f"Stage record not found: {stage_id}"}

    editor_target = getattr(record, "editor_target", {}) or {}
    source_project_path = editor_target.get("project_path", "")

    if not source_project_path:
        return {"error": "No source project path in record"}

    project_dir = Path(source_project_path)
    primary_video = None
    project_file = project_dir / "project.json"

    if project_file.exists():
        data = json.loads(project_file.read_text())
        video_path = data.get("primary_video", {}).get("path", "")
        if video_path:
            primary_video = project_dir / video_path

    if not primary_video or not primary_video.exists():
        return {"error": "Source video not found"}

    archive_dir = _library_archive_dir()
    archive_dir.mkdir(parents=True, exist_ok=True)

    if not output_path:
        archive_filename = f"{stage_id}_archive.mp4"
        output_path = str(archive_dir / archive_filename)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(primary_video),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-vf",
        "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return {"error": f"ffmpeg failed: {result.stderr[:500]}"}
    except subprocess.TimeoutExpired:
        return {"error": "Archive generation timed out"}
    except FileNotFoundError:
        return {"error": "ffmpeg not found on PATH"}

    output_file = Path(output_path)
    file_size = output_file.stat().st_size if output_file.exists() else 0

    return {
        "archive_id": stage_id,
        "path": output_path,
        "file_size_bytes": file_size,
        "status": "complete",
    }


def compute_analytics(discipline: str | None = None, metric_key: str = "score") -> dict:
    """Compute analytics from library stage records.

    Returns trend data, personal bests, outliers, and statistics.
    """
    records = read_stage_records() or read_stage_metrics()

    if discipline:
        records = [r for r in records if r.get("discipline") == discipline]

    if not records:
        return {"error": "No records found", "records": 0}

    def metric_value(record: dict, key: str) -> float | None:
        metric_summary = record.get("metric_summary")
        summary = metric_summary if isinstance(metric_summary, dict) else {}
        candidate_keys = [key]
        if key == "score":
            candidate_keys.extend(["score_total", "hit_factor"])
        for candidate_key in candidate_keys:
            for container in (summary, record):
                value = container.get(candidate_key)
                if value in {None, ""}:
                    continue
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
        return None

    values = []
    for r in records:
        val = metric_value(r, metric_key)
        if val is not None:
            values.append((r, val))

    trend_points = [
        {
            "date": record.get("event_date", ""),
            "score": score,
            "record_id": record.get("library_record_id") or record.get("stage_id", ""),
            "name": record.get("display_name", ""),
        }
        for record, score in sorted(
            values,
            key=lambda item: str(item[0].get("event_date") or ""),
        )
        if record.get("event_date")
    ]

    discipline_counts: dict[str, int] = {}
    for record in records:
        key = str(record.get("discipline") or "other")
        discipline_counts[key] = discipline_counts.get(key, 0) + 1
    discipline_breakdown = [
        {"discipline": key, "count": count}
        for key, count in sorted(
            discipline_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    if not values:
        return {
            "error": f"No valid {metric_key} values found",
            "records": len(records),
            "trend_points": trend_points,
            "discipline_breakdown": discipline_breakdown,
        }

    scores = [v[1] for v in values]
    scores.sort()

    n = len(scores)
    mean_val = sum(scores) / n
    median_val = scores[n // 2]

    variance = sum((x - mean_val) ** 2 for x in scores) / n
    std_dev = variance**0.5

    sorted_records = sorted(values, key=lambda x: x[1], reverse=True)
    personal_bests = []
    for record, score in sorted_records[:5]:
        personal_bests.append(
            {
                "name": record.get("display_name", ""),
                "date": record.get("event_date", ""),
                "discipline": record.get("discipline", ""),
                "score": score,
                "record_id": record.get("library_record_id") or record.get("stage_id", ""),
            }
        )

    q1_idx = n // 4
    q3_idx = (3 * n) // 4
    q1 = scores[q1_idx] if q1_idx < n else scores[0]
    q3 = scores[q3_idx] if q3_idx < n else scores[-1]
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outliers = []
    for record, score in values:
        if score < lower_bound or score > upper_bound:
            outliers.append(
                {
                    "name": record.get("display_name", ""),
                    "date": record.get("event_date", ""),
                    "score": score,
                    "direction": "low" if score < lower_bound else "high",
                }
            )

    if n >= 3:
        recent_avg = sum(scores[-3:]) / 3
        older_avg = sum(scores[:3]) / 3
        if recent_avg > older_avg * 1.05:
            trend = "improving"
        elif recent_avg < older_avg * 0.95:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    return {
        "metric_key": metric_key,
        "discipline": discipline,
        "total_records": n,
        "statistics": {
            "mean": round(mean_val, 2),
            "median": round(median_val, 2),
            "std_dev": round(std_dev, 2),
            "min": round(scores[0], 2),
            "max": round(scores[-1], 2),
        },
        "trend_points": trend_points,
        "discipline_breakdown": discipline_breakdown,
        "personal_bests": personal_bests,
        "outliers": outliers,
        "trend_direction": trend,
    }
