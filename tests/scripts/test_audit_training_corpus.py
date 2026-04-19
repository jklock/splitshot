from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "audit_training_corpus.py"


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
    video_a = synthetic_video_factory(name="corpus-a")
    video_b = synthetic_video_factory(name="corpus-b", shot_times_ms=[800, 1100, 1450, 1750])
    shutil.copy2(video_a, corpus_dir / video_a.name)
    shutil.copy2(video_b, corpus_dir / video_b.name)
    return corpus_dir


def _build_duplicate_stage_corpus(tmp_path: Path, synthetic_video_factory) -> Path:
    corpus_dir = tmp_path / "duplicate-stage-corpus"
    corpus_dir.mkdir()
    stage_a = synthetic_video_factory(name="stage-source", shot_times_ms=[800, 1100, 1450])
    stage_b = synthetic_video_factory(name="stage-source-two", shot_times_ms=[800, 1100, 1450, 1750])
    shutil.copy2(stage_a, corpus_dir / "Stage1.MP4")
    shutil.copy2(stage_b, corpus_dir / "Stage1 2.MP4")
    return corpus_dir


def test_audit_training_corpus_emits_json_summary_for_directory(tmp_path: Path, synthetic_video_factory) -> None:
    corpus_dir = _build_corpus_dir(tmp_path, synthetic_video_factory)

    result = run_script(
        str(corpus_dir),
        "--threshold-grid",
        "0.35,0.50",
        "--reference-threshold",
        "0.35",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["input"] == str(corpus_dir.resolve())
    assert payload["video_count"] == 2
    assert payload["threshold_grid"] == [0.35, 0.5]
    assert len(payload["videos"]) == 2
    assert payload["videos"][0]["reference_threshold"] == 0.35
    assert "consistency" in payload["videos"][0]
    assert "fingerprint" in payload["videos"][0]
    assert "beep_multipass" in payload["videos"][0]
    assert "shot_multipass" in payload["videos"][0]
    assert "duplicate_groups" in payload


def test_audit_training_corpus_writes_json_report_and_table_output(tmp_path: Path, synthetic_video_factory) -> None:
    corpus_dir = _build_corpus_dir(tmp_path, synthetic_video_factory)
    json_output = tmp_path / "training-corpus-audit.json"

    result = run_script(
        str(corpus_dir),
        "--threshold-grid",
        "0.35,0.50",
        "--format",
        "table",
        "--json-output",
        str(json_output),
    )

    assert result.returncode == 0
    assert "Training Corpus Audit:" in result.stdout
    assert "video | shots | shot span | beep span | beep cmp | shot cmp | family | median conf | shot hf | flags" in result.stdout
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["video_count"] == 2
    assert len(payload["videos"]) == 2


def test_audit_training_corpus_reports_duplicate_stage_groups(tmp_path: Path, synthetic_video_factory) -> None:
    corpus_dir = _build_duplicate_stage_corpus(tmp_path, synthetic_video_factory)

    result = run_script(str(corpus_dir), "--threshold-grid", "0.35,0.50", "--format", "json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["duplicate_groups"]) == 1
    assert payload["duplicate_groups"][0]["group_key"] == "stage1"
    assert payload["duplicate_groups"][0]["shot_count_span"] >= 1