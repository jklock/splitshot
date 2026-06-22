from __future__ import annotations

import json
import re
import urllib.request
from types import SimpleNamespace
from pathlib import Path

from splitshot.browser.state import browser_state
from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import MergeLayout, MergeSource, ProjectStage, SecondarySourceAnalysis, VideoAsset
from splitshot.media.probe import probe_video
from splitshot.ui.controller import ProjectController


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "app.js"
SHELL_RUNTIME_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "lib" / "shell-runtime.js"
EXPORT_PANE_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "panes" / "export-pane.js"
MERGE_PANE_JS = REPO_ROOT / "src" / "splitshot" / "browser" / "static" / "panes" / "merge-pane.js"


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
    shell_runtime_source = SHELL_RUNTIME_JS.read_text(encoding="utf-8")
    export_pane_source = EXPORT_PANE_JS.read_text(encoding="utf-8")
    merge_pane_source = MERGE_PANE_JS.read_text(encoding="utf-8")
    drag_body = _function_body(source, "endMergePreviewDrag")
    begin_drag_body = _function_body(source, "beginMergePreviewDrag")
    move_drag_body = _function_body(source, "moveMergePreviewDrag")

    assert 'import { createMergePane } from "./panes/merge-pane.js";' in source
    assert 'import { createExportPane } from "./panes/export-pane.js";' in source
    assert "mergePane = createMergePane({" in source
    assert "exportPane = createExportPane({" in source
    assert "LEGACY_WIRE_EVENTS_SOURCE_ANCHORS" not in source
    assert '$("export-video").addEventListener("click", async () => {' not in source
    assert "function previewFrameClientRect(video, container) {" in source
    assert 'const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();' in begin_drag_body
    assert 'const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();' in move_drag_body
    assert "scheduleMergeSourceCommit(mergeSourcePositionPayload(drag.sourceId, source))" in drag_body
    assert 'callApi("/api/merge/source"' not in drag_body
    assert '$("export-video").addEventListener("click"' not in shell_runtime_source
    assert '$("show-export-log")?.addEventListener("click", openExportLogModal);' in shell_runtime_source
    assert "clearCurrentExportLogState();" in _function_body(source, "beginProcessing")
    assert 'state.project.export.last_error = null;' in _function_body(source, "clearCurrentExportLogState")
    assert 'if (mergePreview && merge.layout === "pip" && mergeSources.length > 0) {' in source
    assert 'media.style.opacity = String(currentSourceOpacity(source));' in source
    assert 'input.dataset.mergeSourceField = "opacity";' in source
    assert "These values are saved per item and take effect in compose layout and export timing." in source

    assert "export function createMergePane({" in merge_pane_source
    assert "function renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue) {" in merge_pane_source
    assert "function renderMergeMediaList() {" in merge_pane_source
    assert "function readMergePayload() {" in merge_pane_source
    assert 'callApi("/api/merge/source/analyze", { source_id: sourceId });' not in merge_pane_source
    assert "Re-run beep sync" not in merge_pane_source
    assert "Analyze beep sync" not in merge_pane_source
    assert "supports_sync_analysis" not in merge_pane_source
    assert "function syncPreviewPlaybackToTarget(preview, target, targetPlaybackRate, paused) {" in source
    assert "const target = mergePreviewTargetTime(primary.currentTime, mergeSourceById(sourceId));" in source
    assert "const target = mergePreviewTargetTime(primary.currentTime, activeSource);" in source
    assert "SECONDARY_PREVIEW_ACTIVE_SEEK_THRESHOLD_S = 0.16" in source
    assert "SECONDARY_PREVIEW_MAX_PLAYBACK_RATE_DELTA = 0.08" in source
    assert "popup_template: normalizePopupTemplate(state?.project?.popup_template || {})," in source
    assert "opacity: currentSourceOpacity(source)," in source

    assert "export function createExportPane({" in export_pane_source
    assert "function readExportLayoutPayload() {" in export_pane_source
    assert "function readExportSettingsPayload() {" in export_pane_source
    assert "function scheduleExportLayoutApply() {" in export_pane_source
    assert "function scheduleExportSettingsApply() {" in export_pane_source


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


