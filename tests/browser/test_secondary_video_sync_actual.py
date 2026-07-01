from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from tests.browser.helpers.video_test_helpers import (
    open_page,
    ensure_project_with_primary_and_merge,
    open_tool,
)


def _enable_merge(page) -> None:
    page.evaluate("() => { state.project.merge.enabled = true; }")
    open_tool(page, "merge")


def test_secondary_video_loads_when_merge_enabled(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(name="secondary-load-p", duration_ms=4000, beep_ms=500)
    )
    merge_path = Path(
        synthetic_video_factory(name="secondary-load-m", duration_ms=4000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "secondary-load.ssproj"
                )
                page.wait_for_timeout(300)

                _enable_merge(page)
                page.wait_for_timeout(500)

                secondary_src = page.evaluate(
                    "() => document.getElementById('secondary-video')?.src || ''"
                )
                assert secondary_src, "Secondary video src should be set when merge enabled"

                secondary_hidden = page.evaluate(
                    "() => document.getElementById('secondary-video')?.hidden || false"
                )
                assert not secondary_hidden, "Secondary video should not be hidden with merge"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_secondary_seeks_to_sync_offset(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(name="sync-offset-p", duration_ms=4000, beep_ms=500)
    )
    merge_path = Path(synthetic_video_factory(name="sync-offset-m", duration_ms=4000, beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "sync-offset.ssproj"
                )
                page.wait_for_timeout(500)
                page.wait_for_function(
                    "() => document.getElementById('primary-video')?.readyState >= 2",
                    timeout=10000,
                )

                page.evaluate("""() => {
                    const sources = state.project.merge_sources;
                    if (sources && sources[0]) sources[0].sync_offset_ms = 500;
                    document.getElementById('primary-video').currentTime = 1.0;
                }""")
                page.wait_for_timeout(500)

                _enable_merge(page)
                page.wait_for_timeout(500)

                secondary = page.evaluate("""() => {
                    const s = document.getElementById('secondary-video');
                    return s ? s.currentTime : -1;
                }""")
                assert secondary >= 0, "Secondary video not found"
                assert abs(secondary - 1.5) < 0.5, (
                    f"Expected secondary currentTime ~1.5s (primary 1.0 + offset 0.5), got {secondary}"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_secondary_uses_trim_derivative_path(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="trim-path-p", duration_ms=4000, beep_ms=500))
    merge_path = Path(synthetic_video_factory(name="trim-path-m", duration_ms=4000, beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-path.ssproj"
                )

                page.evaluate("""() => {
                    const sources = state.project.merge_sources;
                    if (!sources || !sources[0]) return;
                    sources[0].trim_derivative = {
                        active_path_kind: 'local_derivative',
                        derivative_path: '/tmp/trimmed-merge.mp4',
                        start_s: 0.5,
                        end_s: 3.0,
                    };
                }""")
                page.evaluate("() => { state.project.merge.enabled = true; }")
                page.wait_for_timeout(300)

                src = page.evaluate("() => document.getElementById('secondary-video')?.src || ''")
                assert "trimmed-merge" in src or "/media/secondary" in src, (
                    f"Secondary src should reference derivative, got {src}"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_secondary_playback_rate_matches_primary(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="rate-match-p", duration_ms=4000, beep_ms=500))
    merge_path = Path(synthetic_video_factory(name="rate-match-m", duration_ms=4000, beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "rate-match.ssproj"
                )
                page.wait_for_timeout(500)
                page.wait_for_function(
                    "() => document.getElementById('primary-video')?.readyState >= 2",
                    timeout=10000,
                )

                _enable_merge(page)
                page.wait_for_timeout(500)

                page.evaluate(
                    "() => { document.getElementById('primary-video').playbackRate = 0.75; }"
                )
                page.evaluate("() => document.getElementById('primary-video').play()")
                page.wait_for_timeout(500)

                primary_rate = page.evaluate(
                    "() => document.getElementById('primary-video')?.playbackRate || 0"
                )
                secondary_rate = page.evaluate(
                    "() => document.getElementById('secondary-video')?.playbackRate || 0"
                )
                assert abs(secondary_rate - primary_rate) < 0.1, (
                    f"Secondary rate {secondary_rate} should match primary rate {primary_rate}"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
