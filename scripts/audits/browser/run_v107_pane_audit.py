"""Capture pane proof against the real 05072026 project."""

from __future__ import annotations

import argparse
import json
from statistics import median
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
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts" / "v107-phase14-pane-audit"
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
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#current-file")
    page.wait_for_timeout(300)


def _wait_for_processing_bar(page: Page) -> None:
    page.wait_for_function(
        "() => document.getElementById('processing-bar')?.hidden === true", timeout=30_000
    )


def _wait_for_active_tool(page: Page, tool: str) -> None:
    page.wait_for_function(
        """
        (tool) => {
          const inspector = document.querySelector('.inspector');
          const pane = document.querySelector(`[data-tool-pane="${tool}"]`);
          return inspector?.dataset?.activeTool === tool && pane?.classList?.contains('active') === true;
        }
        """,
        arg=tool,
        timeout=10_000,
    )


def _set_tool(page: Page, tool: str) -> None:
    page.locator(f'[data-tool="{tool}"]').click()
    _wait_for_processing_bar(page)
    _wait_for_active_tool(page, tool)
    page.wait_for_timeout(200)


def _reset_inspector_scroll(page: Page) -> None:
    page.evaluate(
        """
        () => {
          const inspector = document.querySelector('.inspector');
          if (inspector instanceof HTMLElement) inspector.scrollTop = 0;
        }
        """
    )
    page.wait_for_timeout(150)


def _set_stage_expansion(page: Page, storage_key: str, expanded: bool, tool: str) -> None:
    page.evaluate(
        """
        ({ storageKey, expanded, tool }) => {
          const stageIds = Array.from(
            document.querySelectorAll('[data-stage-nav-id], [data-queue-stage-id]')
          ).map((element) => element.getAttribute('data-stage-nav-id') || element.getAttribute('data-queue-stage-id')).filter(Boolean);
          const value = Object.fromEntries(stageIds.map((stageId) => [stageId, expanded]));
          window.localStorage.setItem(storageKey, JSON.stringify(value));
          window.localStorage.setItem('splitshot.activeTool', tool);
        }
        """,
        {"storageKey": storage_key, "expanded": expanded, "tool": tool},
    )
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#current-file")
    page.locator(f'[data-tool="{tool}"]').click()
    _wait_for_processing_bar(page)
    _wait_for_active_tool(page, tool)
    page.wait_for_timeout(150)


def _prepare_review_capture(page: Page) -> None:
    page.wait_for_timeout(200)
    imported_button = page.locator("#review-add-imported-box")
    if imported_button.count() > 0 and imported_button.is_visible():
        imported_button.click()
        page.wait_for_timeout(250)
    first_toggle = page.locator(
        '#review-text-box-list .text-box-card [data-text-box-action="toggle"]'
    ).first
    if first_toggle.count() > 0 and first_toggle.is_visible():
        first_toggle.click()
        page.wait_for_timeout(150)
    try:
        first_card = page.locator("#review-text-box-list .text-box-card").first
        if first_card.count() > 0:
            first_card.scroll_into_view_if_needed()
    except Exception:
        pass
    page.wait_for_timeout(250)


def _prepare_capture_state(page: Page, tool: str) -> None:
    if tool == "project":
        _reset_inspector_scroll(page)
        return
    if tool == "media":
        _set_stage_expansion(page, "splitshot.media.stageExpanded", True, tool)
        _reset_inspector_scroll(page)
        return
    if tool == "queue":
        _set_stage_expansion(page, "splitshot.queue.stageExpanded", True, tool)
        _reset_inspector_scroll(page)
        return
    if tool == "review":
        _prepare_review_capture(page)
        return
    _reset_inspector_scroll(page)


def _capture_review_fallback(page: Page, artifact_root: Path) -> str:
    _set_tool(page, "review")
    _prepare_review_capture(page)
    page.wait_for_timeout(250)
    file_name = "review-fallback.png"
    page.screenshot(path=str(artifact_root / file_name))
    return file_name


