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
    penalty_counts: dict[str, float]
    source: str
    confidence: float | None


def sort_shots(shots: list[ShotEvent]) -> list[ShotEvent]:
    return sorted(shots, key=lambda shot: shot.time_ms)


def split_reset_shot_ids(project: Project) -> set[str]:
    shots = sort_shots(project.analysis.shots)
    if len(shots) < 2:
        return set()

    shot_index = {shot.id: index for index, shot in enumerate(shots)}
    reset_ids: set[str] = set()
    for event in project.analysis.events:
        if event.before_shot_id and event.before_shot_id in shot_index:
            reset_ids.add(event.before_shot_id)
            continue
        if event.after_shot_id and event.after_shot_id in shot_index:
            next_index = shot_index[event.after_shot_id] + 1
            if next_index < len(shots):
                reset_ids.add(shots[next_index].id)
    return reset_ids


def compute_split_rows(project: Project) -> list[SplitRow]:
    shots = sort_shots(project.analysis.shots)
    reset_ids = split_reset_shot_ids(project)
    rows: list[SplitRow] = []
    previous_time = None
    for index, shot in enumerate(shots, start=1):
        rows.append(
            SplitRow(
                shot_id=shot.id,
                shot_number=index,
                absolute_time_ms=shot.time_ms,
                split_ms=(
                    None
                    if previous_time is None
                    else 0
                    if shot.id in reset_ids
                    else shot.time_ms - previous_time
                ),
                score_letter=None if shot.score is None else shot.score.letter.value,
                penalty_counts={} if shot.score is None else dict(shot.score.penalty_counts),
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
