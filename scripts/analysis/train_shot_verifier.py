"""Train the 640 ms wearer-shot verifier from manually reviewed hat-camera truth."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from splitshot.analysis.auto_labeling import load_manifest
from splitshot.analysis.detection import (
    _align_samples_to_media_timeline,
    _media_timeline_metadata,
)
from splitshot.analysis.shot_context import (
    CONTEXT_WINDOW_MS,
    FEATURE_SCHEMA_VERSION,
    estimate_stage_noise_floor_dbfs,
    extract_shot_context_features,
)
from splitshot.media.audio import extract_audio_wav, read_wav_channels


def _resolve_video_path(
    video: dict[str, object], manifest_path: Path, manifest: dict[str, object]
) -> Path | None:
    direct = Path(str(video.get("path", ""))).expanduser()
    if direct.is_file():
        return direct.resolve()
    relative = str(video.get("relative_path", "") or "")
    if not relative:
        return None
    root = Path(str(manifest.get("input") or manifest_path.parent)).expanduser()
    candidate = root / relative
    return candidate.resolve() if candidate.is_file() else None


def _load_channels(path: Path) -> tuple[np.ndarray, int]:
    with TemporaryDirectory(prefix="splitshot-verifier-") as temp_dir:
        wav_path = Path(temp_dir) / "audio.wav"
        extract_audio_wav(path, wav_path, preserve_channels=True)
        channels, sample_rate = read_wav_channels(wav_path)
    audio_start_ms, media_duration_ms = _media_timeline_metadata(path)
    return (
        np.stack(
            [
                _align_samples_to_media_timeline(
                    channels[:, index], sample_rate, audio_start_ms, media_duration_ms
                )
                for index in range(channels.shape[1])
            ],
            axis=1,
        ),
        sample_rate,
    )


def _background_times(duration_ms: int, occupied: list[int]) -> list[int]:
    return [
        time_ms
        for time_ms in range(500, duration_ms, 1000)
        if all(abs(time_ms - event_ms) > CONTEXT_WINDOW_MS for event_ms in occupied)
    ][:24]


def _dataset(manifest_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    manifest = load_manifest(manifest_path)
    vectors: list[np.ndarray] = []
    labels: list[int] = []
    splits: list[str] = []
    negative_types: list[str] = []
    for video in manifest.get("videos", []):
        if not isinstance(video, dict):
            continue
        truth = video.get("labels", {})
        if not isinstance(truth, dict) or truth.get("status") != "verified":
            continue
        video_path = _resolve_video_path(video, manifest_path, manifest)
        if video_path is None:
            continue
        positives = [int(value) for value in truth.get("verified_shot_times_ms", [])]
        rejected = [item for item in truth.get("rejected_candidates", []) if isinstance(item, dict)]
        if not positives:
            continue
        channels, sample_rate = _load_channels(video_path)
        stage_noise_floor_dbfs = estimate_stage_noise_floor_dbfs(channels, sample_rate)
        split = str(video.get("dataset_split", "unassigned"))
        occupied = positives + [
            int(item["time_ms"]) for item in rejected if item.get("time_ms") is not None
        ]
        duration_ms = round((channels.shape[0] / sample_rate) * 1000.0)
        examples = [(time_ms, 1, "wearer_shot") for time_ms in positives]
        examples.extend(
            (int(item["time_ms"]), 0, str(item.get("type", "other_noise")))
            for item in rejected
            if item.get("time_ms") is not None
        )
        examples.extend(
            (time_ms, 0, "background") for time_ms in _background_times(duration_ms, occupied)
        )
        for time_ms, label, subtype in examples:
            vectors.append(
                extract_shot_context_features(
                    channels,
                    sample_rate,
                    time_ms,
                    stage_noise_floor_dbfs=stage_noise_floor_dbfs,
                ).vector()
            )
            labels.append(label)
            splits.append(split)
            negative_types.append(subtype)
    if not vectors:
        raise ValueError("No manually verified training examples were found.")
    return (
        np.stack(vectors),
        np.asarray(labels, dtype=np.float32),
        np.asarray(splits),
        negative_types,
    )


def _fit_logistic(
    features: np.ndarray, labels: np.ndarray
) -> tuple[np.ndarray, float, np.ndarray, np.ndarray]:
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    std[std < 1e-6] = 1.0
    normalized = (features - mean) / std
    weights = np.zeros(features.shape[1], dtype=np.float64)
    bias = 0.0
    for _ in range(3000):
        logits = np.clip(normalized @ weights + bias, -20.0, 20.0)
        predicted = 1.0 / (1.0 + np.exp(-logits))
        error = predicted - labels
        weights -= 0.03 * ((normalized.T @ error) / labels.size + (0.0005 * weights))
        bias -= 0.03 * float(np.mean(error))
    return weights, bias, mean, std


def _metrics(
    features: np.ndarray, labels: np.ndarray, weights: np.ndarray, bias: float
) -> dict[str, float]:
    predictions = (1.0 / (1.0 + np.exp(-np.clip(features @ weights + bias, -20, 20)))) >= 0.5
    truth = labels >= 0.5
    tp = int(np.sum(predictions & truth))
    fp = int(np.sum(predictions & ~truth))
    fn = int(np.sum(~predictions & truth))
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    return {
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round((2 * precision * recall) / max(1e-12, precision + recall), 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/shot-verifier-model.npz"))
    args = parser.parse_args()
    manifest_path = args.manifest.expanduser().resolve()
    features, labels, splits, negative_types = _dataset(manifest_path)
    train_mask = splits == "train"
    if not np.any(train_mask):
        raise SystemExit("Manifest has no verified training-split examples.")
    weights, bias, mean, std = _fit_logistic(features[train_mask], labels[train_mask])
    normalized = (features - mean) / std
    report = {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "context_window_ms": CONTEXT_WINDOW_MS,
        "feature_dimensions": int(features.shape[1]),
        "example_count": int(labels.size),
        "negative_subtypes": dict(Counter(negative_types)),
        "metrics": {
            split: _metrics(normalized[splits == split], labels[splits == split], weights, bias)
            for split in ("train", "validation", "test")
            if np.any(splits == split)
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output, weights=weights, bias=bias, mean=mean, std=std, metadata=json.dumps(report)
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
