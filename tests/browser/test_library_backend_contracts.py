from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_PY = REPO_ROOT / "src" / "splitshot" / "persistence" / "library.py"
MODELS_PY = REPO_ROOT / "src" / "splitshot" / "domain" / "models.py"


def test_compute_analytics_handles_empty_data() -> None:
    """compute_analytics should return error dict when no records exist."""
    from splitshot.persistence.library import compute_analytics

    result = compute_analytics()
    assert isinstance(result, dict)
    assert "error" in result or result.get("total_records", 0) == 0


def test_compute_analytics_returns_correct_structure() -> None:
    """compute_analytics result should have metric_key or an error key."""
    from splitshot.persistence.library import compute_analytics

    result = compute_analytics()
    assert isinstance(result, dict)
    assert "metric_key" in result or "records" in result


def test_compute_analytics_builds_trend_breakdown_bests_and_outliers_from_real_records(
    monkeypatch,
) -> None:
    """compute_analytics should build truthful trend, breakdown, PB, and outlier payloads."""
    from splitshot.persistence import library as library_module
    from splitshot.persistence.library import compute_analytics

    def iso(day: int) -> str:
        return datetime(2026, 1, day, tzinfo=timezone.utc).isoformat()

    records = [
        {
            "library_record_id": "stage-1",
            "display_name": "Run 1",
            "event_date": iso(1),
            "discipline": "uspsa_minor",
            "metric_summary": {"score_total": 80},
        },
        {
            "library_record_id": "stage-2",
            "display_name": "Run 2",
            "event_date": iso(5),
            "discipline": "idpa_time_plus",
            "metric_summary": {"score": 81},
        },
        {
            "library_record_id": "stage-3",
            "display_name": "Run 3",
            "event_date": iso(10),
            "discipline": "uspsa_minor",
            "metric_summary": {"hit_factor": 82},
        },
        {
            "library_record_id": "stage-4",
            "display_name": "Run 4",
            "event_date": iso(15),
            "discipline": "idpa_time_plus",
            "metric_summary": {"score_total": 83},
        },
        {
            "library_record_id": "stage-5",
            "display_name": "Run 5",
            "event_date": iso(20),
            "discipline": "uspsa_minor",
            "metric_summary": {"score_total": 130},
        },
    ]

    monkeypatch.setattr(library_module, "read_stage_records", lambda: list(records))
    monkeypatch.setattr(library_module, "read_stage_metrics", lambda: [])

    result = compute_analytics()

    assert result["total_records"] == 5
    assert result["trend_direction"] == "improving"
    assert [point["record_id"] for point in result["trend_points"]] == [
        "stage-1",
        "stage-2",
        "stage-3",
        "stage-4",
        "stage-5",
    ]
    assert result["discipline_breakdown"] == [
        {"discipline": "uspsa_minor", "count": 3},
        {"discipline": "idpa_time_plus", "count": 2},
    ]
    assert result["personal_bests"][0]["record_id"] == "stage-5"
    assert result["personal_bests"][0]["score"] == 130.0
    assert result["outliers"] == [
        {
            "name": "Run 5",
            "date": iso(20),
            "score": 130.0,
            "direction": "high",
        }
    ]


def test_library_models_have_tags_and_notes() -> None:
    """LibraryStageRecord and LibraryMatchRecord should have tags and notes."""
    from splitshot.domain.models import LibraryStageRecord, LibraryMatchRecord

    stage = LibraryStageRecord()
    assert hasattr(stage, "tags")
    assert hasattr(stage, "notes")
    assert isinstance(stage.tags, list)
    assert isinstance(stage.notes, str)

    match = LibraryMatchRecord()
    assert hasattr(match, "tags")
    assert hasattr(match, "notes")
    assert isinstance(match.tags, list)
    assert isinstance(match.notes, str)


def test_update_record_tags_callable() -> None:
    """update_record_tags should be callable with record_id and tags."""
    from splitshot.persistence.library import update_record_tags

    assert callable(update_record_tags)


def test_update_record_notes_callable() -> None:
    """update_record_notes should be callable with record_id and notes."""
    from splitshot.persistence.library import update_record_notes

    assert callable(update_record_notes)


def test_list_recent_projects_returns_list() -> None:
    """list_recent_projects should return a list."""
    from splitshot.persistence.projects import list_recent_projects

    result = list_recent_projects(limit=3)
    assert isinstance(result, list)


def test_analytics_record_serializes() -> None:
    """AnalyticsRecord should serialize correctly."""
    from splitshot.domain.models import AnalyticsRecord, _serialize

    record = AnalyticsRecord(
        metric_key="score",
        trend_direction="improving",
        statistics={"mean": 85.5, "median": 87.0},
    )
    data = _serialize(record)
    assert data["metric_key"] == "score"
    assert data["trend_direction"] == "improving"
    assert data["statistics"]["mean"] == 85.5


