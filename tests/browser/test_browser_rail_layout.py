from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


def test_browser_rail_footer_buttons_stay_square_and_stacked() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = None
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as exc:  # pragma: no cover - depends on local browser install
                pytest.skip(f"Playwright Chromium is unavailable: {exc}")

            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(server.url, wait_until="domcontentloaded")

                settings_button = page.locator("#settings-rail-button")
                toggle_button = page.locator("#toggle-rail")
                settings_pane = page.locator('[data-tool-pane="settings"]')

                settings_button.wait_for(state="visible")
                toggle_button.wait_for(state="visible")

                settings_box = settings_button.bounding_box()
                toggle_box = toggle_button.bounding_box()
                assert settings_box is not None
                assert toggle_box is not None
                assert settings_box["width"] == pytest.approx(settings_box["height"])
                assert toggle_box["width"] == pytest.approx(toggle_box["height"])
                assert settings_box["width"] == pytest.approx(toggle_box["width"])
                assert settings_box["height"] == pytest.approx(toggle_box["height"])
                assert abs(settings_box["x"] - toggle_box["x"]) <= 2
                assert settings_box["y"] < toggle_box["y"]

                settings_button.click()
                settings_pane.wait_for(state="visible")
                assert page.locator('.tool-item.active[data-tool="settings"]').count() == 1

                toggle_button.click()
                page.wait_for_function(
                    "document.querySelector('.cockpit-shell')?.classList.contains('rail-collapsed') === true"
                )
                assert toggle_button.text_content() == "▶"
                assert page.evaluate("localStorage.getItem('splitshot.railCollapsed')") == "true"

                collapsed_settings_box = settings_button.bounding_box()
                collapsed_toggle_box = toggle_button.bounding_box()
                assert collapsed_settings_box is not None
                assert collapsed_toggle_box is not None
                assert collapsed_settings_box["width"] == pytest.approx(settings_box["width"])
                assert collapsed_settings_box["height"] == pytest.approx(settings_box["height"])
                assert collapsed_toggle_box["width"] == pytest.approx(toggle_box["width"])
                assert collapsed_toggle_box["height"] == pytest.approx(toggle_box["height"])
            finally:
                if browser is not None:
                    browser.close()
    finally:
        server.shutdown()


def test_scoring_edit_button_opens_and_closes_workbench() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = None
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as exc:  # pragma: no cover - depends on local browser install
                pytest.skip(f"Playwright Chromium is unavailable: {exc}")

            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(server.url, wait_until="domcontentloaded")

                page.locator('button[data-tool="scoring"]').click()
                page.locator('[data-tool-pane="scoring"]').wait_for(state="visible")

                page.locator('#expand-scoring').click()
                workbench = page.locator('#scoring-workbench')
                workbench.wait_for(state="visible")
                assert page.evaluate("document.querySelector('#scoring-workbench')?.hidden") is False

                page.locator('#collapse-scoring').click()
                page.wait_for_function("document.querySelector('#scoring-workbench')?.hidden === true")
                assert page.evaluate("document.querySelector('#scoring-workbench')?.hidden") is True
            finally:
                if browser is not None:
                    browser.close()
    finally:
        server.shutdown()