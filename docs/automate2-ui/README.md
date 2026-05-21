# Automate2 UI

This package is the comprehensive UI completion command center for the automation work defined in `docs/automate2/`.

Start here:

1. [spec.md](spec.md)
2. [todo.md](todo.md)
3. [execution-order.md](execution-order.md)
4. [outcomes.md](outcomes.md)
5. [tracks/01-landing-page-and-shell-navigation.md](tracks/01-landing-page-and-shell-navigation.md)
6. [tracks/02-stage-video-editor-ui.md](tracks/02-stage-video-editor-ui.md)
7. [tracks/03-match-video-editor-ui.md](tracks/03-match-video-editor-ui.md)
8. [tracks/04-performance-library-ui.md](tracks/04-performance-library-ui.md)
9. [tracks/05-waveform-and-timeline-enhancements.md](tracks/05-waveform-and-timeline-enhancements.md)
10. [tracks/06-export-and-output-workflows.md](tracks/06-export-and-output-workflows.md)
11. [tracks/07-proof-regression-release.md](tracks/07-proof-regression-release.md)
12. [artifacts/readiness-gate.md](artifacts/readiness-gate.md)

## Purpose

`docs/automate2/` defines the backend and contract layer.

`docs/automate2-ui/` defines the browser-shell and packaged-app completion work required to make that backend usable, coherent, and shippable.

This package assumes `main` at `v1.0.5` is the shipped baseline. UI work here must preserve the released Windows export-font/OCR proof path and the packaged `docs/Clip1.MP4` fixture workflow while exposing the automation backend.

Current backend truth comes from [../automate/14-truth-audit-matrix.md](../automate/14-truth-audit-matrix.md) and [../automate2/14-truth-audit-matrix.md](../automate2/14-truth-audit-matrix.md).

## Package Rules

- `spec.md` is the authoritative UI build spec.
- `todo.md` is the execution checklist.
- `outcomes.md` defines what completion means.
- `progress.md` is the live execution ledger.
- `execution-order.md` is the dependency-respecting work order for today.
- `artifacts/readiness-gate.md` is the task-classification gate for starting the next implementation cycle.

## Scope

This package covers:

- landing page design and implementation
- browser shell overhaul
- Stage Video Edit UI completion
- Match Video Edit workspace UI
- Performance Library UI with analytics
- waveform and timeline enhancements
- export and output workflow UI
- PiP playback smoothness and merge-editor usability
- UI-targeted proof, regression, and release closure

This package does not redefine the backend contract in `docs/automate2/`; it builds the UI needed to expose it correctly.
