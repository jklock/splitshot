from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from splitshot.analysis.training_dataset import CLASS_NAMES, DatasetExtractionConfig, extract_training_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract a real-footage feature dataset from a ShotML training manifest.",
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
        default=Path("artifacts/training-dataset.npz"),
        help="Compressed NPZ output path for features and labels.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=None,
        help="Optional JSON summary output path.",
    )
    parser.add_argument(
        "--include-status",
        dest="include_statuses",
        action="append",
        default=None,
        help="Manifest label status to include. Repeat as needed. Defaults to verified only.",
    )
    parser.add_argument(
        "--use-detector-drafts",
        action="store_true",
        help="Use detector draft labels when verified labels are not available yet.",
    )
    parser.add_argument(
        "--detector-draft-policy",
        choices=("review-clean", "all"),
        default="review-clean",
        help="How aggressively to filter detector drafts before extraction. `review-clean` excludes videos flagged for shot disagreement, count drift, duplicate-stage inconsistency, or clipping.",
    )
    parser.add_argument(
        "--background-step-ms",
        type=int,
        default=500,
        help="Spacing between candidate background windows.",
    )
    parser.add_argument(
        "--background-limit-per-video",
        type=int,
        default=24,
        help="Maximum background windows to extract per included video.",
    )
    parser.add_argument(
        "--augment-replicas-per-event",
        type=int,
        default=0,
        help="Number of augmented copies to create for each beep and shot example.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic audio augmentation.",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Console output format.",
    )
    return parser


def render_table(summary: dict[str, object], output_path: Path) -> str:
    counts = summary["class_counts"]
    label_sources = summary["label_source_counts"]
    skipped_reasons = summary["skipped_video_reasons"]
    skipped_text = "--"
    if skipped_reasons:
        skipped_text = ", ".join(f"{reason}={count}" for reason, count in sorted(skipped_reasons.items()))
    return "\n".join(
        [
            f"Training Dataset: {output_path}",
            f"Manifest: {summary['manifest_path']}",
            f"Videos included: {summary['included_video_count']} / {summary['video_count']}",
            f"Use detector drafts: {summary['use_detector_drafts']}",
            f"Detector draft policy: {summary['detector_draft_policy']}",
            f"Augment replicas per event: {summary['augment_replicas_per_event']}",
            f"Label sources: verified={label_sources.get('verified', 0)}, auto_consensus={label_sources.get('auto_consensus', 0)}, detector_draft={label_sources.get('detector_draft', 0)}",
            f"Skipped reasons: {skipped_text}",
            "",
            "class | count",
            "------+------",
            *(f"{name} | {counts[name]}" for name in CLASS_NAMES),
        ]
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    include_statuses = tuple(args.include_statuses or ["verified"])
    config = DatasetExtractionConfig(
        use_detector_drafts=bool(args.use_detector_drafts),
        include_statuses=include_statuses,
        background_step_ms=args.background_step_ms,
        background_limit_per_video=args.background_limit_per_video,
        augment_replicas_per_event=args.augment_replicas_per_event,
        seed=args.seed,
        detector_draft_policy=args.detector_draft_policy,
    )
    features, labels, source_paths, label_sources, is_augmented, summary = extract_training_dataset(args.manifest, config)
    payload = summary.to_dict()

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        features=features,
        labels=labels,
        source_paths=source_paths,
        label_sources=label_sources,
        is_augmented=is_augmented,
        class_names=np.asarray(CLASS_NAMES),
    )

    if args.summary_output is not None:
        summary_path = args.summary_output.expanduser().resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(render_table(payload, output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
