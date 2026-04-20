# ShotML Tab Architecture

This document describes the ShotML tab implementation from the project model through detection, controller orchestration, browser API, static UI, persistence, and tests. It is written for engineers who need to maintain or extend the ShotML detector workflow.

## Executive Summary

ShotML is now a project-scoped detector configuration and timing proposal workflow. The authoritative settings live on `Project.analysis.shotml_settings`, pending timing changes live on `Project.analysis.timing_change_proposals`, and the browser ShotML tab edits those values through controller-backed JSON APIs.

The detector still owns automatic beep and shot discovery. The Splits pane remains the manual timing editor. The ShotML pane sits directly below Splits in the left rail and owns the threshold, advanced detector knobs, explicit reruns, and proposal generation.

## Data Model

| Concern | Code proof |
| --- | --- |
| All detector defaults are centralized in `ShotMLSettings`. | `src/splitshot/domain/models.py:193` through `src/splitshot/domain/models.py:246` define the full settings dataclass. |
| Pending corrections are structured as `TimingChangeProposal`. | `src/splitshot/domain/models.py:249` through `src/splitshot/domain/models.py:263` define proposal type, status, shot references, before/after times, confidence, support, message, and evidence. |
| `AnalysisState` owns settings, proposals, and last run summary. | `src/splitshot/domain/models.py:266` through `src/splitshot/domain/models.py:279` add `shotml_settings`, `timing_change_proposals`, and `last_shotml_run_summary`. |
| Project loading preserves and normalizes settings and proposals. | `src/splitshot/domain/models.py:824` through `src/splitshot/domain/models.py:839` parse settings, `src/splitshot/domain/models.py:842` through `src/splitshot/domain/models.py:858` parse proposals, and `src/splitshot/domain/models.py:940` through `src/splitshot/domain/models.py:971` wire those values into `AnalysisState`. |

`AnalysisState.detection_threshold` remains for compatibility. New code treats `analysis.shotml_settings.detection_threshold` as the source of truth and keeps the legacy field synchronized.

## App Settings And Project Defaults

App-level defaults are stored on `AppSettings.shotml_defaults`. New projects copy those defaults into the project-scoped `AnalysisState`. Resetting ShotML settings from the ShotML pane applies the factory `ShotMLSettings()` profile back into the current project and updates app defaults to the same factory profile.

The important design rule is: project settings are authoritative for an open project. App defaults only seed new projects or reset a project when the user requests it.

## Default Settings Review

The current default threshold is `0.35` because `artifacts/timing-accuracy-summary.json` recommends `0.35` as the lowest timing score with 0 missed shots, 0 extra shots, 304 matched shots at 0 ms mean absolute shot error, and 4.188 ms mean absolute beep/stage-time error across 16 auto-consensus videos.

The model training artifacts support keeping the rest of the detector defaults conservative:

- `artifacts/model-training-auto-summary.json` reports 1.0 validation accuracy and 1.0 validation macro recall, with leave-one-source-out robustness at 0.977 accuracy, 0.926 macro recall, 0.8125 beep recall, and 0.9967 shot recall.
- `artifacts/model-training-auto-clean-summary.json` is stricter and smaller. It has 401 clean samples and shows strong shot recall, but weak beep recall because the clean set contains only 9 beep samples. That supports the existing hybrid beep path, which uses tonal heuristics plus model probability instead of trusting the beep class alone.
- The available timing sweep evaluates threshold, not every advanced tunable. Because the non-threshold defaults are the values that produced the timing artifact and are not independently swept in the committed results, they remain unchanged.

## Detection Pipeline

`src/splitshot/analysis/detection.py` accepts a `ShotMLSettings` object at every public analysis entry point.

| Step | Code proof |
| --- | --- |
| Runtime settings are normalized by `_settings`. | `src/splitshot/analysis/detection.py:73` through `src/splitshot/analysis/detection.py:74`. |
| Classifier window and hop size come from settings. | `src/splitshot/analysis/detection.py:77` through `src/splitshot/analysis/detection.py:84`. |
| Threshold mapping uses settings-controlled cutoff base and span. | `src/splitshot/analysis/detection.py:87` through `src/splitshot/analysis/detection.py:93`. |
| Beep search, tonal scoring, model boost, fallback, and weighted region cutoff read from settings. | `src/splitshot/analysis/detection.py:800` through `src/splitshot/analysis/detection.py:900`. |
| Shot peak picking reads confidence source, cutoff mapping, min interval, min spacing, and beep exclusion radius from settings. | `src/splitshot/analysis/detection.py:903` through `src/splitshot/analysis/detection.py:938`. |
| False-positive filtering reads close-pair and sound-profile controls from settings. | `src/splitshot/analysis/detection.py:550` through `src/splitshot/analysis/detection.py:640`. |
| Full video analysis threads one settings object through prediction, beep detection, shot detection, refinement, suppression, confidence, and review suggestions. | `src/splitshot/analysis/detection.py:976` through `src/splitshot/analysis/detection.py:1018`. |
| Threshold sweeps reuse one prediction pass while evaluating each threshold with the same settings object. | `src/splitshot/analysis/detection.py:1021` through `src/splitshot/analysis/detection.py:1053`. |
| `analyze_video_audio` exposes the settings parameter for controller use. | `src/splitshot/analysis/detection.py:1056` through `src/splitshot/analysis/detection.py:1063`. |

