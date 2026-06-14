# Metrics Pane

The Metrics pane is the read-only post-stage dashboard for the current run. It centers the run around six fixed graphs, then keeps the expanded table, scoring context, and CSV/text exports aligned with that same data.

<img src="../../screenshots/MetricsPane.png" alt="Metrics pane with summary cards, six graphs, compact timing table, scoring context, and export buttons beside the live preview" width="960">

<img src="../../screenshots/MetricsPane2.png" alt="Expanded Metrics view with six graphs and the full shot-by-shot timing table" width="960">

## When To Use This Pane

- After timing and scoring are stable.
- When you want a quick dashboard without editing anything.
- When you need a spreadsheet-friendly CSV.
- When you need a note-friendly text summary.
- When you want timing, placement, and pace context without editing anything.

## Key Controls

| Control | What it does |
| --- | --- |
| Summary cards | Show headline values such as draw, raw time, shot count, average split, beep, and result. |
| `Shot Breakdown` | Shows six shooter-relevant graphs: `Split Timeline`, `Split Distribution`, `Shooting vs Non-Shooting Time`, `Overall Placement`, `Division Placement`, and `Class Placement`. |
| Compact timing table | Keeps the row-by-row snapshot in view. The columns are `Shot`, `Split`, `Run`, `Score`, `ShotML`, and `Action`. |
| Scoring context block | Shows imported `Stage #`, `Competitor`, and `Place` first, followed by ruleset, result, raw/final timing, penalties, and points. |
| `Export CSV` | Downloads the current metrics table as CSV. |
| `Export Text` | Downloads a plain-text run summary. |
| `Expand` | Opens the full-width Metrics table. |
| `Collapse` | Returns from the expanded table to the normal workspace. |

## Expanded Table Columns

| Column | Meaning |
| --- | --- |
| `Shot` | Shot or event row label. |
| `ShotML Split` | Automatic detector split before manual adjustment. |
| `Adjustment` | Manual timing delta. |
| `Final Split` | Final split after edits. |
| `Final Time` | Final cumulative time. |
| `Score` | Current per-shot score text. |
| `Penalties` | Current penalty shorthand. |
| `PractiScore` | Imported official raw comparison value. |
| `Delta` | Difference against imported official timing when available. |
| `Confidence` | ShotML confidence or manual context. |
| `Action` | Draw, reload, malfunction, custom event, or other timing context. |

## How To Use It

1. Read the summary cards for draw, raw, shots, average split, beep, and result.
2. Start with `Split Timeline` to see split-by-split pace.
3. Use `Split Distribution` to spot interval outliers and hesitation points.
4. Use `Shooting vs Non-Shooting Time` to separate shooting cadence from movement and dead time.
5. Check `Overall Placement`, `Division Placement`, and `Class Placement` when imported match data is available.
6. Review the compact timing table for the row-by-row details.
7. Check scoring context when you need stage, competitor, place, ruleset, penalty, or official comparison details. The context is a two-column table so long names wrap instead of clipping.
8. Click `Expand` for the dense table view.
9. Click `Export CSV` for spreadsheet work.
10. Click `Export Text` for coaching notes, messages, or training logs.

## Read-Only Behavior

Metrics does not edit the project. It changes when the source data changes:

- Timing edits come from [splits.md](splits.md).
- Detector confidence and ShotML split context come from [shotml.md](shotml.md).
- Scores and penalties come from [score.md](score.md).
- Imported official context comes from [project.md](project.md).

## Common Fixes

| Problem | Fix |
| --- | --- |
| Metrics changed after timing edits. | That is expected. It follows the current split list. |
| Result changed after scoring. | That is expected. It follows the live scoring summary. |
| CSV is missing official comparison. | Import PractiScore in [project.md](project.md). The graphs still render without it. |
| A row looks wrong but Metrics has no editor. | Fix the source pane: Splits for timing, Score for scoring, Project for imported context. |

## Related Guides

Previous: [settings.md](settings.md)
Next: [../workflow.md](../workflow.md)
