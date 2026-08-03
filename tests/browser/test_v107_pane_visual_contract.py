from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController
from tests.browser.helpers.video_test_helpers import create_project

PANE_TO_TOOL = {
    "media": "media",
    "merge": "merge",
    "trim-sync": "trim-sync",
    "queue": "queue",
}


def _prepare_populated_project(page, primary: Path, added: Path, project_path: Path) -> None:
    create_project(page, str(project_path))
    page.evaluate("() => callApi('/api/project/stage/create', {})")
    page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
    page.evaluate(
        "(path) => callApi('/api/project/stage/import-primary', { stage_id: state.project.active_stage_id, path })",
        str(primary),
    )
    page.evaluate(
        "(path) => callApi('/api/project/stage/import-added', { stage_id: state.project.active_stage_id, path })",
        str(added),
    )
    page.evaluate(
        "() => callApi('/api/project/queue/add', { stage_id: state.project.active_stage_id })"
    )
    page.wait_for_function(
        "() => Boolean(state?.project?.primary_video?.path)"
        " && state.project.merge_sources.length === 1"
        " && state.project.queue.some((entry) => entry.status === 'queued')"
    )


def _layout_metrics(page, pane_name: str) -> dict:
    return page.locator(f'[data-tool-pane="{pane_name}"]').evaluate(
        """(pane) => {
          const visible = (element) => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
          };
          const rect = (element) => element.getBoundingClientRect();
          const paneRect = rect(pane);
          const overflows = [...pane.querySelectorAll('button, input, select, article, section')]
            .filter(visible)
            .filter((element) => {
              const box = rect(element);
              return box.left < paneRect.left - 1 || box.right > paneRect.right + 1;
            })
            .map((element) => element.id || element.className || element.tagName);
          if (pane.scrollWidth - pane.clientWidth > 1) overflows.push('pane-scroll-width');
          const labelGaps = [...pane.querySelectorAll('label:not(.check-row)')]
            .filter(visible)
            .map((label) => {
              const control = label.querySelector(':scope > input, :scope > select, :scope > .pip-size-control, :scope > .opacity-percent-field');
              if (!control || !visible(control)) return null;
              const textNode = [...label.childNodes].find((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
              const caption = label.querySelector(':scope > span');
              let textRect = caption ? rect(caption) : null;
              if (!textRect && textNode) {
                const range = document.createRange();
                range.selectNodeContents(textNode);
                textRect = range.getBoundingClientRect();
              }
              return textRect ? rect(control).top - textRect.bottom : null;
            })
            .filter((value) => value !== null);
          const groupSelectors = [
            '.media-asset-actions', '.media-pane-actions', '.trim-card-actions',
            '.trim-card-row-quick', '.trim-global-actions', '.trim-sync-nudge-buttons',
            '.queue-process-actions'
          ];
          const buttonGaps = groupSelectors.flatMap((selector) =>
            [...pane.querySelectorAll(selector)].filter(visible).flatMap((group) => {
              const buttons = [...group.querySelectorAll(':scope > button')].filter(visible).map(rect);
              const gaps = [];
              for (let index = 0; index < buttons.length; index += 1) {
                for (let next = index + 1; next < buttons.length; next += 1) {
                  const left = buttons[index];
                  const right = buttons[next];
                  const horizontalOverlap = Math.min(left.right, right.right) - Math.max(left.left, right.left);
                  const verticalOverlap = Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top);
                  if (verticalOverlap > 0) gaps.push(Math.max(right.left - left.right, left.left - right.right));
                  else if (horizontalOverlap > 0) gaps.push(Math.max(right.top - left.bottom, left.top - right.bottom));
                }
              }
              return gaps;
            })
          );
          const cardGaps = ['.media-asset-row', '.merge-media-card', '.trim-source-card', '.queue-stage-card']
            .flatMap((selector) => {
              const cards = [...pane.querySelectorAll(selector)].filter(visible).map(rect).sort((a, b) => a.top - b.top);
              return cards.slice(1).map((card, index) => card.top - cards[index].bottom);
            });
          const linePositions = [...pane.querySelectorAll('.settings-section, .pip-defaults-section, .section-header')]
            .filter(visible)
            .flatMap((element) => {
              const style = getComputedStyle(element);
              const box = rect(element);
              const lines = [];
              if (parseFloat(style.borderTopWidth) > 0) lines.push(box.top);
              if (parseFloat(style.borderBottomWidth) > 0) lines.push(box.bottom);
              return lines;
            })
            .sort((a, b) => a - b);
          const lineGaps = linePositions.slice(1).map((line, index) => line - linePositions[index]);
          const opacityInput = pane.querySelector('.opacity-percent-input');
          const opacitySuffix = pane.querySelector('.opacity-percent-suffix');
          const suffixGap = opacityInput && opacitySuffix && visible(opacityInput) && visible(opacitySuffix)
            ? rect(opacitySuffix).left - rect(opacityInput).right
            : null;
          const atomicElements = [...pane.querySelectorAll(
            'button, input, select, output, .pane-status-text, .queue-status-text, .opacity-percent-suffix'
          )].filter(visible);
          const overlaps = [];
          for (let index = 0; index < atomicElements.length; index += 1) {
            for (let next = index + 1; next < atomicElements.length; next += 1) {
              const leftElement = atomicElements[index];
              const rightElement = atomicElements[next];
              if (leftElement.contains(rightElement) || rightElement.contains(leftElement)) continue;
              const left = rect(leftElement);
              const right = rect(rightElement);
              const overlapX = Math.min(left.right, right.right) - Math.max(left.left, right.left);
              const overlapY = Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top);
              if (overlapX > 0.5 && overlapY > 0.5) {
                overlaps.push([
                  leftElement.id || leftElement.className || leftElement.tagName,
                  rightElement.id || rightElement.className || rightElement.tagName,
                ]);
              }
            }
          }
          return { overflows, labelGaps, buttonGaps, cardGaps, lineGaps, suffixGap, overlaps };
        }"""
    )


