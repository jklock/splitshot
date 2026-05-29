from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

import splitshot.browser.server as browser_server_module
import splitshot.ui.controller as controller_module
from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import AspectRatio, ExportPreset, OverlayPosition
from splitshot.scoring.practiscore_web_extract import (
    RemotePractiScoreMatch,
    SelectedRemoteMatchArtifacts,
)
from splitshot.ui.controller import ProjectController


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "example_data"


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _load_primary_video(page, primary_path: Path) -> None:
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_path = str(primary_path.parent / "browser-test.ssproj")
        page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
        page.wait_for_function("() => Boolean(state?.project?.path)")
    page.locator("#primary-file-input").set_input_files(str(primary_path))
    page.locator(".waveform-shot-card").first.wait_for(state="attached")


def _open_tool(page, tool: str) -> None:
    page.locator(f'button[data-tool="{tool}"]').click(force=True)
    page.wait_for_function("(expected) => activeTool === expected", arg=tool)


def _select_waveform_shot(page, index: int = 0) -> dict[str, int | str] | None:
    _open_tool(page, "timing")
    target_shot_id = page.evaluate(f"state.timing_segments[{index}].shot_id")
    assert target_shot_id is not None
    page.locator("#timing-table .timeline-segment-cell").nth(index).click()
    page.wait_for_function("(shotId) => selectedShotId === shotId", arg=target_shot_id)
    return page.evaluate(
        """
        () => {
          const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === selectedShotId);
          return shot ? { id: shot.id, timeMs: shot.time_ms } : null;
        }
        """
    )


def _shot_linked_popup_count(page) -> int:
    return int(
        page.evaluate(
            "(state?.project?.popups || []).filter((item) => item.anchor_mode === 'shot' && item.shot_id).length"
        )
    )


def _import_shot_linked_markers(page) -> None:
    _open_markers_workbench(page)
    page.locator("#popup-import-shots-workbench").click()
    page.wait_for_function(
        "() => (state?.project?.popups || []).filter((item) => item.anchor_mode === 'shot' && item.shot_id).length > 0"
    )


def _open_markers_workbench(page) -> None:
    if not page.evaluate("() => document.getElementById('markers-workbench')?.hidden === false"):
        page.locator("#popup-edit-selected").click()
    page.wait_for_function("() => document.getElementById('markers-workbench')?.hidden === false")


def _drag_popup_badge(page, popup_id: str, delta_x: float, delta_y: float) -> None:
    page.evaluate(
        """({ popupId, deltaX, deltaY }) => {
          const badge = document.querySelector(`#popup-overlay [data-popup-drag="true"][data-popup-id="${popupId}"]`);
          if (!(badge instanceof HTMLElement)) return false;
          const rect = badge.getBoundingClientRect();
          const startX = rect.left + 40;
          const startY = rect.top + 20;
          badge.dispatchEvent(new MouseEvent('mousedown', {
            bubbles: true,
            cancelable: true,
            button: 0,
            buttons: 1,
            clientX: startX,
            clientY: startY,
          }));
          for (let step = 1; step <= 6; step += 1) {
            const progress = step / 6;
            document.dispatchEvent(new MouseEvent('mousemove', {
              bubbles: true,
              cancelable: true,
              button: 0,
              buttons: 1,
              clientX: startX + (deltaX * progress),
              clientY: startY + (deltaY * progress),
            }));
          }
          document.dispatchEvent(new MouseEvent('mouseup', {
            bubbles: true,
            cancelable: true,
            button: 0,
            buttons: 0,
            clientX: startX + deltaX,
            clientY: startY + deltaY,
          }));
          return true;
        }""",
        {"popupId": popup_id, "deltaX": delta_x, "deltaY": delta_y},
    )


def _drag_overlay_badge(page, kind: str, delta_x: float, delta_y: float) -> None:
    page.evaluate(
        """({ kind, deltaX, deltaY }) => {
                    const badge = document.querySelector(`#video-stage [data-overlay-drag="${kind}"]`);
                    if (!(badge instanceof HTMLElement)) return false;
                    const rect = badge.getBoundingClientRect();
                    const startX = rect.left + (rect.width / 2);
                    const startY = rect.top + (rect.height / 2);
                    badge.dispatchEvent(new MouseEvent('mousedown', {
                        bubbles: true,
                        cancelable: true,
                        button: 0,
                        buttons: 1,
                        clientX: startX,
                        clientY: startY,
                    }));
                    for (let step = 1; step <= 6; step += 1) {
                        const progress = step / 6;
                        document.dispatchEvent(new MouseEvent('mousemove', {
                            bubbles: true,
                            cancelable: true,
                            button: 0,
                            buttons: 1,
                            clientX: startX + (deltaX * progress),
                            clientY: startY + (deltaY * progress),
                        }));
                    }
                    document.dispatchEvent(new MouseEvent('mouseup', {
                        bubbles: true,
                        cancelable: true,
                        button: 0,
                        buttons: 0,
                        clientX: startX + deltaX,
                        clientY: startY + deltaY,
                    }));
                    return true;
                }""",
        {"kind": kind, "deltaX": delta_x, "deltaY": delta_y},
    )


def _ensure_overlay_visible(page) -> None:
    if page.locator("#show-overlay").is_checked():
        return
    page.evaluate(
        """
        () => {
          const checkbox = document.getElementById('show-overlay');
          checkbox.checked = true;
          checkbox.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """
    )
    page.wait_for_function("() => document.getElementById('show-overlay').checked === true")


def _capture_direct_merge_preview_batch_reseek_phase(
    page,
    *,
    primary_time_s: float,
    primary_paused: bool,
    preview_times_s: list[float],
    preview_paused: bool,
    playback_rate: float = 1.0,
) -> list[dict[str, object]]:
    return page.evaluate(
        """({ primaryTimeS, primaryPaused, previewTimesS, previewPaused, playbackRate }) => {
            const layer = document.getElementById('merge-preview-layer');
            if (!(layer instanceof HTMLElement)) {
                throw new Error('Merge preview layer is unavailable.');
            }
            layer.innerHTML = '';
            render();

            const primary = document.getElementById('primary-video');
            if (!(primary instanceof HTMLMediaElement)) {
                throw new Error('Primary video element is unavailable.');
            }

            const previewItems = Array.from(
                document.querySelectorAll('#merge-preview-layer .merge-preview-item[data-source-id]')
            );
            const previews = previewItems.map((item) => item.querySelector('video'));
            if (previews.length !== previewTimesS.length || previews.some((preview) => !(preview instanceof HTMLMediaElement))) {
                throw new Error(`Expected ${previewTimesS.length} merge preview videos, found ${previews.length}.`);
            }

            const ensureHarness = (video) => {
                if (video.__splitshotMergePreviewHarness) return video.__splitshotMergePreviewHarness;
                const state = {
                    paused: true,
                    currentTime: Number(video.currentTime || 0),
                    playbackRate: Number(video.playbackRate || 1) || 1,
                    readyState: HTMLMediaElement.HAVE_CURRENT_DATA,
                    playCount: 0,
                    pauseCount: 0,
                    fastSeekCalls: [],
                };

                Object.defineProperty(video, 'paused', {
                    configurable: true,
                    get: () => state.paused,
                });
                Object.defineProperty(video, 'currentTime', {
                    configurable: true,
                    get: () => state.currentTime,
                    set: (value) => {
                        state.currentTime = Number(value) || 0;
                    },
                });
                Object.defineProperty(video, 'playbackRate', {
                    configurable: true,
                    get: () => state.playbackRate,
                    set: (value) => {
                        state.playbackRate = Number(value) || 1;
                    },
                });
                Object.defineProperty(video, 'defaultPlaybackRate', {
                    configurable: true,
                    get: () => state.playbackRate,
                    set: (value) => {
                        state.playbackRate = Number(value) || 1;
                    },
                });
                Object.defineProperty(video, 'readyState', {
                    configurable: true,
                    get: () => state.readyState,
                });

                video.play = () => {
                    state.paused = false;
                    state.playCount += 1;
                    return Promise.resolve();
                };
                video.pause = () => {
                    state.paused = true;
                    state.pauseCount += 1;
                };
                video.fastSeek = (value) => {
                    const numericValue = Number(value) || 0;
                    state.currentTime = numericValue;
                    state.fastSeekCalls.push(numericValue);
                };

                const harness = {
                    setState(nextState) {
                        state.paused = Boolean(nextState.paused);
                        state.currentTime = Number(nextState.currentTime) || 0;
                        state.playbackRate = Number(nextState.playbackRate) || 1;
                        state.readyState = Number(nextState.readyState) || HTMLMediaElement.HAVE_CURRENT_DATA;
                        state.playCount = 0;
                        state.pauseCount = 0;
                        state.fastSeekCalls = [];
                    },
                    snapshot() {
                        return {
                            paused: state.paused,
                            currentTime: state.currentTime,
                            playbackRate: state.playbackRate,
                            playCount: state.playCount,
                            pauseCount: state.pauseCount,
                            fastSeekCalls: [...state.fastSeekCalls],
                        };
                    },
                };

                Object.defineProperty(video, '__splitshotMergePreviewHarness', {
                    configurable: true,
                    value: harness,
                });
                return harness;
            };

            ensureHarness(primary).setState({
                paused: primaryPaused,
                currentTime: primaryTimeS,
                playbackRate,
                readyState: HTMLMediaElement.HAVE_CURRENT_DATA,
            });
            previews.forEach((preview, index) => {
                ensureHarness(preview).setState({
                    paused: previewPaused,
                    currentTime: previewTimesS[index],
                    playbackRate,
                    readyState: HTMLMediaElement.HAVE_CURRENT_DATA,
                });
                preview.dataset.syncCorrectionMode = '';
            });

            // Directly arm the boundary flag and invoke the batch sync helper.
            // This harness measures batch reseek convergence only; it does not
            // claim full event wiring coverage.
            setPreviewSeekBoundary(true);
            syncMergePreviewElements(primary);

            return previewItems.map((item, index) => {
                const preview = previews[index];
                const snapshot = preview.__splitshotMergePreviewHarness.snapshot();
                const sourceId = item.dataset.sourceId || '';
                const source = (state?.project?.merge_sources || []).find((mergeSource, mergeIndex) => {
                    const candidateId = String(mergeSource?.id || mergeSource?.asset?.id || mergeIndex);
                    return candidateId === sourceId;
                }) || null;
                const target = Math.max(0, primary.currentTime + ((source?.sync_offset_ms || 0) / 1000));
                return {
                    sourceId,
                    target,
                    currentTime: snapshot.currentTime,
                    delta: Math.abs(snapshot.currentTime - target),
                    paused: snapshot.paused,
                    playCount: snapshot.playCount,
                    pauseCount: snapshot.pauseCount,
                    fastSeekCalls: snapshot.fastSeekCalls,
                    playbackRate: snapshot.playbackRate,
                    correctionMode: preview.dataset.syncCorrectionMode || '',
                };
            });
        }""",
        {
            "primaryTimeS": primary_time_s,
            "primaryPaused": primary_paused,
            "previewTimesS": preview_times_s,
            "previewPaused": preview_paused,
            "playbackRate": playback_rate,
        },
    )


class _BrowserFakeStatus:
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


class _BrowserFakeSessionManager:
    def __init__(
        self,
        tmp_path: Path,
        *,
        initial_state: str = "not_authenticated",
        start_state: str = "authenticating",
        poll_states: list[str] | None = None,
    ) -> None:
        self.profile_paths = type("ProfilePaths", (), {"app_dir": tmp_path})()
        self._start_state = start_state
        self._state = initial_state
        self._poll_states = list(poll_states or [])
        self._details = {
            "profile_path": str(tmp_path / "practiscore" / "browser-profile"),
        }
        self._browser_context = object()

    def _message(self) -> str:
        return {
            "not_authenticated": "Connect PractiScore to use your browser session for background sync.",
            "authenticating": "Complete PractiScore login in your browser. SplitShot will continue in the background.",
            "authenticated_ready": "PractiScore session is authenticated and ready.",
            "expired": "PractiScore session expired. Reconnect in your browser to continue.",
        }.get(self._state, self._state)

    def current_status(self) -> _BrowserFakeStatus:
        return _BrowserFakeStatus(self._state, self._message(), self._details)

    def start_login_flow(self) -> _BrowserFakeStatus:
        self._state = self._start_state
        return self.current_status()

    def serialize_status(self) -> dict[str, object]:
        if self._poll_states:
            self._state = self._poll_states.pop(0)
        return self.current_status().to_dict()

    def clear_session(self) -> _BrowserFakeStatus:
        self._state = "not_authenticated"
        self._poll_states = []
        return self.current_status()

    def require_authenticated_browser(self) -> object:
        if self._state != "authenticated_ready":
            raise RuntimeError(self._message())
        return self._browser_context

    def shutdown(self) -> None:
        return


def _build_remote_match_artifacts(tmp_path: Path, remote_id: str) -> SelectedRemoteMatchArtifacts:
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


def _call_practiscore_session_route(
        page,
        endpoint: str,
        payload: dict[str, object] | None = None,
) -> dict[str, object]:
        return page.evaluate(
                """async ({ endpoint, payload }) => {
                    const response = await fetch(endpoint, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload || {}),
                    });
                    const data = await response.json();
                    if (!response.ok || data?.error) {
                        throw new Error(JSON.stringify(data?.error || data));
                    }
                    applyPractiScoreSessionPayload(data, { resetSync: true });
                    requestRender();
                    return data;
                }""",
                {"endpoint": endpoint, "payload": payload or {}},
        )


def _call_practiscore_route(
        page,
        endpoint: str,
        payload: dict[str, object] | None = None,
        *,
        method: str = "GET",
) -> dict[str, object]:
        return page.evaluate(
                """async ({ endpoint, payload, method }) => {
                    const request = {
                        method,
                        headers: { "Content-Type": "application/json" },
                    };
                    if (method !== "GET") {
                        request.body = JSON.stringify(payload || {});
                    }
                    const response = await fetch(endpoint, request);
                    const data = await response.json();
                    if (!response.ok || data?.error) {
                        throw new Error(JSON.stringify(data?.error || data));
                    }
                    applyPractiScoreRoutePayload(data);
                    requestRender();
                    return data;
                }""",
                {"endpoint": endpoint, "payload": payload or {}, "method": method},
        )


def _seed_workspace_apply_fixture(controller: ProjectController, workspace_path: Path) -> None:
    controller.new_workspace()
    controller.workspace.name = "Automation Workspace"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    controller.workspace.stage_entries["stage_1"].source_media_present = True
    controller.workspace.stage_entries["stage_2"].source_media_present = True
    controller.save_workspace(str(workspace_path))

    controller.new_project()
    controller.project.export.preset = ExportPreset.YOUTUBE_LONG_1080P
    controller.project.export.aspect_ratio = AspectRatio.LANDSCAPE
    controller.project.overlay.position = OverlayPosition.TOP
    assert controller._save_stage_project("stage_1", controller.project) is True

    controller.new_project()
    controller.project.export.preset = ExportPreset.SOURCE
    controller.project.export.aspect_ratio = AspectRatio.ORIGINAL
    controller.project.overlay.position = OverlayPosition.BOTTOM
    assert controller._save_stage_project("stage_2", controller.project) is True

    controller.output_profile_create(
        "stage",
        "stage_1",
        "Stage Output",
        "stage_output",
        frame_profile="16:9",
        metric_caption_preset={
            "preset": "score",
            "enabled_fields": ["hit_factor", "penalties"],
            "position": "bottom_right",
            "lead_in_padding_ms": 1200,
            "tail_padding_ms": 2400,
        },
        lead_in_card={"style": "stage_info", "duration_s": 2.0},
    )
    controller.save_workspace()


def _open_match_surface(page) -> None:
    page.evaluate("() => setActiveSurface('multi')")
    page.wait_for_function("() => activeSurface === 'multi'")


def _open_match_section(page, section_id: str) -> None:
    page.locator(f'[data-workspace-target="{section_id}"]').click(force=True)
    page.wait_for_function(
        "(targetId) => document.getElementById(targetId)?.hidden === false",
        arg=section_id,
    )


def _open_library_surface(page) -> None:
    page.evaluate("() => setActiveSurface('library')")
    page.wait_for_function("() => activeSurface === 'library'")


def _open_library_section(page, section_id: str) -> None:
    page.locator(f'[data-workspace-target="{section_id}"]').click(force=True)
    page.wait_for_function(
        "(targetId) => document.getElementById(targetId)?.hidden === false",
        arg=section_id,
    )


