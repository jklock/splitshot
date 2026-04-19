from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
import re
from statistics import fmean, median
from tempfile import TemporaryDirectory

import numpy as np

from splitshot.analysis.detection import (
    DetectionResult,
    ThresholdDetectionResult,
    _align_samples_to_media_timeline,
    _analyze_predictions,
    _detect_shots_from_predictions,
    _fallback_beep_from_heuristic,
    _fallback_beep_from_model,
    _media_timeline_metadata,
    _ms_to_sample,
    _predict_audio_events,
    _refine_shot_times,
    _refine_beep_time,
    _rms_series,
)
from splitshot.analysis.ml_runtime import ModelPredictions, pick_event_peaks
from splitshot.domain.models import ShotEvent, ShotSource
from splitshot.media.audio import extract_audio_wav, read_wav_mono, waveform_envelope


DEFAULT_THRESHOLD_GRID = (0.25, 0.35, 0.45, 0.55, 0.65)
VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4"}
BEEP_FAMILY_LOW_RANGE_HZ = (1300.0, 1800.0)
BEEP_FAMILY_HIGH_RANGE_HZ = (2600.0, 3400.0)


@dataclass(frozen=True, slots=True)
class ThresholdConsistencySummary:
    thresholds: list[float]
    shot_counts: list[int]
    beep_times_ms: list[int | None]
    shot_count_span: int
    beep_time_span_ms: int | None
    stable_shot_count: bool
    stable_beep_time: bool


@dataclass(frozen=True, slots=True)
class AcousticFingerprintSummary:
    beep_peak_hz: float | None
    beep_centroid_hz: float | None
    shot_peak_hz: float | None
    shot_centroid_hz: float | None
    shot_high_frequency_ratio: float | None
    overall_clip_ratio: float
    shot_clip_ratio: float | None
    beep_family: str
    possible_lowpass: bool
    possible_clipping: bool


@dataclass(frozen=True, slots=True)
class BeepMultipassSummary:
    final_beep_time_ms: int | None
    tone_beep_time_ms: int | None
    model_beep_time_ms: int | None
    tone_model_gap_ms: int | None
    final_tone_gap_ms: int | None
    final_model_gap_ms: int | None
    passes_agree: bool
    review_required: bool


@dataclass(frozen=True, slots=True)
class ShotMultipassSummary:
    final_shot_count: int
    onset_shot_count: int
    matched_shots: int
    unmatched_final_count: int
    unmatched_onset_count: int
    echo_like_onset_count: int
    median_match_gap_ms: float | None
    max_match_gap_ms: int | None
    passes_agree: bool
    review_required: bool


@dataclass(frozen=True, slots=True)
class DuplicateGroupSummary:
    group_key: str
    members: list[str]
    shot_counts: list[int]
    shot_count_span: int
    beep_families: list[str]
    consistent_shot_count: bool
    consistent_beep_family: bool
    review_required: bool


@dataclass(frozen=True, slots=True)
class CorpusVideoSummary:
    path: str
    duration_seconds: float
    reference_threshold: float
    reference_shot_count: int
    reference_beep_time_ms: int | None
    shot_median_confidence: float | None
    shot_mean_confidence: float | None
    shot_confidence_spread: float | None
    consistency: ThresholdConsistencySummary
    fingerprint: AcousticFingerprintSummary
    beep_multipass: BeepMultipassSummary
    shot_multipass: ShotMultipassSummary
    duplicate_group_key: str | None
    duplicate_group_review_required: bool
    review_flags: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CorpusVideoAnalysis:
    summary: CorpusVideoSummary
    reference_detection: DetectionResult


