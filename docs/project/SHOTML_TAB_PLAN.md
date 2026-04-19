# ShotML Tab And Timing Changer Plan

## Goal

Add a dedicated left-rail `ShotML` tab that owns all ShotML detector and timing-adjustment controls, moves the threshold control out of `Splits`, and adds an explicit timing-changer workflow that can propose, preview, and apply detector corrections instead of only emitting review suggestions.

## Current State

- The only exposed ShotML control in the browser UI is the threshold input in `src/splitshot/browser/static/index.html` under the `Splits` pane.
- The browser sends threshold changes to `/api/analysis/threshold` in `src/splitshot/browser/server.py`, which calls `ProjectController.set_detection_threshold()` in `src/splitshot/ui/controller.py`.
- `AnalysisState` in `src/splitshot/domain/models.py` persists `detection_threshold` and `detection_review_suggestions`, but it does not persist a full detector configuration object.
- `src/splitshot/analysis/detection.py` already contains the timing logic and most of the tunable constants, but they are hard-coded.
- The existing review-suggestion path is write-only: suggestions are stored on the project, but the browser does not expose a dedicated ShotML control surface or a correction workflow built on those suggestions.

## Scope

This plan covers four deliverables:

1. Extract all detector and timing-refinement tunables into a project-scoped ShotML configuration model.
2. Add a new `ShotML` left-rail tab and move the current threshold control into it.
3. Build timing-changer functionality so ShotML can suggest concrete timing corrections and let the user preview/apply them.
4. Persist, test, and document the full workflow end to end.

## Variables To Expose

The new tab needs to expose every runtime tuning variable that materially changes beep selection, shot selection, timing refinement, suppression, or review pressure. That means pulling these values out of `src/splitshot/analysis/detection.py` and related runtime code into configurable settings.

### Detection Threshold And Mapping

- `detection_threshold`
- `_shot_detection_cutoff()` mapping inputs: `base=0.42`, `span=0.28`

### Beep Detection

- `BEEP_ONSET_FRACTION`
- beep search lead window before first shot: `4000 ms`
- beep search tail guard before first shot: `40 ms`
- beep fallback minimum window extension: `80 ms`
- heuristic FFT window length: `0.02 s`
- heuristic hop length: `0.005 s`
- heuristic band range: `1800-4200 Hz`
- fallback target multiplier: `threshold * 0.8`
- tonal score window length: `80 ms`
- tonal score hop length: `1 ms`
- tonal score band range: `1500-5000 Hz`
- beep refinement pre-window: `500 ms`
- beep refinement post-window: `450 ms`
- beep refinement minimum gap before first shot: `40 ms`
- beep exclusion radius around selected shot peaks: `70 ms`
- beep region cutoff formula in `_detect_beep_from_predictions()`: `0.82 - threshold * 0.1`
- model beep boost floor in `_detect_beep_from_predictions()`: `0.3`

### Shot Candidate Detection

- `MIN_SHOT_INTERVAL_MS`
- shot peak minimum spacing: `200 ms`
- earliest auto-shot gate after beep: `beep + MIN_SHOT_INTERVAL_MS`
- shot confidence source selection in `AudioEventClassifier.shot_confidence_scores()`

### Shot Refinement

- `SHOT_ONSET_FRACTION`
- shot refinement pre-window: `150 ms`
- shot refinement post-window: `120 ms`
- inter-shot midpoint clamp padding: `70 ms`
- shot refinement minimum search window: `12 ms`
- RMS window length for shot refinement: `3 ms`
- RMS hop length for shot refinement: `1 ms`

### False-Positive Suppression

- `WEAK_ONSET_SUPPORT_THRESHOLD`
- `NEAR_CUTOFF_INTERVAL_MS`
- shot selection blend weights in `_shot_selection_score()`: `0.55 / 0.45`
- weak-support penalty in `_shot_selection_score()`: `0.08`
- close-pair suppression rules in `_filter_false_positive_shots()`

### Confidence Refinement

- `REFINEMENT_CONFIDENCE_WEIGHT`
- onset support search window: `shot - 45 ms` to `shot + 80 ms`
- onset support RMS window length: `3 ms`
- onset support hop length: `1 ms`
- onset support alignment penalty divisor: `45 ms`
- onset support alignment penalty multiplier: `0.25`

### Sound-Profile Review And Outlier Detection

- `SOUND_PROFILE_SEARCH_RADIUS_MS`
- `SOUND_PROFILE_DISTANCE_LIMIT`
- `SOUND_PROFILE_HIGH_CONFIDENCE_LIMIT`

### Classifier Runtime Values That Affect Timing Placement

- `WINDOW_SIZE`
- `HOP_SIZE`

These are model/runtime parameters rather than ordinary user knobs, so they should live in an `Advanced` section with warnings, but they still belong in the surfaced ShotML configuration because they directly affect timing granularity.

## New ShotML Tab Design

Add `shotml` to the active tool set in `src/splitshot/domain/models.py` and add a new left-rail button plus tool pane in `src/splitshot/browser/static/index.html`.

The new pane should contain these sections:

1. `Threshold`
2. `Beep Detection`
3. `Shot Candidate Detection`
4. `Shot Refinement`
5. `False Positive Suppression`
6. `Confidence And Review`
7. `Timing Changer`
8. `Advanced Runtime`

The existing threshold control and `Re-run ShotML` button should be removed from the `Splits` pane and re-homed here.

## Timing Changer Functionality

The timing changer should not replace the detector timeline outright. It should sit on top of the existing detector-first architecture and turn current review logic into actionable proposals.