The refactor keeps default behavior stable by making every field in `ShotMLSettings` default to the previous hard-coded value. Tests prove parity by comparing a legacy threshold call to a call with `ShotMLSettings()`.

## Timing Proposal Builder

Detector review suggestions are still generated during analysis. The timing changer converts those suggestions into explicit proposals:

- `near_cutoff_spacing` becomes `choose_close_pair_survivor`.
- `weak_onset_support` becomes `suppress_shot`.
- `sound_profile_outlier` becomes `suppress_shot`.
- Manual edits can generate `restore_shot` proposals from controller original-shot memory.

The pure builder lives in `src/splitshot/analysis/detection.py:1066` through `src/splitshot/analysis/detection.py:1135`. It receives sorted shots, the current beep time, and typed review suggestions, then returns `TimingChangeProposal` instances with evidence copied from the suggestion.

## Controller Responsibilities

`ProjectController` is the write boundary for the shared project. ShotML-related controller responsibilities are:

| Responsibility | Code proof |
| --- | --- |
| Primary analysis calls detection with project settings, writes beep, waveform, shots, review suggestions, threshold compatibility, clears proposals, and records a run summary. | `src/splitshot/ui/controller.py:407` through `src/splitshot/ui/controller.py:448`. |
| Secondary analysis uses the same project settings and then computes sync offset. | `src/splitshot/ui/controller.py:450` through `src/splitshot/ui/controller.py:472`. |
| Legacy threshold writes go through the new settings path. | `src/splitshot/ui/controller.py:909` through `src/splitshot/ui/controller.py:910`. |
| Settings updates coerce values by dataclass field type, keep the compatibility threshold synchronized, optionally update app defaults, and optionally rerun analysis. | `src/splitshot/ui/controller.py:912` through `src/splitshot/ui/controller.py:961`. |
| Reset copies the factory profile into project settings and app defaults. | `src/splitshot/ui/controller.py:963` through `src/splitshot/ui/controller.py:973`. |
| Proposal generation combines detector review suggestions with restore proposals for edited shots. | `src/splitshot/ui/controller.py:981` through `src/splitshot/ui/controller.py:1033`. |
| Proposal application handles move beep, move shot, suppress shot, choose close pair, and restore shot. | `src/splitshot/ui/controller.py:1041` through `src/splitshot/ui/controller.py:1071`. |
| Proposal discard marks the proposal as discarded without changing timing. | `src/splitshot/ui/controller.py:1073` through `src/splitshot/ui/controller.py:1078`. |

Applying `move_shot`, `suppress_shot`, `choose_close_pair_survivor`, or `restore_shot` delegates to the existing shot mutation methods. That keeps normalization, scoring updates, timing-event validation, project timestamps, autosave, and UI revalidation consistent with manual edits.

## Browser API

The browser server exposes ShotML routes through the same controller lock and response path as the rest of the app.

| Route | Purpose | Code proof |
| --- | --- | --- |
| `/api/analysis/threshold` | Compatibility alias for threshold rerun. | `src/splitshot/browser/server.py:691` and `src/splitshot/browser/server.py:1239` through `src/splitshot/browser/server.py:1240`. |
| `/api/analysis/shotml-settings` | Update settings and rerun only when the payload sets `rerun: true`. | `src/splitshot/browser/server.py:692` and `src/splitshot/browser/server.py:1242` through `src/splitshot/browser/server.py:1250`. |
| `/api/analysis/shotml/proposals` | Generate pending timing proposals. | `src/splitshot/browser/server.py:693` and `src/splitshot/browser/server.py:1252` through `src/splitshot/browser/server.py:1253`. |
| `/api/analysis/shotml/apply-proposal` | Apply a pending proposal. | `src/splitshot/browser/server.py:694` and `src/splitshot/browser/server.py:1255` through `src/splitshot/browser/server.py:1256`. |
| `/api/analysis/shotml/discard-proposal` | Discard a pending proposal. | `src/splitshot/browser/server.py:695` and `src/splitshot/browser/server.py:1258` through `src/splitshot/browser/server.py:1259`. |
| `/api/analysis/shotml/reset-defaults` | Restore project ShotML settings to the factory profile. | `src/splitshot/browser/server.py:696` and `src/splitshot/browser/server.py:1261` through `src/splitshot/browser/server.py:1262`. |

Every successful POST returns the normal browser state payload, so the UI refreshes from the project model rather than trusting local optimistic state.

## Static Browser UI

The ShotML tab is plain HTML plus the existing app.js state synchronization pattern.

