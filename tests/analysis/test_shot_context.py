from __future__ import annotations

import numpy as np

from splitshot.analysis.detection import _verify_shot_sequence
from splitshot.analysis.shot_context import (
    CONTEXT_WINDOW_MS,
    MEL_BAND_COUNT,
    MEL_FRAME_COUNT,
    extract_shot_context_features,
)
from splitshot.analysis.shot_verifier_bundle import MODEL_METADATA, WEIGHTS
from splitshot.domain.models import ShotEvent


def _impulse(samples: np.ndarray, sample_rate: int, time_ms: int, *, sustained: bool) -> None:
    start = round((time_ms / 1000.0) * sample_rate)
    length = round((0.10 if sustained else 0.01) * sample_rate)
    envelope = np.linspace(1.0, 0.65 if sustained else 0.0, length, dtype=np.float32)
    samples[start : start + length, 0] += envelope


def test_context_features_include_temporal_and_channel_evidence() -> None:
    sample_rate = 22050
    channels = np.zeros((sample_rate, 2), dtype=np.float32)
    _impulse(channels, sample_rate, 500, sustained=True)
    channels[:, 1] = channels[:, 0] * 0.5

    features = extract_shot_context_features(channels, sample_rate, 500)

    assert len(features.log_mel_temporal) == MEL_BAND_COUNT * MEL_FRAME_COUNT
    assert len(features.decay_dbfs) == 6
    assert len(features.decay_slopes_db_per_ms) == 6
    assert features.peak_over_noise_db > 20
    assert features.channel_energy_delta_db > 5
    assert features.vector().shape == (121,)
    assert CONTEXT_WINDOW_MS == 640


def test_sequence_verifier_rejects_short_reflection_without_count_limit() -> None:
    sample_rate = 22050
    channels = np.zeros((sample_rate * 2, 1), dtype=np.float32)
    _impulse(channels, sample_rate, 500, sustained=True)
    _impulse(channels, sample_rate, 740, sustained=False)
    _impulse(channels, sample_rate, 1100, sustained=True)
    shots = [ShotEvent(time_ms=value, confidence=1.0) for value in (500, 740, 1100)]

    retained, scores = _verify_shot_sequence(shots, channels, sample_rate)

    assert [shot.time_ms for shot in retained] == [500, 1100]
    assert scores[500] > scores[740]


def test_anchor_is_timing_evidence_not_a_hard_cutoff() -> None:
    sample_rate = 22050
    channels = np.zeros((sample_rate * 2, 1), dtype=np.float32)
    _impulse(channels, sample_rate, 1000, sustained=True)
    _impulse(channels, sample_rate, 1250, sustained=True)
    shots = [ShotEvent(time_ms=value, confidence=1.0) for value in (1000, 1250)]

    retained, _ = _verify_shot_sequence(shots, channels, sample_rate, last_shot_anchor_ms=1000)

    assert [shot.time_ms for shot in retained] == [1000, 1250]


def test_verifier_bundle_matches_feature_schema() -> None:
    assert MODEL_METADATA["feature_schema_version"] == "shot-context-v1"
    assert MODEL_METADATA["context_window_ms"] == 640
    assert MODEL_METADATA["feature_dimensions"] == 121
    assert all(0 <= index < 121 for index in WEIGHTS)
