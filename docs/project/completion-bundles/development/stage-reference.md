# Stage Reference Map

This is the developer-facing reference for the single-stage editor (`Stage Video Edit`).

Use this file when you need to answer any of these questions quickly:

- Which visible Stage control owns this behavior?
- Which browser file wires the control?
- Which route and server handler apply the change?
- Which controller method mutates the `Project`?
- Where is the result persisted?
- Which tests prove the control or feature today?

For the user-facing pane guides, start at [`../../../../docs/userfacing/USER_GUIDE.md`](../../../../docs/userfacing/USER_GUIDE.md) and the pane pages under [`../../../../docs/userfacing/panes/`](../../../../docs/userfacing/panes/).

## How to read this doc

- The **reference sheets** are grouped by Stage pane.
- Stage has many dynamic row actions and numeric inputs, so some rows represent a **control family** when several controls share the same route and mutation path.
- The **architecture map** traces pane flows from browser UI to persistence and export/media output.
- The **code map** calls out the files and symbols that own the Stage shell and each pane.
- The **test crosswalk** maps buttons and feature clusters to the tests that currently prove them.

If a Stage control is browser-only or runtime-only, the route and controller columns use `—`.

## Stage family proof-taxonomy summary

This summary is intentionally family-level. When one Stage family mixes persisted, output, and runtime-only controls, use the literal reference sheets below instead of flattening every control to one proof class.

| Stage family | Proof-taxonomy summary | Honesty caveat |
| --- | --- | --- |
| Project / import / PractiScore | Mostly `PERSISTED_MODEL`; manual `Select PractiScore File` fallback and the local `Match type` / `Stage #` / `Competitor name` / `Place` selectors remain the proof-bearing controls. | Seam ID `project.practiscore_bridge`: `Open PractiScore Dashboard` and the remote session/match-list bridge stay workflow guardrails; they do not close the family by themselves. |
| ShotML | `PERSISTED_MODEL` for settings, defaults, and applied/discarded proposals. | Proposal generation without apply/discard is intermediate review state, not final closure. |
| Splits / waveform | Mixed `PERSISTED_MODEL` + `RUNTIME_EPHEMERAL`. | Shot/event mutations are meaningful; waveform zoom/pan/mode/selection helpers are not meaningful closure alone. |
| Score | `PERSISTED_MODEL`. | Row focus or visibility alone does not close the family without saved scoring state. |
| Compose / Markers / Overlay / Review | Mixed `PERSISTED_MODEL` + `OUTPUT_ARTIFACT` + `RUNTIME_EPHEMERAL`. | Saved source/overlay/popup/text-box data matters, but preview-only navigation/filter/editor-visibility states need persisted payload or render/export proof behind them. |
| Metrics / Export / Settings | Mixed `OUTPUT_ARTIFACT` + `PERSISTED_MODEL` with some runtime-only affordances. | Downloads or saved defaults/profiles close claims; modal open/close, list refresh, or expand/collapse alone do not. |

## Literal reference sheets

### Shared Stage shell and tool rail

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tool rail | tool buttons `Project`, `Compose`, `Score`, `Splits`, `Markers`, `Overlay`, `Review`, `Export`, `Metrics`, `ShotML` | `.tool-item[data-tool]` | `app.js` + pane factories + shared UI-state helpers | `POST /api/project/ui-state` (deferred UI-state sync) | `browser.server._set_project_ui_state` | `ProjectController.set_ui_state` | `Project.ui_state.active_tool`, pane expansion state, remembered landing tool | `project.json` via `UIState` |
| Shell | `Home` | `#stage-go-home` | `app.js` | — | — | — | active browser surface | browser runtime only |
| Shell | stage settings gear | `#settings-rail-button` | `app.js` / tool activation | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | active tool and pane focus | `project.json` via `UIState` |
| Shell | rail collapse | `#toggle-rail` | `lib/layout.js` + `app.js` | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | rail width / collapsed tool-rail state | `project.json` via `UIState` |
| Shell | `Return to Match` | `#shell-return-match` | stage shell runtime | `POST /api/workspace/stage/return` | `browser.server._workspace_return_to_workspace` | `ProjectController.workspace_return_to_workspace` | clears active stage return context, reloads workspace when available | runtime only + workspace reload |
| Shell | layout lock | `#toggle-layout-lock-video` and `[data-layout-lock-toggle]` | `lib/layout.js` + `lib/shell-runtime.js` | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | `Project.ui_state.layout_locked` | `project.json` via `UIState` |
| Shell | resize handles | `#resize-rail`, `#resize-sidebar`, `#resize-waveform` | `lib/layout.js` | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | `rail_width`, `inspector_width`, `waveform_height` | `project.json` via `UIState` |
| Shell / empty state | `Import Video` | `#stage-empty-import` | `project-pane.js` / app shell | `POST /api/files/primary` or `POST /api/import/primary` | `_import_primary_file` / `_import_primary` | `ingest_primary_video(...)` | primary media + analysis reset/rebuild | project bundle `Input/` + `project.json` |
| Shell / empty state | `Open Project` | `#stage-empty-open` | `project-pane.js` | `POST /api/dialog/path`, then `POST /api/project/open` for an existing bundle, or `POST /api/project/new` + `POST /api/project/save` when adopting an empty folder | `_choose_dialog_path`, `_open_project`, `_new_project`, `_save_project` | `open_project(path)` or `new_project()`, `save_project(path)` | current project/session or a newly adopted project folder | existing or new project bundle |