@dataclass(frozen=True, slots=True)
class LabelReviewState:
    status: str = "needs_review"
    verified_beep_time_ms: int | None = None
    verified_shot_times_ms: list[int] = field(default_factory=list)
    auto_beep_time_ms: int | None = None
    auto_shot_times_ms: list[int] = field(default_factory=list)
    auto_label_score: float | None = None
    auto_label_method: str = ""
    auto_label_reasons: list[str] = field(default_factory=list)
    review_notes: str = ""
    timer_model: str = ""
    range_name: str = ""
    device_notes: str = ""
    environment_tags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class TrainingLabelEntry:
    path: str
    relative_path: str
    duration_seconds: float
    reference_threshold: float
    detector_beep_time_ms: int | None
    detector_shot_times_ms: list[int]
    detector_shot_confidences: list[float | None]
    detector_shot_count: int
    beep_family: str
    beep_multipass: BeepMultipassSummary
    shot_multipass: ShotMultipassSummary
    duplicate_group_key: str | None
    duplicate_group_review_required: bool
    review_flags: list[str]
    labels: LabelReviewState = field(default_factory=LabelReviewState)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def classify_beep_family(beep_peak_hz: float | None) -> str:
    if beep_peak_hz is None:
        return "unknown"
    if BEEP_FAMILY_LOW_RANGE_HZ[0] <= beep_peak_hz <= BEEP_FAMILY_LOW_RANGE_HZ[1]:
        return "timer_low"
    if BEEP_FAMILY_HIGH_RANGE_HZ[0] <= beep_peak_hz <= BEEP_FAMILY_HIGH_RANGE_HZ[1]:
        return "timer_high"
    return "other"


def list_corpus_videos(input_path: str | Path) -> list[Path]:
    root = Path(input_path).expanduser().resolve()
    if root.is_file():
        return [root]
    if not root.exists():
        raise FileNotFoundError(f"Corpus path not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Corpus path is not a directory: {root}")
    return sorted(
        [
            candidate
            for candidate in root.rglob("*")
            if candidate.is_file() and candidate.suffix.lower() in VIDEO_SUFFIXES
        ],
        key=lambda candidate: str(candidate).lower(),
    )


def _ordered_thresholds(
    thresholds: list[float] | tuple[float, ...],
    reference_threshold: float,
) -> list[float]:
    ordered: list[float] = []
    seen: set[float] = set()
    for threshold in [*thresholds, reference_threshold]:
        normalized = round(float(threshold), 4)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _load_aligned_audio(video_path: str | Path) -> tuple[np.ndarray, int, int]:
    path = Path(video_path)
    with TemporaryDirectory(prefix="splitshot-corpus-audit-") as temp_dir:
        wav_path = Path(temp_dir) / "analysis.wav"
        extract_audio_wav(path, wav_path)
        samples, sample_rate = read_wav_mono(wav_path)
    audio_start_ms, media_duration_ms = _media_timeline_metadata(path)
    aligned = _align_samples_to_media_timeline(samples, sample_rate, audio_start_ms, media_duration_ms)
    duration_ms = media_duration_ms
    if duration_ms <= 0:
        duration_ms = int(round((aligned.size / float(sample_rate)) * 1000.0))
    return aligned, sample_rate, duration_ms


def _analyze_thresholds(
    samples: np.ndarray,
    sample_rate: int,
    thresholds: list[float],
) -> list[ThresholdDetectionResult]:
    predictions = _predict_audio_events(samples, sample_rate)
    waveform = waveform_envelope(samples)
    return [
        ThresholdDetectionResult(
            threshold=threshold,
            detection=_analyze_predictions(samples, sample_rate, threshold, predictions, waveform),
        )
        for threshold in thresholds
    ]


def _beep_search_window_ms(
    samples: np.ndarray,
    sample_rate: int,
    first_shot_ms: int | None,
) -> tuple[int, int]:
    search_end_ms = int(min((samples.size / float(sample_rate)) * 1000.0, 12000))
    if first_shot_ms is not None:
        search_start_ms = max(0, first_shot_ms - 4000)
        search_end_ms = max(search_start_ms + 80, first_shot_ms - 40)
        return search_start_ms, search_end_ms
    return 0, search_end_ms


