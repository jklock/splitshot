# PopUp Pane

The PopUp pane creates short-lived callout bubbles on the stage. Use it when a shot needs a visible score callout, penalty callout, or other brief annotation tied to a precise point in the video.

## When To Use This Pane

- After the shot list is stable in [splits.md](splits.md).
- After scoring shots in [score.md](score.md) when you want score and penalty bubbles.
- When you need one popup for the selected shot.
- When you want to create one popup for every shot in the run.

## Key Controls

| Control | What it does |
| --- | --- |
| `Import Shots` | Creates or refreshes one shot-linked popup for every current shot. Re-running it updates existing shot popups instead of duplicating them. |
| `Add Bubble` | Adds a popup. If a shot is selected, the popup is linked to that shot; otherwise it is time-based at the current playhead. |
| Popup header | Selects that popup and seeks the video to the popup's start point. |
| Chevron | Shows or hides the popup editor without seeking the video. |
| `On` | Enables or disables that popup. |
| `Bubble name` | Names the popup card. If blank and shot-linked, the card inherits the shot label. |
| `Start mode` | Chooses `Time` or `Shot`. Shot mode follows the selected shot's timing. |
| `Shot` | Chooses the shot anchor for shot-linked popups. |
| `Text` | Edits manual time-based popup text. Shot-linked popups derive text from the shot score and penalties. |
| `Follow motion path` | Lets a popup move between stored path points during its duration. |
| `Placement`, `X`, and `Y` | Set the popup position. `Custom` enables direct normalized coordinates. |
| `Width` and `Height` | Force popup dimensions. Leave at auto-sized values when possible. |
| `Background`, `Text`, and `Opacity` | Style the popup bubble. |

## Score And Penalty Text

Shot-linked popups use the live shot score and penalties:

- IDPA popups use values like `-0`, `-1`, or `-3`.
- USPSA/IPSC popups use values like `A`, `C`, `D`, `M`, `NS`, or `M+NS`.
- Per-shot penalties are appended with the same shorthand used by Score, such as `PE x1`, `FTDR x1`, or `FPE x1`.
- Browser preview and export rendering both resolve the text from the current shot score, so rescoring a shot updates its popup output.

## How To Use It

1. Confirm shot timing in [splits.md](splits.md).
2. Score shots in [score.md](score.md).
3. Open PopUp.
4. Select a shot and click `Add Bubble` to create one popup for that shot.
5. Click `Import Shots` when every shot should get a popup.
6. Click a popup header to jump to its video time and edit placement or style.
7. Use the chevron to minimize cards when the inspector gets crowded.
8. Drag a rendered popup on the video to move it.

## Minimize And Navigation Behavior

- Popups start minimized by default.
- Switching to another pane and returning minimizes popup cards again.
- Selecting a popup seeks to that popup's start point.
- Minimizing a popup does not seek the video.
- A selected popup remains editable in the PopUp tool even when the playhead is slightly outside its active window.
- The popup inspector is designed to stay inside the right pane without horizontal scrolling.

## How It Affects The Rest Of SplitShot

- Shot-linked popup text follows Score.
- Popup timing follows Splits when the popup is anchored to a shot.
- Export uses the same popup text, timing, placement, and style as the preview.
- Metrics remains read-only; it reports score and split context but does not create popups.

## Common Mistakes And Fixes

| Problem | Fix |
| --- | --- |
| Popup text is disabled. | The popup is shot-linked, so text is generated from that shot's score and penalties. Edit the shot in Score. |
| The popup did not use the score you expected. | Recheck the active scoring preset and the shot row in [score.md](score.md). |
| `Import Shots` did not create duplicates. | That is expected. It refreshes one popup per shot. |
| Clicking a popup moved the video. | That is expected for popup selection. Use the chevron when you only want to minimize or expand. |
| A card is minimized after returning to the pane. | That is expected. Minimizable inspector items default back to minimized for navigation. |

## Related Guides

Previous: [overlay.md](overlay.md)
Next: [review.md](review.md)

**Last updated:** 2026-04-20
**Referenced files last updated:** 2026-04-20
