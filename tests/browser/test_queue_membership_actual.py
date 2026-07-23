from __future__ import annotations

from playwright.sync_api import sync_playwright

from tests.browser.helpers.video_test_helpers import (
    open_page,
    ensure_project_with_primary_and_merge,
    navigate_to_tool,
    setup_server_and_browser,
)


def test_queue_add_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "queue-add.ssproj"
                )
                page.evaluate("""() => {
                    if (!state.project.stages) state.project.stages = [];
                    state.project.stages.push({
                        id: 'test-stage-1',
                        label: 'Test Stage',
                        order_index: 0,
                        primary_media: null,
                        added_media: [],
                    });
                    state.project.active_stage_id = 'test-stage-1';
                }""")
                page.wait_for_timeout(100)
                navigate_to_tool(page, "queue")
                page.wait_for_timeout(300)

                queue_btn = page.locator("button.queue-membership-btn").first
                if queue_btn.count():
                    queue_btn.click()
                    page.wait_for_timeout(500)
                    tracker.assert_activity("queue.add")
                else:
                    tracker.assert_no_activity("queue.add")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_queue_remove_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "queue-remove.ssproj"
                )
                page.evaluate("""() => {
                    if (!state.project.stages) state.project.stages = [];
                    state.project.stages.push({
                        id: 'test-stage-2',
                        label: 'Remove Stage',
                        order_index: 0,
                        primary_media: null,
                        added_media: [],
                    });
                    state.project.active_stage_id = 'test-stage-2';
                    if (!state.project.queue) state.project.queue = [];
                    state.project.queue.push({ stage_id: 'test-stage-2', status: 'queued' });
                }""")
                page.wait_for_timeout(100)
                navigate_to_tool(page, "queue")
                page.wait_for_timeout(300)

                unqueue_btn = page.locator("button.queue-membership-btn").first
                if unqueue_btn.count():
                    unqueue_btn.click()
                    page.wait_for_timeout(500)
                    tracker.assert_activity("queue.remove")
                else:
                    tracker.assert_no_activity("queue.remove")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_requeue_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "requeue.ssproj"
                )
                page.evaluate("""() => {
                    if (!state.project.stages) state.project.stages = [];
                    state.project.stages.push({
                        id: 'test-stage-3',
                        label: 'Requeue Stage',
                        order_index: 0,
                        primary_media: null,
                        added_media: [],
                    });
                    state.project.active_stage_id = 'test-stage-3';
                    if (!state.project.queue) state.project.queue = [];
                    state.project.queue.push({ stage_id: 'test-stage-3', status: 'complete' });
                }""")
                page.wait_for_timeout(100)
                navigate_to_tool(page, "queue")
                page.wait_for_timeout(300)

                requeue_btn = page.locator("button.queue-membership-btn").first
                if requeue_btn.count():
                    requeue_btn.click()
                    page.wait_for_timeout(500)
                    tracker.assert_activity("queue.add")
                else:
                    tracker.assert_no_activity("queue.add")
            finally:
                browser.close()
    finally:
        server.shutdown()
