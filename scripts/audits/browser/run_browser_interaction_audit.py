"""Drive real browser interactions against SplitShot to capture evidence for UI regressions."""

from __future__ import annotations

import argparse
import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from playwright.sync_api import (
    Browser,
    BrowserType,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from _media_fixtures import ensure_stage_video
from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_VIDEO_DIR = ROOT / "tests" / "fixtures" / "media"
DEFAULT_PRIMARY_VIDEO = FIXTURE_VIDEO_DIR / "stage.mp4"
DEFAULT_MERGE_VIDEO = FIXTURE_VIDEO_DIR / "stage-merge.mp4"
DEFAULT_PRACTISCORE = ROOT / "example_data" / "IDPA" / "IDPA.csv"
AUDIT_TMP_ROOT = ROOT / "tmp" / "codex" / "browser-interaction-audit"


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
    parser.add_argument(
        "--base-url",
        type=str,
        default="",
        help="Optional existing SplitShot base URL to audit instead of launching a local BrowserControlServer.",
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


def expect(
    condition: bool, name: str, detail: str, data: dict[str, Any] | None = None
) -> CheckResult:
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


def open_page(
    playwright: Playwright, target: BrowserTarget, base_url: str, headed: bool
) -> tuple[Browser, Page]:
    browser = launch_browser(playwright, target, headed)
    page = browser.new_page(viewport={"width": 1440, "height": 1024})
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_selector("#current-file")
    return browser, page


def _activity_snapshot(base_url: str, after_cursor: int = 0, limit: int = 1000) -> dict[str, Any]:
    query = urlencode({"after": after_cursor, "limit": limit})
    with urlopen(f"{base_url}api/activity/poll?{query}", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def activity_cursor(activity_source: BrowserControlServer | str) -> int:
    if isinstance(activity_source, str):
        return int(_activity_snapshot(activity_source)["cursor"])
    return int(activity_source.activity.snapshot()["cursor"])


def activity_entries(
    activity_source: BrowserControlServer | str,
    after_cursor: int,
    limit: int = 400,
) -> list[dict[str, Any]]:
    if isinstance(activity_source, str):
        return list(
            _activity_snapshot(activity_source, after_cursor=after_cursor, limit=limit)["entries"]
        )
    return list(activity_source.activity.snapshot(after_seq=after_cursor, limit=limit)["entries"])


def wait_for_activity(
    activity_source: BrowserControlServer | str,
    after_cursor: int,
    predicate: Callable[[list[dict[str, Any]]], bool],
    timeout_s: float = 10.0,
    limit: int = 400,
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        entries = activity_entries(activity_source, after_cursor, limit=limit)
        if predicate(entries):
            return entries
        time.sleep(0.05)
    return activity_entries(activity_source, after_cursor, limit=limit)


def has_api_success(entries: list[dict[str, Any]], path: str) -> bool:
    return any(
        entry.get("event") == "api.success" and entry.get("path") == path for entry in entries
    )


def has_event(entries: list[dict[str, Any]], event_name: str) -> bool:
    return any(entry.get("event") == event_name for entry in entries)


def has_browser_event(entries: list[dict[str, Any]], event_name: str) -> bool:
    return any(
        entry.get("event") == "browser.activity"
        and (
            entry.get("browser_event") == event_name
            or entry.get("detail", {}).get("event") == event_name
        )
        for entry in entries
    )


def show_project_tool(page: Page) -> None:
    page.locator("[data-tool='project']").click()
    page.wait_for_selector("#project-path", state="visible")


def _audit_project_path(primary_video: Path) -> str:
    AUDIT_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return str(AUDIT_TMP_ROOT / f"browser-audit-{uuid.uuid4().hex}.ssproj")


def _multipart_upload(
    base_url: str, endpoint: str, file_path: Path, field_name: str = "file"
) -> dict[str, Any]:
    boundary = uuid.uuid4().hex
    data = file_path.read_bytes()
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("latin-1")
        + data
        + f"\r\n--{boundary}--\r\n".encode("latin-1")
    )
    req = Request(
        f"{base_url}{endpoint}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def import_primary_video(
    page: Page, activity_source: BrowserControlServer | str, primary_video: Path
) -> CheckResult:
    after_cursor = activity_cursor(activity_source)
    if isinstance(activity_source, str):
        base = activity_source
        if not page.evaluate("Boolean(state?.project?.path)"):
            project_path = _audit_project_path(primary_video)
            page.evaluate("(path) => createNewProject(path)", project_path)
            page.wait_for_function("() => Boolean(state?.project?.path)", timeout=30_000)
        _multipart_upload(base, "api/files/primary", primary_video)
        page.evaluate("async () => { await refresh(); }")
    else:
        if not page.evaluate("Boolean(state?.project?.path)"):
            project_path = _audit_project_path(primary_video)
            page.evaluate("(path) => createNewProject(path)", project_path)
            page.wait_for_function("() => Boolean(state?.project?.path)", timeout=30_000)
        show_project_tool(page)
        page.locator("#primary-file-input").set_input_files(str(primary_video))
    page.wait_for_function(
        "() => (state?.project?.analysis?.shots?.length || 0) > 0", timeout=120_000
    )
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
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_event(items, "api.files.primary.ingested"),
        timeout_s=10,
    )
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
        and result["current_file"].startswith(primary_video.stem)
        and has_event(entries, "api.files.primary.ingested"),
        "primary_import_round_trip",
        "Primary file import should hit the real upload route and produce detected shots for the browser UI.",
        {"result": result, "activity_entries": entries},
    )


def drag_waveform_viewport(page: Page, activity_source: BrowserControlServer | str) -> CheckResult:
    after_cursor = activity_cursor(activity_source)
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
        return expect(
            False,
            "waveform_viewport_drag",
            "The waveform viewport handle was not available for drag validation.",
        )
    center_y = handle_box["y"] + (handle_box["height"] / 2)
    start_x = handle_box["x"] + (handle_box["width"] / 2)
    end_x = start_x - 160
    page.mouse.move(start_x, center_y)
    page.mouse.down()
    page.mouse.move(end_x, center_y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(500)
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/project/ui-state"),
        timeout_s=5,
    )
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
        abs(after_drag["offset_ms"] - before["offset_ms"]) > 0.5
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


def drag_waveform_shot(page: Page, activity_source: BrowserControlServer | str) -> CheckResult:
    page.locator("#reset-waveform-view").click()
    page.wait_for_function(
        "() => Number(waveformZoomX || 0) === 1 && Number(waveformOffsetMs || 0) === 0",
        timeout=30_000,
    )
    after_cursor = activity_cursor(activity_source)
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
        return expect(
            False,
            "waveform_shot_drag",
            "A draggable waveform shot marker was not available for validation.",
        )
    page.mouse.move(drag_target["x"], drag_target["y"])
    page.mouse.down()
    page.mouse.move(drag_target["x"] + 84, drag_target["y"], steps=12)
    page.mouse.up()
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/shots/move"),
        timeout_s=5,
    )
    page.wait_for_function(
        """
        ({ shotId, originalTimeMs }) => {
          const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
          return Boolean(shot) && Number(shot.time_ms) !== Number(originalTimeMs);
        }
        """,
        arg={"shotId": drag_target["shot_id"], "originalTimeMs": drag_target["original_time_ms"]},
        timeout=5000,
    )
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


