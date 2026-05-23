# Progress

This is the live execution ledger for Automate3 UI.

Last updated: 2026-05-22.

## Current Phase

Phase: **All mechanical checks complete. Blocked on human/vision visual review.**

Fixed since the failed review:

- automated browser bootstrap now starts in Stage instead of hiding the tool rail behind Landing;
- automation surface panel no longer blocks expanded waveform interaction;
- `test_browser_interactions.py` passes 40/40;
- screenshot capture scripts now start their own server, wait on DOM/state predicates, and fail on invalid loaded captures;
- loaded screenshots now show media, stage cards, and library records;
- Library row text no longer overlaps;
- backup restore returns structured per-record errors;
- HTML DOM nesting bug fixed (match/library were children of stage view);
- server.py closure bug fixed (17 `self.controller` → `controller`);
- api.js response ownership fix (excluded non-state API paths);
- PiP/multi-angle, export, and returning-user landing screenshots captured;
- DOM/layout assertion report generated with pass verdict.

## Completed

- [x] Route contract test exists and passes
- [x] Stage rail regression fixed for Project/Export visibility
- [x] Waveform pan and shot drag interaction path unblocked
- [x] Empty screenshot proof regenerated
- [x] Loaded screenshot proof regenerated
- [x] Contact sheet regenerated as a real multi-image sheet
- [x] Screenshot docs updated to stop claiming invalid proof
- [x] Truth matrix downgraded to current reality
- [x] ShootingCut comparison updated for registered-but-unproven export/recap routes

## Pending

- [x] `uv run pytest tests/browser/ -q` (327/327 passed)
- [x] `uv run python scripts/testing/run_test_suite.py --mode all-together --format table` (10 suites, 305s, all passed)
- [x] PiP/multi-angle loaded screenshot captured
- [x] export progress screenshot captured
- [x] export complete screenshot captured
- [x] returning-user landing screenshot captured
- [x] DOM/layout assertion report generated (pass verdict)
- [x] Contact sheets regenerated (empty + loaded)
- [x] real file-export proof for `/api/workspace/export` (test: `test_single_stage_export`, `test_multi_stage_batch_export`)
- [x] recap-render artifact proof for `/api/workspace/recap/render` (test: `test_recap_render`)
- [ ] final human/vision visual approval (**blocking**)

## Latest Proof

| Command | Result |
|---|---|
| `node --check src/splitshot/browser/static/app.js` | pass |
| `uv run python -m py_compile scripts/docs/capture_automate3_views.py scripts/docs/capture_loaded_views.py scripts/docs/setup_and_capture_loaded.py` | pass |
| `uv run pytest tests/browser/test_browser_control.py::test_library_backup_restore_reports_record_errors -q` | pass |
| `uv run pytest tests/browser/test_browser_interactions.py -q --maxfail=1` | pass, 40/40 |
| `uv run python scripts/docs/capture_automate3_views.py` | pass |
| `uv run python scripts/docs/capture_loaded_views.py` | pass |
| `uv run python scripts/docs/capture_additional_screenshots.py` | pass (PiP, export, returning-user) |
| `uv run pytest tests/browser/ -q` | pass, 327/327 |
| `uv run python scripts/testing/run_test_suite.py --mode all-together --format table` | pass |
| `uv run pytest tests/browser/test_workspace_export_and_recap.py -v` | pass, 3/3 (export + recap proof) |

## Risks

- Current screenshots are content-bearing but not final design approval (blocked on human/vision review).
- Broader library persistence E2E remains for a future pass.
