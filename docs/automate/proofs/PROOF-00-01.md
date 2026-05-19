# Proof: docs/automate/00-01 (Product Definition, Naming, Quality, Feature Matrix)

## 00-product-definition.md

| Requirement | Status | Evidence |
|---|---|---|
| MatchWorkspace exists in domain models | PASS | `src/splitshot/domain/models.py:606` — `class MatchWorkspace` with `match_id`, `stage_entries`, `match_output_profiles`, etc. |
| StageEntry exists in domain models | PASS | `src/splitshot/domain/models.py:621` — `class StageEntry` with `stage_id`, `relative_project_path`, `override_values`, etc. |
| OutputProfile exists in domain models | PASS | `src/splitshot/domain/models.py:633` — `class OutputProfile` with `output_id`, `frame_profile`, `metric_caption_preset`, `lead_in_card`, `brand_mark`, `subject_track_crop`, etc. |
| "Single Video" surface name exists in code | PARTIAL | No literal string "Single Video" in code. Concept present as `editor_scope = "single"` at `ui/controller.py:793`. State payload returns `"editor_scope": "single"` via `browser/state.py:23`. |
| "Multi Video" surface name exists in code | PARTIAL | No literal string "Multi Video" in code. Concept present as `editor_scope = "multi"` at `ui/controller.py:825`. State payload returns `"editor_scope"` via `browser/state.py:23`. |
| "Performance Library" surface name exists in code | PARTIAL | No literal string "Performance Library" in code. Concept implemented via `persistence/library.py` with `LibraryStageRecord`, `LibraryMatchRecord`, `library_root()` etc. State payload includes `"library_summary"` at `browser/state.py:396`. |
| Project remains the authoritative stage-truth model (not replaced) | PASS | `class Project` at `domain/models.py:576` is the sole stage-truth model. Only one `class Project` in entire `src/` directory. `LibraryStageRecord` at `:650` is a library indexing record, not a stage-truth replacement. |
| New systems are additive (workspace alongside project) | PASS | `MatchWorkspace` (models.py:606) is a separate dataclass from `Project` (models.py:576). Controller maintains both `self.project` and `self.workspace`. Workspace owns `stage_entries` referencing project bundles by path; it does not duplicate stage truth. |
| Multi Video is a workspace layer, not a second truth model | PASS | `MatchWorkspace` has `shared_defaults` and `StageEntry.override_values` for inheritance, but delegates stage truth to individual `Project` bundles referenced by `relative_project_path`. Controller resolves settings via `resolve_setting()` chain at `controller.py:1827`. |
| Performance Library is separate persisted system beside project bundles | PASS | `persistence/library.py` saves to `~/.splitshot/library/`, fully independent of `persistence/projects.py` bundle structure. Library records reference stage/match IDs but do not embed project data. |
| Existing single-project workflows must open without conversion | PASS | `save_project`/`load_project` at `persistence/projects.py:224/232` are fully preserved. Controller opens single projects via `new_project`/`open_project` routes at `server.py:817-818`. No conversion prompts. |
| All new output behavior preserves one reviewed truth record with many output realizations | PASS | `OutputProfile` (models.py:633) links to a scope (`scope_type`/`scope_id`) but contains only output-layer config (frame, captions, card, mark, crop). Timing/scoring truth remains in the underlying `Project`. |

## 00a-splitshot-naming-contract.md