### Project pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Project | `Select Project` | `#browse-project-path` | `project-pane.js` | `POST /api/dialog/path`, then `POST /api/project/open` for an existing bundle, or `POST /api/project/new` + `POST /api/project/save` when the chosen folder has no `project.json` yet | `_choose_dialog_path`, `_open_project`, `_new_project`, `_save_project` | `open_project(path)` or `new_project()`, `save_project(path)` | current `Project`, `project_path`, stage-scoped profiles loaded or saved into the chosen folder | existing or newly created project bundle |
| Project | `Create Project` | `#new-project` | `project-pane.js` | `POST /api/dialog/path`, `POST /api/project/new`, then `POST /api/project/save` | `_choose_dialog_path`, `_new_project`, `_save_project` | `new_project()`, `save_project(path)` | fresh `Project`, defaults, and a saved project bundle at the chosen folder | new `project.json` bundle |
| Project | `Delete Project` | `#delete-project` | `project-pane.js` | `POST /api/project/delete` | `_delete_project` | `delete_current_project()` | removes saved project metadata and resets to a blank in-memory project | deletes `project.json`; leaves bundle folders/files |
| Project | `Project name` | `#project-name` | `project-pane.js` | `POST /api/project/details` | `_set_project_details` | `set_project_details(...)` | `Project.name` | `project.json` |
| Project | `Project description` | `#project-description` | `project-pane.js` | `POST /api/project/details` | `_set_project_details` | `set_project_details(...)` | `Project.description` | `project.json` |
| Project | `Open PractiScore Dashboard` | `#open-practiscore-dashboard` | `project-pane.js` | `POST /api/practiscore/dashboard/open` | `_open_practiscore_dashboard` | browser-launch helper | none in `Project`; opens system browser | no project persistence |
| Project | `Select PractiScore File` | `#import-practiscore` | `project-pane.js` | `POST /api/files/practiscore` | `_import_practiscore_file` | `import_practiscore_file(...)` | staged PractiScore source + imported context | copied into project `CSV/` + `project.json` |
| Project | PractiScore selectors `Match type`, `Stage #`, `Competitor name`, `Place` | `#match-type`, `#match-stage-number`, `#match-competitor-name`, `#match-competitor-place` | `project-pane.js` | `POST /api/project/practiscore` | `_set_practiscore_context` | `set_practiscore_context(...)` | `ScoringState` PractiScore context, imported summary state | `project.json` + staged PractiScore metadata |
| Project | `Primary Video` typed path | `#primary-file-path` | `project-pane.js` → typed path import | `POST /api/import/primary` | `_import_primary` | `ingest_primary_video(path)` | `Project.primary_video`, analysis state, media-bound state reset | copied into `Input/` + `project.json` |
| Project | `Import Primary Video` | `#browse-primary-path` | `project-pane.js` | `POST /api/files/primary` | `_import_primary_file` | `ingest_primary_video(...)` | same as typed path import | copied into `Input/` + `project.json` |

### ShotML pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ShotML | `Detection threshold` | `#threshold` | `shotml-pane.js` + `lib/shell-runtime.js` | `POST /api/analysis/threshold` | `_set_threshold` | `set_detection_threshold(...)` | `AnalysisState.shotml_settings.detection_threshold`, refreshed automatic detections | `project.json` |
| ShotML | `Re-run ShotML` | `#apply-threshold` | `shotml-pane.js` + `lib/shell-runtime.js` | `POST /api/analysis/threshold` | `_set_threshold` | `set_detection_threshold(...)` | reruns detection with current threshold | `project.json` |
| ShotML | advanced detector controls | `[data-shotml-setting]` | `shotml-pane.js` + `lib/shell-runtime.js` | `POST /api/analysis/shotml-settings` | `_set_shotml_settings` | `set_shotml_settings(...)` | `AnalysisState.shotml_settings` | `project.json` |
| ShotML | `Generate Proposals` | `#generate-shotml-proposals` | `shotml-pane.js` + `lib/shell-runtime.js` | `POST /api/analysis/shotml/proposals` | `_generate_shotml_proposals` | `generate_timing_change_proposals()` | proposal list derived from current detections | runtime + persisted proposal state on project |
| ShotML | proposal `Apply` / `Discard` | proposal list actions | `shotml-pane.js` | `POST /api/analysis/shotml/apply-proposal`, `POST /api/analysis/shotml/discard-proposal` | `_apply_shotml_proposal`, `_discard_shotml_proposal` | `apply_timing_change_proposal(...)`, `discard_timing_change_proposal(...)` | shots / timing deltas or proposal list removal | `project.json` |
| ShotML | `Reset Defaults` | `#reset-shotml-defaults` | `shotml-pane.js` + `lib/shell-runtime.js` | `POST /api/analysis/shotml/reset-defaults` | `_reset_shotml_defaults` | `reset_shotml_settings()` | ShotML settings reset to defaults | `project.json` |

### Splits pane and waveform

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Splits | `Enable Splits` | `#timing-enabled` | `timing-pane.js` + `lib/shell-runtime.js` | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | `Project.ui_state.timing_enabled` | `project.json` via `UIState` |
| Splits | `Edit` / `Collapse` | `#expand-timing`, `#collapse-timing` | `timing-pane.js` + `lib/shell-runtime.js` | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | timing workbench expansion state | `project.json` via `UIState` |
| Waveform | `Single`, `Multi-Track`, `Zoom -`, `Zoom +`, `Amp -`, `Amp +`, `Reset`, `Expand` | `#waveform-mode-single`, `#waveform-mode-multi`, `#zoom-waveform-out`, `#zoom-waveform-in`, `#amp-waveform-out`, `#amp-waveform-in`, `#reset-waveform-view`, `#expand-waveform` | `timing-pane.js` + `lib/shell-runtime.js` + waveform helpers | mostly `—`; some expansion state goes through `POST /api/project/ui-state` | — / `_set_project_ui_state` for persisted expansion | browser waveform helpers; `set_ui_state` for expansion | waveform zoom/amplitude/track mode and expanded layout | mixed: runtime only for transient waveform view, `project.json` for persisted expansion |
| Splits | waveform shot add / drag / selection | waveform canvas + mode buttons | `timing-pane.js` + shared waveform runtime | `POST /api/shots/add`, `POST /api/shots/move`, `POST /api/shots/select` | `_add_shot`, `_move_shot`, `_select_shot` | `add_shot`, `move_shot`, `select_shot` | `AnalysisState.shots`, selected shot id | `project.json` |
| Splits | shot-row `Restore` / `Delete` | timing row actions | `timing-pane.js` | `POST /api/shots/restore`, `POST /api/shots/delete` | `_restore_shot`, `_delete_shot` | `restore_original_shot_timing(...)`, `delete_shot(...)` | `AnalysisState.shots` | `project.json` |
| Splits | `Event`, `Overlay label`, `Position`, `Add Event` | `#timing-event-kind`, `#timing-event-label`, `#timing-event-position`, `#add-timing-event` | `timing-pane.js` + `lib/shell-runtime.js` | `POST /api/events/add` | `_add_event` | `add_timing_event(...)` | `AnalysisState.events` | `project.json` |
| Splits | timing-event row delete | timing event list actions | `timing-pane.js` | `POST /api/events/delete` | `_delete_event` | `delete_timing_event(...)` | `AnalysisState.events` | `project.json` |

