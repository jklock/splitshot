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
| `>` / `v` in the pane header | Collapses the top PopUp controls down to `Previous` / `Next` only, or expands them again. |
| `Import` | Chooses whether `Import Shots` targets all shots, scored shots, or penalty/miss shots. Existing manual bubbles are preserved. |
| `Filter` | Narrows the card list and timeline to all, enabled, disabled, shot-linked, time-based, motion, missing text, or currently visible popups. |
| Popup timeline strip | Shows each popup's effective visible window using the same timing rules as preview and export. Click a bar to select and seek to that popup. |
| `Previous` / `Next` | Selects and seeks to the previous or next popup in the current filter, then keeps that card pinned at the top of the PopUp list. |
| `Play Window` | Plays the selected popup's exact visible window and stops at the end. |
| `Loop` | Loops the selected popup's exact visible window until the loop is stopped. |
| Popup title button | Selects the popup and seeks the video to its start. |
| Card chevron | Selects the popup, seeks the video to its start, and expands or collapses the editor. |
| `On` | Enables or disables the popup. |
| `Duplicate` | Copies the popup. |
| `Clear path` | Removes stored motion keyframes from the expanded motion editor. |
| `Remove` | Deletes the popup. |
| `Bubble name` | Sets the card title. |
| `Text` | Sets manual text for time-based popups. Shot-linked popups derive text from Score. |
| `Start mode` | Chooses `Time` or `Shot`. |
| `Start (seconds)` | Sets a time-based start. Disabled for shot-linked popups. |
| `Shot` | Chooses the shot anchor for shot-linked popups. |
| `Duration (seconds)` | Controls how long the popup stays visible. |
| `Follow motion path` | Enables the motion keyframe editor and on-video path preview. |
| `Add Keyframe` | Inserts a keyframe at the current playhead. |
| `Previous Keyframe` / `Next Keyframe` | Jumps between stored keyframes. |
| Motion keyframe list | Edits offset, easing, X, and Y for each stored keyframe. |
| On-video keyframe dots | Select and drag the base point or later keyframes directly on the video. |
| `Placement`, `X`, `Y` | Set fixed or custom normalized placement. |
| `Width`, `Height` | Force popup size. |
| `Bg`, `Text`, `Alpha` | Style the bubble with the same compact swatch/hex controls used in Overlay. |
| Color swatches | Open the shared color picker modal shown in [overlay.md](overlay.md). |
| Video-frame lock icon | Unlocks or relocks the shared layout resize controls. The waveform and inspector no longer duplicate this icon. |

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
4. Use `Import` before `Import Shots` when you only want scored or penalty/miss callouts.
5. Use `Filter`, the timeline strip, or `Previous` / `Next` to find the popup you want.
6. Collapse the top controls when you want to browse cards with more vertical room; the timeline stays visible and only `Previous` / `Next` remain.
7. The popup card list scrolls independently, so navigation keeps the active card at the top without shifting the whole inspector.
8. Use `Play Window` or `Loop` to verify exactly what appears during that popup's visible window.
9. Expand the popup card with the chevron.
10. Choose `Shot` or `Time` start behavior.
11. Set `Duration` inside that popup card.
12. Place the bubble with a fixed anchor or `Custom` X/Y values.
13. Enable `Follow motion path` when the callout should track movement.
14. Scrub the playhead, click `Add Keyframe`, then drag the on-video dots to place the base point and later keyframes directly on the frame.
15. Use the keyframe list for exact offset, easing, X, and Y edits. `Clear path` removes the stored motion path.
16. Tune size, colors, and opacity against the live preview.
17. Use a color swatch when you want the expanded picker with quick swatches and HSL/hex controls.

## Common Fixes

| Problem | Fix |
| --- | --- |
| `Text` is disabled. | The popup is shot-linked. Edit the shot score instead. |
| The popup appears at the wrong time. | Check `Start mode`, `Shot`, and `Duration`. |
| The bubble does not move. | Turn on `Follow motion path`, add at least one later keyframe, and place it on the video. |
| `Import Shots` did not duplicate existing popups. | That is expected; it refreshes one popup per shot. |
| A popup is missing from export. | Confirm the popup is `On` and visible during the exported time range. |

## Related Guides

Previous: [overlay.md](overlay.md)
Next: [review.md](review.md)

**Last updated:** 2026-04-23
**Referenced files last updated:** 2026-04-23
