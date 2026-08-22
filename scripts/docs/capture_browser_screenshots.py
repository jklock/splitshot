"""Launch SplitShot and refresh the canonical v1.0.7 documentation screenshots."""

from __future__ import annotations

import argparse
import base64
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController

ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = ROOT / "docs" / "screenshots"
PRACTISCORE = ROOT / "example_data" / "IDPA" / "IDPA.csv"
WORK_ROOT = ROOT / "tmp" / "codex" / "doc-screenshots"
VIEWPORT = {"width": 1400, "height": 900}


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
    ScreenshotSpec("MarkersPane2.png", "markers", "expanded"),
    ScreenshotSpec("OverlayPane.png", "overlay"),
    ScreenshotSpec("OverlayPane2.png", "overlay", "scrolled"),
    ScreenshotSpec("ColorPickerModal.png", "overlay", "color-picker"),
    ScreenshotSpec("ReviewPane.png", "review"),
    ScreenshotSpec("ReviewPane2.png", "review", "scrolled"),
    ScreenshotSpec("ExportPane.png", "export"),
    ScreenshotSpec("ExportPane2.png", "export", "scrolled"),
    ScreenshotSpec("IntroOutroPane.png", "intro-outro"),
    ScreenshotSpec("QueuePane.png", "queue"),
    ScreenshotSpec("ProcessingLogModal.png", "queue", "processing-log"),
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
    seek_showcase_frame(page)
    stabilize_visible_video_frames(page)
    validate_showcase_state(page)
    page.screenshot(path=str(screenshot_dir / filename), full_page=False)


def stabilize_visible_video_frames(page: Page) -> None:
    """Seek decoded primary and secondary frames before any visual proof capture."""
    result = page.evaluate(
        r"""
        async () => {
          const frameStats = (video) => {
            const canvas = document.createElement('canvas');
            canvas.width = 32;
            canvas.height = 18;
            const context = canvas.getContext('2d', { willReadFrequently: true });
            if (!context) return { mean: 0, variance: 0 };
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
            const values = [];
            for (let index = 0; index < pixels.length; index += 4) {
              values.push((pixels[index] + pixels[index + 1] + pixels[index + 2]) / 3);
            }
            const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
            const variance = values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / values.length;
            return { mean, variance };
          };
          const waitForFrame = async (video, targetTime) => {
            if (!(video instanceof HTMLVideoElement)) return false;
            if (video.readyState < HTMLMediaElement.HAVE_METADATA) {
              await new Promise((resolve) => {
                video.addEventListener('loadedmetadata', resolve, { once: true });
                window.setTimeout(resolve, 15000);
              });
            }
            const duration = Number.isFinite(video.duration) ? video.duration : 0;
            const target = Math.min(Math.max(0.1, targetTime), Math.max(0.1, duration - 0.05));
            if (Math.abs(video.currentTime - target) > 0.02) {
              await new Promise((resolve) => {
                video.addEventListener('seeked', resolve, { once: true });
                video.currentTime = target;
                window.setTimeout(resolve, 15000);
              });
            }
            const deadline = performance.now() + 15000;
            while (performance.now() < deadline) {
              await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
              const stats = frameStats(video);
              if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA
                  && video.videoWidth > 0
                  && video.videoHeight > 0
                  && stats.mean > 8
                  && stats.variance > 12) return true;
              await new Promise((resolve) => window.setTimeout(resolve, 100));
            }
            return false;
          };

          const primary = document.getElementById('primary-video');
          const activeToolName = typeof activeTool === 'string' ? activeTool : '';
          const primaryTime = primary instanceof HTMLVideoElement && primary.currentTime > 0.05
            ? primary.currentTime
            : 1;
          const primaryReady = await waitForFrame(primary, primaryTime);
          let secondaryVideos = [];
          let secondaryReady = false;
          if (activeToolName !== 'intro-outro') {
            scheduleInteractionPreviewRender({ video: true });
            await new Promise((resolve) => window.setTimeout(resolve, 300));
            secondaryVideos = [...document.querySelectorAll('#merge-preview-layer video')];
            secondaryReady = secondaryVideos.length > 0
              && (await Promise.all(secondaryVideos.map((video) => waitForFrame(video, primaryTime)))).every(Boolean);
            renderLiveOverlay(primaryTime * 1000);
          }
          const primaryRect = primary?.getBoundingClientRect();
          const playerVisible = Boolean(primaryRect && primaryRect.width > 0 && primaryRect.height > 0);
          const secondaryVisible = secondaryVideos.some((video) => {
            const rect = video.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && getComputedStyle(video).visibility !== 'hidden';
          });
          return { primaryReady, secondaryReady, playerVisible, secondaryVisible, activeToolName };
        }
        """
    )
    if not result["primaryReady"] or (
        result["activeToolName"] != "intro-outro" and not result["secondaryReady"]
    ):
        raise RuntimeError(f"Screenshot video frames are not decoded: {result}")
    if (
        result["playerVisible"]
        and result["activeToolName"] != "intro-outro"
        and not result["secondaryVisible"]
    ):
        raise RuntimeError(f"Visible player is missing secondary video: {result}")


