from __future__ import annotations

import argparse
import json
from pathlib import Path

from splitshot.analysis.corpus import DEFAULT_THRESHOLD_GRID, build_label_manifest, list_corpus_videos


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bootstrap a review manifest for local training footage using the current ShotML detector as draft labels.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".training",
        help="Video file or directory to seed into a label manifest. Defaults to .training in the repo root.",
    )
    parser.add_argument(
        "--threshold-grid",
        default=",".join(f"{value:.2f}" for value in DEFAULT_THRESHOLD_GRID),
        help="Comma-separated thresholds to sweep while generating detector draft metadata.",
    )
    parser.add_argument(
        "--reference-threshold",
        type=float,
        default=0.35,
        help="Threshold used for the draft beep and shot labels stored in the manifest.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path. Defaults to shotml-label-manifest.json beside the input corpus.",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Console output format.",
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


def default_output_path(input_path: Path) -> Path:
    if input_path.is_dir():
        return input_path / "shotml-label-manifest.json"
    return input_path.parent / "shotml-label-manifest.json"


def render_table(input_path: Path, output_path: Path, payload: dict[str, object]) -> str:
    lines = [
        f"Training Label Manifest: {input_path}",
        f"Output: {output_path}",
        f"Videos: {payload['video_count']}",
        "",
        "video | shots | beep | beep cmp | shot cmp | family | status | flags",
        "------+-------+------+----------+----------+--------+--------+------",
    ]
    for video in payload["videos"]:
        beep_multipass = video["beep_multipass"]
        beep_compare = format_beep_compare(beep_multipass)
        shot_multipass = video["shot_multipass"]
        shot_unmatched_total = int(shot_multipass["unmatched_final_count"]) + int(shot_multipass["unmatched_onset_count"])
        shot_echo_like = int(shot_multipass.get("echo_like_onset_count", 0))
        if shot_unmatched_total == 0 and shot_multipass["max_match_gap_ms"] is None:
            shot_compare = "--"
        elif bool(shot_multipass["review_required"]):
            shot_compare = f"review {shot_unmatched_total}"
        elif shot_echo_like > 0:
            shot_compare = f"echo {shot_echo_like}"
        else:
            shot_compare = f"ok {shot_unmatched_total}"
        lines.append(
            " | ".join(
                [
                    str(video["relative_path"]),
                    str(video["detector_shot_count"]).rjust(5),
                    ("--" if video["detector_beep_time_ms"] is None else f"{video['detector_beep_time_ms']}ms").rjust(4),
                    beep_compare.rjust(8),
                    shot_compare.rjust(8),
                    str(video["beep_family"]).rjust(6),
                    str(video["labels"]["status"]).rjust(6),
                    ",".join(video["review_flags"]) if video["review_flags"] else "--",
                ]
            )
        )
    duplicate_groups = payload.get("duplicate_groups", [])
    if duplicate_groups:
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


def load_existing_manifest(output_path: Path) -> dict[str, object] | None:
    if not output_path.exists() or not output_path.is_file():
        return None
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


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

    output_path = args.output.expanduser().resolve() if args.output is not None else default_output_path(input_path)
    existing_manifest = load_existing_manifest(output_path)
    payload = build_label_manifest(
        input_path,
        thresholds=threshold_grid,
        reference_threshold=args.reference_threshold,
        existing_manifest=existing_manifest,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(render_table(input_path, output_path, payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())