def test_added_media_import_does_not_enable_merge_and_tracks_each_secondary_waveform(
    synthetic_video_factory,
    monkeypatch,
) -> None:
    primary_path = Path(synthetic_video_factory(name="merge-audit-primary", resolution=(320, 180)))
    second_path = Path(synthetic_video_factory(name="merge-audit-second", resolution=(320, 180)))
    third_path = Path(synthetic_video_factory(name="merge-audit-third", resolution=(320, 180)))
    controller = ProjectController()
    controller.project.primary_video = probe_video(primary_path)
    controller.project.merge.enabled = False

    analysis_runs: list[str] = []

    def fake_analyze(path: str, threshold: float, settings) -> SimpleNamespace:
        analysis_runs.append(path)
        index = len(analysis_runs)
        return SimpleNamespace(
            beep_time_ms=1000 + (index * 25),
            waveform=[0.1 * index, 0.2 * index, 0.3 * index],
            shots=[],
            review_suggestions=[],
            sample_rate=22050,
        )

    monkeypatch.setattr("splitshot.ui.controller._run_analyze_video_audio", fake_analyze)
    monkeypatch.setattr("splitshot.ui.controller.compute_sync_offset", lambda primary, secondary: int((secondary or 0) - (primary or 0)))

    controller.add_merge_source(str(second_path))
    controller.add_merge_source(str(third_path))

    assert controller.project.merge.enabled is False
    assert [entry.source_id for entry in controller.project.analysis.secondary_sources] == [
        source.id for source in controller.project.merge_sources
    ]
    assert controller.project.analysis.analyzed_secondary_source_id == controller.project.merge_sources[-1].id
    assert controller.project.analysis.waveform_secondary == [0.2, 0.4, 0.6]
    assert [entry.sync_offset_ms for entry in controller.project.analysis.secondary_sources] == [1025, 1050]


def test_stage_set_primary_promotes_existing_added_media(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="stage-primary-base", resolution=(320, 180)))
    second_path = Path(synthetic_video_factory(name="stage-primary-second", resolution=(320, 180)))
    third_path = Path(synthetic_video_factory(name="stage-primary-third", resolution=(320, 180)))
    controller = ProjectController()
    stage = ProjectStage(label="Stage 1", order_index=1)
    controller.project.stages = [stage]
    controller.project.active_stage_id = stage.id
    controller.project.primary_video = probe_video(primary_path)
    controller.project.merge_sources = [
        MergeSource(asset=probe_video(second_path), sync_offset_ms=25),
        MergeSource(asset=probe_video(third_path), sync_offset_ms=50),
    ]
    controller._sync_project_to_active_stage()
    promote_id = controller.project.merge_sources[1].id

    controller.set_stage_primary_from_existing(stage.id, promote_id)

    assert controller.project.primary_video.path == str(third_path)
    assert controller.project.active_stage.primary_media.path == str(third_path)
    added_paths = [source.asset.path for source in controller.project.merge_sources]
    assert str(third_path) not in added_paths
    assert str(primary_path) in added_paths
    assert len(controller.project.merge_sources) == 2


def test_browser_state_exposes_all_secondary_waveforms() -> None:
    controller = ProjectController()
    controller.project.analysis.beep_time_ms_primary = 1000
    controller.project.primary_video.path = "/tmp/primary.mp4"
    controller.project.merge.enabled = False
    controller.project.merge_sources = [
        MergeSource(asset=VideoAsset(path="/tmp/added-one.mp4", duration_ms=1000, width=320, height=180, media_kind="video")),
        MergeSource(asset=VideoAsset(path="/tmp/added-two.mp4", duration_ms=1000, width=320, height=180, media_kind="video")),
    ]
    controller.project.merge_sources[0].asset.media_kind = "video"
    controller.project.merge_sources[0].asset.is_still_image = False
    controller.project.merge_sources[1].asset.media_kind = "video"
    controller.project.merge_sources[1].asset.is_still_image = False
    controller.project.analysis.secondary_sources = [
        SecondarySourceAnalysis(
            source_id=controller.project.merge_sources[0].id,
            beep_time_ms=1020,
            sync_offset_ms=20,
            analysis_status="ready",
            analysis_message="Secondary beep detected.",
            sync_source="auto",
            waveform=[0.1, 0.2],
        ),
        SecondarySourceAnalysis(
            source_id=controller.project.merge_sources[1].id,
            beep_time_ms=980,
            sync_offset_ms=-20,
            analysis_status="ready",
            analysis_message="Secondary beep detected.",
            sync_source="auto",
            waveform=[0.3, 0.4, 0.5],
        ),
    ]
    controller.project.analysis.analyzed_secondary_source_id = controller.project.merge_sources[1].id
    controller.project.analysis.waveform_secondary = [0.3, 0.4, 0.5]
    controller.project.analysis.sync_offset_ms = -20

    payload = browser_state(controller.project, "Ready.")
    merge_sources = payload["project"]["merge_sources"]

    assert [item["waveform_sample_count"] for item in merge_sources] == [2, 3]
    assert all(item["supports_sync_analysis"] is True for item in merge_sources)
    assert payload["project"]["analysis"]["secondary_sources"][0]["source_id"] == controller.project.merge_sources[0].id
    assert payload["project"]["analysis"]["secondary_sources"][1]["source_id"] == controller.project.merge_sources[1].id


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
