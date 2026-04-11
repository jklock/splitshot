from __future__ import annotations

import argparse
from pathlib import Path

from splitshot.benchmarks.stage_suite import default_stage_paths, write_stage_suite_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export SplitShot stage benchmark detections to CSV.")
    parser.add_argument(
        "videos",
        nargs="*",
        type=Path,
        help="Stage videos to analyze. Defaults to Stage1.MP4 through Stage4.MP4 when present.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/stage_suite_analysis.csv"),
        help="CSV output path.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Detection threshold used by the local model.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    videos = args.videos or default_stage_paths()
    if not videos:
        raise SystemExit("No stage videos were provided or discovered.")
    rows = write_stage_suite_csv(videos, args.output, threshold=args.threshold)
    print(f"Wrote {len(rows)} benchmark rows to {args.output}")
