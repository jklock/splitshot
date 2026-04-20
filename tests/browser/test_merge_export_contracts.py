from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import MergeLayout, MergeSource
from splitshot.media.probe import probe_video
from splitshot.ui.controller import ProjectController


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "app.js"


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _function_body(source: str, function_name: str) -> str:
    match = re.search(rf"function {function_name}\([^)]*\) \{{", source)
    assert match, f"{function_name} was not found"
    depth = 1
    index = match.end()
    while index < len(source) and depth:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"{function_name} body was not balanced"
    return source[match.end(): index - 1]


def test_app_merge_export_commit_and_log_freshness_contracts() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    drag_body = _function_body(source, "endMergePreviewDrag")
    begin_drag_body = _function_body(source, "beginMergePreviewDrag")
    move_drag_body = _function_body(source, "moveMergePreviewDrag")
    export_click = source[source.index('$("export-video").addEventListener("click"') :]
    export_click = export_click[: export_click.index('$("show-export-log")')]

    assert "function previewFrameClientRect(video, container) {" in source
    assert 'const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();' in begin_drag_body
    assert 'const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();' in move_drag_body
    assert "scheduleMergeSourceCommit(mergeSourcePositionPayload(drag.sourceId, source))" in drag_body
    assert 'callApi("/api/merge/source"' not in drag_body
    assert "await flushPendingMergeSourceCommits();" in export_click
    assert "clearCurrentExportLogState();" in _function_body(source, "beginProcessing")
    assert 'state.project.export.last_error = null;' in _function_body(source, "clearCurrentExportLogState")
    assert 'if (mergePreview && merge.layout === "pip" && mergeSources.length > 0) {' in source
    assert 'media.style.opacity = String(currentSourceOpacity(source));' in source
    assert 'input.dataset.mergeSourceField = "opacity";' in source
    assert "These values are saved per item and take effect in PiP layout and export timing." in source


