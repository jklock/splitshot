# Stage1 Benchmark Final Audit

## Scope Reviewed

- Real benchmark file: `Stage1.MP4`
- User-provided Shot Streamer screenshot for benchmark timings
- SplitShot detector after benchmark tuning

## Benchmark Reference Encoded

- Shot count: `18`
- Draw time: `1.95 s`
- Stage time: `13.65 s`
- Split sequence from the Shot Streamer screenshot:
  - `0.60, 0.75, 0.40, 0.55, 0.40, 0.60, 0.40, 0.85, 0.35, 2.60, 0.40, 0.80, 0.35, 0.95, 0.55, 0.70, 0.45`

## Detector Changes In This Pass

- Reduced duplicate shot detections by increasing shot-event suppression during probability-to-event extraction
- Added a pre-shot tonal beep search tuned for quiet real timer audio
- Kept the detector local and ML-backed for shot classification
- Added a real benchmark test for `Stage1.MP4`

## Actual Stage1 Result

- Beep time: `9586 ms`
- Draw time: `2012 ms`
- Stage time: `13541 ms`
- Shot count: `18`
- Split sequence:
  - `592, 755, 389, 598, 319, 645, 400, 836, 372, 2571, 401, 795, 372, 870, 598, 737, 279`

## Benchmark Verdict

### Matched

- Shot count is matched exactly
- Draw time is close to the reference
- Stage time is close to the reference
- Most split timings are close to the reference pattern

### Remaining mismatch

- The final split remains the weakest benchmark point and trends shorter than the Shot Streamer reference
- A few other splits are off by around a tenth of a second, but still remain within the benchmark tolerance used in the repo test

## Test Audit

- Added `tests/test_stage1_benchmark.py`
- `uv run pytest` passed: `19 passed`
- Offscreen application smoke boot passed: `app-smoke-ok`

## Verdict

- The Stage 1 benchmark now exists as a real repo test instead of an informal screenshot comparison
- SplitShot is materially aligned with the Shot Streamer result on the benchmark file
- The largest remaining benchmark gap is late-stage shot timing precision, not broad detector failure
