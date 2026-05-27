# Implementation Roadmap

## 1. Preserve Baseline And Capture Current Proof

- Record current git status.
- Capture current screenshots if artifacts are missing.
- Run narrow static/browser checks that cover current shell assumptions.
- Do not claim current UI is complete.

## 2. Split Architecture Into Real Views

Use the phased migration from `docs/automate3-ui/execution-order.md` (Wrap → Move → Hide → Retire) so the app is never broken for more than one verified slice.

- Introduce view controller and active view state.
- Create separate Landing, Stage, Match, and Library view bodies.
- Keep shared shell and context header.
- Remove the permanent global automation strip.
- Preserve Stage panes inside Stage view.

## 3. Landing Page

- Build professional first-run and returning-user layouts.
- Wire recent activity and quick starts.
- Verify navigation into Stage, Match, and Library.

## 4. Stage Cleanup And Enhancement

- Simplify Stage chrome.
- Group existing panes into Stage tool structure.
- Integrate output profiles, retained review source, render preview, and export status.
- Add standalone, workspace-stage, empty, and loaded states.

## 5. PiP, Waveform, And Multi-Angle Stability

- Implement bounded sync correction.
- Stop route churn during drag/playback.
- Add multi-track waveform, segments, camera jobs, audio balance, smart cuts, and line-up controls.
- Prove smoothness and state correctness.

## 6. Match Video Edit

- Build match header and stage grid.
- Wire workspace lifecycle, stage open/return, defaults, overrides, reorder.
- Implement Setup Once Apply Everywhere with preview/apply.
- Build Match Recap, Stage Composite, PractiScore import, and batch export.

## 7. Performance Library

- Build dashboard, filters, table, detail, proxy/archive, analytics, comparison, tags, notes, export, and reopen flows.
- Ensure Stage/Match completions update history without navigation.

## 8. Export And Output Workflows

- Complete Stage export, batch export, Match Recap export, Stage Composite export, progress, cancellation, completion, and open output folder actions.

## 9. Integration Polish

- Verify all view transitions.
- Complete empty/loading/error/stale/unresolved states.
- Fix responsive layout and keyboard/focus behavior.
- Remove placeholder language and dead controls.

## 10. Proof, Regression, Release Readiness

- Run targeted tests.
- Run `uv run pytest tests/browser/`.
- Run `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`.
- Capture empty and loaded screenshots for every view.
- Update proof matrices and release readiness.
