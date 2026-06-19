"""Capture Phase 13 pane ownership proof against the real 05072026 project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import Browser, Page, Playwright, sync_playwright
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import MergeSource, QueueStatus
from splitshot.media.probe import probe_video
from splitshot.ui.controller import ProjectController


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROJECT = ROOT / "05072026"
DEFAULT_PRIMARY = ROOT / "05072026" / "Stage2.MP4"
DEFAULT_ADDED = [ROOT / "05072026" / "Stage3.MP4", ROOT / "05072026" / "Stage4.MP4"]
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts" / "v107-pane-audit"
TOOLS = [
    "project",
    "media",
    "merge",
    "trim-sync",
    "scoring",
    "timing",
    "markers",
    "overlay",
    "review",
    "export",
    "queue",
    "metrics",
    "shotml",
    "settings",
]
TOOL_TITLES = {
    "project": "Project",
    "media": "Media",
    "merge": "Compose",
    "trim-sync": "Trim",
    "scoring": "Score",
    "timing": "Splits",
    "markers": "Markers",
    "overlay": "Overlay",
    "review": "Review",
    "export": "Export",
    "queue": "Queue",
    "metrics": "Metrics",
    "shotml": "ShotML",
    "settings": "Settings",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the v107 pane audit against 05072026.")
    parser.add_argument("--project-path", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--primary-video", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--added-video", type=Path, action="append", dest="added_videos")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    return parser


def _open_page(playwright: Playwright, base_url: str) -> tuple[Browser, Page]:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1180})
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_selector("#current-file")
    return browser, page


def _refresh(page: Page) -> None:
    page.evaluate("async () => { await refresh(); }")
    page.wait_for_timeout(300)


def _wait_for_processing_bar(page: Page) -> None:
    page.wait_for_function("() => document.getElementById('processing-bar')?.hidden === true", timeout=30_000)


def _set_tool(page: Page, tool: str) -> None:
    page.evaluate(
        """
        (targetTool) => {
          setActiveTool(targetTool, { collapseExpandedLayout: false, persistUiState: false });
          render();
          const inspector = document.querySelector('.inspector');
          if (inspector instanceof HTMLElement) inspector.scrollTop = 0;
        }
        """,
        tool,
    )
    page.wait_for_function("(targetTool) => activeTool === targetTool", arg=tool, timeout=30_000)
    _wait_for_processing_bar(page)


def _prepare_controller_state(
    controller: ProjectController,
    project_path: Path,
    primary_video: Path,
    added_videos: list[Path],
) -> dict[str, object]:
    controller.open_project(str(project_path))
    stages = list(controller.project.stages)
    stage_two = next(
        (
            stage
            for stage in stages
            if int(getattr(stage, "order_index", 0) or 0) == 2 or str(getattr(stage, "label", "")).strip().lower() == "stage 2"
        ),
        None,
    )
    if stage_two is None:
        raise RuntimeError("Stage 2 was not found in 05072026.")
    controller.select_stage(stage_two.id)
    controller.project.queue.clear()
    for stage in controller.project.stages:
        stage.queue_status = QueueStatus.NOT_QUEUED
    stage = controller.project.active_stage
    if stage is None:
        raise RuntimeError("Active stage was not available.")
    stage.primary_media = probe_video(primary_video)
    stage.added_media = [MergeSource(asset=probe_video(video)) for video in added_videos]
    controller._sync_active_stage_to_project()
    controller.add_stage_to_queue(stage.id)
    if controller.project.merge_sources:
        controller.adjust_merge_source_sync_offset(controller.project.merge_sources[0].id, 10)
    controller.project.touch()
    return {
        "project_path": str(project_path),
        "active_stage_id": stage.id,
        "active_stage_label": stage.label,
        "active_stage_order": stage.order_index,
        "primary_media_path": stage.primary_media.path,
        "added_media_paths": [source.asset.path for source in stage.added_media],
        "merge_source_count": len(controller.project.merge_sources),
        "queue_entries": [
            {
                "stage_id": entry.stage_id,
                "status": str(entry.status),
                "output_path": entry.output_path,
            }
            for entry in controller.project.queue
        ],
        "stage_queue_statuses": [
            {
                "id": project_stage.id,
                "label": project_stage.label,
                "order_index": project_stage.order_index,
                "queue_status": str(project_stage.queue_status),
                "has_primary": bool(project_stage.primary_media.path),
                "added_count": len(project_stage.added_media),
            }
            for project_stage in controller.project.stages
        ],
        "trim_derivatives": [
            {
                "id": source.id,
                "sync_offset_ms": source.sync_offset_ms,
                "trim_path": source.trim_derivative.derivative_path or "",
            }
            for source in controller.project.merge_sources
        ],
    }


def _capture_panes(page: Page, artifact_root: Path) -> list[dict[str, object]]:
    artifact_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    for tool in TOOLS:
        _set_tool(page, tool)
        file_name = f"{tool}.png"
        path = artifact_root / file_name
        page.screenshot(path=str(path), full_page=True)
        results.append({"tool": tool, "title": TOOL_TITLES[tool], "file": file_name})
    return results


def _collect_dom_summary(page: Page) -> dict[str, object]:
    return page.evaluate(
        """
        () => {
          const text = (selector) => document.querySelector(selector)?.textContent?.replace(/\\s+/g, ' ').trim() || '';
          const pane = (tool) => text(`[data-tool-pane="${tool}"]`);
          const stageRows = Array.from(document.querySelectorAll('[data-tool-pane="media"] tbody tr')).map((row) => ({
            label: row.querySelector('[data-stage-row-label]')?.textContent?.trim() || '',
            primary: row.querySelector('[data-stage-primary-name]')?.textContent?.trim() || '',
            added: row.querySelector('[data-stage-added-count]')?.textContent?.trim() || '',
          }));
          const queueRows = Array.from(document.querySelectorAll('[data-tool-pane="queue"] tbody tr')).map((row) => ({
            label: row.querySelector('[data-queue-stage-label]')?.textContent?.trim() || '',
            status: row.querySelector('[data-queue-status]')?.textContent?.trim() || '',
            added: row.querySelector('[data-queue-added-count]')?.textContent?.trim() || '',
          }));
          return {
            project_primary_input_present: Boolean(document.querySelector('[data-tool-pane="project"] #primary-file-input')),
            project_primary_button_present: Boolean(document.querySelector('[data-tool-pane="project"] [data-open-primary]')),
            compose_add_media_present: Boolean(document.querySelector('[data-tool-pane="merge"] #add-merge-media')),
            media_pane_text: pane('media'),
            trim_pane_text: pane('trim-sync'),
            queue_pane_text: pane('queue'),
            media_stage_rows: stageRows,
            queue_rows: queueRows,
          };
        }
        """
    )


def _compose_sheet(artifact_root: Path, captures: list[dict[str, object]]) -> None:
    images: list[tuple[str, QImage]] = []
    for item in captures:
        image = QImage(str(artifact_root / str(item["file"])))
        if image.isNull():
            raise RuntimeError(f"Failed to load screenshot {item['file']}")
        images.append((str(item["title"]), image))

    columns = 2
    cell_width = max(image.width() for _, image in images)
    cell_height = max(image.height() for _, image in images) + 56
    rows = (len(images) + columns - 1) // columns
    sheet = QImage(cell_width * columns, cell_height * rows, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#101317"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setPen(QColor("#f3f5f7"))
    font = QFont("Helvetica", 18)
    font.setBold(True)
    painter.setFont(font)
    for index, (title, image) in enumerate(images):
        row = index // columns
        column = index % columns
        x = column * cell_width
        y = row * cell_height
        painter.drawText(x + 16, y + 30, title)
        offset_x = x + (cell_width - image.width()) // 2
        painter.drawImage(offset_x, y + 48, image)
        painter.setPen(QColor("#2b3138"))
        painter.drawRect(x, y, cell_width - 1, cell_height - 1)
        painter.setPen(QColor("#f3f5f7"))
    painter.end()
    sheet.save(str(artifact_root / "all-panes-sheet.png"))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])
    project_path = args.project_path.expanduser().resolve()
    primary_video = args.primary_video.expanduser().resolve()
    added_videos = [path.expanduser().resolve() for path in (args.added_videos or DEFAULT_ADDED)]
    artifact_root = args.artifact_root.expanduser().resolve()
    controller = ProjectController()
    state_summary = _prepare_controller_state(controller, project_path, primary_video, added_videos)
    server = BrowserControlServer(controller=controller, port=0, log_level="off")
    server.start_background(open_browser=False)
    browser: Browser | None = None
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server.url)
            _refresh(page)
            captures = _capture_panes(page, artifact_root)
            dom_summary = _collect_dom_summary(page)
            _compose_sheet(artifact_root, captures)
            payload = {
                "project_path": str(project_path),
                "primary_video": str(primary_video),
                "added_videos": [str(path) for path in added_videos],
                "captures": captures,
                "state": state_summary,
                "dom": dom_summary,
            }
            (artifact_root / "audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(json.dumps(payload, indent=2))
    finally:
        app.quit()
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
