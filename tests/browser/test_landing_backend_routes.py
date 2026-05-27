from __future__ import annotations

import json
from pathlib import Path
import urllib.request

from splitshot.browser.server import BrowserControlServer

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "app.js"
SERVER_PY = REPO_ROOT / "src" / "splitshot" / "browser" / "server.py"


def _post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _recent_entry(
    name: str,
    *,
    path: str,
    date: str,
    item_type: str,
    surface: str,
) -> dict[str, str]:
    return {
        "name": name,
        "path": path,
        "date": date,
        "type": item_type,
        "surface": surface,
    }


def test_landing_recent_route_registered() -> None:
    """Verify /api/landing/recent route exists in server."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/landing/recent"' in source
    assert "_handle_landing_recent" in source


def test_landing_recent_handler_returns_recent_structure() -> None:
    """Verify the handler returns the expected response shape."""
    # Check controller returns expected structure
    from splitshot.ui.controller import ProjectController

    c = ProjectController()
    result = c.landing_recent()
    assert isinstance(result, dict)
    assert "recent" in result
    assert isinstance(result["recent"], list)


def test_landing_recent_filters_non_stage_entries_before_15_item_cap(
    monkeypatch,
) -> None:
    """Newer non-stage recents should not crowd out stage rows before truncation."""
    import splitshot.ui.services.shared_backend as shared_backend_service

    stage_entries = [
        _recent_entry(
            f"Stage {index:02d}",
            path=f"/tmp/stage-{index:02d}",
            date=f"2026-05-26T10:{index:02d}:00+00:00",
            item_type="stage",
            surface="single",
        )
        for index in range(15)
    ]
    workspace_match_entries = [
        _recent_entry(
            f"Match {index:02d}",
            path=f"/tmp/match-{index:02d}",
            date=f"2026-05-26T11:{index:02d}:00+00:00",
            item_type="match",
            surface="multi",
        )
        for index in range(12)
    ]
    library_match_entries = [
        _recent_entry(
            f"Library Match {index:02d}",
            path=f"/tmp/library-match-{index:02d}",
            date=f"2026-05-26T12:{index:02d}:00+00:00",
            item_type="match",
            surface="multi",
        )
        for index in range(8)
    ]

    monkeypatch.setattr(
        shared_backend_service,
        "list_recent_project_activity",
        lambda limit=20: stage_entries[:10],
    )
    monkeypatch.setattr(
        shared_backend_service,
        "_scan_recent_workspaces",
        lambda limit=20: workspace_match_entries,
    )
    monkeypatch.setattr(
        shared_backend_service,
        "list_recent_library_activity",
        lambda limit=8, stage_limit=5, match_limit=3: [
            *stage_entries[10:],
            *library_match_entries,
        ],
    )

    result = shared_backend_service.landing_recent()

    assert result == {
        "recent": [
            _recent_entry(
                f"Stage {index:02d}",
                path=f"/tmp/stage-{index:02d}",
                date=f"2026-05-26T10:{index:02d}:00+00:00",
                item_type="stage",
                surface="single",
            )
            for index in range(14, -1, -1)
        ]
    }


def test_landing_recent_controller_delegates_to_shared_backend_service(monkeypatch) -> None:
    """Landing recent should delegate through the shared backend service seam."""
    import splitshot.ui.services.shared_backend as shared_backend_service
    from splitshot.ui.controller import ProjectController

    controller = ProjectController()
    expected = {"recent": [{"name": "Delegated Landing Item"}]}
    calls: list[ProjectController] = []

    def fake_landing_recent(passed_controller: ProjectController) -> dict[str, object]:
        calls.append(passed_controller)
        return expected

    monkeypatch.setattr(shared_backend_service, "landing_recent", fake_landing_recent)

    assert controller.landing_recent() == expected
    assert calls == [controller]


def test_landing_recent_route_delegates_to_controller_backend_owner(monkeypatch) -> None:
    """Verify the public landing route delegates to ProjectController.landing_recent."""
    from splitshot.ui.controller import ProjectController

    expected = {
        "recent": [
            {
                "name": "Recent Stage",
                "path": "/tmp/recent-stage",
                "date": "2026-05-26T12:00:00+00:00",
                "type": "stage",
                "surface": "single",
            }
        ]
    }
    calls: list[str] = []

    def fake_landing_recent(self: ProjectController) -> dict[str, object]:
        calls.append("landing_recent")
        return expected

    monkeypatch.setattr(ProjectController, "landing_recent", fake_landing_recent)

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        payload = _post_json(f"{server.url}api/landing/recent", {})
    finally:
        server.shutdown()

    assert calls == ["landing_recent"]
    assert payload == expected


def test_workspace_apply_from_first_route_registered() -> None:
    """Verify /api/workspace/apply-from-first route exists."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/workspace/apply-from-first"' in source
    assert "_handle_workspace_apply_from_first" in source


