from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = ROOT / "docs" / "screenshots"
PRIMARY_VIDEO = ROOT / "tests" / "artifacts" / "test_video" / "TestVideo1.MP4"
MERGE_VIDEO = ROOT / "tests" / "artifacts" / "test_video" / "TestVideo2.MP4"
PRACTISCORE = ROOT / "example_data" / "IDPA" / "IDPA.csv"
VIEWPORT = {"width": 1440, "height": 1024}


def wait_for_app_idle(page: Page) -> None:
    page.wait_for_function(
        "() => document.getElementById('processing-bar')?.hidden === true",
        timeout=30_000,
    )
    page.evaluate("() => window.forceHideProcessingBar?.()")
    page.wait_for_timeout(250)


def click_tool(page: Page, tool: str) -> None:
    page.evaluate(
        """
        (tool) => {
          setActiveTool(tool, { collapseExpandedLayout: false, persistUiState: false });
          render();
        }
        """,
        tool,
    )
    page.wait_for_selector(f"[data-tool-pane='{tool}'].active", timeout=30_000)
    wait_for_app_idle(page)


def set_inspector_scroll(page: Page, scroll_top: int = 0) -> None:
    page.evaluate(
        """
        (scrollTop) => {
          const inspector = document.querySelector('.inspector');
          if (inspector instanceof HTMLElement) inspector.scrollTop = scrollTop;
        }
        """,
        scroll_top,
    )
    page.wait_for_timeout(250)


def screenshot(page: Page, filename: str, scroll_top: int = 0) -> None:
    set_inspector_scroll(page, scroll_top)
    page.screenshot(path=str(SCREENSHOT_DIR / filename), full_page=False)


def open_color_picker(page: Page) -> None:
    page.evaluate(
        """
        () => {
          const button = document.querySelector('#badge-style-grid .color-swatch-button');
          if (button instanceof HTMLElement) button.click();
        }
        """
    )
    page.wait_for_selector("#color-picker-modal:not([hidden])", timeout=30_000)
    page.wait_for_timeout(250)


def open_export_log(page: Page) -> None:
    page.locator("#show-export-log").click()
    page.wait_for_selector("#export-log-modal:not([hidden])", timeout=30_000)
    page.wait_for_timeout(250)


def stabilize_pip_controls(page: Page) -> None:
    page.locator("#merge-enabled").check()
    page.locator("#merge-layout").select_option("pip")
    page.wait_for_timeout(500)
    prepare_demo_state(page)


def import_primary_video(page: Page) -> None:
    click_tool(page, "project")
    page.locator("#primary-file-path").fill(str(PRIMARY_VIDEO))
    page.locator("#primary-file-path").press("Enter")
    page.wait_for_function("() => (state?.project?.analysis?.shots?.length || 0) > 0", timeout=120_000)
    page.wait_for_function(
        """
        () => {
          const video = document.getElementById('primary-video');
          return Boolean(video && Number.isFinite(video.duration) && video.duration > 0);
        }
        """,
        timeout=30_000,
    )
    wait_for_app_idle(page)


def import_practiscore(page: Page) -> None:
    page.locator("#practiscore-file-input").set_input_files(str(PRACTISCORE))
    page.wait_for_function(
        "() => Boolean(state?.project?.scoring?.imported_stage?.source_name)",
        timeout=120_000,
    )
    wait_for_app_idle(page)


def import_merge_media(page: Page) -> None:
    click_tool(page, "merge")
    page.locator("#merge-media-input").set_input_files(str(MERGE_VIDEO))
    page.wait_for_function(
        "() => (state?.project?.merge_sources?.length || 0) > 0 && document.querySelectorAll('#merge-media-list .merge-media-card').length > 0",
        timeout=120_000,
    )
    wait_for_app_idle(page)


