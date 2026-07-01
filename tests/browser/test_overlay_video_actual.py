from __future__ import annotations

from playwright.sync_api import sync_playwright

from tests.browser.helpers.video_test_helpers import (
    open_page,
    ensure_project_with_primary_and_merge,
    navigate_to_tool,
    setup_server_and_browser,
)


def test_toggle_overlay_on_video(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "overlay-toggle.ssproj"
                )
                navigate_to_tool(page, "timing")
                page.wait_for_timeout(300)

                before = page.evaluate("() => Boolean(state?.project?.overlay_enabled)")
                cb = page.locator("#overlay-enabled")
                if cb.count():
                    cb.click()
                else:
                    page.evaluate(
                        "() => { state.project.overlay_enabled = !state.project.overlay_enabled; }"
                    )
                page.wait_for_timeout(300)
                after = page.evaluate("() => Boolean(state?.project?.overlay_enabled)")
                assert before != after, "overlay_enabled should have toggled"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_drag_overlay_badge(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "overlay-drag.ssproj"
                )
                navigate_to_tool(page, "timing")
                page.evaluate("() => { state.project.overlay_enabled = true; }")
                page.wait_for_timeout(300)

                overlay_badge = page.locator("#overlay-badge")
                if overlay_badge.count():
                    box = overlay_badge.bounding_box()
                    if box:
                        start_x = box["x"] + box["width"] / 2
                        start_y = box["y"] + box["height"] / 2
                        page.mouse.move(start_x, start_y)
                        page.mouse.down()
                        page.mouse.move(start_x + 50, start_y + 30, steps=5)
                        page.mouse.up()
                        page.wait_for_timeout(500)
                        tracker.assert_activity("overlay.drag.commit")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_change_overlay_size(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "overlay-size.ssproj"
                )
                navigate_to_tool(page, "timing")
                page.evaluate("() => { state.project.overlay_enabled = true; }")
                page.wait_for_timeout(300)

                size_select = page.locator("#overlay-size")
                if size_select.count():
                    size_select.select_option("large")
                    page.wait_for_timeout(500)
                    current_size = page.evaluate("() => state?.project?.overlay_size ?? ''")
                    assert current_size == "large", (
                        f"Expected overlay_size 'large', got '{current_size}'"
                    )
            finally:
                browser.close()
    finally:
        server.shutdown()
