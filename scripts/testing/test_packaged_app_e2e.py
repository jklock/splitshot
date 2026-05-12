#!/usr/bin/env python3
#!/usr/bin/env python3
"""Full E2E test: launch app, run Playwright browser interactions, record video."""

from __future__ import annotations

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


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _create_test_video(out_dir):
    path = out_dir / "e2e-vid.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", "color=c=black:s=640x360:d=4:r=30",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
         "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(path)],
        check=True, capture_output=True, timeout=30)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--video-dir", type=Path, default=ARTIFACTS_DIR)
    args = parser.parse_args()

    executable = args.app.resolve()
    if not executable.exists():
        print(f"FAIL: executable not found at {executable}", file=sys.stderr)
        return 1

    work_dir = Path(tempfile.mkdtemp(prefix="sshot-e2e-"))
    log_dir = Path(tempfile.mkdtemp(prefix="sshot-e2e-logs-"))
    ready_file = work_dir / "events.jsonl"
    port = _free_port()

    try:
        video_path = _create_test_video(work_dir)
    except Exception as e:
        print(f"WARN: video failed ({e})", flush=True)
        video_path = work_dir / "e2e-vid.mp4"
        video_path.write_text("")

    log_out = log_dir / "stdout.log"
    log_err = log_dir / "stderr.log"

    env = {**os.environ, "CI": "1", "SPLITSHOT_ELECTRON_TEST": "1",
           "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
           "SPLITSHOT_TEST_PORT": str(port)}
    cmd = [str(executable)]
    if sys.platform.startswith("linux"):
        env["ELECTRON_DISABLE_SANDBOX"] = "1"
        cmd.append("--no-sandbox")
    cmd.append(str(video_path.parent / "e2e.ssproj"))

    print(f"E2E port={port}", flush=True)
    with log_out.open("w") as o, log_err.open("w") as e:
        proc = subprocess.Popen(cmd, cwd=executable.parent, env=env, stdout=o, stderr=e, text=True)

    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"App exited (code {proc.returncode})")
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
                break
            except (urllib.error.URLError, ConnectionResetError):
                time.sleep(0.25)
        else:
            raise TimeoutError("Backend did not respond")
        print("PASS: backend responding", flush=True)

        video_file = ARTIFACTS_DIR / f"e2e-{sys.platform}.mp4"
        ARTIFACTS_DIR.mkdir(exist_ok=True)

        # Run Playwright Node.js script (avoids Python C extension crashes on Linux)
        electron_dir = REPO / "electron"
        pw_script = REPO / "scripts" / "testing" / "e2e-playwright.mjs"
        pw_env = {**os.environ, "E2E_PORT": str(port),
                   "NODE_PATH": str(electron_dir / "node_modules")}
        for bad in ("QT_QPA_PLATFORM", "APPIMAGE_EXTRACT_AND_RUN"):
            pw_env.pop(bad, None)

        result = subprocess.run(
            ["node", str(pw_script)],
            capture_output=True, text=True, timeout=300,
            cwd=REPO, env=pw_env)

        print(result.stdout, flush=True)
        if result.returncode != 0:
            print(f"FAIL: Playwright exited code {result.returncode}", file=sys.stderr, flush=True)
            if result.stderr:
                print(result.stderr, file=sys.stderr, flush=True)
            raise RuntimeError("Playwright E2E failed")

        print("PASS: full E2E test completed", flush=True)
        return 0

    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        if proc.poll() is not None:
            print(f"FAIL: exit code {proc.returncode}", file=sys.stderr, flush=True)
        for l in [log_out, log_err]:
            if l and l.exists():
                lines = l.read_text().splitlines()
                print(f"--- {l.name} tail ---", file=sys.stderr, flush=True)
                print("\n".join(lines[-20:]), file=sys.stderr, flush=True)
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

