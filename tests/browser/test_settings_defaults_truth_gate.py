from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _open_settings(page) -> None:
    page.locator("#settings-rail-button").click(force=True)
    page.wait_for_function("() => activeTool === 'settings'")
    page.locator('[data-tool-pane="settings"]').wait_for(state="visible")


def _expand_settings_section(page, section_id: str) -> None:
    selector = f'[data-settings-section="{section_id}"]'
    section = page.locator(selector)
    if section.evaluate("element => element.classList.contains('collapsed')") is False:
        return
    section.locator("button[data-section-toggle]").click()
    page.wait_for_function(
        '(target) => !document.querySelector(target)?.classList.contains("collapsed")',
        arg=selector,
    )


def _set_control(page, control_id: str, value: str | bool) -> None:
    locator = page.locator(f"#{control_id}")
    locator.wait_for(state="visible")
    tag_name = locator.evaluate("element => element.tagName.toLowerCase()")
    if isinstance(value, bool):
        if value:
            locator.check()
        else:
            locator.uncheck()
        return
    if tag_name == "select":
        locator.select_option(str(value))
    else:
        page.evaluate(
            """([selector, nextValue]) => {
                const element = document.querySelector(selector);
                if (!element) {
                    throw new Error(`Control not found: ${selector}`);
                }
                element.value = String(nextValue);
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            [f"#{control_id}", value],
        )


def _set_project_path(page, path: Path) -> None:
    page.evaluate(
        """(projectPath) => {
            const input = document.getElementById('project-path');
            input.value = projectPath;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        str(path),
    )


def _set_global_template_defaults(
    page,
    *,
    scope: str | None = None,
    default_tool: str | None = None,
    reopen_last_tool: bool | None = None,
) -> None:
    page.evaluate(
        """(values) => {
            const scopeControl = document.getElementById('settings-scope');
            const defaultToolControl = document.getElementById('settings-default-tool');
            const reopenLastToolControl = document.getElementById('settings-reopen-last-tool');
            if (scopeControl && values.scope !== null) {
                scopeControl.value = String(values.scope);
            }
            if (defaultToolControl && values.defaultTool !== null) {
                defaultToolControl.value = String(values.defaultTool);
            }
            if (reopenLastToolControl && values.reopenLastTool !== null) {
                reopenLastToolControl.checked = Boolean(values.reopenLastTool);
            }
        }""",
        {
            "scope": scope,
            "defaultTool": default_tool,
            "reopenLastTool": reopen_last_tool,
        },
    )


def _apply_settings_defaults_and_wait(page, predicate: str) -> None:
    page.wait_for_function("() => state?.settings !== undefined")
    page.evaluate("() => flushPendingSettingsDefaults()")
    page.evaluate("() => applySettingsDefaults()")
    page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
    _wait_for_page_predicate(page, predicate)


def _settings_defaults_snapshot(page) -> dict[str, object]:
    return page.evaluate(
        """() => ({
            controlDefaultTool: document.getElementById('settings-default-tool')?.value ?? null,
            controlReopenLastTool: document.getElementById('settings-reopen-last-tool')?.checked ?? null,
            controlScope: document.getElementById('settings-scope')?.value ?? null,
            stateDefaultTool: state?.settings?.default_tool ?? null,
            stateReopenLastTool: state?.settings?.reopen_last_tool ?? null,
            stateScopeProjectPath: state?.project?.path ?? null,
            activeTool,
            pendingSettingsDefaultsPromiseNull: window.pendingSettingsDefaultsPromise === null,
        })"""
    )


def _wait_for_page_predicate(
    page, predicate: str, timeout_ms: int = 30_000, interval_ms: int = 100
) -> None:
    deadline = time.monotonic() + (timeout_ms / 1000)
    last_value = None
    while time.monotonic() < deadline:
        last_value = page.evaluate(predicate)
        if last_value:
            return
        page.wait_for_timeout(interval_ms)
    raise AssertionError(
        f"Timed out waiting for browser predicate: {predicate} "
        f"(last_value={last_value!r}, snapshot={_settings_defaults_snapshot(page)!r})"
    )


def _show_expanded_metrics(page) -> None:
    page.evaluate(
        """() => {
            setActiveTool('metrics', { persistUiState: false });
            setMetricsExpanded(true, { persistUiState: false });
        }"""
    )
    page.wait_for_function(
        """() => activeTool === 'metrics'
            && document.getElementById('cockpit-root')?.classList.contains('metrics-expanded') === true"""
    )


def _wait_for_project_landing(page) -> None:
    page.wait_for_function(
        """() => {
            const root = document.getElementById('cockpit-root');
            return activeTool === 'project'
                && document.querySelector('[data-tool-pane="project"]')?.classList.contains('active') === true
                && root?.classList.contains('waveform-expanded') === false
                && root?.classList.contains('timing-expanded') === false
                && root?.classList.contains('metrics-expanded') === false
                && root?.classList.contains('markers-expanded') === false
                && root?.classList.contains('scoring-expanded') === false;
        }"""
    )
    page.locator('[data-tool-pane="project"]').wait_for(state="visible")


def test_settings_defaults_seed_fresh_project_overlay_marker_export_pip_and_shotml_state(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / f"defaults-seeded-project-{uuid.uuid4().hex[:8]}"
    shutil.rmtree(project_path, ignore_errors=True)
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                assert page.evaluate(
                    '() => applySettingsDefaults.toString().includes("const finalPromise")'
                )
                for section_id in ["pip", "overlay", "markers", "export", "shotml"]:
                    _expand_settings_section(page, section_id)

                default_controls = [
                    ("settings-pip-size", "50%"),
                    ("settings-merge-pip-x", "0.25"),
                    ("settings-merge-pip-y", "0.75"),
                    ("settings-overlay-position", "left"),
                    ("settings-badge-size", "L"),
                    ("settings-overlay-custom-background-color", "#123456"),
                    ("settings-overlay-custom-text-color", "#abcdef"),
                    ("settings-overlay-custom-opacity", "0.75"),
                    ("settings-timer-badge-background-color", "#111111"),
                    ("settings-timer-badge-text-color", "#fef3c7"),
                    ("settings-timer-badge-opacity", "0.61"),
                    ("settings-shot-badge-background-color", "#1d4ed8"),
                    ("settings-shot-badge-text-color", "#dbeafe"),
                    ("settings-shot-badge-opacity", "0.73"),
                    ("settings-current-shot-badge-background-color", "#7e22ce"),
                    ("settings-current-shot-badge-text-color", "#f3e8ff"),
                    ("settings-current-shot-badge-opacity", "0.82"),
                    ("settings-hit-factor-badge-background-color", "#166534"),
                    ("settings-hit-factor-badge-text-color", "#dcfce7"),
                    ("settings-hit-factor-badge-opacity", "0.67"),
                    ("settings-marker-content-type", "text_image"),
                    ("settings-marker-text-source", "custom"),
                    ("settings-marker-duration", "1.500"),
                    ("settings-marker-use-shot-split-duration", True),
                    ("settings-marker-width", "222"),
                    ("settings-marker-height", "88"),
                    ("settings-marker-background-color", "#202020"),
                    ("settings-marker-text-color", "#f8fafc"),
                    ("settings-marker-opacity", "0.55"),
                    ("settings-marker-enabled", False),
                    ("settings-export-quality", "low"),
                    ("settings-export-preset", "universal_vertical"),
                    ("settings-export-frame-rate", "60"),
                    ("settings-export-video-codec", "hevc"),
                    ("settings-export-audio-codec", "aac"),
                    ("settings-export-color-space", "bt709_sdr"),
                    ("settings-export-ffmpeg-preset", "fast"),
                    ("settings-export-two-pass", True),
                    ("settings-shotml-threshold", "0.5"),
                    ("settings-merge-layout", "pip"),
                ]
                for control_id, value in default_controls:
                    _set_control(page, control_id, value)
                page.locator("#settings-marker-follow-motion").check()
                assert page.evaluate(
                    "() => readSettingsDefaultsPayload({}).settings.merge_layout === 'pip'"
                )
                page.evaluate("() => flushPendingSettingsDefaults()")
                page.evaluate("() => applySettingsDefaults()")
                page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
                page.wait_for_function("() => state?.settings?.merge_layout === 'pip'")
                print(
                    "page scope",
                    page.evaluate('() => (document.getElementById("settings-scope") || {}).value'),
                )
                print("payload scope", page.evaluate("() => readSettingsDefaultsPayload({}).scope"))
                print("server folder_settings is None", server.controller.folder_settings is None)
                if server.controller.folder_settings is not None:
                    print(
                        "server folder_settings merge_layout",
                        server.controller.folder_settings.merge_layout,
                    )
                print("server settings before create", server.controller.settings.merge_layout)
                print(
                    "server effective before create",
                    server.controller.effective_settings().merge_layout,
                )
                print(
                    "createNewProject patched",
                    page.evaluate(
                        "() => createNewProject.toString().includes('await flushPendingProjectDrafts()')"
                    ),
                )
                print(
                    "createNewProject function",
                    page.evaluate("() => createNewProject.toString().slice(0, 300)"),
                )
                print(
                    "settings payload before create",
                    page.evaluate("() => JSON.stringify(readSettingsDefaultsPayload({}))"),
                )

                _set_project_path(page, project_path)
                create_result = page.evaluate("(path) => createNewProject(path)", str(project_path))
                assert create_result
                print("server settings merge_layout", server.controller.settings.merge_layout)
                print(
                    "server effective merge_layout",
                    server.controller.effective_settings().merge_layout,
                )
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(project_path)
                )
                page.wait_for_function("() => state?.project?.merge?.layout === 'pip'")

                snapshot = page.evaluate(
                    """() => ({
                            merge: state?.project?.merge,
                            overlay: state?.project?.overlay,
                            popupTemplate: state?.project?.popup_template,
                            export: state?.project?.export,
                            shotmlThreshold: state?.project?.analysis?.shotml_settings?.detection_threshold,
                        })"""
                )
                assert snapshot["merge"]["layout"] == "pip"
                assert snapshot["export"]["ffmpeg_preset"] == "fast"
                assert snapshot["export"]["two_pass"] is True
                assert snapshot["popupTemplate"]["motion_mode"] == "guided"
                assert snapshot["popupTemplate"]["use_shot_split_duration"] is True
                assert snapshot["shotmlThreshold"] == 0.5
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_landing_pane_and_reopen_last_tool_apply_after_reload(tmp_path: Path) -> None:
    first_project = tmp_path / f"landing-pane-project-{uuid.uuid4().hex[:8]}"
    second_project = tmp_path / f"landing-pane-project-no-reopen-{uuid.uuid4().hex[:8]}"
    shutil.rmtree(first_project, ignore_errors=True)
    shutil.rmtree(second_project, ignore_errors=True)
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, "global-template")

                _set_global_template_defaults(
                    page, scope="app", default_tool="metrics", reopen_last_tool=True
                )
                _apply_settings_defaults_and_wait(
                    page,
                    "() => document.getElementById('settings-default-tool')?.value === 'metrics' && document.getElementById('settings-reopen-last-tool')?.checked === true",
                )
                _show_expanded_metrics(page)
                _set_project_path(page, first_project)
                page.evaluate("(path) => createNewProject(path)", str(first_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(first_project)
                )
                _wait_for_project_landing(page)
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(first_project)
                )
                _wait_for_page_predicate(page, "() => activeTool === 'metrics'")

                _open_settings(page)
                _expand_settings_section(page, "global-template")
                _set_global_template_defaults(page, default_tool="export", reopen_last_tool=False)
                _apply_settings_defaults_and_wait(
                    page,
                    "() => state?.settings?.default_tool === 'export' && state?.settings?.reopen_last_tool === false",
                )
                _show_expanded_metrics(page)
                _set_project_path(page, second_project)
                page.evaluate("(path) => createNewProject(path)", str(second_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(second_project)
                )
                _wait_for_project_landing(page)
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(second_project)
                )
                _wait_for_page_predicate(page, "() => activeTool === 'project'")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_selection_stays_on_project_before_reopen_last_tool_applies(tmp_path: Path) -> None:
    first_project = tmp_path / f"project-switch-one-{uuid.uuid4().hex[:8]}"
    second_project = tmp_path / f"project-switch-two-{uuid.uuid4().hex[:8]}"
    shutil.rmtree(first_project, ignore_errors=True)
    shutil.rmtree(second_project, ignore_errors=True)
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, "global-template")

                _set_global_template_defaults(
                    page, scope="app", default_tool="metrics", reopen_last_tool=True
                )
                _apply_settings_defaults_and_wait(
                    page,
                    "() => document.getElementById('settings-default-tool')?.value === 'metrics' && document.getElementById('settings-reopen-last-tool')?.checked === true",
                )

                _show_expanded_metrics(page)
                _set_project_path(page, first_project)
                page.evaluate("(path) => createNewProject(path)", str(first_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(first_project)
                )
                _wait_for_project_landing(page)

                _show_expanded_metrics(page)
                _set_project_path(page, second_project)
                page.evaluate("(path) => createNewProject(path)", str(second_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(second_project)
                )
                _wait_for_project_landing(page)

                _show_expanded_metrics(page)
                page.evaluate("(path) => useProjectFolder(path)", str(first_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(first_project)
                )
                _wait_for_project_landing(page)

                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(first_project)
                )
                _wait_for_page_predicate(page, "() => activeTool === 'metrics'")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_are_application_only_for_new_projects(tmp_path: Path) -> None:
    first_project = tmp_path / f"application-defaults-project-{uuid.uuid4().hex[:8]}"
    second_project = tmp_path / f"second-application-defaults-project-{uuid.uuid4().hex[:8]}"
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, "global-template")

                _set_global_template_defaults(page, default_tool="metrics", reopen_last_tool=True)
                page.evaluate("() => flushPendingSettingsDefaults()")
                page.evaluate("() => applySettingsDefaults()")
                page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
                _wait_for_page_predicate(
                    page,
                    "() => document.getElementById('settings-default-tool')?.value === 'metrics'",
                )
                assert page.locator("#settings-scope").count() == 0
                _set_project_path(page, first_project)
                page.evaluate("(path) => createNewProject(path)", str(first_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(first_project)
                )
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(first_project)
                )
                _wait_for_page_predicate(page, "() => activeTool === 'metrics'")

                _set_project_path(page, second_project)
                page.evaluate("(path) => createNewProject(path)", str(second_project))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(second_project)
                )
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(second_project)
                )
                _wait_for_page_predicate(page, "() => activeTool === 'metrics'")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_state_exposes_only_application_layer(tmp_path: Path) -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, "global-template")

                _set_global_template_defaults(page, default_tool="metrics", reopen_last_tool=True)
                _apply_settings_defaults_and_wait(
                    page,
                    "() => state?.settings_layers?.app?.default_tool === 'metrics'",
                )

                assert page.locator("#settings-scope").count() == 0
                assert page.evaluate("() => state?.settings_layers?.folder") == {}
                assert page.evaluate("() => state?.settings_layers?.app?.default_tool") == "metrics"
            finally:
                browser.close()
    finally:
        server.shutdown()
