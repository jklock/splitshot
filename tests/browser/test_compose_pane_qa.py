from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _ensure_project_with_primary_and_merge(
    page, primary_path: Path, merge_path: Path, project_name: str
) -> None:
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_dir = str(primary_path.parent / project_name)
        page.evaluate(f"() => createNewProject({json.dumps(project_dir)})")
        page.wait_for_function("() => Boolean(state?.project?.path)")

    if not page.evaluate("Boolean(state?.project?.primary_video?.path)"):
        page.locator("#primary-file-input").set_input_files(str(primary_path))
        page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")

    merge_count = page.evaluate("() => (state?.project?.merge_sources || []).length")
    if merge_count == 0:
        page.locator("#merge-media-input").set_input_files(str(merge_path))
        page.wait_for_function("() => (state?.project?.merge_sources || []).length > 0")


def test_compose_pane_renders_merge_sources(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-primary"))
    merge_path = Path(synthetic_video_factory(name="compose-qa-merge"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(200)
                assert page.evaluate("activeTool") == "merge"

                assert page.locator(".merge-media-card").count() >= 1
                assert page.locator("#merge-enabled").count() == 1
                assert page.locator("#merge-layout").count() == 1
                assert page.locator("#pip-size").count() == 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_pane_merge_enabled_toggle(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-toggle"))
    merge_path = Path(synthetic_video_factory(name="compose-qa-toggle-merge"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-toggle.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(200)

                initial = page.evaluate("() => Boolean(state?.project?.merge?.enabled)")
                page.locator("#merge-enabled").click()
                page.wait_for_timeout(100)
                toggled = page.evaluate("() => Boolean(state?.project?.merge?.enabled)")
                assert toggled != initial
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_pane_layout_select_changes_value(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="compose-qa-layout"))
    merge_path = Path(synthetic_video_factory(name="compose-qa-layout-merge"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-qa-layout.ssproj"
                )
                page.locator("button[data-tool='merge']").click(force=True)
                page.wait_for_timeout(200)

                page.locator("#merge-layout").select_option("above_below")
                page.wait_for_timeout(100)
                later = page.evaluate("() => state?.project?.merge?.layout || 'side_by_side'")
                assert later == "above_below"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_pane_no_sync_analysis_buttons_in_merge(synthetic_video_factory) -> None:
    from pathlib import Path as P

    merge_pane_source = (
        P(__file__).resolve().parents[2] / "src/splitshot/browser/static/panes/merge-pane.js"
    ).read_text()
    assert "Re-run beep sync" not in merge_pane_source
    assert "Analyze beep sync" not in merge_pane_source
    assert "supports_sync_analysis" not in merge_pane_source
    assert "trim-analyze-btn" not in merge_pane_source
