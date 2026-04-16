from __future__ import annotations

from dataclasses import dataclass, field

from splitshot.domain.models import Project, ShotEvent, TimingEvent


@dataclass(slots=True)
class SplitAction:
    event_id: str | None
    kind: str
    label: str
    placement: str = "interval"
    synthetic: bool = False


@dataclass(slots=True)
class SplitRow:
    row_id: str
    row_type: str
    label: str
    start_label: str
    end_label: str
    shot_id: str | None
    shot_number: int | None
    absolute_time_ms: int
    cumulative_ms: int | None
    split_ms: int | None
    score_letter: str | None
    penalty_counts: dict[str, float]
    source: str | None
    confidence: float | None
    actions: list[SplitAction] = field(default_factory=list)
    event_id: str | None = None
    event_kind: str | None = None


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


def _default_event_label(event: TimingEvent) -> str:
    label = event.label.strip()
    return label or event.kind.replace("_", " ").title()


def _events_grouped_by_anchor(
    project: Project,
    shots: list[ShotEvent],
) -> tuple[dict[str, list[TimingEvent]], list[TimingEvent]]:
    shot_index = {shot.id: index for index, shot in enumerate(shots)}
    events_by_shot_id = {shot.id: [] for shot in shots}
    tail_events: list[TimingEvent] = []
    for event in project.analysis.events:
        if event.before_shot_id and event.before_shot_id in shot_index:
            events_by_shot_id[event.before_shot_id].append(event)
            continue
        if event.after_shot_id and event.after_shot_id in shot_index:
            after_index = shot_index[event.after_shot_id]
            next_index = after_index + 1
            if next_index < len(shots):
                events_by_shot_id[shots[next_index].id].append(event)
            else:
                tail_events.append(event)
    return events_by_shot_id, tail_events


def compute_split_rows(project: Project) -> list[SplitRow]:
    shots = sort_shots(project.analysis.shots)
    if not shots:
        return []

    beep_time = project.analysis.beep_time_ms_primary
    anchored_events, tail_events = _events_grouped_by_anchor(project, shots)
    rows: list[SplitRow] = []
    previous_boundary_time = beep_time

    def split_from_boundary(absolute_time_ms: int) -> int | None:
        if previous_boundary_time is None:
            return absolute_time_ms
        return max(0, absolute_time_ms - previous_boundary_time)

    for index, shot in enumerate(shots, start=1):
        split_ms = split_from_boundary(shot.time_ms)
        cumulative_ms = None if beep_time is None else max(0, shot.time_ms - beep_time)
        actions: list[SplitAction] = []
        if index == 1 and beep_time is not None:
            actions.append(
                SplitAction(
                    event_id=None,
                    kind="draw",
                    label="Draw",
                    placement="interval",
                    synthetic=True,
                )
            )
        for event in anchored_events.get(shot.id, []):
            actions.append(
                SplitAction(
                    event_id=event.id,
                    kind=event.kind,
                    label=_default_event_label(event),
                )
            )
        if index == len(shots):
            for event in tail_events:
                actions.append(
                    SplitAction(
                        event_id=event.id,
                        kind=event.kind,
                        label=_default_event_label(event),
                        placement="after",
                    )
                )
        rows.append(
            SplitRow(
                row_id=shot.id,
                row_type="interval",
                label=f"{'Start' if index == 1 else f'Shot {index - 1}'} -> Shot {index}",
                start_label="Start" if index == 1 else f"Shot {index - 1}",
                end_label=f"Shot {index}",
                shot_id=shot.id,
                shot_number=index,
                absolute_time_ms=shot.time_ms,
                cumulative_ms=cumulative_ms,
                split_ms=split_ms,
                score_letter=None if shot.score is None else shot.score.letter.value,
                penalty_counts={} if shot.score is None else dict(shot.score.penalty_counts),
                source=shot.source.value,
                confidence=shot.confidence,
                actions=actions,
            )
        )
        previous_boundary_time = shot.time_ms

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
    shots = sort_shots(project.analysis.shots)
    if len(shots) < 2:
        return None
    reset_ids = split_reset_shot_ids(project)
    splits = [
        max(0, shots[index].time_ms - shots[index - 1].time_ms)
        for index in range(1, len(shots))
        if shots[index].id not in reset_ids
    ]
    if not splits:
        return None
    return int(round(sum(splits) / len(splits)))


def total_time_ms(project: Project) -> int | None:
    shots = sort_shots(project.analysis.shots)
    if not shots:
        return None
    return shots[-1].time_ms
