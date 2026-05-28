from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


SETTINGS_SECTION_IDS = [
    "global-template",
    "layout",
    "scoring",
    "pip",
    "overlay",
    "markers",
    "export",
    "shotml",
]

SETTINGS_WAIT_TIMEOUT_MS = 20_000


def _settings_page_snapshot(page) -> dict[str, object]:
    return page.evaluate(
        """() => {
            const controlValue = (id) => document.getElementById(id)?.value ?? null;
            const controlChecked = (id) => document.getElementById(id)?.checked ?? null;
            const sections = {};
            document.querySelectorAll('[data-settings-section]').forEach((section) => {
                const sectionId = section.dataset.settingsSection || '';
                sections[sectionId] = {
                    collapsed: section.classList.contains('collapsed'),
                    ariaExpanded: section.querySelector('button[data-section-toggle]')?.getAttribute('aria-expanded') ?? null,
                };
            });
            return {
                activeTool,
                pendingSettingsDefaultsPromise: window.pendingSettingsDefaultsPromise === null ? null : 'pending',
                lastAppliedSettingsDefaultsPayload: window.lastAppliedSettingsDefaultsPayload ?? null,
                controls: {
                    defaultMatchType: controlValue('settings-default-match-type'),
                    mergeLayout: controlValue('settings-merge-layout'),
                    pipSize: controlValue('settings-pip-size'),
                    overlayPosition: controlValue('settings-overlay-position'),
                    badgeSize: controlValue('settings-badge-size'),
                    exportQuality: controlValue('settings-export-quality'),
                    exportVideoCodec: controlValue('settings-export-video-codec'),
                    exportTwoPass: controlChecked('settings-export-two-pass'),
                    shotmlThreshold: controlValue('settings-shotml-threshold'),
                },
                settings: {
                    defaultMatchType: state?.settings?.default_match_type ?? null,
                    mergeLayout: state?.settings?.merge_layout ?? null,
                    pipSize: state?.settings?.pip_size ?? null,
                    overlayPosition: state?.settings?.overlay_position ?? null,
                    badgeSize: state?.settings?.badge_size ?? null,
                    exportQuality: state?.settings?.export_quality ?? null,
                    exportVideoCodec: state?.settings?.export_video_codec ?? null,
                    exportTwoPass: state?.settings?.export_two_pass ?? null,
                    markerTemplate: state?.settings?.marker_template ?? null,
                    shotmlThreshold: state?.settings?.shotml_defaults?.detection_threshold ?? null,
                },
                project: {
                    matchType: state?.project?.scoring?.match_type ?? null,
                    mergeLayout: state?.project?.merge?.layout ?? null,
                    exportQuality: state?.project?.export?.quality ?? null,
                    exportVideoCodec: state?.project?.export?.video_codec ?? null,
                    overlayPosition: state?.project?.overlay?.position ?? null,
                },
                sections,
            };
        }"""
    )


def _evaluate_page_predicate(page, predicate: str, arg=None):
    return page.evaluate(
        """([predicateSource, predicateArg]) => {
            const predicateFn = globalThis.eval(predicateSource);
            if (typeof predicateFn !== 'function') {
                throw new Error(`Predicate did not evaluate to a function: ${predicateSource}`);
            }
            return predicateFn(predicateArg);
        }""",
        [predicate, arg],
    )


def _wait_for_page_predicate(
    page,
    predicate: str,
    *,
    arg=None,
    description: str | None = None,
    timeout_ms: int = SETTINGS_WAIT_TIMEOUT_MS,
) -> None:
    try:
        if arg is None:
            page.wait_for_function(predicate, timeout=timeout_ms)
        else:
            page.wait_for_function(predicate, arg=arg, timeout=timeout_ms)
    except PlaywrightTimeoutError as exc:
        try:
            last_value = _evaluate_page_predicate(page, predicate, arg)
        except Exception as eval_exc:  # pragma: no cover - best-effort diagnostics
            last_value = f"<predicate evaluation failed: {eval_exc}>"
        try:
            snapshot = _settings_page_snapshot(page)
        except Exception as snapshot_exc:  # pragma: no cover - best-effort diagnostics
            snapshot = {"snapshot_error": str(snapshot_exc)}
        raise AssertionError(
            f"Timed out after {timeout_ms}ms waiting for {description or predicate}; "
            f"last_value={last_value!r}; snapshot={snapshot!r}"
        ) from exc


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _open_settings(page) -> None:
    page.locator("#settings-rail-button").click(force=True)
    _wait_for_page_predicate(page, "() => activeTool === 'settings'", description="settings tool active")
    page.locator('[data-tool-pane="settings"]').wait_for(
        state="visible", timeout=SETTINGS_WAIT_TIMEOUT_MS
    )