### Score pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Score | `Enable scoring` | `#scoring-enabled` | `scoring-pane.js` + `lib/shell-runtime.js` | `POST /api/scoring` | `_set_scoring` | `set_scoring_enabled(...)` | `ScoringState.enabled` | `project.json` |
| Score | `Preset` | `#scoring-preset` | `scoring-pane.js` | `POST /api/scoring/profile` | `_set_scoring_profile` | `set_scoring_preset(ruleset)` | `ScoringState.ruleset` | `project.json` |
| Score | `Edit` / `Collapse` | `#expand-scoring`, `#collapse-scoring` | `scoring-pane.js` + `lib/shell-runtime.js` | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | scoring workbench expansion state | `project.json` via `UIState` |
| Score | per-shot score and penalties | scoring row controls | `scoring-pane.js` | `POST /api/scoring/score` | `_assign_score` | `assign_score(...)` | per-shot score letter / penalty counts in scoring state | `project.json` |
| Score | per-shot `Restore` | scoring row action | `scoring-pane.js` | `POST /api/scoring/restore` | `_restore_score` | `restore_original_shot_score(...)` | restores original per-shot scoring | `project.json` |
| Score | per-shot `Delete` | scoring row action | `scoring-pane.js` | `POST /api/shots/delete` | `_delete_shot` | `delete_shot(...)` | removes shot from analysis/scoring surfaces | `project.json` |

### Compose pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Compose | `Add Media` | `#add-merge-media` | `merge-pane.js` + shared shell | `POST /api/files/merge` or `POST /api/import/merge` | `_import_merge_file` / `_import_merge` | `add_merge_source(...)` | merge source list on `Project` | copied into `Input/` + `project.json` |
| Compose | `Restore` | `#restore-merge-defaults` | `merge-pane.js` + `lib/shell-runtime.js` | `POST /api/merge/reset-defaults` | `_reset_merge_defaults` | `reset_merge_defaults()` | `MergeSettings` default layout/position state | `project.json` |
| Compose | `Enable added media export`, `Layout`, default layer size/position | `#merge-enabled`, `#merge-layout`, `#pip-size`, `#pip-x`, `#pip-y` | `merge-pane.js` + `lib/shell-runtime.js` | `POST /api/merge` | `_set_merge` | `set_merge_enabled`, `set_merge_layout`, `set_pip_size_percent`, `set_pip_position` | `MergeSettings` | `project.json` |
| Compose | per-source size/position/opacity/role/sync | merge source card controls | `merge-pane.js` | `POST /api/merge/source` | `_set_merge_source` | `set_merge_source_position(...)`, `set_merge_source_sync_offset(...)`, `adjust_merge_source_sync_offset(...)` | merge source entries on `Project` | `project.json` |
| Compose | per-source analyze / rerun sync | merge source card actions | `merge-pane.js` | `POST /api/merge/source/analyze` | `_analyze_merge_source` | `rerun_merge_source_analysis(...)` | sync analysis metadata for a merge source | `project.json` |
| Compose | per-source remove | merge source card action | `merge-pane.js` | `POST /api/merge/remove` | `_remove_merge_source` | `remove_merge_source(...)` | merge source list on `Project` | `project.json` |
| Compose | `Trim Dead Time` hook | `[data-output-hook="run-window"]` + `#output-hook-save` | `app.js` hook editor | `POST /api/output-profiles/update` | `_handle_output_profile_update` | `output_profile_update(...)` | selected stage `OutputProfile.metric_caption_preset` lead/tail padding | `profiles.json` beside project bundle |

### Markers pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Markers | `Enable Markers` | `#markers-enable` | `markers-pane.js` + `lib/shell-runtime.js` | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | `Project.ui_state.review_show_markers` | `project.json` via `UIState` |
| Markers | `Edit` | `#popup-edit-selected` | `markers-pane.js` | `POST /api/project/ui-state` for editor visibility continuity | `_set_project_ui_state` | `set_ui_state` | selected-marker editor visibility / marker pane UI state | `project.json` via `UIState` |
| Markers | `Add Time Marker` | `#popup-add-bubble`, `#popup-add-bubble-workbench` | `markers-pane.js` + `lib/shell-runtime.js` | `POST /api/popups` | `_set_popups` | `set_popups(payload)` | `PopupBubble` list | `project.json` + marker assets in `Markers/` when image-backed |
| Markers | `Add Selected Shot` | `#popup-add-selected-shot`, `#popup-add-selected-shot-workbench` | `markers-pane.js` | `POST /api/popups` | `_set_popups` | `set_popups(payload)` | shot-linked `PopupBubble` list | `project.json` |
| Markers | `Import Shots` | `#popup-import-shots`, `#popup-import-shots-workbench` | `markers-pane.js` | `POST /api/popups` | `_set_popups` | `set_popups(payload)` | bulk shot-linked popup markers | `project.json` |
| Markers | `Previous` / `Next` | `#popup-prev-workbench`, `#popup-next-workbench` and compact equivalents | `markers-pane.js` + shell runtime | — | — | — | selected marker only | browser runtime only |
| Markers | `Filter` | `#markers-workbench-filter` and compact filter | `markers-pane.js` | — | — | — | marker filter mode only | browser runtime only |
| Markers | selected marker `Duplicate` / `Remove` / field edits | selected-marker editor | `markers-pane.js` | `POST /api/popups` | `_set_popups` | `set_popups(payload)` | `PopupBubble` data | `project.json` + `Markers/` for image assets |
| Markers | `Enable Motion` and guided motion path actions | selected-marker motion editor | `markers-pane.js` | `POST /api/popups` | `_set_popups` | `set_popups(payload)` | popup motion/path fields | `project.json` |
| Markers | template controls for new markers | `#popup-template-*` and settings marker defaults | `markers-pane.js` + `settings-pane.js` | `POST /api/popups` or `POST /api/settings` | `_set_popups` / `_set_settings_defaults` | `set_popups(payload)` / settings-default methods | popup template defaults | `project.json` or app/folder defaults |

