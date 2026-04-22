# SplitShot Documentation

SplitShot documentation starts with the product guides, then branches into troubleshooting, technical notes, and development references. The current user-facing screenshots live in [screenshots/](screenshots/).

## User Docs

- [userfacing/USER_GUIDE.md](userfacing/USER_GUIDE.md)
- [userfacing/workflow.md](userfacing/workflow.md)
- [userfacing/troubleshooting.md](userfacing/troubleshooting.md)
- [userfacing/panes/project.md](userfacing/panes/project.md)
- [userfacing/panes/score.md](userfacing/panes/score.md)
- [userfacing/panes/splits.md](userfacing/panes/splits.md)
- [userfacing/panes/shotml.md](userfacing/panes/shotml.md)
- [userfacing/panes/pip.md](userfacing/panes/pip.md)
- [userfacing/panes/overlay.md](userfacing/panes/overlay.md)
- [userfacing/panes/popup.md](userfacing/panes/popup.md)
- [userfacing/panes/review.md](userfacing/panes/review.md)
- [userfacing/panes/export.md](userfacing/panes/export.md)
- [userfacing/panes/metrics.md](userfacing/panes/metrics.md)

## Screenshot Set

- `ProjectPane.png`
- `ScoringPane.png`, `ScoringPane2.png`
- `SplitsPane.png`, `SplitsExpanded.png`, `WaveFormExpanded.png`
- `ShotMLPane.png`, `ShotMLPane2.png`
- `PiPPane.png`
- `OverlayPane.png`, `OverlayPane2.png`
- `ColorPickerModal.png`
- `PopUpPane.png`, `PopUpPane2.png`
- `ReviewPane.png`, `ReviewPane2.png`
- `ExportPane.png`, `ExportPane2.png`
- `ExportLogModal.png`
- `MetricsPane.png`, `MetricsPane2.png`, `MetricsCSV.png`

Regenerate the browser screenshots with:

```bash
uv run python scripts/docs/capture_browser_screenshots.py
```

## Expanded State Coverage

The screenshot script covers:

- Every left-rail pane: Project, Score, Splits, ShotML, PiP, Overlay, PopUp, Review, Export, and Metrics.
- Expanded Score shot cards.
- Expanded Splits timing table and expanded waveform layout.
- Every ShotML collapsible section.
- Expanded PiP defaults and per-media card controls.
- Overlay lower style controls and score text color controls.
- Expanded PopUp bubble editor with motion path controls.
- Expanded Review imported-summary and custom text-box editors.
- Export lower controls plus the Export Log modal.
- Expanded Metrics table.
- Shared Color Picker modal used by color swatches across Overlay, PopUp, and Review.

## Current Limitations

- [project/LIMITATIONS.md](project/LIMITATIONS.md)

## Technical Docs

- [analysis/SHOTML.md](analysis/SHOTML.md)
- [project/ARCHITECTURE.md](project/ARCHITECTURE.md)
- [project/SHOTML_ARCHITECTURE.md](project/SHOTML_ARCHITECTURE.md)
- [src/splitshot/README.md](../src/splitshot/README.md)
- [src/splitshot/analysis/README.md](../src/splitshot/analysis/README.md)
- [src/splitshot/browser/README.md](../src/splitshot/browser/README.md)
- [src/splitshot/browser/static/README.md](../src/splitshot/browser/static/README.md)
- [src/splitshot/domain/README.md](../src/splitshot/domain/README.md)
- [src/splitshot/export/README.md](../src/splitshot/export/README.md)
- [src/splitshot/media/README.md](../src/splitshot/media/README.md)
- [src/splitshot/merge/README.md](../src/splitshot/merge/README.md)
- [src/splitshot/overlay/README.md](../src/splitshot/overlay/README.md)
- [src/splitshot/persistence/README.md](../src/splitshot/persistence/README.md)
- [src/splitshot/presentation/README.md](../src/splitshot/presentation/README.md)
- [src/splitshot/scoring/README.md](../src/splitshot/scoring/README.md)
- [src/splitshot/timeline/README.md](../src/splitshot/timeline/README.md)
- [src/splitshot/ui/README.md](../src/splitshot/ui/README.md)
- [src/splitshot/utils/README.md](../src/splitshot/utils/README.md)

## Development Docs

- [project/DEVELOPING.md](project/DEVELOPING.md)
- [scripts/README.md](../scripts/README.md)

## Repository Files

- [../LICENSE](../LICENSE)
- [../CONTRIBUTING.md](../CONTRIBUTING.md)
- [../CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)
- [../SECURITY.md](../SECURITY.md)

**Last updated:** 2026-04-22
**Referenced files last updated:** 2026-04-22
