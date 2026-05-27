from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from splitshot.domain.models import Project
from splitshot.persistence import library as library_module
from splitshot.persistence.library import (
    build_library_reopen_targets,
    build_library_summary,
    list_recent_library_activity,
)
from splitshot.persistence.projects import list_recent_project_activity, list_recent_projects, save_project


UTC = timezone.utc


def _write_project_bundle(
    projects_root: Path,
    bundle_name: str,
    project_name: str,
    *,
    updated_at: datetime,
    last_opened: str | None = None,
    strip_timestamps: bool = False,
) -> Path:
    project = Project(name=project_name)
    project.updated_at = updated_at
    bundle = save_project(project, projects_root / bundle_name)
    metadata_path = bundle / "project.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    if last_opened is not None:
        payload["last_opened"] = last_opened
    if strip_timestamps:
        for key in ("last_opened", "updated_at", "modified_at", "created_at"):
            payload.pop(key, None)
    metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return bundle


def test_list_recent_project_activity_uses_persisted_dates_and_normalizes_entries(
    tmp_path: Path,
) -> None:
    projects_root = tmp_path / "projects"
    _write_project_bundle(
        projects_root,
        "updated-first.ssproj",
        "Updated First",
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    opened_later = _write_project_bundle(
        projects_root,
        "opened-later.ssproj",
        "Opened Later",
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_opened="2026-01-05T12:00:00+00:00",
    )
    broken_bundle = projects_root / "broken.ssproj"
    broken_bundle.mkdir(parents=True, exist_ok=True)
    (broken_bundle / "project.json").write_text("{broken json", encoding="utf-8")

    recent = list_recent_project_activity(limit=5, root=projects_root)

    assert [entry["name"] for entry in recent] == ["Opened Later", "Updated First"]
    assert recent[0]["date"] == "2026-01-05T12:00:00+00:00"
    assert recent[0]["last_opened"] == "2026-01-05T12:00:00+00:00"
    assert recent[0]["type"] == "stage"
    assert recent[0]["surface"] == "single"
    assert recent[0]["path"] == str(opened_later.resolve(strict=False))

    compatibility_rows = list_recent_projects(limit=1, root=projects_root)
    assert len(compatibility_rows) == 1
    assert compatibility_rows[0]["name"] == "Opened Later"
    assert compatibility_rows[0]["last_opened"] == "2026-01-05T12:00:00+00:00"


def test_list_recent_project_activity_falls_back_to_bundle_mtime_when_metadata_dates_missing(
    tmp_path: Path,
) -> None:
    projects_root = tmp_path / "projects"
    timeless_bundle = _write_project_bundle(
        projects_root,
        "timeless.ssproj",
        "Timeless",
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        strip_timestamps=True,
    )
    fallback_timestamp = datetime(2026, 2, 7, 15, 30, tzinfo=UTC).timestamp()
    metadata_path = timeless_bundle / "project.json"
    metadata_path.touch()
    import os

    os.utime(timeless_bundle, (fallback_timestamp, fallback_timestamp))

    recent = list_recent_project_activity(limit=1, root=projects_root)

    assert len(recent) == 1
    assert recent[0]["name"] == "Timeless"
    assert recent[0]["last_opened"] == datetime.fromtimestamp(
        fallback_timestamp, UTC
    ).isoformat()


def test_build_library_summary_prefers_saved_records_and_reports_latest_event(
    monkeypatch,
) -> None:
    stage_records = [
        {
            "library_record_id": "stage-older",
            "display_name": "Older Stage",
            "event_date": "2026-02-01T00:00:00+00:00",
        },
        {
            "library_record_id": "stage-newer",
            "display_name": "Newer Stage",
            "event_date": "2026-02-03T00:00:00+00:00",
        },
    ]
    match_records = [
        {
            "library_record_id": "match-newest",
            "display_name": "Newest Match",
            "event_date": "2026-02-05T00:00:00+00:00",
        }
    ]

    monkeypatch.setattr(library_module, "read_stage_records", lambda: list(stage_records))
    monkeypatch.setattr(
        library_module,
        "read_stage_metrics",
        lambda: [{"library_record_id": "ignored-stage-metric"}],
    )
    monkeypatch.setattr(library_module, "read_match_records", lambda: list(match_records))
    monkeypatch.setattr(
        library_module,
        "read_match_metrics",
        lambda: [{"library_record_id": "ignored-match-metric"}],
    )

    summary = build_library_summary()

    assert summary == {
        "stage_count": 2,
        "match_count": 1,
        "last_updated": "2026-02-05T00:00:00+00:00",
        "filters_available": ["discipline", "competitor", "match_id", "stage_id", "sort_by"],
        "selection": None,
    }


def test_list_recent_library_activity_normalizes_stage_and_match_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        library_module,
        "read_stage_records",
        lambda: [
            {
                "library_record_id": "stage-record",
                "stage_id": "stage-1",
                "display_name": "Stage Record",
                "event_date": "2026-02-01T00:00:00+00:00",
                "discipline": "uspsa_minor",
                "editor_target": {
                    "project_path": "/tmp/stage-record",
                    "workspace_path": "/tmp/workspace-a",
                    "stage_id": "stage-1",
                },
            }
        ],
    )
    monkeypatch.setattr(library_module, "read_stage_metrics", lambda: [])
    monkeypatch.setattr(library_module, "read_match_records", lambda: [])
    monkeypatch.setattr(
        library_module,
        "read_match_metrics",
        lambda: [
            {
                "library_record_id": "match-metric",
                "match_id": "match-1",
                "display_name": "Match Metric",
                "event_date": "2026-02-04T00:00:00+00:00",
                "discipline": "idpa_time_plus",
                "editor_target": {
                    "workspace_path": "/tmp/match-metric",
                    "match_id": "match-1",
                },
            }
        ],
    )

    recent = list_recent_library_activity(limit=5, stage_limit=5, match_limit=5)

    assert [entry["library_record_id"] for entry in recent] == ["match-metric", "stage-record"]
    assert recent[0]["type"] == "match"
    assert recent[0]["surface"] == "multi"
    assert recent[0]["path"] == "/tmp/match-metric"
    assert recent[1]["type"] == "stage"
    assert recent[1]["surface"] == "single"
    assert recent[1]["path"] == "/tmp/stage-record"
    assert recent[1]["workspace_path"] == "/tmp/workspace-a"