def prepare_demo_state(page: Page) -> None:
    page.evaluate(
        """
        () => {
          layoutLocked = false;
          layoutSizes.inspectorWidth = 530;
          layoutSizes.waveformHeight = 250;
          applyLayoutState();

          if (state?.project) {
            state.project.name = 'Stage 1 Review';
            state.project.description = 'Documentation capture with scoring, overlays, PiP, popups, and review text boxes configured.';
          }

          if (state?.project?.scoring) {
            state.project.scoring.enabled = true;
          }

          if (state?.project?.export) {
            state.project.export.output_path = '/Users/klock/splitshot/output.mp4';
            state.project.export.last_error = '';
            state.project.export.last_log = [
              'SplitShot export preview log',
              'Input: TestVideo1.MP4',
              'Overlay: timer, draw, shots, score, popups, and review boxes enabled',
              'PiP: 1 added media item, sync -2555 ms',
              'Output: /Users/klock/splitshot/output.mp4',
              'Status: ready to render'
            ].join('\\n');
          }

          if (state?.project?.merge) {
            state.project.merge.enabled = true;
            state.project.merge.layout = 'pip';
            state.project.merge.pip_size_percent = 35;
            state.project.merge.pip_x = 0.72;
            state.project.merge.pip_y = 0.68;
          }
          (state?.project?.merge_sources || []).forEach((source, index) => {
            source.pip_size_percent = index === 0 ? 35 : 28;
            source.pip_x = index === 0 ? 0.72 : 0.08;
            source.pip_y = index === 0 ? 0.68 : 0.08;
            source.opacity = 0.92;
            mergeSourceExpansion.set(sourceIdentifier(source, String(index)), true);
          });
          mergeSourceExpansion.set(PIP_DEFAULTS_SECTION_ID, true);

          const overlay = state?.project?.overlay;
          if (overlay) {
            overlay.position = 'bottom';
            overlay.badge_size = 'XL';
            overlay.style_type = 'rounded';
            overlay.spacing = 8;
            overlay.margin = 8;
            overlay.max_visible_shots = 4;
            overlay.shot_quadrant = 'bottom_left';
            overlay.shot_direction = 'right';
            overlay.show_timer = true;
            overlay.show_draw = true;
            overlay.show_shots = true;
            overlay.show_score = true;
            overlay.timer_lock_to_stack = false;
            overlay.timer_x = 0.24;
            overlay.timer_y = 0.28;
            overlay.draw_lock_to_stack = true;
            overlay.score_lock_to_stack = true;
            overlay.font_bold = true;
          }

          let boxes = overlayTextBoxes();
          if (!boxes.some((box) => box.source === 'manual')) boxes.push(buildOverlayTextBox('manual'));
          if (!boxes.some((box) => box.source === 'imported_summary')) boxes.push(buildOverlayTextBox('imported_summary'));
          boxes = boxes.map((box) => {
            if (box.source === 'manual') {
              return normalizeOverlayTextBox({
                ...box,
                enabled: true,
                text: 'Stage plan: enter low, exit hard',
                quadrant: 'top_right',
                background_color: '#111827',
                text_color: '#f9fafb',
                opacity: 0.92,
                width: 260,
                height: 0,
              });
            }
            return normalizeOverlayTextBox({
              ...box,
              enabled: true,
              source: 'imported_summary',
              quadrant: ABOVE_FINAL_TEXT_BOX_VALUE,
              background_color: '#064e3b',
              text_color: '#ecfdf5',
              opacity: 0.94,
              width: 360,
              height: 0,
            });
          });
          setLocalOverlayTextBoxes(boxes);
          boxes.forEach((box) => reviewTextBoxExpansion.set(box.id, true));

          const shots = orderedShotsByTime();
          shots.slice(0, 4).forEach((shot) => scoringShotExpansion.set(shot.id, true));
          if (shots[0]) selectedShotId = shots[0].id;

          const popupShot = shots[2] || shots[0] || null;
          const popupTime = popupShot ? shotDisplayTimeMs(popupShot.time_ms) : 2500;
          const popup = normalizePopupBubble({
            id: createPopupBubbleId(),
            name: 'Exit target callout',
            text: '-0',
            enabled: true,
            anchor_mode: popupShot ? 'shot' : 'time',
            shot_id: popupShot?.id || '',
            time_ms: popupTime,
            duration_ms: 1400,
            quadrant: 'custom',
            x: 0.58,
            y: 0.38,
            follow_motion: true,
            motion_path: [
              { offset_ms: 0, x: 0.52, y: 0.34 },
              { offset_ms: 450, x: 0.58, y: 0.38 },
              { offset_ms: 900, x: 0.64, y: 0.43 },
            ],
            background_color: '#7f1d1d',
            text_color: '#fff7ed',
            opacity: 0.92,
            width: 160,
            height: 0,
          });
          setPopupBubbles([popup], { commit: false, rerender: true });
          popupBubbleExpansion.set(popup.id, true);
          selectedPopupBubbleId = popup.id;

          [
            'threshold',
            'beep_detection',
            'shot_candidate_detection',
            'shot_refinement',
            'false_positive_suppression',
            'confidence_review',
            'timing_changer',
            'advanced_runtime',
          ].forEach((sectionId) => shotMLSectionExpansion.set(sectionId, true));

          syncLocalProjectUiState();
          render();
        }
        """
    )
    page.wait_for_timeout(500)