def test_backup_manifest_serializes() -> None:
    """LibraryBackupManifest should serialize correctly."""
    from splitshot.domain.models import LibraryBackupManifest, _serialize

    manifest = LibraryBackupManifest(
        total_records=100,
        total_archives=5,
        record_ids=["a", "b", "c"],
    )
    data = _serialize(manifest)
    assert data["total_records"] == 100
    assert data["total_archives"] == 5
    assert data["record_ids"] == ["a", "b", "c"]


def test_browser_state_keeps_summary_slices_explicit_and_lightweight(monkeypatch) -> None:
    """/api/state should expose summary slices only and strip internal PractiScore payloads."""
    from splitshot.browser import state as browser_state_module
    from splitshot.domain.models import Project

    library_summary = {
        "stage_count": 7,
        "match_count": 3,
        "last_updated": "2026-05-25T12:00:00+00:00",
        "filters_available": ["discipline", "competitor", "match_id", "stage_id", "sort_by"],
        "selection": None,
    }
    proxy_summary = {
        "active_proxy_id": "stage-7",
        "proxy_stale": False,
        "proxy_available": True,
        "proxy_path": "/tmp/proxy.mp4",
        "last_generated": "2026-05-25T12:05:00+00:00",
    }

    monkeypatch.setattr(
        browser_state_module, "_build_library_summary", lambda controller: library_summary
    )
    monkeypatch.setattr(
        browser_state_module, "_build_proxy_summary", lambda controller: proxy_summary
    )

    payload = browser_state_module.browser_state(
        Project(),
        "Ready.",
        practiscore_options={
            "has_source": True,
            "source_name": "report.txt",
            "detected_match_type": "uspsa",
            "stage_numbers": [1],
            "competitors": [{"name": "Ada Lovelace", "place": 1}],
            "_session_payload": {
                "state": "authenticated_ready",
                "message": "Connected.",
                "details": {"browser": "shared"},
            },
            "_sync_payload": {
                "state": "match_list_ready",
                "message": "Found 1 remote PractiScore match.",
                "matches": [
                    {
                        "remote_id": "remote-1",
                        "label": "Classifier",
                        "match_type": "uspsa",
                        "event_name": "Classifier",
                        "event_date": "2026-05-25",
                    }
                ],
                "selected_remote_id": "remote-1",
                "details": {"match_count": 1},
            },
        },
    )

    assert payload["workspace"] is None
    assert payload["match_workspace_summary"] is None
    assert payload["workspace_stage_entries"] == []
    assert payload["workspace_shared_defaults"] == {}
    assert payload["workspace_override_summary"] == {}
    assert payload["output_profiles"] == []
    assert payload["output_profile_summary"] == []
    assert payload["inherited_setting_status"] == {}
    assert payload["library_summary"] == library_summary
    assert payload["proxy_summary"] == proxy_summary
    assert payload["library_filters"] == [
        "discipline",
        "competitor",
        "match_id",
        "stage_id",
        "sort_by",
        "sort_order",
    ]
    assert payload["library_selection"] is None
    assert payload["library_reopen_targets"] == []

    assert payload["practiscore_session"] == {
        "state": "authenticated_ready",
        "message": "Connected.",
        "details": {"browser": "shared"},
    }
    assert payload["practiscore_sync"] == {
        "state": "match_list_ready",
        "message": "Found 1 remote PractiScore match.",
        "matches": [
            {
                "remote_id": "remote-1",
                "label": "Classifier",
                "match_type": "uspsa",
                "event_name": "Classifier",
                "event_date": "2026-05-25",
            }
        ],
        "selected_remote_id": "remote-1",
        "error_category": "",
        "details": {"match_count": 1},
    }
    assert payload["practiscore_options"] == {
        "has_source": True,
        "source_name": "report.txt",
        "detected_match_type": "uspsa",
        "stage_numbers": [1],
        "competitors": [{"name": "Ada Lovelace", "place": 1}],
    }

    for forbidden_key in (
        "library_records",
        "library_results",
        "library_analytics",
        "workspace_stage_clips",
        "workspace_export_payload",
        "workspace_recap_payload",
    ):
        assert forbidden_key not in payload


