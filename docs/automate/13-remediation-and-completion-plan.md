# Remediation and Completion Plan

This document audits the automation implementation (Phases 1-7) against the acceptance criteria in `10-acceptance-and-proof.md` and defines the remaining work to reach 100% completion.

## Current Status

| Category | Status |
|---|---|
| Domain models (7 new dataclasses) | ✅ Complete |
| Persistence (workspace, library) | ✅ Complete |
| Controller methods (~30 new) | ✅ Complete |
| Browser state expansion | ✅ Complete |
| API routes (30 new) | ✅ Complete |
| New tests (42 targeted) | ✅ Complete |
| Legacy compatibility | ✅ Proven (36 persistence tests pass) |
| Ruff lint | ✅ 0 errors |
| Full test suite baseline | 487 pass / 2 pre-existing fail |

---

## Gap 1: OutputProfile not persisted to disk (HIGH)

**Problem**: `controller._output_profiles` is a `dict[str, OutputProfile]` in memory only. Stage-scoped profiles vanish on restart. Match-scoped profiles in `workspace.match_output_profiles` are listed but not serialized in `workspace.json`.

**Fix**:
1. Update `workspaces.py` `_workspace_to_dict` / `_workspace_from_dict` to serialize `match_output_profiles` as `list[dict]`
2. For stage-scoped profiles, add serialization in `project.json` under an `"output_profiles"` key (or create a separate `profiles.json` alongside `project.json`)
3. Wire `save_project` / `load_project` to persist stage-scoped output profiles
4. Wire `save_workspace` / `load_workspace` to persist match-scoped output profiles
5. Add `_serialize_output_profile` / `_deserialize_output_profile` helpers in `workspaces.py`

**Tests**: `test_output_profile_persistence_roundtrip` in `test_workspace_persistence.py`

---

## Gap 2: Export pipeline not wired to OutputProfile (HIGH)

**Problem**: The actual ffmpeg/QPainter render pipeline (`export/pipeline.py`) uses `Project.export` (legacy `ExportSettings`) and does not read `OutputProfile` configurations. Run Window trim, Metric Captions overlay, Lead-In Card prepend, Brand Mark watermark exist as data but are never rendered into video.

**Fix**:
1. Extend `export/pipeline.py` to accept an optional `OutputProfile` (or `output_profile_id`) parameter
2. Implement `Run Window` trim logic — use `start_ms`/`end_ms` from `_resolve_run_window` to clip the input
3. Implement `Metric Captions` text overlay — derive from `compute_split_rows` and `profile.metric_caption_preset`
4. Implement `Lead-In Card` frame prepend — render identity frame with match name, date, shooter, optional logo
5. Implement `Brand Mark` watermark overlay — positioned text/image at configurable opacity, position, scale
6. Update `controller.output_profile_render` to delegate to the export pipeline when a real video path exists

**Tests**: 
- `test_run_window_trim` in `test_export.py`
- `test_metric_captions_render` in `test_export.py`
- `test_lead_in_card_render` in `test_export.py`
- `test_brand_mark_render` in `test_export.py`

---

## Gap 3: Proxy video does not render (HIGH)

**Problem**: `controller.proxy_refresh` creates a `RetainedProxyRecord` metadata entry but never renders the actual review-proxy video file. The export pipeline (Gap 2) must produce the proxy artifact.

**Fix**:
1. In `controller.proxy_refresh`, after profile resolution, call a render helper that invokes the export pipeline with lightweight proxy settings (lower resolution, h264_aac codec)
2. After render produces a file, update the `RetainedProxyRecord` with actual `width`, `height`, `duration_ms`, `file_size_bytes`, `relative_path`
3. Write the rendered proxy file to `<library_root>/proxies/stages/<stage_id>/<truth_hash>.mp4`
4. Wire proxy stale detection: on `proxy_status`, compare current truth hash with stored proxy's `generated_from_truth_hash`

**Tests**:
- `test_proxy_video_metadata_created` in `test_persistence/test_workspace_persistence.py`
- `test_proxy_stale_detection_after_truth_change`
- `test_proxy_reopen_path_resolves`

---

## Gap 4: No packaged or automation E2E proof (HIGH)

**Problem**: None of the 5 E2E scenarios from `10-acceptance-and-proof.md` have been executed against the packaged app or as an automated integration flow. Source/browser/persistence contracts are proven, but visible-flow proof is missing.

**Fix**:
1. Create `scripts/testing/test_automation_e2e.py` that exercises all 5 E2E scenarios against the running backend:
   - Single Video reviewed-output flow
   - Multi Video shared-default and Match Recap flow
   - Stage Composite and Angle Align flow
   - Performance Library browse and reopen flow
   - (Packaged-app flow deferred until packaging infrastructure available)
2. Each scenario validates route responses (no real video rendering required — check structured payload correctness and deterministic id stability)
3. Run browser audit scripts against a local server:
   - `uv run python scripts/audits/browser/run_browser_interaction_audit.py`
   - `uv run python scripts/audits/browser/run_browser_ui_surface_audit.py`
   - `uv run python scripts/audits/browser/run_browser_export_matrix.py`

**Tests**: `uv run python scripts/testing/test_automation_e2e.py`

---

## Gap 5: Workspace media serving unhandled (MEDIUM)

**Problem**: When a stage is opened from a workspace (`workspace_open_stage`), `self.project_path` changes to `<workspace>/Stages/<stage_id>/`. Browser media proxy routes (`/media/primary`, `/media/secondary`) resolve from `self.project.primary_video.path`. Relative paths in the nested stage project should already resolve correctly via the existing `_resolve_saved_paths` logic, but this needs verification.

