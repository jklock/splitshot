# Progress

This is the live execution ledger for Automate3 UI.

Last updated: 2026-05-22.

## Current Phase

Phase: **Remediation partially complete; final proof still open.**

Fixed since the failed review:

- automated browser bootstrap now starts in Stage instead of hiding the tool rail behind Landing;
- automation surface panel no longer blocks expanded waveform interaction;
- `test_browser_interactions.py` passes 40/40;
- screenshot capture scripts now start their own server, wait on DOM/state predicates, and fail on invalid loaded captures;
- loaded screenshots now show media, stage cards, and library records;
- Library row text no longer overlaps;
- backup restore returns structured per-record errors.

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

- [x] `uv run pytest tests/browser/ -q`
- [x] `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`
- [ ] PiP/multi-angle loaded screenshot
- [ ] export progress screenshot
- [ ] export complete screenshot
- [ ] returning-user landing screenshot
- [ ] real file-export proof for `/api/workspace/export`
- [ ] recap-render artifact proof for `/api/workspace/recap/render`
- [ ] final human/vision visual approval

## Latest Proof

| Command | Result |
|---|---|
| `node --check src/splitshot/browser/static/app.js` | pass |
| `uv run python -m py_compile scripts/docs/capture_automate3_views.py scripts/docs/capture_loaded_views.py scripts/docs/setup_and_capture_loaded.py` | pass |
| `uv run pytest tests/browser/test_browser_control.py::test_library_backup_restore_reports_record_errors -q` | pass |
| `uv run pytest tests/browser/test_browser_interactions.py -q --maxfail=1` | pass, 40/40 |
| `uv run python scripts/docs/capture_automate3_views.py` | pass |
| `uv run python scripts/docs/capture_loaded_views.py` | pass |
| `uv run pytest tests/browser/ -q` | pass, 323/323 |
| `uv run python scripts/testing/run_test_suite.py --mode all-together --format table` | pass |

## Risks

- Current screenshots are content-bearing but not final design approval.
- PiP/multi-angle and export-progress screenshot proof are still open.
- Export and recap routes are wired but still need artifact-level proof before a completion claim.
