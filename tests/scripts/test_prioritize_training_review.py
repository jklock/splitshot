from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analysis" / "prioritize_training_review.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _video_entry(
    name: str,
    *,
    duration_seconds: float,
    status: str = "needs_review",
    beep_family: str = "timer_low",
    review_flags: list[str] | None = None,
    duplicate_group_key: str | None = None,
    duplicate_group_review_required: bool = False,
    detector_shot_count: int = 18,
    beep_gap_ms: int = 0,
    shot_review_required: bool = False,
    beep_review_required: bool = False,
) -> dict[str, object]:
    path = str((ROOT / "tests" / "artifacts" / "test_video" / name).resolve())
    return {
        "path": path,
        "relative_path": name,
        "duration_seconds": duration_seconds,
        "detector_beep_time_ms": 1400,
        "detector_shot_count": detector_shot_count,
        "beep_family": beep_family,
        "beep_multipass": {
            "final_beep_time_ms": 1400,
            "tone_beep_time_ms": 1400,
            "model_beep_time_ms": 1400 + beep_gap_ms,
            "tone_model_gap_ms": beep_gap_ms,
            "final_tone_gap_ms": 0,
            "final_model_gap_ms": beep_gap_ms,
            "passes_agree": beep_gap_ms <= 120,
            "review_required": beep_review_required,
        },
        "shot_multipass": {
            "final_shot_count": detector_shot_count,
            "onset_shot_count": detector_shot_count,
            "matched_shots": detector_shot_count,
            "unmatched_final_count": 0,
            "unmatched_onset_count": 0,
            "echo_like_onset_count": 0,
            "median_match_gap_ms": 1.0,
            "max_match_gap_ms": 3,
            "passes_agree": not shot_review_required,
            "review_required": shot_review_required,
        },
        "duplicate_group_key": duplicate_group_key,
        "duplicate_group_review_required": duplicate_group_review_required,
        "review_flags": review_flags or [],
        "labels": {
            "status": status,
            "verified_beep_time_ms": None,
            "verified_shot_times_ms": [],
            "review_notes": "",
            "timer_model": "",
            "range_name": "",
            "device_notes": "",
            "environment_tags": [],
        },
    }


