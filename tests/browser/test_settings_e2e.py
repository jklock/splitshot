from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


SETTINGS_SECTION_IDS = [
    "global-template",
    "scoring",
    "pip",
    "overlay",
    "markers",
    "export",
    "shotml",
]


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _open_settings(page) -> None:
    page.locator('#settings-rail-button').click(force=True)
    page.wait_for_timeout(100)
    assert page.evaluate("activeTool") == "settings"
    page.locator('[data-tool-pane="settings"]').wait_for(state="visible")


def _settings_section_selector(section_id: str) -> str:
    return f'[data-settings-section="{section_id}"]'


def _expand_settings_section(page, section_id: str) -> None:
    selector = _settings_section_selector(section_id)
    section = page.locator(selector)
    if section.evaluate("element => element.classList.contains('collapsed')") is False:
        return
    section.locator('button[data-section-toggle]').click()
    page.wait_for_function(
        "(sectionSelector) => !document.querySelector(sectionSelector)?.classList.contains('collapsed')",
        arg=selector,
    )


def _set_settings_control(page, control_id: str, value: str) -> None:
    control = page.locator(f"#{control_id}")
    if control.evaluate("element => element.tagName === 'SELECT'"):
        control.select_option(value)
        return
    control.evaluate(
        """(element, nextValue) => {
            element.value = String(nextValue);
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        value,
    )


def _apply_settings_defaults_and_wait(page, predicate: str, arg=None) -> None:
    page.wait_for_function("() => state?.settings !== undefined")
    page.evaluate("() => applySettingsDefaults()")
    page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
    if arg is None:
        page.wait_for_function(predicate)
    else:
        page.wait_for_function(predicate, arg=arg)


def test_settings_section_toggles_survive_tool_route_changes() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)

                for section_id in SETTINGS_SECTION_IDS:
                    selector = _settings_section_selector(section_id)
                    section = page.locator(selector)
                    toggle = section.locator('button[data-section-toggle]')
                    toggle.wait_for(state="visible")
                    assert section.evaluate("element => element.classList.contains('collapsed')") is True
                    toggle.click()
                page.wait_for_function(
                        "(sectionSelector) => !document.querySelector(sectionSelector)?.classList.contains('collapsed')",
                        arg=selector,
                )

                page.locator('button[data-tool="project"]').click(force=True)
                page.wait_for_function("() => activeTool === 'project'")

                _open_settings(page)
                for section_id in SETTINGS_SECTION_IDS:
                    selector = _settings_section_selector(section_id)
                    section = page.locator(selector)
                    assert section.evaluate("element => element.classList.contains('collapsed')") is False

                overlay_selector = _settings_section_selector("overlay")
                overlay_section = page.locator(overlay_selector)
                overlay_section.locator('button[data-section-toggle]').click()
                page.wait_for_function(
                    "(sectionSelector) => document.querySelector(sectionSelector)?.classList.contains('collapsed') === true",
                    arg=overlay_selector,
                )

                page.locator('button[data-tool="timing"]').click(force=True)
                page.wait_for_function("() => activeTool === 'timing'")

                _open_settings(page)
                assert overlay_section.evaluate("element => element.classList.contains('collapsed')") is True
                for section_id in [section for section in SETTINGS_SECTION_IDS if section != "overlay"]:
                    selector = _settings_section_selector(section_id)
                    section = page.locator(selector)
                    assert section.evaluate("element => element.classList.contains('collapsed')") is False
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_import_current_and_reset_defaults_round_trip_visible_project_defaults() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                page.locator('button[data-tool="merge"]').click(force=True)
                page.wait_for_function("() => activeTool === 'merge'")
                page.locator("#merge-layout").select_option("pip")
                page.wait_for_function("() => state?.project?.merge?.layout === 'pip'")

                page.locator('button[data-tool="export"]').click(force=True)
                page.wait_for_function("() => activeTool === 'export'")
                page.locator("#quality").select_option("low")
                page.wait_for_function("() => state?.project?.export?.quality === 'low'")

                _open_settings(page)
                _expand_settings_section(page, "global-template")
                _expand_settings_section(page, "pip")
                _expand_settings_section(page, "overlay")
                _expand_settings_section(page, "export")

                page.locator("#settings-import-current").click()
                page.wait_for_function(
                    """() => state?.settings?.merge_layout === 'pip' && state?.settings?.export_quality === 'low'"""
                )
                assert page.locator("#settings-merge-layout").input_value() == "pip"
                assert page.locator("#settings-export-quality").input_value() == "low"

                page.locator("#settings-reset-defaults").click(force=True)
                page.wait_for_function(
                    """() => state?.settings?.merge_layout === 'side_by_side' && state?.settings?.export_quality === 'high'"""
                )
                assert page.locator("#settings-merge-layout").input_value() == "side_by_side"
                assert page.locator("#settings-export-quality").input_value() == "high"
                assert page.evaluate("state.project.merge.layout") == "side_by_side"
                assert page.evaluate("state.project.export.quality") == "high"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_global_template_fields_update_defaults_state_and_reset() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, "global-template")

                page.locator("#settings-scope").select_option("app")
                page.locator("#settings-default-tool").select_option("metrics")
                page.locator("#settings-reopen-last-tool").uncheck()
                _apply_settings_defaults_and_wait(
                    page,
                    "() => state?.settings?.default_tool === 'metrics' && state?.settings?.reopen_last_tool === false",
                )

                assert page.locator("#settings-default-tool").input_value() == "metrics"
                assert page.locator("#settings-reopen-last-tool").is_checked() is False

                page.locator("#settings-reset-defaults").click(force=True)
                page.wait_for_function(
                    """() => document.querySelector('#settings-default-tool')?.value === 'project'
                      && document.querySelector('#settings-reopen-last-tool')?.checked === true"""
                )
                assert page.locator("#settings-default-tool").input_value() == "project"
                assert page.locator("#settings-reopen-last-tool").is_checked() is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_default_controls_commit_to_settings_state_and_reset() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, "global-template")
                _expand_settings_section(page, "scoring")
                _expand_settings_section(page, "pip")
                _expand_settings_section(page, "export")

                page.locator("#settings-default-match-type").select_option("idpa")
                _apply_settings_defaults_and_wait(page, "() => state?.settings?.default_match_type === 'idpa'")
                page.locator("#settings-pip-size").select_option("50%")
                _apply_settings_defaults_and_wait(page, "() => state?.settings?.pip_size === '50%'")
                page.locator("#settings-export-quality").select_option("low")
                _apply_settings_defaults_and_wait(page, "() => state?.settings?.export_quality === 'low'")
                page.locator("#settings-export-two-pass").check()
                _apply_settings_defaults_and_wait(page, "() => state?.settings?.export_two_pass === true")

                assert page.locator("#settings-default-match-type").input_value() == "idpa"
                assert page.locator("#settings-pip-size").input_value() == "50%"
                assert page.locator("#settings-export-quality").input_value() == "low"
                assert page.locator("#settings-export-two-pass").is_checked() is True

                page.locator("#settings-reset-defaults").click()
                page.wait_for_function(
                                        """() => document.querySelector('#settings-default-match-type')?.value === 'uspsa'
                                            && document.querySelector('#settings-pip-size')?.value === '35%'
                                            && document.querySelector('#settings-export-quality')?.value === 'high'
                                            && document.querySelector('#settings-export-two-pass')?.checked === false"""
                )

                assert page.locator("#settings-default-match-type").input_value() == "uspsa"
                assert page.locator("#settings-pip-size").input_value() == "35%"
                assert page.locator("#settings-export-quality").input_value() == "high"
                assert page.locator("#settings-export-two-pass").is_checked() is False
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_remaining_defaults_commit_and_reset_all_panels() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                for section_id in ["pip", "export"]:
                    _expand_settings_section(page, section_id)
                _expand_settings_section(page, "overlay")

                export_preset_values = page.locator("#settings-export-preset").evaluate(
                    "select => [...select.options].map((option) => option.value).filter(Boolean)"
                )
                assert export_preset_values
                next_export_preset = next((value for value in export_preset_values if value != "source"), export_preset_values[0])

                page.locator("#settings-merge-layout").select_option("pip")
                page.locator("#settings-pip-size").select_option("50%")

                page.locator("#settings-export-preset").select_option(next_export_preset)
                page.locator("#settings-export-frame-rate").select_option("60")
                page.locator("#settings-export-video-codec").select_option("hevc")
                page.locator("#settings-export-ffmpeg-preset").select_option("fast")
                page.locator("#settings-export-two-pass").check()
                _set_settings_control(page, "settings-overlay-position", "left")
                _set_settings_control(page, "settings-badge-size", "L")
                _set_settings_control(page, "settings-overlay-custom-background-color", "#123456")
                _set_settings_control(page, "settings-overlay-custom-text-color", "#abcdef")
                _set_settings_control(page, "settings-overlay-custom-opacity", "0.75")
                _set_settings_control(page, "settings-timer-badge-background-color", "#101010")
                _set_settings_control(page, "settings-timer-badge-text-color", "#f8fafc")
                _set_settings_control(page, "settings-timer-badge-opacity", "0.85")
                _set_settings_control(page, "settings-shot-badge-background-color", "#1d4ed8")
                _set_settings_control(page, "settings-shot-badge-text-color", "#eef2ff")
                _set_settings_control(page, "settings-shot-badge-opacity", "0.8")
                _set_settings_control(page, "settings-current-shot-badge-background-color", "#dc2626")
                _set_settings_control(page, "settings-current-shot-badge-text-color", "#ffffff")
                _set_settings_control(page, "settings-current-shot-badge-opacity", "0.75")
                _set_settings_control(page, "settings-hit-factor-badge-background-color", "#047857")
                _set_settings_control(page, "settings-hit-factor-badge-text-color", "#ecfdf5")
                _set_settings_control(page, "settings-hit-factor-badge-opacity", "0.7")
                page.locator("#settings-merge-layout").select_option("pip")
                page.locator("#settings-pip-size").select_option("50%")
                page.locator("#settings-export-preset").select_option(next_export_preset)
                page.locator("#settings-export-frame-rate").select_option("60")
                page.locator("#settings-export-video-codec").select_option("hevc")
                page.locator("#settings-export-ffmpeg-preset").select_option("fast")
                page.locator("#settings-export-two-pass").check()
                assert page.locator("#settings-merge-layout").input_value() == "pip"
                assert page.locator("#settings-pip-size").input_value() == "50%"
                assert page.locator("#settings-export-frame-rate").input_value() == "60"
                assert page.locator("#settings-export-video-codec").input_value() == "hevc"
                assert page.locator("#settings-export-ffmpeg-preset").input_value() == "fast"
                assert page.locator("#settings-export-two-pass").is_checked() is True
                assert page.locator("#settings-overlay-position").count() == 1
                assert page.locator("#settings-badge-size").count() == 1
                assert page.locator("#settings-overlay-custom-background-color").count() == 1
                assert page.locator("#settings-overlay-custom-text-color").count() == 1
                assert page.locator("#settings-overlay-custom-opacity").count() == 1

                page.evaluate("document.getElementById('settings-reset-defaults')?.click()")
                page.wait_for_timeout(150)
                assert page.locator("#settings-reset-defaults").count() == 1
                assert page.locator("#settings-export-two-pass").count() == 1
            finally:
                browser.close()
    finally:
        server.shutdown()