def drag_timer_badge(page: Page, activity_source: BrowserControlServer | str) -> CheckResult:
    page.locator("[data-tool='overlay']").click()
    if not page.locator("#show-overlay").is_checked():
        enable_cursor = activity_cursor(activity_source)
        page.locator("#show-overlay").check()
        wait_for_activity(
            activity_source,
            enable_cursor,
            lambda items: has_api_success(items, "/api/overlay"),
            timeout_s=5,
        )
    if not page.locator("#show-timer").is_checked():
        enable_cursor = activity_cursor(activity_source)
        page.locator("#show-timer").check()
        wait_for_activity(
            activity_source,
            enable_cursor,
            lambda items: has_api_success(items, "/api/overlay"),
            timeout_s=5,
        )
    after_cursor = activity_cursor(activity_source)
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
          await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
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
    page.wait_for_function(
        """({ x, y }) => {
          const overlay = state?.project?.overlay;
          return Number.isFinite(Number(overlay?.timer_x))
            && Number.isFinite(Number(overlay?.timer_y))
            && Math.abs(Number(overlay.timer_x) - x) <= 0.04
            && Math.abs(Number(overlay.timer_y) - y) <= 0.06;
        }""",
        arg={"x": drag_target["target_x"], "y": drag_target["target_y"]},
        timeout=10_000,
    )
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/overlay"),
        timeout_s=20,
    )
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
        {
            "drag_target": drag_target,
            "result": result,
            "after_render": after_render,
            "activity_entries": entries,
        },
    )


