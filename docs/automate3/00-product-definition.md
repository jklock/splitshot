# Product Definition

SplitShot is a local-first browser app for competition shooting video analysis, scoring, merge review, performance history, and export. The final product is an editor built around analysis-derived decisions, not a general video maker.

## Four Views

### Landing Page

The Landing Page is the front door. It gives the user a professional starting point with recent work, quick-start actions, and entry into the three core workflows.

### Stage Video Edit

Stage Video Edit is the deep editor for one stage. It owns the existing editing tools: video review, PiP, timing, scoring, markers, overlay, review, export, metrics, ShotML, and settings. It also owns stage-level output profiles, retained review source, render preview, multi-angle controls, waveform enhancements, and export status.

Stage work can be standalone or attached to a Match. Creating or attaching a Match from Stage must be possible without forcing a navigation change unless the user chooses to enter Match Video Edit.

### Match Video Edit

Match Video Edit is the workspace-level frontend. It owns match identity, stage grid, shared defaults, per-stage overrides, Setup Once Apply Everywhere, Match Recap, Stage Composite, PractiScore import, batch export, and clean open/return behavior for stages.

### Performance Library

Performance Library is the canonical historical performance record. It is not a helper file browser. It owns historical records, retained proxies, analytics, comparison, personal bests, outliers, tags, notes, exports, and reopen links.

Library updates automatically when Stage or Match work produces reviewed/exported history. It must not pull the user away from the current view.

## Shotcut Adaptation Rule

Shotcut is useful because its screenshots show professional editor density, clear preview/timeline/inspector hierarchy, focused modals, and coherent tool placement. SplitShot should adapt those lessons into its own language for shooting analysis. It must not copy Shotcut labels, branding, iconography, or product model.

## Integrated But Separated

The final app must feel tied together:

- Stage can become part of a Match.
- Match can open a Stage for deep editing and return cleanly.
- Stage and Match completions update Library automatically.
- Library can reopen Stage or Match intentionally.

The final app must also feel separated:

- Match does not inherit irrelevant Stage chrome.
- Library does not show editor timeline/chrome by default.
- Landing does not expose editor panels.
- Stage remains a focused editor instead of a generic dashboard.
