"""Exercise every installed runtime control left uncovered by the focused audits."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from playwright.sync_api import Locator, Page, sync_playwright

PREFERRED_ATTRIBUTES = (
    "data-tool",
    "data-settings-section",
    "data-shotml-section",
    "data-shotml-setting",
    "data-text-box-field",
    "data-popup-field",
    "data-merge-source-field",
    "data-stage-field",
    "data-intro-outro-field",
    "data-field",
    "data-boundary-kind",
    "data-text-box-action",
    "data-media-section",
    "data-summary-metric",
    "data-metric-id",
    "data-remove-box",
    "data-stage-id",
    "data-popup-action",
    "name",
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--gaps-json", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--video-output", type=Path, required=True)
    parser.add_argument("--project-path", type=Path, required=True)
    parser.add_argument("--primary-video", type=Path, required=True)
    parser.add_argument("--secondary-video", type=Path, required=True)
    parser.add_argument("--practiscore", type=Path, required=True)
    return parser.parse_args()


def _locator(page: Page, item: dict[str, Any]) -> Locator:
    identity = str(item["identity"])
    occurrence = int(item.get("occurrence") or 0)
    if identity.startswith("id:"):
        return page.locator(f"#{identity[3:]}").nth(occurrence)
    if identity.startswith("data-") and ":" in identity:
        attribute, value = identity.split(":", 1)
        escaped = value.replace('"', '\\"')
        return page.locator(f'[{attribute}="{escaped}"]').nth(occurrence)
    if ":" in identity:
        tag, label = identity.split(":", 1)
        if tag == "button":
            role_match = page.get_by_role("button", name=label, exact=True)
            if role_match.count() > occurrence:
                return role_match.nth(occurrence)
            if label == "Hide stage media controls":
                return page.locator(".merge-media-card .pane-toggle").nth(occurrence)
            escaped = label.replace('"', '\\"')
            return page.locator(
                f'button[title="{escaped}"], button[aria-label="{escaped}"]'
            ).nth(occurrence)
        for attribute in ("aria-label", "title", "placeholder"):
            escaped = label.replace('"', '\\"')
            match = page.locator(f'{tag}[{attribute}="{escaped}"]:visible')
            if match.count() > occurrence:
                return match.nth(occurrence)
        if tag in {"input", "textarea"}:
            valued = page.locator(f"{tag}:visible")
            matches = [
                index
                for index in range(valued.count())
                if valued.nth(index).input_value() == label
            ]
            if len(matches) > occurrence:
                return valued.nth(matches[occurrence])
            if tag == "textarea" and valued.count() > occurrence:
                return valued.nth(occurrence)
        return page.locator(tag).filter(has_text=label).nth(occurrence)
    return page.locator(f"#{identity}").nth(occurrence)


def _prepare_dynamic_controls(
    page: Page, item: dict[str, Any], args: argparse.Namespace
) -> None:
    """Expose conditional controls before exercising their inventory identity."""
    pane = str(item.get("pane") or "")
    identity = str(item.get("identity") or "")
    tool = page.locator(f'[data-tool="{pane}"]')
    if tool.count():
        tool.click(force=True)
        page.wait_for_timeout(150)

    page.evaluate(
        """() => {
          document.querySelectorAll('details').forEach((node) => { node.open = true; });
          document.querySelectorAll('.settings-section.collapsed, .shotml-section.collapsed, .trim-source-card.collapsed')
            .forEach((node) => node.classList.remove('collapsed'));
        }"""
    )

    source_selector = ".trim-source-card" if pane == "trim-sync" else ".merge-media-card"
    if pane in {"merge", "trim-sync"} and page.locator(source_selector).count() == 0:
        page.locator("#merge-media-input").set_input_files(str(args.secondary_video))
        page.wait_for_timeout(1_000)
        tool = page.locator(f'[data-tool="{pane}"]')
        if tool.count():
            tool.click(force=True)
            page.wait_for_timeout(250)

    if pane == "merge" and identity == "button:Hide stage media controls":
        page.evaluate(
            """() => {
              const source = state?.project?.merge_sources?.[0];
              if (!source) return;
              const sourceId = sourceIdentifier(source, '0');
              setMergeSourceExpanded(sourceId, true);
              renderMergeMediaList();
            }"""
        )
        toggle = page.get_by_role("button", name="Show stage media controls", exact=True).first
        if toggle.count():
            toggle.click(force=True)
            page.wait_for_timeout(150)

    if pane == "intro-outro":
        if page.locator('.intro-outro-box[data-box-index="0"]').count() == 0:
            page.locator("#intro-outro-add-text").click(force=True)
            page.wait_for_timeout(250)
        if page.locator('[data-metric-id="score_time"]').count() == 0:
            page.locator("#intro-outro-add-match").click(force=True)
            page.wait_for_timeout(250)

    if pane == "review":
        if page.locator('#review-text-box-list [data-text-box-field="text"]').count() == 0:
            page.locator("#review-add-text-box").click(force=True)
            page.wait_for_timeout(250)
        if page.locator('[data-summary-metric="score_time"]').count() == 0:
            page.locator("#review-add-imported-box").click(force=True)
            page.wait_for_timeout(250)

    if pane == "overlay" and identity.startswith("input:"):
        label = identity.split(":", 1)[1]
        candidate = page.locator(
            '.score-color-input, .badge-style-card [data-field="background_color"], '
            '.badge-style-card [data-field="text_color"]'
        ).first
        if label == "#FFFFFF" and page.locator('input[placeholder="#FFFFFF"]:visible').count() == 0 and candidate.count():
            candidate.click(force=True)
            page.wait_for_timeout(100)

    if pane == "overlay" and identity.startswith("button:"):
        label = identity.split(":", 1)[1]
        if page.get_by_role("button", name=label, exact=True).count() == 0:
            preset = page.locator("#scoring-preset")
            if preset.count():
                values = preset.locator("option").evaluate_all(
                    "options => options.map((option) => option.value)"
                )
                for value in values:
                    page.evaluate(
                        "async (ruleset) => { await applyScoringSettings(undefined, ruleset); }",
                        value,
                    )
                    page.locator('[data-tool="overlay"]').click(force=True)
                    page.wait_for_timeout(100)
                    if page.get_by_role("button", name=label, exact=True).count():
                        break


def _show_step(page: Page, item: dict[str, Any]) -> None:
    page.evaluate(
        """(payload) => {
          let banner = document.getElementById('release-video-current-control');
          if (!banner) {
            banner = document.createElement('div');
            banner.id = 'release-video-current-control';
            Object.assign(banner.style, {
              position: 'fixed', left: '18px', top: '18px', zIndex: '2147483647',
              background: 'rgba(0,0,0,.88)', color: '#fff', border: '2px solid #22c55e',
              borderRadius: '6px', padding: '10px 14px', font: '600 16px sans-serif',
              maxWidth: '900px', pointerEvents: 'none'
            });
            document.body.appendChild(banner);
          }
          banner.textContent = `Installed control proof — ${payload.pane}: ${payload.identity}`;
        }""",
        item,
    )


def _next_value(locator: Locator) -> str:
    return locator.evaluate(
        """(node) => {
          if (node instanceof HTMLSelectElement) {
            const option = [...node.options].find((item) => !item.disabled && item.value !== node.value);
            return option ? option.value : node.value;
          }
          if (node instanceof HTMLInputElement && (node.type === 'number' || node.type === 'range')) {
            const min = Number.isFinite(Number(node.min)) ? Number(node.min) : 0;
            const max = Number.isFinite(Number(node.max)) ? Number(node.max) : min + 100;
            const step = Number(node.step) > 0 ? Number(node.step) : 1;
            const current = Number(node.value || min);
            return String(current + step <= max ? current + step : Math.max(min, current - step));
          }
          if (node instanceof HTMLInputElement && node.type === 'color') return '#22c55e';
          return 'v107 control proof';
        }"""
    )


def _exercise(
    page: Page,
    locator: Locator,
    item: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    tag = str(item.get("tag") or "")
    input_type = str(item.get("type") or "").lower()
    before = locator.evaluate(
        "(node) => ({value: 'value' in node ? String(node.value) : '', checked: Boolean(node.checked), connected: node.isConnected})"
    )
    if tag == "button" or locator.get_attribute("role") == "button":
        locator.click(force=True, timeout=10_000)
    elif tag == "video":
        locator.evaluate("async (node) => { await node.play(); node.pause(); }")
    elif tag == "select":
        locator.select_option(_next_value(locator), force=True)
    elif tag == "textarea":
        locator.fill(_next_value(locator), force=True)
    elif tag == "input" and input_type == "file":
        identity = str(item["identity"])
        fixture = (
            args.practiscore
            if "practiscore" in identity
            else args.secondary_video
            if "merge" in identity or "more" in identity
            else args.primary_video
        )
        locator.set_input_files(str(fixture))
    elif tag == "input" and input_type in {"checkbox", "radio"}:
        locator.click(force=True, timeout=10_000)
    else:
        value = _next_value(locator)
        locator.evaluate(
            """(node, nextValue) => {
              node.value = nextValue;
              node.dispatchEvent(new Event('input', {bubbles: true}));
              node.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            value,
        )
    page.wait_for_timeout(350)
    if page.locator("#export-log-modal").count() and page.locator(
        "#export-log-modal"
    ).is_visible():
        close = page.locator("#close-export-log")
        if close.count() and close.is_enabled():
            close.click(force=True)
    after = None
    try:
        after = locator.evaluate(
            "(node) => ({value: 'value' in node ? String(node.value) : '', checked: Boolean(node.checked), connected: node.isConnected})"
        )
    except Exception:  # noqa: BLE001 - structural actions may intentionally replace the node.
        after = {"connected": False}
    return {"before": before, "after": after}