def summarize_beep_multipass(
    samples: np.ndarray,
    sample_rate: int,
    predictions: ModelPredictions,
    threshold: float,
    detection: DetectionResult,
) -> BeepMultipassSummary:
    provisional_shots = _detect_shots_from_predictions(predictions, threshold, None)
    first_shot_ms = None if not provisional_shots else provisional_shots[0].time_ms
    search_start_ms, search_end_ms = _beep_search_window_ms(samples, sample_rate, first_shot_ms)

    tone_candidate_ms = _fallback_beep_from_heuristic(
        samples,
        sample_rate,
        threshold,
        search_start_ms,
        search_end_ms,
    )
    model_candidate_ms = _fallback_beep_from_model(
        predictions,
        search_start_ms,
        search_end_ms,
    )
    tone_beep_time_ms = None
    model_beep_time_ms = None
    if tone_candidate_ms is not None:
        tone_beep_time_ms = _refine_beep_time(samples, sample_rate, tone_candidate_ms, first_shot_ms)
    if model_candidate_ms is not None:
        model_beep_time_ms = _refine_beep_time(samples, sample_rate, model_candidate_ms, first_shot_ms)

    final_beep_time_ms = detection.beep_time_ms
    tone_model_gap_ms = None
    if tone_beep_time_ms is not None and model_beep_time_ms is not None:
        tone_model_gap_ms = abs(tone_beep_time_ms - model_beep_time_ms)

    final_tone_gap_ms = None
    if final_beep_time_ms is not None and tone_beep_time_ms is not None:
        final_tone_gap_ms = abs(final_beep_time_ms - tone_beep_time_ms)

    final_model_gap_ms = None
    if final_beep_time_ms is not None and model_beep_time_ms is not None:
        final_model_gap_ms = abs(final_beep_time_ms - model_beep_time_ms)

    passes_agree = tone_model_gap_ms is not None and tone_model_gap_ms <= 120
    review_required = (
        final_beep_time_ms is None
        or tone_beep_time_ms is None
        or model_beep_time_ms is None
        or not passes_agree
        or (final_tone_gap_ms is not None and final_tone_gap_ms > 120)
        or (final_model_gap_ms is not None and final_model_gap_ms > 120)
    )
    return BeepMultipassSummary(
        final_beep_time_ms=final_beep_time_ms,
        tone_beep_time_ms=tone_beep_time_ms,
        model_beep_time_ms=model_beep_time_ms,
        tone_model_gap_ms=tone_model_gap_ms,
        final_tone_gap_ms=final_tone_gap_ms,
        final_model_gap_ms=final_model_gap_ms,
        passes_agree=passes_agree,
        review_required=review_required,
    )