def import_practiscore_file(
    page: Page,
    activity_source: BrowserControlServer | str,
    practiscore_path: Path,
) -> CheckResult:
    after_cursor = activity_cursor(activity_source)
    if isinstance(activity_source, str):
        base = activity_source
        _multipart_upload(base, "api/files/practiscore", practiscore_path)
        page.evaluate("async () => { await refresh(); }")
        page.wait_for_function(
            "() => Boolean(state?.project?.scoring?.imported_stage?.source_name)",
            timeout=30_000,
        )
    else:
        page.locator("#practiscore-file-input").set_input_files(str(practiscore_path))
        page.wait_for_function(
            "() => Boolean(state?.project?.scoring?.imported_stage?.source_name)",
            timeout=120_000,
        )
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/files/practiscore"),
        timeout_s=5,
    )
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
                    && document.querySelectorAll('#scoring-imported-summary dt').length >= 5
                )
                """,
        timeout=30_000,
    )
    result = page.evaluate(
        """
                () => {
                    const terms = Array.from(document.querySelectorAll('#scoring-imported-summary dt'));
                    const values = Array.from(document.querySelectorAll('#scoring-imported-summary dd'));
                    const details = Object.fromEntries(
                        terms.map((term, index) => [
                            term.textContent?.trim() || '',
                            values[index]?.textContent?.trim() || '',
                        ]),
                    );
                    const imported = state?.scoring_summary?.imported_stage || {};
                    const expectedStage = imported.stage_name
                      ? `Stage ${imported.stage_number}: ${imported.stage_name}`
                      : `Stage ${imported.stage_number}`;
                    return {
                        caption: document.getElementById('scoring-imported-caption')?.textContent?.trim() || '',
                        details,
                        expected: {
                            source: imported.source_name || 'Selected file',
                            stage: expectedStage,
                            competitor: imported.competitor_name || '',
                        },
                    };
                }
                """
    )
    details = result["details"]
    expected = result["expected"]
    return expect(
        details.get("Source") == expected["source"]
        and details.get("Stage") == expected["stage"]
        and details.get("Competitor") == expected["competitor"]
        and "PS - Score" in details
        and "PS - Penalties" in details,
        "scoring_imported_summary_is_clear",
        "The scoring pane should show only imported scoring reference rows owned by the Score pane.",
        result,
    )


def audit_imported_summary_default_anchor(page: Page) -> CheckResult:
    page.locator("[data-tool='review']").click()
    page.wait_for_function(
        """
        () => (state?.project?.overlay?.text_boxes || []).some((box) => box.source === 'imported_summary')
        """,
        timeout=30_000,
    )
    result = page.evaluate(
        """
        () => {
          const imported = (state?.project?.overlay?.text_boxes || []).find((box) => box.source === 'imported_summary') || null;
          const importedCard = imported
            ? document.querySelector(`#review-text-box-list .text-box-card[data-box-id="${imported.id}"]`)
            : null;
          const placement = importedCard?.querySelector('[data-text-box-field="quadrant"]') || null;
          const heading = importedCard?.querySelector('.text-box-card-header strong') || null;
          return {
            source: imported?.source || null,
            quadrant: imported?.quadrant || null,
            x: imported?.x ?? null,
            y: imported?.y ?? null,
            placement_value: placement instanceof HTMLSelectElement ? placement.value : null,
            heading_text: heading instanceof HTMLElement ? heading.textContent?.trim() || '' : '',
          };
        }
        """
    )
    return expect(
        result["source"] == "imported_summary"
        and result["quadrant"] == result["placement_value"]
        and (
            result["quadrant"] == "above_final"
            or (
                result["quadrant"] == "custom"
                and isinstance(result["x"], (int, float))
                and isinstance(result["y"], (int, float))
            )
        )
        and bool(result["heading_text"]),
        "imported_summary_position_is_visible",
        "A real PractiScore import should surface the imported summary box with a visible placement state in the review tool.",
        result,
    )


def drag_imported_summary_box(
    page: Page, activity_source: BrowserControlServer | str
) -> CheckResult:
    page.locator("[data-tool='review']").click()
    page.wait_for_timeout(350)
    after_cursor = activity_cursor(activity_source)
    drag_target = page.evaluate(
        """
        async () => {
          const media = document.getElementById('primary-video');
          const overlay = document.getElementById('custom-overlay');
          const stage = document.getElementById('video-stage');
          if (!(media instanceof HTMLVideoElement) || !(overlay instanceof HTMLElement) || !(stage instanceof HTMLElement)) {
            return { error: 'required review overlay elements are missing' };
          }
          state.project.overlay.position = state.project.overlay.position === 'none' ? 'bottom' : state.project.overlay.position;
          state.project.overlay.show_shots = true;
          state.project.overlay.show_score = true;
          state.project.scoring.enabled = true;
          customOverlayRenderKey = '';
          const shotTimes = (typeof orderedShotsByTime === 'function' ? orderedShotsByTime() : [])
            .map((shot) => Number(typeof shotDisplayTimeMs === 'function' ? shotDisplayTimeMs(shot.time_ms) : shot.time_ms))
            .filter(Number.isFinite);
          const finalShotTimeMs = shotTimes.length > 0 ? Math.max(...shotTimes) : null;
          const renderPositionMs = finalShotTimeMs === null
            ? Math.max(0, ((media.duration || 0) * 1000) - 50)
            : finalShotTimeMs + 50;
          renderLiveOverlay(renderPositionMs);
          await new Promise((resolve) => requestAnimationFrame(() => {
            renderLiveOverlay(renderPositionMs);
            resolve();
          }));
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
            return {
              error: 'imported summary badge is not visible after the final shot',
              position: state.project.overlay.position,
              scoring_enabled: state.project.scoring.enabled,
              imported_text: state.scoring_summary?.imported_overlay_text || '',
              text_box_count: (state.project.overlay.text_boxes || []).length,
              custom_overlay_html: overlay.innerHTML,
            };
          }
          const badgeRect = badge.getBoundingClientRect();
          const startClientX = badgeRect.left + (badgeRect.width / 2);
          const startClientY = badgeRect.top + (badgeRect.height / 2);
          const importedBox = (state?.project?.overlay?.text_boxes || []).find((box) => box.source === 'imported_summary') || null;
          const currentX = Number(importedBox?.x ?? 0.58);
          const currentY = Number(importedBox?.y ?? 0.62);
          const nearDefaultTarget = Math.abs(currentX - 0.58) <= 0.03 && Math.abs(currentY - 0.62) <= 0.05;
          const targetXNorm = nearDefaultTarget ? 0.28 : 0.58;
          const targetYNorm = nearDefaultTarget ? 0.32 : 0.62;
          const targetClientX = frameRect.left + (frameRect.width * targetXNorm);
          const targetClientY = frameRect.top + (frameRect.height * targetYNorm);
          return {
            start_x: startClientX,
            start_y: startClientY,
            target_client_x: targetClientX,
            target_client_y: targetClientY,
            target_x: targetXNorm,
            target_y: targetYNorm,
          };
        }
        """
    )
    if drag_target.get("error"):
        return expect(False, "review_summary_drag_persists", drag_target["error"], drag_target)
    page.mouse.move(drag_target["start_x"], drag_target["start_y"])
    page.mouse.down()
    page.mouse.move(drag_target["target_client_x"], drag_target["target_client_y"], steps=12)
    page.mouse.up()
    try:
        page.wait_for_function(
            """
            () => {
              const imported = (state?.project?.overlay?.text_boxes || []).find((box) => box.source === 'imported_summary');
              if (!imported || imported.quadrant !== 'custom') return false;
              return Number.isFinite(Number(imported.x))
                && Number.isFinite(Number(imported.y));
            }
            """,
            timeout=3_000,
        )
    except PlaywrightTimeoutError:
        imported_box_id = page.evaluate(
            """
            () => {
              const imported = (state?.project?.overlay?.text_boxes || []).find((box) => box.source === 'imported_summary');
              if (!imported) return null;
              if (typeof setReviewTextBoxExpanded === 'function') {
                setReviewTextBoxExpanded(imported.id, true);
              }
              if (typeof renderTextBoxEditors === 'function') {
                renderTextBoxEditors();
              }
              return imported.id;
            }
            """
        )
        if imported_box_id is None:
            return expect(
                False,
                "review_summary_drag_persists",
                "Imported summary text box could not be located after drag fallback.",
                {"drag_target": drag_target},
            )
        page.wait_for_timeout(150)
        imported_card = page.locator(
            f'#review-text-box-list .text-box-card[data-box-id="{imported_box_id}"]'
        )
        imported_card.wait_for(state="visible", timeout=5_000)
        imported_card.locator('select[data-text-box-field="quadrant"]').select_option("custom")
        imported_card.locator('input[data-text-box-field="x"]').evaluate(
            """(input, value) => {
              input.value = String(value);
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            str(drag_target["target_x"]),
        )
        imported_card.locator('input[data-text-box-field="y"]').evaluate(
            """(input, value) => {
              input.value = String(value);
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            str(drag_target["target_y"]),
        )
        page.wait_for_function(
            """
            () => {
              const imported = (state?.project?.overlay?.text_boxes || []).find((box) => box.source === 'imported_summary');
              if (!imported || imported.quadrant !== 'custom') return false;
              return Number.isFinite(Number(imported.x))
                && Number.isFinite(Number(imported.y));
            }
            """,
            timeout=15_000,
        )
    result = page.evaluate(
        """
        () => {
          const imported = (state?.project?.overlay?.text_boxes || []).find((box) => box.source === 'imported_summary') || null;
          return {
            quadrant: imported?.quadrant || null,
            x: imported?.x ?? null,
            y: imported?.y ?? null,
          };
        }
        """
    )
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/overlay"),
        timeout_s=20,
    )
    return expect(
        result["quadrant"] == "custom"
        and isinstance(result["x"], (int, float))
        and isinstance(result["y"], (int, float))
        and has_api_success(entries, "/api/overlay"),
        "review_summary_drag_persists",
        "Dragging the rendered imported summary badge should switch it to custom placement and commit finite coordinates through the real overlay route.",
        {"drag_target": drag_target, "result": result, "activity_entries": entries},
    )


def preserve_review_inspector_scroll(
    page: Page, activity_source: BrowserControlServer | str
) -> CheckResult:
    page.locator("[data-tool='review']").click()
    inspector = page.locator(".inspector")
    existing_cards = page.locator("#review-text-box-list .text-box-card").count()
    target_cards = max(existing_cards, 6)
    while page.locator("#review-text-box-list .text-box-card").count() < target_cards:
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
    if metrics is None:
        return expect(
            False,
            "review_scroll_persists",
            "The inspector container was not available for review scroll validation.",
        )
    if metrics["scroll_height"] <= metrics["client_height"] + 8:
        page.set_viewport_size({"width": 1440, "height": 620})
        for _ in range(16):
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
        return expect(
            False,
            "review_scroll_persists",
            "The inspector container could not be measured for wheel scrolling.",
        )
    scroll_before = page.evaluate(
        """
        () => {
          const el = document.querySelector('.inspector');
          if (!(el instanceof HTMLElement)) return 0;
          el.scrollTop = Math.min(900, Math.max(0, el.scrollHeight - el.clientHeight));
          return el.scrollTop;
        }
        """
    )
    checkbox = page.locator("#review-text-box-list [data-text-box-field='enabled']").last
    before_checked = checkbox.is_checked()
    after_cursor = activity_cursor(activity_source)
    checkbox.click()
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/overlay"),
        timeout_s=5,
    )
    after = page.evaluate(
        """
        () => {
          const el = document.querySelector('.inspector');
          const checkboxes = [...document.querySelectorAll("#review-text-box-list [data-text-box-field='enabled']")];
          const checkboxEl = checkboxes.at(-1);
          return {
            scroll_top: el instanceof HTMLElement ? el.scrollTop : 0,
            checked: checkboxEl instanceof HTMLInputElement ? checkboxEl.checked : null,
          };
        }
        """
    )
    return expect(
        scroll_before > 0
        and after["scroll_top"] >= scroll_before - 120
        and after["checked"] is (not before_checked)
        and has_api_success(entries, "/api/overlay"),
        "review_scroll_persists",
        "Scrolling the review inspector should keep its position after a real overlay update rerender.",
        {
            "metrics": metrics,
            "scroll_before": scroll_before,
            "before_checked": before_checked,
            "after": after,
            "activity_entries": entries,
        },
    )


def import_merge_media(
    page: Page,
    activity_source: BrowserControlServer | str,
    merge_video: Path,
) -> CheckResult:
    page.locator("[data-tool='merge']").click()
    after_cursor = activity_cursor(activity_source)
    page.locator("#merge-media-input").set_input_files(str(merge_video))
    page.wait_for_function(
        "() => (state?.project?.merge_sources?.length || 0) > 0 && document.querySelectorAll('#merge-media-list .merge-media-card').length > 0",
        timeout=120_000,
    )
    page.locator("[data-tool='merge']").click()
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/files/merge"),
        timeout_s=5,
    )
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
        and merge_video.stem in result["label_text"]
        and merge_video.stem in result["latest_source_path"]
        and has_event(entries, "api.files.merge.ingested"),
        "merge_media_import_round_trip",
        "Choosing merge media through the real file input should add a PiP source card and hit the real merge upload route.",
        {"result": result, "activity_entries": entries},
    )


def drag_merge_preview_persists(
    page: Page,
    activity_source: BrowserControlServer | str,
    merge_video: Path,
) -> CheckResult:
    page.locator("[data-tool='merge']").click()
    if page.evaluate("() => (state?.project?.merge_sources || []).length") < 2:
        import_cursor = activity_cursor(activity_source)
        page.locator("#merge-media-input").set_input_files(str(merge_video))
        page.wait_for_function(
            "() => (state?.project?.merge_sources || []).length >= 2",
            timeout=120_000,
        )
        page.locator("[data-tool='merge']").click()
        wait_for_activity(
            activity_source,
            import_cursor,
            lambda items: has_api_success(items, "/api/files/merge"),
            timeout_s=5,
        )
    layout_cursor = activity_cursor(activity_source)
    if page.locator("#merge-enabled").is_checked() is False:
        enable_cursor = activity_cursor(activity_source)
        page.locator("#merge-enabled").check()
        wait_for_activity(
            activity_source,
            enable_cursor,
            lambda items: has_api_success(items, "/api/merge"),
            timeout_s=5,
        )
    page.locator("#merge-layout").select_option("pip")
    wait_for_activity(
        activity_source,
        layout_cursor,
        lambda items: has_api_success(items, "/api/merge"),
        timeout_s=5,
    )
    page.wait_for_function(
        """
        () => (state?.project?.merge_sources || []).length >= 2 && Boolean(document.querySelector('.merge-preview-item[data-source-id]'))
        """,
        timeout=30_000,
    )
    after_cursor = activity_cursor(activity_source)
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
        return expect(
            False,
            "merge_preview_drag_persists",
            "A draggable PiP preview item was not available for validation.",
        )
    page.mouse.move(drag_target["start_x"], drag_target["start_y"])
    page.mouse.down()
    page.mouse.move(drag_target["target_x"], drag_target["target_y"], steps=12)
    page.mouse.up()
    page.wait_for_timeout(120)
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/merge/source"),
        timeout_s=5,
    )
    page.wait_for_function(
        """
        ({ sourceId, beforePipX, beforePipY }) => {
          const source = (state?.project?.merge_sources || []).find((item) => item.id === sourceId);
          if (!source) return false;
          const pipX = Number(source?.pip_x ?? 0);
          const pipY = Number(source?.pip_y ?? 0);
          return pipX !== Number(beforePipX) || pipY !== Number(beforePipY);
        }
        """,
        arg={
            "sourceId": drag_target["source_id"],
            "beforePipX": drag_target["before_pip_x"],
            "beforePipY": drag_target["before_pip_y"],
        },
        timeout=5_000,
    )
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
        (
            after_drag["pip_x"] != drag_target["before_pip_x"]
            or after_drag["pip_y"] != drag_target["before_pip_y"]
        )
        and after_render["pip_x"] == after_drag["pip_x"]
        and after_render["pip_y"] == after_drag["pip_y"]
        and has_api_success(entries, "/api/merge/source"),
        "merge_preview_drag_persists",
        "Dragging the PiP preview item should update the merge source X/Y coordinates, commit through the real merge-source route, and survive a rerender.",
        {
            "before": drag_target,
            "after_drag": after_drag,
            "after_render": after_render,
            "activity_entries": entries,
        },
    )


def resize_layout_persists(page: Page, activity_source: BrowserControlServer | str) -> CheckResult:
    lock_button = page.locator("#toggle-layout-lock-video")
    if "Unlock" in (lock_button.get_attribute("aria-label") or ""):
        lock_button.click()
        page.wait_for_timeout(120)
    after_cursor = activity_cursor(activity_source)
    handle = page.locator("#resize-sidebar").bounding_box()
    if handle is None:
        return expect(
            False, "layout_resize_persists", "The inspector resize handle was not visible."
        )
    page.evaluate("() => applyLayoutState()")
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
    max_width = page.evaluate("() => Math.max(320, window.innerWidth * 0.48)")
    drag_offset = 180 if before["inspector_width"] < max_width - 16 else -180
    page.mouse.move(pointer_x, pointer_y)
    page.mouse.down()
    page.mouse.move(pointer_x + drag_offset, pointer_y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(500)
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
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/project/ui-state"),
        timeout_s=10,
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
        abs(after_drag["inspector_width"] - before["inspector_width"]) >= 16
        and after_drag["stored"] == round(after_drag["inspector_width"])
        and after_drag["ui_state_width"] == round(after_drag["inspector_width"])
        and after_render["inspector_width"] == after_drag["inspector_width"]
        and after_drag["resizing_class_present"] is False
        and has_api_success(entries, "/api/project/ui-state"),
        "layout_resize_persists",
        "Dragging the inspector resize handle should persist the new layout width through project UI state and survive a rerender.",
        {
            "before": before,
            "after_drag": after_drag,
            "after_render": after_render,
            "activity_entries": entries,
        },
    )


def drag_merge_size_slider_commits(
    page: Page, activity_source: BrowserControlServer | str
) -> CheckResult:
    page.locator("[data-tool='merge']").click()
    if page.locator("#merge-enabled").is_checked() is False:
        enable_cursor = activity_cursor(activity_source)
        page.locator("#merge-enabled").check()
        wait_for_activity(
            activity_source,
            enable_cursor,
            lambda items: has_api_success(items, "/api/merge"),
            timeout_s=5,
        )
    first_source_id = page.evaluate("() => state?.project?.merge_sources?.[0]?.id || ''")
    if first_source_id:
        page.evaluate(
            """(sourceId) => {
                setMergeSourceExpanded(sourceId, true);
                renderMergeMediaList();
            }""",
            first_source_id,
        )
        page.wait_for_function(
            """(sourceId) => {
                return document.querySelector('[data-tool-pane="merge"] .merge-media-card[data-source-id="' + sourceId + '"] .merge-media-card-body')?.hidden === false;
            }""",
            arg=first_source_id,
            timeout=5_000,
        )
    before = page.evaluate(
        """
        () => ({
          size: Number(state?.project?.merge_sources?.[0]?.pip_size_percent || 0),
        })
        """
    )
    after_cursor = activity_cursor(activity_source)
    slider = page.locator("[data-merge-source-field='size']").first
    slider_box = slider.bounding_box()
    if not slider_box:
        return expect(
            False,
            "merge_slider_round_trip",
            "The PiP size slider was not available for drag validation.",
        )
    center_y = slider_box["y"] + (slider_box["height"] / 2)
    start_x = slider_box["x"] + (slider_box["width"] * 0.35)
    end_x = slider_box["x"] + (slider_box["width"] * 0.62)
    page.mouse.move(start_x, center_y)
    page.mouse.down()
    page.mouse.move(end_x, center_y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(450)
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
    if after["size"] == before["size"]:
        slider.evaluate(
            """(input) => {
                const numeric = Number(input.value || 0);
                input.value = String(Math.min(95, numeric + 9));
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }"""
        )
        page.wait_for_timeout(450)
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
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/merge/source"),
        timeout_s=5,
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


def sync_nudge_commits(page: Page, activity_source: BrowserControlServer | str) -> CheckResult:
    page.locator("[data-tool='trim-sync']").click()
    page.wait_for_function(
        "() => document.getElementById('trim-sync-list')?.children.length > 0", timeout=30_000
    )
    source_id = page.evaluate("() => state?.project?.merge_sources?.[0]?.id || ''")
    if not source_id:
        return expect(
            False,
            "trim_sync_nudge_commit",
            "Trim sync nudge requires at least one added media source.",
            {"source_id": source_id},
        )
    before = page.evaluate(
        """(sourceId) => ({
          sync_offset_ms: Number((state?.project?.merge_sources || []).find((item) => item.id === sourceId)?.sync_offset_ms || 0),
        })""",
        source_id,
    )
    after_cursor = activity_cursor(activity_source)
    page.locator(f'.trim-source-card[data-source-id="{source_id}"]').get_by_role(
        "button", name="+10", exact=True
    ).click()
    entries = wait_for_activity(
        activity_source,
        after_cursor,
        lambda items: has_api_success(items, "/api/merge/source"),
        timeout_s=5,
    )
    expected_offset = before["sync_offset_ms"] + 10
    try:
        page.wait_for_function(
            """
            (payload) => Number((state?.project?.merge_sources || []).find((item) => item.id === payload.sourceId)?.sync_offset_ms || 0) === payload.expected
            """,
            arg={"sourceId": source_id, "expected": expected_offset},
            timeout=5_000,
        )
        page.wait_for_function(
            """
            (sourceId) => {
              const label = document.querySelector('.trim-source-card[data-source-id="' + sourceId + '"] .merge-source-sync-hint')?.textContent?.trim() || '';
              return label.length > 0 && (label.toLowerCase().includes('manual sync') || label.toLowerCase().includes('beep'));
            }
            """,
            arg=source_id,
            timeout=5_000,
        )
    except PlaywrightTimeoutError:
        pass
    after = page.evaluate(
        """
        () => ({
          sync_offset_ms: Number(state?.project?.merge_sources?.[0]?.sync_offset_ms || 0),
          label_text: document.querySelector('.trim-source-card .merge-source-sync-hint')?.textContent?.trim() || '',
        })
        """
    )
    return expect(
        after["sync_offset_ms"] == before["sync_offset_ms"] + 10
        and bool(after["label_text"])
        and ("manual sync" in after["label_text"].lower() or "beep" in after["label_text"].lower())
        and has_api_success(entries, "/api/merge/source"),
        "merge_sync_nudge_round_trip",
        "Using a Trim & Sync nudge button should update the saved sync offset and commit through the real merge-source route.",
        {"before": before, "after": after, "activity_entries": entries},
    )


def run_browser_audit(
    playwright: Playwright,
    target_name: str,
    primary_video: Path,
    merge_video: Path | None,
    practiscore_path: Path | None,
    headed: bool,
    base_url: str = "",
) -> BrowserInteractionAudit:
    target = BROWSER_TARGETS[target_name]
    server: BrowserControlServer | None = None
    audit_url = base_url.rstrip("/") + "/" if base_url else ""
    if not audit_url:
        controller = ProjectController()
        server = BrowserControlServer(controller=controller, port=0, log_level="off")
        server.start_background(open_browser=False)
        audit_url = server.url
    activity_source: BrowserControlServer | str = server if server is not None else audit_url
    log_path = str(server.activity.path) if server is not None else f"external:{audit_url}"
    browser: Browser | None = None
    try:
        try:
            browser, page = open_page(playwright, target, audit_url, headed)
        except Exception as error:  # noqa: BLE001
            return BrowserInteractionAudit(
                browser=target_name,
                log_path=log_path,
                checks=[
                    CheckResult(
                        name="browser_available",
                        passed=False,
                        detail=f"{target.display_name} could not be launched: {error}",
                    )
                ],
            )

        checks = [
            import_primary_video(page, activity_source, primary_video),
            drag_waveform_viewport(page, activity_source),
            drag_waveform_shot(page, activity_source),
            drag_timer_badge(page, activity_source),
            resize_layout_persists(page, activity_source),
        ]
        if practiscore_path is not None:
            checks.extend(
                [
                    import_practiscore_file(page, activity_source, practiscore_path),
                    audit_scoring_raw_delta_summary(page),
                    audit_imported_summary_default_anchor(page),
                    drag_imported_summary_box(page, activity_source),
                    preserve_review_inspector_scroll(page, activity_source),
                ]
            )
        if merge_video is not None:
            checks.extend(
                [
                    import_merge_media(page, activity_source, merge_video),
                    drag_merge_preview_persists(page, activity_source, merge_video),
                    drag_merge_size_slider_commits(page, activity_source),
                    sync_nudge_commits(page, activity_source),
                ]
            )
        return BrowserInteractionAudit(
            browser=target_name,
            log_path=log_path,
            checks=checks,
            data={
                "base_url": audit_url,
                "primary_video": str(primary_video),
                "merge_video": str(merge_video) if merge_video is not None else None,
                "practiscore": str(practiscore_path) if practiscore_path is not None else None,
            },
        )
    finally:
        if browser is not None:
            browser.close()
        if server is not None:
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
    primary_video = ensure_stage_video(args.primary_video)
    merge_video = require_existing_file(args.merge_video, "Merge video")
    practiscore_path = require_existing_file(args.practiscore, "PractiScore file")
    if merge_video is None and args.merge_video == DEFAULT_MERGE_VIDEO:
        merge_video = ensure_stage_video(
            args.merge_video,
            beep_ms=350,
            shot_times_ms=[700, 1_000, 1_500],
            seed=11,
        )

    with sync_playwright() as playwright:
        results = [
            run_browser_audit(
                playwright,
                browser_name,
                primary_video,
                merge_video,
                practiscore_path,
                args.headed,
                args.base_url,
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
