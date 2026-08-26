from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import OverlayTextBox
from splitshot.media.probe import probe_video
from splitshot.ui.controller import ProjectController
from tests.browser.helpers.video_test_helpers import create_project


def _open_page(playwright, server: BrowserControlServer):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def _prepare_stage(page, primary_path: Path, project_path: Path) -> str:
    create_project(page, str(project_path))
    page.evaluate("() => callApi('/api/project/stage/create', {})")
    page.wait_for_function("() => Boolean(state?.project?.active_stage_id)")
    page.evaluate(
        "(path) => callApi('/api/project/stage/import-primary', { stage_id: state.project.active_stage_id, path })",
        str(primary_path),
    )
    page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
    return page.evaluate("state.project.active_stage_id")


IN_OUT_SINGLE_INTERACTION_CASES = [
    ("fade_in_s", "#intro-outro-fade-in", "0.7", 0.7, "number", "fades"),
    ("fade_out_s", "#intro-outro-fade-out", "0.9", 0.9, "number", "fades"),
    ("enabled", '[data-box-field="enabled"]', None, False, "checkbox", "overlay"),
    ("text", '[data-box-field="text"]', "One action", "One action", "text", "overlay"),
    ("quadrant", '[data-box-field="quadrant"]', "custom", "custom", "select", "overlay"),
    ("style_type", '[data-box-field="style_type"]', "rounded", "rounded", "select", "overlay"),
    ("x", '[data-box-field="x"]', "0.22", 0.22, "number", "overlay"),
    ("y", '[data-box-field="y"]', "0.71", 0.71, "number", "overlay"),
    ("width", '[data-box-field="width"]', "321", 321, "number", "overlay"),
    ("height", '[data-box-field="height"]', "97", 97, "number", "overlay"),
    ("font_family", '[data-box-field="font_family"]', "Georgia", "Georgia", "text", "overlay"),
    ("font_size", '[data-box-field="font_size"]', "35", 35, "number", "overlay"),
    (
        "background_color",
        '[data-box-field="background_color"]',
        "#123456",
        "#123456",
        "color",
        "overlay",
    ),
    ("text_color", '[data-box-field="text_color"]', "#abcdef", "#abcdef", "color", "overlay"),
    ("opacity", '[data-box-field="opacity"]', "61", 0.61, "number", "overlay"),
    ("font_bold", '[data-box-field="font_bold"]', None, False, "checkbox", "overlay"),
    ("font_italic", '[data-box-field="font_italic"]', None, True, "checkbox", "overlay"),
]


def _dispatch_one_control_interaction(page, selector: str, value: str | None, kind: str):
    return page.evaluate(
        """({ selector, value, kind }) => {
          const control = document.querySelector(selector);
          if (!(control instanceof HTMLInputElement)
              && !(control instanceof HTMLSelectElement)
              && !(control instanceof HTMLTextAreaElement)) {
            throw new Error(`Control not found: ${selector}`);
          }
          const events = { input: 0, change: 0, click: 0 };
          control.addEventListener('input', () => { events.input += 1; });
          control.addEventListener('change', () => { events.change += 1; });
          control.addEventListener('click', () => { events.click += 1; });
          window.__inOutAuditNode = control;
          window.__inOutAuditEvents = events;
          control.focus();
          if (kind === 'checkbox') {
            control.click();
          } else {
            control.value = String(value);
            if (kind !== 'select') control.dispatchEvent(new Event('input', { bubbles: true }));
            control.dispatchEvent(new Event('change', { bubbles: true }));
          }
          return {
            value: control.type === 'checkbox' ? control.checked : control.value,
            connected: control.isConnected,
            events: { ...events },
          };
        }""",
        {"selector": selector, "value": value, "kind": kind},
    )


