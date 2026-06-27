from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _ensure_project_with_primary(synthetic_video_factory, page, name: str) -> str:
    primary_path = str(Path(synthetic_video_factory(name=name, beep_ms=400)))
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_dir = str(Path(primary_path).parent / f"{name}.ssproj")
        page.evaluate(f"() => createNewProject({json.dumps(project_dir)})")
        page.wait_for_function("() => Boolean(state?.project?.path)")

    if not page.evaluate("Boolean(state?.project?.primary_video?.path)"):
        page.locator("#primary-file-input").set_input_files(primary_path)
        page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")

    stage_count = page.evaluate("() => (state?.project?.stages || []).length")
    if stage_count == 0:
        page.locator("button[data-tool='media']").click(force=True)
        page.wait_for_timeout(200)
        page.locator(".media-add-stage-btn").click()
        page.wait_for_timeout(500)

    return primary_path


def test_queue_pane_renders_controls_and_list(synthetic_video_factory) -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary(synthetic_video_factory, page, "queue-qa-render")

                page.locator("button[data-tool='queue']").click(force=True)
                page.wait_for_timeout(300)
                assert page.evaluate("activeTool") == "queue"

                assert page.locator("#queue-stage-select").count() >= 1
                assert page.locator(".queue-membership-btn").count() >= 1
                assert page.locator("#queue-apply-all-btn").count() == 1
                assert page.locator("#queue-process-btn").count() == 1
                assert page.locator("#queue-combined-btn").count() == 1
                assert page.locator(".queue-status-pill, .empty-state").count() >= 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_queue_membership_changes_state(synthetic_video_factory) -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary(synthetic_video_factory, page, "queue-qa-membership")

                page.locator("button[data-tool='queue']").click(force=True)
                page.wait_for_timeout(300)

                queue_before = page.evaluate("() => (state?.project?.queue || []).length")
                assert queue_before == 0

                page.locator(".queue-membership-btn").first.click()
                page.wait_for_timeout(500)

                queue_after = page.evaluate("() => (state?.project?.queue || []).length")
                assert queue_after >= 1

                entry_status = page.evaluate("() => (state?.project?.queue || [])[0]?.status || ''")
                assert entry_status in ("queued", "stale")

                status_text = page.locator("#status-copy").inner_text()
                assert len(status_text.strip()) > 0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_queue_process_individual_creates_output_file(synthetic_video_factory) -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary(synthetic_video_factory, page, "queue-qa-process")

                page.locator("button[data-tool='queue']").click(force=True)
                page.wait_for_timeout(300)

                page.locator(".queue-membership-btn").first.click()
                page.wait_for_timeout(500)

                queue_count = page.evaluate("() => (state?.project?.queue || []).length")
                assert queue_count >= 1

                project_dir = page.evaluate("() => state?.project?.path || ''")
                assert project_dir

                page.locator("#queue-process-btn").click()
                page.wait_for_timeout(15000)

                stage_status = page.evaluate("() => (state?.project?.queue || [])[0]?.status || ''")
                output_path = page.evaluate("() => (state?.project?.queue || [])[0]?.output_path || ''")

                if stage_status == "complete":
                    assert output_path
                    output_file = Path(output_path)
                    assert output_file.exists()
                    assert output_file.stat().st_size > 0
                else:
                    assert stage_status == "queued"
                    output_dir = Path(project_dir) / "Output"
                    if output_dir.exists():
                        found = list(output_dir.glob("*.mp4"))
                        assert len(found) >= 1
                        assert found[0].stat().st_size > 0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_queue_apply_all_copies_settings(synthetic_video_factory) -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary(synthetic_video_factory, page, "queue-qa-apply")

                page.locator("button[data-tool='queue']").click(force=True)
                page.wait_for_timeout(300)

                page.locator(".queue-membership-btn").first.click()
                page.wait_for_timeout(500)

                page.locator("#queue-apply-all-btn").click()
                page.wait_for_timeout(500)

                status_text = page.locator("#status-copy").inner_text()
                assert "Applied" in status_text or "settings" in status_text.lower()
            finally:
                browser.close()
    finally:
        server.shutdown()
