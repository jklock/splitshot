from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from splitshot.analysis.audio_features import extract_window_features
from splitshot.analysis.corpus import _load_aligned_audio
from splitshot.analysis.model_bundle import WINDOW_SIZE


CLASS_NAMES = ("background", "beep", "shot")
CLASS_TO_INDEX = {name: index for index, name in enumerate(CLASS_NAMES)}
LABEL_STATUS_VERIFIED = "verified"
LABEL_STATUS_AUTO_LABELED = "auto_labeled"
LABEL_SOURCE_VERIFIED = "verified"
LABEL_SOURCE_AUTO_CONSENSUS = "auto_consensus"
LABEL_SOURCE_DETECTOR_DRAFT = "detector_draft"
MANIFEST_LABEL_SOURCES = (
    LABEL_SOURCE_VERIFIED,
    LABEL_SOURCE_AUTO_CONSENSUS,
    LABEL_SOURCE_DETECTOR_DRAFT,
)
DETECTOR_DRAFT_POLICIES = ("review-clean", "all")
BLOCKING_REVIEW_FLAGS_FOR_DETECTOR_DRAFTS = frozenset(
    {
        "shot_count_instability",
        "shot_multipass_disagreement",
        "duplicate_stage_inconsistency",
        "possible_clipping",
    }
)


@dataclass(frozen=True, slots=True)
class DatasetExtractionConfig:
    use_detector_drafts: bool = False
    include_statuses: tuple[str, ...] = ("verified",)
    background_step_ms: int = 500
    background_limit_per_video: int = 24
    exclusion_radius_ms: int = 140
    augment_replicas_per_event: int = 0
    seed: int = 42
    detector_draft_policy: str = "review-clean"


@dataclass(frozen=True, slots=True)
class DatasetSummary:
    manifest_path: str
    video_count: int
    included_video_count: int
    skipped_video_count: int
    class_counts: dict[str, int]
    class_counts_by_label_source: dict[str, dict[str, int]]
    label_source_counts: dict[str, int]
    included_video_counts_by_label_source: dict[str, int]
    skipped_video_reasons: dict[str, int]
    feature_count: int
    clean_sample_count: int
    augmented_sample_count: int
    use_detector_drafts: bool
    augment_replicas_per_event: int
    detector_draft_policy: str

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_path": self.manifest_path,
            "video_count": self.video_count,
            "included_video_count": self.included_video_count,
            "skipped_video_count": self.skipped_video_count,
            "class_counts": dict(self.class_counts),
            "class_counts_by_label_source": {
                label_source: dict(class_counts)
                for label_source, class_counts in self.class_counts_by_label_source.items()
            },
            "label_source_counts": dict(self.label_source_counts),
            "included_video_counts_by_label_source": dict(self.included_video_counts_by_label_source),
            "skipped_video_reasons": dict(self.skipped_video_reasons),
            "feature_count": self.feature_count,
            "clean_sample_count": self.clean_sample_count,
            "augmented_sample_count": self.augmented_sample_count,
            "use_detector_drafts": self.use_detector_drafts,
            "augment_replicas_per_event": self.augment_replicas_per_event,
            "detector_draft_policy": self.detector_draft_policy,
        }


