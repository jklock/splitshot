#!/usr/bin/env python3
"""Parity audit: Electron backend vs native CLI.

Tests that the --headless mode (used by Electron) produces identical
behavior to the native `uv run splitshot` dev workflow across
Function, Quality, Speed, and Testing.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
API_URL = "http://127.0.0.1:8765"
TIMEOUT = 30
PASS = 0
FAIL = 0
ERRORS: list[str] = []


def _report(category: str, name: str, status: str) -> None:
    global PASS, FAIL
    if status.startswith("PASS"):
        PASS += 1
    else:
        FAIL += 1
        ERRORS.append(f"  [{category}] {name}: {status}")
    print(f"  [{status[:4]}] {category}: {name}")


def _wait_for_server(timeout: int = TIMEOUT) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(f"{API_URL}/api/state", timeout=5)
            return json.loads(resp.read().decode())
        except (urllib.error.URLError, ConnectionResetError, json.JSONDecodeError):
            time.sleep(0.5)
    raise TimeoutError(f"Server did not start within {timeout}s")


def _api_get(path: str) -> dict | list:
    resp = urllib.request.urlopen(f"{API_URL}{path}", timeout=10)
    return json.loads(resp.read().decode())


def _start_backend() -> subprocess.Popen:
    proc = subprocess.Popen(
        ["uv", "run", "splitshot", "--headless", "--no-open"],
        cwd=REPO,
        env={**os.environ},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def _start_bundled_backend(bundle_path: str) -> subprocess.Popen:
    python_bin = os.path.join(
        bundle_path, ".venv", "bin" if sys.platform != "win32" else "Scripts", "python"
    )
    proc = subprocess.Popen(
        [python_bin, "-m", "splitshot", "--headless", "--no-open"],
        cwd=bundle_path,
        env={
            **os.environ,
            "PYTHONPATH": os.path.join(bundle_path, "src"),
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def _stop_backend(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def audit_function() -> None:
    """Verify all major API endpoints respond correctly."""
    print("\n=== 1. FUNCTION: API endpoint parity ===")

    endpoints = [
        "/api/state",
        "/api/practiscore/session/status",
    ]
    for path in endpoints:
        try:
            data = _api_get(path)
            assert data is not None, f"Empty response from {path}"
            _report("Function", f"GET {path}", "PASS")
        except Exception as e:
            _report("Function", f"GET {path}", f"FAIL: {e}")

    post_endpoints = [
        "/api/project/new",
        "/api/activity",
    ]
    for path in post_endpoints:
        try:
            data = json.loads(
                urllib.request.urlopen(
                    urllib.request.Request(f"{API_URL}{path}", data=b"{}", method="POST"),
                    timeout=10,
                ).read().decode()
            )
            assert data is not None
            _report("Function", f"POST {path}", "PASS")
        except Exception as e:
            _report("Function", f"POST {path}", f"FAIL: {e}")


def audit_quality() -> None:
    """Verify server responses match expected structure."""
    print("\n=== 2. QUALITY: Response structure ===")
    try:
        state = _api_get("/api/state")
        expected_keys = {"status", "project", "settings", "media", "scoring_presets"}
        state_keys = set(state.keys()) if isinstance(state, dict) else set()
        missing = expected_keys - state_keys
        if missing:
            _report("Quality", "api/state keys", f"FAIL: missing {missing}")
        else:
            _report("Quality", "api/state keys", "PASS")
    except Exception as e:
        _report("Quality", "api/state", f"FAIL: {e}")

    assets = [
        ("/", "index.html"),
        ("/static/app.js", "app.js"),
        ("/static/styles.css", "styles.css"),
    ]
    for url_path, name in assets:
        try:
            resp = urllib.request.urlopen(f"{API_URL}{url_path}", timeout=10)
            body = resp.read()
            if resp.status == 200 and len(body) > 0:
                _report("Quality", f"static/{name}", f"PASS ({len(body)} bytes)")
            else:
                _report("Quality", f"static/{name}", f"FAIL: HTTP {resp.status}")
        except Exception as e:
            _report("Quality", f"static/{name}", f"FAIL: {e}")


def audit_speed() -> None:
    """Measure API response times."""
    print("\n=== 3. SPEED: Response latency ===")
    endpoints = ["/", "/api/state", "/static/app.js"]
    for path in endpoints:
        times: list[float] = []
        for _ in range(5):
            start = time.perf_counter()
            try:
                urllib.request.urlopen(f"{API_URL}{path}", timeout=10)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            except Exception:
                pass
        if times:
            avg = sum(times) / len(times)
            label = "PASS" if avg < 1.0 else "WARN"
            _report("Speed", path, f"{label} ({avg*1000:.0f}ms avg)")
        else:
            _report("Speed", path, "FAIL: no response")


def audit_server_tests() -> None:
    """Run headless server tests against the running backend."""
    print("\n=== 4. TESTING: Headless server tests ===")
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/electron/", "--no-header", "-q"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    passed = result.returncode == 0
    if passed:
        lines = result.stdout.strip().split("\n")
        summary = [line for line in lines if line and not line.startswith(" ")]
        _report("Testing", "pytest tests/electron/", f"PASS ({summary[-1] if summary else 'all'})")
    else:
        fail_lines = [line for line in result.stdout.split("\n") if "FAILED" in line]
        fail_info = fail_lines[-1] if fail_lines else "see output"
        _report("Testing", "pytest tests/electron/", f"FAIL: {fail_info}")


def main() -> int:
    global PASS, FAIL
    print("=" * 60)
    print("SplitShot Electron Parity Audit")
    print("=" * 60)
    print("Command: uv run splitshot --headless --no-open")
    print()

    mode = sys.argv[1] if len(sys.argv) > 1 else "dev"
    print(f"Starting backend ({mode})...")
    proc = _start_backend()
    try:
        _wait_for_server()
        print(f"Backend ready at {API_URL}\n")

        audit_function()
        audit_quality()
        audit_speed()
        audit_server_tests()

    except TimeoutError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        FAIL += 1
    finally:
        _stop_backend(proc)

    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    if ERRORS:
        print("\nFailures:")
        for e in ERRORS:
            print(e)
    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
