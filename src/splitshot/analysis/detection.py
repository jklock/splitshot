from __future__ import annotations

from dataclasses import dataclass, field
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
from splitshot.analysis.audio_features import extract_window_features
from splitshot.domain.models import ShotEvent, ShotMLSettings, ShotSource, TimingChangeProposal
from splitshot.media.audio import extract_audio_wav, read_wav_mono, waveform_envelope
from splitshot.media.ffmpeg import run_ffprobe_json
from splitshot.utils.time import seconds_to_ms


DEFAULT_SHOTML_SETTINGS = ShotMLSettings()
BEEP_ONSET_FRACTION = DEFAULT_SHOTML_SETTINGS.beep_onset_fraction
SHOT_ONSET_FRACTION = DEFAULT_SHOTML_SETTINGS.shot_onset_fraction
MIN_SHOT_INTERVAL_MS = DEFAULT_SHOTML_SETTINGS.min_shot_interval_ms
REFINEMENT_CONFIDENCE_WEIGHT = DEFAULT_SHOTML_SETTINGS.refinement_confidence_weight
WEAK_ONSET_SUPPORT_THRESHOLD = DEFAULT_SHOTML_SETTINGS.weak_onset_support_threshold
NEAR_CUTOFF_INTERVAL_MS = DEFAULT_SHOTML_SETTINGS.near_cutoff_interval_ms
SOUND_PROFILE_SEARCH_RADIUS_MS = DEFAULT_SHOTML_SETTINGS.sound_profile_search_radius_ms
SOUND_PROFILE_DISTANCE_LIMIT = DEFAULT_SHOTML_SETTINGS.sound_profile_distance_limit
SOUND_PROFILE_HIGH_CONFIDENCE_LIMIT = DEFAULT_SHOTML_SETTINGS.sound_profile_high_confidence_limit


@dataclass(slots=True)
class TimingReviewSuggestion:
    kind: str
    severity: str
    message: str
    suggested_action: str
    shot_number: int | None = None
    shot_time_ms: int | None = None
    confidence: float | None = None
    support_confidence: float | None = None
    interval_ms: int | None = None


@dataclass(slots=True)
class DetectionResult:
    beep_time_ms: int | None
    shots: list[ShotEvent]
    waveform: list[float]
    sample_rate: int
    review_suggestions: list[TimingReviewSuggestion] = field(default_factory=list)


@dataclass(slots=True)
class ThresholdDetectionResult:
    threshold: float
    detection: DetectionResult


@dataclass(slots=True)
class ShotMLRunContext:
    settings: ShotMLSettings = field(default_factory=ShotMLSettings)


@lru_cache(maxsize=1)
def _classifier() -> AudioEventClassifier:
    return AudioEventClassifier()


def _settings(settings: ShotMLSettings | None = None) -> ShotMLSettings:
    return ShotMLSettings() if settings is None else settings


def _predict_audio_events(samples: np.ndarray, sample_rate: int, settings: ShotMLSettings | None = None) -> ModelPredictions:
    active_settings = _settings(settings)
    return _classifier().predict_audio(
        samples,
        sample_rate,
        window_size=active_settings.window_size,
        hop_size=active_settings.hop_size,
    )


def _shot_detection_cutoff(threshold: float, settings: ShotMLSettings | None = None) -> float:
    active_settings = _settings(settings)
    return sensitivity_to_cutoff(
        threshold,
        base=active_settings.shot_detection_cutoff_base,
        span=active_settings.shot_detection_cutoff_span,
    )


def _nearest_probability(predictions: ModelPredictions, target_ms: int, label: str) -> float:
    if predictions.centers_ms.size == 0:
        return 0.0
    classifier = _classifier()
    label_scores = classifier.class_scores(predictions, label)
    index = int(np.searchsorted(predictions.centers_ms, target_ms))
    index = max(0, min(label_scores.size - 1, index))
    return float(label_scores[index])


