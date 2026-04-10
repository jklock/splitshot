from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from splitshot.domain.models import ShotEvent, ShotSource
from splitshot.media.audio import extract_audio_wav, read_wav_mono, waveform_envelope
from splitshot.utils.time import clamp, seconds_to_ms


@dataclass(slots=True)
class DetectionResult:
    beep_time_ms: int | None
    shots: list[ShotEvent]
    waveform: list[float]
    sample_rate: int


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return values
    kernel = np.ones(window, dtype=np.float32) / float(window)
    return np.convolve(values, kernel, mode="same")


def detect_beep(samples: np.ndarray, sample_rate: int, threshold: float = 0.5) -> int | None:
    if samples.size == 0:
        return None

    window = max(256, int(sample_rate * 0.02))
    hop = max(64, int(sample_rate * 0.005))
    limit = min(samples.size, sample_rate * 8)

    scores: list[float] = []
    times: list[int] = []
    previous_energy = 0.0

    for start in range(0, max(1, limit - window), hop):
        segment = samples[start : start + window]
        if segment.size < window:
            break
        windowed = segment * np.hanning(window)
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(window, 1.0 / sample_rate)
        total_energy = float(np.sum(spectrum)) + 1e-6
        band_energy = float(np.sum(spectrum[(freqs >= 1800) & (freqs <= 4200)]))
        energy = float(np.mean(np.abs(segment)))
        onset = max(0.0, energy - previous_energy)
        score = (band_energy / total_energy) * (energy + onset)
        scores.append(score)
        times.append(start)
        previous_energy = energy

    if not scores:
        return None

    score_array = np.asarray(scores, dtype=np.float32)
    peak = float(score_array.max())
    if peak <= 0:
        return None

    normalized = score_array / peak
    target = clamp(threshold, 0.1, 0.95) * 0.8
    candidates = np.where(normalized >= target)[0]
    if candidates.size == 0:
        candidates = np.asarray([int(np.argmax(score_array))])
    index = int(candidates[0])
    return seconds_to_ms(times[index] / sample_rate)


def detect_shots(
    samples: np.ndarray,
    sample_rate: int,
    threshold: float = 0.5,
    beep_time_ms: int | None = None,
) -> list[ShotEvent]:
    if samples.size == 0:
        return []

    envelope = _moving_average(np.abs(samples), max(16, int(sample_rate * 0.0015)))
    emphasis = np.maximum(0.0, envelope - _moving_average(envelope, max(128, int(sample_rate * 0.01))))
    local_window = max(64, int(sample_rate * 0.002))
    smoothed = _moving_average(emphasis, local_window)

    baseline = float(np.percentile(smoothed, 92))
    peak = float(np.max(smoothed))
    if peak <= 0:
        return []

    min_spacing = int(sample_rate * 0.08)
    cutoff = baseline + (peak - baseline) * clamp(threshold, 0.05, 0.95) * 0.55
    beep_sample = None if beep_time_ms is None else int(sample_rate * (beep_time_ms / 1000.0))

    shots: list[ShotEvent] = []
    index = 1
    last_peak = -min_spacing
    while index < smoothed.size - 1:
        if smoothed[index] >= cutoff and smoothed[index] >= smoothed[index - 1] and smoothed[index] >= smoothed[index + 1]:
            if index - last_peak >= min_spacing:
                if beep_sample is None or abs(index - beep_sample) > int(sample_rate * 0.06):
                    confidence = float(min(1.0, smoothed[index] / peak))
                    shots.append(
                        ShotEvent(
                            time_ms=seconds_to_ms(index / sample_rate),
                            source=ShotSource.AUTO,
                            confidence=confidence,
                        )
                    )
                    last_peak = index
                    index += min_spacing // 2
                    continue
        index += 1

    return shots


def analyze_video_audio(video_path: str | Path, threshold: float = 0.5) -> DetectionResult:
    with TemporaryDirectory(prefix="splitshot-audio-") as temp_dir:
        wav_path = Path(temp_dir) / "analysis.wav"
        extract_audio_wav(video_path, wav_path)
        samples, sample_rate = read_wav_mono(wav_path)

    beep_time_ms = detect_beep(samples, sample_rate, threshold)
    shots = detect_shots(samples, sample_rate, threshold, beep_time_ms)
    waveform = waveform_envelope(samples)
    return DetectionResult(
        beep_time_ms=beep_time_ms,
        shots=shots,
        waveform=waveform,
        sample_rate=sample_rate,
    )
