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


def test_media_pane_active_stage_workspace_present(synthetic_video_factory) -> None:
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
                assert page.locator("#media-pane").get_by_text("Active Stage").count() >= 1
                assert page.locator("#media-pane").get_by_text("Stages").count() >= 1
                assert page.locator("button.media-add-stage-btn").count() >= 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_pane_uses_active_stage_selector_without_stage_navigator(
    synthetic_video_factory,
) -> None:
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
                assert page.locator("#media-active-stage-select").count() >= 1
                assert "Stage Navigator" not in page.locator("#media-pane").inner_text()
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
                inner_text = page.locator("#media-pane").inner_text()
                assert "Primary" in inner_text
                assert "Added Media" in inner_text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_media_add_stage_lives_inside_active_stage_controls(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="media-qa-add-stage"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                if not page.evaluate("Boolean(state?.project?.path)"):
                    project_path = str(primary_path.parent / "media-qa-add-stage.ssproj")
                    page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
                    page.wait_for_function("() => Boolean(state?.project?.path)")
                page.locator("button[data-tool='media']").click(force=True)
                page.wait_for_timeout(100)
                page.locator("#primary-file-input").set_input_files(str(primary_path))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")

                add_stage = page.locator("#media-pane .media-add-stage-full")
                add_stage.wait_for(state="visible")
                active_stage_section = page.locator("#media-pane .media-pane-section-static").first
                assert active_stage_section.locator(".media-add-stage-full").count() == 1
                assert page.locator("#media-pane > .media-add-stage-full").count() == 0
            finally:
                browser.close()
    finally:
        server.shutdown()
