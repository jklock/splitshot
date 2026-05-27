from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _open_tool(page, tool: str) -> None:
    page.locator(f'button[data-tool="{tool}"]').click(force=True)
    page.wait_for_function("(expected) => activeTool === expected", arg=tool)


def test_review_source_controls_apply_selected_output_profile_render_plan(
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_tool(page, "project")
                page.evaluate(
                    f"() => createNewProject({json.dumps(str(tmp_path / 'review-source-hooks.ssproj'))})"
                )
                page.wait_for_function("() => Boolean(state?.project?.path)")
                _open_tool(page, "export")

                page.locator("#output-profile-name").fill("Review Source Profile")
                page.locator("#output-profile-create").click()
                page.locator("#output-profile-list .automation-row").first.wait_for(state="visible")

                profiles = controller.output_profile_list("stage", controller.project.id)
                assert len(profiles) == 1
                profile_id = profiles[0]["output_id"]

                page.evaluate(
                    """() => {
                        window.__reviewSourceRenderCalls = [];
                        const originalFetch = window.fetch.bind(window);
                        window.fetch = async (input, init) => {
                            const url = typeof input === 'string' ? input : String(input?.url || '');
                            if (url.endsWith('/api/output-profiles/render')) {
                                window.__reviewSourceRenderCalls.push({
                                    url,
                                    method: init?.method || 'GET',
                                    body: init?.body || '',
                                });
                            }
                            return originalFetch(input, init);
                        };
                    }"""
                )

                _open_tool(page, "review")
                assert (
                    page.locator("#retained-review-status").text_content() or ""
                ).strip() == "Using live stage data."
                page.wait_for_function(
                    """(profileId) => {
                        const select = document.getElementById('retained-review-source');
                        return Boolean(select)
                          && Array.from(select.options).some((option) => option.value === profileId);
                    }""",
                    arg=profile_id,
                )
                page.locator("#retained-review-source").select_option(profile_id)
                page.locator("#retained-review-apply").click()
                page.wait_for_function(
                    """(profileId) => {
                        const status = document.getElementById('retained-review-status');
                        const select = document.getElementById('retained-review-source');
                        return (select?.value || '') === profileId
                          && Boolean(status?.textContent?.includes(profileId));
                    }""",
                    arg=profile_id,
                )
                page.wait_for_function(
                    """(profileId) => {
                        return (window.__reviewSourceRenderCalls || []).some((call) => {
                            try {
                                return JSON.parse(call.body || '{}').output_id === profileId;
                            } catch (_error) {
                                return false;
                            }
                        });
                    }""",
                    arg=profile_id,
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
