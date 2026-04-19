from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from splitshot.analysis.detection import ThresholdDetectionResult, analyze_video_audio_thresholds
from splitshot.domain.models import Project
from splitshot.presentation.stage import build_stage_presentation
from splitshot.utils.time import format_time_ms


DEFAULT_THRESHOLD_GRID = (0.25, 0.35, 0.45, 0.55, 0.65)


@dataclass(frozen=True, slots=True)
class ThresholdSummary:
    threshold: float
    shot_count: int
    beep_time_ms: int | None
    draw_ms: int | None
    final_shot_ms: int | None
    average_split_ms: int | None
    median_confidence: float | None
    mean_confidence: float | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview ShotML split detection for a video file and suggest a sensitivity slider setting before loading it into SplitShot.",
    )
    parser.add_argument("video", type=Path, help="Video file to analyze.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Threshold to inspect in detail. Defaults to the recommended threshold from the sweep.",
    )
    parser.add_argument(
        "--threshold-grid",
        default=",".join(f"{value:.2f}" for value in DEFAULT_THRESHOLD_GRID),
        help="Comma-separated thresholds to sweep for slider guidance.",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Console output format.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional file where the structured JSON report will be written.",
    )
    return parser


def parse_threshold_grid(value: str) -> list[float]:
    thresholds: list[float] = []
    for item in value.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        threshold = float(candidate)
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0 and 1: {candidate}")
        thresholds.append(round(threshold, 4))
    if not thresholds:
        raise ValueError("At least one threshold is required.")
    return thresholds


def detection_project(result: ThresholdDetectionResult) -> Project:
    project = Project(name="Shot analysis preview")
    project.analysis.beep_time_ms_primary = result.detection.beep_time_ms
    project.analysis.shots = list(result.detection.shots)
    return project


def summarize_detection(result: ThresholdDetectionResult) -> ThresholdSummary:
    project = detection_project(result)
    presentation = build_stage_presentation(project)
    confidences = [float(shot.confidence) for shot in result.detection.shots if shot.confidence is not None]
    sorted_confidences = sorted(confidences)
    median_confidence = None
    if sorted_confidences:
        midpoint = len(sorted_confidences) // 2
        if len(sorted_confidences) % 2 == 1:
            median_confidence = sorted_confidences[midpoint]
        else:
            median_confidence = (sorted_confidences[midpoint - 1] + sorted_confidences[midpoint]) / 2.0
    mean_confidence = None if not confidences else (sum(confidences) / len(confidences))
    return ThresholdSummary(
        threshold=result.threshold,
        shot_count=len(result.detection.shots),
        beep_time_ms=result.detection.beep_time_ms,
        draw_ms=presentation.metrics.draw_ms,
        final_shot_ms=presentation.metrics.final_shot_ms,
        average_split_ms=presentation.metrics.average_split_ms,
        median_confidence=median_confidence,
        mean_confidence=mean_confidence,
    )