**Fix**:
1. Verify that `load_project()` correctly resolves relative paths against the nested stage directory
2. The existing `_resolve_saved_paths` in `projects.py` already handles relative-to-absolute path resolution against `project_path`
3. Add test: verify `/media/primary` HTTP route resolves correctly when stage is opened from workspace

---

## Gap 6: OutputProfile / ExportSettings coexistence (MEDIUM)

**Problem**: `Project.export` (legacy `ExportSettings` dataclass) still exists on every `Project`. New `OutputProfile` system lives beside it. When rendering, no explicit rule determines which one wins.

**Fix**:
1. Document the rule in `controller.output_profile_render`: if an `OutputProfile` exists for the scope, it takes priority. If no profile found, fall back to `Project.export` legacy behavior
2. `Project.export` is preserved for backward compatibility; new work should prefer `OutputProfile`
3. Add `_legacy_export_fallback` method that translates `ExportSettings` to a render-plan-compatible dict

**Tests**: `test_export_fallback_when_no_profile`

---

## Gap 7: Inheritance eligibility table missing (MEDIUM)

**Problem**: `resolve_setting` does a blind dict lookup across all shared defaults. Settings like `detection_threshold` and `shotml_defaults` should never be overridden per-stage. No field-by-field eligibility filter exists.

**Fix**:
1. Define `INHERITANCE_ELIGIBLE_FIELDS` as a frozenset: `frame_profile`, `metric_caption_preset`, `lead_in_card`, `brand_mark`, `subject_track_crop`, `export_quality`, `export_preset`, `aspect_ratio`
2. In `workspace_set_defaults` and `workspace_set_stage_override`, filter incoming keys against this set
3. In `resolve_setting`, only check shared defaults and overrides for eligible fields

**Tests**: `test_inheritance_blocks_ineligible_fields`

---

## Gap 8: Initial match defaults empty (MEDIUM)

**Problem**: `new_workspace()` creates workspace with empty `shared_defaults`. Every new workspace should receive default values from the user's app-level effective settings.

**Fix**:
1. In `new_workspace()`, copy the inheritable subset of `self.effective_settings()` fields into `self.workspace.shared_defaults`
2. Match the pattern from `_apply_effective_settings_to_project` — extract only the eligible fields

---

## Gap 9: browser_state() library/proxy summary caches I/O on every poll (LOW)

**Problem**: `_build_library_summary` and `_build_proxy_summary` read from disk on every `/api/state` request, adding costly I/O for poll-based browser UIs.

**Fix**: Add `self._library_summary_cache` and `self._library_cache_timestamp` to controller. Refresh cache at most every 5 seconds. Read from cache otherwise.

---

## Gap 10: Two pre-existing test failures (LOW)

**Problem**: 
1. `test_browser_control_qa_matrix_documents_current_browser_suites` — QA matrix doc missing PiP row
2. `test_markers_import_shots_select_selected_marker_and_seek_video` — hidden marker element timeout

**Fix**:
1. Update `docs/project/browser-control-qa-matrix.md` to include the PiP row the test expects
2. Update the marker interaction test to use `state="attached"` instead of `state="visible"` for the hidden marker list

---

## Gap 11: Version sources mismatch (LOW)

**Problem**: CHANGELOG says `v1.1.0` but `__init__.py`, `pyproject.toml`, `electron/package.json`, `uv.lock` all say `1.0.4`.

**Fix**: Bump all 4 version sources to `1.1.0` together, then regenerate `uv.lock` with `uv lock`.

---

## Gap 12: Clip CRUD tests missing (LOW)

**Problem**: No direct test file for stage clip create/update/delete cycle used by Stage Composite.

**Fix**: Add `TestStageClips` class to `test_workspace_flows.py` with create, update, remove tests.

---

## Execution Order

| Phase | Gaps | Description |
|---|---|---|
| R1 | 1 | OutputProfile persistence |
| R2 | 7, 8 | Inheritance eligibility + initial defaults |
| R3 | 5, 6 | Media serving verification + ExportSettings coexistence |
| R4 | 2 | Export pipeline OutputProfile wiring |
| R5 | 3 | Proxy video render |
| R6 | 9, 12 | Performance caching + clip CRUD tests |
| R7 | 4 | E2E automation scenarios + browser audits |
| R8 | 10 | Pre-existing test failures |
| R9 | 11 | Version source bump |
| R10 | all | Final full validation |

---

## Validation Checklist (post-remediation)

```bash
# Lint
uvx ruff check .

# Runtime
uv run splitshot --check

# Persistence
uv run pytest tests/persistence/

# Browser contracts
uv run pytest tests/browser/test_browser_control.py
uv run pytest tests/browser/test_project_lifecycle_contracts.py
uv run pytest tests/browser/test_settings_defaults_truth_gate.py
uv run pytest tests/browser/test_merge_export_contracts.py

# Workspace flows
uv run pytest tests/browser/test_workspace_flows.py

# Export
uv run pytest tests/export/test_export.py
uv run pytest tests/export/test_merge_export_contracts.py

# Browser E2E
uv run pytest tests/browser/test_browser_full_app_e2e.py
uv run pytest tests/browser/test_browser_remaining_controls_e2e.py
uv run pytest tests/browser/test_metrics_e2e.py

# Browser audits
uv run python scripts/audits/browser/run_browser_interaction_audit.py
uv run python scripts/audits/browser/run_browser_ui_surface_audit.py
uv run python scripts/audits/browser/run_browser_export_matrix.py

# E2E automation scenarios
uv run python scripts/testing/test_automation_e2e.py

# Canonical grouped runner
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
```

## Acceptance Standard

The remediation is complete when:
- All 12 gaps are resolved
- All validation checklist commands pass (0 errors)
- Only known pre-existing failures remain in the full suite
- All new capabilities are persisted through at least one round-trip test
- The 4 source-level E2E scenarios pass against a running backend