def _window_from_center(samples: np.ndarray, sample_rate: int, center_ms: int, window_size: int | None = None) -> np.ndarray:
    classifier = _classifier()
    window_size = classifier.window_size if window_size is None else window_size
    center_sample = _ms_to_sample(center_ms, sample_rate)
    half_window = window_size // 2
    start = center_sample - half_window
    end = start + window_size

    if start < 0:
        window = np.pad(samples[: max(0, end)], (abs(start), 0))
    elif end > samples.size:
        window = np.pad(samples[start:], (0, end - samples.size))
    else:
        window = samples[start:end]

    if window.size < window_size:
        window = np.pad(window, (0, window_size - window.size))
    return window.astype(np.float32, copy=False)


def _best_sound_window_index(
    predictions: ModelPredictions,
    target_ms: int,
    shot_scores: np.ndarray,
    settings: ShotMLSettings | None = None,
) -> int | None:
    active_settings = _settings(settings)
    centers_ms = predictions.centers_ms
    if centers_ms.size == 0:
        return None

    search_mask = np.abs(centers_ms - target_ms) <= active_settings.sound_profile_search_radius_ms
    if not np.any(search_mask):
        index = int(np.searchsorted(centers_ms, target_ms))
        return max(0, min(shot_scores.size - 1, index))

    candidate_indices = np.flatnonzero(search_mask)
    candidate_scores = shot_scores[search_mask]
    best_local_index = int(np.argmax(candidate_scores))
    return int(candidate_indices[best_local_index])


def _shot_sound_profile_metrics(
    samples: np.ndarray,
    sample_rate: int,
    predictions: ModelPredictions,
    shots: list[ShotEvent],
    settings: ShotMLSettings | None = None,
) -> tuple[list[np.ndarray | None], list[float | None]]:
    active_settings = _settings(settings)
    if predictions.centers_ms.size == 0 or not shots:
        return [], []

    classifier = _classifier()
    shot_scores = classifier.shot_confidence_scores(predictions, active_settings.shot_confidence_source)

    feature_vectors: list[np.ndarray | None] = []
    shot_probabilities: list[float | None] = []
    for shot in shots:
        best_index = _best_sound_window_index(
            predictions,
            shot.time_ms,
            shot_scores,
            active_settings,
        )
        if best_index is None:
            feature_vectors.append(None)
            shot_probabilities.append(None)
            continue

        best_center_ms = int(predictions.centers_ms[best_index])
        window = _window_from_center(samples, sample_rate, best_center_ms)
        feature_vectors.append(extract_window_features(window, sample_rate))
        shot_probabilities.append(float(shot_scores[best_index]))

    return feature_vectors, shot_probabilities


def _sound_profile_distances(feature_vectors: list[np.ndarray | None]) -> list[float | None]:
    valid_feature_vectors = [vector for vector in feature_vectors if vector is not None]
    if len(valid_feature_vectors) < 2:
        return [None for _ in feature_vectors]

    profile = np.median(np.stack(valid_feature_vectors), axis=0)
    return [None if vector is None else float(np.linalg.norm(vector - profile)) for vector in feature_vectors]


def _sound_profile_outlier_mask(
    feature_vectors: list[np.ndarray | None],
    shot_probabilities: list[float | None],
    *,
    settings: ShotMLSettings | None = None,
    distance_limit: float | None = None,
    shot_probability_limit: float | None = None,
) -> list[bool]:
    active_settings = _settings(settings)
    distance_limit = active_settings.sound_profile_distance_limit if distance_limit is None else distance_limit
    shot_probability_limit = (
        active_settings.sound_profile_high_confidence_limit
        if shot_probability_limit is None
        else shot_probability_limit
    )
    distances = _sound_profile_distances(feature_vectors)
    return [
        distance is not None
        and shot_probability is not None
        and distance > distance_limit
        and shot_probability < shot_probability_limit
        for distance, shot_probability in zip(distances, shot_probabilities, strict=True)
    ]


