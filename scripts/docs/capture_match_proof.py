#!/usr/bin/env python3
"""Capture Match proof screenshots and output artifacts for the shared-shell contract."""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from playwright.async_api import Page, async_playwright

from splitshot.analysis.detection import analyze_video_audio
from splitshot.browser.server import BrowserControlServer
from splitshot.domain.models import Project
from splitshot.media.probe import probe_video
from splitshot.persistence.projects import save_project
from splitshot.persistence.workspaces import workspace_stage_path
from splitshot.ui.controller import ProjectController


REPO_ROOT = Path(__file__).resolve().parents[2]
MEDIA_PATH = REPO_ROOT / "docs" / "Clip1.MP4"
SECONDARY_MEDIA_PATH = REPO_ROOT / "tests" / "fixtures" / "media" / "stage.mp4"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%d")
OUTPUT_DIR = REPO_ROOT / "artifacts" / f"match-proof-{STAMP}"
SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"
WORKSPACE_DIR = OUTPUT_DIR / "workspace"
PROOF_JSON = OUTPUT_DIR / "proof-results.json"
SUMMARY_TXT = OUTPUT_DIR / "summary.txt"


class ProofFailure(RuntimeError):
    pass


def _configure_stage_project(video_path: Path, name: str, stage_path: Path) -> None:
    project = Project(name=name)
    project.primary_video = probe_video(video_path)
    analysis = analyze_video_audio(video_path, threshold=0.35)
    project.analysis.beep_time_ms_primary = analysis.beep_time_ms
    project.analysis.shots = analysis.shots
    project.export.target_width = 160
    project.export.target_height = 90
    project.export.video_bitrate_mbps = 1
    project.export.ffmpeg_preset = "ultrafast"
    stage_path.mkdir(parents=True, exist_ok=True)
    save_project(project, stage_path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_record(path: Path, *, assertions: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "file": path.name,
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "assertions": assertions or {},
        "status": "pass",
    }


def _build_loaded_controller() -> tuple[ProjectController, dict[str, object], dict[str, object]]:
    controller = ProjectController()
    proof_state: dict[str, object] = {}

    controller.new_workspace()
    controller.workspace.name = "Match Proof"
    controller.workspace.description = "Shared-shell Match proof bundle capture"
    controller.workspace_add_stage("stage_1", "Stage 1")
    controller.workspace_add_stage("stage_2", "Stage 2")
    controller.workspace.stage_entries["stage_1"].source_media_present = True
    controller.workspace.stage_entries["stage_2"].source_media_present = True

    workspace_path = WORKSPACE_DIR / "match-proof"
    controller.save_workspace(str(workspace_path))

    _configure_stage_project(MEDIA_PATH, "Stage 1", workspace_stage_path(workspace_path, "stage_1"))
    _configure_stage_project(
        SECONDARY_MEDIA_PATH,
        "Stage 2",
        workspace_stage_path(workspace_path, "stage_2"),
    )
    controller.open_workspace(str(workspace_path))

    controller.output_profile_create(
        "stage",
        "stage_1",
        "Single Video",
        "stage_output",
        metric_caption_preset={"lead_in_padding_ms": 0, "tail_padding_ms": 0},
    )
    controller.output_profile_create(
        "stage",
        "stage_2",
        "Single Video",
        "stage_output",
        metric_caption_preset={"lead_in_padding_ms": 0, "tail_padding_ms": 0},
    )

    primary_clip = controller.workspace_stage_clip_add(
        "stage_1", str(SECONDARY_MEDIA_PATH), "primary"
    )[0]
    follow_clip = controller.workspace_stage_clip_add("stage_1", str(MEDIA_PATH), "follow")[-1]
    stage_2_primary = controller.workspace_stage_clip_add("stage_2", str(MEDIA_PATH), "primary")[0]
    controller.workspace_stage_clip_add("stage_2", str(SECONDARY_MEDIA_PATH), "follow")

    profile = controller.output_profile_create(
        "stage",
        "stage_1",
        "Composite",
        "stage_composite",
    )
    controller.angle_director_override_cut(
        "stage_1",
        primary_clip["clip_id"],
        0,
        start_ms=0,
        duration_ms=700,
        output_id=profile["output_id"],
    )
    controller.angle_director_override_cut(
        "stage_1",
        follow_clip["clip_id"],
        1,
        start_ms=0,
        duration_ms=900,
        output_id=profile["output_id"],
    )
    stage_2_profile = controller.output_profile_create(
        "stage",
        "stage_2",
        "Composite",
        "stage_composite",
    )
    controller.angle_director_override_cut(
        "stage_2",
        stage_2_primary["clip_id"],
        0,
        start_ms=0,
        duration_ms=900,
        output_id=stage_2_profile["output_id"],
    )

    return (
        controller,
        proof_state,
        {
            "workspace_path": str(workspace_path),
            "profile_output_id": profile["output_id"],
            "primary_clip_id": primary_clip["clip_id"],
        },
    )


def _capture_auto_seed_membership_artifacts() -> dict[str, object]:
    auto_seed_dir = WORKSPACE_DIR / "auto-seed"
    auto_seed_dir.mkdir(parents=True, exist_ok=True)

    workspace_owner = ProjectController()
    workspace_owner.new_workspace()
    workspace_owner.workspace.name = "Owning Match"
    workspace_path = auto_seed_dir / "owning-match"
    workspace_owner.save_workspace(str(workspace_path))

    workspace_owner.new_project()
    workspace_owner.project.name = "Auto Attached Stage"
    stage_path = workspace_path / "Stages" / "stage_auto"
    workspace_owner.save_project(str(stage_path))

    attached = ProjectController()
    attached.open_project(str(stage_path))

    standalone = ProjectController()
    standalone.new_project()
    standalone.project.name = "Standalone Stage"
    standalone_path = auto_seed_dir / "standalone-stage"
    standalone.save_project(str(standalone_path))

    payload = {
        "saved_workspace_attach": {
            "workspace_path": str(attached.workspace_path) if attached.workspace_path else None,
            "active_stage_id": attached.active_stage_id,
            "return_to_workspace_available": attached._return_to_workspace_available,
            "stage_entries": sorted(attached.workspace.stage_entries.keys())
            if attached.workspace
            else [],
        },
        "unsaved_workspace_create": {
            "workspace_path": str(standalone.workspace_path) if standalone.workspace_path else None,
            "active_stage_id": standalone.active_stage_id,
            "stage_entries": sorted(standalone.workspace.stage_entries.keys())
            if standalone.workspace
            else [],
            "relative_project_path": standalone.workspace.stage_entries[
                standalone.project.id
            ].relative_project_path
            if standalone.workspace and standalone.project.id in standalone.workspace.stage_entries
            else None,
        },
    }
    path = WORKSPACE_DIR / "auto-seed-proof.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"path": str(path), "payload": payload}


async def _open_match_surface(page: Page) -> None:
    await page.evaluate("() => setActiveSurface('multi')")
    await page.wait_for_function("() => activeSurface === 'multi'", timeout=10_000)
    await page.wait_for_selector("#view-match.active", timeout=10_000)


async def _open_match_section(page: Page, section_id: str) -> None:
    await page.locator(f'[data-workspace-target="{section_id}"]').click(force=True)
    await page.wait_for_function(
        "(targetId) => document.getElementById(targetId)?.hidden === false",
        arg=section_id,
        timeout=10_000,
    )


async def _capture_match_screenshot(
    page: Page, filename: str, *, min_text_length: int = 0
) -> dict[str, object]:
    path = SCREENSHOT_DIR / filename
    await page.locator("#view-match").screenshot(path=path)
    assertions = await page.evaluate(
        """() => {
          const view = document.getElementById('view-match');
          const rect = view?.getBoundingClientRect();
          return {
            activeSurface: typeof activeSurface === 'string' ? activeSurface : '',
            viewActive: Boolean(view?.classList.contains('active')),
            width: Math.round(rect?.width || 0),
            height: Math.round(rect?.height || 0),
            textLength: (view?.innerText || '').length,
            stageCards: document.querySelectorAll('#workspace-stage-list .match-stage-card').length,
          };
        }"""
    )
    failures: list[str] = []
    if assertions["activeSurface"] != "multi":
        failures.append("match surface not active")
    if not assertions["viewActive"]:
        failures.append("match view not active")
    if assertions["width"] <= 0 or assertions["height"] <= 0:
        failures.append("match view bounds invalid")
    if assertions["textLength"] < min_text_length:
        failures.append("match view text too short")
    if failures:
        raise ProofFailure(f"{filename} assertions failed: {', '.join(failures)}")
    return _file_record(path, assertions=assertions)


async def _capture_empty_match() -> dict[str, object]:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    console_errors: list[str] = []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )
            page.on("pageerror", lambda exc: console_errors.append(str(exc)))
            await page.goto(server.url, wait_until="domcontentloaded")
            await page.wait_for_selector("#app-shell", timeout=15_000)
            await _open_match_surface(page)
            await page.wait_for_function(
                "() => (document.getElementById('view-match')?.innerText || '').includes('No Match Open')",
                timeout=10_000,
            )
            screenshot = await _capture_match_screenshot(
                page, "match-empty.png", min_text_length=20
            )
            await browser.close()
        if console_errors:
            raise ProofFailure(f"console errors during empty Match capture: {console_errors}")
        return screenshot
    finally:
        server.shutdown()


