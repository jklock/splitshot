from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer


METRICS_ROW_WIDTH = 11


def _open_test_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _load_primary_video(page, primary_path: Path) -> None:
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_path = str(primary_path.parent / "browser-test.ssproj")
        page.evaluate("(path) => createNewProject(path)", project_path)
        page.wait_for_function("() => Boolean(state?.project?.path)")
    page.locator("#primary-file-input").set_input_files(str(primary_path))
    page.locator(".waveform-shot-card").first.wait_for(state="attached")


def _activate_tool(page, tool_id: str) -> None:
    page.locator(f'button[data-tool="{tool_id}"]').click(force=True)
    page.wait_for_timeout(100)
    assert page.evaluate("activeTool") == tool_id


def _select_waveform_shot(page, index: int = 0) -> str:
    _activate_tool(page, "timing")
    target_shot_id = page.evaluate(f"state.timing_segments[{index}].shot_id")
    assert target_shot_id is not None
    waveform_card = page.locator(".waveform-shot-card").nth(index)
    waveform_card.evaluate(
        "(card) => card.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }))"
    )
    page.wait_for_function("(shotId) => selectedShotId === shotId", arg=target_shot_id)
    return str(target_shot_id)


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


def _metrics_graph_snapshot(page) -> list[dict[str, object]]:
    return page.evaluate(
        """() => buildMetricsGraphSeries(buildMetricsRows()).map((graph) => ({
            id: graph.id,
            title: graph.title,
            type: graph.type,
            pointCount: Array.isArray(graph.points) ? graph.points.length : 0,
            barCount: Array.isArray(graph.bars) ? graph.bars.length : 0,
            lineLabels: (graph.lines || []).map((line) => line.label || ''),
            bars: (graph.bars || []).map((bar) => ({
                label: bar.label || '',
                category: bar.category?.label || '',
            })),
            summary: (graph.summary || []).map((item) => ({
                label: item.label || '',
                value: item.value || '',
            })),
        }))"""
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
                score_select = page.locator(
                    '#scoring-workbench-table select[data-score-field="letter"]'
                ).first
                lock_button = page.locator("#scoring-workbench-table .lock-button").first
                lock_button.click()
                score_select.wait_for(state="visible")

                original_letter = score_select.input_value()
                score_values = score_select.evaluate(
                    "select => [...select.options].map((option) => option.value)"
                )
                next_letter = next(
                    (value for value in score_values if value != original_letter), original_letter
                )
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
                page.locator(
                    "#scoring-workbench-table button.restore-button:not(.danger-button)"
                ).first.click()
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
                first_shot_index = next(
                    index for index, row in enumerate(metrics_rows) if row[0] == first_shot_label
                )
                assert "Manual note" in metrics_rows[first_shot_index][-1]

                _open_timing_workbench(page)
                page.locator('button[aria-label="Remove timing event Manual note"]').first.click(
                    force=True
                )
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
                target_shot_id = _select_waveform_shot(page, 1)

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

                _select_waveform_shot(page, 1)
                page.evaluate("() => moveSelectedShot(10)")
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

                _select_waveform_shot(page, 1)
                page.evaluate("() => deleteSelectedShot()")
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


def test_metrics_graphs_show_timeline_intervals_reference_and_segment_story(
    synthetic_video_factory,
) -> None:
    primary_path = Path(synthetic_video_factory(name="metrics-graphs-ui"))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_timing_workbench(page)

                option_values = page.locator("#timing-event-position").evaluate(
                    "select => [...select.options].map((option) => option.value).filter(Boolean)"
                )
                assert option_values
                between_shots_value = next(
                    (
                        value
                        for value in option_values
                        if not value.startswith("::") and not value.endswith("::")
                    ),
                    option_values[0],
                )
                page.locator("#timing-event-kind").select_option("reload")
                page.locator("#timing-event-position").select_option(between_shots_value)
                page.locator("#add-timing-event").click()
                page.wait_for_function(
                    """() => (state?.project?.analysis?.events || []).some((event) => event.kind === 'reload')"""
                )

                _open_metrics_pane(page)
                graph_titles = page.locator(
                    "#metrics-workbench-graphs .metrics-graph-header strong"
                ).all_inner_texts()
                assert "Split Timeline" in graph_titles
                assert "Split Distribution" in graph_titles
                assert "Shooting vs Non-Shooting Time" in graph_titles

                graph_snapshot = _metrics_graph_snapshot(page)
                graph_ids = [graph["id"] for graph in graph_snapshot]
                assert "split_timeline" in graph_ids
                assert "split_distribution" in graph_ids
                assert "shooting_vs_non_shooting" in graph_ids

                timeline_graph = next(
                    graph for graph in graph_snapshot if graph["id"] == "split_timeline"
                )
                assert timeline_graph["type"] == "lines"

                shooting_graph = next(
                    graph for graph in graph_snapshot if graph["id"] == "shooting_vs_non_shooting"
                )
                assert shooting_graph["barCount"] >= 2
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
                assert "# graph_split_timeline" in csv_text
                assert "# graph_split_distribution" in csv_text
                assert "# graph_shooting_vs_non_shooting" in csv_text
                assert "category_id" in csv_text
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