def seek_near_final_shot(page: Page) -> None:
    page.evaluate(
        """
        async () => {
          const video = document.getElementById('primary-video');
          if (!(video instanceof HTMLVideoElement)) return;
          const shots = orderedShotsByTime();
          const last = shots.at(-1);
          const positionMs = last ? shotDisplayTimeMs(last.time_ms) + 100 : Math.max(0, (video.duration || 0) * 1000 - 100);
          video.currentTime = Math.max(0, positionMs / 1000);
          renderLiveOverlay(positionMs);
          await new Promise((resolve) => window.setTimeout(resolve, 250));
        }
        """
    )


def capture_all(page: Page) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    click_tool(page, "project")
    prepare_demo_state(page)
    screenshot(page, "ProjectPane.png")

    click_tool(page, "scoring")
    prepare_demo_state(page)
    screenshot(page, "ScoringPane.png", 0)
    screenshot(page, "ScoringPane2.png", 760)

    click_tool(page, "timing")
    prepare_demo_state(page)
    screenshot(page, "SplitsPane.png", 0)
    page.locator("#expand-timing").click()
    page.wait_for_selector("#cockpit-root.timing-expanded", timeout=30_000)
    page.wait_for_timeout(350)
    screenshot(page, "SplitsExpanded.png", 0)
    page.locator("#collapse-timing").click()
    page.wait_for_timeout(250)
    page.locator("#expand-waveform").click()
    page.wait_for_selector("#cockpit-root.waveform-expanded", timeout=30_000)
    page.wait_for_timeout(350)
    screenshot(page, "WaveFormExpanded.png", 0)
    page.locator("#expand-waveform").click()
    page.wait_for_timeout(250)

    click_tool(page, "shotml")
    prepare_demo_state(page)
    screenshot(page, "ShotMLPane.png", 0)
    screenshot(page, "ShotMLPane2.png", 1180)

    click_tool(page, "merge")
    prepare_demo_state(page)
    stabilize_pip_controls(page)
    screenshot(page, "PiPPane.png", 0)

    click_tool(page, "overlay")
    prepare_demo_state(page)
    seek_near_final_shot(page)
    screenshot(page, "OverlayPane.png", 0)
    screenshot(page, "OverlayPane2.png", 760)
    open_color_picker(page)
    screenshot(page, "ColorPickerModal.png", 760)
    page.locator("#close-color-picker").click()
    page.wait_for_function("() => document.getElementById('color-picker-modal')?.hidden === true")

    click_tool(page, "popup")
    prepare_demo_state(page)
    screenshot(page, "PopUpPane.png", 0)
    screenshot(page, "PopUpPane2.png", 680)

    click_tool(page, "review")
    prepare_demo_state(page)
    seek_near_final_shot(page)
    screenshot(page, "ReviewPane.png", 0)
    screenshot(page, "ReviewPane2.png", 760)

    click_tool(page, "export")
    prepare_demo_state(page)
    screenshot(page, "ExportPane.png", 0)
    screenshot(page, "ExportPane2.png", 760)
    open_export_log(page)
    screenshot(page, "ExportLogModal.png", 760)
    page.locator("#close-export-log").click()
    page.wait_for_function("() => document.getElementById('export-log-modal')?.hidden === true")

    click_tool(page, "metrics")
    prepare_demo_state(page)
    screenshot(page, "MetricsPane.png", 0)
    page.locator("#expand-metrics").click()
    page.wait_for_selector("#cockpit-root.metrics-expanded", timeout=30_000)
    page.wait_for_timeout(350)
    screenshot(page, "MetricsPane2.png", 0)


def main() -> int:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, log_level="off")
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
                page.goto(server.url, wait_until="domcontentloaded")
                page.wait_for_selector("#current-file")
                import_primary_video(page)
                import_practiscore(page)
                import_merge_media(page)
                page.wait_for_timeout(2000)
                prepare_demo_state(page)
                capture_all(page)
            finally:
                browser.close()
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
