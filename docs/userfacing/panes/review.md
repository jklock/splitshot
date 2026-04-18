# Review Pane

The Review pane controls what preview-only artifacts stay visible and manages the text boxes that can appear in both review and export. Use it to show or hide badges, add custom callouts, add an imported summary box, duplicate box layouts, and place boxes either by anchor or by direct stage placement.

<img src="../../screenshots/ReviewPane.png" alt="Review pane showing imported summary and custom text-box cards with placement, size, style, and duplicate or remove controls" width="960">

## When To Use This Pane

- After Overlay is close to final.
- When you want review-only visibility changes while you scrub the run.
- When you want custom text notes, a title card, or an imported PractiScore summary box.
- When you need a summary box to appear after the final shot.

## Before You Start

- Configure the badge stack in [overlay.md](overlay.md) first if you plan to lock boxes to that stack.
- Import PractiScore in [project.md](project.md) if you want an imported summary box with real content.
- Scrub near the final shot before judging how summary boxes appear.

## Key Controls

| Control | What it does |
| --- | --- |
| `Show timer badge` | Shows or hides the timer badge in the preview and export overlay state. |
| `Show draw badge` | Shows or hides the draw badge. |
| `Show split badges` | Shows or hides the running shot badge stack. |
| `Show scoring summary` | Shows or hides the final score badge or result badge. |
| `Lock review text boxes to the overlay stack` | Makes review text boxes follow the shot-stack layout instead of using independent placement. |
| `Add Custom Box` | Adds a blank manual text box card. |
| `Add Summary Box` | Adds an imported-summary card that uses PractiScore stage text after the final shot. |
| Box enable checkbox | Turns an individual box on or off. |
| `Duplicate` | Copies the selected box card and its settings. |
| `Remove` | Deletes that box. |
| `Content Source` | Chooses `Custom text` or `Imported summary`. |
| `Box text` | Edits the text for a custom box. Imported summary boxes show their source text instead of typed text. |
| `Box placement` | Chooses `Above Final Box`, one of the nine anchor positions, or `Custom`. |
| `Box X` and `Box Y` | Set custom normalized placement when the box is unlocked and using `Custom`. |
| `Box width` and `Box height` | Force the box dimensions. |
| `Background`, `Text`, and `Opacity` | Style the box card and final rendered box. |

## How To Use It

1. Decide which badges should stay visible while you review the run by toggling the four preview checkboxes.
2. Turn on `Lock review text boxes to the overlay stack` if you want the boxes to travel with the current badge stack layout from [overlay.md](overlay.md).
3. Use `Add Custom Box` for a title, note, or explanation that you type yourself.
4. Use `Add Summary Box` when you want the imported PractiScore stage summary after the final shot.
5. Set `Content Source` correctly on each card. Custom boxes use typed text. Imported summary boxes use PractiScore text.
6. Choose `Box placement` from the fixed anchors, `Above Final Box`, or `Custom`.
7. If you need direct placement, switch to `Custom`, then set `Box X` and `Box Y` or drag the rendered box on the stage.
8. Adjust `Box width`, `Box height`, `Background`, `Text`, and `Opacity` until the box reads clearly over the footage.
9. Use `Duplicate` when you want a new box that starts from an existing style and size.

## Summary Box Timing

- Imported summary boxes appear after the final shot when imported PractiScore data exists.
- `Above Final Box` keeps the box centered above the final score badge once that badge appears.
- If PractiScore is not imported yet, the summary box stays empty until stage data is available.

## How It Affects The Rest Of SplitShot

- Review uses the same text-box model that Export renders.
- Overlay stack choices affect Review when box locking is on.
- PractiScore import changes the content available to imported summary boxes.

## Common Mistakes And Fixes

| Problem | Fix |
| --- | --- |
| `Box X` and `Box Y` are disabled. | Set `Box placement` to `Custom` and turn off `Lock review text boxes to the overlay stack`. |
| The imported summary box is empty. | Import PractiScore in [project.md](project.md), then recheck the stage and competitor selection. |
| A box looks right in review but is missing from export. | Make sure the box is still enabled on its card. |
| A box moved when the overlay stack changed. | That is expected when the review boxes are locked to the overlay stack. |
| You need a box in the exact stage location. | Drag the rendered box on the video or use `Custom` placement with direct X and Y values. |

## Related Guides

Previous: [overlay.md](overlay.md)
Next: [export.md](export.md)

**Last updated:** 2026-04-18
**Referenced files last updated:** 2026-04-18