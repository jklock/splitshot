# Trim Pane

The Trim pane creates project-managed media derivatives. Bulk Trim can apply the same before-beep and after-last-shot window to selected stages, while Sources edits the active stage one file at a time.

<img src="../../screenshots/TrimPane.png" alt="Trim pane with bulk timing controls, video transport, and expanded primary and added-media source cards" width="960">

## Use This Pane For

- Keeping a fixed amount of video before the beep and after the last shot.
- Selecting any combination of stages and applying or clearing the same bulk trim across them.
- Applying a different start and end trim to one source.
- Aligning added videos with the primary video.
- Returning to the original source or undoing the latest trim change.

## Bulk Trim

| Control | What it does |
| --- | --- |
| `Play` / scrubber | Previews the active video and shows the current position. |
| Stage checkboxes | Select the stages included in the next bulk action. Every stage with primary media is selected initially. |
| `Select All` / `Clear` | Selects every trimmable stage or deselects every stage. |
| `Before beep` | Keeps this many seconds before each selected stage's detected beep. |
| `After last shot` | Keeps this many seconds after each selected stage's final shot. |
| `Reset` | Restores two seconds before and after the run. |
| `Undo` | Restores the previous bulk trim state for every stage included in that action. |
| `Apply All` | Creates trim derivatives for every video in each selected stage. |
| `Clear All` | Returns every source in each selected stage to its original. |
| `Show Log` | Opens the live trim log while ffmpeg processes the selected files. |

Bulk Apply and Clear use the same green aggregate progress bar as Queue. Each primary or added video advances the match-wide percentage, and the bar reaches 100% only after every selected video is terminal.

## Source Controls

Each source card identifies the original file and whether original or trimmed media is active.

| Control | What it does |
| --- | --- |
| `Start` / `End` | Set the source-specific retained range in seconds. |
| `Apply` | Creates and activates the derivative for that source. |
| `Clear` | Returns that source to its original media. |
| `Undo` | Restores the previous trim state for that source. |
| `Start at Beep` | Sets the start from the detected beep. |
| `End at Last Shot` | Sets the end from the final shot. |
| `Sync offset` and nudge buttons | Align an added video with the primary video. |
| `Analyze Sync` / `Re-run Sync` | Calculates a suggested sync relationship for added video. |

Still images and animated GIFs are not trimmed. Trim derivatives remain inside the project `Input/` area, and clearing a trim changes the active source back to the original without removing the original media.

Trimmed files use `Trim_Stage#_HH-MM-SS_YYYY-MM-DD.mp4`. Same-second collisions add `_2`, `_3`, and so on.

## Related Guides

Previous: [compose.md](compose.md)
Next: [score.md](score.md)
