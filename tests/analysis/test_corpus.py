from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import splitshot.analysis.corpus as corpus_module
from splitshot.analysis.audio_features import FEATURE_NAMES, extract_window_features
from splitshot.analysis.corpus import (
    AcousticFingerprintSummary,
    BeepMultipassSummary,
    DuplicateGroupSummary,
    ShotMultipassSummary,
    ThresholdConsistencySummary,
    _dataset_splits,
    build_duplicate_group_summaries,
    build_review_flags,
    classify_beep_family,
    duplicate_group_key,
    list_corpus_videos,
    summarize_threshold_consistency,
)
from splitshot.analysis.detection import DetectionResult, ThresholdDetectionResult
from splitshot.domain.models import ShotEvent, ShotSource


def _detection_result(beep_time_ms: int | None, shot_times_ms: list[int]) -> DetectionResult:
    return DetectionResult(
        beep_time_ms=beep_time_ms,
        shots=[
            ShotEvent(time_ms=time_ms, source=ShotSource.AUTO, confidence=0.9)
            for time_ms in shot_times_ms
        ],
        waveform=[],
        sample_rate=22050,
    )


def test_feature_names_match_extracted_feature_count() -> None:
    features = extract_window_features(np.zeros(2048, dtype=np.float32), 22050)

    assert features.size == 20
    assert len(FEATURE_NAMES) == 20
    assert FEATURE_NAMES[-1] == "band_8"


def test_classify_beep_family_matches_empirical_clusters() -> None:
    assert classify_beep_family(None) == "unknown"
    assert classify_beep_family(1500.0) == "timer_low"
    assert classify_beep_family(3012.0) == "timer_high"
    assert classify_beep_family(2200.0) == "other"


def test_summarize_threshold_consistency_marks_shot_and_beep_instability() -> None:
    results = [
        ThresholdDetectionResult(0.25, _detection_result(1200, [1500, 1800])),
        ThresholdDetectionResult(0.35, _detection_result(1235, [1500, 1800, 2100])),
        ThresholdDetectionResult(0.45, _detection_result(None, [1500, 1800, 2100])),
    ]

    summary = summarize_threshold_consistency(results)

    assert summary.shot_counts == [2, 3, 3]
    assert summary.shot_count_span == 1
    assert summary.stable_shot_count is False
    assert summary.stable_beep_time is False


def test_build_review_flags_surfaces_saturation_and_recording_quality_risks() -> None:
    consistency = ThresholdConsistencySummary(
        thresholds=[0.25, 0.35, 0.45],
        shot_counts=[18, 19, 18],
        beep_times_ms=[1706, 1706, 15065],
        shot_count_span=1,
        beep_time_span_ms=13359,
        stable_shot_count=False,
        stable_beep_time=False,
    )
    fingerprint = AcousticFingerprintSummary(
        beep_peak_hz=1500.0,
        beep_centroid_hz=1800.0,
        shot_peak_hz=400.0,
        shot_centroid_hz=640.0,
        shot_high_frequency_ratio=0.05,
        overall_clip_ratio=0.0,
        shot_clip_ratio=0.0,
        beep_family="timer_low",
        possible_lowpass=True,
        possible_clipping=False,
    )
    beep_multipass = BeepMultipassSummary(
        final_beep_time_ms=1706,
        tone_beep_time_ms=1706,
        model_beep_time_ms=15065,
        tone_model_gap_ms=13359,
        final_tone_gap_ms=0,
        final_model_gap_ms=13359,
        passes_agree=False,
        review_required=True,
    )
    shot_multipass = ShotMultipassSummary(
        final_shot_count=19,
        onset_shot_count=18,
        matched_shots=18,
        unmatched_final_count=1,
        unmatched_onset_count=0,
        echo_like_onset_count=0,
        median_match_gap_ms=20.0,
        max_match_gap_ms=42,
        passes_agree=False,
        review_required=True,
    )

    flags = build_review_flags(consistency, 0.9993, fingerprint, beep_multipass, shot_multipass)

    assert flags == [
        "shot_count_instability",
        "beep_instability",
        "beep_multipass_disagreement",
        "shot_multipass_disagreement",
        "confidence_saturation",
        "possible_microphone_cutoff",
    ]


def test_duplicate_group_key_normalizes_repeat_suffixes() -> None:
    assert duplicate_group_key("Stage1 2.MP4") == "stage1"
    assert duplicate_group_key("stage2 2.MP4") == "stage2"
    assert duplicate_group_key("Stage4.mov") == "stage4"
    assert duplicate_group_key("20251116_095437.MP4") == "20251116_095437"