def test_prioritize_training_review_ranks_clean_clips_before_duplicates_and_blocked(tmp_path: Path) -> None:
    manifest_path = tmp_path / "shotml-label-manifest.json"
    json_output = tmp_path / "training-review-queue.json"
    payload = {
        "input": str(tmp_path),
        "video_count": 6,
        "threshold_grid": [0.35],
        "reference_threshold": 0.35,
        "duplicate_groups": [],
        "videos": [
            _video_entry("clean-low.MP4", duration_seconds=30.0, beep_family="timer_low"),
            _video_entry("clean-high.MP4", duration_seconds=34.0, beep_family="timer_high"),
            _video_entry(
                "Stage1.MP4",
                duration_seconds=36.0,
                beep_family="timer_low",
                duplicate_group_key="stage1",
                duplicate_group_review_required=True,
                review_flags=["duplicate_stage_inconsistency"],
            ),
            _video_entry(
                "Stage1 2.MP4",
                duration_seconds=40.0,
                beep_family="timer_low",
                duplicate_group_key="stage1",
                duplicate_group_review_required=True,
                review_flags=["duplicate_stage_inconsistency", "beep_multipass_disagreement"],
                beep_gap_ms=1800,
                beep_review_required=True,
            ),
            _video_entry(
                "clipped.MP4",
                duration_seconds=28.0,
                review_flags=["possible_clipping"],
            ),
            _video_entry("verified.MP4", duration_seconds=29.0, status="verified"),
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = run_script(
        str(manifest_path),
        "--json-output",
        str(json_output),
        "--format",
        "json",
    )

    assert result.returncode == 0
    queue = json.loads(result.stdout)
    assert json.loads(json_output.read_text(encoding="utf-8")) == queue
    assert queue["queued_video_count"] == 5
    assert queue["status_counts"] == {"needs_review": 5}
    assert queue["entries"][0]["relative_path"] == "clean-low.MP4"
    assert queue["entries"][1]["relative_path"] == "clean-high.MP4"
    assert queue["entries"][2]["relative_path"] == "Stage1.MP4"
    assert queue["entries"][2]["recommended_action"] == "review_duplicate_representative"
    assert queue["entries"][2]["duplicate_representative"] is True
    assert queue["entries"][3]["relative_path"] == "Stage1 2.MP4"
    assert queue["entries"][3]["recommended_action"] == "defer_duplicate"
    assert queue["entries"][4]["relative_path"] == "clipped.MP4"
    assert queue["entries"][4]["recommended_action"] == "blocked"
    assert queue["action_counts"]["blocked"] == 1
    assert queue["beep_family_counts"]["timer_low"] == 4
    assert queue["beep_family_counts"]["timer_high"] == 1


def test_prioritize_training_review_treats_echo_like_onsets_as_nonblocking(tmp_path: Path) -> None:
    manifest_path = tmp_path / "shotml-label-manifest.json"
    payload = {
        "input": str(tmp_path),
        "video_count": 2,
        "threshold_grid": [0.35],
        "reference_threshold": 0.35,
        "duplicate_groups": [],
        "videos": [
            _video_entry("echo-clean.MP4", duration_seconds=30.0, beep_family="timer_low"),
            _video_entry("raw-extra.MP4", duration_seconds=30.0, beep_family="timer_low"),
        ],
    }
    payload["videos"][0]["shot_multipass"] = {
        "final_shot_count": 18,
        "onset_shot_count": 20,
        "matched_shots": 18,
        "unmatched_final_count": 0,
        "unmatched_onset_count": 2,
        "echo_like_onset_count": 2,
        "median_match_gap_ms": 1.0,
        "max_match_gap_ms": 3,
        "passes_agree": True,
        "review_required": False,
    }
    payload["videos"][1]["shot_multipass"] = {
        "final_shot_count": 18,
        "onset_shot_count": 20,
        "matched_shots": 18,
        "unmatched_final_count": 0,
        "unmatched_onset_count": 2,
        "echo_like_onset_count": 0,
        "median_match_gap_ms": 1.0,
        "max_match_gap_ms": 3,
        "passes_agree": True,
        "review_required": False,
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = run_script(str(manifest_path), "--format", "json")

    assert result.returncode == 0
    queue = json.loads(result.stdout)
    assert [entry["relative_path"] for entry in queue["entries"]] == ["echo-clean.MP4", "raw-extra.MP4"]
    assert queue["entries"][0]["shot_echo_like_count"] == 2
    assert queue["entries"][0]["shot_effective_unmatched_count"] == 0
    assert queue["entries"][1]["shot_echo_like_count"] == 0
    assert queue["entries"][1]["shot_effective_unmatched_count"] == 2
    assert queue["entries"][0]["recommended_action"] == "review_now"
    assert queue["entries"][1]["recommended_action"] == "review_now"


def test_prioritize_training_review_table_output_respects_limit(tmp_path: Path) -> None:
    manifest_path = tmp_path / "shotml-label-manifest.json"
    payload = {
        "input": str(tmp_path),
        "video_count": 3,
        "threshold_grid": [0.35],
        "reference_threshold": 0.35,
        "duplicate_groups": [],
        "videos": [
            _video_entry("first.MP4", duration_seconds=30.0, beep_family="timer_low"),
            _video_entry("second.MP4", duration_seconds=31.0, beep_family="timer_high"),
            _video_entry("third.MP4", duration_seconds=32.0, review_flags=["possible_clipping"]),
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = run_script(str(manifest_path), "--limit", "2", "--format", "table")

    assert result.returncode == 0
    assert "Training Review Queue:" in result.stdout
    assert "rank | video | score | action | family | shots | beep gap | duplicate | flags" in result.stdout
    assert "Showing 2 of 3 queued videos." in result.stdout


def test_prioritize_training_review_does_not_mark_consistent_duplicates_as_representatives(tmp_path: Path) -> None:
    manifest_path = tmp_path / "shotml-label-manifest.json"
    payload = {
        "input": str(tmp_path),
        "video_count": 2,
        "threshold_grid": [0.35],
        "reference_threshold": 0.35,
        "duplicate_groups": [],
        "videos": [
            _video_entry(
                "Stage3.MP4",
                duration_seconds=28.0,
                beep_family="timer_high",
                duplicate_group_key="stage3",
                duplicate_group_review_required=False,
                review_flags=["beep_multipass_disagreement"],
                beep_gap_ms=1308,
                beep_review_required=True,
            ),
            _video_entry(
                "Stage3 2.MP4",
                duration_seconds=57.0,
                beep_family="timer_low",
                duplicate_group_key="stage3",
                duplicate_group_review_required=False,
                review_flags=["beep_multipass_disagreement"],
                beep_gap_ms=1383,
                beep_review_required=True,
            ),
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = run_script(str(manifest_path), "--format", "json")

    assert result.returncode == 0
    queue = json.loads(result.stdout)
    assert queue["entries"][0]["duplicate_representative"] is False
    assert queue["entries"][1]["duplicate_representative"] is False
    assert queue["entries"][0]["recommended_action"] == "review_now"
    assert queue["entries"][1]["recommended_action"] == "review_now"