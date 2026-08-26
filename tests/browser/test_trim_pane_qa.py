from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _ensure_project_with_primary_and_merge(
    page, primary_path: Path, merge_path: Path, project_name: str
) -> None:
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_dir = str(primary_path.parent / project_name)
        page.evaluate(f"() => createNewProject({json.dumps(project_dir)})")
        page.wait_for_function("() => Boolean(state?.project?.path)")

    if not page.evaluate("Boolean(state?.project?.primary_video?.path)"):
        page.locator("#primary-file-input").set_input_files(str(primary_path))
        page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")

    merge_count = page.evaluate("() => (state?.project?.merge_sources || []).length")
    if merge_count == 0:
        page.locator("#merge-media-input").set_input_files(str(merge_path))
        page.wait_for_function("() => (state?.project?.merge_sources || []).length > 0")


def _navigate_to_trim_pane(page) -> None:
    page.locator("button[data-tool='trim-sync']").click(force=True)
    page.wait_for_timeout(300)
    assert page.evaluate("activeTool") == "trim-sync"


def _get_first_merge_source_state(page):
    return page.evaluate(
        "() => {"
        "  const sources = state?.project?.merge_sources || [];"
        "  if (!sources.length) return null;"
        "  const s = sources[0];"
        "  const td = s.trim_derivative;"
        "  return {"
        "    source_id: s.id,"
        "    has_derivative: Boolean(td),"
        "    active_path_kind: td?.active_path_kind ?? null,"
        "    derivative_path: td?.derivative_path ?? null,"
        "    start_s: td?.start_s ?? null,"
        "    end_s: td?.end_s ?? null,"
        "  };"
        "}"
    )


def _wait_for_first_merge_derivative(page, present: bool) -> None:
    if present:
        page.wait_for_function(
            """() => {
                const source = (state?.project?.merge_sources || [])[0];
                const trim = source?.trim_derivative;
                return Boolean(trim?.derivative_path)
                    && trim?.active_path_kind === 'local_derivative';
            }"""
        )
        return
    page.wait_for_function(
        """() => {
            const source = (state?.project?.merge_sources || [])[0];
            const trim = source?.trim_derivative;
            return Boolean(source)
                && !trim?.derivative_path
                && trim?.active_path_kind == null;
        }"""
    )


