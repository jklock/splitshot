# Release Readiness

Automate3 implementation is release-ready only when it is user-ready.

## Required Conditions

- app launches cleanly from source and packaged paths
- Landing Page is understandable for first-run and returning users
- Stage Video Edit completes real stage review/edit/export workflows
- Match Video Edit completes real workspace, recap, composite, and batch export workflows
- Performance Library records history, shows analytics, and reopens work
- exports work and output locations are clear
- no known P0/P1 UI regressions remain
- docs and screenshots match the shipped UI.

## Release Note Checklist

If shipping as a release:

- summarize four-view UI model
- call out Stage/Match/Library integration
- call out PiP/multi-angle improvements
- call out Performance Library history/analytics
- mention any known limitations clearly
- verify version/changelog/release flow through the repo release instructions.

## Final Gate

Release readiness requires:

- targeted checks pass
- `tests/browser/` passes
- canonical grouped runner passes or has an external dependency blocker
- screenshot proof package complete
- `docs/automate3-ui/artifacts/readiness-gate.md` marked ready with evidence.
