"""Tests for the --headless server mode used by Electron."""

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
BASE_PORT = 18765


def _wait_for_server(port: int, timeout: int = 20) -> dict:
    url = f"http://127.0.0.1:{port}/api/state"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(url, timeout=5)
            return json.loads(resp.read().decode())
        except (urllib.error.URLError, ConnectionResetError, json.JSONDecodeError):
            time.sleep(0.5)
    raise TimeoutError(f"Server did not start within {timeout}s")


@pytest.fixture
def headless_server(request):
    port = BASE_PORT + hash(request.node.name) % 1000
    proc = subprocess.Popen(
        ["uv", "run", "splitshot", "--headless", "--no-open", "--port", str(port)],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_server(port)
        yield proc, port
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def test_headless_server_starts_and_serves_state(headless_server):
    _, port = headless_server
    state = _wait_for_server(port)
    assert isinstance(state, dict)
    assert "status" in state
    assert "project" in state
    assert "settings" in state


def test_headless_server_serves_static_assets(headless_server):
    _, port = headless_server
    for path in ["/", "/static/app.js", "/static/styles.css"]:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10)
        assert resp.status == 200, f"{path} returned {resp.status}"
        assert len(resp.read()) > 0, f"{path} returned empty body"


def test_headless_check_flag():
    result = subprocess.run(
        ["uv", "run", "splitshot", "--check"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"--check failed: {result.stderr}"
    assert "runtime check" in result.stdout.lower()
    assert "ffmpeg" in result.stdout
    assert "ffprobe" in result.stdout