| Requirement | Status | Evidence |
|---|---|---|
| No forbidden competitor names in implementation code | PASS | Grep for "Shot Cut", "Auto Trim", "Performance subtitles", "Split Sync", "Stage Mix", "Portrait tracking", "Intro title cards", "Custom watermarks", "Camera-role" across entire `src/splitshot/` returns **zero matches** in Python, JS, and HTML files. |
| "Run Window" used instead of "Auto Trim" | PASS | `run_window` in `controller.py:1445,1520`, `_resolve_run_window` at `:1520`. No "Auto Trim" or "auto_trim" in code. |
| "Metric Captions" used instead of "Performance subtitles" | PASS | `metric_caption_preset` in `models.py:640`, `controller.py:754,1550`, `export/pipeline.py:842,847,873`, `persistence/workspaces.py:79,122`. No "subtitle" or "performance_subtitle" in core naming. |
| "Angle Align" used instead of "Split Sync" | PASS | `angle_align` method at `controller.py:1699`, route `/api/angle/align` at `server.py:881`, handler `_handle_angle_align` at `server.py:2175`. No "split_sync" in code. |
| "Match Recap" used instead of "Merge (many stages)" | PASS | `match_recap_preview` at `controller.py:1579`, `profile_kind: "match_recap"` at `controller.py:1615`. |
| "Stage Composite" used instead of "Merge (same stage)" | PASS | `stage_composite_preview` at `controller.py:1630`, `profile_kind: "stage_composite"` at `controller.py:1641`. |
| "Angle Director" used instead of "Stage Mix" | PASS | `angle_director_generate` at `controller.py:1728`, route `/api/angle/director/generate` at `server.py:882`. No "stage_mix" in code. |
| "Frame Profiles" used instead of "Export ratios" | PASS | `frame_profile` field in `models.py:639`, `controller.py:753`, `export/pipeline.py:830,838`, `persistence/workspaces.py:78`. |
| "Subject Track Crop" used instead of "Portrait tracking" | PASS | `subject_track_crop` field in `models.py:643`, `controller.py:757`, `persistence/workspaces.py:82,137`. |
| "Lead-In Card" used instead of "Intro title cards" | PASS | `lead_in_card` field in `models.py:641`, `controller.py:755`, `export/pipeline.py:843,848,882`. Also `_lead_in_card` on Project at `models.py:593`. |
| "Brand Mark" used instead of "Custom watermarks" | PASS | `brand_mark` field in `models.py:642`, `controller.py:756`, `export/pipeline.py:844,851,887`. Also `_brand_mark` on Project at `models.py:594`. |
| "Angle Roles" used instead of "Camera-role labeling" | PASS | `angle_role` in `controller.py:1667,1672,1745`. | 
| "Audio Mix Lanes" used instead of "Per-clip audio control" | PASS | `audio_mix` route `/api/audio/mix` at `server.py:884`, method `audio_mix_set` at `controller.py:1776`, `audio_gain`/`audio_muted`/`audio_primary` fields in clip dict at `controller.py:1669-1671`. |
| "Result Cards" used instead of "Per-clip score metadata" | PASS | `result_card` in `controller.py:1606,1797`, route `/api/result-cards/resolve` at `server.py:885`. |
| Competitor names not in route names | PASS | All new routes use SplitShot-native labels: `/api/angle/align`, `/api/angle/director/*`, `/api/audio/mix`, `/api/result-cards/resolve`, `/api/output-profiles/*`, `/api/workspace/*`. |
| Competitor names not in persisted field names | PASS | All persisted fields use native names: `frame_profile`, `metric_caption_preset`, `lead_in_card`, `brand_mark`, `subject_track_crop` at `persistence/workspaces.py:78-82`. |
| Competitor names not in browser state keys | PASS | State payload at `browser/state.py` uses `editor_scope`, `output_profiles`, `workspace_stage_entries`, `workspace_shared_defaults`, `library_summary`. |

## 00b-implementation-quality-contract.md

| Requirement | Status | Evidence |
|---|---|---|
| No duplicate stage-truth models | PASS | Only one `class Project:` in entire `src/` directory at `domain/models.py:576`. `LibraryStageRecord` at `:650` is a library index, not stage truth. `MatchWorkspace` at `:606` is a workspace container, not truth. |
| Persistence responsibilities separated | PASS | Three distinct persistence modules: `persistence/projects.py` (single-stage bundles), `persistence/workspaces.py` (match workspaces), `persistence/library.py` (library index/proxy records). Each has its own save/load round-trip. |
| Controller responsibilities separated | PASS | Single `ProjectController` class at `ui/controller.py:770`. Controller owns `self.project`, `self.workspace`, `self.editor_scope`, `self._output_profiles`, `self._stage_clips`. Methods organized by feature domain (workspace, profiles, clips, angle, audio, results). |
| Browser-state responsibilities separated | PASS | `browser/state.py` builds state dict independently from controller mutations. Includes `_build_workspace_context` at `:19`, `_build_library_summary` at `:107`, `_build_proxy_summary` at `:134`. |
| Export responsibilities separated | PASS | `export/pipeline.py` contains `export_project`, `_apply_metric_captions_to_project` at `:873`, `_apply_lead_in_card_to_project` at `:882`, `_apply_brand_mark_to_project` at `:887`. |
| Every new route has controller + persistence wiring | PASS | Workspace routes (`/api/workspace/*` at server.py:820-829) → `ProjectController` methods (create/open/save workspace, stage add/remove/open) → `persistence/workspaces.py`. Library routes (`/api/library/*` at server.py:866-872) → handlers → `persistence/library.py`. Output profile routes (`/api/output-profiles/*` at server.py:873-877) → controller `output_profile_*` methods. Angle/audio/result routes (`/api/angle/*`, `/api/audio/*`, `/api/result-cards/*` at server.py:881-885) → controller methods. All handler implementations (server.py:1949-2216) call controller methods directly. |
| No route without persistence | PASS | All new route families have persistence backing: workspace routes → `persistence/workspaces.py` (save/load workspace.json), library routes → `persistence/library.py` (JSON records on disk), output profiles → persisted inside `MatchWorkspace.match_output_profiles` + `OutputProfile` serialization. |
| No UI without route | PASS | Every new feature feature has both a controller method and a browser server route. Handler implementations at server.py:2096-2216 all defer to `self.controller.*` methods. State payload includes workspace context and output profiles for JS consumption at `browser/state.py:19-96`. |
| No partial delivery (route without persistence, UI without route) | PASS | All 13 adopted features from the feature matrix have: model fields, controller methods, server routes/handlers, and persistence serialization. See Feature Matrix section below for per-feature evidence. |
| Project preserved as authoritative stage-truth model | PASS | Project class at `models.py:576` unchanged in structure. All existing project routes (`/api/project/*`) preserved at server.py:813-819. `save_project`/`load_project` at `persistence/projects.py:224/232` unmodified. |
| SplitShot-native names consistent across all layers | PASS | `frame_profile`, `metric_caption_preset`, `lead_in_card`, `brand_mark`, `subject_track_crop` appear identically in models (models.py:639-643), persistence (workspaces.py:78-82), controller (controller.py:753-757), and export pipeline (pipeline.py:830-851). |

