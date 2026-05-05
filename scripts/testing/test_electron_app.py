#!/usr/bin/env python3
"""Test that the SplitShot Electron .app launches and serves the API."""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

APP_PATH = os.environ.get(
    "SPLITSHOT_APP",
    "electron/build/mac-arm64/SplitShot.app",
)
API_URL = "http://127.0.0.1:8765/api/state"
TIMEOUT = 30


def _wait_for_server(timeout: int = TIMEOUT) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(API_URL, timeout=5)
            return json.loads(resp.read().decode())
        except (urllib.error.URLError, ConnectionResetError, json.JSONDecodeError):
            time.sleep(0.5)
    raise TimeoutError(f"API at {API_URL} did not respond within {timeout}s")


def main() -> int:
    app_path = os.path.join(os.path.dirname(__file__), "..", "..", APP_PATH)
    app_path = os.path.abspath(app_path)

    if not os.path.isdir(app_path):
        print(f"FAIL: .app not found at {app_path}", file=sys.stderr)
        return 1

    print(f"Launching {app_path}...")
    proc = subprocess.Popen(
        ["open", app_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    proc.wait()

    try:
        state = _wait_for_server()
        print(f"PASS: API responded: project_loaded={state.get('project', {}).get('loaded', False)}")
        print(f"PASS: App is running at {API_URL}")
        return 0
    except TimeoutError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        # Kill the app
        subprocess.run(
            ["pkill", "-f", "SplitShot.app/Contents/MacOS/SplitShot"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    raise SystemExit(main())
