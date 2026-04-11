# ML Detection Parity Plan

## Goal

Replace the current heuristic audio detector with a local bundled machine-learning detector so SplitShot matches Shot Streamer's "AI analyzes after upload" behavior in both workflow and detection method.

## Baseline Review

### Directions.md Requirements Relevant To This Pass

- Automatic shot and timer-beep detection are core to the product
- The system should do the work automatically after video upload
- Manual waveform editing exists to correct automatic detections, not to replace them

### Current SplitShot State

- Upload-first behavior is implemented
- Automatic analysis is implemented
- The detector itself is still heuristic:
  - beep detection uses FFT band energy and onset scoring
  - shot detection uses amplitude-envelope thresholding and peak picking

### Shot Streamer Requirement To Mirror

- The public product language positions detection as AI/ML-driven
- To match that behavior locally, SplitShot should run a bundled local model rather than a fixed handcrafted detector

## Product Change For This Pass

### Detection Architecture

1. Extract audio locally from the selected video.
2. Slice the audio into overlapping windows.
3. Compute compact audio features per window.
4. Run a bundled local classifier over those features.
5. Convert classifier outputs into:
   - timer beep events
   - shot events
   - event confidence values
6. Feed those detections into the existing waveform, split, merge, scoring, and export flows.

### Model Shape

- Keep the first model small and local-first
- Use a single multi-class classifier over windowed audio:
  - background
  - beep
  - shot
- Store learned weights in the repo so inference is offline and deterministic
- Keep the runtime dependency surface simple by using NumPy-only inference

### Training Approach

- Add a deterministic training script that procedurally generates labeled audio examples
- Train the classifier offline and commit the resulting learned weights
- Keep the feature pipeline and trained parameters versioned with the app

## Implementation Areas

### Analysis

- Add audio feature extraction utilities
- Add a small local classifier implementation
- Replace heuristic shot/beep detection with classifier-backed event extraction
- Preserve threshold control as a probability cutoff or sensitivity modifier

### Packaging

- Bundle model parameters with the source tree
- Keep inference local with no network requirement

### Tests

- Verify primary detection still finds the expected beep and shots on known inputs
- Verify confidence values come from model outputs
- Verify ingest, sync, waveform, and export continue to work with the new detector

## Done Criteria

- Automatic detection is model-backed instead of heuristic-only
- Detection remains local and offline
- Existing UX flow and downstream features remain intact
- Tests cover feature behavior rather than implementation trivia
