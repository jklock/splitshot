from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _open_settings(page) -> None:
    page.locator('#settings-rail-button').click(force=True)
    page.wait_for_function("() => activeTool === 'settings'")
    page.locator('[data-tool-pane="settings"]').wait_for(state='visible')


def _expand_settings_section(page, section_id: str) -> None:
    selector = f'[data-settings-section="{section_id}"]'
    section = page.locator(selector)
    if section.evaluate("element => element.classList.contains('collapsed')") is False:
        return
    section.locator('button[data-section-toggle]').click()
    page.wait_for_function(
        '(target) => !document.querySelector(target)?.classList.contains("collapsed")',
        arg=selector,
    )


def _set_control(page, control_id: str, value: str | bool) -> None:
    locator = page.locator(f'#{control_id}')
    locator.wait_for(state='visible')
    tag_name = locator.evaluate("element => element.tagName.toLowerCase()")
    if isinstance(value, bool):
        if value:
            locator.check()
        else:
            locator.uncheck()
        return
    if tag_name == 'select':
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
            [f'#{control_id}', value],
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


def _apply_settings_defaults_and_wait(page, predicate: str) -> None:
    page.wait_for_function("() => state?.settings !== undefined")
    page.evaluate("() => applySettingsDefaults()")
    page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
    page.wait_for_function(predicate)


