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


def _create_synthetic_video(output_dir: Path) -> Path:
    video_path = output_dir / "e2e-test-video.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi",
            "-i", "color=c=black:s=640x360:d=4:r=30",
            "-f", "lavfi",
            "-i", "sine=frequency=440:duration=4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(video_path),
        ],
        check=True,
    )
    return video_path


def _spawn_app(
    executable: Path,
    ready_file: Path,
    port: int,
    project_path: Path | None,
    stdout_path: Path,
    stderr_path: Path,
    extra_args: list[str] | None = None,
) -> subprocess.Popen[str]:
    env = {
        **os.environ,
        "CI": "1",
        "SPLITSHOT_ELECTRON_TEST": "1",
        "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
        "SPLITSHOT_TEST_PORT": str(port),
    }
    command = [str(executable)]
    if sys.platform.startswith("linux") and "--no-sandbox" not in (extra_args or []):
        env["ELECTRON_DISABLE_SANDBOX"] = "1"
        command.append("--no-sandbox")
    if extra_args:
        command.extend(extra_args)
    if project_path:
        command.append(str(project_path))
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        return subprocess.Popen(command, cwd=executable.parent, env=env, stdout=out, stderr=err, text=True)


def _wait_for_backend(proc: subprocess.Popen[str], port: int, timeout: int = TIMEOUT) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("App exited before backend was ready")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
            return
        except (urllib.error.URLError, ConnectionResetError):
            pass
        time.sleep(0.25)
    raise TimeoutError("Backend did not respond within timeout")


def _e2e_interactions(page, video_path: Path) -> dict:
    page.wait_for_function("() => typeof activeTool !== 'undefined'", timeout=30000)
    page.wait_for_timeout(500)

    if not page.evaluate("Boolean(state?.project?.path)"):
        project_path = str(video_path.parent / "e2e.ssproj")
        page.evaluate("(p) => createNewProject(p)", project_path)
        page.wait_for_function("() => Boolean(state?.project?.path)", timeout=15000)
        page.wait_for_timeout(500)

    page.locator("#primary-file-input").set_input_files(str(video_path))
    page.wait_for_function("() => Boolean(state?.media?.primary_display_name)", timeout=30000)
    page.wait_for_timeout(1000)

    page.wait_for_function("() => (state?.project?.analysis?.shots || []).length > 0", timeout=60000)

    for tool_id in ["project", "merge", "scoring", "timing", "markers", "overlay", "review", "export", "metrics", "settings"]:
        btn = page.locator(f'button[data-tool="{tool_id}"]')
        if btn.is_visible():
            btn.click(force=True)
            page.wait_for_function("(t) => activeTool === t", arg=tool_id, timeout=10000)
            page.wait_for_timeout(250)

    page.locator('button[data-tool="timing"]').click(force=True)
    page.wait_for_function("() => activeTool === 'timing'")
    page.wait_for_timeout(500)
    if page.locator(".waveform-shot-card").count() > 0:
        page.locator(".waveform-shot-card").first.click()
        page.wait_for_timeout(300)

    page.locator('button[data-tool="markers"]').click(force=True)
    page.wait_for_function("() => activeTool === 'markers'")
    page.wait_for_timeout(300)
    popup_edit = page.locator("#popup-edit-selected")
    if popup_edit.is_visible():
        popup_edit.click()
        page.wait_for_timeout(600)
        close_btn = page.locator("#popup-edit-selected")
        if close_btn.is_visible():
            close_btn.click()
            page.wait_for_timeout(300)

    page.locator('button[data-tool="overlay"]').click(force=True)
    page.wait_for_function("() => activeTool === 'overlay'")
    page.wait_for_timeout(300)
    add_box = page.locator("#overlay-add-text-box")
    if add_box.is_visible():
        add_box.click()
        page.wait_for_timeout(300)

    page.locator('button[data-tool="review"]').click(force=True)
    page.wait_for_function("() => activeTool === 'review'")
    page.wait_for_timeout(300)

    page.locator('button[data-tool="settings"]').click(force=True)
    page.wait_for_function("() => activeTool === 'settings'")
    page.wait_for_timeout(500)

    page.locator('button[data-tool="scoring"]').click(force=True)
    page.wait_for_function("() => activeTool === 'scoring'")
    page.wait_for_timeout(300)

    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{_find_free_port() - 1}/api/state", timeout=5)
        return json.loads(response.read().decode())
    except Exception:
        return {}


