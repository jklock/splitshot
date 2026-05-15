# SplitShot Documentation

This is the documentation index for SplitShot. Use it as the routing layer between user docs, maintainer docs, subsystem maps, tests, and scripts.

## Start Here

If you just forked SplitShot, read these in order:

1. [../README.md](../README.md)
2. [project/DEVELOPING.md](project/DEVELOPING.md)
3. [project/ARCHITECTURE.md](project/ARCHITECTURE.md)
4. [../src/splitshot/README.md](../src/splitshot/README.md)
5. [tests/TEST_SUITE_GUIDE.md](tests/TEST_SUITE_GUIDE.md)
6. [../scripts/README.md](../scripts/README.md)

## By Audience

### Product users

- [userfacing/USER_GUIDE.md](userfacing/USER_GUIDE.md)
- [userfacing/workflow.md](userfacing/workflow.md)
- [userfacing/troubleshooting.md](userfacing/troubleshooting.md)
- [userfacing/panes/project.md](userfacing/panes/project.md)
- [userfacing/panes/score.md](userfacing/panes/score.md)
- [userfacing/panes/splits.md](userfacing/panes/splits.md)
- [userfacing/panes/shotml.md](userfacing/panes/shotml.md)
- [userfacing/panes/pip.md](userfacing/panes/pip.md)
- [userfacing/panes/popup.md](userfacing/panes/popup.md)
- [userfacing/panes/overlay.md](userfacing/panes/overlay.md)
- [userfacing/panes/review.md](userfacing/panes/review.md)
- [userfacing/panes/export.md](userfacing/panes/export.md)
- [userfacing/panes/settings.md](userfacing/panes/settings.md)
- [userfacing/panes/metrics.md](userfacing/panes/metrics.md)

### Fork owners and maintainers

- [project/DEVELOPING.md](project/DEVELOPING.md)
- [project/ARCHITECTURE.md](project/ARCHITECTURE.md)
- [project/LIMITATIONS.md](project/LIMITATIONS.md)
- [project/ELECTRON_RELEASE.md](project/ELECTRON_RELEASE.md)
- [tests/TEST_SUITE_GUIDE.md](tests/TEST_SUITE_GUIDE.md)
- [../scripts/README.md](../scripts/README.md)
- [../CONTRIBUTING.md](../CONTRIBUTING.md)

### Code readers

- [../src/splitshot/README.md](../src/splitshot/README.md)
- [../src/splitshot/browser/README.md](../src/splitshot/browser/README.md)
- [../src/splitshot/ui/README.md](../src/splitshot/ui/README.md)
- [../src/splitshot/domain/README.md](../src/splitshot/domain/README.md)
- [../src/splitshot/analysis/README.md](../src/splitshot/analysis/README.md)
- [../src/splitshot/export/README.md](../src/splitshot/export/README.md)
- [../src/splitshot/media/README.md](../src/splitshot/media/README.md)
- [../src/splitshot/scoring/README.md](../src/splitshot/scoring/README.md)
- [../src/splitshot/timeline/README.md](../src/splitshot/timeline/README.md)
- [../src/splitshot/presentation/README.md](../src/splitshot/presentation/README.md)
- [../src/splitshot/persistence/README.md](../src/splitshot/persistence/README.md)
- [../src/splitshot/merge/README.md](../src/splitshot/merge/README.md)
- [../src/splitshot/overlay/README.md](../src/splitshot/overlay/README.md)
- [../src/splitshot/utils/README.md](../src/splitshot/utils/README.md)
- [../src/splitshot/benchmarks/README.md](../src/splitshot/benchmarks/README.md)

## Screenshot Set

The current user-facing screenshot set lives in [screenshots/](screenshots/).

Regenerate it with:

```bash
uv run python scripts/docs/capture_browser_screenshots.py
```

Covered surfaces:

- Every left-rail pane: `Project`, `PiP`, `Score`, `Splits`, `Markers`, `Overlay`, `Review`, `Export`, `Settings`, `Metrics`, `ShotML`
- Expanded score, splits, waveform, metrics, marker, settings, review, and ShotML states already represented by the capture script
- Shared modals: color picker and export log

## Technical Docs

- [analysis/SHOTML.md](analysis/SHOTML.md)
- [project/SHOTML_ARCHITECTURE.md](project/SHOTML_ARCHITECTURE.md)
- [project/browser-pane-ownership.md](project/browser-pane-ownership.md)
- [project/browser-control-qa-matrix.md](project/browser-control-qa-matrix.md)
- [project/browser-control-coverage-plan.md](project/browser-control-coverage-plan.md)
- [project/browser-full-e2e-qa-plan.md](project/browser-full-e2e-qa-plan.md)

## Read This Next

- [../README.md](../README.md) for install and quickstart
- [project/DEVELOPING.md](project/DEVELOPING.md) for first-run developer workflow
- [project/ARCHITECTURE.md](project/ARCHITECTURE.md) for subsystem boundaries
- [tests/TEST_SUITE_GUIDE.md](tests/TEST_SUITE_GUIDE.md) for validation
- [../scripts/README.md](../scripts/README.md) for operational tooling