def validate_showcase_state(page: Page) -> None:
    result = page.evaluate(
        """
        () => {
          const project = state?.project || {};
          const overlay = project.overlay || {};
          const videoRect = document.getElementById('primary-video')?.getBoundingClientRect();
          const previewVisible = Boolean(videoRect && videoRect.width > 0 && videoRect.height > 0);
          const visible = (selector) => [...document.querySelectorAll(selector)].filter((element) => {
            const rect = element.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && getComputedStyle(element).visibility !== 'hidden';
          }).length;
          return {
            activeTool: typeof activeTool === 'string' ? activeTool : '',
            scoring: Boolean(project.scoring?.enabled),
            merge: Boolean(project.merge?.enabled && (project.merge_sources || []).length),
            overlayFlags: ['show_timer', 'show_draw', 'show_shots', 'show_score'].every((key) => overlay[key] === true),
            reviewFlags: project.ui_state?.review_show_markers === true && project.ui_state?.review_show_pip === true,
            markerCount: (project.popups || []).filter((item) => item.enabled !== false).length,
            textBoxCount: (overlay.text_boxes || []).filter((item) => item.enabled !== false).length,
            boundaryMedia: Boolean(project.intro_clip?.asset?.path && project.outro_clip?.asset?.path),
            queuedStages: (project.stages || []).filter((stage) => stage.queue_state === 'queued' || stage.queued).length,
            previewVisible,
            visibleBadges: visible('#custom-overlay .overlay-badge'),
            visibleMarkers: visible('#popup-overlay .popup-overlay-badge'),
            visibleTextBoxes: visible('#custom-overlay [data-text-box-id]'),
            visiblePip: visible('#merge-preview-layer video'),
            visibleBoundaryBoxes: visible('.intro-outro-preview-badge'),
          };
        }
        """
    )
    required = ("scoring", "merge", "overlayFlags", "reviewFlags", "boundaryMedia")
    if not all(result[key] for key in required):
        raise RuntimeError(f"Screenshot showcase state is incomplete: {result}")
    if result["markerCount"] < 1 or result["textBoxCount"] < 2:
        raise RuntimeError(f"Screenshot overlays are incomplete: {result}")
    if (
        result["previewVisible"]
        and result["activeTool"] == "intro-outro"
        and result["visibleBoundaryBoxes"] < 2
    ):
        raise RuntimeError(f"Intro / Outro preview is missing configured text boxes: {result}")
    if (
        result["previewVisible"]
        and result["activeTool"] != "intro-outro"
        and (
            result["visibleBadges"] < 2
            or result["visibleMarkers"] < 1
            or result["visibleTextBoxes"] < 2
            or result["visiblePip"] < 1
        )
    ):
        raise RuntimeError(f"Visible preview is missing showcase features: {result}")


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


def open_processing_log(page: Page) -> None:
    page.locator("#queue-show-log").click()
    page.wait_for_selector("#export-log-modal:not([hidden])", timeout=30_000)
    page.wait_for_timeout(250)


def stabilize_intro_outro_preview(page: Page) -> None:
    """Exercise both boundary tabs and leave the decoded Intro preview active."""
    for kind in ("outro", "intro"):
        page.locator(f"[data-boundary-kind='{kind}']").click()
        page.wait_for_function(
            """
            (kind) => {
              const shell = document.querySelector('.intro-outro-shell');
              const boxes = [...document.querySelectorAll('.intro-outro-preview-badge')];
              return shell?.dataset.renderedBoundaryKind === kind && boxes.length >= 2;
            }
            """,
            arg=kind,
            timeout=30_000,
        )
    page.wait_for_timeout(250)


