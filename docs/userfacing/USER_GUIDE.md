# SplitShot User Guide

SplitShot v1.0.7 is a local-first app for turning stage footage into a reviewed, scored, annotated, and exported video. This guide is the hub for the user-facing docs. Each pane guide below matches the current left-rail tool set and references fresh screenshots from the active UI.

## Start Here

1. Install and launch SplitShot from the per-platform instructions in the root [README.md](../../README.md).
2. Open [panes/project.md](panes/project.md), create or select the project folder, and import PractiScore data when available.
3. Use [workflow.md](workflow.md) for the full import-to-export path.
4. Open the pane guide for any control you need to understand before changing it.

## Browser Layout

Every session uses the same workspace:

- The left rail switches between `Project`, `Media`, `Compose`, `Trim`, `Score`, `Splits`, `Markers`, `Overlay`, `Review`, `Export`, `In / Out`, `Queue`, `Metrics`, `ShotML`, and `Settings`.
- The top status line reports the active file, analysis state, and sync offset.
- The center stage shows the primary video, optional added media, overlay badges, markers, review boxes, and the waveform.
- The right inspector changes to match the selected rail tool.
- The right inspector can be resized; pane cards, tables, badge controls, and action buttons reflow to the available width without horizontal scrolling.
- Inspector card chevrons use `>` when collapsed and `v` when expanded.
- The waveform, timing table, metrics table, and right inspector have expanded states where available.
- Shared modals, including the color picker and export log, appear above the current pane.

Most edits auto-apply. Export saves stage settings. Queue is where packaged processing starts for one file per stage or one combined output.

Imported standings use the sport's own acronyms: `<division> - <place>/<division total>`, `<class> - <place>/<class total>`, and `Overall - <place>/<total competitors>`. Division and class are independent cohorts; there is no combined division-and-class result.

## Pane Guides

| Guide | Use it for |
| --- | --- |
| [panes/project.md](panes/project.md) | Project metadata, PractiScore import, competitor selection, and project-folder controls |
| [panes/media.md](panes/media.md) | Active stage selection, stage naming, primary media, added media, and stage creation |
| [panes/compose.md](panes/compose.md) | Added-media composition, stage defaults, per-source layout/size/position/opacity/sync, and preview truth |
| [panes/trim.md](panes/trim.md) | Bulk and per-source trimming, retained time around the run, trim derivatives, and added-media synchronization |
| [panes/score.md](panes/score.md) | Ruleset selection, per-shot score cards, penalty fields, restore/delete actions, and imported score context |
| [panes/splits.md](panes/splits.md) | Shot timing, waveform review, marker nudges, manual shots, expanded timing edits, and timing events |
| [panes/markers.md](panes/markers.md) | Shot-linked and time-based markers, text/image markers, guided Start/Finish motion authoring, the expanded markers workbench, and project-managed marker images |
| [panes/overlay.md](panes/overlay.md) | Badge visibility, stack placement, timer/draw/final badge locks, fonts, colors, and score text colors |
| [panes/review.md](panes/review.md) | Preview artifact toggles, Summary boxes, custom text boxes, placement, size, and style |
| [panes/export.md](panes/export.md) | Stage-local ffmpeg settings, output profiles, codecs, bitrate, and export logs |
| [panes/queue.md](panes/queue.md) | Queue membership, queue status, processing one file per stage, and processing one combined file |
| [panes/intro-outro.md](panes/intro-outro.md) | Match intro/outro media, text overlays, and selectable match-result fields |
| [panes/metrics.md](panes/metrics.md) | Read-only post-stage graphs, expanded timing table, scoring context, CSV export, and text export |
| [panes/shotml.md](panes/shotml.md) | Detector threshold, beep tuning, shot candidate settings, refinement, suppression, proposals, and runtime controls |
| [panes/settings.md](panes/settings.md) | App defaults, folder defaults in `splitshot.conf`, settings source attribution, and marker template defaults |

## Screenshot Coverage

The screenshot set covers every pane plus expanded timing, waveform, metrics, ShotML sections, score cards, added media cards, marker cards, Settings pane layers, Review text boxes, the shared color picker, and the export log modal.

## Common Workflows

- [workflow.md](workflow.md) walks through the recommended order from raw video to final export.
- [troubleshooting.md](troubleshooting.md) covers the most common user-facing problems and where to fix them.

## Repository Details

Architecture, development, and technical notes live in [../README.md](../README.md).