def summarize_shot_multipass(
    samples: np.ndarray,
    sample_rate: int,
    threshold: float,
    detection: DetectionResult,
) -> ShotMultipassSummary:
    start_ms = 0 if detection.beep_time_ms is None else max(0, detection.beep_time_ms + 100)
    end_ms = int(round((samples.size / float(sample_rate)) * 1000.0))
    centers_ms, envelope = _rms_series(samples, sample_rate, start_ms, end_ms, window_ms=6, hop_ms=2)
    onset_shot_times_ms: list[int] = []
    if envelope.size > 2:
        previous = np.concatenate((envelope[:1], envelope[:-1]))
        onset = np.maximum(0.0, envelope - previous)
        onset_peak = float(np.max(onset)) if onset.size else 0.0
        envelope_peak = float(np.max(envelope)) if envelope.size else 0.0
        if onset_peak > 0.0 and envelope_peak > 0.0:
            normalized_onset = onset / onset_peak
            normalized_envelope = envelope / envelope_peak
            combined = normalized_onset * (0.4 + (0.6 * normalized_envelope))
            cutoff = max(0.16, min(0.45, 0.10 + (float(threshold) * 0.28)))
            peak_indices = pick_event_peaks(
                combined,
                centers_ms,
                cutoff=cutoff,
                min_spacing_ms=150,
                earliest_ms=start_ms,
                exclude_ms=[] if detection.beep_time_ms is None else [detection.beep_time_ms],
                exclude_radius_ms=90,
            )
            onset_shots = [
                ShotEvent(
                    time_ms=int(centers_ms[index]),
                    source=ShotSource.AUTO,
                    confidence=float(np.clip(combined[index], 0.0, 1.0)),
                )
                for index in peak_indices
            ]
            onset_shots = _refine_shot_times(samples, sample_rate, onset_shots)
            onset_shot_times_ms = [shot.time_ms for shot in onset_shots]

    final_shot_times_ms = [shot.time_ms for shot in detection.shots]
    matched_gaps: list[int] = []
    unmatched_final_count = 0
    unmatched_onset_times_ms: list[int] = []
    final_index = 0
    onset_index = 0
    tolerance_ms = 120
    while final_index < len(final_shot_times_ms) and onset_index < len(onset_shot_times_ms):
        final_time_ms = final_shot_times_ms[final_index]
        onset_time_ms = onset_shot_times_ms[onset_index]
        gap_ms = final_time_ms - onset_time_ms
        if abs(gap_ms) <= tolerance_ms:
            matched_gaps.append(abs(gap_ms))
            final_index += 1
            onset_index += 1
            continue
        if final_time_ms < onset_time_ms:
            unmatched_final_count += 1
            final_index += 1
            continue
        unmatched_onset_times_ms.append(onset_time_ms)
        onset_index += 1

    unmatched_final_count += len(final_shot_times_ms) - final_index
    unmatched_onset_times_ms.extend(onset_shot_times_ms[onset_index:])
    unmatched_onset_count = len(unmatched_onset_times_ms)
    echo_like_onset_count = sum(
        1
        for onset_time_ms in unmatched_onset_times_ms
        if any(abs(onset_time_ms - final_time_ms) <= 220 for final_time_ms in final_shot_times_ms)
    )
    effective_unmatched_onset_count = unmatched_onset_count - echo_like_onset_count
    median_match_gap_ms = None if not matched_gaps else float(median(matched_gaps))
    max_match_gap_ms = None if not matched_gaps else int(max(matched_gaps))
    passes_agree = (
        unmatched_final_count == 0
        and effective_unmatched_onset_count == 0
        and (max_match_gap_ms is None or max_match_gap_ms <= 90)
    )
    review_required = (
        unmatched_final_count > 0
        or effective_unmatched_onset_count > 0
        or (max_match_gap_ms is not None and max_match_gap_ms > 90)
    )
    return ShotMultipassSummary(
        final_shot_count=len(final_shot_times_ms),
        onset_shot_count=len(onset_shot_times_ms),
        matched_shots=len(matched_gaps),
        unmatched_final_count=unmatched_final_count,
        unmatched_onset_count=unmatched_onset_count,
        echo_like_onset_count=echo_like_onset_count,
        median_match_gap_ms=median_match_gap_ms,
        max_match_gap_ms=max_match_gap_ms,
        passes_agree=passes_agree,
        review_required=review_required,
    )


def duplicate_group_key(video_path: str | Path) -> str:
    stem = Path(video_path).stem.lower().strip()
    normalized = re.sub(r"\s+", " ", stem)
    parts = normalized.split(" ")
    if len(parts) > 1 and parts[-1].isdigit() and int(parts[-1]) <= 5:
        return " ".join(parts[:-1])
    return normalized


def build_duplicate_group_summaries(analyses: list[CorpusVideoAnalysis]) -> list[DuplicateGroupSummary]:
    grouped: dict[str, list[CorpusVideoAnalysis]] = {}
    for analysis in analyses:
        key = duplicate_group_key(analysis.summary.path)
        grouped.setdefault(key, []).append(analysis)

    summaries: list[DuplicateGroupSummary] = []
    for key, members in grouped.items():
        if len(members) < 2:
            continue
        ordered_members = sorted(members, key=lambda item: item.summary.path.lower())
        shot_counts = [member.summary.reference_shot_count for member in ordered_members]
        beep_families = sorted({member.summary.fingerprint.beep_family for member in ordered_members})
        shot_count_span = max(shot_counts) - min(shot_counts)
        consistent_shot_count = shot_count_span == 0
        consistent_beep_family = len(beep_families) == 1
        summaries.append(
            DuplicateGroupSummary(
                group_key=key,
                members=[member.summary.path for member in ordered_members],
                shot_counts=shot_counts,
                shot_count_span=shot_count_span,
                beep_families=beep_families,
                consistent_shot_count=consistent_shot_count,
                consistent_beep_family=consistent_beep_family,
                review_required=not consistent_shot_count,
            )
        )
    return sorted(summaries, key=lambda item: item.group_key)


