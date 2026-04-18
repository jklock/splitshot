from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from splitshot.analysis.ml_runtime import (
    AudioEventClassifier,
    ModelPredictions,
    pick_event_peaks,
    sensitivity_to_cutoff,
)
from splitshot.domain.models import ShotEvent, ShotSource
from splitshot.media.audio import extract_audio_wav, read_wav_mono, waveform_envelope
from splitshot.media.ffmpeg import run_ffprobe_json
from splitshot.utils.time import seconds_to_ms


BEEP_ONSET_FRACTION = 0.24
SHOT_ONSET_FRACTION = 0.66
MIN_SHOT_INTERVAL_MS = 100


@dataclass(slots=True)
class DetectionResult:
    beep_time_ms: int | None
    shots: list[ShotEvent]
    waveform: list[float]
    sample_rate: int


@dataclass(slots=True)
class ThresholdDetectionResult:
    threshold: float
    detection: DetectionResult


@lru_cache(maxsize=1)
def _classifier() -> AudioEventClassifier:
    return AudioEventClassifier()


def _predict_audio_events(samples: np.ndarray, sample_rate: int) -> ModelPredictions:
    return _classifier().predict_audio(samples, sample_rate)


def _shot_detection_cutoff(threshold: float) -> float:
    return sensitivity_to_cutoff(threshold, base=0.18, span=0.62)


def _nearest_probability(predictions: ModelPredictions, target_ms: int, label: str) -> float:
    if predictions.centers_ms.size == 0:
        return 0.0
    classifier = _classifier()
    label_scores = classifier.class_scores(predictions, label)
    index = int(np.searchsorted(predictions.centers_ms, target_ms))
    index = max(0, min(label_scores.size - 1, index))
    return float(label_scores[index])


def _fallback_beep_from_model(
    predictions: ModelPredictions,
    search_start_ms: int,
    search_end_ms: int,
) -> int | None:
    centers_ms = predictions.centers_ms
    if centers_ms.size == 0:
        return None
    classifier = _classifier()
    beep_scores = classifier.class_scores(predictions, "beep")
    mask = (centers_ms >= search_start_ms) & (centers_ms <= search_end_ms)
    if not np.any(mask):
        return None
    valid_indices = np.flatnonzero(mask)
    best_local = int(np.argmax(beep_scores[mask]))
    return int(centers_ms[int(valid_indices[best_local])])


def _fallback_beep_from_heuristic(
    samples: np.ndarray,
    sample_rate: int,
    threshold: float,
    search_start_ms: int,
    search_end_ms: int,
) -> int | None:
    if samples.size == 0:
        return None
    window = max(256, int(sample_rate * 0.02))
    hop = max(64, int(sample_rate * 0.005))
    start_sample = int(sample_rate * (search_start_ms / 1000.0))
    end_sample = int(sample_rate * (search_end_ms / 1000.0))
    start_sample = max(0, min(start_sample, max(0, samples.size - window)))
    end_sample = max(start_sample + window, min(end_sample, samples.size))

    heuristic_scores: list[float] = []
    heuristic_centers: list[int] = []
    previous_energy = 0.0
    for start in range(start_sample, max(start_sample + 1, end_sample - window), hop):
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
        heuristic_scores.append((band_energy / total_energy) * (energy + onset))
        heuristic_centers.append(int(round(((start + (window / 2)) / sample_rate) * 1000.0)))
        previous_energy = energy

    if not heuristic_scores:
        return None
    score_array = np.asarray(heuristic_scores, dtype=np.float32)
    peak = float(np.max(score_array))
    if peak <= 0.0:
        return None
    normalized = score_array / peak
    target = min(0.95, max(0.1, threshold)) * 0.8
    candidates = np.where(normalized >= target)[0]
    if candidates.size == 0:
        candidates = np.asarray([int(np.argmax(score_array))])
    return int(heuristic_centers[int(candidates[0])])


def _sample_to_ms(sample_index: float, sample_rate: int) -> int:
    return int(round((sample_index / float(sample_rate)) * 1000.0))