| Surface | Code proof |
| --- | --- |
| Left rail includes ShotML directly below Splits. | `src/splitshot/browser/static/index.html:17` through `src/splitshot/browser/static/index.html:20`. |
| Splits no longer contains the threshold control. | `src/splitshot/browser/static/index.html:178` through `src/splitshot/browser/static/index.html:199` contains selected-shot controls and table only. |
| The ShotML pane contains threshold, all settings groups, Timing Changer, and Advanced Runtime. | `src/splitshot/browser/static/index.html:201` through `src/splitshot/browser/static/index.html:342`. |
| Controls use `data-shotml-setting`, so one generic JS reader/writer handles all settings fields. | `src/splitshot/browser/static/app.js:4955` through `src/splitshot/browser/static/app.js:4986`. |
| Proposal rows render from `analysis.timing_change_proposals` and call apply/discard endpoints. | `src/splitshot/browser/static/app.js:5014` through `src/splitshot/browser/static/app.js:5058`. |
| Settings autosave without rerunning detection. | `src/splitshot/browser/static/app.js:7249` through `src/splitshot/browser/static/app.js:7252` and `src/splitshot/browser/static/app.js:7544` through `src/splitshot/browser/static/app.js:7555`. |
| Reanalysis is only triggered by the Re-run ShotML button. | `src/splitshot/browser/static/app.js:7299` through `src/splitshot/browser/static/app.js:7302` and `src/splitshot/browser/static/app.js:7551`. |
| The processing banner only says ShotML is rerunning when the settings payload has `rerun: true`. | `src/splitshot/browser/static/app.js:2494` through `src/splitshot/browser/static/app.js:2504`. |

The threshold input keeps its `id="threshold"` for compatibility with existing browser tests and shortcut code, but it now lives in ShotML.

## Browser Media Error Handling

Browser video playback can abandon a media request while the local server is still writing a large chunk. SplitShot treats broken pipes, aborted connections, connection resets, and macOS `ENOBUFS` no-buffer-space writes as expected client disconnects.

| Behavior | Code proof |
| --- | --- |
| Expected disconnect error classes and errnos are centralized. | `src/splitshot/browser/server.py:38` through `src/splitshot/browser/server.py:39`. |
| `is_expected_disconnect_error` recognizes both exception classes and expected `OSError.errno` values. | `src/splitshot/browser/server.py:263` through `src/splitshot/browser/server.py:266`. |
| Media streaming logs expected write failures as `media.client_disconnect` warnings instead of raising a traceback. | `src/splitshot/browser/server.py:953` through `src/splitshot/browser/server.py:965`. |

The large run log `logs/splitshot-browser-20260420-003128-a784f259.log` already shows a prior `media.client_disconnect` event for an abandoned proxy stream at sequence 3001. The pasted `OSError: [Errno 55] No buffer space available` followed the same client-disconnect shape but was not previously classified as expected because `ENOBUFS` was missing from the helper.

## Persistence And Serialization

Project persistence uses `project_to_dict` and `project_from_dict`, so dataclass fields under `AnalysisState` serialize automatically. The explicit parser keeps old project files compatible:

- Old files with only `analysis.detection_threshold` hydrate `shotml_settings.detection_threshold`.
- New files round-trip all ShotML settings.
- New files round-trip pending proposals and their evidence objects.
- `project.analysis.detection_threshold` is synchronized to the settings threshold after loading.

This means saved projects can reopen with the exact detector settings and pending timing-proposal state they had when saved.

## Test Coverage

| Behavior | Test proof |
| --- | --- |
| Existing threshold API still reanalyzes primary and secondary media. | `tests/analysis/test_analysis.py::test_detection_threshold_reanalyzes_loaded_primary_and_secondary`. |
| Full ShotML settings object reaches analysis and affects run summary. | `tests/analysis/test_analysis.py::test_shotml_settings_update_reanalyzes_with_full_settings_object`. |
| Default settings reproduce the legacy detector output. | `tests/analysis/test_analysis.py::test_default_shotml_settings_match_legacy_threshold_call`. |
| A changed refinement setting changes shot timestamp placement. | `tests/analysis/test_analysis.py::test_shotml_refinement_setting_changes_shot_timestamp`. |
| Timing proposals can be generated, applied, and discarded. | `tests/analysis/test_analysis.py::test_timing_change_proposals_can_be_generated_applied_and_discarded`. |
| Project save/open round-trips settings, run summary, and proposals. | `tests/persistence/test_persistence.py::test_project_round_trip_preserves_feature_state`. |
| Static UI contains ShotML, moved threshold, and wired buttons. | `tests/browser/test_browser_static_ui.py`. |

## Extension Notes

- Add new detector knobs by adding a field to `ShotMLSettings`, reading it in detection, adding one `data-shotml-setting` control, and extending tests.
- Add proposal types by updating `TimingChangeProposal`, `timing_change_proposals_from_review_suggestions`, `ProjectController.apply_timing_change_proposal`, and the browser label/preview helpers.
- Keep proposal application delegated to existing controller mutation methods when possible. That avoids duplicating scoring, timeline, selection, and autosave side effects.
- Keep browser state authoritative from the server response. The ShotML UI should render from `project.analysis`, not from unsaved local-only state.

**Last updated:** 2026-04-20
**Referenced files last updated:** 2026-04-20
