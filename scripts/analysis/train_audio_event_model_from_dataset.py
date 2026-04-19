from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from splitshot.analysis.audio_features import FEATURE_NAMES
from splitshot.analysis.training_dataset import (
    CLASS_NAMES,
    LABEL_SOURCE_AUTO_CONSENSUS,
    LABEL_SOURCE_VERIFIED,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train a candidate ShotML MLP bundle from an extracted NPZ feature dataset.",
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        default="artifacts/training-dataset.npz",
        help="Path to the NPZ dataset produced by extract_training_dataset.py.",
    )
    parser.add_argument(
        "--output-bundle",
        type=Path,
        default=Path("artifacts/model_bundle_candidate.py"),
        help="Python bundle output path for the trained candidate model.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=None,
        help="Optional JSON summary output path.",
    )
    parser.add_argument(
        "--hidden-units",
        type=int,
        default=24,
        help="Hidden layer width for the MLP.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=240,
        help="Training epochs.",
    )
    parser.add_argument(
        "--validation-ratio",
        type=float,
        default=0.15,
        help="Fraction of rows reserved for validation.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed.",
    )
    parser.add_argument(
        "--split-mode",
        choices=("source", "random"),
        default="source",
        help="Validation split mode. `source` holds out entire videos when source_paths are available in the dataset.",
    )
    parser.add_argument(
        "--class-weighting",
        choices=("balanced", "none"),
        default="balanced",
        help="Apply inverse-frequency class weighting during training and validation loss selection.",
    )
    parser.add_argument(
        "--class-weight-alpha",
        type=float,
        default=1.0,
        help="Interpolation between unweighted and balanced class weights. 0 is unweighted, 1 is fully balanced.",
    )
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=20,
        help="Stop if validation loss does not improve for this many epochs.",
    )
    parser.add_argument(
        "--require-verified-validation",
        action="store_true",
        help="Fail if the held-out validation split contains no verified labels, so draft-only runs cannot be mistaken for actuals.",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Console output format.",
    )
    return parser


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=1, keepdims=True)


def _train_mlp(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_validation: np.ndarray,
    y_validation: np.ndarray,
    hidden_units: int,
    epochs: int,
    class_weights: np.ndarray,
    early_stopping_patience: int,
    rng: np.random.Generator,
) -> tuple[dict[str, np.ndarray], int]:
    feature_count = x_train.shape[1]
    class_count = len(CLASS_NAMES)
    w1 = (rng.normal(0.0, math.sqrt(2.0 / feature_count), (feature_count, hidden_units))).astype(np.float32)
    b1 = np.zeros(hidden_units, dtype=np.float32)
    w2 = (rng.normal(0.0, math.sqrt(2.0 / hidden_units), (hidden_units, class_count))).astype(np.float32)
    b2 = np.zeros(class_count, dtype=np.float32)

    one_hot = np.eye(class_count, dtype=np.float32)[y_train]
    learning_rate = 0.01
    batch_size = min(256, max(16, x_train.shape[0]))
    beta1 = 0.9
    beta2 = 0.999
    epsilon = 1e-8
    moments = {"w1": np.zeros_like(w1), "b1": np.zeros_like(b1), "w2": np.zeros_like(w2), "b2": np.zeros_like(b2)}
    velocities = {"w1": np.zeros_like(w1), "b1": np.zeros_like(b1), "w2": np.zeros_like(w2), "b2": np.zeros_like(b2)}

    best_model = {"w1": w1.copy(), "b1": b1.copy(), "w2": w2.copy(), "b2": b2.copy()}
    best_validation_loss = float("inf")
    epochs_without_improvement = 0
    best_epoch = 0
    step = 0
    for epoch in range(epochs):
        indices = rng.permutation(x_train.shape[0])
        for batch_start in range(0, x_train.shape[0], batch_size):
            batch_indices = indices[batch_start : batch_start + batch_size]
            batch_x = x_train[batch_indices]
            batch_y = one_hot[batch_indices]
            batch_weights = class_weights[y_train[batch_indices]].astype(np.float32)

            hidden_linear = batch_x @ w1 + b1
            hidden = np.maximum(hidden_linear, 0.0)
            logits = hidden @ w2 + b2
            probabilities = _softmax(logits)

            normalization = float(np.sum(batch_weights)) or float(batch_x.shape[0])
            grad_logits = ((probabilities - batch_y) * batch_weights[:, None]) / normalization
            grad_w2 = hidden.T @ grad_logits
            grad_b2 = np.sum(grad_logits, axis=0)
            grad_hidden = grad_logits @ w2.T
            grad_hidden[hidden_linear <= 0.0] = 0.0
            grad_w1 = batch_x.T @ grad_hidden
            grad_b1 = np.sum(grad_hidden, axis=0)

            step += 1
            gradients = {"w1": grad_w1, "b1": grad_b1, "w2": grad_w2, "b2": grad_b2}
            for key, gradient in gradients.items():
                moments[key] = (beta1 * moments[key]) + ((1.0 - beta1) * gradient)
                velocities[key] = (beta2 * velocities[key]) + ((1.0 - beta2) * (gradient**2))
                moment_hat = moments[key] / (1.0 - (beta1**step))
                velocity_hat = velocities[key] / (1.0 - (beta2**step))
                update = learning_rate * moment_hat / (np.sqrt(velocity_hat) + epsilon)
                if key == "w1":
                    w1 -= update
                elif key == "b1":
                    b1 -= update
                elif key == "w2":
                    w2 -= update
                else:
                    b2 -= update

        validation_model = {"w1": w1, "b1": b1, "w2": w2, "b2": b2}
        validation_loss = _cross_entropy_loss(x_validation, y_validation, validation_model, class_weights)
        if validation_loss < best_validation_loss - 1e-6:
            best_validation_loss = validation_loss
            best_epoch = epoch + 1
            epochs_without_improvement = 0
            best_model = {
                "w1": w1.copy(),
                "b1": b1.copy(),
                "w2": w2.copy(),
                "b2": b2.copy(),
            }
        else:
            epochs_without_improvement += 1
            if early_stopping_patience > 0 and epochs_without_improvement >= early_stopping_patience:
                break

    return best_model, best_epoch


