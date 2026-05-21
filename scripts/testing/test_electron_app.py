#!/usr/bin/env python3
"""Launch a built Electron app and verify the packaged window/backend come up."""

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
TIMEOUT = 60


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _create_project_bundle(name: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix="splitshot-packaged-smoke-"))
    project_path = root / f"{name}.ssproj"
    script = (
        "from pathlib import Path; "
        "import sys; "
        "from splitshot.domain.models import Project; "
        "from splitshot.persistence.projects import save_project; "
        "save_project(Project(name=sys.argv[2]), Path(sys.argv[1]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(project_path), name],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "failed to create project bundle")
    return project_path


def _default_executable() -> Path:
    if sys.platform == "darwin":
        candidates = sorted(
            (REPO / "electron" / "build").glob("mac*/SplitShot.app/Contents/MacOS/SplitShot")
        )
    elif sys.platform == "win32":
        candidates = sorted((REPO / "electron" / "build").glob("win-unpacked/SplitShot.exe"))
    else:
        candidates = sorted((REPO / "electron" / "build").glob("linux-unpacked/splitshot"))
    if not candidates:
        raise FileNotFoundError("No packaged Electron executable found in electron/build/")
    return candidates[0]


def _spawn_app(
    executable: Path,
    project_path: Path,
    ready_file: Path,
    port: int,
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.Popen[str]:
    env = {
        **os.environ,
        "CI": "1",
        "SPLITSHOT_ELECTRON_TEST": "1",
        "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
        "SPLITSHOT_TEST_PORT": str(port),
    }
    command = [str(executable)]
    if sys.platform.startswith("linux"):
        env["ELECTRON_DISABLE_SANDBOX"] = "1"
        command.append("--no-sandbox")
    command.append(str(project_path))
    with (
        stdout_path.open("w", encoding="utf-8") as stdout_handle,
        stderr_path.open("w", encoding="utf-8") as stderr_handle,
    ):
        return subprocess.Popen(
            command,
            cwd=executable.parent,
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )


def _wait_for_ready_file(
    proc: subprocess.Popen[str], ready_file: Path, timeout: int = TIMEOUT
) -> list[dict]:
    deadline = time.time() + timeout
    events: list[dict] = []
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("Packaged app exited before reporting ready")
        if ready_file.exists():
            lines = [
                line for line in ready_file.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
            events = [json.loads(line) for line in lines]
            event_names = {event.get("event") for event in events}
            if {
                "backend-ready",
                "window-loaded",
                "window-ready-to-show",
                "app-ready",
            } <= event_names:
                return events
        time.sleep(0.25)
    raise TimeoutError(f"Ready file {ready_file} never reported app-ready")


def _wait_for_state(port: int, expected_project_path: Path, timeout: int = TIMEOUT) -> dict:
    deadline = time.time() + timeout
    wanted = expected_project_path.resolve()
    while time.time() < deadline:
        try:
            response = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
            state = json.loads(response.read().decode())
            project_path = state.get("project", {}).get("path") or ""
            if project_path and Path(project_path).resolve() == wanted:
                return state
        except (
            urllib.error.URLError,
            ConnectionResetError,
            json.JSONDecodeError,
            FileNotFoundError,
        ):
            pass
        time.sleep(0.25)
    raise TimeoutError(f"Packaged app never loaded project {expected_project_path}")


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _process_tail(stdout_path: Path, stderr_path: Path) -> str:
    stdout = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
    stderr = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
    combined = "\n".join([part for part in [stdout, stderr] if part]).strip()
    lines = combined.splitlines()
    return "\n".join(lines[-20:]) if lines else "no process output captured"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, default=None, help="Packaged executable to launch")
    args = parser.parse_args()

    executable = (args.app or _default_executable()).resolve()
    if not executable.exists():
        print(f"FAIL: executable not found at {executable}", file=sys.stderr)
        return 1

    project_path = _create_project_bundle("packaged-launch")
    ready_file = Path(tempfile.mkdtemp(prefix="splitshot-ready-file-")) / "events.jsonl"
    log_dir = Path(tempfile.mkdtemp(prefix="splitshot-packaged-logs-"))
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    port = _find_free_port()
    print(f"PACKAGED_SMOKE executable={executable}")
    print(f"PACKAGED_SMOKE project={project_path}")
    print(f"PACKAGED_SMOKE ready_file={ready_file}")
    print(f"PACKAGED_SMOKE stdout_log={stdout_path}")
    print(f"PACKAGED_SMOKE stderr_log={stderr_path}")
    print(f"PACKAGED_SMOKE port={port}")
    proc = _spawn_app(executable, project_path, ready_file, port, stdout_path, stderr_path)

    try:
        _wait_for_ready_file(proc, ready_file)
        state = _wait_for_state(port, project_path)
        print(f"PASS: packaged app launched from {executable}")
        print(f"PASS: backend responded on port {port}")
        print(f"PASS: loaded project {state.get('project', {}).get('path')}")
        shutil.rmtree(project_path.parent, ignore_errors=True)
        shutil.rmtree(ready_file.parent, ignore_errors=True)
        shutil.rmtree(log_dir, ignore_errors=True)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        print(f"FAIL: ready file path {ready_file}", file=sys.stderr)
        print(f"FAIL: stdout log {stdout_path}", file=sys.stderr)
        print(f"FAIL: stderr log {stderr_path}", file=sys.stderr)
        print(f"FAIL: child exit code {proc.returncode}", file=sys.stderr)
        if proc.poll() is not None:
            print(_process_tail(stdout_path, stderr_path), file=sys.stderr)
        return 1
    finally:
        _terminate_process(proc)


if __name__ == "__main__":
    raise SystemExit(main())
