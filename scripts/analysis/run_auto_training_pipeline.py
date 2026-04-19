from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from splitshot.analysis.auto_labeling import apply_auto_labels
from splitshot.analysis.corpus import DEFAULT_THRESHOLD_GRID, build_label_manifest, list_corpus_videos
from splitshot.analysis.training_dataset import (
    DatasetExtractionConfig,
    LABEL_STATUS_AUTO_LABELED,
    LABEL_STATUS_VERIFIED,
    extract_training_dataset,
)


ROOT = Path(__file__).resolve().parents[2]
TRAIN_SCRIPT = ROOT / "scripts" / "analysis" / "train_audio_event_model_from_dataset.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the unattended training pipeline from corpus audit through candidate bundle training.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".training",
        help="Video file or directory to train from. Defaults to .training in the repo root.",
    )
    parser.add_argument(
        "--threshold-grid",
        default=",".join(f"{value:.2f}" for value in DEFAULT_THRESHOLD_GRID),
        help="Comma-separated thresholds to sweep while bootstrapping the manifest.",
    )
    parser.add_argument(
        "--reference-threshold",
        type=float,
        default=0.35,
        help="Reference threshold used for detector draft labels in the manifest.",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=Path(".training/shotml-label-manifest.json"),
        help="Manifest output path.",
    )
    parser.add_argument(
        "--autolabel-summary-output",
        type=Path,
        default=Path("artifacts/training-autolabel-summary.json"),
        help="Automated labeling summary output path.",
    )
    parser.add_argument(
        "--dataset-output",
        type=Path,
        default=Path("artifacts/training-dataset-auto.npz"),
        help="Dataset NPZ output path.",
    )
    parser.add_argument(
        "--dataset-summary-output",
        type=Path,
        default=Path("artifacts/training-dataset-auto-summary.json"),
        help="Dataset JSON summary output path.",
    )
    parser.add_argument(
        "--pipeline-summary-output",
        type=Path,
        default=Path("artifacts/auto-training-pipeline-summary.json"),
        help="Top-level pipeline JSON summary output path.",
    )
    parser.add_argument(
        "--output-bundle",
        type=Path,
        default=Path("artifacts/model_bundle_candidate_auto.py"),
        help="Candidate model bundle output path.",
    )
    parser.add_argument(
        "--training-summary-output",
        type=Path,
        default=Path("artifacts/model-training-auto-summary.json"),
        help="Training summary output path.",
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
        help="Random seed for extraction and training.",
    )
    parser.add_argument(
        "--auto-label-min-score",
        type=float,
        default=0.65,
        help="Minimum consensus score required for automated promotion.",
    )
    parser.add_argument(
        "--beep-consensus-tolerance-ms",
        type=int,
        default=180,
        help="Maximum gap between two beep candidates for pair-consensus promotion.",
    )
    parser.add_argument(
        "--hidden-units",
        type=int,
        default=12,
        help="Hidden layer width for candidate training.",
    )
    parser.add_argument(
        "--train-epochs",
        type=int,
        default=120,
        help="Training epochs for the candidate model.",
    )
    parser.add_argument(
        "--validation-ratio",
        type=float,
        default=0.15,
        help="Validation split fraction for candidate training.",
    )
    parser.add_argument(
        "--class-weighting",
        choices=("balanced", "none"),
        default="balanced",
        help="Class weighting mode for candidate training.",
    )
    parser.add_argument(
        "--class-weight-alpha",
        type=float,
        default=0.85,
        help="Interpolation between unweighted and balanced class weights. 0 is unweighted, 1 is fully balanced.",
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


def load_existing_manifest(output_path: Path) -> dict[str, object] | None:
    if not output_path.exists() or not output_path.is_file():
        return None
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def render_table(summary: dict[str, object]) -> str:
    extraction = summary["dataset_summary"]
    training = summary["training_summary"]
    autolabel = summary["autolabel_summary"]
    lines = [
        f"Auto Training Pipeline: {summary['input']}",
        f"Manifest: {summary['manifest_path']}",
        f"Auto-labeled videos: {autolabel['auto_labeled_count']}",
        f"Dataset videos included: {extraction['included_video_count']} / {extraction['video_count']}",
        f"Dataset label sources: {', '.join(f'{key}={value}' for key, value in sorted(extraction['label_source_counts'].items()))}",
        f"Candidate bundle: {summary['output_bundle']}",
        f"Candidate samples: {training['sample_count']}",
        f"Class weight alpha: {training['class_weight_alpha']:.2f}",
        f"Clean validation: {'yes' if training['validation_clean_only'] else 'no'}",
        f"Deployment validation accuracy: {training['deployment_validation_accuracy']:.4f}",
        f"Deployment validation macro recall: {training['deployment_validation_macro_recall']:.4f}",
        f"Actuals available: {'yes' if training['actual_metrics_available'] else 'no'}",
    ]
    robustness = training.get("robustness_leave_one_source_out", {})
    if isinstance(robustness, dict) and robustness.get("available"):
        lines.extend(
            [
                f"LOSO accuracy: {robustness['accuracy']:.4f}",
                f"LOSO macro recall: {robustness['macro_recall']:.4f}",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Corpus path not found: {input_path}")
    if not list_corpus_videos(input_path):
        raise SystemExit(f"No supported video files found in {input_path}")
    thresholds = parse_threshold_grid(args.threshold_grid)

    manifest_path = args.manifest_output.expanduser().resolve()
    existing_manifest = load_existing_manifest(manifest_path)
    manifest_payload = build_label_manifest(
        input_path,
        thresholds=thresholds,
        reference_threshold=args.reference_threshold,
        existing_manifest=existing_manifest,
    )
    autolabel_payload = dict(manifest_payload)
    autolabel_payload["manifest_path"] = str(manifest_path)
    autolabel_summary = apply_auto_labels(
        autolabel_payload,
        min_score=args.auto_label_min_score,
        beep_consensus_tolerance_ms=args.beep_consensus_tolerance_ms,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

    autolabel_summary_path = args.autolabel_summary_output.expanduser().resolve()
    autolabel_summary_path.parent.mkdir(parents=True, exist_ok=True)
    autolabel_summary_path.write_text(json.dumps(autolabel_summary.to_dict(), indent=2), encoding="utf-8")

    dataset_output = args.dataset_output.expanduser().resolve()
    dataset_summary_output = args.dataset_summary_output.expanduser().resolve()
    dataset_config = DatasetExtractionConfig(
        use_detector_drafts=False,
        include_statuses=(LABEL_STATUS_VERIFIED, LABEL_STATUS_AUTO_LABELED),
        background_step_ms=args.background_step_ms,
        background_limit_per_video=args.background_limit_per_video,
        augment_replicas_per_event=args.augment_replicas_per_event,
        seed=args.seed,
        detector_draft_policy="review-clean",
    )
    features, labels, source_paths, label_sources, is_augmented, dataset_summary = extract_training_dataset(
        manifest_path,
        dataset_config,
    )
    dataset_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        dataset_output,
        features=features,
        labels=labels,
        source_paths=source_paths,
        label_sources=label_sources,
        is_augmented=is_augmented,
        class_names=np.asarray(["background", "beep", "shot"]),
    )
    dataset_summary_output.parent.mkdir(parents=True, exist_ok=True)
    dataset_summary_output.write_text(json.dumps(dataset_summary.to_dict(), indent=2), encoding="utf-8")

    if features.size == 0 or labels.size == 0:
        raise SystemExit(
            "Automated pipeline produced an empty dataset. Adjust the auto-label thresholds or allow detector-draft fallback."
        )

    output_bundle = args.output_bundle.expanduser().resolve()
    training_summary_output = args.training_summary_output.expanduser().resolve()
    training_command = [
        sys.executable,
        str(TRAIN_SCRIPT),
        str(dataset_output),
        "--output-bundle",
        str(output_bundle),
        "--summary-output",
        str(training_summary_output),
        "--hidden-units",
        str(args.hidden_units),
        "--epochs",
        str(args.train_epochs),
        "--validation-ratio",
        str(args.validation_ratio),
        "--class-weighting",
        str(args.class_weighting),
        "--class-weight-alpha",
        str(args.class_weight_alpha),
        "--seed",
        str(args.seed),
        "--format",
        "json",
    ]
    result = subprocess.run(
        training_command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout or "Candidate training failed.")
    training_summary = json.loads(result.stdout)

    pipeline_summary = {
        "input": str(input_path),
        "manifest_path": str(manifest_path),
        "autolabel_summary_path": str(autolabel_summary_path),
        "dataset_path": str(dataset_output),
        "dataset_summary_path": str(dataset_summary_output),
        "output_bundle": str(output_bundle),
        "training_summary_path": str(training_summary_output),
        "autolabel_summary": autolabel_summary.to_dict(),
        "dataset_summary": dataset_summary.to_dict(),
        "training_summary": training_summary,
    }
    pipeline_summary_path = args.pipeline_summary_output.expanduser().resolve()
    pipeline_summary_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline_summary_path.write_text(json.dumps(pipeline_summary, indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(pipeline_summary, indent=2))
    else:
        print(render_table(pipeline_summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