### Overlay pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Overlay | `Show overlay` | `#show-overlay` | `overlay-pane.js` + `lib/shell-runtime.js` | `POST /api/overlay` | `_set_overlay` | overlay mutation methods on controller | `OverlaySettings.position` / visibility | `project.json` |
| Overlay | badge size/style/stack placement/family of layout controls | `#badge-size`, `#overlay-style`, `#overlay-spacing`, `#overlay-margin`, `#max-visible-shots`, `#shot-quadrant`, `#shot-direction`, custom X/Y fields | `overlay-pane.js` + `lib/shell-runtime.js` | `POST /api/overlay` | `_set_overlay` | `set_overlay_position`, `set_badge_size`, `set_overlay_badge_layout`, `set_overlay_display_options` | `OverlaySettings` | `project.json` |
| Overlay | timer/draw/score positions and lock-to-stack | `#timer-lock-to-stack`, `#timer-x`, `#timer-y`, `#draw-lock-to-stack`, `#draw-x`, `#draw-y`, `#score-lock-to-stack`, `#score-x`, `#score-y` | `overlay-pane.js` + `lib/shell-runtime.js` | `POST /api/overlay` | `_set_overlay` | overlay mutation methods | normalized badge placement fields | `project.json` |
| Overlay | bubble size + typography | `#bubble-width`, `#bubble-height`, `#overlay-font-family`, `#overlay-font-size`, `#overlay-font-bold`, `#overlay-font-italic` | `overlay-pane.js` | `POST /api/overlay` | `_set_overlay` | overlay mutation methods | badge style + typography fields | `project.json` |
| Overlay | badge style cards + score colors | `#badge-style-grid`, `#score-color-grid` | `overlay-pane.js` | `POST /api/overlay` | `_set_overlay` | `set_overlay_badge_style(...)`, `set_scoring_color(...)` | badge style payload, scoring colors | `project.json` |
| Overlay | `Export Badges` hook | `[data-output-hook="metric-captions"]` + `#output-hook-save` | `app.js` hook editor | `POST /api/output-profiles/update` | `_handle_output_profile_update` | `output_profile_update(...)` | selected `OutputProfile.metric_caption_preset` | `profiles.json` beside project bundle |

### Review pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Review | `Show markers`, `Show added media` | `#show-markers`, `#show-pip` | `review-pane.js` + `lib/shell-runtime.js` | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | review visibility flags in `UIState` | `project.json` via `UIState` |
| Review | `Show timer badge`, `Show draw badge`, `Show split badges`, `Show scoring summary` | `#show-timer`, `#show-draw`, `#show-shots`, `#show-score` | `review-pane.js` + `overlay-pane.js` + shell runtime | `POST /api/overlay` | `_set_overlay` | overlay mutation methods | overlay display options | `project.json` |
| Review | `Add Custom Box` | `#review-add-text-box` | `review-pane.js` + `lib/shell-runtime.js` | shared overlay/review payload route (`POST /api/overlay`) | `_set_overlay` | overlay/review text-box mutation helpers | `OverlayTextBox` list | `project.json` |
| Review | `Add Summary Box` | `#review-add-imported-box` | `review-pane.js` | shared overlay/review payload route (`POST /api/overlay`) | `_set_overlay` | overlay/review text-box mutation helpers | `OverlayTextBox` list | `project.json` |
| Review | per-box `Duplicate` / `Remove` / placement / size / color / drag | review text-box editor cards | `review-pane.js` | shared overlay/review payload route (`POST /api/overlay`) | `_set_overlay` | overlay/review text-box mutation helpers | `OverlayTextBox` fields | `project.json` |
| Review | `Review Source` selector | `#retained-review-source` | `review-pane.js` + `app.js` | — for selection, `POST /api/output-profiles/render` when applied | `_handle_output_profile_render` | `output_profile_render(...)` | retained review source selection for browser preview only | browser runtime only |
| Review | `Set Source` | `#retained-review-apply` | `review-pane.js` + `app.js` | `POST /api/output-profiles/render` | `_handle_output_profile_render` | `output_profile_render(...)` | retained review preview source selection | browser runtime only |

### Metrics pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Metrics | `Expand` / `Collapse` | `#expand-metrics`, `#collapse-metrics` | `metrics-pane.js` + `lib/shell-runtime.js` | `POST /api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | metrics workbench expansion state | `project.json` via `UIState` |
| Metrics | `Export CSV` | `#metrics-export-csv` | `metrics-pane.js` + `lib/shell-runtime.js` | — | — | — | no mutation; downloads derived metrics | no persistence |
| Metrics | `Export Text` | `#metrics-export-text` | `metrics-pane.js` + `lib/shell-runtime.js` | — | — | — | no mutation; downloads derived metrics | no persistence |

