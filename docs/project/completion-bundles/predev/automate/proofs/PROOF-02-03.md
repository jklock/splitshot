> **Warning:** Historical snapshot; do not use as current completion status. See `docs/automate3/14-truth-audit-matrix.md` for current truth.


# Automation Proof: 02-editor-workflow-spec.md + 03-performance-library-spec.md

Generated: 2026-05-19
Validation of `src/splitshot/` against spec requirements.

Current audited truth lives in [../14-truth-audit-matrix.md](../14-truth-audit-matrix.md).
This file is a point-in-time snapshot and should not override newer code-backed audit results.

---

## 02-editor-workflow-spec.md

| # | Requirement | Verdict | Evidence |
|---|---|---|---|
| 1 | Stage opens from Multi into Single without duplication | PASS | `src/splitshot/ui/controller.py:895` — `workspace_open_stage` loads the stage's `project.json` from the workspace tree and sets `active_stage_id`, no new `Project.id` is created. Route: `src/splitshot/browser/server.py:825,1633`. |
| 2 | Returning to Multi reflects same stage's updated truth | PASS | `src/splitshot/ui/controller.py:916` — `workspace_return_to_workspace` reloads workspace from disk, reflecting updated truth immediately. Route: `src/splitshot/browser/server.py:826,1636`. |
| 3 | Shared match settings apply by default to all stages | PASS | `src/splitshot/ui/controller.py:926` — `workspace_set_defaults` updates `workspace.shared_defaults` (on `MatchWorkspace`), filtered to `_INHERITANCE_ELIGIBLE_FIELDS` (`controller.py:752`). Route: `src/splitshot/browser/server.py:827,1639`. |
| 4 | Stage overrides affect only the edited stage | PASS | `src/splitshot/ui/controller.py:935` — `workspace_set_stage_override` writes only to `entry.override_values` on the specific `stage_id`; sibling stages untouched. Route: `server.py:828,1642`. |
| 5 | Override reset removes override and returns to inheritance | PASS | `src/splitshot/ui/controller.py:948` — `workspace_reset_stage_override` clears specified keys or entire override dict; restores `entry.status`. Route: `server.py:829,1646`. |
| 6 | Output recipes resolved at stage scope vs match scope | PASS | `src/splitshot/domain/models.py:635` — `OutputProfile.scope_type: str = "stage"`. `controller.py:1298-1358` — `output_profile_create` and `output_profile_list` filter by `scope_type`. `state.py:90` — serializes `scope_type` for frontend. Persisted in `workspaces.py:74,117`. |
| 7 | `editor_scope` in browser state | PASS | `src/splitshot/browser/state.py:23,37` — present in both default and live `/api/state` payload. |
| 8 | `active_match_id`, `active_stage_id` in state | PASS | `src/splitshot/browser/state.py:24-25,38-39` — both present. |
| 9 | `return_to_match_available` in state | PASS | `src/splitshot/browser/state.py:26,40` — derived from `controller._return_to_workspace_available`. |
| 10 | `match_workspace_summary` in state | PASS | `src/splitshot/browser/state.py:27,41,50-56` — populated when workspace is active with `match_id`, `name`, `description`, `stage_count`, `updated_at`. |
| 11 | Workspace route: `/api/workspace/new` | PASS | `src/splitshot/browser/server.py:820,1613` |
| 12 | Workspace route: `/api/workspace/open` | PASS | `src/splitshot/browser/server.py:821,1616` |
| 13 | Workspace route: `/api/workspace/save` | PASS | `src/splitshot/browser/server.py:822,1619` |
| 14 | Workspace route: `/api/workspace/stage/open` | PASS | `src/splitshot/browser/server.py:825,1633` |
| 15 | Workspace route: `/api/workspace/stage/return` | PASS | `src/splitshot/browser/server.py:826,1636` |
| 16 | Workspace route: `/api/workspace/defaults` | PASS | `src/splitshot/browser/server.py:827,1639` |
| 17 | Workspace route: `/api/workspace/stage/override` | PASS | `src/splitshot/browser/server.py:828,1642` |
| 18 | Workspace route: `/api/workspace/stage/override/reset` | PASS | `src/splitshot/browser/server.py:829,1646` |
| 19 | Workspace route: `/api/workspace/stage/add` | PASS | `src/splitshot/browser/server.py:823,1623` |
| 20 | Workspace route: `/api/workspace/stage/remove` | PASS | `src/splitshot/browser/server.py:824,1630` |
| 21 | `workspace.json` disk layout | PASS | `src/splitshot/persistence/workspaces.py:9` — `WORKSPACE_FILENAME = "workspace.json"`. |
| 22 | `Stages/<stage_id>/project.json` in workspace tree | PASS | `src/splitshot/persistence/workspaces.py:52-53` — `workspace_stage_project_path` builds `STAGES_DIRNAME / stage_id / "project.json"`. `controller.py:907` — opens stage project from this path. |
| 23 | Inheritance resolution (`resolve_setting`) | PASS | `src/splitshot/ui/controller.py:1827` — `resolve_setting` walks: stage override → match shared → folder → app → domain default. |
| 24 | Legacy `project.json` still opens unchanged | PASS | `src/splitshot/ui/controller.py:4038-4039` — `open_project` calls `load_project(path)`. `src/splitshot/persistence/projects.py:232-239` — reads `project.json` with no migration step. Route: `server.py:818`. |
| 25 | `opened_from_match` in state | PASS | `src/splitshot/browser/state.py:31,49` — present in both default and live workspace context payloads. |
| 26 | `stage_workspace_status` in state | PASS | `src/splitshot/browser/state.py:32,58,106` — workspace status summary is emitted per stage. |
| 27 | `output_profile_summary` in state | PASS | `src/splitshot/browser/state.py:33,59,99-120` — summary list emitted beside `output_profiles`. |
| 28 | UI shows inherited vs overridden setting status | PARTIAL | `src/splitshot/browser/state.py:46` — `inherited_setting_status` key exists but is always initialized to `{}` and never populated with per-field resolution data. `state.py:71-78` — `has_overrides` and `workspace_override_summary` are populated per stage. Frontend can distinguish overridden from inherited but cannot see resolved values per field. |
| 29 | Every workspace route autosaves after successful mutation | PARTIAL | Mutation routes (`_workspace_set_defaults`, `_workspace_set_stage_override`, `_workspace_reset_stage_override`, `_workspace_add_stage`, `_workspace_remove_stage`) emit `project_changed.emit()` but do not trigger workspace-persist autosave. `_workspace_open_stage` (`controller.py:905`) does call `self.save_workspace()`. No `_autosave_workspace_if_needed` analog to `_autosave_project_if_needed` (`controller.py:4391`). |
| 30 | Stage-open failures return structured error with `match_id`, `stage_id`, `reason` | PARTIAL | `controller.py:901-903` — returns early with status message when stage not found, but does not return a structured error dict with `match_id`/`stage_id`/`reason`. Route handler returns `None`. |
| 31 | Return-to-workspace restores previously selected stage row and filter state | PARTIAL | `controller.py:916-922` — `workspace_return_to_workspace` reloads workspace from disk but does not explicitly restore selected row or filter state. `MatchWorkspace` has `ui_state` dict but it is not read/written by the return flow. |

