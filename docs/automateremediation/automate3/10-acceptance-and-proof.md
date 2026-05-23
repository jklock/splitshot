# Acceptance And Proof

## View Acceptance

Each view is accepted only when:

- empty state exists
- loaded state exists
- loading state exists where data is fetched
- error state exists for route failures
- controls are wired or explicitly unavailable
- keyboard focus is visible
- layout works at supported desktop and narrow widths
- screenshot proof exists.

## Workflow Acceptance

Required E2E flows:

- Landing to Stage, Match, Library
- Stage import/edit/export
- Stage attach/create Match without forced navigation
- Match open Stage and return
- Setup Once Apply Everywhere preview/apply
- Match batch export
- Match Recap and Stage Composite preview/render
- Library browse/filter/select/detail
- Library tag/note edit
- Library reopen Stage/Match
- Library export
- PiP sync and drag stability.

## Screenshot Proof Package

Required artifacts:

- Landing empty and returning-user state
- Stage empty and loaded state
- Match empty and loaded state
- Library empty and loaded state
- PiP/multi-angle loaded state
- export progress/completion state
- contact sheet comparing final SplitShot views against the Shotcut reference sheet.

## Non-Vision Agent Proof Rule

The implementation agent may not have image/vision capability. Screenshot capture alone is not enough in that case.

Required non-vision workflow:

1. Capture deterministic screenshots with the repo screenshot/audit scripts.
2. Generate contact sheets and an HTML/Markdown screenshot index with file names, surface names, viewport sizes, and scenario labels.
3. Run DOM/layout assertions for each capture:
   - active view is correct
   - forbidden legacy chrome is absent
   - required headings/actions are visible
   - key panels have non-zero bounds
   - no obvious horizontal overflow
   - no console errors.
4. Update the proof matrix with screenshot paths and assertion command results.
5. Stop before final readiness and request a vision-capable or human visual review of the screenshot folder/contact sheet.

Final user-ready visual sign-off requires either a vision-capable reviewer or human review. A non-vision agent must not self-certify visual polish from screenshots it cannot inspect.

## Commands

Run the narrowest useful checks first, then:

- preservation tests named in `docs/automate3-ui/artifacts/test-preservation-contract.md`
- `uv run pytest tests/browser/`
- `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`

If a check cannot run, document the command, blocker, and remaining risk.

## Failure Conditions

Do not claim completion if:

- Match or Library still inherit irrelevant Stage chrome
- a visible command is dead
- screenshot proof is missing
- loaded-state screenshots are missing
- tests were skipped without documented blocker
- the UI still depends on a permanent global automation strip.
