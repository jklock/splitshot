# SplitShot Workflow

This is the fastest end-to-end path from a raw stage video to a finished local export.

## Before You Start

- Install and launch SplitShot from the root [README.md](../../README.md).
- Keep the primary stage video on a local drive.
- If you want official stage context, have the PractiScore CSV or TXT file ready.
- If you want a second angle or supporting graphics, keep those files ready for the PiP step.

## End-To-End Flow

1. Open SplitShot and start in [panes/project.md](panes/project.md).
2. Name the project, add an optional description, then choose the primary video.
3. Wait for the status bar to report local analysis results. SplitShot will detect the beep, shots, and waveform data before the rest of the workflow is reliable.
4. Open [panes/splits.md](panes/splits.md) and confirm the shot list, first-shot draw time, and waveform markers.
5. Lower the detection threshold if quiet shots were missed, or raise it if background noise created extra shots.
6. Nudge, drag, add, or delete shots until the timing view matches the actual run.
7. If you want official match context, return to [panes/project.md](panes/project.md) and import the PractiScore file.
8. Open [panes/score.md](panes/score.md), enable scoring, choose the correct preset, and score each shot.
9. Open [panes/overlay.md](panes/overlay.md) and set the badge layout, font, colors, and score badge placement.
10. Open [panes/review.md](panes/review.md) and verify which badges should appear in preview and export. Add any custom review text boxes or imported summary boxes here.
11. If you need extra media, open [panes/pip.md](panes/pip.md), add each file, and fine-tune size, position, and sync.
12. Open [panes/metrics.md](panes/metrics.md) when you want a dashboard view or a CSV/text export of the run.
13. Finish in [panes/export.md](panes/export.md), choose an output preset or custom settings, set the output path, and render the final video.
14. Keep the chosen project folder so SplitShot can reopen the same bundle later.

## Practical Order Of Operations

- Do timing work before scoring. A changed shot list changes score rows, metrics, and overlay timing.
- Import PractiScore after the timing pass is stable. That makes it easier to compare official context against the final shot list.
- Tune Overlay before Review if you want review text boxes to line up with the final badge stack.
- Add PiP media after the main angle is stable. It is easier to sync and place secondary media once the primary timeline is finished.
- Export only after you have scrubbed near the final shot and confirmed the score summary, review boxes, and PiP layout.

## When To Save The Bundle

- Choose the project folder early if you want SplitShot to keep the session in a named bundle.
- Keep the same folder through revisions so the run, timing, score, overlay, PiP, and export settings stay together.
- Reopen that folder later from the Project pane when you need to revise timing or export another version.

## Next Stops

- [panes/project.md](panes/project.md) for setup details.
- [panes/export.md](panes/export.md) for render settings.
- [troubleshooting.md](troubleshooting.md) if any step behaves differently than expected.

**Last updated:** 2026-04-18
**Referenced files last updated:** 2026-04-18