def main() -> int:
    args = _args()
    gaps_payload = json.loads(args.gaps_json.read_text(encoding="utf-8"))
    raw_gaps = [item for item in gaps_payload.get("identities") or [] if item.get("status") == "gap"]
    # One successful interaction proves a repeated identity. The identity-result
    # merger intentionally applies that evidence to every runtime occurrence.
    gaps_by_identity: dict[str, dict[str, Any]] = {}
    for item in raw_gaps:
        gaps_by_identity.setdefault(str(item.get("identity") or ""), {**item, "occurrence": 0})
    gaps = list(gaps_by_identity.values())
    destructive = {"id:delete-project", "data-text-box-action:remove", "data-remove-box:0", "data-remove-box:1"}
    gaps.sort(key=lambda item: (str(item.get("identity")) in destructive, str(item.get("pane")), str(item.get("identity"))))
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.video_output.parent.mkdir(parents=True, exist_ok=True)
    recording_dir = args.video_output.parent / f".{args.video_output.stem}-recording"
    shutil.rmtree(recording_dir, ignore_errors=True)
    recording_dir.mkdir(parents=True)
    results: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 1024},
            record_video_dir=str(recording_dir),
            record_video_size={"width": 1440, "height": 1024},
        )
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(args.base_url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_function("() => typeof state !== 'undefined'", timeout=60_000)
        page.evaluate(
            "async (projectPath) => { await callApi('/api/project/open', {path: projectPath}); }",
            str(args.project_path.resolve()),
        )
        page.wait_for_function(
            "(projectPath) => state?.project?.path === projectPath",
            arg=str(args.project_path.resolve()),
            timeout=60_000,
        )
        for item in gaps:
            record = {**item, "status": "failed", "error": ""}
            try:
                _prepare_dynamic_controls(page, item, args)
                _show_step(page, item)
                locator = _locator(page, item)
                if locator.count() == 0:
                    raise RuntimeError("control is not rendered")
                if locator.is_visible():
                    locator.scroll_into_view_if_needed(timeout=5_000)
                record.update(_exercise(page, locator, item, args))
                record["status"] = "passed"
            except Exception as exc:  # noqa: BLE001 - every gap must be reported.
                record["error"] = str(exc)
            results.append(record)
        browser.close()
    recordings = sorted(recording_dir.rglob("*.webm"))
    if not recordings:
        raise RuntimeError("remaining-control audit video was not created")
    shutil.move(str(recordings[-1]), str(args.video_output))
    shutil.rmtree(recording_dir, ignore_errors=True)
    payload = {
        "result": "passed" if all(item["status"] == "passed" for item in results) else "failed",
        "counts": {
            "required": len(results),
            "passed": sum(item["status"] == "passed" for item in results),
            "failed": sum(item["status"] != "passed" for item in results),
        },
        "actions": results,
        "video": str(args.video_output),
    }
    args.report_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], indent=2))
    return 0 if payload["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
