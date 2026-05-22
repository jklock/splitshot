#!/usr/bin/env python3
"""Capture Automate3 view screenshots using Playwright."""
import asyncio
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "screenshots" / "automate3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://127.0.0.1:8765"

async def wait_for_app(page):
    """Wait for the app shell to be ready."""
    await page.wait_for_selector("#app-shell", timeout=15000)
    await page.wait_for_timeout(2000)

async def switch_view(page, view_name):
    """Click the shell nav button to switch views."""
    nav_map = {"stage": "nav-stage", "match": "nav-match", "library": "nav-library"}
    btn_id = nav_map.get(view_name)
    if btn_id:
        await page.click(f"#{btn_id}")
    elif view_name == "landing":
        await page.click("#shell-go-home")
    await page.wait_for_timeout(1500)
    # Verify the view is active
    await page.wait_for_selector(f"#view-{view_name}.active", timeout=5000)
    await page.wait_for_timeout(1000)

async def capture_view(page, view_name, label, filename):
    """Capture a screenshot of a view."""
    print(f"  Capturing {label}...")
    view_el = await page.query_selector(f"#view-{view_name}")
    if view_el:
        path = OUTPUT_DIR / filename
        await view_el.screenshot(path=path)
        print(f"    Saved: {path} ({os.path.getsize(path)} bytes)")
    else:
        print(f"    WARNING: #view-{view_name} not found")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        try:
            await page.goto(BASE_URL)
            await wait_for_app(page)

            # 1. Capture empty landing page
            print("\n=== Empty States ===")
            await switch_view(page, "landing")
            await capture_view(page, "landing", "Empty Landing", "empty-landing.png")

            # 2. Capture empty stage view (no media loaded)
            await switch_view(page, "stage")
            await capture_view(page, "stage", "Empty Stage", "empty-stage.png")

            # 3. Capture empty match view
            await switch_view(page, "match")
            await capture_view(page, "match", "Empty Match", "empty-match.png")

            # 4. Capture empty library view
            await switch_view(page, "library")
            await capture_view(page, "library", "Empty Library", "empty-library.png")

            # 5. Full page screenshot for contact sheet
            print("\n=== Contact Sheet ===")
            await page.set_viewport_size({"width": 1440, "height": 900})
            contact_path = OUTPUT_DIR / "contact-sheet.png"
            await page.screenshot(path=contact_path, full_page=False)
            print(f"  Saved: {contact_path} ({os.path.getsize(contact_path)} bytes)")

            print(f"\nDone. {len(list(OUTPUT_DIR.glob('*.png')))} screenshots in {OUTPUT_DIR}")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