def _sound_profile_review_suggestions(
    shots: list[ShotEvent],
    feature_vectors: list[np.ndarray | None],
    shot_probabilities: list[float | None],
    settings: ShotMLSettings | None = None,
) -> list[TimingReviewSuggestion]:
    active_settings = _settings(settings)
    distances = _sound_profile_distances(feature_vectors)
    suggestions: list[TimingReviewSuggestion] = []
    for index, (shot, distance, shot_probability) in enumerate(zip(shots, distances, shot_probabilities, strict=True)):
        if distance is None or shot_probability is None:
            continue
        if (
            distance <= active_settings.sound_profile_distance_limit
            or shot_probability >= active_settings.sound_profile_high_confidence_limit
        ):
            continue

        suggestions.append(
            TimingReviewSuggestion(
                kind="sound_profile_outlier",
                severity="review",
                message=(
                    f"Shot {index + 1} is a sound-profile outlier ({distance:.2f} feature distance from the stage shot profile); review it before keeping it."
                ),
                suggested_action="review_shot",
                shot_number=index + 1,
                shot_time_ms=shot.time_ms,
                confidence=float(np.clip(shot_probability, 0.0, 1.0)),
                support_confidence=float(
                    np.clip(
                        max(0.0, 1.0 - min(distance / active_settings.sound_profile_distance_limit, 1.0)),
                        0.0,
                        1.0,
                    )
                ),
            )
        )

    return suggestions


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
    settings: ShotMLSettings | None = None,
) -> int | None:
    active_settings = _settings(settings)
    if samples.size == 0:
        return None
    window = max(256, int(sample_rate * active_settings.beep_heuristic_fft_window_s))
    hop = max(64, int(sample_rate * active_settings.beep_heuristic_hop_s))
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
        band_energy = float(np.sum(spectrum[
            (freqs >= active_settings.beep_heuristic_band_min_hz)
            & (freqs <= active_settings.beep_heuristic_band_max_hz)
        ]))
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
    target = min(0.95, max(0.1, threshold)) * active_settings.beep_fallback_threshold_multiplier
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
    band_min_hz: int = 1500,
    band_max_hz: int = 5000,
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
        band = spectrum[(freqs >= band_min_hz) & (freqs <= band_max_hz)]
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
    settings: ShotMLSettings | None = None,
) -> int | None:
    active_settings = _settings(settings)
    if rough_beep_ms is None or samples.size == 0:
        return rough_beep_ms

    start_ms = max(0, rough_beep_ms - active_settings.beep_refine_pre_ms)
    end_ms = rough_beep_ms + active_settings.beep_refine_post_ms
    if first_shot_ms is not None:
        end_ms = min(
            end_ms,
            max(start_ms + 120, first_shot_ms - active_settings.beep_refine_min_gap_before_first_shot_ms),
        )

    centers, scores = _tonal_score_series(
        samples,
        sample_rate,
        start_ms,
        end_ms,
        window_ms=active_settings.beep_tonal_window_ms,
        hop_ms=active_settings.beep_tonal_hop_ms,
        band_min_hz=active_settings.beep_tonal_band_min_hz,
        band_max_hz=active_settings.beep_tonal_band_max_hz,
    )
    if scores.size == 0:
        return rough_beep_ms

    peak = float(np.max(scores))
    if peak <= 0.0:
        return rough_beep_ms

    candidates = np.where(scores >= peak * active_settings.beep_onset_fraction)[0]
    if candidates.size == 0:
        return rough_beep_ms
    return int(centers[int(candidates[0])])


def _refine_shot_times(
    samples: np.ndarray,
    sample_rate: int,
    shots: list[ShotEvent],
    settings: ShotMLSettings | None = None,
) -> list[ShotEvent]:
    active_settings = _settings(settings)
    if samples.size == 0 or not shots:
        return shots

    sorted_shots = sorted(shots, key=lambda shot: shot.time_ms)
    rough_times = [shot.time_ms for shot in sorted_shots]
    refined: list[ShotEvent] = []

    for index, shot in enumerate(sorted_shots):
        rough_time = shot.time_ms
        start_ms = max(0, rough_time - active_settings.shot_refine_pre_ms)
        end_ms = rough_time + active_settings.shot_refine_post_ms
        if index > 0:
            start_ms = max(
                start_ms,
                int((rough_times[index - 1] + rough_time) / 2) - active_settings.shot_refine_midpoint_clamp_padding_ms,
            )
        if index < len(rough_times) - 1:
            end_ms = min(
                end_ms,
                int((rough_time + rough_times[index + 1]) / 2) + active_settings.shot_refine_midpoint_clamp_padding_ms,
            )
        end_ms = max(start_ms + active_settings.shot_refine_min_search_window_ms, end_ms)

        centers, envelope = _rms_series(
            samples,
            sample_rate,
            start_ms,
            end_ms,
            window_ms=active_settings.shot_refine_rms_window_ms,
            hop_ms=active_settings.shot_refine_rms_hop_ms,
        )
        if envelope.size == 0:
            refined.append(shot)
            continue

        peak = float(np.max(envelope))
        if peak <= 0.0:
            refined.append(shot)
            continue

        candidates = np.where(envelope >= peak * active_settings.shot_onset_fraction)[0]
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


