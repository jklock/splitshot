from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "autolabel_training_manifest.py"


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
        "video_count": 2,
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
                "beep_family": "timer_high",
                "beep_multipass": {
                    "final_beep_time_ms": 400,
                    "tone_beep_time_ms": 410,
                    "model_beep_time_ms": 1200,
                    "tone_model_gap_ms": 790,
                    "final_tone_gap_ms": 10,
                    "final_model_gap_ms": 800,
                    "passes_agree": False,
                    "review_required": True,
                },
                "shot_multipass": {
                    "final_shot_count": 3,
                    "onset_shot_count": 3,
                    "matched_shots": 3,
                    "unmatched_final_count": 0,
                    "unmatched_onset_count": 0,
                    "echo_like_onset_count": 0,
                    "median_match_gap_ms": 1.0,
                    "max_match_gap_ms": 3,
                    "passes_agree": True,
                    "review_required": False,
                },
                "duplicate_group_key": None,
                "duplicate_group_review_required": False,
                "review_flags": ["confidence_saturation"],
                "labels": {
                    "status": "needs_review",
                    "verified_beep_time_ms": None,
                    "verified_shot_times_ms": [],
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
            },
            {
                "path": str(video_path.parent / "blocked.MP4"),
                "relative_path": "blocked.MP4",
                "duration_seconds": 2.0,
                "reference_threshold": 0.35,
                "detector_beep_time_ms": 420,
                "detector_shot_times_ms": [850, 1150],
                "detector_shot_confidences": [0.9, 0.95],
                "detector_shot_count": 2,
                "beep_family": "timer_low",
                "beep_multipass": {
                    "final_beep_time_ms": 420,
                    "tone_beep_time_ms": 440,
                    "model_beep_time_ms": 450,
                    "tone_model_gap_ms": 10,
                    "final_tone_gap_ms": 20,
                    "final_model_gap_ms": 30,
                    "passes_agree": True,
                    "review_required": False,
                },
                "shot_multipass": {
                    "final_shot_count": 2,
                    "onset_shot_count": 3,
                    "matched_shots": 2,
                    "unmatched_final_count": 0,
                    "unmatched_onset_count": 1,
                    "echo_like_onset_count": 0,
                    "median_match_gap_ms": 1.0,
                    "max_match_gap_ms": 3,
                    "passes_agree": False,
                    "review_required": True,
                },
                "duplicate_group_key": None,
                "duplicate_group_review_required": False,
                "review_flags": ["shot_multipass_disagreement"],
                "labels": {
                    "status": "needs_review",
                    "verified_beep_time_ms": None,
                    "verified_shot_times_ms": [],
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
            },
        ],
    }


def test_autolabel_training_manifest_promotes_only_stable_entries(tmp_path: Path, synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(name="autolabel-source")
    manifest_path = tmp_path / "shotml-label-manifest.json"
    summary_path = tmp_path / "training-autolabel-summary.json"
    manifest_path.write_text(json.dumps(_manifest_payload(video_path), indent=2), encoding="utf-8")

    result = run_script(
        str(manifest_path),
        "--summary-output",
        str(summary_path),
        "--format",
        "json",
    )

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert summary["auto_labeled_count"] == 2
    assert manifest["videos"][0]["labels"]["status"] == "auto_labeled"
    assert manifest["videos"][0]["labels"]["auto_beep_time_ms"] == 405
    assert manifest["videos"][0]["labels"]["auto_shot_times_ms"] == [800, 1100, 1450]
    assert manifest["videos"][1]["labels"]["status"] == "auto_labeled"
    assert manifest["videos"][1]["labels"]["auto_beep_time_ms"] == 430
    assert manifest["videos"][1]["labels"]["auto_shot_times_ms"] == [850, 1150]
    assert summary["skipped_reason_counts"] == {}
    assert summary_path.exists()


def test_autolabel_training_manifest_prefers_primary_detector_beep_when_other_passes_agree_early(
    tmp_path: Path,
    synthetic_video_factory,
) -> None:
    video_path = synthetic_video_factory(name="autolabel-primary-beep")
    manifest = _manifest_payload(video_path)
    manifest["video_count"] = 1
    manifest["videos"] = [manifest["videos"][0]]
    manifest["videos"][0]["detector_beep_time_ms"] = 11_100
    manifest["videos"][0]["detector_shot_times_ms"] = [17_900, 18_500, 19_900]
    manifest["videos"][0]["beep_multipass"] = {
        "final_beep_time_ms": 11_100,
        "tone_beep_time_ms": 40,
        "model_beep_time_ms": 42,
        "tone_model_gap_ms": 2,
        "final_tone_gap_ms": 11_060,
        "final_model_gap_ms": 11_058,
        "passes_agree": False,
        "review_required": True,
    }
    manifest_path = tmp_path / "shotml-label-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    result = run_script(str(manifest_path), "--format", "json")

    assert result.returncode == 0
    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    labels = updated["videos"][0]["labels"]
    assert labels["status"] == "auto_labeled"
    assert labels["auto_beep_time_ms"] == 11_100
    assert labels["auto_label_method"] == "primary_detector_preferred"
