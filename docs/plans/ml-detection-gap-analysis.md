# ML Detection Gap Analysis

## Current State

The app now behaves like an upload-first product, but the detection engine still relies on hand-written signal-processing rules. That means the workflow parity is stronger than the algorithm parity.

## Gaps

### Detection Method

- Shot detection is not model-backed
- Timer-beep detection is not model-backed
- There is no learned classifier bundled with the app

### Explainability Of Confidence

- Current confidence values are derived from heuristic peak height
- They are not classifier probabilities

### Reproducibility

- There is no versioned training script or model artifact in the repo
- There is no explicit model metadata to explain what the detector was trained to classify

## Closure Plan

1. Add a small local audio-event classifier design to the analysis layer.
2. Add deterministic feature extraction for windowed audio.
3. Add a reproducible training script and generated model artifact.
4. Replace heuristic event picking with classifier-score event extraction.
5. Keep threshold control by mapping it to classifier sensitivity.
6. Add tests that confirm detector behavior and confidence output.
7. Audit the final detector against the Shot Streamer parity target.