def _settings_section_selector(section_id: str) -> str:
    return f'[data-settings-section="{section_id}"]'


def _expand_settings_section(page, section_id: str) -> None:
    selector = _settings_section_selector(section_id)
    section = page.locator(selector)
    if section.evaluate("element => element.classList.contains('collapsed')") is False:
        return
    section.locator("button[data-section-toggle]").click()
    _wait_for_page_predicate(
        page,
        "(sectionSelector) => !document.querySelector(sectionSelector)?.classList.contains('collapsed')",
        arg=selector,
        description=f"settings section '{section_id}' expanded",
    )


def _set_settings_control(page, control_id: str, value: str | bool) -> None:
    control = page.locator(f"#{control_id}")
    control.wait_for(state="visible", timeout=SETTINGS_WAIT_TIMEOUT_MS)
    if isinstance(value, bool):
        if value:
            control.check()
        else:
            control.uncheck()
    elif control.evaluate("element => element.tagName === 'SELECT'"):
        control.select_option(str(value))
    else:
        control.evaluate(
            """(element, nextValue) => {
                element.value = String(nextValue);
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            value,
        )
    _wait_for_page_predicate(
        page,
        """([targetId, nextValue]) => {
            const element = document.getElementById(targetId);
            if (!element) {
                return false;
            }
            if (typeof nextValue === 'boolean') {
                return element.checked === nextValue;
            }
            return element.value === String(nextValue);
        }""",
        arg=[control_id, value],
        description=f"settings control '{control_id}' updated",
    )
    page.wait_for_timeout(50)


def _apply_settings_defaults_and_wait(page, predicate: str, arg=None) -> None:
    _wait_for_page_predicate(page, "() => state?.settings !== undefined", description="settings state ready")
    page.evaluate("() => applySettingsDefaults()")
    _wait_for_page_predicate(
        page,
        "() => window.pendingSettingsDefaultsPromise === null",
        description="settings defaults promise settled",
    )
    _wait_for_page_predicate(page, predicate, arg=arg, description="settings defaults predicate")


def _seed_project_state_for_settings_save_current_buttons(page) -> None:
    page.evaluate(
        """() => {
            state.project.scoring = {
                ...(state.project.scoring || {}),
                match_type: 'idpa',
            };
            state.project.merge = {
                ...(state.project.merge || {}),
                layout: 'pip',
                pip_size: '50%',
                pip_x: 0.25,
                pip_y: 0.75,
            };
            state.project.overlay = {
                ...(state.project.overlay || {}),
                position: 'left',
                badge_size: 'L',
                custom_box_background_color: '#123456',
                custom_box_text_color: '#abcdef',
                custom_box_opacity: 0.75,
                timer_badge: {
                    background_color: '#101010',
                    text_color: '#f8fafc',
                    opacity: 0.85,
                },
                shot_badge: {
                    background_color: '#1d4ed8',
                    text_color: '#eef2ff',
                    opacity: 0.8,
                },
                current_shot_badge: {
                    background_color: '#dc2626',
                    text_color: '#ffffff',
                    opacity: 0.75,
                },
                hit_factor_badge: {
                    background_color: '#047857',
                    text_color: '#ecfdf5',
                    opacity: 0.7,
                },
            };
            state.project.popup_template = {
                ...(state.project.popup_template || {}),
                enabled: false,
                content_type: 'text_image',
                text_source: 'custom',
                duration_ms: 1500,
                use_shot_split_duration: true,
                quadrant: 'middle_middle',
                width: 222,
                height: 88,
                follow_motion: true,
                motion_mode: 'guided',
                background_color: '#202020',
                text_color: '#f8fafc',
                opacity: 0.55,
            };
            state.project.export = {
                ...(state.project.export || {}),
                quality: 'low',
                preset: 'universal_vertical',
                frame_rate: '60',
                video_codec: 'hevc',
                audio_codec: 'aac',
                color_space: 'bt709_sdr',
                two_pass: true,
                ffmpeg_preset: 'fast',
            };
            state.project.analysis = {
                ...(state.project.analysis || {}),
                shotml_settings: {
                    ...(state.project.analysis?.shotml_settings || {}),
                    detection_threshold: 0.5,
                },
            };
            renderSettingsPane();
        }"""
    )


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
                    toggle.wait_for(state="visible", timeout=SETTINGS_WAIT_TIMEOUT_MS)
                    assert (
                        section.evaluate("element => element.classList.contains('collapsed')")
                        is True
                    )
                    toggle.click()
                    _wait_for_page_predicate(
                        page,
                        "(sectionSelector) => !document.querySelector(sectionSelector)?.classList.contains('collapsed')",
                        arg=selector,
                        description=f"settings section '{section_id}' expanded from route toggle test",
                    )

                page.locator('button[data-tool="project"]').click(force=True)
                _wait_for_page_predicate(page, "() => activeTool === 'project'", description="project tool active")

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
                _wait_for_page_predicate(
                    page,
                    "(sectionSelector) => document.querySelector(sectionSelector)?.classList.contains('collapsed') === true",
                    arg=overlay_selector,
                    description="overlay settings section collapsed",
                )

                page.locator('button[data-tool="timing"]').click(force=True)
                _wait_for_page_predicate(page, "() => activeTool === 'timing'", description="timing tool active")

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
                _wait_for_page_predicate(page, "() => activeTool === 'merge'", description="merge tool active")
                page.locator("#merge-layout").select_option("pip")
                _wait_for_page_predicate(
                    page,
                    "() => state?.project?.merge?.layout === 'pip'",
                    description="merge layout set to pip",
                )

                page.locator('button[data-tool="export"]').click(force=True)
                _wait_for_page_predicate(page, "() => activeTool === 'export'", description="export tool active")
                page.locator("#quality").select_option("low")
                _wait_for_page_predicate(
                    page,
                    "() => state?.project?.export?.quality === 'low'",
                    description="project export quality set to low",
                )

                _open_settings(page)
                _expand_settings_section(page, "global-template")
                _expand_settings_section(page, "pip")
                _expand_settings_section(page, "overlay")
                _expand_settings_section(page, "export")

                page.locator("#settings-import-current").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.merge_layout === 'pip' && state?.settings?.export_quality === 'low'"""
                )
                assert page.locator("#settings-merge-layout").input_value() == "pip"
                assert page.locator("#settings-export-quality").input_value() == "low"

                page.locator("#settings-reset-defaults").click(force=True)
                _wait_for_page_predicate(
                    page,
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

                _set_settings_control(page, "settings-scope", "app")
                _set_settings_control(page, "settings-default-tool", "metrics")
                _set_settings_control(page, "settings-reopen-last-tool", False)
                _apply_settings_defaults_and_wait(
                    page,
                    "() => state?.settings?.default_tool === 'metrics' && state?.settings?.reopen_last_tool === false",
                )

                assert page.locator("#settings-default-tool").input_value() == "metrics"
                assert page.locator("#settings-reopen-last-tool").is_checked() is False

                page.locator("#settings-reset-defaults").click(force=True)
                _wait_for_page_predicate(
                    page,
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

                _set_settings_control(page, "settings-default-match-type", "idpa")
                _apply_settings_defaults_and_wait(
                    page, "() => state?.settings?.default_match_type === 'idpa'"
                )
                _set_settings_control(page, "settings-pip-size", "50%")
                _apply_settings_defaults_and_wait(page, "() => state?.settings?.pip_size === '50%'")
                _set_settings_control(page, "settings-export-quality", "low")
                _apply_settings_defaults_and_wait(
                    page, "() => state?.settings?.export_quality === 'low'"
                )
                _set_settings_control(page, "settings-export-two-pass", True)
                _apply_settings_defaults_and_wait(
                    page, "() => state?.settings?.export_two_pass === true"
                )

                assert page.locator("#settings-default-match-type").input_value() == "idpa"
                assert page.locator("#settings-pip-size").input_value() == "50%"
                assert page.locator("#settings-export-quality").input_value() == "low"
                assert page.locator("#settings-export-two-pass").is_checked() is True

                page.locator("#settings-reset-defaults").click()
                _wait_for_page_predicate(
                    page,
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

                _set_settings_control(page, "settings-merge-layout", "pip")
                _set_settings_control(page, "settings-pip-size", "50%")

                _set_settings_control(page, "settings-export-preset", next_export_preset)
                _set_settings_control(page, "settings-export-frame-rate", "60")
                _set_settings_control(page, "settings-export-video-codec", "hevc")
                _set_settings_control(page, "settings-export-ffmpeg-preset", "fast")
                _set_settings_control(page, "settings-export-two-pass", True)
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
                _set_settings_control(
                    page, "settings-current-shot-badge-background-color", "#dc2626"
                )
                _set_settings_control(page, "settings-current-shot-badge-text-color", "#ffffff")
                _set_settings_control(page, "settings-current-shot-badge-opacity", "0.75")
                _set_settings_control(page, "settings-hit-factor-badge-background-color", "#047857")
                _set_settings_control(page, "settings-hit-factor-badge-text-color", "#ecfdf5")
                _set_settings_control(page, "settings-hit-factor-badge-opacity", "0.7")
                _set_settings_control(page, "settings-merge-layout", "pip")
                _set_settings_control(page, "settings-pip-size", "50%")
                _set_settings_control(page, "settings-export-preset", next_export_preset)
                _set_settings_control(page, "settings-export-frame-rate", "60")
                _set_settings_control(page, "settings-export-video-codec", "hevc")
                _set_settings_control(page, "settings-export-ffmpeg-preset", "fast")
                _set_settings_control(page, "settings-export-two-pass", True)
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


def test_settings_layout_section_captures_current_layout_and_resets() -> None:
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
                        window.layoutLocked = false;
                        window.layoutSizes = { railWidth: 96, inspectorWidth: 620, waveformHeight: 240 };
                        syncLocalProjectUiState();
                        renderSettingsPane();
                    }"""
                )

                page.locator("#settings-use-current-layout").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.layout_locked === false
                      && state?.settings?.layout_rail_width === 96
                      && state?.settings?.layout_inspector_width === 620
                      && state?.settings?.layout_waveform_height === 240"""
                )

                page.locator("#settings-release-layout").click()
                _wait_for_page_predicate(
                    page,
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

                _set_settings_control(page, "settings-pip-size", "50%")
                _apply_settings_defaults_and_wait(page, "() => state?.settings?.pip_size === '50%'")
                _set_settings_control(page, "settings-export-quality", "low")
                _apply_settings_defaults_and_wait(
                    page, "() => state?.settings?.export_quality === 'low'"
                )

                page.locator("#settings-reset-section-export").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.pip_size === '50%'
                      && state?.settings?.export_quality === 'high'"""
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_settings_save_current_and_section_reset_buttons_apply_owned_sections() -> None:
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _open_settings(page)
                for section_id in ["scoring", "pip", "overlay", "markers", "export", "shotml"]:
                    _expand_settings_section(page, section_id)

                _seed_project_state_for_settings_save_current_buttons(page)

                page.locator("#settings-save-current-scoring").click()
                _wait_for_page_predicate(page, "() => state?.settings?.default_match_type === 'idpa'")

                _seed_project_state_for_settings_save_current_buttons(page)
                page.locator("#settings-save-current-pip").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.merge_layout === 'pip'
                        && state?.settings?.pip_size === '50%'"""
                )

                _seed_project_state_for_settings_save_current_buttons(page)
                page.locator("#settings-save-current-overlay").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.overlay_position === 'left'
                      && state?.settings?.badge_size === 'L'
                      && state?.settings?.overlay_custom_box_background_color === '#123456'"""
                )

                _seed_project_state_for_settings_save_current_buttons(page)
                page.locator("#settings-save-current-markers").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.marker_template?.content_type === 'text_image'
                      && state?.settings?.marker_template?.use_shot_split_duration === true
                      && state?.settings?.marker_template?.follow_motion === true"""
                )

                _seed_project_state_for_settings_save_current_buttons(page)
                page.locator("#settings-save-current-export").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.export_quality === 'low'
                      && state?.settings?.export_video_codec === 'hevc'
                      && state?.settings?.export_two_pass === true"""
                )

                _seed_project_state_for_settings_save_current_buttons(page)
                page.locator("#settings-save-current-shotml").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.shotml_defaults?.detection_threshold === 0.5
                        && Number(document.querySelector('#settings-shotml-threshold')?.value || 0) === 0.5"""
                )

                page.locator("#settings-reset-section-scoring").click()
                _wait_for_page_predicate(page, "() => state?.settings?.default_match_type === 'uspsa'")

                page.locator("#settings-reset-section-pip").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.merge_layout === 'side_by_side'
                        && state?.settings?.pip_size === '35%'"""
                )

                page.locator("#settings-reset-section-overlay").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.overlay_position === 'bottom'
                      && state?.settings?.badge_size === 'M'
                      && state?.settings?.overlay_custom_box_background_color === '#000000'"""
                )

                page.locator("#settings-reset-section-markers").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.marker_template?.enabled === true
                      && state?.settings?.marker_template?.content_type === 'text'
                      && state?.settings?.marker_template?.follow_motion === false"""
                )

                page.locator("#settings-reset-section-export").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.export_quality === 'high'
                      && state?.settings?.export_video_codec === 'h264'
                      && state?.settings?.export_two_pass === false"""
                )

                page.locator("#settings-reset-section-shotml").click()
                _wait_for_page_predicate(
                    page,
                    """() => state?.settings?.shotml_defaults?.detection_threshold === 0.35
                        && Number(document.querySelector('#settings-shotml-threshold')?.value || 0) === 0.35"""
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
