# Shared Backend Specification

## Normative statement

The shared backend is the contract layer beneath the Stage, Match, and Performance apps. It must expose explicit route ownership, summary state, deterministic persistence, and recoverable error behavior without collapsing app boundaries.

## Route ownership requirements

The current backend route inventory must be treated as the explicit ownership map for Work Effort 1. Route ownership is by contract family, not by where a helper happens to live.

### Shared routes

Shared routes are limited to genuinely shared hydration, project truth, media ingest, analysis, export/settings, and browser-session support.

| Family | Routes | Notes | Primary tests |
| --- | --- | --- | --- |
| Core state and activity | `GET /api/state`; `GET /api/activity/poll`; `POST /api/activity` | Cross-surface hydration, processing, and activity polling | `tests/browser/test_browser_control.py`; `tests/browser/test_automation_ui_shell_contracts.py` |
| Project lifecycle and shared mutations | `POST /api/project/new`; `POST /api/project/open`; `POST /api/project/save`; `POST /api/project/delete`; `POST /api/project/probe`; `POST /api/project/details`; `POST /api/project/ui-state`; `POST /api/project/practiscore` | Shared project truth used by Stage, Match handoff, and library reopen targets | `tests/browser/test_browser_control.py`; `tests/browser/test_project_lifecycle_contracts.py` |
| Media ingest and serving | `POST /api/import/primary`; `POST /api/import/secondary`; `POST /api/import/merge`; `POST /api/files/primary`; `POST /api/files/secondary`; `POST /api/files/merge`; `POST /api/files/practiscore`; `GET /media/primary`; `GET /media/secondary`; `GET /media/merge/{id}`; `GET /media/popup/{id}` | Shared media/browser transport | `tests/browser/test_browser_control.py`; `tests/browser/test_project_lifecycle_contracts.py` |
| Analysis, scoring, and editing | `POST /api/analysis/threshold`; `POST /api/analysis/shotml-settings`; `POST /api/analysis/shotml/proposals`; `POST /api/analysis/shotml/apply-proposal`; `POST /api/analysis/shotml/discard-proposal`; `POST /api/analysis/shotml/reset-defaults`; `POST /api/beep`; `POST /api/shots/add`; `POST /api/shots/move`; `POST /api/shots/restore`; `POST /api/shots/delete`; `POST /api/shots/select`; `POST /api/scoring`; `POST /api/scoring/profile`; `POST /api/scoring/score`; `POST /api/scoring/restore`; `POST /api/scoring/position`; `POST /api/events/add`; `POST /api/events/delete` | Shared Stage analysis and editing contracts | `tests/browser/test_browser_control.py`; `tests/browser/test_timing_waveform_contracts.py`; `tests/browser/test_scoring_metrics_contracts.py` |
| Overlay, merge, export, and shared settings | `POST /api/overlay`; `POST /api/popups`; `POST /api/merge`; `POST /api/merge/source`; `POST /api/merge/source/analyze`; `POST /api/merge/remove`; `POST /api/merge/reset-defaults`; `POST /api/sync`; `POST /api/swap`; `POST /api/export/settings`; `POST /api/export/preset`; `POST /api/export`; `POST /api/settings`; `POST /api/settings/reset-defaults` | Shared shell settings, export, and merge support | `tests/browser/test_browser_control.py`; `tests/browser/test_merge_export_contracts.py` |
| PractiScore session and dialog support | `GET /api/practiscore/session/status`; `GET /api/practiscore/matches`; `POST /api/practiscore/dashboard/open`; `POST /api/practiscore/session/start`; `POST /api/practiscore/session/clear`; `POST /api/practiscore/sync/start`; `POST /api/dialog/path`; `POST /api/landing/recent` | Shared browser-session, landing, and file-picker support | `tests/browser/test_practiscore_session_api.py`; `tests/browser/test_practiscore_sync_controller.py`; `tests/browser/test_landing_backend_routes.py` |

### Stage-supporting routes

Stage-facing routes remain in the shared backend, but the owning contract is still the Stage editor.

