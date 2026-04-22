# PopUp Pane

The PopUp pane creates short-lived callout bubbles on top of the video. A bubble can be tied to a shot, tied to a timestamp, styled independently, and optionally moved along a motion path during its visible window.

<img src="../../screenshots/PopUpPane.png" alt="PopUp pane with an expanded shot-linked bubble, motion path controls, placement fields, and live popup preview" width="960">

<img src="../../screenshots/PopUpPane2.png" alt="Lower PopUp pane with motion path points, custom placement, bubble size, colors, and opacity" width="840">

## When To Use This Pane

- After shot timing is stable.
- After scoring, when you want score or penalty callouts.
- When one target transition or stage moment needs a visible annotation.
- When every shot should receive a score-linked popup.

## Key Controls

| Control | What it does |
| --- | --- |
| `Import Shots` | Creates or refreshes one shot-linked popup for every current shot. |
| `Add Bubble` | Adds a popup for the selected shot, or a time-based popup at the playhead. |
| Popup title button | Selects the popup and seeks the video to its start. |
| Card chevron | Expands or collapses the editor without changing the playhead. |
| `On` | Enables or disables the popup. |
| `Duplicate` | Copies the popup. |
| `Clear path` | Removes stored motion path points from the expanded motion-path editor. |
| `Remove` | Deletes the popup. |
| `Bubble name` | Sets the card title. |
| `Text` | Sets manual text for time-based popups. Shot-linked popups derive text from Score. |
| `Start mode` | Chooses `Time` or `Shot`. |
| `Start (seconds)` | Sets a time-based start. Disabled for shot-linked popups. |
| `Shot` | Chooses the shot anchor for shot-linked popups. |
| `Duration (seconds)` | Controls how long the popup stays visible. |
| `Follow motion path` | Enables guided movement across stored path points. |
| `Points` | Chooses the number of motion guide points. |
| Motion point `Go` buttons | Seek to each path point so you can place it accurately. |
| `Placement`, `X`, `Y` | Set fixed or custom normalized placement. |
| `Width`, `Height` | Force popup size. |
| `Background`, `Text`, `Opacity` | Style the bubble. |
| Color swatches | Open the shared color picker modal shown in [overlay.md](overlay.md). |

## Shot-Linked Text

Shot-linked popups use the live Score pane values:

- IDPA-style scores resolve as values like `-0`, `-1`, or `-3`.
- USPSA/IPSC-style scores resolve as values like `A`, `C`, `D`, `M`, or `NS`.
- Per-shot penalties are appended using the visible scoring shorthand.
- Rescoring a shot updates that popup in preview and export.

## How To Use It

1. Confirm timing in [splits.md](splits.md).
2. Score the run in [score.md](score.md) if popup text should follow shot scores.
3. Click `Add Bubble` for one selected-shot callout, or `Import Shots` for one popup per shot.
4. Expand the popup card.
5. Choose `Shot` or `Time` start behavior.
6. Set `Duration`.
7. Place the bubble with a fixed anchor or `Custom` X/Y values.
8. Enable `Follow motion path` when the callout should track movement; use each `Go` button to set later points. `Clear path` appears inside this expanded motion-path editor when a path exists.
9. Tune size, colors, and opacity against the live preview.
10. Use a color swatch when you want the expanded picker with quick swatches and HSL/hex controls.

## Common Fixes

| Problem | Fix |
| --- | --- |
| `Text` is disabled. | The popup is shot-linked. Edit the shot score instead. |
| The popup appears at the wrong time. | Check `Start mode`, `Shot`, and `Duration`. |
| The bubble does not move. | Turn on `Follow motion path` and set path points. |
| `Import Shots` did not duplicate existing popups. | That is expected; it refreshes one popup per shot. |
| A popup is missing from export. | Confirm the popup is `On` and visible during the exported time range. |

## Related Guides

Previous: [overlay.md](overlay.md)
Next: [review.md](review.md)

**Last updated:** 2026-04-22
**Referenced files last updated:** 2026-04-22
