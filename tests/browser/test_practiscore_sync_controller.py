from __future__ import annotations

import json
import shutil
import urllib.request
from pathlib import Path

import splitshot.ui.controller as controller_module
from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import ImportedStageScore, ShotEvent, VideoAsset
from splitshot.scoring.practiscore_web_extract import (
    MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
    PractiScoreSyncError,
    RemotePractiScoreMatch,
    SelectedRemoteMatchArtifacts,
)
from splitshot.ui.controller import ProjectController

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "example_data"


def test_practiscore_refresh_cannot_clear_existing_stage_media_or_analysis() -> None:
    source = EXAMPLES_DIR / "IDPA" / "IDPA.csv"
    controller = ProjectController()
    controller.import_practiscore_file(str(source), source.name)
    stage = controller.project.stages[1]
    stage.primary_media = VideoAsset(path="Stage2.mp4", duration_ms=12_000)
    stage.analysis.shots = [ShotEvent(time_ms=4321)]
    controller.project.active_stage_id = stage.id
    controller.project.primary_video = VideoAsset()
    controller.project.analysis.shots = []

    controller.import_practiscore_file(str(source), source.name)

    restored = next(item for item in controller.project.stages if item.id == stage.id)
    assert restored.primary_media.path == "Stage2.mp4"
    assert [shot.time_ms for shot in restored.analysis.shots] == [4321]
    assert restored.scoring.imported_stage is not None
    assert restored.scoring.imported_stage.stage_number == 2


def test_practiscore_identity_fields_can_clear_and_survive_stage_override_restore() -> None:
    controller = ProjectController()
    controller.create_stage()
    controller.project.scoring.classification = "Master"
    controller.project.scoring.division = "Carry Optics"
    controller.set_practiscore_context(classification="", division="", competitor_place=0)
    assert controller.project.scoring.classification == ""
    assert controller.project.scoring.division == ""
    assert controller.project.scoring.competitor_place is None

    controller.project.scoring.imported_stage = ImportedStageScore(
        competitor_name="Shooter",
        classification="A",
        division="Limited",
    )
    controller.project.scoring.competitor_name = "Shooter"
    controller.project.scoring.classification = "B"
    controller.project.scoring.division = "Open"
    overrides = controller._active_stage_practiscore_overrides()
    controller.project.scoring.classification = "A"
    controller.project.scoring.division = "Limited"
    controller._restore_active_stage_practiscore_overrides(overrides)
    assert controller.project.scoring.classification == "B"
    assert controller.project.scoring.division == "Open"


def test_open_project_rebuilds_practiscore_comparison_competitors(tmp_path: Path) -> None:
    source = tmp_path / "IDPA.csv"
    shutil.copyfile(EXAMPLES_DIR / "IDPA" / "IDPA.csv", source)
    project_path = tmp_path / "comparison-restore.ssproj"
    controller = ProjectController()
    controller.save_project(str(project_path))
    controller.import_practiscore_file(str(source), source.name)
    controller.save_project(str(project_path))
    expected_count = len(controller.practiscore_browser_state()["comparison_competitors"])
    assert expected_count > 1

    reopened = ProjectController()
    reopened.open_project(str(project_path))
    restored = reopened.practiscore_browser_state()["comparison_competitors"]
    assert len(restored) == expected_count


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


class _FakeStatus:
    def __init__(self, state: str, message: str, details: dict[str, object]) -> None:
        self.state = state
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "message": self.message,
            "details": dict(self.details),
        }


class _FakeSessionManager:
    def __init__(
        self, tmp_path: Path, *, state: str = "authenticated_ready", message: str | None = None
    ) -> None:
        self.profile_paths = type("ProfilePaths", (), {"app_dir": tmp_path})()
        self._state = state
        self._message = message or {
            "authenticated_ready": "PractiScore session is authenticated and ready.",
            "expired": "PractiScore session expired. Reconnect in your browser to continue.",
        }.get(state, state)
        self._details = {
            "profile_path": str(tmp_path / "practiscore" / "browser-profile"),
        }
        self._browser_context = object()

    def current_status(self) -> _FakeStatus:
        return _FakeStatus(self._state, self._message, self._details)

    def serialize_status(self) -> dict[str, object]:
        return self.current_status().to_dict()

    def require_authenticated_browser(self) -> object:
        if self._state != "authenticated_ready":
            raise RuntimeError(self._message)
        return self._browser_context

    def shutdown(self) -> None:
        return


