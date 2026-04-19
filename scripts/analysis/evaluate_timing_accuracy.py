from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

from splitshot.analysis.detection import ThresholdDetectionResult, analyze_video_audio_thresholds
from splitshot.analysis.training_dataset import (
    LABEL_SOURCE_AUTO_CONSENSUS,
    LABEL_SOURCE_DETECTOR_DRAFT,
    LABEL_SOURCE_VERIFIED,
    LABEL_STATUS_AUTO_LABELED,
    LABEL_STATUS_VERIFIED,
    load_manifest,
)
DEFAULT_THRESHOLD_GRID = (0.25, 0.35, 0.45, 0.55, 0.65)


@dataclass(frozen=True, slots=True)
class ExpectedTiming:
    beep_time_ms: int | None
    shot_times_ms: list[int]
    label_source: str


@dataclass(frozen=True, slots=True)
class TimingStats:
    count: int
    mean_abs_ms: float | None
    median_abs_ms: float | None
    p95_abs_ms: float | None
    max_abs_ms: int | None
    signed_mean_ms: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "count": self.count,
            "mean_abs_ms": self.mean_abs_ms,
            "median_abs_ms": self.median_abs_ms,
            "p95_abs_ms": self.p95_abs_ms,
            "max_abs_ms": self.max_abs_ms,
            "signed_mean_ms": self.signed_mean_ms,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate ShotML timestamp accuracy against accepted manifest labels. "
            "Verified labels are used first; auto-consensus labels are used when manual labels are absent."
        ),
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=Path(".training/shotml-label-manifest.json"),
        help="Training manifest JSON. Defaults to .training/shotml-label-manifest.json.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Threshold to inspect in detail. Defaults to the best threshold from the timing sweep.",
    )
    parser.add_argument(
        "--threshold-grid",
        default=",".join(f"{value:.2f}" for value in DEFAULT_THRESHOLD_GRID),
        help="Comma-separated thresholds to sweep for timing accuracy.",
    )
    parser.add_argument(
        "--max-match-ms",
        type=int,
        default=180,
        help="Maximum shot timing distance counted as a matched shot for missed/extra reporting.",
    )
    parser.add_argument(
        "--use-detector-drafts",
        action="store_true",
        help="Use detector draft labels only when verified or auto-consensus labels are unavailable.",
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
        rounded = round(threshold, 4)
        if rounded not in thresholds:
            thresholds.append(rounded)
    if not thresholds:
        raise ValueError("At least one threshold is required.")
    return thresholds


def _int_list(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    return [int(item) for item in value]


def expected_timing_for_entry(video: dict[str, object], use_detector_drafts: bool) -> ExpectedTiming | str:
    labels = video.get("labels", {})
    if not isinstance(labels, dict):
        labels = {}
    status = str(labels.get("status", "needs_review"))

    if status == LABEL_STATUS_VERIFIED:
        beep = labels.get("verified_beep_time_ms")
        shots = _int_list(labels.get("verified_shot_times_ms", []))
        if beep is not None or shots:
            return ExpectedTiming(
                beep_time_ms=None if beep is None else int(beep),
                shot_times_ms=shots,
                label_source=LABEL_SOURCE_VERIFIED,
            )
        return "verified_without_events"

    if status == LABEL_STATUS_AUTO_LABELED:
        beep = labels.get("auto_beep_time_ms")
        shots = _int_list(labels.get("auto_shot_times_ms", []))
        if beep is not None or shots:
            return ExpectedTiming(
                beep_time_ms=None if beep is None else int(beep),
                shot_times_ms=shots,
                label_source=LABEL_SOURCE_AUTO_CONSENSUS,
            )
        return "auto_labeled_without_events"

    if use_detector_drafts:
        beep = video.get("detector_beep_time_ms")
        shots = _int_list(video.get("detector_shot_times_ms", []))
        if beep is not None or shots:
            return ExpectedTiming(
                beep_time_ms=None if beep is None else int(beep),
                shot_times_ms=shots,
                label_source=LABEL_SOURCE_DETECTOR_DRAFT,
            )
        return "detector_draft_without_events"

    return "status_not_accepted"


def resolve_video_path(video: dict[str, object], manifest_path: Path, manifest: dict[str, object]) -> Path | None:
    path_value = video.get("path")
    if isinstance(path_value, str) and path_value:
        candidate = Path(path_value).expanduser()
        if candidate.is_file():
            return candidate.resolve()
        if not candidate.is_absolute():
            relative_candidate = (manifest_path.parent / candidate).resolve()
            if relative_candidate.is_file():
                return relative_candidate

    relative_path = video.get("relative_path")
    roots = [manifest.get("input"), manifest_path.parent]
    for root in roots:
        if not isinstance(relative_path, str) or not relative_path:
            continue
        root_path = Path(str(root)).expanduser() if root is not None else manifest_path.parent
        candidate = (root_path / relative_path).resolve()
        if candidate.is_file():
            return candidate
    return None


def _percentile_abs(errors: list[int], percentile: float) -> float | None:
    if not errors:
        return None
    ordered = sorted(abs(value) for value in errors)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return float(ordered[lower] + ((ordered[upper] - ordered[lower]) * fraction))


def summarize_errors(errors: list[int]) -> TimingStats:
    if not errors:
        return TimingStats(
            count=0,
            mean_abs_ms=None,
            median_abs_ms=None,
            p95_abs_ms=None,
            max_abs_ms=None,
            signed_mean_ms=None,
        )
    absolute = [abs(value) for value in errors]
    return TimingStats(
        count=len(errors),
        mean_abs_ms=round(float(mean(absolute)), 3),
        median_abs_ms=round(float(median(absolute)), 3),
        p95_abs_ms=None if not errors else round(float(_percentile_abs(errors, 0.95)), 3),
        max_abs_ms=max(absolute),
        signed_mean_ms=round(float(mean(errors)), 3),
    )


def _split_times(beep_time_ms: int | None, shots: list[int]) -> list[int]:
    if beep_time_ms is None or not shots:
        return []
    splits = [shots[0] - beep_time_ms]
    for previous, current in zip(shots, shots[1:], strict=False):
        splits.append(current - previous)
    return splits


def _matched_shots(expected_shots: list[int], detected_shots: list[int], max_match_ms: int) -> list[dict[str, int]]:
    matches: list[dict[str, int]] = []
    next_detected_index = 0
    for expected_index, expected_ms in enumerate(expected_shots):
        best_index: int | None = None
        best_error: int | None = None
        for detected_index in range(next_detected_index, len(detected_shots)):
            detected_ms = detected_shots[detected_index]
            error = detected_ms - expected_ms
            if abs(error) > max_match_ms:
                if detected_ms > expected_ms + max_match_ms:
                    break
                continue
            if best_error is None or abs(error) < abs(best_error):
                best_index = detected_index
                best_error = error
        if best_index is None or best_error is None:
            continue
        matches.append(
            {
                "expected_index": expected_index,
                "detected_index": best_index,
                "expected_ms": expected_ms,
                "detected_ms": detected_shots[best_index],
                "error_ms": best_error,
            }
        )
        next_detected_index = best_index + 1
    return matches


def evaluate_detection(
    video: dict[str, object],
    expected: ExpectedTiming,
    result: ThresholdDetectionResult,
    max_match_ms: int,
) -> dict[str, object]:
    detected_beep = result.detection.beep_time_ms
    expected_shots = list(expected.shot_times_ms)
    detected_shots = [int(shot.time_ms) for shot in result.detection.shots]
    matches = _matched_shots(expected_shots, detected_shots, max_match_ms)
    expected_splits = _split_times(expected.beep_time_ms, expected_shots)
    detected_splits = _split_times(detected_beep, detected_shots)
    split_errors = [
        detected_split - expected_split
        for expected_split, detected_split in zip(expected_splits, detected_splits, strict=False)
    ]

    expected_stage_time = None
    detected_stage_time = None
    if expected.beep_time_ms is not None and expected_shots:
        expected_stage_time = expected_shots[-1] - expected.beep_time_ms
    if detected_beep is not None and detected_shots:
        detected_stage_time = detected_shots[-1] - detected_beep

    beep_error = None
    if expected.beep_time_ms is not None and detected_beep is not None:
        beep_error = detected_beep - expected.beep_time_ms

    last_shot_error = None
    if expected_shots and detected_shots:
        last_shot_error = detected_shots[-1] - expected_shots[-1]

    stage_time_error = None
    if expected_stage_time is not None and detected_stage_time is not None:
        stage_time_error = detected_stage_time - expected_stage_time

    matched_detected = {int(match["detected_index"]) for match in matches}
    return {
        "relative_path": str(video.get("relative_path") or Path(str(video.get("path", ""))).name),
        "label_source": expected.label_source,
        "threshold": result.threshold,
        "expected_beep_time_ms": expected.beep_time_ms,
        "detected_beep_time_ms": detected_beep,
        "beep_error_ms": beep_error,
        "expected_shot_times_ms": expected_shots,
        "detected_shot_times_ms": detected_shots,
        "matched_shots": matches,
        "matched_shot_errors_ms": [int(match["error_ms"]) for match in matches],
        "missed_shot_count": len(expected_shots) - len(matches),
        "extra_shot_count": len(detected_shots) - len(matched_detected),
        "expected_split_times_ms": expected_splits,
        "detected_split_times_ms": detected_splits,
        "split_errors_ms": split_errors,
        "first_split_error_ms": None if not split_errors else split_errors[0],
        "last_shot_error_ms": last_shot_error,
        "expected_stage_time_ms": expected_stage_time,
        "detected_stage_time_ms": detected_stage_time,
        "stage_time_error_ms": stage_time_error,
    }


def summarize_video_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    beep_errors = [int(row["beep_error_ms"]) for row in rows if row["beep_error_ms"] is not None]
    shot_errors = [
        int(error)
        for row in rows
        for error in row.get("matched_shot_errors_ms", [])
        if error is not None
    ]
    split_errors = [
        int(error)
        for row in rows
        for error in row.get("split_errors_ms", [])
        if error is not None
    ]
    first_split_errors = [
        int(row["first_split_error_ms"]) for row in rows if row["first_split_error_ms"] is not None
    ]
    last_shot_errors = [int(row["last_shot_error_ms"]) for row in rows if row["last_shot_error_ms"] is not None]
    stage_time_errors = [int(row["stage_time_error_ms"]) for row in rows if row["stage_time_error_ms"] is not None]
    label_sources = Counter(str(row["label_source"]) for row in rows)
    return {
        "evaluated_video_count": len(rows),
        "label_source_counts": dict(label_sources),
        "missed_shot_count": sum(int(row["missed_shot_count"]) for row in rows),
        "extra_shot_count": sum(int(row["extra_shot_count"]) for row in rows),
        "beep_error": summarize_errors(beep_errors).to_dict(),
        "shot_error": summarize_errors(shot_errors).to_dict(),
        "split_error": summarize_errors(split_errors).to_dict(),
        "first_split_error": summarize_errors(first_split_errors).to_dict(),
        "last_shot_error": summarize_errors(last_shot_errors).to_dict(),
        "stage_time_error": summarize_errors(stage_time_errors).to_dict(),
    }


def _summary_score(summary: dict[str, object], threshold: float) -> tuple[float, ...]:
    def metric(name: str, field: str = "mean_abs_ms") -> float:
        value = summary.get(name, {})
        if not isinstance(value, dict):
            return 1_000_000.0
        item = value.get(field)
        return 1_000_000.0 if item is None else float(item)

    return (
        float(summary.get("missed_shot_count", 0)) + float(summary.get("extra_shot_count", 0)),
        metric("stage_time_error"),
        metric("last_shot_error"),
        metric("first_split_error"),
        metric("beep_error"),
        metric("shot_error"),
        abs(float(threshold) - 0.35),
    )


def recommend_threshold(threshold_summaries: list[dict[str, object]]) -> tuple[float, str]:
    if not threshold_summaries:
        raise ValueError("No threshold summaries are available.")
    best = min(
        threshold_summaries,
        key=lambda item: _summary_score(item["summary"], float(item["threshold"])),  # type: ignore[index]
    )
    threshold = float(best["threshold"])
    summary = best["summary"]
    missed = int(summary.get("missed_shot_count", 0)) if isinstance(summary, dict) else 0
    extra = int(summary.get("extra_shot_count", 0)) if isinstance(summary, dict) else 0
    stage = None
    if isinstance(summary, dict) and isinstance(summary.get("stage_time_error"), dict):
        stage = summary["stage_time_error"].get("mean_abs_ms")  # type: ignore[index, union-attr]
    reason = f"Lowest timing score with {missed} missed shots, {extra} extra shots"
    if stage is not None:
        reason += f", and {float(stage):.1f} ms mean absolute stage-time error."
    else:
        reason += "."
    return threshold, reason


def _metric_line(name: str, stats: dict[str, object]) -> str:
    def value(key: str) -> str:
        item = stats.get(key)
        if item is None:
            return "--".rjust(9)
        if isinstance(item, float):
            return f"{item:.1f}".rjust(9)
        return str(item).rjust(9)

    return " | ".join(
        [
            name.ljust(17),
            str(stats.get("count", 0)).rjust(5),
            value("mean_abs_ms"),
            value("median_abs_ms"),
            value("p95_abs_ms"),
            value("max_abs_ms"),
            value("signed_mean_ms"),
        ]
    )


def _format_signed_ms(value: object) -> str:
    if value is None:
        return "--:--.---"
    value_ms = int(value)
    sign = "-" if value_ms < 0 else ""
    absolute_ms = abs(value_ms)
    minutes = absolute_ms // 60_000
    seconds = (absolute_ms % 60_000) / 1000.0
    return f"{sign}{minutes:02d}:{seconds:06.3f}"


def render_table(payload: dict[str, object]) -> str:
    selected_summary = payload["selected_summary"]
    assert isinstance(selected_summary, dict)
    lines = [
        "Timing Accuracy",
        f"Selected threshold: {float(payload['selected_threshold']):.2f}",
        f"Recommended threshold: {float(payload['recommended_threshold']):.2f}",
        f"Reason: {payload['recommendation_reason']}",
        (
            f"Videos: {selected_summary['evaluated_video_count']} evaluated, "
            f"{payload['skipped_video_count']} skipped"
        ),
        "Label sources: "
        + ", ".join(
            f"{source}={count}"
            for source, count in sorted(dict(selected_summary.get("label_source_counts", {})).items())
        ),
        "",
        "Metric            | count |  mean ms | median ms |   p95 ms |   max ms | signed ms",
        "------------------+-------+----------+-----------+----------+----------+----------",
    ]
    for key, label in (
        ("beep_error", "beep"),
        ("first_split_error", "first split"),
        ("split_error", "all splits"),
        ("last_shot_error", "last shot"),
        ("stage_time_error", "stage time"),
        ("shot_error", "matched shots"),
    ):
        stats = selected_summary.get(key, {})
        if isinstance(stats, dict):
            lines.append(_metric_line(label, stats))

    lines.extend(
        [
            "",
            (
                f"Missed shots: {selected_summary['missed_shot_count']} | "
                f"Extra shots: {selected_summary['extra_shot_count']}"
            ),
            "",
            "Threshold Sweep",
            "threshold | missed | extra | stage mean | beep mean | last mean",
            "----------+--------+-------+------------+-----------+----------",
        ]
    )
    for threshold_summary in payload["threshold_summaries"]:
        assert isinstance(threshold_summary, dict)
        summary = threshold_summary["summary"]
        assert isinstance(summary, dict)

        def mean_abs(name: str) -> str:
            stats = summary.get(name, {})
            if not isinstance(stats, dict) or stats.get("mean_abs_ms") is None:
                return "--".rjust(10)
            return f"{float(stats['mean_abs_ms']):.1f}".rjust(10)

        lines.append(
            " | ".join(
                [
                    f"{float(threshold_summary['threshold']):.2f}".rjust(8),
                    str(summary["missed_shot_count"]).rjust(6),
                    str(summary["extra_shot_count"]).rjust(5),
                    mean_abs("stage_time_error"),
                    mean_abs("beep_error"),
                    mean_abs("last_shot_error"),
                ]
            )
        )

    videos = payload.get("videos", [])
    assert isinstance(videos, list)
    worst = sorted(
        videos,
        key=lambda row: (
            abs(int(row.get("stage_time_error_ms") or 0)),
            int(row.get("missed_shot_count") or 0) + int(row.get("extra_shot_count") or 0),
            abs(int(row.get("beep_error_ms") or 0)),
        ),
        reverse=True,
    )[:8]
    lines.extend(
        [
            "",
            "Worst Videos At Selected Threshold",
            "video | beep err | last err | stage err | missed | extra",
            "------+----------+----------+-----------+--------+------",
        ]
    )
    for row in worst:
        assert isinstance(row, dict)
        lines.append(
            " | ".join(
                [
                    str(row["relative_path"]),
                    _format_signed_ms(row.get("beep_error_ms")).rjust(8),
                    _format_signed_ms(row.get("last_shot_error_ms")).rjust(8),
                    _format_signed_ms(row.get("stage_time_error_ms")).rjust(9),
                    str(row["missed_shot_count"]).rjust(6),
                    str(row["extra_shot_count"]).rjust(5),
                ]
            )
        )
    return "\n".join(lines)


def evaluate_manifest(
    manifest_path: Path,
    thresholds: list[float],
    max_match_ms: int,
    use_detector_drafts: bool,
) -> dict[str, object]:
    manifest = load_manifest(manifest_path)
    videos = manifest.get("videos", [])
    if not isinstance(videos, list):
        raise ValueError(f"Manifest videos must be a list: {manifest_path}")

    rows_by_threshold: dict[float, list[dict[str, object]]] = {threshold: [] for threshold in thresholds}
    skipped: Counter[str] = Counter()
    skipped_videos: list[dict[str, object]] = []

    for video in videos:
        if not isinstance(video, dict):
            skipped["invalid_video_entry"] += 1
            continue
        expected = expected_timing_for_entry(video, use_detector_drafts)
        if isinstance(expected, str):
            skipped[expected] += 1
            skipped_videos.append(
                {
                    "relative_path": str(video.get("relative_path") or Path(str(video.get("path", ""))).name),
                    "reason": expected,
                }
            )
            continue

        video_path = resolve_video_path(video, manifest_path, manifest)
        if video_path is None:
            skipped["video_not_found"] += 1
            skipped_videos.append(
                {
                    "relative_path": str(video.get("relative_path") or Path(str(video.get("path", ""))).name),
                    "reason": "video_not_found",
                }
            )
            continue

        results = analyze_video_audio_thresholds(video_path, thresholds)
        for result in results:
            rows_by_threshold[float(result.threshold)].append(
                evaluate_detection(video, expected, result, max_match_ms)
            )

    threshold_summaries = [
        {
            "threshold": threshold,
            "summary": summarize_video_rows(rows_by_threshold[threshold]),
        }
        for threshold in thresholds
    ]
    recommended_threshold, reason = recommend_threshold(threshold_summaries)
    return {
        "manifest_path": str(manifest_path),
        "video_count": len(videos),
        "skipped_video_count": sum(skipped.values()),
        "skipped_video_reasons": dict(skipped),
        "skipped_videos": skipped_videos,
        "threshold_summaries": threshold_summaries,
        "recommended_threshold": recommended_threshold,
        "recommendation_reason": reason,
        "rows_by_threshold": rows_by_threshold,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    manifest_path = args.manifest.expanduser().resolve()
    if not manifest_path.is_file():
        raise SystemExit(f"Manifest file not found: {manifest_path}")

    thresholds = parse_threshold_grid(args.threshold_grid)
    selected_threshold = round(float(args.threshold), 4) if args.threshold is not None else None
    if selected_threshold is not None and selected_threshold not in thresholds:
        thresholds.append(selected_threshold)
        thresholds.sort()

    evaluation = evaluate_manifest(
        manifest_path,
        thresholds=thresholds,
        max_match_ms=max(0, int(args.max_match_ms)),
        use_detector_drafts=bool(args.use_detector_drafts),
    )
    recommended_threshold = float(evaluation["recommended_threshold"])
    if selected_threshold is None:
        selected_threshold = recommended_threshold

    rows_by_threshold = evaluation.pop("rows_by_threshold")
    assert isinstance(rows_by_threshold, dict)
    selected_rows = rows_by_threshold[selected_threshold]
    payload = {
        **evaluation,
        "selected_threshold": selected_threshold,
        "selected_summary": summarize_video_rows(selected_rows),
        "videos": selected_rows,
        "notes": [
            "Verified labels are manual labels when present.",
            "Auto-consensus labels are accepted training labels, not independent manual actuals.",
            "Stage time is measured from beep to the last detected shot.",
        ],
    }

    rendered = json.dumps(payload, indent=2) if args.format == "json" else render_table(payload)
    print(rendered)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
