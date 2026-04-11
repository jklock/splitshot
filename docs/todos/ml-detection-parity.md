# ML Detection Parity Todo

- Add deterministic audio-window feature extraction
- Add a small local multi-class classifier for background, beep, and shot windows
- Add a reproducible training script that generates labeled synthetic training data
- Generate and bundle learned model parameters in the repo
- Replace heuristic beep detection with model-backed detection
- Replace heuristic shot detection with model-backed detection
- Map the existing threshold control to model sensitivity
- Preserve shot confidence values using classifier probabilities
- Keep ingest, sync, waveform, merge, scoring, and export behavior unchanged downstream
- Add feature tests for model-backed detection and confidence output
- Write an ML parity audit document