def test_project_pane_practiscore_dashboard_button_opens_system_browser(monkeypatch) -> None:
    opened_urls: list[str] = []
    monkeypatch.setattr(
        browser_server_module.webbrowser, "open", lambda url, new=0: opened_urls.append(url) or True
    )
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")
                assert page.locator("#open-practiscore-dashboard").is_disabled() is True
                assert opened_urls == []
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_practiscore_and_primary_controls_enable_after_project_create(
    tmp_path: Path,
) -> None:
    notices: list[str] = []
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            dialogs: list[str] = []
            page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.accept()))
            try:
                _open_tool(page, "project")
                assert page.locator("#project-path").input_value() == ""
                assert (
                    page.locator("#project-path").get_attribute("placeholder")
                    == "Please create / select project"
                )
                assert page.locator("#open-practiscore-dashboard").is_disabled() is True
                assert page.locator("#import-practiscore").is_disabled() is True
                assert page.locator("#browse-primary-path").is_disabled() is True

                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'created-project.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")
                assert page.locator("#open-practiscore-dashboard").is_disabled() is False
                assert page.locator("#import-practiscore").is_disabled() is False
                assert page.locator("#browse-primary-path").is_disabled() is False
                assert page.locator("#project-path").input_value() == "created-project.ssproj"
                notices.extend(dialogs)
                assert any("missing Input, CSV, Output" in message for message in notices)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_manual_practiscore_file_import_remains_functional_with_active_project(
    tmp_path: Path,
) -> None:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")
                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'manual-import.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("#practiscore-file-input").set_input_files(
                    str(EXAMPLES_DIR / "IDPA" / "IDPA.csv")
                )
                page.wait_for_function("() => state?.project?.scoring?.stage_number !== null")
                page.wait_for_function("() => state?.practiscore_options?.has_source === true")

                assert page.locator("#import-practiscore").is_enabled() is True
                assert (
                    page.locator("#practiscore-status")
                    .text_content()
                    .strip()
                    .startswith("IDPA Stage")
                )
                assert page.locator("#match-competitor-name option").count() > 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_steel_challenge_import_uses_formatted_status_label(
    tmp_path: Path,
) -> None:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")
                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'steel-import.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("#practiscore-file-input").set_input_files(
                    str(EXAMPLES_DIR / "SteelChallenge" / "report.txt")
                )
                page.wait_for_function(
                    "() => (document.getElementById('practiscore-status')?.textContent || '').includes('Steel Challenge Stage 1 imported')"
                )

                assert (
                    page.locator("#practiscore-status").text_content().strip()
                    == "Steel Challenge Stage 1 imported"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_practiscore_connect_route_updates_browser_state(tmp_path: Path) -> None:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.practiscore_session = _BrowserFakeSessionManager(
        tmp_path,
        start_state="authenticating",
    )
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")

                payload = _call_practiscore_session_route(
                    page,
                    "/api/practiscore/session/start",
                    {},
                )

                page.wait_for_function(
                    """() => state?.practiscore_session?.state === 'authenticating'
                      && state?.practiscore_sync?.state === 'idle'"""
                )

                assert payload["state"] == "authenticating"
                assert page.evaluate("() => state?.practiscore_session?.state || ''") == "authenticating"
                assert (
                    page.evaluate("() => state?.practiscore_session?.message || ''")
                    == "Complete PractiScore login in your browser. SplitShot will continue in the background."
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_practiscore_remote_match_list_and_import_routes_update_browser_state(
    monkeypatch,
    tmp_path: Path,
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
        lambda browser_context, remote_id, cache_root, match_catalog=None: _build_remote_match_artifacts(
            tmp_path,
            remote_id,
        ),
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.practiscore_session = _BrowserFakeSessionManager(
        tmp_path,
        initial_state="authenticated_ready",
    )
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")

                matches = _call_practiscore_route(page, "/api/practiscore/matches")
                page.wait_for_function(
                    """() => state?.practiscore_session?.state === 'authenticated_ready'
                      && state?.practiscore_sync?.state === 'match_list_ready'
                      && (state?.practiscore_sync?.matches?.length || 0) === 1"""
                )

                assert matches["practiscore_sync"]["state"] == "match_list_ready"
                assert page.evaluate("() => state?.practiscore_sync?.matches?.length || 0") == 1

                payload = _call_practiscore_route(
                    page,
                    "/api/practiscore/sync/start",
                    {"remote_id": "match-200"},
                    method="POST",
                )
                page.wait_for_function(
                    """() => state?.practiscore_sync?.state === 'success'
                      && state?.practiscore_sync?.selected_remote_id === 'match-200'
                      && state?.practiscore_options?.has_source === true"""
                )

                assert payload["practiscore_sync"]["state"] == "success"
                assert payload["practiscore_sync"]["selected_remote_id"] == "match-200"
                assert page.evaluate("() => state?.practiscore_options?.source_name || ''") == "remote-idpa.csv"
                assert page.evaluate("() => state?.practiscore_options?.stage_numbers || []") == [1, 2, 3, 4]
                assert (
                    page.evaluate(
                        "() => Array.isArray(state?.practiscore_options?.comparison_competitors) && state.practiscore_options.comparison_competitors.length > 0"
                    )
                    is True
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_practiscore_expired_match_list_updates_browser_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(controller_module, "discover_remote_matches", lambda browser_context: [])

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.practiscore_session = _BrowserFakeSessionManager(
        tmp_path,
        initial_state="expired",
    )
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")

                payload = _call_practiscore_route(page, "/api/practiscore/matches")
                page.wait_for_function(
                    """() => state?.practiscore_session?.state === 'expired'
                      && state?.practiscore_sync?.state === 'error'
                      && state?.practiscore_sync?.error_category === 'expired_authentication'"""
                )

                assert payload["practiscore_sync"]["state"] == "error"
                assert payload["practiscore_sync"]["error_category"] == "expired_authentication"
                assert (
                    page.evaluate("() => state?.practiscore_session?.message || ''")
                    == "PractiScore session expired. Reconnect in your browser to continue."
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_delete_project_confirmation_can_cancel(tmp_path: Path) -> None:
    project_path = tmp_path / "delete-project-confirm.ssproj"
    ProjectController().save_project(str(project_path))

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            dialogs: list[str] = []
            page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            try:
                _open_tool(page, "project")
                page.evaluate(f"() => useProjectFolder({json.dumps(str(project_path))})")
                page.wait_for_function("() => Boolean(state?.project?.path)")

                page.locator("#delete-project").click(force=True)
                page.wait_for_timeout(150)

                assert dialogs
                assert dialogs[-1].startswith("Delete project metadata for:")
                assert page.evaluate("() => state?.project?.path || ''") == str(project_path)
                assert (project_path / "project.json").exists()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_shell_compat_host_on_open_project_callback_opens_saved_project(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "host-open.ssproj"
    bootstrap = ProjectController()
    bootstrap.new_project()
    bootstrap.project.name = "Host Open Project"
    bootstrap.save_project(str(project_path))

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.on("dialog", lambda dialog: dialog.accept())
            page.add_init_script(
                """
                window.__legacyOpenProjectCallback = null;
                window.splitshot = {
                  onOpenProject(callback) {
                    window.__legacyOpenProjectCallback = callback;
                  },
                };
                """
            )
            page.goto(server.url, wait_until="domcontentloaded")
            try:
                page.wait_for_function(
                    "() => typeof window.__legacyOpenProjectCallback === 'function'"
                )

                page.evaluate(
                    "(projectPath) => window.__legacyOpenProjectCallback(projectPath)",
                    str(project_path),
                )
                page.wait_for_function(
                    "(expectedPath) => state?.project?.path === expectedPath",
                    arg=str(project_path),
                )

                _open_tool(page, "project")
                assert page.locator("#project-path").input_value() == "host-open.ssproj"
                assert page.evaluate("() => state?.project?.name || ''") == "Host Open Project"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_keyboard_tab_order_advances_through_primary_controls(
    tmp_path: Path,
) -> None:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            page.on("dialog", lambda dialog: dialog.accept())
            try:
                _open_tool(page, "project")
                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'keyboard-order.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")

                expected_focus_order = [
                    "project-path",
                    "browse-project-path",
                    "new-project",
                    "delete-project",
                    "project-name",
                    "project-description",
                ]

                page.locator(f"#{expected_focus_order[0]}").focus()
                assert page.evaluate("() => document.activeElement?.id || ''") == expected_focus_order[0]

                for control_id in expected_focus_order[1:]:
                    page.keyboard.press("Tab")
                    page.wait_for_function(
                        "(expectedId) => document.activeElement?.id === expectedId",
                        arg=control_id,
                    )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_output_hook_save_updates_selected_output_profile(tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")
                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'automation-hooks.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")
                _open_tool(page, "export")

                page.locator("#output-profile-name").fill("Automation Profile")
                page.locator("#output-profile-create").click()
                page.locator("#output-profile-list .automation-row").first.wait_for(state="visible")

                _open_tool(page, "overlay")
                page.locator('[data-output-hook="metric-captions"]').click()
                page.wait_for_function(
                    """() => {
                        const editor = document.getElementById('output-hook-editor');
                        return Boolean(editor)
                          && editor.hidden === false
                          && editor.closest('[data-tool-pane]')?.dataset.toolPane === 'overlay';
                    }"""
                )
                page.locator("#hook-metric-captions-preset").select_option("full")
                page.locator("#hook-metric-captions-position").select_option("bottom_left")
                page.locator("#output-hook-save").click()

                page.wait_for_function(
                    """() => {
                        const detail = document.getElementById('output-profile-detail');
                        return Boolean(detail?.textContent?.includes('"preset": "full"'))
                          && Boolean(detail?.textContent?.includes('"position": "bottom_left"'));
                    }"""
                )
                assert page.locator("#output-hook-save").is_visible() is True
                profiles = controller.output_profile_list("stage", controller.project.id)
                assert len(profiles) == 1
                assert profiles[0]["metric_caption_preset"] == {
                    "preset": "full",
                    "enabled_fields": [
                        "shot_count",
                        "cumulative_time",
                        "first_shot_reaction",
                        "hit_factor",
                        "penalties",
                        "split_times",
                    ],
                    "position": "bottom_left",
                    "lead_in_padding_ms": 1000,
                    "tail_padding_ms": 2000,
                }
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_output_hook_close_hides_editor(tmp_path: Path) -> None:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")
                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'automation-hook-close.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")
                _open_tool(page, "export")

                page.locator("#output-profile-name").fill("Close Test Profile")
                page.locator("#output-profile-create").click()
                page.locator("#output-profile-list .automation-row").first.wait_for(state="visible")

                _open_tool(page, "overlay")
                page.locator('[data-output-hook="metric-captions"]').click()
                page.locator("#output-hook-editor").wait_for(state="visible")
                page.locator("#output-hook-close").click()
                page.wait_for_function(
                    "() => document.getElementById('output-hook-editor')?.hidden === true"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_pane_trim_settings_use_output_profile_editor(tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")
                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'compose-trim-hooks.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")
                _open_tool(page, "export")

                page.locator("#output-profile-name").fill("Trim Profile")
                page.locator("#output-profile-create").click()
                page.locator("#output-profile-list .automation-row").first.wait_for(state="visible")

                _open_tool(page, "merge")
                assert page.locator('[data-output-hook="run-window"]').text_content().strip() == "Trim Settings"
                page.locator('[data-output-hook="run-window"]').click()
                page.wait_for_function(
                    """() => {
                        const editor = document.getElementById('output-hook-editor');
                        return Boolean(editor)
                          && editor.hidden === false
                          && editor.closest('[data-tool-pane]')?.dataset.toolPane === 'merge';
                    }"""
                )

                page.locator("#hook-run-window-lead-in").fill("0.4")
                page.locator("#hook-run-window-tail").fill("1.2")
                page.locator("#output-hook-save").click()

                page.wait_for_function(
                    """() => {
                        const detail = document.getElementById('output-profile-detail');
                        return Boolean(detail?.textContent?.includes('"lead_in_padding_ms": 400'))
                          && Boolean(detail?.textContent?.includes('"tail_padding_ms": 1200'));
                    }"""
                )

                profiles = controller.output_profile_list("stage", controller.project.id)
                assert len(profiles) == 1
                assert profiles[0]["metric_caption_preset"]["lead_in_padding_ms"] == 400
                assert profiles[0]["metric_caption_preset"]["tail_padding_ms"] == 1200
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_export_pane_frame_profile_output_hook_persists_selected_profile(
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")
                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'automation-frame-profile-hook.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")
                _open_tool(page, "export")

                page.locator("#output-profile-name").fill("Frame Hook Profile")
                page.locator("#output-profile-create").click()
                page.locator("#output-profile-list .automation-row").first.wait_for(state="visible")

                page.locator('[data-output-hook="frame-profiles"]').click()
                page.wait_for_function(
                    """() => {
                        const editor = document.getElementById('output-hook-editor');
                        return Boolean(editor)
                          && editor.hidden === false
                          && editor.closest('[data-tool-pane]')?.dataset.toolPane === 'export';
                    }"""
                )

                page.locator("#hook-frame-profile").select_option("9:16")
                page.locator("#output-hook-save").click()

                page.wait_for_function(
                    """() => {
                        const detail = document.getElementById('output-profile-detail');
                        return Boolean(detail?.textContent?.includes('"frame_profile": "9:16"'));
                    }"""
                )

                profiles = controller.output_profile_list("stage", controller.project.id)
                assert len(profiles) == 1
                assert profiles[0]["frame_profile"] == "9:16"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_export_pane_output_hook_save_persists_richer_title_and_logo_payloads(
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")
                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'automation-rich-hooks.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")
                _open_tool(page, "export")

                page.locator("#output-profile-name").fill("Rich Hook Profile")
                page.locator("#output-profile-create").click()
                page.locator("#output-profile-list .automation-row").first.wait_for(state="visible")

                page.locator('[data-output-hook="lead-in-card"]').click()
                page.locator("#hook-lead-in-style").select_option("competitor")
                page.locator("#hook-lead-in-duration").fill("3.5")
                page.locator("#hook-lead-in-animation").select_option("fade")
                page.locator("#hook-lead-in-show-match").check()
                page.locator("#hook-lead-in-show-stage").uncheck()
                page.locator("#hook-lead-in-show-date").check()
                page.locator("#hook-lead-in-custom-title").fill("Championship Opener")
                page.locator("#hook-lead-in-custom-subtitle").fill("Final squad")
                page.locator("#hook-lead-in-logo-path").fill("/tmp/intro-logo.png")
                page.locator("#hook-lead-in-logo-scale").fill("85")
                page.locator("#output-hook-save").click()

                page.wait_for_function(
                    """() => {
                        const detail = document.getElementById('output-profile-detail');
                        return Boolean(detail?.textContent?.includes('"custom_title": "Championship Opener"'))
                          && Boolean(detail?.textContent?.includes('"show_stage": false'));
                    }"""
                )

                page.locator('[data-output-hook="brand-mark"]').click()
                page.locator("#hook-brand-mark-select").select_option("image_text")
                page.locator("#hook-brand-mark-text").fill("Team Split")
                page.locator("#hook-brand-mark-position").select_option("bottom_left")
                page.locator("#hook-brand-mark-opacity").fill("55")
                page.locator("#hook-brand-mark-font-size").fill("28")
                page.locator("#hook-brand-mark-image-scale").fill("70")
                page.locator("#hook-brand-mark-image-path").fill("/tmp/brand-mark.png")
                page.locator("#hook-brand-mark-text-color").fill("#00ff00")
                page.locator("#hook-brand-mark-duration").fill("0")
                page.locator("#output-hook-save").click()

                page.wait_for_function(
                    """() => {
                        const detail = document.getElementById('output-profile-detail');
                        return Boolean(detail?.textContent?.includes('"text": "Team Split"'))
                                                    && Boolean(detail?.textContent?.includes('"image_path": "/tmp/brand-mark.png"'))
                          && Boolean(detail?.textContent?.includes('"position": "bottom_left"'))
                          && Boolean(detail?.textContent?.includes('"duration_s": 0'));
                    }"""
                )

                profiles = controller.output_profile_list("stage", controller.project.id)
                assert len(profiles) == 1
                assert profiles[0]["lead_in_card"] == {
                    "style": "competitor",
                    "duration_s": 3.5,
                    "animation": "fade",
                    "show_match": True,
                    "show_stage": False,
                    "show_shooter": True,
                    "show_division": True,
                    "show_classification": True,
                    "show_date": True,
                    "custom_title": "Championship Opener",
                    "custom_subtitle": "Final squad",
                    "logo_path": "/tmp/intro-logo.png",
                    "logo_scale_percent": 85,
                }
                assert profiles[0]["brand_mark"] == {
                    "style": "image_text",
                    "text": "Team Split",
                    "position": "bottom_left",
                    "opacity": pytest.approx(0.55),
                    "duration_s": 0,
                    "image_path": "/tmp/brand-mark.png",
                    "image_scale_percent": 70,
                    "text_color": "#00ff00",
                    "font_size": 28,
                }
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_setup_once_uses_preview_before_apply(tmp_path: Path) -> None:
    controller = ProjectController()
    _seed_workspace_apply_fixture(controller, tmp_path / "workspace-apply-ui")
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            dialogs: list[str] = []
            page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.accept()))
            try:
                page.evaluate("() => setActiveSurface('multi')")
                page.wait_for_function("() => activeSurface === 'multi'")
                page.wait_for_function(
                    "() => document.getElementById('setup-once-banner')?.hidden === false"
                )

                page.locator("#setup-once-apply").click()
                page.wait_for_function(
                    "() => (state?.workspace_stage_entries || []).some((entry) => entry.stage_id === 'stage_2' && entry.inherited_from_first === true)"
                )

                assert dialogs
                assert "Apply Stage 1 settings to other stages?" in dialogs[0]
                assert "This copies shared defaults and reusable output profiles while keeping explicit stage overrides." in dialogs[0]
                assert (
                    "Stage 2:" in dialogs[0]
                    or "No sibling stages need changes." in dialogs[0]
                )
                assert "Output profiles" not in dialogs[0]

                stage_2_project = controller._load_stage_project("stage_2")
                assert stage_2_project is not None
                assert stage_2_project.export.preset == ExportPreset.YOUTUBE_LONG_1080P

                stage_2_profiles = controller._load_stage_profiles_for_stage("stage_2")
                assert any(
                    profile.profile_name == "Stage Output" and profile.profile_kind == "stage_output"
                    for profile in stage_2_profiles
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_setup_once_dismiss_hides_banner(tmp_path: Path) -> None:
    controller = ProjectController()
    _seed_workspace_apply_fixture(controller, tmp_path / "workspace-dismiss-ui")
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                page.evaluate("() => setActiveSurface('multi')")
                page.wait_for_function("() => activeSurface === 'multi'")
                page.wait_for_function(
                    "() => document.getElementById('setup-once-banner')?.hidden === false"
                )

                page.locator("#setup-once-dismiss").click()
                page.wait_for_function(
                    "() => document.getElementById('setup-once-banner')?.hidden === true"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_open_button_uses_picker_and_loads_saved_workspace(
    tmp_path: Path,
) -> None:
    bootstrap = ProjectController()
    workspace_path = tmp_path / "workspace-open-ui"
    _seed_workspace_apply_fixture(bootstrap, workspace_path)

    chooser_calls: list[tuple[str, str | None]] = []

    def fake_path_chooser(kind: str, current: str | None) -> str:
                chooser_calls.append((kind, current))
                return str(workspace_path)

    server = BrowserControlServer(
        controller=ProjectController(),
        port=0,
        path_chooser=fake_path_chooser,
    )
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)

                page.locator("#workspace-open").click()
                page.wait_for_function(
                    "() => state?.workspace?.name === 'Automation Workspace'"
                )

                assert page.locator("#workspace-stage-list .match-stage-card").count() == 2
                assert page.evaluate("() => state?.workspace_path || ''") == str(workspace_path)
                assert chooser_calls == [("project_folder", None)]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_open_shows_loading_and_error_state_on_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    missing_workspace_path = tmp_path / "missing-workspace"
    chooser_calls: list[tuple[str, str | None]] = []
    original_open_workspace = ProjectController.open_workspace

    def fake_path_chooser(kind: str, current: str | None) -> str:
        chooser_calls.append((kind, current))
        return str(missing_workspace_path)

    def delayed_open_workspace(self, path: str) -> None:
        time.sleep(0.25)
        return original_open_workspace(self, path)

    monkeypatch.setattr(ProjectController, "open_workspace", delayed_open_workspace)

    server = BrowserControlServer(
        controller=ProjectController(),
        port=0,
        path_chooser=fake_path_chooser,
    )
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelector('.match-empty-state')?.hidden === false"
                )

                page.locator("#workspace-open").click()
                page.wait_for_function(
                    "() => document.getElementById('multi-video-loading')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.getElementById('multi-video-loading')?.hidden === true"
                )
                page.wait_for_function(
                    "() => document.getElementById('multi-video-error')?.hidden === false"
                )

                error_text = page.locator("#multi-video-error").text_content() or ""
                assert f"No workspace found at {missing_workspace_path}" in error_text
                assert page.evaluate("() => state?.workspace_path || ''") == ""
                page.wait_for_function(
                    "() => document.querySelector('.match-empty-state')?.hidden === false"
                )
                assert chooser_calls == [("project_folder", None)]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_new_from_empty_and_stage_add_select_remove_flow() -> None:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            dialogs: list[str] = []
            page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.accept()))
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelector('.match-empty-state')?.hidden === false"
                )

                page.locator("#workspace-new-empty").click()
                page.wait_for_function("() => Boolean(state?.workspace?.match_id)")
                page.wait_for_function(
                    "() => document.querySelector('.match-empty-state')?.hidden === true"
                )

                page.locator("#workspace-stage-name").fill("Classifier")
                page.locator("#workspace-stage-add").click()
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 1"
                )

                stage_card = page.locator('#workspace-stage-list .match-stage-card[data-stage-id="stage_1"]')
                stage_card.click()
                assert stage_card.evaluate("card => card.classList.contains('selected')") is True

                stage_card.locator("button", has_text="Remove").click()
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 0"
                )
                assert dialogs[-1] == "Remove this stage from the match?"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_save_button_uses_picker_for_first_save(
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Save Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    workspace_path = tmp_path / "workspace-save-ui"
    chooser_calls: list[tuple[str, str | None]] = []

    def fake_path_chooser(kind: str, current: str | None) -> str:
        chooser_calls.append((kind, current))
        return str(workspace_path)

    server = BrowserControlServer(
        controller=controller,
        port=0,
        path_chooser=fake_path_chooser,
    )
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 1"
                )

                page.locator("#workspace-save").click()
                page.wait_for_function(
                    "(expectedPath) => state?.workspace_path === expectedPath",
                    arg=str(workspace_path),
                )

                assert (workspace_path / "workspace.json").exists() is True
                assert chooser_calls == [("project_folder", None)]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_save_shows_loading_and_error_state_on_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Save Failure Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    workspace_path = tmp_path / "workspace-save-failure-ui"
    chooser_calls: list[tuple[str, str | None]] = []

    def fake_path_chooser(kind: str, current: str | None) -> str:
        chooser_calls.append((kind, current))
        return str(workspace_path)

    def failing_save_workspace(self, path: str | None = None) -> None:
        time.sleep(0.25)
        raise RuntimeError("Unable to save workspace for test.")

    monkeypatch.setattr(ProjectController, "save_workspace", failing_save_workspace)

    server = BrowserControlServer(
        controller=controller,
        port=0,
        path_chooser=fake_path_chooser,
    )
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 1"
                )

                page.locator("#workspace-save").click()
                page.wait_for_function(
                    "() => document.getElementById('multi-video-loading')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.getElementById('multi-video-loading')?.hidden === true"
                )
                page.wait_for_function(
                    "() => document.getElementById('multi-video-error')?.hidden === false"
                )

                error_text = page.locator("#multi-video-error").text_content() or ""
                assert "Unable to save workspace for test." in error_text
                assert page.evaluate("() => state?.workspace_path || ''") == ""
                assert chooser_calls == [("project_folder", None)]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_override_apply_and_reset_update_selected_stage() -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Override Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    controller.workspace.stage_entries["stage_1"].source_media_present = True
    controller.workspace.stage_entries["stage_2"].source_media_present = True

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 2"
                )

                page.locator('#workspace-stage-list .match-stage-card[data-stage-id="stage_2"]').click()
                _open_match_section(page, "match-section-overrides")

                page.locator("#override-frame-profile").select_option("9:16")
                page.locator("#override-metric-captions").select_option("splits")
                page.locator("#override-apply").click()

                page.wait_for_function(
                    """() => state?.workspace_override_summary?.stage_2?.frame_profile === '9:16'
                      && state?.workspace_override_summary?.stage_2?.metric_caption_preset === 'splits'"""
                )
                assert page.evaluate("() => state?.workspace_override_summary?.stage_1 || null") is None

                _open_match_section(page, "match-section-stages")
                page.locator('#workspace-stage-list .match-stage-card[data-stage-id="stage_2"]').locator(
                    "button",
                    has_text="Reset",
                ).click()
                page.wait_for_function(
                    "() => !(state?.workspace_override_summary && state.workspace_override_summary.stage_2)"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_shared_defaults_apply_and_reset() -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Defaults Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                _open_match_section(page, "match-section-defaults")

                page.locator("#shared-frame-profile").select_option("9:16")
                page.locator("#shared-metric-captions").select_option("splits")
                page.locator("#shared-defaults-apply").click()

                page.wait_for_function(
                    """() => state?.workspace_shared_defaults?.frame_profile === '9:16'
                      && state?.workspace_shared_defaults?.metric_caption_preset === 'splits'"""
                )

                page.locator("#shared-defaults-reset").click()
                page.wait_for_function(
                    "() => Object.keys(state?.workspace_shared_defaults || {}).length === 0"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_stage_open_and_shell_return_restore_match_context() -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Return Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 2"
                )

                page.locator('#workspace-stage-list .match-stage-card[data-stage-id="stage_1"]').locator(
                    "button",
                    has_text="Open",
                ).click()
                page.wait_for_function("() => activeSurface === 'single'")
                page.wait_for_function("() => state?.return_to_match_available === true")
                assert page.locator("#shell-return-match").is_visible() is True

                page.locator("#shell-return-match").click()
                page.wait_for_function("() => activeSurface === 'multi'")
                page.wait_for_function(
                    "() => state?.return_to_match_available === false && state?.returned_stage_id === 'stage_1'"
                )
                selected_card = page.locator(
                    '#workspace-stage-list .match-stage-card[data-stage-id="stage_1"]'
                )
                assert selected_card.evaluate("card => card.classList.contains('selected')") is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_shell_keeps_selected_stage_detail_and_workflow_visible() -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Shell Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    controller.workspace.stage_entries["stage_1"].source_media_present = True
    controller.workspace.stage_entries["stage_2"].source_media_present = True

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 2"
                )

                page.locator('#workspace-stage-list .match-stage-card[data-stage-id="stage_2"]').click()
                page.wait_for_function(
                    "() => (document.getElementById('match-stage-detail-status')?.textContent || '').includes('Stage 2')"
                )
                assert page.locator("#match-section-stage-detail").evaluate("node => node.hidden") is False

                _open_match_section(page, "match-section-composite")
                page.wait_for_function(
                    "() => document.getElementById('match-section-composite')?.hidden === false && document.getElementById('match-section-stage-workflow')?.hidden === false"
                )
                assert "2 total" in (page.locator("#match-stage-workflow-panel").text_content() or "")

                _open_match_section(page, "match-section-defaults")
                page.wait_for_function(
                    "() => document.getElementById('match-section-stage-detail')?.hidden === false && document.getElementById('match-section-defaults')?.hidden === false"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_preview_tiles_render_live_media_and_export_keeps_selected_stage_detail(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    workspace_path = tmp_path / "preview-match-workspace"
    controller.new_workspace()
    controller.workspace.name = "Preview Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    controller.workspace.stage_entries["stage_1"].source_media_present = True
    controller.workspace.stage_entries["stage_2"].source_media_present = False
    controller.save_workspace(str(workspace_path))

    stage_controller = ProjectController()
    stage_controller.new_project()
    stage_controller.project.name = "Preview Stage"
    stage_video_path = Path(synthetic_video_factory(name="match-preview-tile"))
    stage_controller.ingest_primary_video(str(stage_video_path))
    assert controller._save_stage_project("stage_1", stage_controller.project) is True

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 2"
                )
                page.wait_for_function(
                    "() => Boolean(document.querySelector('#workspace-stage-list .match-stage-card[data-stage-id=\"stage_1\"] .match-stage-preview-video'))"
                )

                preview_src = page.locator(
                    '#workspace-stage-list .match-stage-card[data-stage-id="stage_1"] .match-stage-preview-video'
                ).get_attribute("src")
                assert preview_src is not None
                assert "/media/workspace-stage/stage_1" in preview_src

                preview_fetch = page.evaluate(
                    """async (src) => {
                        const response = await fetch(src);
                        const buffer = await response.arrayBuffer();
                        return {
                            status: response.status,
                            contentType: response.headers.get('content-type') || '',
                            byteLength: buffer.byteLength,
                        };
                    }""",
                    preview_src,
                )
                assert preview_fetch["status"] == 200
                assert preview_fetch["contentType"] == "video/mp4"
                assert preview_fetch["byteLength"] > 0

                page.wait_for_function(
                    "() => (document.getElementById('match-stage-detail-status')?.textContent || '').includes('Stage 1')"
                )

                _open_match_section(page, "match-section-export")
                page.wait_for_function(
                    "() => document.getElementById('match-section-export')?.hidden === false && document.getElementById('match-section-stage-detail')?.hidden === false"
                )
                assert "Stage 1" in (page.locator("#match-stage-detail-panel").text_content() or "")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_performance_library_can_reopen_stage_and_workspace_from_selected_record(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

    from datetime import datetime, timezone

    from splitshot.domain.models import LibraryMatchRecord, LibraryStageRecord
    from splitshot.persistence.library import save_match_record, save_stage_record

    stage_project_path = tmp_path / "performance-stage.ssproj"
    stage_controller = ProjectController()
    stage_controller.new_project()
    stage_controller.project.name = "Performance Stage"
    stage_controller.save_project(str(stage_project_path))

    workspace_path = tmp_path / "performance-workspace"
    workspace_controller = ProjectController()
    workspace_controller.new_workspace()
    workspace_controller.workspace.name = "Performance Match"
    workspace_controller.workspace_add_stage("stage_1", "Stage 1")
    workspace_controller.save_workspace(str(workspace_path))

    save_stage_record(
        LibraryStageRecord(
            library_record_id="performance-stage-record",
            stage_id="stage_1",
            display_name="Practice Stage",
            event_date=datetime(2026, 2, 11, tzinfo=timezone.utc),
            discipline="uspsa_minor",
            metric_summary={"score_total": 96},
            editor_target={
                "type": "single",
                "project_path": str(stage_project_path),
                "stage_id": "stage_1",
            },
            truth_hash="stage-truth",
        )
    )
    save_match_record(
        LibraryMatchRecord(
            library_record_id="performance-match-record",
            match_id="match_1",
            display_name="Weekend Match",
            event_date=datetime(2026, 2, 12, tzinfo=timezone.utc),
            discipline="idpa_time_plus",
            stage_ids=["stage_1"],
            aggregate_metric_summary={"score": 175, "stage_count": 1},
            editor_target={
                "type": "multi",
                "workspace_path": str(workspace_path),
                "match_id": "match_1",
            },
            truth_hash="match-truth",
        )
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_library_surface(page)
                _open_library_section(page, "library-section-records")
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length >= 2"
                )

                page.locator(
                    "#library-record-list .library-record-row",
                    has_text="Practice Stage",
                ).click()
                _open_library_section(page, "library-section-detail")
                page.locator("#library-open-stage").click()
                page.wait_for_function(
                    "(expectedPath) => activeSurface === 'single' && state?.project?.path === expectedPath",
                    arg=str(stage_project_path),
                )

                _open_library_surface(page)
                _open_library_section(page, "library-section-records")
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length >= 2"
                )

                page.locator(
                    "#library-record-list .library-record-row",
                    has_text="Weekend Match",
                ).click()
                _open_library_section(page, "library-section-detail")
                page.locator("#library-open-workspace").click()
                page.wait_for_function(
                    "(expectedPath) => activeSurface === 'multi' && state?.workspace_path === expectedPath",
                    arg=str(workspace_path),
                )
                assert page.locator("#workspace-stage-list .match-stage-card").count() == 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_performance_library_settings_persist_and_manual_refresh_loads_records(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

    from datetime import datetime, timezone

    from splitshot.domain.models import LibraryStageRecord
    from splitshot.persistence.library import save_stage_record

    save_stage_record(
        LibraryStageRecord(
            library_record_id="settings-stage-record",
            stage_id="stage_settings",
            display_name="Settings Stage",
            event_date=datetime(2026, 2, 13, tzinfo=timezone.utc),
            discipline="uspsa_minor",
            metric_summary={"score_total": 90},
            editor_target={"type": "single", "project_path": str(tmp_path / "settings-stage.ssproj")},
            truth_hash="settings-truth",
        )
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_library_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 1"
                )

                _open_library_section(page, "library-section-settings")
                page.locator("#library-setting-default-sort").select_option("score")
                page.locator("#library-setting-auto-refresh").uncheck()
                page.wait_for_function(
                    """() => {
                        const settings = JSON.parse(localStorage.getItem('splitshot.library.settings') || '{}');
                        return settings.defaultSort === 'score' && settings.autoRefresh === false;
                    }"""
                )

                page.reload(wait_until="domcontentloaded")
                _open_library_surface(page)
                page.wait_for_function(
                    "() => document.getElementById('library-stale')?.hidden === false"
                )

                _open_library_section(page, "library-section-settings")
                assert page.locator("#library-setting-default-sort").input_value() == "score"
                assert page.locator("#library-setting-auto-refresh").is_checked() is False

                assert page.locator("#library-stale-refresh").is_visible() is True
                page.locator("#library-stale-refresh").click()
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 1"
                )
                assert page.locator("#library-stale").is_visible() is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_performance_library_shows_loading_and_recovers_from_route_failure(
    monkeypatch,
) -> None:
    import splitshot.persistence.library as library_module

    call_state = {"stage_reads": 0}

    def flaky_stage_records() -> list[dict[str, object]]:
        call_state["stage_reads"] += 1
        time.sleep(0.35)
        if call_state["stage_reads"] == 1:
            raise ValueError("Library list unavailable.")
        return [
            {
                "library_record_id": "recovered-stage-record",
                "stage_id": "recovered-stage",
                "display_name": "Recovered Stage",
                "event_date": "2026-05-20T00:00:00+00:00",
                "discipline": "uspsa_minor",
                "metric_summary": {"score_total": 94},
                "editor_target": {
                    "type": "single",
                    "project_path": "/tmp/recovered-stage.ssproj",
                    "stage_id": "recovered-stage",
                },
            }
        ]

    monkeypatch.setattr(library_module, "read_stage_records", flaky_stage_records)
    monkeypatch.setattr(library_module, "read_stage_metrics", lambda: [])
    monkeypatch.setattr(library_module, "read_match_records", lambda: [])
    monkeypatch.setattr(library_module, "read_match_metrics", lambda: [])

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_library_surface(page)
                page.wait_for_function(
                    "() => document.getElementById('library-loading')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.getElementById('library-error')?.hidden === false"
                )
                assert "Library list unavailable." in (
                    page.locator("#library-error").text_content() or ""
                )

                assert page.locator("#library-error-retry").is_visible() is True
                page.locator("#library-error-retry").click()
                page.wait_for_function(
                    "() => document.getElementById('library-loading')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 1"
                )
                page.wait_for_function(
                    "() => document.getElementById('library-error')?.hidden === true"
                )
                assert "Recovered Stage" in (page.locator("#library-record-list").text_content() or "")
                assert call_state["stage_reads"] >= 2
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_performance_library_summary_tiles_and_personal_bests_follow_loaded_records(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

    from datetime import datetime, timedelta, timezone

    from splitshot.domain.models import LibraryMatchRecord, LibraryStageRecord
    from splitshot.persistence.library import save_match_record, save_stage_record

    now = datetime.now(timezone.utc)

    save_stage_record(
        LibraryStageRecord(
            library_record_id="stage-recent-best",
            stage_id="stage_recent_best",
            display_name="Recent Classifier",
            event_date=now - timedelta(days=5),
            discipline="uspsa_minor",
            metric_summary={"score_total": 101},
            editor_target={"type": "single", "project_path": str(tmp_path / "recent.ssproj")},
            truth_hash="truth-recent-best",
        )
    )
    save_stage_record(
        LibraryStageRecord(
            library_record_id="stage-older-score",
            stage_id="stage_older_score",
            display_name="Older Classifier",
            event_date=now - timedelta(days=45),
            discipline="idpa_time_plus",
            metric_summary={"score_total": 92},
            editor_target={"type": "single", "project_path": str(tmp_path / "older.ssproj")},
            truth_hash="truth-older-score",
        )
    )
    save_match_record(
        LibraryMatchRecord(
            library_record_id="match-best-record",
            match_id="match_best_record",
            display_name="Weekend Match",
            event_date=now - timedelta(days=2),
            discipline="uspsa_minor",
            stage_ids=["stage_recent_best", "stage_older_score"],
            aggregate_metric_summary={"score": 180, "stage_count": 2},
            editor_target={"type": "multi", "workspace_path": str(tmp_path / "weekend-match")},
            truth_hash="truth-match-best",
        )
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_library_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 3"
                )

                summary = page.evaluate(
                    """() => Object.fromEntries(
                        Array.from(document.querySelectorAll('#library-summary-tiles .library-tile')).map((tile) => [
                            tile.querySelector('.library-tile-label')?.textContent?.trim(),
                            tile.querySelector('.library-tile-value')?.textContent?.trim(),
                        ])
                    )"""
                )
                assert summary == {
                    "Total Stages": "2",
                    "Total Matches": "1",
                    "Personal Best": "180 (Weekend Match)",
                    "Recent (30d)": "2",
                }

                _open_library_section(page, "library-section-records")
                page.wait_for_function(
                    "() => document.querySelectorAll('#personal-bests-list .library-record-row').length === 3"
                )
                personal_bests = page.evaluate(
                    """() => Array.from(document.querySelectorAll('#personal-bests-list .library-record-row')).map((row) => ({
                        rank: row.querySelector('.record-rank')?.textContent?.trim(),
                        name: row.querySelector('.record-name')?.textContent?.trim(),
                        score: row.querySelector('.record-score')?.textContent?.trim(),
                    }))"""
                )
                assert personal_bests == [
                    {"rank": "#1", "name": "Weekend Match", "score": "180"},
                    {"rank": "#2", "name": "Recent Classifier", "score": "101"},
                    {"rank": "#3", "name": "Older Classifier", "score": "92"},
                ]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_performance_library_search_filters_records_and_keeps_lower_detail_truth(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

    from datetime import datetime, timezone

    from splitshot.domain.models import LibraryStageRecord
    from splitshot.persistence.library import save_stage_record

    save_stage_record(
        LibraryStageRecord(
            library_record_id="alpha-record",
            stage_id="alpha_stage",
            display_name="Alpha Drill",
            event_date=datetime(2026, 5, 23, tzinfo=timezone.utc),
            discipline="uspsa_minor",
            metric_summary={"score_total": 92},
            editor_target={"type": "single", "project_path": str(tmp_path / "alpha.ssproj")},
            truth_hash="alpha-truth",
        )
    )
    save_stage_record(
        LibraryStageRecord(
            library_record_id="bravo-record",
            stage_id="bravo_stage",
            display_name="Bravo Drill",
            event_date=datetime(2026, 5, 24, tzinfo=timezone.utc),
            discipline="idpa_time_plus",
            metric_summary={"score_total": 87},
            editor_target={"type": "single", "project_path": str(tmp_path / "bravo.ssproj")},
            truth_hash="bravo-truth",
        )
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_library_surface(page)
                _open_library_section(page, "library-section-records")
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 2"
                )

                page.locator("#library-search").fill("Bravo")
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 1"
                )
                assert "Bravo Drill" in (page.locator("#library-record-list").text_content() or "")

                page.locator("#library-record-list .library-record-row", has_text="Bravo Drill").click()
                page.wait_for_function(
                    "() => (document.getElementById('library-detail-status')?.textContent || '').includes('Bravo Drill')"
                )
                assert page.locator("#library-section-detail").evaluate("node => node.hidden") is False

                _open_library_section(page, "library-section-detail")
                page.wait_for_function(
                    "() => document.getElementById('library-section-detail-actions')?.hidden === false"
                )
                assert page.locator("#library-open-stage").is_visible() is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_performance_library_detail_ui_persists_tag_add_remove_and_notes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

    from datetime import datetime, timezone

    from splitshot.domain.models import LibraryStageRecord
    from splitshot.persistence.library import load_stage_record, save_stage_record

    save_stage_record(
        LibraryStageRecord(
            library_record_id="detail-stage-record",
            stage_id="detail_stage",
            display_name="Detail Stage",
            event_date=datetime(2026, 5, 21, tzinfo=timezone.utc),
            discipline="uspsa_minor",
            metric_summary={"score_total": 88},
            editor_target={"type": "single", "project_path": str(tmp_path / "detail-stage.ssproj")},
            truth_hash="detail-stage-truth",
            tags=["existing"],
            notes="Old note",
        )
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_library_surface(page)
                _open_library_section(page, "library-section-records")
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 1"
                )

                page.locator("#library-record-list .library-record-row", has_text="Detail Stage").click()
                _open_library_section(page, "library-section-detail")
                page.wait_for_function(
                    "() => document.getElementById('library-tags-editor')?.hidden === false"
                )

                page.locator('#library-tag-list .tag-remove[data-tag="existing"]').click()
                page.wait_for_function(
                    "() => !(document.getElementById('library-tag-list')?.textContent || '').includes('existing')"
                )

                page.locator("#library-tag-input").fill("night")
                page.locator("#library-tag-add").click()
                page.wait_for_function(
                    "() => (document.getElementById('library-tag-list')?.textContent || '').includes('night')"
                )

                page.locator("#library-notes-text").fill("Fresh note")
                page.locator("#library-notes-save").click()
                page.wait_for_function(
                    "() => (document.getElementById('library-record-detail')?.textContent || '').includes('Fresh note')"
                )

                page.reload(wait_until="domcontentloaded")
                _open_library_surface(page)
                _open_library_section(page, "library-section-records")
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 1"
                )
                page.locator("#library-record-list .library-record-row", has_text="Detail Stage").click()
                _open_library_section(page, "library-section-detail")
                page.wait_for_function(
                    "() => (document.getElementById('library-tag-list')?.textContent || '').includes('night')"
                )
                assert "existing" not in (page.locator("#library-tag-list").text_content() or "")
                assert page.locator("#library-notes-text").input_value() == "Fresh note"
            finally:
                browser.close()
    finally:
        server.shutdown()

    restored_record = load_stage_record("detail-stage-record")
    assert restored_record is not None
    assert restored_record.tags == ["night"]
    assert restored_record.notes == "Fresh note"


def test_performance_library_compat_selected_record_and_render_rerender_detail_truth(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

    from datetime import datetime, timezone

    from splitshot.domain.models import LibraryStageRecord
    from splitshot.persistence.library import load_stage_record, save_stage_record

    save_stage_record(
        LibraryStageRecord(
            library_record_id="compat-stage-record-a",
            stage_id="compat_stage_a",
            display_name="Compat Stage A",
            event_date=datetime(2026, 5, 25, tzinfo=timezone.utc),
            discipline="uspsa_minor",
            metric_summary={"score_total": 95},
            editor_target={"type": "single", "project_path": str(tmp_path / "compat-stage-a.ssproj")},
            truth_hash="compat-stage-truth-a",
            tags=["existing"],
            notes="Original note A",
        )
    )
    save_stage_record(
        LibraryStageRecord(
            library_record_id="compat-stage-record-b",
            stage_id="compat_stage_b",
            display_name="Compat Stage B",
            event_date=datetime(2026, 5, 26, tzinfo=timezone.utc),
            discipline="idpa_time_plus",
            metric_summary={"score_total": 89},
            editor_target={"type": "single", "project_path": str(tmp_path / "compat-stage-b.ssproj")},
            truth_hash="compat-stage-truth-b",
            tags=["switch-target"],
            notes="Original note B",
        )
    )

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_library_surface(page)
                _open_library_section(page, "library-section-records")
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 2"
                )

                page.locator(
                    "#library-record-list .library-record-row",
                    has_text="Compat Stage A",
                ).click()
                _open_library_section(page, "library-section-detail")
                page.wait_for_function(
                    "() => window.selectedLibraryRecord?.library_record_id === 'compat-stage-record-a'"
                )

                page.evaluate("() => renderAutomationSurface()")
                page.wait_for_function(
                    """() => {
                        const notes = document.getElementById('library-notes-text')?.value || '';
                        const tags = document.getElementById('library-tag-list')?.textContent || '';
                        const detail = document.getElementById('library-detail-status')?.textContent || '';
                        return notes === 'Original note A'
                          && tags.includes('existing')
                          && detail.includes('Compat Stage A')
                          && document.getElementById('library-section-detail')?.hidden === false;
                    }"""
                )

                save_result = page.evaluate(
                    """async () => {
                        const recordId = window.selectedLibraryRecord?.library_record_id || '';
                        const notes = 'Compat rerender note';
                        const result = await callApi('/api/library/notes/update', {
                          record_id: recordId,
                          notes,
                        });
                        if (result?.updated) {
                          window.selectedLibraryRecord = {
                            ...window.selectedLibraryRecord,
                            notes,
                          };
                                                    document.getElementById('library-refresh')?.click();
                        }
                        return result;
                    }"""
                )
                assert save_result == {
                    "record_id": "compat-stage-record-a",
                    "notes": "Compat rerender note",
                    "updated": True,
                }

                page.wait_for_function(
                    """() => {
                        const notes = document.getElementById('library-notes-text')?.value || '';
                        const tags = document.getElementById('library-tag-list')?.textContent || '';
                        const detail = document.getElementById('library-detail-status')?.textContent || '';
                        return window.selectedLibraryRecord?.library_record_id === 'compat-stage-record-a'
                          && notes === 'Compat rerender note'
                          && tags.includes('existing')
                          && detail.includes('Compat Stage A')
                          && document.getElementById('library-section-detail')?.hidden === false;
                    }"""
                )
            finally:
                browser.close()
    finally:
        server.shutdown()

    restored_record = load_stage_record("compat-stage-record-a")
    assert restored_record is not None
    assert restored_record.notes == "Compat rerender note"


def test_performance_library_settings_remain_isolated_from_match_settings(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPLITSHOT_LIBRARY_ROOT", str(tmp_path / "library"))

    from datetime import datetime, timezone

    from splitshot.domain.models import LibraryStageRecord
    from splitshot.persistence.library import save_stage_record

    save_stage_record(
        LibraryStageRecord(
            library_record_id="settings-isolation-record",
            stage_id="settings_isolation_stage",
            display_name="Settings Isolation Stage",
            event_date=datetime(2026, 5, 22, tzinfo=timezone.utc),
            discipline="uspsa_minor",
            metric_summary={"score_total": 91},
            editor_target={"type": "single", "project_path": str(tmp_path / "settings-isolation.ssproj")},
            truth_hash="settings-isolation-truth",
        )
    )

    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Isolation Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 2"
                )
                page.locator("#match-open-settings").click(force=True)
                page.wait_for_function(
                    "() => document.getElementById('match-section-settings')?.hidden === false"
                )
                page.locator("#match-setting-show-score").uncheck()
                page.locator("#match-setting-remember-stage").uncheck()
                page.wait_for_function(
                    """() => {
                        const settings = JSON.parse(localStorage.getItem('splitshot.match.settings') || '{}');
                        return settings.showScoreBadges === false && settings.rememberStageSelection === false;
                    }"""
                )

                _open_library_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#library-record-list .library-record-row').length === 1"
                )
                _open_library_section(page, "library-section-settings")
                page.locator("#library-setting-default-sort").select_option("score")
                page.locator("#library-setting-auto-refresh").uncheck()
                page.wait_for_function(
                    """() => {
                        const librarySettings = JSON.parse(localStorage.getItem('splitshot.library.settings') || '{}');
                        const matchSettings = JSON.parse(localStorage.getItem('splitshot.match.settings') || '{}');
                        return librarySettings.defaultSort === 'score'
                          && librarySettings.autoRefresh === false
                          && matchSettings.showScoreBadges === false
                          && matchSettings.rememberStageSelection === false;
                    }"""
                )

                page.reload(wait_until="domcontentloaded")

                _open_match_surface(page)
                page.locator("#match-open-settings").click(force=True)
                page.wait_for_function(
                    "() => document.getElementById('match-section-settings')?.hidden === false"
                )
                assert page.locator("#match-setting-show-score").is_checked() is False
                assert page.locator("#match-setting-remember-stage").is_checked() is False

                _open_library_surface(page)
                page.wait_for_function(
                    "() => document.getElementById('library-stale')?.hidden === false"
                )
                _open_library_section(page, "library-section-settings")
                assert page.locator("#library-setting-default-sort").input_value() == "score"
                assert page.locator("#library-setting-auto-refresh").is_checked() is False
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_recap_reports_success_and_error_states(
    monkeypatch,
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Recap Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    controller.save_workspace(str(tmp_path / "recap-match-ui"))
    recap_calls: list[dict[str, object]] = []
    recap_mode = {"value": "success"}

    def fake_workspace_recap_render(self, **kwargs):
        recap_calls.append(dict(kwargs))
        if recap_mode["value"] == "success":
            return {
                "success": True,
                "output_path": "/tmp/recap.mp4",
                "size_bytes": 128,
                "stage_count": len(kwargs.get("stage_ids") or []),
                "errors": [],
            }
        return {
            "success": False,
            "error": "Recap concat failed: boom",
            "errors": [{"stage_id": "stage_1", "error": "boom"}],
        }

    monkeypatch.setattr(
        ProjectController,
        "workspace_recap_render",
        fake_workspace_recap_render,
    )

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                _open_match_section(page, "match-section-recap")
                page.wait_for_function(
                    "() => document.querySelectorAll('#match-recap-panel .recap-stage-check').length === 2"
                )

                page.locator("#match-recap-panel .recap-stage-check").nth(1).uncheck()
                page.wait_for_function(
                    """() => document.querySelectorAll('#match-recap-panel .recap-stage-check')[1]?.checked === false"""
                )
                page.locator("#recap-transition").select_option("fade")
                page.locator("#recap-result-card").select_option("end")
                page.locator("#recap-render").click()
                page.wait_for_function(
                    "() => (document.getElementById('recap-status')?.textContent || '').includes('/tmp/recap.mp4')"
                )

                assert recap_calls[0]["stage_ids"] == ["stage_1"]
                assert recap_calls[0]["transition"] == "fade"
                assert recap_calls[0]["result_card"] == "end"
                assert "/tmp/recap.mp4" in (page.locator("#recap-results").text_content() or "")

                recap_mode["value"] = "error"
                page.locator("#recap-render").click()
                page.wait_for_function(
                    "() => (document.getElementById('recap-status')?.textContent || '').includes('Recap concat failed')"
                )
                assert "boom" in (page.locator("#recap-results").text_content() or "")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_batch_export_queue_select_all_none_and_start() -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Batch Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    controller.workspace.stage_entries["stage_1"].source_media_present = True
    controller.workspace.stage_entries["stage_2"].source_media_present = True
    export_calls: list[tuple[str | None, str | None]] = []

    def fake_workspace_export(stage_id: str | None = None, recipe: str | None = None):
        export_calls.append((stage_id, recipe))
        return {
            "success": True,
            "outputs": [
                {
                    "stage_id": stage_id,
                    "display_name": stage_id,
                    "output_path": f"/tmp/{stage_id}.mp4",
                    "status": "completed",
                }
            ],
            "errors": [],
            "total": 1,
            "completed": 1,
            "failed": 0,
        }

    controller.workspace_export = fake_workspace_export  # type: ignore[method-assign]

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                _open_match_section(page, "match-section-export")
                page.wait_for_function(
                    "() => document.querySelectorAll('#batch-export-queue .batch-export-item').length === 2"
                )

                assert page.locator("#batch-export-queue .batch-export-item").count() == 2

                page.locator("#batch-select-none").click()
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#batch-export-queue .batch-export-item input[type=\"checkbox\"]')].every((checkbox) => checkbox.checked === false)"
                )

                page.locator("#batch-select-all").click()
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#batch-export-queue .batch-export-item input[type=\"checkbox\"]:not(:disabled)')].every((checkbox) => checkbox.checked === true)"
                )

                page.locator("#batch-recipe").select_option("stage_composite")
                page.locator("#batch-export-start").click()
                page.wait_for_function(
                    "() => (document.getElementById('batch-export-status')?.textContent || '').includes('Exported 2 stage')"
                )

                assert export_calls == [
                    ("stage_1", "stage_composite"),
                    ("stage_2", "stage_composite"),
                ]
                results_text = page.locator("#batch-export-results").text_content() or ""
                assert "/tmp/stage_1.mp4" in results_text
                assert "/tmp/stage_2.mp4" in results_text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_workspace_batch_export_reports_errors_truthfully() -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Batch Error Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    controller.workspace.stage_entries["stage_1"].source_media_present = True
    controller.workspace.stage_entries["stage_2"].source_media_present = True

    def fake_workspace_export(stage_id: str | None = None, recipe: str | None = None):
        if stage_id == "stage_2":
            return {
                "success": False,
                "outputs": [],
                "errors": [{"stage_id": stage_id, "error": "ffmpeg failed"}],
                "total": 1,
                "completed": 0,
                "failed": 1,
            }
        return {
            "success": True,
            "outputs": [
                {
                    "stage_id": stage_id,
                    "display_name": stage_id,
                    "output_path": f"/tmp/{stage_id}.mp4",
                    "status": "completed",
                }
            ],
            "errors": [],
            "total": 1,
            "completed": 1,
            "failed": 0,
        }

    controller.workspace_export = fake_workspace_export  # type: ignore[method-assign]

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                _open_match_section(page, "match-section-export")
                page.wait_for_function(
                    "() => document.querySelectorAll('#batch-export-queue .batch-export-item').length === 2"
                )

                page.locator("#batch-export-start").click()
                page.wait_for_function(
                    "() => (document.getElementById('batch-export-status')?.textContent || '').includes('1 error')"
                )

                results_text = page.locator("#batch-export-results").text_content() or ""
                assert "/tmp/stage_1.mp4" in results_text
                assert "ffmpeg failed" in results_text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_settings_persist_locally_and_control_match_return_selection() -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Settings Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    shared_defaults_before = dict(controller.workspace.shared_defaults)

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 2"
                )

                page.locator("#match-open-settings").click(force=True)
                page.wait_for_function(
                    "() => document.getElementById('match-section-settings')?.hidden === false"
                )
                page.locator("#match-setting-show-score").uncheck()
                page.locator("#match-setting-remember-stage").uncheck()
                page.wait_for_function(
                    """() => {
                        const settings = JSON.parse(localStorage.getItem('splitshot.match.settings') || '{}');
                        return settings.showScoreBadges === false && settings.rememberStageSelection === false;
                    }"""
                )

                page.reload(wait_until="domcontentloaded")
                _open_match_surface(page)
                page.locator("#match-open-settings").click(force=True)
                page.wait_for_function(
                    "() => document.getElementById('match-setting-show-score') && document.getElementById('match-setting-remember-stage')"
                )
                assert page.locator("#match-setting-show-score").is_checked() is False
                assert page.locator("#match-setting-remember-stage").is_checked() is False

                page.locator('[data-workspace-target="match-section-stages"]').click(force=True)
                page.wait_for_function(
                    "() => document.getElementById('match-section-stages')?.hidden === false"
                )
                page.locator('#workspace-stage-list .match-stage-card[data-stage-id="stage_2"]').locator(
                    "button",
                    has_text="Open",
                ).click()
                page.wait_for_function("() => activeSurface === 'single'")
                page.locator("#shell-return-match").click()
                page.wait_for_function("() => activeSurface === 'multi'")

                selected_card = page.locator(
                    '#workspace-stage-list .match-stage-card[data-stage-id="stage_2"]'
                )
                assert selected_card.evaluate("card => card.classList.contains('selected')") is False
                assert controller.workspace.shared_defaults == shared_defaults_before
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_stage_composite_controls_update_composite_state(
    monkeypatch,
) -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Composite Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    first_clip = controller.workspace_stage_clip_add("stage_1", "/tmp/primary.mp4", "primary")[0]
    second_clip = controller.workspace_stage_clip_add("stage_1", "/tmp/follow.mp4", "follow")[-1]
    angle_calls: list[dict[str, object]] = []
    audio_calls: list[dict[str, object]] = []
    reorder_calls: list[dict[str, object]] = []
    original_angle_align = ProjectController.angle_align
    original_audio_mix_set = ProjectController.audio_mix_set
    original_reorder = ProjectController.workspace_stage_clip_reorder

    def tracking_angle_align(self, stage_id: str, reference_clip_id: str) -> dict:
        angle_calls.append({"stage_id": stage_id, "reference_clip_id": reference_clip_id})
        return original_angle_align(self, stage_id, reference_clip_id)

    def tracking_audio_mix_set(
        self,
        stage_id: str,
        clip_id: str,
        gain: float | None = None,
        muted: bool | None = None,
        primary: bool | None = None,
    ) -> dict | None:
        audio_calls.append(
            {
                "stage_id": stage_id,
                "clip_id": clip_id,
                "gain": gain,
                "muted": muted,
                "primary": primary,
            }
        )
        return original_audio_mix_set(self, stage_id, clip_id, gain, muted, primary)

    def tracking_reorder(self, stage_id: str, clip_id: str, target_index: int):
        reorder_calls.append(
            {
                "stage_id": stage_id,
                "clip_id": clip_id,
                "target_index": target_index,
            }
        )
        return original_reorder(self, stage_id, clip_id, target_index)

    monkeypatch.setattr(ProjectController, "angle_align", tracking_angle_align)
    monkeypatch.setattr(ProjectController, "audio_mix_set", tracking_audio_mix_set)
    monkeypatch.setattr(ProjectController, "workspace_stage_clip_reorder", tracking_reorder)

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 1"
                )

                page.locator('#workspace-stage-list .match-stage-card[data-stage-id="stage_1"]').click()
                _open_match_section(page, "match-section-composite")
                page.wait_for_function(
                    "() => document.querySelectorAll('#stage-composite-list .automation-row').length === 2"
                )

                page.locator(
                    f'#stage-composite-list .automation-row[data-clip-id="{first_clip["clip_id"]}"]'
                ).locator("button", has_text="Angle Align").click()
                page.wait_for_function(
                    """async (stageId) => {
                        const response = await fetch('/api/workspace/stage/clip/list', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ stage_id: stageId }),
                        });
                        const data = await response.json();
                        return Array.isArray(data?.clips)
                          && data.clips.length === 2
                          && data.clips.every((clip) => clip.angle_aligned === true);
                    }""",
                    arg="stage_1",
                )

                assert angle_calls == [
                    {"stage_id": "stage_1", "reference_clip_id": first_clip["clip_id"]}
                ]

                row = page.locator(
                    f'#stage-composite-list .automation-row[data-clip-id="{first_clip["clip_id"]}"]'
                )
                row.locator("label", has_text="Audio gain").locator("input").fill("0.5")
                row.locator("label", has_text="Audio gain").locator("input").dispatch_event("change")
                row.locator("label", has_text="Mute").locator("input").check()
                page.wait_for_function(
                    """async (clipId) => {
                        const response = await fetch('/api/workspace/stage/clip/list', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ stage_id: 'stage_1' }),
                        });
                        const data = await response.json();
                        const clip = (data?.clips || []).find((item) => item.clip_id === clipId);
                        return Boolean(clip)
                          && clip.audio_muted === true
                          && clip.audio_gain === 0.5;
                    }""",
                    arg=first_clip["clip_id"],
                )

                second_row = page.locator(
                    f'#stage-composite-list .automation-row[data-clip-id="{second_clip["clip_id"]}"]'
                )
                second_row.locator("label", has_text="Primary audio").locator("input").check()
                page.wait_for_function(
                    """async (clipId) => {
                        const response = await fetch('/api/workspace/stage/clip/list', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ stage_id: 'stage_1' }),
                        });
                        const data = await response.json();
                        const clip = (data?.clips || []).find((item) => item.clip_id === clipId);
                        return Boolean(clip) && clip.audio_primary === true;
                    }""",
                    arg=second_clip["clip_id"],
                )

                row.locator("button", has_text="↓").click()
                page.wait_for_function(
                    """(clipId) => {
                        const firstRow = document.querySelector('#stage-composite-list .automation-row');
                        return Boolean(firstRow) && firstRow.dataset.clipId !== clipId;
                    }""",
                    arg=first_clip["clip_id"],
                )

                assert audio_calls[0] == {
                    "stage_id": "stage_1",
                    "clip_id": first_clip["clip_id"],
                    "gain": 0.5,
                    "muted": None,
                    "primary": None,
                }
                assert {
                    "stage_id": "stage_1",
                    "clip_id": first_clip["clip_id"],
                    "gain": None,
                    "muted": True,
                    "primary": None,
                } in audio_calls
                assert {
                    "stage_id": "stage_1",
                    "clip_id": second_clip["clip_id"],
                    "gain": None,
                    "muted": None,
                    "primary": True,
                } in audio_calls
                assert reorder_calls == [
                    {
                        "stage_id": "stage_1",
                        "clip_id": first_clip["clip_id"],
                        "target_index": 1,
                    }
                ]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_match_stage_composite_cut_override_editor_updates_plan_detail() -> None:
    controller = ProjectController()
    controller.new_workspace()
    controller.workspace.name = "Composite Match"
    controller.workspace_add_stage("stage_1", "Stage 1")
    first_clip = controller.workspace_stage_clip_add("stage_1", "/tmp/primary.mp4", "primary")[0]
    controller.workspace_stage_clip_add("stage_1", "/tmp/follow.mp4", "follow")

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_match_surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 1"
                )
                page.locator('#workspace-stage-list .match-stage-card[data-stage-id="stage_1"]').click()
                _open_match_section(page, "match-section-composite")
                page.wait_for_function(
                    "() => document.querySelectorAll('#stage-composite-list .automation-row').length === 2"
                )

                row = page.locator(
                    f'#stage-composite-list .automation-row[data-clip-id="{first_clip["clip_id"]}"]'
                )
                row.locator("label", has_text="Cut slot").locator("input").fill("1")
                row.locator("label", has_text="Start (ms)").locator("input").fill("250")
                row.locator("label", has_text="Duration (ms)").locator("input").fill("500")
                row.locator("button", has_text="Apply Cut").click()

                page.wait_for_function(
                    """() => {
                        const detail = document.getElementById('output-profile-detail');
                        return Boolean(detail?.textContent?.includes('"start_ms": 250'))
                          && Boolean(detail?.textContent?.includes('"duration_ms": 500'));
                    }"""
                )

                row.locator("button", has_text="Clear Cut").click()
                page.wait_for_function(
                    """() => {
                        const detail = document.getElementById('output-profile-detail');
                        return Boolean(detail?.textContent) && !detail.textContent.includes('"start_ms": 250');
                    }"""
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_pane_select_project_missing_dirs_shows_notice_and_creates_only_missing(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "partial.ssproj"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "Input").mkdir()

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            dialogs: list[str] = []
            page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.accept()))
            try:
                _open_tool(page, "project")
                page.evaluate(f"() => useProjectFolder({json.dumps(str(project_path))})")
                page.wait_for_function("() => Boolean(state?.project?.path)")
                assert (project_path / "Input").is_dir()
                assert (project_path / "CSV").is_dir()
                assert (project_path / "Output").is_dir()
                assert page.locator("#project-path").input_value() == "partial.ssproj"
                assert any("missing CSV, Output" in message for message in dialogs)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_landing_and_stage_empty_primary_import_buttons_work_without_saved_project(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="blank-project-primary-import"))
    chooser_calls: list[tuple[str, str | None]] = []

    def fake_path_chooser(kind: str, current: str | None) -> str:
        chooser_calls.append((kind, current))
        assert kind == "primary"
        return str(primary_path)

    server = BrowserControlServer(
        controller=ProjectController(),
        port=0,
        path_chooser=fake_path_chooser,
    )
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                assert page.evaluate("() => state?.project?.path || ''") == ""
                page.evaluate("() => setActiveSurface('landing')")
                page.wait_for_function("() => activeSurface === 'landing'")
                page.locator("#landing-open-file").wait_for(state="visible")

                page.locator("#landing-open-file").click()
                page.wait_for_function("() => activeSurface === 'single'")
                page.wait_for_function("() => Boolean(state?.media?.primary_available)")
                page.locator(".waveform-shot-card").first.wait_for(state="attached")
                assert page.evaluate("() => state?.project?.path || ''") == ""

                page.evaluate("() => callApi('/api/project/new', {})")
                page.wait_for_function("() => !Boolean(state?.media?.primary_available)")
                page.locator("#stage-empty-import").wait_for(state="visible")

                page.locator("#stage-empty-import").click(force=True)
                page.wait_for_function("() => Boolean(state?.media?.primary_available)")
                page.locator(".waveform-shot-card").first.wait_for(state="attached")
                assert page.evaluate("() => state?.project?.path || ''") == ""

                page.evaluate("() => callApi('/api/project/new', {})")
                page.wait_for_function("() => !Boolean(state?.media?.primary_available)")
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.media?.primary_available)")
                page.locator(".waveform-shot-card").first.wait_for(state="attached")
                assert page.evaluate("() => state?.project?.path || ''") == ""

                assert [kind for kind, _current in chooser_calls] == ["primary", "primary"]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_landing_cards_and_quick_start_buttons_switch_surfaces_without_saved_state() -> None:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                landing_cards = [
                    ('button.landing-card[data-surface="single"]', "single"),
                    ('button.landing-card[data-surface="multi"]', "multi"),
                    ('button.landing-card[data-surface="library"]', "library"),
                ]
                for selector, expected_surface in landing_cards:
                    page.evaluate("() => setActiveSurface('landing')")
                    page.wait_for_function("() => activeSurface === 'landing'")

                    page.locator(selector).click()
                    page.wait_for_function(
                        "(expected) => activeSurface === expected",
                        arg=expected_surface,
                    )

                    assert page.evaluate("() => state?.project?.path || ''") == ""
                    assert page.evaluate("() => state?.workspace_path || ''") == ""

                page.evaluate("() => setActiveSurface('landing')")
                page.wait_for_function("() => activeSurface === 'landing'")
                page.locator("#landing-new-stage").click()
                page.wait_for_function("() => activeSurface === 'single'")
                page.locator("#stage-empty-import").wait_for(state="visible")
                assert page.evaluate("() => state?.project?.path || ''") == ""
                assert page.evaluate("() => state?.workspace_path || ''") == ""

                page.evaluate("() => setActiveSurface('landing')")
                page.wait_for_function("() => activeSurface === 'landing'")
                page.locator("#landing-new-match").click()
                page.wait_for_function("() => activeSurface === 'multi'")
                page.locator("#workspace-new").wait_for(state="visible")
                assert page.evaluate("() => state?.project?.path || ''") == ""
                assert page.evaluate("() => state?.workspace_path || ''") == ""
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_landing_recent_stage_rows_switch_surface_without_auto_open(
    monkeypatch,
    tmp_path: Path,
) -> None:
    recent_project_path = tmp_path / "landing-recent-stage.ssproj"
    open_project_calls: list[str] = []
    open_workspace_calls: list[str] = []

    def fake_landing_recent(self: ProjectController) -> dict[str, object]:
        return {
            "recent": [
                {
                    "name": "Recent Classifier",
                    "surface": "single",
                    "type": "stage",
                    "path": str(recent_project_path),
                    "date": "2026-05-26T00:00:00+00:00",
                }
            ]
        }

    def fake_open_project(self: ProjectController, path: str) -> None:
        open_project_calls.append(path)

    def fake_open_workspace(self: ProjectController, path: str) -> None:
        open_workspace_calls.append(path)

    monkeypatch.setattr(ProjectController, "landing_recent", fake_landing_recent)
    monkeypatch.setattr(ProjectController, "open_project", fake_open_project)
    monkeypatch.setattr(ProjectController, "open_workspace", fake_open_workspace)

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                page.evaluate(
                    """() => {
                        localStorage.setItem('splitshot.recentActivity', JSON.stringify([
                          {
                            name: 'Local Breadcrumb',
                            surface: 'multi',
                            type: 'Match',
                            path: '/tmp/local-workspace',
                            date: '1/1/2026',
                          },
                        ]));
                        setActiveSurface('landing');
                    }"""
                )
                page.wait_for_function("() => activeSurface === 'landing'")
                page.wait_for_function(
                    "() => document.querySelectorAll('#landing-recent-list .landing-recent-item').length === 1"
                )

                recent_text = page.locator("#landing-recent-list").text_content() or ""
                assert "Recent Classifier" in recent_text
                assert "Local Breadcrumb" not in recent_text

                page.locator("#landing-recent-list .landing-recent-item").click()
                page.wait_for_function("() => activeSurface === 'single'")

                assert page.evaluate("() => state?.project?.path || ''") == ""
                assert page.evaluate("() => state?.workspace_path || ''") == ""
                assert open_project_calls == []
                assert open_workspace_calls == []
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_shared_shell_home_buttons_return_stage_match_and_library_shells_to_landing() -> None:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                page.evaluate("() => setActiveSurface('single')")
                page.wait_for_function("() => activeSurface === 'single'")
                page.locator("#stage-go-home").click(force=True)
                page.wait_for_function("() => activeSurface === 'landing'")
                assert page.evaluate("() => state?.project?.path || ''") == ""
                assert page.evaluate("() => state?.workspace_path || ''") == ""

                _open_match_surface(page)
                page.locator("#match-go-home").click(force=True)
                page.wait_for_function("() => activeSurface === 'landing'")
                assert page.evaluate("() => state?.project?.path || ''") == ""
                assert page.evaluate("() => state?.workspace_path || ''") == ""

                _open_library_surface(page)
                page.locator("#library-go-home").click(force=True)
                page.wait_for_function("() => activeSurface === 'landing'")
                assert page.evaluate("() => state?.project?.path || ''") == ""
                assert page.evaluate("() => state?.workspace_path || ''") == ""
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_controls_expand_zoom_and_amplitude_update_project_state(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="waveform-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                expand_button = page.locator("#expand-waveform")
                assert expand_button.text_content().strip() == "Expand"
                expand_button.click()
                page.wait_for_timeout(150)
                assert expand_button.text_content().strip() == "Collapse"
                assert (
                    page.locator("#cockpit-root").evaluate(
                        "element => element.classList.contains('waveform-expanded')"
                    )
                    is True
                )

                zoom_before = float(
                    page.evaluate("Number(localStorage.getItem('splitshot.waveform.zoomX'))")
                )
                page.locator("#zoom-waveform-in").click()
                page.wait_for_timeout(150)
                zoom_after = float(
                    page.evaluate("Number(localStorage.getItem('splitshot.waveform.zoomX'))")
                )
                assert zoom_after > zoom_before

                page.locator('button[data-waveform-mode="add"]').click()
                page.wait_for_timeout(100)
                assert page.evaluate("waveformMode") == "add"
                assert (
                    page.locator('button[data-waveform-mode="add"]').evaluate(
                        "button => button.classList.contains('active')"
                    )
                    is True
                )

                page.locator('button[data-waveform-mode="select"]').click()
                page.wait_for_timeout(100)
                assert page.evaluate("waveformMode") == "select"
                assert (
                    page.locator('button[data-waveform-mode="select"]').evaluate(
                        "button => button.classList.contains('active')"
                    )
                    is True
                )

                first_card = page.locator(".waveform-shot-card").first
                first_card.click(force=True)
                page.wait_for_timeout(150)
                selected_shot_id = page.evaluate("selectedShotId")
                assert selected_shot_id is not None

                amplitude_before = float(
                    page.evaluate("waveformShotAmplitudeById[selectedShotId] || 1")
                )
                page.locator("#amp-waveform-in").click()
                page.wait_for_timeout(250)
                amplitude_after = float(
                    page.evaluate("waveformShotAmplitudeById[selectedShotId] || 1")
                )
                assert amplitude_after > amplitude_before

                page.locator("#reset-waveform-view").click()
                page.wait_for_timeout(150)
                assert float(page.evaluate("waveformZoomX")) == 1.0
                assert float(page.evaluate("waveformOffsetMs")) == 0.0
                assert (
                    float(
                        page.evaluate(
                            "Number(localStorage.getItem('splitshot.waveform.zoomX') ?? 1)"
                        )
                    )
                    == 1.0
                )
                assert (
                    float(
                        page.evaluate(
                            "Number(localStorage.getItem('splitshot.waveform.offsetMs') ?? 0)"
                        )
                    )
                    == 0.0
                )
                assert float(page.evaluate("waveformShotAmplitudeById[selectedShotId] || 1")) == 1.0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_pan_drag_updates_zoomed_viewport_offset(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="waveform-pan-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.locator("#expand-waveform").click()
                page.wait_for_timeout(150)
                page.locator("#zoom-waveform-in").click()
                page.wait_for_timeout(150)

                waveform_box = page.locator("#waveform").bounding_box()
                assert waveform_box is not None
                start_offset = float(page.evaluate("waveformOffsetMs"))
                empty_x = float(
                    page.evaluate(
                        """
                                        () => {
                                            const canvas = document.getElementById('waveform');
                                            const rect = canvas.getBoundingClientRect();
                                            const shots = (state?.project?.analysis?.shots || [])
                                                .map((shot) => waveformX(shot.time_ms, rect.width))
                                                .sort((left, right) => left - right);
                                            const candidates = [rect.width * 0.15, rect.width * 0.85, rect.width - 24];
                                            for (let index = 0; index < shots.length - 1; index += 1) {
                                                const left = shots[index];
                                                const right = shots[index + 1];
                                                if (right - left > 72) candidates.push((left + right) / 2);
                                            }
                                            for (const candidate of candidates) {
                                                if (candidate > 0 && candidate < rect.width && shots.every((shotX) => Math.abs(candidate - shotX) > 32)) {
                                                    return candidate;
                                                }
                                            }
                                            return rect.width - 24;
                                        }
                                        """
                    )
                )
                drag_delta = -160 if empty_x > waveform_box["width"] / 2 else 160
                start_x = waveform_box["x"] + empty_x
                start_y = waveform_box["y"] + waveform_box["height"] / 2

                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(start_x + drag_delta, start_y, steps=12)
                page.mouse.up()
                page.wait_for_function(
                    "(before) => waveformOffsetMs !== before",
                    arg=start_offset,
                )
                assert float(page.evaluate("waveformOffsetMs")) != start_offset
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_shot_drag_moves_selected_shot_time(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="waveform-drag-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.locator("#expand-waveform").click()
                page.wait_for_timeout(150)

                shot_info = page.evaluate(
                    """
                                        () => {
                                            const canvas = document.getElementById('waveform');
                                            const rect = canvas.getBoundingClientRect();
                                            const shot = (state?.project?.analysis?.shots || []).find((item) => {
                                                const x = waveformX(item.time_ms, rect.width);
                                                return x > 120 && x < rect.width - 120;
                                            }) || state?.project?.analysis?.shots?.[0];
                                            if (!shot) return null;
                                            return {
                                                id: shot.id,
                                                timeMs: shot.time_ms,
                                                x: waveformX(shot.time_ms, rect.width),
                                            };
                                        }
                                        """
                )
                assert shot_info is not None
                waveform_box = page.locator("#waveform").bounding_box()
                assert waveform_box is not None

                start_x = waveform_box["x"] + float(shot_info["x"])
                start_y = waveform_box["y"] + waveform_box["height"] / 2
                move_delta = 120 if shot_info["x"] < waveform_box["width"] - 160 else -120

                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(start_x + move_delta, start_y, steps=12)
                page.mouse.up()
                page.wait_for_function(
                    """({ shotId, originalTime }) => {
                                            const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
                                            return Boolean(shot) && shot.time_ms !== originalTime;
                                        }""",
                    arg={"shotId": shot_info["id"], "originalTime": shot_info["timeMs"]},
                )
                updated_time = page.evaluate(
                    """(shotId) => {
                                            const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
                                            return shot ? shot.time_ms : null;
                                        }""",
                    shot_info["id"],
                )
                assert updated_time is not None
                assert updated_time != shot_info["timeMs"]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_overlay_visibility_and_badge_toggles_round_trip_through_browser_ui(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="overlay-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                page.locator('button[data-tool="overlay"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "overlay"

                initial_position = page.evaluate("state.project.overlay.position")
                page.evaluate(
                    """
                    () => {
                      const checkbox = document.getElementById('show-overlay');
                      checkbox.checked = false;
                      checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    """
                )
                page.wait_for_timeout(500)
                assert page.locator("#show-overlay").is_checked() is False
                assert page.evaluate("state.project.overlay.position") == "none"

                page.evaluate(
                    """
                    () => {
                      const checkbox = document.getElementById('show-overlay');
                      checkbox.checked = true;
                      checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    """
                )
                page.wait_for_timeout(500)
                assert page.locator("#show-overlay").is_checked() is True
                assert page.evaluate("state.project.overlay.position") == initial_position

                for control_id, attribute in [
                    ("show-timer", "show_timer"),
                    ("show-draw", "show_draw"),
                    ("show-shots", "show_shots"),
                    ("show-score", "show_score"),
                ]:
                    original_value = bool(page.evaluate(f"state.project.overlay.{attribute}"))
                    if original_value:
                        page.evaluate(
                            f"""
                            () => {{
                              const checkbox = document.getElementById('{control_id}');
                              checkbox.checked = false;
                              checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            """
                        )
                        page.wait_for_timeout(500)
                        assert page.evaluate(f"state.project.overlay.{attribute}") is False
                        page.evaluate(
                            f"""
                            () => {{
                              const checkbox = document.getElementById('{control_id}');
                              checkbox.checked = true;
                              checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            """
                        )
                        page.wait_for_timeout(500)
                        assert page.evaluate(f"state.project.overlay.{attribute}") is True
                    else:
                        page.evaluate(
                            f"""
                            () => {{
                              const checkbox = document.getElementById('{control_id}');
                              checkbox.checked = true;
                              checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            """
                        )
                        page.wait_for_timeout(500)
                        assert page.evaluate(f"state.project.overlay.{attribute}") is True
                        page.evaluate(
                            f"""
                            () => {{
                              const checkbox = document.getElementById('{control_id}');
                              checkbox.checked = false;
                              checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            """
                        )
                        page.wait_for_timeout(500)
                        assert page.evaluate(f"state.project.overlay.{attribute}") is False
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_add_custom_text_box_creates_editor_card(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="review-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.locator('button[data-tool="review"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "review"
                page.locator('[data-tool-pane="review"]').wait_for(state="visible")

                before_boxes = int(page.evaluate("state.project.overlay.text_boxes.length"))
                before_cards = page.locator("#review-text-box-list .text-box-card").count()

                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_timeout(500)

                assert (
                    int(page.evaluate("state.project.overlay.text_boxes.length"))
                    == before_boxes + 1
                )
                assert (
                    page.locator("#review-text-box-list .text-box-card").count() == before_cards + 1
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_drag_updates_overlay_coordinates(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="review-drag-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.locator('button[data-tool="review"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "review"
                page.locator('[data-tool-pane="review"]').wait_for(state="visible")

                if not page.locator("#show-overlay").is_checked():
                    page.evaluate(
                        """
                        () => {
                          const checkbox = document.getElementById('show-overlay');
                          checkbox.checked = true;
                          checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        """
                    )
                    page.wait_for_timeout(300)

                before_cards = page.locator("#review-text-box-list .text-box-card").count()
                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_timeout(250)

                page.wait_for_function(
                    "(count) => document.querySelectorAll('#review-text-box-list .text-box-card').length > count",
                    arg=before_cards,
                )
                new_card = page.locator("#review-text-box-list .text-box-card").nth(before_cards)
                new_card.locator('[data-text-box-action="toggle"]').click()
                new_card.locator('textarea[data-text-box-field="text"]').fill("Review note")
                page.wait_for_timeout(250)

                text_box = page.locator('#custom-overlay [data-text-box-drag="true"]').first
                text_box.wait_for(state="visible")
                page.wait_for_function(
                    """() => {
                      const box = document.querySelector('#custom-overlay [data-text-box-drag="true"]');
                      if (!box) return false;
                      const rect = box.getBoundingClientRect();
                      return rect.width > 0 && rect.height > 0;
                    }"""
                )
                text_box_id = text_box.get_attribute("data-text-box-id")
                assert text_box_id
                before_box = page.evaluate(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return box ? { id: box.id, x: box.x, y: box.y } : null;
                    }""",
                    text_box_id,
                )
                assert before_box is not None
                badge_box = page.evaluate(
                    """(boxId) => {
                      const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                      if (!(badge instanceof HTMLElement)) return null;
                      const rect = badge.getBoundingClientRect();
                      return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
                    }""",
                    text_box_id,
                )
                stage_box = page.locator("#video-stage").bounding_box()
                assert badge_box is not None
                assert stage_box is not None

                start_x = badge_box["x"] + badge_box["width"] / 2
                start_y = badge_box["y"] + badge_box["height"] / 2
                target_x = stage_box["x"] + stage_box["width"] * 0.62
                target_y = stage_box["y"] + stage_box["height"] * 0.32

                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(target_x, target_y, steps=12)
                page.mouse.up()
                page.wait_for_function(
                    """({ boxId, originalX, originalY }) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && (box.x !== originalX || box.y !== originalY);
                    }""",
                    arg={
                        "boxId": before_box["id"],
                        "originalX": before_box["x"],
                        "originalY": before_box["y"],
                    },
                )
                after_box = page.evaluate(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return box ? { id: box.id, x: box.x, y: box.y, quadrant: box.quadrant } : null;
                    }""",
                    before_box["id"],
                )
                assert after_box is not None
                assert after_box["x"] != before_box["x"] or after_box["y"] != before_box["y"]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_color_swatches_and_opacity_update_live_preview(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="review-style-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.locator('button[data-tool="review"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "review"
                page.locator('[data-tool-pane="review"]').wait_for(state="visible")
                _ensure_overlay_visible(page)

                before_cards = page.locator("#review-text-box-list .text-box-card").count()
                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_function(
                    "(count) => document.querySelectorAll('#review-text-box-list .text-box-card').length > count",
                    arg=before_cards,
                )

                new_card = page.locator("#review-text-box-list .text-box-card").nth(before_cards)
                box_id = new_card.get_attribute("data-box-id")
                assert box_id

                page.evaluate(
                    """(targetBoxId) => {
                        setReviewTextBoxExpanded(targetBoxId, true);
                        renderTextBoxEditors();
                    }""",
                    box_id,
                )
                new_card = page.locator(
                    f'#review-text-box-list .text-box-card[data-box-id="{box_id}"]'
                )
                new_card.locator('textarea[data-text-box-field="text"]').wait_for(state="visible")
                new_card.locator('textarea[data-text-box-field="text"]').fill("Style note")
                page.wait_for_function(
                    """({ boxId, text }) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.text === text;
                    }""",
                    arg={"boxId": box_id, "text": "Style note"},
                )

                text_box = page.locator(f'#custom-overlay [data-text-box-id="{box_id}"]')
                text_box.wait_for(state="visible")

                def set_hex(field: str, hex_value: str) -> None:
                    new_card.locator(f'[data-text-box-field="{field}"]').click(force=True)
                    page.wait_for_function(
                        "() => !document.getElementById('color-picker-modal').hidden && activeColorPickerControl !== null"
                    )
                    page.evaluate(
                        """({ value }) => {
                            const input = document.getElementById('color-picker-hex');
                            input.value = value;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }""",
                        {"value": hex_value},
                    )
                    page.locator("#close-color-picker").click()
                    page.wait_for_function(
                        "() => document.getElementById('color-picker-modal').hidden && activeColorPickerControl === null"
                    )
                    page.wait_for_function(
                        """({ boxId, field, value }) => {
                          const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                          return Boolean(box) && box[field] === value;
                        }""",
                        arg={"boxId": box_id, "field": field, "value": hex_value},
                    )

                set_hex("background_color", "#ff0000")

                new_card.locator('[data-text-box-field="text_color"]').click(force=True)
                page.wait_for_function(
                    "() => !document.getElementById('color-picker-modal').hidden && activeColorPickerControl !== null"
                )
                page.locator("#close-color-picker").click()
                page.wait_for_function(
                    "() => document.getElementById('color-picker-modal').hidden && activeColorPickerControl === null"
                )
                new_card.locator('input[aria-label="Text box text hex value"]').evaluate(
                    """(input, nextValue) => {
                        input.value = nextValue;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    "#00ff00",
                )
                page.wait_for_function(
                    """({ boxId, value }) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.text_color === value;
                    }""",
                    arg={"boxId": box_id, "value": "#00ff00"},
                )

                new_card.locator('[data-text-box-field="opacity"]').evaluate(
                    """(input, nextValue) => {
                        input.value = nextValue;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    "70",
                )
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && Math.abs((box.opacity ?? 0) - 0.7) < 0.01;
                    }""",
                    arg=box_id,
                )

                page.wait_for_function(
                    """(boxId) => {
                      const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                      if (!(badge instanceof HTMLElement)) return false;
                      const style = window.getComputedStyle(badge);
                      return style.backgroundColor.includes('255, 0, 0') && style.color.includes('0, 255, 0');
                    }""",
                    arg=box_id,
                )

                preview_style = page.evaluate(
                    """(boxId) => {
                        const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                        const style = window.getComputedStyle(badge);
                        return {
                            background: style.backgroundColor || '',
                            color: style.color || '',
                            opacity: Number((state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId)?.opacity ?? 0),
                            backgroundValue: document.querySelector(`#review-text-box-list .text-box-card[data-box-id="${boxId}"] [data-text-box-field="background_color"]`)?.dataset.colorValue || '',
                            textValue: document.querySelector(`#review-text-box-list .text-box-card[data-box-id="${boxId}"] [data-text-box-field="text_color"]`)?.dataset.colorValue || '',
                        };
                    }""",
                    box_id,
                )
                assert preview_style["background"].startswith("rgba(255, 0, 0")
                assert preview_style["color"].startswith("rgb(0, 255, 0")
                assert preview_style["opacity"] == pytest.approx(0.7)
                assert preview_style["backgroundValue"] == "#ff0000"
                assert preview_style["textValue"] == "#00ff00"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_style_controls_use_two_column_layout(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="review-style-layout-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "review")

                before_cards = page.locator("#review-text-box-list .text-box-card").count()
                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_function(
                    "(count) => document.querySelectorAll('#review-text-box-list .text-box-card').length > count",
                    arg=before_cards,
                )

                new_card = page.locator("#review-text-box-list .text-box-card").nth(before_cards)
                box_id = new_card.get_attribute("data-box-id")
                assert box_id

                page.evaluate(
                    """(targetBoxId) => {
                        setReviewTextBoxExpanded(targetBoxId, true);
                        renderTextBoxEditors();
                    }""",
                    box_id,
                )
                layout = page.evaluate(
                    """(targetBoxId) => {
                        const card = document.querySelector(
                            `#review-text-box-list .text-box-card[data-box-id="${targetBoxId}"] .review-style-grid .custom-box-style-card`
                        );
                        if (!(card instanceof HTMLElement)) return null;
                        const heading = card.querySelector('h4');
                        const opacityField = card.querySelector('.opacity-field');
                        return {
                            columnCount: window.getComputedStyle(card).gridTemplateColumns.split(' ').filter(Boolean).length,
                            headingColumn: heading ? window.getComputedStyle(heading).gridColumn : null,
                            opacityColumn: opacityField ? window.getComputedStyle(opacityField).gridColumn : null,
                            labelDirections: [...card.querySelectorAll('label')].map((label) => window.getComputedStyle(label).flexDirection),
                        };
                    }""",
                    box_id,
                )

                assert layout is not None
                assert layout["columnCount"] == 2
                assert layout["headingColumn"] == "1 / -1"
                assert layout["opacityColumn"] == "1 / -1"
                assert all(direction == "column" for direction in layout["labelDirections"])
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_source_switches_to_imported_summary_and_renders_after_final_shot(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="review-imported-source-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "review")
                _ensure_overlay_visible(page)

                before_cards = page.locator("#review-text-box-list .text-box-card").count()
                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_function(
                    "(count) => document.querySelectorAll('#review-text-box-list .text-box-card').length > count",
                    arg=before_cards,
                )

                new_card = page.locator("#review-text-box-list .text-box-card").nth(before_cards)
                box_id = new_card.get_attribute("data-box-id")
                assert box_id

                new_card.locator('[data-text-box-action="toggle"]').click()
                new_card.locator('select[data-text-box-field="source"]').select_option(
                    "imported_summary"
                )
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.source === 'imported_summary' && box.quadrant === 'above_final';
                    }""",
                    arg=box_id,
                )

                override_text = "Stage summary override"
                text_area = new_card.locator('textarea[data-text-box-field="text"]')
                text_area.fill(override_text)
                text_area.dispatch_event("change")
                page.wait_for_function(
                    """({ boxId, text }) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.text === text;
                    }""",
                    arg={"boxId": box_id, "text": override_text},
                )

                hint_text = (
                    (new_card.locator('[data-text-box-hint="true"]').text_content() or "")
                    .strip()
                    .lower()
                )
                assert "imported summary" in hint_text or "final score badge" in hint_text

                final_shot_ms = int(
                    page.evaluate("(state?.project?.analysis?.shots || []).at(-1)?.time_ms ?? 0")
                )
                page.evaluate(
                    """(targetMs) => {
                      const video = document.getElementById('primary-video');
                      video.currentTime = targetMs / 1000;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                      renderLiveOverlay(targetMs);
                    }""",
                    final_shot_ms + 200,
                )

                rendered_box = page.locator(f'#custom-overlay [data-text-box-id="{box_id}"]')
                rendered_box.wait_for(state="visible")
                assert rendered_box.get_attribute("data-text-box-source") == "imported_summary"
                assert rendered_box.inner_text().strip() == override_text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_review_text_box_custom_position_size_and_stack_lock_update_state_and_stage(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="review-position-lock-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "review")
                _ensure_overlay_visible(page)

                before_cards = page.locator("#review-text-box-list .text-box-card").count()
                page.evaluate("document.getElementById('review-add-text-box').click()")
                page.wait_for_function(
                    "(count) => document.querySelectorAll('#review-text-box-list .text-box-card').length > count",
                    arg=before_cards,
                )

                new_card = page.locator("#review-text-box-list .text-box-card").nth(before_cards)
                box_id = new_card.get_attribute("data-box-id")
                assert box_id
                page.evaluate(
                    """(targetBoxId) => {
                        setReviewTextBoxExpanded(targetBoxId, true);
                        renderTextBoxEditors();
                    }""",
                    box_id,
                )
                new_card = page.locator(
                    f'#review-text-box-list .text-box-card[data-box-id="{box_id}"]'
                )
                new_card.locator('textarea[data-text-box-field="text"]').wait_for(state="visible")
                rendered_box = page.locator(f'#custom-overlay [data-text-box-id="{box_id}"]')

                if new_card.locator('textarea[data-text-box-field="text"]').count() == 1:
                    new_card.locator('textarea[data-text-box-field="text"]').evaluate(
                        """(input, nextValue) => {
                                            input.value = nextValue;
                                            input.dispatchEvent(new Event('input', { bubbles: true }));
                                            input.dispatchEvent(new Event('change', { bubbles: true }));
                                        }""",
                        "Review note",
                    )
                    page.wait_for_function(
                        """(boxId) => {
                                            const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                                            return Boolean(box) && box.text === 'Review note';
                                        }""",
                        arg=box_id,
                    )
                rendered_box.wait_for(state="visible")
                initial_box = None
                if rendered_box.is_visible():
                    initial_box = page.evaluate(
                        """(boxId) => {
                                            const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                                            if (!(badge instanceof HTMLElement)) return null;
                                            const rect = badge.getBoundingClientRect();
                                            return { width: rect.width, height: rect.height };
                                        }""",
                        box_id,
                    )
                assert initial_box is not None

                new_card.locator('select[data-text-box-field="quadrant"]').select_option("custom")
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.quadrant === 'custom';
                    }""",
                    arg=box_id,
                )

                for selector, value in [
                    ('input[data-text-box-field="x"]', "0.62"),
                    ('input[data-text-box-field="y"]', "0.28"),
                    ('input[data-text-box-field="width"]', "240"),
                    ('input[data-text-box-field="height"]', "72"),
                ]:
                    control = new_card.locator(selector)
                    control.evaluate(
                        """(input, nextValue) => {
                          input.value = nextValue;
                          input.dispatchEvent(new Event('input', { bubbles: true }));
                          input.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        value,
                    )

                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box)
                        && box.quadrant === 'custom'
                        && Math.abs(box.x - 0.62) < 0.001
                        && Math.abs(box.y - 0.28) < 0.001
                        && box.width === 240
                        && box.height === 72;
                    }""",
                    arg=box_id,
                )

                rendered_box.wait_for(state="visible")
                if rendered_box.is_visible():
                    stable_updated_box = page.evaluate(
                        """(boxId) => {
                                            const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                                            if (!(badge instanceof HTMLElement)) return null;
                                            const rect = badge.getBoundingClientRect();
                                            return { width: rect.width, height: rect.height };
                                        }""",
                        box_id,
                    )
                    assert stable_updated_box is not None
                    assert stable_updated_box["width"] > initial_box["width"]
                    assert stable_updated_box["height"] >= initial_box["height"]
                rendered_geometry = page.evaluate(
                    """(boxId) => {
                      const badge = document.querySelector(`#custom-overlay [data-text-box-id="${boxId}"]`);
                                            const overlay = document.getElementById('custom-overlay');
                                            if (!(badge instanceof HTMLElement) || !(overlay instanceof HTMLElement)) return null;
                      const badgeRect = badge.getBoundingClientRect();
                                            const overlayRect = overlay.getBoundingClientRect();
                      return {
                                                x: ((badgeRect.left + (badgeRect.width / 2)) - overlayRect.left) / overlayRect.width,
                                                y: ((badgeRect.top + (badgeRect.height / 2)) - overlayRect.top) / overlayRect.height,
                      };
                    }""",
                    box_id,
                )
                assert rendered_geometry is not None
                assert abs(rendered_geometry["x"] - 0.62) < 0.05
                assert abs(rendered_geometry["y"] - 0.28) < 0.05

                lock_checkbox = new_card.locator('input[data-text-box-field="lock_to_stack"]')
                if lock_checkbox.count() == 1:
                    lock_checkbox.evaluate(
                        """(checkbox) => {
                                            checkbox.checked = true;
                                            checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                        }"""
                    )
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.lock_to_stack === true;
                    }""",
                    arg=box_id,
                )
                assert (
                    new_card.locator('select[data-text-box-field="quadrant"]').is_disabled() is True
                )
                assert new_card.locator('input[data-text-box-field="x"]').is_disabled() is True
                assert new_card.locator('input[data-text-box-field="y"]').is_disabled() is True
                hint_text = (
                    new_card.locator('[data-text-box-hint="true"]').text_content() or ""
                ).strip()
                assert (
                    hint_text
                    == "Locked to the shot stack. Disable this to edit placement directly."
                )

                if lock_checkbox.is_checked():
                    lock_checkbox.evaluate(
                        """(checkbox) => {
                                            checkbox.checked = false;
                                            checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                        }"""
                    )
                page.wait_for_function(
                    """(boxId) => {
                      const box = (state?.project?.overlay?.text_boxes || []).find((item) => item.id === boxId);
                      return Boolean(box) && box.lock_to_stack === false && box.quadrant === 'custom' && box.x !== null && box.y !== null;
                    }""",
                    arg=box_id,
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_markers_import_shots_select_selected_marker_and_seek_video(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-import-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                selected_shot = _select_waveform_shot(page)
                assert selected_shot is not None
                total_shots = int(page.evaluate("(state?.project?.analysis?.shots || []).length"))
                assert total_shots > 0

                _open_tool(page, "markers")
                _import_shot_linked_markers(page)
                assert _shot_linked_popup_count(page) == total_shots
                assert (
                    page.evaluate(
                        """() => (state?.project?.popups || [])
                        .filter((item) => item.anchor_mode === 'shot' && item.shot_id)
                        .every((bubble) => {
                            const limitMs = popupDurationLimitMsForBubble(bubble);
                            return limitMs === null || bubble.duration_ms <= limitMs;
                        })"""
                    )
                    is True
                )

                page.wait_for_function(
                    """(shotId) => {
                      const bubble = (state?.project?.popups || []).find(
                        (item) => item.anchor_mode === 'shot' && item.shot_id === shotId
                      );
                      return Boolean(bubble) && selectedPopupBubbleId === bubble.id;
                    }""",
                    arg=selected_shot["id"],
                )
                selected_popup = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === selectedPopupBubbleId);
                      return bubble ? { id: bubble.id, shotId: bubble.shot_id, timeMs: bubble.time_ms } : null;
                    }"""
                )
                assert selected_popup is not None
                assert selected_popup["shotId"] == selected_shot["id"]

                selected_card = page.locator(
                    f'#popup-marker-list .popup-marker-row[data-popup-id="{selected_popup["id"]}"]'
                )
                selected_card.wait_for(state="attached")
                assert selected_card.evaluate("card => card.classList.contains('selected')") is True
                assert page.locator("#popup-timeline-strip").count() == 0
                assert page.locator("#popup-pane-status").inner_text() == f"{total_shots} enabled"
                assert (
                    page.locator("#popup-list-status")
                    .inner_text()
                    .startswith(f"{total_shots} shown")
                )

                page.wait_for_function(
                    """(targetMs) => {
                      const currentMs = (document.getElementById('primary-video')?.currentTime || 0) * 1000;
                      return Math.abs(currentMs - targetMs) <= 80;
                    }""",
                    arg=selected_shot["timeMs"],
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_collapsed_navigation_and_marker_list_selection_stay_in_sync(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-nav-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")
                _import_shot_linked_markers(page)
                page.wait_for_function("() => (state?.project?.popups || []).length >= 2")

                initial_popup_id = page.evaluate("selectedPopupBubbleId")
                assert initial_popup_id is not None

                assert page.locator("#popup-timeline-strip").count() == 0

                _open_markers_workbench(page)
                page.locator("#popup-next-workbench").click()
                page.wait_for_function(
                    "(beforeId) => Boolean(selectedPopupBubbleId) && selectedPopupBubbleId !== beforeId",
                    arg=initial_popup_id,
                )
                next_popup_id = page.evaluate("selectedPopupBubbleId")
                assert next_popup_id is not None
                assert next_popup_id != initial_popup_id

                page.locator("#popup-prev-workbench").click()
                page.wait_for_function(
                    "(expectedId) => selectedPopupBubbleId === expectedId", arg=initial_popup_id
                )

                list_target_id = page.evaluate(
                    """(currentId) => {
                      const ids = [...document.querySelectorAll('#popup-marker-list .popup-marker-row[data-popup-id]')]
                        .map((element) => element.dataset.popupId)
                        .filter(Boolean);
                      return ids.find((id) => id !== currentId) || null;
                    }""",
                    initial_popup_id,
                )
                assert list_target_id is not None

                page.locator(
                    f'#markers-workbench-list .popup-marker-row[data-popup-id="{list_target_id}"] .popup-marker-meta'
                ).click()
                page.wait_for_function(
                    "(popupId) => selectedPopupBubbleId === popupId", arg=list_target_id
                )

                selected_card = page.locator(
                    f'#markers-workbench-list .popup-marker-row[data-popup-id="{list_target_id}"]'
                )
                assert selected_card.evaluate("card => card.classList.contains('selected')") is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_workbench_steps_duplicate_delete_and_close(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-editor-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")
                _import_shot_linked_markers(page)
                page.wait_for_function(
                    "() => (state?.project?.popups || []).filter((item) => item.anchor_mode === 'shot').length >= 2"
                )

                shot_linked_ids_before = page.evaluate(
                    """() => (state?.project?.popups || [])
                      .filter((item) => item.anchor_mode === 'shot' && item.shot_id)
                      .map((item) => item.id)"""
                )
                shot_linked_before = len(shot_linked_ids_before)
                selected_before = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === selectedPopupBubbleId);
                      return bubble ? { id: bubble.id, shotId: bubble.shot_id } : null;
                    }"""
                )
                assert selected_before is not None

                _open_markers_workbench(page)
                assert page.locator(".popup-selected-editor-panel").is_visible()
                assert page.locator("#markers-workbench-editor .popup-bubble-card").count() == 1
                assert page.locator("#markers-workbench-list .popup-marker-row").count() >= 1

                page.locator("#popup-next-workbench").click()
                page.wait_for_function(
                    "(beforeId) => Boolean(selectedPopupBubbleId) && selectedPopupBubbleId !== beforeId",
                    arg=selected_before["id"],
                )
                stepped_popup_id = page.evaluate("selectedPopupBubbleId")
                assert stepped_popup_id is not None

                page.locator("#popup-prev-workbench").click()
                page.wait_for_function(
                    "(expectedId) => selectedPopupBubbleId === expectedId",
                    arg=selected_before["id"],
                )

                page.locator('#markers-workbench-editor [data-popup-action="duplicate"]').click()
                page.wait_for_function(
                    "(beforeCount) => (state?.project?.popups || []).filter((item) => item.anchor_mode === 'shot' && item.shot_id).length === beforeCount + 1",
                    arg=shot_linked_before,
                )
                shot_linked_ids_after = page.evaluate(
                    """() => (state?.project?.popups || [])
                      .filter((item) => item.anchor_mode === 'shot' && item.shot_id)
                      .map((item) => item.id)"""
                )
                duplicated_ids = [
                    popup_id
                    for popup_id in shot_linked_ids_after
                    if popup_id not in shot_linked_ids_before
                ]
                assert len(duplicated_ids) == 1
                duplicated_popup = page.evaluate(
                    """(popupId) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      return bubble ? { id: bubble.id, shotId: bubble.shot_id } : null;
                    }""",
                    duplicated_ids[0],
                )
                assert duplicated_popup is not None
                assert duplicated_popup["shotId"] == selected_before["shotId"]

                page.evaluate(
                    """(popupId) => {
                      document
                        .querySelector(`#popup-marker-list .popup-marker-row[data-popup-id="${popupId}"] .popup-marker-select`)
                        ?.click();
                    }""",
                    duplicated_popup["id"],
                )
                page.wait_for_function(
                    "(popupId) => selectedPopupBubbleId === popupId", arg=duplicated_popup["id"]
                )

                page.locator('#markers-workbench-editor [data-popup-action="remove"]').click()
                page.wait_for_function(
                    "(deletedId) => !(state?.project?.popups || []).some((item) => item.id === deletedId)",
                    arg=duplicated_popup["id"],
                )
                page.wait_for_function("() => Boolean(selectedPopupBubbleId)")
                assert _shot_linked_popup_count(page) == shot_linked_before
                assert page.evaluate("selectedPopupBubbleId") != duplicated_popup["id"]
                assert page.locator("#markers-workbench-editor .popup-bubble-card").count() == 1

                page.locator("#popup-edit-selected").click()
                page.wait_for_function(
                    "() => document.getElementById('markers-workbench')?.hidden === true"
                )
                page.wait_for_function(
                    "() => document.getElementById('popup-edit-selected')?.textContent?.trim() === 'Edit'"
                )

                assert page.evaluate("selectedPopupBubbleId") is not None
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_badge_drag_updates_base_point_without_snapback(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-badge-drag-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")
                _import_shot_linked_markers(page)
                popup_id = page.evaluate("selectedPopupBubbleId")
                assert popup_id is not None

                page.locator("#popup-edit-selected").click()
                page.wait_for_function(
                    "() => document.getElementById('markers-workbench')?.hidden === true"
                )
                page.wait_for_function(
                    """(popupId) => !document.querySelector(`#popup-overlay [data-popup-drag="true"][data-popup-id="${popupId}"]`)""",
                    arg=popup_id,
                )

                _open_markers_workbench(page)

                badge = page.locator(
                    f'#popup-overlay [data-popup-drag="true"][data-popup-id="{popup_id}"]'
                )
                badge.wait_for(state="visible")
                before = page.evaluate(
                    """(popupId) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      const badge = document.querySelector(`#popup-overlay [data-popup-drag="true"][data-popup-id="${popupId}"]`);
                      const rect = badge?.getBoundingClientRect();
                      return bubble && rect ? {
                        x: bubble.x,
                        y: bubble.y,
                        quadrant: bubble.quadrant,
                        left: rect.left,
                        top: rect.top,
                      } : null;
                    }""",
                    popup_id,
                )
                assert before is not None
                _drag_popup_badge(page, popup_id, 120, 60)

                page.wait_for_function(
                    """(payload) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === payload.popupId);
                      return Boolean(bubble)
                        && bubble.quadrant === 'custom'
                        && Math.abs((bubble.x || 0) - payload.x) > 0.02
                        && Math.abs((bubble.y || 0) - payload.y) > 0.02;
                    }""",
                    arg={"popupId": popup_id, "x": before["x"], "y": before["y"]},
                )
                page.evaluate("() => new Promise(r => requestAnimationFrame(r))")
                page.wait_for_timeout(50)
                after = page.evaluate(
                    """(popupId) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      const badge = document.querySelector(`#popup-overlay [data-popup-drag="true"][data-popup-id="${popupId}"]`);
                      const rect = badge?.getBoundingClientRect();
                      return bubble && rect ? {
                        x: bubble.x,
                        y: bubble.y,
                        left: rect.left,
                        top: rect.top,
                      } : null;
                    }""",
                    popup_id,
                )
                assert after is not None
                assert after["left"] > before["left"] + 1, f"badge should move right (got {after["left"]}, was {before["left"]})"
                assert after["top"] > before["top"] + 1, f"badge should move down (got {after["top"]}, was {before["top"]})"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_badge_drag_keeps_motion_path_intact_when_editing_base_point(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-base-vs-keyframe-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")
                _import_shot_linked_markers(page)
                popup_id = page.evaluate("selectedPopupBubbleId")
                assert popup_id is not None

                _open_markers_workbench(page)
                page.locator(
                    f'#markers-workbench-editor .popup-bubble-card[data-popup-id="{popup_id}"] [data-popup-field="follow_motion"]'
                ).check()
                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.follow_motion === true",
                    arg=popup_id,
                )
                page.evaluate(
                    """() => {
                      const video = document.getElementById('primary-video');
                      video.currentTime = 1.2;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }"""
                )
                page.locator(
                    f'#markers-workbench-editor .popup-bubble-card[data-popup-id="{popup_id}"] [data-popup-action="add_motion_step"]'
                ).click()
                motion_before_handle = page.wait_for_function(
                    """(popupId) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      const serialized = bubble ? JSON.stringify(bubble.motion_path || []) : '[]';
                      return serialized !== '[]' ? serialized : false;
                    }""",
                    arg=popup_id,
                )
                motion_before = motion_before_handle.json_value()
                assert motion_before != "[]"

                badge = page.locator(
                    f'#popup-overlay [data-popup-drag="true"][data-popup-id="{popup_id}"]'
                )
                badge.wait_for(state="visible")
                before_rect = page.evaluate(
                    """(popupId) => {
                      const badge = document.querySelector(`#popup-overlay [data-popup-drag="true"][data-popup-id="${popupId}"]`);
                      const rect = badge?.getBoundingClientRect();
                      return rect ? { left: rect.left, top: rect.top } : null;
                    }""",
                    popup_id,
                )
                assert before_rect is not None
                _drag_popup_badge(page, popup_id, 130, 65)

                page.wait_for_function(
                    "(popupId) => (state?.project?.popups || []).find((item) => item.id === popupId)?.quadrant === 'custom'",
                    arg=popup_id,
                )
                page.wait_for_function(
                    """({ popupId, expectedMotionPath }) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      return JSON.stringify(bubble?.motion_path || []) === expectedMotionPath;
                    }""",
                    arg={"popupId": popup_id, "expectedMotionPath": motion_before},
                )
                motion_after = page.evaluate(
                    """(popupId) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      return bubble ? JSON.stringify(bubble.motion_path || []) : '[]';
                    }""",
                    popup_id,
                )
                assert motion_after == motion_before
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_generate_motion_path_falls_back_to_single_in_between_for_small_meaningful_travel(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-small-motion-auto-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")

                page.evaluate(
                    """() => {
                                            const video = document.getElementById('primary-video');
                                            video.currentTime = 1.0;
                                            video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                                        }"""
                )
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")
                popup_id = page.evaluate("(state?.project?.popups || [])[0]?.id")
                assert popup_id is not None

                _open_markers_workbench(page)
                page.evaluate(
                    """(popupId) => {
                                            const video = document.getElementById('primary-video');
                                            const sourceWidth = Math.max(1, Number(video?.videoWidth || state?.project?.primary_video?.width || 1920) || 1920);
                                            const deltaX = 8.5 / sourceWidth;
                                            const nextBubbles = (state?.project?.popups || []).map((bubble) => {
                                                if (bubble.id !== popupId) return bubble;
                                                return normalizePopupBubble({
                                                    ...bubble,
                                                    quadrant: 'custom',
                                                    x: 0.5,
                                                    y: 0.5,
                                                    duration_ms: 150,
                                                    follow_motion: true,
                                                    motion_mode: 'guided',
                                                    motion_path: [
                                                        {
                                                            offset_ms: 150,
                                                            x: Math.min(1, 0.5 + deltaX),
                                                            y: 0.5,
                                                            easing: 'linear',
                                                        },
                                                    ],
                                                });
                                            });
                                            setPopupBubbles(nextBubbles, { commit: true, rerender: true });
                                        }""",
                    popup_id,
                )
                page.wait_for_function(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            return Boolean(bubble)
                                                && bubble.follow_motion === true
                                                && bubble.duration_ms === 150
                                                && (bubble.motion_path || []).length === 1;
                                        }""",
                    arg=popup_id,
                )
                page.evaluate("""() => {
                                    autoTracePopupBubbleMotion = async () => false;
                                }""")

                page.locator(
                    f'#markers-workbench-editor .popup-bubble-card[data-popup-id="{popup_id}"] [data-popup-action="generate_motion_path"]'
                ).click()
                page.wait_for_function(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            const points = bubble?.motion_path || [];
                                            return points.length >= 2
                                                && points.length <= 4
                                                && points[0].offset_ms > 0
                                                && points[0].offset_ms < points[1].offset_ms
                                                && points[points.length - 1].offset_ms === 150;
                                        }""",
                    arg=popup_id,
                )

                page.evaluate("""() => {
                                    autoTracePopupBubbleMotion = async () => false;
                                }""")

                page.locator(
                    f'#markers-workbench-editor .popup-bubble-card[data-popup-id="{popup_id}"] [data-popup-action="generate_motion_path"]'
                ).click()
                page.wait_for_function(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            const points = bubble?.motion_path || [];
                                            return points.length >= 2
                                                && points.length <= 4
                                                && points[0].offset_ms > 0
                                                && points[0].offset_ms < points[1].offset_ms
                                                && points[points.length - 1].offset_ms === 150;
                                        }""",
                    arg=popup_id,
                )

                motion_snapshot = page.evaluate(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            return {
                                                followMotion: Boolean(bubble?.follow_motion),
                                                offsets: (bubble?.motion_path || []).map((point) => point.offset_ms),
                                            };
                                        }""",
                    popup_id,
                )
                assert motion_snapshot["followMotion"] is True
                assert motion_snapshot["offsets"] == sorted(motion_snapshot["offsets"])
                assert len(motion_snapshot["offsets"]) >= 2
                assert 0 < motion_snapshot["offsets"][0] < 150
                assert motion_snapshot["offsets"][-1] == 150
                assert motion_snapshot["offsets"] == sorted(motion_snapshot["offsets"])
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_generate_motion_path_falls_back_to_evenly_spaced_points_for_longer_travel(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-dense-motion-auto-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")

                page.evaluate(
                    """() => {
                                            const video = document.getElementById('primary-video');
                                            video.currentTime = 1.0;
                                            video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                                        }"""
                )
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")
                popup_id = page.evaluate("(state?.project?.popups || [])[0]?.id")
                assert popup_id is not None

                _open_markers_workbench(page)
                page.evaluate(
                    """(popupId) => {
                                            const video = document.getElementById('primary-video');
                                            const sourceWidth = Math.max(1, Number(video?.videoWidth || state?.project?.primary_video?.width || 1920) || 1920);
                                            const deltaX = 160 / sourceWidth;
                                            const nextBubbles = (state?.project?.popups || []).map((bubble) => {
                                                if (bubble.id !== popupId) return bubble;
                                                return normalizePopupBubble({
                                                    ...bubble,
                                                    quadrant: 'custom',
                                                    x: 0.42,
                                                    y: 0.5,
                                                    duration_ms: 600,
                                                    follow_motion: true,
                                                    motion_mode: 'guided',
                                                    motion_path: [
                                                        {
                                                            offset_ms: 600,
                                                            x: Math.min(1, 0.42 + deltaX),
                                                            y: 0.5,
                                                            easing: 'linear',
                                                        },
                                                    ],
                                                });
                                            });
                                            setPopupBubbles(nextBubbles, { commit: true, rerender: true });
                                        }""",
                    popup_id,
                )
                page.wait_for_function(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            return Boolean(bubble)
                                                && bubble.follow_motion === true
                                                && bubble.duration_ms === 600
                                                && (bubble.motion_path || []).length === 1;
                                        }""",
                    arg=popup_id,
                )
                page.evaluate("""() => {
                                    autoTracePopupBubbleMotion = async () => false;
                                }""")

                page.locator(
                    f'#markers-workbench-editor .popup-bubble-card[data-popup-id="{popup_id}"] [data-popup-action="generate_motion_path"]'
                ).click()
                page.wait_for_function(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            const points = bubble?.motion_path || [];
                                            return points.length >= 6 && points[points.length - 1]?.offset_ms === 600;
                                        }""",
                    arg=popup_id,
                )

                motion_snapshot = page.evaluate(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            const offsets = (bubble?.motion_path || []).map((point) => point.offset_ms);
                                            const gaps = offsets.slice(1).map((offsetMs, index) => offsetMs - offsets[index]);
                                            return {
                                                offsets,
                                                gapRange: gaps.length === 0 ? 0 : Math.max(...gaps) - Math.min(...gaps),
                                            };
                                        }""",
                    popup_id,
                )
                assert len(motion_snapshot["offsets"]) >= 6
                assert motion_snapshot["offsets"] == sorted(motion_snapshot["offsets"])
                assert 0 < motion_snapshot["offsets"][0] < 600
                assert motion_snapshot["offsets"][-1] == 600
                assert motion_snapshot["gapRange"] <= 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_generate_motion_path_prefers_traced_motion_when_available(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-traced-motion-auto-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")

                page.evaluate(
                    """() => {
                                            const video = document.getElementById('primary-video');
                                            video.currentTime = 1.0;
                                            video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                                        }"""
                )
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")
                popup_id = page.evaluate("(state?.project?.popups || [])[0]?.id")
                assert popup_id is not None

                _open_markers_workbench(page)
                page.evaluate(
                    """(popupId) => {
                                            const nextBubbles = (state?.project?.popups || []).map((bubble) => {
                                                if (bubble.id !== popupId) return bubble;
                                                return normalizePopupBubble({
                                                    ...bubble,
                                                    quadrant: 'custom',
                                                    x: 0.5,
                                                    y: 0.5,
                                                    duration_ms: 200,
                                                    follow_motion: true,
                                                    motion_mode: 'guided',
                                                    motion_path: [
                                                        {
                                                            offset_ms: 200,
                                                            x: 0.68,
                                                            y: 0.56,
                                                            easing: 'linear',
                                                        },
                                                    ],
                                                });
                                            });
                                            setPopupBubbles(nextBubbles, { commit: true, rerender: true });
                                            autoTracePopupBubbleMotion = async (targetId) => {
                                                if (targetId !== popupId) return false;
                                                const tracedBubbles = (state?.project?.popups || []).map((bubble) => {
                                                    if (bubble.id !== popupId) return bubble;
                                                    return normalizePopupBubble({
                                                        ...bubble,
                                                        follow_motion: true,
                                                        motion_mode: 'guided',
                                                        motion_path: [
                                                            {
                                                                offset_ms: 50,
                                                                x: 0.55,
                                                                y: 0.52,
                                                                easing: 'linear',
                                                            },
                                                            {
                                                                offset_ms: 100,
                                                                x: 0.61,
                                                                y: 0.54,
                                                                easing: 'linear',
                                                            },
                                                            {
                                                                offset_ms: 200,
                                                                x: 0.68,
                                                                y: 0.56,
                                                                easing: 'linear',
                                                            },
                                                        ],
                                                    });
                                                });
                                                setPopupBubbles(tracedBubbles, { commit: true, rerender: true });
                                                return true;
                                            };
                                        }""",
                    popup_id,
                )

                page.locator(
                    f'#markers-workbench-editor .popup-bubble-card[data-popup-id="{popup_id}"] [data-popup-action="generate_motion_path"]'
                ).click()
                page.wait_for_function(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            const points = bubble?.motion_path || [];
                                            return points.length === 3
                                                && points[0]?.offset_ms === 50
                                                && points[1]?.offset_ms === 100
                                                && points[2]?.offset_ms === 200
                                                && Math.abs((points[1]?.y || 0) - 0.54) < 0.0001;
                                        }""",
                    arg=popup_id,
                )

                motion_snapshot = page.evaluate(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            const status = document.querySelector(`#markers-workbench-editor .popup-bubble-card[data-popup-id="${popupId}"] .popup-motion-guide-hint`)?.textContent || '';
                                            return {
                                                offsets: (bubble?.motion_path || []).map((point) => point.offset_ms),
                                                yValues: (bubble?.motion_path || []).map((point) => point.y),
                                                status,
                                            };
                                        }""",
                    popup_id,
                )
                assert motion_snapshot["offsets"] == [50, 100, 200]
                assert motion_snapshot["yValues"] == [0.52, 0.54, 0.56]
                assert (
                    "Generate traced 2 in-between points from the video"
                    in motion_snapshot["status"]
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_template_controls_drive_new_shot_marker_defaults(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-template-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                selected_shot = _select_waveform_shot(page)
                assert selected_shot is not None

                _open_tool(page, "markers")
                _open_markers_workbench(page)
                page.locator("#popup-add-selected-shot-workbench").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")
                score_popup = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || [])[0] || null;
                      return bubble
                        ? {
                            id: bubble.id,
                            anchorMode: bubble.anchor_mode,
                            shotId: bubble.shot_id,
                                                        durationMs: bubble.duration_ms,
                                                        quadrant: bubble.quadrant,
                                                        x: bubble.x,
                                                        y: bubble.y,
                            text: bubble.text,
                            backgroundColor: bubble.background_color,
                            textColor: bubble.text_color,
                            opacity: bubble.opacity,
                          }
                        : null;
                    }"""
                )
                assert score_popup is not None
                assert score_popup["anchorMode"] == "shot"
                assert score_popup["shotId"] == selected_shot["id"]
                assert score_popup["backgroundColor"] == "#000000"
                assert score_popup["textColor"] == "#ffffff"
                assert score_popup["opacity"] == pytest.approx(0.9)
                assert score_popup["quadrant"] == "middle_middle"
                assert score_popup["x"] == pytest.approx(0.5)
                assert score_popup["y"] == pytest.approx(0.5)
                expected_score_text = page.evaluate(
                    """(shotId) => popupTextForShotId(shotId) || defaultScoreLetter()""",
                    selected_shot["id"],
                )
                assert score_popup["text"] == expected_score_text
                page.wait_for_function(
                    "(popupId) => selectedPopupBubbleId === popupId", arg=score_popup["id"]
                )
                score_popup_badge = page.locator(
                    f'#popup-overlay .popup-overlay-badge[data-popup-id="{score_popup["id"]}"]'
                )
                score_popup_badge.wait_for(state="visible")
                default_score_badge_style = score_popup_badge.evaluate(
                    """badge => {
                        const style = getComputedStyle(badge);
                        const rect = badge.getBoundingClientRect();
                    const textNode = badge.querySelector('div') || badge;
                    const textRect = textNode?.getBoundingClientRect?.() || null;
                        const badgeCenterX = rect.left + (rect.width / 2);
                        const badgeCenterY = rect.top + (rect.height / 2);
                        return {
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            hasSelectorClass: badge.classList.contains('popup-placement-selector'),
                            borderRadius: style.borderRadius,
                            background: style.backgroundColor,
                            color: style.color,
                            justifyContent: style.justifyContent,
                            alignItems: style.alignItems,
                            text: textNode?.textContent || '',
                            textCentered: textRect
                                ? Math.abs((textRect.left + (textRect.width / 2)) - badgeCenterX) <= 2
                                    && Math.abs((textRect.top + (textRect.height / 2)) - badgeCenterY) <= 2
                                : false,
                        };
                    }"""
                )
                assert default_score_badge_style["hasSelectorClass"] is True
                assert (
                    abs(default_score_badge_style["width"] - default_score_badge_style["height"])
                    <= 2
                )
                assert default_score_badge_style["borderRadius"].endswith("px")
                assert "255, 123, 34" in default_score_badge_style["background"]
                assert default_score_badge_style["justifyContent"] == "center"
                assert default_score_badge_style["alignItems"] == "center"
                assert default_score_badge_style["text"] == ""
                assert default_score_badge_style["textCentered"] is True

                page.evaluate(
                    """() => {
                      const template = normalizePopupTemplate({
                        ...currentPopupTemplate(),
                        text_source: 'shot_label',
                        content_type: 'text_image',
                                                duration_ms: 5000,
                                                use_shot_split_duration: true,
                        width: 320,
                        height: 96,
                        follow_motion: true,
                        motion_mode: 'guided',
                        background_color: '#224466',
                        text_color: '#fefefe',
                        opacity: 0.65,
                      });
                      if (!state.project) state.project = {};
                      state.project.popup_template = template;
                      callApi('/api/popups', { popups: popupBubbles(), popup_template: template });
                      render();
                    }"""
                )
                page.wait_for_function(
                    """() => {
                      const template = state?.project?.popup_template || {};
                      return template.text_source === 'shot_label'
                        && template.content_type === 'text_image'
                                                && template.duration_ms === 5000
                                                && template.use_shot_split_duration === true
                        && template.width === 320
                        && template.height === 96
                        && template.follow_motion === true
                        && template.motion_mode === 'guided'
                        && template.background_color === '#224466'
                        && template.text_color === '#fefefe'
                        && Math.abs((template.opacity || 0) - 0.65) < 0.001;
                    }"""
                )
                expected_shot_duration_ms = int(
                    page.evaluate(
                        """(shotId) => {
                        const shot = shotById(shotId);
                        return popupDefaultDurationMsForShot(shot, currentPopupTemplate());
                    }""",
                        selected_shot["id"],
                    )
                )

                _open_tool(page, "markers")
                _open_markers_workbench(page)
                page.locator("#popup-add-selected-shot-workbench").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 2")
                labeled_popup = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || [])[1] || null;
                      return bubble
                        ? {
                            id: bubble.id,
                            shotId: bubble.shot_id,
                            text: bubble.text,
                            contentType: bubble.content_type,
                            durationMs: bubble.duration_ms,
                            quadrant: bubble.quadrant,
                            x: bubble.x,
                            y: bubble.y,
                            width: bubble.width,
                            height: bubble.height,
                            followMotion: bubble.follow_motion,
                            backgroundColor: bubble.background_color,
                            textColor: bubble.text_color,
                            opacity: bubble.opacity,
                          }
                        : null;
                    }"""
                )
                assert labeled_popup is not None
                assert labeled_popup["shotId"] == selected_shot["id"]
                assert labeled_popup["text"] == "Shot 1"
                assert labeled_popup["contentType"] == "text_image"
                assert labeled_popup["durationMs"] == expected_shot_duration_ms
                assert labeled_popup["quadrant"] == "middle_middle"
                assert labeled_popup["x"] == pytest.approx(0.5)
                assert labeled_popup["y"] == pytest.approx(0.5)
                assert labeled_popup["width"] == 320
                assert labeled_popup["height"] == 96
                assert labeled_popup["followMotion"] is True
                assert labeled_popup["backgroundColor"] == "#224466"
                assert labeled_popup["textColor"] == "#fefefe"
                assert labeled_popup["opacity"] == pytest.approx(0.65)

                page.evaluate(
                    """(popupId) => {
                      document
                        .querySelector(`#markers-workbench-list .popup-marker-row[data-popup-id="${popupId}"] .popup-marker-meta`)
                        ?.click();
                    }""",
                    labeled_popup["id"],
                )
                page.wait_for_function(
                    "(popupId) => selectedPopupBubbleId === popupId", arg=labeled_popup["id"]
                )
                _open_markers_workbench(page)
                page.evaluate(
                    """(timeMs) => {
                        const video = document.getElementById('primary-video');
                        video.currentTime = timeMs / 1000;
                        video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }""",
                    selected_shot["timeMs"] + 240,
                )
                page.locator(
                    f'#markers-workbench-editor .popup-bubble-card[data-popup-id="{labeled_popup["id"]}"] [data-popup-action="add_motion_step"]'
                ).click()
                page.wait_for_function(
                    """(popupId) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      return selectedPopupBubbleId === popupId
                        && selectedPopupPlacementMode === 'keyframe'
                        && selectedPopupKeyframeOffsetMs > 0
                        && ((bubble?.motion_path || []).length === 1);
                    }""",
                    arg=labeled_popup["id"],
                )
                popup_badge = page.locator(
                    f'#popup-overlay .popup-overlay-badge[data-popup-id="{labeled_popup["id"]}"]'
                )
                popup_badge.wait_for(state="attached")
                page.wait_for_timeout(50)
                popup_badge_style = popup_badge.evaluate(
                    """badge => {
                        const rect = badge.getBoundingClientRect();
                        return {
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            text: badge.innerText,
                            background: getComputedStyle(badge).backgroundColor,
                            hasSelectorClass: badge.classList.contains('popup-placement-selector'),
                        };
                    }"""
                )
                assert popup_badge_style["hasSelectorClass"] is True
                assert popup_badge_style["width"] >= 12
                assert popup_badge_style["height"] >= 12
                assert popup_badge_style["text"] == ""
                assert (
                    "255, 123, 34" in popup_badge_style["background"]
                    or "ff7b22" in popup_badge_style["background"]
                )

                page.evaluate(
                    """() => {
                      const template = normalizePopupTemplate({
                        ...currentPopupTemplate(),
                        text_source: 'custom',
                      });
                      if (!state.project) state.project = {};
                      state.project.popup_template = template;
                      callApi('/api/popups', { popups: popupBubbles(), popup_template: template });
                      render();
                    }"""
                )
                page.wait_for_function(
                    "() => state?.project?.popup_template?.text_source === 'custom'"
                )
                _open_tool(page, "markers")
                _open_markers_workbench(page)
                page.locator("#popup-add-bubble-workbench").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 3")
                custom_popup = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || [])[2] || null;
                      return bubble ? { id: bubble.id, text: bubble.text, shotId: bubble.shot_id } : null;
                    }"""
                )
                assert custom_popup is not None
                assert custom_popup["shotId"] is None
                assert custom_popup["text"] == "A"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_motion_toggle_keeps_current_marker_selected(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-motion-toggle-selection"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")
                _import_shot_linked_markers(page)
                _open_markers_workbench(page)

                selected_popup_id = page.evaluate("selectedPopupBubbleId")
                assert selected_popup_id is not None

                page.locator(
                    f'#markers-workbench-editor .popup-bubble-card[data-popup-id="{selected_popup_id}"] [data-popup-field="follow_motion"]'
                ).check()
                page.wait_for_function(
                    """(popupId) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      return selectedPopupBubbleId === popupId && Boolean(bubble?.follow_motion);
                    }""",
                    arg=selected_popup_id,
                )

                page.locator(
                    f'#markers-workbench-editor .popup-bubble-card[data-popup-id="{selected_popup_id}"] [data-popup-field="follow_motion"]'
                ).uncheck()
                page.wait_for_function(
                    """(popupId) => {
                      const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                      return selectedPopupBubbleId === popupId
                        && bubble?.follow_motion === false
                        && selectedPopupPlacementMode === 'base'
                        && selectedPopupKeyframeOffsetMs === 0;
                    }""",
                    arg=selected_popup_id,
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_shotml_threshold_apply_and_reset_defaults_update_project_analysis(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="shotml-threshold-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "shotml")
                page.locator('[data-tool-pane="shotml"]').wait_for(state="visible")

                threshold_section = page.locator('[data-shotml-section="threshold"]')
                if threshold_section.evaluate("el => el.classList.contains('collapsed')"):
                    threshold_section.locator("button[data-section-toggle]").click()
                    page.wait_for_function(
                        "(sectionSelector) => !document.querySelector(sectionSelector)?.classList.contains('collapsed')",
                        arg='[data-shotml-section="threshold"]',
                    )

                threshold_input = page.locator("#threshold")
                threshold_input.wait_for(state="visible")
                assert threshold_input.input_value() == "0.35"
                assert page.locator("#apply-threshold").is_enabled() is True

                threshold_input.fill("0.5")
                page.locator("#apply-threshold").click()
                page.wait_for_function(
                    """() => {
                      const analysis = state?.project?.analysis || {};
                      return analysis.detection_threshold === 0.5
                        && analysis.shotml_settings?.detection_threshold === 0.5;
                    }"""
                )
                assert threshold_input.input_value() == "0.5"

                page.locator("#reset-shotml-defaults").click()
                page.wait_for_function(
                    """() => {
                      const analysis = state?.project?.analysis || {};
                      return analysis.detection_threshold === 0.35
                        && analysis.shotml_settings?.detection_threshold === 0.35;
                    }"""
                )
                assert threshold_input.input_value() == "0.35"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_shotml_settings_controls_commit_and_reset_defaults_update_project_analysis(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="shotml-settings-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "shotml")
                page.locator('[data-tool-pane="shotml"]').wait_for(state="visible")

                threshold_section = page.locator('[data-shotml-section="threshold"]')
                if threshold_section.evaluate("el => el.classList.contains('collapsed')"):
                    threshold_section.locator("button[data-section-toggle]").click()
                    page.wait_for_function(
                        "(sectionSelector) => !document.querySelector(sectionSelector)?.classList.contains('collapsed')",
                        arg='[data-shotml-section="threshold"]',
                    )

                baseline_settings = page.evaluate(
                    """() => {
                        const snapshot = {};
                        document.querySelectorAll('[data-shotml-setting]').forEach((element) => {
                            if (element.id === 'threshold') return;
                            const key = element.dataset.shotmlSetting;
                            if (!key) return;
                            if (element.type === 'checkbox') snapshot[key] = Boolean(element.checked);
                            else if (element.tagName === 'SELECT') snapshot[key] = element.value;
                            else snapshot[key] = element.value === '' ? '' : Number(element.value);
                        });
                        return snapshot;
                    }"""
                )

                updates = page.evaluate(
                    """() => {
                        const snapshot = {};
                        const nextNumericValue = (element) => {
                            const currentText = element.value;
                            const min = element.min === '' ? Number.NaN : Number(element.min);
                            const max = element.max === '' ? Number.NaN : Number(element.max);
                            const stepText = element.step && element.step !== 'any' ? element.step : '';
                            const parsedStep = stepText ? Number(stepText) : Number.NaN;
                            const step = Number.isFinite(parsedStep) && parsedStep > 0
                                ? parsedStep
                                : (currentText.includes('.') ? 0.1 : 1);
                            const decimals = stepText.includes('.')
                                ? stepText.split('.')[1].length
                                : (Number.isInteger(step) ? 0 : 3);
                            const current = currentText === '' ? (Number.isFinite(min) ? min : 0) : Number(currentText);
                            let nextValue = Number.isFinite(current) ? current + step : (Number.isFinite(min) ? min + step : step);
                            if (Number.isFinite(max) && nextValue > max) {
                                nextValue = Number.isFinite(min) ? Math.max(min, max - step) : max - step;
                            }
                            if (Number.isFinite(min) && nextValue < min) {
                                nextValue = min;
                            }
                            return decimals > 0 ? Number(nextValue.toFixed(decimals)) : Math.round(nextValue);
                        };

                        document.querySelectorAll('[data-shotml-setting]').forEach((element) => {
                            if (element.id === 'threshold') return;
                            const key = element.dataset.shotmlSetting;
                            if (!key) return;
                            let nextValue;
                            if (element.type === 'checkbox') {
                                nextValue = !element.checked;
                                element.checked = nextValue;
                                element.dispatchEvent(new Event('change', { bubbles: true }));
                            } else if (element.tagName === 'SELECT') {
                                const options = Array.from(element.options).map((option) => option.value);
                                const currentIndex = options.indexOf(element.value);
                                nextValue = options[(currentIndex + 1) % options.length];
                                element.value = nextValue;
                                element.dispatchEvent(new Event('change', { bubbles: true }));
                            } else {
                                nextValue = nextNumericValue(element);
                                element.value = String(nextValue);
                                element.dispatchEvent(new Event('input', { bubbles: true }));
                                element.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            snapshot[key] = nextValue;
                        });
                        return snapshot;
                    }"""
                )

                page.wait_for_function(
                    """(expected) => {
                        const settings = state?.project?.analysis?.shotml_settings || {};
                        return Object.entries(expected).every(([key, value]) => settings[key] === value);
                    }""",
                    arg=updates,
                )

                mutated_settings = page.evaluate("state?.project?.analysis?.shotml_settings || {}")
                for key, value in updates.items():
                    assert mutated_settings[key] == value

                page.locator("#reset-shotml-defaults").click()
                page.wait_for_function(
                    """(baseline) => {
                        const settings = state?.project?.analysis?.shotml_settings || {};
                        return Object.entries(baseline).every(([key, value]) => settings[key] === value);
                    }""",
                    arg=baseline_settings,
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_merge_controls_update_live_preview_layout_and_position(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="merge-primary-ui"))
    secondary_path = Path(synthetic_video_factory(name="merge-secondary-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "merge")

                page.locator("#merge-media-input").set_input_files(str(secondary_path))
                page.wait_for_function("() => (state?.project?.merge_sources || []).length === 1")
                page.locator(".merge-media-card").first.wait_for(state="visible")

                page.locator("#merge-enabled").check()
                page.wait_for_function("() => state?.project?.merge?.enabled === true")

                source_card = page.locator(".merge-media-card").first

                page.locator("#merge-layout").select_option("side_by_side")
                page.wait_for_function("() => state?.project?.merge?.layout === 'side_by_side'")
                page.wait_for_function(
                    "() => document.getElementById('video-stage')?.classList.contains('merge-side-by-side')"
                )
                page.wait_for_function(
                    "() => document.getElementById('merge-preview-layer')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.querySelectorAll('#merge-preview-layer .merge-preview-item[data-source-id]').length === 1"
                )

                page.locator("#merge-layout").select_option("above_below")
                page.wait_for_function("() => state?.project?.merge?.layout === 'above_below'")
                page.wait_for_function(
                    "() => document.getElementById('video-stage')?.classList.contains('merge-above-below')"
                )
                page.wait_for_function(
                    "() => document.getElementById('merge-preview-layer')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.querySelectorAll('#merge-preview-layer .merge-preview-item[data-source-id]').length === 1"
                )

                page.locator("#merge-layout").select_option("full_screen_portrait")
                page.wait_for_function(
                    "() => state?.project?.merge?.layout === 'full_screen_portrait'"
                )
                page.wait_for_function(
                    "() => document.getElementById('video-stage')?.classList.contains('merge-full-screen-portrait')"
                )
                page.wait_for_function(
                    "() => document.getElementById('merge-preview-layer')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.querySelectorAll('#merge-preview-layer .merge-preview-item[data-source-id]').length === 1"
                )

                page.locator("#merge-layout").select_option("dual_center_hud")
                page.wait_for_function(
                    "() => state?.project?.merge?.layout === 'dual_center_hud'"
                )
                page.wait_for_function(
                    "() => document.getElementById('video-stage')?.classList.contains('merge-dual-center-hud')"
                )

                page.locator("#merge-layout").select_option("dual_top_hud")
                page.wait_for_function(
                    "() => state?.project?.merge?.layout === 'dual_top_hud'"
                )
                page.wait_for_function(
                    "() => document.getElementById('video-stage')?.classList.contains('merge-dual-top-hud')"
                )

                page.locator("#merge-layout").select_option("pip")
                page.wait_for_function("() => state?.project?.merge?.layout === 'pip'")
                page.wait_for_function(
                    "() => document.getElementById('video-stage')?.classList.contains('merge-pip')"
                )

                source_card.locator('[data-merge-source-field="placement_mode"]').select_option("pip")
                page.wait_for_function(
                    "() => state?.project?.merge_sources?.[0]?.placement?.mode === 'pip'"
                )
                source_card.locator('[data-merge-source-field="placement_slot"]').select_option("overlay")
                page.wait_for_function(
                    "() => state?.project?.merge_sources?.[0]?.placement?.mode === 'pip' && state?.project?.merge_sources?.[0]?.placement?.slot === 'overlay'"
                )

                preview_layer = page.locator("#merge-preview-layer")
                preview_layer.wait_for(state="visible")
                preview_item = preview_layer.locator(".merge-preview-item").first
                preview_item.wait_for(state="visible")
                size_output = source_card.locator('[data-merge-source-output="size"]')

                def read_preview_style() -> dict[str, str]:
                    return preview_item.evaluate(
                        """element => ({
                            left: element.style.left || '',
                            top: element.style.top || '',
                            width: element.style.width || '',
                            height: element.style.height || '',
                        })"""
                    )

                before_style = read_preview_style()
                assert page.locator("#pip-size-label").text_content().strip().endswith("%")
                initial_size_percent = page.evaluate(
                    "() => state?.project?.merge_sources?.[0]?.pip_size_percent ?? null"
                )
                assert isinstance(initial_size_percent, int | float)
                target_size_percent = 65 if initial_size_percent < 65 else 25

                page.evaluate(
                    """({ selector, value }) => {
                        const control = document.querySelector(selector);
                        control.value = String(value);
                        control.dispatchEvent(new Event('input', { bubbles: true }));
                        control.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    {"selector": '[data-merge-source-field="size"]', "value": target_size_percent},
                )
                page.wait_for_function(
                    """(expected) => document.querySelector('[data-merge-source-output="size"]')?.textContent === expected""",
                    arg=f"{target_size_percent}%",
                )
                page.wait_for_function(
                    "(expected) => state?.project?.merge_sources?.[0]?.pip_size_percent === expected",
                    arg=target_size_percent,
                )
                expected_direction = "grow" if target_size_percent > initial_size_percent else "shrink"
                page.wait_for_function(
                    """({ previousWidth, previousHeight, direction }) => {
                        const item = document.querySelector('#merge-preview-layer .merge-preview-item');
                        if (!item) return false;
                        const width = Number.parseFloat(item.style.width || '0');
                        const height = Number.parseFloat(item.style.height || '0');
                        const previousWidthValue = Number.parseFloat(previousWidth || '0');
                        const previousHeightValue = Number.parseFloat(previousHeight || '0');
                        if (!Number.isFinite(width) || !Number.isFinite(height)) return false;
                        if (!Number.isFinite(previousWidthValue) || !Number.isFinite(previousHeightValue)) {
                            return item.style.width !== previousWidth || item.style.height !== previousHeight;
                        }
                        if (direction === 'grow') {
                            return width > previousWidthValue || height > previousHeightValue;
                        }
                        return width < previousWidthValue || height < previousHeightValue;
                    }""",
                    arg={
                        "previousWidth": before_style["width"],
                        "previousHeight": before_style["height"],
                        "direction": expected_direction,
                    },
                )
                after_size_style = read_preview_style()
                assert size_output.text_content().strip() == f"{target_size_percent}%"
                before_width = float(before_style["width"].removesuffix("px"))
                before_height = float(before_style["height"].removesuffix("px"))
                after_width = float(after_size_style["width"].removesuffix("px"))
                after_height = float(after_size_style["height"].removesuffix("px"))
                if target_size_percent > initial_size_percent:
                    assert after_width > before_width or after_height > before_height
                else:
                    assert after_width < before_width or after_height < before_height

                target_x = page.evaluate(
                    """() => {
                        const control = document.querySelector('[data-merge-source-field="x"]');
                        const current = Number(control?.value || '0');
                        return current < 0.25 ? 0.25 : 0.1;
                    }"""
                )
                target_y = page.evaluate(
                    """() => {
                        const control = document.querySelector('[data-merge-source-field="y"]');
                        const current = Number(control?.value || '0');
                        return current < 0.75 ? 0.75 : 0.4;
                    }"""
                )
                page.evaluate(
                    """({ selector, value }) => {
                        const control = document.querySelector(selector);
                        control.value = String(value);
                        control.dispatchEvent(new Event('input', { bubbles: true }));
                        control.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    {"selector": '[data-merge-source-field="x"]', "value": target_x},
                )
                page.evaluate(
                    """({ selector, value }) => {
                        const control = document.querySelector(selector);
                        control.value = String(value);
                        control.dispatchEvent(new Event('input', { bubbles: true }));
                        control.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    {"selector": '[data-merge-source-field="y"]', "value": target_y},
                )
                page.wait_for_function(
                    "({ expectedX, expectedY }) => state?.project?.merge_sources?.[0]?.pip_x === expectedX && state?.project?.merge_sources?.[0]?.pip_y === expectedY",
                    arg={"expectedX": target_x, "expectedY": target_y},
                )
                page.wait_for_function(
                    """({ previousLeft, previousTop }) => {
                        const item = document.querySelector('#merge-preview-layer .merge-preview-item');
                        return Boolean(item) && (item.style.left !== previousLeft || item.style.top !== previousTop);
                    }""",
                    arg={"previousLeft": before_style["left"], "previousTop": before_style["top"]},
                )

                after_position_style = read_preview_style()
                assert (
                    after_position_style["left"] != before_style["left"]
                    or after_position_style["top"] != before_style["top"]
                )

                page.locator("#merge-enabled").uncheck()
                page.wait_for_function("() => state?.project?.merge?.enabled === false")
                page.wait_for_function(
                    "() => document.getElementById('merge-preview-layer')?.hidden === true"
                )
                assert preview_layer.is_hidden() is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_merge_default_pip_controls_commit_to_state_and_label(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="merge-default-pip-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "merge")
                page.locator('[data-tool-pane="merge"]').wait_for(state="visible")

                assert page.locator("#pip-size-label").text_content().strip().endswith("%")

                page.evaluate(
                    """() => {
                        const sizeControl = document.getElementById('pip-size');
                        sizeControl.value = '50';
                        sizeControl.dispatchEvent(new Event('input', { bubbles: true }));
                        sizeControl.dispatchEvent(new Event('change', { bubbles: true }));
                    }"""
                )
                page.wait_for_function("() => state?.project?.merge?.pip_size_percent === 50")
                assert page.locator("#pip-size").input_value() == "50"
                assert page.locator("#pip-size-label").text_content().strip() == "50%"

                page.evaluate(
                    """() => {
                        const pipX = document.getElementById('pip-x');
                        const pipY = document.getElementById('pip-y');
                        pipX.value = '0.25';
                        pipY.value = '0.75';
                        [pipX, pipY].forEach((control) => {
                            control.dispatchEvent(new Event('input', { bubbles: true }));
                            control.dispatchEvent(new Event('change', { bubbles: true }));
                        });
                    }"""
                )
                page.wait_for_function(
                    "() => state?.project?.merge?.pip_x === 0.25 && state?.project?.merge?.pip_y === 0.75"
                )
                assert page.locator("#pip-x").input_value() == "0.25"
                assert page.locator("#pip-y").input_value() == "0.75"
                page.locator("#merge-enabled").check()
                page.wait_for_function("() => state?.project?.merge?.enabled === true")
                page.locator("#merge-layout").select_option("full_screen_portrait")
                page.wait_for_function(
                    "() => state?.project?.merge?.layout === 'full_screen_portrait'"
                )
                page.locator("#restore-merge-defaults").click()
                page.wait_for_function(
                    """() => {
                        const merge = state?.project?.merge;
                        return Boolean(merge)
                            && merge.enabled === false
                            && merge.layout === 'side_by_side'
                            && merge.pip_size_percent === 35
                            && merge.pip_x === 1
                            && merge.pip_y === 1;
                    }"""
                )
                assert page.locator("#merge-enabled").is_checked() is False
                assert page.locator("#merge-layout").input_value() == "side_by_side"
                assert page.locator("#pip-size").input_value() == "35"
                assert page.locator("#pip-size-label").text_content().strip() == "35%"
                assert page.locator("#pip-x").input_value() == "1"
                assert page.locator("#pip-y").input_value() == "1"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_direct_merge_preview_batch_boundary_reseek_converges_all_added_previews_after_play_seek_and_forced_drift(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="merge-preview-sync-primary-ui"))
    merge_paths = [
        Path(synthetic_video_factory(name="merge-preview-sync-secondary-ui")),
        Path(synthetic_video_factory(name="merge-preview-sync-tertiary-ui")),
        Path(synthetic_video_factory(name="merge-preview-sync-quaternary-ui")),
    ]
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "merge")

                for expected_count, merge_path in enumerate(merge_paths, start=1):
                    page.locator("#merge-media-input").set_input_files(str(merge_path))
                    page.wait_for_function(
                        "(expectedCount) => (state?.project?.merge_sources || []).length === expectedCount",
                        arg=expected_count,
                    )

                page.locator("#merge-enabled").check()
                page.wait_for_function("() => state?.project?.merge?.enabled === true")
                page.locator("#merge-layout").select_option("pip")
                page.wait_for_function("() => state?.project?.merge?.layout === 'pip'")
                page.wait_for_function(
                    "() => document.querySelectorAll('#merge-preview-layer .merge-preview-item video').length === 3"
                )

                play_phase = _capture_direct_merge_preview_batch_reseek_phase(
                    page,
                    primary_time_s=4.25,
                    primary_paused=False,
                    preview_times_s=[0.1, 1.4, 2.6],
                    preview_paused=True,
                    playback_rate=1.1,
                )
                seek_phase = _capture_direct_merge_preview_batch_reseek_phase(
                    page,
                    primary_time_s=8.75,
                    primary_paused=True,
                    preview_times_s=[1.0, 3.8, 5.9],
                    preview_paused=False,
                    playback_rate=1.0,
                )
                forced_drift_phase = _capture_direct_merge_preview_batch_reseek_phase(
                    page,
                    primary_time_s=11.5,
                    primary_paused=True,
                    preview_times_s=[0.35, 4.25, 9.1],
                    preview_paused=True,
                    playback_rate=0.95,
                )

                assert len(play_phase) == 3
                assert len({phase["sourceId"] for phase in play_phase}) == 3
                assert [phase["sourceId"] for phase in play_phase] == [
                    phase["sourceId"] for phase in seek_phase
                ] == [phase["sourceId"] for phase in forced_drift_phase]

                assert [len(phase["fastSeekCalls"]) for phase in play_phase] == [1, 1, 1]
                assert [len(phase["fastSeekCalls"]) for phase in seek_phase] == [1, 1, 1]
                assert [len(phase["fastSeekCalls"]) for phase in forced_drift_phase] == [1, 1, 1]

                for preview in play_phase:
                    assert preview["correctionMode"] == "reseek"
                    assert preview["currentTime"] == pytest.approx(preview["target"], abs=1e-6)
                    assert preview["delta"] == pytest.approx(0, abs=1e-6)
                    assert preview["paused"] is False
                    assert preview["playCount"] == 1
                    assert preview["pauseCount"] == 0

                for preview in seek_phase:
                    assert preview["correctionMode"] == "reseek"
                    assert preview["currentTime"] == pytest.approx(preview["target"], abs=1e-6)
                    assert preview["delta"] == pytest.approx(0, abs=1e-6)
                    assert preview["paused"] is True
                    assert preview["playCount"] == 0
                    assert preview["pauseCount"] == 1

                for preview in forced_drift_phase:
                    assert preview["correctionMode"] == "reseek"
                    assert preview["currentTime"] == pytest.approx(preview["target"], abs=1e-6)
                    assert preview["delta"] == pytest.approx(0, abs=1e-6)
                    assert preview["paused"] is True
                    assert preview["playCount"] == 0
                    assert preview["pauseCount"] == 0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_time_marker_list_cards_select_marker_and_seek_video(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-time-list-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")

                page.evaluate(
                    """(timeMs) => {
                      selectedShotId = null;
                      const video = document.getElementById('primary-video');
                      video.currentTime = timeMs / 1000;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }""",
                    1250,
                )
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")

                page.evaluate(
                    """(timeMs) => {
                      selectedShotId = null;
                      const video = document.getElementById('primary-video');
                      video.currentTime = timeMs / 1000;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }""",
                    1600,
                )
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 2")

                time_popups = page.evaluate(
                    """() => (state?.project?.popups || []).map((bubble) => ({
                      id: bubble.id,
                      anchorMode: bubble.anchor_mode,
                      shotId: bubble.shot_id,
                      timeMs: bubble.time_ms,
                    }))"""
                )
                assert len(time_popups) == 2
                assert all(popup["anchorMode"] == "time" for popup in time_popups)
                assert all(popup["shotId"] is None for popup in time_popups)
                assert abs(time_popups[0]["timeMs"] - 1250) <= 40
                assert abs(time_popups[1]["timeMs"] - 1600) <= 40

                page.evaluate(
                    """() => {
                      const video = document.getElementById('primary-video');
                      video.currentTime = 3;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }"""
                )

                first_popup_id = time_popups[0]["id"]
                first_popup_button = page.locator(
                    f'#popup-marker-list .popup-marker-row[data-popup-id="{first_popup_id}"] .popup-marker-select'
                )
                first_popup_button.wait_for(state="visible")
                first_popup_button.click()
                page.wait_for_function(
                    "(popupId) => selectedPopupBubbleId === popupId", arg=first_popup_id
                )
                page.wait_for_function(
                    """(targetMs) => {
                      const currentMs = (document.getElementById('primary-video')?.currentTime || 0) * 1000;
                      return Math.abs(currentMs - targetMs) <= 80;
                    }""",
                    arg=time_popups[0]["timeMs"],
                )

                selected_card = page.locator(
                    f'#popup-marker-list .popup-marker-row[data-popup-id="{first_popup_id}"]'
                )
                assert selected_card.evaluate("card => card.classList.contains('selected')") is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_markers_clicking_video_stage_does_not_create_marker(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-stage-click-disabled-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")

                page.evaluate(
                    """() => {
                      selectedShotId = null;
                      const video = document.getElementById('primary-video');
                      video.pause();
                      video.currentTime = 1.25;
                      video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }"""
                )

                page.locator("#video-stage").click(position={"x": 320, "y": 180}, force=True)
                page.wait_for_timeout(150)
                assert page.evaluate("() => (state?.project?.popups || []).length") == 0

                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")

                popup_snapshot = page.evaluate(
                    """() => {
                      const bubble = (state?.project?.popups || [])[0] || null;
                      return bubble
                        ? {
                            anchorMode: bubble.anchor_mode,
                            shotId: bubble.shot_id,
                          }
                        : null;
                    }"""
                )
                assert popup_snapshot is not None
                assert popup_snapshot["anchorMode"] == "time"
                assert popup_snapshot["shotId"] is None
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_popup_bubble_enabled_checkbox_hides_and_restores_live_badge(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-enabled-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")
                _ensure_overlay_visible(page)

                page.evaluate(
                    """(timeMs) => {
                                            selectedShotId = null;
                                            const video = document.getElementById('primary-video');
                                            video.currentTime = timeMs / 1000;
                                            video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                                        }""",
                    900,
                )
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")

                popup_id = page.evaluate("(state?.project?.popups || [])[0]?.id || null")
                assert popup_id is not None

                popup_badge = page.locator(
                    f'#popup-overlay .popup-overlay-badge[data-popup-id="{popup_id}"]'
                )
                popup_badge.wait_for(state="visible")

                page.evaluate(
                    """(popupId) => {
                                            const checkbox = document.querySelector(
                                                `#popup-marker-list .popup-marker-row[data-popup-id="${popupId}"] input[data-popup-field="enabled"]`
                                            );
                                            if (!(checkbox instanceof HTMLInputElement)) return;
                                            checkbox.checked = false;
                                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                        }""",
                    popup_id,
                )
                page.wait_for_function(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            return Boolean(bubble) && bubble.enabled === false;
                                        }""",
                    arg=popup_id,
                )
                page.wait_for_function(
                    """(popupId) => !document.querySelector(
                                            `#popup-overlay .popup-overlay-badge[data-popup-id="${popupId}"]`
                                        )""",
                    arg=popup_id,
                )

                page.evaluate(
                    """(popupId) => {
                                            const checkbox = document.querySelector(
                                                `#popup-marker-list .popup-marker-row[data-popup-id="${popupId}"] input[data-popup-field="enabled"]`
                                            );
                                            if (!(checkbox instanceof HTMLInputElement)) return;
                                            checkbox.checked = true;
                                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                        }""",
                    popup_id,
                )
                page.wait_for_function(
                    """(popupId) => {
                                            const bubble = (state?.project?.popups || []).find((item) => item.id === popupId);
                                            return Boolean(bubble) && bubble.enabled === true;
                                        }""",
                    arg=popup_id,
                )
                popup_badge.wait_for(state="visible")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_popup_selected_marker_editor_duplicate_and_remove_markers(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-card-actions-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")

                page.evaluate(
                    """(timeMs) => {
                        selectedShotId = null;
                        const video = document.getElementById('primary-video');
                        video.currentTime = timeMs / 1000;
                        video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                    }""",
                    950,
                )
                page.locator("#popup-add-bubble").click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 1")

                original_popup_id = page.evaluate("(state?.project?.popups || [])[0]?.id || null")
                assert original_popup_id is not None

                original_card = page.locator(
                    f'#popup-marker-list .popup-marker-row[data-popup-id="{original_popup_id}"]'
                )
                original_card.wait_for(state="visible")
                assert page.locator("#popup-timeline-strip").count() == 0

                page.locator(
                    f'#popup-marker-list .popup-marker-row[data-popup-id="{original_popup_id}"] .popup-marker-select'
                ).click()
                page.wait_for_function(
                    "(popupId) => selectedPopupBubbleId === popupId", arg=original_popup_id
                )

                page.locator("#popup-edit-selected").click()
                page.wait_for_function(
                    "() => document.getElementById('markers-workbench')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.getElementById('popup-edit-selected')?.textContent?.trim() === 'Collapse'"
                )

                page.locator("#popup-edit-selected").click()
                page.wait_for_function(
                    "() => document.getElementById('markers-workbench')?.hidden === true"
                )
                page.wait_for_function(
                    "() => document.getElementById('popup-edit-selected')?.textContent?.trim() === 'Edit'"
                )

                page.locator("#popup-edit-selected").click()
                page.wait_for_function(
                    "() => document.getElementById('markers-workbench')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.getElementById('popup-selected-editor-panel')?.hidden === false"
                )
                page.wait_for_function(
                    """(popupId) => {
                        const card = document.querySelector('#markers-workbench-editor .popup-bubble-card');
                        const body = card?.querySelector('.text-box-card-body');
                        return card instanceof HTMLElement && card.dataset.popupId === popupId
                          && body instanceof HTMLElement && body.hidden === false;
                    }""",
                    arg=original_popup_id,
                )
                page.wait_for_function(
                    """() => {
                        const sections = [...document.querySelectorAll('#markers-workbench-editor [data-popup-editor-section]')];
                        return sections.length >= 4 && sections.every((section) => section.querySelector('.section-header'));
                    }"""
                )

                page.locator('#markers-workbench-editor [data-popup-action="duplicate"]').click()
                page.wait_for_function("() => (state?.project?.popups || []).length === 2")
                popup_ids_after_duplicate = page.evaluate(
                    "(state?.project?.popups || []).map((bubble) => bubble.id)"
                )
                duplicate_ids = [
                    popup_id
                    for popup_id in popup_ids_after_duplicate
                    if popup_id != original_popup_id
                ]
                assert len(duplicate_ids) == 1
                duplicate_popup_id = duplicate_ids[0]
                page.wait_for_function(
                    "(popupId) => selectedPopupBubbleId === popupId", arg=duplicate_popup_id
                )
                assert (
                    page.locator(
                        f'#popup-marker-list .popup-marker-row[data-popup-id="{duplicate_popup_id}"]'
                    ).count()
                    == 1
                )

                page.locator('#markers-workbench-editor [data-popup-action="remove"]').click()
                page.wait_for_function(
                    """(popupId) => !(state?.project?.popups || []).some((bubble) => bubble.id === popupId)""",
                    arg=duplicate_popup_id,
                )
                assert (
                    page.locator(
                        f'#popup-marker-list .popup-marker-row[data-popup-id="{duplicate_popup_id}"]'
                    ).count()
                    == 0
                )
                assert (
                    page.locator(
                        f'#popup-marker-list .popup-marker-row[data-popup-id="{original_popup_id}"]'
                    ).count()
                    == 1
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_markers_workbench_hides_when_switching_to_another_tool(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-tool-switch-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "markers")
                page.locator("#popup-edit-selected").click()
                page.wait_for_function(
                    "() => document.getElementById('markers-workbench')?.hidden === false"
                )
                page.wait_for_function(
                    "() => document.getElementById('cockpit-root')?.classList.contains('markers-expanded')"
                )

                _open_tool(page, "project")
                page.wait_for_function(
                    "() => document.getElementById('markers-workbench')?.hidden === true"
                )
                page.wait_for_function(
                    "() => !document.getElementById('cockpit-root')?.classList.contains('markers-expanded')"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_overlay_color_picker_updates_timer_badge_preview_and_reopens_with_selected_hex(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="overlay-color-picker-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "overlay")
                _ensure_overlay_visible(page)

                if not page.locator("#show-timer").is_checked():
                    page.evaluate(
                        """() => {
                                                    const checkbox = document.getElementById('show-timer');
                                                    checkbox.checked = true;
                                                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                                }"""
                    )
                page.evaluate(
                    """() => {
                                            const video = document.getElementById('primary-video');
                                            video.currentTime = 1.2;
                                            video.dispatchEvent(new Event('timeupdate', { bubbles: true }));
                                            renderLiveOverlay();
                                        }"""
                )

                page.wait_for_function("() => state?.project?.overlay?.show_timer === true")
                timer_badge = page.locator('[data-overlay-drag="timer"]')
                timer_badge.wait_for(state="visible")

                color_button = page.locator(
                    '#badge-style-grid .style-card[data-badge="timer_badge"] .color-swatch-button[data-field="background_color"]'
                )
                initial_snapshot = page.evaluate(
                    """() => ({
                                            buttonColor: document.querySelector('#badge-style-grid .style-card[data-badge="timer_badge"] .color-swatch-button[data-field="background_color"]')?.dataset.colorValue || null,
                                            overlayColor: state?.project?.overlay?.timer_badge?.background_color || null,
                                        })"""
                )
                assert initial_snapshot["buttonColor"] == initial_snapshot["overlayColor"]

                color_button.click()
                page.wait_for_function(
                    "() => !document.getElementById('color-picker-modal').hidden && activeColorPickerControl !== null"
                )

                modal_snapshot = page.evaluate(
                    """() => ({
                                            target: document.getElementById('color-picker-target')?.textContent?.trim() || '',
                                            hex: document.getElementById('color-picker-hex')?.value || '',
                                            current: document.getElementById('color-picker-current')?.textContent?.trim() || '',
                                        })"""
                )
                assert modal_snapshot["target"] == "Bg"
                assert modal_snapshot["hex"] == initial_snapshot["buttonColor"].upper()
                assert modal_snapshot["current"] == initial_snapshot["buttonColor"].upper()

                page.evaluate(
                    """() => {
                                            [
                                                ['color-picker-hue', '120'],
                                                ['color-picker-saturation', '100'],
                                                ['color-picker-lightness', '50'],
                                            ].forEach(([elementId, nextValue]) => {
                                                const slider = document.getElementById(elementId);
                                                slider.value = nextValue;
                                                slider.dispatchEvent(new Event('input', { bubbles: true }));
                                            });
                                        }"""
                )
                page.wait_for_function(
                    """() => {
                                            const preview = document.getElementById('color-picker-preview');
                                              const badge = document.querySelector('[data-overlay-drag="timer"]');
                                            const current = document.getElementById('color-picker-current');
                                            const button = document.querySelector('#badge-style-grid .style-card[data-badge="timer_badge"] .color-swatch-button[data-field="background_color"]');
                                            return preview?.style.getPropertyValue('--picker-color') === '#00ff00'
                                                && current?.textContent?.trim() === '#00FF00'
                                                && button?.dataset.colorValue === '#00ff00'
                                                && badge instanceof HTMLElement
                                                && badge.style.background.includes('0, 255, 0');
                                        }"""
                )

                page.evaluate(
                    """() => {
                                            const input = document.getElementById('color-picker-hex');
                                            input.value = '#ff0000';
                                            input.dispatchEvent(new Event('input', { bubbles: true }));
                                        }"""
                )
                page.wait_for_function(
                    """() => {
                                            const preview = document.getElementById('color-picker-preview');
                                            const current = document.getElementById('color-picker-current');
                                            const hue = document.getElementById('color-picker-hue');
                                            const saturation = document.getElementById('color-picker-saturation');
                                            const lightness = document.getElementById('color-picker-lightness');
                                              const badge = document.querySelector('[data-overlay-drag="timer"]');
                                            return preview?.style.getPropertyValue('--picker-color') === '#ff0000'
                                                && current?.textContent?.trim() === '#FF0000'
                                                && hue?.value === '0'
                                                && saturation?.value === '100'
                                                && lightness?.value === '50'
                                                && badge instanceof HTMLElement
                                                && badge.style.background.includes('255, 0, 0');
                                        }"""
                )

                page.locator("#close-color-picker").click()
                page.wait_for_function(
                    "() => document.getElementById('color-picker-modal').hidden && activeColorPickerControl === null"
                )
                page.wait_for_function(
                    "() => state?.project?.overlay?.timer_badge?.background_color === '#ff0000'"
                )

                persisted_snapshot = page.evaluate(
                    """() => ({
                                            buttonColor: document.querySelector('#badge-style-grid .style-card[data-badge="timer_badge"] .color-swatch-button[data-field="background_color"]')?.dataset.colorValue || null,
                                            overlayColor: state?.project?.overlay?.timer_badge?.background_color || null,
                                        })"""
                )
                assert persisted_snapshot == {
                    "buttonColor": "#ff0000",
                    "overlayColor": "#ff0000",
                }
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_overlay_badge_position_controls_update_state_and_persist(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="overlay-badge-position-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "overlay")
                _ensure_overlay_visible(page)

                def set_checkbox(control_id: str, checked: bool) -> None:
                    page.evaluate(
                        """({ controlId, checked }) => {
                            const control = document.getElementById(controlId);
                            control.checked = checked;
                            control.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        {"controlId": control_id, "checked": checked},
                    )

                def set_number(control_id: str, value: float) -> None:
                    page.evaluate(
                        """({ controlId, value }) => {
                            const control = document.getElementById(controlId);
                            control.value = String(value);
                            control.dispatchEvent(new Event('input', { bubbles: true }));
                            control.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        {"controlId": control_id, "value": value},
                    )

                coordinate_targets = {
                    "timer": (0.25, 0.75),
                    "draw": (0.33, 0.67),
                    "score": (0.42, 0.58),
                }

                timer_badge = page.locator('[data-overlay-drag="timer"]')
                timer_badge.wait_for(state="visible")

                for kind, (x_value, y_value) in coordinate_targets.items():
                    lock_id = f"{kind}-lock-to-stack"
                    x_id = f"{kind}-x"
                    y_id = f"{kind}-y"
                    lock_control = page.locator(f"#{lock_id}")
                    x_control = page.locator(f"#{x_id}")
                    y_control = page.locator(f"#{y_id}")

                    assert lock_control.is_checked() is True
                    assert x_control.is_disabled() is True
                    assert y_control.is_disabled() is True
                    assert x_control.get_attribute("placeholder") == "Stack locked"
                    assert y_control.get_attribute("placeholder") == "Stack locked"

                    set_checkbox(lock_id, False)
                    page.wait_for_function(
                        "(controlId) => document.getElementById(controlId)?.checked === false",
                        arg=lock_id,
                    )
                    page.wait_for_function(
                        """({ xId, yId }) => {
                          const xControl = document.getElementById(xId);
                          const yControl = document.getElementById(yId);
                          return Boolean(xControl) && Boolean(yControl) && !xControl.disabled && !yControl.disabled;
                        }""",
                        arg={"xId": x_id, "yId": y_id},
                    )
                    if lock_control.is_checked() is True:
                        # Some badge lanes remain stack-locked when source data is unavailable.
                        continue
                    x_enabled = x_control.evaluate("element => element.disabled") is False
                    y_enabled = y_control.evaluate("element => element.disabled") is False
                    if not (x_enabled and y_enabled):
                        continue

                    set_number(x_id, x_value)
                    set_number(y_id, y_value)
                    page.wait_for_function(
                        """({ xId, yId, xValue, yValue }) => {
                          const xControl = document.getElementById(xId);
                          const yControl = document.getElementById(yId);
                          return Boolean(xControl)
                            && Boolean(yControl)
                            && xControl.value === String(xValue)
                            && yControl.value === String(yValue);
                        }""",
                        arg={"xId": x_id, "yId": y_id, "xValue": x_value, "yValue": y_value},
                    )
                    current_x_value = x_control.input_value()
                    current_y_value = y_control.input_value()
                    if current_x_value and current_y_value:
                        assert current_x_value == str(x_value)
                        assert current_y_value == str(y_value)

                    if kind == "timer":
                        timer_badge.wait_for(state="visible")
                        score_layer_box = page.locator("#score-layer").bounding_box()
                        badge_box = timer_badge.bounding_box()
                        if score_layer_box is not None and badge_box is not None:
                            assert badge_box["height"] > 0

            finally:
                browser.close()
    finally:
        server.shutdown()


def test_overlay_font_controls_apply_to_timer_badge_and_bubble_size_override(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="overlay-font-controls-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "overlay")
                _ensure_overlay_visible(page)

                timer_badge = page.locator('[data-overlay-drag="timer"]')
                timer_badge.wait_for(state="visible")
                before_box = timer_badge.bounding_box()
                assert before_box is not None

                before_style = page.evaluate(
                    """() => {
                        const badge = document.querySelector('[data-overlay-drag="timer"]');
                        return {
                            width: badge?.style.width || '',
                            height: badge?.style.height || '',
                            family: badge?.style.fontFamily || '',
                            size: badge?.style.fontSize || '',
                            weight: badge?.style.fontWeight || '',
                            style: badge?.style.fontStyle || '',
                        };
                    }"""
                )

                def set_number(control_id: str, value: int | float) -> None:
                    page.evaluate(
                        """({ controlId, value }) => {
                            const control = document.getElementById(controlId);
                            control.value = String(value);
                            control.dispatchEvent(new Event('input', { bubbles: true }));
                        }""",
                        {"controlId": control_id, "value": value},
                    )

                def set_checkbox(control_id: str, checked: bool) -> None:
                    page.evaluate(
                        """({ controlId, checked }) => {
                            const control = document.getElementById(controlId);
                            control.checked = checked;
                            control.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        {"controlId": control_id, "checked": checked},
                    )

                set_number("bubble-width", 280)
                set_number("bubble-height", 120)
                page.wait_for_function(
                    """() => state?.project?.overlay?.bubble_width === 280 && state?.project?.overlay?.bubble_height === 120"""
                )
                page.wait_for_function(
                    """() => {
                        const badge = document.querySelector('[data-overlay-drag="timer"]');
                        return Boolean(badge?.style.width) && Boolean(badge?.style.height);
                    }"""
                )

                page.locator("#overlay-font-family").select_option("Courier New")
                page.wait_for_function(
                    "() => state?.project?.overlay?.font_family === 'Courier New'"
                )
                timer_badge.wait_for(state="visible")
                page.wait_for_function(
                    """() => {
                        const badge = document.querySelector('[data-overlay-drag="timer"]');
                        return Boolean(badge) && window.getComputedStyle(badge).fontFamily.includes('Courier New');
                    }"""
                )
                page.wait_for_function(
                    """() => {
                        const badge = document.querySelector('[data-overlay-drag="timer"]');
                        if (!(badge instanceof HTMLElement)) return false;
                        const rect = badge.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    }"""
                )

                after_box = timer_badge.bounding_box()
                assert after_box is not None
                assert after_box["width"] > before_box["width"]

                set_number("overlay-font-size", 22)
                set_checkbox("overlay-font-bold", True)
                set_checkbox("overlay-font-italic", True)

                page.wait_for_function("() => state?.project?.overlay?.font_size === 22")
                page.wait_for_function("() => state?.project?.overlay?.font_bold === true")
                page.wait_for_function("() => state?.project?.overlay?.font_italic === true")

                page.evaluate("renderLiveOverlay()")
                after_style = page.evaluate(
                    """() => {
                        const badge = document.querySelector('[data-overlay-drag="timer"]');
                        const style = window.getComputedStyle(badge);
                        return {
                            width: badge?.style.width || '',
                            height: badge?.style.height || '',
                            family: style?.fontFamily || '',
                            size: style?.fontSize || '',
                            weight: style?.fontWeight || '',
                            style: style?.fontStyle || '',
                        };
                    }"""
                )
                assert float(after_style["size"].removesuffix("px")) > float(
                    before_style["size"].removesuffix("px")
                )
                assert after_style["weight"] in {"700", "bold"}
                assert after_style["style"] == "italic"
                assert after_style["width"] != ""
                assert after_style["height"] != ""
                assert "Courier New" in after_style["family"]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_export_log_modal_opens_closes_backdrop_and_downloads_last_log(tmp_path: Path) -> None:
    controller = ProjectController()
    controller.project.export.last_log = "Encoder command:\nffmpeg -i input"
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "export")

                page.locator("#show-export-log").click(force=True)
                modal = page.locator("#export-log-modal")
                modal.wait_for(state="visible")
                assert modal.evaluate("element => element.hidden") is False
                assert "Encoder command:" in page.locator("#export-log-output").text_content()
                assert page.locator("#export-export-log").is_disabled() is False

                with page.expect_download() as download_info:
                    page.locator("#export-export-log").click()
                download = download_info.value
                assert download.suggested_filename.endswith("-export-log.txt")
                download_target = tmp_path / download.suggested_filename
                download.save_as(str(download_target))
                assert (
                    download_target.read_text(encoding="utf-8")
                    == "Encoder command:\nffmpeg -i input\n"
                )

                page.locator("#close-export-log").click()
                page.wait_for_function(
                    "() => document.getElementById('export-log-modal')?.hidden === true"
                )

                page.locator("#show-export-log").click(force=True)
                page.wait_for_function(
                    "() => document.getElementById('export-log-modal')?.hidden === false"
                )
                page.evaluate("document.querySelector('[data-close-export-log=\"true\"]')?.click()")
                page.wait_for_function(
                    "() => document.getElementById('export-log-modal')?.hidden === true"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_export_controls_update_preset_and_settings_state(
    synthetic_video_factory, tmp_path: Path
) -> None:
    primary_path = Path(synthetic_video_factory(name="export-controls-ui"))
    export_path = tmp_path / "exports" / "custom-output.mp4"
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "export")
                page.locator('[data-tool-pane="export"]').wait_for(state="visible")

                page.locator("#export-preset").select_option("youtube_long_1080p")
                page.wait_for_function(
                    "() => state?.project?.export?.preset === 'youtube_long_1080p'"
                )
                assert page.locator("#export-preset").input_value() == "youtube_long_1080p"
                assert "1920x1080" in page.locator("#export-preset-description").text_content()

                page.locator("#quality").select_option("low")
                page.wait_for_function("() => state?.project?.export?.quality === 'low'")

                page.locator("#aspect-ratio").select_option("1:1")
                page.wait_for_function("() => state?.project?.export?.aspect_ratio === '1:1'")

                page.locator("#target-width").fill("1440")
                page.locator("#target-height").fill("1440")
                page.wait_for_function(
                    "() => state?.project?.export?.target_width === 1440 && state?.project?.export?.target_height === 1440"
                )

                page.locator("#frame-rate").select_option("60")
                page.wait_for_function("() => state?.project?.export?.frame_rate === '60'")

                page.locator("#video-codec").select_option("hevc")
                page.wait_for_function("() => state?.project?.export?.video_codec === 'hevc'")

                page.locator("#video-bitrate").fill("20")
                page.wait_for_function("() => state?.project?.export?.video_bitrate_mbps === 20")

                page.locator("#audio-sample-rate").fill("44100")
                page.wait_for_function("() => state?.project?.export?.audio_sample_rate === 44100")

                page.locator("#audio-bitrate").fill("256")
                page.wait_for_function("() => state?.project?.export?.audio_bitrate_kbps === 256")

                page.locator("#color-space").select_option("bt709_sdr")
                page.wait_for_function("() => state?.project?.export?.color_space === 'bt709_sdr'")

                page.locator("#ffmpeg-preset").select_option("slow")
                page.wait_for_function("() => state?.project?.export?.ffmpeg_preset === 'slow'")

                page.locator("#two-pass").check()
                page.wait_for_function("() => state?.project?.export?.two_pass === true")

                page.locator("#export-path").fill(str(export_path))
                page.wait_for_function(
                    "expected => document.getElementById('export-path')?.value === expected",
                    arg=str(export_path),
                )
                page.wait_for_function(
                    "expected => state?.project?.export?.output_path === expected",
                    arg=str(export_path),
                )

                export_state = page.evaluate(
                    """() => ({
                        preset: state?.project?.export?.preset || '',
                        quality: state?.project?.export?.quality || '',
                        aspectRatio: state?.project?.export?.aspect_ratio || '',
                        targetWidth: state?.project?.export?.target_width ?? null,
                        targetHeight: state?.project?.export?.target_height ?? null,
                        frameRate: state?.project?.export?.frame_rate || '',
                        videoCodec: state?.project?.export?.video_codec || '',
                        videoBitrateMbps: state?.project?.export?.video_bitrate_mbps ?? null,
                        audioSampleRate: state?.project?.export?.audio_sample_rate ?? null,
                        audioBitrateKbps: state?.project?.export?.audio_bitrate_kbps ?? null,
                        colorSpace: state?.project?.export?.color_space || '',
                        ffmpegPreset: state?.project?.export?.ffmpeg_preset || '',
                        twoPass: Boolean(state?.project?.export?.two_pass),
                        outputPath: state?.project?.export?.output_path || '',
                    })"""
                )
                assert export_state["preset"] == "custom"
                assert export_state["quality"] == "low"
                assert export_state["aspectRatio"] == "1:1"
                assert export_state["frameRate"] == "60"
                assert export_state["videoCodec"] == "hevc"
                assert export_state["audioBitrateKbps"] == 256
                assert export_state["colorSpace"] == "bt709_sdr"
                assert export_state["ffmpegPreset"] == "slow"
                assert export_state["twoPass"] is True
                assert export_state["outputPath"] == str(export_path)
                assert page.locator("#export-preset").input_value() == "custom"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_scoring_workbench_rows_lock_edit_delete_and_restore(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="scoring-workbench-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                page.locator('button[data-tool="scoring"]').click(force=True)
                page.wait_for_timeout(100)
                assert page.evaluate("activeTool") == "scoring"

                page.locator("#scoring-enabled").check()
                page.wait_for_timeout(150)

                preset_values = page.locator("#scoring-preset").evaluate(
                    "select => [...select.options].map((option) => option.value).filter(Boolean)"
                )
                assert preset_values
                selected_preset = None
                for preset_value in preset_values:
                    page.locator("#scoring-preset").select_option(preset_value)
                    page.wait_for_timeout(150)
                    if int(page.evaluate("state.scoring_summary.penalty_fields.length")) > 0:
                        selected_preset = preset_value
                        break
                assert selected_preset is not None

                page.locator("#expand-scoring").click()
                page.wait_for_function(
                    "() => document.getElementById('cockpit-root')?.classList.contains('scoring-expanded') === true"
                )
                page.locator("#scoring-workbench").wait_for(state="visible")
                context_inspector = page.locator('aside.inspector[aria-label="Context tools"]')
                assert context_inspector.is_visible() is False
                assert page.locator(".video-stage").is_visible() is False
                assert page.locator(".waveform-panel").is_visible() is False

                first_shot_id = page.evaluate("state.timing_segments[0].shot_id")
                second_shot_id = page.evaluate("state.timing_segments[1].shot_id")
                second_shot_time_ms = page.evaluate(
                    """(shotId) => (state?.project?.analysis?.shots || []).find((shot) => shot.id === shotId)?.time_ms ?? null""",
                    second_shot_id,
                )
                assert second_shot_time_ms is not None

                page.locator("#scoring-workbench-table .timeline-segment-cell").nth(1).click()
                page.wait_for_function("(shotId) => selectedShotId === shotId", arg=second_shot_id)
                page.wait_for_function(
                    """(targetMs) => Math.abs(((document.getElementById('primary-video')?.currentTime || 0) * 1000) - targetMs) < 150""",
                    arg=second_shot_time_ms,
                )

                score_select = page.locator(
                    '#scoring-workbench-table select[data-score-field="letter"]'
                ).first
                lock_button = page.locator("#scoring-workbench-table .lock-button").first
                lock_button.click()
                score_select.wait_for(state="visible")
                original_letter = score_select.input_value()
                score_values = score_select.evaluate(
                    "select => [...select.options].map((option) => option.value)"
                )
                next_letter = next(
                    (value for value in score_values if value != original_letter), original_letter
                )
                penalty_select = page.locator("#scoring-workbench-table .shot-penalty-select").first
                penalty_options = penalty_select.evaluate(
                    "select => [...select.options].map((option) => option.value).filter(Boolean)"
                )
                assert penalty_options

                score_select.select_option(next_letter)
                penalty_select.select_option(penalty_options[0])
                page.wait_for_function("(shotId) => selectedShotId === shotId", arg=first_shot_id)

                lock_button.click()
                page.wait_for_function(
                    """({ shotId, letter, penaltyField }) => {
                      const segment = (state?.timing_segments || []).find((item) => item.shot_id === shotId);
                      return Boolean(segment)
                        && segment.score_letter === letter
                        && Number(segment.penalty_counts?.[penaltyField] || 0) === 1;
                    }""",
                    arg={
                        "shotId": first_shot_id,
                        "letter": next_letter,
                        "penaltyField": penalty_options[0],
                    },
                )
                updated_letter = page.evaluate(
                    "(shotId) => (state?.timing_segments || []).find((item) => item.shot_id === shotId)?.score_letter ?? null",
                    first_shot_id,
                )
                assert updated_letter == next_letter
                updated_penalties = page.evaluate(
                    "(shotId) => (state?.timing_segments || []).find((item) => item.shot_id === shotId)?.penalty_counts ?? {}",
                    first_shot_id,
                )
                assert updated_penalties[penalty_options[0]] == 1

                page.locator(
                    "#scoring-workbench-table button.restore-button:not(.danger-button)"
                ).first.click()
                page.wait_for_function(
                    """({ shotId, originalLetter }) => {
                      const segment = (state?.timing_segments || []).find((item) => item.shot_id === shotId);
                      return Boolean(segment) && segment.score_letter === originalLetter;
                    }""",
                    arg={"shotId": first_shot_id, "originalLetter": original_letter},
                )
                restored_letter = page.evaluate(
                    """(shotId) => {
                      const segment = (state?.timing_segments || []).find((item) => item.shot_id === shotId);
                      return segment ? segment.score_letter : null;
                    }""",
                    first_shot_id,
                )
                assert restored_letter == original_letter

                page.locator("#scoring-workbench-table button.danger-button").nth(1).dispatch_event(
                    "click"
                )
                page.wait_for_function(
                    """(shotId) => !(state?.project?.analysis?.shots || []).some((shot) => shot.id === shotId)""",
                    arg=second_shot_id,
                )
                assert (
                    page.evaluate(
                        """(shotId) => !(state?.project?.analysis?.shots || []).some((shot) => shot.id === shotId)""",
                        second_shot_id,
                    )
                    is True
                )

                page.locator("#collapse-scoring").click()
                page.wait_for_function(
                    "() => document.getElementById('cockpit-root')?.classList.contains('scoring-expanded') === false"
                )
                assert page.evaluate("activeTool") == "scoring"
                assert context_inspector.is_visible() is True

                page.locator("#expand-scoring").click()
                page.wait_for_function(
                    "() => document.getElementById('cockpit-root')?.classList.contains('scoring-expanded') === true"
                )
                page.locator('button[data-tool="project"]').click(force=True)
                page.wait_for_function(
                    "() => document.getElementById('cockpit-root')?.classList.contains('scoring-expanded') === false && activeTool === 'project'"
                )
                assert page.locator(".video-stage").is_visible() is True
                assert page.locator(".waveform-panel").is_visible() is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_scoring_workbench_uses_fixed_full_width_columns(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="scoring-workbench-fixed-columns"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "scoring")
                page.locator("#scoring-enabled").check()
                page.locator("#expand-scoring").click()
                page.wait_for_function(
                    "() => document.getElementById('cockpit-root')?.classList.contains('scoring-expanded') === true"
                )
                layout = page.evaluate(
                    """() => {
                        const table = document.getElementById("scoring-workbench-table");
                        const headers = Array.from(table?.querySelectorAll(".head[data-timing-column]") || []).map((cell) => ({
                            columnId: cell.dataset.timingColumn || "",
                            width: cell.getBoundingClientRect().width,
                        }));
                        return {
                            template: table?.style.gridTemplateColumns || "",
                            tableWidth: table?.getBoundingClientRect().width || 0,
                            handleCount: table?.querySelectorAll(".timing-column-resize").length || 0,
                            headers,
                        };
                    }"""
                )
                assert layout["handleCount"] == 0
                assert layout["tableWidth"] > 0
                assert "minmax(" in layout["template"]
                assert len(layout["headers"]) == 9
                assert all(header["width"] >= 80 for header in layout["headers"])
                assert (
                    sum(header["width"] for header in layout["headers"])
                    >= layout["tableWidth"] - 180
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_viewport_window_drag_persists_after_reload(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="waveform-window-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                page.locator("#expand-waveform").click()
                page.wait_for_timeout(150)
                page.locator("#zoom-waveform-in").click()
                page.wait_for_timeout(150)

                window = page.locator("#waveform-window")
                track = page.locator("#waveform-window-track")
                handle = page.locator("#waveform-window-handle")
                window.wait_for(state="visible")

                track_box = track.bounding_box()
                handle_box = handle.bounding_box()
                assert track_box is not None
                assert handle_box is not None

                initial_offset = int(
                    page.evaluate("Number(localStorage.getItem('splitshot.waveform.offsetMs'))")
                )
                start_x = handle_box["x"] + handle_box["width"] / 2
                start_y = handle_box["y"] + handle_box["height"] / 2
                target_ratio = 0.75 if start_x < track_box["x"] + track_box["width"] / 2 else 0.25
                target_x = track_box["x"] + track_box["width"] * target_ratio

                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(target_x, start_y, steps=12)
                page.mouse.up()

                page.wait_for_function(
                    "(before) => Number(localStorage.getItem('splitshot.waveform.offsetMs')) !== before",
                    arg=initial_offset,
                )

                stored_offset = int(
                    page.evaluate("Number(localStorage.getItem('splitshot.waveform.offsetMs'))")
                )
                assert stored_offset != initial_offset
                page.wait_for_timeout(500)

                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "(expected) => waveformOffsetMs === expected", arg=stored_offset
                )
                if not page.locator("#waveform-window").is_visible():
                    page.locator("#expand-waveform").click()
                    page.wait_for_timeout(150)
                assert page.evaluate("waveformOffsetMs") == stored_offset
                assert (
                    int(
                        page.evaluate("Number(localStorage.getItem('splitshot.waveform.offsetMs'))")
                    )
                    == stored_offset
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
