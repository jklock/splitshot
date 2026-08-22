from __future__ import annotations

from playwright.sync_api import sync_playwright

from tests.browser.helpers.video_test_helpers import (
    ensure_project_with_primary_and_merge,
    navigate_to_tool,
    open_page,
    setup_server_and_browser,
)


def _wait_waveform_ready(page) -> None:
    """Wait for waveform analysis to complete (zoom button enabled)."""
    page.wait_for_function(
        "() => !document.getElementById('zoom-waveform-in')?.disabled",
        timeout=30000,
    )


def _select_first_shot(page) -> None:
    """Click the first shot marker in the waveform to select it."""
    page.wait_for_function(
        "() => (state?.project?.analysis?.shots || []).length > 0",
        timeout=30000,
    )
    page.evaluate("""() => {
        const shots = state?.project?.analysis?.shots || [];
        if (shots.length > 0) selectShot(shots[0].id);
    }""")
    page.wait_for_timeout(200)


def test_waveform_expand_collapse(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "wave-expand.ssproj"
                )
                navigate_to_tool(page, "timing")
                _wait_waveform_ready(page)

                btn = page.locator("#expand-waveform")
                btn.wait_for(state="visible", timeout=5000)

                btn.click()
                page.wait_for_timeout(300)
                tracker.assert_activity("waveform.expand")
                expanded = page.evaluate(
                    "() => document.getElementById('cockpit-root')?.classList.contains('waveform-expanded')"
                )
                assert expanded, "Waveform should be expanded"

                btn.click()
                page.wait_for_timeout(300)
                tracker.assert_activity_count("waveform.expand", 2, timeout=4000)
                expanded = page.evaluate(
                    "() => document.getElementById('cockpit-root')?.classList.contains('waveform-expanded')"
                )
                assert not expanded, "Waveform should be collapsed"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_zoom_in_out(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "wave-zoom.ssproj"
                )
                navigate_to_tool(page, "timing")
                page.wait_for_timeout(300)

                zoom_in = page.locator("#zoom-waveform-in")
                zoom_out = page.locator("#zoom-waveform-out")
                zoom_in.wait_for(state="visible", timeout=5000)

                zoom_in.click()
                page.wait_for_timeout(300)
                tracker.assert_activity("waveform.zoom_x")

                zoom_out.click()
                page.wait_for_timeout(300)
                tracker.assert_activity_count("waveform.zoom_x", 2, timeout=4000)

                zoom_in.click()
                page.wait_for_timeout(300)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_amp_zoom(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "wave-amp.ssproj"
                )
                navigate_to_tool(page, "timing")
                page.wait_for_timeout(300)

                _wait_waveform_ready(page)
                _select_first_shot(page)

                amp_in = page.locator("#amp-waveform-in")
                amp_out = page.locator("#amp-waveform-out")
                amp_in.wait_for(state="visible", timeout=5000)

                amp_in.click()
                page.wait_for_timeout(300)
                tracker.assert_activity("waveform.shot_amplitude")

                amp_out.click()
                page.wait_for_timeout(300)
                tracker.assert_activity_count("waveform.shot_amplitude", 2, timeout=4000)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_reset_view(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "wave-reset.ssproj"
                )
                navigate_to_tool(page, "timing")
                page.wait_for_timeout(300)

                reset = page.locator("#reset-waveform-view")
                reset.wait_for(state="visible", timeout=5000)
                reset.click()
                page.wait_for_timeout(300)
                tracker.assert_activity("waveform.zoom_reset")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_mode_switch(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "wave-mode.ssproj"
                )
                navigate_to_tool(page, "timing")
                page.wait_for_timeout(300)

                add_mode = page.locator('.mode-button[data-waveform-mode="add"]')
                select_mode = page.locator('.mode-button[data-waveform-mode="select"]')
                add_mode.wait_for(state="visible", timeout=5000)

                add_mode.click()
                page.wait_for_timeout(300)
                tracker.assert_activity("waveform.mode")
                is_add = page.evaluate(
                    "() => document.querySelector('.mode-button[data-waveform-mode=\"add\"]')?.classList.contains('active')"
                )
                assert is_add, "Add mode should be active"

                select_mode.click()
                page.wait_for_timeout(300)
                tracker.assert_activity_count("waveform.mode", 2, timeout=4000)
                is_select = page.evaluate(
                    "() => document.querySelector('.mode-button[data-waveform-mode=\"select\"]')?.classList.contains('active')"
                )
                assert is_select, "Select mode should be active"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_add_shot_in_add_mode(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "wave-add-shot.ssproj"
                )
                navigate_to_tool(page, "timing")
                page.wait_for_timeout(300)

                add_mode = page.locator('.mode-button[data-waveform-mode="add"]')
                add_mode.wait_for(state="visible", timeout=5000)
                add_mode.click()
                page.wait_for_timeout(200)

                canvas = page.locator("#waveform")
                box = canvas.bounding_box()
                assert box, "Waveform canvas must have bounding box"

                click_x = box["x"] + box["width"] * 0.3
                click_y = box["y"] + box["height"] * 0.5
                page.mouse.click(click_x, click_y)
                page.wait_for_timeout(500)
                tracker.assert_activity("waveform.add_shot")

                shot_count = page.evaluate("() => (state?.project?.analysis?.shots || []).length")
                assert shot_count > 0, "At least one shot should exist"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_click_to_seek(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "wave-seek.ssproj"
                )
                navigate_to_tool(page, "timing")
                _wait_waveform_ready(page)

                canvas = page.locator("#waveform")
                canvas.wait_for(state="visible", timeout=5000)
                box = canvas.bounding_box()
                assert box, "Waveform canvas must have bounding box"

                click_x = box["x"] + box["width"] * 0.05
                click_y = box["y"] + box["height"] * 0.5
                page.mouse.click(click_x, click_y)
                page.wait_for_timeout(500)
                tracker.assert_activity("waveform.seek")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_pan_via_drag(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "wave-pan.ssproj"
                )
                navigate_to_tool(page, "timing")
                page.wait_for_timeout(300)

                expand = page.locator("#expand-waveform")
                expand.wait_for(state="visible", timeout=5000)
                expand.click()
                page.wait_for_timeout(300)

                zoom_in = page.locator("#zoom-waveform-in")
                for _ in range(3):
                    zoom_in.click()
                    page.wait_for_timeout(100)

                canvas = page.locator("#waveform")
                box = canvas.bounding_box()
                assert box, "Canvas must have bounding box"

                start_x = box["x"] + box["width"] * 0.5
                start_y = box["y"] + box["height"] * 0.5
                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(start_x - 100, start_y, steps=5)
                page.mouse.up()
                page.wait_for_timeout(500)
                tracker.assert_activity("waveform.pan_drag.commit")
            finally:
                browser.close()
    finally:
        server.shutdown()