async def _capture_loaded_match() -> dict[str, object]:
    controller, proof_state, seeded = _build_loaded_controller()
    auto_seed = _capture_auto_seed_membership_artifacts()
    console_errors: list[str] = []
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    screenshots: list[dict[str, object]] = []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )
            page.on("pageerror", lambda exc: console_errors.append(str(exc)))
            await page.goto(server.url, wait_until="domcontentloaded")
            await page.wait_for_selector("#app-shell", timeout=15_000)
            await _open_match_surface(page)
            await page.wait_for_function(
                "() => document.querySelectorAll('#workspace-stage-list .match-stage-card').length === 2",
                timeout=10_000,
            )

            await _open_match_section(page, "match-section-stages")
            await page.locator(
                '#workspace-stage-list .match-stage-card[data-stage-id="stage_1"]'
            ).click()
            await page.wait_for_function(
                """() => document.querySelector('#workspace-stage-list .match-stage-card[data-stage-id="stage_1"]')?.classList.contains('selected') === true""",
                timeout=10_000,
            )
            await page.wait_for_function(
                "() => document.getElementById('match-stage-detail-panel')?.hidden !== true",
                timeout=10_000,
            )
            screenshots.append(
                await _capture_match_screenshot(page, "match-loaded.png", min_text_length=120)
            )

            await _open_match_section(page, "match-section-recap")
            await page.wait_for_function(
                "() => document.querySelectorAll('#match-recap-panel .recap-stage-check').length === 2",
                timeout=10_000,
            )
            await page.locator("#match-recap-panel .recap-stage-check").nth(1).uncheck()
            await page.locator("#recap-transition").select_option("fade")
            await page.locator("#recap-result-card").select_option("end")
            await page.locator("#recap-render").click()
            await page.wait_for_function(
                "() => (document.getElementById('recap-status')?.textContent || '').includes('recap.mp4')",
                timeout=10_000,
            )
            screenshots.append(
                await _capture_match_screenshot(page, "match-recap.png", min_text_length=120)
            )

            await _open_match_section(page, "match-section-composite")
            await page.wait_for_function(
                "() => document.querySelectorAll('#stage-composite-list .automation-row').length === 2",
                timeout=10_000,
            )
            const_row_selector = (
                f'#stage-composite-list .automation-row[data-clip-id="{seeded["primary_clip_id"]}"]'
            )
            row = page.locator(const_row_selector)
            await row.locator("label", has_text="Cut slot").locator("input").fill("1")
            await row.locator("label", has_text="Start (ms)").locator("input").fill("250")
            await row.locator("label", has_text="Duration (ms)").locator("input").fill("500")
            await row.locator("button", has_text="Apply Cut").click()
            await page.wait_for_function(
                """() => {
                    const detail = document.getElementById('output-profile-detail');
                    return Boolean(detail?.textContent?.includes('"start_ms": 250'))
                      && Boolean(detail?.textContent?.includes('"duration_ms": 500'));
                }""",
                timeout=10_000,
            )
            composite_detail_path = WORKSPACE_DIR / "composite-plan-detail.txt"
            composite_detail_path.write_text(
                await page.locator("#output-profile-detail").text_content() or "",
                encoding="utf-8",
            )
            screenshots.append(
                await _capture_match_screenshot(page, "match-composite.png", min_text_length=120)
            )

            await _open_match_section(page, "match-section-export")
            await page.wait_for_function(
                "() => document.querySelectorAll('#batch-export-queue .batch-export-item').length === 2",
                timeout=10_000,
            )
            await page.locator("#batch-recipe").select_option("stage_composite")
            await page.locator("#batch-export-start").click()
            await page.wait_for_function(
                "() => (document.getElementById('batch-export-status')?.textContent || '').includes('Exported 2 stage')",
                timeout=10_000,
            )
            screenshots.append(
                await _capture_match_screenshot(page, "match-export.png", min_text_length=120)
            )

            await page.locator("#match-open-settings").click(force=True)
            await page.wait_for_function(
                "() => document.getElementById('match-section-settings')?.hidden === false",
                timeout=10_000,
            )
            screenshots.append(
                await _capture_match_screenshot(page, "match-settings.png", min_text_length=120)
            )
            await browser.close()

        if console_errors:
            raise ProofFailure(f"console errors during Match proof capture: {console_errors}")

        controller.workspace_export(stage_id="stage_1", recipe="stage_output")
        composite_plan = controller.angle_director_plan("stage_1", str(seeded["profile_output_id"]))
        composite_plan_path = WORKSPACE_DIR / "composite-plan.json"
        composite_plan_path.write_text(json.dumps(composite_plan, indent=2), encoding="utf-8")

        workspace_root = Path(seeded["workspace_path"])
        source_recap_output = workspace_root / "recap.mp4"
        recap_output = WORKSPACE_DIR / "recap.mp4"
        if source_recap_output.exists():
            shutil.copy2(source_recap_output, recap_output)

        exports_dir = WORKSPACE_DIR / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        source_exports = sorted((workspace_root / "exports").glob("*.mp4"))
        published_export_paths: list[Path] = []
        for source_path in source_exports:
            published_path = exports_dir / source_path.name
            shutil.copy2(source_path, published_path)
            published_export_paths.append(published_path)

        composite_outputs = [
            path for path in published_export_paths if path.name.endswith("-stage_composite.mp4")
        ]
        single_output_path = next(
            path for path in published_export_paths if path.name.endswith("-stage_output.mp4")
        )
        summary = {
            "workspace": str(WORKSPACE_DIR),
            "export_success": len(composite_outputs) == 2,
            "export_outputs": len(composite_outputs),
            "recap_success": recap_output.is_file(),
            "recap_output": str(recap_output),
            "single_stage_output_success": single_output_path.is_file(),
            "single_stage_output": str(single_output_path),
            "auto_seed_saved_workspace": auto_seed["payload"]["saved_workspace_attach"][
                "return_to_workspace_available"
            ],
            "auto_seed_unsaved_workspace": auto_seed["payload"]["unsaved_workspace_create"][
                "workspace_path"
            ]
            is None,
        }
        SUMMARY_TXT.write_text(
            "\n".join(
                [
                    f"workspace={summary['workspace']}",
                    f"export_success={summary['export_success']}",
                    f"export_outputs={summary['export_outputs']}",
                    f"recap_success={summary['recap_success']}",
                    f"recap_output={summary['recap_output']}",
                    f"single_stage_output_success={summary['single_stage_output_success']}",
                    f"single_stage_output={summary['single_stage_output']}",
                    f"auto_seed_saved_workspace={summary['auto_seed_saved_workspace']}",
                    f"auto_seed_unsaved_workspace={summary['auto_seed_unsaved_workspace']}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        return {
            "screenshots": screenshots,
            "summary": summary,
            "seeded": seeded,
            "proof_state": proof_state,
            "auto_seed": auto_seed,
            "composite_plan": {
                "path": str(composite_plan_path),
                "has_overrides": composite_plan.get("has_overrides"),
                "cut_count": len(composite_plan.get("cut_plan") or []),
            },
            "composite_detail_path": str(composite_detail_path),
            "export_outputs": [str(path) for path in composite_outputs] + [str(single_output_path)],
        }
    finally:
        server.shutdown()


async def run() -> dict[str, object]:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    empty_match = await _capture_empty_match()
    loaded = await _capture_loaded_match()
    proof = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "kind": "match-proof",
        "output_dir": str(OUTPUT_DIR),
        "empty_match": empty_match,
        "loaded": loaded,
    }
    PROOF_JSON.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    return proof


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
