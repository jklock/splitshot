# SplitShot User Guide

SplitShot is a local-first browser app for turning stage footage into a reviewed, scored, annotated, and exported video. This guide is the hub for the user-facing docs. Each pane guide below matches the current left-rail tool set and references fresh screenshots from the active UI.

## Start Here

1. Install and launch SplitShot from the root [README.md](../../README.md).
2. Open [panes/project.md](panes/project.md), name the run, and import the primary video.
3. Use [workflow.md](workflow.md) for the full import-to-export path.
4. Open the pane guide for any control you need to understand before changing it.

## Browser Layout

Every session uses the same workspace:

- The left rail switches between `Project`, `Score`, `Splits`, `ShotML`, `PiP`, `Overlay`, `PopUp`, `Review`, `Export`, and `Metrics`.
- The top status line reports the active file, analysis state, and sync offset.
- The center stage shows the primary video, optional PiP media, overlay badges, popup bubbles, review boxes, and the waveform.
- The right inspector changes to match the selected rail tool.
- The waveform, timing table, metrics table, and right inspector have expanded states where available.

Most edits auto-apply. Export is the main exception: the final video is created only when you click `Export Video`.

## Pane Guides

| Guide | Use it for |
| --- | --- |
| [panes/project.md](panes/project.md) | Project metadata, primary video import, PractiScore import, and project bundle controls |
| [panes/score.md](panes/score.md) | Ruleset selection, per-shot score cards, penalty fields, restore/delete actions, and imported score context |
| [panes/splits.md](panes/splits.md) | Shot timing, waveform review, marker nudges, manual shots, expanded timing edits, and timing events |
| [panes/shotml.md](panes/shotml.md) | Detector threshold, beep tuning, shot candidate settings, refinement, suppression, proposals, and runtime controls |
| [panes/pip.md](panes/pip.md) | Added media, picture-in-picture layout, per-item size/position/opacity, sync nudges, and export inclusion |
| [panes/overlay.md](panes/overlay.md) | Badge visibility, stack placement, timer/draw/final badge locks, fonts, colors, and score text colors |
| [panes/popup.md](panes/popup.md) | Shot-linked callouts, imported shot bubbles, custom timing, motion paths, placement, and bubble styling |
| [panes/review.md](panes/review.md) | Preview artifact toggles, imported summary boxes, custom text boxes, placement, size, and style |
| [panes/export.md](panes/export.md) | Render presets, frame settings, codecs, bitrate, output path, FFmpeg logs, and final export |
| [panes/metrics.md](panes/metrics.md) | Read-only run dashboard, expanded timing table, scoring context, CSV export, and text export |

## Common Workflows

- [workflow.md](workflow.md) walks through the recommended order from raw video to final export.
- [troubleshooting.md](troubleshooting.md) covers the most common user-facing problems and where to fix them.

## Repository Details

Architecture, development, and technical notes live in [../README.md](../README.md).

**Last updated:** 2026-04-22
**Referenced files last updated:** 2026-04-22
