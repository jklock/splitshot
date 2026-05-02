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


def _load_primary_video(page, primary_path: Path) -> None:
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_path = str(primary_path.parent / "browser-rail-layout.ssproj")
        page.evaluate(f"() => createNewProject({json.dumps(project_path)})")
        page.wait_for_function("() => Boolean(state?.project?.path)")
    page.locator("#primary-file-input").set_input_files(str(primary_path))
    page.locator(".waveform-shot-card").first.wait_for(state="attached")


def _open_tool(page, tool: str) -> None:
    page.locator(f'button[data-tool="{tool}"]').click(force=True)
    page.wait_for_function("(expected) => activeTool === expected", arg=tool)


def _open_markers_workbench(page) -> None:
    if not page.evaluate("() => document.getElementById('markers-workbench')?.hidden === false"):
        page.locator("#popup-edit-selected").click()
    page.wait_for_function("() => document.getElementById('markers-workbench')?.hidden === false")


def _unlock_layout(page) -> None:
    if page.evaluate("localStorage.getItem('splitshot.layoutLocked')") == "false":
        return
    page.locator("#toggle-layout-lock-video").click()
    page.wait_for_function("localStorage.getItem('splitshot.layoutLocked') === 'false'")


def test_browser_rail_footer_buttons_stay_square_and_stacked() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
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
                assert page.evaluate("localStorage.getItem('splitshot.activeTool')") == "settings"

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

                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "document.querySelector('.cockpit-shell')?.classList.contains('rail-collapsed') === true"
                )
                page.locator('[data-tool-pane="settings"]').wait_for(state="visible")
                assert page.locator('.tool-item.active[data-tool="settings"]').count() == 1
                assert page.locator("#toggle-rail").text_content() == "▶"
                assert page.locator("#toggle-rail").get_attribute("aria-label") == "Expand left rail"
                assert page.evaluate("localStorage.getItem('splitshot.activeTool')") == "settings"
                assert page.evaluate("localStorage.getItem('splitshot.railCollapsed')") == "true"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_primary_rail_tool_buttons_route_to_matching_panes_and_persist_active_tool() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                tool_ids = [
                    "project",
                    "merge",
                    "scoring",
                    "timing",
                    "markers",
                    "overlay",
                    "review",
                    "export",
                    "metrics",
                    "shotml",
                    "settings",
                ]

                for tool_id in tool_ids:
                    page.locator(f'[data-tool="{tool_id}"]').click(force=True)
                    page.wait_for_function("(tool) => activeTool === tool", arg=tool_id)
                    page.locator(f'[data-tool-pane="{tool_id}"]').wait_for(state="visible")
                    assert page.locator(f'.tool-item.active[data-tool="{tool_id}"]').count() == 1
                    assert page.evaluate("localStorage.getItem('splitshot.activeTool')") == tool_id

                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("(tool) => activeTool === tool", arg=tool_ids[-1])
                page.locator(f'[data-tool-pane="{tool_ids[-1]}"]').wait_for(state="visible")
                assert page.locator(f'.tool-item.active[data-tool="{tool_ids[-1]}"]').count() == 1
                assert page.evaluate("localStorage.getItem('splitshot.activeTool')") == tool_ids[-1]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_scoring_edit_button_opens_and_closes_workbench() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
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
                browser.close()
    finally:
        server.shutdown()


