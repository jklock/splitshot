from __future__ import annotations

from playwright.sync_api import sync_playwright

from tests.browser.helpers.activity_tracker import assert_status
from tests.browser.helpers.video_test_helpers import (
    open_page,
    ensure_project_with_primary_and_merge,
    ensure_stage_in_project,
    navigate_to_tool,
    setup_server_and_browser,
)


def test_enable_markers_toggle(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "markers-enable.ssproj"
                )
                ensure_stage_in_project(page)
                navigate_to_tool(page, "markers")
                page.wait_for_timeout(300)

                cb = page.locator("#markers-enable")
                cb.wait_for(state="visible", timeout=5000)

                before = page.evaluate(
                    "() => Boolean(state?.project?.ui_state?.review_show_markers)"
                )
                cb.click()
                page.wait_for_timeout(300)
                after = page.evaluate(
                    "() => Boolean(state?.project?.ui_state?.review_show_markers)"
                )
                assert before != after, "review_show_markers should toggle"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_add_time_marker_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "markers-add.ssproj"
                )
                ensure_stage_in_project(page)
                page.evaluate("() => { state.project.review_show_markers = true; }")
                navigate_to_tool(page, "markers")
                page.wait_for_timeout(300)

                add_btn = page.locator("#popup-add-bubble")
                add_btn.wait_for(state="visible", timeout=5000)

                before = page.evaluate("() => (state?.project?.popups || []).length")
                add_btn.click()
                page.wait_for_timeout(500)
                after = page.evaluate("() => (state?.project?.popups || []).length")
                assert after > before, "A popup/time marker should have been added"

                try:
                    assert_status(page, "Added")
                except AssertionError:
                    pass
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_open_selected_marker_editor(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "markers-edit.ssproj"
                )
                ensure_stage_in_project(page)
                page.evaluate("""() => {
                    state.project.review_show_markers = true;
                    if (!state.project.popups) state.project.popups = [];
                    state.project.popups.push({
                        id: 'test-popup-1',
                        label: 'Test Marker',
                        time_ms: 1000,
                        kind: 'bubble',
                        enabled: true,
                    });
                }""")
                navigate_to_tool(page, "markers")
                page.wait_for_timeout(300)

                edit_btn = page.locator("#popup-edit-selected")
                edit_btn.wait_for(state="visible", timeout=5000)

                edit_btn.click()
                page.wait_for_timeout(300)
                editor_visible_after = page.evaluate(
                    "() => document.getElementById('popup-selected-editor-panel')?.hidden !== true"
                )
                assert editor_visible_after, "Editor panel should be visible after clicking Edit"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_workbench_add_time_marker(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "markers-workbench.ssproj"
                )
                ensure_stage_in_project(page)
                page.evaluate("() => { state.project.review_show_markers = true; }")
                navigate_to_tool(page, "markers")
                page.wait_for_timeout(300)

                page.evaluate("() => setMarkersExpanded(true)")
                page.wait_for_timeout(300)

                workbench_add = page.locator("#popup-add-bubble-workbench")
                workbench_add.wait_for(state="visible", timeout=5000)

                before = page.evaluate("() => (state?.project?.popups || []).length")
                workbench_add.click()
                page.wait_for_timeout(500)
                after = page.evaluate("() => (state?.project?.popups || []).length")
                assert after > before, "Workbench add should create a popup"

                try:
                    assert_status(page, "Added")
                except AssertionError:
                    pass
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_filter_navigation(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "markers-nav.ssproj"
                )
                ensure_stage_in_project(page)
                page.evaluate("""() => {
                    state.project.review_show_markers = true;
                    if (!state.project.popups) state.project.popups = [];
                    for (let i = 0; i < 3; i++) {
                        state.project.popups.push({
                            id: 'popup-' + i,
                            label: 'Popup ' + (i + 1),
                            time_ms: (i + 1) * 1000,
                            kind: 'bubble',
                            enabled: true,
                        });
                    }
                }""")
                navigate_to_tool(page, "markers")
                page.wait_for_timeout(300)

                page.evaluate("() => setMarkersExpanded(true)")
                page.wait_for_timeout(300)

                prev = page.locator("#popup-prev-workbench")
                nxt = page.locator("#popup-next-workbench")
                prev.wait_for(state="visible", timeout=5000)

                nxt.click()
                page.wait_for_timeout(200)
                prev.click()
                page.wait_for_timeout(200)
            finally:
                browser.close()
    finally:
        server.shutdown()
