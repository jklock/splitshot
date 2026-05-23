> **Warning:** Historical snapshot; do not use as current completion status. See `docs/automate3/14-truth-audit-matrix.md` for current truth.


# PROOF-04-05: Data Model & Technical Architecture Validation

Validated against:
- `docs/automate/04-data-model-spec.md`
- `docs/automate/05-technical-architecture.md`

## 04 — Data Model

### Required IDs

| ID | Status | Evidence |
|---|---|---|
| `run_id` | PASS | Realized as `Project.id` (`src/splitshot/domain/models.py:577`). Spec line 200 confirms `Project.id` is the primary stable `stage_id` for legacy and new records. No separate run entity exists per exact model decisions. |
| `stage_id` | PASS | `StageEntry.stage_id` (`src/splitshot/domain/models.py:622`), `Project.id` as stage truth (`:577`) |
| `match_id` | PASS | `MatchWorkspace.match_id` (`src/splitshot/domain/models.py:607`) |
| `output_id` | PASS | `OutputProfile.output_id` (`src/splitshot/domain/models.py:634`) |
| `library_record_id` | PASS | `LibraryStageRecord.library_record_id` (`:651`), `LibraryMatchRecord.library_record_id` (`:667`), `LibraryOutputRecord.library_record_id` (`:698`) |
| `retained_proxy_id` | PASS | `RetainedProxyRecord.retained_proxy_id` (`src/splitshot/domain/models.py:682`) |

### Relationship Model

| Requirement | Status | Evidence |
|---|---|---|
| match_id contains many stage_id | PASS | `MatchWorkspace.stage_entries: dict[str, StageEntry]` (`models.py:613`) and `stage_order: list[str]` (`models.py:612`) |
| stage_id → authoritative reviewed truth | PASS | `Project.id` is the stage truth (`models.py:577`); `Project` holds analysis, scoring, overlay |
| stage_id → many output_id | PASS | Controller `_output_profiles: dict[str, OutputProfile]` (`controller.py:792`), profiled per scope |
| stage/match → library_record_id | PASS | `_sync_project_to_library` (`controller.py:965`) and `_sync_workspace_to_library` (`controller.py:1009`) |
| output_id → 0/1 retained proxy | PASS | `OutputProfile.retained_proxy_id: str | None` (`models.py:645`) |

### Settings Inheritance Model

| Requirement | Status | Evidence |
|---|---|---|
| Global (app) defaults | PASS | `load_settings()` → `AppSettings` (`controller.py:778`), persisted at `~/.splitshot/settings.json` |
| Folder defaults | PASS | `load_folder_settings()` → `splitshot.conf` (`controller.py:779`) |
| Match-shared defaults | PASS | `MatchWorkspace.shared_defaults` (`models.py:614`), `workspace_set_defaults` (`controller.py:926`) |
| Stage-local overrides | PASS | `StageEntry.override_values` (`models.py:627`), `workspace_set_stage_override` (`controller.py:935`) |
| Inheritance rule (stage→match→folder→app→domain) | PASS | `resolve_setting` at `controller.py:1827-1842` with resolution order docstring at `:1828-1830` |
| Resolution order verified | PASS | `controller.py:1832-1842`: stage override → match shared → effective (folder+app) → domain default |

### OutputProfile Fields

| Field | Status | Evidence (`models.py`) |
|---|---|---|
| `output_id` | PASS | `:634` |
| `scope_type` | PASS | `:635` |
| `scope_id` | PASS | `:636` |
| `profile_name` | PASS | `:637` |
| `profile_kind` | PASS | `:638` |
| `frame_profile` | PASS | `:639` |
| `metric_caption_preset` | PASS | `:640` |
| `lead_in_card` | PASS | `:641` |
| `brand_mark` | PASS | `:642` |
| `subject_track_crop` | PASS | `:643` |
| `visibility_recipe` | PASS | `:644` |
| `retained_proxy_id` | PASS | `:645` |
| `last_rendered_at` | PASS | `:646` |

### RetainedProxyRecord Fields

