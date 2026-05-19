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
