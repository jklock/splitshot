from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from tests.browser.helpers.activity_tracker import ActivityTracker
from tests.browser.helpers.video_test_helpers import (
    open_page,
    ensure_project_with_primary_and_merge,
)


def test_import_primary_video_creates_project_state(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(name="import-primary", duration_ms=4000, beep_ms=500)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    tracker = ActivityTracker(server.url)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, primary_path, "import-test.ssproj"
                )
                entries = tracker.assert_activity_count("file.ingested", 1)
                meta = entries[0].get("detail", {}) if entries else {}
                assert meta.get("shots", 0) >= 1, "Expected at least 1 detected shot"

                assert page.evaluate("() => Boolean(state?.project?.primary_video?.path)")
                dur = page.evaluate("() => state?.project?.primary_video?.duration_ms ?? 0") or 0
                assert dur > 0, "Expected non-zero duration"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_import_merge_video_adds_source(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="imp-merge-p", duration_ms=4000, beep_ms=500))
    merge_path = Path(synthetic_video_factory(name="imp-merge-m", duration_ms=3000, beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "merge-import-test.ssproj"
                )
                merge_count = page.evaluate("() => (state?.project?.merge_sources || []).length")
                assert merge_count >= 1, "Expected at least 1 merge source"

                source = page.evaluate(
                    "() => { const s = (state?.project?.merge_sources || [])[0]; return s ? s.asset?.path || null : null; }"
                )
                assert source, "Merge source should have an asset path"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_import_two_merge_sources(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="multi-p", duration_ms=4000, beep_ms=500))
    merge1_path = Path(synthetic_video_factory(name="multi-m1", duration_ms=3000))
    merge2_path = Path(synthetic_video_factory(name="multi-m2", duration_ms=3500))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    tracker = ActivityTracker(server.url)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge1_path, "multi-source.ssproj"
                )
                page.locator("#merge-media-input").set_input_files(str(merge2_path))
                page.wait_for_function("() => (state?.project?.merge_sources || []).length >= 2")
                tracker.assert_activity_count("file.ingested", 2)
                count = page.evaluate("() => (state?.project?.merge_sources || []).length")
                assert count >= 2, f"Expected 2+ merge sources, got {count}"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_import_video_metadata_populated(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="meta-test", duration_ms=4000, beep_ms=500, resolution=(320, 180)
        )
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, primary_path, "metadata-test.ssproj"
                )
                dur = page.evaluate("() => state?.project?.primary_video?.duration_ms ?? 0") or 0
                assert abs(dur - 4000) < 200, f"Expected duration ~4000ms, got {dur}"

                w = page.evaluate("() => state?.project?.primary_video?.width ?? 0") or 0
                h = page.evaluate("() => state?.project?.primary_video?.height ?? 0") or 0
                assert w > 0 and h > 0, f"Expected dimensions >0, got {w}x{h}"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_import_primary_video_activates_tool(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(name="activate-tool", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, primary_path, "activate-test.ssproj"
                )
                tool = page.evaluate("() => activeTool")
                assert tool == "media", f"Expected media tool, got {tool}"
            finally:
                browser.close()
    finally:
        server.shutdown()
