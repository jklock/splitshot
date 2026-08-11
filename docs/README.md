# SplitShot Documentation

<!-- Documentation reviewed: 2026-08-11 -->

This is the documentation index for SplitShot. It routes readers through user docs first, then maintainer, developer, and code-reader references.

## Start Here

If you just forked SplitShot, read these in order after the top-level install path in the root README:

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
- [userfacing/panes/media.md](userfacing/panes/media.md)
- [userfacing/panes/compose.md](userfacing/panes/compose.md)
- [userfacing/panes/trim.md](userfacing/panes/trim.md)
- [userfacing/panes/score.md](userfacing/panes/score.md)
- [userfacing/panes/splits.md](userfacing/panes/splits.md)
- [userfacing/panes/markers.md](userfacing/panes/markers.md)
- [userfacing/panes/overlay.md](userfacing/panes/overlay.md)
- [userfacing/panes/review.md](userfacing/panes/review.md)
- [userfacing/panes/export.md](userfacing/panes/export.md)
- [userfacing/panes/queue.md](userfacing/panes/queue.md)
- [userfacing/panes/metrics.md](userfacing/panes/metrics.md)
- [userfacing/panes/shotml.md](userfacing/panes/shotml.md)
- [userfacing/panes/settings.md](userfacing/panes/settings.md)

This is the primary reading path for people trying to use SplitShot rather than maintain it.

### Fork owners and maintainers

- [../CHANGELOG.md](../CHANGELOG.md)
- [project/DEVELOPING.md](project/DEVELOPING.md)
- [project/ARCHITECTURE.md](project/ARCHITECTURE.md)
- [project/GOVERNANCE.md](project/GOVERNANCE.md)
- [project/LIMITATIONS.md](project/LIMITATIONS.md)
- [project/ELECTRON_RELEASE.md](project/ELECTRON_RELEASE.md)
- [tests/TEST_SUITE_GUIDE.md](tests/TEST_SUITE_GUIDE.md)
- [../scripts/README.md](../scripts/README.md)
- [../CONTRIBUTING.md](../CONTRIBUTING.md)

The repo supports macOS, Windows, and Linux source usage, and it also includes Electron packaging targets for all three platforms. macOS remains the deepest documented signing/notarization path, while Windows and Linux also have packaging and smoke coverage in CI.

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
uv run python scripts/docs/capture_browser_screenshots.py \
  --primary-video /path/to/approved-primary.mp4 \
  --secondary-video /path/to/approved-secondary.mp4
```

Covered surfaces:

- Every left-rail pane: `Project`, `Media`, `Compose`, `Trim`, `Score`, `Splits`, `Markers`, `Overlay`, `Review`, `Export`, `In / Out`, `Queue`, `Metrics`, `ShotML`, and `Settings`.
- Expanded score, splits, waveform, metrics, marker, settings, review, and ShotML states already represented by the capture script
- Shared modals: color picker and Queue processing log

The canonical filenames are `ProjectPane.png`, `MediaPane.png`, `ComposePane.png`, `TrimPane.png`, `ScorePane.png`, `ScorePane2.png`, `SplitsPane.png`, `SplitsExpanded.png`, `WaveformExpanded.png`, `MarkersPane.png`, `MarkersPane2.png`, `OverlayPane.png`, `OverlayPane2.png`, `ColorPickerModal.png`, `ReviewPane.png`, `ReviewPane2.png`, `ExportPane.png`, `ExportPane2.png`, `IntroOutroPane.png`, `QueuePane.png`, `ProcessingLogModal.png`, `MetricsPane.png`, `MetricsExpanded.png`, `ShotMLPane.png`, `ShotMLPane2.png`, `SettingsPane.png`, and `SettingsPane2.png`.

The capture command requires two different maintainer-approved real videos outside `tests/`; synthetic fixtures are rejected. The 1400×900 capture validates decoded, non-black frames and enabled showcase overlays before writing each screenshot.

## Technical Docs

- [analysis/SHOTML.md](analysis/SHOTML.md)
- [project/SHOTML_ARCHITECTURE.md](project/SHOTML_ARCHITECTURE.md)
- [project/browser-pane-ownership.md](project/browser-pane-ownership.md)
- [project/browser-control-qa-matrix.md](project/browser-control-qa-matrix.md)

## Read This Next

- [../README.md](../README.md) for the per-OS install and launch paths
- [userfacing/USER_GUIDE.md](userfacing/USER_GUIDE.md) for product usage
- [project/DEVELOPING.md](project/DEVELOPING.md) for developer workflow
- [project/ARCHITECTURE.md](project/ARCHITECTURE.md) for subsystem boundaries
- [project/GOVERNANCE.md](project/GOVERNANCE.md) for branch and release policy
- [tests/TEST_SUITE_GUIDE.md](tests/TEST_SUITE_GUIDE.md) for validation
