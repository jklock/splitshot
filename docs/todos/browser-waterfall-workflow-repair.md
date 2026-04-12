# Browser Waterfall Workflow Repair Todo

## Planning

- [x] Re-read `Directions.md`.
- [x] Review latest browser logs for failed button/control behavior.
- [x] Write repair plan.
- [x] Write pessimistic gap analysis.

## Implementation

- [x] Rename Timing to Splits and reorder left rail workflow.
- [x] Move Review down and repurpose it for custom preview artifacts.
- [x] Move split cards out of Review and keep timing edits under Splits.
- [x] Make Project secondary action say Add Second Video.
- [x] Make Delete Project full-width red destructive action.
- [x] Show status bar only during import/export.
- [x] Render secondary video in the primary video stage for WYSIWYG merge preview.
- [x] Sync secondary playback with primary playback and merge offset.
- [x] Add waveform scale, horizontal zoom, amplitude zoom, and millisecond labels.
- [x] Collapse expanded waveform/splits mode when navigating pages.
- [x] Restrict layout unlock controls to expanded waveform mode.
- [x] Embed per-shot score text in split badges instead of floating score letters.
- [x] Add overlay controls for shot count, quadrant, direction, X/Y, bubble size, font, bold, italic, colors, and artifact toggles.
- [x] Auto-apply all overlay/layout/review changes.
- [x] Keep export settings and FFmpeg log visible and functional.

## Validation

- [x] Add feature tests for overlay state round-trip and persistence.
- [x] Add feature tests for secondary-video merge preview state and export.
- [x] Add static tests for button wiring and page ownership.
- [x] Add renderer/export tests for score text inside shot badges.
- [x] Run the full test suite.
- [x] Generate Stage1 all-options MP4.
- [x] Extract a Stage1 preview frame for the final report.

## Closeout

- [x] Write final audit.
- [x] Commit the branch.
- [x] Merge into `main`.