def _shot_selection_score(
    shot: ShotEvent,
    support_confidence: float | None = None,
    settings: ShotMLSettings | None = None,
) -> tuple[float, float, float, float]:
    active_settings = _settings(settings)
    confidence = 0.5 if shot.confidence is None else float(np.clip(shot.confidence, 0.0, 1.0))
    support = 0.0 if support_confidence is None else float(np.clip(support_confidence, 0.0, 1.0))
    combined = (
        (confidence * active_settings.shot_selection_confidence_weight)
        + (support * active_settings.shot_selection_support_weight)
    )
    if support_confidence is not None and support < active_settings.weak_onset_support_threshold:
        combined -= active_settings.weak_support_penalty
    return combined, support, confidence, -float(shot.time_ms)


def _filter_false_positive_shots(
    shots: list[ShotEvent],
    beep_time_ms: int | None,
    samples: np.ndarray | None = None,
    sample_rate: int | None = None,
    predictions: ModelPredictions | None = None,
    min_interval_ms: int = MIN_SHOT_INTERVAL_MS,
    settings: ShotMLSettings | None = None,
) -> list[ShotEvent]:
    active_settings = _settings(settings)
    min_interval_ms = active_settings.min_shot_interval_ms if min_interval_ms == MIN_SHOT_INTERVAL_MS else min_interval_ms
    if not shots:
        return []

    eligible = [
        shot
        for shot in sorted(shots, key=lambda item: item.time_ms)
        if beep_time_ms is None or shot.time_ms - beep_time_ms >= min_interval_ms
    ]
    if not eligible:
        return []

    support_confidences: list[float | None] | None = None
    if samples is not None and sample_rate is not None and samples.size > 0:
        support_confidences = _shot_support_confidences(samples, sample_rate, eligible, active_settings)

    filtered: list[ShotEvent] = []
    cluster: list[tuple[ShotEvent, float | None]] = [
        (eligible[0], None if support_confidences is None else support_confidences[0])
    ]
    for index, shot in enumerate(eligible[1:], start=1):
        support_confidence = None if support_confidences is None else support_confidences[index]
        if shot.time_ms - cluster[-1][0].time_ms < min_interval_ms:
            cluster.append((shot, support_confidence))
            continue
        filtered.append(max(cluster, key=lambda item: _shot_selection_score(item[0], item[1], active_settings))[0])
        cluster = [(shot, support_confidence)]
    filtered.append(max(cluster, key=lambda item: _shot_selection_score(item[0], item[1], active_settings))[0])

    if (
        not active_settings.suppress_close_pair_duplicates
        or support_confidences is None
        or samples is None
        or sample_rate is None
        or len(filtered) <= 1
    ):
        filtered.sort(key=lambda item: item.time_ms)
        return filtered

    corrected: list[ShotEvent] = []
    filtered_support_confidences = _shot_support_confidences(samples, sample_rate, filtered, active_settings)
    for index, shot in enumerate(filtered):
        support_confidence = filtered_support_confidences[index]
        previous_support = filtered_support_confidences[index - 1] if index > 0 else None
        next_support = filtered_support_confidences[index + 1] if index < len(filtered) - 1 else None
        previous_gap_ms = shot.time_ms - filtered[index - 1].time_ms if index > 0 else None
        next_gap_ms = filtered[index + 1].time_ms - shot.time_ms if index < len(filtered) - 1 else None

        should_suppress = False
        if support_confidence is not None and support_confidence < active_settings.weak_onset_support_threshold:
            if previous_gap_ms is not None and previous_gap_ms < active_settings.near_cutoff_interval_ms:
                should_suppress = previous_support is None or previous_support >= support_confidence
            elif next_gap_ms is not None and next_gap_ms < active_settings.near_cutoff_interval_ms:
                should_suppress = next_support is not None and next_support > support_confidence

        if should_suppress:
            continue
        corrected.append(shot)

    corrected.sort(key=lambda item: item.time_ms)
    if predictions is None or not active_settings.suppress_sound_profile_outliers:
        return corrected

    sound_feature_vectors, sound_probabilities = _shot_sound_profile_metrics(
        samples,
        sample_rate,
        predictions,
        corrected,
        active_settings,
    )
    sound_outlier_mask = _sound_profile_outlier_mask(sound_feature_vectors, sound_probabilities, settings=active_settings)
    if not any(sound_outlier_mask):
        return corrected
    return [shot for shot, is_outlier in zip(corrected, sound_outlier_mask, strict=True) if not is_outlier]


