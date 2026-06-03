from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

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


@pytest.mark.parametrize("width", [1280, 900])
def test_loaded_stage_shell_remains_responsive_without_horizontal_overflow(
    synthetic_video_factory,
    width: int,
) -> None:
    primary_path = Path(synthetic_video_factory(name=f"responsive-stage-layout-{width}"))

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "settings")
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(150)

                layout = page.evaluate(
                    """() => {
                        const stage = document.getElementById('video-stage');
                        const inspector = document.querySelector('.inspector');
                        const rail = document.querySelector('.tool-rail');
                        const stageRect = stage?.getBoundingClientRect();
                        const inspectorRect = inspector?.getBoundingClientRect();
                        return {
                            activeSurface: typeof activeSurface === 'string' ? activeSurface : '',
                            activeTool: typeof activeTool === 'string' ? activeTool : '',
                            mediaLoaded: Boolean(state?.media?.primary_available),
                            waveformCards: document.querySelectorAll('.waveform-shot-card').length,
                            horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
                            railDisplay: rail ? getComputedStyle(rail).display : 'none',
                            stageWidth: Math.round(stageRect?.width || 0),
                            stageHeight: Math.round(stageRect?.height || 0),
                            inspectorWidth: Math.round(inspectorRect?.width || 0),
                            inspectorHidden: inspector ? Boolean(inspector.hidden) : true,
                        };
                    }"""
                )

                assert layout["activeSurface"] == "single"
                assert layout["activeTool"] == "settings"
                assert layout["mediaLoaded"] is True
                assert layout["waveformCards"] > 0
                assert layout["horizontalOverflow"] is False
                assert layout["railDisplay"] != "none"
                assert layout["stageWidth"] >= 320
                assert layout["stageHeight"] > 0
                assert layout["inspectorWidth"] >= 320
                assert layout["inspectorHidden"] is False
            finally:
                browser.close()
    finally:
        server.shutdown()


def _drag_resize_handle(
    page,
    handle_id: str,
    cx: float,
    cy: float,
    delta_x: float,
    delta_y: float,
    css_var: str,
    before_css: str,
) -> None:
    payload = {"handleId": handle_id, "cx": cx, "cy": cy, "dx": delta_x, "dy": delta_y}
    for _ in range(3):
        page.evaluate(
            """
            (args) => {
                const handle = document.getElementById(args.handleId);
                if (!handle) return;
                handle.dispatchEvent(new PointerEvent('pointerdown', {
                    bubbles: true, cancelable: true, pointerId: 1,
                    clientX: args.cx, clientY: args.cy,
                }));
            }
            """,
            payload,
        )
        page.evaluate(
            """
            (args) => document.dispatchEvent(new PointerEvent('pointermove', {
                bubbles: true, cancelable: true, pointerId: 1,
                clientX: args.cx + args.dx, clientY: args.cy + args.dy,
            }))
            """,
            payload,
        )
        page.evaluate(
            """() => document.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, pointerId: 1 }))"""
        )
        try:
            page.wait_for_function(
                """(args) => {
                    const value = getComputedStyle(document.documentElement).getPropertyValue(args.variable).trim();
                    return value !== args.before;
                }""",
                arg={"variable": css_var, "before": before_css},
                timeout=1500,
            )
            return
        except PlaywrightTimeoutError:
            page.wait_for_timeout(150)
    page.wait_for_function(
        """(args) => {
            const value = getComputedStyle(document.documentElement).getPropertyValue(args.variable).trim();
            return value !== args.before;
        }""",
        arg={"variable": css_var, "before": before_css},
        timeout=5000,
    )


