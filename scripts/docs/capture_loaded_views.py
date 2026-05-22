#!/usr/bin/env python3
"""Capture loaded-state Automate3 view screenshots using Playwright."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "screenshots" / "automate3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://127.0.0.1:8765"
MEDIA_PATH = str((Path(__file__).resolve().parent.parent.parent / "docs" / "Clip1.MP4").absolute())


async def wait_for_app(page):
    await page.wait_for_selector("#app-shell", timeout=15000)
    await page.wait_for_timeout(2000)


async def wait_for_app_idle(page):
    await page.wait_for_function(
        "() => document.getElementById('processing-bar')?.hidden === true",
        timeout=60000,
    )
    await page.evaluate("() => window.forceHideProcessingBar?.()")
    await page.wait_for_timeout(500)


async def switch_view(page, view_name):
    nav_map = {"stage": "nav-stage", "match": "nav-match", "library": "nav-library"}
    btn_id = nav_map.get(view_name)
    if btn_id:
        await page.click(f"#{btn_id}")
    elif view_name == "landing":
        await page.click("#shell-go-home")
    await page.wait_for_timeout(1500)
    await page.wait_for_selector(f"#view-{view_name}.active", timeout=5000)
    await page.wait_for_timeout(500)


async def capture_view(page, view_name, filename):
    print(f"  Capturing {filename}...")
    view_el = await page.query_selector(f"#view-{view_name}")
    if view_el:
        path = OUTPUT_DIR / filename
        await view_el.screenshot(path=path)
        print(f"    Saved: {path} ({os.path.getsize(path)} bytes)")
    else:
        print(f"    WARNING: #view-{view_name} not found")


async def call_api(page, endpoint, payload=None):
    result = await page.evaluate(
        """
        async ([endpoint, payload]) => {
            const resp = await callApi(endpoint, payload || {});
            return resp;
        }
        """,
        [endpoint, payload or {}],
    )
    return result


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        try:
            await page.goto(BASE_URL)
            await wait_for_app(page)

            print("\n=== Stage: Create project and import media ===")
            await switch_view(page, "stage")
            await call_api(page, "/api/project/new")
            await page.wait_for_timeout(1000)

            print(f"  Importing primary media: {MEDIA_PATH}")
            await call_api(page, "/api/import/primary", {"path": MEDIA_PATH})

            print("  Waiting for shot analysis...")
            await page.wait_for_function(
                "() => (state?.project?.analysis?.shots?.length || 0) > 0",
                timeout=120000,
            )
            await wait_for_app_idle(page)
            print("  Analysis complete.")

            print("\n=== Capturing Loaded Stage ===")
            await capture_view(page, "stage", "loaded-stage.png")

            print("\n=== Match: Create workspace ===")
            await switch_view(page, "match")
            await call_api(page, "/api/workspace/new")
            await page.wait_for_timeout(1000)

            project_path = await page.evaluate("() => state?.projectPath || ''")
            print(f"  Project path: {project_path}")

            await call_api(page, "/api/workspace/stage/add", {
                "stage_id": "stage_1",
                "display_name": "Stage 1 - Warmup",
                "project_path": project_path,
            })
            await wait_for_app_idle(page)

            print("\n=== Capturing Loaded Match ===")
            await capture_view(page, "match", "loaded-match.png")

            print("\n=== Capturing Loaded Library ===")
            await switch_view(page, "library")
            await page.wait_for_timeout(2000)
            await capture_view(page, "library", "loaded-library.png")

            print("\n=== Contact Sheet ===")
            await switch_view(page, "landing")
            await page.wait_for_timeout(1000)
            contact_path = OUTPUT_DIR / "contact-sheet-loaded.png"
            await page.screenshot(path=contact_path, full_page=False)
            print(f"  Saved: {contact_path} ({os.path.getsize(contact_path)} bytes)")

            print(f"\nDone. {len(list(OUTPUT_DIR.glob('*.png')))} screenshots in {OUTPUT_DIR}")
            for f in sorted(OUTPUT_DIR.glob('*.png')):
                print(f"  {f.name}: {os.path.getsize(f)} bytes")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