def _shot_onset_support(
    samples: np.ndarray,
    sample_rate: int,
    shot_time_ms: int,
    settings: ShotMLSettings | None = None,
) -> float | None:
    active_settings = _settings(settings)
    if samples.size == 0:
        return None
    centers, envelope = _rms_series(
        samples,
        sample_rate,
        max(0, shot_time_ms - active_settings.onset_support_pre_ms),
        shot_time_ms + active_settings.onset_support_post_ms,
        window_ms=active_settings.onset_support_rms_window_ms,
        hop_ms=active_settings.onset_support_rms_hop_ms,
    )
    if envelope.size == 0:
        return None

    peak_index = int(np.argmax(envelope))
    peak = float(envelope[peak_index])
    if peak <= 0.0:
        return None
    baseline = float(np.percentile(envelope, 20))
    contrast = max(0.0, peak - baseline) / (peak + 1e-6)
    alignment_penalty = (
        min(abs(int(centers[peak_index]) - shot_time_ms) / active_settings.onset_support_alignment_penalty_divisor_ms, 1.0)
        * active_settings.onset_support_alignment_penalty_multiplier
    )
    return float(np.clip(contrast * (1.0 - alignment_penalty), 0.0, 1.0))


def _apply_refinement_confidence(
    samples: np.ndarray,
    sample_rate: int,
    shots: list[ShotEvent],
    settings: ShotMLSettings | None = None,
) -> list[ShotEvent]:
    active_settings = _settings(settings)
    if samples.size == 0 or not shots:
        return shots

    supports = [_shot_onset_support(samples, sample_rate, shot.time_ms, active_settings) for shot in shots]
    max_support = max((support for support in supports if support is not None), default=0.0)
    if max_support <= 0.0:
        return shots

    refined: list[ShotEvent] = []
    for shot, support in zip(shots, supports, strict=True):
        base_confidence = 0.5 if shot.confidence is None else float(np.clip(shot.confidence, 0.0, 1.0))
        support_confidence = base_confidence if support is None else float(np.clip(support / max_support, 0.0, 1.0))
        supported_confidence = (
            (base_confidence * (1.0 - active_settings.refinement_confidence_weight))
            + (support_confidence * active_settings.refinement_confidence_weight)
        )
        confidence = max(base_confidence, supported_confidence)
        refined.append(
            ShotEvent(
                id=shot.id,
                time_ms=shot.time_ms,
                source=shot.source,
                confidence=float(np.clip(confidence, 0.0, 1.0)),
                score=shot.score,
            )
        )
    return refined


def _shot_support_confidences(
    samples: np.ndarray,
    sample_rate: int,
    shots: list[ShotEvent],
    settings: ShotMLSettings | None = None,
) -> list[float | None]:
    active_settings = _settings(settings)
    supports = [_shot_onset_support(samples, sample_rate, shot.time_ms, active_settings) for shot in shots]
    max_support = max((support for support in supports if support is not None), default=0.0)
    if max_support <= 0.0:
        return [None for _ in shots]
    return [None if support is None else float(np.clip(support / max_support, 0.0, 1.0)) for support in supports]