def _cross_entropy_loss(
    x_values: np.ndarray,
    y_values: np.ndarray,
    model: dict[str, np.ndarray],
    class_weights: np.ndarray,
) -> float:
    hidden = np.maximum((x_values @ model["w1"]) + model["b1"], 0.0)
    logits = hidden @ model["w2"] + model["b2"]
    probabilities = _softmax(logits)
    target_probabilities = np.clip(probabilities[np.arange(y_values.size), y_values], 1e-8, 1.0)
    weights = class_weights[y_values]
    return float(np.sum(-np.log(target_probabilities) * weights) / max(float(np.sum(weights)), 1.0))


def _predict(x_values: np.ndarray, model: dict[str, np.ndarray]) -> np.ndarray:
    hidden = np.maximum((x_values @ model["w1"]) + model["b1"], 0.0)
    logits = hidden @ model["w2"] + model["b2"]
    return np.argmax(logits, axis=1)


def _accuracy(x_values: np.ndarray, y_values: np.ndarray, model: dict[str, np.ndarray]) -> float:
    predictions = _predict(x_values, model)
    return float(np.mean(predictions == y_values))


def _write_bundle(
    output_path: Path,
    mean: np.ndarray,
    std: np.ndarray,
    model: dict[str, np.ndarray],
    train_accuracy: float,
    validation_accuracy: float,
) -> None:
    lines = [
        "from __future__ import annotations",
        "",
        f'MODEL_METADATA = {{"version": "audio-event-ml-v1-candidate", "sample_rate": 22050, "train_accuracy": {train_accuracy:.6f}, "validation_accuracy": {validation_accuracy:.6f}}}',
        f"CLASS_LABELS = {list(CLASS_NAMES)!r}",
        f"FEATURE_NAMES = {list(FEATURE_NAMES)!r}",
        "WINDOW_SIZE = 2048",
        "HOP_SIZE = 128",
        f"STANDARDIZATION_MEAN = {mean.tolist()!r}",
        f"STANDARDIZATION_STD = {std.tolist()!r}",
        f'W1 = {model["w1"].tolist()!r}',
        f'B1 = {model["b1"].tolist()!r}',
        f'W2 = {model["w2"].tolist()!r}',
        f'B2 = {model["b2"].tolist()!r}',
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def render_table(summary: dict[str, object], output_bundle: Path) -> str:
    class_counts = summary["class_counts"]
    lines = [
        f"Candidate Model Bundle: {output_bundle}",
        f"Dataset: {summary['dataset_path']}",
        f"Samples: {summary['sample_count']}",
        f"Feature count: {summary['feature_count']}",
        f"Split mode: {summary['split_mode']}",
        f"Class weighting: {summary['class_weighting']}",
        f"Class weight alpha: {summary['class_weight_alpha']:.2f}",
        f"Clean samples: {summary['clean_sample_count']}",
        f"Augmented training samples: {summary['augmented_sample_count']}",
        f"Best epoch: {summary['best_epoch']}",
        f"Train accuracy: {summary['train_accuracy']:.4f}",
        f"Validation accuracy: {summary['validation_accuracy']:.4f}",
        f"Validation macro recall: {summary['validation_macro_recall']:.4f}",
        f"Validation clean only: {'yes' if summary['validation_clean_only'] else 'no'}",
        f"Actuals available: {'yes' if summary['actual_metrics_available'] else 'no'}",
        f"Verified validation samples: {summary['verified_validation_sample_count']}",
    ]
    robustness = summary.get("robustness_leave_one_source_out", {})
    if isinstance(robustness, dict) and robustness.get("available"):
        lines.extend(
            [
                f"LOSO accuracy: {robustness['accuracy']:.4f}",
                f"LOSO macro recall: {robustness['macro_recall']:.4f}",
            ]
        )
    if summary["verified_validation_accuracy"] is not None:
        lines.append(f"Verified validation accuracy: {summary['verified_validation_accuracy']:.4f}")
    if summary["verified_validation_macro_recall"] is not None:
        lines.append(f"Verified validation macro recall: {summary['verified_validation_macro_recall']:.4f}")
    lines.extend(
        [
            "",
            "class | count",
            "------+------",
            *(f"{name} | {class_counts[name]}" for name in CLASS_NAMES),
        ]
    )
    warnings = summary.get("warnings", [])
    if warnings:
        lines.extend(["", *(f"warning: {warning}" for warning in warnings)])
    return "\n".join(lines)


def compute_class_weights(labels: np.ndarray, mode: str, alpha: float = 1.0) -> np.ndarray:
    if mode == "none":
        return np.ones(len(CLASS_NAMES), dtype=np.float32)
    counts = np.bincount(labels, minlength=len(CLASS_NAMES)).astype(np.float32)
    weights = np.ones(len(CLASS_NAMES), dtype=np.float32)
    nonzero = counts > 0
    if np.any(nonzero):
        weights[nonzero] = float(labels.size) / (float(len(CLASS_NAMES)) * counts[nonzero])
        weights = weights / float(np.mean(weights[nonzero]))
    alpha = min(1.0, max(0.0, float(alpha)))
    interpolated = np.ones(len(CLASS_NAMES), dtype=np.float32) + (alpha * (weights.astype(np.float32) - 1.0))
    return interpolated.astype(np.float32)


def per_class_recall(x_values: np.ndarray, y_values: np.ndarray, model: dict[str, np.ndarray]) -> dict[str, float]:
    predictions = _predict(x_values, model)
    return per_class_recall_from_predictions(y_values, predictions)


def per_class_recall_from_predictions(y_values: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    recalls: dict[str, float] = {}
    for index, name in enumerate(CLASS_NAMES):
        mask = y_values == index
        if not np.any(mask):
            recalls[name] = 0.0
            continue
        recalls[name] = float(np.mean(predictions[mask] == index))
    return recalls


def macro_recall(recalls: dict[str, float], labels: np.ndarray) -> float | None:
    if labels.size == 0:
        return None
    present_indices = sorted(set(int(value) for value in labels.tolist()))
    if not present_indices:
        return None
    return float(np.mean([recalls[CLASS_NAMES[index]] for index in present_indices]))


def confusion_counts(y_values: np.ndarray, predictions: np.ndarray) -> dict[str, dict[str, int]]:
    matrix = {actual: {predicted: 0 for predicted in CLASS_NAMES} for actual in CLASS_NAMES}
    for actual_index, predicted_index in zip(y_values.tolist(), predictions.tolist()):
        matrix[CLASS_NAMES[int(actual_index)]][CLASS_NAMES[int(predicted_index)]] += 1
    return matrix


def count_label_sources(label_sources: np.ndarray | None) -> dict[str, int]:
    if label_sources is None or label_sources.size == 0:
        return {}
    unique_values, counts = np.unique(np.asarray(label_sources, dtype=str), return_counts=True)
    return {str(value): int(count) for value, count in zip(unique_values.tolist(), counts.tolist())}


def split_indices(
    features: np.ndarray,
    labels: np.ndarray,
    source_paths: np.ndarray | None,
    eligible_validation_mask: np.ndarray,
    validation_ratio: float,
    split_mode: str,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, str, list[str]]:
    if split_mode == "source" and source_paths is not None and source_paths.size == labels.size:
        eligible_sources = source_paths[eligible_validation_mask]
        unique_sources = np.asarray(sorted(set(eligible_sources.tolist())))
        if unique_sources.size >= 2:
            shuffled_sources = unique_sources[rng.permutation(unique_sources.size)]
            target_validation_count = max(1, int(round(unique_sources.size * validation_ratio)))
            validation_sources = set(shuffled_sources[:target_validation_count].tolist())
            source_validation_mask = np.asarray([path in validation_sources for path in source_paths], dtype=bool)
            validation_mask = source_validation_mask & eligible_validation_mask
            train_mask = ~source_validation_mask
            if np.any(validation_mask) and np.any(train_mask):
                return (
                    np.flatnonzero(train_mask),
                    np.flatnonzero(validation_mask),
                    "source",
                    sorted(validation_sources),
                )

    eligible_indices = np.flatnonzero(eligible_validation_mask)
    if eligible_indices.size < 2:
        eligible_indices = np.arange(features.shape[0])
    permutation = eligible_indices[rng.permutation(eligible_indices.size)]
    split_index = max(1, min(permutation.size - 1, int(permutation.size * (1.0 - validation_ratio))))
    validation_indices = permutation[split_index:]
    validation_index_set = set(int(index) for index in validation_indices.tolist())
    train_indices = np.asarray(
        [index for index in range(features.shape[0]) if index not in validation_index_set],
        dtype=np.int64,
    )
    validation_sources = []
    if source_paths is not None and source_paths.size == labels.size:
        validation_sources = sorted(set(source_paths[validation_indices].tolist()))
    return train_indices, validation_indices, "random", validation_sources


def _normalize_from_train(
    train_features: np.ndarray,
    validation_features: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = train_features.mean(axis=0).astype(np.float32)
    std = train_features.std(axis=0).astype(np.float32)
    std = np.where(std < 1e-5, 1.0, std)
    return (train_features - mean) / std, (validation_features - mean) / std, mean, std


def _source_display_name(source: str) -> str:
    name = Path(source).name
    return name or source


def evaluate_leave_one_source_out(
    features: np.ndarray,
    labels: np.ndarray,
    source_paths: np.ndarray | None,
    label_sources: np.ndarray | None,
    is_augmented: np.ndarray,
    hidden_units: int,
    epochs: int,
    class_weighting: str,
    class_weight_alpha: float,
    early_stopping_patience: int,
    seed: int,
) -> dict[str, object]:
    if source_paths is None or source_paths.size != labels.size:
        return {
            "available": False,
            "reason": "source_paths_unavailable",
            "source_count": 0,
            "folds": [],
        }

    clean_mask = ~is_augmented
    unique_sources = sorted(set(source_paths[clean_mask].tolist()))
    folds: list[dict[str, object]] = []
    aggregate_labels: list[np.ndarray] = []
    aggregate_predictions: list[np.ndarray] = []
    total_correct = 0
    total_samples = 0

    for fold_index, source in enumerate(unique_sources):
        validation_mask = (source_paths == source) & clean_mask
        train_mask = source_paths != source
        if not np.any(validation_mask) or not np.any(train_mask):
            continue

        train_features = features[train_mask]
        validation_features = features[validation_mask]
        train_labels = labels[train_mask]
        validation_labels = labels[validation_mask]
        normalized_train, normalized_validation, _, _ = _normalize_from_train(train_features, validation_features)
        class_weights = compute_class_weights(train_labels, class_weighting, class_weight_alpha)
        model, best_epoch = _train_mlp(
            normalized_train,
            train_labels,
            normalized_validation,
            validation_labels,
            hidden_units,
            epochs,
            class_weights,
            early_stopping_patience,
            np.random.default_rng(seed + fold_index + 1),
        )
        predictions = _predict(normalized_validation, model)
        correct = int(np.sum(predictions == validation_labels))
        sample_count = int(validation_labels.size)
        recalls = per_class_recall_from_predictions(validation_labels, predictions)
        folds.append(
            {
                "source": str(source),
                "source_name": _source_display_name(str(source)),
                "sample_count": sample_count,
                "train_sample_count": int(np.sum(train_mask)),
                "best_epoch": int(best_epoch),
                "accuracy": float(correct / max(sample_count, 1)),
                "macro_recall": macro_recall(recalls, validation_labels),
                "class_recall": recalls,
                "confusion_counts": confusion_counts(validation_labels, predictions),
                "label_source_counts": count_label_sources(None if label_sources is None else label_sources[validation_mask]),
            }
        )
        aggregate_labels.append(validation_labels)
        aggregate_predictions.append(predictions)
        total_correct += correct
        total_samples += sample_count

    if not folds or total_samples == 0:
        return {
            "available": False,
            "reason": "not_enough_sources",
            "source_count": len(unique_sources),
            "folds": folds,
        }

    all_labels = np.concatenate(aggregate_labels)
    all_predictions = np.concatenate(aggregate_predictions)
    aggregate_recalls = per_class_recall_from_predictions(all_labels, all_predictions)
    source_accuracies = [float(fold["accuracy"]) for fold in folds]
    source_macro_recalls = [
        float(fold["macro_recall"])
        for fold in folds
        if fold.get("macro_recall") is not None
    ]
    return {
        "available": True,
        "source_count": len(unique_sources),
        "fold_count": len(folds),
        "sample_count": int(total_samples),
        "accuracy": float(total_correct / total_samples),
        "macro_recall": macro_recall(aggregate_recalls, all_labels),
        "class_recall": aggregate_recalls,
        "mean_source_accuracy": float(np.mean(source_accuracies)) if source_accuracies else None,
        "mean_source_macro_recall": float(np.mean(source_macro_recalls)) if source_macro_recalls else None,
        "confusion_counts": confusion_counts(all_labels, all_predictions),
        "folds": folds,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dataset_path = Path(args.dataset).expanduser().resolve()
    archive = np.load(dataset_path)
    features = archive["features"].astype(np.float32)
    labels = archive["labels"].astype(np.int64)
    source_paths = archive["source_paths"] if "source_paths" in archive else None
    label_sources = np.asarray(archive["label_sources"], dtype=str) if "label_sources" in archive else None
    is_augmented = archive["is_augmented"].astype(bool) if "is_augmented" in archive else np.zeros(labels.size, dtype=bool)
    if features.size == 0 or labels.size == 0:
        raise SystemExit(f"Dataset is empty: {dataset_path}")
    if is_augmented.size != labels.size:
        raise SystemExit(f"Dataset is_augmented row count does not match labels: {dataset_path}")
    if not 0.0 <= float(args.class_weight_alpha) <= 1.0:
        raise SystemExit("--class-weight-alpha must be between 0 and 1.")

    validation_ratio = min(0.5, max(0.05, float(args.validation_ratio)))
    rng = np.random.default_rng(args.seed)
    clean_validation_mask = ~is_augmented
    train_indices, validation_indices, effective_split_mode, validation_sources = split_indices(
        features,
        labels,
        source_paths,
        clean_validation_mask,
        validation_ratio,
        args.split_mode,
        rng,
    )
    train_features = features[train_indices]
    validation_features = features[validation_indices]
    train_labels = labels[train_indices]
    validation_labels = labels[validation_indices]
    train_label_sources = None if label_sources is None else label_sources[train_indices]
    validation_label_sources = None if label_sources is None else label_sources[validation_indices]

    normalized_train, normalized_validation, mean, std = _normalize_from_train(train_features, validation_features)
    class_weights = compute_class_weights(train_labels, args.class_weighting, args.class_weight_alpha)
    model, best_epoch = _train_mlp(
        normalized_train,
        train_labels,
        normalized_validation,
        validation_labels,
        args.hidden_units,
        args.epochs,
        class_weights,
        args.early_stopping_patience,
        rng,
    )
    train_accuracy = _accuracy(normalized_train, train_labels, model)
    validation_accuracy = _accuracy(normalized_validation, validation_labels, model)
    validation_predictions = _predict(normalized_validation, model)
    validation_class_recall = per_class_recall(normalized_validation, validation_labels, model)
    validation_macro_recall = macro_recall(validation_class_recall, validation_labels)
    validation_confusion_counts = confusion_counts(validation_labels, validation_predictions)
    robustness_summary = evaluate_leave_one_source_out(
        features,
        labels,
        source_paths,
        label_sources,
        is_augmented,
        args.hidden_units,
        args.epochs,
        args.class_weighting,
        args.class_weight_alpha,
        args.early_stopping_patience,
        args.seed,
    )

    verified_validation_sample_count = 0
    verified_validation_accuracy = None
    verified_validation_class_recall = None
    verified_validation_macro_recall = None
    if validation_label_sources is not None:
        verified_validation_mask = validation_label_sources == LABEL_SOURCE_VERIFIED
        verified_validation_sample_count = int(np.sum(verified_validation_mask))
        if verified_validation_sample_count > 0:
            verified_features = normalized_validation[verified_validation_mask]
            verified_labels = validation_labels[verified_validation_mask]
            verified_validation_accuracy = _accuracy(verified_features, verified_labels, model)
            verified_validation_class_recall = per_class_recall(verified_features, verified_labels, model)
            verified_validation_macro_recall = macro_recall(verified_validation_class_recall, verified_labels)

    if args.require_verified_validation and verified_validation_sample_count == 0:
        raise SystemExit(
            "Validation split contains no verified labels. Actual metrics are unavailable; review more clips or train without --require-verified-validation for exploratory draft-only runs."
        )

    warnings: list[str] = []
    overall_label_source_counts = count_label_sources(label_sources)
    train_label_source_counts = count_label_sources(train_label_sources)
    validation_label_source_counts = count_label_sources(validation_label_sources)
    if overall_label_source_counts.get(LABEL_SOURCE_VERIFIED, 0) == 0:
        warnings.append(
            "Dataset contains no verified labels; validation metrics are automated or exploratory metrics, not manual actuals."
        )
    elif verified_validation_sample_count == 0:
        warnings.append(
            "Validation split contains no verified labels; use verified validation metrics only after reviewing more clips."
        )
    if overall_label_source_counts.get(LABEL_SOURCE_AUTO_CONSENSUS, 0) > 0:
        warnings.append(
            "Auto-consensus labels are present; they are stronger than raw detector drafts but still not manual verified labels."
        )
    if overall_label_source_counts.get("detector_draft", 0) > 0:
        warnings.append(
            "Detector-draft labels are present; use verified_validation_* metrics for actual comparisons."
        )

    output_bundle = args.output_bundle.expanduser().resolve()
    _write_bundle(output_bundle, mean, std, model, train_accuracy, validation_accuracy)

    class_counts = {name: int(np.sum(labels == index)) for index, name in enumerate(CLASS_NAMES)}
    payload = {
        "dataset_path": str(dataset_path),
        "output_bundle": str(output_bundle),
        "sample_count": int(features.shape[0]),
        "feature_count": int(features.shape[1]),
        "split_mode": effective_split_mode,
        "validation_clean_only": bool(not np.any(is_augmented[validation_indices])),
        "clean_sample_count": int(np.sum(~is_augmented)),
        "augmented_sample_count": int(np.sum(is_augmented)),
        "train_sample_count": int(train_labels.size),
        "validation_sample_count": int(validation_labels.size),
        "validation_sources": [str(source) for source in validation_sources],
        "validation_source_names": [_source_display_name(str(source)) for source in validation_sources],
        "class_weighting": args.class_weighting,
        "class_weight_alpha": float(args.class_weight_alpha),
        "class_weights": {name: float(class_weights[index]) for index, name in enumerate(CLASS_NAMES)},
        "label_source_counts": overall_label_source_counts,
        "train_label_source_counts": train_label_source_counts,
        "validation_label_source_counts": validation_label_source_counts,
        "best_epoch": int(best_epoch),
        "train_accuracy": train_accuracy,
        "validation_accuracy": validation_accuracy,
        "validation_macro_recall": validation_macro_recall,
        "validation_class_recall": validation_class_recall,
        "validation_confusion_counts": validation_confusion_counts,
        "deployment_validation_accuracy": validation_accuracy,
        "deployment_validation_macro_recall": validation_macro_recall,
        "deployment_validation_class_recall": validation_class_recall,
        "deployment_validation_confusion_counts": validation_confusion_counts,
        "robustness_leave_one_source_out": robustness_summary,
        "actual_metrics_available": verified_validation_sample_count > 0,
        "verified_validation_sample_count": verified_validation_sample_count,
        "verified_validation_accuracy": verified_validation_accuracy,
        "verified_validation_macro_recall": verified_validation_macro_recall,
        "verified_validation_class_recall": verified_validation_class_recall,
        "warnings": warnings,
        "class_counts": class_counts,
        "hidden_units": int(args.hidden_units),
        "epochs": int(args.epochs),
    }

    if args.summary_output is not None:
        summary_path = args.summary_output.expanduser().resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(render_table(payload, output_bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