def test_workspace_apply_from_first_preview_route_registered() -> None:
    """Verify /api/workspace/apply-from-first/preview route exists."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/workspace/apply-from-first/preview"' in source
    assert "_handle_workspace_apply_from_first_preview" in source


def test_library_analytics_trend_route_registered() -> None:
    """Verify /api/library/analytics/trend route exists."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/library/analytics/trend"' in source
    assert "_handle_library_analytics_trend" in source


def test_library_analytics_compare_route_registered() -> None:
    """Verify /api/library/analytics/compare route exists."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/library/analytics/compare"' in source
    assert "_handle_library_analytics_compare" in source


def test_library_tags_route_registered() -> None:
    """Verify /api/library/tags/update route exists."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/library/tags/update"' in source
    assert "_handle_library_tags_update" in source


def test_library_notes_route_registered() -> None:
    """Verify /api/library/notes/update route exists."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/library/notes/update"' in source
    assert "_handle_library_notes_update" in source


def test_library_export_routes_registered() -> None:
    """Verify /api/library/export/csv and /export/json routes exist."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/library/export/csv"' in source
    assert '"/api/library/export/json"' in source
    assert "_handle_library_export_csv" in source
    assert "_handle_library_export_json" in source


def test_library_backup_routes_registered() -> None:
    """Verify /api/library/backup/create and /backup/restore routes exist."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/library/backup/create"' in source
    assert '"/api/library/backup/restore"' in source
    assert "_handle_library_backup_create" in source
    assert "_handle_library_backup_restore" in source


def test_library_archive_route_registered() -> None:
    """Verify /api/library/archive/create route exists."""
    source = SERVER_PY.read_text(encoding="utf-8")
    assert '"/api/library/archive/create"' in source
    assert "_handle_library_archive_create" in source


def test_analytics_computation_exists() -> None:
    """Verify compute_analytics function exists in library.py."""
    library_py = REPO_ROOT / "src" / "splitshot" / "persistence" / "library.py"
    source = library_py.read_text(encoding="utf-8")
    assert "def compute_analytics" in source


def test_archive_generation_exists() -> None:
    """Verify generate_archive function exists in library.py."""
    library_py = REPO_ROOT / "src" / "splitshot" / "persistence" / "library.py"
    source = library_py.read_text(encoding="utf-8")
    assert "def generate_archive" in source


def test_list_recent_projects_exists() -> None:
    """Verify list_recent_projects function exists in projects.py."""
    projects_py = REPO_ROOT / "src" / "splitshot" / "persistence" / "projects.py"
    source = projects_py.read_text(encoding="utf-8")
    assert "def list_recent_projects" in source


def test_controller_apply_from_first_exists() -> None:
    """Verify workspace_apply_from_first method exists on ProjectController."""
    controller_py = REPO_ROOT / "src" / "splitshot" / "ui" / "controller.py"
    source = controller_py.read_text(encoding="utf-8")
    assert "def workspace_apply_from_first" in source
    assert "def workspace_apply_from_first_preview" in source


def test_data_models_have_required_fields() -> None:
    """Verify new data model fields exist."""
    models_py = REPO_ROOT / "src" / "splitshot" / "domain" / "models.py"
    source = models_py.read_text(encoding="utf-8")
    assert "inherited_from_first" in source
    assert "first_stage_snapshot" in source
    assert "archive_id" in source
    assert "class AnalyticsRecord" in source
    assert "class LibraryBackupManifest" in source
    assert "tags: list[str]" in source or "tags: list" in source
    assert "notes: str" in source
