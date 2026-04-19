from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "train_audio_event_model_from_dataset.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_train_audio_event_model_from_dataset_writes_bundle_and_summary(tmp_path: Path) -> None:
    rng = np.random.default_rng(7)
    background = rng.normal(loc=-1.0, scale=0.1, size=(40, 20)).astype(np.float32)
    beep = rng.normal(loc=1.0, scale=0.1, size=(40, 20)).astype(np.float32)
    shot = rng.normal(loc=3.0, scale=0.1, size=(40, 20)).astype(np.float32)
    features = np.vstack([background, beep, shot]).astype(np.float32)
    labels = np.asarray(([0] * 40) + ([1] * 40) + ([2] * 40), dtype=np.int64)
    source_paths = np.asarray(
        (["source-a"] * 10)
        + (["source-b"] * 10)
        + (["source-c"] * 10)
        + (["source-d"] * 10)
        + (["source-a"] * 10)
        + (["source-b"] * 10)
        + (["source-c"] * 10)
        + (["source-d"] * 10)
        + (["source-a"] * 10)
        + (["source-b"] * 10)
        + (["source-c"] * 10)
        + (["source-d"] * 10)
    )
    label_sources = np.asarray(
        (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
        + (["verified"] * 5)
        + (["detector_draft"] * 5)
    )
    is_augmented = np.zeros(labels.size, dtype=bool)
    augmented_features = np.vstack(
        [
            beep[:8] + rng.normal(loc=0.0, scale=0.02, size=(8, 20)).astype(np.float32),
            shot[:8] + rng.normal(loc=0.0, scale=0.02, size=(8, 20)).astype(np.float32),
        ]
    )
    features = np.vstack([features, augmented_features]).astype(np.float32)
    labels = np.concatenate([labels, np.asarray(([1] * 8) + ([2] * 8), dtype=np.int64)])
    source_paths = np.concatenate([source_paths, np.asarray((["source-a"] * 8) + (["source-b"] * 8))])
    label_sources = np.concatenate([label_sources, np.asarray(["verified"] * 16)])
    is_augmented = np.concatenate([is_augmented, np.ones(16, dtype=bool)])
    dataset_path = tmp_path / "training-dataset.npz"
    bundle_path = tmp_path / "model_bundle_candidate.py"
    summary_path = tmp_path / "model-training-summary.json"
    np.savez_compressed(
        dataset_path,
        features=features,
        labels=labels,
        source_paths=source_paths,
        label_sources=label_sources,
        is_augmented=is_augmented,
        class_names=np.asarray(["background", "beep", "shot"]),
    )

    result = run_script(
        str(dataset_path),
        "--output-bundle",
        str(bundle_path),
        "--summary-output",
        str(summary_path),
        "--epochs",
        "80",
        "--class-weight-alpha",
        "0.7",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert bundle_path.exists()
    assert summary_path.exists()
    assert payload["sample_count"] == 136
    assert payload["feature_count"] == 20
    assert payload["split_mode"] == "source"
    assert payload["class_weighting"] == "balanced"
    assert payload["class_weight_alpha"] == 0.7
    assert payload["validation_clean_only"] is True
    assert payload["clean_sample_count"] == 120
    assert payload["augmented_sample_count"] == 16
    assert payload["best_epoch"] >= 1
    assert payload["train_accuracy"] >= 0.95
    assert payload["validation_accuracy"] >= 0.95
    assert payload["validation_macro_recall"] >= 0.95
    assert payload["label_source_counts"]["verified"] == 76
    assert payload["label_source_counts"]["detector_draft"] == 60
    assert payload["validation_confusion_counts"]["background"]["background"] >= 1
    assert payload["robustness_leave_one_source_out"]["available"] is True
    assert payload["robustness_leave_one_source_out"]["fold_count"] == 4
    assert payload["robustness_leave_one_source_out"]["accuracy"] >= 0.95
    assert payload["actual_metrics_available"] is True
    assert payload["verified_validation_sample_count"] > 0
    assert payload["verified_validation_accuracy"] >= 0.95
    assert payload["verified_validation_macro_recall"] >= 0.95
