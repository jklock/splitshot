from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tests.browser.helpers.export_verifier import assert_video_file
from tests.browser.helpers.video_test_helpers import (
    ensure_project_with_primary_and_merge,
    navigate_to_tool,
    open_page,
    setup_server_and_browser,
)


@pytest.mark.slow
def test_export_individual_file_exists(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "export-individual.ssproj"
                )
                navigate_to_tool(page, "queue")
                page.wait_for_timeout(300)

                output_path = Path(
                    page.evaluate(
                        """() => {
                            const path = state.project.path + '/export-individual.mp4';
                            callApi('/api/export', { path });
                            return path;
                        }"""
                    )
                )
                tracker.assert_activity("api.export.complete", timeout=180000)
                assert output_path.exists(), f"Export file not found: {output_path}"
                assert_video_file(str(output_path), min_duration_s=0.5)
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.slow
def test_export_combined_file_exists(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "export-combined.ssproj"
                )
                page.evaluate("() => { state.project.merge.enabled = true; }")
                page.evaluate("() => { state.project.merge.layout = 'pip'; }")
                navigate_to_tool(page, "queue")
                page.wait_for_timeout(300)

                output_path = Path(
                    page.evaluate(
                        """() => {
                            const path = state.project.path + '/export-combined.mp4';
                            callApi('/api/export', { path });
                            return path;
                        }"""
                    )
                )
                tracker.assert_activity("api.export.complete", timeout=180000)
                assert output_path.exists(), f"Export file not found: {output_path}"
                assert_video_file(str(output_path), min_duration_s=0.5)
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.slow
def test_export_queue_process_individual(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "export-queue-ind.ssproj"
                )

                stage_id = page.evaluate(
                    "() => new Promise(resolve => { const f = () => { const s = state?.project?.stages?.[0]; if (s) resolve(s.id); else setTimeout(f, 100); }; callApi('/api/project/stage/create', { label: 'Stage 1' }); f(); })"
                )
                assert stage_id, "Stage must be created"

                page.evaluate(
                    "({ sid, p }) => callApi('/api/project/stage/import-primary', { stage_id: sid, path: p })",
                    {"sid": stage_id, "p": str(primary_path)},
                )
                page.wait_for_timeout(300)
                page.evaluate(
                    "(sid) => callApi('/api/project/queue/add', { stage_id: sid })",
                    stage_id,
                )
                page.wait_for_timeout(300)

                page.evaluate(
                    "setTimeout(() => callApi('/api/project/queue/process', { mode: 'individual' }), 0)"
                )
                page.wait_for_function(
                    "() => (state?.project?.queue || []).some(q => q.status === 'complete' || q.status === 'failed')",
                    timeout=300000,
                )
                page.wait_for_timeout(500)

                output_path = page.evaluate(
                    "() => { const e = (state?.project?.queue || []).find(q => q.status === 'complete'); return e?.output_path || null; }"
                )
                assert output_path, "Expected an output path for individual queue export"
                assert_video_file(output_path, min_duration_s=0.5)
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.slow
def test_export_queue_process_combined(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "export-queue-comb.ssproj"
                )
                page.evaluate("() => { state.project.merge.enabled = true; }")
                page.evaluate("() => { state.project.merge.layout = 'pip'; }")

                stage_id = page.evaluate(
                    "() => new Promise(resolve => { const f = () => { const s = state?.project?.stages?.[0]; if (s) resolve(s.id); else setTimeout(f, 100); }; callApi('/api/project/stage/create', { label: 'Stage 1' }); f(); })"
                )
                assert stage_id, "Stage must be created"

                page.evaluate(
                    "({ sid, p }) => callApi('/api/project/stage/import-primary', { stage_id: sid, path: p })",
                    {"sid": stage_id, "p": str(primary_path)},
                )
                page.wait_for_timeout(300)
                page.evaluate(
                    "(sid) => callApi('/api/project/queue/add', { stage_id: sid })",
                    stage_id,
                )
                page.wait_for_timeout(300)

                page.evaluate(
                    "setTimeout(() => callApi('/api/project/queue/process', { mode: 'combined' }), 0)"
                )
                page.wait_for_function(
                    "() => (state?.project?.queue || []).some(q => q.status === 'complete' || q.status === 'failed')",
                    timeout=300000,
                )
                page.wait_for_timeout(1000)

                output_path = page.evaluate(
                    "() => { const e = (state?.project?.queue || []).find(q => q.status === 'complete'); return e?.output_path || null; }"
                )
                assert output_path, "Expected an output path for combined queue export"
                assert_video_file(output_path, min_duration_s=0.5)
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.slow
def test_export_ffprobe_duration_match(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "export-duration.ssproj"
                )
                navigate_to_tool(page, "queue")
                page.wait_for_timeout(300)

                expected_duration = page.evaluate(
                    "() => state?.project?.video_info?.duration ?? null"
                )
                output_path = Path(
                    page.evaluate(
                        """() => {
                            const path = state.project.path + '/export-duration.mp4';
                            callApi('/api/export', { path });
                            return path;
                        }"""
                    )
                )
                tracker.assert_activity("api.export.complete", timeout=180000)
                assert output_path.exists(), f"Export file not found: {output_path}"

                if expected_duration:
                    assert_video_file(
                        str(output_path),
                        expected_duration_s=expected_duration,
                        tolerance_s=expected_duration * 0.5,
                    )
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.slow
def test_export_ffprobe_codec_h264(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(synthetic_video_factory)
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "export-codec.ssproj"
                )
                navigate_to_tool(page, "queue")
                page.wait_for_timeout(300)

                output_path = Path(
                    page.evaluate(
                        """() => {
                            const path = state.project.path + '/export-codec.mp4';
                            callApi('/api/export', { path });
                            return path;
                        }"""
                    )
                )
                tracker.assert_activity("api.export.complete", timeout=180000)
                assert output_path.exists(), f"Export file not found: {output_path}"

                info = assert_video_file(str(output_path), min_duration_s=0.1)
                assert info.get("codec", "").lower() in (
                    "h264",
                    "h.264",
                    "hevc",
                    "libx264",
                    "avc1",
                ), f"Expected H.264, got {info.get('codec', 'unknown')}"
            finally:
                browser.close()
    finally:
        server.shutdown()
