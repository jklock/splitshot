from __future__ import annotations

import argparse
import json
from pathlib import Path

from splitshot.analysis.review_queue import build_review_queue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rank manifest entries by how quickly they can turn into trustworthy verified labels.",
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        default=".training/shotml-label-manifest.json",
        help="Path to the training manifest JSON. Defaults to .training/shotml-label-manifest.json.",
    )
    parser.add_argument(
        "--include-status",
        dest="include_statuses",
        action="append",
        default=None,
        help="Manifest label status to include in the queue. Repeat as needed. Defaults to needs_review.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=12,
        help="Maximum number of rows to render in table mode.",
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
        help="Optional file where the structured JSON queue will be written.",
    )
    return parser


def _render_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "--"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def _format_beep_gap(beep_gap_ms: int | None) -> str:
    if beep_gap_ms is None:
        return "--"
    return f"{beep_gap_ms}ms"


def _format_duplicate(entry: dict[str, object]) -> str:
    group_key = entry["duplicate_group_key"]
    if group_key is None:
        return "--"
    if entry["duplicate_representative"]:
        return f"{group_key}:rep"
    return str(group_key)


def render_table(payload: dict[str, object], limit: int) -> str:
    entries = payload["entries"][: max(0, limit)]
    lines = [
        f"Training Review Queue: {payload['manifest_path']}",
        f"Queued videos: {payload['queued_video_count']} / {payload['video_count']}",
        f"Included statuses: {', '.join(payload['included_statuses']) if payload['included_statuses'] else '--'}",
        f"Status counts: {_render_counts(payload['status_counts'])}",
        f"Actions: {_render_counts(payload['action_counts'])}",
        f"Families: {_render_counts(payload['beep_family_counts'])}",
        "",
        "rank | video | score | action | family | shots | beep gap | duplicate | flags",
        "-----+-------+-------+--------+--------+-------+----------+-----------+------",
    ]
    for entry in entries:
        flags = ",".join(entry["review_flags"]) if entry["review_flags"] else "--"
        lines.append(
            " | ".join(
                [
                    str(entry["rank"]).rjust(4),
                    str(Path(str(entry["relative_path"])).name),
                    f"{float(entry['priority_score']):6.2f}",
                    str(entry["recommended_action"]),
                    str(entry["beep_family"]),
                    str(entry["detector_shot_count"]).rjust(5),
                    _format_beep_gap(entry["beep_gap_ms"]),
                    _format_duplicate(entry),
                    flags,
                ]
            )
        )
    if payload["queued_video_count"] > len(entries):
        lines.extend(
            [
                "",
                f"Showing {len(entries)} of {payload['queued_video_count']} queued videos. Increase --limit or use --format json for the full queue.",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    include_statuses = tuple(args.include_statuses or ["needs_review"])
    summary = build_review_queue(args.manifest, include_statuses=include_statuses)
    payload = summary.to_dict()

    if args.json_output is not None:
        output_path = args.json_output.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(render_table(payload, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())