def test_build_duplicate_group_summaries_flags_inconsistent_stage_counts() -> None:
    first = type("Analysis", (), {})()
    second = type("Analysis", (), {})()
    first.summary = type(
        "Summary",
        (),
        {
            "path": "/tmp/Stage1.MP4",
            "reference_shot_count": 18,
            "fingerprint": type("Fingerprint", (), {"beep_family": "timer_low"})(),
        },
    )()
    second.summary = type(
        "Summary",
        (),
        {
            "path": "/tmp/Stage1 2.MP4",
            "reference_shot_count": 17,
            "fingerprint": type("Fingerprint", (), {"beep_family": "timer_low"})(),
        },
    )()

    groups = build_duplicate_group_summaries([first, second])

    assert groups == [
        DuplicateGroupSummary(
            group_key="stage1",
            members=["/tmp/Stage1 2.MP4", "/tmp/Stage1.MP4"],
            shot_counts=[17, 18],
            shot_count_span=1,
            beep_families=["timer_low"],
            consistent_shot_count=False,
            consistent_beep_family=True,
            review_required=True,
        )
    ]


def test_corpus_inventory_excludes_generated_media_and_byte_duplicates(tmp_path) -> None:
    canonical = tmp_path / "September2026" / "09102026" / "Stage1.MP4"
    duplicate = tmp_path / "September2026" / "09102026" / "Stage1 copy.MOV"
    generated = tmp_path / "September2026" / "09102026" / "Input" / "Stage1.MP4"
    canonical.parent.mkdir(parents=True)
    generated.parent.mkdir(parents=True)
    canonical.write_bytes(b"same-video")
    duplicate.write_bytes(b"same-video")
    generated.write_bytes(b"generated-copy")

    assert list_corpus_videos(tmp_path) == [canonical]


def test_dataset_splits_group_match_dates_and_lock_september_failure() -> None:
    paths = [
        Path(f"/bank/{month:02d}{day:02d}2026/Stage1.MP4")
        for month, day in (
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (4, 6),
            (4, 7),
            (5, 1),
            (5, 2),
            (5, 3),
            (5, 4),
            (5, 5),
            (5, 6),
            (5, 7),
            (6, 1),
            (6, 2),
            (6, 3),
            (7, 1),
            (7, 2),
            (8, 1),
            (8, 2),
            (9, 10),
        )
    ]

    splits = _dataset_splits(paths)

    assert list(splits.values()).count("train") == 15
    assert list(splits.values()).count("validation") == 3
    assert list(splits.values()).count("test") == 4
    assert splits["2026-09-10"] == "test"


def test_corpus_audio_loader_preserves_native_channels(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}
    channels = np.asarray([[0.5, 0.25], [0.25, 0.125]], dtype=np.float32)

    def fake_extract(video_path, wav_path, sample_rate=22050, *, preserve_channels=False):
        captured["preserve_channels"] = preserve_channels
        return Path(wav_path)

    monkeypatch.setattr(corpus_module, "extract_audio_wav", fake_extract)
    monkeypatch.setattr(corpus_module, "read_wav_channels", lambda path: (channels, 22050))
    monkeypatch.setattr(corpus_module, "_media_timeline_metadata", lambda path: (0, 1))

    aligned, sample_rate, duration_ms = corpus_module._load_aligned_audio(tmp_path / "stage.mp4")

    assert captured["preserve_channels"] is True
    assert aligned.shape == (22, 2)
    assert np.allclose(aligned[:2], channels)
    assert sample_rate == 22050
    assert duration_ms == 1


def test_practiscore_raw_time_maps_input_copy_to_canonical_corpus_video(tmp_path) -> None:
    canonical = tmp_path / "September2026" / "09102026" / "Stage1.MP4"
    input_copy = canonical.parent / "Input" / "Stage1.MP4"
    input_copy.parent.mkdir(parents=True)
    canonical.write_bytes(b"same-stage-media")
    input_copy.write_bytes(b"same-stage-media")
    (canonical.parent / "project.json").write_text(
        json.dumps(
            {
                "stages": [
                    {
                        "primary_media": {"path": str(input_copy)},
                        "scoring": {"imported_stage": {"raw_seconds": 16.34}},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    values = corpus_module._practiscore_raw_seconds_by_path(tmp_path)

    assert values[str(canonical.resolve())] == 16.34
