# ML Detection Final Audit

## Scope Reviewed

- `Directions.md`
- Shot Streamer public product language describing AI-based automatic analysis
- SplitShot analysis pipeline after the local ML detector pass

## What Changed In This Pass

- The detector is no longer heuristic-only.
- SplitShot now uses a bundled local audio-event classifier for:
  - background
  - timer beep
  - shot
- Model inference is fully local and offline.
- The repo now includes:
  - deterministic audio feature extraction
  - a small local classifier runtime
  - a reproducible training script
  - a checked-in trained model bundle

## Implementation Review

### Feature extraction

- Added deterministic windowed audio features in `analysis/audio_features.py`
- Features cover both transient and spectral behavior so beep and shot windows can be separated by a learned classifier

### Model runtime

- Added a lightweight NumPy MLP runtime in `analysis/ml_runtime.py`
- The runtime loads a bundled learned model and produces class probabilities per audio window

### Training artifact

- Added `scripts/train_audio_event_model.py`
- The script procedurally generates labeled audio windows, trains the classifier deterministically, and writes the bundled model file

### Detection behavior

- `analysis/detection.py` now turns classifier probabilities into:
  - beep timing
  - shot timings
  - shot confidence values
- Confidence values are now model scores rather than heuristic peak ratios

## Directions.md Coverage

### Automatic shot detection

- Met
- Detection remains automatic after upload, but is now model-backed

### Automatic timer-beep detection

- Met
- Beep timing is now produced by the local classifier and aligned to onset-style timing

### Manual correction after auto analysis

- Met
- The waveform editing flow remains unchanged downstream from the detector swap

## Shot Streamer Comparison Verdict

### What now matches better

- The "AI analyzes after upload" behavior is now matched not only in UX flow, but in detection method
- Automatic shot and beep detection now come from a learned local model rather than fixed rules
- Confidence values now represent classifier output

### Remaining differences

- SplitShot's current local model is a compact bundled classifier rather than Shot Streamer's undisclosed production model stack
- The model is procedurally trained and versioned in-repo for local reproducibility rather than trained on Shot Streamer's private production dataset

## Test Audit

- `uv run pytest` passed: `18 passed`
- Offscreen application smoke boot passed: `app-smoke-ok`

### Feature-focused additions in this pass

- Verified primary analysis still detects expected beep and shot timing
- Verified threshold still affects sensitivity
- Verified detection emits bounded model confidence values
- Verified ingest, merge, export, persistence, and UI flows still pass with the detector swap

## Verdict

- This pass closes the major algorithm-parity gap that remained after the UX refresh
- SplitShot now has local ML-backed automatic detection, which is the correct local equivalent for Shot Streamer's AI detection claims
