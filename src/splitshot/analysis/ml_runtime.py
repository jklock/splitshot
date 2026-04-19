from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from splitshot.analysis.audio_features import extract_feature_matrix
from splitshot.analysis.model_bundle import (
    CLASS_LABELS,
    FEATURE_NAMES,
    HOP_SIZE,
    MODEL_METADATA,
    STANDARDIZATION_MEAN,
    STANDARDIZATION_STD,
    W1,
    W2,
    WINDOW_SIZE,
    B1,
    B2,
)


@dataclass(slots=True)
class ModelPredictions:
    centers_ms: np.ndarray
    probabilities: np.ndarray


class AudioEventClassifier:
    def __init__(self) -> None:
        self.class_labels = tuple(CLASS_LABELS)
        self.feature_names = tuple(FEATURE_NAMES)
        self.window_size = WINDOW_SIZE
        self.hop_size = HOP_SIZE
        self.metadata = MODEL_METADATA
        self._mean = np.asarray(STANDARDIZATION_MEAN, dtype=np.float32)
        self._std = np.asarray(STANDARDIZATION_STD, dtype=np.float32)
        self._w1 = np.asarray(W1, dtype=np.float32)
        self._b1 = np.asarray(B1, dtype=np.float32)
        self._w2 = np.asarray(W2, dtype=np.float32)
        self._b2 = np.asarray(B2, dtype=np.float32)
        self._label_to_index = {label: index for index, label in enumerate(self.class_labels)}

    def predict_audio(self, samples: np.ndarray, sample_rate: int) -> ModelPredictions:
        features, centers_ms = extract_feature_matrix(samples, sample_rate, self.window_size, self.hop_size)
        probabilities = self.predict_proba(features)
        return ModelPredictions(centers_ms=centers_ms, probabilities=probabilities)

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        if features.size == 0:
            return np.zeros((0, len(self.class_labels)), dtype=np.float32)

        normalized = (features - self._mean) / self._std
        hidden = np.maximum(0.0, normalized @ self._w1 + self._b1)
        logits = hidden @ self._w2 + self._b2
        logits -= np.max(logits, axis=1, keepdims=True)
        exp = np.exp(logits)
        return exp / np.sum(exp, axis=1, keepdims=True)

    def class_scores(self, predictions: ModelPredictions, label: str) -> np.ndarray:
        index = self._label_to_index[label]
        return predictions.probabilities[:, index]

    def shot_confidence_scores(self, predictions: ModelPredictions) -> np.ndarray:
        shot_scores = self.class_scores(predictions, "shot")
        background_scores = self.class_scores(predictions, "background")
        beep_scores = self.class_scores(predictions, "beep")
        return np.clip(shot_scores - np.maximum(background_scores, beep_scores), 0.0, 1.0)


def sensitivity_to_cutoff(threshold: float, base: float, span: float) -> float:
    clamped = min(0.95, max(0.05, float(threshold)))
    return base + (clamped * span)


def pick_event_peaks(
    scores: np.ndarray,
    centers_ms: np.ndarray,
    cutoff: float,
    min_spacing_ms: int,
    earliest_ms: int | None = None,
    latest_ms: int | None = None,
    exclude_ms: list[int] | None = None,
    exclude_radius_ms: int = 0,
) -> list[int]:
    if scores.size == 0:
        return []

    exclude = exclude_ms or []
    candidates: list[int] = []
    for index in range(1, scores.size - 1):
        score = float(scores[index])
        center = int(centers_ms[index])
        if score < cutoff:
            continue
        if earliest_ms is not None and center < earliest_ms:
            continue
        if latest_ms is not None and center > latest_ms:
            continue
        if any(abs(center - value) <= exclude_radius_ms for value in exclude):
            continue
        if score >= float(scores[index - 1]) and score >= float(scores[index + 1]):
            candidates.append(index)

    candidates.sort(key=lambda item: float(scores[item]), reverse=True)
    selected: list[int] = []
    for index in candidates:
        center = int(centers_ms[index])
        if any(abs(center - int(centers_ms[chosen])) < min_spacing_ms for chosen in selected):
            continue
        selected.append(index)

    selected.sort(key=lambda item: int(centers_ms[item]))
    return selected