### Export pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Export | `Preset` | `#export-preset` | `export-pane.js` + `lib/shell-runtime.js` | `POST /api/export/preset` | `_set_export_preset` | `apply_export_preset(preset)` | `ExportSettings.preset` and related defaults | `project.json` |
| Export | output-profile refresh | `#output-profile-refresh` | `export-pane.js` | `POST /api/output-profiles/list` | `_handle_output_profile_list` | `output_profile_list(...)` | none; refreshes browser list | no persistence |
| Export | output-profile create | `#output-profile-create` | `export-pane.js` + `app.js` | `POST /api/output-profiles/create` | `_handle_output_profile_create` | `output_profile_create(...)` | stage-scoped `OutputProfile` | `profiles.json` beside project bundle |
| Export | output-profile select / render detail | output-profile list row | `export-pane.js` | `POST /api/output-profiles/render` | `_handle_output_profile_render` | `output_profile_render(...)` | no mutation; reads render plan | no persistence |
| Export | output-profile delete | dynamic row action | `export-pane.js` | `POST /api/output-profiles/delete` | `_handle_output_profile_delete` | `output_profile_delete(...)` | removes one `OutputProfile` | `profiles.json` |
| Export | hook buttons `Aspect Ratio / Framing`, `Opening Title`, `Your Logo`, plus `Save Hook` / `Close` | `[data-output-hook]`, `#output-hook-save`, `#output-hook-close` | `app.js` hook editor | `POST /api/output-profiles/update` | `_handle_output_profile_update` | `output_profile_update(...)` | selected `OutputProfile` payload fields | `profiles.json` |
| Export | frame / codec / bitrate / output-path controls | `#quality`, `#aspect-ratio`, `#target-width`, `#target-height`, `#frame-rate`, `#video-codec`, `#audio-codec`, `#video-bitrate`, `#audio-sample-rate`, `#audio-bitrate`, `#color-space`, `#ffmpeg-preset`, `#two-pass`, `#export-path` | `export-pane.js` + `lib/shell-runtime.js` | `POST /api/export/settings` | `_set_export_settings` | `set_export_settings(payload)` | `ExportSettings` | `project.json` |
| Export | output-path browse | `#browse-export-path` | `export-pane.js` | `POST /api/dialog/path` | `_choose_dialog_path` | browser chooses path; export settings later persist it | chosen output path | `project.json` after settings/export |
| Export | `Export Video` | `#export-video` | `export-pane.js` + `lib/shell-runtime.js` | `POST /api/export` | `_export_project` | controller sync methods + `splitshot.export.pipeline.export_project(...)` | render output, export log, `project.export.output_path` | output file in chosen path / default `Output/output.mp4` |
| Export | `Show Export Log` | `#show-export-log` | `export-pane.js` + shell runtime | — | — | — | opens modal only | browser runtime only |
| Export | export-log modal `Close` / `Export Log` | `#close-export-log`, `#export-export-log` | `export-pane.js` + shell runtime | — | — | — | close modal or download last log | browser runtime only |

### Settings pane

| Pane / area | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Settings | template controls (`Save scope`, `Landing pane`, `Reopen last tool`) | `#settings-scope`, `#settings-default-tool`, `#settings-reopen-last-tool` | `settings-pane.js` + shell runtime | `POST /api/settings` | `_set_settings_defaults` | settings-default methods on controller | app/folder defaults model | app defaults or folder defaults |
| Settings | `Save Current Settings` (global template) | `#settings-import-current` | `settings-pane.js` | `POST /api/settings` | `_set_settings_defaults` | settings-default methods on controller | current project values copied into defaults | app defaults or folder defaults |
| Settings | `Reset to Default` (global template) | `#settings-reset-defaults` | `settings-pane.js` | `POST /api/settings/reset-defaults` | `_reset_settings_defaults` | reset settings-defaults method | clears saved defaults for selected scope/section | app defaults or folder defaults |
| Settings | layout `Save Current Settings` / `Reset to Default` | `#settings-use-current-layout`, `#settings-release-layout` | `settings-pane.js` + shell runtime | `POST /api/settings`, `POST /api/settings/reset-defaults` | `_set_settings_defaults`, `_reset_settings_defaults` | settings-default methods | layout defaults | app defaults or folder defaults |
| Settings | section save buttons (`Scoring`, `Compose`, `Overlay`, `Markers`, `Export`, `ShotML`) | `[data-settings-save-section]` | `settings-pane.js` | `POST /api/settings` | `_set_settings_defaults` | settings-default methods | section-specific defaults | app defaults or folder defaults |
| Settings | section reset buttons | `[data-settings-reset-section]` | `settings-pane.js` | `POST /api/settings/reset-defaults` | `_reset_settings_defaults` | reset settings-defaults method | clears section-specific defaults | app defaults or folder defaults |
| Settings | settings controls inside each section | `#settings-*` fields | `settings-pane.js` + shell runtime | `POST /api/settings` (debounced/scheduled) | `_set_settings_defaults` | settings-default methods | default settings payload for later new projects | app defaults or folder defaults |

## Developer architecture map