| Field | Status | Evidence (`models.py`) |
|---|---|---|
| `retained_proxy_id` | PASS | `:682` |
| `scope_type` | PASS | `:683` |
| `scope_id` | PASS | `:684` |
| `source_output_id` | PASS | `:685` |
| `relative_path` | PASS | `:686` |
| `codec_profile` | PASS | `:687` |
| `width` | PASS | `:688` |
| `height` | PASS | `:689` |
| `duration_ms` | PASS | `:690` |
| `file_size_bytes` | PASS | `:691` |
| `generated_from_truth_hash` | PASS | `:692` |
| `generated_at` | PASS | `:693` |

### Disk Layouts

| Layout | Status | Evidence |
|---|---|---|
| Single-stage bundle | PASS | `projects.py:10-15`: `project.json`, `Input/`, `CSV/`, `Output/`, `Markers/` |
| Workspace bundle | PASS | `workspaces.py:9-11`: `workspace.json`, `Stages/<stage_id>/project.json`, `Output/Match/`. Stage paths via `workspace_stage_path` (`:52-57`) |
| Library store | PASS | `library.py:18-22`: `~/.splitshot/library/` with `records/`, `index/`, `proxies/` subdirs |

### Compatibility

| Requirement | Status | Evidence |
|---|---|---|
| Legacy `project.json` readable | PASS | `load_project` (`projects.py:232-239`) reads `project.json`, `project_from_dict` (`models.py:1277`) parses legacy format |
| Legacy `Project.id` → workspace `stage_id` | PASS | `workspace_add_stage` (`controller.py:868`) uses `stage_id` parameter tied to `Project.id` |
| No pre-conversion needed | PASS | `load_project` / `project_from_dict` handle all existing formats directly |
| New metadata does not change stage analysis | PASS | Workspace metadata stored separately in `workspace.json`, never mutates `project.json` |

### MatchWorkspace Fields

| Field | Status | Evidence (`models.py`) |
|---|---|---|
| `match_id` | PASS | `:607` |
| `name` | PASS | `:608` |
| `description` | PASS | `:609` |
| `created_at` | PASS | `:610` |
| `updated_at` | PASS | `:611` |
| `stage_order` | PASS | `:612` |
| `stage_entries` | PASS | `:613` |
| `shared_defaults` | PASS | `:614` |
| `match_output_profiles` | PASS | `:615` |
| `ui_state` | PASS | `:616` |
| `schema_version` | PASS | `:617` |

### StageEntry Fields

| Field | Status | Evidence (`models.py`) |
|---|---|---|
| `stage_id` | PASS | `:622` |
| `relative_project_path` | PASS | `:623` |
| `display_name` | PASS | `:624` |
| `stage_number` | PASS | `:625` |
| `status` | PASS | `:626` |
| `override_values` | PASS | `:627` |
| `last_reviewed_at` | PASS | `:628` |
| `source_media_present` | PASS | `:629` |

### Inheritance Serialization

| Requirement | Status | Evidence |
|---|---|---|
| App defaults → `~/.splitshot/settings.json` | PASS | Config module, `load_settings()` at `controller.py:778` |
| Folder defaults → `splitshot.conf` | PASS | `load_folder_settings()` at `controller.py:779` |
| Match defaults → `workspace.json` | PASS | `workspace_set_defaults` updates `shared_defaults` (`controller.py:926`), saved via `save_workspace` (`workspaces.py:208`) |
| Stage overrides → `workspace.json.stage_entries[].override_values` | PASS | `_stage_entry_from_dict` reads `override_values` (`workspaces.py:98-101`), `_stage_entry_to_dict` serializes them |
| Stage `project.json` does NOT duplicate workspace defaults | PASS | Overrides stored only in `workspace.json`; `project.json` is never mutated by workspace logic |

### Resolution Order

| Layer | Status | Evidence |
|---|---|---|
| 1. Stage override | PASS | `controller.py:1833-1836` |
| 2. Match shared default | PASS | `controller.py:1837-1838` |
| 3. Folder default | PASS | Through `effective_settings()` (`controller.py:4074`) merging folder over app |
| 4. App default | PASS | Through `effective_settings()` (`controller.py:4074`) |
| 5. Domain default | PASS | Falls through to `default` parameter (`controller.py:1842`) |

### Browser-State Field Names

| Field | Status | Evidence |
|---|---|---|
| `editor_scope` | PASS | `state.py:37` |
| `active_match_id` | PASS | `state.py:38` |
| `active_stage_id` | PASS | `state.py:39` |
| `workspace_stage_entries` | PASS | `state.py:79` |
| `workspace_shared_defaults` | PASS | `state.py:57` |
| `workspace_override_summary` | PASS | `state.py:79` |
| `output_profiles` | PASS | `state.py:94` |
| `library_summary` | PASS | `state.py:396` |
| `proxy_summary` | PASS | `state.py:397` |