| Family | Routes | Notes | Primary tests |
| --- | --- | --- | --- |
| Stage workspace and override support | `POST /api/workspace/stage/open`; `POST /api/workspace/stage/return`; `POST /api/workspace/stage/add`; `POST /api/workspace/stage/remove`; `POST /api/workspace/stage/override`; `POST /api/workspace/stage/override/reset` | Stage open/return and stage-level override flows | `tests/browser/test_project_lifecycle_contracts.py`; `tests/browser/test_workspace_flows.py` |
| Stage composite and media planning | `POST /api/workspace/stage/clip/list`; `POST /api/workspace/stage/clip/add`; `POST /api/workspace/stage/clip/update`; `POST /api/workspace/stage/clip/reorder`; `POST /api/workspace/stage/clip/remove`; `POST /api/angle/align`; `POST /api/angle/director/plan`; `POST /api/angle/director/generate`; `POST /api/angle/director/override`; `POST /api/angle/director/override/clear`; `POST /api/audio/mix`; `POST /api/result-cards/resolve` | Stage clip/composite, angle, audio, and result-card support | `tests/browser/test_automation_ui_shell_contracts.py`; `tests/browser/test_browser_control.py` |

### Match routes

Match-facing workspace routes remain explicitly namespaced and must stay separate from Stage editor mutations.

| Family | Routes | Notes | Primary tests |
| --- | --- | --- | --- |
| Match workspace lifecycle | `POST /api/workspace/new`; `POST /api/workspace/open`; `POST /api/workspace/save` | Match workspace creation/open/save | `tests/browser/test_workspace_flows.py`; `tests/browser/test_browser_interactions.py` |
| Match defaults and inheritance | `POST /api/workspace/defaults`; `POST /api/workspace/defaults/reset`; `POST /api/workspace/apply-from-first`; `POST /api/workspace/apply-from-first/preview` | Shared defaults and setup-once/apply-from-first flows | `tests/browser/test_browser_control.py`; `tests/browser/test_browser_interactions.py` |
| Match export and recap | `POST /api/workspace/export`; `POST /api/workspace/recap/render` | Recap and batch-export support | `tests/browser/test_automation_ui_shell_contracts.py`; `tests/browser/test_browser_interactions.py` |

### Performance routes

Performance-facing library routes remain explicitly namespaced and must stay independent from Match workspace state.

| Family | Routes | Notes | Primary tests |
| --- | --- | --- | --- |
| Library records and reopen | `POST /api/library/list`; `POST /api/library/filter`; `POST /api/library/stage/open`; `POST /api/library/match/open` | Record browsing, filter, and reopen targets | `tests/browser/test_library_backend_contracts.py`; `tests/browser/test_browser_interactions.py` |
| Library analytics and archive | `POST /api/library/analytics/trend`; `POST /api/library/analytics/compare`; `POST /api/library/archive/create` | Performance analytics and archive support | `tests/browser/test_library_backend_contracts.py`; `tests/browser/test_browser_interactions.py` |
| Library backup, export, notes, and tags | `POST /api/library/backup/create`; `POST /api/library/backup/restore`; `POST /api/library/export/json`; `POST /api/library/export/csv`; `POST /api/library/notes/update`; `POST /api/library/tags/update` | Backup/export and record metadata truth | `tests/browser/test_library_backend_contracts.py`; `tests/browser/test_browser_interactions.py` |
| Library proxy support | `POST /api/library/proxy/refresh`; `POST /api/library/proxy/open`; `POST /api/proxy/status`; `POST /api/proxy/refresh` | Performance proxy/remote support | `tests/browser/test_library_backend_contracts.py` |

### Landing and global-settings support routes

Landing, dialog, and global settings support remain shared-shell contracts even when exercised from one app surface.

- `POST /api/landing/recent`
- `POST /api/settings`
- `POST /api/settings/reset-defaults`
- `POST /api/dialog/path`
- `POST /api/project/probe`

## `/api/state` requirements

- `/api/state` must remain a summary-oriented endpoint.
- `/api/state` must provide only the data required for cross-app hydration, current status, and app summary state.
- Heavy app workflows must use dedicated routes rather than bloating `/api/state`.
- App-local settings or large workflow payloads must not drift into `/api/state` without explicit contract updates.

### Allowed `/api/state` summary families

The current summary contract is grouped by family.

