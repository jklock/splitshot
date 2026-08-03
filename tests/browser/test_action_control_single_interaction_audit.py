from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "tmp/codex/artifacts/action-control-single-interaction-audit.json"


def _load_inventory_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        script = ROOT / "scripts/audits/browser/run_value_control_interaction_audit.py"
        spec = importlib.util.spec_from_file_location("splitshot_value_control_audit", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module.build_source_inventory(path)
    return json.loads(path.read_text(encoding="utf-8"))["controls"]


def _install_probe(page: Page) -> None:
    page.evaluate(
        """() => {
          window.__actionAuditRequests = [];
          const originalFetch = window.fetch.bind(window);
          window.fetch = async (...args) => {
            const request = args[0];
            const options = args[1] || {};
            const url = typeof request === 'string' ? request : request?.url || '';
            window.__actionAuditRequests.push({
              url: String(url),
              method: String(options.method || request?.method || 'GET').toUpperCase(),
            });
            return originalFetch(...args);
          };
        }"""
    )


def _click_once(
    page: Page, selector: str, *, occurrence: int = 0, expect_same_node: bool = True
) -> dict[str, Any]:
    armed = page.evaluate(
        """({ selector, occurrence }) => {
          const node = document.querySelectorAll(selector)[occurrence];
          if (!(node instanceof HTMLElement)) throw new Error(`Missing action ${selector}[${occurrence}]`);
          window.__actionAuditNode = node;
          window.__actionAuditCounts = { click: 0 };
          node.addEventListener('click', () => { window.__actionAuditCounts.click += 1; }, { once: true });
          return { connected: node.isConnected, disabled: Boolean(node.disabled), text: node.textContent.trim() };
        }""",
        {"selector": selector, "occurrence": occurrence},
    )
    assert armed["connected"] is True
    assert armed["disabled"] is False
    page.locator(selector).nth(occurrence).click(timeout=3_000)
    immediate = page.evaluate(
        """() => ({
          clickEvents: window.__actionAuditCounts.click,
          sameNodeConnected: Boolean(window.__actionAuditNode?.isConnected),
        })"""
    )
    assert immediate == {"clickEvents": 1, "sameNodeConnected": expect_same_node}
    return {"before": armed, "immediate": immediate}


def _request_count(page: Page, path: str) -> int:
    return page.evaluate(
        """(path) => window.__actionAuditRequests.filter(
          (item) => item.method !== 'GET' && new URL(item.url, location.href).pathname === path
        ).length""",
        path,
    )


def _open_tool_once(page: Page, tool: str) -> dict[str, Any]:
    selector = f'[data-tool="{tool}"]'
    proof = _click_once(page, selector)
    immediate = page.evaluate(
        """(tool) => ({
          activeTool,
          paneVisible: document.querySelector(`[data-tool-pane="${tool}"]`)?.hidden === false,
          focused: document.activeElement === document.querySelector(`[data-tool="${tool}"]`),
        })""",
        tool,
    )
    assert immediate["activeTool"] == tool
    assert immediate["paneVisible"] is True
    proof["after"] = immediate
    return proof


def _write_report(
    results: list[dict[str, Any]],
    inventory_rows: list[dict[str, Any]],
    browser_name: str,
) -> None:
    action_rows = [row for row in inventory_rows if row.get("tag") in {"button", "details", "video"}]
    covered = {result["inventory_identity"] for result in results}
    gaps = [
        {
            "inventory_identity": row["identity"],
            "file": row["file"],
            "line": row["line"],
            "status": "GAP",
            "reason": "not yet exercised by this action-control proof; remains explicitly unverified",
        }
        for row in action_rows
        if row["identity"] not in covered
    ]
    report_path = REPORT_PATH.with_name(
        f"{REPORT_PATH.stem}-{browser_name}{REPORT_PATH.suffix}"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "scope": "user-visible action controls only; ordinary scalar controls are audited separately",
                "browser": browser_name,
                "interaction_rule": "one Playwright click, immediate event count exactly one, no assertion action retries",
                "summary": {
                    "source_action_rows": len(action_rows),
                    "passed_runtime_cases": len(results),
                    "unique_covered_inventory_identities": len(covered),
                    "remaining_source_rows": len(gaps),
                },
                "results": results,
                "gaps": gaps,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("browser_name", ["chromium", "chrome", "firefox", "webkit"])
def test_action_controls_emit_one_click_and_make_one_intended_transition(
    tmp_path: Path,
    browser_name: str,
) -> None:
    inventory_path = ROOT / "tmp/codex/artifacts/complete-browser-control-source-inventory.json"
    inventory_rows = _load_inventory_rows(inventory_path)
    controller = ProjectController()
    controller.project_path = tmp_path / "action-proof.ssproj"
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
            _install_probe(page)
            try:
                # Every user-visible pane gets an independent, exactly-once rail proof.
                for tool in (
                    "project", "media", "merge", "trim-sync", "scoring", "timing", "markers",
                    "overlay", "review", "export", "intro-outro", "queue", "metrics", "shotml", "settings",
                ):
                    proof = _open_tool_once(page, tool)
                    results.append({"case": f"rail:{tool}", "pane": tool, "inventory_identity": f"[data-tool={tool}]", "status": "PASS", **proof})

                # Keyboard focus/activation is proved separately from pointer clicks.
                page.locator('[data-tool="project"]').focus()
                before_tool = page.evaluate("activeTool")
                page.keyboard.press("Enter")
                keyboard_after = page.evaluate("() => ({ activeTool, focused: document.activeElement?.dataset?.tool })")
                assert before_tool != "project"
                assert keyboard_after == {"activeTool": "project", "focused": "project"}
                results.append({"case": "keyboard:rail-enter", "pane": "project", "inventory_identity": "[data-tool=project]", "status": "PASS", "before": before_tool, "after": keyboard_after, "event_counts": {"keyboard": 1}})

                # Media stage tree/select and its component-only expanders.
                _open_tool_once(page, "media")
                before_stage = page.evaluate("state.project.active_stage_id")
                stage_options = page.locator("#media-active-stage-select option")
                assert stage_options.count() > 1, "fixture must expose at least two stage choices"
                if stage_options.count() > 1:
                    next_stage = stage_options.nth(1).get_attribute("value")
                    request_before = _request_count(page, "/api/project/select-stage")
                    stage_event = page.locator("#media-active-stage-select").evaluate(
                        """(node, value) => {
                          let changes = 0;
                          node.addEventListener('change', () => { changes += 1; }, { once: true });
                          node.value = value;
                          node.dispatchEvent(new Event('change', { bubbles: true }));
                          return { value: node.value, changes, connected: node.isConnected };
                        }""",
                        next_stage,
                    )
                    # A stage switch is an intentional structural pane rebuild; unlike an
                    # ordinary save, replacing this selector is allowed.
                    assert stage_event == {"value": next_stage, "changes": 1, "connected": False}
                    page.wait_for_function("id => state.project.active_stage_id === id", arg=next_stage)
                    immediate_stage = page.evaluate("state.project.active_stage_id")
                    assert immediate_stage == next_stage and immediate_stage != before_stage
                    request_after = _request_count(page, "/api/project/select-stage")
                    assert request_after - request_before == 1
                    results.append({"case": "media:stage-selection", "pane": "media", "inventory_identity": "id:media-active-stage-select", "status": "PASS", "before": before_stage, "immediate_visible": stage_event["value"], "intentional_structural_rebuild": True, "after": immediate_stage, "event_counts": {"change": 1}, "mutating_requests": 1})
                for section in ("primary", "added"):
                    selector = f'[data-media-section="{section}"]'
                    before_hidden = page.locator(selector).locator("xpath=ancestor::section[1]").locator(".media-pane-section-body").get_attribute("hidden") is not None
                    proof = _click_once(page, selector, expect_same_node=False)
                    after_hidden = page.locator(selector).locator("xpath=ancestor::section[1]").locator(".media-pane-section-body").get_attribute("hidden") is not None
                    assert after_hidden is not before_hidden
                    results.append({"case": f"media:toggle-{section}", "pane": "media", "inventory_identity": f"[data-media-section={section}]", "status": "PASS", "before": before_hidden, "after": after_hidden, **proof})

                # Queue membership is a single click and exactly one server mutation.
                _open_tool_once(page, "queue")
                queue_selector = f'.queue-membership-btn[data-stage-id="{stage.id}"]'
                before_queued = page.evaluate("(id) => state.project.queue.some((item) => item.stage_id === id)", stage.id)
                request_before = _request_count(page, "/api/project/queue/add") + _request_count(page, "/api/project/queue/remove")
                proof = _click_once(page, queue_selector)
                page.wait_for_function("([id, before]) => state.project.queue.some((item) => item.stage_id === id) !== before", arg=[stage.id, before_queued])
                after_queued = page.evaluate("(id) => state.project.queue.some((item) => item.stage_id === id)", stage.id)
                request_after = _request_count(page, "/api/project/queue/add") + _request_count(page, "/api/project/queue/remove")
                assert request_after - request_before == 1
                results.append({"case": "queue:membership", "pane": "queue", "inventory_identity": "[data-stage-id=${stageId}]", "status": "PASS", "before": before_queued, "after": after_queued, "mutating_requests": 1, **proof})

                # Two rapid scalar changes keep both live nodes and coalesce to
                # no more than one mutation per user action.
                page.evaluate(
                    """() => {
                      const first = document.getElementById('queue-fade-in');
                      const second = document.getElementById('queue-fade-out');
                      const events = { first: 0, second: 0 };
                      first.addEventListener('change', () => { events.first += 1; }, { once: true });
                      second.addEventListener('change', () => { events.second += 1; }, { once: true });
                      const firstValue = String(Number(first.value) + 0.1);
                      const secondValue = String(Number(second.value) + 0.2);
                      first.value = firstValue;
                      first.dispatchEvent(new Event('change', { bubbles: true }));
                      second.value = secondValue;
                      second.dispatchEvent(new Event('change', { bubbles: true }));
                      window.__actionFadeProof = { first, second, firstValue, secondValue, events };
                    }"""
                )
                page.wait_for_function(
                    """() => Number(state.project.queue_settings.fade_in_s) === 0.6
                      && Number(state.project.queue_settings.fade_out_s) === 0.7"""
                )
                settled_fades = page.evaluate(
                    """() => ({
                      firstConnected: window.__actionFadeProof.first.isConnected,
                      secondConnected: window.__actionFadeProof.second.isConnected,
                      firstSame: window.__actionFadeProof.first === document.getElementById('queue-fade-in'),
                      secondSame: window.__actionFadeProof.second === document.getElementById('queue-fade-out'),
                      firstValue: window.__actionFadeProof.first.value,
                      secondValue: window.__actionFadeProof.second.value,
                      events: window.__actionFadeProof.events,
                    })"""
                )
                assert settled_fades == {
                    "firstConnected": True,
                    "secondConnected": True,
                    "firstSame": True,
                    "secondSame": True,
                    "firstValue": "0.6",
                    "secondValue": "0.7",
                    "events": {"first": 1, "second": 1},
                }
                results.append({"case": "queue:rapid-fades", "pane": "queue", "inventory_identity": "id:queue-fade-in+id:queue-fade-out", "status": "PASS", **settled_fades})

                page.evaluate(
                    "id => callApi('/api/project/select-stage', { stage_id: id })",
                    stage.id,
                )
                page.wait_for_function(
                    "id => state.project.active_stage_id === id",
                    arg=stage.id,
                )
                _open_tool_once(page, "merge")
                merge_source_id = page.evaluate("state.project.merge_sources[0].id")
                merge_request_before = _request_count(page, "/api/merge/source")
                page.evaluate(
                    """(sourceId) => {
                      const size = document.querySelector(`[data-source-id="${sourceId}"][data-merge-source-field="size"]`);
                      const opacity = document.querySelector(`[data-source-id="${sourceId}"][data-merge-source-field="opacity"]`);
                      const events = { size: 0, opacity: 0 };
                      size.addEventListener('change', () => { events.size += 1; }, { once: true });
                      opacity.addEventListener('change', () => { events.opacity += 1; }, { once: true });
                      window.__actionMergeProof = { size, opacity, events };
                      size.value = '36';
                      size.dispatchEvent(new Event('input', { bubbles: true }));
                      size.dispatchEvent(new Event('change', { bubbles: true }));
                      opacity.value = '99';
                      opacity.dispatchEvent(new Event('input', { bubbles: true }));
                      opacity.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    merge_source_id,
                )
                page.wait_for_function(
                    """sourceId => {
                      const source = state.project.merge_sources.find((item) => item.id === sourceId);
                      return Number(source?.pip_size_percent) === 36 && Number(source?.opacity) === 0.99;
                    }""",
                    arg=merge_source_id,
                )
                page.wait_for_timeout(180)
                settled_merge = page.evaluate(
                    """() => ({
                      sizeConnected: window.__actionMergeProof.size.isConnected,
                      opacityConnected: window.__actionMergeProof.opacity.isConnected,
                      sizeSame: window.__actionMergeProof.size === document.querySelector('[data-merge-source-field="size"]'),
                      opacitySame: window.__actionMergeProof.opacity === document.querySelector('[data-merge-source-field="opacity"]'),
                      sizeValue: window.__actionMergeProof.size.value,
                      opacityValue: window.__actionMergeProof.opacity.value,
                      events: window.__actionMergeProof.events,
                    })"""
                )
                assert settled_merge == {
                    "sizeConnected": True,
                    "opacityConnected": True,
                    "sizeSame": True,
                    "opacitySame": True,
                    "sizeValue": "36",
                    "opacityValue": "99",
                    "events": {"size": 1, "opacity": 1},
                }
                merge_request_after = _request_count(page, "/api/merge/source")
                assert 1 <= merge_request_after - merge_request_before <= 2
                results.append({"case": "merge:rapid-source-scalars", "pane": "merge", "inventory_identity": "data-merge-source-field:size+opacity", "status": "PASS", "mutating_requests": merge_request_after - merge_request_before, **settled_merge})

                _open_tool_once(page, "scoring")
                scoring_before = page.evaluate("state.project.scoring.enabled")
                scoring_request_before = _request_count(page, "/api/scoring")
                scoring_profile_before = _request_count(page, "/api/scoring/profile")
                scoring_proof = _click_once(page, "#scoring-enabled")
                page.wait_for_function(
                    "before => state.project.scoring.enabled !== before",
                    arg=scoring_before,
                )
                assert _request_count(page, "/api/scoring") - scoring_request_before == 1
                assert _request_count(page, "/api/scoring/profile") - scoring_profile_before == 0
                page.evaluate(
                    "path => useProjectFolder(path)",
                    str(controller.project_path),
                )
                page.wait_for_function(
                    "expected => state.project.scoring.enabled === expected",
                    arg=not scoring_before,
                )
                stored_after_scoring = json.loads(
                    (controller.project_path / "project.json").read_text(encoding="utf-8")
                )
                assert stored_after_scoring["scoring"]["enabled"] is (not scoring_before)
                results.append({"case": "scoring:enable-without-profile-reapply", "pane": "scoring", "inventory_identity": "id:scoring-enabled", "status": "PASS", "before": scoring_before, "after": not scoring_before, "mutating_requests": 1, **scoring_proof})

                # Additive actions prove one click creates exactly one object.
                for tool, selector, identity, state_expr in (
                    ("review", "#review-add-text-box", "id:review-add-text-box", "(state.project.overlay.text_boxes || []).length"),
                    ("intro-outro", "#intro-outro-add-text", "intro-outro-add-text", "(state.project.intro_clip.overlay.text_boxes || []).length"),
                ):
                    _open_tool_once(page, tool)
                    before = page.evaluate(state_expr)
                    proof = _click_once(
                        page,
                        selector,
                        expect_same_node=selector != "#intro-outro-add-text",
                    )
                    page.wait_for_function(f"before => {state_expr} === before + 1", arg=before)
                    after = page.evaluate(state_expr)
                    assert after == before + 1
                    results.append({"case": f"{tool}:add-one", "pane": tool, "inventory_identity": identity, "status": "PASS", "before": before, "after": after, **proof})

                # Workbench and shell expanders are synchronous, preserve their node, and toggle once.
                for tool, selector, identity, before_expr, after_expr in (
                    ("timing", "#expand-timing", "id:expand-timing", "state.project.ui_state.timing_expanded === true", "state.project.ui_state.timing_expanded === true"),
                    ("scoring", "#expand-scoring", "id:expand-scoring", "scoringWorkbenchExpanded === true", "scoringWorkbenchExpanded === true"),
                    ("metrics", "#expand-metrics", "id:expand-metrics", "state.project.ui_state.metrics_expanded === true", "state.project.ui_state.metrics_expanded === true"),
                ):
                    _open_tool_once(page, tool)
                    before = page.evaluate(before_expr)
                    assert before is False
                    proof = _click_once(page, selector)
                    after = page.evaluate(after_expr)
                    assert after is True
                    results.append({"case": f"{tool}:expand", "pane": tool, "inventory_identity": identity, "status": "PASS", "before": before, "after": after, **proof})
            finally:
                browser.close()
    finally:
        server.shutdown()

    _write_report(results, inventory_rows, browser_name)
    assert results
