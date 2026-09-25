from __future__ import annotations

from pathlib import Path

import pytest

from splitshot.benchmarks.stage_suite import analyze_stage

RELEASE_CORPUS = Path("tests/release_data")
EXPECTED_RAW_MS = {
    "primary.MP4": 10587,
    "secondary.MP4": 4937,
}


@pytest.mark.parametrize("filename, expected_raw_ms", EXPECTED_RAW_MS.items())
def test_stage_suite_tracks_raw_time_reference(filename: str, expected_raw_ms: int) -> None:
    path = RELEASE_CORPUS / filename

    result = analyze_stage(path, threshold=0.5)

    assert result.raw_time_ms is not None
    assert abs(result.raw_time_ms - expected_raw_ms) <= 10
