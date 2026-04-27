# SplitShot Workflow

This is the recommended path from raw stage video to finished local export.

## Before You Start

- Launch SplitShot from the root [README.md](../../README.md).
- Keep the primary video on a local drive.
- Keep your PractiScore login available if official match context is needed. A local CSV/TXT export still works as the fallback path.
- Keep secondary angles or graphics ready if you plan to use PiP.

## End-To-End Flow

1. Open [panes/project.md](panes/project.md).
2. Name the project, add a description, and import the primary video.
3. Wait for analysis to finish.
4. If needed, open [panes/shotml.md](panes/shotml.md), tune detector settings, and click `Re-run ShotML`.
5. Use `Generate Proposals` only when ShotML suggestions should become explicit reviewable changes.
6. Open [panes/splits.md](panes/splits.md) and confirm the shot count, beep, first shot, and waveform markers.
7. Nudge, drag, add, or delete shots until the timeline matches the video.
8. If official match context is needed, open [panes/project.md](panes/project.md) and click `Connect PractiScore`.
9. Finish the login or challenge in the visible PractiScore window, then let SplitShot load the available remote matches.
10. If only one remote match is available and nothing is staged yet, SplitShot imports it automatically. Otherwise choose the correct `Remote match` and click `Import Selected Match`.
11. Continue in the existing local `Match type`, `Stage #`, `Competitor name`, and `Place` controls.
12. Open [panes/score.md](panes/score.md), enable scoring, choose the preset, and score each shot.
13. Open [panes/pip.md](panes/pip.md) if added media is needed; sync and place each item.
14. Open [panes/score.md](panes/score.md) for final score and penalty edits if timing changed.
15. Open [panes/popup.md](panes/popup.md) for shot-linked or time-based markers, including text/image callouts.
16. Open [panes/overlay.md](panes/overlay.md) and configure badge layout, locks, fonts, colors, and score-token colors.
17. Open [panes/review.md](panes/review.md) to set badge visibility and add summary/custom text boxes.
18. Open [panes/metrics.md](panes/metrics.md) to inspect the dashboard, expanded table, or CSV/text exports.
19. Finish in [panes/export.md](panes/export.md), choose render settings, set output path, and click `Export Video`.
20. Keep the project folder if you will revise or rerender later.

## Practical Order

- Tune ShotML before manual timing because reruns replace the automatic draft.
- Keep a manual PractiScore CSV/TXT export around when remote sync is unavailable or when the staged source should change again.
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

**Last updated:** 2026-04-27
**Referenced files last updated:** 2026-04-27
