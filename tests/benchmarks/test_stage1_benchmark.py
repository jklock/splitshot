from __future__ import annotations

from pathlib import Path

from splitshot.analysis.detection import analyze_video_audio


STAGE1_PATH = Path(".training") / "Stage1.MP4"
EXPECTED_SHOT_COUNT = 18
EXPECTED_DRAW_MS = 1950
EXPECTED_STAGE_MS = 13650
EXPECTED_SPLITS_MS = [
    600,
    750,
    400,
    550,
    400,
    600,
    400,
    850,
    350,
    2600,
    400,
    800,
    350,
    950,
    550,
    700,
    450,
]


def test_stage1_benchmark_tracks_shotstreamer_reference() -> None:
    assert STAGE1_PATH.exists(), f"Missing benchmark media: {STAGE1_PATH}"
    result = analyze_video_audio(str(STAGE1_PATH), threshold=0.5)

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