def _ms_to_sample(time_ms: int | float, sample_rate: int) -> int:
    return int(round((float(time_ms) / 1000.0) * sample_rate))


def _float_metadata_value(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _media_timeline_metadata(video_path: str | Path) -> tuple[int, int]:
    metadata = run_ffprobe_json(Path(video_path))
    streams = metadata.get("streams", [])
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})
    format_info = metadata.get("format", {})
    audio_start_ms = seconds_to_ms(_float_metadata_value(audio_stream.get("start_time"), 0.0))
    duration_seconds = _float_metadata_value(
        video_stream.get("duration") or format_info.get("duration"),
        0.0,
    )
    return audio_start_ms, seconds_to_ms(duration_seconds)


def _align_samples_to_media_timeline(
    samples: np.ndarray,
    sample_rate: int,
    audio_start_ms: int,
    media_duration_ms: int,
) -> np.ndarray:
    aligned = samples.astype(np.float32, copy=False)
    if audio_start_ms > 0:
        padding = np.zeros(_ms_to_sample(audio_start_ms, sample_rate), dtype=np.float32)
        aligned = np.concatenate((padding, aligned))
    elif audio_start_ms < 0:
        trim_samples = min(aligned.size, _ms_to_sample(abs(audio_start_ms), sample_rate))
        aligned = aligned[trim_samples:]

    if media_duration_ms > 0:
        target_samples = max(0, _ms_to_sample(media_duration_ms, sample_rate))
        if aligned.size > target_samples:
            aligned = aligned[:target_samples]
        elif aligned.size < target_samples:
            aligned = np.pad(aligned, (0, target_samples - aligned.size))

    return aligned.astype(np.float32, copy=False)