def recommend_threshold(summaries: list[ThresholdSummary]) -> tuple[float, str]:
    if len(summaries) == 1:
        summary = summaries[0]
        return summary.threshold, "Only one threshold was analyzed."

    ordered = sorted(summaries, key=lambda item: item.threshold)
    dominant_shot_count = Counter(summary.shot_count for summary in ordered).most_common(1)[0][0]
    dominant_segments: list[list[ThresholdSummary]] = []
    current_segment: list[ThresholdSummary] = []
    for summary in ordered:
        if summary.shot_count == dominant_shot_count:
            current_segment.append(summary)
            continue
        if current_segment:
            dominant_segments.append(current_segment)
            current_segment = []
    if current_segment:
        dominant_segments.append(current_segment)

    best_segment = max(
        dominant_segments,
        key=lambda segment: (
            len(segment),
            max((item.median_confidence or 0.0) for item in segment),
        ),
    )
    recommended = best_segment[len(best_segment) // 2]
    reason = (
        f"Shot count stays stable at {dominant_shot_count} from {best_segment[0].threshold:.2f} "
        f"to {best_segment[-1].threshold:.2f}."
    )
    return recommended.threshold, reason


def selected_detection(results: list[ThresholdDetectionResult], threshold: float) -> ThresholdDetectionResult:
    by_threshold = {round(result.threshold, 4): result for result in results}
    key = round(threshold, 4)
    if key not in by_threshold:
        raise KeyError(f"Threshold {threshold:.4f} was not included in the sweep.")
    return by_threshold[key]


def detailed_shot_rows(result: ThresholdDetectionResult) -> list[dict[str, object]]:
    presentation = build_stage_presentation(detection_project(result))
    rows: list[dict[str, object]] = []
    for segment in presentation.timing_segments:
        rows.append(
            {
                "shot_number": segment.shot_number,
                "absolute_ms": segment.absolute_ms,
                "absolute_time": format_time_ms(segment.absolute_ms),
                "split_ms": segment.segment_ms,
                "split_time": format_time_ms(segment.segment_ms),
                "sequence_total_ms": segment.sequence_total_ms,
                "sequence_total_time": format_time_ms(segment.sequence_total_ms),
                "confidence": segment.confidence,
                "confidence_percent": None if segment.confidence is None else round(segment.confidence * 100.0, 1),
                "source": segment.source,
            }
        )
    return rows


def render_table(summaries: list[ThresholdSummary], recommendation: float, reason: str, rows: list[dict[str, object]]) -> str:
    lines = [
        f"Recommended threshold: {recommendation:.2f}",
        f"Reason: {reason}",
        "",
        "Threshold Sweep",
        "threshold | shots | beep     | draw     | final    | avg split | median conf | mean conf",
        "----------+-------+----------+----------+----------+-----------+-------------+----------",
    ]
    for summary in sorted(summaries, key=lambda item: item.threshold):
        lines.append(
            " | ".join(
                [
                    f"{summary.threshold:.2f}".rjust(8),
                    str(summary.shot_count).rjust(5),
                    format_time_ms(summary.beep_time_ms).rjust(8),
                    format_time_ms(summary.draw_ms).rjust(8),
                    format_time_ms(summary.final_shot_ms).rjust(8),
                    format_time_ms(summary.average_split_ms).rjust(9),
                    ("--" if summary.median_confidence is None else f"{summary.median_confidence * 100.0:5.1f}%").rjust(11),
                    ("--" if summary.mean_confidence is None else f"{summary.mean_confidence * 100.0:5.1f}%").rjust(8),
                ]
            )
        )

    lines.extend(
        [
            "",
            f"Shot Details At {recommendation:.2f}",
            "shot | absolute   | split      | run total  | confidence | source",
            "-----+------------+------------+------------+------------+--------",
        ]
    )
    for row in rows:
        confidence = row["confidence_percent"]
        lines.append(
            " | ".join(
                [
                    str(row["shot_number"]).rjust(4),
                    str(row["absolute_time"]).rjust(10),
                    str(row["split_time"]).rjust(10),
                    str(row["sequence_total_time"]).rjust(10),
                    ("--" if confidence is None else f"{confidence:5.1f}%").rjust(10),
                    str(row["source"]).rjust(6),
                ]
            )
        )
    return "\n".join(lines)


def render_review_suggestions(suggestions: list[dict[str, object]]) -> list[str]:
    if not suggestions:
        return ["", "Review Suggestions", "none"]
    lines = [
        "",
        "Review Suggestions",
        "shot | time      | kind                | confidence | support | action",
        "-----+-----------+---------------------+------------+---------+--------",
    ]
    for suggestion in suggestions:
        confidence = suggestion.get("confidence")
        support = suggestion.get("support_confidence")
        lines.append(
            " | ".join(
                [
                    str(suggestion.get("shot_number") or "--").rjust(4),
                    format_time_ms(suggestion.get("shot_time_ms")).rjust(9),
                    str(suggestion.get("kind") or "").ljust(19),
                    ("--" if confidence is None else f"{float(confidence) * 100.0:5.1f}%").rjust(10),
                    ("--" if support is None else f"{float(support) * 100.0:5.1f}%").rjust(7),
                    str(suggestion.get("suggested_action") or ""),
                ]
            )
        )
    return lines


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    video_path = args.video.expanduser().resolve()
    if not video_path.is_file():
        raise SystemExit(f"Video file not found: {video_path}")

    thresholds = parse_threshold_grid(args.threshold_grid)
    results = analyze_video_audio_thresholds(video_path, thresholds)
    summaries = [summarize_detection(result) for result in results]
    recommended_threshold, reason = recommend_threshold(summaries)
    selected_threshold = recommended_threshold if args.threshold is None else args.threshold
    detail_result = selected_detection(results, selected_threshold)
    detail_rows = detailed_shot_rows(detail_result)
    review_suggestions = [asdict(suggestion) for suggestion in detail_result.detection.review_suggestions]

    payload = {
        "video": str(video_path),
        "recommended_threshold": recommended_threshold,
        "selected_threshold": selected_threshold,
        "recommendation_reason": reason,
        "sweep": [
            {
                "threshold": summary.threshold,
                "shot_count": summary.shot_count,
                "beep_time_ms": summary.beep_time_ms,
                "draw_ms": summary.draw_ms,
                "final_shot_ms": summary.final_shot_ms,
                "average_split_ms": summary.average_split_ms,
                "median_confidence": summary.median_confidence,
                "mean_confidence": summary.mean_confidence,
            }
            for summary in summaries
        ],
        "shots": detail_rows,
        "review_suggestions": review_suggestions,
    }

    if args.format == "json":
        rendered = json.dumps(payload, indent=2)
    else:
        rendered = render_table(summaries, selected_threshold, reason, detail_rows)
        rendered += "\n" + "\n".join(render_review_suggestions(review_suggestions))
    print(rendered)

    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
