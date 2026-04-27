from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


METRICS_ROW_WIDTH = 11


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _load_primary_video(page, primary_path: Path) -> None:
    page.locator("#primary-file-input").set_input_files(str(primary_path))
    page.locator(".waveform-shot-card").first.wait_for(state="attached")


def _activate_tool(page, tool_id: str) -> None:
    page.locator(f'button[data-tool="{tool_id}"]').click(force=True)
    page.wait_for_timeout(100)
    assert page.evaluate("activeTool") == tool_id


def _open_scoring_workbench(page) -> None:
    _activate_tool(page, "scoring")
    page.locator("#expand-scoring").click()
    page.wait_for_timeout(150)
    page.locator("#scoring-workbench").wait_for(state="visible")


def _open_timing_workbench(page) -> None:
    _activate_tool(page, "timing")
    page.locator("#expand-timing").click()
    page.wait_for_timeout(150)
    page.locator("#timing-workbench").wait_for(state="visible")


def _open_metrics_pane(page) -> None:
    _activate_tool(page, "metrics")
    page.locator("#expand-metrics").click()
    page.wait_for_timeout(150)
    page.locator("#metrics-workbench").wait_for(state="visible")


def _select_scoring_preset_with_penalties(page) -> str:
    preset_values = page.locator("#scoring-preset").evaluate(
        "select => [...select.options].map((option) => option.value).filter(Boolean)"
    )
    assert preset_values
    for preset_value in preset_values:
        page.locator("#scoring-preset").select_option(preset_value)
        page.wait_for_timeout(150)
        if int(page.evaluate("state.scoring_summary.penalty_fields.length")) > 0:
            return preset_value
    raise AssertionError("Expected at least one scoring preset with penalty fields.")


def _metrics_table_rows(page) -> list[list[str]]:
    return page.evaluate(
        """(rowWidth) => {
          const table = document.getElementById("metrics-workbench-table");
          if (!table) return [];
          const headerCount = table.querySelectorAll(".head").length;
          const values = Array.from(table.children)
            .slice(headerCount)
            .map((cell) => (cell.textContent || "").trim());
          const rows = [];
          for (let index = 0; index < values.length; index += rowWidth) {
            const row = values.slice(index, index + rowWidth);
            if (row.length === rowWidth) rows.push(row);
          }
          return rows;
        }""",
        METRICS_ROW_WIDTH,
    )


def _metrics_row_for_shot(page, shot_id: str) -> list[str]:
    payload = {"shotId": shot_id, "rowWidth": METRICS_ROW_WIDTH}
    page.wait_for_function(
        """({ shotId, rowWidth }) => {
          const rows = typeof buildMetricsRows === "function" ? buildMetricsRows() : [];
          const rowIndex = rows.findIndex((entry) => entry.shotId === shotId);
          if (rowIndex < 0) return false;
          const table = document.getElementById("metrics-workbench-table");
          if (!table) return false;
          const headerCount = table.querySelectorAll(".head").length;
          const start = headerCount + (rowIndex * rowWidth);
          const values = Array.from(table.children)
            .slice(start, start + rowWidth)
            .map((cell) => (cell.textContent || "").trim());
          return values.length === rowWidth;
        }""",
        arg=payload,
    )
    row = page.evaluate(
        """({ shotId, rowWidth }) => {
          const rows = typeof buildMetricsRows === "function" ? buildMetricsRows() : [];
          const rowIndex = rows.findIndex((entry) => entry.shotId === shotId);
          if (rowIndex < 0) return null;
          const table = document.getElementById("metrics-workbench-table");
          if (!table) return null;
          const headerCount = table.querySelectorAll(".head").length;
          const start = headerCount + (rowIndex * rowWidth);
          const values = Array.from(table.children)
            .slice(start, start + rowWidth)
            .map((cell) => (cell.textContent || "").trim());
          return values.length === rowWidth ? values : null;
        }""",
        payload,
    )
    assert row is not None
    return row