def test_merge_source_offsets_persist_reopen_and_export_in_order(
    synthetic_video_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    primary_path = Path(synthetic_video_factory(name="merge-contract-primary", resolution=(320, 180)))
    secondary_path = Path(synthetic_video_factory(name="merge-contract-secondary", resolution=(320, 180)))
    tertiary_path = Path(synthetic_video_factory(name="merge-contract-tertiary", resolution=(320, 180)))
    controller = ProjectController()
    controller.project.primary_video = probe_video(primary_path)
    controller.project.merge.enabled = True
    controller.project.merge.layout = MergeLayout.PIP
    controller.project.merge_sources = [
        MergeSource(asset=probe_video(secondary_path), pip_size_percent=35, pip_x=1.0, pip_y=1.0),
        MergeSource(asset=probe_video(tertiary_path), pip_size_percent=35, pip_x=1.0, pip_y=1.0),
    ]
    controller.project.secondary_video = controller.project.merge_sources[0].asset
    first_id = controller.project.merge_sources[0].id
    second_id = controller.project.merge_sources[1].id
    captured: list[list[tuple[str, int | None, float, float, float, int]]] = []

    def fake_export_project(project, output_path, progress_callback=None, log_callback=None):
        captured.append([
            (
                source.id,
                source.pip_size_percent,
                source.pip_x,
                source.pip_y,
                source.opacity,
                source.sync_offset_ms,
            )
            for source in project.merge_sources
        ])
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake mp4")
        project.export.last_log = "current export"
        project.export.last_error = None
        return output

    monkeypatch.setattr("splitshot.browser.server.export_project", fake_export_project)
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(
            f"{server.url}api/merge/source",
            {
                "source_id": first_id,
                "pip_size_percent": 1,
                "pip_x": 0.25,
                "pip_y": 0.75,
                "opacity": 0.45,
                "sync_offset_ms": 125,
            },
        )
        first = next(source for source in state["project"]["merge_sources"] if source["id"] == first_id)
        assert first["pip_size_percent"] == 1
        assert first["pip_x"] == 0.25
        assert first["pip_y"] == 0.75
        assert first["opacity"] == 0.45
        assert first["sync_offset_ms"] == 125

        _post_json(
            f"{server.url}api/merge/source",
            {
                "source_id": second_id,
                "pip_size_percent": 55,
                "pip_x": 0.1,
                "pip_y": 0.2,
                "opacity": 0.8,
                "sync_offset_ms": -75,
            },
        )
        bundle_path = tmp_path / "merge-export-project"
        _post_json(f"{server.url}api/project/save", {"path": str(bundle_path)})
        _post_json(f"{server.url}api/project/new", {})
        reopened = _post_json(f"{server.url}api/project/open", {"path": str(bundle_path)})

        reopened_sources = reopened["project"]["merge_sources"]
        assert [source["id"] for source in reopened_sources] == [first_id, second_id]
        assert [source["sync_offset_ms"] for source in reopened_sources] == [125, -75]
        assert reopened_sources[0]["pip_x"] == 0.25
        assert reopened_sources[0]["opacity"] == 0.45
        assert reopened_sources[1]["pip_size_percent"] == 55
        assert reopened_sources[1]["opacity"] == 0.8

        output_path = tmp_path / "merge-export.mp4"
        state = _post_json(
            f"{server.url}api/export",
            {
                "path": str(output_path),
                "preset": "source",
                "merge": {
                    "enabled": True,
                    "layout": "pip",
                    "sources": [
                        {
                            "source_id": first_id,
                            "pip_size_percent": 46,
                            "pip_x": 0.3,
                            "pip_y": 0.7,
                            "opacity": 0.4,
                            "sync_offset_ms": 140,
                        },
                        {
                            "source_id": second_id,
                            "pip_size_percent": 58,
                            "pip_x": 0.12,
                            "pip_y": 0.22,
                            "opacity": 0.85,
                            "sync_offset_ms": -90,
                        },
                    ],
                },
            },
        )

        assert state["project"]["export"]["output_path"] == str(output_path)
        assert captured == [[(first_id, 46, 0.3, 0.7, 0.4, 140), (second_id, 58, 0.12, 0.22, 0.85, -90)]]
    finally:
        server.shutdown()


def test_export_path_preset_and_custom_mode_contract_persists(tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        typed_path = tmp_path / "typed-output.mp4"
        state = _post_json(f"{server.url}api/export/settings", {"output_path": str(typed_path)})
        assert state["project"]["export"]["output_path"] == str(typed_path)
        assert state["project"]["export"]["preset"] == "source"

        state = _post_json(f"{server.url}api/export/preset", {"preset": "universal_vertical"})
        assert state["project"]["export"]["output_path"] == str(typed_path)
        assert state["project"]["export"]["preset"] == "universal_vertical"
        assert state["project"]["export"]["target_width"] == 1080
        assert state["project"]["export"]["target_height"] == 1920

        state = _post_json(f"{server.url}api/export/settings", {"video_bitrate_mbps": 12.5})
        assert state["project"]["export"]["preset"] == "custom"
        assert state["project"]["export"]["video_bitrate_mbps"] == 12.5
        assert state["project"]["export"]["output_path"] == str(typed_path)

        bundle_path = tmp_path / "export-path-project"
        _post_json(f"{server.url}api/project/save", {"path": str(bundle_path)})
        _post_json(f"{server.url}api/project/new", {})
        reopened = _post_json(f"{server.url}api/project/open", {"path": str(bundle_path)})
        assert reopened["project"]["export"]["preset"] == "custom"
        assert reopened["project"]["export"]["video_bitrate_mbps"] == 12.5
        assert reopened["project"]["export"]["output_path"] == str(typed_path)
    finally:
        server.shutdown()


def test_project_open_defaults_blank_export_output_path_to_project_output_folder(tmp_path: Path) -> None:
    controller = ProjectController()
    project_path = tmp_path / "project-output-default.ssproj"
    controller.save_project(str(project_path))
    project_json = project_path / "project.json"
    payload = json.loads(project_json.read_text(encoding="utf-8"))
    payload.setdefault("export", {})["output_path"] = ""
    project_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        opened = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        assert opened["project"]["export"]["output_path"] == str(project_path / "Output" / "output.mp4")
    finally:
        server.shutdown()
