from __future__ import annotations

import math

import numpy as np


BAND_EDGES_HZ = np.asarray([0.0, 180.0, 400.0, 800.0, 1400.0, 2200.0, 3400.0, 5200.0, 8000.0, 11025.0])
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
]


def frame_audio(samples: np.ndarray, window_size: int, hop_size: int) -> np.ndarray:
    if samples.size == 0:
        return np.zeros((0, window_size), dtype=np.float32)

    pad_left = window_size // 2
    pad_right = window_size - pad_left
    padded = np.pad(samples.astype(np.float32), (pad_left, pad_right))
    frames: list[np.ndarray] = []
    for start in range(0, max(1, padded.size - window_size + 1), hop_size):
        frame = padded[start : start + window_size]
        if frame.size < window_size:
            frame = np.pad(frame, (0, window_size - frame.size))
        frames.append(frame.astype(np.float32, copy=False))
    return np.stack(frames, axis=0)


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
    features = np.stack([extract_window_features(frame, sample_rate) for frame in frames], axis=0)
    centers_ms = frame_centers_ms(frames.shape[0], hop_size, sample_rate)
    return features.astype(np.float32), centers_ms


def extract_window_features(window: np.ndarray, sample_rate: int) -> np.ndarray:
    eps = 1e-6
    signal = window.astype(np.float32, copy=False)
    absolute = np.abs(signal)
    peak_abs = float(np.max(absolute)) + eps
    rms = float(np.sqrt(np.mean(signal**2))) + eps
    crest_factor = peak_abs / rms
    zero_crossing_rate = float(np.mean(np.abs(np.diff(np.signbit(signal).astype(np.int8)))))

    split = signal.size // 3
    attack = absolute[:split]
    sustain = absolute[split : split * 2]
    tail = absolute[split * 2 :]
    attack_ratio = float(np.mean(attack) / (np.mean(absolute) + eps))
    sustain_ratio = float(np.mean(sustain) / (np.mean(absolute) + eps))
    attack_peak = float(np.max(np.abs(np.diff(signal[: max(2, split)])))) + eps

    windowed = signal * np.hanning(signal.size)
    spectrum = np.abs(np.fft.rfft(windowed))
    power = spectrum**2 + eps
    freqs = np.fft.rfftfreq(signal.size, 1.0 / sample_rate)
    total_power = float(np.sum(power)) + eps
    weighted_freq = float(np.sum(freqs * power))
    centroid = weighted_freq / total_power
    bandwidth = math.sqrt(float(np.sum(((freqs - centroid) ** 2) * power)) / total_power)
    cumulative_power = np.cumsum(power)
    rolloff_index = int(np.searchsorted(cumulative_power, cumulative_power[-1] * 0.85))
    spectral_rolloff = float(freqs[min(rolloff_index, freqs.size - 1)])
    geometric = float(np.exp(np.mean(np.log(power))))
    arithmetic = float(np.mean(power)) + eps
    flatness = geometric / arithmetic

    band_ratios: list[float] = []
    for start_hz, end_hz in zip(BAND_EDGES_HZ[:-1], BAND_EDGES_HZ[1:]):
        mask = (freqs >= start_hz) & (freqs < end_hz)
        band_ratios.append(float(np.sum(power[mask]) / total_power))

    feature_vector = np.asarray(
        [
            math.log(rms),
            peak_abs,
            crest_factor,
            zero_crossing_rate,
            attack_ratio,
            sustain_ratio,
            math.log(attack_peak),
            centroid / (sample_rate / 2.0),
            bandwidth / (sample_rate / 2.0),
            spectral_rolloff / (sample_rate / 2.0),
            flatness,
            *band_ratios,
        ],
        dtype=np.float32,
    )
    return feature_vector
