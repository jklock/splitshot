from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import Browser, BrowserType, Page, Playwright, sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


ROOT = Path(__file__).resolve().parents[3]
TEST_VIDEO_DIR = ROOT / "tests" / "artifacts" / "test_video"
DEFAULT_PRIMARY_VIDEO = TEST_VIDEO_DIR / "TestVideo1.MP4"
DEFAULT_MERGE_VIDEO = TEST_VIDEO_DIR / "TestVideo2.MP4"
DEFAULT_PRACTISCORE = ROOT / "example_data" / "IDPA" / "IDPA.csv"


@dataclass(frozen=True, slots=True)
class BrowserTarget:
    name: str
    browser_type_name: str
    display_name: str
    channel: str | None = None
    app_path: Path | None = None


BROWSER_TARGETS: dict[str, BrowserTarget] = {
    "chromium": BrowserTarget(
        name="chromium",
        browser_type_name="chromium",
        display_name="Chromium",
    ),
    "chrome": BrowserTarget(
        name="chrome",
        browser_type_name="chromium",
        display_name="Google Chrome",
        channel="chrome",
        app_path=Path("/Applications/Google Chrome.app"),
    ),
    "edge": BrowserTarget(
        name="edge",
        browser_type_name="chromium",
        display_name="Microsoft Edge",
        channel="msedge",
        app_path=Path("/Applications/Microsoft Edge.app"),
    ),
    "firefox": BrowserTarget(
        name="firefox",
        browser_type_name="firefox",
        display_name="Firefox",
    ),
    "safari": BrowserTarget(
        name="safari",
        browser_type_name="webkit",
        display_name="Safari (WebKit)",
    ),
    "webkit": BrowserTarget(
        name="webkit",
        browser_type_name="webkit",
        display_name="WebKit",
    ),
}
SUPPORTED_BROWSERS = tuple(BROWSER_TARGETS)


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    data: dict[str, Any] | None = None


@dataclass(slots=True)
class BrowserInteractionAudit:
    browser: str
    log_path: str
    checks: list[CheckResult]
    data: dict[str, Any] | None = None

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit SplitShot interaction loops against real browsers, real routes, and real media inputs.",
    )
    parser.add_argument(
        "--browser",
        action="append",
        choices=SUPPORTED_BROWSERS,
        dest="browsers",
        help="Browser target to audit. Defaults to Chromium, Firefox, and Safari-class WebKit when available.",
    )
    parser.add_argument(
        "--primary-video",
        type=Path,
        default=DEFAULT_PRIMARY_VIDEO,
        help="Primary stage video to import during the audit.",
    )
    parser.add_argument(
        "--merge-video",
        type=Path,
        default=DEFAULT_MERGE_VIDEO,
        help="Optional merge video used for PiP interaction checks.",
    )
    parser.add_argument(
        "--practiscore",
        type=Path,
        default=DEFAULT_PRACTISCORE,
        help="Optional PractiScore file used for imported-summary review checks.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run headed instead of headless.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional path where the JSON report will be written.",
    )
    return parser


def default_browser_names() -> list[str]:
    names = ["chromium", "firefox", "safari"]
    if not BROWSER_TARGETS["chrome"].app_path or not BROWSER_TARGETS["chrome"].app_path.exists():
        pass
    else:
        names.insert(1, "chrome")
    if BROWSER_TARGETS["edge"].app_path and BROWSER_TARGETS["edge"].app_path.exists():
        names.append("edge")
    return names


def expect(condition: bool, name: str, detail: str, data: dict[str, Any] | None = None) -> CheckResult:
    return CheckResult(name=name, passed=condition, detail=detail, data=data)


def require_existing_file(path: Path | None, label: str) -> Path | None:
    if path is None:
        return None
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        return None
    return resolved


def launch_browser(playwright: Playwright, target: BrowserTarget, headed: bool) -> Browser:
    if target.app_path is not None and not target.app_path.exists():
        raise FileNotFoundError(f"{target.display_name} is not installed at {target.app_path}")
    browser_type: BrowserType = getattr(playwright, target.browser_type_name)
    launch_kwargs: dict[str, Any] = {"headless": not headed}
    if target.channel:
        launch_kwargs["channel"] = target.channel
    return browser_type.launch(**launch_kwargs)


def open_page(playwright: Playwright, target: BrowserTarget, base_url: str, headed: bool) -> tuple[Browser, Page]:
    browser = launch_browser(playwright, target, headed)
    page = browser.new_page(viewport={"width": 1440, "height": 1024})
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_selector("#current-file")
    return browser, page


def activity_cursor(server: BrowserControlServer) -> int:
    return int(server.activity.snapshot()["cursor"])


def activity_entries(server: BrowserControlServer, after_cursor: int, limit: int = 400) -> list[dict[str, Any]]:
    return list(server.activity.snapshot(after_seq=after_cursor, limit=limit)["entries"])


