from __future__ import annotations

from dataclasses import dataclass

from splitshot.domain.models import Project
from splitshot.scoring.logic import calculate_scoring_summary
from splitshot.timeline.model import average_split_ms, compute_split_rows, draw_time_ms, raw_time_ms, sort_shots


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
    scoring_summary: dict[str, object]


@dataclass(slots=True)
class TimingSegment:
    shot_id: str
    shot_number: int
    label: str
    interval_kind: str
    interval_label: str
    segment_ms: int | None
    segment_s: str
    cumulative_ms: int | None
    cumulative_s: str
    sequence_total_ms: int | None
    sequence_total_s: str
    absolute_ms: int
    absolute_s: str
    confidence: float | None
    source: str
    score_letter: str | None
    penalty_counts: dict[str, float]
    resets_sequence: bool
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
    split_rows = compute_split_rows(project)
    beep_ms = project.analysis.beep_time_ms_primary
    raw_ms = raw_time_ms(project)
    scoring_summary = calculate_scoring_summary(project)
    metrics = StageMetrics(
        draw_ms=draw_time_ms(project),
        raw_time_ms=raw_ms,
        stage_time_ms=raw_ms,
        total_shots=len(shots),
        average_split_ms=average_split_ms(project),
        beep_ms=beep_ms,
        final_shot_ms=None if not shots else shots[-1].time_ms,
        scoring_summary=scoring_summary,
    )

    segments: list[TimingSegment] = []
    for row in split_rows:
        label = row.label or f"Shot {row.shot_number}"
        segment_ms = row.split_ms
        cumulative_ms = row.cumulative_ms
        sequence_total_ms = row.sequence_total_ms
        confidence = row.confidence
        score_letter = row.score_letter
        penalty_counts = dict(row.penalty_counts)
        source_value = str(row.source or "")
        if source_value == "manual":
            subtitle = "Manual"
            source_label = "Manual"
        elif confidence is None:
            subtitle = "ShotML"
            source_label = "ShotML"
        else:
            subtitle = f"{confidence:.2f}"
            source_label = "ShotML"

        meta_parts = []
        if segment_ms is not None:
            meta_parts.append(f"{row.interval_label or 'Split'} {format_seconds_short(segment_ms)}s")
        if sequence_total_ms is not None:
            meta_parts.append(f"Run {format_seconds_short(sequence_total_ms)}s")
        if cumulative_ms is not None:
            meta_parts.append(f"Stage {format_seconds_short(cumulative_ms)}s")
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
                shot_id=row.shot_id or "",
                shot_number=row.shot_number or 0,
                label=label,
                interval_kind=row.interval_kind,
                interval_label=row.interval_label,
                segment_ms=segment_ms,
                segment_s=format_seconds_precise(segment_ms),
                cumulative_ms=cumulative_ms,
                cumulative_s=format_seconds_precise(cumulative_ms),
                sequence_total_ms=sequence_total_ms,
                sequence_total_s=format_seconds_precise(sequence_total_ms),
                absolute_ms=row.absolute_time_ms,
                absolute_s=format_seconds_precise(row.absolute_time_ms),
                confidence=confidence,
                source=source_value,
                score_letter=score_letter,
                penalty_counts=penalty_counts,
                resets_sequence=row.resets_sequence,
                card_title=label,
                card_value=format_seconds_short(segment_ms),
                card_subtitle=subtitle,
                card_meta=" | ".join(meta_parts),
            )
        )

    return StagePresentation(metrics=metrics, timing_segments=segments)