def _metrics_summary_values(page) -> dict[str, str]:
        return page.evaluate(
                """() => {
                    const values = {};
                    document.querySelectorAll("#metrics-summary-grid .metric-card").forEach((card) => {
                        const label = (card.querySelector("small")?.textContent || "").trim();
                        const value = (card.querySelector("strong")?.textContent || "").trim();
                        if (label) values[label] = value;
                    });
                    return values;
                }"""
        )


def test_metrics_pane_reflects_scoring_workbench_edits_and_restore(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="metrics-scoring-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)

                _activate_tool(page, "scoring")
                page.locator("#scoring-enabled").check()
                page.wait_for_timeout(150)
                _select_scoring_preset_with_penalties(page)
                _open_scoring_workbench(page)

                first_shot_id = page.evaluate("state.timing_segments[0].shot_id")

                _open_metrics_pane(page)
                baseline_metrics_row = _metrics_row_for_shot(page, first_shot_id)

                _open_scoring_workbench(page)
                score_select = page.locator('#scoring-workbench-table select[data-score-field="letter"]').first
                lock_button = page.locator("#scoring-workbench-table .lock-button").first
                lock_button.click()
                score_select.wait_for(state="visible")

                original_letter = score_select.input_value()
                score_values = score_select.evaluate(
                    "select => [...select.options].map((option) => option.value)"
                )
                next_letter = next((value for value in score_values if value != original_letter), original_letter)
                assert next_letter != original_letter

                score_select.select_option(next_letter)
                page.wait_for_timeout(250)
                lock_button.click()

                page.wait_for_function(
                    """({ shotId, expectedLetter }) => {
                      const segment = (state?.timing_segments || []).find((item) => item.shot_id === shotId);
                      return Boolean(segment) && segment.score_letter === expectedLetter;
                    }""",
                    arg={"shotId": first_shot_id, "expectedLetter": next_letter},
                )

                _open_metrics_pane(page)
                updated_metrics_row = _metrics_row_for_shot(page, first_shot_id)
                assert updated_metrics_row[5] == next_letter

                _open_scoring_workbench(page)
                page.locator("#scoring-workbench-table button.restore-button:not(.danger-button)").first.click()
                page.wait_for_function(
                    """({ shotId, originalLetter }) => {
                      const segment = (state?.timing_segments || []).find((item) => item.shot_id === shotId);
                      return Boolean(segment) && segment.score_letter === originalLetter;
                    }""",
                    arg={"shotId": first_shot_id, "originalLetter": original_letter},
                )

                _open_metrics_pane(page)
                restored_metrics_row = _metrics_row_for_shot(page, first_shot_id)
                assert restored_metrics_row[5] == baseline_metrics_row[5]
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_metrics_pane_reflects_timing_event_position_and_delete(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="metrics-timing-event-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_timing_workbench(page)

                first_shot_label = page.evaluate(
                    """() => {
                      const firstShotId = state?.timing_segments?.[0]?.shot_id;
                      const row = (state?.split_rows || []).find((item) => item.shot_id === firstShotId);
                      return row ? row.label : null;
                    }"""
                )
                assert first_shot_label is not None

                page.locator("#timing-event-kind").select_option("custom_label")
                page.locator("#timing-event-label").fill("Manual note")
                option_values = page.locator("#timing-event-position").evaluate(
                    "select => [...select.options].map((option) => option.value).filter(Boolean)"
                )
                assert option_values
                page.locator("#timing-event-position").select_option(option_values[0])

                page.locator("#add-timing-event").click()
                page.wait_for_function(
                    """() => (state?.project?.analysis?.events || []).some((event) => event.label === "Manual note")"""
                )

                _open_metrics_pane(page)
                page.wait_for_function(
                    """(label) => {
                      const table = document.getElementById("metrics-workbench-table");
                      return Boolean(table) && (table.textContent || "").includes(label);
                    }""",
                    arg="Manual note",
                )
                metrics_rows = _metrics_table_rows(page)
                first_shot_index = next(index for index, row in enumerate(metrics_rows) if row[0] == first_shot_label)
                assert "Manual note" in metrics_rows[first_shot_index][-1]

                _open_timing_workbench(page)
                page.locator('button[aria-label="Remove timing event Manual note"]').first.click(force=True)
                page.wait_for_function(
                    """() => !(state?.project?.analysis?.events || []).some((event) => event.label === "Manual note")"""
                )

                _open_metrics_pane(page)
                page.wait_for_function(
                    """(label) => {
                      const table = document.getElementById("metrics-workbench-table");
                      return Boolean(table) && !(table.textContent || "").includes(label);
                    }""",
                    arg="Manual note",
                )
                metrics_rows = _metrics_table_rows(page)
                assert not any("Manual note" in cell for row in metrics_rows for cell in row)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_selected_shot_nudge_and_delete_propagate_to_metrics(synthetic_video_factory) -> None:
    primary_path = Path(synthetic_video_factory(name="metrics-selected-shot-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _activate_tool(page, "timing")

                target_shot_id = page.evaluate("state.timing_segments[1].shot_id")
                page.locator("#timing-table .timeline-segment-cell").nth(1).click()
                page.wait_for_function("(shotId) => selectedShotId === shotId", arg=target_shot_id)

                original_time_ms = page.evaluate(
                    """(shotId) => {
                      const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
                      return shot ? shot.time_ms : null;
                    }""",
                    target_shot_id,
                )
                assert original_time_ms is not None

                _open_metrics_pane(page)
                baseline_metrics_row = _metrics_row_for_shot(page, target_shot_id)
                baseline_summary = _metrics_summary_values(page)

                _activate_tool(page, "timing")
                page.locator('button[data-nudge="10"]').click()
                page.wait_for_function(
                    """({ shotId, originalTime }) => {
                      const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
                      return Boolean(shot) && shot.time_ms === originalTime + 10;
                    }""",
                    arg={"shotId": target_shot_id, "originalTime": original_time_ms},
                )

                _open_metrics_pane(page)
                nudged_metrics_row = _metrics_row_for_shot(page, target_shot_id)
                assert nudged_metrics_row[3] != baseline_metrics_row[3]

                _activate_tool(page, "timing")
                page.locator("#delete-selected").click()
                page.wait_for_function(
                    """(shotId) => !(state?.project?.analysis?.shots || []).some((shot) => shot.id === shotId)""",
                    arg=target_shot_id,
                )
                page.wait_for_function("(shotId) => selectedShotId !== shotId", arg=target_shot_id)

                _open_metrics_pane(page)
                updated_summary = _metrics_summary_values(page)
                assert int(updated_summary["Shots"]) == int(baseline_summary["Shots"]) - 1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_metrics_export_buttons_download_current_metrics_context(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    primary_path = Path(synthetic_video_factory(name="metrics-export-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_timing_workbench(page)

                page.locator("#timing-event-kind").select_option("custom_label")
                page.locator("#timing-event-label").fill("Manual note")
                option_values = page.locator("#timing-event-position").evaluate(
                    "select => [...select.options].map((option) => option.value).filter(Boolean)"
                )
                assert option_values
                page.locator("#timing-event-position").select_option(option_values[0])
                page.locator("#add-timing-event").click()
                page.wait_for_function(
                    """() => (state?.project?.analysis?.events || []).some((event) => event.label === "Manual note")"""
                )

                _open_metrics_pane(page)

                with page.expect_download() as csv_download_info:
                    page.evaluate("document.getElementById('metrics-export-csv').click()")
                csv_download = csv_download_info.value
                csv_target = tmp_path / csv_download.suggested_filename
                csv_download.save_as(str(csv_target))
                csv_text = csv_target.read_text(encoding="utf-8")

                assert csv_download.suggested_filename.endswith("-metrics.csv")
                assert "# per_shot_metrics" in csv_text
                assert "segment_label" in csv_text
                assert "actions" in csv_text
                assert "Manual note" in csv_text

                with page.expect_download() as text_download_info:
                    page.evaluate("document.getElementById('metrics-export-text').click()")
                text_download = text_download_info.value
                text_target = tmp_path / text_download.suggested_filename
                text_download.save_as(str(text_target))
                text_output = text_target.read_text(encoding="utf-8")

                assert text_download.suggested_filename.endswith("-metrics.txt")
                assert "Split Timeline" in text_output
                assert "Manual note" in text_output
                assert "Absolute" in text_output
            finally:
                browser.close()
    finally:
        server.shutdown()