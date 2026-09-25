from __future__ import annotations

from pathlib import Path

from splitshot.analysis.detection import analyze_video_audio

RELEASE_PRIMARY_PATH = Path("tests/release_data/primary.MP4")
EXPECTED_SHOT_COUNT = 7
EXPECTED_DRAW_MS = 1894
EXPECTED_STAGE_MS = 10587
EXPECTED_SPLITS_MS = [
    381,
    1806,
    1196,
    3148,
    261,
    1901,
]


def test_primary_release_benchmark_tracks_reference() -> None:
    result = analyze_video_audio(str(RELEASE_PRIMARY_PATH), threshold=0.5)

    assert result.beep_time_ms is not None
    assert len(result.shots) == EXPECTED_SHOT_COUNT

    draw_ms = result.shots[0].time_ms - result.beep_time_ms
    stage_ms = result.shots[-1].time_ms - result.beep_time_ms
    assert abs(draw_ms - EXPECTED_DRAW_MS) <= 250
    assert abs(stage_ms - EXPECTED_STAGE_MS) <= 250

    actual_splits = [
        result.shots[index].time_ms - result.shots[index - 1].time_ms
        for index in range(1, len(result.shots))
    ]
    assert len(actual_splits) == len(EXPECTED_SPLITS_MS)
    for actual, expected in zip(actual_splits, EXPECTED_SPLITS_MS):
        assert abs(actual - expected) <= 200