def _prepare_controller_state(
    controller: ProjectController,
    project_path: Path,
    primary_video: Path,
    added_videos: list[Path],
) -> dict[str, object]:
    controller.open_project(str(project_path))
    stages = list(controller.project.stages)
    target_stage = next(
        (
            stage
            for stage in stages
            if int(getattr(stage, "order_index", 0) or 0) == 2
            or str(getattr(stage, "label", "")).strip().lower() == "stage 2"
        ),
        None,
    )
    if target_stage is None:
        target_stage = controller.project.active_stage or (stages[0] if stages else None)
    if target_stage is None:
        raise RuntimeError("No stage was available in 05072026.")
    controller.select_stage(target_stage.id)
    controller.project.queue.clear()
    for stage in controller.project.stages:
        stage.queue_status = QueueStatus.NOT_QUEUED
    stage = controller.project.active_stage
    if stage is None:
        raise RuntimeError("Active stage was not available.")
    stage.primary_media = probe_video(primary_video)
    stage.added_media = [MergeSource(asset=probe_video(video)) for video in added_videos]
    controller._sync_active_stage_to_project()
    controller.project.merge.enabled = False
    controller.project.active_stage.merge.enabled = False
    controller.analyze_primary()
    for source in controller.project.merge_sources:
        controller.analyze_secondary(source.id)
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
        _prepare_capture_state(page, tool)
        file_name = f"{tool}.png"
        path = artifact_root / file_name
        page.screenshot(path=str(path))
        results.append({"tool": tool, "title": TOOL_TITLES[tool], "file": file_name})
    return results


