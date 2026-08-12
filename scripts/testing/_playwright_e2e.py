#!/usr/bin/env python3
"""Playwright E2E interactions against a running SplitShot backend. Run as subprocess."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--video-output", type=Path, default=None)
    args = parser.parse_args()

    base_url = f"http://127.0.0.1:{args.port}"

    try:
        resp = urllib.request.urlopen(f"{base_url}/api/state", timeout=10)
        state = json.loads(resp.read().decode())
        print(f"PW: API state OK, project={bool(state.get('project'))}", flush=True)
    except Exception as e:
        print(f"PW: API state FAILED: {e}", file=sys.stderr, flush=True)
        return 1

    video_file = args.video_output
    if video_file:
        video_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                record_video_dir=str(video_file.parent) if video_file else None,
            )
            page = context.new_page()

            page.goto(base_url, wait_until="domcontentloaded", timeout=45000)
            print("PW: page loaded", flush=True)

            page.wait_for_function("() => typeof activeTool !== 'undefined'", timeout=45000)
            print("PW: app initialized", flush=True)
            time.sleep(1)

            if not page.evaluate("Boolean(state?.project?.path)"):
                pp = str(args.video.parent / "pw-e2e.ssproj")
                page.evaluate("(p) => createNewProject(p)", pp)
                page.wait_for_function("() => Boolean(state?.project?.path)", timeout=15000)
                time.sleep(0.5)

            page.locator("#primary-file-input").set_input_files(str(args.video))
            page.wait_for_function(
                "() => Boolean(state?.media?.primary_display_name)", timeout=60000
            )
            page.wait_for_function(
                "() => (state?.project?.analysis?.shots || []).length > 0", timeout=120000
            )
            print("PW: video imported, shots detected", flush=True)
            time.sleep(0.5)

            for t in [
                "project",
                "merge",
                "scoring",
                "timing",
                "markers",
                "overlay",
                "review",
                "export",
                "metrics",
                "settings",
            ]:
                btn = page.locator(f'button[data-tool="{t}"]')
                if btn.is_visible():
                    btn.click(force=True)
                    page.wait_for_function("(tool) => activeTool === tool", arg=t, timeout=15000)
                    time.sleep(0.3)
                    print(f"PW: tool {t} activated", flush=True)

            page.locator('button[data-tool="timing"]').click(force=True)
            page.wait_for_function("() => activeTool === 'timing'", timeout=10000)
            if page.locator(".waveform-shot-card").count() > 0:
                page.locator(".waveform-shot-card").first.click()
                time.sleep(0.3)
                print("PW: waveform shot selected", flush=True)

            for t in ["markers", "overlay", "review", "settings", "scoring"]:
                page.locator(f'button[data-tool="{t}"]').click(force=True)
                page.wait_for_function("(tool) => activeTool === tool", arg=t, timeout=10000)
                time.sleep(0.3)

            context.close()
            browser.close()
    except Exception as e:
        print(f"PW: Playwright error: {e}", file=sys.stderr, flush=True)
        return 1

    if video_file:
        recorded = sorted(video_file.parent.glob("*.webm")) + sorted(
            video_file.parent.glob("*.mp4")
        )
        if recorded:
            src = max(recorded, key=lambda p: p.stat().st_mtime)
            import shutil

            shutil.move(str(src), str(video_file))
            sz = os.path.getsize(video_file) / 1024
            print(f"PW: video saved ({sz:.1f} KB)", flush=True)

    try:
        resp = urllib.request.urlopen(f"{base_url}/api/state", timeout=5)
        final = json.loads(resp.read().decode())
        shots = len(final.get("project", {}).get("analysis", {}).get("shots", []))
        popups = len(final.get("project", {}).get("popups", []))
        print(f"PW: final state shots={shots} popups={popups}", flush=True)
    except Exception:
        pass

    print("PW: E2E test passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
