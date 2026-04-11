from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from splitshot.analysis.detection import analyze_video_audio
from splitshot.domain.models import Project, ShotEvent
from splitshot.presentation.stage import build_stage_presentation
from splitshot.timeline.model import average_split_ms


@dataclass(slots=True)
class StageBenchmark:
    stage: str
    file: str
    beep_ms: int | None
    draw_ms: int | None
    raw_time_ms: int | None
    total_shots: int
    avg_split_ms: int | None
    shot_times_ms: list[int]
    segment_times_ms: list[int | None]
    cumulative_times_ms: list[int | None]
    split_times_ms: list[int]
    confidences: list[float | None]


def _seconds(value_ms: int | None) -> str:
    if value_ms is None:
        return ""
    return f"{value_ms / 1000.0:.3f}"


def _integer(value: int | None) -> str:
    return "" if value is None else str(value)


def _stage_name(path: Path) -> str:
    return path.stem


def _split_times(shots: list[ShotEvent]) -> list[int]:
    return [
        shots[index].time_ms - shots[index - 1].time_ms
        for index in range(1, len(shots))
    ]


def analyze_stage(path: str | Path, threshold: float = 0.5) -> StageBenchmark:
    stage_path = Path(path)
    result = analyze_video_audio(stage_path, threshold=threshold)
    shots = sorted(result.shots, key=lambda shot: shot.time_ms)
    shot_times_ms = [shot.time_ms for shot in shots]
    confidences = [shot.confidence for shot in shots]
    splits = _split_times(shots)
    draw_ms = None
    raw_time = None
    if result.beep_time_ms is not None and shots:
        draw_ms = shots[0].time_ms - result.beep_time_ms
        raw_time = shots[-1].time_ms - result.beep_time_ms

    project = Project()
    project.analysis.beep_time_ms_primary = result.beep_time_ms
    project.analysis.shots = shots
    presentation = build_stage_presentation(project)

    return StageBenchmark(
        stage=_stage_name(stage_path),
        file=str(stage_path),
        beep_ms=result.beep_time_ms,
        draw_ms=draw_ms,
        raw_time_ms=raw_time,
        total_shots=len(shots),
        avg_split_ms=average_split_ms(project),
        shot_times_ms=shot_times_ms,
        segment_times_ms=[segment.segment_ms for segment in presentation.timing_segments],
        cumulative_times_ms=[segment.cumulative_ms for segment in presentation.timing_segments],
        split_times_ms=splits,
        confidences=confidences,
    )


def default_stage_paths(root: str | Path = ".") -> list[Path]:
    base = Path(root)
    return [path for path in (base / f"Stage{index}.MP4" for index in range(1, 5)) if path.exists()]


def _fieldnames(max_shots: int) -> list[str]:
    fields = [
        "stage",
        "file",
        "beep_ms",
        "beep_s",
        "draw_ms",
        "draw_s",
        "raw_time_ms",
        "raw_time_s",
        "stage_time_ms",
        "stage_time_s",
        "total_shots",
        "avg_split_ms",
        "avg_split_s",
    ]
    for index in range(1, max_shots + 1):
        fields.extend(
            [
                f"shot_{index}_ms",
                f"shot_{index}_s",
                f"shot_{index}_confidence",
            ]
        )
    for index in range(1, max_shots + 1):
        fields.extend([f"split_{index}_ms", f"split_{index}_s"])
    for index in range(1, max_shots + 1):
        fields.extend([f"beep_to_shot_{index}_ms", f"beep_to_shot_{index}_s"])
    return fields


def _row_dict(row: StageBenchmark, max_shots: int) -> dict[str, str | int]:
    payload: dict[str, str | int] = {
        "stage": row.stage,
        "file": row.file,
        "beep_ms": _integer(row.beep_ms),
        "beep_s": _seconds(row.beep_ms),
        "draw_ms": _integer(row.draw_ms),
        "draw_s": _seconds(row.draw_ms),
        "raw_time_ms": _integer(row.raw_time_ms),
        "raw_time_s": _seconds(row.raw_time_ms),
        "stage_time_ms": _integer(row.raw_time_ms),
        "stage_time_s": _seconds(row.raw_time_ms),
        "total_shots": row.total_shots,
        "avg_split_ms": _integer(row.avg_split_ms),
        "avg_split_s": _seconds(row.avg_split_ms),
    }
    for index in range(1, max_shots + 1):
        shot_index = index - 1
        if shot_index < len(row.shot_times_ms):
            shot_ms = row.shot_times_ms[shot_index]
            confidence = row.confidences[shot_index]
            payload[f"shot_{index}_ms"] = str(shot_ms)
            payload[f"shot_{index}_s"] = _seconds(shot_ms)
            payload[f"shot_{index}_confidence"] = (
                "" if confidence is None else f"{float(confidence):.3f}"
            )
        else:
            payload[f"shot_{index}_ms"] = ""
            payload[f"shot_{index}_s"] = ""
            payload[f"shot_{index}_confidence"] = ""
    for index in range(1, max_shots + 1):
        split_index = index - 1
        if split_index < len(row.segment_times_ms):
            split_ms = row.segment_times_ms[split_index]
            payload[f"split_{index}_ms"] = _integer(split_ms)
            payload[f"split_{index}_s"] = _seconds(split_ms)
        else:
            payload[f"split_{index}_ms"] = ""
            payload[f"split_{index}_s"] = ""
    for index in range(1, max_shots + 1):
        cumulative_index = index - 1
        if cumulative_index < len(row.cumulative_times_ms):
            cumulative_ms = row.cumulative_times_ms[cumulative_index]
            payload[f"beep_to_shot_{index}_ms"] = _integer(cumulative_ms)
            payload[f"beep_to_shot_{index}_s"] = _seconds(cumulative_ms)
        else:
            payload[f"beep_to_shot_{index}_ms"] = ""
            payload[f"beep_to_shot_{index}_s"] = ""
    return payload


def write_stage_suite_csv(
    paths: Iterable[str | Path],
    output_path: str | Path,
    threshold: float = 0.5,
) -> list[StageBenchmark]:
    rows = [analyze_stage(path, threshold=threshold) for path in paths]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    max_shots = max((row.total_shots for row in rows), default=0)
    fieldnames = _fieldnames(max_shots)
    with output.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(_row_dict(row, max_shots))
    return rows
