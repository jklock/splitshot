# Metrics Pane

The Metrics pane is the read-only post-stage dashboard for the current run. It centers the timing story with four non-sport-specific graphs — `Shot / Interval Timeline`, `Split / Interval Bar Chart`, `Run Comparison Overlay`, and `Stage Segment Breakdown` — then keeps the expanded table, scoring context, and CSV/text exports aligned with that same data.

<img src="../../screenshots/MetricsPane.png" alt="Metrics pane with summary cards, stage-story graphs, compact timing table, scoring context, and export buttons beside the live preview" width="960">

<img src="../../screenshots/MetricsPane2.png" alt="Expanded Metrics view with post-stage graphs and the full shot-by-shot timing table" width="960">

## When To Use This Pane

- After timing and scoring are stable.
- When you want a quick dashboard without editing anything.
- When you need a spreadsheet-friendly CSV.
- When you need a note-friendly text summary.
- When you want to see where the run actually slowed down without relying on sport-specific scoring.

## Key Controls

| Control | What it does |
| --- | --- |
| Summary cards | Show headline values such as draw, raw time, shot count, average split, beep, and result. |
| `Stage Story` | Shows the four post-stage graphs: `Shot / Interval Timeline`, `Split / Interval Bar Chart`, `Run Comparison Overlay`, and `Stage Segment Breakdown`. The comparison overlay currently uses the ShotML baseline as the reference series. |
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
2. Start with `Shot / Interval Timeline` to see where the run actually spent time from beep to last shot.
3. Use `Split / Interval Bar Chart` to spot interval outliers and hesitation points between shots.
4. Check `Run Comparison Overlay` to compare the current cumulative pace against the ShotML reference baseline.
5. Use `Stage Segment Breakdown` to separate shooting cadence from movement, reload/manipulation, and dead time.
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
| CSV is missing official comparison. | Import PractiScore in [project.md](project.md). The post-stage graphs still render without it. |
| The comparison graph is not using another run yet. | In V1 the overlay uses the ShotML baseline as the reference series. External run-to-run reference selection is future work. |
| A row looks wrong but Metrics has no editor. | Fix the source pane: Splits for timing, Score for scoring, Project for imported context. |

## Related Guides

Previous: [settings.md](settings.md)
Next: [../workflow.md](../workflow.md)

**Last updated:** 2026-05-06
**Referenced files last updated:** 2026-05-06
