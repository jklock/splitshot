from __future__ import annotations

import argparse
import json
from pathlib import Path

from splitshot.analysis.auto_labeling import apply_auto_labels, load_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auto-promote stable manifest entries into an automated consensus label tier.",
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        default=".training/shotml-label-manifest.json",
        help="Path to the training manifest JSON. Defaults to .training/shotml-label-manifest.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output manifest path. Defaults to updating the input manifest in place.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=None,
        help="Optional JSON summary output path.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.65,
        help="Minimum automation confidence score required to promote an entry.",
    )
    parser.add_argument(
        "--beep-consensus-tolerance-ms",
        type=int,
        default=180,
        help="Maximum gap between two beep candidates for pair-consensus promotion.",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Console output format.",
    )
    return parser


def _render_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "--"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def render_table(summary: dict[str, object], output_path: Path, limit: int = 12) -> str:
    entries = summary["entries"][: max(0, limit)]
    lines = [
        f"Auto-Labeled Training Manifest: {output_path}",
        f"Videos: {summary['video_count']}",
        f"Preserved verified: {summary['preserved_verified_count']}",
        f"Auto-labeled: {summary['auto_labeled_count']}",
        f"Demoted to needs_review: {summary['demoted_to_needs_review_count']}",
        f"Statuses: {_render_counts(summary['status_counts'])}",
        f"Skipped reasons: {_render_counts(summary['skipped_reason_counts'])}",
        "",
        "video | previous | current | score | method | skip",
        "------+----------+---------+-------+--------+-----",
    ]
    for entry in entries:
        score = "--" if entry["auto_label_score"] is None else f"{float(entry['auto_label_score']):0.3f}"
        skip_reason = entry["skip_reason"] or "--"
        method = entry["auto_label_method"] or "--"
        lines.append(
            " | ".join(
                [
                    str(entry["relative_path"]),
                    str(entry["previous_status"]),
                    str(entry["new_status"]),
                    score,
                    method,
                    skip_reason,
                ]
            )
        )
    if summary["video_count"] > len(entries):
        lines.extend(["", f"Showing {len(entries)} of {summary['video_count']} manifest entries."])
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    payload = load_manifest(manifest_path)
    summary_payload = dict(payload)
    summary_payload["manifest_path"] = str(manifest_path)
    summary = apply_auto_labels(
        summary_payload,
        min_score=args.min_score,
        beep_consensus_tolerance_ms=args.beep_consensus_tolerance_ms,
    )

    output_path = args.output.expanduser().resolve() if args.output is not None else manifest_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary_payload = summary.to_dict()
    if args.summary_output is not None:
        summary_path = args.summary_output.expanduser().resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(summary_payload, indent=2))
    else:
        print(render_table(summary_payload, output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())