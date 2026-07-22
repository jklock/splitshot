"""Launch SplitShot and refresh the canonical v1.0.7 documentation screenshots."""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import Page, sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = ROOT / "docs" / "screenshots"
PRIMARY_VIDEO = ROOT / "tests" / "fixtures" / "media" / "stage.mp4"
MERGE_VIDEO = ROOT / "tests" / "fixtures" / "media" / "stage-merge.mp4"
PRACTISCORE = ROOT / "example_data" / "IDPA" / "IDPA.csv"
WORK_ROOT = ROOT / "tmp" / "codex" / "doc-screenshots"
VIEWPORT = {"width": 1440, "height": 1024}


@dataclass(frozen=True, slots=True)
class ScreenshotSpec:
    filename: str
    tool: str
    state: str = "default"


SCREENSHOT_MANIFEST = (
    ScreenshotSpec("ProjectPane.png", "project"),
    ScreenshotSpec("MediaPane.png", "media"),
    ScreenshotSpec("ComposePane.png", "merge"),
    ScreenshotSpec("TrimPane.png", "trim-sync"),
    ScreenshotSpec("ScorePane.png", "scoring"),
    ScreenshotSpec("ScorePane2.png", "scoring", "scrolled"),
    ScreenshotSpec("SplitsPane.png", "timing"),
    ScreenshotSpec("SplitsExpanded.png", "timing", "timing-expanded"),
    ScreenshotSpec("WaveformExpanded.png", "timing", "waveform-expanded"),
    ScreenshotSpec("MarkersPane.png", "markers"),
    ScreenshotSpec("MarkersPane2.png", "markers", "scrolled"),
    ScreenshotSpec("OverlayPane.png", "overlay"),
    ScreenshotSpec("OverlayPane2.png", "overlay", "scrolled"),
    ScreenshotSpec("ColorPickerModal.png", "overlay", "color-picker"),
    ScreenshotSpec("ReviewPane.png", "review"),
    ScreenshotSpec("ReviewPane2.png", "review", "scrolled"),
    ScreenshotSpec("ExportPane.png", "export"),
    ScreenshotSpec("ExportPane2.png", "export", "scrolled"),
    ScreenshotSpec("ExportLogModal.png", "export", "export-log"),
    ScreenshotSpec("QueuePane.png", "queue"),
    ScreenshotSpec("MetricsPane.png", "metrics"),
    ScreenshotSpec("MetricsExpanded.png", "metrics", "expanded"),
    ScreenshotSpec("ShotMLPane.png", "shotml"),
    ScreenshotSpec("ShotMLPane2.png", "shotml", "scrolled"),
    ScreenshotSpec("SettingsPane.png", "settings"),
    ScreenshotSpec("SettingsPane2.png", "settings", "scrolled"),
)
SCREENSHOT_FILENAMES = tuple(spec.filename for spec in SCREENSHOT_MANIFEST)


def create_project(page: Page, project_dir: Path) -> None:
    page.evaluate(
        """
        async (projectPath) => {
          await createNewProject(projectPath);
        }
        """,
        str(project_dir),
    )
    page.wait_for_function(
        "() => Boolean(state?.project?.path)",
        timeout=30_000,
    )
    wait_for_app_idle(page)


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