def test_settings_defaults_seed_fresh_project_overlay_marker_export_pip_and_shotml_state(tmp_path: Path) -> None:
    project_path = tmp_path / f'defaults-seeded-project-{uuid.uuid4().hex[:8]}'
    shutil.rmtree(project_path, ignore_errors=True)
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                assert page.evaluate('() => applySettingsDefaults.toString().includes("const finalPromise")')
                for section_id in ['pip', 'overlay', 'markers', 'export', 'shotml']:
                    _expand_settings_section(page, section_id)

                default_controls = [
                    ('settings-pip-size', '50%'),
                    ('settings-merge-pip-x', '0.25'),
                    ('settings-merge-pip-y', '0.75'),
                    ('settings-overlay-position', 'left'),
                    ('settings-badge-size', 'L'),
                    ('settings-overlay-custom-background-color', '#123456'),
                    ('settings-overlay-custom-text-color', '#abcdef'),
                    ('settings-overlay-custom-opacity', '0.75'),
                    ('settings-timer-badge-background-color', '#111111'),
                    ('settings-timer-badge-text-color', '#fef3c7'),
                    ('settings-timer-badge-opacity', '0.61'),
                    ('settings-shot-badge-background-color', '#1d4ed8'),
                    ('settings-shot-badge-text-color', '#dbeafe'),
                    ('settings-shot-badge-opacity', '0.73'),
                    ('settings-current-shot-badge-background-color', '#7e22ce'),
                    ('settings-current-shot-badge-text-color', '#f3e8ff'),
                    ('settings-current-shot-badge-opacity', '0.82'),
                    ('settings-hit-factor-badge-background-color', '#166534'),
                    ('settings-hit-factor-badge-text-color', '#dcfce7'),
                    ('settings-hit-factor-badge-opacity', '0.67'),
                    ('settings-marker-content-type', 'text_image'),
                    ('settings-marker-text-source', 'custom'),
                    ('settings-marker-duration', '1.500'),
                    ('settings-marker-quadrant', 'bottom_right'),
                    ('settings-marker-width', '222'),
                    ('settings-marker-height', '88'),
                    ('settings-marker-follow-motion', True),
                    ('settings-marker-background-color', '#202020'),
                    ('settings-marker-text-color', '#f8fafc'),
                    ('settings-marker-opacity', '0.55'),
                    ('settings-marker-enabled', False),
                    ('settings-export-quality', 'low'),
                    ('settings-export-preset', 'universal_vertical'),
                    ('settings-export-frame-rate', '60'),
                    ('settings-export-video-codec', 'hevc'),
                    ('settings-export-audio-codec', 'aac'),
                    ('settings-export-color-space', 'bt709_sdr'),
                    ('settings-export-ffmpeg-preset', 'fast'),
                    ('settings-export-two-pass', True),
                    ('settings-shotml-threshold', '0.5'),
                    ('settings-merge-layout', 'pip'),
                ]
                for control_id, value in default_controls:
                    _set_control(page, control_id, value)
                assert page.evaluate("() => readSettingsDefaultsPayload({}).settings.merge_layout === 'pip'")
                page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
                page.evaluate("() => applySettingsDefaults()")
                page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
                page.wait_for_function("() => state?.settings?.merge_layout === 'pip'")
                print('page scope', page.evaluate('() => (document.getElementById("settings-scope") || {}).value'))
                print('payload scope', page.evaluate('() => readSettingsDefaultsPayload({}).scope'))
                print('server folder_settings is None', server.controller.folder_settings is None)
                if server.controller.folder_settings is not None:
                    print('server folder_settings merge_layout', server.controller.folder_settings.merge_layout)
                print('server settings before create', server.controller.settings.merge_layout)
                print('server effective before create', server.controller.effective_settings().merge_layout)
                print('createNewProject patched', page.evaluate("() => createNewProject.toString().includes('await flushPendingProjectDrafts()')"))
                print('createNewProject function', page.evaluate("() => createNewProject.toString().slice(0, 300)"))
                print('settings payload before create', page.evaluate("() => JSON.stringify(readSettingsDefaultsPayload({}))"))

                _set_project_path(page, project_path)
                create_result = page.evaluate('(path) => createNewProject(path)', str(project_path))
                assert create_result
                print('server settings merge_layout', server.controller.settings.merge_layout)
                print('server effective merge_layout', server.controller.effective_settings().merge_layout)
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(project_path))
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
                assert snapshot['merge']['layout'] == 'pip'
                assert snapshot['export']['ffmpeg_preset'] == 'fast'
                assert snapshot['export']['two_pass'] is True
                assert snapshot['shotmlThreshold'] == 0.5
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_landing_pane_and_reopen_last_tool_apply_after_reload(tmp_path: Path) -> None:
    first_project = tmp_path / f'landing-pane-project-{uuid.uuid4().hex[:8]}'
    second_project = tmp_path / f'landing-pane-project-no-reopen-{uuid.uuid4().hex[:8]}'
    shutil.rmtree(first_project, ignore_errors=True)
    shutil.rmtree(second_project, ignore_errors=True)
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, 'global-template')

                _set_control(page, 'settings-scope', 'app')
                _set_control(page, 'settings-default-tool', 'metrics')
                _set_control(page, 'settings-reopen-last-tool', True)
                _apply_settings_defaults_and_wait(
                    page,
                    "() => document.getElementById('settings-default-tool')?.value === 'metrics' && document.getElementById('settings-reopen-last-tool')?.checked === true",
                )
                _set_project_path(page, first_project)
                page.evaluate('(path) => createNewProject(path)', str(first_project))
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(first_project))
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(first_project))
                page.wait_for_function("() => activeTool === 'metrics'")

                _open_settings(page)
                _expand_settings_section(page, 'global-template')
                _set_control(page, 'settings-default-tool', 'export')
                _set_control(page, 'settings-reopen-last-tool', False)
                page.wait_for_function("() => state?.settings !== undefined")
                page.evaluate("() => applySettingsDefaults()")
                page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
                _set_project_path(page, second_project)
                page.evaluate('(path) => createNewProject(path)', str(second_project))
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(second_project))
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(second_project))
                page.wait_for_function("() => activeTool === 'project'")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_scope_separates_app_and_folder_defaults_for_new_projects(tmp_path: Path) -> None:
    folder_scoped_project = tmp_path / f'folder-scope-project-{uuid.uuid4().hex[:8]}'
    second_folder_project = tmp_path / f'second-folder-scope-project-{uuid.uuid4().hex[:8]}'
    shutil.rmtree(folder_scoped_project, ignore_errors=True)
    shutil.rmtree(second_folder_project, ignore_errors=True)
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                _expand_settings_section(page, 'global-template')

                _set_control(page, 'settings-scope', 'app')
                _set_control(page, 'settings-default-tool', 'metrics')
                page.wait_for_function("() => state?.settings !== undefined")
                page.evaluate("() => applySettingsDefaults()")
                page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
                page.wait_for_function(
                    "() => document.getElementById('settings-default-tool')?.value === 'metrics'",
                )
                _set_project_path(page, folder_scoped_project)
                page.evaluate('(path) => createNewProject(path)', str(folder_scoped_project))
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(folder_scoped_project))

                _open_settings(page)
                _expand_settings_section(page, 'global-template')
                _set_control(page, 'settings-scope', 'folder')
                _set_control(page, 'settings-default-tool', 'review')
                page.evaluate("() => applySettingsDefaults()")
                page.wait_for_function("() => window.pendingSettingsDefaultsPromise === null")
                page.evaluate('(path) => useProjectFolder(path)', str(folder_scoped_project))
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(folder_scoped_project))
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(folder_scoped_project))
                page.wait_for_function("() => activeTool === 'review'")

                _set_project_path(page, second_folder_project)
                page.evaluate('(path) => createNewProject(path)', str(second_folder_project))
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(second_folder_project))
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('(path) => state?.project?.path === path', arg=str(second_folder_project))
                page.wait_for_function("() => activeTool === 'metrics'")
            finally:
                browser.close()
    finally:
        server.shutdown()