| Feature | Browser UI | JS owner | Route | Server handler | Controller method | Persistence layer | Export / media path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Tool activation and Stage shell state | tool rail, shell toggles, layout controls | `app.js`, `lib/shell-runtime.js`, `lib/layout.js` | `/api/project/ui-state` | `_set_project_ui_state` | `set_ui_state` | `Project.ui_state` in `project.json` | — |
| Project lifecycle | Project pane folder/name/details controls | `project-pane.js` | `/api/project/new`, `/api/project/open`, `/api/project/save`, `/api/project/delete`, `/api/project/details` | `_new_project`, `_open_project`, `_save_project`, `_delete_project`, `_set_project_details` | `new_project`, `open_project`, `save_project`, `delete_current_project`, `set_project_details` | `persistence/projects.py` | bundle root + `project.json` |
| PractiScore setup | Project pane PractiScore actions | `project-pane.js` | `/api/practiscore/dashboard/open`, `/api/files/practiscore`, `/api/project/practiscore` | `_open_practiscore_dashboard`, `_import_practiscore_file`, `_set_practiscore_context` | browser launch helper, `import_practiscore_file`, `set_practiscore_context` | `project.json` + staged `CSV/` file | `CSV/` |
| Primary video import | Project pane primary import controls | `project-pane.js` | `/api/files/primary`, `/api/import/primary` | `_import_primary_file`, `_import_primary` | `ingest_primary_video(...)` | `project.json` + staged media in `Input/` | `Input/` |
| ShotML tuning | ShotML pane | `shotml-pane.js`, shell runtime | `/api/analysis/threshold`, `/api/analysis/shotml-settings`, proposal routes | `_set_threshold`, `_set_shotml_settings`, proposal handlers | ShotML controller methods | `AnalysisState` in `project.json` | analysis-derived media/waveform, no separate output |
| Manual timing | Splits pane + waveform | `timing-pane.js`, waveform helpers | `/api/shots/*`, `/api/events/*`, `/api/project/ui-state` | shot/event handlers, `_set_project_ui_state` | shot/event methods + `set_ui_state` | `AnalysisState` + `UIState` in `project.json` | waveform is derived, no separate persisted media |
| Scoring | Score pane | `scoring-pane.js`, shell runtime | `/api/scoring`, `/api/scoring/profile`, `/api/scoring/score`, `/api/scoring/restore` | scoring handlers | scoring controller methods | `ScoringState` in `project.json` | influences overlay/export/metrics |
| Compose / added media | Compose pane | `merge-pane.js`, shell runtime | `/api/files/merge`, `/api/import/merge`, `/api/merge`, `/api/merge/source`, `/api/merge/source/analyze`, `/api/merge/remove` | merge handlers | merge controller methods | merge sources and settings in `project.json`, media copied into `Input/` | `Input/`, later used by export pipeline |
| Markers | Markers pane | `markers-pane.js`, shell runtime | `/api/popups`, `/api/project/ui-state` | `_set_popups`, `_set_project_ui_state` | `set_popups`, `set_ui_state` | `PopupBubble` + marker template in `project.json`; image assets in `Markers/` | `Markers/`, popup media route |
| Overlay + Review | Overlay and Review panes | `overlay-pane.js`, `review-pane.js`, shell runtime | `/api/overlay`, `/api/project/ui-state`, `/api/output-profiles/render` | `_set_overlay`, `_set_project_ui_state`, `_handle_output_profile_render` | overlay mutation methods, `set_ui_state`, `output_profile_render` | `OverlaySettings`, `OverlayTextBox`, `UIState`, retained preview source in runtime only | used live in preview and later in export |
| Metrics | Metrics pane | `metrics-pane.js`, shell runtime | `/api/project/ui-state` for expansion; exports are browser-only | `_set_project_ui_state` | `set_ui_state` | metrics workbench expansion in `UIState`; metrics content derived from project state | browser-generated CSV/TXT downloads |
| Export | Export pane | `export-pane.js`, shell runtime, hook editor in `app.js` | `/api/export/preset`, `/api/export/settings`, `/api/output-profiles/*`, `/api/export`, `/api/dialog/path` | export handlers + output-profile handlers + path chooser | export settings methods, output-profile methods, `export_project(...)` | `ExportSettings` in `project.json`, stage output profiles in `profiles.json` beside project bundle | final output path, default `Output/output.mp4` |
| Settings defaults | Settings pane | `settings-pane.js`, shell runtime | `/api/settings`, `/api/settings/reset-defaults` | `_set_settings_defaults`, `_reset_settings_defaults` | controller settings-default methods | app defaults or folder defaults persistence | affects later new/open project defaults |

## How Stage works in code and where

### Browser shell and tool registration

Stage is not a single monolithic pane. The browser shell is split like this:

- [`../../../../src/splitshot/browser/static/index.html`](../../../../src/splitshot/browser/static/index.html)
  - owns the Stage shell DOM, tool rail, video stage, waveform, inspector panes, export log modal, and all control ids.
- [`../../../../src/splitshot/browser/static/app.js`](../../../../src/splitshot/browser/static/app.js)
  - owns tool registration, pane factory wiring, project UI-state sync, output-hook editor routing, and many top-level event handlers.
- [`../../../../src/splitshot/browser/static/lib/shell-runtime.js`](../../../../src/splitshot/browser/static/lib/shell-runtime.js)
  - owns many shared listeners for timing, overlay, popup, export-log modal, metrics export, and review/overlay interactions.
- [`../../../../src/splitshot/browser/static/lib/layout.js`](../../../../src/splitshot/browser/static/lib/layout.js)
  - owns rail/sidebar/waveform resizing and layout-lock persistence.

The fixed pane modules are:

- [`../../../../src/splitshot/browser/static/panes/project-pane.js`](../../../../src/splitshot/browser/static/panes/project-pane.js)
- [`../../../../src/splitshot/browser/static/panes/shotml-pane.js`](../../../../src/splitshot/browser/static/panes/shotml-pane.js)
- [`../../../../src/splitshot/browser/static/panes/timing-pane.js`](../../../../src/splitshot/browser/static/panes/timing-pane.js)
- [`../../../../src/splitshot/browser/static/panes/scoring-pane.js`](../../../../src/splitshot/browser/static/panes/scoring-pane.js)
- [`../../../../src/splitshot/browser/static/panes/merge-pane.js`](../../../../src/splitshot/browser/static/panes/merge-pane.js)
- [`../../../../src/splitshot/browser/static/panes/markers-pane.js`](../../../../src/splitshot/browser/static/panes/markers-pane.js)
- [`../../../../src/splitshot/browser/static/panes/overlay-pane.js`](../../../../src/splitshot/browser/static/panes/overlay-pane.js)
- [`../../../../src/splitshot/browser/static/panes/review-pane.js`](../../../../src/splitshot/browser/static/panes/review-pane.js)
- [`../../../../src/splitshot/browser/static/panes/metrics-pane.js`](../../../../src/splitshot/browser/static/panes/metrics-pane.js)
- [`../../../../src/splitshot/browser/static/panes/export-pane.js`](../../../../src/splitshot/browser/static/panes/export-pane.js)
- [`../../../../src/splitshot/browser/static/panes/settings-pane.js`](../../../../src/splitshot/browser/static/panes/settings-pane.js)

