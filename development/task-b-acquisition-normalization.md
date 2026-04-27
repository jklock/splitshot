# Task B: Acquisition And Normalization Engine

## Goal
Implement remote match discovery, selected-match artifact download, and one-match-at-a-time normalization into the existing PractiScore import model.

This task does not edit browser static UI controls and does not add agent instruction files.

## Owned Files (Exclusive)
### Source
1. `src/splitshot/scoring/practiscore_web_extract.py` (new)
2. `src/splitshot/scoring/practiscore_sync_normalize.py` (new)
3. `src/splitshot/ui/controller.py`
4. `src/splitshot/browser/state.py`

### Tests
1. `tests/analysis/test_practiscore_web_extract.py` (new)
2. `tests/analysis/test_practiscore_sync_normalize.py` (new)
3. `tests/browser/test_practiscore_sync_controller.py` (new)

### Docs
1. `docs/userfacing/workflow.md`
2. `docs/userfacing/troubleshooting.md`

Do not edit files owned by Task A or Task C.

## Prerequisite Contract From Task A
1. Task A must expose the stable session route surface.
2. Task A must provide a reusable authenticated browser/session manager hook that Task B can consume.
3. Task A-owned routes in `server.py` must fail safely before Task B is merged and then delegate to Task B controller methods once they exist.

## Step-by-Step Code Directions
1. Create `src/splitshot/scoring/practiscore_web_extract.py`.
2. Add explicit entrypoints for:
   - discovering available remote matches from an authenticated session,
   - downloading one selected remote match by `remote_id`.
3. Accept the authenticated browser/session handle provided by Task A. Do not add separate login logic in Task B.
4. Discover one list of remote matches at a time and expose stable match objects with:
   - `remote_id`
   - `label`
   - `match_type`
   - `event_name`
   - `event_date`
5. When the user selects one remote match, download and cache these artifacts together:
   - the CSV or TXT file used for scoring import,
   - the selected-match HTML page,
   - a serialized summary snapshot of the selected-match metadata shown in the remote UI.
6. Cache the downloaded artifacts under a deterministic local sync-audit directory. Do not change project-bundle persistence in phase one.
7. Create `src/splitshot/scoring/practiscore_sync_normalize.py`.
8. Bridge the downloaded CSV or TXT artifact into the existing local import path by reusing the current PractiScore helper behavior.
9. Reuse and preserve the existing semantics from:
   - `describe_practiscore_file()`
   - `infer_practiscore_context()`
   - `import_practiscore_stage()`
10. Preserve the current name/place fallback and reimport-on-context-change behavior already exercised by the existing file-import tests.
11. Update `src/splitshot/ui/controller.py`.
12. Add controller methods that Task A routes can call for:
   - listing remote PractiScore matches,
   - importing one selected remote match,
   - surfacing stable browser-state payloads for session and sync status.
13. A successful selected-match import must replace the currently staged PractiScore source in the same way a new manual file import does.
14. Add deterministic error categories for:
   - expired authentication,
   - timeout or transient network failure,
   - malformed remote response,
   - missing required remote artifact,
   - normalization/import failure.
15. Update `src/splitshot/browser/state.py` so `/api/state` exposes these stable top-level payloads for Task C:
   - `practiscore_session`
   - `practiscore_sync`
   - existing `practiscore_options`
16. Keep `practiscore_options` as the local-stage source that drives `Match type`, `Stage #`, `Competitor name`, and `Place` after sync completes.
17. Expose stable `practiscore_sync` states:
   - `idle`
   - `discovering_matches`
   - `match_list_ready`
   - `importing_selected_match`
   - `success`
   - `error`
18. Do not add multi-match storage to the project model.

## Step-by-Step Test Directions
1. Create `tests/analysis/test_practiscore_web_extract.py`.
2. Add tests for remote match discovery shape.
3. Add tests for selected-match artifact download and cache metadata.
4. Add tests that verify CSV or TXT, HTML, and summary snapshot are all captured together for one selected remote match.
5. Create `tests/analysis/test_practiscore_sync_normalize.py`.
6. Add tests for bridging the downloaded CSV or TXT artifact into the existing imported-stage expectations.
7. Add tests for competitor place-change and name normalization edge cases.
8. Create `tests/browser/test_practiscore_sync_controller.py`.
9. Add tests for match-list payload shape.
10. Add tests for selected-match import success payload shape.
11. Add tests for expired-session and missing-artifact error paths.
12. Run:
```bash
uv run pytest tests/analysis/test_practiscore_web_extract.py tests/analysis/test_practiscore_sync_normalize.py tests/browser/test_practiscore_sync_controller.py
```
13. Run parser and browser regression slices:
```bash
uv run pytest tests/analysis/test_practiscore_import.py
uv run pytest tests/browser/test_browser_control.py -k practiscore
uv run pytest tests/browser/test_project_lifecycle_contracts.py -k practiscore
```

## Step-by-Step Documentation Directions
1. Update `docs/userfacing/workflow.md` with the selected-match flow:
   - connect,
   - select one remote match,
   - import it,
   - continue in the existing local PractiScore controls.
2. Make clear that manual file import remains available if remote import is unavailable or if the user wants to overwrite the synced source.
3. Update `docs/userfacing/troubleshooting.md` with:
   - expired session handling,
   - challenge loop handling,
   - remote match discovery failure,
   - selected-match artifact download failures,
   - manual overwrite behavior after sync.
4. Keep the two-line markdown footer format in both docs.

## Human Verification Checklist
1. The app can list available remote matches after authentication.
2. Importing one selected remote match stages a local CSV or TXT source and updates the existing PractiScore local controls.
3. HTML and summary snapshot artifacts are cached locally for the selected match.
4. Existing file-import semantics still work after a sync import.
5. Workflow and troubleshooting docs explain the selected-match behavior clearly.

## Out Of Scope
1. New Project-pane buttons, selects, or status styling.
2. Static browser UI rendering changes.
3. `.github` agent governance files.

Last updated: 2026-04-27
Referenced files last updated: 2026-04-27
