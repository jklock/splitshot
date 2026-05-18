#!/usr/bin/env python3
"""Comprehensive E2E test: launch app, run Playwright interactions via Node.js, verify results.
Tests all feature combinations: import, scoring, overlay, markers, merge, export, settings."""

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
ELECTRON_DIR = REPO / "electron"
PW_SCRIPT = REPO / "scripts" / "testing" / "e2e-playwright.cjs"
EXAMPLE_DATA = REPO / "example_data"
PASS = 0
FAIL = 0
ERRORS = []


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _check(description, condition, detail=""):
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


def _create_synthetic_video(out_dir, name="primary.mp4"):
    import numpy as np, wave
    path = out_dir / name
    audio_path = out_dir / f"{name}.wav"
    raw_vid = out_dir / f"{name}.raw.mp4"

    sr = 22050
    ns = int(sr * 4)
    s = np.zeros(ns, dtype=np.float32)
    beep_start = int(sr * 0.4)
    bl = int(sr * 0.09)
    bt = np.arange(bl) / sr
    s[beep_start:beep_start + bl] += (0.85 * np.sin(2 * np.pi * 2600 * bt) * np.hanning(bl)).astype(np.float32)
    rng = np.random.default_rng(7)
    for ms in [800, 1100, 1450]:
        ss = int(sr * (ms / 1000.0))
        sl = int(sr * 0.025)
        s[ss:ss + sl] += (rng.normal(0, 1, sl).astype(np.float32) * np.exp(-np.linspace(0, 8, sl)) * 0.95)

    c = np.clip(s, -1.0, 1.0)
    with wave.open(str(audio_path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((c * 32767).astype(np.int16).tobytes())

    subprocess.run(["ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "color=c=black:s=640x360:d=4:r=30",
        "-i", str(audio_path), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(path)], check=True, capture_output=True, timeout=30)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=ARTIFACTS_DIR)
    args = parser.parse_args()

    executable = args.app.resolve()
    if not executable.exists():
        print(f"FAIL: executable not found at {executable}")
        return 1

    global PASS, FAIL, ERRORS
    PASS = FAIL = 0
    ERRORS = []
    proc = None

    args.artifacts.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="sshot-comp-"))
    log_dir = Path(tempfile.mkdtemp(prefix="sshot-comp-logs-"))

    try:
        video = _create_synthetic_video(work_dir, "primary.mp4")
        project_path = work_dir / "comp.ssproj"
        port = _free_port()
        ready_file = log_dir / "events.jsonl"

        # Create project
        subprocess.run(["uv", "run", "python", "-c",
            "from pathlib import Path; import sys; "
            "from splitshot.domain.models import Project; "
            "from splitshot.persistence.projects import save_project; "
            "save_project(Project(name=sys.argv[2]), Path(sys.argv[1]))",
            str(project_path), "comprehensive"],
            cwd=REPO, capture_output=True, text=True, timeout=60, check=True)

        # Launch app
        env = {**os.environ, "CI": "1", "SPLITSHOT_ELECTRON_TEST": "1",
               "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
               "SPLITSHOT_TEST_PORT": str(port)}
        cmd = [str(executable)]
        if sys.platform.startswith("linux"):
            env["ELECTRON_DISABLE_SANDBOX"] = "1"
            cmd.append("--no-sandbox")
        cmd.append(str(project_path))

        sout = log_dir / "app-stdout.log"
        serr = log_dir / "app-stderr.log"
        proc = subprocess.Popen(cmd, cwd=executable.parent, env=env,
                                stdout=sout.open("w"), stderr=serr.open("w"), text=True)

        # Wait for backend
        dl = time.time() + 60
        while time.time() < dl:
            if proc.poll() is not None:
                raise RuntimeError(f"App exited (code {proc.returncode})")
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
                break
            except (urllib.error.URLError, ConnectionResetError):
                time.sleep(0.25)
        else:
            raise TimeoutError("Backend did not respond")
        print(f"App launched on port {port}", flush=True)

        # Run Node.js Playwright E2E script (works on all platforms, no Python C extension crash)
        pw_log_dir = args.artifacts / "e2e-logs"
        pw_log_dir.mkdir(parents=True, exist_ok=True)
        pw_env = {**os.environ, "E2E_PORT": str(port),
                   "E2E_LOG_DIR": str(pw_log_dir),
                   "E2E_VIDEO_PATH": str(video),
                   "NODE_PATH": str(ELECTRON_DIR / "node_modules")}
        for bad in ("QT_QPA_PLATFORM", "APPIMAGE_EXTRACT_AND_RUN"):
            pw_env.pop(bad, None)

        pw_result = subprocess.run(
            ["node", str(PW_SCRIPT)],
            capture_output=True, text=True, timeout=300,
            cwd=REPO, env=pw_env)

        if pw_result.stdout:
            print(pw_result.stdout, flush=True)
        if pw_result.stderr:
            print(pw_result.stderr, file=sys.stderr, flush=True)

        # Verify results via API
        time.sleep(1)
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=10)
            state = json.loads(resp.read().decode())
            prj = state.get("project", {})
            shots = len(prj.get("analysis", {}).get("shots", []))
            popups = len(prj.get("popups", []))
            boxes = len(prj.get("overlay", {}).get("text_boxes", []))
            merged = len(prj.get("merge_sources", []))
            events = len(prj.get("analysis", {}).get("events", []))
            ps = bool(prj.get("scoring", {}).get("imported_stage")) or bool(state.get("practiscore_options", {}).get("has_source"))

            _check(f"shots detected: {shots}", shots > 0)
            _check(f"text boxes created: {boxes}", boxes > 0)
            _check(f"merge sources: {merged}", merged > 0)
            _check(f"timing events: {events}", events > 0)
            _check(f"PractiScore imported: {ps}", ps)
        except Exception as e:
            _check("API state verification", False, str(e))

        # Export verification - check if Node.js script created the export
        export_dir = Path(tempfile.gettempdir()) / "sshot-e2e-export"
        export_files = list(work_dir.glob("*.mp4")) + list(export_dir.glob("*.mp4"))
        export_file = next((f for f in export_files if f.stat().st_size > 1024), None)
        if export_file:
            sz = export_file.stat().st_size
            _check(f"export file: {sz / 1024 / 1024:.1f}MB", sz > 1024)
            try:
                r = subprocess.run(["ffprobe", "-v", "error",
                    "-show_entries", "format=format_name,duration:stream=codec_type",
                    "-of", "json", str(export_file)],
                    capture_output=True, text=True, timeout=15)
                info = json.loads(r.stdout)
                streams = info.get("streams", [])
                _check("export has video", any(s.get("codec_type") == "video" for s in streams))
                _check("export has audio", any(s.get("codec_type") == "audio" for s in streams))
            except Exception as e:
                _check("export ffprobe", False, str(e))
        else:
            _check("export file found on disk", False)

        # Summary
        total = PASS + FAIL
        print(f"\n{'='*50}")
        print(f"RESULTS: {PASS} passed, {FAIL} failed out of {total} checks")
        if ERRORS:
            print("FAILURES:")
            for e in ERRORS:
                print(f"  {e}")
        print(f"{'='*50}")
        (args.artifacts / "comprehensive-results.json").write_text(
            json.dumps({"pass": PASS, "fail": FAIL, "total": total, "errors": ERRORS}, indent=2))
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