def _suggest_timing_review_actions(
    samples: np.ndarray,
    sample_rate: int,
    shots: list[ShotEvent],
    settings: ShotMLSettings | None = None,
) -> list[TimingReviewSuggestion]:
    active_settings = _settings(settings)
    if not shots:
        return []

    support_confidences = _shot_support_confidences(samples, sample_rate, shots, active_settings)
    suggestions: list[TimingReviewSuggestion] = []
    for index, (shot, support_confidence) in enumerate(zip(shots, support_confidences, strict=True)):
        shot_number = index + 1
        confidence = None if shot.confidence is None else float(np.clip(shot.confidence, 0.0, 1.0))
        if support_confidence is not None and support_confidence < active_settings.weak_onset_support_threshold:
            suggestions.append(
                TimingReviewSuggestion(
                    kind="weak_onset_support",
                    severity="review",
                    message=(
                        f"Shot {shot_number} has weak local onset support; review before keeping or using it as the stage end."
                    ),
                    suggested_action="review_shot",
                    shot_number=shot_number,
                    shot_time_ms=shot.time_ms,
                    confidence=confidence,
                    support_confidence=round(float(support_confidence), 4),
                )
            )

        if index == 0:
            continue
        previous = shots[index - 1]
        interval_ms = shot.time_ms - previous.time_ms
        if active_settings.min_shot_interval_ms <= interval_ms < active_settings.near_cutoff_interval_ms:
            previous_support = support_confidences[index - 1]
            suggested_shot_number = shot_number
            suggested_time_ms = shot.time_ms
            suggested_confidence = confidence
            suggested_support = support_confidence
            if previous_support is not None and support_confidence is not None and previous_support < support_confidence:
                suggested_shot_number = shot_number - 1
                suggested_time_ms = previous.time_ms
                suggested_confidence = None if previous.confidence is None else float(np.clip(previous.confidence, 0.0, 1.0))
                suggested_support = previous_support
            suggestions.append(
                TimingReviewSuggestion(
                    kind="near_cutoff_spacing",
                    severity="review",
                    message=(
                        f"Shots {shot_number - 1} and {shot_number} are {interval_ms} ms apart, near the cutoff; review whether one is an echo or duplicate."
                    ),
                    suggested_action="review_close_pair",
                    shot_number=suggested_shot_number,
                    shot_time_ms=suggested_time_ms,
                    confidence=suggested_confidence,
                    support_confidence=None if suggested_support is None else round(float(suggested_support), 4),
                    interval_ms=interval_ms,
                )
            )
    return suggestions


def _detect_beep_from_predictions(
    samples: np.ndarray,
    predictions: ModelPredictions,
    threshold: float,
    sample_rate: int,
    first_shot_ms: int | None,
    settings: ShotMLSettings | None = None,
) -> int | None:
    active_settings = _settings(settings)
    if samples.size == 0:
        return None
    search_end_ms = int(min((samples.size / float(sample_rate)) * 1000.0, 12000))
    if first_shot_ms is not None:
        search_start_ms = max(0, first_shot_ms - active_settings.beep_search_lead_ms)
        search_end_ms = max(
            search_start_ms + active_settings.beep_fallback_min_window_ms,
            first_shot_ms - active_settings.beep_search_tail_guard_ms,
        )
    else:
        search_start_ms = 0

    window = max(512, _ms_to_sample(active_settings.beep_tonal_window_ms, sample_rate))
    hop = max(32, _ms_to_sample(active_settings.beep_tonal_hop_ms, sample_rate))
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
        band = spectrum[
            (freqs >= active_settings.beep_tonal_band_min_hz)
            & (freqs <= active_settings.beep_tonal_band_max_hz)
        ]
        if band.size == 0:
            continue
        band_sum = float(np.sum(band)) + eps
        band_ratio = band_sum / total
        peak_ratio = float(np.max(band) / ((np.mean(band)) + eps))
        flatness = float(np.exp(np.mean(np.log(band + eps))) / ((np.mean(band)) + eps))
        tonal_score = band_ratio * peak_ratio * max(0.05, 1.0 - flatness)
        center_ms = int(round(((start + (window / 2)) / sample_rate) * 1000.0))
        ml_boost = active_settings.beep_model_boost_floor + _nearest_probability(predictions, center_ms, "beep")
        scores.append(tonal_score * ml_boost)
        centers.append(center_ms)

    if not scores:
        fallback = _fallback_beep_from_heuristic(
            samples,
            sample_rate,
            threshold,
            search_start_ms,
            search_end_ms,
            active_settings,
        ) or _fallback_beep_from_model(predictions, search_start_ms, search_end_ms)
        return _refine_beep_time(samples, sample_rate, fallback, first_shot_ms, active_settings)
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
            active_settings,
        ) or _fallback_beep_from_model(predictions, search_start_ms, search_end_ms)
        return _refine_beep_time(samples, sample_rate, fallback, first_shot_ms, active_settings)
    region_cutoff = best_score * (
        active_settings.beep_region_cutoff_base
        - (min(0.95, max(0.05, threshold)) * active_settings.beep_region_cutoff_threshold_weight)
    )
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
            active_settings,
        ) or _fallback_beep_from_model(predictions, search_start_ms, search_end_ms)
        return _refine_beep_time(samples, sample_rate, fallback, first_shot_ms, active_settings)
    weighted_center = int(round(float(np.average(region_centers, weights=region_scores))))
    return _refine_beep_time(samples, sample_rate, weighted_center, first_shot_ms, active_settings)


