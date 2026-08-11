# Analysis

<!-- Documentation reviewed: 2026-08-11 -->

This package owns audio extraction inputs, ShotML inference, beep and shot detection, sync helpers, and review-suggestion generation.

## Purpose

Use this package when the change affects detector behavior, confidence output, threshold handling, waveform-driven refinement, or training-corpus tooling.

## Read This First

- [detection.py](detection.py)
- [audio_features.py](audio_features.py)
- [ml_runtime.py](ml_runtime.py)

## Main Files

- [audio_features.py](audio_features.py): feature extraction for classifier windows
- [ml_runtime.py](ml_runtime.py): embedded model runtime and prediction helpers
- [detection.py](detection.py): detector orchestration and `DetectionResult`
- [sync.py](sync.py): primary and secondary timing offset calculation
- [model_bundle.py](model_bundle.py): shipped classifier weights and metadata
- [corpus.py](corpus.py), [training_dataset.py](training_dataset.py), [review_queue.py](review_queue.py), [auto_labeling.py](auto_labeling.py): corpus and training workflows

## Runtime Flow

1. Media helpers extract mono WAV audio and waveform data.
2. Feature extraction builds classifier windows.
3. The model runtime produces class probabilities.
4. Detection combines probabilities with heuristics to find the start beep and shots.
5. Review suggestions and timing proposals feed the browser and script workflows.

## Key Extension Points

- `analyze_video_audio`
- `detect_beep`
- `detect_shots`
- `timing_change_proposals_from_review_suggestions`

## Related Tests

- [../../../tests/analysis/](../../../tests/analysis/)
- [../../../tests/scripts/](../../../tests/scripts/)

## Related Docs

- [../../../docs/analysis/SHOTML.md](../../../docs/analysis/SHOTML.md)
- [../../../docs/project/SHOTML_ARCHITECTURE.md](../../../docs/project/SHOTML_ARCHITECTURE.md)
