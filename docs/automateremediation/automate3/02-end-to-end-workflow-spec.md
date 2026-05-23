# End-To-End Workflow Spec

This document defines how users move through the finished app.

## Landing To Stage

1. User opens SplitShot.
2. Landing Page shows recent activity, New Stage, New Match, Open File, and three entry cards.
3. User chooses Stage Video Edit or New Stage.
4. Stage Video Edit opens in standalone stage mode.
5. If no media is loaded, Stage shows a professional empty state with import/open actions.
6. After media import, Stage shows preview, timeline/waveform, inspector, and stage tool groups.

Navigation rule: entering Stage from Landing does not create a Match unless the user asks.

Current limitation: `/api/landing/recent` currently returns only stage project directories from `~/.splitshot/projects`. It does not return Match or Library records. The Landing Page UI must display only what the route returns and must not fabricate Match/Library recent items. Future backend work may extend the route to aggregate workspace and library records.

## Stage Editing

1. User reviews media, timing, scoring, markers, overlay, review, metrics, ShotML, and export.
2. User can configure output profiles, retained review source, and render plan.
3. User can add PiP/multi-angle clips, line up angles, assign camera jobs, balance audio, and override smart cuts.
4. User can export a stage or save/review it into Library.

Library rule: completed/reviewed/exported stage work records history in Performance Library without navigating away.

## Stage To Match

1. User can choose Add to Match or Create Match from Stage.
2. The app creates or attaches a match workspace in the background.
3. Stage stays visible unless the user chooses Open Match.
4. Stage context shows match attachment and return/open-match affordances.

## Match Creation

1. User enters Match Video Edit from Landing or Stage.
2. Match view shows match header and stage grid.
3. User creates stages, imports videos, imports PractiScore data, and edits stage metadata.
4. Stage grid shows status, thumbnail, missing media, scoring summary, shared/custom setting badges, and actions.

## Match To Stage And Back

1. User clicks Open on a stage row.
2. Stage Video Edit opens in workspace-stage mode.
3. Stage context shows match name, stage name, inherited/defaulted status, and Return to Match.
4. User edits deeply in Stage.
5. Return to Match returns to the same match grid, scroll position, selected stage, and active tab where practical.

## Setup Once Apply Everywhere

1. User configures Stage 1.
2. User returns to Match Video Edit.
3. Match detects Stage 1 has reusable configuration.
4. User opens Preview Changes.
5. Preview shows affected stages, settings to apply, and override conflicts.
6. User confirms Apply to All.
7. Stage grid updates with shared badges and result summary.

## Export Workflows

- Stage export runs inside Stage Video Edit.
- Batch export runs inside Match Video Edit.
- Match Recap and Stage Composite are separate Match workflows.
- Export progress is visible, cancellable where possible, and reports output paths.

## Library Reopen

1. User opens Performance Library.
2. User filters/searches/selects a record.
3. Detail panel shows metrics, proxy/archive state, notes, tags, and available reopen actions.
4. Open Stage opens Stage Video Edit in the correct context.
5. Open Match opens Match Video Edit in the correct context.
6. Unresolved targets remain inspectable and clearly unavailable.
