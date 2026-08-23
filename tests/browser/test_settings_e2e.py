from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import splitshot.config as splitshot_config
from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController

SETTINGS_SECTION_IDS = [
    "global-template",
    "scoring",
    "pip",
    "overlay",
    "markers",
    "export",
    "shotml",
]


def test_settings_path_override_isolated_from_user_profile(tmp_path: Path) -> None:
    settings_path = tmp_path / "isolated" / "settings.json"
    env = {**os.environ, "SPLITSHOT_SETTINGS_PATH": str(settings_path)}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from splitshot.config import SETTINGS_PATH, load_settings; load_settings(); print(SETTINGS_PATH)",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(settings_path)
    assert settings_path.is_file()


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _open_settings(page) -> None:
    page.locator("#settings-rail-button").click(force=True)
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
    section.locator("button[data-section-toggle]").click()
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
                    toggle = section.locator("button[data-section-toggle]")
                    toggle.wait_for(state="visible")
                    assert (
                        section.evaluate("element => element.classList.contains('collapsed')")
                        is True
                    )
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
                    assert (
                        section.evaluate("element => element.classList.contains('collapsed')")
                        is False
                    )

                overlay_selector = _settings_section_selector("overlay")
                overlay_section = page.locator(overlay_selector)
                overlay_section.locator("button[data-section-toggle]").click()
                page.wait_for_function(
                    "(sectionSelector) => document.querySelector(sectionSelector)?.classList.contains('collapsed') === true",
                    arg=overlay_selector,
                )

                page.locator('button[data-tool="timing"]').click(force=True)
                page.wait_for_function("() => activeTool === 'timing'")

                _open_settings(page)
                assert (
                    overlay_section.evaluate("element => element.classList.contains('collapsed')")
                    is True
                )
                for section_id in [
                    section for section in SETTINGS_SECTION_IDS if section != "overlay"
                ]:
                    selector = _settings_section_selector(section_id)
                    section = page.locator(selector)
                    assert (
                        section.evaluate("element => element.classList.contains('collapsed')")
                        is False
                    )
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
                project_layout = page.evaluate("state.project.merge.layout")
                project_quality = page.evaluate("state.project.export.quality")
                assert project_layout == "pip", f"unexpected layout: {project_layout}"
                assert project_quality == "low", f"unexpected quality: {project_quality}"
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
                _apply_settings_defaults_and_wait(
                    page, "() => state?.settings?.default_match_type === 'idpa'"
                )
                page.locator("#settings-pip-size").select_option("50%")
                _apply_settings_defaults_and_wait(page, "() => state?.settings?.pip_size === '50%'")
                page.locator("#settings-export-quality").select_option("low")
                _apply_settings_defaults_and_wait(
                    page, "() => state?.settings?.export_quality === 'low'"
                )
                page.locator("#settings-export-two-pass").check()
                _apply_settings_defaults_and_wait(
                    page, "() => state?.settings?.export_two_pass === true"
                )

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
                next_export_preset = next(
                    (value for value in export_preset_values if value != "source"),
                    export_preset_values[0],
                )

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
                _set_settings_control(page, "settings-overlay-custom-opacity", "75")
                _set_settings_control(page, "settings-timer-badge-background-color", "#101010")
                _set_settings_control(page, "settings-timer-badge-text-color", "#f8fafc")
                _set_settings_control(page, "settings-timer-badge-opacity", "85")
                _set_settings_control(page, "settings-shot-badge-background-color", "#1d4ed8")
                _set_settings_control(page, "settings-shot-badge-text-color", "#eef2ff")
                _set_settings_control(page, "settings-shot-badge-opacity", "80")
                _set_settings_control(
                    page, "settings-current-shot-badge-background-color", "#dc2626"
                )
                _set_settings_control(page, "settings-current-shot-badge-text-color", "#ffffff")
                _set_settings_control(page, "settings-current-shot-badge-opacity", "75")
                _set_settings_control(page, "settings-hit-factor-badge-background-color", "#047857")
                _set_settings_control(page, "settings-hit-factor-badge-text-color", "#ecfdf5")
                _set_settings_control(page, "settings-hit-factor-badge-opacity", "70")
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


