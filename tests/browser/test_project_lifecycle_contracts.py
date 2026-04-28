from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest

import splitshot.browser.server as browser_server_module
from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "example_data"
STATIC_ROOT = REPO_ROOT / "src" / "splitshot" / "browser" / "static"


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_multipart(url: str, field_name: str, filename: str, payload: bytes) -> dict:
    boundary = "----splitshot-project-contract-boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + payload + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_project_json(project_path: Path) -> dict:
    return json.loads((project_path / "project.json").read_text(encoding="utf-8"))


def _changed_place_idpa_results(tmp_path: Path) -> Path:
    source = (EXAMPLES_DIR / "IDPA" / "IDPA.csv").read_text(encoding="utf-8")
    source = source.replace(
        "4,CO,UN,Klockenkemper,John,A1035577,,1,1,0,,83.01,11,1,1,,,,14.55,1,,,,,,,29.83,5,1,,,,,,18.62,5,,,,,,,20.01,,,1,,,,",
        "6,CO,UN,Klockenkemper,John,A1035577,,1,1,0,,83.01,11,1,1,,,,14.55,1,,,,,,,20.57,5,1,,,,,,18.62,5,,,,,,,20.01,,,1,,,,",
    )
    source = source.replace(
        "8,PCC,NV,Brown,Ben,A598326,,1,1,0,,88.21,15,,,,,,19.21,7,,,,,,,32.95,4,,,,,,,15.32,2,,,,,,,20.73,2,,,,,,",
        ",PCC,NV,Brown,Ben,A598326,,1,0,1,,88.21,15,,,,,,19.21,7,,,,,,,32.95,4,,,,,,,15.32,2,,,,,,,20.73,2,,,,,,",
    )
    path = tmp_path / "thursday-night.csv"
    path.write_text(source, encoding="utf-8")
    return path


def test_project_client_flushes_drafts_before_lifecycle_and_primary_import_paths() -> None:
    js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert "let projectDetailsDraft = { name: null, description: null };" in js
    assert "function mergeProjectDetailsDraft(project) {" in js
    assert "let projectFolderProbeRequestId = 0;" in js
    assert "if (requestId !== projectFolderProbeRequestId)" in js
    assert "function sameProjectFolderPath(left, right) {" in js
    assert "function hasActiveProject() {" in js
    assert 'await flushPendingProjectDrafts();\n  const currentPath = normalizeProjectFolderInput' in js
    assert 'const result = await callApi("/api/project/open", { path: projectPath });' in js
    assert 'const result = await callApi("/api/project/save", { path: projectPath });' in js
    assert 'if (!hasActiveProject()) {\n      setStatus(gatedProjectActionMessage());' in js
    assert 'window.alert(folderMessage);' in js
    assert 'if (apiPath === "/api/import/primary") {\n    await flushPendingProjectDrafts();' in js
    assert '$("primary-file-input").addEventListener("change", async (event) => {' in js
    assert 'if (!hasActiveProject()) {\n      setStatus(gatedProjectActionMessage());\n      event.target.value = "";\n      return;\n    }\n    await flushPendingProjectDrafts();' in js


def test_practiscore_dashboard_open_route_uses_system_browser(monkeypatch) -> None:
    opened_urls: list[str] = []
    monkeypatch.setattr(browser_server_module.webbrowser, "open", lambda url, new=0: opened_urls.append(url) or True)

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        payload = _post_json(f"{server.url}api/practiscore/dashboard/open", {})
    finally:
        server.shutdown()

    assert payload["status"] == "Opened PractiScore dashboard in your browser."
    assert payload["url"] == "https://practiscore.com/dashboard/home"
    assert opened_urls == ["https://practiscore.com/dashboard/home"]


