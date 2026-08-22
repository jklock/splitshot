#!/usr/bin/env python3
"""Parity audit: native headless backend vs bundled Electron backend."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
BUNDLE = REPO / "electron" / "bundle"
TIMEOUT = 60 if sys.platform == "win32" else 30


@dataclass(frozen=True)
class BackendSpec:
    name: str
    port: int
    command: list[str]
    cwd: Path
    env: dict[str, str]

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


class BackendStartupError(RuntimeError):
    """Backend did not become ready."""


def _build_specs() -> tuple[BackendSpec, BackendSpec]:
    native_port = _find_free_port()
    bundled_port = _find_free_port(exclude={native_port})
    native = BackendSpec(
        name="native",
        port=native_port,
        command=["uv", "run", "splitshot", "--headless", "--no-open", "--port", str(native_port)],
        cwd=REPO,
        env={**os.environ},
    )
    python_bin = (
        BUNDLE
        / ".venv"
        / ("Scripts" if sys.platform == "win32" else "bin")
        / ("python.exe" if sys.platform == "win32" else "python")
    )
    bundled = BackendSpec(
        name="bundled",
        port=bundled_port,
        command=[
            str(python_bin),
            "-m",
            "splitshot",
            "--headless",
            "--no-open",
            "--port",
            str(bundled_port),
        ],
        cwd=BUNDLE,
        env={**os.environ, "PYTHONPATH": str(BUNDLE / "src")},
    )
    return native, bundled


def _find_free_port(*, exclude: set[int] | None = None) -> int:
    exclude = exclude or set()
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        if port not in exclude:
            return port


def _report(name: str, passed: bool, detail: str = "") -> int:
    status = "PASS" if passed else "FAIL"
    suffix = f" {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return 0 if passed else 1


def _summarize_mismatch(left: Any, right: Any) -> str:
    if isinstance(left, dict) and isinstance(right, dict):
        differing = sorted(key for key in set(left) | set(right) if left.get(key) != right.get(key))
        return f"(differing keys: {', '.join(differing[:6])})"
    return "(values differ)"


def _read_process_tail(proc: subprocess.Popen[bytes]) -> str:
    chunks: list[bytes] = []
    for stream in (proc.stdout, proc.stderr):
        if stream is None:
            continue
        try:
            chunks.append(stream.read() or b"")
        except Exception:  # noqa: BLE001, S112 - preserve output from the readable stream.
            continue
    combined = b"".join(chunks).decode(errors="replace").strip()
    if not combined:
        return "no process output captured"
    lines = combined.splitlines()
    return "\n".join(lines[-20:])


def _wait_for_server(
    spec: BackendSpec,
    proc: subprocess.Popen[bytes],
    timeout: int = TIMEOUT,
) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        exit_code = proc.poll()
        if exit_code is not None:
            detail = _read_process_tail(proc)
            raise BackendStartupError(
                f"{spec.name} backend exited before startup with code {exit_code}\n{detail}"
            )
        try:
            response = urllib.request.urlopen(f"{spec.base_url}/api/state", timeout=5)
            return json.loads(response.read().decode())
        except (urllib.error.URLError, ConnectionResetError, json.JSONDecodeError):
            time.sleep(0.5)
    detail = (
        _read_process_tail(proc)
        if proc.poll() is not None
        else "process still running without responding"
    )
    raise BackendStartupError(
        f"{spec.name} backend at {spec.base_url} did not start within {timeout}s\n{detail}"
    )


def _start_backend(spec: BackendSpec) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        spec.command,
        cwd=str(spec.cwd),
        env=spec.env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _stop_backend(proc: subprocess.Popen[bytes]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _http_get(base_url: str, route: str) -> Any:
    response = urllib.request.urlopen(f"{base_url}{route}", timeout=10)
    content_type = response.headers.get("content-type", "")
    body = response.read()
    if "application/json" in content_type:
        return json.loads(body.decode())
    return body


def _http_post(base_url: str, route: str, payload: dict[str, Any]) -> Any:
    request = urllib.request.Request(
        f"{base_url}{route}",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    response = urllib.request.urlopen(request, timeout=10)
    return json.loads(response.read().decode())


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"id", "created_at", "updated_at", "cache_token"}:
                continue
            normalized[key] = _normalize(item)
        return normalized
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _collect_contracts(spec: BackendSpec) -> dict[str, Any]:
    return {
        "GET /api/state": _normalize(_http_get(spec.base_url, "/api/state")),
        "GET /api/practiscore/session/status": _normalize(
            _http_get(spec.base_url, "/api/practiscore/session/status")
        ),
        "POST /api/project/new": _normalize(_http_post(spec.base_url, "/api/project/new", {})),
        "POST /api/activity": _normalize(_http_post(spec.base_url, "/api/activity", {})),
        "GET /": _http_get(spec.base_url, "/"),
        "GET /static/app.js": _http_get(spec.base_url, "/static/app.js"),
        "GET /static/styles.css": _http_get(spec.base_url, "/static/styles.css"),
    }


def run_parity_audit() -> int:
    failures = 0
    native, bundled = _build_specs()
    if not BUNDLE.exists():
        print(f"Missing bundled backend at {BUNDLE}", file=sys.stderr)
        return 1

    native_proc = _start_backend(native)
    bundled_proc = _start_backend(bundled)
    try:
        _wait_for_server(native, native_proc)
        _wait_for_server(bundled, bundled_proc)
        failures += _report("backend startup", True, "(native + bundled ready)")
        native_contracts = _collect_contracts(native)
        bundled_contracts = _collect_contracts(bundled)
        for contract_name, native_value in native_contracts.items():
            bundled_value = bundled_contracts[contract_name]
            passed = native_value == bundled_value
            failures += _report(
                contract_name,
                passed,
                "" if passed else _summarize_mismatch(native_value, bundled_value),
            )
    except BackendStartupError as exc:
        failures += _report("backend startup", False, f"({exc})")
    finally:
        _stop_backend(native_proc)
        _stop_backend(bundled_proc)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("parity",), default="parity")
    args = parser.parse_args()
    print("=" * 60)
    print("SplitShot Electron Parity Audit")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    failures = run_parity_audit()
    print("=" * 60)
    print("RESULT:", "PASS" if failures == 0 else f"FAIL ({failures} mismatch(es))")
    print("=" * 60)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
