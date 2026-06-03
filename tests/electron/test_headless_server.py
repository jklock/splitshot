"""Tests for the --headless server mode used by Electron."""

from __future__ import annotations

import json
import os
import select
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
PYTHON = REPO / ".venv" / "bin" / "python"
ARTIFACT_DIR = REPO / "artifacts" / "backend-startup"


def _read_ready_line(process: subprocess.Popen[str], timeout: int = 20) -> tuple[dict, list[str]]:
    deadline = time.time() + timeout
    lines: list[str] = []
    while time.time() < deadline:
        if process.stdout is None:
            break
        remaining = max(0.1, deadline - time.time())
        ready, _, _ = select.select([process.stdout], [], [], min(0.5, remaining))
        if ready:
            line = process.stdout.readline()
            if not line:
                break
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
            if stripped.startswith("SPLITSHOT_READY "):
                return json.loads(stripped.removeprefix("SPLITSHOT_READY ")), lines
        if process.poll() is not None:
            break
    stderr = process.stderr.read() if process.stderr is not None else ""
    raise TimeoutError(
        f"Server did not emit a ready line within {timeout}s. stdout={lines!r} stderr={stderr!r}"
    )


def _json_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[dict, dict[str, str]]:
    request_headers = dict(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
        return body, dict(response.headers)


def _claim_backend_session(ready_payload: dict) -> tuple[dict, dict[str, str]]:
    claim_url = f"{ready_payload['base_url']}{ready_payload['claim_path']}"
    payload, response_headers = _json_request(
        claim_url,
        method="POST",
        payload={},
        headers={"X-SplitShot-Bootstrap-Token": str(ready_payload["bootstrap_token"])},
    )
    cookie = str(response_headers["Set-Cookie"]).split(";", 1)[0]
    return payload, {"Cookie": cookie}


@pytest.fixture
def headless_server():
    env = {
        **os.environ,
        "SPLITSHOT_REQUIRE_SESSION_CLAIM": "1",
    }
    proc = subprocess.Popen(
        [str(PYTHON), "-m", "splitshot", "--headless", "--no-open", "--port", "0"],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        ready_payload, stdout_lines = _read_ready_line(proc)
        yield {
            "process": proc,
            "ready_payload": ready_payload,
            "stdout_lines": stdout_lines,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def test_headless_server_emits_ready_line_claims_session_and_serves_state(headless_server):
    ready_payload = headless_server["ready_payload"]
    startup_payload, _ = _json_request(
        f"{ready_payload['base_url']}{ready_payload['startup_status_path']}"
    )
    claim_payload, auth_headers = _claim_backend_session(ready_payload)
    state_payload, _ = _json_request(f"{ready_payload['base_url']}/api/state", headers=auth_headers)
    health_payload, _ = _json_request(
        f"{ready_payload['base_url']}{claim_payload['health_path']}",
        headers=auth_headers,
    )

    denied_payload: dict[str, object] | None = None
    denied_status = None
    try:
        _json_request(f"{ready_payload['base_url']}/api/health")
    except urllib.error.HTTPError as exc_info:
        denied_status = exc_info.code
        denied_payload = json.loads(exc_info.read().decode("utf-8"))

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "ready-line.json").write_text(
        json.dumps(
            {
                "mode": "headless",
                "actual_host": ready_payload["host"],
                "actual_port": ready_payload["port"],
                "electron_observed_endpoint": ready_payload["base_url"],
                "ready_payload": ready_payload,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (ARTIFACT_DIR / "claim-health-trace.json").write_text(
        json.dumps(
            {
                "startup_status": startup_payload,
                "claim": claim_payload,
                "cookie_policy": {
                    "http_only": True,
                    "same_site": "Strict",
                    "loopback_only": True,
                },
                "health": health_payload,
                "denied_unauthenticated_call": {
                    "status": denied_status,
                    "payload": denied_payload,
                },
                "state_status": state_payload["status"],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    assert ready_payload["protocol_version"] == "1"
    assert ready_payload["claim_path"] == "/api/startup/claim"
    assert ready_payload["startup_status_path"] == "/api/startup/status"
    assert ready_payload["health_path"] == "/api/health"
    assert ready_payload["events_path"] == "/api/events"
    assert ready_payload["session_id"] == claim_payload["session_id"]
    assert isinstance(ready_payload["port"], int)
    assert ready_payload["port"] > 0
    assert isinstance(state_payload, dict)
    assert "project" in state_payload
    assert startup_payload["state"] == "ready"
    assert health_payload["session_id"] == claim_payload["session_id"]
    assert health_payload["state"] == "ready"
    assert denied_status == 401
    assert denied_payload is not None
    assert denied_payload["error"]["code"] == "backend_session_required"


def test_headless_server_serves_static_assets(headless_server):
    ready_payload = headless_server["ready_payload"]
    for route in ["/", "/static/app.js", "/static/styles.css"]:
        with urllib.request.urlopen(f"{ready_payload['base_url']}{route}", timeout=10) as response:
            assert response.status == 200, f"{route} returned {response.status}"
            assert len(response.read()) > 0, f"{route} returned empty body"


def test_headless_check_flag():
    result = subprocess.run(
        [str(PYTHON), "-m", "splitshot", "--check"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"--check failed: {result.stderr}"
    assert "runtime check" in result.stdout.lower()
    assert "ffmpeg" in result.stdout
    assert "ffprobe" in result.stdout
    assert "ffprobe" in result.stdout
