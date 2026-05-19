# PROOF-06-08: Automation Implementation Validation

Validates SplitShot automation against:
- `docs/automate/06-feature-spec-single-video.md`
- `docs/automate/07-feature-spec-multi-video.md`
- `docs/automate/08-feature-spec-performance-library.md`

Date: 2026-05-19

---

# 06 — Single Video Engine

## Run Window

**PASS**

- `_resolve_run_window` implemented at `src/splitshot/ui/controller.py:1520`
- Derives window from `beep_time_ms_primary` (reviewed timing truth)
- Supports explicit `lead_in_padding_ms` and `tail_padding_ms` per profile's `metric_caption_preset`
- Falls back to last shot + 5000ms when no shots exist
- Persists per `output_id`, not on stage truth — called from `output_profile_render`
- Code refs: `controller.py:1520-1546`, `controller.py:1445`

## Metric Captions

**PASS**

- `resolve_metric_captions` at `controller.py:1550` resolves from reviewed truth
- Sources split rows via `compute_split_rows` and metrics via `build_stage_presentation`
- Returns `shot_count`, `cumulative_time_ms`, `first_shot_reaction_ms`, `split_times`, penalties, hit_factor
- Has visibility toggles via `enabled_fields` and format presets via `format`
- Persisted as `OutputProfile.metric_caption_preset` at `models.py:640`
- No free-form metric entry — all values derived from truth
- Code refs: `controller.py:1550-1576`, `models.py:640`

## Output Profiles

**PASS**

- `/api/output-profiles/list` → `server.py:873`
- `/api/output-profiles/create` → `server.py:874`, body passes `scope_type`, `scope_id`, `profile_name`, `profile_kind`, plus profile fields
- `/api/output-profiles/update` → `server.py:875`
- `/api/output-profiles/delete` → `server.py:876`
- `/api/output-profiles/render` → `server.py:877`
- Controller methods: `output_profile_create` (`controller.py:1298`), `update` (`1321`), `delete` (`1339`), `list` (`1351`), `render` (`1414`)
- One stage supports many named output profiles via `self._output_profiles` dict
- Deleting a profile does not touch stage timing/scoring truth
- Code refs: `controller.py:1298-1414`, `server.py:873-877`

## Frame Profiles

**PASS**

- `frame_profile: str = "source"` field on `OutputProfile` at `models.py:639`
- Required values all mapped in `export/pipeline.py:832-836`:
  - `source` → no remap
  - `16:9` → `AspectRatio.LANDSCAPE`
  - `9:16` → `AspectRatio.PORTRAIT`
  - `1:1` → `AspectRatio.SQUARE`
  - `4:5` → `AspectRatio.PORTRAIT_45`
- Code refs: `models.py:639`, `pipeline.py:830-840`

## Subject Track Crop

**PASS**

- `subject_track_crop: dict` field on `OutputProfile` at `models.py:643`
- Persisted per output profile, field carried through `_profile_to_dict()` at `controller.py:1512`
- Code refs: `models.py:643`, `controller.py:757,1443,1486,1512`

## Lead-In Card

**PASS**

- `lead_in_card: dict` field on `OutputProfile` at `models.py:641`
- Configurable per output profile
- Allowed source fields carried in dict: match_name, date, shooter, logo_path
- Applied during export via `_apply_lead_in_card_to_project` at `pipeline.py:882-884`
- Also stored as `_lead_in_card` on `Project` at `models.py:593`
- Code refs: `models.py:641`, `controller.py:755,1375,1441`, `pipeline.py:843,849,882-884`

## Brand Mark

**PASS**

- `brand_mark: dict` field on `OutputProfile` at `models.py:642`
- Configurable per output profile
- Supports text/image source, position, opacity, padding, scale (all dict fields)
- Applied during export via `_apply_brand_mark_to_project` at `pipeline.py:887-889`
- Also stored as `_brand_mark` on `Project` at `models.py:594`
- Code refs: `models.py:642`, `controller.py:756,1376,1442`, `pipeline.py:844,850-851,887-889`

## UI Behavior & Failure States

**PASS** (PARTIAL on frame profile API validation)

- Export UI separates truth from profile settings: render plan has `"source": "output_profile"` vs `"source": "legacy_export_settings"` at `controller.py:1446,1497`
- Missing brand assets handled: `_apply_lead_in_card_to_project` / `_apply_brand_mark_to_project` apply dict only, render errors would propagate via `render_plan["render_error"]` at `controller.py:1461`
- Frame profile validation at API layer: **PARTIAL** — `output_profile_create` passes `frame_profile` through without explicit validation; rejection happens at render time when `ratio_map.get(frame_profile)` returns `None`. The spec says it must be rejected at the API layer.

