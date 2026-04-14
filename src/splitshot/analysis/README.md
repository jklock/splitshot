# Analysis

The analysis package extracts audio features, runs the embedded model, and turns the results into beep and shot detections.

## Files

- [audio_features.py](audio_features.py) frames mono audio and builds the feature matrix used by the classifier.
- [ml_runtime.py](ml_runtime.py) hosts the embedded `AudioEventClassifier`, `ModelPredictions`, and peak-picking helpers.
- [detection.py](detection.py) combines model output with refinement heuristics and returns a `DetectionResult`.
- [sync.py](sync.py) computes the primary/secondary beep offset.
- [model_bundle.py](model_bundle.py) contains the generated classifier weights, metadata, and normalization constants.

## Processing Chain

1. `media.audio.extract_audio_wav` writes a mono WAV file.
2. `media.audio.read_wav_mono` loads the samples into NumPy.
3. `extract_feature_matrix` and `AudioEventClassifier.predict_audio` produce class probabilities over time.
4. `detect_beep` and `detect_shots` identify the timer beep and shot peaks.
5. `analyze_video_audio` returns a `DetectionResult` with the beep time, shot events, waveform envelope, and sample rate.

## Important Behaviors

- The classifier is cached with `lru_cache` so repeated detections reuse the same model instance.
- Beep detection uses both tonal heuristics and model probabilities.
- Shot detection respects the detection threshold and excludes the beep region.
- Refiner helpers adjust rough detections to the nearest stronger onset in the waveform.

## Downstream Consumers

- The controller stores detected shots and beep timing on the shared `Project` model.
- The browser waveform and stage presentation use the derived shot list and waveform envelope.
- The benchmark CLI uses the same analysis pipeline to produce CSV output for Stage*.MP4 files.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-10
