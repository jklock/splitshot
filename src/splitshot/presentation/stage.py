from __future__ import annotations

from dataclasses import dataclass

from splitshot.domain.models import Project, ShotSource
from splitshot.timeline.model import average_split_ms, draw_time_ms, raw_time_ms, sort_shots
from splitshot.utils.time import format_time_ms


def format_seconds_short(time_ms: int | None) -> str:
    if time_ms is None:
        return "--.--"
    return f"{time_ms / 1000:.2f}"


def format_seconds_precise(time_ms: int | None) -> str:
    if time_ms is None:
        return ""
    return f"{time_ms / 1000:.3f}"


@dataclass(slots=True)
class StageMetrics:
    draw_ms: int | None
    raw_time_ms: int | None
    stage_time_ms: int | None
    total_shots: int
    average_split_ms: int | None
    beep_ms: int | None
    final_shot_ms: int | None


@dataclass(slots=True)
class TimingSegment:
    shot_id: str
    shot_number: int
    label: str
    segment_ms: int | None
    segment_s: str
    cumulative_ms: int | None
    cumulative_s: str
    absolute_ms: int
    absolute_s: str
    confidence: float | None
    source: str
    score_letter: str | None
    penalty_counts: dict[str, float]
    card_title: str
    card_value: str
    card_subtitle: str
    card_meta: str


@dataclass(slots=True)
class StagePresentation:
    metrics: StageMetrics
    timing_segments: list[TimingSegment]


def build_stage_presentation(project: Project) -> StagePresentation:
    shots = sort_shots(project.analysis.shots)
    beep_ms = project.analysis.beep_time_ms_primary
    raw_ms = raw_time_ms(project)
    metrics = StageMetrics(
        draw_ms=draw_time_ms(project),
        raw_time_ms=raw_ms,
        stage_time_ms=raw_ms,
        total_shots=len(shots),
        average_split_ms=average_split_ms(project),
        beep_ms=beep_ms,
        final_shot_ms=None if not shots else shots[-1].time_ms,
    )

    segments: list[TimingSegment] = []
    previous_time_ms: int | None = beep_ms
    for index, shot in enumerate(shots, start=1):
        if index == 1:
            label = "Draw"
            segment_ms = None if beep_ms is None else shot.time_ms - beep_ms
        else:
            label = f"Shot {index}"
            segment_ms = None if previous_time_ms is None else shot.time_ms - previous_time_ms

        cumulative_ms = None if beep_ms is None else shot.time_ms - beep_ms
        confidence = shot.confidence
        score_letter = None if shot.score is None else shot.score.letter.value
        penalty_counts = {} if shot.score is None else dict(shot.score.penalty_counts)
        if shot.source == ShotSource.MANUAL:
            subtitle = "Manual"
            source_label = "Manual"
        elif confidence is None:
            subtitle = "ShotML"
            source_label = "ShotML"
        else:
            subtitle = f"{confidence:.2f}"
            source_label = "ShotML"

        meta_parts = []
        if cumulative_ms is not None:
            meta_parts.append(f"Split {format_seconds_short(cumulative_ms)}s")
        meta_parts.append(source_label)
        if score_letter is not None:
            meta_parts.append(f"Score {score_letter}")
        if penalty_counts:
            meta_parts.append(
                ", ".join(
                    f"{key.replace('_', ' ')} x{int(value) if float(value).is_integer() else value}"
                    for key, value in penalty_counts.items()
                )
            )

        segments.append(
            TimingSegment(
                shot_id=shot.id,
                shot_number=index,
                label=label,
                segment_ms=segment_ms,
                segment_s=format_seconds_precise(segment_ms),
                cumulative_ms=cumulative_ms,
                cumulative_s=format_seconds_precise(cumulative_ms),
                absolute_ms=shot.time_ms,
                absolute_s=format_seconds_precise(shot.time_ms),
                confidence=confidence,
                source=shot.source.value,
                score_letter=score_letter,
                penalty_counts=penalty_counts,
                card_title=label,
                card_value=format_seconds_short(segment_ms),
                card_subtitle=subtitle,
                card_meta=" | ".join(meta_parts),
            )
        )
        previous_time_ms = shot.time_ms

    return StagePresentation(metrics=metrics, timing_segments=segments)
