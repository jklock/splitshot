from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from splitshot.analysis.corpus import DEFAULT_THRESHOLD_GRID, audit_corpus, list_corpus_videos


def format_beep_compare(beep_multipass: dict[str, object]) -> str:
    gaps = [
        value
        for value in (
            beep_multipass["tone_model_gap_ms"],
            beep_multipass["final_tone_gap_ms"],
            beep_multipass["final_model_gap_ms"],
        )
        if value is not None
    ]
    if not gaps:
        return "--"
    worst_gap_ms = max(int(value) for value in gaps)
    if bool(beep_multipass["review_required"]):
        return f"review {worst_gap_ms}ms"
    return f"ok {worst_gap_ms}ms"


def format_shot_compare(shot_multipass: dict[str, object]) -> str:
    unmatched_total = int(shot_multipass["unmatched_final_count"]) + int(shot_multipass["unmatched_onset_count"])
    echo_like = int(shot_multipass.get("echo_like_onset_count", 0))
    if unmatched_total == 0 and shot_multipass["max_match_gap_ms"] is None:
        return "--"
    if bool(shot_multipass["review_required"]):
        return f"review {unmatched_total}"
    if echo_like > 0:
        return f"echo {echo_like}"
    return f"ok {unmatched_total}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit a local training corpus with the current ShotML detector and surface threshold stability, beep families, and recording-quality flags.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".training",
        help="Video file or directory to audit. Defaults to .training in the repo root.",
    )
    parser.add_argument(
        "--threshold-grid",
        default=",".join(f"{value:.2f}" for value in DEFAULT_THRESHOLD_GRID),
        help="Comma-separated thresholds to sweep for every video.",
    )
    parser.add_argument(
        "--reference-threshold",
        type=float,
        default=0.35,
        help="Threshold used for detailed per-video fingerprinting and confidence summaries.",
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


def render_table(input_path: Path, threshold_grid: list[float], reference_threshold: float, payloads: list[dict[str, object]]) -> str:
    lines = [
        f"Training Corpus Audit: {input_path}",
        f"Videos: {len(payloads)}",
        f"Threshold grid: {', '.join(f'{value:.2f}' for value in threshold_grid)}",
        f"Reference threshold: {reference_threshold:.2f}",
        "",
        "video | shots | shot span | beep span | beep cmp | shot cmp | family | median conf | shot hf | flags",
        "------+-------+-----------+-----------+----------+----------+--------+-------------+---------+------",
    ]
    for payload in payloads:
        consistency = payload["consistency"]
        fingerprint = payload["fingerprint"]
        beep_multipass = payload["beep_multipass"]
        shot_multipass = payload["shot_multipass"]
        median_conf = payload["shot_median_confidence"]
        flags = payload["review_flags"]
        beep_span = consistency["beep_time_span_ms"]
        shot_hf_ratio = fingerprint["shot_high_frequency_ratio"]
        beep_compare = format_beep_compare(beep_multipass)
        shot_compare = format_shot_compare(shot_multipass)
        lines.append(
            " | ".join(
                [
                    Path(str(payload["path"])).name,
                    str(payload["reference_shot_count"]).rjust(5),
                    str(consistency["shot_count_span"]).rjust(9),
                    ("--" if beep_span is None else f"{beep_span}ms").rjust(9),
                    beep_compare.rjust(8),
                    shot_compare.rjust(8),
                    str(fingerprint["beep_family"]).rjust(6),
                    ("--" if median_conf is None else f"{float(median_conf) * 100.0:5.1f}%").rjust(11),
                    ("--" if shot_hf_ratio is None else f"{float(shot_hf_ratio):0.3f}").rjust(7),
                    ",".join(flags) if flags else "--",
                ]
            )
        )
    duplicate_groups = payloads[0].get("__duplicate_groups__") if payloads else None
    if isinstance(duplicate_groups, list) and duplicate_groups:
        lines.extend(
            [
                "",
                "Duplicate Stage Groups",
                "group | members | shot span | families | status",
                "------+---------+-----------+----------+-------",
            ]
        )
        for group in duplicate_groups:
            lines.append(
                " | ".join(
                    [
                        str(group["group_key"]),
                        str(len(group["members"])).rjust(7),
                        str(group["shot_count_span"]).rjust(9),
                        ",".join(group["beep_families"]),
                        "review" if bool(group["review_required"]) else "ok",
                    ]
                )
            )
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Corpus path not found: {input_path}")
    threshold_grid = parse_threshold_grid(args.threshold_grid)
    if not 0.0 <= args.reference_threshold <= 1.0:
        raise SystemExit("Reference threshold must be between 0 and 1.")

    if not list_corpus_videos(input_path):
        raise SystemExit(f"No supported video files found in {input_path}")

    summaries = audit_corpus(
        input_path,
        thresholds=threshold_grid,
        reference_threshold=args.reference_threshold,
    )
    payload = {
        "input": str(input_path),
        "video_count": len(summaries),
        "threshold_grid": threshold_grid,
        "reference_threshold": args.reference_threshold,
        "duplicate_groups": [],
        "videos": [summary.to_dict() for summary in summaries],
    }
    duplicate_groups = payload["duplicate_groups"]
    if summaries:
        from splitshot.analysis.corpus import analyze_corpus, build_duplicate_group_summaries

        analyses = analyze_corpus(
            input_path,
            thresholds=threshold_grid,
            reference_threshold=args.reference_threshold,
        )
        duplicate_groups = [asdict(group) for group in build_duplicate_group_summaries(analyses)]
        payload["duplicate_groups"] = duplicate_groups

    if args.format == "json":
        rendered = json.dumps(payload, indent=2)
    else:
        table_payloads = [dict(video) for video in payload["videos"]]
        if table_payloads:
            table_payloads[0]["__duplicate_groups__"] = duplicate_groups
        rendered = render_table(input_path, threshold_grid, args.reference_threshold, table_payloads)
    print(rendered)

    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())