def test_project_details_save_open_and_refresh_contract(tmp_path: Path) -> None:
    project_path = tmp_path / "draft-details.ssproj"
    ProjectController().save_project(str(project_path))

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        opened = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        assert opened["project"]["name"] == "Untitled Project"
        assert opened["project"]["description"] == ""

        updated = _post_json(
            f"{server.url}api/project/details",
            {"name": "Classifier Practice", "description": "Morning classifier run"},
        )
        assert updated["project"]["name"] == "Classifier Practice"
        assert updated["project"]["description"] == "Morning classifier run"

        saved = _post_json(f"{server.url}api/project/save", {"path": str(project_path)})
        assert saved["project"]["name"] == "Classifier Practice"
        assert _read_project_json(project_path)["description"] == "Morning classifier run"

        _post_json(f"{server.url}api/project/new", {})
        reopened = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        refreshed = json.loads(urllib.request.urlopen(f"{server.url}api/state", timeout=30).read().decode("utf-8"))

        assert reopened["project"]["name"] == "Classifier Practice"
        assert reopened["project"]["description"] == "Morning classifier run"
        assert refreshed["project"]["name"] == "Classifier Practice"
        assert refreshed["project"]["description"] == "Morning classifier run"
    finally:
        server.shutdown()


def test_project_folder_probe_and_project_json_path_use_same_folder(tmp_path: Path) -> None:
    project_path = tmp_path / "chosen-project.ssproj"
    ProjectController().save_project(str(project_path))
    metadata_path = project_path / "project.json"

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        probed = _post_json(f"{server.url}api/project/probe", {"path": str(metadata_path)})
        assert probed["path"] == str(metadata_path)
        assert probed["normalized_path"] == str(project_path.resolve())
        assert probed["has_project_file"] is True
        assert probed["missing_required_dirs"] == []

        opened = _post_json(f"{server.url}api/project/open", {"path": str(metadata_path)})
        assert opened["project"]["path"] == str(project_path)

        opened["project"]["name"] = "ignored local copy"
        saved = _post_json(f"{server.url}api/project/save", {"path": str(metadata_path)})
        assert saved["project"]["path"] == str(project_path)
        assert (project_path / "project.json").is_file()
    finally:
        server.shutdown()


def test_practiscore_reimport_is_deterministic_for_staged_source_and_context() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "IDPA.csv",
            (EXAMPLES_DIR / "IDPA" / "IDPA.csv").read_bytes(),
        )

        payload = {
            "match_type": "idpa",
            "stage_number": 2,
            "competitor_name": "John Klockenkemper",
            "competitor_place": 4,
        }
        first = _post_json(f"{server.url}api/project/practiscore", payload)
        second = _post_json(f"{server.url}api/project/practiscore", payload)

        assert second["project"]["scoring"]["imported_stage"] == first["project"]["scoring"]["imported_stage"]
        assert second["project"]["scoring"]["penalty_counts"] == first["project"]["scoring"]["penalty_counts"]
        assert second["practiscore_options"] == first["practiscore_options"]
        assert second["scoring_summary"]["imported_overlay_text"] == first["scoring_summary"]["imported_overlay_text"]
        assert any(
            box["source"] == "imported_summary" and box["enabled"]
            for box in second["project"]["overlay"]["text_boxes"]
        )
    finally:
        server.shutdown()


def test_practiscore_reimport_preserves_name_fallback_when_place_changes(tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        _post_json(
            f"{server.url}api/project/practiscore",
            {
                "match_type": "idpa",
                "stage_number": 2,
                "competitor_name": "John Klockenkemper",
                "competitor_place": 4,
            },
        )
        _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "IDPA.csv",
            (EXAMPLES_DIR / "IDPA" / "IDPA.csv").read_bytes(),
        )

        changed_file = _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "thursday-night.csv",
            _changed_place_idpa_results(tmp_path).read_bytes(),
        )

        assert changed_file["project"]["scoring"]["competitor_name"] == "John Klockenkemper"
        assert changed_file["project"]["scoring"]["competitor_place"] == 6
        assert changed_file["project"]["scoring"]["imported_stage"]["source_name"] == "thursday-night.csv"
        assert changed_file["project"]["scoring"]["imported_stage"]["final_time"] == 20.57
        assert changed_file["project"]["overlay"]["custom_box_mode"] == "imported_summary"
    finally:
        server.shutdown()


