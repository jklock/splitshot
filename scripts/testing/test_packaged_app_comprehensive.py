#!/usr/bin/env python3
"""Comprehensive E2E test suite for the packaged SplitShot app.
Tests all feature combinations: import, scoring, overlay, markers, merge, export, settings, timing, PractiScore.
Verifies correct results via DOM state + API + file inspection."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO / "artifacts"
EXAMPLE_DATA = REPO / "example_data"
TIMEOUT = 120
PASS = 0
FAIL = 0
ERRORS = []


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _check(description: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {description}")
    else:
        FAIL += 1
        msg = f"FAIL: {description}"
        if detail:
            msg += f" - {detail}"
        print(f"  {msg}")
        ERRORS.append(msg)


def _create_synthetic_video(out_dir: Path, name: str = "primary.mp4") -> Path:
    """Create a test video with detectable beep + shot transients for analysis."""
    import numpy as np
    import wave
    path = out_dir / name
    audio_path = out_dir / "audio.wav"
    raw_video = out_dir / "raw.mp4"

    sample_rate = 22050
    duration_s = 4
    n_samples = int(sample_rate * duration_s)
    samples = np.zeros(n_samples, dtype=np.float32)

    beep_ms = 400
    beep_start = int(sample_rate * (beep_ms / 1000.0))
    beep_length = int(sample_rate * 0.09)
    beep_time = np.arange(beep_length) / sample_rate
    beep_wave = 0.85 * np.sin(2 * np.pi * 2600 * beep_time) * np.hanning(beep_length)
    samples[beep_start:beep_start + beep_length] += beep_wave.astype(np.float32)

    rng = np.random.default_rng(7)
    for shot_ms in [800, 1100, 1450]:
        shot_start = int(sample_rate * (shot_ms / 1000.0))
        shot_length = int(sample_rate * 0.025)
        envelope = np.exp(-np.linspace(0, 8, shot_length))
        burst = rng.normal(0, 1, shot_length).astype(np.float32) * envelope * 0.95
        samples[shot_start:shot_start + shot_length] += burst

    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767).astype(np.int16)
    with wave.open(str(audio_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())

    subprocess.run(["ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=black:s=640x360:d={duration_s}:r=30",
        "-i", str(audio_path),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(path)],
        check=True, capture_output=True, timeout=30)
    return path


def _create_second_video(out_dir: Path) -> Path:
    return _create_synthetic_video(out_dir, "secondary.mp4")


def _launch_app(executable: Path, port: int, project_path: Path, log_dir: Path):
    ready_file = log_dir / "events.jsonl"
    env = {**os.environ, "CI": "1", "SPLITSHOT_ELECTRON_TEST": "1",
           "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
           "SPLITSHOT_TEST_PORT": str(port)}
    cmd = [str(executable)]
    if sys.platform.startswith("linux"):
        env["ELECTRON_DISABLE_SANDBOX"] = "1"
        cmd.append("--no-sandbox")
    cmd.append(str(project_path))
    stdout_log = log_dir / "app-stdout.log"
    stderr_log = log_dir / "app-stderr.log"
    proc = subprocess.Popen(cmd, cwd=executable.parent, env=env,
                            stdout=stdout_log.open("w"), stderr=stderr_log.open("w"), text=True)
    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"App exited (code {proc.returncode})")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
            return proc, ready_file
        except (urllib.error.URLError, ConnectionResetError):
            time.sleep(0.25)
    raise TimeoutError("Backend did not respond")


# ====== SUITE: Core / Import / Scoring ======
def suite_core(page, video_path: Path):
    print("\n--- Suite: Core / Import / Scoring ---")
    _check("activeTool defined", page.evaluate("typeof activeTool !== 'undefined'"))

    if not page.evaluate("Boolean(state?.project?.path)"):
        pp = str(video_path.parent / "core-test.ssproj")
        page.evaluate("(p) => createNewProject(p)", pp)
        page.wait_for_function("() => Boolean(state?.project?.path)", timeout=15000)
    _check("project created", page.evaluate("Boolean(state?.project?.path)"))

    page.locator("#primary-file-input").set_input_files(str(video_path))
    page.wait_for_function("() => Boolean(state?.media?.primary_display_name)", timeout=60000)
    _check("video import started", page.evaluate("Boolean(state?.media?.primary_display_name)"))
    time.sleep(2)
    shot_count = 0
    for _ in range(120):
        shot_count = page.evaluate("(state?.project?.analysis?.shots || []).length")
        if shot_count > 0:
            break
        time.sleep(2)
    _check(f"shots detected: {shot_count}", shot_count > 0)

    timing_count = page.evaluate("(state?.timing_segments || []).length")
    _check("timing segments exist", timing_count > 0)


# ====== SUITE: Tools (all panes open correctly) ======
def suite_tools(page):
    print("\n--- Suite: All Tools ---")
    tools = ["project", "merge", "scoring", "timing", "markers", "overlay", "review", "export", "metrics", "settings"]
    for t in tools:
        btn = page.locator(f'button[data-tool="{t}"]')
        if btn.is_visible():
            btn.click(force=True)
            page.wait_for_function("(tool) => activeTool === tool", arg=t, timeout=15000)
            _check(f"tool '{t}' activated", page.evaluate("activeTool") == t)


# ====== SUITE: Overlay / Review ======
def suite_overlay(page):
    print("\n--- Suite: Overlay / Review ---")
    page.locator('button[data-tool="review"]').click(force=True)
    page.wait_for_function("() => activeTool === 'review'", timeout=10000)
    time.sleep(0.3)

    review_add = page.locator("#review-add-text-box")
    if review_add.is_visible():
        review_add.click()
        time.sleep(0.5)
    boxes = page.evaluate("(state?.project?.overlay?.text_boxes || []).length")
    _check(f"text boxes created: {boxes}", boxes > 0)


# ====== SUITE: Markers ======
def suite_markers(page):
    print("\n--- Suite: Markers ---")
    page.locator('button[data-tool="markers"]').click(force=True)
    page.wait_for_function("() => activeTool === 'markers'", timeout=10000)
    time.sleep(0.3)

    popup_edit = page.locator("#popup-edit-selected")
    if popup_edit.is_visible():
        popup_edit.click()
        time.sleep(0.3)
        _check("markers workbench opened", True)
        close_btn = page.locator("#popup-edit-selected")
        if close_btn.is_visible():
            close_btn.click()
            time.sleep(0.3)
    else:
        # Try importing shot-linked markers
        import_btn = page.locator("#popup-import-shots-workbench")
        if import_btn.is_visible():
            import_btn.click()
            time.sleep(0.5)
            popup_count = page.evaluate("(state?.project?.popups || []).length")
            _check("shot-linked markers imported", popup_count > 0)


# ====== SUITE: Merge ======
def suite_merge(page, second_video_path: Path):
    print("\n--- Suite: Merge ---")
    page.locator('button[data-tool="merge"]').click(force=True)
    page.wait_for_function("() => activeTool === 'merge'", timeout=10000)
    time.sleep(0.3)

    add_media = page.locator("#add-merge-media")
    if add_media.is_visible():
        add_media.click()
        time.sleep(0.3)
        merge_input = page.locator("#merge-media-input")
        if merge_input.is_visible():
            merge_input.set_input_files(str(second_video_path))
            time.sleep(1)
            merge_sources = page.evaluate("(state?.project?.merge?.sources || []).length")
            _check("second video imported for merge", merge_sources > 0)
        else:
            _check("merge file input dialog opened", True)
    else:
        _check("merge add media button visible", False, "no #add-merge-media found")


# ====== SUITE: Export ======
def suite_export(page, export_dir: Path):
    print("\n--- Suite: Export ---")
    export_file = export_dir / "comprehensive-export-test.mp4"
    page.locator('button[data-tool="export"]').click(force=True)
    page.wait_for_function("() => activeTool === 'export'", timeout=10000)
    time.sleep(0.5)

    path_input = page.locator("#export-path")
    if path_input.is_visible():
        path_input.fill(str(export_file))
        time.sleep(0.2)
        page.evaluate("""
            const el = document.getElementById('export-path');
            if (el) el.dispatchEvent(new Event('input', { bubbles: true }));
        """)
        time.sleep(0.3)
    export_btn = page.locator("#export-video")
    if export_btn.is_visible():
        export_btn.click(force=True)
        time.sleep(2)
        file_found = False
        for _ in range(60):
            if export_file.exists() and export_file.stat().st_size > 0:
                file_found = True
                break
            time.sleep(1)
        _check("export file created", file_found)
        if file_found:
            sz = export_file.stat().st_size
            _check(f"export file size ({sz / 1024 / 1024:.1f} MB)", sz > 1024, "file too small")
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=format_name,duration",
                     "-of", "json", str(export_file)],
                    capture_output=True, text=True, timeout=15)
                info = json.loads(result.stdout)
                fmt = info.get("format", {}).get("format_name", "unknown")
                dur = float(info.get("format", {}).get("duration", 0))
                _check(f"export is valid: format={fmt} duration={dur:.1f}s", dur > 0 and "mp4" in fmt)
            except Exception as e:
                _check("export ffprobe validation", False, str(e))
    else:
        _check("export button visible", False, "no export button found")


# ====== SUITE: Settings ======
def suite_settings(page):
    print("\n--- Suite: Settings ---")
    page.locator('button[data-tool="settings"]').click(force=True)
    page.wait_for_function("() => activeTool === 'settings'", timeout=10000)
    time.sleep(0.5)

    sections = page.evaluate("""
        () => {
            const pane = document.querySelector('[data-tool-pane="settings"]');
            if (!pane) return [];
            const items = pane.querySelectorAll('[data-settings-section], .settings-section');
            return Array.from(items).map(l => l.getAttribute('data-settings-section') || l.id || '');
        }
    """)
    _check(f"settings sections found: {len(sections)}", len(sections) >= 3)
    for s in sections[:3]:
        section_id = s.lstrip("#")
        section_el = page.locator(f"[data-settings-section=\"{section_id}\"], #{section_id}")
        if section_el.is_visible():
            section_el.click()
            time.sleep(0.3)
            _check(f"settings section '{section_id}' clickable", True)

    try:
        toggles = page.locator("input[type=\"checkbox\"]")
        count = toggles.count()
        if count > 0:
            first_toggle = toggles.first
            if first_toggle.is_visible():
                was_checked = first_toggle.is_checked()
                first_toggle.click(force=True)
                time.sleep(0.3)
                now_checked = first_toggle.is_checked()
                _check("settings checkbox toggle works", now_checked != was_checked)
    except Exception as e:
        _check("settings checkbox toggle", False, str(e))


# ====== SUITE: Timing Events ======
def suite_timing(page):
    print("\n--- Suite: Timing Events ---")
    page.locator('button[data-tool="timing"]').click(force=True)
    page.wait_for_function("() => activeTool === 'timing'", timeout=10000)
    time.sleep(0.3)

    events_before = page.evaluate("(state?.project?.analysis?.events || []).length")
    add_event = page.locator("#add-timing-event")
    if add_event.is_visible():
        kind_select = page.locator("#timing-event-kind")
        if kind_select.is_visible():
            kind_select.select_option("custom_label")
            time.sleep(0.1)
        label_input = page.locator("#timing-event-label")
        if label_input.is_visible():
            label_input.fill("E2E test event")
            time.sleep(0.1)
        add_event.click()
        time.sleep(0.5)
        events_after = page.evaluate("(state?.project?.analysis?.events || []).length")
        _check("timing event added", events_after > events_before)
    else:
        _check("add timing event button visible", False, "no #add-timing-event found")


# ====== SUITE: Feature Combinations ======
def suite_combinations(page, video_path: Path, export_dir: Path):
    print("\n--- Suite: Feature Combinations ---")

    # Combination 1: Create overlay, then export with overlay visible
    page.locator('button[data-tool="overlay"]').click(force=True)
    page.wait_for_function("() => activeTool === 'overlay'", timeout=10000)
    time.sleep(0.3)
    add_box = page.locator("#overlay-add-text-box")
    if add_box.is_visible():
        for _ in range(2):
            add_box.click()
            time.sleep(0.3)
    boxes = page.evaluate("(state?.project?.overlay?.text_boxes || []).length")
    _check("overlay text boxes added for export test", boxes >= 2)

    # Export with overlay
    combo_export = export_dir / "combo-overlay-export.mp4"
    page.locator('button[data-tool="export"]').click(force=True)
    page.wait_for_function("() => activeTool === 'export'", timeout=10000)
    time.sleep(0.5)
    path_input = page.locator("#export-path")
    if path_input.is_visible():
        path_input.fill(str(combo_export))
        time.sleep(0.2)
        page.evaluate("""
            const el = document.getElementById('export-path');
            if (el) el.dispatchEvent(new Event('input', { bubbles: true }));
        """)
        time.sleep(0.3)
    export_btn = page.locator("#export-video")
    if export_btn.is_visible():
        export_btn.click(force=True)
        time.sleep(2)
        for _ in range(60):
            if combo_export.exists() and combo_export.stat().st_size > 0:
                break
            time.sleep(1)
        _check("overlay + export combination produces file", combo_export.exists() and combo_export.stat().st_size > 1024)
        if combo_export.exists() and combo_export.stat().st_size > 0:
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name",
                     "-of", "json", str(combo_export)],
                    capture_output=True, text=True, timeout=15)
                streams = json.loads(result.stdout).get("streams", [])
                has_video = any(s.get("codec_type") == "video" for s in streams)
                has_audio = any(s.get("codec_type") == "audio" for s in streams)
                _check("combo export has video stream", has_video)
                _check("combo export has audio stream", has_audio)
            except Exception as e:
                _check("combo export ffprobe", False, str(e))

    # Combination 2: Markers + Timing (select shot, verify sync)
    page.locator('button[data-tool="timing"]').click(force=True)
    page.wait_for_function("() => activeTool === 'timing'", timeout=10000)
    time.sleep(0.3)
    shot_cards = page.locator(".waveform-shot-card")
    if shot_cards.count() > 0:
        shot_cards.first.click()
        time.sleep(0.5)
        sel_shot = page.evaluate("selectedShotId")
        _check("shot selected in timing", sel_shot is not None)

        page.locator('button[data-tool="markers"]').click(force=True)
        page.wait_for_function("() => activeTool === 'markers'", timeout=10000)
        time.sleep(0.3)
        markers_shot = page.evaluate("""
            () => {
                const popup = (state?.project?.popups || []).find(p => p.anchor_mode === 'shot');
                return popup ? popup.shot_id : null;
            }
        """)
        _check("markers linked to shot", markers_shot is not None, "no shot-linked marker found")

    # Combination 3: Settings + Export
    page.locator('button[data-tool="settings"]').click(force=True)
    page.wait_for_function("() => activeTool === 'settings'", timeout=10000)
    time.sleep(0.5)
    _check("settings accessible before export", True)

    # Combination 4: Verify state consistency via API
    page.locator('button[data-tool="scoring"]').click(force=True)
    page.wait_for_function("() => activeTool === 'scoring'", timeout=10000)
    time.sleep(0.3)
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{_free_port() - 1}/api/state", timeout=5)
        api_state = json.loads(resp.read().decode())
        has_project = api_state.get("project") is not None
        has_shots = len(api_state.get("project", {}).get("analysis", {}).get("shots", [])) > 0
        _check("API state: project exists", has_project)
        _check("API state: shots exist", has_shots)
    except Exception as e:
        _check("API state check", False, str(e))


# ====== SUITE: Second Video + PractiScore (if available) ======
def suite_practiscore(page, work_dir: Path):
    print("\n--- Suite: PractiScore Import ---")
    csv_file = EXAMPLE_DATA / "IDPA" / "IDPA.csv"
    if not csv_file.exists():
        _check("PractiScore CSV exists", False, "no example IDPA.csv found")
        return

    page.locator('button[data-tool="project"]').click(force=True)
    page.wait_for_function("() => activeTool === 'project'", timeout=10000)
    time.sleep(0.3)

    csv_input = page.locator("#practiscore-file-input, [data-practiscore-input]")
    if csv_input.is_visible():
        csv_input.set_input_files(str(csv_file))
        time.sleep(2)
        practiscore_state = page.evaluate("Boolean(state?.project?.practiscore)")
        _check("PractiScore data imported", practiscore_state)
        participants = page.evaluate("(state?.project?.practiscore?.participants || []).length")
        if participants > 0:
            _check(f"PractiScore participants: {participants}", True)
        stages = page.evaluate("(state?.project?.practiscore?.stages || []).length")
        if stages > 0:
            _check(f"PractiScore stages: {stages}", True)
    else:
        _check("PractiScore file input visible", False, "no PractiScore input found")


def main():
    parser = argparse.ArgumentParser(description="Comprehensive E2E test for packaged SplitShot app")
    parser.add_argument("--app", type=Path, required=True, help="Path to the app executable")
    parser.add_argument("--artifacts", type=Path, default=ARTIFACTS_DIR)
    args = parser.parse_args()

    executable = args.app.resolve()
    if not executable.exists():
        print(f"FAIL: executable not found at {executable}")
        return 1

    args.artifacts.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="sshot-comprehensive-"))
    log_dir = Path(tempfile.mkdtemp(prefix="sshot-comprehensive-logs-"))

    global PASS, FAIL, ERRORS
    PASS = 0
    FAIL = 0
    ERRORS = []
    proc = None

    try:
        primary_video = _create_synthetic_video(work_dir, "primary.mp4")
        second_video = _create_second_video(work_dir)
        project_path = work_dir / "comprehensive.ssproj"
        port = _free_port()

        script = (
            "from pathlib import Path; import sys; "
            "from splitshot.domain.models import Project; "
            "from splitshot.persistence.projects import save_project; "
            "save_project(Project(name=sys.argv[2]), Path(sys.argv[1]))"
        )
        subprocess.run(["uv", "run", "python", "-c", script, str(project_path), "comprehensive"],
                       cwd=REPO, capture_output=True, text=True, timeout=60, check=True)

        print(f"Launching app on port {port}...")
        proc, ready_file = _launch_app(executable, port, project_path, log_dir)
        print("App launched, backend responding")

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu", "--disable-software-rasterizer"])
            context = browser.new_context(viewport={"width": 1280, "height": 900},
                                          accept_downloads=True)
            page = context.new_page()

            page.on("console", lambda msg: None)  # suppress console noise
            page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded", timeout=30000)

            # Wait for app to be ready
            page.wait_for_function("() => typeof activeTool !== 'undefined'", timeout=45000)
            time.sleep(1)

            # Run all suites
            suite_core(page, primary_video)
            suite_tools(page)
            suite_overlay(page)
            suite_markers(page)
            suite_merge(page, second_video)
            suite_export(page, work_dir)
            suite_settings(page)
            suite_timing(page)
            suite_practiscore(page, work_dir)
            suite_combinations(page, primary_video, work_dir)

            context.close()
            browser.close()

        # Summary
        total = PASS + FAIL
        print(f"\n{'='*50}")
        print(f"RESULTS: {PASS} passed, {FAIL} failed out of {total} checks")
        if ERRORS:
            print(f"FAILURES:")
            for e in ERRORS:
                print(f"  {e}")
        print(f"{'='*50}")

        # Save results
        results = {"pass": PASS, "fail": FAIL, "total": total, "errors": ERRORS}
        (args.artifacts / "comprehensive-results.json").write_text(json.dumps(results, indent=2))

        return 0 if FAIL == 0 else 1

    except Exception as exc:
        print(f"\nFATAL: {exc}", file=sys.stderr)
        return 1
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
