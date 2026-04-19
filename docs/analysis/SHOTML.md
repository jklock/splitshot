# ShotML In SplitShot

This document explains how SplitShot's embedded ShotML pipeline works in the current codebase, what each stage is responsible for, and what its confidence values do and do not mean.

ShotML is not a full stage-understanding system. It is a local audio event detector that helps SplitShot estimate the timer beep and shot times from a video's audio track. Everything downstream, including split rows, timer badges, metrics, and scoring summaries, depends on how well this detector lines up with the real audio.

## High-Level Goal

ShotML answers two questions from a stage video:

1. Where is the start beep?
2. Where are the shot events after the beep?

The output is a `DetectionResult` containing:

- `beep_time_ms`
- `shots`
- `waveform`
- `sample_rate`

Code path:

- `analyze_video_audio` in `src/splitshot/analysis/detection.py`
- `analyze_video_audio_thresholds` in `src/splitshot/analysis/detection.py`

## End-To-End Pipeline

## 1. Audio Extraction And Timeline Alignment

SplitShot first extracts a mono WAV file from the source media and reads it into NumPy.

Relevant functions:

- `extract_audio_wav`
- `read_wav_mono`
- `_media_timeline_metadata`
- `_align_samples_to_media_timeline`

The alignment step matters. Browser playback, FFmpeg, and container metadata can disagree about where the audio stream starts relative to the video stream. SplitShot reads the media metadata, pads or trims the audio to match the media timeline, and then pads or truncates the sample array to the media duration.

That means ShotML does not run on an arbitrary raw audio buffer. It runs on an audio buffer that has already been normalized to the media timeline used by the rest of the app.

## 2. Windowing And Feature Extraction

The embedded model uses a fixed feature vector per audio frame.

Current model bundle facts:

- model version: `audio-event-ml-v1`
- class labels: `background`, `beep`, `shot`
- sample rate: `22050`
- window size: `2048` samples
- hop size: `128` samples

Feature extraction happens in `src/splitshot/analysis/audio_features.py`.

The audio is framed with centered padding by `frame_audio`, then each frame becomes a 19-value feature vector via `extract_window_features`.

The feature set is:

- log RMS energy
- absolute peak
- crest factor
- zero crossing rate
- attack ratio
- sustain ratio
- log attack peak
- normalized spectral centroid
- normalized spectral bandwidth
- normalized spectral rolloff
- spectral flatness
- 8 band-energy ratios across fixed frequency bands

The current band edges are:

- `0-180 Hz`
- `180-400 Hz`
- `400-800 Hz`
- `800-1400 Hz`
- `1400-2200 Hz`
- `2200-3400 Hz`
- `3400-5200 Hz`
- `5200-8000 Hz`
- `8000-11025 Hz`

This mix is intentionally simple. It gives the classifier transient shape, energy, and coarse spectral placement without requiring a heavy runtime stack.

## 3. Embedded Neural Network Runtime

The classifier lives in `src/splitshot/analysis/ml_runtime.py` and its weights live in `src/splitshot/analysis/model_bundle.py`.

The runtime does three things:

1. Standardizes features using the stored mean and standard deviation.
2. Applies a small ReLU hidden layer.
3. Produces softmax probabilities for the three classes.

The main public object is `AudioEventClassifier`, which returns a `ModelPredictions` object containing:

- `centers_ms`: frame center times in milliseconds
- `probabilities`: per-frame class probabilities

The model is cached with `lru_cache(maxsize=1)`, so repeated detections reuse the same loaded classifier.

## 4. Beep Detection

Beep detection is not just "pick the highest beep probability".

SplitShot first creates provisional shot detections, then uses the first provisional shot to constrain the beep search window. That keeps the beep detector from wandering too far into later audio.

The beep detector combines:

- tonal heuristics in the `1500-5000 Hz` range
- a model-probability boost for the `beep` class
- fallback heuristics if the main path is weak
- a final beep-onset refinement pass

Main functions:

- `_detect_beep_from_predictions`
- `_fallback_beep_from_model`
- `_fallback_beep_from_heuristic`
- `_refine_beep_time`

Important implementation details:

- The tonal heuristic uses short FFT windows and looks for a concentrated high-frequency tone.
- The best region is selected by score, then collapsed into a weighted center rather than a raw argmax.
- Final refinement uses `_tonal_score_series` and `BEEP_ONSET_FRACTION = 0.24` to move the rough beep estimate toward the actual onset.

This is why the beep time usually lands earlier and more stably than a plain frame-level peak would.

## 5. Shot Candidate Detection

Shot candidate detection starts from the model's `shot` probability track.