def test_browser_state_workspace_summary_stays_alias_only_without_heavy_stage_payloads(
    monkeypatch,
) -> None:
    """Workspace slices should stay summary-sized and avoid stage workflow payloads."""
    from splitshot.browser import state as browser_state_module
    from splitshot.ui.controller import ProjectController

    monkeypatch.setattr(
        browser_state_module,
        "_build_library_summary",
        lambda controller: {
            "stage_count": 0,
            "match_count": 0,
            "last_updated": None,
            "filters_available": ["discipline", "competitor", "match_id", "stage_id", "sort_by"],
            "selection": None,
        },
    )
    monkeypatch.setattr(
        browser_state_module,
        "_build_proxy_summary",
        lambda controller: {
            "active_proxy_id": None,
            "proxy_stale": False,
            "proxy_available": False,
            "proxy_path": None,
            "last_generated": None,
        },
    )

    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Summary Contract Match"
    controller.workspace.description = "Alias-only payload"
    controller.workspace_add_stage("stage_1", "Bay 1")
    controller.workspace.stage_entries["stage_1"].override_values = {"frame_profile": "16:9"}

    payload = browser_state_module.browser_state(
        controller.project,
        controller.status_message,
        controller=controller,
    )

    assert payload["workspace"] == payload["match_workspace_summary"]
    assert payload["workspace"]["name"] == "Summary Contract Match"
    assert payload["workspace"]["stage_count"] == 1

    entry = payload["workspace_stage_entries"][0]
    assert entry["stage_id"] == "stage_1"
    assert entry["name"] == "Bay 1"
    assert entry["override_count"] == 1
    assert entry["override_values"] == {"frame_profile": "16:9"}
    assert payload["workspace_override_summary"] == {"stage_1": {"frame_profile": "16:9"}}

    for forbidden_key in ("clip_sources", "clips", "recap", "project"):
        assert forbidden_key not in entry


def test_proxy_controller_methods_delegate_to_shared_backend_service(monkeypatch) -> None:
    """Proxy helpers should stay thin controller delegations to the shared service."""
    import splitshot.ui.services.shared_backend as shared_backend_service
    from splitshot.ui.controller import ProjectController

    controller = ProjectController()
    calls: list[tuple[str, object, str, str | None]] = []
    status_result = {"exists": True, "scope_id": "stage-proxy"}
    plan_result = {"steps": ["proxy_encode"]}
    refresh_result = {"status": "scheduled", "scope_id": "match-1"}
    open_result = {"success": True, "proxy_path": "/tmp/proxy.mp4"}

    def fake_proxy_status(
        passed_controller: ProjectController,
        scope_type: str = "stage",
        scope_id: str | None = None,
    ) -> dict[str, object]:
        calls.append(("status", passed_controller, scope_type, scope_id))
        return status_result

    def fake_generate_default_render_plan(scope_type: str = "stage") -> dict[str, object]:
        calls.append(("plan", controller, scope_type, None))
        return plan_result

    def fake_proxy_refresh(
        passed_controller: ProjectController,
        scope_type: str = "stage",
        scope_id: str | None = None,
    ) -> dict[str, object]:
        calls.append(("refresh", passed_controller, scope_type, scope_id))
        return refresh_result

    def fake_proxy_open_target(
        passed_controller: ProjectController,
        scope_type: str = "stage",
        scope_id: str | None = None,
    ) -> dict[str, object]:
        calls.append(("open", passed_controller, scope_type, scope_id))
        return open_result

    monkeypatch.setattr(shared_backend_service, "proxy_status", fake_proxy_status)
    monkeypatch.setattr(
        shared_backend_service,
        "generate_default_render_plan",
        fake_generate_default_render_plan,
    )
    monkeypatch.setattr(shared_backend_service, "proxy_refresh", fake_proxy_refresh)
    monkeypatch.setattr(shared_backend_service, "proxy_open_target", fake_proxy_open_target)

    assert controller.proxy_status() == status_result
    assert controller._generate_default_render_plan("match") == plan_result
    assert controller.proxy_refresh("match", "match-1") == refresh_result
    assert controller.proxy_open_target("stage", "stage-proxy") == open_result
    assert calls == [
        ("status", controller, "stage", None),
        ("plan", controller, "match", None),
        ("refresh", controller, "match", "match-1"),
        ("open", controller, "stage", "stage-proxy"),
    ]


def test_library_backup_controller_methods_delegate_to_shared_backend_service(
    monkeypatch,
) -> None:
    """Library backup endpoints should preserve controller wrappers over the shared service."""
    import splitshot.ui.services.shared_backend as shared_backend_service
    from splitshot.ui.controller import ProjectController

    controller = ProjectController()
    manifest = {"schema_version": 1, "stage_records": [], "match_records": []}
    create_result = {"manifest": {"backup_id": "backup-1"}, "total_stages": 0, "total_matches": 0}
    restore_result = {"restored": True, "stages_restored": 0, "matches_restored": 0, "errors": []}
    calls: list[tuple[str, object]] = []

    def fake_library_backup_create() -> dict[str, object]:
        calls.append(("create", None))
        return create_result

    def fake_library_backup_restore(
        passed_manifest: dict[str, object],
    ) -> dict[str, object]:
        calls.append(("restore", passed_manifest))
        return restore_result

    monkeypatch.setattr(
        shared_backend_service,
        "library_backup_create",
        fake_library_backup_create,
    )
    monkeypatch.setattr(
        shared_backend_service,
        "library_backup_restore",
        fake_library_backup_restore,
    )

    assert controller.library_backup_create() == create_result
    assert controller.library_backup_restore(manifest) == restore_result
    assert calls == [("create", None), ("restore", manifest)]
