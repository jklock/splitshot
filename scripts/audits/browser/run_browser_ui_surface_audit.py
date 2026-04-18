from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserType, Page, Playwright, sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


ROOT = Path(__file__).resolve().parents[3]
TEST_VIDEO_DIR = ROOT / "tests" / "artifacts" / "test_video"
DEFAULT_PRIMARY_VIDEO = TEST_VIDEO_DIR / "TestVideo1.MP4"


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
class BrowserAudit:
    browser: str
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
    description="Audit SplitShot rendered UI surfaces with DOM-level smoke checks across Chromium, Chrome, Firefox, Safari-class WebKit, and Edge-aware channels via Playwright.",
    )
    parser.add_argument(
        "--browser",
        action="append",
        choices=SUPPORTED_BROWSERS,
        dest="browsers",
        help="Browser target to audit. Defaults to available Chromium, Chrome, Firefox, and Safari-class WebKit targets.",
    )
    parser.add_argument(
        "--primary-video",
        type=Path,
        default=DEFAULT_PRIMARY_VIDEO,
        help="Primary video path to import during the audit.",
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
    chrome_target = BROWSER_TARGETS["chrome"]
    edge_target = BROWSER_TARGETS["edge"]
    if chrome_target.app_path and chrome_target.app_path.exists():
        names.insert(1, "chrome")
    if edge_target.app_path and edge_target.app_path.exists():
        names.append("edge")
    return names


def expect(condition: bool, name: str, detail: str, data: dict[str, Any] | None = None) -> CheckResult:
    return CheckResult(name=name, passed=condition, detail=detail, data=data)


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


def show_project_tool(page: Page) -> None:
    page.locator("[data-tool='project']").click()
    page.wait_for_selector("#primary-file-path", state="visible")


def import_primary_video(page: Page, primary_video: Path) -> None:
    show_project_tool(page)
    page.locator("#primary-file-path").fill(str(primary_video))
    page.locator("#primary-file-path").press("Enter")
    page.wait_for_function(
        "() => (state?.project?.analysis?.shots?.length || 0) > 0",
        timeout=120_000,
    )
    page.wait_for_function(
        "() => document.getElementById('current-file')?.textContent?.trim().length > 0",
        timeout=30_000,
    )


def wait_for_processing_bar_to_settle(page: Page) -> None:
    page.wait_for_function(
        "() => document.getElementById('processing-bar')?.hidden === true",
        timeout=15_000,
    )
    page.evaluate("forceHideProcessingBar()")
    page.wait_for_timeout(400)


def audit_overlay_surfaces(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    result = page.evaluate(
        """
        async () => {
          const video = document.getElementById("primary-video");
          const stage = document.getElementById("video-stage");
          const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));
          const seekVideo = async (seconds) => {
            await new Promise((resolve) => {
              const handleSeeked = () => {
                video.removeEventListener("seeked", handleSeeked);
                resolve();
              };
              video.addEventListener("seeked", handleSeeked, { once: true });
              video.currentTime = seconds;
            });
            await wait(50);
            renderLiveOverlay();
          };
          const frameRect = () => {
            const stageRect = stage.getBoundingClientRect();
            const localRect = videoContentRect(video, stage);
            if (!localRect) {
              return {
                left: stageRect.left,
                top: stageRect.top,
                width: stageRect.width,
                height: stageRect.height,
              };
            }
            return {
              left: stageRect.left + localRect.left,
              top: stageRect.top + localRect.top,
              width: localRect.width,
              height: localRect.height,
            };
          };
          const collect = () => {
            const rect = frameRect();
            const badges = Array.from(document.querySelectorAll("#live-overlay .overlay-badge, #custom-overlay .overlay-badge")).map((badge) => {
              const badgeRect = badge.getBoundingClientRect();
              const frameRight = rect.left + rect.width;
              const frameBottom = rect.top + rect.height;
              const inside = badgeRect.left >= rect.left - 1
                && badgeRect.top >= rect.top - 1
                && badgeRect.right <= frameRight + 1
                && badgeRect.bottom <= frameBottom + 1;
              return {
                text: badge.textContent?.trim() || "",
                inside,
              };
            });
            return {
              frame: {
                left: rect.left,
                top: rect.top,
                right: rect.left + rect.width,
                bottom: rect.top + rect.height,
              },
              texts: badges.map((badge) => badge.text),
              all_inside: badges.every((badge) => badge.inside),
            };
          };

          const shots = state.project.analysis.shots || [];
          const finalShotTimeMs = shots.at(-1)?.time_ms || 0;
          state.project.merge.enabled = false;
          state.project.overlay.position = "bottom";
          state.project.overlay.show_timer = true;
          state.project.overlay.show_draw = true;
          state.project.overlay.show_shots = true;
          state.project.overlay.show_score = true;
          state.project.overlay.max_visible_shots = 3;
          state.project.overlay.custom_box_enabled = true;
          state.project.overlay.custom_box_mode = "manual";
          state.project.overlay.custom_box_text = "QA Box";
          state.project.overlay.custom_box_background_color = "#0f4c81";
          state.project.overlay.custom_box_text_color = "#ffffff";
          state.project.overlay.custom_box_quadrant = "top_right";
          state.project.overlay.custom_box_x = null;
          state.project.overlay.custom_box_y = null;
          state.project.scoring.enabled = true;
          state.scoring_summary = {
            ...state.scoring_summary,
            display_label: "Hit Factor",
            display_value: "5.75",
          };
          shots.forEach((shot, index) => {
            shot.score = { letter: index === 0 ? "A" : "C" };
          });
          render();

          const beforeFirstShotSeconds = Math.max(0, ((state.project.analysis.beep_time_ms_primary || 0) - 80) / 1000);
          await seekVideo(beforeFirstShotSeconds);
          const before = collect();

          const afterFinalShotSeconds = Math.max(0, (finalShotTimeMs + 80) / 1000);
          await seekVideo(afterFinalShotSeconds);
          const after = collect();

          return { before, after };
        }
        """
    )
    before_texts = result["before"]["texts"]
    after_texts = result["after"]["texts"]
    return expect(
        any(text.startswith("Timer ") for text in before_texts)
        and any(text.startswith("Shot ") for text in after_texts)
        and any(text.startswith("Hit Factor ") for text in after_texts)
        and "QA Box" in after_texts
        and result["before"]["all_inside"]
        and result["after"]["all_inside"],
        "overlay_elements_stay_inside_video",
      "Timer, shot, score, and custom overlay badges should render inside the live video frame.",
        result,
    )


def audit_waveform_drag(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    page.evaluate("setWaveformMode('select')")
    drag_target = page.evaluate(
        """
        () => {
          renderWaveform();
          const waveform = document.getElementById("waveform");
          const rect = waveform.getBoundingClientRect();
          const shots = state?.project?.analysis?.shots || [];
          const shot = shots[1] || shots[0];
          return {
            shot_id: shot.id,
            original_time_ms: shot.time_ms,
            x: rect.left + waveformX(shot.time_ms, rect.width),
            y: rect.top + (rect.height / 2),
          };
        }
        """
    )
    page.mouse.move(drag_target["x"], drag_target["y"])
    page.mouse.down()
    page.mouse.move(drag_target["x"] + 80, drag_target["y"], steps=8)
    page.mouse.up()
    page.wait_for_function(
        """
        ({ shotId, originalTimeMs }) => {
          const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
          return Boolean(shot)
            && shot.time_ms > originalTimeMs
            && selectedShotId === shotId
            && draggingShotId === null;
        }
        """,
          arg={"shotId": drag_target["shot_id"], "originalTimeMs": drag_target["original_time_ms"]},
        timeout=30_000,
    )
    result = page.evaluate(
        """
        ({ shotId, originalTimeMs }) => {
          const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
          return {
            selected_shot_id: selectedShotId,
            new_time_ms: shot?.time_ms || null,
            delta_ms: shot ? shot.time_ms - originalTimeMs : null,
          };
        }
        """,
        {"shotId": drag_target["shot_id"], "originalTimeMs": drag_target["original_time_ms"]},
    )
    return expect(
        result["selected_shot_id"] == drag_target["shot_id"] and (result["delta_ms"] or 0) > 0,
        "waveform_drag_moves_shot",
        "Dragging a waveform marker should move the selected shot and commit the new time through the browser UI.",
        result,
    )


def audit_layout_resize_persists(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    page.evaluate(
        """
        () => {
          layoutLocked = false;
          window.localStorage.setItem("splitshot.layoutLocked", "false");
          applyLayoutState();
        }
        """
    )
    handle = page.locator("#resize-sidebar").bounding_box()
    if handle is None:
        return expect(False, "layout_resize_persists", "The inspector resize handle was not visible.")
    before = page.evaluate(
        """
        () => ({
          inspector_width: layoutSizes.inspectorWidth,
          stored: Number(window.localStorage.getItem("splitshot.layout.inspectorWidth") || 0),
        })
        """
    )
    pointer_x = handle["x"] + (handle["width"] / 2)
    pointer_y = handle["y"] + (handle["height"] / 2)
    page.mouse.move(pointer_x, pointer_y)
    page.mouse.down()
    page.mouse.move(pointer_x - 80, pointer_y, steps=8)
    page.mouse.up()
    page.wait_for_function(
        """
        (originalWidth) => {
          const stored = Number(window.localStorage.getItem("splitshot.layout.inspectorWidth") || 0);
          return stored > 0 && stored !== Math.round(originalWidth) && !document.body.classList.contains("resizing-layout");
        }
        """,
        arg=before["inspector_width"],
        timeout=30_000,
    )
    result = page.evaluate(
        """
        () => ({
          inspector_width: layoutSizes.inspectorWidth,
          stored: Number(window.localStorage.getItem("splitshot.layout.inspectorWidth") || 0),
          css_value: getComputedStyle(document.documentElement).getPropertyValue("--inspector-width").trim(),
          layout_locked: window.localStorage.getItem("splitshot.layoutLocked"),
          resizing_class_present: document.body.classList.contains("resizing-layout"),
        })
        """
    )
    return expect(
        result["stored"] > before["stored"]
        and result["layout_locked"] == "false"
        and result["resizing_class_present"] is False,
        "layout_resize_persists",
        "Dragging the inspector resize handle should persist the new layout width and release the resize state.",
        {"before": before, "after": result},
    )


def audit_merge_file_input_change(page: Page, primary_video: Path) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    page.locator("[data-tool='merge']").click()
    page.locator("#merge-media-input").set_input_files(str(primary_video))
    page.wait_for_function(
        """
        () => document.querySelectorAll('#merge-media-list .merge-media-card').length > 0
          && (state?.project?.merge_sources || []).length > 0
        """,
        timeout=120_000,
    )
    result = page.evaluate(
        """
        () => ({
          merge_source_count: (state?.project?.merge_sources || []).length,
          items: Array.from(document.querySelectorAll("#merge-media-list .merge-media-card strong")).map((node) => node.textContent?.trim() || ""),
        })
        """
    )
    return expect(
        result["merge_source_count"] > 0
        and any(primary_video.name in item for item in result["items"])
        and len(result["items"]) == result["merge_source_count"],
        "merge_file_input_change_adds_media",
        "Setting files on the merge-media input should trigger the browser change path and update the added-media list.",
        result,
    )


def run_browser_audit(
    playwright: Playwright,
    target_name: str,
    primary_video: Path,
    headed: bool,
) -> BrowserAudit:
    target = BROWSER_TARGETS[target_name]
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, log_level="off")
    server.start_background(open_browser=False)
    browser: Browser | None = None
    try:
        try:
            browser, page = open_page(playwright, target, server.url, headed)
        except Exception as error:  # noqa: BLE001
            return BrowserAudit(
                browser=target_name,
                checks=[
                    CheckResult(
                        name="browser_available",
                        passed=False,
                        detail=f"{target.display_name} could not be launched: {error}",
                    )
                ],
            )

        import_primary_video(page, primary_video)
        checks = [
            audit_overlay_surfaces(page),
            audit_waveform_drag(page),
            audit_layout_resize_persists(page),
            audit_merge_file_input_change(page, primary_video),
        ]
        return BrowserAudit(browser=target_name, checks=checks)
    finally:
        if browser is not None:
            browser.close()
        server.shutdown()


def summarize_results(results: list[BrowserAudit]) -> str:
    lines = ["# Browser UI Surface Audit", ""]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"## {result.browser}: {status}")
        for check in result.checks:
            mark = "PASS" if check.passed else "FAIL"
            lines.append(f"- {mark} {check.name}: {check.detail}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    browsers = args.browsers or default_browser_names()
    primary_video = args.primary_video.resolve()
    if not primary_video.is_file():
        raise SystemExit(f"Primary video not found: {primary_video}")

    with sync_playwright() as playwright:
        results = [
            run_browser_audit(playwright, browser_name, primary_video, args.headed)
            for browser_name in browsers
        ]

    payload = {
        "primary_video": str(primary_video),
        "results": [
            {
                "browser": result.browser,
                "passed": result.passed,
                "checks": [asdict(check) for check in result.checks],
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
