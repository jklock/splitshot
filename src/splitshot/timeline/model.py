from __future__ import annotations

from dataclasses import dataclass, field

from splitshot.domain.models import Project, ShotEvent, TimingEvent


RESETTING_EVENT_KINDS = {"reload", "malfunction"}


@dataclass(slots=True)
class SplitAction:
    event_id: str | None
    kind: str
    label: str
    placement: str = "interval"
    synthetic: bool = False
    resets_sequence: bool = False


@dataclass(slots=True)
class SplitRow:
    row_id: str
    row_type: str
    label: str
    start_label: str
    end_label: str
    interval_kind: str
    interval_label: str
    shot_id: str | None
    shot_number: int | None
    absolute_time_ms: int
    cumulative_ms: int | None
    sequence_total_ms: int | None
    split_ms: int | None
    score_letter: str | None
    penalty_counts: dict[str, float]
    source: str | None
    confidence: float | None
    actions: list[SplitAction] = field(default_factory=list)
    resets_sequence: bool = False
    event_id: str | None = None
    event_kind: str | None = None


def sort_shots(shots: list[ShotEvent]) -> list[ShotEvent]:
    return sorted(shots, key=lambda shot: shot.time_ms)


def timing_event_resets_sequence(kind: str | TimingEvent) -> bool:
    event_kind = kind.kind if isinstance(kind, TimingEvent) else str(kind or "")
    return event_kind.strip().lower() in RESETTING_EVENT_KINDS


def split_reset_shot_ids(project: Project) -> set[str]:
    shots = sort_shots(project.analysis.shots)
    if len(shots) < 2:
        return set()

    shot_index = {shot.id: index for index, shot in enumerate(shots)}
    reset_ids: set[str] = set()
    for event in project.analysis.events:
        if not timing_event_resets_sequence(event):
            continue
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


def _interval_actions(events: list[TimingEvent]) -> list[SplitAction]:
    return [
        SplitAction(
            event_id=event.id,
            kind=event.kind,
            label=_default_event_label(event),
            resets_sequence=timing_event_resets_sequence(event),
        )
        for event in events
    ]


def _interval_summary(
    shot_index: int,
    beep_time: int | None,
    actions: list[SplitAction],
) -> tuple[str, str, bool]:
    if shot_index == 1 and beep_time is not None:
        return "draw", "Draw", True
    if actions:
        return (
            actions[0].kind if len(actions) == 1 else "event",
            " • ".join(action.label for action in actions),
            any(action.resets_sequence for action in actions),
        )
    if shot_index == 1:
        return "start", "Start", True
    return "split", "Split", False


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
    previous_boundary_time = beep_time if beep_time is not None else 0
    sequence_anchor_time = previous_boundary_time

    for index, shot in enumerate(shots, start=1):
        interval_actions = _interval_actions(anchored_events.get(shot.id, []))
        row_actions = list(interval_actions)
        if index == len(shots):
            row_actions.extend(_interval_actions(tail_events))

        interval_kind, interval_label, resets_sequence = _interval_summary(
            index,
            beep_time,
            interval_actions,
        )
        interval_start_time = previous_boundary_time
        sequence_total_ms = max(
            0,
            shot.time_ms - (interval_start_time if resets_sequence else sequence_anchor_time),
        )
        split_ms = max(0, shot.time_ms - previous_boundary_time)
        cumulative_ms = None if beep_time is None else max(0, shot.time_ms - beep_time)
        primary_action = interval_actions[0] if interval_actions else None
        rows.append(
            SplitRow(
                row_id=shot.id,
                row_type="shot",
                label=f"Shot {index}",
                start_label="Start" if index == 1 else f"Shot {index - 1}",
                end_label=f"Shot {index}",
                interval_kind=interval_kind,
                interval_label=interval_label,
                shot_id=shot.id,
                shot_number=index,
                absolute_time_ms=shot.time_ms,
                cumulative_ms=cumulative_ms,
                sequence_total_ms=sequence_total_ms,
                split_ms=split_ms,
                score_letter=None if shot.score is None else shot.score.letter.value,
                penalty_counts={} if shot.score is None else dict(shot.score.penalty_counts),
                source=shot.source.value,
                confidence=shot.confidence,
                actions=row_actions,
                resets_sequence=resets_sequence,
                event_id=primary_action.event_id if primary_action is not None else None,
                event_kind=primary_action.kind if primary_action is not None else None,
            )
        )
        if resets_sequence:
            sequence_anchor_time = interval_start_time
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