def summarize_threshold_consistency(results: list[ThresholdDetectionResult]) -> ThresholdConsistencySummary:
    thresholds = [float(result.threshold) for result in results]
    shot_counts = [len(result.detection.shots) for result in results]
    beep_times_ms = [result.detection.beep_time_ms for result in results]
    shot_count_span = 0 if not shot_counts else max(shot_counts) - min(shot_counts)
    beep_values = [beep for beep in beep_times_ms if beep is not None]
    beep_time_span_ms = None if len(beep_values) < 2 else max(beep_values) - min(beep_values)
    beep_presence = {beep is not None for beep in beep_times_ms}
    stable_beep_time = len(beep_presence) <= 1 and (beep_time_span_ms is None or beep_time_span_ms <= 120)
    return ThresholdConsistencySummary(
        thresholds=thresholds,
        shot_counts=shot_counts,
        beep_times_ms=beep_times_ms,
        shot_count_span=shot_count_span,
        beep_time_span_ms=beep_time_span_ms,
        stable_shot_count=shot_count_span == 0,
        stable_beep_time=stable_beep_time,
    )


def _confidence_summary(detection: DetectionResult) -> tuple[float | None, float | None, float | None]:
    confidences = [float(shot.confidence) for shot in detection.shots if shot.confidence is not None]
    if not confidences:
        return None, None, None
    spread = 0.0
    if len(confidences) > 1:
        spread = float(np.percentile(confidences, 90) - np.percentile(confidences, 10))
    return float(median(confidences)), float(fmean(confidences)), spread


def _spectral_summary(
    samples: np.ndarray,
    sample_rate: int,
    center_ms: int,
    window_ms: int,
    band: tuple[float, float] | None = None,
) -> tuple[float, float] | None:
    start = max(0, _ms_to_sample(center_ms - (window_ms / 2.0), sample_rate))
    end = min(samples.size, _ms_to_sample(center_ms + (window_ms / 2.0), sample_rate))
    segment = samples[start:end]
    if segment.size < 64:
        return None
    windowed = segment * np.hanning(segment.size)
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(segment.size, 1.0 / sample_rate)
    if band is None:
        work_spectrum = spectrum
        work_freqs = freqs
    else:
        mask = (freqs >= band[0]) & (freqs <= band[1])
        if not np.any(mask):
            return None
        work_spectrum = spectrum[mask]
        work_freqs = freqs[mask]
    peak_index = int(np.argmax(work_spectrum))
    power = work_spectrum**2
    total_power = float(np.sum(power)) or 1e-9
    centroid = float(np.sum(work_freqs * power) / total_power)
    return float(work_freqs[peak_index]), centroid


def _band_energy_ratio(
    samples: np.ndarray,
    sample_rate: int,
    center_ms: int,
    window_ms: int,
    numerator_band: tuple[float, float],
    denominator_band: tuple[float, float],
) -> float | None:
    start = max(0, _ms_to_sample(center_ms - (window_ms / 2.0), sample_rate))
    end = min(samples.size, _ms_to_sample(center_ms + (window_ms / 2.0), sample_rate))
    segment = samples[start:end]
    if segment.size < 64:
        return None
    windowed = segment * np.hanning(segment.size)
    spectrum = np.abs(np.fft.rfft(windowed)) ** 2
    freqs = np.fft.rfftfreq(segment.size, 1.0 / sample_rate)
    numerator = float(np.sum(spectrum[(freqs >= numerator_band[0]) & (freqs <= numerator_band[1])]))
    denominator = float(np.sum(spectrum[(freqs >= denominator_band[0]) & (freqs <= denominator_band[1])]))
    if denominator <= 0.0:
        return None
    return numerator / denominator