def stabilize_pip_controls(page: Page) -> None:
    page.locator("#merge-enabled").check()
    page.locator("#merge-layout").select_option("pip")
    page.wait_for_timeout(500)
    prepare_demo_state(page)
    try:
        page.wait_for_function(
            """
            () => {
              const videos = [...document.querySelectorAll('#merge-preview-layer video')];
              return videos.length > 0 && videos.every((video) => (
                video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA
                && video.videoWidth > 0
                && video.videoHeight > 0
              ));
            }
            """,
            timeout=30_000,
        )
    except PlaywrightTimeoutError as exc:
        detail = page.evaluate(
            """
            () => ({
              merge: state?.project?.merge || null,
              sources: (state?.project?.merge_sources || []).map((source) => ({
                id: source.id,
                path: source.effective_media_path || source.asset?.path || '',
                placement: source.placement || null,
              })),
              showPip: document.getElementById('show-pip')?.checked,
              layer: {
                hidden: document.getElementById('merge-preview-layer')?.hidden,
                html: document.getElementById('merge-preview-layer')?.innerHTML || '',
              },
              classic: (() => {
                const video = document.getElementById('secondary-video');
                return video ? { hidden: video.hidden, src: video.src, readyState: video.readyState } : null;
              })(),
            })
            """
        )
        raise RuntimeError(f"PiP preview did not become ready: {detail}") from exc


