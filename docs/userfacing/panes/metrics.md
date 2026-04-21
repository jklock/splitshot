# Metrics Pane

The Metrics pane is the read-only dashboard for the current run. It summarizes timing, scoring, and imported stage context, then lets you export the timeline as CSV or plain text for spreadsheets, notes, or post-match analysis.

<img src="../../screenshots/MetricsPane.png" alt="Metrics pane showing summary cards, the trend snapshot list, and the scoring context block beside the live preview" width="960">

## When To Use This Pane

- After timing and scoring are stable.
- When you want a quick stage dashboard without editing anything.
- When you want to export a spreadsheet-friendly CSV or a plain-text summary.
- When you want to compare draw time, raw time, split trend, and scoring result in one place.

## Before You Start

- Finish timing work in [splits.md](splits.md) first.
- Turn on scoring in [score.md](score.md) if you want a result summary.
- Import PractiScore in [project.md](project.md) if you want the imported source listed in scoring context.

## Key Controls

| Control | What it does |
| --- | --- |
| Summary cards | Show `Draw`, `Raw`, `Shots`, `Avg Split`, `Beep`, and the final scoring result in the inspector pane. |
| `Expand` | Opens the full-width Metrics workbench as one dense table. |
| `Trend Snapshot` | Lists each timeline row with its absolute time, split, run total, and stage total. |
| Confidence context | Shows ShotML confidence for detected shots or `Manual` when a row came from a manual timing edit. |
| Scoring context | Shows the current ruleset, result, shot points, penalties, raw time, and imported source. |
| `Export CSV` | Downloads the current run as a spreadsheet-friendly CSV file. |
| `Export Text` | Downloads the current run as a plain-text report. |

<img src="../../screenshots/MetricsPane2.png" alt="Metrics pane showing the lower scoring-context block and the Export CSV and Export Text buttons" width="840">

<img src="../../screenshots/MetricsCSV.png" alt="Metrics CSV export opened in a spreadsheet with columns for project, video, result, raw time, split timing, score letter, penalties, and confidence" width="760">

## How To Use It

1. Read the summary cards first for the headline numbers: draw time, raw time, shot count, average split, beep timing, and result.
2. Use `Trend Snapshot` when you want the row-by-row story of the run.
3. Click `Expand` when you want the big table view with shot, ShotML split, adjustment, final split, final time, score, penalties, PractiScore comparison, delta, confidence, and action context.
4. Check the `Scoring Context` block when you need to confirm the ruleset, result, penalty total, raw time, or imported source.
5. Click `Export CSV` when you want to graph the run or compare it in a spreadsheet.
6. Click `Export Text` when you want a note-friendly summary that can be pasted into a message, training log, or document.

## What The Metrics Mean

- `Draw` is the time from the beep to the first shot.
- `Raw` is the time from the beep to the final shot.
- `Shots` is the current shot count after any timing edits.
- `Avg Split` is the average split time across the current shot list.
- `Beep` is the detected start marker time in the source video.
- The final result card mirrors the current score summary.

## CSV And Text Export Uses

- CSV is best when you want to sort, chart, or compare runs across sessions.
- The CSV includes columns such as project, primary video, result label, result value, raw time, shot number, segment label, source, absolute time, split, cumulative time, score letter, penalties, and confidence.
- Text export is best when you want a quick timeline summary in notes or coaching feedback.

## How It Affects The Rest Of SplitShot

Metrics is read-only. It does not edit the project directly, but it changes immediately when you edit Splits, Score, or PractiScore context because it is built from the current timing rows and scoring summary.

## Common Mistakes And Fixes

| Problem | Fix |
| --- | --- |
| The numbers changed after editing Splits. | That is expected. Metrics follows the current timing model. |
| The result changed after rescoring a shot. | That is expected. Metrics follows the current scoring summary. |
| The CSV does not match the run you expected. | Recheck [splits.md](splits.md) and [score.md](score.md), then export again. |
| The pane feels like it should be editable. | Metrics is intentionally a read-only dashboard. Use Splits and Score for edits. |

## Related Guides

Previous: [export.md](export.md)
Next: [../workflow.md](../workflow.md)

**Last updated:** 2026-04-20
**Referenced files last updated:** 2026-04-20