Relevant functions:

- `_shot_detection_cutoff`
- `_detect_shots_from_predictions`
- `pick_event_peaks`

The user-facing threshold slider is converted into a probability cutoff by:

`cutoff = 0.18 + threshold * 0.62`

So the slider is not the raw probability threshold. It is mapped to a narrower internal cutoff range.

After the cutoff is calculated, SplitShot:

- ignores detections that land inside the beep exclusion radius
- requires a minimum shot spacing of `200 ms`
- rejects detections earlier than `beep + 45 ms`
- keeps only local maxima above the cutoff

Each raw shot candidate is initially assigned a confidence equal to its clipped frame-level `shot` probability.

That initial confidence is only a starting point. It is not the final user-facing confidence.

## 6. Shot Time Refinement

Raw model peaks are not treated as final shot times.

Each shot is refined with a localized waveform search in `_refine_shot_times`.

For each shot, SplitShot:

- opens a local search window around the rough time
- computes a short RMS envelope with `_rms_series`
- finds the onset region relative to the local peak
- moves the shot time to the first strong onset candidate

The onset threshold uses `SHOT_ONSET_FRACTION = 0.66`.

This step is what turns a coarse model frame into a tighter event time that better matches the visible split timeline and export timer.

## 7. Confidence Derivation

The confidence shown by the UI is the model's raw per-shot probability for the `shot` class, expressed on a `0%` to `100%` scale.

Shot-time refinement still moves the event timestamp to a stronger local onset in the waveform, but it does not rewrite the confidence into a separate heuristic estimate.

That number is still only local evidence. It is not proof that:

- no shot was missed elsewhere
- no non-shot transient was counted
- the final accumulated stage time is perfectly reconciled to outside reference data

Manual timings are different. Once a shot is added or manually moved, it is no longer an ML confidence problem. The app should treat it as a manual edit, not as a `100%` model prediction.

## 8. Threshold Sweeps And Preflight Analysis

`analyze_video_audio_thresholds` runs the full detection flow across multiple thresholds while reusing the same extracted audio, aligned samples, predictions, and waveform.

This powers threshold-sweep and preflight tooling so a user can compare outcomes before loading a video into the full browser workflow.

The important detail is that the threshold sweep does not rerun FFmpeg extraction for every threshold. It extracts once, predicts once, and reuses the intermediate state.

## 9. How ShotML Flows Into The Product

Once ShotML returns a `DetectionResult`, the rest of the app builds on top of it.

Consumers include:

- the shared `Project.analysis` state in the controller
- split-row generation in the timeline model
- browser timing tables and waveform navigation
- metrics summaries and CSV/text exports
- scoring summaries that rely on the current raw video timeline
- overlay/export timer badges and imported-summary overlays

In practice, this means one bad shot time can ripple into:

- split values
- cumulative totals
- end-of-stage raw time
- any score calculation derived from current video time

## 10. What Confidence Does Not Mean

A high confidence value means the model assigned a high probability to the `shot` class at the selected detection peak.

It does not mean:

- the stage is perfectly synchronized to an imported CSV
- all shots were found
- no extra shots were created
- the final displayed raw time is guaranteed to match an external source

That distinction matters. If the imported raw time says `30.00` and the split timeline totals `29.72`, the run may still contain several individually plausible detections while being wrong as a whole.

That is why imported-versus-video raw delta is important. It is a stage-level reconciliation signal, not just a per-shot classifier score.

## 11. Practical Limits

ShotML will struggle more when:

- the timer beep is clipped, buried, or missing
- shots are suppressed, distant, or heavily echoed
- another impulse sound overlaps a real shot
- the source media has timeline offsets or problematic container metadata
- multiple shots are extremely close together

Those are review cases, not proof that the model is useless. But they are exactly the cases where the UI should avoid sounding certain.

Echo is usually handled as a near-duplicate onset problem, not as a fresh shot. The corpus layer records `echo_like_onset_count` for unmatched onsets that sit close to an accepted shot, and the review queue subtracts that count from the unmatched-onset penalty so reflections stay visible without dominating review priority.

## 12. Recommended Reading And Debug Path

For the implementation details, start here:

- `src/splitshot/analysis/audio_features.py`
- `src/splitshot/analysis/ml_runtime.py`
- `src/splitshot/analysis/detection.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/timeline/model.py`
- `src/splitshot/scoring/logic.py`

If you are diagnosing a mismatch between imported results and exported timing, inspect the pipeline in this order:

1. beep placement
2. missing or extra shots
3. shot refinement windows
4. threshold choice
5. imported-versus-video raw delta

That order matches the real dependency chain in the code.