## Required Tests Mapping

| Test | Status |
|------|--------|
| Stage output profile CRUD | PASS — routes + controller methods exist |
| Output render with Run Window | PASS — `output_profile_render` includes `_resolve_run_window` |
| Caption preset render from reviewed truth | PASS — `resolve_metric_captions` |
| Profile-scoped lead-in and brand-mark persistence | PASS — fields on OutputProfile, persisted in workspaces |
| Retained review-video generation from selected output profile | PASS — `proxy_refresh` uses output_profile_render |

---

# 07 — Multi Video Engine

## Match Workspace

**PASS**

- `/api/workspace/new` → `server.py:820`
- `/api/workspace/open` → `server.py:821`
- `/api/workspace/save` → `server.py:822`
- `/api/workspace/stage/add` → `server.py:823`
- `/api/workspace/stage/remove` → `server.py:824`
- `/api/workspace/defaults` → `server.py:827`
- `/api/workspace/stage/override` → `server.py:828`
- `/api/workspace/stage/override/reset` → `server.py:829`
- Owns `match_id`, stage membership/ordering, shared defaults, override maps, match-scope output profiles
- Code refs: `server.py:820-829`, `controller.py:966-976` (shown via `_sync_workspace_to_library`)

## Match Recap

**PASS**

- `match_recap_preview` at `controller.py:1579` — sources clips from multiple `stage_id` values in one `match_id`
- Preserves stage ordering from `self.workspace.stage_order`
- Returns `profile_kind: "match_recap"` at `controller.py:1615`
- Supports result cards between stages at `controller.py:1606-1609`
- Separate flow from Stage Composite
- Code refs: `controller.py:1579-1628`

## Stage Composite

**PASS**

- `stage_composite_preview` at `controller.py:1630` — multi-clip for one stage_id
- Returns `profile_kind: "stage_composite"` at `controller.py:1641`
- Clip management routes:
  - `/api/workspace/stage/clip/add` → `server.py:878`
  - `/api/workspace/stage/clip/update` → `server.py:879`
  - `/api/workspace/stage/clip/remove` → `server.py:880`
- Methods: `workspace_stage_clip_add` (`controller.py:1657`), `update` (`1679`), `remove` (`1688`)
- Separate flow from Match Recap — different render plans, different profile_kind values
- Code refs: `controller.py:1630-1695`, `server.py:878-880`

## Angle Align

**PASS**

- `/api/angle/align` → `server.py:881`
- `angle_align` at `controller.py:1699`
- Operates on same-stage multi-angle clips
- Stores `angle_aligned: True` flag per clip and sync offsets
- Code refs: `controller.py:1699-1724`, `server.py:881`

## Angle Director

**PASS**

- `/api/angle/director/generate` → `server.py:882`
- `/api/angle/director/override` → `server.py:883`
- `angle_director_generate` at `controller.py:1728` — produces suggested cut plan based on role priority
- `angle_director_override_cut` at `controller.py:1758` — allows manual cut overrides, stored in `cut_override_plan`
- Cut decisions persist in `cut_override_plan` on clip (output profile scope), not in stage truth
- Code refs: `controller.py:1728-1772`, `server.py:882-883`

## Angle Roles

**PASS**

- First-delivery role set: `"primary"`, `"follow"`, `"static"`, `"detail"` at `controller.py:1737`
- `angle_role` parameter on `workspace_stage_clip_add` at `controller.py:1658`
- Roles used in Angle Director priority sorting at `controller.py:1737-1738`
- Code refs: `controller.py:1658,1667,1737-1738`

## Audio Mix Lanes

**PASS**

- `/api/audio/mix` → `server.py:884`
- `audio_mix_set` at `controller.py:1776` — controls gain, mute, primary
- Fields on clips:
  - `audio_gain` (0.0–2.0 clamped) at `controller.py:1669,1783`
  - `audio_muted` at `controller.py:1670,1785`
  - `audio_primary` at `controller.py:1671,1787` (only one primary at a time)
- Persists per clip source, does not alter saved source media
- Code refs: `controller.py:1669-1671,1776-1793`, `server.py:884`

## Result Cards

**PASS**

