from __future__ import annotations

from dataclasses import dataclass

from splitshot.domain.models import Project, ShotEvent


@dataclass(slots=True)
class SplitRow:
    shot_id: str
    shot_number: int
    absolute_time_ms: int
    split_ms: int | None
    score_letter: str | None
    source: str
    confidence: float | None


def sort_shots(shots: list[ShotEvent]) -> list[ShotEvent]:
    return sorted(shots, key=lambda shot: shot.time_ms)


def compute_split_rows(project: Project) -> list[SplitRow]:
    shots = sort_shots(project.analysis.shots)
    rows: list[SplitRow] = []
    previous_time = None
    for index, shot in enumerate(shots, start=1):
        rows.append(
            SplitRow(
                shot_id=shot.id,
                shot_number=index,
                absolute_time_ms=shot.time_ms,
                split_ms=None if previous_time is None else shot.time_ms - previous_time,
                score_letter=None if shot.score is None else shot.score.letter.value,
                source=shot.source.value,
                confidence=shot.confidence,
            )
        )
        previous_time = shot.time_ms
    return rows


def draw_time_ms(project: Project) -> int | None:
    shots = sort_shots(project.analysis.shots)
    if not shots or project.analysis.beep_time_ms_primary is None:
        return None
    return shots[0].time_ms - project.analysis.beep_time_ms_primary


def stage_time_ms(project: Project) -> int | None:
    shots = sort_shots(project.analysis.shots)
    if not shots or project.analysis.beep_time_ms_primary is None:
        return None
    return shots[-1].time_ms - project.analysis.beep_time_ms_primary


def raw_time_ms(project: Project) -> int | None:
    return stage_time_ms(project)


def average_split_ms(project: Project) -> int | None:
    rows = compute_split_rows(project)
    splits = [row.split_ms for row in rows if row.split_ms is not None]
    if not splits:
        return None
    return int(round(sum(splits) / len(splits)))


def total_time_ms(project: Project) -> int | None:
    shots = sort_shots(project.analysis.shots)
    if not shots:
        return None
    return shots[-1].time_ms
