# Markers Pane

The Markers pane creates short-lived callouts on top of the video. A marker can be tied to a shot, tied to a timestamp, show text, show an image, show both, and optionally move along a motion path during its visible window.

<img src="../../screenshots/PopUpPane.png" alt="Markers pane with an expanded shot-linked marker, motion path controls, X/Y placement fields, and live preview" width="960">

<img src="../../screenshots/PopUpPane2.png" alt="Lower Markers pane with motion path points, direct X/Y placement, marker size, colors, and opacity" width="840">

## When To Use This Pane

- After shot timing is stable.
- After scoring, when you want score or penalty callouts.
- When one target transition or stage moment needs a visible annotation.
- When every shot should receive a score-linked marker.

## Key Controls

| Control | What it does |
| --- | --- |
| `Import Shots` | Creates or refreshes one shot-linked marker for every current shot. |
| `Add Time Marker` | Adds a time-based marker at the playhead. |
| `Shot Marker Template` | Sets the default content, duration, size, and motion behavior used when importing shot-linked markers. |
| `>` / `v` in the pane header | Collapses the authoring block while keeping the timeline and lists visible. |
| `Import` | Chooses whether `Import Shots` targets all shots, scored shots, or penalty/miss shots. Existing manual time markers are preserved. |
| `Filter` | Narrows the lists and timeline to all, enabled, disabled, shot-linked, time-based, motion, missing text, or currently visible markers. |
| Marker timeline strip | Shows each marker's effective visible window using the same timing rules as preview and export. Click a bar to select and seek to that marker. |
| `Previous` / `Next` | Selects and seeks to the previous or next marker in the current filter. |
| `Play Window` | Plays the selected marker's exact visible window and stops at the end. |
| `Loop` | Loops the selected marker's exact visible window until the loop is stopped. |
| `Shot-linked Markers` | Lists markers anchored to shots. |
| `Time Markers` | Lists time-based markers. |
| `Open Editor` | Opens the dedicated shot-linked marker editor with previous/next, duplicate, delete, and done actions. |
| Marker title button | Selects the marker and seeks the video to its start. |
| Card chevron | Selects the marker, seeks the video to its start, and expands or collapses the editor. |
| `On` | Enables or disables the marker. |
| `Duplicate` | Copies the marker. |
| `Clear path` | Removes stored motion keyframes from the expanded motion editor. |
| `Remove` | Deletes the marker. |
| `Bubble name` | Sets the card title. |
| `Text` | Sets manual text for time-based markers. Shot-linked text can still follow Score. |
| `Content` | Chooses `Text`, `Image`, or `Text + Image`. |
| `Image path` / `Browse` | Chooses a local image for the marker. Saved projects copy that image into the bundle automatically. |
| `Scale` | Chooses `Contain` or `Cover` for image rendering. |
| `Start mode` | Chooses `Time` or `Shot`. |
| `Start (seconds)` | Sets a time-based start. Disabled for shot-linked markers. |
| `Shot` | Chooses the shot anchor for shot-linked markers. |
| `Duration (seconds)` | Controls how long the marker stays visible. |
| `Follow motion path` | Enables the motion keyframe editor and on-video path preview. |
| `Add Keyframe` | Inserts a keyframe at the current playhead. |
| `Previous Keyframe` / `Next Keyframe` | Jumps between stored keyframes. |
| Motion keyframe list | Edits offset, easing, X, and Y for each stored keyframe. |
| On-video keyframe dots | Select and drag the base point or later keyframes directly on the video. |
| `X`, `Y` | Set direct normalized placement for the marker base point. |
| `Width`, `Height` | Force marker size. |
| `Bg`, `Text`, `Alpha` | Style the bubble with the same compact swatch/hex controls used in Overlay. |
| Color swatches | Open the shared color picker modal shown in [overlay.md](overlay.md). |
| Video-frame lock icon | Unlocks or relocks the shared layout resize controls. The waveform and inspector no longer duplicate this icon. |

## Shot-Linked Text

Shot-linked markers use the live Score pane values:

- IDPA-style scores resolve as values like `-0`, `-1`, or `-3`.
- USPSA/IPSC-style scores resolve as values like `A`, `C`, `D`, `M`, or `NS`.
- Per-shot penalties are appended using the visible scoring shorthand.
- Rescoring a shot updates that marker in preview and export.

## How To Use It

1. Confirm timing in [splits.md](splits.md).
2. Score the run in [score.md](score.md) if shot-linked marker text should follow shot scores.
3. Configure `Shot Marker Template` first when imported shot markers should share the same defaults.
4. Click `Add Time Marker` for one free-timed callout, or `Import Shots` for one shot-linked marker per shot.
5. Use `Import` before `Import Shots` when you only want scored or penalty/miss callouts.
6. Use `Filter`, the timeline strip, or `Previous` / `Next` to find the marker you want.
7. Collapse the top controls when you want to browse with more vertical room; the timeline and lists stay visible.
8. Use `Open Editor` when you want to walk shot-linked markers one shot at a time.
9. Use `Play Window` or `Loop` to verify exactly what appears during that marker's visible window.
10. Expand the marker card with the chevron.
11. Choose `Shot` or `Time` start behavior.
12. Set `Duration` inside that marker card.
12. Adjust `X` and `Y`, or drag the rendered marker on the video, when the bubble needs an exact position.
13. Enable `Follow motion path` when the callout should track movement.
14. Scrub the playhead, click `Add Keyframe`, then drag the on-video dots to place the base point and later keyframes directly on the frame.
15. Use the keyframe list for exact offset, easing, X, and Y edits. `Clear path` removes the stored motion path.
16. Tune size, colors, and opacity against the live preview.
17. Use a color swatch when you want the expanded picker with quick swatches and HSL/hex controls.

## Common Fixes

| Problem | Fix |
| --- | --- |
| `Text` is disabled. | The marker is shot-linked and text is coming from Score. Edit the shot score instead, or switch content/text source. |
| The marker appears at the wrong time. | Check `Start mode`, `Shot`, and `Duration`. |
| The bubble does not move. | Turn on `Follow motion path`, add at least one later keyframe, and place it on the video. |
| The image is missing after reopening. | Save the project after choosing the image so SplitShot can bundle it into the project folder. |
| A marker is missing from export. | Confirm the marker is `On`, still points to a valid image if it uses one, and is visible during the exported time range. |

## Related Guides

Previous: [overlay.md](overlay.md)
Next: [review.md](review.md)

**Last updated:** 2026-04-23
**Referenced files last updated:** 2026-04-23
