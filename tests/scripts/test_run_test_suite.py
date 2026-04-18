from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "testing" / "run_test_suite.py"


def run_runner(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_runner_lists_available_suites_as_json() -> None:
    result = run_runner("--list", "--format", "json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    suite_names = [suite["name"] for suite in payload["suites"]]
    assert "analysis" in suite_names
    assert "browser" in suite_names
    assert "scripts" in suite_names


def test_runner_dry_run_expands_browser_suite_one_by_one_as_json() -> None:
    result = run_runner("--suite", "browser", "--mode", "one-by-one", "--format", "json", "--dry-run")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["dry_run"] is True
    assert payload["summary"]["planned"] == 2
    assert payload["summary"]["total_runs"] == 2
    assert {run["status"] for run in payload["runs"]} == {"planned"}
    assert {tuple(run["targets"]) for run in payload["runs"]} == {
        ("tests/browser/test_browser_control.py",),
        ("tests/browser/test_browser_static_ui.py",),
    }


def test_runner_dry_run_writes_raw_and_json_output_files(tmp_path: Path) -> None:
    raw_output = tmp_path / "test-plan.raw.txt"
    json_output = tmp_path / "test-plan.json"

    result = run_runner(
        "--suite",
        "cli",
        "--mode",
        "all-together",
        "--dry-run",
        "--raw-output",
        str(raw_output),
        "--json-output",
        str(json_output),
    )

    assert result.returncode == 0
    assert raw_output.is_file()
    assert json_output.is_file()
    assert "tests/cli" in raw_output.read_text(encoding="utf-8")
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["planned"] == 1
    assert payload["runs"][0]["targets"] == ["tests/cli"]