def _detect_shots_from_predictions(
    predictions: ModelPredictions,
    threshold: float,
    beep_time_ms: int | None = None,
    settings: ShotMLSettings | None = None,
) -> list[ShotEvent]:
    active_settings = _settings(settings)
    centers_ms = predictions.centers_ms
    if centers_ms.size == 0:
        return []

    classifier = _classifier()
    shot_scores = classifier.shot_confidence_scores(predictions, active_settings.shot_confidence_source)
    cutoff = _shot_detection_cutoff(threshold, active_settings)
    earliest_ms = None if beep_time_ms is None else max(0, beep_time_ms + active_settings.min_shot_interval_ms)
    peaks = pick_event_peaks(
        shot_scores,
        centers_ms,
        cutoff=cutoff,
        min_spacing_ms=active_settings.shot_peak_min_spacing_ms,
        earliest_ms=earliest_ms,
        exclude_ms=[] if beep_time_ms is None else [beep_time_ms],
        exclude_radius_ms=active_settings.beep_exclusion_radius_ms,
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


def detect_beep(
    samples: np.ndarray,
    sample_rate: int,
    threshold: float = 0.5,
    settings: ShotMLSettings | None = None,
) -> int | None:
    active_settings = _settings(settings)
    predictions = _predict_audio_events(samples, sample_rate, active_settings)
    provisional_shots = _detect_shots_from_predictions(predictions, threshold, None, active_settings)
    first_shot_ms = None if not provisional_shots else provisional_shots[0].time_ms
    return _detect_beep_from_predictions(samples, predictions, threshold, sample_rate, first_shot_ms, active_settings)


def detect_shots(
    samples: np.ndarray,
    sample_rate: int,
    threshold: float = 0.5,
    beep_time_ms: int | None = None,
    settings: ShotMLSettings | None = None,
) -> list[ShotEvent]:
    active_settings = _settings(settings)
    predictions = _predict_audio_events(samples, sample_rate, active_settings)
    shots = _detect_shots_from_predictions(predictions, threshold, beep_time_ms, active_settings)
    shots = _refine_shot_times(samples, sample_rate, shots, active_settings)
    shots = _filter_false_positive_shots(
        shots,
        beep_time_ms,
        samples=samples,
        sample_rate=sample_rate,
        predictions=predictions,
        settings=active_settings,
    )
    return _apply_refinement_confidence(samples, sample_rate, shots, active_settings)


def _analyze_predictions(
    samples: np.ndarray,
    sample_rate: int,
    threshold: float,
    predictions: ModelPredictions,
    waveform: list[float],
    settings: ShotMLSettings | None = None,
) -> DetectionResult:
    active_settings = _settings(settings)
    provisional_shots = _detect_shots_from_predictions(predictions, threshold, None, active_settings)
    first_shot_ms = None if not provisional_shots else provisional_shots[0].time_ms
    beep_time_ms = _detect_beep_from_predictions(
        samples,
        predictions,
        threshold,
        sample_rate,
        first_shot_ms,
        active_settings,
    )
    shots = _detect_shots_from_predictions(predictions, threshold, beep_time_ms, active_settings)
    shots = _refine_shot_times(samples, sample_rate, shots, active_settings)
    sound_review_suggestions = _sound_profile_review_suggestions(
        shots,
        *_shot_sound_profile_metrics(samples, sample_rate, predictions, shots, active_settings),
        active_settings,
    )
    shots = _filter_false_positive_shots(
        shots,
        beep_time_ms,
        samples=samples,
        sample_rate=sample_rate,
        predictions=predictions,
        settings=active_settings,
    )
    shots = _apply_refinement_confidence(samples, sample_rate, shots, active_settings)
    review_suggestions = sound_review_suggestions + _suggest_timing_review_actions(samples, sample_rate, shots, active_settings)
    return DetectionResult(
        beep_time_ms=beep_time_ms,
        shots=shots,
        waveform=waveform,
        sample_rate=sample_rate,
        review_suggestions=review_suggestions,
    )


def analyze_video_audio_thresholds(
    video_path: str | Path,
    thresholds: list[float] | tuple[float, ...],
    settings: ShotMLSettings | None = None,
) -> list[ThresholdDetectionResult]:
    active_settings = _settings(settings)
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
    predictions = _predict_audio_events(samples, sample_rate, active_settings)
    waveform = waveform_envelope(samples)
    return [
        ThresholdDetectionResult(
            threshold=threshold,
            detection=_analyze_predictions(samples, sample_rate, threshold, predictions, waveform, active_settings),
        )
        for threshold in ordered_thresholds
    ]


def analyze_video_audio(
    video_path: str | Path,
    threshold: float = 0.5,
    settings: ShotMLSettings | None = None,
) -> DetectionResult:
    active_settings = _settings(settings)
    results = analyze_video_audio_thresholds(video_path, [threshold], active_settings)
    return results[0].detection


def timing_change_proposals_from_review_suggestions(
    shots: list[ShotEvent],
    beep_time_ms: int | None,
    review_suggestions: list[TimingReviewSuggestion],
) -> list[TimingChangeProposal]:
    ordered_shots = sorted(shots, key=lambda shot: shot.time_ms)
    proposals: list[TimingChangeProposal] = []
    seen_keys: set[tuple[str, str | None, int | None]] = set()

    def shot_for_number(number: int | None) -> ShotEvent | None:
        if number is None or number < 1 or number > len(ordered_shots):
            return None
        return ordered_shots[number - 1]

    for suggestion in review_suggestions:
        shot = shot_for_number(suggestion.shot_number)
        if shot is None:
            continue
        confidence = None if suggestion.confidence is None else float(np.clip(suggestion.confidence, 0.0, 1.0))
        support_confidence = (
            None
            if suggestion.support_confidence is None
            else float(np.clip(suggestion.support_confidence, 0.0, 1.0))
        )
        evidence = {
            "review_kind": suggestion.kind,
            "severity": suggestion.severity,
            "suggested_action": suggestion.suggested_action,
        }
        if suggestion.interval_ms is not None:
            evidence["interval_ms"] = suggestion.interval_ms
        if beep_time_ms is not None:
            evidence["beep_time_ms"] = beep_time_ms

        if suggestion.kind == "near_cutoff_spacing":
            survivor: ShotEvent | None = None
            if suggestion.shot_number is not None:
                neighbors = [
                    shot_for_number(suggestion.shot_number - 1),
                    shot_for_number(suggestion.shot_number + 1),
                ]
                survivor = next((candidate for candidate in neighbors if candidate is not None), None)
            key = ("choose_close_pair_survivor", shot.id, suggestion.interval_ms)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            proposals.append(
                TimingChangeProposal(
                    proposal_type="choose_close_pair_survivor",
                    shot_id=shot.id,
                    shot_number=suggestion.shot_number,
                    source_time_ms=shot.time_ms,
                    alternate_shot_id=None if survivor is None else survivor.id,
                    alternate_time_ms=None if survivor is None else survivor.time_ms,
                    confidence=confidence,
                    support_confidence=support_confidence,
                    message=suggestion.message,
                    evidence=evidence,
                )
            )
            continue

        if suggestion.kind in {"weak_onset_support", "sound_profile_outlier"}:
            key = ("suppress_shot", shot.id, None)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            proposals.append(
                TimingChangeProposal(
                    proposal_type="suppress_shot",
                    shot_id=shot.id,
                    shot_number=suggestion.shot_number,
                    source_time_ms=shot.time_ms,
                    confidence=confidence,
                    support_confidence=support_confidence,
                    message=suggestion.message,
                    evidence=evidence,
                )
            )

    return proposals