def test_primary_import_replacement_has_deterministic_state_boundaries(
    synthetic_video_factory,
) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        first_primary = Path(synthetic_video_factory(name="project-primary-one", beep_ms=400))
        second_primary = Path(synthetic_video_factory(name="project-primary-two", beep_ms=520))
        merge_media = Path(synthetic_video_factory(name="project-merge", beep_ms=680))

        imported = _post_json(f"{server.url}api/import/primary", {"path": str(first_primary)})
        first_shot_id = imported["project"]["analysis"]["shots"][0]["id"]
        _post_json(f"{server.url}api/import/merge", {"path": str(merge_media)})
        _post_json(
            f"{server.url}api/project/ui-state",
            {
                "selected_shot_id": first_shot_id,
                "timeline_offset_ms": 999,
                "active_tool": "review",
                "waveform_expanded": True,
                "timing_expanded": False,
                "scoring_shot_expansion": {first_shot_id: True},
                "waveform_shot_amplitudes": {first_shot_id: 1.25},
                "timing_edit_shot_ids": [first_shot_id],
            },
        )
        controller.project.export.last_log = "old export log"
        controller.project.export.last_error = "old export error"

        replaced = _post_json(f"{server.url}api/import/primary", {"path": str(second_primary)})

        assert replaced["project"]["primary_video"]["path"] == str(second_primary)
        assert replaced["project"]["secondary_video"] is None
        assert replaced["project"]["merge_sources"] == []
        assert replaced["project"]["merge"]["enabled"] is False
        assert replaced["project"]["export"]["last_log"] == ""
        assert replaced["project"]["export"]["last_error"] is None
        assert replaced["project"]["ui_state"]["active_tool"] == "review"
        assert replaced["project"]["ui_state"]["waveform_expanded"] is True
        assert replaced["project"]["ui_state"]["selected_shot_id"] is None
        assert replaced["project"]["ui_state"]["timeline_offset_ms"] == 0
        assert replaced["project"]["ui_state"]["scoring_shot_expansion"] == {}
        assert replaced["project"]["ui_state"]["waveform_shot_amplitudes"] == {}
        assert replaced["project"]["ui_state"]["timing_edit_shot_ids"] == []
    finally:
        server.shutdown()


def test_lifecycle_new_open_save_delete_restore_order(tmp_path: Path) -> None:
    project_path = tmp_path / "lifecycle.ssproj"
    controller = ProjectController()
    controller.project.name = "Lifecycle"
    controller.project.ui_state.active_tool = "timing"
    controller.project.ui_state.timing_expanded = True
    controller.project.export.last_log = "saved log"
    controller.save_project(str(project_path))

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        opened = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        assert opened["project"]["name"] == "Lifecycle"
        assert opened["project"]["ui_state"]["active_tool"] == "timing"
        assert opened["project"]["ui_state"]["timing_expanded"] is True
        assert opened["project"]["export"]["last_log"] == "saved log"

        saved = _post_json(f"{server.url}api/project/save", {"path": str(project_path)})
        assert saved["project"]["path"] == str(project_path)
        assert saved["project"]["ui_state"]["active_tool"] == "timing"

        fresh = _post_json(f"{server.url}api/project/new", {})
        assert fresh["project"]["path"] == ""
        assert fresh["project"]["name"] == "Untitled Project"
        assert fresh["project"]["ui_state"]["active_tool"] == "project"
        assert fresh["project"]["ui_state"]["timing_expanded"] is False
        assert fresh["project"]["export"]["last_log"] == ""

        _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        deleted = _post_json(f"{server.url}api/project/delete", {})
        assert project_path.exists()
        assert not (project_path / "project.json").exists()
        assert deleted["project"]["path"] == ""
        assert deleted["project"]["ui_state"]["active_tool"] == "project"
        assert deleted["project"]["export"]["last_log"] == ""
        assert deleted["status"] == "Deleted the saved project metadata file."
    finally:
        server.shutdown()


def test_project_probe_reports_missing_required_dirs_for_existing_partial_folder(tmp_path: Path) -> None:
    project_path = tmp_path / "partial.ssproj"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "Input").mkdir()

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        probed = _post_json(f"{server.url}api/project/probe", {"path": str(project_path)})
    finally:
        server.shutdown()

    assert probed["path"] == str(project_path)
    assert probed["normalized_path"] == str(project_path.resolve())
    assert probed["has_project_file"] is False
    assert probed["missing_required_dirs"] == ["CSV", "Output"]