def summarize_acoustic_fingerprint(
    samples: np.ndarray,
    sample_rate: int,
    detection: DetectionResult,
) -> AcousticFingerprintSummary:
    beep_peak_hz = None
    beep_centroid_hz = None
    if detection.beep_time_ms is not None:
        beep_summary = _spectral_summary(samples, sample_rate, detection.beep_time_ms + 20, 80, band=(1200.0, 5200.0))
        if beep_summary is not None:
            beep_peak_hz, beep_centroid_hz = beep_summary

    shot_peaks: list[float] = []
    shot_centroids: list[float] = []
    shot_clip_ratios: list[float] = []
    shot_high_frequency_ratios: list[float] = []
    for shot in detection.shots[:8]:
        shot_summary = _spectral_summary(samples, sample_rate, shot.time_ms, 35, band=(80.0, 7000.0))
        if shot_summary is not None:
            shot_peak_hz, shot_centroid_hz = shot_summary
            shot_peaks.append(shot_peak_hz)
            shot_centroids.append(shot_centroid_hz)
        clip_start = max(0, _ms_to_sample(shot.time_ms - 10, sample_rate))
        clip_end = min(samples.size, _ms_to_sample(shot.time_ms + 20, sample_rate))
        clip_segment = samples[clip_start:clip_end]
        if clip_segment.size:
            shot_clip_ratios.append(float(np.mean(np.abs(clip_segment) >= 0.98)))
        high_frequency_ratio = _band_energy_ratio(
            samples,
            sample_rate,
            shot.time_ms,
            35,
            numerator_band=(2500.0, 7000.0),
            denominator_band=(120.0, 2500.0),
        )
        if high_frequency_ratio is not None:
            shot_high_frequency_ratios.append(high_frequency_ratio)

    median_shot_peak_hz = None if not shot_peaks else float(median(shot_peaks))
    median_shot_centroid_hz = None if not shot_centroids else float(median(shot_centroids))
    median_shot_clip_ratio = None if not shot_clip_ratios else float(median(shot_clip_ratios))
    median_shot_high_frequency_ratio = None if not shot_high_frequency_ratios else float(median(shot_high_frequency_ratios))
    overall_clip_ratio = 0.0 if samples.size == 0 else float(np.mean(np.abs(samples) >= 0.98))
    possible_lowpass = bool(
        median_shot_high_frequency_ratio is not None
        and median_shot_high_frequency_ratio < 0.12
        and median_shot_centroid_hz is not None
        and median_shot_centroid_hz < 700.0
    )
    possible_clipping = overall_clip_ratio >= 0.001 or (
        median_shot_clip_ratio is not None and median_shot_clip_ratio >= 0.01
    )
    return AcousticFingerprintSummary(
        beep_peak_hz=beep_peak_hz,
        beep_centroid_hz=beep_centroid_hz,
        shot_peak_hz=median_shot_peak_hz,
        shot_centroid_hz=median_shot_centroid_hz,
        shot_high_frequency_ratio=median_shot_high_frequency_ratio,
        overall_clip_ratio=overall_clip_ratio,
        shot_clip_ratio=median_shot_clip_ratio,
        beep_family=classify_beep_family(beep_peak_hz),
        possible_lowpass=possible_lowpass,
        possible_clipping=possible_clipping,
    )


def build_review_flags(
    consistency: ThresholdConsistencySummary,
    shot_median_confidence: float | None,
    fingerprint: AcousticFingerprintSummary,
    beep_multipass: BeepMultipassSummary,
    shot_multipass: ShotMultipassSummary,
) -> list[str]:
    flags: list[str] = []
    if not consistency.stable_shot_count:
        flags.append("shot_count_instability")
    if not consistency.stable_beep_time:
        flags.append("beep_instability")
    if beep_multipass.review_required:
        flags.append("beep_multipass_disagreement")
    if shot_multipass.review_required:
        flags.append("shot_multipass_disagreement")
    if shot_median_confidence is not None and shot_median_confidence >= 0.995:
        flags.append("confidence_saturation")
    if fingerprint.possible_lowpass:
        flags.append("possible_microphone_cutoff")
    if fingerprint.possible_clipping:
        flags.append("possible_clipping")
    return flags