def screenshot(
    page: Page,
    filename: str,
    scroll_top: int = 0,
    screenshot_dir: Path = SCREENSHOT_DIR,
) -> None:
    set_inspector_scroll(page, scroll_top)
    page.screenshot(path=str(screenshot_dir / filename), full_page=False)


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
    page.evaluate(
        """
        async (path) => {
          await callApi("/api/import/primary", { path });
        }
        """,
        str(PRIMARY_VIDEO),
    )
    page.wait_for_function(
        "() => (state?.project?.analysis?.shots?.length || 0) > 0", timeout=120_000
    )
    page.wait_for_function(
        r"""
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


def add_second_stage(page: Page) -> None:
    """Populate the Media and Queue panes without changing the configured active stage."""
    page.evaluate(
        """
        async (path) => {
          const originalStageId = state?.project?.active_stage_id;
          await callApi('/api/project/stage/create', { label: 'Stage 2' });
          const secondStageId = state?.project?.active_stage_id;
          await callApi('/api/project/stage/import-primary', { stage_id: secondStageId, path });
          await callApi('/api/project/queue/add', { stage_id: secondStageId });
          await callApi('/api/project/select-stage', { active_stage_id: originalStageId });
        }
        """,
        str(MERGE_VIDEO),
    )
    page.wait_for_function("() => (state?.project?.stages || []).length >= 2", timeout=120_000)
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
            state.project.description = 'Documentation capture with scoring, overlays, composition, markers, and review text boxes configured.';
          }

          if (state?.project?.scoring) {
            state.project.scoring.enabled = true;
          }

          if (state?.project?.export) {
            state.project.export.output_path = 'ScreenshotProject/Output/final.mp4';
            state.project.export.last_error = '';
            state.project.export.last_log = [
              'SplitShot export preview log',
              'Input: stage.mp4',
              'Overlay: timer, draw, shots, score, markers, and review boxes enabled',
              'Compose: 1 added media item, sync -2555 ms',
              'Output: ScreenshotProject/Output/final.mp4',
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
          });

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
              summary_metric_ids: [
                'division_placement',
                'class_placement',
                'overall_placement',
              ],
              quadrant: window.aboveFinalTextBoxValue,
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
          scoringRowEdits = new Set();
          shots.slice(0, 4).forEach((shot) => scoringRowEdits.add(shot.id));
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


def validate_dynamic_standings(page: Page) -> None:
    """Fail capture if the imported summary regresses to generic placement labels."""
    click_tool(page, "review")
    prepare_demo_state(page)
    page.wait_for_function(
        r"""
        () => {
          const text = [...document.querySelectorAll('[data-text-box-preview]')]
            .map((control) => control.value || control.textContent || '')
            .join('\n');
          const rows = text.split(/\n/).map((row) => row.trim()).filter(Boolean);
          return rows.some((row) => /^Overall - \d+\/\d+$/.test(row))
            && rows.filter((row) => / - \d+\/\d+$/.test(row)).length >= 3;
        }
        """,
        timeout=30_000,
    )
    text = page.locator("[data-text-box-preview]").evaluate_all(
        "controls => controls.map((control) => control.value || control.textContent || '').join('\\n')"
    )
    obsolete = (
        "Division Placement",
        "Class Placement",
        "Division + Class Placement",
    )
    if any(label in text for label in obsolete):
        raise RuntimeError("Imported standings contain obsolete generic placement labels")
    click_tool(page, "overlay")
    prepare_demo_state(page)
    seek_near_final_shot(page)


def capture_all(page: Page, screenshot_dir: Path = SCREENSHOT_DIR) -> None:
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    captured: list[str] = []

    def take(filename: str, scroll_top: int = 0) -> None:
        screenshot(page, filename, scroll_top, screenshot_dir)
        captured.append(filename)

    try:
        for tool, filename in (
            ("project", "ProjectPane.png"),
            ("media", "MediaPane.png"),
            ("merge", "ComposePane.png"),
            ("trim-sync", "TrimPane.png"),
        ):
            click_tool(page, tool)
            prepare_demo_state(page)
            if tool == "merge":
                stabilize_pip_controls(page)
            take(filename)

        click_tool(page, "scoring")
        prepare_demo_state(page)
        take("ScorePane.png")
        take("ScorePane2.png", 760)

        click_tool(page, "timing")
        prepare_demo_state(page)
        take("SplitsPane.png")
        page.locator("#expand-timing").click()
        page.wait_for_selector("#cockpit-root.timing-expanded", timeout=30_000)
        take("SplitsExpanded.png")
        page.locator("#collapse-timing").click()
        page.locator("#expand-waveform").click()
        page.wait_for_selector("#cockpit-root.waveform-expanded", timeout=30_000)
        take("WaveformExpanded.png")
        page.locator("#expand-waveform").click()

        click_tool(page, "markers")
        prepare_demo_state(page)
        take("MarkersPane.png")
        take("MarkersPane2.png", 680)

        click_tool(page, "overlay")
        prepare_demo_state(page)
        validate_dynamic_standings(page)
        take("OverlayPane.png")
        take("OverlayPane2.png", 760)
        open_color_picker(page)
        take("ColorPickerModal.png", 760)
        page.locator("#close-color-picker").click()

        click_tool(page, "review")
        prepare_demo_state(page)
        seek_near_final_shot(page)
        take("ReviewPane.png")
        take("ReviewPane2.png", 760)

        click_tool(page, "export")
        prepare_demo_state(page)
        take("ExportPane.png")
        take("ExportPane2.png", 760)
        open_export_log(page)
        take("ExportLogModal.png", 760)
        page.locator("#close-export-log").click()

        click_tool(page, "queue")
        prepare_demo_state(page)
        take("QueuePane.png")

        click_tool(page, "metrics")
        prepare_demo_state(page)
        take("MetricsPane.png")
        page.locator("#expand-metrics").click()
        page.wait_for_selector("#cockpit-root.metrics-expanded", timeout=30_000)
        take("MetricsExpanded.png")
        page.locator("#collapse-metrics").click()

        click_tool(page, "shotml")
        prepare_demo_state(page)
        take("ShotMLPane.png")
        take("ShotMLPane2.png", 1180)

        click_tool(page, "settings")
        prepare_demo_state(page)
        take("SettingsPane.png")
        take("SettingsPane2.png", 760)

        if tuple(captured) != SCREENSHOT_FILENAMES:
            raise RuntimeError(f"Capture sequence does not match manifest: {captured}")
    finally:
        set_inspector_scroll(page, 0)


def create_contact_sheet(browser, screenshot_dir: Path, output_path: Path) -> None:
    """Render an ignored review sheet without adding an image-processing dependency."""
    cards = []
    for filename in SCREENSHOT_FILENAMES:
        data = base64.b64encode((screenshot_dir / filename).read_bytes()).decode("ascii")
        cards.append(
            f'<figure><img src="data:image/png;base64,{data}"><figcaption>{filename}</figcaption></figure>'
        )
    page = browser.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=1)
    try:
        page.set_content(
            "<style>body{margin:16px;background:#111;color:#fff;font:14px sans-serif}"
            ".grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}"
            "figure{margin:0}img{display:block;width:100%;aspect-ratio:45/32;object-fit:cover;object-position:top}"
            "figcaption{padding:6px 0}</style><div class=grid>" + "".join(cards) + "</div>"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output_path), full_page=True)
    finally:
        page.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=SCREENSHOT_DIR)
    parser.add_argument("--work-root", type=Path, default=WORK_ROOT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    work_root = args.work_root.expanduser().resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, log_level="off")
    server.start_background(open_browser=False)
    try:
        with TemporaryDirectory(prefix="run-", dir=work_root) as temp_dir:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
                    page.goto(server.url, wait_until="domcontentloaded")
                    page.wait_for_selector("#current-file")
                    create_project(page, Path(temp_dir) / "ScreenshotProject")
                    import_primary_video(page)
                    import_practiscore(page)
                    import_merge_media(page)
                    add_second_stage(page)
                    page.wait_for_timeout(2000)
                    prepare_demo_state(page)
                    capture_all(page, args.output_dir.expanduser().resolve())
                    create_contact_sheet(
                        browser,
                        args.output_dir.expanduser().resolve(),
                        work_root / "contact-sheet.png",
                    )
                finally:
                    browser.close()
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
