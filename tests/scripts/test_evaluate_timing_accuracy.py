from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "evaluate_timing_accuracy.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _manifest_payload(video_path: Path) -> dict[str, object]:
    return {
        "input": str(video_path.parent),
        "video_count": 1,
        "threshold_grid": [0.35],
        "reference_threshold": 0.35,
        "duplicate_groups": [],
        "videos": [
            {
                "path": str(video_path),
                "relative_path": video_path.name,
                "duration_seconds": 2.0,
                "reference_threshold": 0.35,
                "detector_beep_time_ms": 400,
                "detector_shot_times_ms": [800, 1100, 1450],
                "detector_shot_confidences": [0.9, 0.95, 0.96],
                "detector_shot_count": 3,
                "review_flags": [],
                "labels": {
                    "status": "verified",
                    "verified_beep_time_ms": 400,
                    "verified_shot_times_ms": [800, 1100, 1450],
                    "auto_beep_time_ms": None,
                    "auto_shot_times_ms": [],
                    "auto_label_score": None,
                    "auto_label_method": "",
                    "auto_label_reasons": [],
                    "review_notes": "",
                    "timer_model": "",
                    "range_name": "",
                    "device_notes": "",
                    "environment_tags": [],
                },
            }
        ],
    }


def test_evaluate_timing_accuracy_emits_json_summary(
    tmp_path: Path, synthetic_video_factory
) -> None:
    video_path = synthetic_video_factory(name="timing-json")
    manifest_path = tmp_path / "shotml-label-manifest.json"
    manifest_path.write_text(json.dumps(_manifest_payload(video_path), indent=2), encoding="utf-8")

    result = run_script(
        str(manifest_path),
        "--threshold-grid",
        "0.35",
        "--threshold",
        "0.35",
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["selected_threshold"] == 0.35
    assert payload["acceptance_dataset_split"] == "all"
    assert payload["selected_summary"]["evaluated_video_count"] == 1
    assert payload["selected_summary"]["label_source_counts"] == {"verified": 1}
    assert payload["selected_summary"]["missed_shot_count"] == 0
    assert payload["selected_summary"]["extra_shot_count"] == 0
    assert payload["selected_summary"]["precision"] == 1.0
    assert payload["selected_summary"]["recall"] == 1.0
    assert payload["selected_summary"]["f1"] == 1.0
    assert payload["selected_summary"]["exact_count_rate"] == 1.0
    assert payload["selected_summary"]["shot_count_coverage"] == {"below_18": 1}
    assert payload["acceptance"]["shot_count_buckets_present"] is False
    assert payload["acceptance"]["passed"] is False
    assert abs(payload["videos"][0]["beep_error_ms"]) <= 80
    assert abs(payload["videos"][0]["stage_time_error_ms"]) <= 120


def test_evaluate_timing_accuracy_writes_json_report_and_table_output(
    tmp_path: Path,
    synthetic_video_factory,
) -> None:
    video_path = synthetic_video_factory(name="timing-table")
    manifest_path = tmp_path / "shotml-label-manifest.json"
    output_path = tmp_path / "timing-report.json"
    manifest_path.write_text(json.dumps(_manifest_payload(video_path), indent=2), encoding="utf-8")

    result = run_script(
        str(manifest_path),
        "--threshold-grid",
        "0.35,0.50",
        "--json-output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    assert "Timing Accuracy" in result.stdout
    assert "Threshold Sweep" in result.stdout
    assert "Worst Videos At Selected Threshold" in result.stdout
    assert "Precision:" in result.stdout
    assert "Shot-count coverage:" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["recommended_threshold"] in {0.35, 0.5}
    assert len(payload["threshold_summaries"]) == 2
    assert payload["videos"][0]["label_source"] == "verified"


def test_evaluate_timing_accuracy_excludes_automatic_truth_by_default(
    tmp_path: Path, synthetic_video_factory
) -> None:
    video_path = synthetic_video_factory(name="timing-auto-label")
    manifest = _manifest_payload(video_path)
    labels = manifest["videos"][0]["labels"]
    labels["status"] = "auto_labeled"
    labels["auto_beep_time_ms"] = labels["verified_beep_time_ms"]
    labels["auto_shot_times_ms"] = labels["verified_shot_times_ms"]
    manifest["videos"][0]["dataset_split"] = "test"
    manifest_path = tmp_path / "shotml-label-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    result = run_script(str(manifest_path), "--threshold-grid", "0.35", "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["acceptance_dataset_split"] == "test"
    assert payload["selected_summary"]["evaluated_video_count"] == 0
    assert payload["skipped_video_reasons"] == {"status_not_accepted": 1}