### Browser API boundary

All Stage POST routes are dispatched in [`../../../../src/splitshot/browser/server.py`](../../../../src/splitshot/browser/server.py).

Important route clusters:

- project and PractiScore setup
  - `/api/project/*`
  - `/api/files/primary`
  - `/api/files/practiscore`
  - `/api/import/primary`
  - `/api/practiscore/*`
- analysis / ShotML / timing
  - `/api/analysis/*`
  - `/api/shots/*`
  - `/api/events/*`
- scoring
  - `/api/scoring*`
- merge / overlay / popups
  - `/api/merge*`
  - `/api/overlay`
  - `/api/popups`
- export and output profiles
  - `/api/export*`
  - `/api/output-profiles/*`
- shell and pane state
  - `/api/project/ui-state`
  - `/api/settings*`

### Controller ownership

[`../../../../src/splitshot/ui/controller.py`](../../../../src/splitshot/ui/controller.py) is the main mutation boundary for Stage.

The high-level Stage responsibilities live there:

- project lifecycle and bundle save/load
- primary and added-media ingest
- PractiScore import and scoring context
- ShotML settings and proposal application
- shot timing add/move/restore/delete
- scoring and per-shot score assignment
- overlay and popup mutation
- merge layout/source mutation
- export setting mutation and export rendering
- output-profile create/update/delete/render
- browser UI-state persistence

### Persistence and model ownership

Model layer:

- [`../../../../src/splitshot/domain/models.py`](../../../../src/splitshot/domain/models.py)
  - `Project`
  - `UIState`
  - `AnalysisState`
  - `ScoringState`
  - `OverlaySettings`
  - `MergeSettings`
  - `OverlayTextBox`
  - `PopupBubble`
  - `ExportSettings`
  - `OutputProfile`

Persistence layer:

- [`../../../../src/splitshot/persistence/projects.py`](../../../../src/splitshot/persistence/projects.py)
  - `project.json`
  - staged `Input/`, `CSV/`, `Markers/`, `Output/`
- Stage-scoped output profiles are saved beside the project bundle as:
  - `<project>/profiles.json`
  - see controller helpers `_save_stage_profiles(...)` and `_load_stage_profiles(...)`

### Media and export paths

The important Stage bundle paths are:

- primary and added media:
  - `Input/`
- PractiScore imports:
  - `CSV/`
- marker images:
  - `Markers/`
- default export target:
  - `Output/output.mp4`
- stage output profile storage:
  - `profiles.json` beside `project.json`

Important browser media routes:

- `/media/primary`
- `/media/secondary`
- `/media/merge/{source_id}`
- `/media/popup/{popup_id}`

### Export is a cross-subsystem endpoint

The Stage `Export Video` button is not just a pure render call.

`browser.server._export_project(...)` can first sync payload fragments into the controller for:

- scoring
- overlay
- popups
- merge layout and per-source settings
- analysis shots/events/beep state

and only then call the export pipeline.

That means the export button is both:

- a late-state synchronization point
- the final FFmpeg render trigger

## Test crosswalk: buttons and features to code

Not every Stage control has its own one-control-one-test proof. The table below maps each button or feature cluster to the closest direct interaction, controller, persistence, contract, or full-flow tests.

