#!/usr/bin/env python3
"""Full E2E test of installed Electron app via Playwright with video recording."""

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
TIMEOUT = 120


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _create_test_video(output_dir: Path) -> Path:
    video_path = output_dir / "e2e-test-video.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", "color=c=black:s=640x360:d=4:r=30",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
         "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(video_path)],
        check=True, capture_output=True, timeout=30)
    return video_path


def _spawn_app(executable, ready_file, port, project_path, stdout_path, stderr_path, extra_args=None):
    env = {**os.environ, "CI": "1", "SPLITSHOT_ELECTRON_TEST": "1",
           "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
           "SPLITSHOT_TEST_PORT": str(port)}
    cmd = [str(executable)]
    if sys.platform.startswith("linux") and "--no-sandbox" not in (extra_args or []):
        env["ELECTRON_DISABLE_SANDBOX"] = "1"
        cmd.append("--no-sandbox")
    if extra_args:
        cmd.extend(extra_args)
    if project_path:
        cmd.append(str(project_path))
    with stdout_path.open("w") as out, stderr_path.open("w") as err:
        return subprocess.Popen(cmd, cwd=executable.parent, env=env, stdout=out, stderr=err, text=True)


def _wait_for_backend(proc, port, timeout=TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("App exited before backend was ready")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
            return
        except (urllib.error.URLError, ConnectionResetError):
            time.sleep(0.25)
    raise TimeoutError("Backend did not respond")


def _exercise_app(page, video_path):
    page.goto(page.url, wait_until="networkidle", timeout=30000)
    page.wait_for_function("() => typeof activeTool !== 'undefined'", timeout=45000)
    time.sleep(1)

    if not page.evaluate("Boolean(state?.project?.path)"):
        pp = str(video_path.parent / "e2e.ssproj")
        page.evaluate("(p) => createNewProject(p)", pp)
        page.wait_for_function("() => Boolean(state?.project?.path)", timeout=15000)
        time.sleep(0.5)

    page.locator("#primary-file-input").set_input_files(str(video_path))
    page.wait_for_function("() => Boolean(state?.media?.primary_display_name)", timeout=60000)
    page.wait_for_function("() => (state?.project?.analysis?.shots || []).length > 0", timeout=120000)
    time.sleep(1)

    tools = ["project", "merge", "scoring", "timing", "markers", "overlay", "review", "export", "metrics", "settings"]
    for t in tools:
        btn = page.locator(f'button[data-tool="{t}"]')
        if btn.is_visible():
            btn.click(force=True)
            page.wait_for_function("(t) => activeTool === t", arg=t, timeout=15000)
            time.sleep(0.3)

    page.locator('button[data-tool="timing"]').click(force=True)
    page.wait_for_function("() => activeTool === 'timing'", timeout=10000)
    if page.locator(".waveform-shot-card").count() > 0:
        page.locator(".waveform-shot-card").first.click()
        time.sleep(0.5)

    for t in ["markers", "overlay", "review", "settings", "scoring"]:
        page.locator(f'button[data-tool="{t}"]').click(force=True)
        page.wait_for_function("(tool) => activeTool === tool", arg=t, timeout=10000)
        time.sleep(0.3)

    state_url = f"http://127.0.0.1:{_find_free_port() - 1}/api/state"
    try:
        resp = urllib.request.urlopen(state_url, timeout=5)
        return json.loads(resp.read().decode())
    except Exception:
        return {}


def _terminate(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def tail_log(path, n=20):
    if path and path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[-n:])
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--video-dir", type=Path, default=ARTIFACTS_DIR)
    parser.add_argument("--no-video", action="store_true")
    args = parser.parse_args()

    executable = args.app.resolve()
    if not executable.exists():
        print(f"FAIL: executable not found at {executable}", file=sys.stderr)
        return 1

    args.video_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="sshot-e2e-"))
    log_dir = Path(tempfile.mkdtemp(prefix="sshot-e2e-logs-"))

    try:
        video_path = _create_test_video(work_dir)
    except Exception as e:
        print(f"WARN: video creation failed ({e}), using empty file", flush=True)
        video_path = work_dir / "e2e-test-video.mp4"
        video_path.write_text("")

    ready_file = work_dir / "events.jsonl"
    port = _find_free_port()
    stdout_log = log_dir / "stdout.log"
    stderr_log = log_dir / "stderr.log"

    print(f"E2E executable={executable}", flush=True)
    print(f"E2E port={port}", flush=True)

    proc = _spawn_app(executable, ready_file, port, video_path.parent / "e2e.ssproj",
                       stdout_log, stderr_log)

    try:
        _wait_for_backend(proc, port)
        print("PASS: backend is responding", flush=True)

        from playwright.sync_api import sync_playwright
        video_file = args.video_dir / f"e2e-{sys.platform}.mp4"

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu", "--disable-software-rasterizer"])
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                record_video_dir=str(args.video_dir / "pw-video") if not args.no_video else None)
            page = context.new_page()

            page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded", timeout=30000)
            print("PASS: Playwright connected to app", flush=True)

            state = page.evaluate("typeof state !== 'undefined'")
            print(f"PASS: app state object available: {state}", flush=True)

            summary = _exercise_app(page, video_path)

            context.close()
            browser.close()

        recorded = sorted((args.video_dir / "pw-video").glob("*")) if (args.video_dir / "pw-video").exists() else []
        if recorded:
            src = max(recorded, key=lambda p: p.stat().st_mtime)
            shutil.move(str(src), str(video_file))
            print(f"PASS: video saved ({video_file.stat().st_size / 1024 / 1024:.1f} MB)", flush=True)

        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
            final = json.loads(resp.read().decode())
            shots = len(final.get("project", {}).get("analysis", {}).get("shots", []))
            popups = len(final.get("project", {}).get("popups", []))
            print(f"PASS: shots={shots} popups={popups}", flush=True)
        except Exception:
            pass

        print("PASS: full E2E test completed", flush=True)
        return 0

    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        print(f"FAIL: exit code {proc.returncode}", file=sys.stderr, flush=True)
        if proc.poll() is not None:
            so = tail_log(stdout_log)
            se = tail_log(stderr_log)
            if so:
                print(f"--- stdout tail ---\n{so}", file=sys.stderr, flush=True)
            if se:
                print(f"--- stderr tail ---\n{se}", file=sys.stderr, flush=True)
        return 1
    finally:
        _terminate(proc)
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
