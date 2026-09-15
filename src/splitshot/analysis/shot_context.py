from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CONTEXT_WINDOW_MS = 640
FEATURE_SCHEMA_VERSION = "shot-context-v1"
VERIFIER_VERSION = "wearer-shot-verifier-v1"
DECAY_BOUNDARIES_MS = (10, 25, 50, 100, 200, 320)
MEL_BAND_COUNT = 12
MEL_FRAME_COUNT = 8


@dataclass(frozen=True, slots=True)
class ShotContextFeatures:
    peak_dbfs: float
    rms_dbfs: float
    noise_floor_dbfs: float
    peak_over_noise_db: float
    rms_over_noise_db: float
    rise_time_ms: float
    transient_energy_ratio: float
    energy_entropy: float
    clipping_ratio: float
    pre_event_dbfs: float
    post_event_dbfs: float
    decay_dbfs: tuple[float, ...]
    decay_slopes_db_per_ms: tuple[float, ...]
    channel_energy_delta_db: float
    channel_correlation: float
    log_mel_temporal: tuple[float, ...]

    def vector(self) -> np.ndarray:
        return np.asarray(
            [
                self.peak_dbfs,
                self.rms_dbfs,
                self.noise_floor_dbfs,
                self.peak_over_noise_db,
                self.rms_over_noise_db,
                self.rise_time_ms,
                self.transient_energy_ratio,
                self.energy_entropy,
                self.clipping_ratio,
                self.pre_event_dbfs,
                self.post_event_dbfs,
                *self.decay_dbfs,
                *self.decay_slopes_db_per_ms,
                self.channel_energy_delta_db,
                self.channel_correlation,
                *self.log_mel_temporal,
            ],
            dtype=np.float32,
        )


def _db(value: float) -> float:
    return float(20.0 * np.log10(max(float(value), 1e-7)))


def _rms(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(values.astype(np.float64) ** 2)))


