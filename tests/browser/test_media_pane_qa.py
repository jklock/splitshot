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


def test_media_pane_active_stage_card_present(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-card"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                if not page.evaluate("Boolean(state?.project?.path)"):
                    project_path = str(primary_path.parent / "media-qa.ssproj")
                    page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
                    page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(100)
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                assert page.locator(".media-stage-card").count() == 1
                assert page.locator(".media-stage-card .primary-badge").count() >= 1
                assert page.locator("button.media-add-stage-btn").count() >= 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_pane_stage_navigator_expands(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-nav"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                if not page.evaluate("Boolean(state?.project?.path)"):
                    project_path = str(primary_path.parent / "media-qa-nav.ssproj")
                    page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
                    page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(100)
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                assert page.locator("[data-media-section='navigator']").count() >= 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_pane_primary_and_added_sections_present(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-sections"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                if not page.evaluate("Boolean(state?.project?.path)"):
                    project_path = str(primary_path.parent / "media-qa-sec.ssproj")
                    page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
                    page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(100)
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                inner_text = page.locator(".media-stage-card-body").inner_text()
                assert "Primary Media" in inner_text
                assert "Added Media" in inner_text
            finally:
                browser.close()
    finally:
        server.shutdown()