## 01-shootingcut-feature-matrix.md

| Requirement (Adopt Feature) | Status | Evidence |
|---|---|---|
| Detection Review (Smart audio analysis) | PASS | Pre-existing core system. `AnalysisState` at `models.py:275`, `analyze_video_audio` at `analysis/detection.py`, beep/shot detection, waveform review in UI. Listed as "Already core" in matrix. |
| Run Window | PASS | `_resolve_run_window` at `controller.py:1520` derives start/end from beep + last shot with padding. `run_window` key in render plan at `controller.py:1445,1488`. |
| Metric Captions | PASS | `metric_caption_preset` field in `OutputProfile` (models.py:640). `resolve_metric_captions` at `controller.py:1550` builds caption data from reviewed truth. `_apply_metric_captions_to_project` at `export/pipeline.py:873`. |
| Angle Align | PASS | `angle_align` method at `controller.py:1699`. Route `/api/angle/align` at `server.py:881`. Handler at `server.py:2175`. Computes sync offsets across clips. |
| Match Recap | PASS | `match_recap_preview` at `controller.py:1579` builds multi-stage recap plan from workspace stages. Returns clips per stage with `result_card` support. |
| Stage Composite | PASS | `stage_composite_preview` at `controller.py:1630` builds composite render plan for one stage with multiple clips. Uses `_get_stage_clips` at `:1653`. |
| Angle Director | PASS | `angle_director_generate` at `controller.py:1728` generates cut plan based on role priority. `angle_director_override_cut` at `:1758` supports manual overrides. Routes at `server.py:882-883`. |
| Frame Profiles | PASS | `frame_profile` field in `OutputProfile` (models.py:639). Used in export pipeline at `pipeline.py:830,838` to select aspect ratio. |
| Subject Track Crop | PASS | `subject_track_crop` field in `OutputProfile` (models.py:643). Serialized in `_output_profile_to_dict` at `persistence/workspaces.py:82`. Referenced in `_profile_to_dict` at `controller.py:1512`. |
| Lead-In Card | PASS | `lead_in_card` field in `OutputProfile` (models.py:641). `_lead_in_card` on `Project` (models.py:593). `_apply_lead_in_card_to_project` at `export/pipeline.py:882`. |
| Brand Mark | PASS | `brand_mark` field in `OutputProfile` (models.py:642). `_brand_mark` on `Project` (models.py:594). `_apply_brand_mark_to_project` at `export/pipeline.py:887`. |
| Angle Roles | PASS | `angle_role` used in clip dicts at `controller.py:1667,1672`. Valid roles include "primary", "follow", "static", "detail" per `angle_director_generate` at `:1737`. |
| Cut Override Plan | PASS | `cut_override_plan` field per clip at `controller.py:1673`. `angle_director_override_cut` at `:1758` appends manual cut overrides. Route `/api/angle/director/override` at `server.py:883`. |
| Audio Mix Lanes | PASS | `audio_gain`, `audio_muted`, `audio_primary` fields in clip dict at `controller.py:1669-1671`. `audio_mix_set` at `:1776` sets gain/mute/primary. Route `/api/audio/mix` at `server.py:884`. |
| Result Cards | PASS | `resolve_result_cards` at `controller.py:1797` builds stage transition cards from workspace entries. `result_card` key in match recap preview at `:1606`. Route `/api/result-cards/resolve` at `server.py:885`. |

## Summary

- Total requirements: 52
- PASS: 49
- PARTIAL: 3
- FAIL: 0

**Partials detail:**
- "Single Video", "Multi Video", "Performance Library" surface names: These exact strings do not appear as literals in the implementation code. The concepts are fully implemented via `editor_scope` ("single"/"multi") and the library persistence module. The product definition names them as user-facing surfaces, so the absence of literal strings is minor but technically PARTIAL per the verification directive "surface names exist in code".
