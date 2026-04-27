from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


TOOL_IDS = ["project", "merge", "scoring", "timing", "markers", "overlay", "review", "export", "metrics", "shotml", "settings"]


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _load_primary_video(page, primary_path: Path) -> None:
    page.locator("#primary-file-input").set_input_files(str(primary_path))
    page.locator(".waveform-shot-card").first.wait_for(state="attached")


def _open_tool(page, tool_id: str) -> None:
    page.locator(f'button[data-tool="{tool_id}"]').click(force=True)
    page.wait_for_function("(tool) => activeTool === tool", arg=tool_id)


def _set_input_value(locator, value: str) -> None:
    locator.evaluate(
        """(element, nextValue) => {
            element.value = String(nextValue);
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        value,
    )


def _alternate_select_value(locator) -> str:
    return str(
        locator.evaluate(
            """(select) => [...select.options].find((option) => option.value && option.value !== select.value)?.value || select.value"""
        )
    )


def _set_color_picker_value(page, swatch_locator, hex_value: str) -> None:
    swatch_locator.click(force=True)
    page.wait_for_function("() => !document.getElementById('color-picker-modal')?.hidden")
    page.locator("#color-picker-hex").evaluate(
        """(input, nextValue) => {
            input.value = nextValue;
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }""",
        hex_value,
    )
    page.locator("#close-color-picker").click()
    page.wait_for_function("() => document.getElementById('color-picker-modal')?.hidden === true")


def _select_first_waveform_shot(page) -> str:
    shot_id = page.evaluate("() => state?.timing_segments?.[0]?.shot_id || null")
    assert shot_id is not None
    waveform_card = page.locator(".waveform-shot-card").first
    if waveform_card.count() > 0:
        waveform_card.evaluate(
            "(card) => card.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }))"
        )
        page.wait_for_function("(expectedShotId) => selectedShotId === expectedShotId", arg=shot_id)
        selected_shot_id = page.evaluate("selectedShotId")
        assert selected_shot_id is not None
        return str(selected_shot_id)

    locator = page.locator("#timing-table .timeline-segment-cell").first
    locator.wait_for(state="visible", timeout=30000)
    locator.click()
    page.wait_for_function("(expectedShotId) => selectedShotId === expectedShotId", arg=shot_id)
    selected_shot_id = page.evaluate("selectedShotId")
    assert selected_shot_id is not None
    return str(selected_shot_id)


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


def _exercise_shell_routing(page) -> None:
    for tool_id in TOOL_IDS:
        _open_tool(page, tool_id)
        page.locator(f'[data-tool-pane="{tool_id}"]').wait_for(state="visible")
        assert page.evaluate("activeTool") == tool_id


def _exercise_waveform_and_timing(page) -> None:
    page.locator("#expand-waveform").click()
    page.wait_for_timeout(150)
    page.locator("#zoom-waveform-in").click()
    page.wait_for_timeout(150)
    page.locator("#reset-waveform-view").click()
    page.wait_for_function("() => waveformZoomX === 1 && waveformOffsetMs === 0")

    _open_tool(page, "timing")
    page.locator("#expand-timing").click()
    page.wait_for_timeout(150)

    page.locator("#timing-event-kind").select_option("custom_label")
    page.locator("#timing-event-label").fill("Master timing note")
    timing_positions = page.locator("#timing-event-position").evaluate(
        "select => [...select.options].map((option) => option.value).filter(Boolean)"
    )
    assert timing_positions
    page.locator("#timing-event-position").select_option(timing_positions[0])
    baseline_event_count = int(page.evaluate("() => (state?.project?.analysis?.events || []).length"))
    page.locator("#add-timing-event").click()
    page.wait_for_function(
        "(expectedCount) => (state?.project?.analysis?.events || []).length === expectedCount",
        arg=baseline_event_count + 1,
    )
    page.locator("#timing-workbench-table").get_by_text("Master timing note").first.wait_for(state="visible")

def _exercise_markers_review_overlay(page) -> None:
    _open_tool(page, "timing")
    _select_first_waveform_shot(page)

    _open_tool(page, "markers")
    page.locator("#popup-import-shots").click()
    page.wait_for_function("() => (state?.project?.popups || []).length > 0")
    page.locator("#popup-play-window").click()
    page.locator("#popup-loop-window").click()

    page.locator("#popup-open-shot-editor").click()
    page.wait_for_function("() => document.getElementById('popup-shot-editor')?.hidden === false")
    page.locator("#popup-shot-editor-next").click()
    page.locator("#popup-shot-editor-prev").click()
    page.locator("#popup-shot-editor-duplicate").click()
    page.wait_for_function("() => (state?.project?.popups || []).length > 1")
    page.locator("#popup-shot-editor-delete").click()
    page.wait_for_function("() => document.getElementById('popup-shot-editor')?.hidden === false")
    page.locator("#popup-shot-editor-done").click()
    page.wait_for_function("() => document.getElementById('popup-shot-editor')?.hidden === true")

    page.locator("#popup-toggle-authoring").click()
    page.wait_for_function("() => document.getElementById('popup-authoring-panel')?.hidden === true")

    page.locator("#popup-next-compact").click()
    page.wait_for_function("() => selectedPopupBubbleId !== null")
    page.locator("#popup-prev-compact").click()
    page.wait_for_function("() => selectedPopupBubbleId !== null")

    _open_tool(page, "review")
    page.locator("#show-overlay").check()
    page.locator("#review-add-text-box").click()
    page.wait_for_function("() => (state?.project?.overlay?.text_boxes || []).length > 0")

    review_card = page.locator("#review-text-box-list .text-box-card").last
    review_card.wait_for(state="attached")
    review_card.locator('[data-text-box-action="toggle"]').click()
    review_card.locator('textarea[data-text-box-field="text"]').wait_for(state="visible")
    review_card.locator('textarea[data-text-box-field="text"]').fill("Master review note")
    page.wait_for_function(
        "() => (state?.project?.overlay?.text_boxes || []).some((box) => box.text === 'Master review note')"
    )
    _set_color_picker_value(page, review_card.locator('button[data-text-box-field="background_color"]'), "#ff0000")
    review_box_id = page.evaluate(
        """() => {
          const boxes = state?.project?.overlay?.text_boxes || [];
          return boxes.length ? boxes[boxes.length - 1]?.id ?? null : null;
        }"""
    )
    assert review_box_id is not None

    _open_tool(page, "overlay")
    page.locator("#show-overlay").check()
    page.locator("#badge-size").select_option(_alternate_select_value(page.locator("#badge-size")))
    page.locator("#overlay-style").select_option("bubble")
    page.locator("#overlay-font-family").select_option(_alternate_select_value(page.locator("#overlay-font-family")))
    _set_input_value(page.locator("#overlay-font-size"), "16")
    page.locator("#overlay-font-bold").check()
    page.locator("#overlay-font-italic").check()
    _set_input_value(page.locator("#bubble-width"), "240")
    _set_input_value(page.locator("#bubble-height"), "96")
    _set_input_value(page.locator("#timer-x"), "0.25")
    _set_input_value(page.locator("#timer-y"), "0.15")
    page.locator("#timer-lock-to-stack").check()


def _exercise_merge_and_export(page, secondary_path: Path, tmp_path: Path, monkeypatch) -> None:
    captured_exports: list[dict[str, object]] = []

    def fake_export_project(project, output_path, progress_callback=None, log_callback=None):
        captured_exports.append(
            {
                "output_path": str(output_path),
                "merge_sources": len(project.merge_sources),
                "quality": project.export.quality,
                "preset": project.export.preset,
            }
        )
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake mp4")
        project.export.last_log = "Master export log"
        project.export.last_error = None
        return output

    monkeypatch.setattr("splitshot.browser.server.export_project", fake_export_project)

    _open_tool(page, "merge")
    page.locator("#merge-media-input").set_input_files(str(secondary_path))
    page.wait_for_function("() => (state?.project?.merge_sources || []).length === 1")

    tertiary_path = secondary_path.parent / f"{secondary_path.stem}-extra{secondary_path.suffix}"
    if not tertiary_path.exists():
        tertiary_path.write_bytes(secondary_path.read_bytes())
    page.locator("#merge-media-input").set_input_files(str(tertiary_path))
    page.wait_for_function("() => (state?.project?.merge_sources || []).length === 2")

    page.locator("#merge-enabled").check()
    page.wait_for_function("() => state?.project?.merge?.enabled === true")
    page.locator("#merge-layout").select_option("pip")
    page.wait_for_function("() => state?.project?.merge?.layout === 'pip'")

    _set_input_value(page.locator("#pip-size"), "50")
    _set_input_value(page.locator("#pip-x"), "0.25")
    _set_input_value(page.locator("#pip-y"), "0.75")

    first_card = page.locator(".merge-media-card").first
    source_id = first_card.get_attribute("data-source-id")
    page.evaluate(
        """(sourceId) => {
            setMergeSourceExpanded(sourceId, true);
            renderMergeMediaList();
        }""",
        source_id,
    )
    page.wait_for_selector(".merge-media-card-body:not([hidden])")
    page.locator('.merge-media-card .merge-source-sync-buttons button', has_text='+1 ms').first.click()
    first_card.locator('[data-merge-source-field="size"]').evaluate(
        """(input) => {
            input.value = '60';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )
    first_card.locator('[data-merge-source-field="opacity"]').evaluate(
        """(input) => {
            input.value = '80';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )
    first_card.get_by_role("button", name="+1 ms").click()

    second_card = page.locator(".merge-media-card").nth(1)
    second_card.locator('button[aria-label*="PiP item controls"]').click()
    second_card.locator('[data-merge-source-field="size"]').evaluate(
        """(input) => {
            input.value = '55';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )
    second_card.locator('[data-merge-source-remove]').click()
    page.wait_for_function("() => (state?.project?.merge_sources || []).length === 1")

    _open_tool(page, "export")
    page.locator("#quality").select_option(_alternate_select_value(page.locator("#quality")))
    page.locator("#aspect-ratio").select_option(_alternate_select_value(page.locator("#aspect-ratio")))
    _set_input_value(page.locator("#target-width"), "1280")
    _set_input_value(page.locator("#target-height"), "720")
    page.locator("#frame-rate").select_option(_alternate_select_value(page.locator("#frame-rate")))
    page.locator("#video-codec").select_option(_alternate_select_value(page.locator("#video-codec")))
    _set_input_value(page.locator("#video-bitrate"), "12")
    page.locator("#audio-codec").select_option(_alternate_select_value(page.locator("#audio-codec")))
    _set_input_value(page.locator("#audio-sample-rate"), "48000")
    _set_input_value(page.locator("#audio-bitrate"), "256")
    page.locator("#color-space").select_option(_alternate_select_value(page.locator("#color-space")))
    page.locator("#ffmpeg-preset").select_option(_alternate_select_value(page.locator("#ffmpeg-preset")))
    page.locator("#two-pass").check()

    output_path = tmp_path / "master-full-app-export.mp4"
    page.locator("#export-path").fill(str(output_path))
    page.locator("#export-video").click()
    page.wait_for_function("(path) => state?.project?.export?.output_path === path", arg=str(output_path))
    page.locator("#show-export-log").click()
    page.wait_for_function("() => document.getElementById('export-log-modal')?.hidden === false")
    page.locator("#close-export-log").click()
    page.wait_for_function("() => document.getElementById('export-log-modal')?.hidden === true")

    assert captured_exports
    assert captured_exports[0]["output_path"] == str(output_path)


def _exercise_settings_and_shotml(page) -> None:
    _open_tool(page, "settings")
    for section_id in ["global-template", "pip", "overlay", "export"]:
        section = page.locator(f'[data-settings-section="{section_id}"]')
        if section.evaluate("element => element.classList.contains('collapsed')"):
            section.locator('button[data-section-toggle]').click()
            page.wait_for_function(
                "(selector) => !document.querySelector(selector)?.classList.contains('collapsed')",
                arg=f'[data-settings-section="{section_id}"]',
            )

    _set_select = lambda selector: page.locator(selector).select_option(_alternate_select_value(page.locator(selector)))
    _set_select("#settings-scope")
    _set_select("#settings-default-tool")
    page.locator("#settings-reopen-last-tool").uncheck()
    _set_select("#settings-merge-layout")
    _set_select("#settings-pip-size")
    _set_select("#settings-overlay-position")
    _set_select("#settings-badge-size")
    _set_input_value(page.locator("#settings-overlay-custom-opacity"), "0.75")
    _set_select("#settings-export-quality")
    _set_select("#settings-export-preset")
    _set_select("#settings-export-frame-rate")
    _set_select("#settings-export-video-codec")
    _set_select("#settings-export-audio-codec")
    _set_select("#settings-export-color-space")
    _set_select("#settings-export-ffmpeg-preset")
    page.locator("#settings-export-two-pass").check()
    page.locator("#settings-import-current").click()
    page.locator("#settings-reset-defaults").click()
    page.wait_for_function("() => state?.settings?.default_tool === 'project'")

    _open_tool(page, "shotml")
    threshold_section = page.locator('[data-shotml-section="threshold"]')
    if threshold_section.evaluate("element => element.classList.contains('collapsed')"):
        threshold_section.locator('button[data-section-toggle]').click()
        page.wait_for_function(
            "(sectionSelector) => !document.querySelector(sectionSelector)?.classList.contains('collapsed')",
            arg='[data-shotml-section="threshold"]',
        )

    page.locator("#threshold").fill("0.5")
    page.locator("#apply-threshold").click()
    page.wait_for_function(
        "() => state?.project?.analysis?.shotml_settings?.detection_threshold === 0.5"
    )
    page.locator("#reset-shotml-defaults").click()
    page.wait_for_function(
        "() => state?.project?.analysis?.shotml_settings?.detection_threshold === 0.35"
    )


def test_browser_full_app_e2e_calls_surface_workflows(synthetic_video_factory, tmp_path: Path, monkeypatch) -> None:
    primary_path = Path(synthetic_video_factory(name="full-app-primary"))
    secondary_path = Path(synthetic_video_factory(name="full-app-secondary"))
    secondary_path.parent.mkdir(parents=True, exist_ok=True)
    tertiary_path = secondary_path.parent / f"{secondary_path.stem}-extra{secondary_path.suffix}"
    tertiary_path.write_bytes(secondary_path.read_bytes())

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _exercise_shell_routing(page)
                _exercise_waveform_and_timing(page)
                _exercise_markers_review_overlay(page)
                _exercise_merge_and_export(page, secondary_path, tmp_path, monkeypatch)
                _exercise_settings_and_shotml(page)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_browser_full_app_practiscore_timing_scoring_save_reload_persistence_truth_gate(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    primary_path = Path(synthetic_video_factory(name="truth-gate-practiscore-primary"))
    project_path = tmp_path / "truth-gate-practiscore"
    practiscore_path = Path(__file__).resolve().parents[2] / "example_data" / "IDPA" / "IDPA.csv"

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _set_project_path(page, project_path)
                page.evaluate("(path) => createNewProject(path)", str(project_path))
                page.wait_for_function("(path) => state?.project?.path === path", arg=str(project_path))
                _load_primary_video(page, primary_path)

                page.locator("#practiscore-file-input").set_input_files(str(practiscore_path))
                page.wait_for_function("() => state?.project?.scoring?.stage_number !== null")

                _exercise_waveform_and_timing(page)
                _open_tool(page, "scoring")
                page.locator("#expand-scoring").click()
                page.wait_for_function("() => scoringWorkbenchExpanded === true")

                page.evaluate("(path) => useProjectFolder(path)", str(project_path))
                page.wait_for_function("(path) => state?.project?.path === path", arg=str(project_path))
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("() => state?.project?.scoring?.stage_number !== null")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_browser_full_app_markers_review_overlay_export_preview_parity_truth_gate(
    synthetic_video_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    primary_path = Path(synthetic_video_factory(name="truth-gate-markers-primary"))
    secondary_path = Path(synthetic_video_factory(name="truth-gate-markers-secondary"))

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _exercise_markers_review_overlay(page)
                _exercise_merge_and_export(page, secondary_path, tmp_path, monkeypatch)
                page.wait_for_function("() => (state?.project?.overlay?.text_boxes || []).length > 0")
                page.wait_for_function("() => (state?.project?.popups || []).length > 0")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_browser_full_app_merge_export_sync_truth_gate(synthetic_video_factory, tmp_path: Path, monkeypatch) -> None:
    primary_path = Path(synthetic_video_factory(name="truth-gate-merge-primary"))
    secondary_path = Path(synthetic_video_factory(name="truth-gate-merge-secondary"))

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _exercise_merge_and_export(page, secondary_path, tmp_path, monkeypatch)
                page.wait_for_function("() => state?.project?.merge?.layout === 'pip'")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_browser_full_app_settings_defaults_seed_fresh_project_truth_gate(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    primary_path = Path(synthetic_video_factory(name="truth-gate-settings-primary"))
    project_path = tmp_path / "truth-gate-settings"

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _exercise_settings_and_shotml(page)
                _set_project_path(page, project_path)
                page.evaluate("(path) => createNewProject(path)", str(project_path))
                page.wait_for_function("(path) => state?.project?.path === path", arg=str(project_path))
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("() => state?.project?.analysis?.shotml_settings?.detection_threshold !== undefined")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_browser_full_app_shotml_rerun_apply_or_discard_truth_gate(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="truth-gate-shotml-primary"))

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                _open_tool(page, "shotml")
                threshold_section = page.locator('[data-shotml-section="threshold"]')
                if threshold_section.evaluate("element => element.classList.contains('collapsed')"):
                    threshold_section.locator('button[data-section-toggle]').click()
                    page.wait_for_function(
                        "(selector) => !document.querySelector(selector)?.classList.contains('collapsed')",
                        arg='[data-shotml-section="threshold"]',
                    )
                page.locator("#threshold").fill("0.5")
                page.locator("#apply-threshold").click()
                page.wait_for_function("() => state?.project?.analysis?.shotml_settings?.detection_threshold === 0.5")

                _open_tool(page, "timing")
                target_shot_id = _select_first_waveform_shot(page)
                original_time_ms = page.evaluate(
                    """(shotId) => (state?.project?.analysis?.shots || []).find((item) => item.id === shotId)?.time_ms ?? null""",
                    target_shot_id,
                )
                assert original_time_ms is not None
                page.locator('button[data-nudge="10"]').click()
                page.wait_for_function(
                    """(payload) => (state?.project?.analysis?.shots || []).find((item) => item.id === payload.shotId)?.time_ms === payload.timeMs""",
                    arg={"shotId": target_shot_id, "timeMs": original_time_ms + 10},
                )

                timing_changer_section = page.locator('[data-shotml-section="timing_changer"]')
                _open_tool(page, "shotml")
                if timing_changer_section.evaluate("element => element.classList.contains('collapsed')"):
                    timing_changer_section.locator('button[data-section-toggle]').click()
                    page.wait_for_function(
                        "(selector) => !document.querySelector(selector)?.classList.contains('collapsed')",
                        arg='[data-shotml-section="timing_changer"]',
                    )

                page.locator("#generate-shotml-proposals").click()
                page.wait_for_function(
                    """(shotId) => (state?.project?.analysis?.timing_change_proposals || []).some((item) => item.shot_id === shotId && item.proposal_type === 'restore_shot' && item.status === 'pending')""",
                    arg=target_shot_id,
                )
                restore_index = page.evaluate(
                    """(shotId) => (state?.project?.analysis?.timing_change_proposals || []).filter((item) => item.status === 'pending').findIndex((item) => item.shot_id === shotId && item.proposal_type === 'restore_shot')""",
                    target_shot_id,
                )
                assert restore_index >= 0
                proposal_rows = page.locator('.shotml-proposal-row')
                proposal_rows.nth(restore_index).get_by_role('button', name='Apply').click()
                page.wait_for_function(
                    """(payload) => (state?.project?.analysis?.shots || []).find((item) => item.id === payload.shotId)?.time_ms === payload.timeMs""",
                    arg={"shotId": target_shot_id, "timeMs": original_time_ms},
                )

                _open_tool(page, "timing")
                page.locator('button[data-nudge="10"]').click()
                page.wait_for_function(
                    """(payload) => (state?.project?.analysis?.shots || []).find((item) => item.id === payload.shotId)?.time_ms === payload.timeMs""",
                    arg={"shotId": target_shot_id, "timeMs": original_time_ms + 10},
                )

                _open_tool(page, "shotml")
                if timing_changer_section.evaluate("element => element.classList.contains('collapsed')"):
                    timing_changer_section.locator('button[data-section-toggle]').click()
                    page.wait_for_function(
                        "(selector) => !document.querySelector(selector)?.classList.contains('collapsed')",
                        arg='[data-shotml-section="timing_changer"]',
                    )
                page.locator("#generate-shotml-proposals").click()
                page.wait_for_function(
                    """(shotId) => (state?.project?.analysis?.timing_change_proposals || []).some((item) => item.shot_id === shotId && item.proposal_type === 'restore_shot' && item.status === 'pending')""",
                    arg=target_shot_id,
                )
                restore_index = page.evaluate(
                    """(shotId) => (state?.project?.analysis?.timing_change_proposals || []).filter((item) => item.status === 'pending').findIndex((item) => item.shot_id === shotId && item.proposal_type === 'restore_shot')""",
                    target_shot_id,
                )
                assert restore_index >= 0
                proposal_rows = page.locator('.shotml-proposal-row')
                proposal_rows.nth(restore_index).get_by_role('button', name='Discard').click()
                page.wait_for_function(
                    """(payload) => {
                        const proposal = (state?.project?.analysis?.timing_change_proposals || []).find((item) => item.shot_id === payload.shotId && item.proposal_type === 'restore_shot' && item.status === 'discarded');
                        const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === payload.shotId);
                        return Boolean(proposal) && shot?.time_ms === payload.timeMs;
                    }""",
                    arg={"shotId": target_shot_id, "timeMs": original_time_ms + 10},
                )
            finally:
                browser.close()
    finally:
        server.shutdown()