def import_primary_video(page: Page, video_path: Path) -> None:
    click_tool(page, "project")
    page.evaluate(
        """
        async (path) => {
          await callApi("/api/import/primary", { path });
        }
        """,
        str(video_path),
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


def import_merge_media(page: Page, video_path: Path) -> None:
    click_tool(page, "merge")
    page.locator("#merge-media-input").set_input_files(str(video_path))
    page.wait_for_function(
        "() => (state?.project?.merge_sources?.length || 0) > 0 && document.querySelectorAll('#merge-media-list .merge-media-card').length > 0",
        timeout=120_000,
    )
    wait_for_app_idle(page)


def add_second_stage(page: Page, video_path: Path) -> str:
    """Populate the Media and Queue panes without changing the configured active stage."""
    stage_ids = page.evaluate(
        """
        async (path) => {
          const originalStageId = state?.project?.active_stage_id;
          const existingStage = (state?.project?.stages || []).find((stage) => (
            stage.id !== originalStageId && String(stage.label || '').trim().toLowerCase() === 'stage 2'
          ));
          let secondStageId = existingStage?.id || '';
          if (!secondStageId) {
            const created = await callApi('/api/project/stage/create', { label: 'Documentation Stage 2' });
            secondStageId = created?.project?.active_stage_id || '';
          }
          if (!originalStageId || !secondStageId) throw new Error('Unable to resolve documentation stage IDs.');
          await callApi('/api/project/stage/import-primary', { stage_id: secondStageId, path });
          await callApi('/api/project/queue/add', { stage_id: secondStageId });
          await callApi('/api/project/select-stage', { active_stage_id: originalStageId });
          return { originalStageId, secondStageId };
        }
        """,
        str(video_path),
    )
    page.wait_for_function(
        """
        ({ originalStageId, secondStageId }) => {
          const second = (state?.project?.stages || []).find((stage) => stage.id === secondStageId);
          return state?.project?.active_stage_id === originalStageId
            && String(second?.primary_media?.path || '').endsWith('secondary-stage.mp4');
        }
        """,
        arg=stage_ids,
        timeout=120_000,
    )
    wait_for_app_idle(page)
    return str(stage_ids["originalStageId"])


def restore_primary_stage(page: Page, stage_id: str) -> None:
    page.evaluate(
        "async (id) => callApi('/api/project/select-stage', { active_stage_id: id })",
        stage_id,
    )
    page.wait_for_function(
        """
        (id) => state?.project?.active_stage_id === id
          && String(state?.media?.primary_display_name || '').endsWith('primary-stage.mp4')
          && String(state?.status || '').startsWith('Selected stage ')
        """,
        arg=stage_id,
        timeout=30_000,
    )
    wait_for_app_idle(page)


def import_boundary_media(page: Page, primary_video: Path, secondary_video: Path) -> None:
    page.evaluate(
        """
        async ({ primaryPath, secondaryPath }) => {
          await callApi('/api/project/in-out/media', { kind: 'intro', path: primaryPath });
          await callApi('/api/project/in-out/media', { kind: 'outro', path: secondaryPath });
          const manual = {
            enabled: true,
            source: 'manual',
            text: 'SplitShot Match Review',
            quadrant: 'top_left',
            background_color: '#111827',
            text_color: '#f9fafb',
            opacity: 0.92,
            font_size: 32,
            font_bold: true,
          };
          const summary = {
            enabled: true,
            source: 'match_summary',
            text: '',
            summary_metric_ids: ['score_time', 'points_down', 'division_placement', 'class_placement', 'overall_placement'],
            quadrant: 'top_right',
            background_color: '#064e3b',
            text_color: '#ecfdf5',
            opacity: 0.94,
            font_size: 28,
            font_bold: true,
          };
          await callApi('/api/project/intro-outro/overlay', { kind: 'intro', text_boxes: [manual, summary] });
          await callApi('/api/project/intro-outro/overlay', { kind: 'outro', text_boxes: [manual, summary] });
          await callApi('/api/project/intro-outro/fades', { kind: 'intro', fade_in_s: 0.5, fade_out_s: 0.5 });
          await callApi('/api/project/intro-outro/fades', { kind: 'outro', fade_in_s: 0.5, fade_out_s: 0.5 });
        }
        """,
        {"primaryPath": str(primary_video), "secondaryPath": str(secondary_video)},
    )
    page.wait_for_function(
        "() => Boolean(state?.project?.intro_clip?.asset?.path && state?.project?.outro_clip?.asset?.path)",
        timeout=120_000,
    )
    wait_for_app_idle(page)


def prewarm_boundary_media(server: BrowserControlServer, controller: ProjectController) -> None:
    """Prepare browser-compatible copies before the In / Out preview is opened."""
    paths = tuple(
        Path(clip.asset.path)
        for clip in (controller.project.intro_clip, controller.project.outro_clip)
        if clip.asset.path
    )
    server._prewarm_media_paths(paths)


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

          if (state?.project?.ui_state) {
            state.project.ui_state.review_show_markers = true;
            state.project.ui_state.review_show_pip = true;
          }
          if (document.getElementById('show-markers')) document.getElementById('show-markers').checked = true;
          if (document.getElementById('show-pip')) document.getElementById('show-pip').checked = true;

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
            source.placement = { ...(source.placement || {}), mode: 'pip' };
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

          const popupShot = shots.at(-1) || shots[0] || null;
          const popupTime = popupShot ? shotDisplayTimeMs(popupShot.time_ms) : 2500;
          const popup = normalizePopupBubble({
            id: createPopupBubbleId(),
            name: 'Exit target callout',
            text: '-0',
            enabled: true,
            anchor_mode: popupShot ? 'shot' : 'time',
            shot_id: popupShot?.id || '',
            time_ms: popupTime,
            duration_ms: 5000,
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


def seek_showcase_frame(page: Page) -> None:
    page.evaluate(
        """
        async () => {
          const video = document.getElementById('primary-video');
          if (!(video instanceof HTMLVideoElement)) return;
          if (typeof activeTool === 'string' && activeTool === 'intro-outro') {
            video.currentTime = Math.min(1, Math.max(0, (video.duration || 1) - 0.05));
            await new Promise((resolve) => window.setTimeout(resolve, 250));
            return;
          }
          const shots = orderedShotsByTime();
          const last = shots.at(-1);
          const positionMs = last ? shotDisplayTimeMs(last.time_ms) + 100 : Math.max(100, (video.duration || 0) * 1000 - 100);
          video.currentTime = Math.max(0, positionMs / 1000);
          renderLiveOverlay(positionMs);
          await new Promise((resolve) => window.setTimeout(resolve, 250));
        }
        """
    )


def validate_dynamic_standings(page: Page) -> None:
    """Keep generic selectors distinct from source-derived rendered standings."""
    click_tool(page, "review")
    prepare_demo_state(page)
    selector_labels = page.locator(
        "[data-summary-metric='division_placement'], "
        "[data-summary-metric='class_placement'], "
        "[data-summary-metric='overall_placement']"
    ).evaluate_all(
        "controls => controls.map((control) => control.closest('label')?.textContent?.trim() || '')"
    )
    if selector_labels != ["Division", "Class", "Overall"]:
        raise RuntimeError(f"Summary metric selectors must remain generic: {selector_labels}")
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
    seek_showcase_frame(page)


def capture_all(page: Page, screenshot_dir: Path = SCREENSHOT_DIR) -> None:
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    captured: list[str] = []

    def take(filename: str, scroll_top: int = 0) -> None:
        screenshot(page, filename, scroll_top, screenshot_dir)
        captured.append(filename)

    try:
        click_tool(page, "merge")
        stabilize_pip_controls(page)
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
            take(filename, 625 if tool == "trim-sync" else 0)

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
        page.locator("#popup-edit-selected").click()
        page.wait_for_selector("#cockpit-root.markers-expanded", timeout=30_000)
        take("MarkersPane2.png")
        page.locator("#popup-edit-selected").click()
        page.wait_for_selector("#cockpit-root:not(.markers-expanded)", timeout=30_000)

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
        seek_showcase_frame(page)
        take("ReviewPane.png")
        take("ReviewPane2.png", 760)

        click_tool(page, "export")
        prepare_demo_state(page)
        take("ExportPane.png")
        take("ExportPane2.png", 760)
        prepare_demo_state(page)
        click_tool(page, "intro-outro")
        stabilize_intro_outro_preview(page)
        take("IntroOutroPane.png", 0)

        click_tool(page, "queue")
        prepare_demo_state(page)
        take("QueuePane.png")
        open_processing_log(page)
        take("ProcessingLogModal.png", 760)
        page.locator("#close-export-log").click()

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
        page.evaluate(
            """
            () => {
              ['markers', 'export', 'shotml'].forEach((sectionId) => {
                setSettingsSectionExpanded(sectionId, true);
              });
              renderSettingsSections();
            }
            """
        )
        take("SettingsPane2.png", 900)

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
    parser.add_argument("--primary-video", type=Path, required=True)
    parser.add_argument("--secondary-video", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=SCREENSHOT_DIR)
    parser.add_argument("--work-root", type=Path, default=WORK_ROOT)
    return parser


def validated_real_video(path: Path, *, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} video does not exist: {resolved}")
    if resolved.is_relative_to(ROOT / "tests"):
        raise ValueError(f"{label} video must not come from tests/: {resolved}")
    if resolved.suffix.lower() not in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}:
        raise ValueError(f"{label} input is not a supported video: {resolved}")
    return resolved


def validated_video_pair(primary: Path, secondary: Path) -> tuple[Path, Path]:
    primary_source = validated_real_video(primary, label="Primary")
    secondary_source = validated_real_video(secondary, label="Secondary")
    if primary_source == secondary_source:
        raise ValueError("Primary and secondary documentation videos must be different files.")
    return primary_source, secondary_source


def main() -> int:
    args = build_parser().parse_args()
    primary_source, secondary_source = validated_video_pair(
        args.primary_video, args.secondary_video
    )
    work_root = args.work_root.expanduser().resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, log_level="off")
    server.start_background(open_browser=False)
    try:
        with TemporaryDirectory(prefix="run-", dir=work_root) as temp_dir:
            media_root = Path(temp_dir) / "capture-media"
            media_root.mkdir(parents=True, exist_ok=True)
            primary_video = media_root / "primary-stage.mp4"
            secondary_video = media_root / "secondary-stage.mp4"
            shutil.copy2(primary_source, primary_video)
            shutil.copy2(secondary_source, secondary_video)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
                    page.goto(server.url, wait_until="domcontentloaded")
                    page.wait_for_selector("#current-file")
                    create_project(page, Path(temp_dir) / "ScreenshotProject")
                    import_primary_video(page, primary_video)
                    import_practiscore(page)
                    primary_stage_id = add_second_stage(page, secondary_video)
                    import_merge_media(page, secondary_video)
                    import_boundary_media(page, primary_video, secondary_video)
                    restore_primary_stage(page, primary_stage_id)
                    prewarm_boundary_media(server, controller)
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
