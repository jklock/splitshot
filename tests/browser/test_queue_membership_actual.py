from __future__ import annotations

from playwright.sync_api import sync_playwright

from splitshot.domain.models import QueueStatus
from tests.browser.helpers.video_test_helpers import (
    create_project,
    navigate_to_tool,
    open_page,
    setup_server_and_browser,
)


def _prepare_queueable_stage(page, primary_path, project_name: str) -> str:
    page.set_default_timeout(30000)
    create_project(page, str(primary_path.parent / project_name))
    page.evaluate("() => callApi('/api/project/stage/create', {})")
    page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
    stage_id = page.evaluate("state.project.active_stage_id")
    page.evaluate(
        "(path) => callApi('/api/project/stage/import-primary', { stage_id: state.project.active_stage_id, path })",
        str(primary_path),
    )
    page.wait_for_function(
        """stageId => Boolean((state?.project?.stages || []).find((stage) => stage.id === stageId)?.primary_media?.path)""",
        arg=stage_id,
    )
    return stage_id


def test_queue_add_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, _merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "queue-add-primary"},
        merge_kwargs={"name": "queue-add-merge"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                stage_id = _prepare_queueable_stage(page, primary_path, "queue-add.ssproj")
                navigate_to_tool(page, "queue")
                queue_btn = page.locator(
                    f'button.queue-membership-btn[data-stage-id="{stage_id}"]'
                )
                queue_btn.click()
                page.wait_for_function(
                    "stageId => (state?.project?.queue || []).some((entry) => entry.stage_id === stageId)",
                    arg=stage_id,
                )
                tracker.assert_activity("queue.add")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_queue_remove_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, _merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "queue-remove-primary"},
        merge_kwargs={"name": "queue-remove-merge"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                stage_id = _prepare_queueable_stage(page, primary_path, "queue-remove.ssproj")
                navigate_to_tool(page, "queue")
                membership_btn = page.locator(
                    f'button.queue-membership-btn[data-stage-id="{stage_id}"]'
                )
                membership_btn.click()
                page.wait_for_function(
                    "stageId => (state?.project?.queue || []).some((entry) => entry.stage_id === stageId)",
                    arg=stage_id,
                )
                membership_btn.click()
                page.wait_for_function(
                    "stageId => !(state?.project?.queue || []).some((entry) => entry.stage_id === stageId)",
                    arg=stage_id,
                )
                tracker.assert_activity("queue.remove")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_requeue_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, _merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "queue-requeue-primary"},
        merge_kwargs={"name": "queue-requeue-merge"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                stage_id = _prepare_queueable_stage(page, primary_path, "requeue.ssproj")
                navigate_to_tool(page, "queue")
                requeue_btn = page.locator(
                    f'button.queue-membership-btn[data-stage-id="{stage_id}"]'
                )
                requeue_btn.click()
                page.wait_for_function(
                    "stageId => (state?.project?.queue || []).some((entry) => entry.stage_id === stageId)",
                    arg=stage_id,
                )
                queue_entry = next(
                    entry for entry in server.controller.project.queue if entry.stage_id == stage_id
                )
                stage = next(
                    item for item in server.controller.project.stages if item.id == stage_id
                )
                queue_entry.status = QueueStatus.COMPLETE
                stage.queue_status = QueueStatus.COMPLETE
                page.evaluate("() => refresh()")
                page.wait_for_function(
                    "stageId => document.querySelector(`button.queue-membership-btn[data-stage-id=\"${stageId}\"]`)?.textContent === 'Requeue'",
                    arg=stage_id,
                )
                requeue_btn.click()
                page.wait_for_function(
                    "stageId => (state?.project?.queue || []).find((entry) => entry.stage_id === stageId)?.status === 'queued'",
                    arg=stage_id,
                )
                tracker.assert_activity("queue.add")
            finally:
                browser.close()
    finally:
        server.shutdown()