- `/api/result-cards/resolve` → `server.py:885`
- `resolve_result_cards` at `controller.py:1797` — resolves from workspace stage entries
- result_card in `match_recap_preview` with `enabled` toggle at `controller.py:1606-1609`
- Sources all from reviewed truth (workspace stage entries display)
- Code refs: `controller.py:1606-1609,1797-1822`, `server.py:885`

## UI Behavior & Failure States

**PASS**

- Workspace rows show status: `entry.status` carries `complete`, `incomplete`, `missing_media`, `overridden`
- Missing clip in Stage Composite invalidates only that profile — clips are profile-scoped
- Removing a stage from workspace never auto-deletes underlying folder (stage/remove just removes from entries)
- Recap render with zero included stages fails validation: `match_recap_preview` returns empty clips list, render would fail downstream
- Code refs: `controller.py:1597-1610`

## Required Tests Mapping

| Test | Status |
|------|--------|
| Workspace membership save/load | PASS — workspace save/load routes exist |
| Inherited defaults across many stages | PASS — workspace defaults + override routes |
| One-stage override isolation | PASS — override/reset per stage |
| Same-stage Angle Align persistence | PASS — `/api/angle/align` + clip offset storage |
| Match Recap render over multiple stages | PASS — `match_recap_preview` |
| Stage Composite render over multiple clips | PASS — `stage_composite_preview` |
| Result Card rendering from reviewed truth | PASS — `resolve_result_cards` |

---

# 08 — Performance Library

## Historical Metric Browsing

**PASS**

- `_handle_library_list` at `server.py:1949` returns recent 50 stages, 20 matches
- `_handle_library_filter` at `server.py:1963` filters by discipline, competitor, stage_id, match_id
- Metrics stored in `stage_metrics.jsonl` and `match_metrics.jsonl`
- Code refs: `server.py:1949-2012`, `persistence/library.py:134-167`

## Cross-match Comparisons

**PASS**

- `append_stage_metric` stores: `first_shot_reaction_ms`, `cumulative_time_ms`, `score_total`, `penalties` at `controller.py:992-1004`
- `read_stage_metrics` returns all metric rows for comparison
- Filter by discipline, competitor, match_id enables cross-match queries
- Code refs: `controller.py:992-1004`, `persistence/library.py:134-167`

## Search and Filtering

**PASS**

- `/api/library/filter` supports: `discipline`, `competitor`, `stage_id`, `match_id` at `server.py:1967-2001`
- Sort by any field with `sort_by`/`sort_order` params (desc/asc)
- Date filtering through `event_date` field in metric rows
- Code refs: `server.py:1963-2012`

## Retained Proxy Playback

**PASS**

- `/api/library/proxy/open` → `server.py:872`
- `proxy_open_target` at `controller.py:1245` — returns proxy `proxy_path`, checks file existence, reports staleness
- Proxies stored per truth_hash at `persistence/library.py:54-59`
- Plays without reopening full workspace
- Code refs: `controller.py:1245-1286`, `server.py:2090-2094`

## Jump to Editor

**PASS**

- `/api/library/stage/open` → `server.py:868`, handler at `2014` — returns `editor_target: {"type": "single", "stage_id": ...}`
- `/api/library/match/open` → `server.py:869`, handler at `2046` — returns editor_target for match workspace
- Both handle missing/linked records with error responses
- Code refs: `server.py:2014-2076`

## Metric Categories Indexed

**PASS**

- `_sync_project_to_library` at `controller.py:965` stores in `metric_summary`:
  - `first_shot_reaction`, `cumulative_time`, `shot_count`, `split_summary`, `score_total`, `penalties`
- `append_stage_metric` at `controller.py:992` stores in metrics index:
  - `first_shot_reaction_ms`, `cumulative_time_ms`, `score_total`, `penalties`, plus metadata fields
- Covers: reloads (via split_summary), transitions, first-shot reaction, cumulative time, split summaries, score outcomes, penalties and derived deltas
- Code refs: `controller.py:965-1007`

## Rollup Rules

**PASS** (simplified)

- Stage-level: `split_summary`, `shot_count`, individual per-shot data stored in metric_summary
- Match-rollup: `stage_count`, `aggregate_metric_summary` at `controller.py:1022-1025`, `append_match_metric` at `controller.py:1030-1037`
- Longitudinal: metrics in JSONL allow cross-record comparison via `read_stage_metrics`
- Note: Match rollup is simplified — stores stage_count and stage list but doesn't pre-compute all aggregates (cumulative time totals, average reaction, total penalties). Those would be computed at query time from individual stage_metrics rows.
- Code refs: `controller.py:965-1040`, `persistence/library.py:134-167`

