from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from tests.browser.helpers.video_test_helpers import create_project


def _open_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _prepare_stage(page, primary_path: Path, project_path: Path) -> str:
    create_project(page, str(project_path))
    page.evaluate("() => callApi('/api/project/stage/create', {})")
    page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
    page.evaluate(
        "(path) => callApi('/api/project/stage/import-primary', { stage_id: state.project.active_stage_id, path })",
        str(primary_path),
    )
    page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
    return page.evaluate("state.project.active_stage_id")


def test_queue_pane_membership_and_status_are_visible(synthetic_video_factory) -> None:
    primary = Path(synthetic_video_factory(name="queue-pane-membership", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                stage_id = _prepare_stage(page, primary, primary.parent / "queue-membership.ssproj")
                page.locator("button[data-tool='queue']").click(force=True)
                page.locator(".queue-membership-btn").first.click()
                page.wait_for_function(
                    "(id) => state.project.queue.some((entry) => entry.stage_id === id)",
                    arg=stage_id,
                )
                card = page.locator(f'[data-queue-stage-id="{stage_id}"]')
                assert card.is_visible()
                assert "queued" in card.inner_text().lower()
                assert page.locator("#queue-process-btn").is_visible()
                assert page.locator("#queue-combined-btn").is_visible()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_queue_uses_flat_og_controls_without_apply_settings_ui(synthetic_video_factory) -> None:
    primary = Path(synthetic_video_factory(name="queue-pane-controls", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                stage_id = _prepare_stage(page, primary, primary.parent / "queue-controls.ssproj")
                page.evaluate(
                    "(id) => callApi('/api/project/queue/add', { stage_id: id })", stage_id
                )
                page.locator("button[data-tool='queue']").click(force=True)
                assert page.locator("#queue-apply-all-btn").count() == 0
                assert page.locator("#queue-stage-select").count() == 0
                assert page.get_by_text("Match Stages", exact=True).is_visible()
                assert page.get_by_text("Process", exact=True).is_visible()
                assert page.get_by_role("button", name="Process Queue", exact=True).is_visible()
                assert page.get_by_role("button", name="Process as One File", exact=True).is_visible()
                assert page.locator(".queue-status-pill").count() == 0
                assert page.locator(".queue-status-text").count() == 1
                assert page.locator(".queue-stage-list").is_visible()
                assert page.locator(".queue-stage-toggle").count() == 0
                assert page.get_by_role("button", name="Show Output Folder").is_enabled()
                assert page.get_by_role("button", name="Show Log").is_visible()
                assert page.locator("#queue-include-intro").is_disabled()
                assert page.locator("#queue-include-outro").is_disabled()
                assert page.locator("#queue-combined-btn").evaluate(
                    "button => getComputedStyle(button).backgroundColor"
                ) == "rgb(57, 208, 111)"
                assert page.locator("#queue-fade-in").input_value() == "0.5"
                assert page.locator("#queue-fade-out").input_value() == "0.5"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_intro_outro_pane_previews_match_overlay_and_queue_include_choice(
    synthetic_video_factory,
) -> None:
    intro = Path(synthetic_video_factory(name="intro-pane-preview", beep_ms=250))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                create_project(page, str(intro.parent / "intro-pane.ssproj"))
                page.evaluate(
                    "(path) => callApi('/api/project/queue/media', { kind: 'intro', path })",
                    str(intro),
                )
                page.evaluate(
                    "() => callApi('/api/project/intro-outro/overlay', { kind: 'intro', text_boxes: [{ enabled: true, source: 'match_summary', summary_metric_ids: ['stage_count'], quadrant: 'top_right', text: '', background_color: '#000000', text_color: '#ffffff', opacity: 0.9, font_size: 28, font_bold: true }] })"
                )
                intro_nav = page.locator("button[data-tool='intro-outro']")
                queue_nav = page.locator("button[data-tool='queue']")
                assert intro_nav.evaluate("node => node.compareDocumentPosition(document.querySelector(\"button[data-tool='queue']\")) & Node.DOCUMENT_POSITION_FOLLOWING")
                intro_nav.click(force=True)
                page.wait_for_function("() => document.querySelector('#primary-video').src.includes('/media/intro')")
                assert page.locator(".intro-outro-preview-badge").inner_text() == "Stages 1"
                assert page.get_by_role("button", name="Add Text Box").is_visible()
                assert page.get_by_role("button", name="Add Match Results").is_visible()

                queue_nav.click(force=True)
                assert page.locator("#queue-include-intro").is_enabled()
                assert page.locator("#queue-include-intro").is_checked()
                assert page.locator("#queue-include-outro").is_disabled()
            finally:
                browser.close()
    finally:
        server.shutdown()
