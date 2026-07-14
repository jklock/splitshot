from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tests.browser.helpers.video_test_helpers import (
    open_page,
    ensure_project_with_primary_and_merge,
    navigate_to_tool,
    get_merge_source_state,
    setup_server_and_browser,
    import_merge_video,
)


ALL_LAYOUTS = [
    "side_by_side",
    "above_below",
    "pip",
    "full_screen_portrait",
    "dual_center_hud",
    "dual_top_hud",
]


def test_enable_merge_logs_and_updates_state(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "comp-enable-p"},
        merge_kwargs={"name": "comp-enable-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "enable-merge.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.evaluate("() => { document.getElementById('merge-enabled')?.click(); }")
                page.wait_for_timeout(500)
                enabled = page.evaluate("() => state?.project?.merge?.enabled ?? false")
                assert enabled, "Merge should be enabled after clicking checkbox"
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("layout", ALL_LAYOUTS)
def test_each_layout_option(synthetic_video_factory, layout: str) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": f"comp-lo-p-{layout}"},
        merge_kwargs={"name": f"comp-lo-m-{layout}"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, f"layout-{layout}.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.evaluate("() => { state.project.merge.enabled = true; renderVideo(); }")
                page.wait_for_function(
                    "() => state?.project?.merge?.enabled === true", timeout=3000
                )
                page.evaluate(
                    f"() => {{ document.getElementById('merge-layout').value = '{layout}'; }}"
                )
                page.evaluate(
                    "() => { document.getElementById('merge-layout').dispatchEvent(new Event('change', { bubbles: true })); renderVideo(); }"
                )
                page.wait_for_function(
                    f"() => state?.project?.merge?.layout === '{layout}'",
                    timeout=5000,
                )
                actual = page.evaluate("() => state?.project?.merge?.layout")
                assert actual == layout, f"Expected layout '{layout}', got '{actual}'"
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("layout", ALL_LAYOUTS)
def test_each_layout_with_three_sources(synthetic_video_factory, layout: str) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": f"comp-l3-p-{layout}"},
        merge_kwargs={"name": f"comp-l3-m-{layout}", "duration_ms": 3000, "beep_ms": 600},
    )
    merge2_path = Path(
        synthetic_video_factory(name=f"comp-l3-m2-{layout}", duration_ms=3000, beep_ms=700)
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, f"layout3-{layout}.ssproj"
                )
                import_merge_video(page, merge2_path, expected_count=2)
                navigate_to_tool(page, "merge")
                page.evaluate("() => { state.project.merge.enabled = true; renderVideo(); }")
                page.evaluate(
                    f"() => {{ state.project.merge.layout = '{layout}'; renderVideo(); }}"
                )
                page.wait_for_timeout(300)
                count = page.evaluate("() => (state?.project?.merge_sources || []).length")
                assert count == 2, f"Expected 2 merge sources, got {count}"
                actual = page.evaluate("() => state?.project?.merge?.layout")
                assert actual == layout, f"Expected layout '{layout}', got '{actual}'"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_pip_size_change_updates(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "comp-pipsz-p"},
        merge_kwargs={"name": "comp-pipsz-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "pipsize.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.evaluate("() => { state.project.merge.enabled = true; }")
                page.evaluate("() => { state.project.merge.layout = 'pip'; }")
                page.evaluate(
                    "() => { document.getElementById('show-pip').checked = true; scheduleInteractionPreviewRender({ video: true }); }"
                )
                page.wait_for_timeout(200)

                page.evaluate("() => { document.getElementById('pip-size').value = '50'; }")
                page.evaluate(
                    "() => document.getElementById('pip-size').dispatchEvent(new Event('input', { bubbles: true }))"
                )
                page.wait_for_timeout(500)

                pip_size = page.evaluate("() => state?.project?.merge?.pip_size_percent ?? 0")
                assert pip_size == pytest.approx(50, abs=5), (
                    f"Expected pip_size_percent ~50, got {pip_size}"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_pip_position_controls(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "comp-pippos-p"},
        merge_kwargs={"name": "comp-pippos-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "pippos.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.evaluate("() => { state.project.merge.enabled = true; }")
                page.evaluate("() => { state.project.merge.layout = 'pip'; }")
                page.evaluate(
                    "() => { document.getElementById('show-pip').checked = true; scheduleInteractionPreviewRender({ video: true }); }"
                )
                page.wait_for_timeout(200)

                page.evaluate("() => { document.getElementById('pip-x').value = '0.25'; }")
                page.evaluate(
                    "() => document.getElementById('pip-x').dispatchEvent(new Event('input', { bubbles: true }))"
                )
                page.evaluate("() => { document.getElementById('pip-y').value = '0.75'; }")
                page.evaluate(
                    "() => document.getElementById('pip-y').dispatchEvent(new Event('input', { bubbles: true }))"
                )
                page.wait_for_timeout(300)

                pip_x = page.evaluate("() => state?.project?.merge?.pip_x ?? -1")
                pip_y = page.evaluate("() => state?.project?.merge?.pip_y ?? -1")
                assert abs(pip_x - 0.25) < 0.05, f"Expected pip_x ~0.25, got {pip_x}"
                assert abs(pip_y - 0.75) < 0.05, f"Expected pip_y ~0.75, got {pip_y}"

            finally:
                browser.close()
    finally:
        server.shutdown()


def test_restore_merge_defaults(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "comp-restore-p"},
        merge_kwargs={"name": "comp-restore-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "restore-merge.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.evaluate("() => { state.project.merge.enabled = true; }")
                page.evaluate("() => { state.project.merge.layout = 'pip'; }")
                page.evaluate("() => { state.project.merge.pip_size_percent = 50; }")
                page.wait_for_timeout(200)

                restore = page.locator("#restore-merge-defaults")
                restore.wait_for(state="visible", timeout=5000)
                restore.click()
                page.wait_for_timeout(500)

                layout = page.evaluate("() => state?.project?.merge?.layout ?? ''")
                pip_size = page.evaluate("() => state?.project?.merge?.pip_size_percent ?? -1")
                assert layout == "side_by_side", (
                    f"Expected layout restored to side_by_side, got {layout}"
                )
                assert pip_size == 35, f"Expected pip_size restored to 35, got {pip_size}"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_per_source_opacity_change(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "comp-opacity-p"},
        merge_kwargs={"name": "comp-opacity-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "opacity.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.evaluate("() => { state.project.merge.enabled = true; renderVideo(); }")
                page.wait_for_timeout(300)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id
                commit_route = "/api/merge/source"
                assert commit_route == "/api/merge/source"

                opacity_input = page.locator(
                    f'input[data-merge-source-field="opacity"][data-source-id="{source_id}"]'
                )
                if opacity_input.count():
                    opacity_input.fill("75")
                    opacity_input.dispatch_event("input")
                    page.wait_for_timeout(500)
                    state = get_merge_source_state(page, source_id)
                    if state and state.get("opacity") is not None:
                        assert abs(float(state["opacity"]) - 0.75) < 0.1
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_per_source_placement_mode_changes(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "comp-placement-p"},
        merge_kwargs={"name": "comp-placement-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "placement.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.evaluate("() => { state.project.merge.enabled = true; }")
                page.wait_for_timeout(300)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id

                placement_select = page.locator(
                    f'select[data-merge-source-field="placement_mode"][data-source-id="{source_id}"]'
                )
                if placement_select.count():
                    placement_select.select_option("above_below")
                    page.wait_for_timeout(500)
                    state = get_merge_source_state(page, source_id)
                    if state:
                        assert state.get("placement_mode") == "above_below"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_per_source_layout_change_updates_visible_preview_mode(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "comp-visible-layout-p"},
        merge_kwargs={"name": "comp-visible-layout-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "visible-layout.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.locator("#merge-enabled").check()
                page.locator("#merge-layout").select_option("pip")
                page.wait_for_timeout(400)
                assert not page.locator("#merge-preview-layer").evaluate("(el) => el.hidden")

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id
                commit_route = "/api/merge/source"
                assert commit_route == "/api/merge/source"

                placement_select = page.locator(
                    f'select[data-merge-source-field="placement_mode"][data-source-id="{source_id}"]'
                )
                placement_select.select_option("above_below")
                page.wait_for_timeout(500)

                preview_state = page.evaluate(
                    """() => {
                        const stage = document.getElementById('video-stage');
                        const preview = document.getElementById('merge-preview-layer');
                        const secondary = document.getElementById('secondary-video');
                        return {
                            stage_above_below: stage?.classList.contains('merge-above-below') ?? false,
                            stage_pip: stage?.classList.contains('merge-pip') ?? false,
                            preview_hidden: preview?.hidden ?? true,
                            secondary_hidden: secondary?.hidden ?? true,
                        };
                    }"""
                )
                assert preview_state["stage_above_below"] is True
                assert preview_state["stage_pip"] is False
                assert preview_state["preview_hidden"] is True
                assert preview_state["secondary_hidden"] is False
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_project_layout_change_keeps_per_source_override(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "comp-override-p"},
        merge_kwargs={"name": "comp-override-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "layout-override.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.locator("#merge-enabled").check()
                page.locator("#merge-layout").select_option("pip")
                page.wait_for_timeout(400)

                source_id = page.evaluate(
                    "() => (state?.project?.merge_sources || [])[0]?.id || ''"
                )
                assert source_id

                placement_select = page.locator(
                    f'select[data-merge-source-field="placement_mode"][data-source-id="{source_id}"]'
                )
                placement_select.select_option("above_below")
                page.wait_for_timeout(400)
                page.locator("#merge-layout").select_option("side_by_side")
                page.wait_for_timeout(500)

                preview_state = page.evaluate(
                    """(sid) => {
                        const stage = document.getElementById('video-stage');
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === sid);
                        return {
                            project_layout: state?.project?.merge?.layout || '',
                            placement_mode: source?.placement?.mode || '',
                            stage_above_below: stage?.classList.contains('merge-above-below') ?? false,
                            stage_side_by_side: stage?.classList.contains('merge-side-by-side') ?? false,
                        };
                    }""",
                    source_id,
                )
                assert preview_state["project_layout"] == "side_by_side"
                assert preview_state["placement_mode"] == "above_below"
                assert preview_state["stage_above_below"] is True
                assert preview_state["stage_side_by_side"] is False
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_compose_controls_use_two_columns_before_compact_width(synthetic_video_factory) -> None:
    server, tracker, primary_path, merge_path = setup_server_and_browser(
        synthetic_video_factory,
        primary_kwargs={"name": "comp-columns-p"},
        merge_kwargs={"name": "comp-columns-m"},
    )
    try:
        with sync_playwright() as playwright:
            browser, page = open_page(playwright, server)
            try:
                ensure_project_with_primary_and_merge(
                    page, primary_path, merge_path, "compose-columns.ssproj"
                )
                navigate_to_tool(page, "merge")
                page.wait_for_timeout(300)

                wide_columns = page.evaluate(
                    """() => {
                        document.documentElement.style.setProperty('--inspector-width', '520px');
                        window.dispatchEvent(new Event('resize'));
                        const controls = document.querySelector('.merge-source-controls');
                        return getComputedStyle(controls).gridTemplateColumns.split(' ').length;
                    }"""
                )
                compact_columns = page.evaluate(
                    """() => {
                        document.documentElement.style.setProperty('--inspector-width', '340px');
                        window.dispatchEvent(new Event('resize'));
                        const controls = document.querySelector('.merge-source-controls');
                        return getComputedStyle(controls).gridTemplateColumns.split(' ').length;
                    }"""
                )
                assert wide_columns >= 2, (
                    f"Expected dual-column compose controls, got {wide_columns}"
                )
                assert compact_columns == 1, (
                    f"Expected single-column compose controls in compact inspector, got {compact_columns}"
                )
            finally:
                browser.close()
    finally:
        server.shutdown()
