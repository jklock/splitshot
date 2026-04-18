from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "analyze_video_shots.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_analyze_video_shots_emits_json_sweep_and_shot_details(synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(name="preflight-json")

    result = run_script(
        str(video_path),
        "--threshold-grid",
        "0.35,0.50",
        "--threshold",
        "0.35",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["video"] == str(video_path)
    assert payload["selected_threshold"] == 0.35
    assert len(payload["sweep"]) == 2
    assert payload["shots"]
    assert payload["shots"][0]["shot_number"] == 1
    assert payload["shots"][0]["confidence_percent"] is not None


def test_analyze_video_shots_writes_json_report_and_table_output(tmp_path: Path, synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(name="preflight-table")
    json_output = tmp_path / "preflight-report.json"

    result = run_script(
        str(video_path),
        "--threshold-grid",
        "0.35,0.50",
        "--format",
        "table",
        "--json-output",
        str(json_output),
    )

    assert result.returncode == 0
    assert "Recommended threshold:" in result.stdout
    assert "Threshold Sweep" in result.stdout
    assert "Shot Details At" in result.stdout
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["recommended_threshold"] in {0.35, 0.5}
    assert len(payload["shots"]) >= 1