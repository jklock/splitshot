from __future__ import annotations

import csv
from pathlib import Path

from splitshot.benchmarks.stage_suite import write_stage_suite_csv


def test_stage_suite_csv_exports_feature_metrics(synthetic_video_factory, tmp_path: Path) -> None:
    video_path = synthetic_video_factory()
    output_path = tmp_path / "stage-suite.csv"

    rows = write_stage_suite_csv([video_path], output_path, threshold=0.35)

    assert len(rows) == 1
    assert output_path.exists()
    with output_path.open(newline="") as csv_file:
        csv_rows = list(csv.DictReader(csv_file))

    assert len(csv_rows) == 1
    row = csv_rows[0]
    assert row["stage"] == video_path.stem
    assert int(row["total_shots"]) == 3
    assert abs(int(row["draw_ms"]) - 400) <= 60
    assert row["raw_time_ms"] == row["stage_time_ms"]
    assert row["split_1_ms"] == row["draw_ms"]
    assert abs(int(row["split_2_ms"]) - 300) <= 70
    assert abs(int(row["beep_to_shot_3_ms"]) - int(row["raw_time_ms"])) <= 1
    assert row["shot_1_confidence"] != ""