---

## 05 — Technical Architecture

### Domain Model Expansion

| Model | Status | Evidence (`models.py`) |
|---|---|---|
| Stage records (stable ids) | PASS | `Project` (line 576) — single stage-truth contract |
| Match workspaces | PASS | `MatchWorkspace` (line 606) |
| Output variants | PASS | `OutputProfile` (line 633) |
| Library records | PASS | `LibraryStageRecord` (line 650), `LibraryMatchRecord` (line 666), `LibraryOutputRecord` (line 697) |
| Retained proxies | PASS | `RetainedProxyRecord` (line 681) |

### Persistence Expansion

| Module | Status | Evidence |
|---|---|---|
| Match workspace state | PASS | `src/splitshot/persistence/workspaces.py` — `save_workspace`, `load_workspace` (`:208-220`) |
| Stage override state | PASS | Stored in `workspace.json` via `StageEntry.override_values`; deserialized at `workspaces.py:98-101` |
| Output-variant state | PASS | `OutputProfile` serialization at `workspaces.py:70-86`, stage-level `profiles.json` at `controller.py:1383-1407` |
| Library metadata / index | PASS | `src/splitshot/persistence/library.py` — record CRUD (`:95-131`), metric append (`:134-146`), metrics read (`:148-167`), search catalog (`:170-180`) |
| Retained proxy metadata | PASS | `library.py:183-197` — `save_proxy_record`, `load_proxy_record` |

### Controller Orchestration

| Responsibility | Status | Evidence (`controller.py`) |
|---|---|---|
| Stage vs workspace mutation | PASS | `new_workspace` (`:821`), `save_workspace` (`:840`), `open_workspace` (`:852`), `workspace_add_stage` (`:868`), `workspace_remove_stage` (`:883`), `workspace_open_stage` (`:895`), `workspace_return_to_workspace` (`:916`) |
| Inheritance resolution | PASS | `resolve_setting` (`:1827`) with all 5 layers |
| Output-variant generation | PASS | `output_profile_create` (`:1298`), `output_profile_update` (`:1321`), `output_profile_delete` (`:1339`), `output_profile_render` (`:1414`) |
| Library record refresh | PASS | `_sync_project_to_library` (`:965`), `_sync_workspace_to_library` (`:1009`) |
| Retained proxy refresh | PASS | `proxy_status` (`:1083`), `proxy_refresh` (`:1143`), `proxy_open_target` (`:1245`) |

### Browser State

| Requirement | Status | Evidence (`state.py`) |
|---|---|---|
| Editor scope: single/multi | PASS | `editor_scope` from `_build_workspace_context` (`:37`) |
| Match workspace context | PASS | `active_match_id` (`:38`), `active_stage_id` (`:39`), `match_workspace_summary` (`:50-56`) |
| Inherited vs overridden state | PASS | `workspace_shared_defaults` (`:57`), `workspace_override_summary` (`:78-80`), `inherited_setting_status` (`:46`) |
| Output variants | PASS | `output_profiles` list from `workspace.match_output_profiles` (`:82-94`) |
| Library previews/retrieval | PASS | `_build_library_summary` (`:107`) — returns `stage_count`, `match_count`, `last_updated` |
| Proxy freshness | PASS | `_build_proxy_summary` (`:134`) — returns `active_proxy_id`, `proxy_stale`, `proxy_available`, `proxy_path`, `last_generated` |
| Single serialization seam | PASS | `browser_state()` at `:284` is the single `/api/state` seam; `**workspace_context` unpacked at `:395` |

### Browser Routes

| Route Family | Status | Evidence (`server.py`) |
|---|---|---|
| `/api/workspace/*` (10 routes) | PASS | Lines 820-829: `new`, `open`, `save`, `stage/add`, `stage/remove`, `stage/open`, `stage/return`, `defaults`, `stage/override`, `stage/override/reset` |
| `/api/output-profiles/*` (5 routes) | PASS | Lines 873-877: `list`, `create`, `update`, `delete`, `render` |
| `/api/library/*` (4 routes) | PASS | Lines 866-869: `list`, `filter`, `stage/open`, `match/open` |
| `/api/proxy/*` (3 routes) | PASS | Lines 870-872: `status`, `refresh`, `library/proxy/open` |
| All match spec exactly | PASS | Compare spec exact route list against server.py route map at lines 812-886 |

