# SplitShot Workflow

This is the recommended path from raw stage video to finished local export.

## Before You Start

- Launch SplitShot from the root [README.md](../../README.md).
- Keep the primary video on a local drive.
- Keep PractiScore CSV/TXT data ready if you want official context.
- Keep secondary angles or graphics ready if you plan to use PiP.

## End-To-End Flow

1. Open [panes/project.md](panes/project.md).
2. Name the project, add a description, and import the primary video.
3. Wait for analysis to finish.
4. If needed, open [panes/shotml.md](panes/shotml.md), tune detector settings, and click `Re-run ShotML`.
5. Use `Generate Proposals` only when ShotML suggestions should become explicit reviewable changes.
6. Open [panes/splits.md](panes/splits.md) and confirm the shot count, beep, first shot, and waveform markers.
7. Nudge, drag, add, or delete shots until the timeline matches the video.
8. Import PractiScore in [panes/project.md](panes/project.md) if official match context is needed.
9. Open [panes/score.md](panes/score.md), enable scoring, choose the preset, and score each shot.
10. Open [panes/pip.md](panes/pip.md) if added media is needed; sync and place each item.
11. Open [panes/score.md](panes/score.md) for final score and penalty edits if timing changed.
12. Open [panes/popup.md](panes/popup.md) for shot-linked or time-based markers, including text/image callouts.
13. Open [panes/overlay.md](panes/overlay.md) and configure badge layout, locks, fonts, colors, and score-token colors.
14. Open [panes/review.md](panes/review.md) to set badge visibility and add summary/custom text boxes.
15. Open [panes/metrics.md](panes/metrics.md) to inspect the dashboard, expanded table, or CSV/text exports.
16. Finish in [panes/export.md](panes/export.md), choose render settings, set output path, and click `Export Video`.
16. Keep the project folder if you will revise or rerender later.

## Practical Order

- Tune ShotML before manual timing because reruns replace the automatic draft.
- Finish timing before scoring because score rows follow the shot list.
- Score before Markers when shot-linked markers should show score and penalties.
- Configure PiP before final overlay placement when added media changes where badges should sit.
- Configure Overlay before Review when text boxes need to align with the final badge stack.
- Check Metrics before Export when you need confidence, raw delta, or CSV confirmation.
- Export only after scrubbing near the final shot and confirming overlays, markers, review boxes, and PiP.

## Bundle Guidance

- Choose the project folder early when you want a reusable bundle.
- Keep using the same folder through revisions.
- Reopen the bundle from Project when you need another export version.

## Next Stops

- [panes/project.md](panes/project.md) for setup.
- [panes/shotml.md](panes/shotml.md) for detector tuning.
- [panes/splits.md](panes/splits.md) for manual timing.
- [panes/export.md](panes/export.md) for final render settings.
- [troubleshooting.md](troubleshooting.md) for common issues.

**Last updated:** 2026-04-23
**Referenced files last updated:** 2026-04-23
