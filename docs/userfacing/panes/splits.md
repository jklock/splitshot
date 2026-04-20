# Splits Pane

The Splits pane is SplitShot's manual timing workbench. It shows the detected shot list, the waveform, selected-shot timing, and the expanded editing surface for timing events and detailed split review.

<img src="../../screenshots/SplitsPane.png" alt="Splits pane showing selected-shot controls, the timing table, and the waveform review area" width="960">

## When To Use This Pane

- Immediately after importing the primary video.
- Any time the detected shot list does not match the actual run.
- When you need to add, delete, nudge, or drag individual shot markers.
- When you want to add timing events such as reloads, malfunctions, or custom labels.
- After the [ShotML pane](shotml.md) has produced a useful automatic draft.

## Before You Start

- Import the primary video in [project.md](project.md) first.
- Let local analysis finish before editing shots.
- Use [shotml.md](shotml.md) for threshold changes, detector tuning, reruns, and timing-change proposals.
- Expect Score, Overlay, Review, Metrics, and Export to change when the timing changes.

## Key Controls

### Compact Pane

| Control | What it does |
| --- | --- |
| `Edit` | Opens the expanded timing workbench. |
| `Selected Shot` | Shows the active shot number and its timing summary. |
| `-10 ms`, `-1 ms`, `+1 ms`, `+10 ms` | Nudges the selected shot earlier or later. |
| `Delete Selected Shot` | Removes the active shot from the run. |
| Timing table | Lists each shot's segment name, split, total, and action summary. |

### Waveform Panel

| Control | What it does |
| --- | --- |
| Beep marker | Shows the detected start signal in orange. |
| Shot markers | Show each detected or manual shot in green. |
| `Select` | Selects and drags existing markers. |
| `Add Shot` | Places a new manual shot when you click the waveform. |
| `Zoom -`, `Zoom +` | Changes the visible time window. |
| `Amp -`, `Amp +` | Changes waveform amplitude scaling so quiet and loud peaks are easier to read. |
| `Reset` | Restores the default waveform view. |
| `Expand` | Opens the waveform-focused layout with the larger timeline and shot cards. |

### Expanded Timing Workbench

| Control | What it does |
| --- | --- |
| `Collapse` | Returns to the compact Splits pane. |
| `Event` | Chooses the timing event type: `Reload`, `Malfunction`, or `Custom Label`. |
| `Overlay label` | Sets the text that will appear for that event in the overlay/event row. |
| `Position` | Places the event before a shot, between two shots, or after the final shot. |
| `Add Event` | Inserts the timing event into the run. |
| `Unlock` | Switches a row into inline edit mode for direct split adjustments in the expanded table. |
| `Segment`, `Split`, `Total` | Show draw/split timing, run timing since the last reset, and stage time from the beep. |
| `Action` | Shows draw, reload, malfunction, or custom timing-event labels. |
| `Score` | Mirrors the current score letter for the row so timing and score stay aligned. |
| `Confidence` | Shows ShotML confidence or `Manual` for manual shot markers. |
| `Source` | Shows whether a row came from `ShotML` or a manual edit. |
| Event list `Remove` | Deletes a timing event without deleting the shot that surrounds it. |

<img src="../../screenshots/SplitsExpanded.png" alt="Expanded Splits workbench showing event controls and the full timing table with score, confidence, and source columns" width="840">

<img src="../../screenshots/WaveFormExpanded.png" alt="Expanded waveform editor showing the larger waveform viewport, selected shot cards, and Add Shot mode controls" width="840">

## How To Use It

1. Start in the compact pane and check whether the total shot count matches the run.
2. Select a shot from the table or click its waveform marker to make it the active shot.
3. Use the nudge buttons for tiny corrections, or drag a waveform marker when you need a larger change.
4. If the automatic detector needs a different threshold or detector profile, open [ShotML](shotml.md), adjust the setting, and re-run ShotML before doing detailed manual edits.
5. Switch to `Add Shot` and click the waveform when a real shot was missed completely.
6. Use `Delete Selected Shot` only for false detections.
7. Click `Edit` when you need the expanded workbench.
8. Add timing events with `Event`, `Overlay label`, and `Position` when you want explicit reload, malfunction, or custom timeline markers.
9. In the expanded table, use `Unlock` and the inline row fields when you want direct split editing instead of marker dragging.
10. Use `Expand` in the waveform footer when you want the timeline-first layout with more room for pan, zoom, and shot-card selection.

## How It Affects The Rest Of SplitShot

- Score rows follow the current shot list and selected-shot order.
- Overlay badges, timer summaries, and review text timing all follow the active split timeline.
- Metrics recomputes draw time, raw time, average split, and timeline exports after every timing change.
- Export burns in the timing you see here, not the original auto-detected draft.

## Common Mistakes And Fixes

| Problem | Fix |
| --- | --- |
| The app found too many shots. | Open ShotML, raise `Detection threshold`, then delete any remaining false shots. |
| The app missed quiet shots. | Open ShotML, lower `Detection threshold`, or add the missing shot manually with `Add Shot`. |
| The selected shot summary does not match the run. | Select the right marker first, then use the nudge buttons or drag the marker in the waveform. |
| A reload or malfunction disappeared after editing shots. | Recheck the timing event `Position`. Event anchors follow the shot order. |
| Score and Metrics changed unexpectedly. | That is normal after timing edits. Recheck the Score and Metrics panes after the split list is final. |

## Related Guides

Previous: [shotml.md](shotml.md)
Next: [score.md](score.md)

**Last updated:** 2026-04-19
**Referenced files last updated:** 2026-04-19
