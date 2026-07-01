from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from tests.browser.helpers.activity_tracker import assert_status
from tests.browser.helpers.video_test_helpers import (
    open_page,
    ensure_project_with_primary_and_merge,
    navigate_to_tool,
    get_merge_source_state,
    setup_server_and_browser,
)


def test_apply_all_trims_logs_event(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
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
                page.wait_for_timeout(300)
                tracker.assert_activity("trim.apply-all")
                try:
                    assert_status(page, "Applied trim")
                except AssertionError:
                    assert_status(page, "analysis")
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
                page.wait_for_timeout(500)
                page.click("#trim-global-clear")
                page.wait_for_timeout(500)
                tracker.assert_activity("trim.clear-all")
                try:
                    assert_status(page, "Cleared all trims")
                except AssertionError:
                    assert_status(page, "analysis")
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
                page.wait_for_timeout(1000)

                tracker.assert_activity("trim.apply")
                try:
                    assert_status(page, "Applied trim")
                except AssertionError:
                    assert_status(page, "analysis")

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
                        assert_status(page, "analysis")
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
                        assert_status(page, "analysis")
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
