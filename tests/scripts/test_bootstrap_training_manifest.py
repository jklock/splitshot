from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "bootstrap_training_manifest.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _build_corpus_dir(tmp_path: Path, synthetic_video_factory) -> Path:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    video_a = synthetic_video_factory(name="manifest-a")
    video_b = synthetic_video_factory(name="manifest-b", shot_times_ms=[800, 1100, 1450, 1750])
    shutil.copy2(video_a, corpus_dir / video_a.name)
    shutil.copy2(video_b, corpus_dir / video_b.name)
    return corpus_dir


def test_bootstrap_training_manifest_writes_default_output_and_table(tmp_path: Path, synthetic_video_factory) -> None:
    corpus_dir = _build_corpus_dir(tmp_path, synthetic_video_factory)
    output_path = corpus_dir / "shotml-label-manifest.json"

    result = run_script(str(corpus_dir), "--threshold-grid", "0.35,0.50")

    assert result.returncode == 0
    assert "Training Label Manifest:" in result.stdout
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["video_count"] == 2
    assert payload["videos"][0]["labels"]["status"] == "needs_review"
    assert isinstance(payload["videos"][0]["detector_shot_times_ms"], list)
    assert "shot_multipass" in payload["videos"][0]


def test_bootstrap_training_manifest_emits_json_to_stdout(tmp_path: Path, synthetic_video_factory) -> None:
    corpus_dir = _build_corpus_dir(tmp_path, synthetic_video_factory)
    output_path = tmp_path / "custom-manifest.json"

    result = run_script(
        str(corpus_dir),
        "--threshold-grid",
        "0.35,0.50",
        "--output",
        str(output_path),
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["input"] == str(corpus_dir.resolve())
    assert output_path.exists()
    assert len(payload["videos"]) == 2
    assert "beep_multipass" in payload["videos"][0]


def test_bootstrap_training_manifest_preserves_existing_labels(tmp_path: Path, synthetic_video_factory) -> None:
    corpus_dir = _build_corpus_dir(tmp_path, synthetic_video_factory)
    output_path = corpus_dir / "shotml-label-manifest.json"

    first = run_script(str(corpus_dir), "--threshold-grid", "0.35,0.50")
    assert first.returncode == 0

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    payload["videos"][0]["labels"] = {
        "status": "verified",
        "verified_beep_time_ms": 1234,
        "verified_shot_times_ms": [2000, 2500],
        "auto_beep_time_ms": 1250,
        "auto_shot_times_ms": [1990, 2490],
        "auto_label_score": 0.91,
        "auto_label_method": "pair_consensus",
        "auto_label_reasons": ["beep_pair_agreement:primary_detector+tone"],
        "review_notes": "confirmed manually",
        "timer_model": "PACT",
        "range_name": "East Bay",
        "device_notes": "phone mic",
        "environment_tags": ["outdoor", "wind"],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    second = run_script(str(corpus_dir), "--threshold-grid", "0.35,0.50")
    assert second.returncode == 0

    merged = json.loads(output_path.read_text(encoding="utf-8"))
    assert merged["videos"][0]["labels"]["status"] == "verified"
    assert merged["videos"][0]["labels"]["verified_beep_time_ms"] == 1234
    assert merged["videos"][0]["labels"]["auto_beep_time_ms"] == 1250
    assert merged["videos"][0]["labels"]["auto_label_score"] == 0.91
    assert merged["videos"][0]["labels"]["review_notes"] == "confirmed manually"