def wait_for_activity(
    server: BrowserControlServer,
    after_cursor: int,
    predicate: Callable[[list[dict[str, Any]]], bool],
    timeout_s: float = 10.0,
    limit: int = 400,
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        entries = activity_entries(server, after_cursor, limit=limit)
        if predicate(entries):
            return entries
        time.sleep(0.05)
    return activity_entries(server, after_cursor, limit=limit)


def has_api_success(entries: list[dict[str, Any]], path: str) -> bool:
    return any(entry.get("event") == "api.success" and entry.get("path") == path for entry in entries)


def has_event(entries: list[dict[str, Any]], event_name: str) -> bool:
    return any(entry.get("event") == event_name for entry in entries)


def has_browser_event(entries: list[dict[str, Any]], event_name: str) -> bool:
    return any(
        entry.get("event") == "browser.activity"
        and (entry.get("browser_event") == event_name or entry.get("detail", {}).get("event") == event_name)
        for entry in entries
    )


def show_project_tool(page: Page) -> None:
    page.locator("[data-tool='project']").click()
    page.wait_for_selector("#primary-file-path", state="visible")


def import_primary_video(page: Page, server: BrowserControlServer, primary_video: Path) -> CheckResult:
    after_cursor = activity_cursor(server)
    show_project_tool(page)
    page.locator("#primary-file-path").fill(str(primary_video))
    page.locator("#primary-file-path").press("Enter")
    page.wait_for_function("() => (state?.project?.analysis?.shots?.length || 0) > 0", timeout=120_000)
    page.wait_for_function(
        """
        () => {
          const video = document.getElementById('primary-video');
          return Boolean(
            video
            && Number.isFinite(video.duration)
            && video.duration > 0
            && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA
          );
        }
        """,
        timeout=30_000,
    )
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/import/primary"), timeout_s=5)
    result = page.evaluate(
        """
        () => ({
          shot_count: state?.project?.analysis?.shots?.length || 0,
          beep_ms: state?.project?.analysis?.beep_time_ms_primary ?? null,
          current_file: document.getElementById('current-file')?.textContent?.trim() || '',
          status: state?.status || '',
        })
        """
    )
    return expect(
        result["shot_count"] > 0
        and result["beep_ms"] is not None
        and result["current_file"] == primary_video.name
        and has_api_success(entries, "/api/import/primary"),
        "primary_import_round_trip",
        "Typed primary-path import should hit the real import route and produce detected shots for the browser UI.",
        {"result": result, "activity_entries": entries},
    )


def drag_waveform_viewport(page: Page, server: BrowserControlServer) -> CheckResult:
    after_cursor = activity_cursor(server)
    page.locator("#expand-waveform").click()
    page.wait_for_timeout(120)
    page.locator("#zoom-waveform-in").click()
    page.locator("#zoom-waveform-in").click()
    handle = page.locator("#waveform-window-handle")
    handle.wait_for(state="visible", timeout=30_000)
    before = page.evaluate(
        """
        () => ({
                    offset_ms: Number(waveformOffsetMs || 0),
                    zoom_x: Number(waveformZoomX || 0),
        })
        """
    )
    handle_box = handle.bounding_box()
    if not handle_box:
        return expect(False, "waveform_viewport_drag", "The waveform viewport handle was not available for drag validation.")
    center_y = handle_box["y"] + (handle_box["height"] / 2)
    start_x = handle_box["x"] + (handle_box["width"] / 2)
    end_x = start_x + 72
    page.mouse.move(start_x, center_y)
    page.mouse.down()
    page.mouse.move(end_x, center_y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(500)
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/project/ui-state"), timeout_s=5)
    after_drag = page.evaluate(
        """
        () => ({
          offset_ms: Number(waveformOffsetMs || 0),
          zoom_x: Number(waveformZoomX || 0),
        })
        """
    )
    page.evaluate("() => render()")
    after_render = page.evaluate(
        """
        () => ({
          offset_ms: Number(waveformOffsetMs || 0),
          zoom_x: Number(waveformZoomX || 0),
        })
        """
    )
    return expect(
        after_drag["offset_ms"] != before["offset_ms"]
        and after_render["offset_ms"] == after_drag["offset_ms"]
        and has_api_success(entries, "/api/project/ui-state"),
        "waveform_viewport_drag",
        "Dragging the waveform viewport handle should move the viewport, persist UI state, and survive a rerender.",
        {
          "before": before,
          "after_drag": after_drag,
          "after_render": after_render,
          "activity_entries": entries,
        },
    )


def drag_waveform_shot(page: Page, server: BrowserControlServer) -> CheckResult:
    page.locator("#reset-waveform-view").click()
    page.wait_for_function(
        "() => Number(waveformZoomX || 0) === 1 && Number(waveformOffsetMs || 0) === 0",
        timeout=30_000,
    )
    after_cursor = activity_cursor(server)
    drag_target = page.evaluate(
        """
        () => {
          renderWaveform();
          const waveform = document.getElementById('waveform');
          if (!(waveform instanceof HTMLCanvasElement)) return null;
          const rect = waveform.getBoundingClientRect();
          const shots = state?.project?.analysis?.shots || [];
          const shot = shots[1] || shots[0] || null;
          if (!shot) return null;
          return {
            shot_id: shot.id,
            original_time_ms: shot.time_ms,
            x: rect.left + waveformX(shot.time_ms, rect.width),
            y: rect.top + (rect.height / 2),
          };
        }
        """
    )
    if not drag_target:
        return expect(False, "waveform_shot_drag", "A draggable waveform shot marker was not available for validation.")
    page.mouse.move(drag_target["x"], drag_target["y"])
    page.mouse.down()
    page.mouse.move(drag_target["x"] + 84, drag_target["y"], steps=12)
    page.mouse.up()
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/shots/move"), timeout_s=5)
    after_drag = page.evaluate(
        """
        ({ shotId, originalTimeMs }) => {
          const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
          return {
            selected_shot_id: selectedShotId,
            time_ms: shot?.time_ms ?? null,
            delta_ms: shot ? shot.time_ms - originalTimeMs : null,
          };
        }
        """,
        {"shotId": drag_target["shot_id"], "originalTimeMs": drag_target["original_time_ms"]},
    )
    page.evaluate("() => renderWaveform()")
    after_render = page.evaluate(
        """
        ({ shotId }) => {
          const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
          return {
            time_ms: shot?.time_ms ?? null,
            selected_shot_id: selectedShotId,
          };
        }
        """,
        {"shotId": drag_target["shot_id"]},
    )
    return expect(
        after_drag["selected_shot_id"] == drag_target["shot_id"]
        and isinstance(after_drag["delta_ms"], (int, float))
        and after_drag["delta_ms"] > 0
        and after_render["time_ms"] == after_drag["time_ms"]
        and has_api_success(entries, "/api/shots/move"),
        "waveform_shot_drag",
        "Dragging a waveform shot marker should move the selected shot, commit through the real shots route, and survive a rerender.",
        {
            "before": drag_target,
            "after_drag": after_drag,
            "after_render": after_render,
            "activity_entries": entries,
        },
    )


def drag_timer_badge(page: Page, server: BrowserControlServer) -> CheckResult:
    page.locator("[data-tool='overlay']").click()
    if not page.locator("#show-timer").is_checked():
        enable_cursor = activity_cursor(server)
        page.locator("#show-timer").check()
        wait_for_activity(server, enable_cursor, lambda items: has_api_success(items, "/api/overlay"), timeout_s=5)
    after_cursor = activity_cursor(server)
    drag_target = page.evaluate(
        """
        async () => {
          const media = document.getElementById('primary-video');
          const stage = document.getElementById('video-stage');
          if (!(media instanceof HTMLVideoElement) || !(stage instanceof HTMLElement)) {
            return { error: 'required overlay elements are missing' };
          }
          const beepMs = Number(state?.project?.analysis?.beep_time_ms_primary || 0);
          media.currentTime = Math.max(0.05, (beepMs + 750) / 1000);
          renderLiveOverlay();
          await new Promise((resolve) => requestAnimationFrame(() => resolve()));
          const badge = document.querySelector('#score-layer [data-overlay-drag="timer"], #live-overlay [data-overlay-drag="timer"]');
                    const stageRect = stage.getBoundingClientRect();
          const frameGeometry = typeof previewFrameGeometry === 'function' ? previewFrameGeometry(media, stage) : null;
                    const frameRect = frameGeometry?.frameRect
                        ? {
                                left: stageRect.left + frameGeometry.frameRect.left,
                                top: stageRect.top + frameGeometry.frameRect.top,
                                width: frameGeometry.frameRect.width,
                                height: frameGeometry.frameRect.height,
                            }
                        : null;
          if (!(badge instanceof HTMLElement) || !frameRect) {
            return { error: 'timer badge is not visible for drag validation' };
          }
          const badgeRect = badge.getBoundingClientRect();
          const targetXNorm = 0.24;
          const targetYNorm = 0.28;
          return {
            start_x: badgeRect.left + (badgeRect.width / 2),
            start_y: badgeRect.top + (badgeRect.height / 2),
            target_client_x: frameRect.left + (frameRect.width * targetXNorm),
            target_client_y: frameRect.top + (frameRect.height * targetYNorm),
            target_x: targetXNorm,
            target_y: targetYNorm,
          };
        }
        """
    )
    if drag_target.get("error"):
        return expect(False, "timer_badge_drag_persists", drag_target["error"], drag_target)
    page.mouse.move(drag_target["start_x"], drag_target["start_y"])
    page.mouse.down()
    page.mouse.move(drag_target["target_client_x"], drag_target["target_client_y"], steps=12)
    page.mouse.up()
    page.wait_for_timeout(120)
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/overlay"), timeout_s=5)
    result = page.evaluate(
        """
        () => ({
          timer_x: state?.project?.overlay?.timer_x ?? null,
          timer_y: state?.project?.overlay?.timer_y ?? null,
          shot_quadrant: state?.project?.overlay?.shot_quadrant || null,
        })
        """
    )
    page.evaluate("() => renderLiveOverlay()")
    after_render = page.evaluate(
        """
        () => ({
          timer_x: state?.project?.overlay?.timer_x ?? null,
          timer_y: state?.project?.overlay?.timer_y ?? null,
        })
        """
    )
    return expect(
        isinstance(result["timer_x"], (int, float))
        and isinstance(result["timer_y"], (int, float))
        and abs(result["timer_x"] - drag_target["target_x"]) <= 0.04
        and abs(result["timer_y"] - drag_target["target_y"]) <= 0.06
        and after_render["timer_x"] == result["timer_x"]
        and after_render["timer_y"] == result["timer_y"]
        and has_api_success(entries, "/api/overlay"),
        "timer_badge_drag_persists",
        "Dragging the rendered timer badge should update the timer X/Y controls, commit through the real overlay route, and survive a rerender.",
        {"drag_target": drag_target, "result": result, "after_render": after_render, "activity_entries": entries},
    )


def import_practiscore_file(page: Page, server: BrowserControlServer, practiscore_path: Path) -> CheckResult:
    after_cursor = activity_cursor(server)
    page.locator("#practiscore-file-input").set_input_files(str(practiscore_path))
    page.wait_for_function(
        "() => Boolean(state?.project?.scoring?.imported_stage?.source_name)",
        timeout=120_000,
    )
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/files/practiscore"), timeout_s=5)
    result = page.evaluate(
        """
        () => ({
          source_name: state?.project?.scoring?.imported_stage?.source_name || '',
          stage_number: state?.project?.scoring?.imported_stage?.stage_number ?? null,
          match_type: state?.project?.scoring?.match_type || '',
          custom_box_mode: state?.project?.overlay?.custom_box_mode || '',
          imported_summary_boxes: (state?.project?.overlay?.text_boxes || []).filter((box) => box.source === 'imported_summary').length,
        })
        """
    )
    return expect(
        result["source_name"] == practiscore_path.name
        and result["stage_number"] is not None
        and result["match_type"]
        and result["custom_box_mode"] == "imported_summary"
        and result["imported_summary_boxes"] > 0
        and has_event(entries, "api.files.practiscore.imported"),
        "practiscore_import_round_trip",
        "Uploading a PractiScore file should hit the real upload route and populate imported scoring state plus the review summary box.",
        {"result": result, "activity_entries": entries},
    )


def audit_scoring_raw_delta_summary(page: Page) -> CheckResult:
        page.locator("[data-tool='scoring']").click()
        page.wait_for_function(
                """
                () => Boolean(
                    state?.scoring_summary?.imported_stage
                    && document.querySelectorAll('#practiscore-import-summary dt').length >= 4
                )
                """,
                timeout=30_000,
        )
        result = page.evaluate(
                """
                () => {
                    const terms = Array.from(document.querySelectorAll('#practiscore-import-summary dt'));
                    const values = Array.from(document.querySelectorAll('#practiscore-import-summary dd'));
                    const details = Object.fromEntries(
                        terms.map((term, index) => [
                            term.textContent?.trim() || '',
                            values[index]?.textContent?.trim() || '',
                        ]),
                    );
                    const summary = state?.scoring_summary || {};
                    const formatSeconds = (value) => (
                        value === null || value === undefined || value === ''
                            ? ''
                            : `${formatNumber(value, 2)}s`
                    );
                    const expectedResultLabel = summary.display_label || 'Result';
                    return {
                        caption: document.getElementById('scoring-imported-caption')?.textContent?.trim() || '',
                        details,
                        expected: {
                            official_raw: formatSeconds(summary.official_raw_seconds ?? summary.imported_stage?.raw_seconds),
                            video_raw: formatSeconds(summary.raw_seconds),
                            raw_delta: formatSeconds(summary.raw_delta_seconds),
                            result_label: expectedResultLabel,
                            result_value: summary.display_value || '',
                        },
                    };
                }
                """
        )
        details = result["details"]
        expected = result["expected"]
        return expect(
                details.get("Official Raw") == expected["official_raw"]
                and details.get("Video Raw") == expected["video_raw"]
                and details.get("Raw Delta") == expected["raw_delta"]
                and details.get(expected["result_label"]) == expected["result_value"]
                and result["caption"].startswith("Imported "),
                "scoring_raw_delta_summary_is_clear",
                "The scoring pane should spell out Official Raw, Video Raw, and Raw Delta using the same values as the current scoring summary so stage-level mismatch is obvious.",
                result,
        )


def audit_imported_summary_default_anchor(page: Page) -> CheckResult:
    page.locator("[data-tool='review']").click()
    page.wait_for_function(
        """
        () => Boolean(document.querySelector('#review-text-box-list [data-text-box-field="quadrant"]'))
        """,
        timeout=30_000,
    )
    result = page.evaluate(
        """
        () => {
          const imported = (state?.project?.overlay?.text_boxes || []).find((box) => box.source === 'imported_summary') || null;
          const placement = document.querySelector('#review-text-box-list [data-text-box-field="quadrant"]');
          const hint = document.querySelector('#review-text-box-list .hint, #review-text-box-list p');
          return {
            quadrant: imported?.quadrant || null,
            x: imported?.x ?? null,
            y: imported?.y ?? null,
            placement_value: placement instanceof HTMLSelectElement ? placement.value : null,
            hint_text: hint instanceof HTMLElement ? hint.textContent?.trim() || '' : '',
          };
        }
        """
    )
    return expect(
        result["quadrant"] == "above_final"
        and result["placement_value"] == "above_final"
        and "above the final score badge" in result["hint_text"].lower(),
        "imported_summary_defaults_to_above_final",
        "A real PractiScore import should surface the imported summary box as Above Final Box by default in the review tool.",
        result,
    )


def drag_imported_summary_box(page: Page, server: BrowserControlServer) -> CheckResult:
    after_cursor = activity_cursor(server)
    result = page.evaluate(
        """
        async () => {
          const media = document.getElementById('primary-video');
          const overlay = document.getElementById('custom-overlay');
          const stage = document.getElementById('video-stage');
          if (!(media instanceof HTMLVideoElement) || !(overlay instanceof HTMLElement) || !(stage instanceof HTMLElement)) {
            return { error: 'required review overlay elements are missing' };
          }
          media.currentTime = Math.max(0, (media.duration || 0) - 0.05);
                    renderLiveOverlay();
          await new Promise((resolve) => requestAnimationFrame(() => resolve()));
          const badge = document.querySelector('#custom-overlay [data-text-box-drag="true"]');
                    const stageRect = stage.getBoundingClientRect();
                    const frameGeometry = typeof previewFrameGeometry === 'function' ? previewFrameGeometry(media, stage) : null;
                    const frameRect = frameGeometry?.frameRect
                        ? {
                                left: stageRect.left + frameGeometry.frameRect.left,
                                top: stageRect.top + frameGeometry.frameRect.top,
                                width: frameGeometry.frameRect.width,
                                height: frameGeometry.frameRect.height,
                            }
                        : null;
          if (!(badge instanceof HTMLElement) || !frameRect) {
            return { error: 'imported summary badge is not visible after the final shot' };
          }
          const badgeRect = badge.getBoundingClientRect();
          const startClientX = badgeRect.left + (badgeRect.width / 2);
          const startClientY = badgeRect.top + (badgeRect.height / 2);
          const targetXNorm = 0.58;
          const targetYNorm = 0.62;
          const targetClientX = frameRect.left + (frameRect.width * targetXNorm);
          const targetClientY = frameRect.top + (frameRect.height * targetYNorm);
          const pointerId = 11;
          badge.dispatchEvent(new PointerEvent('pointerdown', {
            bubbles: true,
            pointerId,
            button: 0,
            clientX: startClientX,
            clientY: startClientY,
          }));
          overlay.dispatchEvent(new PointerEvent('pointermove', {
            bubbles: true,
            pointerId,
            button: 0,
            buttons: 1,
            clientX: targetClientX,
            clientY: targetClientY,
          }));
          overlay.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true,
            pointerId,
            button: 0,
            clientX: targetClientX,
            clientY: targetClientY,
          }));
          await new Promise((resolve) => window.setTimeout(resolve, 80));
          const imported = (state?.project?.overlay?.text_boxes || []).find((box) => box.source === 'imported_summary') || null;
          return {
            target_x: targetXNorm,
            target_y: targetYNorm,
            quadrant: imported?.quadrant || null,
            x: imported?.x ?? null,
            y: imported?.y ?? null,
          };
        }
        """
    )
    if result.get("error"):
        return expect(False, "review_summary_drag_persists", result["error"], result)
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/overlay"), timeout_s=5)
    return expect(
        result["quadrant"] == "custom"
        and isinstance(result["x"], (int, float))
        and isinstance(result["y"], (int, float))
        and abs(result["x"] - result["target_x"]) <= 0.03
        and abs(result["y"] - result["target_y"]) <= 0.05
        and has_api_success(entries, "/api/overlay"),
        "review_summary_drag_persists",
        "Dragging the rendered imported summary badge should switch it to custom placement and commit the new coordinates through the real overlay route.",
        {"result": result, "activity_entries": entries},
    )


def preserve_review_inspector_scroll(page: Page, server: BrowserControlServer) -> CheckResult:
    page.locator("[data-tool='review']").click()
    inspector = page.locator(".inspector")
    metrics = page.evaluate(
        """
        () => {
          const el = document.querySelector('.inspector');
          if (!(el instanceof HTMLElement)) return null;
          return {
            client_height: el.clientHeight,
            scroll_height: el.scrollHeight,
            scroll_top: el.scrollTop,
          };
        }
        """
    )
    if metrics is None:
        return expect(False, "review_scroll_persists", "The inspector container was not available for review scroll validation.")
    if metrics["scroll_height"] <= metrics["client_height"] + 8:
        page.set_viewport_size({"width": 1440, "height": 720})
        for _ in range(8):
            page.locator("#review-add-text-box").click()
        page.wait_for_timeout(250)
        metrics = page.evaluate(
            """
            () => {
              const el = document.querySelector('.inspector');
              if (!(el instanceof HTMLElement)) return null;
              return {
                client_height: el.clientHeight,
                scroll_height: el.scrollHeight,
                scroll_top: el.scrollTop,
              };
            }
            """
        )
    if metrics is None or metrics["scroll_height"] <= metrics["client_height"] + 8:
        return expect(
            False,
            "review_scroll_persists",
            "The review inspector did not have enough overflow content to validate wheel-scroll persistence.",
            metrics,
        )
    inspector_box = inspector.bounding_box()
    if not inspector_box:
        return expect(False, "review_scroll_persists", "The inspector container could not be measured for wheel scrolling.")
    page.mouse.move(inspector_box["x"] + 140, inspector_box["y"] + 180)
    page.mouse.wheel(0, 900)
    page.wait_for_timeout(100)
    scroll_before = page.evaluate(
        """
        () => {
          const el = document.querySelector('.inspector');
          return el instanceof HTMLElement ? el.scrollTop : 0;
        }
        """
    )
    checkbox = page.locator("#show-draw")
    before_checked = checkbox.is_checked()
    after_cursor = activity_cursor(server)
    checkbox.click()
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/overlay"), timeout_s=5)
    after = page.evaluate(
        """
        () => {
          const el = document.querySelector('.inspector');
          const checkboxEl = document.getElementById('show-draw');
          return {
            scroll_top: el instanceof HTMLElement ? el.scrollTop : 0,
            checked: checkboxEl instanceof HTMLInputElement ? checkboxEl.checked : null,
          };
        }
        """
    )
    return expect(
        scroll_before > 0
        and after["scroll_top"] >= scroll_before - 24
        and after["checked"] is (not before_checked)
        and has_api_success(entries, "/api/overlay"),
        "review_scroll_persists",
        "Wheel-scrolling the review inspector should keep its position after a real overlay update rerender.",
        {
            "metrics": metrics,
            "scroll_before": scroll_before,
            "before_checked": before_checked,
            "after": after,
            "activity_entries": entries,
        },
    )


def import_merge_media(page: Page, server: BrowserControlServer, merge_video: Path) -> CheckResult:
    page.locator("[data-tool='merge']").click()
    after_cursor = activity_cursor(server)
    page.locator("#merge-media-input").set_input_files(str(merge_video))
    page.wait_for_function(
        "() => (state?.project?.merge_sources?.length || 0) > 0 && document.querySelectorAll('#merge-media-list .merge-media-card').length > 0",
        timeout=120_000,
    )
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/files/merge"), timeout_s=5)
    result = page.evaluate(
        """
        () => ({
          merge_source_count: (state?.project?.merge_sources || []).length,
          latest_source_path: state?.project?.merge_sources?.at(-1)?.asset?.path || state?.project?.merge_sources?.at(-1)?.path || '',
          label_text: document.querySelector('#merge-media-list .merge-media-card strong')?.textContent?.trim() || '',
        })
        """
    )
    return expect(
        result["merge_source_count"] > 0
        and merge_video.name in result["label_text"]
        and result["latest_source_path"].endswith(merge_video.name)
        and has_event(entries, "api.files.merge.ingested"),
        "merge_media_import_round_trip",
        "Choosing merge media through the real file input should add a PiP source card and hit the real merge upload route.",
        {"result": result, "activity_entries": entries},
    )


def drag_merge_preview_persists(page: Page, server: BrowserControlServer, merge_video: Path) -> CheckResult:
    page.locator("[data-tool='merge']").click()
    if page.evaluate("() => (state?.project?.merge_sources || []).length") < 2:
        import_cursor = activity_cursor(server)
        page.locator("#merge-media-input").set_input_files(str(merge_video))
        page.wait_for_function(
            "() => (state?.project?.merge_sources || []).length >= 2",
            timeout=120_000,
        )
        wait_for_activity(server, import_cursor, lambda items: has_api_success(items, "/api/files/merge"), timeout_s=5)
    layout_cursor = activity_cursor(server)
    page.locator("#merge-layout").select_option("pip")
    wait_for_activity(server, layout_cursor, lambda items: has_api_success(items, "/api/merge"), timeout_s=5)
    page.wait_for_function(
        """
        () => (state?.project?.merge_sources || []).length >= 2 && Boolean(document.querySelector('.merge-preview-item[data-source-id]'))
        """,
        timeout=30_000,
    )
    after_cursor = activity_cursor(server)
    drag_target = page.evaluate(
        """
        () => {
          renderVideo();
                    const items = Array.from(document.querySelectorAll('.merge-preview-item[data-source-id]'));
                    const item = items.at(-1) || null;
          const stage = document.getElementById('video-stage');
          const media = document.getElementById('primary-video');
          if (!(item instanceof HTMLElement) || !(stage instanceof HTMLElement) || !(media instanceof HTMLVideoElement)) return null;
                    const stageRect = stage.getBoundingClientRect();
          const frameGeometry = typeof previewFrameGeometry === 'function' ? previewFrameGeometry(media, stage) : null;
                    const frameRect = frameGeometry?.frameRect
                        ? {
                                left: stageRect.left + frameGeometry.frameRect.left,
                                top: stageRect.top + frameGeometry.frameRect.top,
                                width: frameGeometry.frameRect.width,
                                height: frameGeometry.frameRect.height,
                            }
                        : null;
          if (!frameRect) return null;
          const itemRect = item.getBoundingClientRect();
          const centerX = itemRect.left + (itemRect.width / 2);
          const centerY = itemRect.top + (itemRect.height / 2);
                    const targetClientX = Math.max(frameRect.left + 24, centerX - 96);
                    const targetClientY = Math.max(frameRect.top + 24, centerY - 72);
          return {
            source_id: item.dataset.sourceId || '',
            start_x: centerX,
            start_y: centerY,
            target_x: targetClientX,
            target_y: targetClientY,
                        before_pip_x: Number((state?.project?.merge_sources || []).find((entry) => (entry.id || '') === (item.dataset.sourceId || ''))?.pip_x ?? 0),
                        before_pip_y: Number((state?.project?.merge_sources || []).find((entry) => (entry.id || '') === (item.dataset.sourceId || ''))?.pip_y ?? 0),
          };
        }
        """
    )
    if not drag_target or not drag_target["source_id"]:
        return expect(False, "merge_preview_drag_persists", "A draggable PiP preview item was not available for validation.")
    page.mouse.move(drag_target["start_x"], drag_target["start_y"])
    page.mouse.down()
    page.mouse.move(drag_target["target_x"], drag_target["target_y"], steps=12)
    page.mouse.up()
    page.wait_for_timeout(120)
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/merge/source"), timeout_s=5)
    after_drag = page.evaluate(
        """
        ({ sourceId }) => {
          const source = (state?.project?.merge_sources || []).find((item) => item.id === sourceId);
          return {
            pip_x: Number(source?.pip_x ?? 0),
            pip_y: Number(source?.pip_y ?? 0),
          };
        }
        """,
        {"sourceId": drag_target["source_id"]},
    )
    page.evaluate("() => renderVideo()")
    after_render = page.evaluate(
        """
        ({ sourceId }) => {
          const source = (state?.project?.merge_sources || []).find((item) => item.id === sourceId);
          return {
            pip_x: Number(source?.pip_x ?? 0),
            pip_y: Number(source?.pip_y ?? 0),
          };
        }
        """,
        {"sourceId": drag_target["source_id"]},
    )
    return expect(
        (after_drag["pip_x"] != drag_target["before_pip_x"] or after_drag["pip_y"] != drag_target["before_pip_y"])
        and after_render["pip_x"] == after_drag["pip_x"]
        and after_render["pip_y"] == after_drag["pip_y"]
        and has_api_success(entries, "/api/merge/source"),
        "merge_preview_drag_persists",
        "Dragging the PiP preview item should update the merge source X/Y coordinates, commit through the real merge-source route, and survive a rerender.",
        {"before": drag_target, "after_drag": after_drag, "after_render": after_render, "activity_entries": entries},
    )


def resize_layout_persists(page: Page, server: BrowserControlServer) -> CheckResult:
    lock_button = page.locator("#toggle-layout-lock-waveform")
    if "Unlock" in (lock_button.get_attribute("aria-label") or ""):
        lock_button.click()
        page.wait_for_timeout(120)
    after_cursor = activity_cursor(server)
    handle = page.locator("#resize-sidebar").bounding_box()
    if handle is None:
        return expect(False, "layout_resize_persists", "The inspector resize handle was not visible.")
    before = page.evaluate(
        """
        () => ({
          inspector_width: layoutSizes.inspectorWidth,
          stored: Number(window.localStorage.getItem('splitshot.layout.inspectorWidth') || 0),
          ui_state_width: Number(state?.project?.ui_state?.inspector_width || 0),
        })
        """
    )
    pointer_x = handle["x"] + (handle["width"] / 2)
    pointer_y = handle["y"] + (handle["height"] / 2)
    page.mouse.move(pointer_x, pointer_y)
    page.mouse.down()
    page.mouse.move(pointer_x - 88, pointer_y, steps=12)
    page.mouse.up()
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/project/ui-state"), timeout_s=5)
    after_drag = page.evaluate(
        """
        () => ({
          inspector_width: layoutSizes.inspectorWidth,
          stored: Number(window.localStorage.getItem('splitshot.layout.inspectorWidth') || 0),
          ui_state_width: Number(state?.project?.ui_state?.inspector_width || 0),
          resizing_class_present: document.body.classList.contains('resizing-layout'),
        })
        """
    )
    page.evaluate("() => renderViewportLayout()")
    after_render = page.evaluate(
        """
        () => ({
          inspector_width: layoutSizes.inspectorWidth,
          stored: Number(window.localStorage.getItem('splitshot.layout.inspectorWidth') || 0),
          ui_state_width: Number(state?.project?.ui_state?.inspector_width || 0),
        })
        """
    )
    return expect(
        after_drag["inspector_width"] != before["inspector_width"]
        and after_drag["stored"] == round(after_drag["inspector_width"])
        and after_drag["ui_state_width"] == round(after_drag["inspector_width"])
        and after_render["inspector_width"] == after_drag["inspector_width"]
        and after_drag["resizing_class_present"] is False
        and has_api_success(entries, "/api/project/ui-state"),
        "layout_resize_persists",
        "Dragging the inspector resize handle should persist the new layout width through project UI state and survive a rerender.",
        {"before": before, "after_drag": after_drag, "after_render": after_render, "activity_entries": entries},
    )


def drag_merge_size_slider_commits(page: Page, server: BrowserControlServer) -> CheckResult:
    page.locator("[data-tool='merge']").click()
    before = page.evaluate(
        """
        () => ({
          size: Number(state?.project?.merge_sources?.[0]?.pip_size_percent || 0),
        })
        """
    )
    after_cursor = activity_cursor(server)
    slider = page.locator("[data-merge-source-field='size']").first
    slider_box = slider.bounding_box()
    if not slider_box:
        return expect(False, "merge_slider_round_trip", "The PiP size slider was not available for drag validation.")
    center_y = slider_box["y"] + (slider_box["height"] / 2)
    start_x = slider_box["x"] + (slider_box["width"] * 0.35)
    end_x = slider_box["x"] + (slider_box["width"] * 0.62)
    page.mouse.move(start_x, center_y)
    page.mouse.down()
    page.mouse.move(end_x, center_y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(450)
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/merge/source"), timeout_s=5)
    after = page.evaluate(
        """
        () => {
          const el = document.querySelector('.inspector');
          const sliderEl = document.querySelector('[data-merge-source-field="size"]');
          return {
                        scroll_top: el instanceof HTMLElement ? el.scrollTop : 0,
            size: Number(state?.project?.merge_sources?.[0]?.pip_size_percent || 0),
            slider_value: sliderEl instanceof HTMLInputElement ? Number(sliderEl.value || 0) : 0,
          };
        }
        """
    )
    return expect(
                after["size"] != before["size"]
        and after["slider_value"] == after["size"]
        and has_api_success(entries, "/api/merge/source"),
                "merge_slider_round_trip",
                "Dragging a PiP size slider should update the live value and commit through the real merge-source route.",
        {
          "before": before,
          "after": after,
          "activity_entries": entries,
        },
    )


def sync_nudge_commits(page: Page, server: BrowserControlServer) -> CheckResult:
    page.locator("[data-tool='merge']").click()
    before = page.evaluate(
        """
        () => ({
          sync_offset_ms: Number(state?.project?.merge_sources?.[0]?.sync_offset_ms || 0),
        })
        """
    )
    after_cursor = activity_cursor(server)
    page.get_by_role("button", name="+10 ms").first.click()
    entries = wait_for_activity(server, after_cursor, lambda items: has_api_success(items, "/api/merge/source"), timeout_s=5)
    after = page.evaluate(
        """
        () => ({
          sync_offset_ms: Number(state?.project?.merge_sources?.[0]?.sync_offset_ms || 0),
          label_text: document.querySelector('[data-merge-source-sync-label="true"]')?.textContent?.trim() || '',
        })
        """
    )
    return expect(
        after["sync_offset_ms"] == before["sync_offset_ms"] + 10
        and str(after["sync_offset_ms"]) in after["label_text"]
        and has_api_success(entries, "/api/merge/source"),
        "merge_sync_nudge_round_trip",
        "Using a PiP sync nudge button should update the saved sync offset and commit through the real merge-source route.",
        {"before": before, "after": after, "activity_entries": entries},
    )


def run_browser_audit(
    playwright: Playwright,
    target_name: str,
    primary_video: Path,
    merge_video: Path | None,
    practiscore_path: Path | None,
    headed: bool,
) -> BrowserInteractionAudit:
    target = BROWSER_TARGETS[target_name]
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, log_level="off")
    server.start_background(open_browser=False)
    browser: Browser | None = None
    try:
        try:
            browser, page = open_page(playwright, target, server.url, headed)
        except Exception as error:  # noqa: BLE001
            return BrowserInteractionAudit(
                browser=target_name,
                log_path=str(server.activity.path),
                checks=[
                    CheckResult(
                        name="browser_available",
                        passed=False,
                        detail=f"{target.display_name} could not be launched: {error}",
                    )
                ],
            )

        checks = [
            import_primary_video(page, server, primary_video),
            drag_waveform_viewport(page, server),
            drag_waveform_shot(page, server),
            drag_timer_badge(page, server),
            resize_layout_persists(page, server),
        ]
        if practiscore_path is not None:
            checks.extend(
                [
                    import_practiscore_file(page, server, practiscore_path),
                    audit_scoring_raw_delta_summary(page),
                    audit_imported_summary_default_anchor(page),
                    drag_imported_summary_box(page, server),
                    preserve_review_inspector_scroll(page, server),
                ]
            )
        if merge_video is not None:
            checks.extend(
                [
                    import_merge_media(page, server, merge_video),
                    drag_merge_preview_persists(page, server, merge_video),
                    drag_merge_size_slider_commits(page, server),
                    sync_nudge_commits(page, server),
                ]
            )
        return BrowserInteractionAudit(
            browser=target_name,
            log_path=str(server.activity.path),
            checks=checks,
            data={
                "primary_video": str(primary_video),
                "merge_video": str(merge_video) if merge_video is not None else None,
                "practiscore": str(practiscore_path) if practiscore_path is not None else None,
            },
        )
    finally:
        if browser is not None:
            browser.close()
        server.shutdown()


def summarize_results(results: list[BrowserInteractionAudit]) -> str:
    lines = ["# Browser Interaction Audit", ""]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"## {result.browser}: {status}")
        lines.append(f"- Log: {result.log_path}")
        for check in result.checks:
            mark = "PASS" if check.passed else "FAIL"
            lines.append(f"- {mark} {check.name}: {check.detail}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    browsers = args.browsers or default_browser_names()
    primary_video = require_existing_file(args.primary_video, "Primary video")
    merge_video = require_existing_file(args.merge_video, "Merge video")
    practiscore_path = require_existing_file(args.practiscore, "PractiScore file")
    if primary_video is None:
        raise SystemExit("Primary video not found. Pass --primary-video with a real stage video path.")

    with sync_playwright() as playwright:
        results = [
            run_browser_audit(
                playwright,
                browser_name,
                primary_video,
                merge_video,
                practiscore_path,
                args.headed,
            )
            for browser_name in browsers
        ]

    payload = {
        "primary_video": str(primary_video),
        "merge_video": str(merge_video) if merge_video is not None else None,
        "practiscore": str(practiscore_path) if practiscore_path is not None else None,
        "results": [
            {
                "browser": result.browser,
                "passed": result.passed,
                "log_path": result.log_path,
                "checks": [asdict(check) for check in result.checks],
                "data": result.data,
            }
            for result in results
        ],
    }
    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(summarize_results(results))
    print(json.dumps(payload, indent=2))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())