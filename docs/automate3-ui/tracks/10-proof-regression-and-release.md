# Track 10: Proof, Regression, And Release

## Required Test Order

1. targeted tests for changed behavior
2. relevant browser tests
3. `uv run pytest tests/browser/`
4. `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`

## Required Visual Proof

- Landing empty and returning screenshots
- Stage empty and loaded screenshots
- Match empty and loaded screenshots
- Library empty and loaded screenshots
- PiP/multi-angle loaded screenshot
- export progress/completion screenshots
- final contact sheet.

## Non-Vision Agent Requirements

Agents without vision capability must produce reviewable artifacts instead of self-certifying visual quality:

- screenshot folder with stable names
- contact sheet
- screenshot index with surface, state, viewport, and scenario
- DOM/layout assertion report
- console error report
- explicit note that final visual sign-off is blocked on human or vision-capable review.

The non-vision agent can complete implementation and mechanical validation, but release readiness remains blocked until the screenshots are visually reviewed.

## Required Docs Updates

- `progress.md`
- `artifacts/ui-gap-matrix.md`
- `artifacts/ui-proof-matrix.md`
- `artifacts/readiness-gate.md`
- user/developer docs if commands or behavior change.

## Release Gate

Do not release if:

- any view lacks loaded proof
- Match/Library remain panel-like
- visible controls are dead
- tests fail without documented external blocker
- release notes overstate completion.