def load_manifest(manifest_path: str | Path) -> dict[str, object]:
    path = Path(manifest_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest must contain a JSON object: {path}")
    return payload


def _extract_window(samples: np.ndarray, sample_rate: int, center_ms: int) -> np.ndarray:
    center_sample = int(round((center_ms / 1000.0) * sample_rate))
    half_window = WINDOW_SIZE // 2
    start = center_sample - half_window
    end = start + WINDOW_SIZE
    if start < 0:
        window = np.pad(samples[: max(0, end)], (abs(start), 0))
    elif end > samples.size:
        window = np.pad(samples[start:], (0, end - samples.size))
    else:
        window = samples[start:end]
    if window.size != WINDOW_SIZE:
        window = np.pad(window, (0, max(0, WINDOW_SIZE - window.size)))
    return window.astype(np.float32, copy=False)


def _fft_filter_window(
    window: np.ndarray,
    sample_rate: int,
    lowpass_hz: float | None = None,
    highpass_hz: float | None = None,
) -> np.ndarray:
    spectrum = np.fft.rfft(window)
    freqs = np.fft.rfftfreq(window.size, 1.0 / sample_rate)
    mask = np.ones(freqs.shape, dtype=bool)
    if lowpass_hz is not None:
        mask &= freqs <= lowpass_hz
    if highpass_hz is not None:
        mask &= freqs >= highpass_hz
    filtered = np.fft.irfft(spectrum * mask, n=window.size)
    return filtered.astype(np.float32, copy=False)


def _augment_window(
    window: np.ndarray,
    sample_rate: int,
    label_name: str,
    rng: np.random.Generator,
) -> np.ndarray:
    augmented = window.astype(np.float32, copy=True)
    gain_db = float(rng.uniform(-6.0, 6.0))
    augmented *= float(10.0 ** (gain_db / 20.0))

    noise_std = float(rng.uniform(0.0015, 0.015))
    augmented += rng.normal(0.0, noise_std, size=augmented.shape).astype(np.float32)

    if label_name in {"beep", "shot"} and rng.random() < 0.7:
        lowpass_hz = float(rng.uniform(1800.0, 6500.0))
        augmented = _fft_filter_window(augmented, sample_rate, lowpass_hz=lowpass_hz)

    if label_name == "shot" and rng.random() < 0.35:
        highpass_hz = float(rng.uniform(80.0, 240.0))
        augmented = _fft_filter_window(augmented, sample_rate, highpass_hz=highpass_hz)

    if rng.random() < 0.3:
        clip_limit = float(rng.uniform(0.45, 0.9))
        augmented = np.clip(augmented, -clip_limit, clip_limit)
        augmented = augmented / max(clip_limit, 1e-6)

    return np.clip(augmented, -1.0, 1.0).astype(np.float32, copy=False)


def _skip_reason(reason: str) -> tuple[None, list[int], None, str]:
    return None, [], None, reason


def _detector_draft_blockers(video: dict[str, object], policy: str) -> list[str]:
    if policy == "all":
        return []

    blockers = [
        str(flag)
        for flag in video.get("review_flags", [])
        if str(flag) in BLOCKING_REVIEW_FLAGS_FOR_DETECTOR_DRAFTS
    ]
    if bool(video.get("duplicate_group_review_required")) and "duplicate_stage_inconsistency" not in blockers:
        blockers.append("duplicate_stage_inconsistency")
    return sorted(set(blockers))


def _event_times_for_entry(
    video: dict[str, object],
    config: DatasetExtractionConfig,
) -> tuple[int | None, list[int], str | None, str]:
    labels = video.get("labels", {})
    if not isinstance(labels, dict):
        labels = {}
    status = str(labels.get("status", "needs_review"))

    if status in config.include_statuses:
        if status == LABEL_STATUS_VERIFIED:
            included_beep = labels.get("verified_beep_time_ms")
            included_shots = labels.get("verified_shot_times_ms", [])
            label_source = LABEL_SOURCE_VERIFIED
        elif status == LABEL_STATUS_AUTO_LABELED:
            included_beep = labels.get("auto_beep_time_ms")
            included_shots = labels.get("auto_shot_times_ms", [])
            label_source = LABEL_SOURCE_AUTO_CONSENSUS
        else:
            return _skip_reason("included_status_without_supported_events")

        shot_times = [int(value) for value in included_shots]
        beep_time = None if included_beep is None else int(included_beep)
        if beep_time is None and not shot_times:
            return _skip_reason("included_status_without_supported_events")
        return beep_time, shot_times, label_source, ""

    if config.use_detector_drafts:
        blockers = _detector_draft_blockers(video, config.detector_draft_policy)
        if blockers:
            return _skip_reason("detector_draft_blocked_by_review_flags")
        detector_beep = video.get("detector_beep_time_ms")
        detector_shots = video.get("detector_shot_times_ms", [])
        shot_times = [int(value) for value in detector_shots]
        beep_time = None if detector_beep is None else int(detector_beep)
        if beep_time is None and not shot_times:
            return _skip_reason("detector_draft_without_events")
        return beep_time, shot_times, LABEL_SOURCE_DETECTOR_DRAFT, ""

    return _skip_reason("status_not_included")


def _background_centers(
    duration_ms: int,
    occupied_times_ms: list[int],
    config: DatasetExtractionConfig,
) -> list[int]:
    centers: list[int] = []
    limit = max(0, config.background_limit_per_video)
    if limit == 0:
        return centers
    step = max(100, config.background_step_ms)
    start_offsets = [max(50, step // 2), step]
    seen: set[int] = set()
    for offset_ms in start_offsets:
        for center_ms in range(offset_ms, duration_ms, step):
            if center_ms in seen:
                continue
            seen.add(center_ms)
            if any(abs(center_ms - event_time_ms) <= config.exclusion_radius_ms for event_time_ms in occupied_times_ms):
                continue
            centers.append(center_ms)
            if len(centers) >= limit:
                return centers
    return centers


def extract_training_dataset(
    manifest_path: str | Path,
    config: DatasetExtractionConfig,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, DatasetSummary]:
    path = Path(manifest_path).expanduser().resolve()
    manifest = load_manifest(path)
    videos = manifest.get("videos", [])
    if not isinstance(videos, list):
        raise ValueError(f"Manifest videos must be a list: {path}")

    if config.detector_draft_policy not in DETECTOR_DRAFT_POLICIES:
        raise ValueError(
            f"Detector draft policy must be one of {DETECTOR_DRAFT_POLICIES}: {config.detector_draft_policy}"
        )

    features: list[np.ndarray] = []
    labels: list[int] = []
    source_paths: list[str] = []
    label_sources: list[str] = []
    is_augmented: list[bool] = []
    rng = np.random.default_rng(config.seed)
    class_counts = {name: 0 for name in CLASS_NAMES}
    class_counts_by_label_source = {
        label_source: {name: 0 for name in CLASS_NAMES}
        for label_source in MANIFEST_LABEL_SOURCES
    }
    label_source_counts = {label_source: 0 for label_source in MANIFEST_LABEL_SOURCES}
    included_video_counts_by_label_source = {label_source: 0 for label_source in MANIFEST_LABEL_SOURCES}
    skipped_video_reasons: dict[str, int] = {}
    included_video_count = 0
    skipped_video_count = 0

    for video in videos:
        if not isinstance(video, dict):
            skipped_video_count += 1
            skipped_video_reasons["invalid_video_entry"] = skipped_video_reasons.get("invalid_video_entry", 0) + 1
            continue
        beep_time_ms, shot_times_ms, label_source, skip_reason = _event_times_for_entry(video, config)
        if label_source is None:
            skipped_video_count += 1
            skipped_video_reasons[skip_reason] = skipped_video_reasons.get(skip_reason, 0) + 1
            continue

        video_path = Path(str(video["path"])).expanduser().resolve()
        samples, sample_rate, duration_ms = _load_aligned_audio(video_path)
        included_video_count += 1
        included_video_counts_by_label_source[label_source] += 1

        if beep_time_ms is not None:
            beep_window = _extract_window(samples, sample_rate, beep_time_ms)
            features.append(extract_window_features(beep_window, sample_rate))
            labels.append(CLASS_TO_INDEX["beep"])
            source_paths.append(str(video_path))
            label_sources.append(label_source)
            is_augmented.append(False)
            class_counts["beep"] += 1
            class_counts_by_label_source[label_source]["beep"] += 1
            label_source_counts[label_source] += 1
            for _ in range(max(0, config.augment_replicas_per_event)):
                features.append(extract_window_features(_augment_window(beep_window, sample_rate, "beep", rng), sample_rate))
                labels.append(CLASS_TO_INDEX["beep"])
                source_paths.append(str(video_path))
                label_sources.append(label_source)
                is_augmented.append(True)
                class_counts["beep"] += 1
                class_counts_by_label_source[label_source]["beep"] += 1
                label_source_counts[label_source] += 1

        for shot_time_ms in shot_times_ms:
            shot_window = _extract_window(samples, sample_rate, shot_time_ms)
            features.append(extract_window_features(shot_window, sample_rate))
            labels.append(CLASS_TO_INDEX["shot"])
            source_paths.append(str(video_path))
            label_sources.append(label_source)
            is_augmented.append(False)
            class_counts["shot"] += 1
            class_counts_by_label_source[label_source]["shot"] += 1
            label_source_counts[label_source] += 1
            for _ in range(max(0, config.augment_replicas_per_event)):
                features.append(extract_window_features(_augment_window(shot_window, sample_rate, "shot", rng), sample_rate))
                labels.append(CLASS_TO_INDEX["shot"])
                source_paths.append(str(video_path))
                label_sources.append(label_source)
                is_augmented.append(True)
                class_counts["shot"] += 1
                class_counts_by_label_source[label_source]["shot"] += 1
                label_source_counts[label_source] += 1

        occupied = list(shot_times_ms)
        if beep_time_ms is not None:
            occupied.append(beep_time_ms)
        for background_center_ms in _background_centers(duration_ms, occupied, config):
            features.append(extract_window_features(_extract_window(samples, sample_rate, background_center_ms), sample_rate))
            labels.append(CLASS_TO_INDEX["background"])
            source_paths.append(str(video_path))
            label_sources.append(label_source)
            is_augmented.append(False)
            class_counts["background"] += 1
            class_counts_by_label_source[label_source]["background"] += 1
            label_source_counts[label_source] += 1

    feature_matrix = np.zeros((0, len(extract_window_features(np.zeros(WINDOW_SIZE, dtype=np.float32), 22050))), dtype=np.float32)
    if features:
        feature_matrix = np.stack(features, axis=0).astype(np.float32)
    label_vector = np.asarray(labels, dtype=np.int64)
    source_vector = np.asarray(source_paths)
    label_source_vector = np.asarray(label_sources)
    augmented_vector = np.asarray(is_augmented, dtype=bool)
    summary = DatasetSummary(
        manifest_path=str(path),
        video_count=len(videos),
        included_video_count=included_video_count,
        skipped_video_count=skipped_video_count,
        class_counts=class_counts,
        class_counts_by_label_source=class_counts_by_label_source,
        label_source_counts=label_source_counts,
        included_video_counts_by_label_source=included_video_counts_by_label_source,
        skipped_video_reasons=skipped_video_reasons,
        feature_count=int(feature_matrix.shape[1]) if feature_matrix.ndim == 2 else 0,
        clean_sample_count=int(np.sum(~augmented_vector)) if augmented_vector.size else 0,
        augmented_sample_count=int(np.sum(augmented_vector)) if augmented_vector.size else 0,
        use_detector_drafts=config.use_detector_drafts,
        augment_replicas_per_event=config.augment_replicas_per_event,
        detector_draft_policy=config.detector_draft_policy,
    )
    return feature_matrix, label_vector, source_vector, label_source_vector, augmented_vector, summary
