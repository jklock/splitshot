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


def _ensure_project_with_primary_and_merge(
    page, primary_path: Path, merge_path: Path, project_name: str
) -> None:
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_dir = str(primary_path.parent / project_name)
        page.evaluate(f"() => createNewProject({json.dumps(project_dir)})")
        page.wait_for_function("() => Boolean(state?.project?.path)")

    if not page.evaluate("Boolean(state?.project?.primary_video?.path)"):
        page.locator("#primary-file-input").set_input_files(str(primary_path))
        page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")

    merge_count = page.evaluate("() => (state?.project?.merge_sources || []).length")
    if merge_count == 0:
        page.locator("#merge-media-input").set_input_files(str(merge_path))
        page.wait_for_function("() => (state?.project?.merge_sources || []).length > 0")


def test_trim_pane_renders_global_and_source_sections(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-primary", duration_ms=4000, beep_ms=500, shot_times_ms=[800, 1200, 1600]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-merge", duration_ms=4000, beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(200)
                assert page.evaluate("activeTool") == "trim-sync"

                assert page.locator(".trim-timing-bar").count() >= 1
                assert page.locator("#trim-global-start").count() == 1
                assert page.locator("#trim-global-end").count() == 1
                assert page.locator("#trim-global-apply").count() == 1
                assert page.locator("#trim-global-clear").count() == 1

                assert page.locator(".trim-source-card").count() >= 1
                assert page.locator(".trim-computed-label").count() >= 1
                assert page.locator(".trim-beep-btn").count() >= 1
                assert page.locator(".trim-last-shot-btn").count() >= 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_pane_timing_bar_shows_beep_and_last_shot(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-timing", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-timing-merge", beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-timing.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(300)

                timing_text = page.locator(".trim-timing-bar").inner_text()
                assert "Beep:" in timing_text
                assert "Last Shot:" in timing_text
                assert "Total:" in timing_text
                assert timing_text.count("s") >= 3
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_pane_default_buffers_are_two_seconds(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-buffers", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-buffers-merge", beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-buffers.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(200)

                global_start = page.locator("#trim-global-start").input_value()
                global_end = page.locator("#trim-global-end").input_value()
                assert global_start == "2.00"
                assert global_end == "2.00"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_pane_reset_to_defaults_button(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-reset", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-reset-merge", beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-reset.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(200)

                page.locator("#trim-global-start").fill("5.00")
                page.locator("#trim-global-end").fill("5.00")
                page.locator("#trim-global-defaults-btn").click()
                page.wait_for_timeout(100)

                start_val = page.locator("#trim-global-start").input_value()
                end_val = page.locator("#trim-global-end").input_value()
                assert start_val != "5.00"
                assert end_val != "5.00"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_pane_computed_label_format(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-computed", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-computed-merge", beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-computed.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(500)

                label = page.locator(".trim-computed-label").first.inner_text()
                assert "Before trim:" in label
                assert "After trim:" in label
                assert "Kept:" in label
                assert "Total:" in label
            finally:
                browser.close()
    finally:
        server.shutdown()
