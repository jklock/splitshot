# Task B: Acquisition And Normalization Engine

## Goal
Implement authenticated PractiScore data acquisition and normalization into existing imported-stage scoring structures.

This task does not edit browser static UI controls and does not add agent instruction files.

## Owned Files (Exclusive)
### Source
1. `src/splitshot/scoring/practiscore_web_extract.py` (new)
2. `src/splitshot/scoring/practiscore_sync_normalize.py` (new)
3. `src/splitshot/ui/controller.py`

### Tests
1. `tests/analysis/test_practiscore_web_extract.py` (new)
2. `tests/analysis/test_practiscore_sync_normalize.py` (new)
3. `tests/browser/test_practiscore_sync_controller.py` (new)

### Docs
1. `docs/userfacing/workflow.md`
2. `docs/userfacing/troubleshooting.md`

Do not edit files owned by Task A or Task C.

## Prerequisite Contract From Task A
Task A must expose stable session payload states via session routes.

## Step-by-Step Code Directions
1. Create `src/splitshot/scoring/practiscore_web_extract.py`.
2. Add extractor entrypoint that accepts an authenticated browser context/session handle.
3. Implement extraction order:
   - Structured payload extraction first.
   - DOM fallback extraction second.
4. Add extraction artifact output fields:
   - `source_url`
   - `fetched_at`
   - `extractor_version`
   - `raw_snapshot`
5. Create `src/splitshot/scoring/practiscore_sync_normalize.py`.
6. Add mapping from extracted records to existing imported-stage field expectations used by current scoring.
7. Preserve name/place compatibility behavior already present in file import paths.
8. Update `src/splitshot/ui/controller.py`.
9. Add sync orchestration method that:
   - calls extractor,
   - normalizes records,
   - applies existing PractiScore import context behavior,
   - returns browser-friendly payload.
10. Add deterministic partial-failure handling so one failed match does not abort all successful matches.
11. Return payload fields for Task C UI consumption:
   - `status`
   - `matches_processed`
   - `matches_failed`
   - `errors`
   - `practiscore_options`

## Step-by-Step Test Directions
1. Create `tests/analysis/test_practiscore_web_extract.py`.
2. Add tests for structured extraction success.
3. Add tests for DOM fallback extraction.
4. Add tests that verify artifact metadata fields exist.
5. Create `tests/analysis/test_practiscore_sync_normalize.py`.
6. Add tests for required field mappings to imported-stage expectations.
7. Add tests for competitor place-change and name normalization edge cases.
8. Create `tests/browser/test_practiscore_sync_controller.py`.
9. Add tests for sync success payload shape.
10. Add tests for partial failure reporting and successful continuation.
11. Run:
```bash
uv run pytest tests/analysis/test_practiscore_web_extract.py tests/analysis/test_practiscore_sync_normalize.py tests/browser/test_practiscore_sync_controller.py
```
12. Run parser regression slice:
```bash
uv run pytest tests/analysis/test_practiscore_import.py
```

## Step-by-Step Documentation Directions
1. Update `docs/userfacing/workflow.md` with login-first then sync flow.
2. Make clear that manual file import remains available if sync is unavailable.
3. Update `docs/userfacing/troubleshooting.md` with:
   - expired session handling,
   - challenge loop handling,
   - partial sync failure interpretation.
4. Keep the two-line markdown footer format in both docs.

## Human Verification Checklist
1. Controller sync method produces stable payload fields.
2. Extractor supports structured then DOM fallback.
3. Partial failures do not block successful imports.
4. Workflow and troubleshooting docs explain expected behavior clearly.

## Out Of Scope
1. New Project-pane Connect/Sync buttons.
2. Browser state/UI rendering changes.
3. `.github` agent governance files.

Last updated: 2026-04-27
Referenced files last updated: 2026-04-27