def _build_downloaded_artifacts(tmp_path: Path, remote_id: str) -> SelectedRemoteMatchArtifacts:
    cache_dir = tmp_path / "practiscore" / "sync-audit" / remote_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    source_artifact_path = cache_dir / "remote-idpa.csv"
    shutil.copyfile(EXAMPLES_DIR / "IDPA" / "IDPA.csv", source_artifact_path)
    html_path = cache_dir / "selected-match.html"
    html_path.write_text("<html><body><h1>Remote IDPA Match</h1></body></html>", encoding="utf-8")
    summary_path = cache_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "remote_match": {
                    "remote_id": remote_id,
                    "label": "Remote IDPA Match",
                    "match_type": "idpa",
                    "event_name": "Remote IDPA Match",
                    "event_date": "2026-04-21",
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return SelectedRemoteMatchArtifacts(
        match=RemotePractiScoreMatch(
            remote_id=remote_id,
            label="Remote IDPA Match",
            match_type="idpa",
            event_name="Remote IDPA Match",
            event_date="2026-04-21",
        ),
        cache_dir=cache_dir,
        source_artifact_path=source_artifact_path,
        source_name="remote-idpa.csv",
        html_path=html_path,
        summary_path=summary_path,
        summary_snapshot={
            "remote_match": {
                "remote_id": remote_id,
                "label": "Remote IDPA Match",
                "match_type": "idpa",
                "event_name": "Remote IDPA Match",
                "event_date": "2026-04-21",
            }
        },
    )


def test_practiscore_match_list_route_exposes_sync_payload_shape(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        controller_module,
        "discover_remote_matches",
        lambda browser_context: [
            RemotePractiScoreMatch(
                remote_id="match-100",
                label="April USPSA Night Match",
                match_type="uspsa",
                event_name="April USPSA Night Match",
                event_date="2026-04-21",
            )
        ],
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.practiscore_session = _FakeSessionManager(tmp_path)
    server.start_background(open_browser=False)

    try:
        payload = _get_json(f"{server.url}api/practiscore/matches")
        state_payload = _get_json(f"{server.url}api/state")
    finally:
        server.shutdown()

    assert payload["matches"] == [
        {
            "remote_id": "match-100",
            "label": "April USPSA Night Match",
            "match_type": "uspsa",
            "event_name": "April USPSA Night Match",
            "event_date": "2026-04-21",
        }
    ]
    assert payload["practiscore_sync"]["state"] == "match_list_ready"
    assert state_payload["practiscore_session"]["state"] == "authenticated_ready"
    assert state_payload["practiscore_sync"]["state"] == "match_list_ready"


def test_practiscore_selected_match_import_route_exposes_success_payload_shape(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        controller_module,
        "discover_remote_matches",
        lambda browser_context: [
            RemotePractiScoreMatch(
                remote_id="match-200",
                label="Remote IDPA Match",
                match_type="idpa",
                event_name="Remote IDPA Match",
                event_date="2026-04-21",
            )
        ],
    )
    monkeypatch.setattr(
        controller_module,
        "download_remote_match_artifacts",
        lambda browser_context, remote_id, cache_root, match_catalog=None: (
            _build_downloaded_artifacts(tmp_path, remote_id)
        ),
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.practiscore_session = _FakeSessionManager(tmp_path)
    server.start_background(open_browser=False)

    try:
        _get_json(f"{server.url}api/practiscore/matches")
        payload = _post_json(
            f"{server.url}api/practiscore/sync/start",
            {"remote_id": "match-200"},
        )
        state_payload = _get_json(f"{server.url}api/state")
    finally:
        server.shutdown()

    assert payload["practiscore_sync"]["state"] == "success"
    assert payload["practiscore_sync"]["selected_remote_id"] == "match-200"
    assert payload["practiscore_sync"]["details"]["summary_path"].endswith("summary.json")
    assert payload["practiscore_options"]["has_source"] is True
    assert payload["practiscore_options"]["source_name"] == "remote-idpa.csv"
    assert payload["practiscore_options"]["stage_numbers"] == [1, 2, 3, 4]
    assert state_payload["practiscore_sync"]["state"] == "success"
    assert state_payload["practiscore_options"]["has_source"] is True


def test_practiscore_match_list_route_reports_expired_session_error(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(controller_module, "discover_remote_matches", lambda browser_context: [])

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.practiscore_session = _FakeSessionManager(tmp_path, state="expired")
    server.start_background(open_browser=False)

    try:
        payload = _get_json(f"{server.url}api/practiscore/matches")
    finally:
        server.shutdown()

    assert payload["practiscore_session"]["state"] == "expired"
    assert payload["practiscore_sync"]["state"] == "error"
    assert payload["practiscore_sync"]["error_category"] == "expired_authentication"


def test_practiscore_selected_match_import_route_reports_missing_artifact_error(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        controller_module,
        "download_remote_match_artifacts",
        lambda browser_context, remote_id, cache_root, match_catalog=None: (_ for _ in ()).throw(
            PractiScoreSyncError(
                MISSING_REQUIRED_REMOTE_ARTIFACT_ERROR,
                "PractiScore did not expose a CSV or TXT artifact for remote match match-300.",
                details={"remote_id": remote_id},
            )
        ),
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.practiscore_session = _FakeSessionManager(tmp_path)
    server.start_background(open_browser=False)

    try:
        payload = _post_json(
            f"{server.url}api/practiscore/sync/start",
            {"remote_id": "match-300"},
        )
    finally:
        server.shutdown()

    assert payload["practiscore_sync"]["state"] == "error"
    assert payload["practiscore_sync"]["selected_remote_id"] == "match-300"
    assert payload["practiscore_sync"]["error_category"] == "missing_required_remote_artifact"
