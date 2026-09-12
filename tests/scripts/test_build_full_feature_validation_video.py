from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "build_full_feature_validation_video.py"
SPEC = importlib.util.spec_from_file_location("build_full_feature_validation_video", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_duration_accepts_playwright_webm_stream_tag() -> None:
    metadata = {
        "format": {"duration": "N/A"},
        "streams": [{"duration": "N/A", "tags": {"DURATION": "00:02:03.456000000"}}],
    }

    assert MODULE._duration(metadata) == 123.456


def test_build_video_contains_live_audits_and_finishes_with_rendered_outputs(
    tmp_path: Path,
) -> None:
    fixture = ROOT / "tests" / "fixtures" / "media" / "e2e-stage.mp4"
    inputs = [
        "browser-workflow.webm",
        "browser-audits/ui-surface.webm",
        "browser-audits/interaction.webm",
        "browser-audits/value-controls.webm",
        "browser-audits/remaining-controls.webm",
        "exports/e2e-export-test.mp4",
        "exports/combined-output.mp4",
    ]
    for relative in inputs:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fixture, destination)
    (tmp_path / "visual-feature-proof.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "visible": {
                    "marker": True,
                    "review_text": True,
                    "timer": True,
                    "draw": True,
                    "splits": True,
                    "score": True,
                    "secondary_media": True,
                },
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "shards": [
                    {"id": "media", "cases": ["media.primary-add-replace-clear"]},
                    {
                        "id": "rendered-output",
                        "cases": ["output.individual-real-video"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    result = MODULE.build_video(tmp_path, manifest)

    assert result["result"] == "passed"
    assert result["cases"] == {"required": 2, "covered": 2, "gaps": 0}
    assert result["rendered_outputs_are_final_segments"] is True
    assert [item["id"] for item in result["segments"][-2:]] == [
        "rendered-individual-output",
        "rendered-combined-output",
    ]
    assert (tmp_path / "full-feature-validation.mp4").stat().st_size > 0
    assert (tmp_path / "full-feature-validation.json").stat().st_size > 0


def test_build_video_rejects_missing_visible_feature_proof(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"shards": []}), encoding="utf-8")

    try:
        MODULE.build_video(tmp_path, manifest)
    except RuntimeError as exc:
        assert "Missing visible feature proof" in str(exc)
    else:
        raise AssertionError("missing visible feature proof must fail closed")