def analyze_corpus_video(
    video_path: str | Path,
    thresholds: list[float] | tuple[float, ...] = DEFAULT_THRESHOLD_GRID,
    reference_threshold: float = 0.35,
) -> CorpusVideoAnalysis:
    ordered_thresholds = _ordered_thresholds(thresholds, reference_threshold)
    samples, sample_rate, duration_ms = _load_aligned_audio(video_path)
    predictions = _predict_audio_events(samples, sample_rate)
    waveform = waveform_envelope(samples)
    results = [
        ThresholdDetectionResult(
            threshold=threshold,
            detection=_analyze_predictions(samples, sample_rate, threshold, predictions, waveform),
        )
        for threshold in ordered_thresholds
    ]
    selected = next(
        result for result in results if round(result.threshold, 4) == round(reference_threshold, 4)
    )
    consistency = summarize_threshold_consistency(results)
    shot_median_confidence, shot_mean_confidence, shot_confidence_spread = _confidence_summary(selected.detection)
    fingerprint = summarize_acoustic_fingerprint(samples, sample_rate, selected.detection)
    beep_multipass = summarize_beep_multipass(samples, sample_rate, predictions, selected.threshold, selected.detection)
    shot_multipass = summarize_shot_multipass(samples, sample_rate, selected.threshold, selected.detection)
    review_flags = build_review_flags(consistency, shot_median_confidence, fingerprint, beep_multipass, shot_multipass)
    return CorpusVideoAnalysis(
        summary=CorpusVideoSummary(
            path=str(Path(video_path).expanduser().resolve()),
            duration_seconds=duration_ms / 1000.0,
            reference_threshold=selected.threshold,
            reference_shot_count=len(selected.detection.shots),
            reference_beep_time_ms=selected.detection.beep_time_ms,
            shot_median_confidence=shot_median_confidence,
            shot_mean_confidence=shot_mean_confidence,
            shot_confidence_spread=shot_confidence_spread,
            consistency=consistency,
            fingerprint=fingerprint,
            beep_multipass=beep_multipass,
            shot_multipass=shot_multipass,
            duplicate_group_key=None,
            duplicate_group_review_required=False,
            review_flags=review_flags,
        ),
        reference_detection=selected.detection,
    )


def audit_corpus_video(
    video_path: str | Path,
    thresholds: list[float] | tuple[float, ...] = DEFAULT_THRESHOLD_GRID,
    reference_threshold: float = 0.35,
) -> CorpusVideoSummary:
    return analyze_corpus_video(video_path, thresholds=thresholds, reference_threshold=reference_threshold).summary


def analyze_corpus(
    input_path: str | Path,
    thresholds: list[float] | tuple[float, ...] = DEFAULT_THRESHOLD_GRID,
    reference_threshold: float = 0.35,
) -> list[CorpusVideoAnalysis]:
    analyses = [
        analyze_corpus_video(path, thresholds=thresholds, reference_threshold=reference_threshold)
        for path in list_corpus_videos(input_path)
    ]
    duplicate_groups = build_duplicate_group_summaries(analyses)
    group_state_by_path: dict[str, tuple[str, bool]] = {}
    flagged_paths: set[str] = set()
    for group in duplicate_groups:
        for path in group.members:
            group_state_by_path[path] = (group.group_key, group.review_required)
            if group.review_required:
                flagged_paths.add(path)

    updated: list[CorpusVideoAnalysis] = []
    for analysis in analyses:
        group_key, group_review_required = group_state_by_path.get(analysis.summary.path, (None, False))
        flags = list(analysis.summary.review_flags)
        if group_review_required and "duplicate_stage_inconsistency" not in flags:
            flags.append("duplicate_stage_inconsistency")
        updated_summary = replace(
            analysis.summary,
            duplicate_group_key=group_key,
            duplicate_group_review_required=group_review_required,
            review_flags=flags,
        )
        updated.append(CorpusVideoAnalysis(summary=updated_summary, reference_detection=analysis.reference_detection))
    return updated