| Visible control / feature | Tests | Coverage depth | Code path exercised |
| --- | --- | --- | --- |
| tool rail activation, shell layout, resize handles, return-to-match affordances | `tests/browser/test_browser_static_ui.py`; `tests/browser/test_automation_ui_shell_contracts.py`; `tests/browser/test_browser_rail_layout.py`; relevant Match open/return tests in `tests/browser/test_browser_interactions.py` | static contract + interaction | `index.html` + `app.js` + `lib/layout.js` + `lib/shell-runtime.js` |
| `Select Project`, `Create Project`, `Delete Project`, project details | `tests/browser/test_browser_interactions.py` Project lifecycle tests; `tests/browser/test_project_lifecycle_contracts.py`; `tests/persistence/test_project_lifecycle_contracts.py` | interaction + contract + persistence | `project-pane.js` → `/api/project/*` → controller project lifecycle methods |
| `Open PractiScore Dashboard` | `tests/browser/test_browser_interactions.py::test_project_pane_practiscore_dashboard_button_opens_system_browser` | interaction | `project-pane.js` → `/api/practiscore/dashboard/open` |
| `Select PractiScore File`, PractiScore selectors | `tests/browser/test_browser_interactions.py` manual-file and remote-match PractiScore tests; `tests/persistence/test_persistence.py` PractiScore staging assertions | interaction + persistence | `project-pane.js` → `/api/files/practiscore` / `/api/project/practiscore` → controller import/context methods |
| `Primary Video`, `Import Primary Video` | `tests/browser/test_browser_interactions.py` primary import tests; `tests/persistence/test_persistence.py::test_save_project_moves_browser_session_media_into_project_input_folder` | interaction + persistence | primary import routes → `ingest_primary_video(...)` → `Input/` staging |
| `Detection threshold`, `Re-run ShotML`, advanced ShotML settings | `tests/browser/test_browser_interactions.py::test_shotml_threshold_apply_and_reset_defaults_update_project_analysis`; `tests/browser/test_browser_interactions.py::test_shotml_settings_controls_commit_and_reset_defaults_update_project_analysis`; `tests/browser/test_browser_remaining_controls_e2e.py` ShotML numeric control tests | interaction + remaining-controls e2e | `shotml-pane.js` / shell runtime → `/api/analysis/threshold` / `/api/analysis/shotml-settings` |
| `Generate Proposals`, proposal `Apply` / `Discard` | `tests/browser/test_browser_remaining_controls_e2e.py::test_shotml_section_toggles_persist_routes_and_proposal_actions_apply_or_discard` | interaction | ShotML proposal routes → controller proposal methods |
| `Enable Splits`, shot editing, waveform controls, `Add Event` | `tests/browser/test_timing_waveform_contracts.py`; timing-related interaction coverage in `tests/browser/test_browser_interactions.py` | interaction + contract | `timing-pane.js` / shell runtime → `/api/project/ui-state`, `/api/shots/*`, `/api/events/*` |
| `Enable scoring`, `Preset`, per-shot score/restore/delete | `tests/browser/test_browser_interactions.py::test_scoring_workbench_rows_lock_edit_delete_and_restore`; `tests/browser/test_scoring_metrics_contracts.py` | interaction + contract | `scoring-pane.js` → `/api/scoring*` and `/api/shots/delete` |
| `Add Media`, merge defaults, per-source sync/layout/role controls | `tests/browser/test_browser_interactions.py::test_merge_controls_update_live_preview_layout_and_position`; `tests/browser/test_merge_export_contracts.py`; full-flow merge export proofs in `tests/browser/test_browser_full_app_e2e.py` | interaction + contract + full-flow | `merge-pane.js` / shell runtime → `/api/files/merge`, `/api/merge*` |
| `Trim Dead Time` hook and output-profile save flows | `tests/browser/test_browser_interactions.py` output-profile / hook save flow coverage; `tests/browser/test_merge_export_contracts.py` | interaction + contract | hook editor in `app.js` → `/api/output-profiles/update` |
| `Enable Markers`, `Add Time Marker`, `Add Selected Shot`, `Import Shots`, selected-marker editor, motion workflow | `tests/browser/test_browser_interactions.py` marker import/select/edit/motion tests; `tests/browser/test_overlay_review_contracts.py` where popup/review contracts overlap | interaction + contract | `markers-pane.js` → `/api/popups` and `/api/project/ui-state` |
| `Show overlay`, badge positions, typography, color controls | `tests/browser/test_browser_interactions.py::test_overlay_visibility_and_badge_toggles_round_trip_through_browser_ui`; `tests/browser/test_overlay_review_contracts.py` | interaction + contract | `overlay-pane.js` / shell runtime → `/api/overlay` |
| `Show markers`, `Show added media`, `Show timer`, `Show draw`, `Show split badges`, `Show scoring summary`, `Add Custom Box`, `Add Summary Box`, `Review Source`, `Set Source` | `tests/browser/test_browser_interactions.py` review show-box, text-box creation/drag, review-source tests; `tests/browser/test_overlay_review_contracts.py` | interaction + contract | `review-pane.js` + shared overlay/review runtime → `/api/project/ui-state`, `/api/overlay`, `/api/output-profiles/render` |
| `Expand` / `Collapse` Metrics, `Export CSV`, `Export Text` | `tests/browser/test_metrics_e2e.py`; `tests/browser/test_browser_interactions.py` metrics pane propagation tests | interaction + e2e | `metrics-pane.js` / shell runtime + browser-side metrics export |
| export preset/settings/output profiles/hook editor/`Export Video`/`Show Export Log` | `tests/browser/test_browser_interactions.py::test_export_controls_update_preset_and_settings_state`; `tests/browser/test_browser_interactions.py::test_export_log_modal_opens_closes_backdrop_and_downloads_last_log`; `tests/browser/test_browser_control.py::test_browser_control_api_exports_mp4_and_exposes_ffmpeg_log`; `tests/export/test_export.py`; full-flow export truths in `tests/browser/test_browser_full_app_e2e.py` | interaction + controller + export proof + full-flow | `export-pane.js` / shell runtime → `/api/export*` and `/api/output-profiles/*` → export pipeline |
| Settings pane save/reset flows and defaults sections | `tests/browser/test_settings_e2e.py`; `tests/browser/test_settings_defaults_truth_gate.py`; static/settings assertions in `tests/browser/test_browser_static_ui.py` | interaction + truth-gate + static contract | `settings-pane.js` / shell runtime → `/api/settings` and `/api/settings/reset-defaults` |
| project round-trip persistence for Stage-owned state | `tests/persistence/test_persistence.py::test_project_round_trip_preserves_feature_state` and related persistence tests | persistence | `controller.save_project(...)` + `persistence/projects.py` |
| control-inventory claim for Stage | `tests/browser/test_browser_control_coverage_matrix.py` | docs/contract | `docs/project/browser-control-qa-matrix.md` Stage-related rows |

## Known caveats

- Stage control ownership is intentionally split across `index.html`, `app.js`, `lib/shell-runtime.js`, `lib/layout.js`, and pane modules. One visible control can have more than one real owner.
- Several Review behaviors reuse overlay data structures instead of a separate review-only route; that is expected, not a missing implementation.
- `Export Video` is a cross-subsystem endpoint: it can apply scoring, overlay, popup, merge, and analysis payloads before rendering.
- Not every Stage numeric input has a direct one-control browser test. The crosswalk maps those to the closest feature-proving tests instead of overstating coverage.
- Some shell controls persist through `Project.ui_state` rather than a pane-specific route, so button behavior can look pane-owned while the durable state belongs to shared UI-state logic.
- Seam ID `project.practiscore_bridge`: PractiScore proof is intentionally mixed — manual `Select PractiScore File` fallback and the local selectors remain required, while dashboard open and remote-session or match-list bridges are workflow guardrails rather than proof of every downstream consumer path.
