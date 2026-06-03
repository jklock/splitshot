from __future__ import annotations

from functools import lru_cache

import numpy as np


BAND_EDGES_HZ = np.asarray(
    [0.0, 180.0, 400.0, 800.0, 1400.0, 2200.0, 3400.0, 5200.0, 8000.0, 11025.0]
)
FEATURE_NAMES = [
    "log_rms",
    "peak_abs",
    "crest_factor",
    "zero_crossing_rate",
    "attack_ratio",
    "sustain_ratio",
    "log_attack_peak",
    "spectral_centroid",
    "spectral_bandwidth",
    "spectral_rolloff",
    "spectral_flatness",
    "band_0",
    "band_1",
    "band_2",
    "band_3",
    "band_4",
    "band_5",
    "band_6",
    "band_7",
    "band_8",
]


def frame_audio(samples: np.ndarray, window_size: int, hop_size: int) -> np.ndarray:
    if samples.size == 0:
        return np.zeros((0, window_size), dtype=np.float32)

    pad_left = window_size // 2
    pad_right = window_size - pad_left
    padded = np.pad(samples.astype(np.float32, copy=False), (pad_left, pad_right))
    windows = np.lib.stride_tricks.sliding_window_view(padded, window_size)
    frames = windows[::hop_size]
    return np.ascontiguousarray(frames, dtype=np.float32)


def frame_centers_ms(frame_count: int, hop_size: int, sample_rate: int) -> np.ndarray:
    if frame_count == 0:
        return np.zeros(0, dtype=np.int32)
    centers = (np.arange(frame_count, dtype=np.float32) * hop_size) / float(sample_rate)
    return np.round(centers * 1000.0).astype(np.int32)


def extract_feature_matrix(
    samples: np.ndarray,
    sample_rate: int,
    window_size: int,
    hop_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    frames = frame_audio(samples, window_size, hop_size)
    if frames.size == 0:
        return np.zeros((0, len(FEATURE_NAMES)), dtype=np.float32), np.zeros(0, dtype=np.int32)
    features = _extract_frame_features(frames, sample_rate)
    centers_ms = frame_centers_ms(frames.shape[0], hop_size, sample_rate)
    return features.astype(np.float32), centers_ms


def extract_window_features(window: np.ndarray, sample_rate: int) -> np.ndarray:
    if window.size == 0:
        return np.zeros(len(FEATURE_NAMES), dtype=np.float32)
    return _extract_frame_features(
        np.asarray(window, dtype=np.float32).reshape(1, -1),
        sample_rate,
    )[0]


@lru_cache(maxsize=None)
def _spectral_feature_cache(
    window_size: int, sample_rate: int
) -> tuple[np.ndarray, np.ndarray, tuple[tuple[int, int], ...]]:
    hanning_window = np.hanning(window_size).astype(np.float32)
    freqs = np.fft.rfftfreq(window_size, 1.0 / sample_rate).astype(np.float32)
    band_slices: list[tuple[int, int]] = []
    for start_hz, end_hz in zip(BAND_EDGES_HZ[:-1], BAND_EDGES_HZ[1:]):
        start_index = int(np.searchsorted(freqs, start_hz, side="left"))
        end_index = int(np.searchsorted(freqs, end_hz, side="left"))
        band_slices.append((start_index, end_index))
    return hanning_window, freqs, tuple(band_slices)


def _extract_frame_features(frames: np.ndarray, sample_rate: int) -> np.ndarray:
    eps = 1e-6
    signal = np.asarray(frames, dtype=np.float32)
    if signal.ndim != 2:
        raise ValueError("Expected a 2D frame matrix")
    if signal.shape[0] == 0:
        return np.zeros((0, len(FEATURE_NAMES)), dtype=np.float32)

    absolute = np.abs(signal)
    peak_abs = np.max(absolute, axis=1) + eps
    rms = np.sqrt(np.mean(signal * signal, axis=1)) + eps
    crest_factor = peak_abs / rms
    zero_crossing_rate = np.mean(
        np.abs(np.diff(np.signbit(signal).astype(np.int8), axis=1)),
        axis=1,
    )

    split = signal.shape[1] // 3
    mean_abs = np.mean(absolute, axis=1) + eps
    if split > 0:
        attack_ratio = np.mean(absolute[:, :split], axis=1) / mean_abs
        sustain_ratio = np.mean(absolute[:, split : split * 2], axis=1) / mean_abs
    else:
        attack_ratio = np.zeros(signal.shape[0], dtype=np.float32)
        sustain_ratio = np.zeros(signal.shape[0], dtype=np.float32)

    attack_width = max(2, split)
    attack_segment = signal[:, :attack_width]
    if attack_segment.shape[1] > 1:
        attack_peak = np.max(np.abs(np.diff(attack_segment, axis=1)), axis=1) + eps
    else:
        attack_peak = np.full(signal.shape[0], eps, dtype=np.float32)

    hanning_window, freqs, band_slices = _spectral_feature_cache(signal.shape[1], sample_rate)
    windowed = signal * hanning_window[np.newaxis, :]
    spectrum = np.abs(np.fft.rfft(windowed, axis=1))
    power = spectrum * spectrum + eps
    total_power = np.sum(power, axis=1) + eps
    weighted_freq = power @ freqs
    centroid = weighted_freq / total_power
    bandwidth = np.sqrt(
        np.sum(((freqs[np.newaxis, :] - centroid[:, np.newaxis]) ** 2) * power, axis=1)
        / total_power
    )
    cumulative_power = np.cumsum(power, axis=1)
    rolloff_index = np.argmax(cumulative_power >= cumulative_power[:, -1:] * 0.85, axis=1)
    spectral_rolloff = freqs[np.clip(rolloff_index, 0, freqs.size - 1)]
    geometric = np.exp(np.mean(np.log(power), axis=1))
    arithmetic = np.mean(power, axis=1) + eps
    flatness = geometric / arithmetic

    band_ratios: list[np.ndarray] = []
    for start_index, end_index in band_slices:
        if end_index <= start_index:
            band_ratios.append(np.zeros(signal.shape[0], dtype=np.float32))
            continue
        band_ratios.append(np.sum(power[:, start_index:end_index], axis=1) / total_power)

    feature_matrix = np.column_stack(
        [
            np.log(rms),
            peak_abs,
            crest_factor,
            zero_crossing_rate,
            attack_ratio,
            sustain_ratio,
            np.log(attack_peak),
            centroid / (sample_rate / 2.0),
            bandwidth / (sample_rate / 2.0),
            spectral_rolloff / (sample_rate / 2.0),
            flatness,
            *band_ratios,
        ]
    )
    return feature_matrix.astype(np.float32, copy=False)
