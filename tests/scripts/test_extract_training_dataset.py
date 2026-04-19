from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "extract_training_dataset.py"


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
                "beep_family": "timer_high",
                "beep_multipass": {
                    "final_beep_time_ms": 400,
                    "tone_beep_time_ms": 400,
                    "model_beep_time_ms": 400,
                    "tone_model_gap_ms": 0,
                    "final_tone_gap_ms": 0,
                    "final_model_gap_ms": 0,
                    "passes_agree": True,
                    "review_required": False,
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


def test_extract_training_dataset_from_verified_manifest(tmp_path: Path, synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(name="dataset-verified")
    manifest_path = tmp_path / "shotml-label-manifest.json"
    output_path = tmp_path / "training-dataset.npz"
    summary_path = tmp_path / "training-dataset-summary.json"
    manifest_path.write_text(json.dumps(_manifest_payload(video_path), indent=2), encoding="utf-8")

    result = run_script(
        str(manifest_path),
        "--output",
        str(output_path),
        "--summary-output",
        str(summary_path),
        "--format",
        "table",
    )

    assert result.returncode == 0
    assert "Training Dataset:" in result.stdout
    archive = np.load(output_path)
    assert archive["features"].shape[0] >= 4
    assert archive["features"].shape[1] == 20
    assert set(archive["labels"].tolist()) == {0, 1, 2}
    assert archive["source_paths"].shape[0] == archive["features"].shape[0]
    assert archive["label_sources"].shape[0] == archive["features"].shape[0]
    assert archive["is_augmented"].shape[0] == archive["features"].shape[0]
    assert not np.any(archive["is_augmented"])
    assert set(archive["label_sources"].tolist()) == {"verified"}
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["included_video_count"] == 1
    assert summary["class_counts"]["beep"] == 1
    assert summary["class_counts"]["shot"] == 3
    assert summary["clean_sample_count"] == archive["features"].shape[0]
    assert summary["augmented_sample_count"] == 0
    assert summary["label_source_counts"]["verified"] >= 4
    assert summary["label_source_counts"]["detector_draft"] == 0


def test_extract_training_dataset_can_use_detector_drafts(tmp_path: Path, synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(name="dataset-draft")
    manifest = _manifest_payload(video_path)
    manifest["videos"][0]["labels"]["status"] = "needs_review"
    manifest["videos"][0]["labels"]["verified_beep_time_ms"] = None
    manifest["videos"][0]["labels"]["verified_shot_times_ms"] = []
    manifest_path = tmp_path / "shotml-label-manifest.json"
    output_path = tmp_path / "training-dataset.npz"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    result = run_script(
        str(manifest_path),
        "--output",
        str(output_path),
        "--use-detector-drafts",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["use_detector_drafts"] is True
    assert payload["detector_draft_policy"] == "review-clean"
    assert payload["label_source_counts"]["detector_draft"] >= 4
    archive = np.load(output_path)
    assert archive["features"].shape[0] >= 4
    assert set(archive["label_sources"].tolist()) == {"detector_draft"}


def test_extract_training_dataset_can_use_auto_consensus_labels(tmp_path: Path, synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(name="dataset-auto")
    manifest = _manifest_payload(video_path)
    manifest["videos"][0]["labels"]["status"] = "auto_labeled"
    manifest["videos"][0]["labels"]["verified_beep_time_ms"] = None
    manifest["videos"][0]["labels"]["verified_shot_times_ms"] = []
    manifest["videos"][0]["labels"]["auto_beep_time_ms"] = 420
    manifest["videos"][0]["labels"]["auto_shot_times_ms"] = [810, 1110, 1460]
    manifest["videos"][0]["labels"]["auto_label_score"] = 0.88
    manifest["videos"][0]["labels"]["auto_label_method"] = "pair_consensus"
    manifest["videos"][0]["labels"]["auto_label_reasons"] = ["beep_pair_agreement:primary_detector+tone"]
    manifest_path = tmp_path / "shotml-label-manifest.json"
    output_path = tmp_path / "training-dataset-auto.npz"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    result = run_script(
        str(manifest_path),
        "--output",
        str(output_path),
        "--include-status",
        "auto_labeled",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["included_video_count"] == 1
    assert payload["label_source_counts"]["auto_consensus"] >= 4
    archive = np.load(output_path)
    assert set(archive["label_sources"].tolist()) == {"auto_consensus"}


def test_extract_training_dataset_can_augment_event_windows(tmp_path: Path, synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(name="dataset-augment")
    manifest_path = tmp_path / "shotml-label-manifest.json"
    output_path = tmp_path / "training-dataset.npz"
    manifest_path.write_text(json.dumps(_manifest_payload(video_path), indent=2), encoding="utf-8")

    result = run_script(
        str(manifest_path),
        "--output",
        str(output_path),
        "--augment-replicas-per-event",
        "1",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    archive = np.load(output_path)
    assert payload["augment_replicas_per_event"] == 1
    assert payload["augmented_sample_count"] >= 4
    assert int(np.sum(archive["is_augmented"])) == payload["augmented_sample_count"]
    assert archive["features"].shape[0] >= 8


def test_extract_training_dataset_review_clean_blocks_flagged_detector_drafts(tmp_path: Path, synthetic_video_factory) -> None:
    video_path = synthetic_video_factory(name="dataset-flagged-draft")
    manifest = _manifest_payload(video_path)
    manifest["videos"][0]["labels"]["status"] = "needs_review"
    manifest["videos"][0]["labels"]["verified_beep_time_ms"] = None
    manifest["videos"][0]["labels"]["verified_shot_times_ms"] = []
    manifest["videos"][0]["review_flags"] = ["shot_multipass_disagreement"]
    manifest_path = tmp_path / "shotml-label-manifest.json"
    output_path = tmp_path / "training-dataset.npz"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    result = run_script(
        str(manifest_path),
        "--output",
        str(output_path),
        "--use-detector-drafts",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    archive = np.load(output_path)
    assert payload["included_video_count"] == 0
    assert payload["skipped_video_reasons"]["detector_draft_blocked_by_review_flags"] == 1
    assert archive["features"].shape[0] == 0
