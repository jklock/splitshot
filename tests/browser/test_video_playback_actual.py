from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from tests.browser.helpers.activity_tracker import ActivityTracker
from tests.browser.helpers.video_test_helpers import (
    ensure_project_with_primary_and_merge,
    open_page,
)


def test_play_primary_video(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="play-test", duration_ms=4000, beep_ms=500))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    tracker = ActivityTracker(server.url)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, primary_path, "play-test.ssproj"
                )
                page.wait_for_timeout(500)

                video_ready = page.evaluate(
                    "() => document.getElementById('primary-video')?.readyState >= 2"
                )
                if not video_ready:
                    page.wait_for_function(
                        "() => document.getElementById('primary-video')?.readyState >= 2",
                        timeout=10000,
                    )

                page.evaluate("() => document.getElementById('primary-video').play()")
                page.wait_for_function(
                    "() => !document.getElementById('primary-video').paused", timeout=5000
                )
                tracker.assert_activity("video.primary.state")

                is_playing = page.evaluate("() => !document.getElementById('primary-video').paused")
                assert is_playing, "Video should be playing"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_pause_primary_video(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="pause-test", duration_ms=4000, beep_ms=500))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    tracker = ActivityTracker(server.url)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, primary_path, "pause-test.ssproj"
                )
                page.wait_for_timeout(500)
                page.wait_for_function(
                    "() => document.getElementById('primary-video')?.readyState >= 2", timeout=10000
                )

                page.evaluate("() => document.getElementById('primary-video').play()")
                page.wait_for_function(
                    "() => !document.getElementById('primary-video').paused", timeout=5000
                )
                page.wait_for_timeout(300)

                page.evaluate("() => document.getElementById('primary-video').pause()")
                page.wait_for_function(
                    "() => document.getElementById('primary-video').paused", timeout=5000
                )
                tracker.assert_activity_count("video.primary.state", 2)

                is_paused = page.evaluate("() => document.getElementById('primary-video').paused")
                assert is_paused, "Video should be paused"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_seek_primary_video(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="seek-test", duration_ms=4000, beep_ms=500))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    tracker = ActivityTracker(server.url)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, primary_path, "seek-test.ssproj"
                )
                page.wait_for_timeout(500)
                page.wait_for_function(
                    "() => document.getElementById('primary-video')?.readyState >= 2", timeout=10000
                )

                page.evaluate(
                    "() => { document.getElementById('primary-video').currentTime = 1.5; }"
                )
                page.wait_for_timeout(300)

                ct = (
                    page.evaluate("() => document.getElementById('primary-video').currentTime") or 0
                )
                assert abs(ct - 1.5) < 0.3, f"Expected currentTime ~1.5s, got {ct}"

                tracker.assert_activity("video.seeked")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_playback_rate_change(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="rate-test", duration_ms=4000, beep_ms=500))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    tracker = ActivityTracker(server.url)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, primary_path, "rate-test.ssproj"
                )
                page.wait_for_timeout(500)
                page.wait_for_function(
                    "() => document.getElementById('primary-video')?.readyState >= 2", timeout=10000
                )

                page.evaluate(
                    "() => { document.getElementById('primary-video').playbackRate = 0.5; }"
                )
                page.wait_for_timeout(200)

                rate = page.evaluate("() => document.getElementById('primary-video').playbackRate")
                assert abs(rate - 0.5) < 0.01, f"Expected playbackRate 0.5, got {rate}"

                tracker.assert_activity("video.primary.state")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_video_ends_and_stops(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="end-test", duration_ms=1500, beep_ms=200))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    tracker = ActivityTracker(server.url)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, primary_path, "end-test.ssproj"
                )
                page.wait_for_timeout(500)
                page.wait_for_function(
                    "() => document.getElementById('primary-video')?.readyState >= 2", timeout=10000
                )

                page.evaluate("() => document.getElementById('primary-video').play()")
                page.wait_for_function(
                    "() => document.getElementById('primary-video').ended", timeout=10000
                )

                ended = page.evaluate("() => document.getElementById('primary-video').ended")
                paused = page.evaluate("() => document.getElementById('primary-video').paused")
                assert ended, "Video should be ended"
                assert paused, "Video should be paused after end"

                tracker.assert_activity("video.primary.state")
            finally:
                browser.close()
    finally:
        server.shutdown()