---

## 03-performance-library-spec.md

| # | Requirement | Verdict | Evidence |
|---|---|---|---|
| 1 | `LibraryStageRecord` model | PASS | `src/splitshot/domain/models.py:650-662` — dataclass with `library_record_id`, `stage_id`, `match_id`, `display_name`, `event_date`, `discipline`, `competitor_name`, `metric_summary`, `output_profile_refs`, `active_retained_proxy`, `editor_target`, `truth_hash`. |
| 2 | `LibraryMatchRecord` model | PASS | `src/splitshot/domain/models.py:666-677` — dataclass with `match_id`, `stage_ids`, `aggregate_metric_summary`, `truth_hash`, etc. |
| 3 | `LibraryOutputRecord` model | PASS | `src/splitshot/domain/models.py:697-706` — dataclass with `output_id`, `scope_type`, `scope_id`, `profile_name`, etc. |
| 4 | `RetainedProxyRecord` model with `truth_hash` | PASS | `src/splitshot/domain/models.py:681-693` — dataclass with `generated_from_truth_hash: str = ""`, `scope_type`, `scope_id`, `relative_path`, `codec_profile`, dimensions, `file_size_bytes`. |
| 5 | Library storage under `~/.splitshot/library/` | PASS | `src/splitshot/persistence/library.py:22` — `library_root()` resolves to `Path.home() / ".splitshot" / "library"`. |
| 6 | Record types: stage, match, output, proxy persisted | PASS | `src/splitshot/persistence/library.py:95,108,121,187` — `save_stage_record`, `save_match_record`, `save_output_record`, `save_proxy_record`. |
| 7 | Indexing model: `stage_metrics.jsonl` | PASS | `src/splitshot/persistence/library.py:63` — `stage_metrics_path()`. `library.py:134` — `append_stage_metric` appends JSONL lines. |
| 8 | Indexing model: `match_metrics.jsonl` | PASS | `src/splitshot/persistence/library.py:67` — `match_metrics_path()`. `library.py:141` — `append_match_metric` appends JSONL lines. |
| 9 | Indexing model: `search_catalog.json` | PASS | `src/splitshot/persistence/library.py:70-71` — `search_catalog_path()`. `library.py:170-180` — `save_search_catalog`/`load_search_catalog`. |
| 10 | Library browse route: `/api/library/list` | PASS | `src/splitshot/browser/server.py:866,1949` — returns paginated `stages`/`matches`/`total_stages`/`total_matches`. |
| 11 | Library filter route: `/api/library/filter` | PASS | `src/splitshot/browser/server.py:867,1963` — filters by `discipline`, `competitor`, `stage_id`, `match_id`, sorts by `sort_by`. |
| 12 | Library open route: `/api/library/stage/open` | PASS | `src/splitshot/browser/server.py:868,2014` — loads `LibraryStageRecord`, returns `record` + `editor_target: {type: "single", stage_id}`. |
| 13 | Library open route: `/api/library/match/open` | PASS | `src/splitshot/browser/server.py:869,2046` — loads `LibraryMatchRecord`, returns `record` + `editor_target: {type: "multi", match_id}`. |
| 14 | Library proxy route: `/api/library/proxy/open` | PASS | `src/splitshot/browser/server.py:872,2090` — delegates to `controller.proxy_open_target`. |
| 15 | Proxy route: `/api/proxy/refresh` | PASS | `src/splitshot/browser/server.py:871,2084` — delegates to `controller.proxy_refresh`. |
| 16 | Proxy layout: `<stage_id>/<truth_hash>.mp4` | PASS | `src/splitshot/persistence/library.py:54-55` — `library_root() / "proxies" / "stages" / stage_id / f"{truth_hash}.mp4"`. |
| 17 | Proxy layout: `<match_id>/<truth_hash>.mp4` | PASS | `src/splitshot/persistence/library.py:58-59` — `library_root() / "proxies" / "matches" / match_id / f"{truth_hash}.mp4"`. |
| 18 | Proxy stale detection via `generated_from_truth_hash` | PASS | `src/splitshot/ui/controller.py:1112` — `stale = record.generated_from_truth_hash != current_hash`. Also validated in `proxy_refresh` (`controller.py:1166`) and `proxy_open_target` (`controller.py:1279`). |
| 19 | Proxy refresh (`proxy_refresh`) | PASS | `src/splitshot/ui/controller.py:1143` — returns status `no_media`/`skipped_current`/`scheduled`/`rendered`. Attempts actual render via `export_output_profile` when video is available. |
| 20 | Update contract: save triggers library refresh (`_sync_project_to_library`) | PASS | `src/splitshot/ui/controller.py:4029` — `save_project` calls `_sync_project_to_library`. `controller.py:4401` — `_autosave_project_if_needed` calls `_sync_project_to_library`. `controller.py:849` — `save_workspace` calls `_sync_workspace_to_library`. |
| 21 | `_sync_project_to_library` includes metric summary | PASS | `src/splitshot/ui/controller.py:965-1007` — builds `LibraryStageRecord` with `metric_summary` (first_shot_reaction, cumulative_time, shot_count, score_total, penalties), writes stage record + appends JSONL metric. |
| 22 | `_sync_workspace_to_library` includes aggregate summary | PASS | `src/splitshot/ui/controller.py:1009-1039` — builds `LibraryMatchRecord` with `aggregate_metric_summary`, stage_ids, writes match record + appends JSONL metric. |
| 23 | Missing source media doesn't invalidate record | PASS | `src/splitshot/ui/controller.py:965-1007` — library sync is wrapped in `try/except: pass`, so sync failures (e.g., no media for truth hash) don't block. `controller.py:1150-1156` — `proxy_refresh` returns `status: "no_media"` when `primary_video.path` is empty, doesn't invalidate the record. |
| 24 | Missing retained proxy marks playable as unavailable | PASS | `src/splitshot/ui/controller.py:1259-1264` — `proxy_open_target` returns `{"playable": False, "reason": "No retained proxy found"}` when record is None. |
| 25 | Stale proxy never presented as current | PASS | `src/splitshot/ui/controller.py:1112` — `proxy_status` returns `stale: True` when `generated_from_truth_hash` != `current_hash`. |
| 26 | `library_summary` in `/api/state` | PASS | `src/splitshot/browser/state.py:100-131,396` — `_build_library_summary` provides `stage_count`, `match_count`, `last_updated` with 5-second cache TTL. |
| 27 | `proxy_summary` (equivalent to `library_proxy_status`) in `/api/state` | PASS | `src/splitshot/browser/state.py:134-162,397` — `_build_proxy_summary` provides `active_proxy_id`, `proxy_stale`, `proxy_available`, `proxy_path`, `last_generated`. (Spec calls this `library_proxy_status`; implementation uses `proxy_summary`.) |
| 28 | `library_filters` in `/api/state` | PASS | `src/splitshot/browser/state.py:488-495` — library filter options are emitted in the top-level state payload. |
| 29 | `library_selection` in `/api/state` | PASS | `src/splitshot/browser/state.py:496` — `library_selection` key exists in the top-level state payload. |
| 30 | `library_reopen_targets` in `/api/state` | PASS | `src/splitshot/browser/state.py:497` — `library_reopen_targets` key exists in the top-level state payload. |

---

## Summary

### 02-editor-workflow-spec.md

| Verdict | Count |
|---|---|
| PASS | 24 |
| PARTIAL | 4 |
| FAIL | 3 |

### 03-performance-library-spec.md

| Verdict | Count |
|---|---|
| PASS | 27 |
| FAIL | 3 |

### Combined

| Verdict | Count |
|---|---|
| PASS | 51 |
| PARTIAL | 4 |
| FAIL | 6 |

### Key Gaps

**02-spec FAILs:**
- `opened_from_match` field missing from `/api/state`
- `stage_workspace_status` field missing from `/api/state`
- `output_profile_summary` field missing from `/api/state`

**02-spec PARTIALs:**
- `inherited_setting_status` exists as empty dict; not populated with per-field resolved values
- Workspace mutations (set_defaults, set_stage_override, reset, add/remove stage) do not autosave
- Stage-open failures do not return structured error (`match_id`/`stage_id`/`reason`)
- Return-to-workspace does not restore previously selected row or filter state

**03-spec FAILs:**
- `library_filters` field missing from `/api/state`
- `library_selection` field missing from `/api/state`
- `library_reopen_targets` field missing from `/api/state`
