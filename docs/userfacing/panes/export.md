# Export Pane

The Export pane configures ffmpeg export settings for the active stage. It does not start processing directly.

## Use This Pane For

- Setting the render settings for the active stage.
- Saving stage-local export settings before queueing.
- Checking the export log for the most recent processing run.

## Key Controls

| Control | What it does |
| --- | --- |
| Output Profiles selector | Loads or switches an output profile for the active stage. |
| `Create` / `Delete` | Creates or removes an output profile. |
| `Profile name` | Names the selected output profile. |
| `Type` | Chooses the stage output type. |
| `Frame profile` | Chooses the output framing override. |
| `Preset` | Chooses a built-in export preset or `Custom`. |
| `Quality` / `Aspect ratio` / `Output Width` / `Output Height` | Set the output frame. |
| `Frame rate` / `Video codec` / `Audio codec` | Set render codecs and playback rate. |
| `Video bitrate (Mbps)` / `Audio kbps` | Set target bitrate values. |
| `Color` / `Ffmpeg preset` / `2-pass` | Set encoding behavior for the active stage. |
| `Show Log` | Opens the export log from the latest queue processing run. |

## Workflow

1. Finish Compose, Trim, scoring, overlay, review, and metrics checks for the active stage.
2. Set the output profile and any stage-local export settings.
3. Move to [queue.md](queue.md) to queue the stage and process one or more outputs.

## Notes

- Export settings are stage-local.
- Queue is the only export execution surface.
- Review the stage here, then queue and process it downstream.

## Related Guides

Previous: [review.md](review.md)
Next: [queue.md](queue.md)