def test_queue_pane_membership_and_status_are_visible(synthetic_video_factory) -> None:
    primary = Path(synthetic_video_factory(name="queue-pane-membership", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                stage_id = _prepare_stage(page, primary, primary.parent / "queue-membership.ssproj")
                page.locator("button[data-tool='queue']").click(force=True)
                page.locator(".queue-membership-btn").first.click()
                page.wait_for_function(
                    "(id) => state.project.queue.some((entry) => entry.stage_id === id)",
                    arg=stage_id,
                )
                card = page.locator(f'[data-queue-stage-id="{stage_id}"]')
                assert card.is_visible()
                assert "queued" in card.inner_text().lower()
                assert page.locator("#queue-process-btn").is_visible()
                assert page.locator("#queue-combined-btn").is_visible()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_queue_uses_flat_og_controls_without_apply_settings_ui(synthetic_video_factory) -> None:
    primary = Path(synthetic_video_factory(name="queue-pane-controls", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                stage_id = _prepare_stage(page, primary, primary.parent / "queue-controls.ssproj")
                page.evaluate(
                    "(id) => callApi('/api/project/queue/add', { stage_id: id })", stage_id
                )
                page.locator("button[data-tool='queue']").click(force=True)
                assert page.locator("#queue-apply-all-btn").count() == 0
                assert page.locator("#queue-stage-select").count() == 0
                assert page.get_by_text("Match Stages", exact=True).is_visible()
                assert page.get_by_text("Process", exact=True).is_visible()
                assert page.get_by_role("button", name="Process Queue", exact=True).is_visible()
                assert page.get_by_role(
                    "button", name="Process as One File", exact=True
                ).is_visible()
                assert page.locator(".queue-status-pill").count() == 0
                assert page.locator(".queue-status-text").count() == 1
                assert page.locator(".queue-stage-list").is_visible()
                assert page.locator(".queue-stage-toggle").count() == 0
                assert page.get_by_role("button", name="Show Output Folder").is_enabled()
                assert page.get_by_role("button", name="Show Log").is_visible()
                assert page.locator("#queue-include-intro").is_disabled()
                assert page.locator("#queue-include-outro").is_disabled()
                assert (
                    page.locator("#queue-combined-btn").evaluate(
                        "button => getComputedStyle(button).backgroundColor"
                    )
                    == "rgb(57, 208, 111)"
                )
                assert page.locator("#queue-fade-in").input_value() == "0.5"
                assert page.locator("#queue-fade-out").input_value() == "0.5"
            finally:
                browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize(
    ("field", "selector", "input_value", "expected", "control_kind", "route_kind"),
    IN_OUT_SINGLE_INTERACTION_CASES,
    ids=[case[0] for case in IN_OUT_SINGLE_INTERACTION_CASES],
)
def test_in_out_control_inventory_uses_one_interaction_and_preserves_node(
    synthetic_video_factory,
    tmp_path: Path,
    field: str,
    selector: str,
    input_value: str | None,
    expected,
    control_kind: str,
    route_kind: str,
) -> None:
    intro = Path(synthetic_video_factory(name=f"in-out-single-{field}", beep_ms=250))
    project_path = tmp_path / f"in-out-single-{field}.ssproj"
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                create_project(page, str(project_path))
                page.evaluate(
                    "(path) => callApi('/api/project/in-out/media', { kind: 'intro', path })",
                    str(intro),
                )
                page.evaluate(
                    """() => callApi('/api/project/intro-outro/overlay', {
                      kind: 'intro',
                      text_boxes: [{
                        enabled: true,
                        source: 'manual',
                        text: 'Seed',
                        quadrant: 'top_right',
                        background_color: '#000000',
                        text_color: '#ffffff',
                        opacity: 0.9,
                        font_size: 28,
                        font_bold: true,
                        font_italic: false,
                      }],
                    })"""
                )
                page.locator("button[data-tool='intro-outro']").click(force=True)
                page.wait_for_selector(selector)
                activity_before = server.activity.snapshot()["cursor"]
                primary_node = page.locator(selector).element_handle()
                assert primary_node is not None

                immediate = _dispatch_one_control_interaction(
                    page, selector, input_value, control_kind
                )
                assert immediate["connected"] is True
                if control_kind == "checkbox":
                    assert immediate["events"] == {"input": 1, "change": 1, "click": 1}
                elif control_kind == "select":
                    assert immediate["events"] == {"input": 0, "change": 1, "click": 0}
                else:
                    assert immediate["events"] == {"input": 1, "change": 1, "click": 0}

                second_selector = (
                    "#intro-outro-fade-in"
                    if selector == "#intro-outro-fade-out"
                    else "#intro-outro-fade-out"
                )
                second_value = "1.2" if second_selector.endswith("fade-out") else "1.1"
                second_node = page.locator(second_selector).element_handle()
                assert second_node is not None
                second = _dispatch_one_control_interaction(
                    page, second_selector, second_value, "number"
                )
                assert second == {
                    "value": second_value,
                    "connected": True,
                    "events": {"input": 1, "change": 1, "click": 0},
                }

                if route_kind == "fades":
                    page.wait_for_function(
                        """({ field, expected }) =>
                          Number(state?.project?.intro_clip?.[field]) === Number(expected)""",
                        arg={"field": field, "expected": expected},
                    )
                else:
                    page.wait_for_function(
                        """({ field, expected }) => {
                          const value = state?.project?.intro_clip?.overlay?.text_boxes?.[0]?.[field];
                          return typeof expected === 'number'
                            ? Number(value) === Number(expected)
                            : value === expected;
                        }""",
                        arg={"field": field, "expected": expected},
                    )
                page.wait_for_function(
                    """({ field, expected }) =>
                      Number(state?.project?.intro_clip?.[field]) === Number(expected)""",
                    arg={
                        "field": "fade_out_s"
                        if second_selector.endswith("fade-out")
                        else "fade_in_s",
                        "expected": second_value,
                    },
                )
                page.wait_for_timeout(350)

                assert primary_node.evaluate("element => element.isConnected") is True
                assert second_node.evaluate("element => element.isConnected") is True

                entries = server.activity.snapshot(after_seq=activity_before)["entries"]
                expected_route = (
                    "/api/project/intro-outro/fades"
                    if route_kind == "fades"
                    else "/api/project/intro-outro/overlay"
                )
                expected_route_mutations = 2 if route_kind == "fades" else 1
                assert (
                    len(
                        [
                            entry
                            for entry in entries
                            if entry.get("event") == "api.success"
                            and entry.get("path") == expected_route
                        ]
                    )
                    == expected_route_mutations
                )

                stored = json.loads((project_path / "project.json").read_text(encoding="utf-8"))
                if route_kind == "fades":
                    assert stored["intro_clip"][field] == expected
                else:
                    assert stored["intro_clip"]["overlay"]["text_boxes"][0][field] == expected

                page.locator("button[data-tool='queue']").click(force=True)
                page.locator("button[data-tool='intro-outro']").click(force=True)
                assert page.locator(selector).count() == 1
                page.get_by_role("button", name="Outro", exact=True).click()
                page.get_by_role("button", name="Intro", exact=True).click()
                page.evaluate("path => useProjectFolder(path)", str(project_path))
                page.wait_for_function("() => Boolean(state?.project?.intro_clip?.asset?.path)")
                if route_kind == "fades":
                    assert float(page.locator(selector).input_value()) == expected
                else:
                    reopened = page.locator(selector)
                    if control_kind == "checkbox":
                        assert reopened.is_checked() is expected
                    else:
                        assert reopened.input_value() == str(input_value)
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_intro_outro_match_results_preview_uses_spreadsheet_match_totals() -> None:
    controller = ProjectController()
    source = Path(__file__).resolve().parents[2] / "example_data" / "IDPA" / "IDPA.csv"
    controller.import_practiscore_file(str(source), source_name="IDPA.csv")
    controller.set_practiscore_context(
        competitor_name="John Klockenkemper",
        competitor_place=4,
    )
    controller.project.intro_clip.overlay.text_boxes = [OverlayTextBox(source="match_summary")]
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                page.locator("button[data-tool='intro-outro']").click(force=True)
                assert page.locator(".intro-outro-preview-badge").inner_text().splitlines() == [
                    "Final 83.01",
                    "Points Down 11",
                    "Penalties 2",
                    "Division CO - 2/12",
                    "Class UN - 1/7",
                    "Overall 4/26",
                ]
                labels = page.locator(".intro-outro-metrics .check-row").all_inner_texts()
                assert labels == [
                    "Score / Time",
                    "Raw Time",
                    "Points Down",
                    "Penalties",
                    "Division",
                    "Class",
                    "Overall",
                ]
                match = page.evaluate("state.match_metrics")
                assert match["spreadsheet_authoritative"] is True
                assert match["result_value"] == 83.01
                assert match["points_down"] == 11.0
                assert match["total_penalties"] == 2.0
                csv_lines = page.evaluate("buildMetricsCsv()").splitlines()
                match_section = csv_lines.index("# match_stats")
                headers = csv_lines[match_section + 1].split(",")
                values = csv_lines[match_section + 2].split(",")
                match_row = dict(zip(headers, values, strict=True))
                assert match_row["result_value"] == "83.01"
                assert match_row["points_label"] == "Points Down"
                assert match_row["points_value"] == "11"
                assert match_row["points_down"] == "11"
                assert match_row["penalties"] == "2"
                assert match_row["division"] == "CO"
                assert match_row["division_placement"] == "2/12"
                assert match_row["class"] == "UN"
                assert match_row["class_placement"] == "1/7"
                assert match_row["overall_placement"] == "4/26"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_intro_outro_pane_previews_match_overlay_and_queue_include_choice(
    synthetic_video_factory,
) -> None:
    intro = Path(
        synthetic_video_factory(
            name="intro-pane-preview",
            beep_ms=250,
            duration_ms=5_000,
            resolution=(640, 640),
        )
    )
    outro = Path(
        synthetic_video_factory(
            name="outro-pane-preview",
            beep_ms=300,
            duration_ms=5_000,
            resolution=(360, 640),
        )
    )
    primary = Path(synthetic_video_factory(name="intro-pane-primary", beep_ms=400))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                create_project(page, str(intro.parent / "intro-pane.ssproj"))
                page.locator("#primary-file-input").set_input_files(str(primary))
                page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)")
                page.evaluate(
                    "(path) => callApi('/api/project/in-out/media', { kind: 'intro', path })",
                    str(intro),
                )
                page.evaluate(
                    "() => callApi('/api/project/intro-outro/overlay', { kind: 'intro', text_boxes: [{ enabled: true, source: 'match_summary', summary_metric_ids: ['stage_count'], quadrant: 'top_right', text: '', background_color: '#000000', text_color: '#ffffff', opacity: 0.9, font_size: 28, font_bold: true }] })"
                )
                page.evaluate(
                    "(path) => callApi('/api/project/in-out/media', { kind: 'outro', path })",
                    str(outro),
                )
                page.evaluate(
                    "() => callApi('/api/project/intro-outro/overlay', { kind: 'outro', text_boxes: [{ enabled: true, source: 'match_summary', summary_metric_ids: ['stage_count'], quadrant: 'top_right', text: '', background_color: '#000000', text_color: '#ffffff', opacity: 0.9, font_size: 28, font_bold: true }] })"
                )
                intro_nav = page.locator("button[data-tool='intro-outro']")
                queue_nav = page.locator("button[data-tool='queue']")
                assert intro_nav.inner_text() == "In / Out"
                assert intro_nav.evaluate(
                    "node => node.compareDocumentPosition(document.querySelector(\"button[data-tool='queue']\")) & Node.DOCUMENT_POSITION_FOLLOWING"
                )
                intro_nav.click(force=True)
                page.wait_for_function(
                    "() => document.querySelector('#waveform')?.dataset.boundaryPreview === 'true'"
                )
                assert page.locator("#waveform").get_attribute("data-waveform-samples") == "0"
                assert page.locator("#waveform").get_attribute("data-waveform-lane-count") == "0"
                assert page.locator("#waveform-shot-list").count() == 1
                assert page.locator("#waveform-shot-list").inner_text() == ""
                assert page.get_by_role("heading", name="Intro / Outro", exact=True).is_visible()
                assert page.get_by_role("button", name="Intro", exact=True).is_visible()
                assert page.get_by_role("button", name="Outro", exact=True).is_visible()
                assert page.locator("#intro-outro-fade-in").input_value() == "0.5"
                assert page.locator("#intro-outro-fade-out").input_value() == "0.5"
                page.wait_for_function(
                    "() => document.querySelector('#primary-video')?.readyState >= HTMLMediaElement.HAVE_METADATA"
                )
                video_fit = page.locator("#primary-video").evaluate(
                    """video => ({
                        objectFit: getComputedStyle(video).objectFit,
                        inlinePosition: video.style.position,
                        inlineWidth: video.style.width,
                        videoWidth: video.videoWidth,
                        videoHeight: video.videoHeight,
                        stageClasses: document.getElementById('video-stage').className,
                    })"""
                )
                assert video_fit == {
                    "objectFit": "contain",
                    "inlinePosition": "",
                    "inlineWidth": "",
                    "videoWidth": 640,
                    "videoHeight": 640,
                    "stageClasses": "video-stage",
                }
                page.locator("#primary-video").evaluate("video => { video.currentTime = 1.25; }")
                page.wait_for_function(
                    "() => Math.abs(document.querySelector('#primary-video').currentTime - 1.25) < 0.05"
                )
                source_before_inspector_save = page.locator("#primary-video").get_attribute("src")
                page.locator("#intro-outro-fade-in").fill("0.7")
                page.locator("#intro-outro-fade-in").dispatch_event("change")
                page.wait_for_function("() => state.project.intro_clip.fade_in_s === 0.7")
                assert (
                    page.locator("#primary-video").get_attribute("src")
                    == source_before_inspector_save
                )
                assert (
                    abs(
                        page.locator("#primary-video").evaluate("video => video.currentTime") - 1.25
                    )
                    < 0.05
                )
                page.locator("#intro-outro-fade-out").fill("0.9")
                page.locator("#intro-outro-fade-out").dispatch_event("change")
                page.wait_for_function("() => state.project.intro_clip.fade_out_s === 0.9")
                page.get_by_role("button", name="Outro", exact=True).click()
                page.wait_for_function(
                    "() => document.querySelector('#primary-video')?.src.includes('/media/outro')"
                )
                page.wait_for_function(
                    "() => document.querySelector('#primary-video')?.readyState >= HTMLMediaElement.HAVE_METADATA"
                )
                assert page.locator("#primary-video").is_visible()
                outro_fit = page.locator("#primary-video").evaluate(
                    """video => {
                        const stage = document.getElementById('video-stage').getBoundingClientRect();
                        const overlay = document.getElementById('custom-overlay').getBoundingClientRect();
                        const sourceAspect = video.videoWidth / video.videoHeight;
                        const expectedWidth = Math.min(stage.width, stage.height * sourceAspect);
                        const expectedHeight = expectedWidth / sourceAspect;
                        return {
                            objectFit: getComputedStyle(video).objectFit,
                            inlinePosition: video.style.position,
                            inlineWidth: video.style.width,
                            videoWidth: video.videoWidth,
                            videoHeight: video.videoHeight,
                            overlayWidthDelta: Math.abs(overlay.width - expectedWidth),
                            overlayHeightDelta: Math.abs(overlay.height - expectedHeight),
                            overlayCenterXDelta: Math.abs(
                                (overlay.left + (overlay.width / 2)) - (stage.left + (stage.width / 2))
                            ),
                            overlayCenterYDelta: Math.abs(
                                (overlay.top + (overlay.height / 2)) - (stage.top + (stage.height / 2))
                            ),
                        };
                    }"""
                )
                assert outro_fit["objectFit"] == "contain"
                assert outro_fit["inlinePosition"] == ""
                assert outro_fit["inlineWidth"] == ""
                assert outro_fit["videoWidth"] == 360
                assert outro_fit["videoHeight"] == 640
                assert outro_fit["overlayWidthDelta"] < 2
                assert outro_fit["overlayHeightDelta"] < 2
                assert outro_fit["overlayCenterXDelta"] < 2
                assert outro_fit["overlayCenterYDelta"] < 2
                assert page.locator(".intro-outro-preview-badge").inner_text() == "Stages 1"
                assert page.locator("#intro-outro-fade-in").input_value() == "0.5"
                assert page.locator("#intro-outro-fade-out").input_value() == "0.5"
                page.locator("#intro-outro-fade-in").fill("1.1")
                page.locator("#intro-outro-fade-in").dispatch_event("change")
                page.wait_for_function("() => state.project.outro_clip.fade_in_s === 1.1")
                page.locator("#intro-outro-fade-out").fill("1.3")
                page.locator("#intro-outro-fade-out").dispatch_event("change")
                page.wait_for_function("() => state.project.outro_clip.fade_out_s === 1.3")
                page.get_by_role("button", name="Intro", exact=True).click()
                assert page.locator("#intro-outro-fade-in").input_value() == "0.7"
                assert page.locator("#intro-outro-fade-out").input_value() == "0.9"
                page.wait_for_function(
                    "() => document.querySelector('#primary-video').src.includes('/media/intro')"
                )
                assert page.locator("#primary-video").evaluate(
                    "node => node.dataset.sourcePath === state.project.intro_clip.asset.path"
                )
                assert page.locator(".intro-outro-preview-badge").inner_text() == "Stages 1"
                assert (
                    page.locator(".intro-outro-preview-badge").get_attribute(
                        "data-intro-outro-box-drag"
                    )
                    == "true"
                )
                assert page.get_by_role("button", name="Add Text Box").is_visible()
                assert page.get_by_role("button", name="Add Match Results").is_visible()

                queue_nav.click(force=True)
                page.wait_for_function(
                    "() => document.querySelector('#waveform')?.dataset.boundaryPreview === 'false'"
                )
                page.wait_for_function(
                    "() => document.querySelector('#primary-video').src.includes('/media/primary')"
                )
                assert page.locator("#primary-video").evaluate(
                    "node => node.dataset.sourcePath === state.media.primary_active_path"
                )
                intro_nav.click(force=True)

                card = page.locator(".intro-outro-box").first
                card.locator('[data-box-field="source"]').select_option("manual")
                card.locator('[data-box-field="text"]').fill("Stable intro title")
                card.locator('[data-box-field="text"]').dispatch_event("change")
                card.locator('[data-box-field="quadrant"]').select_option("custom")
                shape_control = card.locator('[data-box-field="style_type"]')
                shape_element = shape_control.element_handle()
                assert shape_element is not None
                shape_control.select_option("rounded")
                card.locator('[data-box-field="x"]').fill("0.21")
                page.wait_for_timeout(300)
                card.locator('[data-box-field="y"]').fill("0.73")
                card.locator('[data-box-field="y"]').dispatch_event("change")
                for field, value in {
                    "width": "320",
                    "height": "96",
                    "font_family": "Arial",
                    "font_size": "34",
                    "opacity": "62",
                }.items():
                    control = card.locator(f'[data-box-field="{field}"]')
                    control.fill(value)
                    control.dispatch_event("change")
                bold_control = card.locator('[data-box-field="font_bold"]')
                italic_control = card.locator('[data-box-field="font_italic"]')
                bold_control.click(force=True)
                assert bold_control.is_checked() is False
                italic_control.click(force=True)
                assert italic_control.is_checked() is True
                page.wait_for_function(
                    """() => {
                        const box = state?.project?.intro_clip?.overlay?.text_boxes?.[0];
                        return box?.text === 'Stable intro title'
                            && box?.quadrant === 'custom'
                            && box?.style_type === 'rounded'
                            && box?.x === 0.21
                            && box?.y === 0.73
                            && box?.width === 320
                            && box?.height === 96
                            && box?.font_size === 34
                            && box?.opacity === 0.62
                            && box?.font_bold === false
                            && box?.font_italic === true;
                    }"""
                )
                page.wait_for_timeout(500)
                assert shape_element.evaluate("element => element.isConnected") is True
                assert card.locator('[data-box-field="text"]').input_value() == "Stable intro title"
                assert card.locator('[data-box-field="x"]').input_value() == "0.21"
                assert card.locator('[data-box-field="y"]').input_value() == "0.73"

                preview_geometry = page.evaluate(
                    """() => {
                        const badge = document.querySelector('.intro-outro-preview-badge');
                        const overlay = document.getElementById('custom-overlay');
                            const media = state.project.intro_clip.asset;
                        const rect = badge.getBoundingClientRect();
                        const frame = overlay.getBoundingClientRect();
                        return {
                            width: rect.width,
                            height: rect.height,
                            expectedWidth: 320 * (frame.width / media.width),
                            expectedHeight: 96 * (frame.height / media.height),
                            opacity: getComputedStyle(badge).opacity,
                            background: getComputedStyle(badge).backgroundColor,
                        };
                    }"""
                )
                assert abs(preview_geometry["width"] - preview_geometry["expectedWidth"]) < 1
                assert abs(preview_geometry["height"] - preview_geometry["expectedHeight"]) < 1
                assert preview_geometry["opacity"] == "1"
                assert preview_geometry["background"] == "rgba(0, 0, 0, 0.62)"

                badge = page.locator(".intro-outro-preview-badge")
                badge_box = badge.bounding_box()
                stage_box = page.locator("#video-stage").bounding_box()
                assert badge_box is not None
                assert stage_box is not None
                page.evaluate(
                    "() => { window.__introDragNode = document.querySelector('.intro-outro-preview-badge'); }"
                )
                drag_x = stage_box["x"] + stage_box["width"] + 40
                drag_y = max(stage_box["y"] + 40, badge_box["y"] - 70)
                page.mouse.move(
                    badge_box["x"] + (badge_box["width"] / 2),
                    badge_box["y"] + (badge_box["height"] / 2),
                )
                page.mouse.down()
                page.mouse.move(drag_x, drag_y, steps=8)
                page.mouse.up()
                page.wait_for_function(
                    """() => {
                        const box = state?.project?.intro_clip?.overlay?.text_boxes?.[0];
                        return box?.quadrant === 'custom' && box?.x !== 0.21 && box?.y !== 0.73;
                    }"""
                )
                assert page.evaluate(
                    """() => ({
                        sameNode: window.__introDragNode === document.querySelector('.intro-outro-preview-badge'),
                        connected: window.__introDragNode?.isConnected,
                        dragging: document.getElementById('custom-overlay')?.classList.contains('dragging'),
                    })"""
                ) == {"sameNode": True, "connected": True, "dragging": False}
                page.locator('[data-boundary-kind="outro"]').click()
                assert page.locator(".intro-outro-kind-tabs .active").inner_text() == "Outro"
                page.locator('[data-boundary-kind="intro"]').click()
                assert page.locator(".intro-outro-kind-tabs .active").inner_text() == "Intro"

                queue_nav.click(force=True)
                assert page.locator("#queue-include-intro").is_enabled()
                assert page.locator("#queue-include-intro").is_checked()
                assert page.locator("#queue-include-outro").is_enabled()
                assert page.locator("#queue-include-outro").is_checked()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_queue_all_files_queues_every_stage_in_one_action(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    project_path = tmp_path / "review-queue-all.ssproj"
    controller.save_project(project_path)
    created_stages = []
    for index in range(1, 4):
        stage = controller.create_stage(f"Stage {index}")
        created_stages.append(stage)
    for index, stage in enumerate(created_stages, start=1):
        stage.primary_media = probe_video(
            Path(synthetic_video_factory(name=f"review-queue-all-{index}"))
        )
    controller.project.active_stage_id = controller.project.stages[0].id
    controller._sync_active_stage_to_project()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                page.locator("button[data-tool='queue']").click(force=True)
                button = page.get_by_role("button", name="Queue All Files", exact=True)
                assert button.is_visible()
                assert button.locator("xpath=..").get_attribute("class") == "queue-process-actions"
                assert button.locator("xpath=..").get_by_role("button").all_inner_texts() == [
                    "Queue All Files",
                    "Process Queue",
                    "Process as One File",
                ]
                assert "btn-secondary" in (button.get_attribute("class") or "")
                queue_grid = button.locator("xpath=..").evaluate(
                    "node => getComputedStyle(node).gridTemplateColumns"
                )
                assert len(queue_grid.split()) == 2
                assert button.evaluate("node => getComputedStyle(node).gridColumnEnd") == "-1"
                page.locator("button[data-tool='review']").click(force=True)
                assert page.get_by_role("button", name="Queue All Files", exact=True).count() == 0
                page.locator("button[data-tool='queue']").click(force=True)
                button.click()
                page.wait_for_function(
                    """() => state?.project?.queue?.length === 3
                        && state.project.queue.every((entry) => entry.status === 'queued')"""
                )
                assert [entry.stage_id for entry in controller.project.queue] == [
                    stage.id for stage in controller.project.stages
                ]
                assert all(entry.snapshot for entry in controller.project.queue)
                saved = json.loads((project_path / "project.json").read_text(encoding="utf-8"))
                assert [entry["stage_id"] for entry in saved["queue"]] == [
                    stage.id for stage in controller.project.stages
                ]
                activity = server.activity.snapshot(after_seq=0, limit=1000)["entries"]
                assert (
                    sum(
                        entry.get("event") == "api.start"
                        and entry.get("path") == "/api/project/queue/add-all"
                        for entry in activity
                    )
                    == 1
                )
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_in_out_video_picker_updates_preview_and_queue_state(
    synthetic_video_factory,
) -> None:
    intro = Path(synthetic_video_factory(name="in-out-picker", beep_ms=250))

    def choose_video(kind: str, current: str | None, default_root: str | None = None) -> str:
        assert kind == "in_out_media"
        return str(intro)

    server = BrowserControlServer(port=0, path_chooser=choose_video)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, server)
            try:
                create_project(page, str(intro.parent / "in-out-picker.ssproj"))
                page.locator("button[data-tool='intro-outro']").click(force=True)
                page.get_by_role("button", name="Select Video", exact=True).click()
                page.wait_for_function("() => Boolean(state?.project?.intro_clip?.asset?.path)")
                assert page.locator(".intro-outro-file").inner_text() == intro.name
                assert "/media/intro" in page.locator("#primary-video").get_attribute("src")
                page.locator("button[data-tool='queue']").click(force=True)
                assert page.locator("#queue-include-intro").is_enabled()
                assert page.locator("#queue-include-intro").is_checked()
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_in_out_video_picker_uses_packaged_native_bridge(
    synthetic_video_factory,
) -> None:
    intro = Path(synthetic_video_factory(name="in-out-native-picker", beep_ms=250))

    def unexpected_browser_picker(
        kind: str, current: str | None, default_root: str | None = None
    ) -> str:
        raise AssertionError(f"Browser path picker should not be used for {kind}")

    server = BrowserControlServer(port=0, path_chooser=unexpected_browser_picker)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.expose_function("pickInOutVideo", lambda: str(intro))
            page.add_init_script(
                "window.splitshot = { openInOutVideoDialog: () => window.pickInOutVideo() };"
            )
            page.goto(server.url, wait_until="domcontentloaded")
            try:
                create_project(page, str(intro.parent / "in-out-native-picker.ssproj"))
                page.locator("button[data-tool='intro-outro']").click(force=True)
                page.get_by_role("button", name="Select Video", exact=True).click()
                page.wait_for_function("() => Boolean(state?.project?.intro_clip?.asset?.path)")
                assert page.locator(".intro-outro-file").inner_text() == intro.name
                assert "/media/intro" in page.locator("#primary-video").get_attribute("src")
            finally:
                browser.close()
    finally:
        server.shutdown()
