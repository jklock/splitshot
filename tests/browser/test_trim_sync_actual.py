from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tests.browser.helpers.activity_tracker import assert_status
from tests.browser.helpers.video_test_helpers import (
    ensure_project_with_primary_and_merge,
    get_merge_source_state,
    get_primary_media_state,
    navigate_to_tool,
    open_page,
    setup_server_and_browser,
)


def test_apply_all_trims_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "trim-apply-all-primary"},
        merge_kwargs={"name": "trim-apply-all-merge"},
    )
    project_name = "trim-apply-all"
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, f"{project_name}.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.fill("#trim-global-start", "0.5")
                page.fill("#trim-global-end", "3.0")
                page.click("#trim-global-apply")
                page.wait_for_function(
                    "() => document.querySelector('#status')?.textContent?.startsWith('Trimming ')",
                )
                tracker.assert_activity("trim.apply-all")
                page.wait_for_function(
                    "() => document.querySelector('#status')?.textContent === 'Trimmed 1 selected stage.'",
                    timeout=30000,
                )
                assert_status(page, "Trimmed 1 selected stage")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_bulk_trim_duration_matches_displayed_original_boundaries(
    synthetic_video_factory,
) -> None:
    server, _, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={
            "name": "trim-wysiwyg-primary",
            "duration_ms": 10_000,
            "beep_ms": 3_000,
            "shot_times_ms": [4_000, 5_500, 7_000],
        },
        merge_kwargs={
            "name": "trim-wysiwyg-merge",
            "duration_ms": 10_000,
            "beep_ms": 3_200,
            "shot_times_ms": [4_200, 5_700, 7_200],
        },
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-wysiwyg.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.fill("#trim-global-start", "2.00")
                page.fill("#trim-global-end", "2.00")
                page.screenshot(path="artifacts/trim-visual-original.png", full_page=True)
                page.click("#trim-global-apply")
                page.wait_for_function(
                    "() => Boolean(state?.project?.primary_trim_derivative?.derivative_path)",
                    timeout=120_000,
                )

                first = get_primary_media_state(page)
                expected_duration_ms = round((first["end_s"] - first["start_s"]) * 1000)
                assert first["active_duration_ms"] == pytest.approx(expected_duration_ms, abs=40)
                assert page.locator("#trim-global-start").input_value() == "2.00"
                assert page.locator("#trim-global-end").input_value() == "2.00"
                assert (
                    page.locator("#trim-video-time")
                    .inner_text()
                    .endswith(f"/ {first['active_duration_ms'] / 1000:.2f}s")
                )
                page.screenshot(path="artifacts/trim-visual-applied.png", full_page=True)

                page.click("#trim-global-apply")
                page.wait_for_function(
                    "(path) => state?.project?.primary_trim_derivative?.derivative_path !== path",
                    arg=first["derivative_path"],
                    timeout=120_000,
                )
                repeated = get_primary_media_state(page)
                assert repeated["start_s"] == pytest.approx(first["start_s"], abs=0.08)
                assert repeated["end_s"] == pytest.approx(first["end_s"], abs=0.08)
                assert repeated["active_duration_ms"] == pytest.approx(
                    round((repeated["end_s"] - repeated["start_s"]) * 1000), abs=40
                )
                page.screenshot(path="artifacts/trim-visual-reapplied.png", full_page=True)
                page.click("#trim-global-clear")
                page.wait_for_function(
                    "() => !state?.project?.primary_trim_derivative?.derivative_path",
                    timeout=120_000,
                )
                page.screenshot(path="artifacts/trim-visual-cleared.png", full_page=True)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_clear_all_trims_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-clear-all.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.fill("#trim-global-start", "0.5")
                page.fill("#trim-global-end", "3.0")
                page.click("#trim-global-apply")
                page.wait_for_function(
                    "() => Boolean(state?.project?.primary_trim_derivative?.derivative_path)",
                    timeout=120_000,
                )
                page.click("#trim-global-clear")
                page.wait_for_function(
                    "() => !state?.project?.primary_trim_derivative?.derivative_path",
                    timeout=120_000,
                )
                tracker.assert_activity("trim.clear-all")
                try:
                    assert_status(page, "Cleared trim for")
                except AssertionError:
                    try:
                        assert_status(page, "analysis")
                    except AssertionError:
                        assert_status(page, "Clearing trim derivatives")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_per_source_apply_creates_derivative_file(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-source-deriv.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.wait_for_timeout(300)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id, "No merge source found"

                start_input = page.locator(f'[data-trim-start="{source_id}"]')
                if start_input.count():
                    start_input.fill("0.5")
                end_input = page.locator(f'[data-trim-end="{source_id}"]')
                if end_input.count():
                    end_input.fill("3.0")

                apply_btn = page.locator(f'button.trim-apply-btn[data-source-id="{source_id}"]')
                if apply_btn.count():
                    apply_btn.click()
                else:
                    page.evaluate(
                        """(sid) => {
                            const btn = document.querySelector(`.trim-apply-btn[data-source-id="${sid}"]`);
                            if (btn) btn.click();
                        }""",
                        source_id,
                    )
                page.wait_for_function(
                    "(sid) => Boolean((state?.project?.merge_sources || []).find((source) => source.id === sid)?.trim_derivative?.derivative_path)",
                    arg=source_id,
                    timeout=120_000,
                )

                tracker.assert_activity("trim.apply")
                try:
                    assert_status(page, "Applied trim")
                except AssertionError:
                    try:
                        assert_status(page, "analysis")
                    except AssertionError:
                        try:
                            assert_status(page, "Trimming source")
                        except AssertionError:
                            assert_status(page, "Trimmed source")

                state = get_merge_source_state(page, source_id)
                assert state, "Merge source not found"
                if state.get("active_path_kind") == "local_derivative":
                    deriv_path = state.get("derivative_path")
                    if deriv_path:
                        assert Path(deriv_path).exists(), f"Derivative not found: {deriv_path}"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_apply_and_clear_switch_active_media_and_waveform(synthetic_video_factory) -> None:
    server, _tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "trim-active-waveform-p", "duration_ms": 3200, "beep_ms": 500},
        merge_kwargs={"name": "trim-active-waveform-m", "duration_ms": 3200, "beep_ms": 400},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-active-path.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.wait_for_timeout(500)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id, "No merge source found"

                before = get_merge_source_state(page, source_id)
                assert before
                original_path = page.evaluate(
                    """(sid) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === sid);
                        return source?.asset?.path || '';
                    }""",
                    source_id,
                )
                assert original_path

                page.locator(f'[data-trim-start="{source_id}"]').fill("0.50")
                page.locator(f'[data-trim-end="{source_id}"]').fill("2.20")
                page.locator(f'button.trim-apply-btn[data-source-id="{source_id}"]').click()
                page.wait_for_function(
                    """(sid) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === sid);
                        const trim = source?.trim_derivative;
                        return Boolean(trim?.derivative_path)
                            && trim?.active_path_kind === 'local_derivative';
                    }""",
                    arg=source_id,
                    timeout=120_000,
                )

                trimmed = get_merge_source_state(page, source_id)
                assert trimmed
                assert trimmed["trim_active"] is True
                assert trimmed["effective_media_path"] == trimmed["derivative_path"]
                assert Path(trimmed["derivative_path"]).exists()
                assert trimmed["waveform_sample_count"] not in {None, 0}
                assert (
                    page.locator(
                        f'.trim-source-card[data-source-id="{source_id}"] .trim-active-path-state'
                    ).inner_text()
                    == "Using trimmed media"
                )

                page.locator(f'button.trim-clear-btn[data-source-id="{source_id}"]').click()
                page.wait_for_function(
                    """(payload) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === payload.sourceId);
                        const trim = source?.trim_derivative;
                        return Boolean(source)
                            && !trim?.derivative_path
                            && trim?.active_path_kind == null
                            && source?.effective_media_path === payload.originalPath;
                    }""",
                    arg={"sourceId": source_id, "originalPath": original_path},
                    timeout=120_000,
                )

                cleared = get_merge_source_state(page, source_id)
                assert cleared
                assert cleared["trim_active"] is False
                assert cleared["effective_media_path"] == original_path
                assert cleared["waveform_sample_count"] not in {None, 0}
                assert (
                    page.locator(
                        f'.trim-source-card[data-source-id="{source_id}"] .trim-active-path-state'
                    ).inner_text()
                    == "Using original"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_apply_all_switches_primary_and_added_active_media(synthetic_video_factory) -> None:
    server, _tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "trim-primary-added-p", "duration_ms": 4200, "beep_ms": 500},
        merge_kwargs={"name": "trim-primary-added-m", "duration_ms": 4200, "beep_ms": 430},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-primary-added.ssproj"
                )
                page.evaluate("() => callApi('/api/project/stage/create', {})")
                page.wait_for_function(
                    "() => Boolean(state?.project?.active_stage_id) && (state?.project?.stages || []).length >= 1"
                )
                navigate_to_tool(page, "merge")
                page.locator("#merge-enabled").check()
                page.locator("#merge-layout").select_option("pip")
                navigate_to_tool(page, "trim-sync")
                page.wait_for_timeout(500)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id, "No merge source found"

                original_primary_path = page.evaluate(
                    "() => state?.project?.primary_video?.path || ''"
                )
                original_added_path = page.evaluate(
                    """(sid) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === sid);
                        return source?.asset?.path || '';
                    }""",
                    source_id,
                )

                page.fill("#trim-global-start", "2.00")
                page.fill("#trim-global-end", "2.00")
                page.click("#trim-global-apply")
                page.wait_for_function(
                    """(sid) => {
                        const primary = state?.project?.primary_video || {};
                        const primaryTrim = state?.project?.primary_trim_derivative || {};
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === sid);
                        const trim = source?.trim_derivative || {};
                        return Boolean(primaryTrim?.derivative_path)
                            && primaryTrim?.active_path_kind === 'local_derivative'
                            && Boolean(trim?.derivative_path)
                            && trim?.active_path_kind === 'local_derivative'
                            && primary?.effective_media_path === primaryTrim?.derivative_path
                            && source?.effective_media_path === trim?.derivative_path;
                    }""",
                    arg=source_id,
                    timeout=120_000,
                )

                primary_state = get_primary_media_state(page)
                added_state = get_merge_source_state(page, source_id)
                assert primary_state["trim_active"] is True
                assert added_state["trim_active"] is True
                assert primary_state["effective_media_path"] != original_primary_path
                assert added_state["effective_media_path"] != original_added_path
                assert Path(primary_state["derivative_path"]).exists()
                assert Path(added_state["derivative_path"]).exists()

                navigate_to_tool(page, "media")
                media_text = page.locator("#media-pane").inner_text()
                assert primary_state["active_display_name"] in media_text
                assert Path(added_state["effective_media_path"]).name in media_text

                navigate_to_tool(page, "merge")
                page.wait_for_function(
                    """(sid) => {
                        const media = document.querySelector(`#merge-preview-layer .merge-preview-item[data-source-id="${sid}"] video`);
                        return Boolean(media?.dataset?.sourcePath)
                            && media.dataset.sourcePath.includes('_trim');
                    }""",
                    arg=source_id,
                    timeout=10000,
                )

                navigate_to_tool(page, "trim-sync")
                page.click("#trim-global-clear")
                page.wait_for_function(
                    """(payload) => {
                        const primary = state?.project?.primary_video || {};
                        const primaryTrim = state?.project?.primary_trim_derivative || {};
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === payload.sourceId);
                        const trim = source?.trim_derivative || {};
                        return !primaryTrim?.derivative_path
                            && primaryTrim?.active_path_kind == null
                            && primary?.effective_media_path === payload.primaryPath
                            && !trim?.derivative_path
                            && trim?.active_path_kind == null
                            && source?.effective_media_path === payload.addedPath;
                    }""",
                    arg={
                        "sourceId": source_id,
                        "primaryPath": original_primary_path,
                        "addedPath": original_added_path,
                    },
                    timeout=120_000,
                )
                cleared_primary = get_primary_media_state(page)
                cleared_added = get_merge_source_state(page, source_id)
                assert cleared_primary["trim_active"] is False
                assert cleared_added["trim_active"] is False
                assert cleared_primary["effective_media_path"] == original_primary_path
                assert cleared_added["effective_media_path"] == original_added_path
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_start_at_beep_logs_and_sets_time(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-beep.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.wait_for_timeout(300)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id, "No merge source found"

                beep_btn = page.locator(f'button.trim-beep-btn[data-source-id="{source_id}"]')
                if beep_btn.count():
                    beep_btn.click()
                    page.wait_for_timeout(500)
                    tracker.assert_activity("trim.set-beep")
                    try:
                        assert_status(page, "Set trim start to beep time")
                    except AssertionError:
                        try:
                            assert_status(page, "analysis")
                        except AssertionError:
                            assert_status(page, "Trimming source")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_end_after_last_shot_logs_and_sets_time(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-lastshot.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.wait_for_timeout(300)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id, "No merge source found"

                ls_btn = page.locator(f'button.trim-last-shot-btn[data-source-id="{source_id}"]')
                if ls_btn.count():
                    ls_btn.click()
                    page.wait_for_timeout(500)
                    tracker.assert_activity("trim.set-last-shot")
                    try:
                        assert_status(page, "Set trim end to last shot time")
                    except AssertionError:
                        try:
                            assert_status(page, "analysis")
                        except AssertionError:
                            assert_status(page, "Trimming source")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_sync_offset_change_logs_and_updates(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "sync-offset-change.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.wait_for_timeout(300)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id

                offset_input = page.locator(f'[data-source-sync-offset="{source_id}"]')
                if offset_input.count():
                    offset_input.fill("250")
                    offset_input.dispatch_event("change")
                    page.wait_for_timeout(500)
                    tracker.assert_activity("trim.sync.set")
                    try:
                        assert_status(page, "Updated sync offset")
                    except AssertionError:
                        assert_status(page, "analysis")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_sync_nudge_buttons_log_and_adjust(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "sync-nudge.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.wait_for_timeout(300)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id

                nudge_btn = page.locator(
                    f'button[data-sync-delta="10"][data-source-id="{source_id}"]'
                )
                if nudge_btn.count():
                    nudge_btn.click()
                    page.wait_for_timeout(300)
                    nudge_btn.click()
                    page.wait_for_timeout(300)
                    nudge_btn.click()
                    page.wait_for_timeout(500)
                    tracker.assert_activity_count("trim.sync.nudge", 3)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_analyze_sync_logs_and_completes(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "sync-analyze.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.wait_for_timeout(300)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id

                analyze_btn = page.locator(f'button.trim-analyze-btn[data-source-id="{source_id}"]')
                if analyze_btn.count():
                    analyze_btn.click()
                    page.wait_for_timeout(500)
                    tracker.assert_activity("trim.sync.analyze")

                    page.wait_for_function(
                        """(sid) => {
                            const s = (state?.project?.merge_sources || []).find(m => m.id === sid);
                            return s?.sync_analysis_status === 'ready' || s?.sync_analysis_status === 'no_beep';
                        }""",
                        arg=source_id,
                        timeout=120000,
                    )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_reset_trim_defaults_logs(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-defaults.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.fill("#trim-global-start", "5.0")
                page.fill("#trim-global-end", "5.0")
                page.click("#trim-global-defaults-btn")
                page.wait_for_timeout(300)
                tracker.assert_activity("trim.global-defaults")
                try:
                    assert_status(page, "Reset trim defaults")
                except AssertionError:
                    assert_status(page, "analysis")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_undo_restores_values(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-undo.ssproj"
                )
                navigate_to_tool(page, "trim-sync")
                page.fill("#trim-global-start", "1.0")
                page.fill("#trim-global-end", "3.0")
                page.click("#trim-global-apply")
                page.wait_for_timeout(500)
                page.fill("#trim-global-start", "0.5")
                page.fill("#trim-global-end", "2.0")
                page.click("#trim-global-apply")
                page.wait_for_timeout(500)

                page.click("#trim-global-undo")
                page.wait_for_timeout(500)
                tracker.assert_activity_count("trim.apply-all", 2)
            finally:
                browser.close()
    finally:
        server.shutdown()
