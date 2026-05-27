# Track 07: Proof, Regression, And Release

## Goal

Prove the new UI structure and features before release.

## Proof Targets

### Landing Page

- [ ] loads in under 1 second
- [ ] shows three entry cards
- [ ] recent activity is accurate
- [ ] quick-start shortcuts work
- [ ] empty state is friendly

### Stage Video Edit

- [ ] all existing features work
- [ ] output profile manager works
- [ ] all output hook editors have previews
- [ ] multi-angle features work
- [ ] multi-track waveform renders
- [ ] color-coded segments display

### Match Video Edit

- [ ] workspace create/open/save works
- [ ] stage grid shows status
- [ ] drag-and-drop reordering works
- [ ] Setup Once, Apply Everywhere works
- [ ] batch export shows progress
- [ ] Match Recap and Stage Composite render

### Performance Library

- [ ] records are browsable
- [ ] proxy playback works
- [ ] analytics charts render
- [ ] tags and notes persist
- [ ] export works

### Cross-Cutting

- [ ] PiP playback is smooth
- [ ] waveform renders at 60fps
- [ ] library queries are fast
- [ ] no regressions in legacy features
- [ ] Windows export font policy holds

## Regression Suite

Run these before every release:

1. `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`
2. `uv run pytest tests/browser/`
3. `uv run pytest tests/analysis/`
4. Browser interaction audit
5. Export pipeline test with `docs/Clip1.MP4`

## Release Checklist

- [ ] all proof targets pass
- [ ] all regression tests pass
- [ ] version bumped
- [ ] changelog updated
- [ ] release notes extracted
- [ ] tag created and pushed

## Acceptance

- all tests pass
- all features are proven
- no P0 bugs
- release is ready
