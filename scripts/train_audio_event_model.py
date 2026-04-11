from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from splitshot.analysis.audio_features import FEATURE_NAMES, extract_window_features


SAMPLE_RATE = 22050
WINDOW_SIZE = 2048
HIDDEN_UNITS = 24
CLASS_LABELS = ("background", "beep", "shot")
OUTPUT_PATH = Path("src/splitshot/analysis/model_bundle.py")


def _background_window(rng: np.random.Generator) -> np.ndarray:
    t = np.arange(WINDOW_SIZE, dtype=np.float32) / SAMPLE_RATE
    signal = rng.normal(0.0, rng.uniform(0.002, 0.018), WINDOW_SIZE).astype(np.float32)

    for _ in range(int(rng.integers(1, 4))):
        frequency = float(rng.uniform(45.0, 900.0))
        phase = float(rng.uniform(0.0, math.tau))
        amplitude = float(rng.uniform(0.002, 0.03))
        signal += amplitude * np.sin((2 * math.pi * frequency * t) + phase).astype(np.float32)

    if rng.random() < 0.35:
        sweep_length = int(rng.integers(120, 480))
        start = int(rng.integers(0, max(1, WINDOW_SIZE - sweep_length)))
        sweep = rng.normal(0.0, 0.04, sweep_length).astype(np.float32) * np.hanning(sweep_length)
        signal[start : start + sweep_length] += sweep.astype(np.float32)

    return np.clip(signal, -1.0, 1.0)


def _beep_window(rng: np.random.Generator) -> np.ndarray:
    signal = _background_window(rng)
    length = int(rng.integers(int(SAMPLE_RATE * 0.05), min(WINDOW_SIZE - 8, int(SAMPLE_RATE * 0.13))))
    start = int(rng.integers(0, max(1, WINDOW_SIZE - length)))
    time = np.arange(length, dtype=np.float32) / SAMPLE_RATE
    start_frequency = float(rng.uniform(1800.0, 3400.0))
    end_frequency = start_frequency + float(rng.uniform(-250.0, 350.0))
    frequencies = np.linspace(start_frequency, end_frequency, length, dtype=np.float32)
    phase = np.cumsum((2 * math.pi * frequencies) / SAMPLE_RATE)
    envelope = np.hanning(length).astype(np.float32)
    amplitude = float(rng.uniform(0.45, 0.95))
    tone = amplitude * np.sin(phase).astype(np.float32) * envelope
    signal[start : start + length] += tone
    return np.clip(signal, -1.0, 1.0)


def _shot_window(rng: np.random.Generator) -> np.ndarray:
    signal = _background_window(rng)
    burst_length = int(rng.integers(int(SAMPLE_RATE * 0.012), int(SAMPLE_RATE * 0.035)))
    start = int(rng.integers(0, max(1, WINDOW_SIZE - burst_length - 1)))
    decay = np.exp(-np.linspace(0.0, float(rng.uniform(5.0, 10.0)), burst_length)).astype(np.float32)
    burst = rng.normal(0.0, 1.0, burst_length).astype(np.float32) * decay
    burst -= np.mean(burst)
    burst /= max(1e-6, float(np.max(np.abs(burst))))
    amplitude = float(rng.uniform(0.6, 1.0))
    signal[start : start + burst_length] += burst * amplitude

    tail_length = int(rng.integers(int(SAMPLE_RATE * 0.03), int(SAMPLE_RATE * 0.09)))
    if start + burst_length + tail_length < WINDOW_SIZE:
        tail = rng.normal(0.0, 0.4, tail_length).astype(np.float32)
        tail *= np.exp(-np.linspace(0.0, 7.0, tail_length)).astype(np.float32)
        signal[start + burst_length : start + burst_length + tail_length] += tail * amplitude * 0.18

    low_thump_length = int(rng.integers(int(SAMPLE_RATE * 0.02), int(SAMPLE_RATE * 0.05)))
    if start + low_thump_length < WINDOW_SIZE:
        time = np.arange(low_thump_length, dtype=np.float32) / SAMPLE_RATE
        thump = np.sin(2 * math.pi * float(rng.uniform(90.0, 180.0)) * time).astype(np.float32)
        thump *= np.exp(-np.linspace(0.0, 4.0, low_thump_length)).astype(np.float32)
        signal[start : start + low_thump_length] += thump * amplitude * 0.12

    return np.clip(signal, -1.0, 1.0)


def _build_dataset(rng: np.random.Generator, per_class: int = 2400) -> tuple[np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    labels: list[int] = []

    generators = [
        _background_window,
        _beep_window,
        _shot_window,
    ]
    for label_index, generator in enumerate(generators):
        for _ in range(per_class):
            features.append(extract_window_features(generator(rng), SAMPLE_RATE))
            labels.append(label_index)

    return np.stack(features, axis=0), np.asarray(labels, dtype=np.int64)


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=1, keepdims=True)


