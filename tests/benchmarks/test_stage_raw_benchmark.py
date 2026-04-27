from __future__ import annotations

from pathlib import Path

import pytest

from splitshot.benchmarks.stage_suite import analyze_stage


EXPECTED_RAW_MS = {
    "Stage1.MP4": 13550,
    "Stage2.MP4": 19830,
    "Stage3.MP4": 13620,
    "Stage4.MP4": 17010,
}


@pytest.mark.parametrize("filename, expected_raw_ms", EXPECTED_RAW_MS.items())
def test_stage_suite_tracks_raw_time_reference(filename: str, expected_raw_ms: int) -> None:
    path = Path(".training") / filename
    assert path.exists(), f"Missing benchmark media: {path}"

    result = analyze_stage(path, threshold=0.5)

    assert result.raw_time_ms is not None
    assert abs(result.raw_time_ms - expected_raw_ms) <= 10