def test_build_library_reopen_targets_uses_metrics_fallback_contract(monkeypatch) -> None:
    monkeypatch.setattr(library_module, "read_stage_records", lambda: [])
    monkeypatch.setattr(library_module, "read_match_records", lambda: [])
    monkeypatch.setattr(
        library_module,
        "read_stage_metrics",
        lambda: [
            {
                "library_record_id": "fallback-stage",
                "stage_id": "stage-1",
                "display_name": "Fallback Stage",
                "event_date": "2026-02-05T00:00:00+00:00",
                "editor_target": {
                    "project_path": "/tmp/fallback-stage",
                    "stage_id": "stage-1",
                },
            }
        ],
    )
    monkeypatch.setattr(
        library_module,
        "read_match_metrics",
        lambda: [
            {
                "library_record_id": "fallback-match",
                "match_id": "match-1",
                "display_name": "Fallback Match",
                "event_date": "2026-02-06T00:00:00+00:00",
                "editor_target": {
                    "workspace_path": "/tmp/fallback-match",
                    "match_id": "match-1",
                },
            }
        ],
    )

    targets = build_library_reopen_targets(limit=4)

    stage_target = next(target for target in targets if target["library_record_id"] == "fallback-stage")
    match_target = next(target for target in targets if target["library_record_id"] == "fallback-match")

    assert stage_target["editor_target"] == {
        "project_path": "/tmp/fallback-stage",
        "stage_id": "stage-1",
        "type": "single",
        "workspace_path": "",
    }
    assert match_target["editor_target"] == {
        "workspace_path": "/tmp/fallback-match",
        "match_id": "match-1",
        "type": "multi",
    }