from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

from tests.browser.helpers.video_test_helpers import (
    ensure_project_with_primary_and_merge,
    navigate_to_tool,
    open_page,
    setup_server_and_browser,
)


def test_merge_preview_renders_pip_elements(synthetic_video_factory) -> None:
    server, _tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "mp-pip-p"},
        merge_kwargs={"name": "mp-pip-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "preview-pip.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.evaluate("() => { state.project.merge.enabled = true; renderVideo(); }")
                page.evaluate("() => { state.project.merge.layout = 'pip'; renderVideo(); }")
                page.wait_for_timeout(500)

                preview_videos = page.evaluate(
                    "() => document.querySelectorAll('#merge-preview-layer video').length"
                )
                assert preview_videos >= 1, (
                    f"Expected >=1 video elements in merge preview layer, found {preview_videos}"
                )

                preview_layer = page.evaluate(
                    "() => !!document.querySelector('#merge-preview-layer')"
                )
                assert preview_layer, "Merge preview layer should exist"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_merge_preview_syncs_to_primary_time(synthetic_video_factory) -> None:
    server, _tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "mp-sync-p"},
        merge_kwargs={"name": "mp-sync-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "preview-sync.ssproj"
                )
                page.evaluate("() => { state.project.merge.enabled = true; }")
                page.evaluate("() => { state.project.merge.layout = 'pip'; }")
                navigate_to_tool(page, "timing")
                page.wait_for_timeout(500)

                primary_video = page.locator("#primary-video").first
                if primary_video.count():
                    primary_video.evaluate("(el) => el.currentTime = 1.0")
                    page.wait_for_timeout(500)
                    primary_time = primary_video.evaluate("(el) => el.currentTime")
                    assert abs(primary_time - 1.0) < 0.3, (
                        f"Primary video should be at ~1.0s, got {primary_time}"
                    )
                else:
                    pytest.skip("Primary video element not found")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_merge_preview_drag_repositions(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "mp-drag-p"},
        merge_kwargs={"name": "mp-drag-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "preview-drag.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.evaluate("() => { state.project.merge.enabled = true; }")
                page.evaluate("() => { state.project.merge.layout = 'pip'; }")
                page.evaluate("() => scheduleInteractionPreviewRender({ video: true })")
                page.wait_for_timeout(500)

                pip_item = page.locator("#merge-preview-layer .merge-preview-item")
                pip_item.wait_for(state="visible", timeout=5000)
                box = pip_item.bounding_box()
                assert box, "PIP item must have a bounding box"
                video_box = page.locator("#primary-video").bounding_box()
                assert video_box, "Primary video must have a bounding box"
                assert box["y"] + box["height"] <= video_box["y"] + video_box["height"] - 40
                start_x = box["x"] + box["width"] / 2
                start_y = box["y"] + box["height"] / 2
                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(start_x + 20, start_y + 15, steps=5)
                page.mouse.up()
                page.wait_for_timeout(500)
                tracker.assert_activity("merge.preview.drag.commit", timeout=5000)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_merge_preview_drag_survives_pending_merge_auto_apply(
    synthetic_video_factory,
) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "mp-drag-race-p"},
        merge_kwargs={"name": "mp-drag-race-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "preview-drag-race.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.locator("#merge-enabled").check()
                page.locator("#merge-layout").select_option("pip")
                page.evaluate("() => scheduleInteractionPreviewRender({ video: true })")
                page.wait_for_timeout(80)

                pip_item = page.locator("#merge-preview-layer .merge-preview-item").last
                pip_item.wait_for(state="visible", timeout=5000)
                source_id = pip_item.get_attribute("data-source-id")
                assert source_id, "PIP item must expose a merge source id"

                before = page.evaluate(
                    """(sid) => {
                        const source = (state?.project?.merge_sources || []).find((entry) => entry.id === sid);
                        return {
                            pip_x: Number(source?.pip_x ?? 0),
                            pip_y: Number(source?.pip_y ?? 0),
                        };
                    }""",
                    source_id,
                )
                box = pip_item.bounding_box()
                assert box, "PIP item must have a bounding box"
                start_x = box["x"] + box["width"] / 2
                start_y = box["y"] + box["height"] / 2
                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(start_x - 96, start_y - 72, steps=12)
                page.mouse.up()
                page.wait_for_timeout(700)

                tracker.assert_activity("merge.preview.drag.commit", timeout=5000)
                after = page.evaluate(
                    """(sid) => {
                        const source = (state?.project?.merge_sources || []).find((entry) => entry.id === sid);
                        return {
                            pip_x: Number(source?.pip_x ?? 0),
                            pip_y: Number(source?.pip_y ?? 0),
                        };
                    }""",
                    source_id,
                )
                page.evaluate("() => renderVideo()")
                page.wait_for_timeout(150)
                after_render = page.evaluate(
                    """(sid) => {
                        const source = (state?.project?.merge_sources || []).find((entry) => entry.id === sid);
                        return {
                            pip_x: Number(source?.pip_x ?? 0),
                            pip_y: Number(source?.pip_y ?? 0),
                        };
                    }""",
                    source_id,
                )

                assert after["pip_x"] != before["pip_x"] or after["pip_y"] != before["pip_y"], (
                    "Drag should change the source PiP position"
                )
                assert after_render == after, (
                    "A pending merge auto-apply must not reset PiP drag state"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_merge_preview_updated_by_trim(synthetic_video_factory) -> None:
    server, _tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "mp-trim-p"},
        merge_kwargs={"name": "mp-trim-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "preview-trim.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.locator("#merge-enabled").check()
                page.locator("#merge-layout").select_option("pip")
                navigate_to_tool(page, "trim-sync")
                page.wait_for_timeout(300)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id
                page.locator(f'[data-trim-start="{source_id}"]').fill("0.50")
                page.locator(f'[data-trim-end="{source_id}"]').fill("3.00")
                page.locator(f'button.trim-apply-btn[data-source-id="{source_id}"]').click()
                page.wait_for_function(
                    """(sid) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === sid);
                        const trim = source?.trim_derivative;
                        return Boolean(trim?.derivative_path)
                            && trim?.active_path_kind === 'local_derivative'
                            && source?.effective_media_path === trim?.derivative_path;
                    }""",
                    arg=source_id,
                    timeout=120000,
                )
                trimmed_name = page.evaluate(
                    """(sid) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === sid);
                        const path = source?.effective_media_path || '';
                        return path.split(/[\\\\/]/).pop();
                    }""",
                    source_id,
                )

                page.locator("#close-export-log").click()
                navigate_to_tool(page, "merge")
                page.wait_for_timeout(500)
                page.wait_for_function(
                    """(payload) => {
                        const media = document.querySelector(`#merge-preview-layer .merge-preview-item[data-source-id="${payload.sid}"] video`);
                        return Boolean(media?.dataset?.sourcePath)
                            && media.dataset.sourcePath.endsWith(payload.trimmedName);
                    }""",
                    arg={"sid": source_id, "trimmedName": trimmed_name},
                    timeout=10000,
                )
                bound_path = page.evaluate(
                    """(sid) => {
                        const media = document.querySelector(`#merge-preview-layer .merge-preview-item[data-source-id="${sid}"] video`);
                        return media?.dataset?.sourcePath || '';
                    }""",
                    source_id,
                )
                assert trimmed_name in bound_path, (
                    f"Preview media should bind to trimmed media path, got {bound_path!r}"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
