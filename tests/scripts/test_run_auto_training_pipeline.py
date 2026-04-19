from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "run_auto_training_pipeline.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_run_auto_training_pipeline_builds_candidate_from_clean_corpus(tmp_path: Path, synthetic_video_factory) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    video_a = synthetic_video_factory(name="pipeline-a")
    video_b = synthetic_video_factory(name="pipeline-b", shot_times_ms=[800, 1100, 1450, 1750])
    shutil.copy2(video_a, corpus_dir / video_a.name)
    shutil.copy2(video_b, corpus_dir / video_b.name)

    manifest_path = tmp_path / "shotml-label-manifest.json"
    autolabel_summary_path = tmp_path / "training-autolabel-summary.json"
    dataset_path = tmp_path / "training-dataset-auto.npz"
    dataset_summary_path = tmp_path / "training-dataset-auto-summary.json"
    bundle_path = tmp_path / "model_bundle_candidate_auto.py"
    training_summary_path = tmp_path / "model-training-auto-summary.json"
    pipeline_summary_path = tmp_path / "auto-training-pipeline-summary.json"

    result = run_script(
        str(corpus_dir),
        "--manifest-output",
        str(manifest_path),
        "--autolabel-summary-output",
        str(autolabel_summary_path),
        "--dataset-output",
        str(dataset_path),
        "--dataset-summary-output",
        str(dataset_summary_path),
        "--output-bundle",
        str(bundle_path),
        "--training-summary-output",
        str(training_summary_path),
        "--pipeline-summary-output",
        str(pipeline_summary_path),
        "--train-epochs",
        "20",
        "--class-weight-alpha",
        "0.7",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert any(video["labels"]["status"] == "auto_labeled" for video in manifest["videos"])
    dataset = np.load(dataset_path)
    assert dataset["features"].shape[0] > 0
    assert dataset["is_augmented"].shape[0] == dataset["features"].shape[0]
    assert set(dataset["label_sources"].tolist()) <= {"auto_consensus", "verified"}
    assert bundle_path.exists()
    training_summary = json.loads(training_summary_path.read_text(encoding="utf-8"))
    assert training_summary["sample_count"] > 0
    assert training_summary["class_weight_alpha"] == 0.7
    assert training_summary["validation_clean_only"] is True
    assert "deployment_validation_accuracy" in training_summary
    assert "robustness_leave_one_source_out" in training_summary
    assert training_summary["actual_metrics_available"] is False
    assert payload["autolabel_summary"]["auto_labeled_count"] >= 1
    assert pipeline_summary_path.exists()