def test_layout_lock_toggle_switches_shell_state_and_persistence() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                toggle_button = page.locator("#toggle-layout-lock-video")
                shell = page.locator(".cockpit-shell")

                assert page.evaluate("localStorage.getItem('splitshot.layoutLocked')") != "false"
                assert toggle_button.text_content() == "🔒"

                toggle_button.click()
                page.wait_for_function("localStorage.getItem('splitshot.layoutLocked') === 'false'")
                assert toggle_button.text_content() == "🔓"
                assert toggle_button.get_attribute("aria-label") == "Lock video layout"
                assert shell.evaluate("element => element.classList.contains('layout-unlocked')") is True

                toggle_button.click()
                page.wait_for_function("localStorage.getItem('splitshot.layoutLocked') === 'true'")
                assert toggle_button.text_content() == "🔒"
                assert toggle_button.get_attribute("aria-label") == "Unlock video layout"
                assert shell.evaluate("element => element.classList.contains('layout-locked')") is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_status_bar_hosts_layout_lock_and_processing_bar_fills_top_row() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                status_bar = page.locator(".status-bar")
                toggle_button = page.locator("#toggle-layout-lock-video")
                video_stage = page.locator(".video-stage")

                status_box = status_bar.bounding_box()
                toggle_box = toggle_button.bounding_box()
                video_box = video_stage.bounding_box()
                assert status_box is not None
                assert toggle_box is not None
                assert video_box is not None

                assert status_box["x"] <= toggle_box["x"]
                assert toggle_box["x"] + toggle_box["width"] <= status_box["x"] + status_box["width"] + 1
                assert status_box["y"] <= toggle_box["y"]
                assert toggle_box["y"] + toggle_box["height"] <= status_box["y"] + status_box["height"] + 1
                assert toggle_box["x"] >= status_box["x"] + status_box["width"] - toggle_box["width"] - 28
                assert toggle_box["y"] + toggle_box["height"] <= video_box["y"] + 1

                page.evaluate(
                    """() => {
                        window.__finishTopbarProcessing = beginProcessing('Importing video', 'Working locally', '/api/import/primary');
                    }"""
                )
                page.wait_for_function("() => document.getElementById('processing-bar')?.hidden === false")

                processing_box = page.locator("#processing-bar").bounding_box()
                assert processing_box is not None
                assert processing_box["x"] == pytest.approx(status_box["x"], abs=1)
                assert processing_box["y"] == pytest.approx(status_box["y"], abs=1)
                assert processing_box["width"] == pytest.approx(status_box["width"], abs=1)
                assert processing_box["height"] == pytest.approx(status_box["height"], abs=1)

                page.evaluate("""() => {
                    forceHideProcessingBar('Ready.');
                }""")
                page.wait_for_function("() => document.getElementById('processing-bar')?.hidden === true")
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize(
    ("handle_id", "panel_selector", "storage_key", "delta_x", "delta_y"),
    [
        ("resize-rail", ".tool-rail", "splitshot.layout.railWidth", 12, 0),
        ("resize-waveform", ".waveform-panel", "splitshot.layout.waveformHeight", 0, -40),
        ("resize-sidebar", ".inspector", "splitshot.layout.inspectorWidth", -40, 0),
    ],
)
def test_layout_resize_handles_persist_layout_sizes(
    handle_id: str,
    panel_selector: str,
    storage_key: str,
    delta_x: float,
    delta_y: float,
) -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _unlock_layout(page)

                panel = page.locator(panel_selector)
                handle = page.locator(f"#{handle_id}")
                initial_panel_box = panel.bounding_box()
                initial_size = page.evaluate("(key) => Number(localStorage.getItem(key))", storage_key)
                handle_box = handle.bounding_box()
                assert initial_panel_box is not None
                assert handle_box is not None

                start_x = handle_box["x"] + handle_box["width"] / 2
                start_y = handle_box["y"] + handle_box["height"] / 2
                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(start_x + delta_x, start_y + delta_y, steps=12)
                page.mouse.up()

                page.wait_for_function(
                    "(args) => Number(localStorage.getItem(args.key)) !== args.before",
                    arg={"key": storage_key, "before": initial_size},
                )

                updated_panel_box = panel.bounding_box()
                updated_size = page.evaluate("(key) => Number(localStorage.getItem(key))", storage_key)
                assert updated_panel_box is not None
                assert updated_size > initial_size

                if panel_selector == ".waveform-panel":
                    assert updated_panel_box["height"] > initial_panel_box["height"]
                else:
                    assert updated_panel_box["width"] > initial_panel_box["width"]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_workbench_bottom_resize_is_temporary_and_restores_waveform_height(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="markers-workbench-layout-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _unlock_layout(page)

                waveform_panel = page.locator(".waveform-panel")
                initial_waveform_box = waveform_panel.bounding_box()
                initial_waveform_height = page.evaluate("state?.project?.ui_state?.waveform_height")
                assert initial_waveform_box is not None
                assert initial_waveform_height is not None

                _open_tool(page, "markers")
                _open_markers_workbench(page)

                workbench = page.locator("#markers-workbench")
                video_stage = page.locator(".video-stage")
                resize_handle = page.locator("#resize-waveform")

                workbench_before = workbench.bounding_box()
                video_before = video_stage.bounding_box()
                handle_box = resize_handle.bounding_box()
                assert workbench_before is not None
                assert video_before is not None
                assert handle_box is not None

                start_x = handle_box["x"] + (handle_box["width"] / 2)
                start_y = handle_box["y"] + (handle_box["height"] / 2)
                page.mouse.move(start_x, start_y)
                page.mouse.down()
                page.mouse.move(start_x, start_y - 80, steps=12)
                page.mouse.up()

                page.wait_for_function(
                    """(beforeHeight) => {
                        const workbench = document.getElementById('markers-workbench');
                        const rect = workbench?.getBoundingClientRect();
                        return Boolean(rect) && rect.height < beforeHeight - 20;
                    }""",
                    arg=workbench_before["height"],
                )

                workbench_after = workbench.bounding_box()
                video_after = video_stage.bounding_box()
                assert workbench_after is not None
                assert video_after is not None
                assert workbench_after["height"] < workbench_before["height"] - 20
                assert video_after["height"] > video_before["height"] + 20
                assert page.evaluate("state?.project?.ui_state?.waveform_height") == initial_waveform_height

                page.locator("#popup-edit-selected").click()
                page.wait_for_function("() => document.getElementById('markers-workbench')?.hidden === true")
                waveform_panel.wait_for(state="visible")

                restored_waveform_box = waveform_panel.bounding_box()
                assert restored_waveform_box is not None
                assert restored_waveform_box["height"] == pytest.approx(initial_waveform_box["height"], abs=4)
                assert page.evaluate("state?.project?.ui_state?.waveform_height") == initial_waveform_height
            finally:
                browser.close()
    finally:
        server.shutdown()