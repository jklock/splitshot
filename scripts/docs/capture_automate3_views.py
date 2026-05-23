#!/usr/bin/env python3
"""Capture Automate3 empty-state screenshots with DOM assertions."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from playwright.async_api import Page, async_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "automate3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ProofFailure(RuntimeError):
    pass


async def switch_view(page: Page, view_name: str) -> None:
    await page.evaluate(
        """
        (viewName) => {
          const mapping = {landing: "landing", stage: "single", match: "multi", library: "library"};
          window.setActiveSurface?.(mapping[viewName] || "landing");
        }
        """,
        view_name,
    )
    await page.wait_for_selector(f"#view-{view_name}.active", timeout=10_000)
    await page.wait_for_function(
        "(viewName) => document.getElementById('app-shell')?.dataset.activeView === viewName",
        arg=view_name,
        timeout=10_000,
    )


async def assert_view_layout(page: Page, view_name: str) -> dict[str, object]:
    result = await page.evaluate(
        """
        (viewName) => {
          const view = document.getElementById(`view-${viewName}`);
          const shell = document.getElementById("app-shell");
          const rail = view?.querySelector(".tool-rail");
          const rect = view?.getBoundingClientRect();
          const railDisplay = rail ? getComputedStyle(rail).display : "none";
          return {
            activeView: shell?.dataset.activeView || "",
            viewActive: Boolean(view?.classList.contains("active")),
            width: Math.round(rect?.width || 0),
            height: Math.round(rect?.height || 0),
            horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            railDisplay,
            text: view?.innerText || "",
          };
        }
        """,
        view_name,
    )
    failures: list[str] = []
    if result["activeView"] != view_name or not result["viewActive"]:
        failures.append("view is not active")
    if result["width"] <= 0 or result["height"] <= 0:
        failures.append("view has zero bounds")
    if result["horizontalOverflow"]:
        failures.append("horizontal overflow")
    if view_name == "landing" and result["railDisplay"] != "none":
        failures.append("landing rail should be hidden")
    if view_name in {"stage", "match", "library"} and result["railDisplay"] == "none":
        failures.append(f"{view_name} rail hidden")
    if failures:
        raise ProofFailure(f"{view_name} layout assertion failed: {', '.join(failures)}")
    return {key: value for key, value in result.items() if key != "text"} | {
        "text_length": len(result["text"])
    }


async def capture_view(page: Page, view_name: str, filename: str) -> dict[str, object]:
    await switch_view(page, view_name)
    assertions = await assert_view_layout(page, view_name)
    path = OUTPUT_DIR / filename
    await page.locator(f"#view-{view_name}").screenshot(path=path)
    data = path.read_bytes()
    return {
        "file": filename,
        "path": str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "assertions": assertions,
        "status": "pass",
    }


async def build_contact_sheet(page: Page, images: list[dict[str, object]], filename: str) -> dict[str, object]:
    cards = "\n".join(
        f"""
        <figure>
          <figcaption>{item['file']}</figcaption>
          <img src="data:image/png;base64,{base64.b64encode(Path(str(item['path'])).read_bytes()).decode('ascii')}" />
        </figure>
        """
        for item in images
    )
    await page.set_viewport_size({"width": 1440, "height": 900})
    await page.set_content(
        f"""
        <html>
          <head>
            <style>
              body {{ margin: 0; background: #101214; color: #f2f4f7; font: 13px system-ui, sans-serif; }}
              main {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; padding: 16px; }}
              figure {{ margin: 0; border: 1px solid #30363d; background: #171b20; }}
              figcaption {{ padding: 8px 10px; font-weight: 800; }}
              img {{ display: block; width: 100%; height: 360px; object-fit: contain; background: #050607; }}
            </style>
          </head>
          <body><main>{cards}</main></body>
        </html>
        """,
        wait_until="load",
    )
    path = OUTPUT_DIR / filename
    await page.screenshot(path=path, full_page=False)
    data = path.read_bytes()
    return {"file": filename, "path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


async def run() -> dict[str, object]:
    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    console_errors: list[str] = []
    results: list[dict[str, object]] = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: console_errors.append(str(exc)))
            await page.goto(server.url, wait_until="domcontentloaded")
            await page.wait_for_selector("#app-shell", timeout=15_000)

            results.append(await capture_view(page, "landing", "empty-landing.png"))
            results.append(await capture_view(page, "stage", "empty-stage.png"))
            results.append(await capture_view(page, "match", "empty-match.png"))
            results.append(await capture_view(page, "library", "empty-library.png"))
            contact = await build_contact_sheet(page, results, "contact-sheet.png")
            await browser.close()

        if console_errors:
            raise ProofFailure(f"console errors during empty capture: {console_errors}")
        proof = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "kind": "empty",
            "status": "pass",
            "screenshots": results,
            "contact_sheet": contact,
        }
        (OUTPUT_DIR / "proof-results.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
        return proof
    finally:
        server.shutdown()


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
