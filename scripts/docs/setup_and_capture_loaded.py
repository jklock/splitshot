#!/usr/bin/env python3
"""Set up project data and capture loaded-state Automate3 view screenshots."""
import asyncio
import os
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "screenshots" / "automate3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://127.0.0.1:8765"
MEDIA_PATH = str((Path(__file__).resolve().parent.parent.parent / "docs" / "Clip1.MP4").absolute())

async def api_post(page, path, body=None):
    """Call the SplitShot API."""
    result = await page.evaluate(f"""
        async () => {{
            const resp = await fetch('{path}', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({json.dumps(body) if body else '{}'})
            }});
            const text = await resp.text();
            try {{ return JSON.parse(text); }} catch(e) {{ return {{text: text}}; }}
        }}
    """)
    print(f"  POST {path} -> {json.dumps(result)[:120]}")
    return result

async def api_get(page, path):
    result = await page.evaluate(f"""
        async () => {{
            const resp = await fetch('{path}');
            try {{ return await resp.json(); }} catch(e) {{ return null; }}
        }}
    """)
    return result

async def switch_view(page, view_name):
    nav_map = {"stage": "nav-stage", "match": "nav-match", "library": "nav-library"}
    btn_id = nav_map.get(view_name)
    if btn_id:
        await page.click(f"#{btn_id}")
    elif view_name == "landing":
        await page.click("#shell-go-home")
    await page.wait_for_timeout(2000)

async def capture_view(page, view_name, filename):
    print(f"  Capturing {filename}...")
    view_el = await page.query_selector(f"#view-{view_name}")
    if view_el:
        path = OUTPUT_DIR / filename
        await view_el.screenshot(path=path)
        print(f"    Saved: {path} ({os.path.getsize(path)} bytes)")
        return path
    else:
        print(f"    WARNING: #view-{view_name} not found")
        return None

async def setup_project(page):
    """Create a project, import media, save it."""
    print("\n=== Setting up project ===")
    
    # Create new project
    result = await page.evaluate("""
        async () => {
            const resp = await fetch('/api/project/new', { method: 'POST' });
            return await resp.json();
        }
    """)
    print(f"  New project: {json.dumps(result)[:200]}")
    await page.wait_for_timeout(1000)

    # Import media via the correct API endpoint
    result = await api_post(page, "/api/import/primary", {"path": MEDIA_PATH})
    await page.wait_for_timeout(3000)
    
    # Save project with a temporary path
    project_path = str(Path(tempfile.gettempdir()) / "splitshot_screenshot_loaded.splitshot")
    result = await page.evaluate(f"""
        async () => {{
            const resp = await fetch('/api/project/save', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{path: {json.dumps(project_path)}}})
            }});
            return await resp.json();
        }}
    """)
    print(f"  Save project: {json.dumps(result)[:200]}")
    await page.wait_for_timeout(1000)

async def setup_match(page):
    """Create a workspace with stages."""
    print("\n=== Setting up match/workspace ===")
    
    result = await api_post(page, "/api/workspace/new")
    await page.wait_for_timeout(1000)
    
    # Add Stage 1
    result = await api_post(page, "/api/workspace/stage/add", {
        "stage_id": "stage_1",
        "display_name": "Stage 1 - Warmup",
        "project_path": "."
    })
    await page.wait_for_timeout(500)
    
    # Add Stage 2
    result = await api_post(page, "/api/workspace/stage/add", {
        "stage_id": "stage_2", 
        "display_name": "Stage 2 - Box Drill",
        "project_path": "."
    })
    await page.wait_for_timeout(500)
    
    # Save workspace
    project_path = str(Path(tempfile.gettempdir()) / "splitshot_screenshot_loaded.splitshot")
    result = await api_post(page, "/api/workspace/save", {"path": project_path, "name": "Practice Match"})
    await page.wait_for_timeout(1000)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        try:
            await page.goto(BASE_URL)
            await page.wait_for_selector("#app-shell", timeout=15000)
            await page.wait_for_timeout(2000)

            # Setup: create project and import media
            await switch_view(page, "stage")
            await setup_project(page)
            
            # Capture loaded stage with media
            print("\n=== Capturing loaded stage ===")
            await capture_view(page, "stage", "loaded-stage.png")

            # Setup and capture loaded match
            await setup_match(page)
            await switch_view(page, "match")
            await page.wait_for_timeout(2000)
            print("\n=== Capturing loaded match ===")
            await capture_view(page, "match", "loaded-match.png")

            # Capture loaded library
            await switch_view(page, "library")
            await page.wait_for_timeout(2000)
            print("\n=== Capturing loaded library ===")
            await capture_view(page, "library", "loaded-library.png")

            # Contact sheet
            print("\n=== Final contact sheet ===")
            await switch_view(page, "landing")
            await page.wait_for_timeout(1000)
            contact_path = OUTPUT_DIR / "contact-sheet-final.png"
            await page.screenshot(path=contact_path, full_page=False)
            print(f"  Saved: {contact_path} ({os.path.getsize(contact_path)} bytes)")

            # Summary
            print(f"\n=== Done. Screenshots in {OUTPUT_DIR} ===")
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