def test_browser_rail_footer_buttons_stay_square_and_stacked() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                stage_rail = page.locator('#view-stage .tool-rail[aria-label="SplitShot tools"]')
                settings_button = page.locator("#settings-rail-button")
                toggle_button = page.locator("#toggle-rail")
                settings_pane = page.locator('[data-tool-pane="settings"]')

                stage_rail.wait_for(state="visible")
                settings_button.wait_for(state="visible")
                toggle_button.wait_for(state="visible")

                rail_box = stage_rail.bounding_box()
                settings_box = settings_button.bounding_box()
                toggle_box = toggle_button.bounding_box()
                assert rail_box is not None
                assert settings_box is not None
                assert toggle_box is not None
                assert settings_box["width"] > settings_box["height"]
                assert toggle_box["width"] > toggle_box["height"]
                assert settings_box["width"] == pytest.approx(toggle_box["width"])
                assert settings_box["height"] == pytest.approx(toggle_box["height"])
                assert settings_box["width"] < rail_box["width"]
                assert settings_box["width"] >= rail_box["width"] * 0.8
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

                collapsed_rail_box = stage_rail.bounding_box()
                collapsed_settings_box = settings_button.bounding_box()
                collapsed_toggle_box = toggle_button.bounding_box()
                assert collapsed_rail_box is not None
                assert collapsed_settings_box is not None
                assert collapsed_toggle_box is not None
                assert collapsed_settings_box["width"] < settings_box["width"]
                assert collapsed_settings_box["height"] == pytest.approx(settings_box["height"])
                assert collapsed_toggle_box["width"] == pytest.approx(
                    collapsed_settings_box["width"]
                )
                assert collapsed_toggle_box["height"] == pytest.approx(toggle_box["height"])
                assert collapsed_settings_box["width"] < collapsed_rail_box["width"]
                assert collapsed_settings_box["width"] >= collapsed_settings_box["height"]

                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "document.querySelector('.cockpit-shell')?.classList.contains('rail-collapsed') === true"
                )
                page.locator('[data-tool-pane="settings"]').wait_for(state="visible")
                assert page.locator('.tool-item.active[data-tool="settings"]').count() == 1
                assert page.locator("#toggle-rail").text_content() == "▶"
                assert (
                    page.locator("#toggle-rail").get_attribute("aria-label") == "Expand left rail"
                )
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

                page.locator("#expand-scoring").click()
                workbench = page.locator("#scoring-workbench")
                workbench.wait_for(state="visible")
                assert (
                    page.evaluate("document.querySelector('#scoring-workbench')?.hidden") is False
                )

                page.locator("#collapse-scoring").click()
                page.wait_for_function(
                    "document.querySelector('#scoring-workbench')?.hidden === true"
                )
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
                assert toggle_button.get_attribute("aria-label") == "Unlock video layout"

                toggle_button.click()
                page.wait_for_function("localStorage.getItem('splitshot.layoutLocked') === 'false'")
                assert toggle_button.text_content() == "🔓"
                assert toggle_button.get_attribute("aria-label") == "Lock video layout"
                assert (
                    shell.evaluate("element => element.classList.contains('layout-unlocked')")
                    is True
                )

                toggle_button.click()
                page.wait_for_function("localStorage.getItem('splitshot.layoutLocked') === 'true'")
                assert toggle_button.text_content() == "🔒"
                assert toggle_button.get_attribute("aria-label") == "Unlock video layout"
                assert (
                    shell.evaluate("element => element.classList.contains('layout-locked')") is True
                )
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
                status_bar = page.locator("#view-stage .status-bar")
                toggle_button = page.locator("#toggle-layout-lock-video")
                video_stage = page.locator("#view-stage .video-stage")

                status_box = status_bar.bounding_box()
                toggle_box = toggle_button.bounding_box()
                video_box = video_stage.bounding_box()
                assert status_box is not None
                assert toggle_box is not None
                assert video_box is not None

                assert status_box["x"] <= toggle_box["x"]
                assert (
                    toggle_box["x"] + toggle_box["width"]
                    <= status_box["x"] + status_box["width"] + 1
                )
                assert status_box["y"] <= toggle_box["y"]
                assert (
                    toggle_box["y"] + toggle_box["height"]
                    <= status_box["y"] + status_box["height"] + 1
                )
                assert (
                    toggle_box["x"]
                    >= status_box["x"] + status_box["width"] - toggle_box["width"] - 28
                )
                assert toggle_box["y"] + toggle_box["height"] <= video_box["y"] + 1

                page.evaluate(
                    """() => {
                        window.__finishTopbarProcessing = beginProcessing('Importing video', 'Working locally', '/api/import/primary');
                    }"""
                )
                page.wait_for_function(
                    "() => document.getElementById('processing-bar')?.hidden === false"
                )

                app_shell_box = page.locator("#app-shell").bounding_box()
                processing_box = page.locator("#processing-bar").bounding_box()
                assert app_shell_box is not None
                assert processing_box is not None
                assert processing_box["x"] == pytest.approx(app_shell_box["x"], abs=2)
                assert processing_box["y"] == pytest.approx(app_shell_box["y"], abs=2)
                assert processing_box["width"] == pytest.approx(app_shell_box["width"], abs=5)
                assert processing_box["height"] == 38

                page.evaluate("""() => {
                    forceHideProcessingBar('Ready.');
                }""")
                page.wait_for_function(
                    "() => document.getElementById('processing-bar')?.hidden === true"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize(
    ("handle_id", "panel_selector", "storage_key", "css_var", "delta_x", "delta_y"),
    [
        (
            "resize-rail",
            "#view-stage .tool-rail",
            "splitshot.layout.railWidth",
            "--rail-width",
            12,
            0,
        ),
        (
            "resize-waveform",
            ".waveform-panel",
            "splitshot.layout.waveformHeight",
            "--waveform-height",
            0,
            -120,
        ),
        (
            "resize-sidebar",
            "#view-stage .inspector",
            "splitshot.layout.inspectorWidth",
            "--inspector-width",
            120,
            0,
        ),
    ],
)
def test_layout_resize_handles_persist_layout_sizes(
    handle_id: str,
    panel_selector: str,
    storage_key: str,
    css_var: str,
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
                initial_size = page.evaluate(
                    "(key) => Number(localStorage.getItem(key))", storage_key
                )
                initial_css = page.evaluate(
                    "(variable) => getComputedStyle(document.documentElement).getPropertyValue(variable).trim()",
                    css_var,
                )
                handle_box = handle.bounding_box()
                assert initial_panel_box is not None
                assert handle_box is not None

                cx = handle_box["x"] + handle_box["width"] / 2
                cy = handle_box["y"] + handle_box["height"] / 2
                _drag_resize_handle(
                    page,
                    handle_id,
                    cx,
                    cy,
                    delta_x,
                    delta_y,
                    css_var,
                    initial_css,
                )

                updated_panel_box = panel.bounding_box()
                updated_size = page.evaluate(
                    "(key) => Number(localStorage.getItem(key))", storage_key
                )
                updated_css = page.evaluate(
                    "(variable) => getComputedStyle(document.documentElement).getPropertyValue(variable).trim()",
                    css_var,
                )
                assert updated_panel_box is not None
                assert updated_size != initial_size
                assert updated_css != initial_css
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_marker_workbench_bottom_resize_is_temporary_and_restores_waveform_height(
    synthetic_video_factory,
) -> None:
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
                        return Boolean(rect) && rect.height > beforeHeight + 20;
                    }""",
                    arg=workbench_before["height"],
                )

                workbench_after = workbench.bounding_box()
                video_after = video_stage.bounding_box()
                assert workbench_after is not None
                assert video_after is not None
                assert workbench_after["height"] > workbench_before["height"] + 20
                assert video_after["height"] < video_before["height"] - 20
                assert (
                    page.evaluate("state?.project?.ui_state?.waveform_height")
                    == initial_waveform_height
                )

                page.locator("#popup-edit-selected").click()
                page.wait_for_function(
                    "() => document.getElementById('markers-workbench')?.hidden === true"
                )
                waveform_panel.wait_for(state="visible")

                restored_waveform_box = waveform_panel.bounding_box()
                assert restored_waveform_box is not None
                assert restored_waveform_box["height"] == pytest.approx(
                    initial_waveform_box["height"], abs=4
                )
                assert (
                    page.evaluate("state?.project?.ui_state?.waveform_height")
                    == initial_waveform_height
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_stage_surface_shows_tool_rail_after_project_load(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="rail-surface-test"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                # After loading a project, the app should be in stage view with visible tools
                project_button = page.locator('button[data-tool="project"]')
                project_button.wait_for(state="visible", timeout=5000)
                assert project_button.is_visible()
                # Also verify the rail itself is visible
                rail = page.locator('#view-stage .tool-rail[aria-label="SplitShot tools"]')
                assert rail.is_visible()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_workspace_rail_toggles_follow_shared_shell_markers() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                page.evaluate("""() => setActiveSurface('multi')""")
                page.wait_for_function("() => activeSurface === 'multi'")
                page.locator("#match-toggle-rail").click(force=True)
                page.wait_for_function(
                    """() => document.querySelector('[data-shell-family="stage-workspace"][data-shell-view="match"]')?.classList.contains('rail-collapsed') === true"""
                )
                assert (
                    page.evaluate("localStorage.getItem('splitshot.match.railCollapsed')") == "true"
                )

                page.evaluate("""() => setActiveSurface('library')""")
                page.wait_for_function("() => activeSurface === 'library'")
                page.locator("#library-toggle-rail").click(force=True)
                page.wait_for_function(
                    """() => document.querySelector('[data-shell-family="stage-workspace"][data-shell-view="library"]')?.classList.contains('rail-collapsed') === true"""
                )
                assert (
                    page.evaluate("localStorage.getItem('splitshot.library.railCollapsed')")
                    == "true"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
