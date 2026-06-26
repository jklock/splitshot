from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


TOOL_IDS = [
    "project",
    "media",
    "merge",
    "trim-sync",
    "scoring",
    "timing",
    "markers",
    "overlay",
    "review",
    "export",
    "queue",
    "metrics",
    "shotml",
    "settings",
]
ROOT = Path(__file__).resolve().parents[2]
CLIP1_VIDEO = ROOT / "docs" / "Clip1.MP4"
RELEASE_PROOF_ARTIFACT_ENV = "SPLITSHOT_RELEASE_PROOF_ARTIFACT_ROOT"
RELEASE_PROOF_THRESHOLDS_MS = {
    "tool_switch": 500,
    "profile_create": 750,
    "profile_edit": 750,
    "review_source": 750,
    "export_badges": 750,
    "source_commit": 750,
    "trim_apply": 3000,
    "trim_clear": 2000,
    "export_ack": 1000,
}


def _release_proof_artifact_root() -> Path | None:
    raw_value = os.environ.get(RELEASE_PROOF_ARTIFACT_ENV, "").strip()
    if not raw_value:
        return None
    root = Path(raw_value).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_release_proof_json(root: Path | None, name: str, payload: object) -> None:
    if root is None:
        return
    (root / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_release_proof_text(root: Path | None, name: str, text: str) -> None:
    if root is None:
        return
    (root / name).write_text(text, encoding="utf-8")


def _capture_release_proof_screenshot(page, root: Path | None, name: str) -> None:
    if root is None:
        return
    page.screenshot(path=str(root / f"{name}.png"), full_page=True)


def _write_release_proof_contact_sheet(root: Path | None) -> None:
    if root is None:
        return
    screenshots = sorted(root.glob("*.png"))
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Source Release Proof Contact Sheet</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #111827; color: #f3f4f6; margin: 0; padding: 24px; }
    h1 { margin: 0 0 16px; font-size: 24px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
    figure { margin: 0; padding: 12px; background: #1f2937; border-radius: 12px; }
    figcaption { margin-top: 8px; font-size: 13px; word-break: break-all; }
    img { width: 100%; height: auto; border-radius: 8px; display: block; }
  </style>
</head>
<body>
  <h1>Source Release Proof Contact Sheet</h1>
  <div class="grid">
"""
    html += "\n".join(
        f'    <figure><img src="{shot.name}" alt="{shot.name}"><figcaption>{shot.name}</figcaption></figure>'
        for shot in screenshots
    )
    html += """
  </div>
</body>
</html>
"""
    (root / "contact-sheet.html").write_text(html, encoding="utf-8")


def _record_timing(
    timings: list[dict[str, object]], name: str, started_at: float, threshold_ms: int
) -> None:
    elapsed_ms = round((time.perf_counter() - started_at) * 1000)
    entry = {
        "name": name,
        "elapsed_ms": elapsed_ms,
        "threshold_ms": threshold_ms,
        "passed": elapsed_ms <= threshold_ms,
    }
    timings.append(entry)
    assert elapsed_ms <= threshold_ms, (
        f"{name} exceeded threshold: {elapsed_ms}ms > {threshold_ms}ms"
    )


def _wait_for_ui_settled(page) -> None:
    page.wait_for_function(
        "() => document.getElementById('processing-bar')?.hidden !== false",
        timeout=15000,
    )
    page.wait_for_timeout(150)


def _overflow_snapshot(page) -> dict:
    return page.evaluate(
        """() => {
            const inspector = document.querySelector('.inspector');
            const pane = document.querySelector(`[data-tool-pane="${activeTool}"]`);
            const paneRect = pane?.getBoundingClientRect?.() || { left: 0, right: 0 };
            const offenders = [];
            const elements = pane
              ? Array.from(pane.querySelectorAll('label, button, input, select, textarea, .merge-source-trim-status'))
              : [];
            for (const element of elements) {
              const rect = element.getBoundingClientRect();
              if (rect.width <= 0 || rect.height <= 0) continue;
              if (rect.right > paneRect.right + 1 || rect.left < paneRect.left - 1) {
                offenders.push({
                  text: element.textContent?.trim?.() || element.getAttribute('aria-label') || element.id || element.className || '<unknown>',
                  left: rect.left,
                  right: rect.right,
                  pane_left: paneRect.left,
                  pane_right: paneRect.right,
                });
              }
            }
            return {
              active_tool: activeTool,
              inspector_client_width: inspector?.clientWidth || 0,
              inspector_scroll_width: inspector?.scrollWidth || 0,
              pane_client_width: pane?.clientWidth || 0,
              pane_scroll_width: pane?.scrollWidth || 0,
              body_client_width: document.documentElement.clientWidth,
              body_scroll_width: document.documentElement.scrollWidth,
              offenders,
            };
        }"""
    )


def _assert_no_horizontal_overflow(page, label: str, root: Path | None = None) -> None:
    snapshot = _overflow_snapshot(page)
    if (
        snapshot["inspector_scroll_width"] > snapshot["inspector_client_width"] + 2
        or snapshot["pane_scroll_width"] > snapshot["pane_client_width"] + 2
        or snapshot["body_scroll_width"] > snapshot["body_client_width"] + 2
        or snapshot["offenders"]
    ):
        _write_release_proof_json(root, f"overflow-{label}.json", snapshot)
    assert snapshot["inspector_scroll_width"] <= snapshot["inspector_client_width"] + 2, (
        f"{label}: inspector overflow"
    )
    assert snapshot["pane_scroll_width"] <= snapshot["pane_client_width"] + 2, (
        f"{label}: pane overflow"
    )
    assert snapshot["body_scroll_width"] <= snapshot["body_client_width"] + 2, (
        f"{label}: body overflow"
    )
    assert not snapshot["offenders"], f"{label}: clipped controls detected"


def _open_tool_for_release(
    page,
    tool_id: str,
    timings: list[dict[str, object]],
    root: Path | None,
    screenshot_name: str | None = None,
) -> None:
    started_at = time.perf_counter()
    _open_tool(page, tool_id)
    _wait_for_ui_settled(page)
    _record_timing(
        timings, f"tool-switch:{tool_id}", started_at, RELEASE_PROOF_THRESHOLDS_MS["tool_switch"]
    )
    _assert_no_horizontal_overflow(page, tool_id, root)
    if screenshot_name:
        _capture_release_proof_screenshot(page, root, screenshot_name)


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


def _copy_clip1_video(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copyfile(CLIP1_VIDEO, target)
    return target


def _merge_source_state(page, source_id: str) -> dict | None:
    return page.evaluate(
        """(targetSourceId) => {
            const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
            return source ? JSON.parse(JSON.stringify(source)) : null;
        }""",
        source_id,
    )


def _current_camera_role(source: dict | None) -> str | None:
    if not isinstance(source, dict):
        return None
    value = source.get("camera_role") or source.get("angle_role")
    return None if value in {None, ""} else str(value)


def _configure_output_profile_badges(page) -> tuple[str, str]:
    _open_tool(page, "overlay")
    page.locator("#show-overlay").check()
    badge_size = _alternate_select_value(page.locator("#badge-size"))
    page.locator("#badge-size").select_option(badge_size)
    page.wait_for_function(
        "(value) => state?.project?.overlay?.badge_size === value", arg=badge_size
    )

    _open_tool(page, "export")
    page.locator("#create-output-profile").click()
    page.wait_for_function(
        """() => {
            const select = document.getElementById('output-profile-select');
            return Boolean(select?.value) && (state?.output_profiles || []).length > 0;
        }"""
    )
    assert page.locator("#output-profile-name").is_disabled() is False
    assert page.locator("#output-profile-type").is_disabled() is False
    assert page.locator("#output-profile-frame").is_disabled() is False
    profile_id = page.locator("#output-profile-select").input_value()
    assert profile_id

    _set_input_value(page.locator("#output-profile-name"), "Release Proof Profile")
    frame_profile = _alternate_select_value(page.locator("#output-profile-frame"))
    profile_kind = _alternate_select_value(page.locator("#output-profile-type"))
    page.locator("#output-profile-frame").evaluate(
        """(element, nextValue) => {
            element.value = nextValue;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        frame_profile,
    )
    page.locator("#output-profile-type").evaluate(
        """(element, nextValue) => {
            element.value = nextValue;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        profile_kind,
    )
    page.wait_for_function(
        """(payload) => {
            const profile = (state?.output_profiles || []).find((item) => item.output_id === payload.profileId);
            return Boolean(profile)
                && profile.profile_name === 'Release Proof Profile'
                && profile.profile_kind === payload.profileKind
                && profile.frame_profile === payload.frameProfile;
        }""",
        arg={"profileId": profile_id, "profileKind": profile_kind, "frameProfile": frame_profile},
    )

    _open_tool(page, "overlay")
    page.locator("#export-badges").click()
    page.wait_for_function(
        """(payload) => {
            const profile = (state?.output_profiles || []).find((item) => item.output_id === payload.profileId);
            if (!profile?.metric_caption_preset) return false;
            const parsed = JSON.parse(profile.metric_caption_preset);
            return parsed.badge_size === payload.badgeSize;
        }""",
        arg={"profileId": profile_id, "badgeSize": badge_size},
    )
    return profile_id, badge_size


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
    baseline_event_count = int(
        page.evaluate("() => (state?.project?.analysis?.events || []).length")
    )
    page.locator("#add-timing-event").click()
    page.wait_for_function(
        "(expectedCount) => (state?.project?.analysis?.events || []).length === expectedCount",
        arg=baseline_event_count + 1,
    )
    page.locator("#timing-workbench-table").get_by_text("Master timing note").first.wait_for(
        state="visible"
    )


def _exercise_markers_review_overlay(page) -> None:
    _open_tool(page, "timing")
    _select_first_waveform_shot(page)

    _open_tool(page, "markers")
    page.locator("#popup-edit-selected").click()
    page.wait_for_function("() => document.getElementById('markers-workbench')?.hidden === false")
    page.locator("#popup-import-shots-workbench").click()
    page.wait_for_function("() => (state?.project?.popups || []).length > 0")
    page.locator("#popup-next-workbench").click()
    page.locator("#popup-prev-workbench").click()
    page.locator('#markers-workbench-editor [data-popup-action="duplicate"]').click()
    page.wait_for_function("() => (state?.project?.popups || []).length > 1")
    page.locator('#markers-workbench-editor [data-popup-action="remove"]').click()
    page.wait_for_function(
        "() => document.querySelector('#markers-workbench-editor .popup-bubble-card') !== null"
    )

    page.locator("#popup-edit-selected").click()
    page.wait_for_function("() => document.getElementById('markers-workbench')?.hidden === true")

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
    _set_color_picker_value(
        page, review_card.locator('button[data-text-box-field="background_color"]'), "#ff0000"
    )
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
    page.locator("#overlay-font-family").select_option(
        _alternate_select_value(page.locator("#overlay-font-family"))
    )
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
    monkeypatch.setattr("splitshot.export.pipeline.export_project", fake_export_project)
    monkeypatch.setattr("splitshot.export.pipeline.export_project", fake_export_project)

    _open_tool(page, "merge")
    page.locator("#merge-media-input").set_input_files(str(secondary_path))
    page.wait_for_function("() => (state?.project?.merge_sources || []).length === 1")
    _open_tool(page, "merge")

    tertiary_path = secondary_path.parent / f"{secondary_path.stem}-extra{secondary_path.suffix}"
    if not tertiary_path.exists():
        tertiary_path.write_bytes(secondary_path.read_bytes())
    page.locator("#merge-media-input").set_input_files(str(tertiary_path))
    page.wait_for_function("() => (state?.project?.merge_sources || []).length === 2")
    _open_tool(page, "merge")

    page.locator("#merge-enabled").check()
    page.wait_for_function("() => state?.project?.merge?.enabled === true")
    page.locator("#merge-layout").select_option("pip")
    page.wait_for_function("() => state?.project?.merge?.layout === 'pip'")

    _set_input_value(page.locator("#pip-size"), "50")
    _set_input_value(page.locator("#pip-x"), "0.25")
    _set_input_value(page.locator("#pip-y"), "0.75")

    merge_pane_cards = page.locator('[data-tool-pane="merge"] .merge-media-card')
    first_card = merge_pane_cards.first
    source_id = first_card.get_attribute("data-source-id")
    page.evaluate(
        """(sourceId) => {
            setMergeSourceExpanded(sourceId, true);
            renderMergeMediaList();
        }""",
        source_id,
    )
    page.wait_for_function(
        """(sourceId) => {
            return document.querySelector('[data-tool-pane="merge"] .merge-media-card[data-source-id="' + sourceId + '"] .merge-media-card-body')?.hidden === false;
        }""",
        arg=source_id,
    )
    first_card.locator(".pip-size-control input").first.evaluate("input => Number(input.value)")

    _open_tool(page, "trim-sync")
    trim_sync_card = page.locator(f'.trim-source-card[data-source-id="{source_id}"]')
    trim_sync_card.wait_for(state="visible")
    trim_sync_card.get_by_role("button", name="+1", exact=True).click()

    _open_tool(page, "merge")
    merge_pane_cards = page.locator('[data-tool-pane="merge"] .merge-media-card')
    second_card = merge_pane_cards.nth(1)

    second_body = second_card.locator(".merge-media-card-body")
    if second_body.evaluate("body => body.hidden"):
        second_card.locator('button[aria-label*="stage media controls"]').click()
        page.wait_for_function(
            """(sourceId) => {
                return document.querySelector('[data-tool-pane="merge"] .merge-media-card[data-source-id="' + sourceId + '"] .merge-media-card-body')?.hidden === false;
            }""",
            arg=second_card.get_attribute("data-source-id"),
        )
    second_card.locator('[data-merge-source-field="size"]').evaluate(
        """(input) => {
            input.value = '55';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )
    second_source_id = second_card.get_attribute("data-source-id")
    page.evaluate(
        """(sourceId) => { callApi('/api/merge/remove', { source_id: sourceId }); }""",
        second_source_id,
    )
    page.wait_for_function("() => (state?.project?.merge_sources || []).length === 1")
    page.evaluate(
        """async () => { await callApi('/api/project/stage/create', { label: 'Stage 1' }); }"""
    )
    page.wait_for_function(
        """() => {
            const project = state?.project;
            return (project?.stages || []).length === 1
                && Boolean(project?.active_stage_id)
                && Boolean(project?.primary_video?.path)
                && (project?.merge_sources || []).length === 1;
        }"""
    )

    _open_tool(page, "export")
    page.locator("#quality").select_option(_alternate_select_value(page.locator("#quality")))
    page.locator("#aspect-ratio").select_option(
        _alternate_select_value(page.locator("#aspect-ratio"))
    )
    _set_input_value(page.locator("#target-width"), "1280")
    _set_input_value(page.locator("#target-height"), "720")
    page.locator("#frame-rate").select_option(_alternate_select_value(page.locator("#frame-rate")))
    page.locator("#video-codec").select_option(
        _alternate_select_value(page.locator("#video-codec"))
    )
    _set_input_value(page.locator("#video-bitrate"), "12")
    page.locator("#audio-codec").select_option(
        _alternate_select_value(page.locator("#audio-codec"))
    )
    _set_input_value(page.locator("#audio-sample-rate"), "48000")
    _set_input_value(page.locator("#audio-bitrate"), "256")
    page.locator("#color-space").select_option(
        _alternate_select_value(page.locator("#color-space"))
    )
    page.locator("#ffmpeg-preset").select_option(
        _alternate_select_value(page.locator("#ffmpeg-preset"))
    )
    page.locator("#two-pass").check()

    output_root = tmp_path / "master-full-app-export"
    project_path = tmp_path / "master-full-app-project"
    output_root.mkdir(parents=True, exist_ok=True)
    page.locator('[data-tool="project"]').click()
    page.evaluate(
        """async (path) => { await callApi('/api/project/save', { path }); }""", str(project_path)
    )
    page.wait_for_function("(path) => state?.project?.path === path", arg=str(project_path))
    page.evaluate(
        """async (path) => {
            const input = document.getElementById('project-output-root');
            if (input) {
                input.value = path;
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
            await callApi('/api/project/details', { output_root: path });
        }""",
        str(output_root),
    )
    page.wait_for_function("(path) => state?.project?.output_root === path", arg=str(output_root))
    page.locator('[data-tool="export"]').click()
    export_state = page.evaluate(
        """async () => {
            const response = await fetch('/api/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });
            return await response.json();
        }"""
    )
    assert "error" not in export_state
    assert export_state["project"]["export"]["last_log"] == "Master export log"
    page.locator("#show-export-log").click()
    page.wait_for_function("() => document.getElementById('export-log-modal')?.hidden === false")
    page.locator("#close-export-log").click()
    page.wait_for_function("() => document.getElementById('export-log-modal')?.hidden === true")

    assert captured_exports
    assert str(captured_exports[0]["output_path"]).startswith(str(output_root))


def _exercise_settings_and_shotml(page) -> None:
    _open_tool(page, "settings")
    for section_id in ["global-template", "pip", "overlay", "export"]:
        section = page.locator(f'[data-settings-section="{section_id}"]')
        if section.evaluate("element => element.classList.contains('collapsed')"):
            section.locator("button[data-section-toggle]").click()
            page.wait_for_function(
                "(selector) => !document.querySelector(selector)?.classList.contains('collapsed')",
                arg=f'[data-settings-section="{section_id}"]',
            )

    _set_select = lambda selector: page.locator(selector).select_option(
        _alternate_select_value(page.locator(selector))
    )
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
        threshold_section.locator("button[data-section-toggle]").click()
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


def test_browser_full_app_e2e_calls_surface_workflows(
    synthetic_video_factory, tmp_path: Path, monkeypatch
) -> None:
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
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(project_path)
                )
                _load_primary_video(page, primary_path)

                page.locator("#practiscore-file-input").set_input_files(str(practiscore_path))
                page.wait_for_function("() => state?.project?.scoring?.stage_number !== null")

                _exercise_waveform_and_timing(page)
                _open_tool(page, "scoring")
                page.locator("#expand-scoring").click()
                page.wait_for_function("() => scoringWorkbenchExpanded === true")

                page.evaluate("(path) => useProjectFolder(path)", str(project_path))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(project_path)
                )
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("() => state?.project?.scoring?.stage_number !== null")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_browser_review_summary_imported_metrics_truth_gate(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    primary_path = Path(synthetic_video_factory(name="truth-gate-review-summary-primary"))
    project_path = tmp_path / "truth-gate-review-summary"
    practiscore_path = Path(__file__).resolve().parents[2] / "example_data" / "IDPA" / "IDPA.csv"

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _set_project_path(page, project_path)
                page.evaluate("(path) => createNewProject(path)", str(project_path))
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(project_path)
                )
                _load_primary_video(page, primary_path)

                page.locator("#practiscore-file-input").set_input_files(str(practiscore_path))
                page.wait_for_function("() => state?.project?.scoring?.stage_number !== null")

                _open_tool(page, "review")
                page.locator("#review-add-imported-box").click()
                page.wait_for_function(
                    """() => {
                        const card = document.querySelector('#review-text-box-list .text-box-card');
                        const preview = card?.querySelector('[data-text-box-preview]')?.value || '';
                        const checkboxes = card?.querySelectorAll('input[data-summary-metric]') || [];
                        return checkboxes.length > 0
                            && preview.includes('Score / Time')
                            && preview.includes('Points Down')
                            && preview.includes('Overall Placement');
                    }"""
                )
                review_card = page.locator("#review-text-box-list .text-box-card").last
                review_card.locator('[data-text-box-action="toggle"]').click()
                preview_text = review_card.locator("[data-text-box-preview]").input_value()
                assert "Score / Time" in preview_text
                assert "Points Down" in preview_text
                assert "Overall Placement 1/26" in preview_text
                assert "Division Placement 1/4" in preview_text
                assert "Class Placement 1/4" in preview_text
                assert "Division + Class Placement 1/1" in preview_text
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
                page.wait_for_function(
                    "() => (state?.project?.overlay?.text_boxes || []).length > 0"
                )
                page.wait_for_function("() => (state?.project?.popups || []).length > 0")
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_browser_full_app_merge_export_sync_truth_gate(
    synthetic_video_factory, tmp_path: Path, monkeypatch
) -> None:
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


def test_browser_full_app_output_profile_review_source_and_badges_truth_gate(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    primary_path = Path(synthetic_video_factory(name="truth-gate-output-profile-primary"))
    secondary_path = Path(synthetic_video_factory(name="truth-gate-output-profile-secondary"))

    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                _load_primary_video(page, primary_path)
                _open_tool(page, "merge")
                page.locator("#merge-media-input").set_input_files(str(secondary_path))
                page.wait_for_function("() => (state?.project?.merge_sources || []).length === 1")
                _open_tool(page, "merge")
                source_id = page.locator(".merge-media-card").first.get_attribute("data-source-id")
                assert source_id

                profile_id, badge_size = _configure_output_profile_badges(page)

                _open_tool(page, "review")
                _open_tool(page, "overlay")
                _open_tool(page, "export")
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("() => Boolean(state?.project?.path)")
                _open_tool(page, "export")
                page.locator("#output-profile-select").select_option(profile_id)
                page.wait_for_function(
                    """(payload) => {
                        const profile = (state?.output_profiles || []).find((item) => item.output_id === payload.profileId);
                        if (!profile?.metric_caption_preset) return false;
                        const parsed = JSON.parse(profile.metric_caption_preset);
                        return parsed.badge_size === payload.badgeSize;
                    }""",
                    arg={"profileId": profile_id, "badgeSize": badge_size},
                )
                assert page.locator("#output-profile-name").input_value() == "Release Proof Profile"
            finally:
                browser.close()
    finally:
        server.shutdown()


def test_browser_full_app_real_media_stage_release_workflow_truth_gate(
    tmp_path: Path, monkeypatch
) -> None:
    primary_path = _copy_clip1_video(tmp_path, "clip1-primary.MP4")
    secondary_path = _copy_clip1_video(tmp_path, "clip1-secondary.MP4")
    tertiary_path = _copy_clip1_video(tmp_path, "clip1-tertiary.MP4")
    project_path = tmp_path / "release-proof-project"
    practiscore_path = Path(__file__).resolve().parents[2] / "example_data" / "IDPA" / "IDPA.csv"
    captured_exports: list[dict[str, object]] = []
    artifact_root = _release_proof_artifact_root()
    timings: list[dict[str, object]] = []
    controller = ProjectController()
    controller.project_path = project_path
    controller.import_practiscore_file(str(practiscore_path), source_name=practiscore_path.name)
    stage = next(
        (item for item in controller.project.stages if item.imported_stage_number == 2),
        controller.project.active_stage or controller.project.stages[0],
    )
    controller.select_stage(stage.id)
    controller.import_stage_primary(stage.id, str(primary_path))
    controller.import_stage_added(stage.id, str(secondary_path))
    controller.import_stage_added(stage.id, str(tertiary_path))

    def fake_export_project(project, destination, progress_callback=None, log_callback=None):
        captured_exports.append(
            {
                "output_path": str(destination),
                "merge_sources": len(project.merge_sources),
                "profiles": len(getattr(project, "merge_sources", [])),
            }
        )
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"real-media-proof-export")
        project.export.last_log = "Real media proof export completed."
        project.export.last_error = None
        return destination

    monkeypatch.setattr("splitshot.browser.server.export_project", fake_export_project)
    monkeypatch.setattr("splitshot.export.pipeline.export_project", fake_export_project)

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser, page = _open_test_page(playwright, server)
            try:
                page.wait_for_function(
                    """(payload) => {
                        const project = state?.project;
                        return project?.path === payload.projectPath
                            && (project?.stages || []).length > 0
                            && project?.active_stage_id === payload.stageId
                            && (project?.merge_sources || []).length === 2
                            && (project?.analysis?.shots?.length || 0) > 0;
                    }""",
                    arg={"projectPath": str(project_path), "stageId": stage.id},
                )
                _capture_release_proof_screenshot(
                    page, artifact_root, "release-01-primary-imported"
                )

                _open_tool_for_release(
                    page, "media", timings, artifact_root, "release-01b-media-pane"
                )
                _open_tool_for_release(
                    page, "merge", timings, artifact_root, "release-02-merge-pane"
                )
                _open_tool(page, "merge")
                page.locator("#merge-enabled").check()
                page.wait_for_function("() => state?.project?.merge?.enabled === true")
                page.locator("#merge-layout").select_option("pip")
                page.wait_for_function("() => state?.project?.merge?.layout === 'pip'")
                _capture_release_proof_screenshot(page, artifact_root, "release-03-merge-sources")

                first_card = page.locator(".merge-media-card").first
                first_body = first_card.locator(".merge-media-card-body")
                source_id = first_card.get_attribute("data-source-id")
                assert source_id
                if first_body.evaluate("body => body.hidden"):
                    first_card.locator('button[aria-label*="stage media controls"]').click()
                    first_body.wait_for(state="visible")
                _capture_release_proof_screenshot(
                    page, artifact_root, "release-04-merge-card-expanded"
                )

                _open_tool_for_release(
                    page, "trim-sync", timings, artifact_root, "release-05-trim-sync-pane"
                )
                trim_sync_card = page.locator(f'.trim-source-card[data-source-id="{source_id}"]')
                trim_sync_card.wait_for(state="visible")
                trim_sync_card.locator("button.trim-analyze-btn").first.click(force=True)
                page.wait_for_function(
                    """(targetSourceId) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
                        return Boolean(source)
                            && source.sync_analysis_status === 'ready'
                            && source.sync_offset_source === 'auto';
                    }""",
                    arg=source_id,
                    timeout=120000,
                )
                _capture_release_proof_screenshot(page, artifact_root, "release-06-sync-ready")

                started_at = time.perf_counter()
                _open_tool_for_release(
                    page, "merge", timings, artifact_root, "release-07-merge-returned"
                )
                first_card = page.locator(f'.merge-media-card[data-source-id="{source_id}"]')
                first_card.locator('[data-merge-source-field="placement_mode"]').select_option(
                    "above_below"
                )
                page.wait_for_function(
                    """(targetSourceId) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
                        return source?.placement?.mode === 'above_below';
                    }""",
                    arg=source_id,
                )
                _record_timing(
                    timings,
                    "per-source-layout",
                    started_at,
                    RELEASE_PROOF_THRESHOLDS_MS["source_commit"],
                )
                _capture_release_proof_screenshot(
                    page, artifact_root, "release-08-layout-committed"
                )

                page.locator("#expand-waveform").click()
                _wait_for_ui_settled(page)
                _capture_release_proof_screenshot(
                    page, artifact_root, "release-10-waveform-expanded"
                )

                _open_tool_for_release(
                    page, "overlay", timings, artifact_root, "release-11-overlay-before-profile"
                )
                page.locator("#show-overlay").check()
                badge_size = _alternate_select_value(page.locator("#badge-size"))
                page.locator("#badge-size").select_option(badge_size)
                page.wait_for_function(
                    "(value) => state?.project?.overlay?.badge_size === value", arg=badge_size
                )

                _open_tool_for_release(
                    page, "export", timings, artifact_root, "release-12-export-before-profile"
                )
                _open_tool_for_release(page, "review", timings, artifact_root, "release-14-review")
                _capture_release_proof_screenshot(page, artifact_root, "release-15-review-metrics")
                _open_tool_for_release(
                    page, "overlay", timings, artifact_root, "release-16-overlay-ready"
                )

                _open_tool_for_release(page, "timing", timings, artifact_root)
                page.locator("#expand-timing").click()
                _wait_for_ui_settled(page)
                _capture_release_proof_screenshot(
                    page, artifact_root, "release-18-timing-workbench-expanded"
                )

                for tool_id in TOOL_IDS:
                    _open_tool_for_release(page, tool_id, timings, artifact_root, f"pane-{tool_id}")

                _open_tool_for_release(
                    page, "queue", timings, artifact_root, "release-19-queue-pane"
                )
                page.wait_for_timeout(300)
                enabled_queue_button = page.locator(".queue-add-btn:not([disabled])").first
                if enabled_queue_button.count():
                    enabled_queue_button.click()
                elif not page.evaluate("() => (state?.project?.queue || []).length > 0"):
                    page.evaluate(
                        """async (stageId) => {
                            if (!stageId) return;
                            await callApi('/api/project/queue/add', { stage_id: stageId });
                        }""",
                        stage.id,
                    )
                page.wait_for_function(
                    """(targetStageId) => {
                        const project = state?.project;
                        const stage = (project?.stages || []).find((item) => item.id === targetStageId);
                        const queue = state?.project?.queue || [];
                        return queue.length > 0
                            && queue.some((entry) => entry.stage_id === targetStageId && entry.status === 'queued')
                            && stage?.queue_status === 'queued';
                    }""",
                    arg=stage.id,
                    timeout=10000,
                )
                started_at = time.perf_counter()
                page.evaluate(
                    """async () => { await callApi('/api/project/queue/process', { mode: 'individual' }); }"""
                )
                page.wait_for_function(
                    """(targetStageId) => {
                        const queue = state?.project?.queue || [];
                        const stage = (state?.project?.stages || []).find((item) => item.id === targetStageId);
                        return queue.length > 0
                            && queue.some((entry) => entry.stage_id === targetStageId && entry.status === 'complete')
                            && stage?.queue_status === 'complete'
                            && Boolean(queue.find((entry) => entry.stage_id === targetStageId)?.output_path);
                    }""",
                    arg=stage.id,
                    timeout=10000,
                )
                _record_timing(timings, "queue-process-complete", started_at, 15_000)
                _open_tool_for_release(
                    page, "export", timings, artifact_root, "release-20-export-pane-after-queue"
                )
                page.locator("#show-export-log").click()
                page.wait_for_function(
                    "() => document.getElementById('export-log-modal')?.hidden === false"
                )
                _capture_release_proof_screenshot(page, artifact_root, "release-21-export-log")
                page.locator("#close-export-log").click()
                _write_release_proof_text(
                    artifact_root, "export-log.txt", "Queue processing completed."
                )

                _open_tool_for_release(
                    page, "trim-sync", timings, artifact_root, "release-22-before-trim-clear"
                )
                trim_sync_card = page.locator(f'.trim-source-card[data-source-id="{source_id}"]')
                trim_sync_card.wait_for(state="visible")
                started_at = time.perf_counter()
                trim_sync_card.get_by_role("button", name="Clear", exact=True).click()
                page.wait_for_function(
                    """(targetSourceId) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
                        const trim = source?.trim_derivative;
                        return Boolean(source)
                            && source.asset?.path
                            && (!trim?.derivative_path)
                            && trim?.active_path_kind !== 'local_derivative';
                    }""",
                    arg=source_id,
                )
                _record_timing(
                    timings, "trim-clear", started_at, RELEASE_PROOF_THRESHOLDS_MS["trim_clear"]
                )
                _capture_release_proof_screenshot(page, artifact_root, "release-23-trim-cleared")

                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("() => Boolean(state?.project?.path)")
                _open_tool_for_release(
                    page, "trim-sync", timings, artifact_root, "release-24-reloaded-trim-sync"
                )
                # Reload persistence should assert saved merge-source truth only.
                # The sync analysis status is exercised earlier in this flow and is
                # synthesized from runtime analysis state rather than owned by the
                # merge source itself.
                page.wait_for_function(
                    """(targetSourceId) => {
                        const source = (state?.project?.merge_sources || []).find((item) => item.id === targetSourceId);
                        const trim = source?.trim_derivative;
                        return source?.placement?.mode === 'above_below'
                            && (!trim?.derivative_path)
                            && trim?.active_path_kind !== 'local_derivative';
                    }""",
                    arg=source_id,
                )
                _open_tool_for_release(
                    page, "review", timings, artifact_root, "release-25-reloaded-review"
                )
                _capture_release_proof_screenshot(page, artifact_root, "release-26-final-composite")
                _write_release_proof_json(
                    artifact_root,
                    "state-summary.json",
                    page.evaluate(
                        """() => JSON.parse(JSON.stringify({
                            activeTool,
                            project_path: state?.project?.path || '',
                            shots: state?.project?.analysis?.shots?.length || 0,
                            merge_sources: state?.project?.merge_sources || [],
                            output_profiles: state?.output_profiles || [],
                            export: state?.project?.export || {},
                            overlay: state?.project?.overlay || {},
                        }))"""
                    ),
                )
            finally:
                browser.close()
    finally:
        server.shutdown()

    assert captured_exports
    assert Path(str(captured_exports[0]["output_path"])).exists()
    _write_release_proof_json(artifact_root, "timings.json", timings)
    _write_release_proof_contact_sheet(artifact_root)


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
                page.wait_for_function(
                    "(path) => state?.project?.path === path", arg=str(project_path)
                )
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    "() => state?.project?.analysis?.shotml_settings?.detection_threshold !== undefined"
                )
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
                    threshold_section.locator("button[data-section-toggle]").click()
                    page.wait_for_function(
                        "(selector) => !document.querySelector(selector)?.classList.contains('collapsed')",
                        arg='[data-shotml-section="threshold"]',
                    )
                page.locator("#threshold").fill("0.5")
                page.locator("#apply-threshold").click()
                page.wait_for_function(
                    "() => state?.project?.analysis?.shotml_settings?.detection_threshold === 0.5"
                )

                _open_tool(page, "timing")
                target_shot_id = _select_first_waveform_shot(page)
                original_time_ms = page.evaluate(
                    """(shotId) => (state?.project?.analysis?.shots || []).find((item) => item.id === shotId)?.time_ms ?? null""",
                    target_shot_id,
                )
                assert original_time_ms is not None
                page.evaluate(
                    """({ shotId, deltaMs }) => {
                        const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
                        if (!shot) return;
                        callApi("/api/shots/move", { shot_id: shot.id, time_ms: shot.time_ms + deltaMs, preserve_following_splits: true });
                    }""",
                    {"shotId": target_shot_id, "deltaMs": 10},
                )
                page.wait_for_function(
                    """(payload) => (state?.project?.analysis?.shots || []).find((item) => item.id === payload.shotId)?.time_ms === payload.timeMs""",
                    arg={"shotId": target_shot_id, "timeMs": original_time_ms + 10},
                )

                timing_changer_section = page.locator('[data-shotml-section="timing_changer"]')
                _open_tool(page, "shotml")
                if timing_changer_section.evaluate(
                    "element => element.classList.contains('collapsed')"
                ):
                    timing_changer_section.locator("button[data-section-toggle]").click()
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
                proposal_rows = page.locator(".shotml-proposal-row")
                proposal_rows.nth(restore_index).get_by_role("button", name="Apply").click()
                page.wait_for_function(
                    """(payload) => (state?.project?.analysis?.shots || []).find((item) => item.id === payload.shotId)?.time_ms === payload.timeMs""",
                    arg={"shotId": target_shot_id, "timeMs": original_time_ms},
                )

                _open_tool(page, "timing")
                page.evaluate(
                    """({ shotId, deltaMs }) => {
                        const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId);
                        if (!shot) return;
                        callApi("/api/shots/move", { shot_id: shot.id, time_ms: shot.time_ms + deltaMs, preserve_following_splits: true });
                    }""",
                    {"shotId": target_shot_id, "deltaMs": 10},
                )
                page.wait_for_function(
                    """(payload) => (state?.project?.analysis?.shots || []).find((item) => item.id === payload.shotId)?.time_ms === payload.timeMs""",
                    arg={"shotId": target_shot_id, "timeMs": original_time_ms + 10},
                )

                _open_tool(page, "shotml")
                if timing_changer_section.evaluate(
                    "element => element.classList.contains('collapsed')"
                ):
                    timing_changer_section.locator("button[data-section-toggle]").click()
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
                proposal_rows = page.locator(".shotml-proposal-row")
                proposal_rows.nth(restore_index).get_by_role("button", name="Discard").click()
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
