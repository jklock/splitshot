from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "train_shot_verifier.py"


def test_verifier_training_rejects_unreviewed_detector_drafts(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "input": str(tmp_path),
                "videos": [
                    {
                        "path": str(tmp_path / "draft.mp4"),
                        "dataset_split": "train",
                        "detector_shot_times_ms": [1000],
                        "labels": {"status": "needs_review"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(manifest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "No manually verified training examples" in result.stderr