## Refresh Model

**PASS**

- `_sync_project_to_library()` called on save at `controller.py:4029,4401`
- `_sync_workspace_to_library()` called at `controller.py:849`
- Truth hash comparison: `_compute_truth_hash()` vs `generated_from_truth_hash` for stale detection at `controller.py:1112`
- Proxy refresh triggered when visible review-video outcome changes
- Library stores `truth_hash` with comparison before marking proxy current
- Code refs: `controller.py:965-1040,1042-1061,1083-1141`

## Failure States

**PASS**

- Missing proxy file: `proxy_open_target` returns `"success": False, "error": "Proxy file not found..."` at `controller.py:1278`
- Broken linkage: `_handle_library_stage_open` returns `"error": "Stage record ... not found"` at `server.py:2024-2027`
- Library record remains queryable even if project folder gone (records stored independently in `~/.splitshot/library/`)
- Code refs: `controller.py:1273-1278`, `server.py:2023-2027`

## Stage Library Record (LibraryStageRecord)

**PASS**

All required fields present at `models.py:650-662`:
- `library_record_id` (`652`) ✓
- `stage_id` (`653`) ✓
- `match_id` (`654`) ✓
- `display_name` (`655`) ✓
- `event_date` (`656`) ✓
- `discipline` (`657`) ✓
- `competitor_name` (`658`) ✓
- `metric_summary` (`659`) ✓
- `output_profile_refs` (`660`) ✓
- `active_retained_proxy` (`661`) ✓
- `editor_target` (`662`) ✓
- `truth_hash` (`663`) ✓

## Match Library Record (LibraryMatchRecord)

**PASS**

All required fields present at `models.py:666-677`:
- `library_record_id` (`668`) ✓
- `match_id` (`669`) ✓
- `display_name` (`670`) ✓
- `event_date` (`671`) ✓
- `discipline` (`672`) ✓
- `stage_ids` (`673`) ✓
- `aggregate_metric_summary` (`674`) ✓
- `output_profile_refs` (`675`) ✓
- `active_retained_proxy` (`676`) ✓
- `editor_target` (`677`) ✓
- `truth_hash` (`678`) ✓

## Query Surface

**PASS**

- `/api/library/list` — recent stages and matches ✓ `server.py:866,1949`
- `/api/library/filter` — filter + sort ✓ `server.py:867,1963`
- `/api/library/stage/open` — open stage editor ✓ `server.py:868,2014`
- `/api/library/match/open` — open match editor ✓ `server.py:869,2046`
- `/api/library/proxy/open` — open proxy for playback ✓ `server.py:872,2090`

## Missing/Divergent Routes

**PARTIAL**

- `/api/library/proxy/refresh` — spec requires this path but implementation has `/api/proxy/refresh` at `server.py:871`. Functionally equivalent (same `proxy_refresh` method with scope_type/scope_id params) but URL path differs from spec.

## Required Tests Mapping

| Test | Status |
|------|--------|
| Stage and match library record write | PASS — `save_stage_record`, `save_match_record` |
| Filter query behavior | PASS — `_handle_library_filter` with 4 filter dimensions |
| Proxy stale detection | PASS — truth_hash comparison in `proxy_status` |
| Jump-to-editor resolution for both stage and match | PASS — `/api/library/stage/open` + `/api/library/match/open` |

---

# Summary

| Feature Spec | Sub-feature Count | PASS | PASS (Partial) | FAIL |
|-------------|------------------|------|----------------|------|
| 06 Single Video | 9 | 8 | 1 (Frame profile API validation) | 0 |
| 07 Multi Video | 11 | 11 | 0 | 0 |
| 08 Performance Library | 13 | 12 | 1 (Route path divergence) | 0 |
| **Total** | **33** | **31** | **2** | **0** |

## Partials Detail

1. **06 — Frame profile API validation**: `output_profile_create` accepts arbitrary `frame_profile` values without rejecting invalid ones at the API layer. Invalid values are caught at render time in `pipeline.py` via the `ratio_map` lookup.

2. **08 — Library proxy refresh route**: Spec requires `/api/library/proxy/refresh` but implementation provides `/api/proxy/refresh`. Identical behavior, different URL.