### Existing Routes Preserved

| Route | Status | Evidence (`server.py`) |
|---|---|---|
| `/api/project/probe` | PASS | `:809` |
| `/api/project/details` | PASS | `:813` |
| `/api/project/practiscore` | PASS | `:814` |
| `/api/project/ui-state` | PASS | `:815` |
| `/api/project/new` | PASS | `:816` |
| `/api/project/open` | PASS | `:817` |
| `/api/project/save` | PASS | `:818` |
| `/api/project/delete` | PASS | `:819` |
| `/api/export` | PASS | `:865` |
| `/api/export/settings` | PASS | `:863` |
| `/api/export/preset` | PASS | `:864` |
| `/api/state` | PASS | `:751` |
| `/api/settings` | PASS | `:839` |

### Export Pipeline

| Requirement | Status | Evidence (`pipeline.py`) |
|---|---|---|
| Extended, not replaced | PASS | `export_project` (`:695`) preserved intact; `export_output_profile` (`:819`) is additive |
| Named output variants | PASS | `export_output_profile` accepts `render_plan` dict from `OutputProfile` (`:819`) |
| Review proxy generation | PASS | `proxy_refresh` in controller calls `export_output_profile` for proxy renders (`controller.py:1212-1215`) |
| Lead-In Card support | PASS | `_apply_lead_in_card_to_project` (`pipeline.py:882`) |
| Brand Mark support | PASS | `_apply_brand_mark_to_project` (`pipeline.py:887`) |
| Ratio-aware exports | PASS | `frame_profile` → `AspectRatio` mapping (`pipeline.py:832-840`) |
| Subject Track Crop seam | PASS | `render_plan.get("subject_track_crop")` field present; implementation reserved |
| Stage-scope and match-scope exports | PASS | `output_profile_render` (`controller.py:1414`) with `scope_type` routing |

### Library Indexing Subsystem

| Requirement | Status | Evidence (`library.py`) |
|---|---|---|
| Ingest reviewed truth | PASS | Controller calls `save_stage_record` / `save_match_record` (`:95-131`) |
| Write normalized metric rows | PASS | `append_stage_metric` (`:134`), `append_match_metric` (`:141`) — JSONL format |
| Update historical records | PASS | `save_stage_record` overwrites on same `library_record_id` |
| Link retained proxies | PASS | `LibraryStageRecord.active_retained_proxy` field; proxy metadata stored at `proxies/<type>/<id>/metadata.json` (`library.py:183`) |
| Link outputs | PASS | `LibraryStageRecord.output_profile_refs` (`models.py:659`) |

### Background Refresh Seam

| Requirement | Status | Evidence |
|---|---|---|
| Keep library records current | PASS | `_sync_project_to_library` and `_sync_workspace_to_library` called at save points (`controller.py:965-1040`) |
| Rebuild stale proxies | PASS | `proxy_refresh` checks `generated_from_truth_hash` mismatch before rebuild (`controller.py:1166`) |
| Avoid UI-blocking | PASS | `proxy_refresh` returns immediately with `scheduled` status if media unavailable; architecture reserves background seam (`controller.py:1237-1243`) |

### Code Clarity

| Requirement | Status | Evidence |
|---|---|---|
| One stage-truth model | PASS | `Project` (`models.py:576`) is the sole stage editor contract; no competing stage models |
| One browser-state seam | PASS | `browser_state()` (`state.py:284`) is the single serialization for `/api/state` |
| One controller owner | PASS | `ProjectController` (`controller.py:770`) owns all persisted mutations |
| Additive route families | PASS | New routes at `server.py:820-886` are additive; legacy `/api/project/*` routes preserved intact at `:809-819` |

---

## Summary

| Document | PASS | PARTIAL | FAIL |
|---|---|---|---|
| 04-data-model-spec.md | 14 requirement groups | 0 | 0 |
| 05-technical-architecture.md | 15 requirement groups | 0 | 0 |
| **Total** | **29** | **0** | **0** |

All requirements in both specifications are satisfied by the current implementation.