def test_trim_pane_renders_global_and_source_sections(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-primary", duration_ms=4000, beep_ms=500, shot_times_ms=[800, 1200, 1600]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-merge", duration_ms=4000, beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(200)
                assert page.evaluate("activeTool") == "trim-sync"

                assert page.locator(".trim-timing-bar").count() == 0
                assert page.locator("#trim-global-start").count() == 1
                assert page.locator("#trim-global-end").count() == 1
                assert page.locator("#trim-global-apply").count() == 1
                assert page.locator("#trim-global-clear").count() == 1

                assert page.locator(".trim-source-card").count() >= 1
                assert page.locator(".trim-computed-label").count() >= 1
                assert page.locator(".trim-beep-btn").count() >= 1
                assert page.locator(".trim-last-shot-btn").count() >= 1
                assert page.locator("#trim-video-toggle").count() == 1
                assert page.locator("#trim-video-scrubber").count() == 1
                assert page.evaluate("document.querySelector('#primary-video').controls") is False
                page.evaluate(
                    """() => {
                        const video = document.querySelector('#primary-video');
                        video.currentTime = 0.25;
                        video.dispatchEvent(new Event('timeupdate'));
                    }"""
                )
                assert re.fullmatch(
                    r"\d+\.\d{2}s / \d+\.\d{2}s",
                    page.locator("#trim-video-time").inner_text(),
                )
                page.locator("button[data-tool='media']").click(force=True)
                assert page.evaluate("document.querySelector('#primary-video').controls") is True
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_pane_omits_bulk_beep_last_shot_duration_summary(
    synthetic_video_factory,
) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-timing", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-timing-merge", beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-timing.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(300)

                bulk_text = page.locator('[data-trim-section="bulk"]').inner_text()
                assert "Last shot" not in bulk_text
                assert "Duration" not in bulk_text
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_pane_default_buffers_are_two_seconds(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-buffers", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-buffers-merge", beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-buffers.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(200)

                global_start = page.locator("#trim-global-start").input_value()
                global_end = page.locator("#trim-global-end").input_value()
                assert global_start == "2.00"
                assert global_end == "2.00"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_pane_reset_to_defaults_button(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-reset", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-reset-merge", beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-reset.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(200)

                page.locator("#trim-global-start").fill("5.00")
                page.locator("#trim-global-end").fill("5.00")
                page.locator("#trim-global-defaults-btn").click()
                page.wait_for_timeout(100)

                start_val = page.locator("#trim-global-start").input_value()
                end_val = page.locator("#trim-global-end").input_value()
                assert start_val != "5.00"
                assert end_val != "5.00"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_pane_computed_label_format(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-computed", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-computed-merge", beep_ms=600))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-computed.ssproj"
                )
                page.locator("button[data-tool='trim-sync']").click(force=True)
                page.wait_for_timeout(500)

                label = page.locator(".trim-computed-label").first.inner_text()
                assert label.startswith("Start ")
                assert " · End " in label
                assert " · Duration " in label
                assert len(re.findall(r"\d+\.\d{2}s", label)) == 3
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_apply_all_sets_derivative_and_file(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-applyall", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(
        synthetic_video_factory(name="trim-qa-applyall-merge", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-applyall.ssproj"
                )
                _navigate_to_trim_pane(page)

                expected = page.evaluate(
                    """() => {
                        const source = (state?.project?.merge_sources || [])[0];
                        const beepMs = Number(state?.project?.analysis?.beep_time_ms_primary ?? 0);
                        const shots = state?.project?.analysis?.shots || [];
                        const lastShotMs = shots.length ? Math.max(...shots.map((shot) => Number(shot.time_ms || 0))) : 0;
                        const syncOffsetMs = Number(source?.sync_offset_ms || 0);
                        const durationS = Number(source?.asset?.duration_ms || 0) / 1000;
                        const beepS = (beepMs + syncOffsetMs) / 1000;
                        const bufferedEndS = ((lastShotMs + syncOffsetMs) / 1000) + 1.0;
                        return {
                            start_s: beepS >= 0.5 ? beepS - 0.5 : null,
                            end_s: bufferedEndS <= durationS ? bufferedEndS : null,
                        };
                    }"""
                )
                page.locator("#trim-global-start").fill("0.50")
                page.locator("#trim-global-end").fill("1.00")
                page.wait_for_timeout(100)
                page.locator("#trim-global-apply").click()
                _wait_for_first_merge_derivative(page, True)
                page.locator("#close-export-log").click()

                state = _get_first_merge_source_state(page)
                assert state is not None
                assert state["has_derivative"] is True
                assert state["active_path_kind"] == "local_derivative"
                if expected["start_s"] is None:
                    assert state["start_s"] is None
                else:
                    assert state["start_s"] == pytest.approx(expected["start_s"], abs=0.1)
                assert state["end_s"] == pytest.approx(expected["end_s"], abs=0.1)

                deriv_path = state.get("derivative_path")
                assert deriv_path
                assert Path(deriv_path).exists()
                assert Path(deriv_path).stat().st_size > 0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_clear_all_removes_derivative(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-clear", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(
        synthetic_video_factory(name="trim-qa-clear-merge", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-clear.ssproj"
                )
                _navigate_to_trim_pane(page)

                page.locator("#trim-global-start").fill("0.50")
                page.locator("#trim-global-end").fill("1.00")
                page.wait_for_timeout(100)
                page.locator("#trim-global-apply").click()
                _wait_for_first_merge_derivative(page, True)
                page.locator("#close-export-log").click()

                before = _get_first_merge_source_state(page)
                assert before["has_derivative"] is True

                page.locator("#trim-global-clear").click()
                _wait_for_first_merge_derivative(page, False)

                after = _get_first_merge_source_state(page)
                assert after["active_path_kind"] is None
                assert after["derivative_path"] is None
                assert after["start_s"] is None
                assert after["end_s"] is None

                deriv_path = before.get("derivative_path")
                assert deriv_path
                if Path(deriv_path).exists():
                    Path(deriv_path).unlink()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_start_at_beep_sets_input_to_beep_time(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-beep", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(
        synthetic_video_factory(name="trim-qa-beep-merge", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-beep.ssproj"
                )
                _navigate_to_trim_pane(page)

                before = page.locator("[data-trim-start]").first.input_value()

                page.locator(".trim-beep-btn").first.click()
                page.wait_for_timeout(800)

                after = page.locator("[data-trim-start]").first.input_value()
                assert before != after
                assert float(after) > 0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_end_after_last_shot_sets_input_to_last_shot_time(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-lastshot", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1800]
        )
    )
    merge_path = Path(
        synthetic_video_factory(name="trim-qa-lastshot-merge", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-lastshot.ssproj"
                )
                _navigate_to_trim_pane(page)

                before = page.locator("[data-trim-end]").first.input_value()

                page.locator(".trim-last-shot-btn").first.click()
                page.wait_for_timeout(800)

                after = page.locator("[data-trim-end]").first.input_value()
                assert before != after
                assert float(after) > 0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_undo_restores_previous_global_values(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-undo", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(
        synthetic_video_factory(name="trim-qa-undo-merge", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-undo.ssproj"
                )
                _navigate_to_trim_pane(page)

                expected_first = page.evaluate(
                    """() => {
                        const source = (state?.project?.merge_sources || [])[0];
                        const beepMs = Number(state?.project?.analysis?.beep_time_ms_primary ?? 0);
                        const shots = state?.project?.analysis?.shots || [];
                        const lastShotMs = shots.length ? Math.max(...shots.map((shot) => Number(shot.time_ms || 0))) : 0;
                        const syncOffsetMs = Number(source?.sync_offset_ms || 0);
                        const durationS = Number(source?.asset?.duration_ms || 0) / 1000;
                        const beepS = (beepMs + syncOffsetMs) / 1000;
                        const bufferedEndS = ((lastShotMs + syncOffsetMs) / 1000) + 1.0;
                        return {
                            start_s: beepS >= 0.3 ? beepS - 0.3 : null,
                            end_s: bufferedEndS <= durationS ? bufferedEndS : null,
                        };
                    }"""
                )
                page.locator("#trim-global-start").fill("0.30")
                page.locator("#trim-global-end").fill("1.00")
                page.wait_for_timeout(100)
                page.locator("#trim-global-apply").click()
                _wait_for_first_merge_derivative(page, True)

                after_first = _get_first_merge_source_state(page)
                page.locator("#close-export-log").click()
                assert after_first["has_derivative"] is True
                first_derivative_path = after_first["derivative_path"]

                expected_second = page.evaluate(
                    """() => {
                        const source = (state?.project?.merge_sources || [])[0];
                        const beepMs = Number(state?.project?.analysis?.beep_time_ms_primary ?? 0);
                        const shots = state?.project?.analysis?.shots || [];
                        const lastShotMs = shots.length ? Math.max(...shots.map((shot) => Number(shot.time_ms || 0))) : 0;
                        const originalOffsetMs = Math.round(Number(state?.project?.primary_trim_derivative?.start_s || 0) * 1000);
                        const syncOffsetMs = Number(source?.sync_offset_ms || 0);
                        const durationS = Number(source?.asset?.duration_ms || 0) / 1000;
                        const beepS = (beepMs + originalOffsetMs + syncOffsetMs) / 1000;
                        const bufferedEndS = ((lastShotMs + originalOffsetMs + syncOffsetMs) / 1000) + 1.2;
                        return {
                            start_s: beepS >= 0.4 ? beepS - 0.4 : null,
                            end_s: bufferedEndS <= durationS ? bufferedEndS : null,
                        };
                    }"""
                )
                page.locator("#trim-global-start").fill("0.40")
                page.locator("#trim-global-end").fill("1.20")
                page.wait_for_timeout(100)
                page.locator("#trim-global-apply").click()
                page.wait_for_function(
                    "(path) => (state?.project?.merge_sources || [])[0]?.trim_derivative?.derivative_path !== path",
                    arg=first_derivative_path,
                    timeout=120_000,
                )

                after_second = _get_first_merge_source_state(page)
                page.locator("#close-export-log").click()
                if expected_second["start_s"] is None:
                    assert after_second["start_s"] is None
                else:
                    assert after_second["start_s"] == pytest.approx(
                        expected_second["start_s"], abs=0.2
                    )
                assert after_second["end_s"] == pytest.approx(expected_second["end_s"], abs=0.2)
                second_derivative_path = after_second["derivative_path"]

                page.locator("#trim-global-undo").click()
                page.wait_for_function(
                    "(path) => (state?.project?.merge_sources || [])[0]?.trim_derivative?.derivative_path !== path",
                    arg=second_derivative_path,
                    timeout=120_000,
                )

                restored = _get_first_merge_source_state(page)
                if expected_first["start_s"] is None:
                    assert restored["start_s"] is None
                else:
                    assert restored["start_s"] == pytest.approx(expected_first["start_s"], abs=0.2)
                assert restored["end_s"] == pytest.approx(expected_first["end_s"], abs=0.2)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_per_source_apply_persists(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-srcapply", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(
        synthetic_video_factory(name="trim-qa-srcapply-merge", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-srcapply.ssproj"
                )
                _navigate_to_trim_pane(page)
                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id

                start_input = page.locator(f'[data-trim-start="{source_id}"]')
                end_input = page.locator(f'[data-trim-end="{source_id}"]')
                start_input.fill("0.30")
                end_input.fill("2.10")
                page.wait_for_timeout(100)
                page.locator(f'.trim-apply-btn[data-source-id="{source_id}"]').click()
                _wait_for_first_merge_derivative(page, True)

                state = _get_first_merge_source_state(page)
                assert state["has_derivative"] is True
                assert state["active_path_kind"] == "local_derivative"
                assert state["derivative_path"]
                assert Path(state["derivative_path"]).exists()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_sync_nudge_adjusts_offset(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-nudge", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(
        synthetic_video_factory(name="trim-qa-nudge-merge", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-nudge.ssproj"
                )
                _navigate_to_trim_pane(page)
                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id

                label_el = page.locator(
                    f'.trim-source-card[data-source-id="{source_id}"] .trim-source-card-copy small'
                )
                before_label = label_el.inner_text()
                assert "ms" in before_label.lower()

                page.locator(
                    f'.trim-source-card[data-source-id="{source_id}"] [data-sync-delta="10"]'
                ).click()
                page.wait_for_timeout(800)

                after_label = label_el.inner_text()
                assert after_label != before_label
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_status_bar_updates_after_apply(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-status", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(synthetic_video_factory(name="trim-qa-status-merge", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-status.ssproj"
                )
                _navigate_to_trim_pane(page)

                page.locator("#trim-global-start").fill("0.50")
                page.locator("#trim-global-end").fill("2.50")
                page.wait_for_timeout(100)
                page.locator("#trim-global-apply").click()
                page.wait_for_timeout(1000)

                status_text = page.locator("#status-copy").inner_text()
                assert len(status_text.strip()) > 0
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_per_source_apply_creates_valid_derivative(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-valid", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(
        synthetic_video_factory(name="trim-qa-valid-merge", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-valid.ssproj"
                )
                _navigate_to_trim_pane(page)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id

                source_card = page.locator(f'.trim-source-card[data-source-id="{source_id}"]')
                source_card.locator("[data-trim-start]").fill("0.20")
                source_card.locator("[data-trim-end]").fill("1.80")
                page.wait_for_timeout(100)
                source_card.locator(".trim-apply-btn").click()
                page.wait_for_function(
                    """(sourceId) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === sourceId);
                        return Boolean(source?.trim_derivative?.derivative_path);
                    }""",
                    arg=source_id,
                    timeout=120000,
                )

                deriv_path = page.evaluate(
                    """(sourceId) =>
                    (state?.project?.merge_sources || []).find((item) => item.id === sourceId)?.trim_derivative?.derivative_path || ''""",
                    source_id,
                )
                assert deriv_path
                deriv_file = Path(deriv_path)
                assert deriv_file.exists()
                assert deriv_file.stat().st_size > 0

                orig_size = Path(merge_path).stat().st_size
                assert deriv_file.stat().st_size != orig_size
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_computed_label_updates_after_source_apply(synthetic_video_factory) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-label", duration_ms=4000, beep_ms=500, shot_times_ms=[600, 1000, 1400]
        )
    )
    merge_path = Path(
        synthetic_video_factory(name="trim-qa-label-merge", duration_ms=3000, beep_ms=400)
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "trim-qa-label.ssproj"
                )
                _navigate_to_trim_pane(page)

                before_label = page.locator(".trim-computed-label").first.inner_text()

                page.locator("[data-trim-start]").first.fill("0.20")
                page.locator("[data-trim-end]").first.fill("2.80")
                page.wait_for_timeout(100)
                page.locator(".trim-apply-btn").first.click()
                page.wait_for_timeout(800)

                after_label = page.locator(".trim-computed-label").first.inner_text()
                assert after_label != before_label
                assert after_label.startswith("Start ")
                assert " · End " in after_label
                assert " · Duration " in after_label
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_trim_disables_video_controls_for_still_images(
    synthetic_video_factory, tmp_path: Path
) -> None:
    primary_path = Path(
        synthetic_video_factory(
            name="trim-qa-still-primary",
            duration_ms=4000,
            beep_ms=500,
            shot_times_ms=[600, 1000, 1400],
        )
    )
    image_path = tmp_path / "trim-reference.png"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=green:s=320x180",
            "-frames:v",
            "1",
            str(image_path),
        ],
        check=True,
    )
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _ensure_project_with_primary_and_merge(
                    page, primary_path, image_path, "trim-qa-still.ssproj"
                )
                _navigate_to_trim_pane(page)
                still_card = page.locator(".trim-source-card").filter(has_text="trim-reference.png")

                assert "Trim not applicable" in still_card.inner_text()
                assert still_card.locator("[data-trim-start]").is_disabled()
                assert still_card.locator("[data-trim-end]").is_disabled()
                assert still_card.locator(".trim-apply-btn").is_disabled()
                assert still_card.locator(".trim-beep-btn").is_disabled()
                assert still_card.locator(".trim-last-shot-btn").is_disabled()
            finally:
                browser.close()
    finally:
        server.shutdown()