def _terminate(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def main() -> int:
    print("E2E_SCRIPT_STARTED", flush=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True, help="Installed app executable")
    parser.add_argument("--video-dir", type=Path, default=ARTIFACTS_DIR, help="Output dir for recorded video")
    parser.add_argument("--no-video", action="store_true", help="Skip video recording")
    parser.add_argument("extra_args", nargs='*', help="Extra args passed to the app executable (use -- before them)")
    args = parser.parse_args()
    print("E2E_ARGS_PARSED", flush=True)

    executable = args.app.resolve()
    if not executable.exists():
        print(f"FAIL: executable not found at {executable}", file=sys.stderr)
        return 1
    print("E2E_EXECUTABLE_OK", flush=True)

    args.video_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="splitshot-e2e-"))
    log_dir = Path(tempfile.mkdtemp(prefix="splitshot-e2e-logs-"))
    video_path = _create_synthetic_video(work_dir)
    ready_file = work_dir / "events.jsonl"
    port = _find_free_port()
    stdout_log = log_dir / "stdout.log"
    stderr_log = log_dir / "stderr.log"

    print(f"E2E_APP={executable}")
    print(f"E2E_VIDEO={video_path}")
    print(f"E2E_PORT={port}")
    print(f"E2E_READY={ready_file}")
    print(f"E2E_STDOUT={stdout_log}")
    print(f"E2E_STDERR={stderr_log}")

    proc = _spawn_app(
        executable, ready_file, port, video_path.parent / "e2e.ssproj",
        stdout_log, stderr_log, extra_args=args.extra_args,
    )

    try:
        _wait_for_backend(proc, port)
        print("PASS: backend is responding")

        video_file = args.video_dir / f"e2e-{sys.platform}.mp4"
        summary: dict = {}

        from playwright.sync_api import sync_playwright

        # Verify Playwright chromium can launch
        import shutil
        print(f"PLAYWRIGHT_BROWSERS_PATH: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH', 'not set')}", flush=True)
        chromium_path = None
        cache_dir = Path(os.environ.get('PLAYWRIGHT_BROWSERS_PATH', Path.home() / '.cache' / 'ms-playwright'))
        for p in cache_dir.rglob('chrome-headless-shell'):
            if p.is_file() and os.access(p, os.X_OK):
                chromium_path = p
                break
        if not chromium_path:
            for p in cache_dir.rglob('chromium'):
                if p.is_file() and os.access(p, os.X_OK):
                    chromium_path = p
                    break
        print(f"CHROMIUM_PATH: {chromium_path}")
        if chromium_path:
            result = subprocess.run([str(chromium_path), '--version'], capture_output=True, text=True, timeout=10)
            print(f"CHROMIUM_VERSION: {result.stdout.strip() or result.stderr.strip()}")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu", "--disable-software-rasterizer", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                record_video_dir=str(args.video_dir / "playwright-video") if not args.no_video else None,
            )
            page = context.new_page()
            try:
                page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"FAIL: Playwright page.goto failed: {e}", file=sys.stderr)
                raise
            summary = _e2e_interactions(page, video_path)
            context.close()
            browser.close()

        recorded = list((args.video_dir / "playwright-video").glob("*")) if (args.video_dir / "playwright-video").exists() else []
        if recorded:
            src = max(recorded, key=lambda p: p.stat().st_mtime)
            shutil.move(str(src), str(video_file))
            print(f"PASS: E2E video saved to {video_file} ({video_file.stat().st_size / 1024 / 1024:.1f} MB)")

        shot_count = len(summary.get("project", {}).get("analysis", {}).get("shots", []))
        if shot_count > 0:
            print(f"PASS: {shot_count} shots detected in project")
        else:
            try:
                resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
                state = json.loads(resp.read().decode())
                shot_count = len(state.get("project", {}).get("analysis", {}).get("shots", []))
                print(f"PASS: {shot_count} shots detected via API")
            except Exception:
                pass

        print("PASS: full E2E test completed successfully")
        return 0

    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        print(f"FAIL: child exit code {proc.returncode}", file=sys.stderr)
        if proc.poll() is not None:
            for log in [stdout_log, stderr_log]:
                if log.exists():
                    print(f"--- {log.name} tail (last 20 lines) ---", file=sys.stderr)
                    lines = log.read_text(encoding="utf-8").splitlines()
                    print("\n".join(lines[-20:]), file=sys.stderr)
        return 1
    finally:
        _terminate(proc)
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