def _rms_series(
    samples: np.ndarray,
    sample_rate: int,
    start_ms: int,
    end_ms: int,
    window_ms: int = 3,
    hop_ms: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    window = max(8, _ms_to_sample(window_ms, sample_rate))
    hop = max(1, _ms_to_sample(hop_ms, sample_rate))
    start_sample = max(0, _ms_to_sample(start_ms, sample_rate))
    end_sample = min(samples.size, _ms_to_sample(end_ms, sample_rate))
    if end_sample - start_sample < window:
        return np.asarray([], dtype=np.int32), np.asarray([], dtype=np.float32)

    centers: list[int] = []
    values: list[float] = []
    for start in range(start_sample, end_sample - window + 1, hop):
        segment = samples[start : start + window]
        values.append(float(np.sqrt(np.mean(segment * segment))))
        centers.append(_sample_to_ms(start + (window / 2.0), sample_rate))
    return np.asarray(centers, dtype=np.int32), np.asarray(values, dtype=np.float32)


def _tonal_score_series(
    samples: np.ndarray,
    sample_rate: int,
    start_ms: int,
    end_ms: int,
    window_ms: int = 80,
    hop_ms: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    window = max(512, _ms_to_sample(window_ms, sample_rate))
    hop = max(1, _ms_to_sample(hop_ms, sample_rate))
    start_sample = max(0, _ms_to_sample(start_ms, sample_rate))
    end_sample = min(samples.size, _ms_to_sample(end_ms, sample_rate))
    if end_sample - start_sample < window:
        return np.asarray([], dtype=np.int32), np.asarray([], dtype=np.float32)

    centers: list[int] = []
    scores: list[float] = []
    eps = 1e-6
    for start in range(start_sample, end_sample - window + 1, hop):
        segment = samples[start : start + window]
        windowed = segment * np.hanning(window)
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(window, 1.0 / sample_rate)
        band = spectrum[(freqs >= 1500) & (freqs <= 5000)]
        if band.size == 0:
            continue
        total = float(np.sum(spectrum)) + eps
        band_ratio = (float(np.sum(band)) + eps) / total
        peak_ratio = float(np.max(band) / (np.mean(band) + eps))
        flatness = float(np.exp(np.mean(np.log(band + eps))) / (np.mean(band) + eps))
        scores.append(band_ratio * peak_ratio * max(0.05, 1.0 - flatness))
        centers.append(_sample_to_ms(start + (window / 2.0), sample_rate))
    return np.asarray(centers, dtype=np.int32), np.asarray(scores, dtype=np.float32)


def _refine_beep_time(
    samples: np.ndarray,
    sample_rate: int,
    rough_beep_ms: int | None,
    first_shot_ms: int | None,
) -> int | None:
    if rough_beep_ms is None or samples.size == 0:
        return rough_beep_ms

    start_ms = max(0, rough_beep_ms - 500)
    end_ms = rough_beep_ms + 450
    if first_shot_ms is not None:
        end_ms = min(end_ms, max(start_ms + 120, first_shot_ms - 40))

    centers, scores = _tonal_score_series(samples, sample_rate, start_ms, end_ms)
    if scores.size == 0:
        return rough_beep_ms

    peak = float(np.max(scores))
    if peak <= 0.0:
        return rough_beep_ms

    candidates = np.where(scores >= peak * BEEP_ONSET_FRACTION)[0]
    if candidates.size == 0:
        return rough_beep_ms
    return int(centers[int(candidates[0])])


def _refine_shot_times(
    samples: np.ndarray,
    sample_rate: int,
    shots: list[ShotEvent],
) -> list[ShotEvent]:
    if samples.size == 0 or not shots:
        return shots

    sorted_shots = sorted(shots, key=lambda shot: shot.time_ms)
    rough_times = [shot.time_ms for shot in sorted_shots]
    refined: list[ShotEvent] = []

    for index, shot in enumerate(sorted_shots):
        rough_time = shot.time_ms
        start_ms = max(0, rough_time - 150)
        end_ms = rough_time + 120
        if index > 0:
            start_ms = max(start_ms, int((rough_times[index - 1] + rough_time) / 2) - 70)
        if index < len(rough_times) - 1:
            end_ms = min(end_ms, int((rough_time + rough_times[index + 1]) / 2) + 70)
        end_ms = max(start_ms + 12, end_ms)

        centers, envelope = _rms_series(samples, sample_rate, start_ms, end_ms)
        if envelope.size == 0:
            refined.append(shot)
            continue

        peak = float(np.max(envelope))
        if peak <= 0.0:
            refined.append(shot)
            continue

        candidates = np.where(envelope >= peak * SHOT_ONSET_FRACTION)[0]
        refined_time = rough_time if candidates.size == 0 else int(centers[int(candidates[0])])
        refined.append(
            ShotEvent(
                id=shot.id,
                time_ms=refined_time,
                source=shot.source,
                confidence=None if shot.confidence is None else float(np.clip(shot.confidence, 0.0, 1.0)),
                score=shot.score,
            )
        )

    refined.sort(key=lambda item: item.time_ms)
    return refined


def _shot_confidence_cluster_key(shot: ShotEvent) -> tuple[float, int]:
    confidence = -1.0 if shot.confidence is None else float(shot.confidence)
    return confidence, -shot.time_ms


def _filter_false_positive_shots(
    shots: list[ShotEvent],
    beep_time_ms: int | None,
    min_interval_ms: int = MIN_SHOT_INTERVAL_MS,
) -> list[ShotEvent]:
    if not shots:
        return []

    eligible = [
        shot
        for shot in sorted(shots, key=lambda item: item.time_ms)
        if beep_time_ms is None or shot.time_ms - beep_time_ms >= min_interval_ms
    ]
    if not eligible:
        return []

    filtered: list[ShotEvent] = []
    cluster: list[ShotEvent] = [eligible[0]]
    for shot in eligible[1:]:
        if shot.time_ms - cluster[-1].time_ms < min_interval_ms:
            cluster.append(shot)
            continue
        filtered.append(max(cluster, key=_shot_confidence_cluster_key))
        cluster = [shot]
    filtered.append(max(cluster, key=_shot_confidence_cluster_key))
    filtered.sort(key=lambda item: item.time_ms)
    return filtered


def _detect_beep_from_predictions(
    samples: np.ndarray,
    predictions: ModelPredictions,
    threshold: float,
    sample_rate: int,
    first_shot_ms: int | None,
) -> int | None:
    if samples.size == 0:
        return None
    search_end_ms = int(min((samples.size / float(sample_rate)) * 1000.0, 12000))
    if first_shot_ms is not None:
        search_start_ms = max(0, first_shot_ms - 4000)
        search_end_ms = max(search_start_ms + 80, first_shot_ms - 40)
    else:
        search_start_ms = 0

    window = max(512, int(sample_rate * 0.08))
    hop = max(32, int(sample_rate * 0.005))
    start_sample = int(sample_rate * (search_start_ms / 1000.0))
    end_sample = int(sample_rate * (search_end_ms / 1000.0))

    centers: list[int] = []
    scores: list[float] = []
    eps = 1e-6
    for start in range(start_sample, max(start_sample + 1, end_sample - window), hop):
        segment = samples[start : start + window]
        if segment.size < window:
            break
        windowed = segment * np.hanning(window)
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(window, 1.0 / sample_rate)
        total = float(np.sum(spectrum)) + eps
        band = spectrum[(freqs >= 1500) & (freqs <= 5000)]
        if band.size == 0:
            continue
        band_sum = float(np.sum(band)) + eps
        band_ratio = band_sum / total
        peak_ratio = float(np.max(band) / ((np.mean(band)) + eps))
        flatness = float(np.exp(np.mean(np.log(band + eps))) / ((np.mean(band)) + eps))
        tonal_score = band_ratio * peak_ratio * max(0.05, 1.0 - flatness)
        center_ms = int(round(((start + (window / 2)) / sample_rate) * 1000.0))
        ml_boost = 0.3 + _nearest_probability(predictions, center_ms, "beep")
        scores.append(tonal_score * ml_boost)
        centers.append(center_ms)

    if not scores:
        fallback = _fallback_beep_from_heuristic(
            samples,
            sample_rate,
            threshold,
            search_start_ms,
            search_end_ms,
        ) or _fallback_beep_from_model(predictions, search_start_ms, search_end_ms)
        return _refine_beep_time(samples, sample_rate, fallback, first_shot_ms)
    score_array = np.asarray(scores, dtype=np.float32)
    best_index = int(np.argmax(score_array))
    best_score = float(score_array[best_index])
    if best_score <= 0.0:
        fallback = _fallback_beep_from_heuristic(
            samples,
            sample_rate,
            threshold,
            search_start_ms,
            search_end_ms,
        ) or _fallback_beep_from_model(predictions, search_start_ms, search_end_ms)
        return _refine_beep_time(samples, sample_rate, fallback, first_shot_ms)
    region_cutoff = best_score * (0.82 - (min(0.95, max(0.05, threshold)) * 0.1))
    left = best_index
    right = best_index
    while left > 0 and float(score_array[left - 1]) >= region_cutoff:
        left -= 1
    while right < score_array.size - 1 and float(score_array[right + 1]) >= region_cutoff:
        right += 1

    region_centers = np.asarray(centers[left : right + 1], dtype=np.float32)
    region_scores = score_array[left : right + 1]
    if float(np.sum(region_scores)) <= 0.0:
        fallback = _fallback_beep_from_heuristic(
            samples,
            sample_rate,
            threshold,
            search_start_ms,
            search_end_ms,
        ) or _fallback_beep_from_model(predictions, search_start_ms, search_end_ms)
        return _refine_beep_time(samples, sample_rate, fallback, first_shot_ms)
    weighted_center = int(round(float(np.average(region_centers, weights=region_scores))))
    return _refine_beep_time(samples, sample_rate, weighted_center, first_shot_ms)


def _detect_shots_from_predictions(
    predictions: ModelPredictions,
    threshold: float,
    beep_time_ms: int | None = None,
) -> list[ShotEvent]:
    centers_ms = predictions.centers_ms
    if centers_ms.size == 0:
        return []

    classifier = _classifier()
    shot_scores = classifier.class_scores(predictions, "shot")
    cutoff = _shot_detection_cutoff(threshold)
    earliest_ms = None if beep_time_ms is None else max(0, beep_time_ms + MIN_SHOT_INTERVAL_MS)
    peaks = pick_event_peaks(
        shot_scores,
        centers_ms,
        cutoff=cutoff,
        min_spacing_ms=200,
        earliest_ms=earliest_ms,
        exclude_ms=[] if beep_time_ms is None else [beep_time_ms],
        exclude_radius_ms=70,
    )

    shots: list[ShotEvent] = []
    for peak_index in peaks:
        confidence = float(np.clip(shot_scores[peak_index], 0.0, 1.0))
        shots.append(
            ShotEvent(
                time_ms=int(centers_ms[peak_index]),
                source=ShotSource.AUTO,
                confidence=confidence,
            )
        )
    return shots


def detect_beep(samples: np.ndarray, sample_rate: int, threshold: float = 0.5) -> int | None:
    predictions = _predict_audio_events(samples, sample_rate)
    provisional_shots = _detect_shots_from_predictions(predictions, threshold, None)
    first_shot_ms = None if not provisional_shots else provisional_shots[0].time_ms
    return _detect_beep_from_predictions(samples, predictions, threshold, sample_rate, first_shot_ms)


def detect_shots(
    samples: np.ndarray,
    sample_rate: int,
    threshold: float = 0.5,
    beep_time_ms: int | None = None,
) -> list[ShotEvent]:
    predictions = _predict_audio_events(samples, sample_rate)
    shots = _detect_shots_from_predictions(predictions, threshold, beep_time_ms)
    shots = _refine_shot_times(samples, sample_rate, shots)
    return _filter_false_positive_shots(shots, beep_time_ms)


def _analyze_predictions(
    samples: np.ndarray,
    sample_rate: int,
    threshold: float,
    predictions: ModelPredictions,
    waveform: list[float],
) -> DetectionResult:
    provisional_shots = _detect_shots_from_predictions(predictions, threshold, None)
    first_shot_ms = None if not provisional_shots else provisional_shots[0].time_ms
    beep_time_ms = _detect_beep_from_predictions(
        samples,
        predictions,
        threshold,
        sample_rate,
        first_shot_ms,
    )
    shots = _detect_shots_from_predictions(predictions, threshold, beep_time_ms)
    shots = _refine_shot_times(samples, sample_rate, shots)
    shots = _filter_false_positive_shots(shots, beep_time_ms)
    return DetectionResult(
        beep_time_ms=beep_time_ms,
        shots=shots,
        waveform=waveform,
        sample_rate=sample_rate,
    )


def analyze_video_audio_thresholds(
    video_path: str | Path,
    thresholds: list[float] | tuple[float, ...],
) -> list[ThresholdDetectionResult]:
    ordered_thresholds: list[float] = []
    seen_thresholds: set[float] = set()
    for threshold in thresholds:
        normalized = float(threshold)
        if normalized in seen_thresholds:
            continue
        seen_thresholds.add(normalized)
        ordered_thresholds.append(normalized)
    if not ordered_thresholds:
        return []

    with TemporaryDirectory(prefix="splitshot-audio-") as temp_dir:
        wav_path = Path(temp_dir) / "analysis.wav"
        extract_audio_wav(video_path, wav_path)
        samples, sample_rate = read_wav_mono(wav_path)

    audio_start_ms, media_duration_ms = _media_timeline_metadata(video_path)
    samples = _align_samples_to_media_timeline(samples, sample_rate, audio_start_ms, media_duration_ms)
    predictions = _predict_audio_events(samples, sample_rate)
    waveform = waveform_envelope(samples)
    return [
        ThresholdDetectionResult(
            threshold=threshold,
            detection=_analyze_predictions(samples, sample_rate, threshold, predictions, waveform),
        )
        for threshold in ordered_thresholds
    ]


def analyze_video_audio(video_path: str | Path, threshold: float = 0.5) -> DetectionResult:
    results = analyze_video_audio_thresholds(video_path, [threshold])
    return results[0].detection
