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


def _load_primary_video(page, primary_path: Path) -> None:
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_path = str(primary_path.parent / "waveform-qa.ssproj")
        page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
        page.wait_for_function("() => Boolean(state?.project?.path)")
    page.locator("#primary-file-input").set_input_files(str(primary_path))
    page.locator(".waveform-shot-card").first.wait_for(state="attached")


def test_waveform_total_time_label_renders(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="waveform-qa-time", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                total_label = page.locator("#waveform-total-time")
                assert total_label.count() == 1
                text = total_label.inner_text()
                assert "s" in text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_total_time_matches_video_duration(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="waveform-qa-dur",
            duration_ms=4000,
            beep_ms=500,
            shot_times_ms=[600, 1000, 1400],
            resolution=(320, 180),
        )
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.wait_for_timeout(300)
                dur_ms = page.evaluate("() => state?.project?.primary_video?.duration_ms || 0")
                total_text = page.locator("#waveform-total-time").inner_text()
                expected_s = f"{(dur_ms / 1000):.2f}"
                assert expected_s in total_text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_waveform_expand_shows_shot_list(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="waveform-qa-expand",
            duration_ms=4000,
            beep_ms=500,
            shot_times_ms=[600, 1000, 1400],
        )
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                page.locator("#expand-waveform").click()
                page.wait_for_timeout(300)
                assert page.locator(".waveform-shot-card").count() >= 1
            finally:
                browser.close()
    finally:
        server.shutdown()