The timing changer needs to do three things:

1. Generate proposed edits.
2. Show the user what would change before applying it.
3. Apply or discard those proposed edits explicitly.

### Proposed Edit Types

- `move_beep`
- `move_shot`
- `suppress_shot`
- `restore_shot`
- `choose_close_pair_survivor`

### Data Model Additions

Add a project-scoped `ShotMLSettings` dataclass under `AnalysisState` and a `TimingChangeProposal` dataclass for pending suggestions.

Suggested additions in `src/splitshot/domain/models.py`:

- `AnalysisState.shotml_settings`
- `AnalysisState.timing_change_proposals`
- optional `AnalysisState.last_shotml_run_summary`

### Controller/API Additions

Add browser server endpoints in `src/splitshot/browser/server.py` for:

- `/api/analysis/shotml-settings`
- `/api/analysis/shotml/proposals`
- `/api/analysis/shotml/apply-proposal`
- `/api/analysis/shotml/discard-proposal`
- `/api/analysis/shotml/reset-defaults`

Add controller methods in `src/splitshot/ui/controller.py` for:

- setting ShotML config values
- rerunning analysis with the full ShotML settings object
- generating timing proposals from current detections
- applying a selected proposal using the existing shot/beep mutation methods
- resetting ShotML settings to project default or app default

### Detection-Layer Refactor

Refactor `src/splitshot/analysis/detection.py` so every tunable currently defined as a module constant or hidden literal comes from a `ShotMLSettings` object.

That refactor should split the code into:

- `ShotMLSettings`
- `ShotMLRunContext`
- detection functions that accept settings instead of relying on module globals
- proposal builders that reuse current review-suggestion logic and produce structured timing-change proposals

## Persistence Model

Use project-scoped persistence first.

- Primary source of truth: `Project.analysis.shotml_settings`
- App-level fallback defaults: `AppSettings.shotml_defaults`
- Browser UI state: keep selected pane in `ui_state.active_tool`, but keep the actual tuning values in `analysis`, not `ui_state`

This keeps one project's detector tuning from silently changing another project's timing.

## Browser Work Breakdown

### Phase 1: Data Model And Persistence

- Add `ShotMLSettings` and proposal dataclasses to `src/splitshot/domain/models.py`.
- Extend project serialization/deserialization.
- Extend `src/splitshot/config.py` with app-level ShotML defaults.

### Phase 2: Detection Refactor

- Replace hard-coded constants in `src/splitshot/analysis/detection.py` with settings fields.
- Thread settings through `analyze_video_audio()` and `analyze_video_audio_thresholds()`.
- Keep existing default behavior identical by seeding the settings object with today's values.

### Phase 3: Controller And Server

- Replace `set_detection_threshold()` with a broader ShotML settings update path.
- Keep `/api/analysis/threshold` as a compatibility alias during migration, but make it write the new settings object.
- Add proposal-generation and apply/discard endpoints.

### Phase 4: Browser ShotML Pane

- Add the `ShotML` tool button and pane.
- Move threshold out of `Splits`.
- Add controls for all settings groups.
- Add a proposal list that shows suggested change type, before/after time, confidence, and support evidence.
- Add `Apply`, `Discard`, and `Reset Defaults` actions.

### Phase 5: Validation

- Update static UI tests for the new rail item and moved threshold control.
- Add controller/browser tests for settings persistence and proposal application.
- Add analysis tests to prove default settings reproduce current detector output exactly.
- Add focused tests proving changed settings actually move beep/shot outcomes when expected.

## Acceptance Criteria

This work is complete only when all of the following are true:

1. The left rail contains a `ShotML` tab.
2. The threshold control is removed from `Splits` and lives only in `ShotML`.
3. All timing-relevant detector variables are persisted in a dedicated settings object and editable from the browser UI.
4. Re-running ShotML uses the full settings object, not only the threshold.
5. Timing review suggestions can be turned into explicit proposals the user can preview and apply.
6. Default ShotML settings reproduce today's detector behavior so the refactor does not silently change existing projects.
7. Project save/open round-trips all ShotML settings and pending proposals correctly.

## Immediate Execution Order

1. Add `ShotMLSettings` and proposal types to `domain/models.py`.
2. Refactor `analysis/detection.py` to consume those settings with no behavior change.
3. Add controller/server update endpoints for the settings object.
4. Add the new `ShotML` pane and move the threshold UI into it.
5. Add proposal generation and apply/discard actions.
6. Finish tests and documentation.

## Todo Status

- Completed: locate the current threshold UI, server route, controller path, and persisted state.
- Completed: map the current hard-coded timing variables that must be moved into settings.
- Pending: implement the `ShotMLSettings` dataclass and serialization.
- Pending: refactor detector code to read from settings.
- Pending: add the new browser `ShotML` tab and move threshold out of `Splits`.
- Pending: build timing-change proposals and apply/discard flows.
- Pending: update tests and docs.

## Progress Snapshot

- Planning is complete enough to implement without another discovery pass.
- The main architectural constraint is now clear: the detector-first runtime already exists, but its tunables and suggestions are trapped inside code and not surfaced as project state.
- The first implementation milestone should be the settings-object refactor, because every other part of the ShotML tab depends on it.

Last updated: 2026-04-19
Referenced files last updated: src/splitshot/browser/static/index.html, src/splitshot/browser/static/app.js, src/splitshot/browser/server.py, src/splitshot/ui/controller.py, src/splitshot/domain/models.py, src/splitshot/analysis/detection.py, src/splitshot/analysis/ml_runtime.py, src/splitshot/config.py