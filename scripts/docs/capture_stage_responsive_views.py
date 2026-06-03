#!/usr/bin/env python3
# ruff: noqa: E402
"""Capture responsive Stage screenshots at 1280px and 900px with layout assertions."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from playwright.async_api import Page, async_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController
from scripts.docs.capture_loaded_views import setup_loaded_state, switch_view


OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "automate3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESPONSIVE_CASES = (
    {"width": 1280, "tool": "project", "filename": "responsive-stage-1280.png"},
    {"width": 900, "tool": "settings", "filename": "responsive-stage-900.png"},
)


class ProofFailure(RuntimeError):
    pass


async def assert_responsive_stage(page: Page, *, width: int, tool: str) -> dict[str, object]:
    await switch_view(page, "stage")
    await page.set_viewport_size({"width": width, "height": 900})
    await page.evaluate(
        """(tool) => {
        window.dispatchEvent(new Event('resize'));
        setActiveTool(tool);
    }""",
        tool,
    )
    await page.wait_for_function("(tool) => activeTool === tool", arg=tool, timeout=10_000)
    await page.wait_for_timeout(250)

    result = await page.evaluate(
        """({ expectedWidth, expectedTool }) => {
          const stageView = document.getElementById('view-stage');
          const stage = document.getElementById('video-stage');
          const inspector = document.querySelector('.inspector');
          const rail = document.querySelector('.tool-rail');
          const toolPane = document.querySelector(`[data-tool-pane="${expectedTool}"]`);
          const shell = document.querySelector('.cockpit-shell');
          const stageRect = stage?.getBoundingClientRect();
          const inspectorRect = inspector?.getBoundingClientRect();
          return {
            activeSurface: typeof activeSurface === 'string' ? activeSurface : '',
            activeTool: typeof activeTool === 'string' ? activeTool : '',
            viewActive: Boolean(stageView?.classList.contains('active')),
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
            mediaLoaded: Boolean(state?.media?.primary_available),
            shotCount: state?.project?.analysis?.shots?.length || 0,
            horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            railDisplay: rail ? getComputedStyle(rail).display : 'none',
            toolPaneVisible: toolPane ? toolPane.hidden === false : false,
            stageWidth: Math.round(stageRect?.width || 0),
            stageHeight: Math.round(stageRect?.height || 0),
            inspectorWidth: Math.round(inspectorRect?.width || 0),
            inspectorHeight: Math.round(inspectorRect?.height || 0),
            inspectorCompact: shell ? shell.classList.contains('inspector-compact') : false,
            expectedWidth,
            expectedTool,
          };
        }""",
        {"expectedWidth": width, "expectedTool": tool},
    )

    failures: list[str] = []
    if result["activeSurface"] != "single" or not result["viewActive"]:
        failures.append("stage view is not active")
    if result["activeTool"] != tool:
        failures.append("expected tool is not active")
    if abs(int(result["viewportWidth"]) - width) > 1:
        failures.append("viewport width drifted")
    if not result["mediaLoaded"] or int(result["shotCount"]) <= 0:
        failures.append("stage media was not loaded")
    if result["horizontalOverflow"]:
        failures.append("horizontal overflow detected")
    if result["railDisplay"] == "none":
        failures.append("tool rail hidden")
    if not result["toolPaneVisible"]:
        failures.append("active tool pane hidden")
    if int(result["stageWidth"]) < 320 or int(result["stageHeight"]) <= 0:
        failures.append("video stage collapsed")
    if int(result["inspectorWidth"]) < 320 or int(result["inspectorHeight"]) <= 0:
        failures.append("inspector collapsed")
    if failures:
        raise ProofFailure(
            f"responsive stage assertion failed at {width}px/{tool}: {', '.join(failures)}"
        )
    return result


async def capture_case(page: Page, *, width: int, tool: str, filename: str) -> dict[str, object]:
    assertions = await assert_responsive_stage(page, width=width, tool=tool)
    path = OUTPUT_DIR / filename
    await page.locator("#view-stage").screenshot(path=path)
    data = path.read_bytes()
    return {
        "file": filename,
        "path": str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "assertions": assertions,
        "status": "pass",
    }


async def run() -> dict[str, object]:
    previous_library_root = os.environ.get("SPLITSHOT_LIBRARY_ROOT")
    proof_library_root = tempfile.mkdtemp(prefix="splitshot-automate3-responsive-library-")
    os.environ["SPLITSHOT_LIBRARY_ROOT"] = proof_library_root

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    console_errors: list[str] = []
    captures: list[dict[str, object]] = []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )
            page.on("pageerror", lambda exc: console_errors.append(str(exc)))
            await page.goto(server.url, wait_until="domcontentloaded")
            await page.wait_for_selector("#app-shell", timeout=15_000)

            setup = await setup_loaded_state(page)
            for case in RESPONSIVE_CASES:
                captures.append(await capture_case(page, **case))

            await browser.close()

        if console_errors:
            raise ProofFailure(f"console errors during responsive capture: {console_errors}")

        proof = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "kind": "responsive",
            "status": "pass",
            "setup": setup | {"library_root": proof_library_root},
            "screenshots": captures,
        }
        (OUTPUT_DIR / "responsive-proof-results.json").write_text(
            json.dumps(proof, indent=2),
            encoding="utf-8",
        )
        return proof
    finally:
        server.shutdown()
        if previous_library_root is None:
            os.environ.pop("SPLITSHOT_LIBRARY_ROOT", None)
        else:
            os.environ["SPLITSHOT_LIBRARY_ROOT"] = previous_library_root


def main() -> int:
    try:
        proof = asyncio.run(run())
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(proof, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