def _assert_saved_layout(controller: ProjectController) -> None:
    assert controller.project.ui_state.layout_locked is False
    assert controller.project.ui_state.rail_width == 96
    assert controller.project.ui_state.inspector_width == 620
    assert controller.project.ui_state.waveform_height == 240


def test_settings_layout_section_captures_current_layout_and_resets(tmp_path: Path) -> None:
    assert tmp_path in splitshot_config.SETTINGS_PATH.parents
    first_project = tmp_path / "saved-layout-first"
    second_project = tmp_path / "saved-layout-second"
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, "layout")
                page.evaluate(
                    """() => {
                        layoutLocked = false;
                        layoutSizes = { railWidth: 96, inspectorWidth: 620, waveformHeight: 240 };
                        syncLocalProjectUiState();
                        renderSettingsPane();
                    }"""
                )

                page.evaluate(
                    """() => {
                        const button = document.getElementById("settings-use-current-layout");
                        window.__layoutSaveProof = {
                            button,
                            clicks: 0,
                            settingsRequests: [],
                        };
                        button.addEventListener("click", () => {
                            window.__layoutSaveProof.clicks += 1;
                        }, { capture: true });
                        const originalFetch = window.fetch.bind(window);
                        window.fetch = (input, init = {}) => {
                            const url = new URL(typeof input === "string" ? input : input.url, window.location.href);
                            if (url.pathname === "/api/settings" && init.method === "POST") {
                                window.__layoutSaveProof.settingsRequests.push(JSON.parse(init.body || "{}"));
                            }
                            return originalFetch(input, init);
                        };
                        button.click();
                    }"""
                )
                assert page.evaluate("() => window.__layoutSaveProof.clicks") == 1
                assert page.evaluate("() => window.__layoutSaveProof.button.isConnected") is True
                page.wait_for_function(
                    """() => state?.settings?.layout_locked === false
                      && state?.settings?.layout_rail_width === 96
                      && state?.settings?.layout_inspector_width === 620
                      && state?.settings?.layout_waveform_height === 240"""
                )
                page.wait_for_function(
                    "() => window.__layoutSaveProof.settingsRequests.length === 1"
                )
                request_payload = page.evaluate(
                    "() => window.__layoutSaveProof.settingsRequests[0]"
                )
                assert request_payload == {
                    "scope": "app",
                    "section": "layout",
                    "project_defaults": True,
                    "settings": {
                        "layout_locked": False,
                        "layout_rail_width": 96,
                        "layout_inspector_width": 620,
                        "layout_waveform_height": 240,
                    },
                }
                assert page.evaluate("() => window.__layoutSaveProof.button.isConnected") is True
                assert page.evaluate("() => layoutSizes.inspectorWidth") == 620
                assert (
                    page.evaluate(
                        "() => getComputedStyle(document.documentElement).getPropertyValue('--inspector-width').trim()"
                    )
                    == "614px"
                )

                disk_settings = json.loads(splitshot_config.SETTINGS_PATH.read_text())
                assert disk_settings["layout_locked"] is False
                assert disk_settings["layout_rail_width"] == 96
                assert disk_settings["layout_inspector_width"] == 620
                assert disk_settings["layout_waveform_height"] == 240

                page.evaluate("(path) => createNewProject(path)", str(first_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(first_project)
                )
                _assert_saved_layout(server.controller)

                page.evaluate("(path) => createNewProject(path)", str(second_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(second_project)
                )
                _assert_saved_layout(server.controller)

                page.evaluate("(path) => useProjectFolder(path)", str(first_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(first_project)
                )
                _assert_saved_layout(server.controller)

                restarted = ProjectController()
                _assert_saved_layout(restarted)
                restarted.open_project(str(first_project))
                _assert_saved_layout(restarted)

                _open_settings(page)
                _expand_settings_section(page, "layout")
                page.locator("#settings-release-layout").click()
                page.wait_for_function(
                    """() => state?.settings?.layout_locked === null
                      && state?.settings?.layout_rail_width === null
                      && state?.settings?.layout_inspector_width === null
                      && state?.settings?.layout_waveform_height === null"""
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_section_reset_preserves_other_sections() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, "pip")
                _expand_settings_section(page, "export")

                page.locator("#settings-pip-size").select_option("50%")
                _apply_settings_defaults_and_wait(page, "() => state?.settings?.pip_size === '50%'")
                page.locator("#settings-export-quality").select_option("low")
                _apply_settings_defaults_and_wait(
                    page, "() => state?.settings?.export_quality === 'low'"
                )

                page.locator("#settings-reset-section-export").click()
                page.wait_for_function(
                    """() => state?.settings?.pip_size === '50%'
                      && state?.settings?.export_quality === 'high'"""
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def _value_at_path(payload: object, path: list[str]) -> object:
    current = payload
    for key in path:
        assert isinstance(current, dict)
        current = current[key]
    return current


def test_every_settings_value_survives_immediate_rerender_disk_save_and_restart() -> None:
    cases = [
        ("settings-default-tool", "metrics", ["default_tool"], "metrics", False),
        ("settings-reopen-last-tool", False, ["reopen_last_tool"], False, True),
        ("settings-layout-locked", False, ["layout_locked"], False, True),
        ("settings-layout-rail-width", "92", ["layout_rail_width"], 92, False),
        ("settings-layout-inspector-width", "610", ["layout_inspector_width"], 610, False),
        ("settings-layout-waveform-height", "245", ["layout_waveform_height"], 245, False),
        ("settings-default-match-type", "idpa", ["default_match_type"], "idpa", False),
        ("settings-merge-layout", "pip", ["merge_layout"], "pip", False),
        ("settings-pip-size", "50%", ["pip_size"], "50%", False),
        ("settings-merge-pip-x", "0.24", ["merge_pip_x"], 0.24, False),
        ("settings-merge-pip-y", "0.76", ["merge_pip_y"], 0.76, False),
        ("settings-overlay-position", "left", ["overlay_position"], "left", False),
        ("settings-badge-size", "L", ["badge_size"], "L", False),
        (
            "settings-overlay-custom-background-color",
            "#123456",
            ["overlay_custom_box_background_color"],
            "#123456",
            False,
        ),
        (
            "settings-overlay-custom-text-color",
            "#abcdef",
            ["overlay_custom_box_text_color"],
            "#abcdef",
            False,
        ),
        (
            "settings-overlay-custom-opacity",
            "63",
            ["overlay_custom_box_opacity"],
            0.63,
            False,
        ),
        (
            "settings-timer-badge-background-color",
            "#101010",
            ["timer_badge", "background_color"],
            "#101010",
            False,
        ),
        (
            "settings-timer-badge-text-color",
            "#f0f0f0",
            ["timer_badge", "text_color"],
            "#f0f0f0",
            False,
        ),
        ("settings-timer-badge-opacity", "81", ["timer_badge", "opacity"], 0.81, False),
        (
            "settings-shot-badge-background-color",
            "#202020",
            ["shot_badge", "background_color"],
            "#202020",
            False,
        ),
        (
            "settings-shot-badge-text-color",
            "#e0e0e0",
            ["shot_badge", "text_color"],
            "#e0e0e0",
            False,
        ),
        ("settings-shot-badge-opacity", "72", ["shot_badge", "opacity"], 0.72, False),
        (
            "settings-current-shot-badge-background-color",
            "#303030",
            ["current_shot_badge", "background_color"],
            "#303030",
            False,
        ),
        (
            "settings-current-shot-badge-text-color",
            "#d0d0d0",
            ["current_shot_badge", "text_color"],
            "#d0d0d0",
            False,
        ),
        (
            "settings-current-shot-badge-opacity",
            "69",
            ["current_shot_badge", "opacity"],
            0.69,
            False,
        ),
        (
            "settings-hit-factor-badge-background-color",
            "#404040",
            ["hit_factor_badge", "background_color"],
            "#404040",
            False,
        ),
        (
            "settings-hit-factor-badge-text-color",
            "#c0c0c0",
            ["hit_factor_badge", "text_color"],
            "#c0c0c0",
            False,
        ),
        (
            "settings-hit-factor-badge-opacity",
            "58",
            ["hit_factor_badge", "opacity"],
            0.58,
            False,
        ),
        ("settings-marker-enabled", False, ["marker_template", "enabled"], False, True),
        (
            "settings-marker-content-type",
            "text_image",
            ["marker_template", "content_type"],
            "text_image",
            False,
        ),
        (
            "settings-marker-text-source",
            "custom",
            ["marker_template", "text_source"],
            "custom",
            False,
        ),
        ("settings-marker-duration", "1.250", ["marker_template", "duration_ms"], 1250, False),
        (
            "settings-marker-use-shot-split-duration",
            True,
            ["marker_template", "use_shot_split_duration"],
            True,
            True,
        ),
        ("settings-marker-width", "420", ["marker_template", "width"], 420, False),
        ("settings-marker-height", "180", ["marker_template", "height"], 180, False),
        (
            "settings-marker-follow-motion",
            True,
            ["marker_template", "follow_motion"],
            True,
            True,
        ),
        (
            "settings-marker-quadrant",
            "bottom_right",
            ["marker_template", "quadrant"],
            "bottom_right",
            False,
        ),
        (
            "settings-marker-background-color",
            "#505050",
            ["marker_template", "background_color"],
            "#505050",
            False,
        ),
        (
            "settings-marker-text-color",
            "#b0b0b0",
            ["marker_template", "text_color"],
            "#b0b0b0",
            False,
        ),
        ("settings-marker-opacity", "47", ["marker_template", "opacity"], 0.47, False),
        ("settings-export-quality", "low", ["export_quality"], "low", False),
        (
            "settings-export-preset",
            "universal_vertical",
            ["export_preset"],
            "universal_vertical",
            False,
        ),
        ("settings-export-frame-rate", "60", ["export_frame_rate"], "60", False),
        ("settings-export-video-codec", "hevc", ["export_video_codec"], "hevc", False),
        ("settings-export-audio-codec", "aac", ["export_audio_codec"], "aac", False),
        ("settings-export-color-space", "bt709_sdr", ["export_color_space"], "bt709_sdr", False),
        ("settings-export-two-pass", True, ["export_two_pass"], True, True),
        (
            "settings-export-ffmpeg-preset",
            "slow",
            ["export_ffmpeg_preset"],
            "slow",
            False,
        ),
        (
            "settings-shotml-threshold",
            "0.55",
            ["shotml_defaults", "detection_threshold"],
            0.55,
            False,
        ),
    ]

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                page.evaluate(
                    """() => {
                        window.__settingsSaveRequests = [];
                        const originalFetch = window.fetch.bind(window);
                        window.fetch = (input, init = {}) => {
                            const url = new URL(typeof input === "string" ? input : input.url, window.location.href);
                            if (url.pathname === "/api/settings" && init.method === "POST") {
                                window.__settingsSaveRequests.push(JSON.parse(init.body || "{}"));
                            }
                            return originalFetch(input, init);
                        };
                    }"""
                )

                for index, (control_id, value, path, expected, is_checkbox) in enumerate(
                    cases, start=1
                ):
                    visible_value = page.evaluate(
                        """({ controlId, value, isCheckbox }) => {
                            const control = document.getElementById(controlId);
                            if (isCheckbox) control.checked = Boolean(value);
                            else control.value = String(value);
                            control.dispatchEvent(new Event("change", { bubbles: true }));
                            control.blur();
                            renderSettingsPane();
                            return isCheckbox ? control.checked : control.value;
                        }""",
                        {
                            "controlId": control_id,
                            "value": value,
                            "isCheckbox": is_checkbox,
                        },
                    )
                    assert visible_value == value, control_id
                    page.wait_for_function(
                        "count => window.__settingsSaveRequests.length >= count", arg=index
                    )
                    page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
                    layer_value = page.evaluate(
                        """path => path.reduce(
                            (value, key) => value?.[key], state?.settings_layers?.app
                        )""",
                        path,
                    )
                    assert layer_value == expected, control_id

                disk_settings = json.loads(splitshot_config.SETTINGS_PATH.read_text())
                restarted_settings = ProjectController().settings.config_dict()
                for control_id, _value, path, expected, _is_checkbox in cases:
                    assert _value_at_path(disk_settings, path) == expected, control_id
                    assert _value_at_path(restarted_settings, path) == expected, control_id
            finally:
                browser.close()
    finally:
        server.shutdown()