def _collect_dom_summary(page: Page) -> dict[str, object]:
    return page.evaluate(
        """
        () => {
          const px = (value) => {
            const parsed = Number.parseFloat(String(value || '').replace('px', '').trim());
            return Number.isFinite(parsed) ? parsed : 0;
          };
          const countColumns = (element) => {
            if (!(element instanceof HTMLElement)) return 0;
            const style = window.getComputedStyle(element);
            if (style.display !== 'grid') return 1;
            const template = String(style.gridTemplateColumns || '').trim();
            if (!template || template === 'none') return 0;
            let depth = 0;
            let token = '';
            const tracks = [];
            for (const char of template) {
              if (char === '(') depth += 1;
              if (char === ')') depth = Math.max(0, depth - 1);
              if (depth === 0 && /\\s/.test(char)) {
                if (token.trim()) tracks.push(token.trim());
                token = '';
                continue;
              }
              token += char;
            }
            if (token.trim()) tracks.push(token.trim());
            return tracks.reduce((count, track) => {
              const repeatMatch = track.match(/^repeat\\((\\d+),/);
              return count + (repeatMatch ? Number(repeatMatch[1]) : 1);
            }, 0);
          };
          const metricNumberList = (elements, picker) => elements.map((element) => picker(element)).filter((value) => Number.isFinite(value) && value > 0);
          const text = (selector) => document.querySelector(selector)?.textContent?.replace(/\\s+/g, ' ').trim() || '';
          const pane = (tool) => text(`[data-tool-pane="${tool}"]`);
          const paneElement = (tool) => document.querySelector(`[data-tool-pane="${tool}"]`);
          const titleElement = (tool) => paneElement(tool)?.querySelector('.pane-title-row h3, :scope > .section-header > h3');
          const summaryElement = (tool) => paneElement(tool)?.querySelector('.pane-title-row .pane-summary-token, .pane-title-row small');
          const paneMetrics = (tool) => {
            const root = paneElement(tool);
            if (!(root instanceof HTMLElement)) return null;
            const title = titleElement(tool);
            const summary = summaryElement(tool);
            const sectionHeaders = Array.from(root.querySelectorAll(':scope .section-header'))
              .filter((header) => header.closest('[data-tool-pane]') === root);
            const toggleButtons = Array.from(root.querySelectorAll('.scoring-shot-toggle'))
              .filter((button) => button.closest('[data-tool-pane]') === root);
            const controlGrids = Array.from(root.querySelectorAll('.control-grid, .trim-bulk-grid, .trim-card-row, .merge-source-controls, .media-stage-nav-actions, .queue-stage-actions'))
              .filter((element) => element.closest('[data-tool-pane]') === root);
            const cards = Array.from(root.querySelectorAll('.merge-media-card, .trim-source-card, .media-asset-row, .media-stage-nav-card, .queue-stage-card, .text-box-card'))
              .filter((element) => element.closest('[data-tool-pane]') === root);
            const labels = Array.from(root.querySelectorAll('label, .merge-source-field > span, .media-asset-copy span, .queue-stage-copy small, .trim-source-card-copy small'))
              .filter((element) => element.closest('[data-tool-pane]') === root);
            const sections = Array.from(root.querySelectorAll(':scope .settings-section > .section-header, :scope .pip-defaults-section > .section-header'))
              .map((header) => header.querySelector('h3, strong')?.textContent?.replace(/\\s+/g, ' ').trim() || '')
              .filter(Boolean);
            const titleRect = title instanceof HTMLElement ? title.getBoundingClientRect() : null;
            return {
              title_text: title?.textContent?.trim() || '',
              title_font_size_px: title instanceof HTMLElement ? px(window.getComputedStyle(title).fontSize) : 0,
              title_font_weight: title instanceof HTMLElement ? Number(window.getComputedStyle(title).fontWeight) || 0 : 0,
              title_line_height_px: title instanceof HTMLElement ? px(window.getComputedStyle(title).lineHeight) : 0,
              title_bottom_gap_px: titleRect ? Math.max(0, (summary instanceof HTMLElement ? summary.getBoundingClientRect().top : titleRect.bottom) - titleRect.bottom) : 0,
              summary_text: summary?.textContent?.trim() || '',
              summary_font_size_px: summary instanceof HTMLElement ? px(window.getComputedStyle(summary).fontSize) : 0,
              summary_right_offset_px: summary instanceof HTMLElement ? Math.max(0, root.getBoundingClientRect().right - summary.getBoundingClientRect().right) : 0,
              section_labels: sections,
              section_header_gap_px: metricNumberList(sectionHeaders, (header) => px(window.getComputedStyle(header).columnGap || window.getComputedStyle(header).gap)),
              section_vertical_gap_px: metricNumberList(sectionHeaders, (header) => px(window.getComputedStyle(header.parentElement || header).gap)),
              card_padding_px: metricNumberList(cards, (card) => px(window.getComputedStyle(card).paddingTop)),
              card_gap_px: metricNumberList(cards, (card) => px(window.getComputedStyle(card).gap)),
              label_font_size_px: metricNumberList(labels, (label) => px(window.getComputedStyle(label).fontSize)),
              input_height_px: metricNumberList(
                Array.from(root.querySelectorAll('input:not([type="checkbox"]):not([type="range"]), select, button[class*="btn"]'))
                  .filter((element) => element.closest('[data-tool-pane]') === root),
                (element) => element.getBoundingClientRect().height,
              ),
              control_column_counts: controlGrids.map((element) => ({
                class_name: element.className,
                column_count: countColumns(element),
              })),
              toggle_right_offsets_px: toggleButtons.map((button) => Math.max(0, root.getBoundingClientRect().right - button.getBoundingClientRect().right)),
            };
          };
          const mediaCards = Array.from(document.querySelectorAll('.media-stage-nav-card')).map((card) => ({
            label: card.querySelector('strong')?.textContent?.trim() || '',
            summary: card.querySelector('small')?.textContent?.trim() || '',
            selected: card.classList.contains('selected'),
          }));
          const queueCards = Array.from(document.querySelectorAll('.queue-stage-card')).map((card) => ({
            label: card.querySelector('strong')?.textContent?.trim() || '',
            meta: Array.from(card.querySelectorAll('small, .queue-status-pill')).map((item) => item.textContent?.trim() || ''),
            selected: card.classList.contains('selected'),
          }));
          const trimCards = Array.from(document.querySelectorAll('.trim-source-card')).map((card) => ({
            label: card.querySelector('strong')?.textContent?.trim() || '',
            meta: Array.from(card.querySelectorAll('small, .pane-summary-token')).map((item) => item.textContent?.trim() || ''),
          }));
          const duplicateTokens = (textValue) => {
            const tokens = (textValue.match(/\\b\\d+\\s+(?:asset|assets|added|queued|queue|source|sources)\\b/gi) || []).map((item) => item.toLowerCase());
            const counts = {};
            for (const token of tokens) counts[token] = (counts[token] || 0) + 1;
            return Object.entries(counts).filter(([, count]) => count > 1).map(([token]) => token);
          };
          const waveform = document.getElementById('waveform');
          const composeEnabled = document.getElementById('merge-enabled');
          const forbiddenHelperCopy = [
            'Keeps this box centered above the final score badge once it appears.',
            'Switch to Custom placement to edit X and Y directly.',
            'Choose the stage you are editing next',
            'Review the export settings already prepared',
          ].filter((token) => document.body.textContent?.includes(token));
          const headerSummaryToken = (selector) => document.querySelector(selector)?.textContent?.trim() || '';
          return {
            media_pane_text: pane('media'),
            trim_pane_text: pane('trim-sync'),
            queue_pane_text: pane('queue'),
            compose_pane_text: pane('merge'),
            project_pane_text: pane('project'),
            project_output_root_present: Boolean(document.getElementById('project-output-root')),
            export_path_controls_present: {
              browse: Boolean(document.getElementById('browse-export-path')),
              input: Boolean(document.getElementById('export-path')),
            },
            media_stage_cards: mediaCards,
            queue_cards: queueCards,
            trim_cards: trimCards,
            waveform_lane_count: Number(waveform?.dataset.waveformLaneCount || 0),
            waveform_lane_layout: waveform?.dataset.waveformLaneLayout || '',
            waveform_lane_clipping: waveform?.dataset.waveformLaneClipping || '',
            waveform_lane_bleed: waveform?.dataset.waveformLaneBleed || '',
            compose_merge_enabled: composeEnabled instanceof HTMLInputElement ? composeEnabled.checked : null,
            duplicate_summary_counts: {
              project: duplicateTokens(pane('project')),
              media: duplicateTokens(pane('media')),
              merge: duplicateTokens(pane('merge')),
              trim: duplicateTokens(pane('trim-sync')),
              queue: duplicateTokens(pane('queue')),
            },
            forbidden_helper_copy: forbiddenHelperCopy,
            media_header_text: text('#media-pane .pane-title-row h3'),
            media_header_summary: headerSummaryToken('#media-pane .pane-title-row .pane-summary-token'),
            queue_header_text: text('#queue-pane .pane-title-row h3'),
            queue_header_summary: headerSummaryToken('#queue-pane .pane-title-row .pane-summary-token'),
            trim_header_text: text('#trim-sync-pane .pane-title-row h3'),
            trim_header_summary: headerSummaryToken('#trim-sync-pane .pane-title-row .pane-summary-token'),
            media_toggle_count: document.querySelectorAll('.media-section-toggle').length,
            queue_toggle_count: document.querySelectorAll('.queue-stage-toggle').length,
            trim_toggle_count: document.querySelectorAll('[data-trim-toggle]').length,
            media_primary_button_count: document.querySelectorAll('.media-set-primary-btn').length,
            pane_metrics: {
              project: paneMetrics('project'),
              scoring: paneMetrics('scoring'),
              timing: paneMetrics('timing'),
              markers: paneMetrics('markers'),
              overlay: paneMetrics('overlay'),
              review: paneMetrics('review'),
              media: paneMetrics('media'),
              merge: paneMetrics('merge'),
              'trim-sync': paneMetrics('trim-sync'),
              queue: paneMetrics('queue'),
            },
          };
        }
        """
    )