def test_four_panes_hold_og_spacing_at_supported_inspector_widths(
    synthetic_video_factory,
) -> None:
    primary = Path(synthetic_video_factory(name="visual-primary", beep_ms=380))
    added = Path(synthetic_video_factory(name="visual-added", beep_ms=410))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            try:
                page.goto(server.url, wait_until="domcontentloaded")
                _prepare_populated_project(
                    page, primary, added, primary.parent / "visual-contract.ssproj"
                )
                for width in (360, 520, 640):
                    page.evaluate(
                        "(width) => document.documentElement.style.setProperty('--inspector-width', `${width}px`)",
                        width,
                    )
                    assert page.locator(".inspector").evaluate(
                        "(element, expected) => Math.abs(element.getBoundingClientRect().width - expected) < 0.5",
                        width,
                    )
                    for pane_name, tool_name in PANE_TO_TOOL.items():
                        page.locator(f'button[data-tool="{tool_name}"]').click(force=True)
                        metrics = _layout_metrics(page, pane_name)
                        assert not metrics["overflows"], (width, pane_name, metrics["overflows"])
                        assert not metrics["overlaps"], (width, pane_name, metrics["overlaps"])
                        assert all(gap >= 6 for gap in metrics["labelGaps"]), (
                            width,
                            pane_name,
                            metrics["labelGaps"],
                        )
                        assert all(gap >= 8 for gap in metrics["buttonGaps"]), (
                            width,
                            pane_name,
                            metrics["buttonGaps"],
                        )
                        assert all(gap >= 8 for gap in metrics["cardGaps"]), (
                            width,
                            pane_name,
                            metrics["cardGaps"],
                        )
                        assert all(gap == 0 or gap >= 8 for gap in metrics["lineGaps"]), (
                            width,
                            pane_name,
                            metrics["lineGaps"],
                        )
                        if metrics["suffixGap"] is not None:
                            assert metrics["suffixGap"] >= 6

                page.locator('button[data-tool="trim-sync"]').click(force=True)
                inspector = page.locator(".inspector")
                inspector.evaluate("element => { element.scrollTop = element.scrollHeight; }")
                assert page.locator(".trim-source-card").last.is_visible()
                assert inspector.evaluate(
                    "element => element.scrollTop + element.clientHeight >= element.scrollHeight - 1"
                )

                green_buttons = page.evaluate(
                    """() => [...document.querySelectorAll(
                      '[data-tool-pane="media"] button, [data-tool-pane="merge"] button, '
                      + '[data-tool-pane="trim-sync"] button, [data-tool-pane="queue"] button'
                    )].filter((button) => getComputedStyle(button).backgroundColor === 'rgb(57, 208, 111)')
                      .map((button) => button.textContent.trim()).sort()"""
                )
                assert green_buttons == ["Add Media", "Add Stage", "Process as One File"]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_create_and_open_actions_fill_the_inspector_evenly() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            try:
                page.goto(server.url, wait_until="domcontentloaded")
                page.locator('button[data-tool="project"]').click(force=True)

                for width in (400, 520, 640):
                    page.evaluate(
                        "(value) => document.documentElement.style.setProperty('--inspector-width', `${value}px`)",
                        width,
                    )
                    geometry = page.locator(".project-action-grid").evaluate(
                        """(grid) => {
                          const create = document.querySelector('#new-project').getBoundingClientRect();
                          const open = document.querySelector('#open-project').getBoundingClientRect();
                          const remove = document.querySelector('#delete-project').getBoundingClientRect();
                          const bounds = grid.getBoundingClientRect();
                          return {
                            createWidth: create.width,
                            openWidth: open.width,
                            createLeftGap: create.left - bounds.left,
                            openRightGap: bounds.right - open.right,
                            deleteLeftGap: remove.left - bounds.left,
                            deleteRightGap: bounds.right - remove.right,
                          };
                        }"""
                    )
                    assert abs(geometry["createWidth"] - geometry["openWidth"]) < 0.5
                    assert geometry["createWidth"] > 0
                    assert abs(geometry["createLeftGap"]) < 0.5
                    assert abs(geometry["openRightGap"]) < 0.5
                    assert abs(geometry["deleteLeftGap"]) < 0.5
                    assert abs(geometry["deleteRightGap"]) < 0.5
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_overlay_alpha_controls_keep_number_stepper_and_suffix_separated() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            try:
                page.goto(server.url, wait_until="domcontentloaded")
                create_project(page, str(Path("tmp/codex/alpha-spacing.ssproj").resolve()))
                page.evaluate("() => callApi('/api/project/stage/create', {})")
                page.locator('button[data-tool="overlay"]').click(force=True)

                for width in (360, 520, 640):
                    page.evaluate(
                        "(value) => document.documentElement.style.setProperty('--inspector-width', `${value}px`)",
                        width,
                    )
                    fields = page.locator('[data-tool-pane="overlay"] .opacity-percent-field')
                    assert fields.count() == 4
                    for index in range(fields.count()):
                        geometry = fields.nth(index).evaluate(
                            """(field) => {
                              const input = field.querySelector('.opacity-percent-input');
                              const suffix = field.querySelector('.opacity-percent-suffix');
                              const inputRect = input.getBoundingClientRect();
                              const suffixRect = suffix.getBoundingClientRect();
                              const style = getComputedStyle(input);
                              return {
                                gap: suffixRect.left - inputRect.right,
                                rightPadding: parseFloat(style.paddingRight),
                                textAlign: style.textAlign,
                                overflow: inputRect.right > field.getBoundingClientRect().right + 1,
                              };
                            }"""
                        )
                        assert geometry["gap"] >= 12
                        assert geometry["rightPadding"] >= 44
                        assert geometry["textAlign"] == "left"
                        assert geometry["overflow"] is False
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_imported_stage_review_summary_is_populated_without_manual_reentry() -> None:
    controller = ProjectController()
    practiscore_path = Path("example_data/IDPA/IDPA.csv").resolve()
    controller.import_practiscore_file(str(practiscore_path), source_name="IDPA.csv")
    stage = next(item for item in controller.project.stages if item.imported_stage_number == 3)
    controller.select_stage(stage.id)
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            try:
                page.goto(server.url, wait_until="domcontentloaded")
                page.locator('button[data-tool="review"]').click(force=True)
                card = page.locator(".text-box-card").filter(has_text="Summary").first
                card.locator('[data-text-box-action="toggle"]').click()
                page.wait_for_function(
                    """() => {
                      const card = document.querySelector('.text-box-card');
                      return card
                        && card.querySelectorAll('[data-summary-metric]').length >= 3
                        && card.querySelector('[data-text-box-preview]')?.value.includes('Overall - ');
                    }"""
                )
                imported = page.evaluate("state.project.scoring.imported_stage")
                preview = card.locator("[data-text-box-preview]").input_value()
                assert f"{imported['division']} - " in preview
                assert f"{imported['classification']} - " in preview
                assert "Overall - " in preview
                assert card.locator("[data-summary-metric]:checked").count() >= 3
            finally:
                browser.close()
    finally:
        server.shutdown()
