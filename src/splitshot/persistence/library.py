from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

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
    kwargs: dict = {}
    for field_name, field_def in cls.__dataclass_fields__.items():
        value = data.get(field_name, field_def.default)
        if field_def.type in (datetime, datetime | None) and isinstance(value, str):
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
    """Update tags on a library stage record."""
    record = load_stage_record(record_id)
    if record:
        record.tags = tags
        save_stage_record(record)


def update_record_notes(record_id: str, notes: str) -> None:
    """Update notes on a library stage record."""
    record = load_stage_record(record_id)
    if record:
        record.notes = notes
        save_stage_record(record)


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
        "scale='min(1280,iw)':min'(720,ih)':force_original_aspect_ratio=decrease",
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
    records = read_stage_metrics()

    if discipline:
        records = [r for r in records if r.get("discipline") == discipline]

    if not records:
        return {"error": "No records found", "records": 0}

    values = []
    for r in records:
        summary = r.get("metric_summary", {})
        val = summary.get(metric_key)
        if val is not None:
            try:
                values.append((r, float(val)))
            except (ValueError, TypeError):
                pass

    if not values:
        return {"error": f"No valid {metric_key} values found"}

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
                "record_id": record.get("stage_id", ""),
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
        "personal_bests": personal_bests,
        "outliers": outliers,
        "trend_direction": trend,
    }
