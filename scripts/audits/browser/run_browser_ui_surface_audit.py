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
    page.wait_for_selector("#primary-file-input", state="attached")


def import_primary_video(page: Page, primary_video: Path) -> None:
    show_project_tool(page)
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_path = str(primary_video.parent / "browser-audit.ssproj")
        page.evaluate(
            f"""async () => {{
                await callApi("/api/project/new", {{}});
                await callApi("/api/project/save", {{ path: {json.dumps(project_path)} }});
            }}"""
        )
        page.wait_for_function("() => Boolean(state?.project?.path)")
    page.locator("#primary-file-input").set_input_files(str(primary_video))
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


def audit_project_practiscore_context(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    page.locator("[data-tool='project']").click()
    result = page.evaluate(
        """
        async () => {
          state.practiscore_options = {
            source_name: "local-idpa.csv",
            detected_match_type: "idpa",
            stage_numbers: [4, 5],
            competitors: [
              { name: "John Klockenkemper", place: 6 },
              { name: "Jane Doe", place: 2 },
              { name: "Jane Doe", place: 7 },
            ],
          };
          state.project.scoring.match_type = "idpa";
          state.project.scoring.stage_number = 4;
          state.project.scoring.competitor_name = "John Klockenkemper";
          state.project.scoring.competitor_place = 6;
          state.scoring_summary = {
            ...state.scoring_summary,
            enabled: true,
            display_label: "Final",
            display_value: "24.87",
            raw_seconds: 17.87,
            raw_delta_seconds: -0.01,
            official_raw_seconds: 17.87,
            official_final_time: 24.88,
            imported_stage: {
              source_name: "local-idpa.csv",
              match_type: "idpa",
              stage_number: 4,
              competitor_name: "John Klockenkemper",
              competitor_place: 6,
              raw_seconds: 17.87,
              final_time: 24.88,
            },
          };
          state.metrics.scoring_summary = state.scoring_summary;
          setActiveTool("project", { collapseExpandedLayout: false, persistUiState: false });
          render();
          await new Promise((resolve) => window.setTimeout(resolve, 100));

          const matchType = document.getElementById("match-type");
          if (matchType) matchType.value = "idpa";
          renderPractiScoreOptionLists({
            stage_number: 4,
            competitor_name: "John Klockenkemper",
            competitor_place: 6,
          });
          renderPractiScoreSummaries();
          await new Promise((resolve) => window.setTimeout(resolve, 50));

          const stageSelect = document.getElementById("match-stage-number");
          const nameSelect = document.getElementById("match-competitor-name");
          const placeSelect = document.getElementById("match-competitor-place");
          nameSelect.value = "John Klockenkemper";
          syncPractiScoreSelectionFields("name");
          const uniquePlace = placeSelect.value;
          placeSelect.value = "2";
          syncPractiScoreSelectionFields("place");
          const duplicateName = nameSelect.value;

          return {
            status: document.getElementById("practiscore-status")?.textContent?.trim() || "",
            summary_terms: Array.from(document.querySelectorAll("#practiscore-import-summary dt")).map((node) => node.textContent.trim()),
            summary_values: Array.from(document.querySelectorAll("#practiscore-import-summary dd")).map((node) => node.textContent.trim()),
            match_type: document.getElementById("match-type")?.value || "",
            stage_options: Array.from(stageSelect?.options || []).map((node) => node.value).filter(Boolean),
            competitor_options: Array.from(nameSelect?.options || []).map((node) => node.value).filter(Boolean),
            place_options: Array.from(placeSelect?.options || []).map((node) => node.value).filter(Boolean),
            unique_place_after_name: uniquePlace,
            duplicate_name_after_place: duplicateName,
            primary_video_path: document.getElementById("primary-file-path")?.value || "",
            project_path_placeholder: document.getElementById("project-path")?.placeholder || "",
          };
        }
        """
    )
    return expect(
        result["status"] == "IDPA Stage 4 imported"
        and result["summary_terms"] == ["Source File", "Match Type", "Official Raw", "Video Raw", "Raw Delta", "Final", "Official Final"]
        and result["summary_values"][:2] == ["local-idpa.csv", "IDPA"]
        and result["match_type"] == "idpa"
        and result["stage_options"] == ["4", "5"]
        and "John Klockenkemper" in result["competitor_options"]
        and "Jane Doe" in result["competitor_options"]
        and set(result["place_options"]) == {"2", "6", "7"}
        and result["unique_place_after_name"] == "6"
        and result["duplicate_name_after_place"] == "Jane Doe"
        and result["primary_video_path"]
        and "splitshot" in result["project_path_placeholder"].lower(),
        "project_practiscore_context_is_consistent",
        "Project should show imported PractiScore context clearly and keep competitor/place selection synchronized.",
        result,
    )


def audit_popup_card_interactions(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    page.locator("[data-tool='markers']").click()
    page.locator("#popup-import-shots").click()
    page.wait_for_function(
        "() => document.querySelectorAll('.popup-marker-row').length > 0 && (state?.project?.popups || []).length > 0",
        timeout=30_000,
    )
    page.locator(".popup-marker-row .popup-marker-select").first.click()
    page.wait_for_timeout(250)
    card_click = page.evaluate(
        """
        () => {
          const row = document.querySelector(".popup-marker-row.selected");
          const id = row?.dataset.popupId;
          const bubble = popupBubbles().find((item) => item.id === id);
          const overlayBubble = document.querySelector(`#popup-overlay [data-popup-id="${id}"]`);
          return {
            id,
            selected: selectedPopupBubbleId === id,
            overlay_visible: Boolean(overlayBubble),
            current_ms: Math.round((document.getElementById("primary-video")?.currentTime || 0) * 1000),
            expected_ms: popupBubbleSeekTimeMs(bubble),
          };
        }
        """
    )
    marker_shell = page.evaluate(
        """
        () => {
          const rows = Array.from(document.querySelectorAll("#popup-marker-list .popup-marker-row[data-popup-id]"));
          const selected = document.querySelector("#popup-marker-list .popup-marker-row.selected");
          const filter = document.querySelector("#popup-filter");
          return {
            row_count: rows.length,
            selected_id: selected?.dataset.popupId || "",
            filter_value: filter?.value || "",
            summary_text: document.querySelector("#popup-authoring-summary")?.textContent || "",
            pane_status: document.querySelector("#popup-pane-status")?.textContent || "",
            list_status: document.querySelector("#popup-list-status")?.textContent || "",
            selected_summary: document.querySelector("#popup-selected-summary")?.textContent || "",
          };
        }
        """
    )
    page.locator("#popup-next-compact").click()
    page.wait_for_timeout(250)
    next_control = page.evaluate(
        """
        () => {
          const list = document.querySelector("#popup-marker-list");
          const listRect = list?.getBoundingClientRect();
          const selectedCard = document.querySelector(".popup-marker-row.selected");
          const cardRect = selectedCard?.getBoundingClientRect();
          const bubble = popupBubbles().find((item) => item.id === selectedPopupBubbleId);
          return {
            selected_id: selectedPopupBubbleId,
            selected_card_id: selectedCard?.dataset.popupId || "",
            current_ms: Math.round((document.getElementById("primary-video")?.currentTime || 0) * 1000),
            expected_ms: popupBubbleSeekTimeMs(bubble),
            inspector_scroll_top: Math.round(document.querySelector(".inspector")?.scrollTop || 0),
            list_scroll_top: Math.round(list?.scrollTop || 0),
            list_scrollable: Boolean(list && list.scrollHeight > list.clientHeight + 2),
            selected_card_top: listRect && cardRect ? Math.round(cardRect.top - listRect.top) : null,
            selected_card_bottom: listRect && cardRect ? Math.round(cardRect.bottom - listRect.top) : null,
            list_client_height: Math.round(list?.clientHeight || 0),
          };
        }
        """
    )
    page.locator("#popup-edit-selected").click()
    page.wait_for_selector("#markers-workbench-editor .popup-bubble-card")
    page.wait_for_timeout(150)
    opened = page.evaluate(
        """
        () => {
          const card = document.querySelector("#markers-workbench-editor .popup-bubble-card");
          const id = card?.dataset.popupId;
          const fields = Array.from(card.querySelectorAll(".popup-style-card .color-field"))
            .map((field) => field.getBoundingClientRect());
          const hexes = Array.from(card.querySelectorAll(".popup-style-card .color-hex-input"))
            .map((field) => field.getBoundingClientRect());
          return {
            selected: selectedPopupBubbleId === id,
            workbench_visible: document.getElementById("markers-workbench")?.hidden === false,
            body_visible: card?.querySelector(".text-box-card-body")?.hidden === false,
            color_field_count: fields.length,
            color_fields_same_row: fields.length >= 2 && Math.abs(fields[0].top - fields[1].top) < 3,
            hex_widths: hexes.map((rect) => Math.round(rect.width)),
          };
        }
        """
    )
    expanded_layout = page.evaluate(
        """
        () => {
          const rightEditor = document.querySelector('.popup-selected-editor-panel');
          const compactList = document.querySelector('[data-tool-pane="markers"] > .popup-list-section.popup-list-section-unified');
          const defaultsPanel = document.querySelector('#popup-authoring-panel');
          const bottomList = document.querySelector('#markers-workbench-list');
          return {
            workbench_visible: document.getElementById('markers-workbench')?.hidden === false,
            right_editor_visible: Boolean(rightEditor) && getComputedStyle(rightEditor).display !== 'none',
            compact_list_hidden: Boolean(compactList) && getComputedStyle(compactList).display === 'none',
            defaults_hidden: Boolean(defaultsPanel) && getComputedStyle(defaultsPanel).display === 'none',
            bottom_list_visible: Boolean(bottomList) && getComputedStyle(bottomList).display !== 'none',
          };
        }
        """
    )
    page.evaluate(
        """
        () => {
          const bubble = selectedPopupBubble();
          if (!bubble) return false;
          return seekPrimaryVideoToTimeMs(popupBubbleEffectiveTimeMs(bubble) + 400);
        }
        """
    )
    page.wait_for_timeout(150)
    page.locator("#markers-workbench-editor .popup-bubble-card [data-popup-field='follow_motion']").check()
    page.wait_for_timeout(150)
    page.evaluate(
        """
        () => {
          document.querySelector("#markers-workbench-editor .popup-bubble-card [data-popup-action='add_keyframe']")?.click();
        }
        """
    )
    page.wait_for_timeout(250)
    keyframes = page.evaluate(
        """
        () => {
          const card = document.querySelector("#markers-workbench-editor .popup-bubble-card");
          const dots = Array.from(document.querySelectorAll("#popup-overlay .popup-keyframe-dot"));
          const selectedDot = document.querySelector("#popup-overlay .popup-keyframe-dot.selected");
          const paths = document.querySelectorAll("#popup-overlay .popup-keyframe-path");
          const rows = card?.querySelectorAll("[data-popup-keyframe-list] .popup-motion-point-row") || [];
          return {
            follow_motion: card?.querySelector("[data-popup-field='follow_motion']")?.checked === true,
            row_count: rows.length,
            dot_count: dots.length,
            path_count: paths.length,
            selected_offset: Number(selectedDot?.dataset.popupKeyframeOffset || 0),
          };
        }
        """
    )
    closed = page.evaluate(
        """
        () => {
          const card = document.querySelector("#markers-workbench-editor .popup-bubble-card");
          const id = card?.dataset.popupId;
          return {
            selected: selectedPopupBubbleId === id,
            workbench_visible: document.getElementById("markers-workbench")?.hidden === false,
            body_visible: card?.querySelector(".text-box-card-body")?.hidden === false,
          };
        }
        """
    )
    seek_delta_ms = abs((card_click["current_ms"] or 0) - (card_click["expected_ms"] or 0))
    next_seek_delta_ms = abs((next_control["current_ms"] or 0) - (next_control["expected_ms"] or 0))
    passed = (
        card_click["selected"]
        and card_click["overlay_visible"]
        and seek_delta_ms < 300
      and marker_shell["row_count"] > 0
      and marker_shell["selected_id"] == card_click["id"]
      and marker_shell["filter_value"] == "all"
      and "shown" in marker_shell["summary_text"]
      and "enabled" in marker_shell["pane_status"]
      and "shown" in marker_shell["list_status"]
      and "Select a marker" not in marker_shell["selected_summary"]
      and expanded_layout["workbench_visible"]
      and expanded_layout["right_editor_visible"]
      and expanded_layout["compact_list_hidden"]
      and expanded_layout["defaults_hidden"]
      and expanded_layout["bottom_list_visible"]
      and next_control["selected_id"] == next_control["selected_card_id"]
        and next_seek_delta_ms < 300
        and (
            not next_control["list_scrollable"]
        or (
          next_control["selected_card_top"] is not None
          and next_control["selected_card_bottom"] is not None
          and 0 <= next_control["selected_card_top"]
          and next_control["selected_card_bottom"] <= next_control["list_client_height"] + 2
        )
        )
        and opened["selected"]
        and opened["workbench_visible"]
        and opened["body_visible"]
        and opened["color_field_count"] == 2
        and opened["color_fields_same_row"]
        and all(24 <= width <= 180 for width in opened["hex_widths"])
        and keyframes["follow_motion"]
        and keyframes["row_count"] >= 2
        and keyframes["dot_count"] >= 2
        and keyframes["path_count"] >= 1
        and keyframes["selected_offset"] >= 300
        and closed["selected"]
        and closed["workbench_visible"]
        and closed["body_visible"]
    )
    return expect(
        passed,
        "popup_card_interactions_are_stable",
      "Markers list, selected-marker editor, and motion-path controls should keep stable behavior.",
        {
            "card_click": card_click,
          "marker_shell": marker_shell,
          "expanded_layout": expanded_layout,
            "next_control": next_control,
            "opened": opened,
            "keyframes": keyframes,
            "closed": closed,
            "seek_delta_ms": seek_delta_ms,
            "next_seek_delta_ms": next_seek_delta_ms,
        },
    )


def audit_splits_waveform_selection_consistency(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    page.locator("[data-tool='timing']").click()
    setup = page.evaluate(
        """
        () => {
          setWaveformMode("select");
          render();
          const segments = state?.timing_segments || [];
          const firstIndex = Math.min(Math.max(1, 0), Math.max(0, segments.length - 1));
          const secondIndex = Math.min(Math.max(3, 0), Math.max(0, segments.length - 1));
          const table = document.getElementById("timing-table");
          const headerCount = 4;
          const stride = 4;
          const firstCell = table?.children?.[headerCount + (firstIndex * stride)];
          const firstRect = firstCell?.getBoundingClientRect();
          const shotTimeMs = (shotId) => (state?.project?.analysis?.shots || []).find((shot) => shot.id === shotId)?.time_ms || 0;
          return {
            first_shot_id: segments[firstIndex]?.shot_id || "",
            first_shot_time_ms: shotTimeMs(segments[firstIndex]?.shot_id || ""),
            second_shot_id: segments[secondIndex]?.shot_id || "",
            second_shot_time_ms: shotTimeMs(segments[secondIndex]?.shot_id || ""),
            timing_cell_x: firstRect ? firstRect.left + (firstRect.width / 2) : 0,
            timing_cell_y: firstRect ? firstRect.top + (firstRect.height / 2) : 0,
            waveform_card_index: secondIndex,
            second_shot_number: segments[secondIndex]?.shot_number || 0,
          };
        }
        """
    )
    page.mouse.move(setup["timing_cell_x"], setup["timing_cell_y"])
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(150)
    after_timing = page.evaluate(
        """
        () => ({
          selected_shot_id: selectedShotId,
          video_time_ms: Math.round((document.getElementById("primary-video")?.currentTime || 0) * 1000),
          waveform_selected_title: document.querySelector(".waveform-shot-card.selected strong")?.textContent?.trim() || "",
          timing_selected_cells: Array.from(document.querySelectorAll("#timing-table .selected")).map((node) => node.textContent?.trim() || ""),
        })
        """
    )
    waveform_target = page.evaluate(
        f"""
        () => {{
          const card = Array.from(document.querySelectorAll(".waveform-shot-card"))[{setup["waveform_card_index"]}] || null;
          card?.scrollIntoView({{ block: "center" }});
          return {{
            found: Boolean(card),
          }};
        }}
        """
    )
    if not waveform_target["found"]:
        return expect(
            False,
            "splits_waveform_selection_stays_in_sync",
            "The waveform shot card could not be located for the selection audit.",
            {"setup": setup, "waveform_target": waveform_target},
        )
    page.evaluate(
        f"""
        () => {{
          const card = Array.from(document.querySelectorAll(".waveform-shot-card"))[{setup["waveform_card_index"]}] || null;
          card?.click();
        }}
        """
    )
    page.wait_for_timeout(150)
    after_waveform = page.evaluate(
        """
        () => ({
          selected_shot_id: selectedShotId,
          video_time_ms: Math.round((document.getElementById("primary-video")?.currentTime || 0) * 1000),
          waveform_selected_title: document.querySelector(".waveform-shot-card.selected strong")?.textContent?.trim() || "",
          timing_selected_cells: Array.from(document.querySelectorAll("#timing-table .selected")).map((node) => node.textContent?.trim() || ""),
        })
        """
    )
    page.locator("[data-tool='scoring']").click()
    page.wait_for_timeout(100)
    after_score = page.evaluate(
        """
        () => ({
          selected_shot_id: selectedShotId,
          selected_score_row_title: document.querySelector(".scoring-shot-row.selected .scoring-shot-button strong")?.textContent?.trim() || "",
        })
        """
    )
    before_nudge = page.evaluate(
        f"""
        () => ({{
          time_ms: (state?.project?.analysis?.shots || []).find((shot) => shot.id === "{setup["second_shot_id"]}")?.time_ms || 0,
        }})
        """
    )
    page.locator("[data-tool='timing']").click()
    page.wait_for_timeout(100)
    page.locator('#selected-shot-panel [data-nudge="1"]').click()
    page.wait_for_timeout(250)
    after_nudge = page.evaluate(
        f"""
        () => ({{
          selected_shot_id: selectedShotId,
          time_ms: (state?.project?.analysis?.shots || []).find((shot) => shot.id === "{setup["second_shot_id"]}")?.time_ms || 0,
          waveform_selected_title: document.querySelector(".waveform-shot-card.selected strong")?.textContent?.trim() || "",
        }})
        """
    )
    return expect(
        after_timing["selected_shot_id"] == setup["first_shot_id"]
        and abs(after_timing["video_time_ms"] - setup["first_shot_time_ms"]) < 300
        and after_timing["waveform_selected_title"]
        and after_timing["timing_selected_cells"]
        and after_waveform["selected_shot_id"] == setup["second_shot_id"]
        and abs(after_waveform["video_time_ms"] - setup["second_shot_time_ms"]) < 300
        and after_waveform["waveform_selected_title"]
        and after_waveform["timing_selected_cells"]
        and after_score["selected_shot_id"] == setup["second_shot_id"]
        and str(setup["second_shot_number"]) in after_score["selected_score_row_title"]
        and after_nudge["selected_shot_id"] == setup["second_shot_id"]
        and after_nudge["time_ms"] - before_nudge["time_ms"] == 1,
        "splits_waveform_selection_stays_in_sync",
        "Timing table, waveform cards, scoring selection, and nudges should stay synchronized around the selected shot.",
        {
            "setup": setup,
            "after_timing": after_timing,
            "after_waveform": after_waveform,
            "after_score": after_score,
            "before_nudge": before_nudge,
            "after_nudge": after_nudge,
        },
    )


def audit_review_locked_text_box_drag_moves_stack(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    page.locator("[data-tool='review']").click()
    setup = page.evaluate(
        """
        async () => {
          const video = document.getElementById("primary-video");
          const shots = state?.project?.analysis?.shots || [];
          const lastShot = shots.at(-1);
          if (lastShot && video instanceof HTMLVideoElement) {
            video.currentTime = Math.max(0, (lastShot.time_ms + 100) / 1000);
            await new Promise((resolve) => window.setTimeout(resolve, 100));
          }
          state.project.overlay.position = "bottom";
          state.project.overlay.show_timer = false;
          state.project.overlay.show_draw = false;
          state.project.overlay.show_shots = true;
          state.project.overlay.show_score = false;
          state.project.overlay.max_visible_shots = 3;
          state.project.overlay.shot_quadrant = "bottom_left";
          state.project.overlay.shot_direction = "right";
          state.project.overlay.custom_x = null;
          state.project.overlay.custom_y = null;
          state.project.overlay.text_boxes = [normalizeOverlayTextBox({
            id: "audit-review-lock",
            enabled: true,
            lock_to_stack: true,
            source: "manual",
            text: "Locked review",
            quadrant: "custom",
            x: 0.35,
            y: 0.35,
            background_color: "#047857",
            text_color: "#ffffff",
            opacity: 1,
            width: 180,
            height: 42,
          })];
          render();
          await callApi("/api/overlay", readOverlayPayload());
          setActiveTool("review", { collapseExpandedLayout: false, persistUiState: false });
          render();
          reviewTextBoxExpansion.set("audit-review-lock", false);
          renderTextBoxEditors();
          renderLiveOverlay();
          await new Promise((resolve) => window.setTimeout(resolve, 100));
          const badge = document.querySelector('#custom-overlay [data-text-box-id="audit-review-lock"]');
          const rect = badge?.getBoundingClientRect();
          return {
            found: Boolean(rect),
            x: rect ? rect.left + (rect.width / 2) : 0,
            y: rect ? rect.top + (rect.height / 2) : 0,
            before_quadrant: state.project.overlay.shot_quadrant,
            before_box_locked: state.project.overlay.text_boxes[0]?.lock_to_stack,
            before_box_quadrant: state.project.overlay.text_boxes[0]?.quadrant,
            before_payload_count: readOverlayPayload().text_boxes.length,
          };
        }
        """
    )
    if not setup["found"]:
        return expect(False, "review_locked_text_box_drag_moves_stack", "The locked Review text box did not render.", setup)
    page.locator('.text-box-card[data-box-id="audit-review-lock"] .text-box-card-header').dispatch_event("click")
    page.wait_for_timeout(100)
    header_click = page.evaluate(
        """
        () => ({
          expanded: isReviewTextBoxExpanded("audit-review-lock"),
          body_hidden: document.querySelector('.text-box-card[data-box-id="audit-review-lock"] .text-box-card-body')?.hidden === true,
        })
        """
    )
    page.mouse.move(setup["x"], setup["y"])
    page.mouse.down()
    page.mouse.move(setup["x"] + 96, setup["y"] - 36, steps=8)
    page.mouse.up()
    page.wait_for_timeout(100)
    result = page.evaluate(
        """
        () => ({
          shot_quadrant: state.project.overlay.shot_quadrant,
          custom_x: state.project.overlay.custom_x,
          custom_y: state.project.overlay.custom_y,
          box_locked: state.project.overlay.text_boxes[0]?.lock_to_stack,
          box_quadrant: state.project.overlay.text_boxes[0]?.quadrant,
          text_box_count: state.project.overlay.text_boxes?.length || 0,
          legacy_text: state.project.overlay.custom_box_text || "",
          last_payload_count: readOverlayPayload().text_boxes.length,
          overlay_drag_cleared: overlayBadgeDrag === null,
          text_box_drag_cleared: textBoxDrag === null,
        })
        """
    )
    return expect(
        setup["before_box_locked"] is True
        and header_click["expanded"] is False
        and header_click["body_hidden"] is True
        and result["shot_quadrant"] == "custom"
        and result["custom_x"] is not None
        and result["custom_y"] is not None
        and result["box_locked"] is True
        and result["box_quadrant"] == setup["before_box_quadrant"]
        and result["overlay_drag_cleared"]
        and result["text_box_drag_cleared"],
        "review_locked_text_box_drag_moves_stack",
        "Dragging a Review box locked to the shot stack should move the stack and keep the box locked.",
        {"setup": setup, "header_click": header_click, "after": result},
    )


def audit_overlay_and_pip_preview_interactions(page: Page, primary_video: Path) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    page.locator("[data-tool='overlay']").click()
    overlay_setup = page.evaluate(
        """
        async () => {
          state.project.overlay.position = "bottom";
          state.project.overlay.show_timer = true;
          state.project.overlay.show_draw = false;
          state.project.overlay.show_shots = true;
          state.project.overlay.show_score = false;
          state.project.overlay.max_visible_shots = 3;
          state.project.overlay.shot_quadrant = "top_left";
          state.project.overlay.shot_direction = "right";
          state.project.overlay.custom_x = null;
          state.project.overlay.custom_y = null;
          state.project.overlay.timer_lock_to_stack = true;
          render();
          await new Promise((resolve) => window.setTimeout(resolve, 100));
          const timer = document.querySelector('[data-overlay-drag="timer"]');
          const rect = timer?.getBoundingClientRect();
          return {
            found: Boolean(rect),
            x: rect ? rect.left + (rect.width / 2) : 0,
            y: rect ? rect.top + (rect.height / 2) : 0,
            before_quadrant: state.project.overlay.shot_quadrant,
            before_timer_locked: state.project.overlay.timer_lock_to_stack,
          };
        }
        """
    )
    if not overlay_setup["found"]:
        return expect(
            False,
            "overlay_and_pip_preview_interactions_are_stable",
            "Overlay timer badge did not render for locked-stack drag testing.",
            {"overlay_setup": overlay_setup},
        )
    page.mouse.move(overlay_setup["x"], overlay_setup["y"])
    page.mouse.down()
    page.mouse.move(overlay_setup["x"] + 96, overlay_setup["y"] + 40, steps=8)
    page.mouse.up()
    page.wait_for_timeout(200)
    overlay_after = page.evaluate(
        """
        () => ({
          shot_quadrant: state.project.overlay.shot_quadrant,
          custom_x: state.project.overlay.custom_x,
          custom_y: state.project.overlay.custom_y,
          timer_lock_to_stack: state.project.overlay.timer_lock_to_stack,
          drag_cleared: overlayBadgeDrag === null,
        })
        """
    )

    page.locator("[data-tool='merge']").click()
    page.locator("#merge-media-input").set_input_files(str(primary_video))
    page.wait_for_function(
        """
        () => (state?.project?.merge_sources || []).length > 0
          && document.querySelectorAll('#merge-media-list .merge-media-card').length > 0
        """,
        timeout=120_000,
    )
    wait_for_processing_bar_to_settle(page)
    page.evaluate(
        """
        async () => {
          document.getElementById("merge-enabled").checked = true;
          document.getElementById("merge-layout").value = "pip";
          syncMergePreviewStateFromControls();
          await callApi("/api/merge", readMergePayload());
          setActiveTool("merge", { collapseExpandedLayout: false, persistUiState: false });
          render();
        }
        """
    )
    page.wait_for_function(
        """
        () => state?.project?.merge?.enabled
          && state?.project?.merge?.layout === "pip"
          && document.querySelector(".merge-preview-item[data-source-id]") !== null
        """,
        timeout=30_000,
    )
    pip_setup = page.evaluate(
        """
        async () => {
          await new Promise((resolve) => window.setTimeout(resolve, 150));
          const preview = document.querySelector(".merge-preview-item[data-source-id]");
          const rect = preview?.getBoundingClientRect();
          const sourceId = preview?.dataset.sourceId || "";
          const source = (state?.project?.merge_sources || [])[0] || null;
          return {
            found: Boolean(rect),
            source_id: sourceId,
            x: rect ? rect.left + (rect.width / 2) : 0,
            y: rect ? rect.top + (rect.height / 2) : 0,
            before_pip_x: source?.pip_x ?? null,
            before_pip_y: source?.pip_y ?? null,
          };
        }
        """
    )
    if not pip_setup["found"]:
        return expect(
            False,
            "overlay_and_pip_preview_interactions_are_stable",
            "PiP preview item did not render for preview drag testing.",
            {"overlay_setup": overlay_setup, "overlay_after": overlay_after, "pip_setup": pip_setup},
        )
    page.mouse.move(pip_setup["x"], pip_setup["y"])
    page.mouse.down()
    page.mouse.move(pip_setup["x"] - 80, pip_setup["y"] - 40, steps=8)
    page.mouse.up()
    page.wait_for_timeout(350)
    pip_after = page.evaluate(
        """
        () => {
          const source = (state?.project?.merge_sources || [])[0] || null;
          const preview = document.querySelector(".merge-preview-item[data-source-id]");
          const stage = document.getElementById("video-stage");
          const previewRect = preview?.getBoundingClientRect();
          const frameRect = previewFrameClientRect(document.getElementById("primary-video"), stage) || stage?.getBoundingClientRect();
          const xControl = document.querySelector('[data-merge-source-field="x"]');
          const yControl = document.querySelector('[data-merge-source-field="y"]');
          return {
            pip_x: source?.pip_x ?? null,
            pip_y: source?.pip_y ?? null,
            x_control: xControl?.value || "",
            y_control: yControl?.value || "",
            drag_cleared: mergePreviewDrag === null,
            inside_frame: Boolean(
              previewRect
                && frameRect
                && previewRect.left >= frameRect.left - 1
                && previewRect.top >= frameRect.top - 1
                && previewRect.right <= (frameRect.left + frameRect.width) + 1
                && previewRect.bottom <= (frameRect.top + frameRect.height) + 1
            ),
          };
        }
        """
    )
    return expect(
        overlay_setup["before_timer_locked"] is True
        and overlay_after["timer_lock_to_stack"] is True
        and overlay_after["shot_quadrant"] == "custom"
        and overlay_after["custom_x"] is not None
        and overlay_after["custom_y"] is not None
        and overlay_after["drag_cleared"]
        and pip_after["drag_cleared"]
        and pip_after["inside_frame"]
        and pip_after["pip_x"] is not None
        and pip_after["pip_y"] is not None
        and (pip_after["pip_x"] != pip_setup["before_pip_x"] or pip_after["pip_y"] != pip_setup["before_pip_y"])
        and bool(pip_after["x_control"])
        and bool(pip_after["y_control"]),
        "overlay_and_pip_preview_interactions_are_stable",
        "Overlay locked-stack drags and PiP preview drags should update shared placement state without leaving stale drag state.",
        {
            "overlay_setup": overlay_setup,
            "overlay_after": overlay_after,
            "pip_setup": pip_setup,
            "pip_after": pip_after,
        },
    )


def audit_metrics_and_score_surface(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    result = page.evaluate(
        """
        async () => {
          state.project.scoring.enabled = true;
          state.project.scoring.ruleset = state.project.scoring.ruleset || "idpa_time_plus";
          state.scoring_summary = {
            ...state.scoring_summary,
            enabled: true,
            sport: "IDPA",
            ruleset_name: "IDPA Time Plus",
            mode: "time_plus",
            display_label: "Final",
            display_value: "24.87",
            raw_seconds: 17.87,
            official_raw_seconds: 17.87,
            raw_delta_seconds: -0.01,
            final_time: 24.87,
            official_final_time: 24.88,
            final_delta_seconds: -0.01,
            shot_points: 7,
            shot_penalties: 0,
            field_penalties: 0,
            total_penalties: 7,
            penalty_label: "Points Down",
            score_options: ["-0", "-1", "-3", "-5", "M", "NS"],
            imported_stage: {
              source_name: "PractiScore",
              stage_number: 4,
              competitor_name: "John Klockenkemper",
              competitor_place: 6,
            },
          };
          state.metrics.scoring_summary = state.scoring_summary;
          if (state.timing_segments?.length) {
            state.timing_segments[0].score_letter = "-0";
            state.timing_segments[0].penalty_counts = {};
          }
          setActiveTool("metrics", { collapseExpandedLayout: false, persistUiState: false });
          render();
          await new Promise((resolve) => window.setTimeout(resolve, 100));
          const trend = document.getElementById("metrics-trend-list");
          const trendStyle = window.getComputedStyle(trend);
          const trendHeaders = Array.from(trend.querySelectorAll(".head")).map((cell) => cell.textContent.trim());
          const trendCells = Array.from(trend.children).map((cell) => ({
            text: cell.textContent.trim(),
            left: cell.getBoundingClientRect().left,
            top: cell.getBoundingClientRect().top,
            width: cell.getBoundingClientRect().width,
            scrollWidth: cell.scrollWidth,
            clientWidth: cell.clientWidth,
          }));
          const firstRowTops = trendCells.slice(0, 6).map((cell) => Math.round(cell.top));
          const firstRowLefts = trendCells.slice(0, 6).map((cell) => Math.round(cell.left));
          const details = document.getElementById("metrics-score-summary");
          const detailTerms = Array.from(details.querySelectorAll("dt")).map((cell) => cell.textContent.trim());
          const detailValues = Array.from(details.querySelectorAll("dd")).map((cell) => cell.textContent.trim());
          const detailOverflow = Array.from(details.querySelectorAll("dt, dd")).filter((cell) => (
            cell.scrollWidth > cell.clientWidth + 2
          )).map((cell) => cell.textContent.trim());

          setActiveTool("scoring", { collapseExpandedLayout: false, persistUiState: false });
          render();
          await new Promise((resolve) => window.setTimeout(resolve, 100));
          const scoreRows = Array.from(document.querySelectorAll(".scoring-shot-row"));
          const secondRow = scoreRows[1] || scoreRows[0];
          const secondShotId = state.timing_segments?.[1]?.shot_id || state.timing_segments?.[0]?.shot_id || "";
          scoringShotExpansion.set(secondShotId, false);
          renderScoringShotList();
          const rowAfterRerender = Array.from(document.querySelectorAll(".scoring-shot-row"))[1] || document.querySelector(".scoring-shot-row");
          const collapsedBefore = {
            text: rowAfterRerender?.querySelector(".scoring-shot-toggle")?.textContent.trim() || "",
            hidden: rowAfterRerender?.querySelector(".scoring-shot-controls")?.hidden ?? null,
          };
          rowAfterRerender?.querySelector(".scoring-shot-toggle")?.click();
          await new Promise((resolve) => window.setTimeout(resolve, 100));
          const openedRow = Array.from(document.querySelectorAll(".scoring-shot-row"))[1] || document.querySelector(".scoring-shot-row");
          const opened = {
            text: openedRow?.querySelector(".scoring-shot-toggle")?.textContent.trim() || "",
            hidden: openedRow?.querySelector(".scoring-shot-controls")?.hidden ?? null,
            expanded: Boolean(scoringShotExpansion.get(secondShotId)),
          };
          openedRow?.querySelector(".scoring-shot-toggle")?.click();
          await new Promise((resolve) => window.setTimeout(resolve, 100));
          const closedRow = Array.from(document.querySelectorAll(".scoring-shot-row"))[1] || document.querySelector(".scoring-shot-row");
          const closed = {
            text: closedRow?.querySelector(".scoring-shot-toggle")?.textContent.trim() || "",
            hidden: closedRow?.querySelector(".scoring-shot-controls")?.hidden ?? null,
            expanded: Boolean(scoringShotExpansion.get(secondShotId)),
          };
          return {
            trend: {
              class_name: trend.className,
              display: trendStyle.display,
              columns: trendStyle.gridTemplateColumns,
              headers: trendHeaders,
              first_row_same_top: new Set(firstRowTops).size === 1,
              first_row_distinct_lefts: new Set(firstRowLefts).size === 6,
              cell_count: trendCells.length,
            },
            details: {
              terms: detailTerms,
              values: detailValues,
              overflow: detailOverflow,
              status: document.getElementById("metrics-score-status")?.textContent?.trim() || "",
            },
            score: { collapsedBefore, opened, closed },
          };
        }
        """
    )
    return expect(
        result["trend"]["display"] == "grid"
        and result["trend"]["headers"] == ["Shot", "Split", "Run", "Score", "ShotML", "Action"]
        and result["trend"]["first_row_same_top"]
        and result["trend"]["first_row_distinct_lefts"]
        and result["trend"]["cell_count"] > 6
        and result["details"]["terms"][:3] == ["Stage #", "Competitor", "Place"]
        and "Score Options" not in result["details"]["terms"]
        and "Imported" not in result["details"]["terms"]
        and "Imported Stage" not in result["details"]["terms"]
        and not result["details"]["overflow"]
        and result["score"]["opened"]["text"] == "v"
        and result["score"]["opened"]["hidden"] is False
        and result["score"]["opened"]["expanded"] is True
        and result["score"]["closed"]["text"] == ">"
        and result["score"]["closed"]["hidden"] is True
        and result["score"]["closed"]["expanded"] is False,
        "metrics_and_score_surfaces_are_consistent",
        "Metrics should use table/scoring-context layouts and Score chevrons should open and close reliably.",
        result,
    )


def audit_remaining_pane_controls(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    result = page.evaluate(
        """
        async () => {
          const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));
          const sectionState = (section) => ({
            collapsed: section?.classList.contains("collapsed") ?? null,
            toggle_text: section?.querySelector("[data-section-toggle]")?.textContent.trim() || "",
            content_hidden: Array.from(section?.children || [])
              .filter((child) => !child.classList.contains("section-header"))
              .every((child) => window.getComputedStyle(child).display === "none"),
          });

          setActiveTool("shotml", { collapseExpandedLayout: false, persistUiState: false });
          render();
          const shotmlSection = document.querySelector('[data-shotml-section="confidence_review"]');
          shotMLSectionExpansion.set("confidence_review", false);
          renderCollapsibleInspectorSections();
          const shotmlClosedBefore = sectionState(shotmlSection);
          shotmlSection?.querySelector("[data-section-toggle]")?.click();
          await wait(50);
          const shotmlOpened = sectionState(shotmlSection);
          shotmlSection?.querySelector("[data-section-toggle]")?.click();
          await wait(50);
          const shotmlClosedAfter = sectionState(shotmlSection);

          setActiveTool("merge", { collapseExpandedLayout: false, persistUiState: false });
          render();
          const pipSection = document.querySelector('[data-inspector-section="pip-defaults"]');
          setMergeSourceExpanded("pip-defaults", true);
          renderCollapsibleInspectorSections();
          const pipOpenedBefore = sectionState(pipSection);
          pipSection?.querySelector("[data-section-toggle]")?.click();
          await wait(50);
          const pipClosed = sectionState(pipSection);
          pipSection?.querySelector("[data-section-toggle]")?.click();
          await wait(50);
          const pipOpenedAfter = sectionState(pipSection);

          setActiveTool("export", { collapseExpandedLayout: false, persistUiState: false });
          render();
          document.getElementById("show-export-log")?.click();
          await wait(50);
          const modalOpened = {
            hidden: document.getElementById("export-log-modal")?.hidden ?? null,
            output_text: document.getElementById("export-log-output")?.textContent.trim() || "",
          };
          document.getElementById("close-export-log")?.click();
          await wait(50);
          const modalClosed = {
            hidden: document.getElementById("export-log-modal")?.hidden ?? null,
          };
          const inspector = document.querySelector(".inspector");
          const activePane = document.querySelector(".tool-pane.active");
          return {
            shotml: { closed_before: shotmlClosedBefore, opened: shotmlOpened, closed_after: shotmlClosedAfter },
            pip: { opened_before: pipOpenedBefore, closed: pipClosed, opened_after: pipOpenedAfter },
            export_log: { opened: modalOpened, closed: modalClosed },
            layout: {
              inspector_client_width: inspector?.clientWidth || 0,
              inspector_scroll_width: inspector?.scrollWidth || 0,
              pane_client_width: activePane?.clientWidth || 0,
              pane_scroll_width: activePane?.scrollWidth || 0,
            },
          };
        }
        """
    )
    return expect(
        result["shotml"]["closed_before"]["toggle_text"] == ">"
        and result["shotml"]["closed_before"]["content_hidden"] is True
        and result["shotml"]["opened"]["toggle_text"] == "v"
        and result["shotml"]["opened"]["collapsed"] is False
        and result["shotml"]["closed_after"]["toggle_text"] == ">"
        and result["shotml"]["closed_after"]["content_hidden"] is True
        and result["pip"]["opened_before"]["toggle_text"] == "v"
        and result["pip"]["opened_before"]["collapsed"] is False
        and result["pip"]["closed"]["toggle_text"] == ">"
        and result["pip"]["closed"]["content_hidden"] is True
        and result["pip"]["opened_after"]["toggle_text"] == "v"
        and result["pip"]["opened_after"]["collapsed"] is False
        and result["export_log"]["opened"]["hidden"] is False
        and result["export_log"]["closed"]["hidden"] is True
        and result["layout"]["inspector_scroll_width"] <= result["layout"]["inspector_client_width"] + 2
        and result["layout"]["pane_scroll_width"] <= result["layout"]["pane_client_width"] + 2,
        "remaining_pane_controls_are_stable",
        "ShotML, PiP, and Export controls should use stable chevrons/modals without resized-pane overflow.",
        result,
    )


def audit_all_panes_avoid_horizontal_overflow(page: Page) -> CheckResult:
    wait_for_processing_bar_to_settle(page)
    tools = ["project", "scoring", "timing", "shotml", "merge", "overlay", "popup", "review", "export", "metrics"]
    result = page.evaluate(
        """
        async (tools) => {
          const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));
          layoutLocked = false;
          layoutSizes.inspectorWidth = 360;
          applyLayoutState();
          const rows = [];
          for (const tool of tools) {
            setActiveTool(tool, { collapseExpandedLayout: true, persistUiState: false });
            render();
            await wait(80);
            const inspector = document.querySelector(".inspector");
            const pane = document.querySelector(`[data-tool-pane="${tool}"]`);
            rows.push({
              tool,
              inspector_client_width: inspector?.clientWidth || 0,
              inspector_scroll_width: inspector?.scrollWidth || 0,
              pane_client_width: pane?.clientWidth || 0,
              pane_scroll_width: pane?.scrollWidth || 0,
              body_scroll_width: document.documentElement.scrollWidth,
              body_client_width: document.documentElement.clientWidth,
            });
          }
          return rows;
        }
        """,
        tools,
    )
    overflowing = [
        row
        for row in result
        if row["inspector_scroll_width"] > row["inspector_client_width"] + 2
        or row["pane_scroll_width"] > row["pane_client_width"] + 2
        or row["body_scroll_width"] > row["body_client_width"] + 2
    ]
    return expect(
        not overflowing,
        "all_panes_avoid_horizontal_overflow",
        "Every inspector pane should fit the resized right panel without horizontal overflow or a permanent black gutter.",
        {"rows": result, "overflowing": overflowing},
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
            audit_project_practiscore_context(page),
            audit_waveform_drag(page),
            audit_layout_resize_persists(page),
            audit_popup_card_interactions(page),
            audit_splits_waveform_selection_consistency(page),
            audit_review_locked_text_box_drag_moves_stack(page),
            audit_overlay_and_pip_preview_interactions(page, primary_video),
            audit_metrics_and_score_surface(page),
            audit_remaining_pane_controls(page),
            audit_all_panes_avoid_horizontal_overflow(page),
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