def estimate_stage_noise_floor_dbfs(channels: np.ndarray, sample_rate: int) -> float:
    source = channels.mean(axis=1) if channels.ndim == 2 else channels
    window = max(1, round(sample_rate * 0.02))
    usable = source[: (source.size // window) * window]
    if usable.size == 0:
        return -140.0
    frames = usable.reshape(-1, window)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    return _db(float(np.percentile(rms, 20)))


def _slice_ms(
    samples: np.ndarray, sample_rate: int, center_ms: int, start_ms: int, end_ms: int
) -> np.ndarray:
    start = max(0, round(((center_ms + start_ms) / 1000.0) * sample_rate))
    end = min(samples.shape[0], round(((center_ms + end_ms) / 1000.0) * sample_rate))
    return samples[start:end]


def _mel_filterbank(sample_rate: int, fft_size: int) -> np.ndarray:
    def hz_to_mel(hz: float) -> float:
        return 2595.0 * np.log10(1.0 + (hz / 700.0))

    def mel_to_hz(mel: np.ndarray) -> np.ndarray:
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    mel_points = np.linspace(hz_to_mel(60.0), hz_to_mel(sample_rate / 2.0), MEL_BAND_COUNT + 2)
    bins = np.floor((fft_size + 1) * mel_to_hz(mel_points) / sample_rate).astype(int)
    bins = np.clip(bins, 0, (fft_size // 2))
    filters = np.zeros((MEL_BAND_COUNT, (fft_size // 2) + 1), dtype=np.float32)
    for band in range(MEL_BAND_COUNT):
        left, center, right = bins[band : band + 3]
        if center <= left:
            center = min(left + 1, filters.shape[1] - 1)
        if right <= center:
            right = min(center + 1, filters.shape[1])
        for index in range(left, center):
            filters[band, index] = (index - left) / max(1, center - left)
        for index in range(center, right):
            filters[band, index] = (right - index) / max(1, right - center)
    return filters


def _log_mel_temporal(context: np.ndarray, sample_rate: int) -> tuple[float, ...]:
    mono = context.mean(axis=1) if context.ndim == 2 else context
    frames = np.array_split(mono, MEL_FRAME_COUNT)
    fft_size = 1
    longest = max((frame.size for frame in frames), default=1)
    while fft_size < longest:
        fft_size *= 2
    fft_size = max(64, fft_size)
    filters = _mel_filterbank(sample_rate, fft_size)
    values: list[float] = []
    for frame in frames:
        padded = np.zeros(fft_size, dtype=np.float32)
        padded[: frame.size] = frame
        power = np.abs(np.fft.rfft(padded * np.hanning(fft_size))) ** 2
        values.extend(np.log10((filters @ power) + 1e-10).tolist())
    return tuple(float(value) for value in values)


def extract_shot_context_features(
    channels: np.ndarray,
    sample_rate: int,
    center_ms: int,
    *,
    context_window_ms: int = CONTEXT_WINDOW_MS,
    stage_noise_floor_dbfs: float | None = None,
) -> ShotContextFeatures:
    source = channels.astype(np.float32, copy=False)
    if source.ndim == 1:
        source = source[:, None]
    mono = source.mean(axis=1)
    half = context_window_ms // 2
    context = _slice_ms(source, sample_rate, center_ms, -half, half)
    event = _slice_ms(mono, sample_rate, center_ms, -5, 100)
    noise = _slice_ms(mono, sample_rate, center_ms, -half, -80)
    pre = _slice_ms(mono, sample_rate, center_ms, -80, -5)
    post = _slice_ms(mono, sample_rate, center_ms, 100, 200)
    absolute = np.abs(event)
    peak = float(np.max(absolute)) if absolute.size else 0.0
    rms = _rms(event)
    noise_rms = _rms(noise)
    noise_floor_dbfs = (
        _db(noise_rms) if stage_noise_floor_dbfs is None else float(stage_noise_floor_dbfs)
    )

    onset = _slice_ms(mono, sample_rate, center_ms, -20, 20)
    onset_abs = np.abs(onset)
    if onset_abs.size and float(np.max(onset_abs)) > 0.0:
        low = float(np.max(onset_abs)) * 0.1
        high = float(np.max(onset_abs)) * 0.9
        low_indices = np.flatnonzero(onset_abs >= low)
        high_indices = np.flatnonzero(onset_abs >= high)
        rise_ms = (
            0.0
            if low_indices.size == 0 or high_indices.size == 0
            else max(0.0, (int(high_indices[0]) - int(low_indices[0])) * 1000.0 / sample_rate)
        )
    else:
        rise_ms = 0.0

    entropy_frames = np.array_split(np.square(event.astype(np.float64)), 16)
    energies = np.asarray([float(np.sum(frame)) for frame in entropy_frames]) + 1e-12
    probabilities = energies / float(np.sum(energies))
    entropy = float(-np.sum(probabilities * np.log2(probabilities)) / np.log2(len(energies)))
    first_10 = _slice_ms(mono, sample_rate, center_ms, 0, 10)
    transient_ratio = float(_rms(first_10) / max(rms, 1e-7))
    decay = tuple(
        _db(_rms(_slice_ms(mono, sample_rate, center_ms, start, end)))
        for start, end in zip((0, *DECAY_BOUNDARIES_MS[:-1]), DECAY_BOUNDARIES_MS, strict=True)
    )
    decay_slopes: list[float] = []
    for start, end in zip((0, *DECAY_BOUNDARIES_MS[:-1]), DECAY_BOUNDARIES_MS, strict=True):
        midpoint = (start + end) // 2
        first_db = _db(_rms(_slice_ms(mono, sample_rate, center_ms, start, midpoint)))
        second_db = _db(_rms(_slice_ms(mono, sample_rate, center_ms, midpoint, end)))
        decay_slopes.append((second_db - first_db) / max(1.0, end - midpoint))

    channel_delta = 0.0
    correlation = 1.0
    if context.ndim == 2 and context.shape[1] > 1 and context.shape[0] > 1:
        channel_rms = [_rms(context[:, index]) for index in range(context.shape[1])]
        channel_delta = _db(max(channel_rms)) - _db(min(channel_rms))
        left = context[:, 0]
        right = context[:, 1]
        if float(np.std(left)) > 1e-7 and float(np.std(right)) > 1e-7:
            correlation = float(np.clip(np.corrcoef(left, right)[0, 1], -1.0, 1.0))

    return ShotContextFeatures(
        peak_dbfs=_db(peak),
        rms_dbfs=_db(rms),
        noise_floor_dbfs=noise_floor_dbfs,
        peak_over_noise_db=_db(peak) - noise_floor_dbfs,
        rms_over_noise_db=_db(rms) - noise_floor_dbfs,
        rise_time_ms=rise_ms,
        transient_energy_ratio=transient_ratio,
        energy_entropy=entropy,
        clipping_ratio=float(np.mean(np.abs(event) >= 0.995)) if event.size else 0.0,
        pre_event_dbfs=_db(_rms(pre)),
        post_event_dbfs=_db(_rms(post)),
        decay_dbfs=decay,
        decay_slopes_db_per_ms=tuple(decay_slopes),
        channel_energy_delta_db=channel_delta,
        channel_correlation=correlation,
        log_mel_temporal=_log_mel_temporal(context, sample_rate),
    )
