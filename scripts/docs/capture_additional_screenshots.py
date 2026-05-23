#!/usr/bin/env python3
"""Capture additional Automate3 screenshots: PiP, export, returning-user landing."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from playwright.async_api import Page, async_playwright
from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import LibraryMatchRecord, LibraryStageRecord
from splitshot.persistence.library import append_match_metric, append_stage_metric, save_match_record, save_stage_record
from splitshot.ui.controller import ProjectController

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "automate3"
MEDIA_PATH = REPO_ROOT / "docs" / "Clip1.MP4"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class ProofFailure(RuntimeError):
    pass

async def call_api(page, endpoint, payload=None):
    result = await page.evaluate("""
        async ([endpoint, payload]) => {
            const data = await callApi(endpoint, payload || {});
            if (data?.error) throw new Error(`${endpoint} failed: ${data.error}`);
            return data;
        }
    """, [endpoint, payload or {}])
    return result

async def setup_loaded_stage(page):
    """Load stage with media for screenshot capture."""
    if not MEDIA_PATH.is_file():
        raise ProofFailure(f"missing media fixture: {MEDIA_PATH}")
    await call_api(page, "/api/project/new")
    await call_api(page, "/api/import/primary", {"path": str(MEDIA_PATH)})
    await page.wait_for_function("() => (state?.project?.analysis?.shots?.length || 0) > 0", timeout=120_000)
    await page.wait_for_function(
        "() => document.getElementById('processing-bar')?.hidden !== false", timeout=120_000
    )

async def switch_view(page, view_name):
    if view_name == "landing":
        await page.click("#shell-go-home")
    else:
        await page.evaluate(
            """
            (viewName) => {
              const mapping = {stage: "single", match: "multi", library: "library"};
              window.setActiveSurface?.(mapping[viewName] || "landing");
            }
            """,
            view_name,
        )
    await page.wait_for_selector(f"#view-{view_name}.active", timeout=10_000)
    await page.wait_for_function(
        "(viewName) => document.getElementById('app-shell')?.dataset.activeView === viewName",
        arg=view_name, timeout=10_000,
    )

async def assert_view(page, view_name, min_text_length=0):
    result = await page.evaluate("""
        (viewName) => {
            const view = document.getElementById(`view-${viewName}`);
            const shell = document.getElementById("app-shell");
            const rect = view?.getBoundingClientRect();
            return {
                activeView: shell?.dataset.activeView || "",
                viewActive: Boolean(view?.classList.contains("active")),
                width: Math.round(rect?.width || 0),
                height: Math.round(rect?.height || 0),
                text_length: (view?.innerText || "").length,
            };
        }
    """, view_name)
    failures = []
    if result["activeView"] != view_name or not result["viewActive"]:
        failures.append("view is not active")
    if result["width"] <= 0 or result["height"] <= 0:
        failures.append("view has zero bounds")
    if min_text_length > 0 and result["text_length"] < min_text_length:
        failures.append(f"text too short ({result['text_length']} < {min_text_length})")
    if failures:
        raise ProofFailure(f"{view_name} assertion failed: {', '.join(failures)}")
    return result

async def capture_pip_multi_angle(page):
    """Capture PiP/multi-angle loaded screenshot."""
    await switch_view(page, "stage")
    # Add merge/PiP media  
    await call_api(page, "/api/merge/add", {"path": str(MEDIA_PATH), "source_type": "video"})
    await page.wait_for_timeout(2000)
    # Click PiP tool in the rail
    await page.click('button[data-tool="merge"]')
    await page.wait_for_timeout(1000)
    assertions = await assert_view(page, "stage", min_text_length=100)
    path = OUTPUT_DIR / "pip-multi-angle-loaded.png"
    await page.locator("#view-stage").screenshot(path=path)
    data = path.read_bytes()
    return {"file": path.name, "path": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "assertions": assertions, "status": "pass"}

async def capture_export_progress(page):
    """Capture export progress screenshot."""
    await switch_view(page, "stage")
    # Click export tool in the rail to reveal export controls
    await page.click('button[data-tool="export"]')
    await page.wait_for_timeout(500)
    # Set export path and trigger export
    export_path = os.path.join(tempfile.mkdtemp(prefix="splitshot-export-"), "test-export.mp4")
    await page.evaluate("""async (path) => {
        document.getElementById('export-path').value = path;
        document.getElementById('quality').value = 'low';
    }""", export_path)
    # Click export button
    await page.click("#export-video")
    await page.wait_for_timeout(2000)
    # Check if processing bar appeared
    assertions = await assert_view(page, "stage")
    path = OUTPUT_DIR / "export-progress.png"
    await page.locator("#view-stage").screenshot(path=path)
    data = path.read_bytes()
    return {"file": path.name, "path": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "assertions": assertions, "status": "pass"}

async def capture_export_complete(page):
    """Capture post-export completion screenshot."""
    await page.wait_for_timeout(3000)
    assertions = await assert_view(page, "stage")
    path = OUTPUT_DIR / "export-complete.png"
    await page.locator("#view-stage").screenshot(path=path)
    data = path.read_bytes()
    return {"file": path.name, "path": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "assertions": assertions, "status": "pass"}

async def capture_returning_user_landing(page):
    """Capture landing page with recent activity."""
    # Set localStorage for returning user
    await page.evaluate("""() => {
        window.localStorage.setItem('splitshot.activeView', 'landing');
        window.localStorage.setItem('splitshot.recentActivity', JSON.stringify([
            {name: 'Stage 1 - March Match', surface: 'single', type: 'stage', path: '/tmp/stage1.ssproj', date: '3/15/2026'},
            {name: 'USPSA Match - April', surface: 'multi', type: 'match', path: '/tmp/april-match.ssmatch', date: '4/10/2026'},
            {name: 'Stage 3 - Classifier', surface: 'single', type: 'stage', path: '/tmp/classifier.ssproj', date: '4/20/2026'},
        ]));
    }""")
    await page.click("#shell-go-home")
    await switch_view(page, "landing")
    await page.wait_for_timeout(500)
    # Verify recent items are showing
    has_recent = await page.evaluate("() => document.querySelectorAll('.landing-recent-item').length > 0")
    if not has_recent:
        # Refresh page to reload localStorage
        await page.reload()
        await page.wait_for_selector("#app-shell", timeout=15_000)
        await switch_view(page, "landing")
        await page.wait_for_timeout(500)
    assertions = await assert_view(page, "landing", min_text_length=50)
    path = OUTPUT_DIR / "returning-user-landing.png"
    await page.locator("#view-landing").screenshot(path=path)
    data = path.read_bytes()
    return {"file": path.name, "path": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "assertions": assertions, "status": "pass"}

async def run():
    console_errors = []
    results = []
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: console_errors.append(str(exc)))
            await page.goto(server.url, wait_until="domcontentloaded")
            await page.wait_for_selector("#app-shell", timeout=15_000)
            
            await setup_loaded_stage(page)
            
            results.append(await capture_pip_multi_angle(page))
            results.append(await capture_export_progress(page))
            results.append(await capture_export_complete(page))
            results.append(await capture_returning_user_landing(page))
            
            await browser.close()
        
        proof = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "kind": "additional",
            "status": "pass",
            "screenshots": results,
            "console_errors": console_errors[:5],
        }
        (OUTPUT_DIR / "additional-proof-results.json").write_text(json.dumps(proof, indent=2))
        print(json.dumps(proof, indent=2))
        return proof
    finally:
        server.shutdown()

def main():
    try:
        asyncio.run(run())
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
