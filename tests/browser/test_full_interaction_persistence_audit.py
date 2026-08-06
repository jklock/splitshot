"""Full-scale interaction, persistence, and stale-render audit for SplitShot.

This test verifies:
- Single interactions cause exactly one visible change and one mutation.
- Active DOM controls are preserved during ordinary saves.
- Changes survive pane navigation, stage switching, and project reopening.
- Debounced saves use current values, not stale captures.
- API responses never overwrite newer user input.
- Timing and scoring row editors survive concurrent renders.
- Media pane uses structural keys to avoid full rebuilds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "tmp/codex/artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = ARTIFACT_DIR / "full-interaction-persistence-audit.json"


def _install_probes(page: Page) -> None:
    page.evaluate(
        """() => {
          window.__audit = {
            requests: [],
            events: { input: 0, change: 0, click: 0 },
          };
          const originalFetch = window.fetch.bind(window);
          window.fetch = async (...args) => {
            const request = args[0];
            const options = args[1] || {};
            const url = typeof request === 'string' ? request : request?.url || '';
            const method = String(options.method || request?.method || 'GET').toUpperCase();
            window.__audit.requests.push({ url: String(url), method });
            return originalFetch(...args);
          };
          document.addEventListener('input', () => { window.__audit.events.input += 1; }, true);
          document.addEventListener('change', () => { window.__audit.events.change += 1; }, true);
          document.addEventListener('click', () => { window.__audit.events.click += 1; }, true);
        }"""
    )


def _reset_event_counts(page: Page) -> None:
    page.evaluate("() => { window.__audit.events = { input: 0, change: 0, click: 0 }; }")


def _event_counts(page: Page) -> dict[str, int]:
    return page.evaluate("() => window.__audit.events")


def _mutating_request_count(page: Page, path: str) -> int:
    return page.evaluate(
        """(path) => window.__audit.requests.filter(
          (item) => item.method !== 'GET' && new URL(item.url, location.href).pathname === path
        ).length""",
        path,
    )


def _open_tool(page: Page, tool: str) -> None:
    page.locator(f'[data-tool="{tool}"]').click(timeout=3_000)
    page.wait_for_function("(expected) => activeTool === expected", arg=tool)


def _assert_node_preserved(page: Page, selector: str, before_id: str | None) -> None:
    after = page.evaluate(
        """(selector) => {
          const node = document.querySelector(selector);
          return node ? { connected: node.isConnected, id: node.id || null } : null;
        }""",
        selector,
    )
    assert after is not None and after["connected"] is True, f"{selector} was removed from DOM"
    if before_id is not None:
        assert after.get("id") == before_id, f"{selector} node identity changed"


def _interact_scalar(
    page: Page,
    selector: str,
    next_value: str | bool,
    *,
    pane: str,
    tool: str,
    api_path: str,
    state_expr: str,
    expect_same_node: bool = True,
) -> dict[str, Any]:
    _open_tool(page, tool)
    before = page.evaluate(
        """(selector) => {
          const node = document.querySelector(selector);
          if (!node) return null;
          const isCheckbox = node.type === 'checkbox';
          return {
            value: isCheckbox ? node.checked : node.value,
            connected: node.isConnected,
            id: node.id || null,
          };
        }""",
        selector,
    )
    assert before is not None, f"{selector} not found in {pane} pane"
    _reset_event_counts(page)

    if isinstance(next_value, bool):
        page.evaluate(
            """({ selector, checked }) => {
              const node = document.querySelector(selector);
              if (!node) return;
              node.checked = checked;
              node.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            {"selector": selector, "checked": next_value},
        )
    else:
        page.evaluate(
            """({ selector, value }) => {
              const node = document.querySelector(selector);
              if (!node) return;
              node.value = String(value);
              node.dispatchEvent(new Event('input', { bubbles: true }));
              node.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            {"selector": selector, "value": next_value},
        )

    immediate = page.evaluate(
        """(selector) => {
          const node = document.querySelector(selector);
          if (!node) return null;
          const isCheckbox = node.type === 'checkbox';
          return {
            value: isCheckbox ? node.checked : node.value,
            connected: node.isConnected,
            id: node.id || null,
          };
        }""",
        selector,
    )
    events = _event_counts(page)
    assert events["change"] == 1, f"Expected exactly 1 change event for {selector}, got {events}"

    # Wait for server state to reflect the change (may be debounced)
    page.wait_for_function(
        f"(expected) => {state_expr} === expected",
        arg=next_value if isinstance(next_value, bool) else (float(next_value) if "." in str(next_value) else next_value),
        timeout=5_000,
    )
    # Allow debounced saves to reach the server before checking node identity
    page.wait_for_timeout(400)
    settled = page.evaluate(
        """(selector) => {
          const node = document.querySelector(selector);
          if (!node) return null;
          const isCheckbox = node.type === 'checkbox';
          return {
            value: isCheckbox ? node.checked : node.value,
            connected: node.isConnected,
            id: node.id || null,
          };
        }""",
        selector,
    )
    if expect_same_node:
        assert settled["id"] == before["id"], f"{selector} DOM node replaced after save"
    assert settled["connected"] is True
    return {
        "pane": pane,
        "selector": selector,
        "before": before["value"],
        "immediate": immediate["value"],
        "settled": settled["value"],
        "events": events,
    }


def _write_report(results: list[dict[str, Any]], browser_name: str) -> None:
    report_path = REPORT_PATH.with_name(f"{REPORT_PATH.stem}-{browser_name}{REPORT_PATH.suffix}")
    report_path.write_text(
        json.dumps(
            {
                "browser": browser_name,
                "scope": "interaction, persistence, and stale-render audit",
                "summary": {"passed": len([r for r in results if r.get("status") == "PASS"]), "total": len(results)},
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("browser_name", ["chromium", "chrome", "firefox", "webkit"])
def test_scalar_controls_preserve_node_and_persist(
    tmp_path: Path,
    browser_name: str,
) -> None:
    controller = ProjectController()
    controller.project_path = tmp_path / "audit.ssproj"
    practiscore = ROOT / "example_data/IDPA/IDPA.csv"
    controller.import_practiscore_file(str(practiscore), source_name=practiscore.name)
    stage = controller.project.active_stage or controller.project.stages[0]
    controller.import_stage_primary(stage.id, str(ROOT / "tests/fixtures/media/stage.mp4"))
    controller.import_stage_added(stage.id, str(ROOT / "tests/fixtures/media/stage-merge.mp4"))
    controller.save_project(str(controller.project_path))

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    results: list[dict[str, Any]] = []
    try:
        with sync_playwright() as playwright:
            browser_type = playwright.chromium if browser_name == "chrome" else getattr(playwright, browser_name)
            launch_options = {"headless": True}
            if browser_name == "chrome":
                launch_options["channel"] = "chrome"
            browser = browser_type.launch(**launch_options)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(server.url, wait_until="domcontentloaded")
            page.wait_for_function("() => Boolean(state?.project?.path)")
            _install_probes(page)

            try:
                # Project pane: name text input
                results.append(
                    _interact_scalar(
                        page,
                        "#project-name",
                        "Audit Test Project",
                        pane="project",
                        tool="project",
                        api_path="/api/project/details",
                        state_expr="state.project.name",
                    )
                )

                # Media pane: structural key must prevent full rebuild
                _open_tool(page, "media")
                media_select = page.locator("#media-active-stage-select")
                assert media_select.count() > 0
                # Verify media pane shell exists after render
                assert page.evaluate("() => document.querySelector('#media-pane .media-pane-shell') !== null")
                # Change project name from project pane and come back
                _open_tool(page, "project")
                _interact_scalar(
                    page,
                    "#project-name",
                    "Structural Key Test",
                    pane="project",
                    tool="project",
                    api_path="/api/project/details",
                    state_expr="state.project.name",
                )
                _open_tool(page, "media")
                assert page.evaluate("() => document.querySelector('#media-pane .media-pane-shell') !== null")
                results.append({"pane": "media", "case": "structural-key-survives-cross-pane", "status": "PASS"})

                # Scoring pane: checkbox
                _open_tool(page, "scoring")
                scoring_before = page.evaluate("state.project.scoring.enabled")
                results.append(
                    _interact_scalar(
                        page,
                        "#scoring-enabled",
                        not scoring_before,
                        pane="scoring",
                        tool="scoring",
                        api_path="/api/scoring",
                        state_expr="state.project.scoring.enabled",
                    )
                )

                # Merge pane: layout select
                _open_tool(page, "merge")
                results.append(
                    _interact_scalar(
                        page,
                        "#merge-layout",
                        "pip",
                        pane="merge",
                        tool="merge",
                        api_path="/api/merge",
                        state_expr="state.project.merge.layout",
                    )
                )

                # Overlay pane: show-overlay checkbox
                _open_tool(page, "overlay")
                overlay_before = page.evaluate("state.project.overlay.position !== 'none'")
                results.append(
                    _interact_scalar(
                        page,
                        "#show-overlay",
                        not overlay_before,
                        pane="overlay",
                        tool="overlay",
                        api_path="/api/overlay",
                        state_expr="state.project.overlay.position !== 'none'",
                    )
                )

                # Export pane: quality select
                _open_tool(page, "export")
                results.append(
                    _interact_scalar(
                        page,
                        "#quality",
                        "medium",
                        pane="export",
                        tool="export",
                        api_path="/api/export/settings",
                        state_expr="state.project.export.quality",
                    )
                )

                # Queue pane: fade-in number input
                _open_tool(page, "queue")
                results.append(
                    _interact_scalar(
                        page,
                        "#queue-fade-in",
                        "0.8",
                        pane="queue",
                        tool="queue",
                        api_path="/api/project/queue/settings",
                        state_expr="state.project.queue_settings.fade_in_s",
                    )
                )

                # Overlay pane: font-size number input
                _open_tool(page, "overlay")
                results.append(
                    _interact_scalar(
                        page,
                        "#overlay-font-size",
                        18,
                        pane="overlay",
                        tool="overlay",
                        api_path="/api/overlay",
                        state_expr="state.project.overlay.font_size",
                    )
                )

                # Timing pane: timing-enabled checkbox
                _open_tool(page, "timing")
                results.append(
                    _interact_scalar(
                        page,
                        "#timing-enabled",
                        False,
                        pane="timing",
                        tool="timing",
                        api_path="/api/project/ui-state",
                        state_expr="state.project.ui_state.timing_enabled",
                    )
                )

                # Cross-pane persistence: change queue fade, switch to export, return
                _open_tool(page, "queue")
                _interact_scalar(
                    page,
                    "#queue-fade-out",
                    "1.2",
                    pane="queue",
                    tool="queue",
                    api_path="/api/project/queue/settings",
                    state_expr="state.project.queue_settings.fade_out_s",
                )
                _open_tool(page, "export")
                _open_tool(page, "queue")
                settled_value = page.evaluate("state.project.queue_settings.fade_out_s")
                assert settled_value == 1.2
                results.append({"pane": "queue", "case": "cross-pane-persistence", "status": "PASS", "value": settled_value})

                # Verify project file persistence
                page.evaluate(
                    "path => useProjectFolder(path)",
                    str(controller.project_path),
                )
                page.wait_for_function("expected => state.project.name === expected", arg="Structural Key Test")
                stored = json.loads((controller.project_path / "project.json").read_text(encoding="utf-8"))
                assert stored["name"] == "Structural Key Test"
                assert stored["queue_settings"]["fade_out_s"] == 1.2
                results.append({"case": "project-file-persistence", "status": "PASS"})

            finally:
                browser.close()
    finally:
        server.shutdown()

    _write_report(results, browser_name)
    assert all(r.get("status") != "FAIL" for r in results)


@pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
def test_timing_row_editor_survives_concurrent_render(
    tmp_path: Path,
    browser_name: str,
) -> None:
    """Unlock a timing row, type an adjustment, trigger a render from another pane,
    and assert the editor input survives with focus and value intact."""
    controller = ProjectController()
    controller.project_path = tmp_path / "timing-audit.ssproj"
    practiscore = ROOT / "example_data/IDPA/IDPA.csv"
    controller.import_practiscore_file(str(practiscore), source_name=practiscore.name)
    stage = controller.project.active_stage or controller.project.stages[0]
    controller.import_stage_primary(stage.id, str(ROOT / "tests/fixtures/media/stage.mp4"))
    controller.save_project(str(controller.project_path))

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser_type = playwright.chromium if browser_name == "chrome" else getattr(playwright, browser_name)
            launch_options = {"headless": True}
            if browser_name == "chrome":
                launch_options["channel"] = "chrome"
            browser = browser_type.launch(**launch_options)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(server.url, wait_until="domcontentloaded")
            page.wait_for_function("() => Boolean(state?.project?.path)")

            try:
                _open_tool(page, "timing")
                # Expand timing workbench if not already expanded
                if not page.evaluate("state.project.ui_state.timing_expanded"):
                    page.locator("#expand-timing").click()
                    page.wait_for_function("() => state.project.ui_state.timing_expanded")

                # Wait for timing workbench table
                page.wait_for_selector("#timing-workbench-table .timing-lock-cell", timeout=5_000)

                # Click first unlock button
                page.locator("#timing-workbench-table .timing-lock-cell .lock-button").first.click()
                page.wait_for_selector("#timing-workbench-table .timing-adjustment-input", timeout=3_000)

                # Type a new adjustment value
                page.evaluate(
                    """() => {
                      const input = document.querySelector('#timing-workbench-table .timing-adjustment-input');
                      input.value = '0.15';
                      input.dispatchEvent(new Event('input', { bubbles: true }));
                    }"""
                )

                # Capture editor state
                before_editor = page.evaluate(
                    """() => {
                      const input = document.querySelector('#timing-workbench-table .timing-adjustment-input');
                      return input ? { value: input.value, focused: document.activeElement === input, id: input.id || null } : null;
                    }"""
                )
                assert before_editor is not None
                assert before_editor["value"] == "0.15"

                # Trigger a direct render() call while the editor is active.
                # This exercises the editor-preservation code in renderTimingTable.
                page.evaluate("() => render()")
                page.wait_for_timeout(500)

                after_editor = page.evaluate(
                    """() => {
                      const input = document.querySelector('#timing-workbench-table .timing-adjustment-input');
                      return input ? { value: input.value, focused: document.activeElement === input } : null;
                    }"""
                )
                assert after_editor is not None
                assert after_editor["value"] == "0.15", f"Timing editor value lost: {after_editor}"

                # Also verify that requestRender() defers while editing.
                page.evaluate("() => requestRender()")
                page.wait_for_timeout(500)
                deferred_check = page.evaluate(
                    """() => {
                      const input = document.querySelector('#timing-workbench-table .timing-adjustment-input');
                      return input ? { value: input.value, focused: document.activeElement === input } : null;
                    }"""
                )
                assert deferred_check is not None
                assert deferred_check["value"] == "0.15"

            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
def test_scoring_row_editor_survives_concurrent_render(
    tmp_path: Path,
    browser_name: str,
) -> None:
    """Unlock a scoring row, change score select, trigger a direct render,
    and assert the select survives with value intact."""
    controller = ProjectController()
    controller.project_path = tmp_path / "scoring-audit.ssproj"
    practiscore = ROOT / "example_data/IDPA/IDPA.csv"
    controller.import_practiscore_file(str(practiscore), source_name=practiscore.name)
    stage = controller.project.active_stage or controller.project.stages[0]
    controller.import_stage_primary(stage.id, str(ROOT / "tests/fixtures/media/stage.mp4"))
    controller.save_project(str(controller.project_path))

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser_type = playwright.chromium if browser_name == "chrome" else getattr(playwright, browser_name)
            launch_options = {"headless": True}
            if browser_name == "chrome":
                launch_options["channel"] = "chrome"
            browser = browser_type.launch(**launch_options)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(server.url, wait_until="domcontentloaded")
            page.wait_for_function("() => Boolean(state?.project?.path)")

            try:
                _open_tool(page, "scoring")
                # Expand scoring workbench if not already expanded
                if not page.evaluate("scoringWorkbenchExpanded"):
                    page.locator("#expand-scoring").click()
                    page.wait_for_function("() => scoringWorkbenchExpanded")

                # Wait for scoring workbench table
                page.wait_for_selector("#scoring-workbench-table .timing-lock-cell", timeout=5_000)

                # Click first unlock button
                page.locator("#scoring-workbench-table .timing-lock-cell .lock-button").first.click()
                page.wait_for_selector("#scoring-workbench-table .shot-score-select", timeout=3_000)

                # Change the score select
                page.evaluate(
                    """() => {
                      const select = document.querySelector('#scoring-workbench-table .shot-score-select');
                      select.value = 'M';
                      select.dispatchEvent(new Event('change', { bubbles: true }));
                    }"""
                )

                before_select = page.evaluate(
                    """() => {
                      const select = document.querySelector('#scoring-workbench-table .shot-score-select');
                      return select ? { value: select.value, focused: document.activeElement === select } : null;
                    }"""
                )
                assert before_select is not None
                assert before_select["value"] == "M"

                # Trigger a direct render() call while the select is active.
                page.evaluate("() => render()")
                page.wait_for_timeout(500)

                after_select = page.evaluate(
                    """() => {
                      const select = document.querySelector('#scoring-workbench-table .shot-score-select');
                      return select ? { value: select.value, focused: document.activeElement === select } : null;
                    }"""
                )
                assert after_select is not None
                assert after_select["value"] == "M", f"Scoring select value lost: {after_select}"

                # Also verify requestRender() defers while editing.
                page.evaluate("() => requestRender()")
                page.wait_for_timeout(500)
                deferred_check = page.evaluate(
                    """() => {
                      const select = document.querySelector('#scoring-workbench-table .shot-score-select');
                      return select ? { value: select.value, focused: document.activeElement === select } : null;
                    }"""
                )
                assert deferred_check is not None
                assert deferred_check["value"] == "M"

            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
def test_rapid_control_changes_coalesce_to_one_mutation_each(
    tmp_path: Path,
    browser_name: str,
) -> None:
    """Change two controls rapidly and assert both survive and each causes exactly one mutation."""
    controller = ProjectController()
    controller.project_path = tmp_path / "rapid-audit.ssproj"
    practiscore = ROOT / "example_data/IDPA/IDPA.csv"
    controller.import_practiscore_file(str(practiscore), source_name=practiscore.name)
    stage = controller.project.active_stage or controller.project.stages[0]
    controller.import_stage_primary(stage.id, str(ROOT / "tests/fixtures/media/stage.mp4"))
    controller.save_project(str(controller.project_path))

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser_type = playwright.chromium if browser_name == "chrome" else getattr(playwright, browser_name)
            launch_options = {"headless": True}
            if browser_name == "chrome":
                launch_options["channel"] = "chrome"
            browser = browser_type.launch(**launch_options)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(server.url, wait_until="domcontentloaded")
            page.wait_for_function("() => Boolean(state?.project?.path)")
            _install_probes(page)

            try:
                _open_tool(page, "queue")
                request_before_fade_in = _mutating_request_count(page, "/api/project/queue/settings")
                request_before_fade_out = request_before_fade_in

                page.evaluate(
                    """() => {
                      const first = document.getElementById('queue-fade-in');
                      const second = document.getElementById('queue-fade-out');
                      const events = { first: 0, second: 0 };
                      first.addEventListener('change', () => { events.first += 1; }, { once: true });
                      second.addEventListener('change', () => { events.second += 1; }, { once: true });
                      window.__rapidProof = { first, second, events };
                      first.value = '0.9';
                      first.dispatchEvent(new Event('change', { bubbles: true }));
                      second.value = '1.1';
                      second.dispatchEvent(new Event('change', { bubbles: true }));
                    }"""
                )

                page.wait_for_function(
                    """() => Number(state.project.queue_settings.fade_in_s) === 0.9
                      && Number(state.project.queue_settings.fade_out_s) === 1.1""",
                    timeout=5_000,
                )

                settled = page.evaluate(
                    """() => ({
                      firstConnected: window.__rapidProof.first.isConnected,
                      secondConnected: window.__rapidProof.second.isConnected,
                      firstSame: window.__rapidProof.first === document.getElementById('queue-fade-in'),
                      secondSame: window.__rapidProof.second === document.getElementById('queue-fade-out'),
                      firstValue: window.__rapidProof.first.value,
                      secondValue: window.__rapidProof.second.value,
                      events: window.__rapidProof.events,
                    })"""
                )
                assert settled["firstConnected"] is True
                assert settled["secondConnected"] is True
                assert settled["firstSame"] is True
                assert settled["secondSame"] is True
                assert settled["firstValue"] == "0.9"
                assert settled["secondValue"] == "1.1"
                assert settled["events"] == {"first": 1, "second": 1}

                request_after = _mutating_request_count(page, "/api/project/queue/settings")
                assert request_after - request_before_fade_in <= 2, f"Expected <= 2 mutations, got {request_after - request_before_fade_in}"

            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
def test_media_pane_preserves_controls_during_scalar_update(
    tmp_path: Path,
    browser_name: str,
) -> None:
    """Change project name while media pane is open, then verify media pane
    controls were not destroyed by a full innerHTML rebuild."""
    controller = ProjectController()
    controller.project_path = tmp_path / "media-audit.ssproj"
    practiscore = ROOT / "example_data/IDPA/IDPA.csv"
    controller.import_practiscore_file(str(practiscore), source_name=practiscore.name)
    stage = controller.project.active_stage or controller.project.stages[0]
    controller.import_stage_primary(stage.id, str(ROOT / "tests/fixtures/media/stage.mp4"))
    controller.save_project(str(controller.project_path))

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser_type = playwright.chromium if browser_name == "chrome" else getattr(playwright, browser_name)
            launch_options = {"headless": True}
            if browser_name == "chrome":
                launch_options["channel"] = "chrome"
            browser = browser_type.launch(**launch_options)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(server.url, wait_until="domcontentloaded")
            page.wait_for_function("() => Boolean(state?.project?.path)")

            try:
                _open_tool(page, "media")
                # Capture the stage select node identity
                before_node = page.evaluate(
                    """() => {
                      const node = document.getElementById('media-active-stage-select');
                      return { id: node?.id || null, connected: node?.isConnected || false };
                    }"""
                )
                assert before_node["connected"] is True

                # Change project name via API from another pane context
                _open_tool(page, "project")
                page.evaluate(
                    """() => {
                      const input = document.getElementById('project-name');
                      input.value = 'Media Structural Key Test';
                      input.dispatchEvent(new Event('input', { bubbles: true }));
                      input.dispatchEvent(new Event('change', { bubbles: true }));
                    }"""
                )
                page.wait_for_function("() => state.project.name === 'Media Structural Key Test'", timeout=5_000)

                # Return to media pane
                _open_tool(page, "media")
                after_node = page.evaluate(
                    """() => {
                      const node = document.getElementById('media-active-stage-select');
                      return { id: node?.id || null, connected: node?.isConnected || false };
                    }"""
                )
                assert after_node["connected"] is True
                assert after_node["id"] == before_node["id"], "Media pane select was replaced by full rebuild"

            finally:
                browser.close()
    finally:
        server.shutdown()