def _train_mlp(x_train: np.ndarray, y_train: np.ndarray, rng: np.random.Generator) -> dict[str, np.ndarray]:
    feature_count = x_train.shape[1]
    class_count = len(CLASS_LABELS)
    w1 = (rng.normal(0.0, math.sqrt(2.0 / feature_count), (feature_count, HIDDEN_UNITS))).astype(np.float32)
    b1 = np.zeros(HIDDEN_UNITS, dtype=np.float32)
    w2 = (rng.normal(0.0, math.sqrt(2.0 / HIDDEN_UNITS), (HIDDEN_UNITS, class_count))).astype(np.float32)
    b2 = np.zeros(class_count, dtype=np.float32)

    one_hot = np.eye(class_count, dtype=np.float32)[y_train]
    learning_rate = 0.01
    batch_size = 256
    beta1 = 0.9
    beta2 = 0.999
    epsilon = 1e-8
    moments = {
        "w1": np.zeros_like(w1),
        "b1": np.zeros_like(b1),
        "w2": np.zeros_like(w2),
        "b2": np.zeros_like(b2),
    }
    velocities = {
        "w1": np.zeros_like(w1),
        "b1": np.zeros_like(b1),
        "w2": np.zeros_like(w2),
        "b2": np.zeros_like(b2),
    }

    step = 0
    for _ in range(240):
        indices = rng.permutation(x_train.shape[0])
        for batch_start in range(0, x_train.shape[0], batch_size):
            batch_indices = indices[batch_start : batch_start + batch_size]
            batch_x = x_train[batch_indices]
            batch_y = one_hot[batch_indices]

            hidden_linear = batch_x @ w1 + b1
            hidden = np.maximum(hidden_linear, 0.0)
            logits = hidden @ w2 + b2
            probabilities = _softmax(logits)

            grad_logits = (probabilities - batch_y) / batch_x.shape[0]
            grad_w2 = hidden.T @ grad_logits
            grad_b2 = np.sum(grad_logits, axis=0)
            grad_hidden = grad_logits @ w2.T
            grad_hidden[hidden_linear <= 0.0] = 0.0
            grad_w1 = batch_x.T @ grad_hidden
            grad_b1 = np.sum(grad_hidden, axis=0)

            step += 1
            gradients = {
                "w1": grad_w1,
                "b1": grad_b1,
                "w2": grad_w2,
                "b2": grad_b2,
            }
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

    return {
        "w1": w1,
        "b1": b1,
        "w2": w2,
        "b2": b2,
    }


def _accuracy(x_values: np.ndarray, y_values: np.ndarray, model: dict[str, np.ndarray]) -> float:
    hidden = np.maximum((x_values @ model["w1"]) + model["b1"], 0.0)
    logits = hidden @ model["w2"] + model["b2"]
    predictions = np.argmax(logits, axis=1)
    return float(np.mean(predictions == y_values))


def _write_bundle(
    mean: np.ndarray,
    std: np.ndarray,
    model: dict[str, np.ndarray],
    train_accuracy: float,
    validation_accuracy: float,
) -> None:
    lines = [
        "from __future__ import annotations",
        "",
        f'MODEL_METADATA = {{"version": "audio-event-ml-v1", "sample_rate": {SAMPLE_RATE}, "train_accuracy": {train_accuracy:.6f}, "validation_accuracy": {validation_accuracy:.6f}}}',
        f"CLASS_LABELS = {list(CLASS_LABELS)!r}",
        f"FEATURE_NAMES = {list(FEATURE_NAMES)!r}",
        f"WINDOW_SIZE = {WINDOW_SIZE}",
        "HOP_SIZE = 128",
        f"STANDARDIZATION_MEAN = {mean.tolist()!r}",
        f"STANDARDIZATION_STD = {std.tolist()!r}",
        f'W1 = {model["w1"].tolist()!r}',
        f'B1 = {model["b1"].tolist()!r}',
        f'W2 = {model["w2"].tolist()!r}',
        f'B2 = {model["b2"].tolist()!r}',
        "",
    ]
    OUTPUT_PATH.write_text("\n".join(lines))


def main() -> None:
    rng = np.random.default_rng(42)
    features, labels = _build_dataset(rng)
    permutation = rng.permutation(features.shape[0])
    features = features[permutation]
    labels = labels[permutation]

    split_index = int(features.shape[0] * 0.85)
    train_features = features[:split_index]
    validation_features = features[split_index:]
    train_labels = labels[:split_index]
    validation_labels = labels[split_index:]

    mean = train_features.mean(axis=0).astype(np.float32)
    std = train_features.std(axis=0).astype(np.float32)
    std = np.where(std < 1e-5, 1.0, std)

    normalized_train = (train_features - mean) / std
    normalized_validation = (validation_features - mean) / std

    model = _train_mlp(normalized_train, train_labels, rng)
    train_accuracy = _accuracy(normalized_train, train_labels, model)
    validation_accuracy = _accuracy(normalized_validation, validation_labels, model)
    _write_bundle(mean, std, model, train_accuracy, validation_accuracy)

    print(f"train_accuracy={train_accuracy:.4f}")
    print(f"validation_accuracy={validation_accuracy:.4f}")
    print(f"wrote={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