def audit_corpus(
    input_path: str | Path,
    thresholds: list[float] | tuple[float, ...] = DEFAULT_THRESHOLD_GRID,
    reference_threshold: float = 0.35,
) -> list[CorpusVideoSummary]:
    return [
        analysis.summary
        for analysis in analyze_corpus(input_path, thresholds=thresholds, reference_threshold=reference_threshold)
    ]


def build_label_manifest(
    input_path: str | Path,
    thresholds: list[float] | tuple[float, ...] = DEFAULT_THRESHOLD_GRID,
    reference_threshold: float = 0.35,
    existing_manifest: dict[str, object] | None = None,
) -> dict[str, object]:
    root = Path(input_path).expanduser().resolve()
    analyses = analyze_corpus(root, thresholds=thresholds, reference_threshold=reference_threshold)
    duplicate_groups = build_duplicate_group_summaries(analyses)
    existing_labels_by_key: dict[tuple[str, str], dict[str, object]] = {}
    if existing_manifest is not None:
        for video in existing_manifest.get("videos", []):
            if not isinstance(video, dict):
                continue
            path = video.get("path")
            relative_path = video.get("relative_path")
            labels = video.get("labels")
            if not isinstance(labels, dict):
                continue
            if isinstance(path, str):
                existing_labels_by_key[("path", path)] = labels
            if isinstance(relative_path, str):
                existing_labels_by_key[("relative_path", relative_path)] = labels
    videos: list[dict[str, object]] = []
    for analysis in analyses:
        path = Path(analysis.summary.path)
        if root.is_dir():
            relative_path = str(path.relative_to(root))
        else:
            relative_path = path.name
        existing_labels = existing_labels_by_key.get(("path", str(path))) or existing_labels_by_key.get(("relative_path", relative_path))
        label_state = LabelReviewState()
        if existing_labels is not None:
            label_state = LabelReviewState(
                status=str(existing_labels.get("status", label_state.status)),
                verified_beep_time_ms=existing_labels.get("verified_beep_time_ms"),
                verified_shot_times_ms=list(existing_labels.get("verified_shot_times_ms", [])),
                auto_beep_time_ms=existing_labels.get("auto_beep_time_ms"),
                auto_shot_times_ms=list(existing_labels.get("auto_shot_times_ms", [])),
                auto_label_score=existing_labels.get("auto_label_score"),
                auto_label_method=str(existing_labels.get("auto_label_method", "")),
                auto_label_reasons=list(existing_labels.get("auto_label_reasons", [])),
                review_notes=str(existing_labels.get("review_notes", "")),
                timer_model=str(existing_labels.get("timer_model", "")),
                range_name=str(existing_labels.get("range_name", "")),
                device_notes=str(existing_labels.get("device_notes", "")),
                environment_tags=list(existing_labels.get("environment_tags", [])),
            )
        videos.append(
            TrainingLabelEntry(
                path=str(path),
                relative_path=relative_path,
                duration_seconds=analysis.summary.duration_seconds,
                reference_threshold=analysis.summary.reference_threshold,
                detector_beep_time_ms=analysis.reference_detection.beep_time_ms,
                detector_shot_times_ms=[shot.time_ms for shot in analysis.reference_detection.shots],
                detector_shot_confidences=[
                    None if shot.confidence is None else float(shot.confidence)
                    for shot in analysis.reference_detection.shots
                ],
                detector_shot_count=len(analysis.reference_detection.shots),
                beep_family=analysis.summary.fingerprint.beep_family,
                beep_multipass=analysis.summary.beep_multipass,
                shot_multipass=analysis.summary.shot_multipass,
                duplicate_group_key=analysis.summary.duplicate_group_key,
                duplicate_group_review_required=analysis.summary.duplicate_group_review_required,
                review_flags=list(analysis.summary.review_flags),
                labels=label_state,
            ).to_dict()
        )
    return {
        "input": str(root),
        "video_count": len(videos),
        "threshold_grid": [float(value) for value in thresholds],
        "reference_threshold": float(reference_threshold),
        "duplicate_groups": [asdict(group) for group in duplicate_groups],
        "videos": videos,
    }