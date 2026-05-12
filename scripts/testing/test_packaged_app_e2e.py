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
PLAYWRIGHT_SCRIPT = REPO / "scripts" / "testing" / "_playwright_e2e.py"


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


def _spawn_app(executable, ready_file, port, project_path, stdout_path, stderr_path):
    env = {**os.environ, "CI": "1", "SPLITSHOT_ELECTRON_TEST": "1",
           "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
           "SPLITSHOT_TEST_PORT": str(port)}
    cmd = [str(executable)]
    if sys.platform.startswith("linux"):
        env["ELECTRON_DISABLE_SANDBOX"] = "1"
        cmd.append("--no-sandbox")
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


def _terminate(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


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
        print(f"WARN: video creation failed ({e})", flush=True)
        video_path = work_dir / "e2e-test-video.mp4"
        video_path.write_text("")

    ready_file = work_dir / "events.jsonl"
    port = _find_free_port()
    stdout_log = log_dir / "stdout.log"
    stderr_log = log_dir / "stderr.log"

    print(f"E2E executable={executable}", flush=True)
    print(f"E2E port={port}", flush=True)
    print(f"E2E video={video_path}", flush=True)

    proc = _spawn_app(executable, ready_file, port, video_path.parent / "e2e.ssproj",
                       stdout_log, stderr_log)

    try:
        _wait_for_backend(proc, port)
        print("PASS: backend is responding", flush=True)

        video_file = args.video_dir / f"e2e-{sys.platform}.mp4"

        pw_env = dict(os.environ)
        pw_env.pop("QT_QPA_PLATFORM", None)
        pw_env.pop("APPIMAGE_EXTRACT_AND_RUN", None)
        pw_env["CI"] = "1"
        pw_result = subprocess.run(
            [sys.executable, str(PLAYWRIGHT_SCRIPT),
             "--port", str(port),
             "--video", str(video_path),
             "--video-output", str(video_file)],
            capture_output=True, text=True, timeout=300,
            env=minimal_env)
        print(pw_result.stdout, flush=True)
        if pw_result.returncode != 0:
            print(pw_result.stderr, file=sys.stderr, flush=True)
            raise RuntimeError(f"Playwright E2E test failed (exit {pw_result.returncode})")

        print("PASS: full E2E test completed", flush=True)
        return 0

    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        if proc.poll() is not None:
            print(f"FAIL: exit code {proc.returncode}", file=sys.stderr, flush=True)
        for log in [stdout_log, stderr_log]:
            if log and log.exists():
                lines = log.read_text(encoding="utf-8").splitlines()
                print(f"--- {log.name} tail ---", file=sys.stderr, flush=True)
                print("\n".join(lines[-20:]), file=sys.stderr, flush=True)
        return 1
    finally:
        _terminate(proc)
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