| Family | Representative keys | Notes | Primary tests |
| --- | --- | --- | --- |
| Core | `status`, `project`, `default_project_path` | Current status plus current project summary | `tests/browser/test_browser_control.py` |
| Shared settings | `settings`, `settings_layers` | Shared settings layers only; app-local persistence remains in browser storage | `tests/browser/test_browser_control.py` |
| Timing and scoring summaries | `metrics`, `timing_segments`, `split_rows`, `scoring_summary`, `scoring_presets` | Summary tables and normalized row payloads only | `tests/browser/test_timing_waveform_contracts.py`; `tests/browser/test_scoring_metrics_contracts.py` |
| Media summary | `media.primary_available`, `media.secondary_available`, `media.primary_url`, `media.secondary_url`, `media.secondary_source_id`, `media.cache_token`, `media.primary_display_name`, `media.secondary_display_name` | Lightweight media availability and browser URLs | `tests/browser/test_browser_control.py` |
| PractiScore summary | `practiscore_session`, `practiscore_sync`, `practiscore_options` | Browser-facing normalized summary only; internal session/sync payloads remain stripped | `tests/browser/test_practiscore_session_api.py`; `tests/browser/test_practiscore_sync_controller.py` |
| Match/workspace summary | `editor_scope`, `active_match_id`, `active_stage_id`, `workspace_path`, `return_to_match_available`, `workspace`, `match_workspace_summary`, `workspace_stage_entries`, `workspace_shared_defaults`, `workspace_override_summary`, `stage_workspace_status`, `inherited_setting_status`, `output_profiles`, `output_profile_summary`, `opened_from_match`, `returned_stage_id` | Match and Stage handoff summary only | `tests/browser/test_browser_control.py`; `tests/browser/test_workspace_flows.py` |
| Performance summary | `library_summary`, `proxy_summary`, `library_filters`, `library_selection`, `library_reopen_targets` | Summary slices only; record lists and analytics payloads stay on dedicated library routes | `tests/browser/test_library_backend_contracts.py`; `tests/browser/test_browser_interactions.py` |
| Export presets | `export_presets` | Summary of export preset availability | `tests/browser/test_browser_control.py` |

### Heavy payloads that stay off `/api/state`

The following flows stay on dedicated routes by contract:

- full library record lists and filtered results (`/api/library/list`, `/api/library/filter`)
- backup, restore, archive, CSV, and JSON export payloads
- stage composite clip lists and angle/audio planning payloads
- recap render and workspace export payloads
- long-running import, sync, and export activity details beyond summary status

## Controller boundary requirements

- `ui.controller` is the mutation boundary for shared project/workspace/library truth.
- `browser.server` owns HTTP transport and browser-facing route contracts, not domain business logic.
- The backend must not require UI modules to infer hidden controller state in order to operate correctly.

## Persistence requirements

- Save/load/autosave behavior must be deterministic.
- Workspace open-stage and return-to-workspace behavior must preserve identity and truth.
- Workspace-to-library synchronization must be deterministic.
- Truth-hash behavior used to guard library sync must remain stable and testable.
- Export, backup, and restore flows must record truthful paths and results.

## Status and error requirements

- Browser callers must receive recoverable, user-visible error information for expected failure classes.
- Remote-session, sync, import, export, backup, and restore failures must not silently degrade state.
- Status and activity behavior must be consistent enough that tests and docs can rely on them.

## PractiScore and import requirements

- The backend must preserve Stage-facing PractiScore contracts used by the browser state.
- The backend must preserve manual PractiScore file import support.
- The backend must preserve supported import behavior for blank-project and saved-project flows.

## Cross-app support requirements

- Match-facing workspace routes must remain stable and namespaced.
- Performance-facing library routes must remain stable and namespaced.
- Shared backend behavior must not force Stage, Match, or Performance to depend on each other’s UI modules.

## Documentation and contract requirements

Any backend route, state, or persistence contract change requires synchronized updates to:

- owning backend/browser tests
- architecture documentation where ownership changed
- test guide documentation where validation changed
- app bundle docs that reference the changed contract

Current contract-owning test/doc anchors for this pass are:

- `tests/browser/test_browser_control.py`
- `tests/browser/test_automation_ui_shell_contracts.py`
- `tests/browser/test_workspace_flows.py`
- `tests/browser/test_library_backend_contracts.py`
- `tests/browser/test_practiscore_session_api.py`
- `tests/browser/test_practiscore_sync_controller.py`
- `tests/persistence/test_persistence.py`
- `tests/persistence/test_workspace_persistence.py`
- `docs/project/completion-bundles/development/`
- `docs/project/completion-bundles/predev/performance/`

## Test requirements

At minimum, backend completion must be backed by:

- route registration and contract coverage
- browser state serialization coverage
- persistence and reopen-flow coverage
- import and PractiScore coverage
- workspace and library backend coverage

## Definition of specification success

The shared backend spec is satisfied only when routes, summary state, persistence, tests, docs, and the three app bundles all describe the same backend contract.