def _median_or_zero(values: list[float]) -> float:
    cleaned = [float(value) for value in values if isinstance(value, (int, float)) and value > 0]
    return float(median(cleaned)) if cleaned else 0.0


def _compute_visual_parity(dom_summary: dict[str, object]) -> dict[str, object]:
    pane_metrics = dict(dom_summary.get("pane_metrics") or {})
    baseline_ids = ["project", "scoring", "timing", "markers", "overlay", "review"]
    touched_ids = ["media", "merge", "trim-sync", "queue"]
    baseline_metrics = [pane_metrics.get(tool) for tool in baseline_ids if pane_metrics.get(tool)]
    baseline = {
        "title_font_size_px": _median_or_zero(
            [item.get("title_font_size_px", 0) for item in baseline_metrics]
        ),
        "label_font_size_px": _median_or_zero(
            [
                _median_or_zero(list(item.get("label_font_size_px") or []))
                for item in baseline_metrics
            ]
        ),
        "card_padding_px": _median_or_zero(
            [_median_or_zero(list(item.get("card_padding_px") or [])) for item in baseline_metrics]
        ),
        "input_height_px": _median_or_zero(
            [_median_or_zero(list(item.get("input_height_px") or [])) for item in baseline_metrics]
        ),
        "toggle_right_offset_px": _median_or_zero(
            [
                _median_or_zero(list(item.get("toggle_right_offsets_px") or []))
                for item in baseline_metrics
            ]
        ),
    }
    expected_sections = {
        "media": ["Active Stage", "Primary", "Added Media", "Stages"],
        "merge": ["Stage Defaults"],
        "trim-sync": ["Bulk Trim", "Sources"],
    }
    allowed_multi_column = {
        "media": set(),
        "merge": set(),
        "trim-sync": {"trim-sync-nudge-buttons"},
        "queue": set(),
    }
    failures: list[dict[str, object]] = []
    per_pane: dict[str, object] = {}
    for tool in touched_ids:
        metrics = pane_metrics.get(tool) or {}
        pane_failures: list[str] = []
        title_size = float(metrics.get("title_font_size_px") or 0)
        label_size = _median_or_zero(list(metrics.get("label_font_size_px") or []))
        card_padding = _median_or_zero(list(metrics.get("card_padding_px") or []))
        input_height = _median_or_zero(list(metrics.get("input_height_px") or []))
        toggle_offset = _median_or_zero(list(metrics.get("toggle_right_offsets_px") or []))
        if abs(title_size - baseline["title_font_size_px"]) > 0.2:
            pane_failures.append(
                f"title font {title_size:.2f}px != baseline {baseline['title_font_size_px']:.2f}px"
            )
        if (
            label_size
            and baseline["label_font_size_px"]
            and abs(label_size - baseline["label_font_size_px"]) > 0.35
        ):
            pane_failures.append(
                f"label font {label_size:.2f}px != baseline {baseline['label_font_size_px']:.2f}px"
            )
        if (
            card_padding
            and baseline["card_padding_px"]
            and abs(card_padding - baseline["card_padding_px"]) > 2.5
        ):
            pane_failures.append(
                f"card padding drift {card_padding:.2f}px vs baseline {baseline['card_padding_px']:.2f}px"
            )
        if (
            input_height
            and baseline["input_height_px"]
            and abs(input_height - baseline["input_height_px"]) > 3.0
        ):
            pane_failures.append(
                f"control height drift {input_height:.2f}px vs baseline {baseline['input_height_px']:.2f}px"
            )
        if toggle_offset and toggle_offset > 24.0:
            pane_failures.append(
                f"toggle not right-aligned enough at {toggle_offset:.2f}px from pane edge"
            )
        if tool in expected_sections:
            labels = list(metrics.get("section_labels") or [])
            expected = expected_sections[tool]
            if labels[: len(expected)] != expected:
                pane_failures.append(f"section order {labels[: len(expected)]} != {expected}")
        disallowed_columns = [
            item
            for item in list(metrics.get("control_column_counts") or [])
            if int(item.get("column_count") or 0) > 1
            and not any(
                token in str(item.get("class_name") or "")
                for token in allowed_multi_column.get(tool, set())
            )
        ]
        if disallowed_columns:
            pane_failures.append(
                "unexpected multi-column controls: "
                + ", ".join(
                    f"{item.get('class_name')} ({item.get('column_count')})"
                    for item in disallowed_columns
                )
            )
        per_pane[tool] = {
            "title_font_size_px": title_size,
            "label_font_size_px": label_size,
            "card_padding_px": card_padding,
            "input_height_px": input_height,
            "toggle_right_offset_px": toggle_offset,
            "failures": pane_failures,
        }
        for failure in pane_failures:
            failures.append({"pane": tool, "failure": failure})

    helper_copy = list(dom_summary.get("forbidden_helper_copy") or [])
    if helper_copy:
        failures.append(
            {"pane": "global", "failure": f"forbidden helper copy present: {helper_copy}"}
        )
    duplicate_counts = dict(dom_summary.get("duplicate_summary_counts") or {})
    for pane_name, duplicates in duplicate_counts.items():
        if duplicates:
            failures.append(
                {"pane": pane_name, "failure": f"duplicate summary tokens: {duplicates}"}
            )
    if int(dom_summary.get("waveform_lane_count") or 0) < 3:
        failures.append({"pane": "waveform", "failure": "expected 3 waveform lanes"})
    if str(dom_summary.get("waveform_lane_bleed") or "").lower() != "false":
        failures.append({"pane": "waveform", "failure": "waveform bleed flag is not false"})
    if bool(dom_summary.get("compose_merge_enabled")):
        failures.append({"pane": "merge", "failure": "compose auto-enabled after media import"})
    return {"baseline": baseline, "per_pane": per_pane, "failures": failures}


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
            review_fallback_file = _capture_review_fallback(page, artifact_root)
            dom_summary = _collect_dom_summary(page)
            parity = _compute_visual_parity(dom_summary)
            _compose_sheet(artifact_root, captures)
            payload = {
                "project_path": str(project_path),
                "primary_video": str(primary_video),
                "added_videos": [str(path) for path in added_videos],
                "captures": captures,
                "focused_review_fallback": review_fallback_file,
                "state": state_summary,
                "dom": dom_summary,
                "visual_parity": parity,
            }
            (artifact_root / "audit.json").write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
            print(json.dumps(payload, indent=2))
            if parity["failures"]:
                raise RuntimeError(f"Pane visual parity audit failed: {parity['failures']}")
    finally:
        app.quit()
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
